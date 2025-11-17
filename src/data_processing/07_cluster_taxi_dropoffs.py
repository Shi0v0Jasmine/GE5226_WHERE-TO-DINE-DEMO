"""
Taxi Dropoff Clustering with HDBSCAN
=====================================

Purpose: Identify dining hotspots from taxi dropoff patterns

Input:
    - data/interim/taxi_dropoffs_weighted.parquet

Output:
    - data/processed/taxi_hotspots.geojson
    - data/processed/taxi_dropoffs_clustered.parquet
    - data/processed/taxi_clustering_metrics.json

Author: Where to DINE Project
Date: 2025-11-09
"""

import pandas as pd
import geopandas as gpd
import numpy as np
from pathlib import Path
import json
import logging
from typing import Tuple, Dict
from shapely.geometry import MultiPoint, Point
from hdbscan import HDBSCAN
from sklearn.metrics import silhouette_score, davies_bouldin_score
import sys
sys.path.append(str(Path(__file__).parent.parent))
from utils.config_loader import load_config, get_config_value

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_taxi_data(filepath: str) -> pd.DataFrame:
    """
    Load processed taxi dropoff data.

    Parameters:
    -----------
    filepath : str
        Path to taxi_dropoffs_weighted.parquet

    Returns:
    --------
    pd.DataFrame
        Taxi dropoff data with weights
    """
    logger.info(f"Loading taxi data from {filepath}")

    df = pd.read_parquet(filepath)

    logger.info(f"Loaded {len(df):,} taxi dropoffs")
    logger.info(f"Columns: {list(df.columns)}")

    return df


def aggregate_with_h3(
    df: pd.DataFrame,
    h3_resolution: int = 10,
    use_h3: bool = False
) -> pd.DataFrame:
    """
    Optionally aggregate taxi dropoffs using H3 hexagons.

    H3 resolution 10: ~15m hexagon edge
    This reduces 50M+ points to ~500k cells (96% reduction)

    Parameters:
    -----------
    df : pd.DataFrame
        Taxi data with dropoff_lon, dropoff_lat, weight
    h3_resolution : int
        H3 resolution level (default: 10)
    use_h3 : bool
        Whether to use H3 aggregation (default: False)

    Returns:
    --------
    pd.DataFrame
        Original or aggregated data
    """
    if not use_h3:
        logger.info("Skipping H3 aggregation (use_h3=False)")
        return df

    logger.info(f"Aggregating with H3 resolution {h3_resolution}...")

    try:
        import h3
    except ImportError:
        logger.warning("h3 library not installed. Install with: pip install h3")
        logger.warning("Proceeding without H3 aggregation...")
        return df

    # Convert coordinates to H3 hexagons
    df['h3_cell'] = df.apply(
        lambda row: h3.geo_to_h3(row['dropoff_lat'], row['dropoff_lon'], h3_resolution),
        axis=1
    )

    # Aggregate by hexagon
    df_agg = df.groupby('h3_cell').agg({
        'weight': 'sum',  # Sum weights in each hexagon
        'dropoff_lat': 'mean',  # Mean coordinates (approximate)
        'dropoff_lon': 'mean'
    }).reset_index()

    logger.info(f"Aggregated {len(df):,} points to {len(df_agg):,} hexagons")
    logger.info(f"Reduction: {(1 - len(df_agg)/len(df))*100:.1f}%")

    return df_agg


def prepare_weighted_coordinates(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
    """
    Prepare weighted coordinates for clustering.

    For weighted clustering, we duplicate points based on weights.
    Weight 1.5 → point appears ~2 times
    Weight 0.5 → point appears ~1 time with 50% probability

    Parameters:
    -----------
    df : pd.DataFrame
        Taxi data with dropoff_lon, dropoff_lat, weight

    Returns:
    --------
    coords : np.ndarray
        Coordinate array (duplicated based on weights)
    weights : np.ndarray
        Original weights for each point
    """
    logger.info("Preparing weighted coordinates...")

    # Convert to projected CRS for accurate distances
    geometry = [Point(lon, lat) for lon, lat in zip(df['dropoff_lon'], df['dropoff_lat'])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")
    gdf_proj = gdf.to_crs("EPSG:2263")  # NAD83 / NY Long Island

    # Extract projected coordinates
    coords_proj = np.array([[point.x, point.y] for point in gdf_proj.geometry])
    weights = df['weight'].values

    # Weight-based sampling approach
    # Round weights and duplicate points accordingly
    weights_rounded = np.round(weights).astype(int)
    weights_rounded = np.maximum(weights_rounded, 1)  # Ensure at least 1 copy

    # Duplicate coordinates based on weights
    coords_weighted = np.repeat(coords_proj, weights_rounded, axis=0)

    logger.info(f"Original points: {len(coords_proj):,}")
    logger.info(f"Weighted points: {len(coords_weighted):,}")
    logger.info(f"Expansion factor: {len(coords_weighted)/len(coords_proj):.2f}x")

    return coords_weighted, coords_proj


def perform_clustering(
    coords: np.ndarray,
    min_cluster_size: int = 50,
    min_samples: int = 15,
    cluster_selection_epsilon: float = 250.0
) -> Tuple[np.ndarray, HDBSCAN]:
    """
    Apply HDBSCAN clustering to taxi dropoff coordinates.

    Parameters:
    -----------
    coords : np.ndarray
        Nx2 array of coordinates in meters
    min_cluster_size : int
        Minimum cluster size (default: 50 dropoffs)
    min_samples : int
        Conservative parameter (default: 15)
    cluster_selection_epsilon : float
        Maximum distance in meters (default: 250m)

    Returns:
    --------
    labels : np.ndarray
        Cluster labels
    clusterer : HDBSCAN
        Fitted HDBSCAN object
    """
    logger.info("Running HDBSCAN clustering on taxi dropoffs...")
    logger.info(f"Parameters: min_cluster_size={min_cluster_size}, "
                f"min_samples={min_samples}, epsilon={cluster_selection_epsilon}m")

    clusterer = HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        cluster_selection_epsilon=cluster_selection_epsilon,
        metric='euclidean',
        cluster_selection_method='eom',
        algorithm='best'
    )

    labels = clusterer.fit_predict(coords)

    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = list(labels).count(-1)

    logger.info(f"Clustering complete:")
    logger.info(f"  - Hotspots found: {n_clusters}")
    logger.info(f"  - Noise points: {n_noise} ({n_noise/len(labels)*100:.1f}%)")
    logger.info(f"  - Clustered points: {len(labels) - n_noise} ({(len(labels)-n_noise)/len(labels)*100:.1f}%)")

    return labels, clusterer


def calculate_validation_metrics(coords: np.ndarray, labels: np.ndarray) -> Dict[str, float]:
    """
    Calculate clustering validation metrics.

    Parameters:
    -----------
    coords : np.ndarray
        Coordinate array
    labels : np.ndarray
        Cluster labels

    Returns:
    --------
    dict
        Validation metrics
    """
    logger.info("Calculating validation metrics...")

    # Filter out noise
    mask = labels != -1
    coords_clustered = coords[mask]
    labels_clustered = labels[mask]

    metrics = {}

    if len(set(labels_clustered)) > 1:
        # Sample if too large (silhouette score is expensive)
        if len(coords_clustered) > 100000:
            logger.info("Sampling 100k points for validation metrics...")
            indices = np.random.choice(len(coords_clustered), 100000, replace=False)
            coords_sample = coords_clustered[indices]
            labels_sample = labels_clustered[indices]
        else:
            coords_sample = coords_clustered
            labels_sample = labels_clustered

        # Silhouette score
        silhouette = silhouette_score(coords_sample, labels_sample, metric='euclidean')
        metrics['silhouette_score'] = float(silhouette)

        # Davies-Bouldin index
        db_index = davies_bouldin_score(coords_sample, labels_sample)
        metrics['davies_bouldin_index'] = float(db_index)

        logger.info(f"Silhouette Score: {silhouette:.3f}")
        logger.info(f"Davies-Bouldin Index: {db_index:.3f}")
    else:
        logger.warning("Not enough clusters for validation")
        metrics['silhouette_score'] = None
        metrics['davies_bouldin_index'] = None

    # Cluster statistics
    metrics['n_clusters'] = int(len(set(labels)) - (1 if -1 in labels else 0))
    metrics['n_noise'] = int(list(labels).count(-1))
    metrics['n_total'] = int(len(labels))
    metrics['pct_clustered'] = float((len(labels) - list(labels).count(-1)) / len(labels) * 100)

    return metrics


def create_hotspot_polygons(
    df: pd.DataFrame,
    labels: np.ndarray,
    buffer_distance: float = 150.0
) -> gpd.GeoDataFrame:
    """
    Generate taxi hotspot polygons from clustered dropoffs.

    Parameters:
    -----------
    df : pd.DataFrame
        Taxi data with coordinates
    labels : np.ndarray
        Cluster labels
    buffer_distance : float
        Buffer distance in meters (default: 150m)

    Returns:
    --------
    gpd.GeoDataFrame
        Hotspot polygons
    """
    logger.info("Creating hotspot polygons...")
    logger.info(f"Buffer distance: {buffer_distance}m")

    # Create GeoDataFrame
    geometry = [Point(lon, lat) for lon, lat in zip(df['dropoff_lon'], df['dropoff_lat'])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")
    gdf['cluster'] = labels

    # Project to meters
    gdf_proj = gdf.to_crs("EPSG:2263")

    hotspots = []

    # Process each cluster
    for cluster_id in sorted(set(labels)):
        if cluster_id == -1:
            continue

        cluster_points = gdf_proj[gdf_proj['cluster'] == cluster_id]
        n_dropoffs = len(cluster_points)
        total_weight = cluster_points['weight'].sum() if 'weight' in cluster_points.columns else n_dropoffs

        # Create convex hull
        points = MultiPoint(list(cluster_points.geometry))
        hull = points.convex_hull

        # Apply buffer
        hotspot_polygon = hull.buffer(buffer_distance)

        # Calculate area
        area_sqm = hotspot_polygon.area
        area_sqkm = area_sqm / 1_000_000

        hotspots.append({
            'hotspot_id': cluster_id,
            'n_dropoffs': n_dropoffs,
            'total_weight': total_weight,
            'area_sqm': area_sqm,
            'area_sqkm': area_sqkm,
            'geometry': hotspot_polygon
        })

    # Create GeoDataFrame
    gdf_hotspots = gpd.GeoDataFrame(hotspots, crs="EPSG:2263")

    logger.info(f"Created {len(gdf_hotspots)} hotspot polygons")
    logger.info(f"Total area: {gdf_hotspots['area_sqkm'].sum():.2f} km²")
    logger.info(f"Total weighted dropoffs: {gdf_hotspots['total_weight'].sum():,.0f}")

    return gdf_hotspots


def save_outputs(
    df: pd.DataFrame,
    labels: np.ndarray,
    gdf_hotspots: gpd.GeoDataFrame,
    metrics: Dict,
    output_dir: str
):
    """
    Save taxi clustering results.

    Parameters:
    -----------
    df : pd.DataFrame
        Taxi data
    labels : np.ndarray
        Cluster labels
    gdf_hotspots : gpd.GeoDataFrame
        Hotspot polygons
    metrics : dict
        Validation metrics
    output_dir : str
        Output directory
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Add cluster labels to taxi data
    df['cluster'] = labels

    # Save clustered dropoffs (Parquet for efficiency)
    dropoffs_path = output_path / "taxi_dropoffs_clustered.parquet"
    df.to_parquet(dropoffs_path, compression='snappy', index=False)
    logger.info(f"Saved clustered dropoffs: {dropoffs_path}")

    # Save hotspot polygons (GeoJSON)
    gdf_hotspots_wgs84 = gdf_hotspots.to_crs("EPSG:4326")
    hotspots_path = output_path / "taxi_hotspots.geojson"
    gdf_hotspots_wgs84.to_file(hotspots_path, driver="GeoJSON")
    logger.info(f"Saved hotspot polygons: {hotspots_path}")

    # Save metrics
    metrics_path = output_path / "taxi_clustering_metrics.json"
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    logger.info(f"Saved metrics: {metrics_path}")

    # Print summary
    print("\n" + "="*60)
    print("TAXI CLUSTERING - SUMMARY")
    print("="*60)
    print(f"Total dropoffs: {len(df):,}")
    print(f"Hotspots identified: {metrics['n_clusters']}")
    print(f"Clustered dropoffs: {len(df) - metrics['n_noise']:,} ({metrics['pct_clustered']:.1f}%)")
    print(f"Noise points: {metrics['n_noise']:,} ({(metrics['n_noise']/len(df)*100):.1f}%)")
    print(f"\nValidation Metrics:")
    if metrics['silhouette_score'] is not None:
        print(f"  Silhouette Score: {metrics['silhouette_score']:.3f}")
        print(f"  Davies-Bouldin Index: {metrics['davies_bouldin_index']:.3f}")
    print(f"\nHotspot Statistics:")
    print(f"  Total hotspots: {len(gdf_hotspots)}")
    print(f"  Total area: {gdf_hotspots['area_sqkm'].sum():.2f} km²")
    print(f"  Average hotspot: {gdf_hotspots['area_sqkm'].mean():.3f} km²")
    print(f"  Largest hotspot: {gdf_hotspots['area_sqkm'].max():.3f} km² ({gdf_hotspots.loc[gdf_hotspots['area_sqkm'].idxmax(), 'n_dropoffs']:,} dropoffs)")
    print("="*60 + "\n")


def main():
    """
    Main execution function.
    """
    logger.info("="*60)
    logger.info("TAXI CLUSTERING PIPELINE")
    logger.info("="*60)

    # Load configuration
    config = load_config()

    # Define paths
    input_path = "data/interim/taxi_dropoffs_weighted.parquet"
    output_dir = "data/processed"

    # Get clustering parameters
    min_cluster_size = get_config_value('clustering.taxi.min_cluster_size', config)
    min_samples = get_config_value('clustering.taxi.min_samples', config)
    cluster_selection_epsilon = get_config_value('clustering.taxi.cluster_selection_epsilon', config)
    buffer_distance = get_config_value('clustering.taxi_hotspot_buffer', config) or 150.0

    # H3 aggregation (optional - disable for smaller datasets)
    use_h3 = get_config_value('clustering.taxi.use_h3_aggregation', config) or False
    h3_resolution = get_config_value('clustering.taxi.h3_resolution', config) or 10

    logger.info(f"Configuration:")
    logger.info(f"  min_cluster_size: {min_cluster_size}")
    logger.info(f"  min_samples: {min_samples}")
    logger.info(f"  cluster_selection_epsilon: {cluster_selection_epsilon}m")
    logger.info(f"  buffer_distance: {buffer_distance}m")
    logger.info(f"  use_h3_aggregation: {use_h3}")

    # Step 1: Load taxi data
    logger.info("\n[Step 1/6] Loading taxi data...")
    df = load_taxi_data(input_path)

    # Step 2: Optional H3 aggregation
    logger.info("\n[Step 2/6] H3 aggregation (optional)...")
    df = aggregate_with_h3(df, h3_resolution=h3_resolution, use_h3=use_h3)

    # Step 3: Prepare coordinates
    logger.info("\n[Step 3/6] Preparing weighted coordinates...")
    coords_weighted, coords_original = prepare_weighted_coordinates(df)

    # Step 4: Perform clustering
    logger.info("\n[Step 4/6] Performing HDBSCAN clustering...")
    labels, clusterer = perform_clustering(
        coords_weighted,
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        cluster_selection_epsilon=cluster_selection_epsilon
    )

    # Map labels back to original (unweighted) points
    # For weighted points, we need to deduplicate labels
    # Simple approach: take the cluster label for each original point
    weights_rounded = np.round(df['weight'].values).astype(int)
    weights_rounded = np.maximum(weights_rounded, 1)

    # Create mapping from weighted labels to original points
    labels_original = []
    idx = 0
    for weight in weights_rounded:
        # Take the most common label among duplicates
        label_group = labels[idx:idx+weight]
        unique, counts = np.unique(label_group, return_counts=True)
        most_common = unique[np.argmax(counts)]
        labels_original.append(most_common)
        idx += weight

    labels_original = np.array(labels_original)

    # Step 5: Calculate validation metrics (on weighted data)
    logger.info("\n[Step 5/6] Calculating validation metrics...")
    metrics = calculate_validation_metrics(coords_weighted, labels)

    # Step 6: Create hotspot polygons
    logger.info("\n[Step 6/6] Creating hotspot polygons...")
    gdf_hotspots = create_hotspot_polygons(df, labels_original, buffer_distance=buffer_distance)

    # Step 7: Save outputs
    logger.info("\n[Step 7/7] Saving outputs...")
    save_outputs(df, labels_original, gdf_hotspots, metrics, output_dir)

    logger.info("\n✅ Taxi clustering completed successfully!")


if __name__ == "__main__":
    main()
