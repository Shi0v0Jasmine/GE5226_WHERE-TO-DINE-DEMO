"""
Cluster 2014 Taxi Dropoffs with HDBSCAN (Coordinate-Level)
=========================================================

Identifies dining hotspots from 2014 coordinate-level taxi dropoffs.
This is a variant of 07_cluster_taxi_dropoffs.py adapted for 2014 data:
- Input: data/interim/taxi_dropoffs_2014_weighted.parquet
- Output: data/processed/taxi_hotspots_2014.geojson

All clustering parameters are reused from config.yaml.

Author: Where to DINE Project
Date: 2026-06-25
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
import importlib.util

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load config via project util
sys.path.append(str(Path(__file__).parent.parent))
from utils.config_loader import load_config, get_config_value

# Dynamically load functions from 07_cluster_taxi_dropoffs.py
_07_PATH = Path(__file__).parent / "07_cluster_taxi_dropoffs.py"
_07_SPEC = importlib.util.spec_from_file_location("_07_cluster_taxi_dropoffs", _07_PATH)
_07_MODULE = importlib.util.module_from_spec(_07_SPEC)
_07_SPEC.loader.exec_module(_07_MODULE)

load_taxi_data = _07_MODULE.load_taxi_data
aggregate_with_h3 = _07_MODULE.aggregate_with_h3
prepare_weighted_coordinates = _07_MODULE.prepare_weighted_coordinates
perform_clustering = _07_MODULE.perform_clustering
calculate_validation_metrics = _07_MODULE.calculate_validation_metrics
create_hotspot_polygons = _07_MODULE.create_hotspot_polygons


def save_outputs_2014(
    df: pd.DataFrame,
    labels: np.ndarray,
    gdf_hotspots: gpd.GeoDataFrame,
    metrics: Dict,
    output_dir: str
):
    """Save 2014 clustering results with _2014 suffix."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Add cluster labels
    df['cluster'] = labels

    # Save clustered dropoffs
    dropoffs_path = output_path / "taxi_dropoffs_2014_clustered.parquet"
    df.to_parquet(dropoffs_path, compression='snappy', index=False)
    logger.info(f"Saved clustered dropoffs: {dropoffs_path}")

    # Save hotspot polygons (with _2014 suffix)
    gdf_hotspots_wgs84 = gdf_hotspots.to_crs("EPSG:4326")
    hotspots_path = output_path / "taxi_hotspots_2014.geojson"
    gdf_hotspots_wgs84.to_file(hotspots_path, driver="GeoJSON")
    logger.info(f"Saved hotspot polygons: {hotspots_path}")

    # Save metrics (with _2014 suffix)
    metrics_path = output_path / "taxi_2014_clustering_metrics.json"
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    logger.info(f"Saved metrics: {metrics_path}")

    # Print summary
    print("\n" + "=" * 60)
    print("2014 TAXI CLUSTERING - SUMMARY")
    print("=" * 60)
    print(f"Total dropoffs: {len(df):,}")
    print(f"Hotspots identified: {metrics['n_clusters']}")
    print(f"Clustered dropoffs: {len(df) - metrics['n_noise']:,} ({metrics['pct_clustered']:.1f}%)")
    print(f"Noise points: {metrics['n_noise']:,} ({(metrics['n_noise'] / len(df) * 100):.1f}%)")
    print(f"\nValidation Metrics:")
    if metrics['silhouette_score'] is not None:
        print(f"  Silhouette Score: {metrics['silhouette_score']:.3f}")
        print(f"  Davies-Bouldin Index: {metrics['davies_bouldin_index']:.3f}")
    print(f"\nHotspot Statistics:")
    print(f"  Total hotspots: {len(gdf_hotspots)}")
    print(f"  Total area: {gdf_hotspots['area_sqkm'].sum():.2f} km^2")
    print(f"  Average hotspot: {gdf_hotspots['area_sqkm'].mean():.3f} km^2")
    if len(gdf_hotspots) > 0:
        print(f"  Largest hotspot: {gdf_hotspots['area_sqkm'].max():.3f} km^2 "
              f"({gdf_hotspots.loc[gdf_hotspots['area_sqkm'].idxmax(), 'n_dropoffs']:,} dropoffs)")
    print("=" * 60 + "\n")


def main():
    """Main execution for 2014 coordinate-level clustering."""
    logger.info("=" * 60)
    logger.info("2014 TAXI CLUSTERING PIPELINE (Coordinate-Level)")
    logger.info("=" * 60)

    # Load configuration
    config = load_config()

    # Define paths (2014-specific)
    input_path = "data/interim/taxi_dropoffs_2014_weighted.parquet"
    output_dir = "data/processed"

    # Get clustering parameters from config
    min_cluster_size = get_config_value('clustering.taxi.min_cluster_size', config)
    min_samples = get_config_value('clustering.taxi.min_samples', config)
    cluster_selection_epsilon = get_config_value('clustering.taxi.cluster_selection_epsilon', config)
    buffer_distance = get_config_value('clustering.taxi_hotspot_buffer', config) or 150.0

    # H3 aggregation (optional)
    use_h3 = get_config_value('clustering.taxi.use_h3_aggregation', config) or False
    h3_resolution = get_config_value('clustering.taxi.h3_resolution', config) or 10

    logger.info(f"Configuration:")
    logger.info(f"  Input: {input_path}")
    logger.info(f"  min_cluster_size: {min_cluster_size}")
    logger.info(f"  min_samples: {min_samples}")
    logger.info(f"  cluster_selection_epsilon: {cluster_selection_epsilon}m")
    logger.info(f"  buffer_distance: {buffer_distance}m")
    logger.info(f"  use_h3_aggregation: {use_h3}")

    # Check input exists
    if not Path(input_path).exists():
        logger.error(f"Input not found: {input_path}")
        logger.error("Run 10_process_2014_taxi_data.py first.")
        return 1

    # Step 1: Load 2014 taxi data
    logger.info("\n[Step 1/6] Loading 2014 taxi data...")
    df = load_taxi_data(input_path)

    # Step 2: Optional H3 aggregation
    logger.info("\n[Step 2/6] H3 aggregation (optional)...")
    df = aggregate_with_h3(df, h3_resolution=h3_resolution, use_h3=use_h3)

    # Step 3: Prepare weighted coordinates
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

    # Map labels back to original points
    weights_rounded = np.round(df['weight'].values).astype(int)
    weights_rounded = np.maximum(weights_rounded, 1)

    labels_original = []
    idx = 0
    for weight in weights_rounded:
        label_group = labels[idx:idx + weight]
        unique, counts = np.unique(label_group, return_counts=True)
        most_common = unique[np.argmax(counts)]
        labels_original.append(most_common)
        idx += weight
    labels_original = np.array(labels_original)

    # Step 5: Calculate validation metrics
    logger.info("\n[Step 5/6] Calculating validation metrics...")
    metrics = calculate_validation_metrics(coords_weighted, labels)

    # Step 6: Create hotspot polygons
    logger.info("\n[Step 6/6] Creating hotspot polygons...")
    gdf_hotspots = create_hotspot_polygons(df, labels_original, buffer_distance=buffer_distance)

    # Step 7: Save outputs
    logger.info("\n[Step 7/7] Saving outputs...")
    save_outputs_2014(df, labels_original, gdf_hotspots, metrics, output_dir)

    logger.info("\n✅ 2014 taxi clustering completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
