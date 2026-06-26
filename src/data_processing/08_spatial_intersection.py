"""
Spatial Intersection: Final Dining Hotspot Identification
==========================================================

Purpose: Identify final dining hotspots by intersecting restaurant density zones
         with taxi dropoff hotspots

Mathematical Definition:
    H_final = {h | h ∈ (D ∩ T) ∧ area(h) ≥ 10,000 m² ∧ overlap_ratio(h) ≥ 0.15}

where:
    D = restaurant dining zones
    T = taxi hotspot areas
    overlap_ratio(h) = min(area(h)/area(D), area(h)/area(T))

Input:
    - data/processed/dining_zones.geojson
    - data/processed/taxi_hotspots.geojson

Output:
    - data/processed/final_hotspots.geojson
    - data/processed/intersection_analysis.json

Author: Where to DINE Project
Date: 2025-11-09
"""

import geopandas as gpd
import pandas as pd
import numpy as np
from pathlib import Path
import json
import logging
from typing import Tuple, List
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
import sys
sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent.parent))
from utils.config_loader import load_config, get_config_value
from src.analysis.scoring import (
    normalize_zscore_to_100,
    compute_composite_score,
    compute_tiebreaker_rank,
    PREFERENCE_PROFILES,
    compute_access_score_decay,
    compute_access_score_euclidean,
    compute_baseline_score,
    compute_entropy_weights,
    compute_topsis_ranking,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Scoring version 2 (robust, replaces max-normalization)
# ---------------------------------------------------------------------------

def calculate_hotspot_scores_v2(gdf_hotspots: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Calculate robust composite scores using z-score + winsorization.

    Replaces the unstable max-normalization with:
    - z-score standardization + winsorization (1%, 99%)
    - rescale to [0, 100]
    - entropy-weighted composite (default: equal weights)
    - deterministic tie-breaker

    Parameters
    ----------
    gdf_hotspots : gpd.GeoDataFrame
        Hotspots with n_restaurants, taxi_weight, intersection_area_sqm

    Returns
    -------
    gpd.GeoDataFrame
        Hotspots with old and new score columns
    """
    logger.info("Calculating robust (v2) composite scores...")

    if len(gdf_hotspots) == 0:
        return gdf_hotspots

    # Calculate raw densities
    area_km2 = gdf_hotspots['intersection_area_sqm'] / 1_000_000
    area_km2 = area_km2.replace(0, np.nan).fillna(1e-6)

    gdf_hotspots['restaurant_density'] = gdf_hotspots['n_restaurants'] / area_km2
    gdf_hotspots['taxi_density'] = gdf_hotspots['taxi_weight'] / area_km2

    # Robust normalization: z-score + winsorization + rescale to [0, 100]
    gdf_hotspots['restaurant_score_v2'] = normalize_zscore_to_100(
        gdf_hotspots['restaurant_density'].values,
        winsorize=True,
        winsorize_pct=(0.01, 0.99)
    )
    gdf_hotspots['taxi_score_v2'] = normalize_zscore_to_100(
        gdf_hotspots['taxi_density'].values,
        winsorize=True,
        winsorize_pct=(0.01, 0.99)
    )

    # -------------------------------------------------------------------
    # Entropy-weighted TOPSIS (replaces fixed 0.5/0.5 weighting)
    # -------------------------------------------------------------------
    indicators = np.column_stack([
        gdf_hotspots['restaurant_score_v2'].values,
        gdf_hotspots['taxi_score_v2'].values
    ])
    # Ensure non-negative for entropy weights
    indicators = np.clip(indicators, 0, None)

    entropy_w = compute_entropy_weights(indicators)
    topsis_scores = compute_topsis_ranking(
        indicators,
        weights=entropy_w,
        benefit_criteria=[0, 1]  # both are benefit criteria
    )
    # TOPSIS returns [0, 1]; rescale to [0, 100] for consistency
    gdf_hotspots['popularity_score_v2'] = topsis_scores * 100.0
    gdf_hotspots['entropy_weight_restaurant'] = entropy_w[0]
    gdf_hotspots['entropy_weight_taxi'] = entropy_w[1]

    # Tie-breaker: TOPSIS → taxi_score_v2 → restaurant_score_v2 → original index
    gdf_v2_sorted = gdf_hotspots.sort_values(
        by=['popularity_score_v2', 'taxi_score_v2', 'restaurant_score_v2'],
        ascending=[False, False, False],
        kind='mergesort'
    ).reset_index(drop=True)
    gdf_v2_sorted['rank_v2'] = np.arange(1, len(gdf_v2_sorted) + 1)
    gdf_hotspots = gdf_v2_sorted

    logger.info(f"V2 Entropy-TOPSIS score statistics:")
    logger.info(f"  Restaurant score: [{gdf_hotspots['restaurant_score_v2'].min():.1f}, {gdf_hotspots['restaurant_score_v2'].max():.1f}]")
    logger.info(f"  Taxi score: [{gdf_hotspots['taxi_score_v2'].min():.1f}, {gdf_hotspots['taxi_score_v2'].max():.1f}]")
    logger.info(f"  TOPSIS popularity score: [{gdf_hotspots['popularity_score_v2'].min():.1f}, {gdf_hotspots['popularity_score_v2'].max():.1f}]")
    logger.info(f"  Entropy weights: restaurant={entropy_w[0]:.3f}, taxi={entropy_w[1]:.3f}")

    return gdf_hotspots


def load_spatial_data(
    dining_zones_path: str,
    taxi_hotspots_path: str
) -> Tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """
    Load dining zones and taxi hotspots.

    Parameters:
    -----------
    dining_zones_path : str
        Path to dining_zones.geojson
    taxi_hotspots_path : str
        Path to taxi_hotspots.geojson

    Returns:
    --------
    gdf_dining : gpd.GeoDataFrame
        Restaurant dining zones
    gdf_taxi : gpd.GeoDataFrame
        Taxi hotspot areas
    """
    logger.info("Loading spatial data...")

    gdf_dining = gpd.read_file(dining_zones_path)
    gdf_taxi = gpd.read_file(taxi_hotspots_path)

    logger.info(f"Loaded {len(gdf_dining)} dining zones")
    logger.info(f"Loaded {len(gdf_taxi)} taxi hotspots")
    logger.info(f"Dining zones CRS: {gdf_dining.crs}")
    logger.info(f"Taxi hotspots CRS: {gdf_taxi.crs}")

    # Ensure same CRS
    if gdf_dining.crs != gdf_taxi.crs:
        logger.info("Reprojecting to common CRS (EPSG:4326)...")
        gdf_dining = gdf_dining.to_crs("EPSG:4326")
        gdf_taxi = gdf_taxi.to_crs("EPSG:4326")

    return gdf_dining, gdf_taxi


def compute_spatial_intersections(
    gdf_dining: gpd.GeoDataFrame,
    gdf_taxi: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    """
    Compute spatial intersections between dining zones and taxi hotspots.

    For each pair of overlapping zones, create an intersection polygon
    with combined attributes.

    Parameters:
    -----------
    gdf_dining : gpd.GeoDataFrame
        Restaurant dining zones
    gdf_taxi : gpd.GeoDataFrame
        Taxi hotspots

    Returns:
    --------
    gpd.GeoDataFrame
        Intersection polygons with combined attributes
    """
    logger.info("Computing spatial intersections...")

    # Project to meters for accurate area calculations
    crs_projected = "EPSG:2263"  # NAD83 / NY Long Island
    gdf_d_proj = gdf_dining.to_crs(crs_projected)
    gdf_t_proj = gdf_taxi.to_crs(crs_projected)

    intersections = []
    intersection_count = 0

    # Nested loop to find all intersections
    for idx_d, dining_zone in gdf_d_proj.iterrows():
        for idx_t, taxi_zone in gdf_t_proj.iterrows():
            # Check if geometries intersect
            if dining_zone.geometry.intersects(taxi_zone.geometry):
                # Compute intersection geometry
                intersection_geom = dining_zone.geometry.intersection(taxi_zone.geometry)

                # Skip if empty or point/line (we want polygons)
                if intersection_geom.is_empty:
                    continue
                if intersection_geom.geom_type not in ['Polygon', 'MultiPolygon']:
                    continue

                # Calculate areas
                dining_area = dining_zone.geometry.area
                taxi_area = taxi_zone.geometry.area
                intersection_area = intersection_geom.area

                # Calculate overlap ratios
                overlap_ratio_dining = intersection_area / dining_area
                overlap_ratio_taxi = intersection_area / taxi_area
                min_overlap_ratio = min(overlap_ratio_dining, overlap_ratio_taxi)

                # Combine attributes
                intersections.append({
                    'dining_cluster_id': dining_zone.get('cluster_id', idx_d),
                    'taxi_hotspot_id': taxi_zone.get('hotspot_id', idx_t),
                    'n_restaurants': dining_zone.get('n_restaurants', 0),
                    'n_taxi_dropoffs': taxi_zone.get('n_dropoffs', 0),
                    'taxi_weight': taxi_zone.get('total_weight', 0),
                    'avg_rating': dining_zone.get('avg_rating', None),
                    'dining_area_sqm': dining_area,
                    'taxi_area_sqm': taxi_area,
                    'intersection_area_sqm': intersection_area,
                    'overlap_ratio_dining': overlap_ratio_dining,
                    'overlap_ratio_taxi': overlap_ratio_taxi,
                    'min_overlap_ratio': min_overlap_ratio,
                    'geometry': intersection_geom
                })

                intersection_count += 1

    logger.info(f"Found {intersection_count} intersections")

    # Create GeoDataFrame
    if intersections:
        gdf_intersections = gpd.GeoDataFrame(intersections, crs=crs_projected)
    else:
        logger.warning("No intersections found!")
        gdf_intersections = gpd.GeoDataFrame(columns=['geometry'], crs=crs_projected)

    return gdf_intersections


def apply_filtering_criteria(
    gdf_intersections: gpd.GeoDataFrame,
    min_area_sqm: float = 10000.0,
    min_overlap_ratio: float = 0.15
) -> gpd.GeoDataFrame:
    """
    Filter intersections based on area and overlap criteria.

    Criteria:
    - Minimum area: 10,000 m² (approx 2-3 NYC blocks)
    - Minimum overlap ratio: 15% (ensures meaningful spatial agreement)

    Parameters:
    -----------
    gdf_intersections : gpd.GeoDataFrame
        Raw intersection polygons
    min_area_sqm : float
        Minimum intersection area in square meters (default: 10,000)
    min_overlap_ratio : float
        Minimum overlap ratio (default: 0.15)

    Returns:
    --------
    gpd.GeoDataFrame
        Filtered hotspots
    """
    logger.info("Applying filtering criteria...")
    logger.info(f"  Minimum area: {min_area_sqm:,.0f} m²")
    logger.info(f"  Minimum overlap ratio: {min_overlap_ratio:.0%}")

    if len(gdf_intersections) == 0:
        logger.warning("No intersections to filter")
        return gdf_intersections

    # Apply filters
    mask_area = gdf_intersections['intersection_area_sqm'] >= min_area_sqm
    mask_overlap = gdf_intersections['min_overlap_ratio'] >= min_overlap_ratio

    gdf_filtered = gdf_intersections[mask_area & mask_overlap].copy()

    logger.info(f"Filtering results:")
    logger.info(f"  Before: {len(gdf_intersections)} intersections")
    logger.info(f"  Area filter: {mask_area.sum()} passed")
    logger.info(f"  Overlap filter: {mask_overlap.sum()} passed")
    logger.info(f"  After both filters: {len(gdf_filtered)} hotspots")

    if len(gdf_filtered) == 0:
        logger.warning("No hotspots passed filtering criteria!")
        logger.warning("Consider lowering thresholds or checking data quality")

    return gdf_filtered


def calculate_composite_scores_v2(gdf_hotspots: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Calculate robust composite scores using z-score + winsorization (v2).

    Replaces the unstable max-normalization with:
    - z-score standardization + winsorization (1%, 99%)
    - rescale to [0, 100]
    - deterministic tie-breaker

    Parameters
    ----------
    gdf_hotspots : gpd.GeoDataFrame
        Hotspots with n_restaurants, taxi_weight, intersection_area_sqm

    Returns
    -------
    gpd.GeoDataFrame
        Hotspots with v2 score columns added
    """
    logger.info("Calculating robust (v2) composite scores...")

    if len(gdf_hotspots) == 0:
        return gdf_hotspots

    # Calculate raw densities
    area_km2 = gdf_hotspots['intersection_area_sqm'] / 1_000_000
    area_km2 = area_km2.replace(0, np.nan).fillna(1e-6)

    gdf_hotspots['restaurant_density'] = gdf_hotspots['n_restaurants'] / area_km2
    gdf_hotspots['taxi_density'] = gdf_hotspots['taxi_weight'] / area_km2

    # Robust normalization: z-score + winsorization + rescale to [0, 100]
    gdf_hotspots['restaurant_score_v2'] = normalize_zscore_to_100(
        gdf_hotspots['restaurant_density'].values,
        winsorize=True, winsorize_pct=(0.01, 0.99)
    )
    gdf_hotspots['taxi_score_v2'] = normalize_zscore_to_100(
        gdf_hotspots['taxi_density'].values,
        winsorize=True, winsorize_pct=(0.01, 0.99)
    )

    # -------------------------------------------------------------------
    # Entropy-weighted TOPSIS (replaces fixed 0.5/0.5 weighting)
    # -------------------------------------------------------------------
    indicators = np.column_stack([
        gdf_hotspots['restaurant_score_v2'].values,
        gdf_hotspots['taxi_score_v2'].values
    ])
    # Ensure non-negative for entropy weights
    indicators = np.clip(indicators, 0, None)

    entropy_w = compute_entropy_weights(indicators)
    topsis_scores = compute_topsis_ranking(
        indicators,
        weights=entropy_w,
        benefit_criteria=[0, 1]  # both are benefit criteria
    )
    # TOPSIS returns [0, 1]; rescale to [0, 100] for consistency
    gdf_hotspots['popularity_score_v2'] = topsis_scores * 100.0
    gdf_hotspots['entropy_weight_restaurant'] = entropy_w[0]
    gdf_hotspots['entropy_weight_taxi'] = entropy_w[1]

    # Tie-breaker: TOPSIS → taxi_score_v2 → restaurant_score_v2 → original index
    # Manually create rank_v2 without overwriting v1's 'rank' column
    gdf_v2_sorted = gdf_hotspots.sort_values(
        by=['popularity_score_v2', 'taxi_score_v2', 'restaurant_score_v2'],
        ascending=[False, False, False],
        kind='mergesort'
    ).reset_index(drop=True)
    gdf_v2_sorted['rank_v2'] = np.arange(1, len(gdf_v2_sorted) + 1)
    gdf_hotspots = gdf_v2_sorted

    logger.info(f"V2 Entropy-TOPSIS score statistics:")
    logger.info(f"  Restaurant score: [{gdf_hotspots['restaurant_score_v2'].min():.1f}, {gdf_hotspots['restaurant_score_v2'].max():.1f}]")
    logger.info(f"  Taxi score: [{gdf_hotspots['taxi_score_v2'].min():.1f}, {gdf_hotspots['taxi_score_v2'].max():.1f}]")
    logger.info(f"  TOPSIS popularity score: [{gdf_hotspots['popularity_score_v2'].min():.1f}, {gdf_hotspots['popularity_score_v2'].max():.1f}]")
    logger.info(f"  Entropy weights: restaurant={entropy_w[0]:.3f}, taxi={entropy_w[1]:.3f}")

    return gdf_hotspots


def calculate_composite_scores(gdf_hotspots: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Calculate composite popularity scores for each hotspot (legacy v1).

    Uses max-normalization, which is unstable to outliers.
    Kept for backward compatibility and A/B comparison.

    Parameters:
    -----------
    gdf_hotspots : gpd.GeoDataFrame
        Filtered hotspots

    Returns:
    --------
    gpd.GeoDataFrame
        Hotspots with composite scores
    """
    logger.info("Calculating composite popularity scores (v1 legacy)...")

    if len(gdf_hotspots) == 0:
        return gdf_hotspots

    # Restaurant density (restaurants per km²)
    gdf_hotspots['restaurant_density'] = (
        gdf_hotspots['n_restaurants'] / (gdf_hotspots['intersection_area_sqm'] / 1_000_000)
    )

    # Taxi activity density (weighted dropoffs per km²)
    gdf_hotspots['taxi_density'] = (
        gdf_hotspots['taxi_weight'] / (gdf_hotspots['intersection_area_sqm'] / 1_000_000)
    )

    # Normalize to [0, 100]
    if gdf_hotspots['restaurant_density'].max() > 0:
        gdf_hotspots['restaurant_score'] = (
            100 * gdf_hotspots['restaurant_density'] / gdf_hotspots['restaurant_density'].max()
        )
    else:
        gdf_hotspots['restaurant_score'] = 0

    if gdf_hotspots['taxi_density'].max() > 0:
        gdf_hotspots['taxi_score'] = (
            100 * gdf_hotspots['taxi_density'] / gdf_hotspots['taxi_density'].max()
        )
    else:
        gdf_hotspots['taxi_score'] = 0

    # Composite popularity score
    gdf_hotspots['popularity_score'] = (
        0.5 * gdf_hotspots['restaurant_score'] +
        0.5 * gdf_hotspots['taxi_score']
    )

    # Rank hotspots
    gdf_hotspots['rank'] = gdf_hotspots['popularity_score'].rank(ascending=False, method='dense').astype(int)

    logger.info(f"Score statistics:")
    logger.info(f"  Restaurant score: [{gdf_hotspots['restaurant_score'].min():.1f}, {gdf_hotspots['restaurant_score'].max():.1f}]")
    logger.info(f"  Taxi score: [{gdf_hotspots['taxi_score'].min():.1f}, {gdf_hotspots['taxi_score'].max():.1f}]")
    logger.info(f"  Popularity score: [{gdf_hotspots['popularity_score'].min():.1f}, {gdf_hotspots['popularity_score'].max():.1f}]")

    return gdf_hotspots


def save_outputs(
    gdf_hotspots: gpd.GeoDataFrame,
    gdf_dining: gpd.GeoDataFrame,
    gdf_taxi: gpd.GeoDataFrame,
    output_dir: str
):
    """
    Save final hotspots and analysis results.

    Parameters:
    -----------
    gdf_hotspots : gpd.GeoDataFrame
        Final filtered hotspots with scores
    gdf_dining : gpd.GeoDataFrame
        Original dining zones
    gdf_taxi : gpd.GeoDataFrame
        Original taxi hotspots
    output_dir : str
        Output directory
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Convert to WGS84 for output
    gdf_hotspots_wgs84 = gdf_hotspots.to_crs("EPSG:4326")

    # Save final hotspots
    hotspots_path = output_path / "final_hotspots.geojson"
    gdf_hotspots_wgs84.to_file(hotspots_path, driver="GeoJSON")
    logger.info(f"Saved final hotspots: {hotspots_path}")

    # Calculate summary statistics
    analysis = {
        'input_data': {
            'n_dining_zones': int(len(gdf_dining)),
            'n_taxi_hotspots': int(len(gdf_taxi)),
            'dining_total_area_sqkm': float(gdf_dining.to_crs("EPSG:2263").area.sum() / 1_000_000),
            'taxi_total_area_sqkm': float(gdf_taxi.to_crs("EPSG:2263").area.sum() / 1_000_000)
        },
        'final_hotspots': {
            'n_hotspots': int(len(gdf_hotspots)),
            'total_area_sqkm': float(gdf_hotspots['intersection_area_sqm'].sum() / 1_000_000),
            'avg_area_sqm': float(gdf_hotspots['intersection_area_sqm'].mean()) if len(gdf_hotspots) > 0 else 0,
            'total_restaurants': int(gdf_hotspots['n_restaurants'].sum()) if len(gdf_hotspots) > 0 else 0,
            'total_taxi_dropoffs': int(gdf_hotspots['n_taxi_dropoffs'].sum()) if len(gdf_hotspots) > 0 else 0
        },
        'top_hotspots': []
    }

    # Top 10 hotspots
    if len(gdf_hotspots) > 0:
        top_10 = gdf_hotspots.nlargest(10, 'popularity_score')
        for idx, row in top_10.iterrows():
            centroid = row.geometry.centroid
            centroid_wgs84 = gpd.GeoSeries([centroid], crs="EPSG:2263").to_crs("EPSG:4326").iloc[0]

            analysis['top_hotspots'].append({
                'rank': int(row['rank']),
                'popularity_score': float(row['popularity_score']),
                'n_restaurants': int(row['n_restaurants']),
                'n_taxi_dropoffs': int(row['n_taxi_dropoffs']),
                'area_sqkm': float(row['intersection_area_sqm'] / 1_000_000),
                'avg_rating': float(row['avg_rating']) if pd.notna(row.get('avg_rating')) else None,
                'centroid_lat': float(centroid_wgs84.y),
                'centroid_lon': float(centroid_wgs84.x)
            })

    # Save analysis
    analysis_path = output_path / "intersection_analysis.json"
    with open(analysis_path, 'w') as f:
        json.dump(analysis, f, indent=2)
    logger.info(f"Saved analysis: {analysis_path}")

    # Print summary
    print("\n" + "="*60)
    print("SPATIAL INTERSECTION - FINAL HOTSPOTS")
    print("="*60)
    print(f"Input Data:")
    print(f"  Dining zones: {analysis['input_data']['n_dining_zones']}")
    print(f"  Taxi hotspots: {analysis['input_data']['n_taxi_hotspots']}")
    print(f"\nFinal Hotspots:")
    print(f"  Total hotspots: {analysis['final_hotspots']['n_hotspots']}")
    print(f"  Total area: {analysis['final_hotspots']['total_area_sqkm']:.2f} km^2")
    print(f"  Average hotspot size: {analysis['final_hotspots']['avg_area_sqm']:,.0f} m^2")
    print(f"  Total restaurants: {analysis['final_hotspots']['total_restaurants']}")
    print(f"  Total taxi dropoffs: {analysis['final_hotspots']['total_taxi_dropoffs']}")

    if len(analysis['top_hotspots']) > 0:
        print(f"\nTop 5 Hotspots:")
        for i, hotspot in enumerate(analysis['top_hotspots'][:5]):
            print(f"  #{i+1}: Score {hotspot['popularity_score']:.1f} | "
                  f"{hotspot['n_restaurants']} restaurants | "
                  f"{hotspot['n_taxi_dropoffs']:,} taxi dropoffs | "
                  f"{hotspot['area_sqkm']:.3f} km^2")

    print("="*60 + "\n")


def save_v2_outputs(
    gdf_hotspots: gpd.GeoDataFrame,
    gdf_dining: gpd.GeoDataFrame,
    gdf_taxi: gpd.GeoDataFrame,
    output_dir: str
):
    """
    Save v2 (robust scoring) hotspots as a separate file for comparison.
    
    Also saves a JSON with v2-specific analysis metrics.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Save v2 final hotspots
    gdf_hotspots_wgs84 = gdf_hotspots.to_crs("EPSG:4326")
    hotspots_v2_path = output_path / "final_hotspots_v2.geojson"
    gdf_hotspots_wgs84.to_file(hotspots_v2_path, driver="GeoJSON")
    logger.info(f"Saved v2 final hotspots: {hotspots_v2_path}")

    # V2 analysis JSON
    analysis_v2 = {
        'scoring_version': 'v2',
        'method': 'z-score + winsorization (1%, 99%) + min-max rescale',
        'final_hotspots': {
            'n_hotspots': int(len(gdf_hotspots)),
            'total_area_sqkm': float(gdf_hotspots['intersection_area_sqm'].sum() / 1_000_000) if len(gdf_hotspots) > 0 else 0,
            'total_restaurants': int(gdf_hotspots['n_restaurants'].sum()) if len(gdf_hotspots) > 0 else 0,
            'total_taxi_dropoffs': int(gdf_hotspots['n_taxi_dropoffs'].sum()) if len(gdf_hotspots) > 0 else 0,
        },
        'top_hotspots_v2': []
    }

    if len(gdf_hotspots) > 0 and 'popularity_score_v2' in gdf_hotspots.columns:
        top_10_v2 = gdf_hotspots.nsmallest(10, 'rank_v2')
        for idx, row in top_10_v2.iterrows():
            centroid = row.geometry.centroid
            centroid_wgs84 = gpd.GeoSeries([centroid], crs="EPSG:2263").to_crs("EPSG:4326").iloc[0]

            analysis_v2['top_hotspots_v2'].append({
                'rank_v2': int(row['rank_v2']),
                'popularity_score_v2': float(row['popularity_score_v2']),
                'restaurant_score_v2': float(row['restaurant_score_v2']),
                'taxi_score_v2': float(row['taxi_score_v2']),
                'n_restaurants': int(row['n_restaurants']),
                'n_taxi_dropoffs': int(row['n_taxi_dropoffs']),
                'area_sqkm': float(row['intersection_area_sqm'] / 1_000_000),
                'avg_rating': float(row['avg_rating']) if pd.notna(row.get('avg_rating')) else None,
                'centroid_lat': float(centroid_wgs84.y),
                'centroid_lon': float(centroid_wgs84.x)
            })

    analysis_v2_path = output_path / "intersection_analysis_v2.json"
    with open(analysis_v2_path, 'w') as f:
        json.dump(analysis_v2, f, indent=2)
    logger.info(f"Saved v2 analysis: {analysis_v2_path}")


def main():
    """
    Main execution function.
    """
    logger.info("="*60)
    logger.info("SPATIAL INTERSECTION PIPELINE")
    logger.info("="*60)

    # Load configuration
    config = load_config()

    # Define paths
    dining_zones_path = "data/processed/dining_zones.geojson"
    # Use 2014 coordinate-level taxi hotspots (better spatial resolution)
    taxi_hotspots_path = "data/processed/taxi_hotspots_2014.geojson"
    output_dir = "data/processed"

    # Get filtering parameters
    min_area_sqm = get_config_value('intersection.min_area_sqm', config) or 10000.0
    min_overlap_ratio = get_config_value('intersection.min_overlap_ratio', config) or 0.15

    logger.info(f"Configuration:")
    logger.info(f"  min_area_sqm: {min_area_sqm:,.0f}")
    logger.info(f"  min_overlap_ratio: {min_overlap_ratio:.0%}")

    # Step 1: Load spatial data
    logger.info("\n[Step 1/5] Loading spatial data...")
    gdf_dining, gdf_taxi = load_spatial_data(dining_zones_path, taxi_hotspots_path)

    # Step 2: Compute intersections
    logger.info("\n[Step 2/5] Computing spatial intersections...")
    gdf_intersections = compute_spatial_intersections(gdf_dining, gdf_taxi)

    # Step 3: Apply filtering criteria
    logger.info("\n[Step 3/5] Applying filtering criteria...")
    gdf_hotspots = apply_filtering_criteria(
        gdf_intersections,
        min_area_sqm=min_area_sqm,
        min_overlap_ratio=min_overlap_ratio
    )

    # Step 4: Calculate composite scores (v1 + v2)
    logger.info("\n[Step 4/5] Calculating composite scores (v1 legacy)...")
    gdf_hotspots = calculate_composite_scores(gdf_hotspots)

    logger.info("\n[Step 4b/5] Calculating composite scores (v2 robust)...")
    gdf_hotspots = calculate_composite_scores_v2(gdf_hotspots)

    # Step 5: Save outputs (v1 as default, v2 as comparison)
    logger.info("\n[Step 5/5] Saving outputs...")
    save_outputs(gdf_hotspots, gdf_dining, gdf_taxi, output_dir)

    # Step 5b: Save v2 analysis separately for comparison
    logger.info("\n[Step 5b/5] Saving v2 comparison outputs...")
    save_v2_outputs(gdf_hotspots, gdf_dining, gdf_taxi, output_dir)

    logger.info("\n✅ Spatial intersection completed successfully!")


if __name__ == "__main__":
    main()
