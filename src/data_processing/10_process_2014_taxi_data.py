"""
Process 2014 NYC Yellow Taxi Data with Real Coordinates
========================================================

Processes 2014 coordinate-level taxi data through the existing pipeline,
SKIPPING the LocationID-to-centroid conversion step (2014 data already
has real dropoff_longitude / dropoff_latitude).

Pipeline:
    1. Load raw 2014 parquet
    2. Standardize column names (reuse 02 logic)
    3. Filter invalid coordinates (0 or NaN)
    4. Filter to NYC boundaries
    5. Filter to dining hours
    6. Apply temporal weights
    7. Save as taxi_dropoffs_2014_weighted.parquet

Input:
    - data/raw/taxi_2014/*.parquet

Output:
    - data/interim/taxi_dropoffs_2014_weighted.parquet
    - data/interim/taxi_dropoffs_2014_weighted_sample.geojson

Author: Where to DINE Project
Date: 2026-06-25
"""

import pandas as pd
import geopandas as gpd
import numpy as np
from pathlib import Path
import logging
import importlib.util
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Dynamically load functions from 02_process_taxi_data.py
# (can't import directly because filename starts with a number)
# ---------------------------------------------------------------------------

_02_PATH = Path(__file__).parent / "02_process_taxi_data.py"
_02_SPEC = importlib.util.spec_from_file_location("_02_process_taxi_data", _02_PATH)
_02_MODULE = importlib.util.module_from_spec(_02_SPEC)
_02_SPEC.loader.exec_module(_02_MODULE)

# Reuse existing functions
standardize_columns = _02_MODULE.standardize_columns
filter_to_nyc_bounds = _02_MODULE.filter_to_nyc_bounds
filter_dining_hours = _02_MODULE.filter_dining_hours
apply_temporal_weights = _02_MODULE.apply_temporal_weights

# Load config via project util
sys.path.append(str(Path(__file__).parent.parent))
from utils.config_loader import load_config


def load_2014_taxi_data(data_dir: str) -> pd.DataFrame:
    """
    Load 2014 taxi parquet files from the specified directory.

    Parameters:
    -----------
    data_dir : str
        Directory containing 2014 parquet files

    Returns:
    --------
    pd.DataFrame
        Combined taxi trip records
    """
    data_path = Path(data_dir)
    parquet_files = sorted(data_path.glob("*.parquet"))

    if not parquet_files:
        raise FileNotFoundError(
            f"No Parquet files found in {data_dir}. "
            f"Run: python scripts/download_2014_taxi_data.py"
        )

    logger.info(f"Found {len(parquet_files)} Parquet file(s)")

    dfs = []
    for file in parquet_files:
        logger.info(f"Loading {file.name}...")
        df = pd.read_parquet(file)
        dfs.append(df)

    df_combined = pd.concat(dfs, ignore_index=True)
    logger.info(f"Loaded {len(df_combined):,} total 2014 taxi trips")

    return df_combined


def filter_invalid_coordinates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove records with invalid or zero coordinates.

    2014 TLC data often contains:
    - (0, 0) coordinates for missing GPS
    - NaN coordinates
    - Out-of-range coordinates

    Parameters:
    -----------
    df : pd.DataFrame
        Raw taxi data with dropoff_lon, dropoff_lat

    Returns:
    --------
    pd.DataFrame
        Filtered data with valid coordinates
    """
    initial = len(df)

    # Remove NaN
    df = df.dropna(subset=['dropoff_lon', 'dropoff_lat'])

    # Remove zeros
    df = df[(df['dropoff_lon'] != 0) & (df['dropoff_lat'] != 0)]

    # Remove pickup = dropoff (likely GPS error or very short trip)
    df = df[
        ~((df['dropoff_lon'] == df.get('pickup_lon')) &
          (df['dropoff_lat'] == df.get('pickup_lat')))
    ]

    # NYC rough bounds (generous to avoid false negatives)
    df = df[
        (df['dropoff_lat'] >= 40.4) & (df['dropoff_lat'] <= 41.0) &
        (df['dropoff_lon'] >= -74.5) & (df['dropoff_lon'] <= -73.5)
    ]

    removed = initial - len(df)
    logger.info(f"Removed {removed:,} invalid coordinates ({removed / initial * 100:.1f}%)")
    logger.info(f"Remaining: {len(df):,} trips with valid coordinates")

    return df


def save_2014_outputs(df: pd.DataFrame, output_dir: str, sample_size: int = 10000):
    """
    Save processed 2014 taxi data in multiple formats.

    Parameters:
    -----------
    df : pd.DataFrame
        Processed taxi data
    output_dir : str
        Output directory
    sample_size : int
        Number of records for GeoJSON sample
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    columns_to_save = [
        'dropoff_datetime', 'dropoff_lon', 'dropoff_lat',
        'hour', 'day_of_week', 'is_weekend', 'weight'
    ]

    # Ensure all columns exist
    available_cols = [c for c in columns_to_save if c in df.columns]
    df_output = df[available_cols].copy()

    # Save Parquet
    parquet_path = output_path / "taxi_dropoffs_2014_weighted.parquet"
    df_output.to_parquet(parquet_path, compression='snappy', index=False)
    logger.info(f"Saved Parquet: {parquet_path}")
    logger.info(f"  Size: {parquet_path.stat().st_size / 1_048_576:.1f} MB")

    # Save GeoJSON sample
    from shapely.geometry import Point
    n_sample = min(sample_size, len(df_output))
    df_sample = df_output.sample(n=n_sample, random_state=42)

    geometry = [Point(lon, lat) for lon, lat in zip(df_sample['dropoff_lon'], df_sample['dropoff_lat'])]
    gdf_sample = gpd.GeoDataFrame(df_sample, geometry=geometry, crs="EPSG:4326")

    geojson_path = output_path / "taxi_dropoffs_2014_weighted_sample.geojson"
    gdf_sample.to_file(geojson_path, driver="GeoJSON")
    logger.info(f"Saved GeoJSON sample: {geojson_path} ({len(df_sample):,} records)")

    # Save summary
    import json
    summary = {
        'total_trips': len(df),
        'date_range': {
            'start': str(df['dropoff_datetime'].min()),
            'end': str(df['dropoff_datetime'].max())
        },
        'weight_stats': {
            'mean': float(df['weight'].mean()),
            'median': float(df['weight'].median()),
            'min': float(df['weight'].min()),
            'max': float(df['weight'].max())
        },
        'temporal_distribution': {
            'breakfast': int(((df['hour'] >= 7) & (df['hour'] < 10)).sum()),
            'lunch': int(((df['hour'] >= 11) & (df['hour'] < 14)).sum()),
            'dinner': int(((df['hour'] >= 17) & (df['hour'] < 22)).sum()),
            'late_night': int(((df['hour'] >= 22) | (df['hour'] < 1)).sum())
        },
        'note': '2014 coordinate-level data (no zone-centroid conversion)'
    }

    summary_path = output_path / "taxi_2014_processing_summary.json"
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    logger.info(f"Saved summary: {summary_path}")

    # Print summary
    print("\n" + "=" * 60)
    print("2014 TAXI DATA PROCESSING - SUMMARY")
    print("=" * 60)
    print(f"Total processed trips: {len(df):,}")
    print(f"Date range: {summary['date_range']['start']} to {summary['date_range']['end']}")
    print(f"\nTemporal distribution:")
    for k, v in summary['temporal_distribution'].items():
        print(f"  {k}: {v:,} trips")
    print(f"\nWeight statistics:")
    print(f"  Mean: {summary['weight_stats']['mean']:.3f}")
    print(f"  Range: [{summary['weight_stats']['min']:.1f}, {summary['weight_stats']['max']:.1f}]")
    print("=" * 60 + "\n")


def main():
    """Main execution function."""
    logger.info("=" * 60)
    logger.info("2014 TAXI DATA PROCESSING PIPELINE")
    logger.info("=" * 60)
    logger.info("Source: Real coordinate-level data (no zone-centroid conversion)")

    # Load configuration
    config = load_config()

    # Define paths
    data_dir = "data/raw/taxi_2014"
    boundary_path = "data/external/boundaries/nybb.shp"
    output_dir = "data/interim"

    # Step 1: Load 2014 data
    logger.info("\n[Step 1/6] Loading 2014 taxi data...")
    df = load_2014_taxi_data(data_dir)

    # Step 2: Standardize columns
    logger.info("\n[Step 2/6] Standardizing columns...")
    df = standardize_columns(df)

    # Step 3: Filter invalid coordinates (2014-specific: real coords, not IDs)
    logger.info("\n[Step 3/6] Filtering invalid coordinates...")
    df = filter_invalid_coordinates(df)

    # Step 4: Filter to NYC boundaries
    logger.info("\n[Step 4/6] Filtering to NYC boundaries...")
    df = filter_to_nyc_bounds(df, boundary_path)

    # Step 5: Filter to dining hours
    logger.info("\n[Step 5/6] Filtering to dining hours...")
    df = filter_dining_hours(df)

    # Step 6: Apply temporal weights
    logger.info("\n[Step 6/6] Applying temporal weights...")
    df = apply_temporal_weights(df, config)

    # Step 7: Save outputs
    logger.info("\n[Step 7/7] Saving outputs...")
    save_2014_outputs(df, output_dir)

    logger.info("\n✅ 2014 taxi data processing completed successfully!")


if __name__ == "__main__":
    main()
