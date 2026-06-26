"""
Compare 2014 Coordinate-Level vs 2024 Zone-Centroid Hotspots
===============================================================

Reproducible comparison script for the core experiment:
Pipeline A (2024 zone-centroid) vs Pipeline B (2014 coordinate-level).

Metrics:
- Hotspot count, area, density, compactness
- Spatial overlap: Jaccard, IoU, Hausdorff distance
- Distribution comparison: area, dropoff count, weight
- Ranking stability (if comparable scores available)

Input:
    - data/processed/taxi_hotspots.geojson (2024, zone-centroid)
    - data/processed/taxi_hotspots_2014.geojson (2014, coordinate-level)

Output:
    - data/processed/comparison_2014_vs_2024.json
    - outputs/figures/comparison_*.png (if matplotlib available)

Author: Where to DINE Project
Date: 2026-06-25
"""

import geopandas as gpd
import pandas as pd
import numpy as np
from pathlib import Path
import json
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_hotspots(path_2024: str, path_2014: str) -> tuple:
    """Load both hotspot GeoDataFrames."""
    gdf_2024 = gpd.read_file(path_2024)
    gdf_2014 = gpd.read_file(path_2014)
    logger.info(f"2024 hotspots: {len(gdf_2024)}")
    logger.info(f"2014 hotspots: {len(gdf_2014)}")
    return gdf_2024, gdf_2014


def compare_hotspot_counts(gdf_2024, gdf_2014) -> dict:
    """Compare hotspot counts and sizes."""
    return {
        'n_hotspots_2024': int(len(gdf_2024)),
        'n_hotspots_2014': int(len(gdf_2014)),
        'difference': int(len(gdf_2014) - len(gdf_2024)),
        'pct_change': float((len(gdf_2014) - len(gdf_2024)) / max(len(gdf_2024), 1) * 100)
    }


def compare_area_stats(gdf_2024, gdf_2014) -> dict:
    """Compare hotspot area statistics (in projected CRS)."""
    gdf_2024 = gdf_2024.to_crs("EPSG:2263")
    gdf_2014 = gdf_2014.to_crs("EPSG:2263")

    areas_2024 = gdf_2024.area / 1e6  # km²
    areas_2014 = gdf_2014.area / 1e6

    return {
        'total_area_km2_2024': float(areas_2024.sum()),
        'total_area_km2_2014': float(areas_2014.sum()),
        'avg_area_km2_2024': float(areas_2024.mean()),
        'avg_area_km2_2014': float(areas_2014.mean()),
        'median_area_km2_2024': float(areas_2024.median()),
        'median_area_km2_2014': float(areas_2014.median()),
        'std_area_km2_2024': float(areas_2024.std()),
        'std_area_km2_2014': float(areas_2014.std()),
        'min_area_km2_2024': float(areas_2024.min()),
        'min_area_km2_2014': float(areas_2014.min()),
        'max_area_km2_2024': float(areas_2024.max()),
        'max_area_km2_2014': float(areas_2014.max()),
    }


def compare_dropoff_stats(gdf_2024, gdf_2014) -> dict:
    """Compare dropoff count and weight statistics."""
    stats = {}

    for col, label in [('n_dropoffs', 'dropoffs'), ('total_weight', 'weight')]:
        if col in gdf_2024.columns and col in gdf_2014.columns:
            stats[f'{label}_total_2024'] = int(gdf_2024[col].sum())
            stats[f'{label}_total_2014'] = int(gdf_2014[col].sum())
            stats[f'{label}_mean_2024'] = float(gdf_2024[col].mean())
            stats[f'{label}_mean_2014'] = float(gdf_2014[col].mean())
            stats[f'{label}_median_2024'] = float(gdf_2024[col].median())
            stats[f'{label}_median_2014'] = float(gdf_2014[col].median())

    return stats


def compare_spatial_overlap(gdf_2024, gdf_2014) -> dict:
    """Calculate spatial overlap between hotspot sets."""
    gdf_2024 = gdf_2024.to_crs("EPSG:2263")
    gdf_2014 = gdf_2014.to_crs("EPSG:2263")

    # Union of all hotspots per pipeline
    union_2024 = gdf_2024.unary_union
    union_2014 = gdf_2014.unary_union

    intersection = union_2024.intersection(union_2014)
    union_total = union_2024.union(union_2014)

    area_2024 = union_2024.area
    area_2014 = union_2014.area
    area_intersection = intersection.area
    area_union = union_total.area

    iou = area_intersection / area_union if area_union > 0 else 0
    jaccard = area_intersection / (area_2024 + area_2014 - area_intersection) if (area_2024 + area_2014 - area_intersection) > 0 else 0

    # Pairwise overlap: for each 2014 hotspot, find overlapping 2024 hotspots
    pairwise_overlaps = []
    for idx_2014, hotspot_2014 in gdf_2014.iterrows():
        overlaps = gdf_2024[gdf_2024.intersects(hotspot_2014.geometry)]
        for idx_2024, hotspot_2024 in overlaps.iterrows():
            inter = hotspot_2014.geometry.intersection(hotspot_2024.geometry)
            union = hotspot_2014.geometry.union(hotspot_2024.geometry)
            if union.area > 0:
                pairwise_overlaps.append({
                    'hotspot_2014': idx_2014,
                    'hotspot_2024': idx_2024,
                    'iou': inter.area / union.area,
                    'intersection_area_km2': inter.area / 1e6,
                    'union_area_km2': union.area / 1e6
                })

    n_overlapping_pairs = len(pairwise_overlaps)
    avg_pairwise_iou = np.mean([p['iou'] for p in pairwise_overlaps]) if pairwise_overlaps else 0

    return {
        'iou': float(iou),
        'jaccard': float(jaccard),
        'intersection_area_km2': float(area_intersection / 1e6),
        'union_area_km2': float(area_union / 1e6),
        'area_2024_km2': float(area_2024 / 1e6),
        'area_2014_km2': float(area_2014 / 1e6),
        'n_overlapping_pairs': int(n_overlapping_pairs),
        'avg_pairwise_iou': float(avg_pairwise_iou),
        'pairwise_overlaps': pairwise_overlaps[:50]  # Save top 50 for inspection
    }


def compare_density_and_compactness(gdf_2024, gdf_2014) -> dict:
    """Compare density (dropoffs per km²) and compactness (area/perimeter)."""
    gdf_2024 = gdf_2024.to_crs("EPSG:2263")
    gdf_2014 = gdf_2014.to_crs("EPSG:2263")

    def _compute(gdf, dropoff_col='n_dropoffs'):
        areas = gdf.area / 1e6  # km²
        perimeters = gdf.length / 1000  # km

        # Density = dropoffs / area
        density = gdf[dropoff_col] / areas if dropoff_col in gdf.columns else pd.Series([np.nan] * len(gdf))

        # Compactness = 4π * area / perimeter² (circle = 1)
        compactness = 4 * np.pi * gdf.area / (gdf.length ** 2)
        compactness = compactness.replace([np.inf, -np.inf], np.nan)

        return {
            'density_mean': float(density.mean()),
            'density_median': float(density.median()),
            'compactness_mean': float(compactness.mean()),
            'compactness_median': float(compactness.median()),
        }

    return {
        '2024': _compute(gdf_2024),
        '2014': _compute(gdf_2014)
    }


def generate_figures(gdf_2024, gdf_2014, output_dir: str):
    """Generate comparison figures (if matplotlib is available)."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        logger.warning("matplotlib not available, skipping figure generation")
        return

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    gdf_2024 = gdf_2024.to_crs("EPSG:2263")
    gdf_2014 = gdf_2014.to_crs("EPSG:2263")

    # Figure 1: Area distribution comparison
    fig, ax = plt.subplots(figsize=(10, 6))
    areas_2024 = gdf_2024.area / 1e6
    areas_2014 = gdf_2014.area / 1e6
    ax.hist(areas_2024, bins=30, alpha=0.5, label='2024 (zone-centroid)', color='steelblue')
    ax.hist(areas_2014, bins=30, alpha=0.5, label='2014 (coordinate)', color='coral')
    ax.set_xlabel('Hotspot Area (km²)')
    ax.set_ylabel('Count')
    ax.set_title('Hotspot Area Distribution: 2024 vs 2014')
    ax.legend()
    fig.savefig(output_path / 'comparison_area_distribution.png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    logger.info(f"Saved: {output_path / 'comparison_area_distribution.png'}")

    # Figure 2: Spatial overlap map
    fig, ax = plt.subplots(figsize=(12, 10))
    gdf_2024.to_crs("EPSG:4326").plot(ax=ax, color='steelblue', alpha=0.3, edgecolor='steelblue', label='2024')
    gdf_2014.to_crs("EPSG:4326").plot(ax=ax, color='coral', alpha=0.3, edgecolor='coral', label='2014')
    ax.set_title('Spatial Overlap: 2024 (zone-centroid) vs 2014 (coordinate)')
    ax.legend()
    fig.savefig(output_path / 'comparison_spatial_overlap.png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    logger.info(f"Saved: {output_path / 'comparison_spatial_overlap.png'}")


def main():
    """Main execution function."""
    logger.info("=" * 60)
    logger.info("2014 vs 2024 HOTSPOT COMPARISON")
    logger.info("=" * 60)

    # Paths
    path_2024 = "data/processed/taxi_hotspots.geojson"
    path_2014 = "data/processed/taxi_hotspots_2014.geojson"
    output_dir = "data/processed"
    figure_dir = "outputs/figures"

    # Check prerequisites
    if not Path(path_2024).exists():
        logger.error(f"2024 hotspots not found: {path_2024}")
        logger.error("Run: python run_pipeline.py")
        return 1

    if not Path(path_2014).exists():
        logger.error(f"2014 hotspots not found: {path_2014}")
        logger.error("Run: python src/data_processing/10_process_2014_taxi_data.py")
        logger.error("Then: python src/data_processing/11_cluster_2014_taxi_dropoffs.py")
        return 1

    # Load data
    logger.info("\n[Step 1/5] Loading hotspot data...")
    gdf_2024, gdf_2014 = load_hotspots(path_2024, path_2014)

    # Compare counts
    logger.info("\n[Step 2/5] Comparing hotspot counts...")
    count_metrics = compare_hotspot_counts(gdf_2024, gdf_2014)

    # Compare areas
    logger.info("\n[Step 3/5] Comparing area statistics...")
    area_metrics = compare_area_stats(gdf_2024, gdf_2014)

    # Compare dropoff stats
    logger.info("\n[Step 4/5] Comparing dropoff statistics...")
    dropoff_metrics = compare_dropoff_stats(gdf_2024, gdf_2014)

    # Compare spatial overlap
    logger.info("\n[Step 5/5] Comparing spatial overlap...")
    overlap_metrics = compare_spatial_overlap(gdf_2024, gdf_2014)

    # Density and compactness
    logger.info("\n[Step 5b/5] Comparing density and compactness...")
    density_metrics = compare_density_and_compactness(gdf_2024, gdf_2014)

    # Combine results
    results = {
        'experiment': '2014 coordinate-level vs 2024 zone-centroid',
        'timestamp': str(pd.Timestamp.now()),
        'count_metrics': count_metrics,
        'area_metrics': area_metrics,
        'dropoff_metrics': dropoff_metrics,
        'overlap_metrics': overlap_metrics,
        'density_compactness': density_metrics
    }

    # Save JSON
    output_path = Path(output_dir) / "comparison_2014_vs_2024.json"
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    logger.info(f"\nComparison results saved to {output_path}")

    # Generate figures
    logger.info("\nGenerating figures...")
    generate_figures(gdf_2024, gdf_2014, figure_dir)

    # Print summary
    print("\n" + "=" * 60)
    print("COMPARISON SUMMARY")
    print("=" * 60)
    print(f"2024 hotspots (zone-centroid): {count_metrics['n_hotspots_2024']}")
    print(f"2014 hotspots (coordinate):    {count_metrics['n_hotspots_2014']}")
    print(f"Difference: {count_metrics['difference']:+,} ({count_metrics['pct_change']:+.1f}%)")
    print(f"\nArea comparison:")
    print(f"  2024 total: {area_metrics['total_area_km2_2024']:.2f} km^2")
    print(f"  2014 total: {area_metrics['total_area_km2_2014']:.2f} km^2")
    print(f"  2024 avg:   {area_metrics['avg_area_km2_2024']:.3f} km^2")
    print(f"  2014 avg:   {area_metrics['avg_area_km2_2014']:.3f} km^2")
    print(f"\nSpatial overlap:")
    print(f"  IoU:       {overlap_metrics['iou']:.3f}")
    print(f"  Jaccard:   {overlap_metrics['jaccard']:.3f}")
    print(f"  Intersection: {overlap_metrics['intersection_area_km2']:.2f} km^2")
    print(f"  Union:        {overlap_metrics['union_area_km2']:.2f} km^2")
    print(f"  Overlapping pairs: {overlap_metrics['n_overlapping_pairs']}")
    print(f"  Avg pairwise IoU: {overlap_metrics['avg_pairwise_iou']:.3f}")
    print(f"\nDensity:")
    print(f"  2024 avg density: {density_metrics['2024']['density_mean']:.1f} dropoffs/km^2")
    print(f"  2014 avg density: {density_metrics['2014']['density_mean']:.1f} dropoffs/km^2")
    print(f"\nCompactness (circle = 1):")
    print(f"  2024 avg: {density_metrics['2024']['compactness_mean']:.3f}")
    print(f"  2014 avg: {density_metrics['2014']['compactness_mean']:.3f}")
    print("=" * 60 + "\n")

    logger.info("✅ Comparison completed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
