"""
Restaurant Clustering with HDBSCAN
====================================

Purpose: Identify dining zones through density-based clustering of restaurants

Input:
    - data/interim/restaurants_merged.geojson

Output:
    - data/processed/dining_zones.geojson
    - data/processed/restaurants_clustered.geojson
    - data/processed/clustering_metrics.json

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
from shapely.ops import unary_union
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


def load_restaurant_data(filepath: str) -> gpd.GeoDataFrame:
    """
    Load merged restaurant GeoJSON data.

    Parameters:
    -----------
    filepath : str
        Path to restaurants_merged.geojson

    Returns:
    --------
    gpd.GeoDataFrame
        Restaurant data with geometries
    """
    logger.info(f"Loading restaurant data from {filepath}")

    gdf = gpd.read_file(filepath)

    logger.info(f"Loaded {len(gdf)} restaurants")
    logger.info(f"CRS: {gdf.crs}")

    return gdf


def prepare_clustering_data(gdf: gpd.GeoDataFrame) -> Tuple[np.ndarray, gpd.GeoDataFrame]:
    """
    Prepare coordinate array for HDBSCAN clustering.

    HDBSCAN requires projected coordinates in meters for accurate
    distance-based clustering.

    Parameters:
    -----------
    gdf : gpd.GeoDataFrame
        Restaurant data in WGS84

    Returns:
    --------
    coords : np.ndarray
        Nx2 array of (x, y) coordinates in meters
    gdf_proj : gpd.GeoDataFrame
        GeoDataFrame projected to EPSG:2263
    """
    logger.info("Preparing data for clustering...")

    # Project to NAD83 / NY Long Island (meters)
    crs_projected = "EPSG:2263"
    gdf_proj = gdf.to_crs(crs_projected)

    # Extract coordinates
    coords = np.array([[point.x, point.y] for point in gdf_proj.geometry])

    logger.info(f"Prepared {len(coords)} coordinate pairs")
    logger.info(f"Projected to {crs_projected}")

    return coords, gdf_proj


def perform_clustering(
    coords: np.ndarray,
    min_cluster_size: int = 30,
    min_samples: int = 10,
    cluster_selection_epsilon: float = 200.0
) -> Tuple[np.ndarray, HDBSCAN]:
    """
    Apply HDBSCAN clustering to restaurant coordinates.

    Parameters:
    -----------
    coords : np.ndarray
        Nx2 array of coordinates in meters
    min_cluster_size : int
        Minimum cluster size (default: 30 restaurants)
    min_samples : int
        Conservative parameter for noise reduction (default: 10)
    cluster_selection_epsilon : float
        Maximum distance in meters for cluster merging (default: 200m)

    Returns:
    --------
    labels : np.ndarray
        Cluster labels (-1 = noise, 0+ = cluster ID)
    clusterer : HDBSCAN
        Fitted HDBSCAN object
    """
    logger.info("Running HDBSCAN clustering...")
    logger.info(f"Parameters: min_cluster_size={min_cluster_size}, "
                f"min_samples={min_samples}, epsilon={cluster_selection_epsilon}m")

    clusterer = HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        cluster_selection_epsilon=cluster_selection_epsilon,
        metric='euclidean',
        cluster_selection_method='eom',  # Excess of Mass
        algorithm='best'
    )

    labels = clusterer.fit_predict(coords)

    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = list(labels).count(-1)

    logger.info(f"Clustering complete:")
    logger.info(f"  - Clusters found: {n_clusters}")
    logger.info(f"  - Noise points: {n_noise} ({n_noise/len(labels)*100:.1f}%)")
    logger.info(f"  - Clustered points: {len(labels) - n_noise} ({(len(labels)-n_noise)/len(labels)*100:.1f}%)")

    return labels, clusterer


def calculate_validation_metrics(coords: np.ndarray, labels: np.ndarray) -> Dict[str, float]:
    """
    Calculate clustering validation metrics.

    Metrics:
    - Silhouette Score: Measures cluster cohesion/separation [-1, 1]
      > 0.5 = good, > 0.7 = excellent
    - Davies-Bouldin Index: Average similarity ratio (lower is better)
      < 1.0 = good separation

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

    # Filter out noise points for validation
    mask = labels != -1
    coords_clustered = coords[mask]
    labels_clustered = labels[mask]

    metrics = {}

    if len(set(labels_clustered)) > 1:
        # Silhouette score
        silhouette = silhouette_score(coords_clustered, labels_clustered, metric='euclidean')
        metrics['silhouette_score'] = float(silhouette)

        # Davies-Bouldin index
        db_index = davies_bouldin_score(coords_clustered, labels_clustered)
        metrics['davies_bouldin_index'] = float(db_index)

        logger.info(f"Silhouette Score: {silhouette:.3f}")
        logger.info(f"Davies-Bouldin Index: {db_index:.3f}")
    else:
        logger.warning("Not enough clusters for validation metrics")
        metrics['silhouette_score'] = None
        metrics['davies_bouldin_index'] = None

    # Add cluster statistics
    metrics['n_clusters'] = int(len(set(labels)) - (1 if -1 in labels else 0))
    metrics['n_noise'] = int(list(labels).count(-1))
    metrics['n_total'] = int(len(labels))
    metrics['pct_clustered'] = float((len(labels) - list(labels).count(-1)) / len(labels) * 100)

    return metrics


def create_dining_zones(
    gdf_proj: gpd.GeoDataFrame,
    labels: np.ndarray,
    buffer_distance: float = 100.0
) -> gpd.GeoDataFrame:
    """
    Generate dining zone polygons from clustered restaurants.

    Process:
    1. Group restaurants by cluster
    2. Create convex hull for each cluster
    3. Apply buffer to create continuous zone
    4. Calculate zone statistics

    Parameters:
    -----------
    gdf_proj : gpd.GeoDataFrame
        Restaurant data (projected to meters)
    labels : np.ndarray
        Cluster labels
    buffer_distance : float
        Buffer distance in meters (default: 100m)

    Returns:
    --------
    gpd.GeoDataFrame
        Dining zone polygons with statistics
    """
    logger.info("Creating dining zone polygons...")
    logger.info(f"Buffer distance: {buffer_distance}m")

    # Add cluster labels to GeoDataFrame
    gdf_proj['cluster'] = labels

    zones = []

    # Process each cluster (skip noise = -1)
    for cluster_id in sorted(set(labels)):
        if cluster_id == -1:
            continue

        # Get restaurants in this cluster
        cluster_restaurants = gdf_proj[gdf_proj['cluster'] == cluster_id]
        n_restaurants = len(cluster_restaurants)

        # Create convex hull
        points = MultiPoint(list(cluster_restaurants.geometry))
        hull = points.convex_hull

        # Apply buffer
        zone_polygon = hull.buffer(buffer_distance)

        # Calculate statistics
        zone_area_sqm = zone_polygon.area
        zone_area_sqkm = zone_area_sqm / 1_000_000

        # Average rating (if available)
        avg_rating = cluster_restaurants['rating'].mean() if 'rating' in cluster_restaurants.columns else None

        zones.append({
            'cluster_id': cluster_id,
            'n_restaurants': n_restaurants,
            'area_sqm': zone_area_sqm,
            'area_sqkm': zone_area_sqkm,
            'avg_rating': avg_rating,
            'geometry': zone_polygon
        })

    # Create GeoDataFrame
    gdf_zones = gpd.GeoDataFrame(zones, crs=gdf_proj.crs)

    logger.info(f"Created {len(gdf_zones)} dining zones")
    logger.info(f"Total area: {gdf_zones['area_sqkm'].sum():.2f} km²")
    logger.info(f"Average zone size: {gdf_zones['area_sqkm'].mean():.3f} km²")

    return gdf_zones


def save_outputs(
    gdf_restaurants: gpd.GeoDataFrame,
    gdf_zones: gpd.GeoDataFrame,
    metrics: Dict,
    output_dir: str
):
    """
    Save clustering results in multiple formats.

    Parameters:
    -----------
    gdf_restaurants : gpd.GeoDataFrame
        Restaurant data with cluster labels
    gdf_zones : gpd.GeoDataFrame
        Dining zone polygons
    metrics : dict
        Validation metrics
    output_dir : str
        Output directory path
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Convert back to WGS84 for output
    gdf_restaurants_wgs84 = gdf_restaurants.to_crs("EPSG:4326")
    gdf_zones_wgs84 = gdf_zones.to_crs("EPSG:4326")

    # Save clustered restaurants
    restaurants_path = output_path / "restaurants_clustered.geojson"
    gdf_restaurants_wgs84.to_file(restaurants_path, driver="GeoJSON")
    logger.info(f"Saved clustered restaurants: {restaurants_path}")

    # Save dining zones
    zones_path = output_path / "dining_zones.geojson"
    gdf_zones_wgs84.to_file(zones_path, driver="GeoJSON")
    logger.info(f"Saved dining zones: {zones_path}")

    # Save metrics
    metrics_path = output_path / "clustering_metrics.json"
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    logger.info(f"Saved metrics: {metrics_path}")

    # Print summary
    print("\n" + "="*60)
    print("RESTAURANT CLUSTERING - SUMMARY")
    print("="*60)
    print(f"Total restaurants: {len(gdf_restaurants)}")
    print(f"Clusters found: {metrics['n_clusters']}")
    print(f"Clustered restaurants: {len(gdf_restaurants) - metrics['n_noise']} ({metrics['pct_clustered']:.1f}%)")
    print(f"Noise points: {metrics['n_noise']} ({(metrics['n_noise']/len(gdf_restaurants)*100):.1f}%)")
    print(f"\nValidation Metrics:")
    if metrics['silhouette_score'] is not None:
        print(f"  Silhouette Score: {metrics['silhouette_score']:.3f}")
        print(f"  Davies-Bouldin Index: {metrics['davies_bouldin_index']:.3f}")
    print(f"\nDining Zones:")
    print(f"  Total zones: {len(gdf_zones)}")
    print(f"  Total area: {gdf_zones['area_sqkm'].sum():.2f} km²")
    print(f"  Average zone size: {gdf_zones['area_sqkm'].mean():.3f} km²")
    print(f"  Largest zone: {gdf_zones['area_sqkm'].max():.3f} km² ({gdf_zones.loc[gdf_zones['area_sqkm'].idxmax(), 'n_restaurants']} restaurants)")
    print("="*60 + "\n")


def main():
    """
    Main execution function.
    """
    logger.info("="*60)
    logger.info("RESTAURANT CLUSTERING PIPELINE")
    logger.info("="*60)

    # Load configuration
    config = load_config()

    # Define paths
    input_path = "data/interim/restaurants_merged.geojson"
    output_dir = "data/processed"

    # Get clustering parameters from config
    min_cluster_size = get_config_value('clustering.restaurants.min_cluster_size', config)
    min_samples = get_config_value('clustering.restaurants.min_samples', config)
    cluster_selection_epsilon = get_config_value('clustering.restaurants.cluster_selection_epsilon', config)
    buffer_distance = get_config_value('clustering.dining_zone_buffer', config) or 100.0

    logger.info(f"Configuration loaded:")
    logger.info(f"  min_cluster_size: {min_cluster_size}")
    logger.info(f"  min_samples: {min_samples}")
    logger.info(f"  cluster_selection_epsilon: {cluster_selection_epsilon}m")
    logger.info(f"  buffer_distance: {buffer_distance}m")

    # Step 1: Load data
    logger.info("\n[Step 1/5] Loading restaurant data...")
    gdf = load_restaurant_data(input_path)

    # Step 2: Prepare clustering data
    logger.info("\n[Step 2/5] Preparing clustering data...")
    coords, gdf_proj = prepare_clustering_data(gdf)

    # Step 3: Perform clustering
    logger.info("\n[Step 3/5] Performing HDBSCAN clustering...")
    labels, clusterer = perform_clustering(
        coords,
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        cluster_selection_epsilon=cluster_selection_epsilon
    )

    # Add labels to GeoDataFrame
    gdf_proj['cluster'] = labels

    # Step 4: Calculate validation metrics
    logger.info("\n[Step 4/5] Calculating validation metrics...")
    metrics = calculate_validation_metrics(coords, labels)

    # Step 5: Create dining zones
    logger.info("\n[Step 5/5] Creating dining zone polygons...")
    gdf_zones = create_dining_zones(gdf_proj, labels, buffer_distance=buffer_distance)

    # Step 6: Save outputs
    logger.info("\n[Step 6/6] Saving outputs...")
    save_outputs(gdf_proj, gdf_zones, metrics, output_dir)

    logger.info("\n✅ Restaurant clustering completed successfully!")


if __name__ == "__main__":
    main()
