"""
Taxi Trip Data Processing with Temporal Weighting
==================================================

Purpose: Process NYC taxi data, filter to dining hours, and apply temporal weights

Input:
    - data/raw/taxi/*.parquet (NYC taxi trip records)
    - data/external/boundaries/nybb.shp (NYC boundary shapefile)

Output:
    - data/interim/taxi_dropoffs_weighted.parquet
    - data/interim/taxi_dropoffs_weighted.geojson (sample for visualization)

Author: Where to DINE Project
Date: 2025-11-09
"""

import pandas as pd
import geopandas as gpd
import numpy as np
from pathlib import Path
import logging
from typing import Tuple
from shapely.geometry import Point
import sys
sys.path.append(str(Path(__file__).parent.parent))
from utils.config_loader import load_config, get_config_value
from pandarallel import pandarallel

pandarallel.initialize(progress_bar=True) # 初始化并行处理器，并显示一个进度条

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_taxi_data(data_dir: str) -> pd.DataFrame:
    """
    Load taxi trip data from Parquet files.

    Parameters:
    -----------
    data_dir : str
        Directory containing taxi Parquet files

    Returns:
    --------
    pd.DataFrame
        Combined taxi trip records
    """
    data_path = Path(data_dir)
    parquet_files = sorted(data_path.glob("*.parquet"))

    if not parquet_files:
        raise FileNotFoundError(f"No Parquet files found in {data_dir}")

    logger.info(f"Found {len(parquet_files)} Parquet file(s)")

    dfs = []
    for file in parquet_files:
        logger.info(f"Loading {file.name}...")
        df = pd.read_parquet(file)
        dfs.append(df)

    df_combined = pd.concat(dfs, ignore_index=True)

    logger.info(f"Loaded {len(df_combined):,} total taxi trips")

    return df_combined


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize column names across different taxi data schemas.

    NYC taxi data has different column names depending on:
    - Yellow vs Green taxi
    - Year/format changes

    Parameters:
    -----------
    df : pd.DataFrame
        Raw taxi data

    Returns:
    --------
    pd.DataFrame
        Standardized column names
    """
    logger.info("Standardizing column names...")

    # Column name mappings (various formats)
    column_mappings = {
        'tpep_dropoff_datetime': 'dropoff_datetime',
        'lpep_dropoff_datetime': 'dropoff_datetime',
        'dropoff_datetime': 'dropoff_datetime',

        'dropoff_longitude': 'dropoff_lon',
        'dropoff_latitude': 'dropoff_lat',
        'DOLocationID': 'dropoff_location_id',

        'pickup_datetime': 'pickup_datetime',
        'tpep_pickup_datetime': 'pickup_datetime',
        'lpep_pickup_datetime': 'pickup_datetime',
    }

    # Rename columns
    df = df.rename(columns=column_mappings)

    # Check for required columns
    if 'dropoff_datetime' not in df.columns:
        raise ValueError("Missing dropoff_datetime column")

    # For newer data with LocationIDs but no coordinates
    if 'dropoff_lon' not in df.columns and 'dropoff_location_id' in df.columns:
        logger.warning("Data has LocationIDs but no coordinates - will need zone lookup")
        # This would require NYC Taxi Zone shapefile lookup
        # For now, we'll just note this

    logger.info(f"Columns available: {list(df.columns)}")

    return df

def convert_ids_to_coords(df: pd.DataFrame, zones_path: str) -> pd.DataFrame:
    """
    Convert dropoff_location_id to lon/lat coordinates using the taxi zones shapefile.
    """
    logger.info(f"Loading taxi zones from {zones_path}...")
    try:
        gdf_zones = gpd.read_file(zones_path)
    except Exception as e:
        logger.error(f"CRITICAL: Failed to read taxi zones file: {e}")
        logger.error(f"Please ensure '{zones_path}' exists.")
        raise
    
    # 确保坐标系为 EPSG:4326 (lat/lon)
    gdf_zones = gdf_zones.to_crs("EPSG:4326")
    
    # 计算每个区域的“质心”（中心点）
    gdf_zones['centroid'] = gdf_zones.geometry.centroid
    
    # 准备“对照表” (我们只需要 ID 和 质心)
    # Taxi Zones 文件里的 ID 列名是 'LocationID'
    zones_lookup = gdf_zones[['LocationID', 'centroid']].copy()
    
    # 准备ID以便合并。将两者都转换为通用的数字类型。
    zones_lookup['LocationID'] = pd.to_numeric(zones_lookup['LocationID'], errors='coerce')
    df['dropoff_location_id'] = pd.to_numeric(df['dropoff_location_id'], errors='coerce')
    
    # 执行 'left' 合并，将“质心”添加到我们的主数据中
    logger.info("Merging taxi data with zone centroids...")
    df_merged = df.merge(
        zones_lookup,
        left_on='dropoff_location_id',
        right_on='LocationID',
        how='left'
    )
    
    # 从“质心”的 Point 几何中提取 lon (.x) 和 lat (.y)
    logger.info("Extracting coordinates from centroids...")
    # 旧的、慢速的代码
    # df_merged['dropoff_lon'] = df_merged['centroid'].apply(lambda p: p.x if p and p.is_valid else None)
    # df_merged['dropoff_lat'] = df_merged['centroid'].apply(lambda p: p.y if p and p.is_valid else None)
    # 这是新的、并行的代码！
    df_merged['dropoff_lon'] = df_merged['centroid'].parallel_apply(lambda p: p.x if p and p.is_valid else None)
    df_merged['dropoff_lat'] = df_merged['centroid'].parallel_apply(lambda p: p.y if p and p.is_valid else None)
    
    # 清理多余的列
    df_merged = df_merged.drop(columns=['LocationID', 'centroid'])
    
    # 打印日志结果
    total_trips = len(df_merged)
    converted_trips = df_merged['dropoff_lon'].notna().sum()
    failed_trips = total_trips - converted_trips
    
    logger.info(f"Successfully converted {converted_trips:,} of {total_trips:,} trips.")
    if failed_trips > 0:
        logger.warning(f"Failed to find coordinates for {failed_trips:,} trips (invalid LocationID).")
        
    return df_merged

def filter_to_nyc_bounds(
    df: pd.DataFrame,
    boundary_path: str
) -> pd.DataFrame:
    """
    Filter taxi dropoffs to NYC boundaries.

    Parameters:
    -----------
    df : pd.DataFrame
        Taxi data with dropoff coordinates
    boundary_path : str
        Path to NYC boundary shapefile

    Returns:
    --------
    pd.DataFrame
        Filtered taxi data within NYC bounds
    """
    logger.info("Filtering to NYC boundaries...")

    # Load NYC boundary
    nyc_boundary = gpd.read_file(boundary_path)
    nyc_boundary = nyc_boundary.to_crs("EPSG:4326")
    nyc_polygon = nyc_boundary.unary_union

    # Remove invalid coordinates
    df_clean = df.dropna(subset=['dropoff_lon', 'dropoff_lat'])

    # Filter obviously invalid coordinates
    # NYC rough bounds: lat [40.5, 40.92], lon [-74.3, -73.7]
    df_clean = df_clean[
        (df_clean['dropoff_lat'] >= 40.5) & (df_clean['dropoff_lat'] <= 40.92) &
        (df_clean['dropoff_lon'] >= -74.3) & (df_clean['dropoff_lon'] <= -73.7)
    ]

    logger.info(f"After coordinate validation: {len(df_clean):,} trips")

    # Create geometries and filter by boundary
    # geometry = [Point(lon, lat) for lon, lat in zip(df_clean['dropoff_lon'], df_clean['dropoff_lat'])]
    # gdf = gpd.GeoDataFrame(df_clean, geometry=geometry, crs="EPSG:4326")
    # 这是新的、向量化的代码 (快 100 倍！)
    gdf = gpd.GeoDataFrame(df_clean, geometry=gpd.points_from_xy(df_clean['dropoff_lon'], df_clean['dropoff_lat']), crs="EPSG:4326")

    # Spatial filter
    gdf_nyc = gdf[gdf.within(nyc_polygon)]

    logger.info(f"After NYC boundary filter: {len(gdf_nyc):,} trips ({len(gdf_nyc)/len(df)*100:.1f}% of original)")

    return gdf_nyc.drop(columns='geometry')


def filter_dining_hours(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter taxi trips to dining hours.

    Dining periods:
    - Breakfast: 7:00-10:00
    - Lunch: 11:00-14:00
    - Dinner: 17:00-22:00
    - Late night: 22:00-01:00

    Parameters:
    -----------
    df : pd.DataFrame
        Taxi data with dropoff_datetime

    Returns:
    --------
    pd.DataFrame
        Filtered to dining hours
    """
    logger.info("Filtering to dining hours...")

    # Ensure datetime format
    df['dropoff_datetime'] = pd.to_datetime(df['dropoff_datetime'])

    # Extract time features
    df['hour'] = df['dropoff_datetime'].dt.hour
    df['day_of_week'] = df['dropoff_datetime'].dt.dayofweek  # 0=Monday, 6=Sunday
    df['is_weekend'] = df['day_of_week'].isin([4, 5, 6])  # Fri, Sat, Sun

    # Define dining hours mask
    is_breakfast = (df['hour'] >= 7) & (df['hour'] < 10)
    is_lunch = (df['hour'] >= 11) & (df['hour'] < 14)
    is_dinner = (df['hour'] >= 17) & (df['hour'] < 22)
    is_late_night = (df['hour'] >= 22) | (df['hour'] < 1)

    dining_mask = is_breakfast | is_lunch | is_dinner | is_late_night

    df_dining = df[dining_mask].copy()

    logger.info(f"After dining hours filter: {len(df_dining):,} trips ({len(df_dining)/len(df)*100:.1f}% of total)")
    logger.info(f"  Breakfast: {is_breakfast.sum():,}")
    logger.info(f"  Lunch: {is_lunch.sum():,}")
    logger.info(f"  Dinner: {is_dinner.sum():,}")
    logger.info(f"  Late night: {is_late_night.sum():,}")

    return df_dining


def apply_temporal_weights(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """
    Apply temporal weights based on time and day of week.

    Weights reflect dining demand patterns:
    - Weekend dinner (Fri-Sun 18:00-22:00): 1.5× (highest demand)
    - Weekday dinner (Mon-Thu 18:00-22:00): 1.0× (baseline)
    - Weekday lunch (Mon-Fri 12:00-14:00): 0.8×
    - Breakfast (7:00-10:00): 0.5×
    - Late night weekend: 0.7×
    - Late night weekday: 0.4×
    - Other times: 0.3×

    Parameters:
    -----------
    df : pd.DataFrame
        Taxi data with hour, day_of_week, is_weekend columns
    config : dict
        Configuration with temporal weights

    Returns:
    --------
    pd.DataFrame
        Data with 'weight' column added
    """
    logger.info("Applying temporal weights...")

    # Get weights from config
    weights = get_config_value('temporal.weights', config)

    # Initialize weight column
    df['weight'] = 0.3  # Default: off-peak

    # Weekend dinner (highest demand)
    mask_weekend_dinner = (df['is_weekend']) & (df['hour'] >= 18) & (df['hour'] < 22)
    df.loc[mask_weekend_dinner, 'weight'] = weights.get('weekend_dinner', 1.5)

    # Weekday dinner (baseline)
    mask_weekday_dinner = (~df['is_weekend']) & (df['hour'] >= 18) & (df['hour'] < 22)
    df.loc[mask_weekday_dinner, 'weight'] = weights.get('weekday_dinner', 1.0)

    # Weekday lunch
    mask_weekday_lunch = (~df['is_weekend']) & (df['hour'] >= 12) & (df['hour'] < 14)
    df.loc[mask_weekday_lunch, 'weight'] = weights.get('weekday_lunch', 0.8)

    # Breakfast
    mask_breakfast = (df['hour'] >= 7) & (df['hour'] < 10)
    df.loc[mask_breakfast, 'weight'] = weights.get('breakfast', 0.5)

    # Late night weekend
    mask_late_weekend = (df['is_weekend']) & ((df['hour'] >= 22) | (df['hour'] < 1))
    df.loc[mask_late_weekend, 'weight'] = weights.get('late_night_weekend', 0.7)

    # Late night weekday
    mask_late_weekday = (~df['is_weekend']) & ((df['hour'] >= 22) | (df['hour'] < 1))
    df.loc[mask_late_weekday, 'weight'] = weights.get('late_night_weekday', 0.4)

    # Log weight distribution
    logger.info("Weight distribution:")
    logger.info(f"  Mean weight: {df['weight'].mean():.3f}")
    logger.info(f"  Median weight: {df['weight'].median():.3f}")
    logger.info(f"  Weekend dinner (1.5): {mask_weekend_dinner.sum():,} trips")
    logger.info(f"  Weekday dinner (1.0): {mask_weekday_dinner.sum():,} trips")
    logger.info(f"  Weekday lunch (0.8): {mask_weekday_lunch.sum():,} trips")

    return df


def save_outputs(df: pd.DataFrame, output_dir: str, sample_size: int = 10000):
    """
    Save processed taxi data in multiple formats.

    Parameters:
    -----------
    df : pd.DataFrame
        Processed taxi data
    output_dir : str
        Output directory
    sample_size : int
        Number of records for GeoJSON sample (default: 10,000)
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Select columns to save
    columns_to_save = [
        'dropoff_datetime', 'dropoff_lon', 'dropoff_lat',
        'hour', 'day_of_week', 'is_weekend', 'weight'
    ]

    df_output = df[columns_to_save].copy()

    # Save as Parquet (efficient for large data)
    parquet_path = output_path / "taxi_dropoffs_weighted.parquet"
    df_output.to_parquet(parquet_path, compression='snappy', index=False)
    logger.info(f"Saved Parquet: {parquet_path}")
    logger.info(f"  Size: {parquet_path.stat().st_size / 1_048_576:.1f} MB")

    # Save sample as GeoJSON for visualization
    df_sample = df_output.sample(n=min(sample_size, len(df_output)), random_state=42)

    geometry = [Point(lon, lat) for lon, lat in zip(df_sample['dropoff_lon'], df_sample['dropoff_lat'])]
    gdf_sample = gpd.GeoDataFrame(df_sample, geometry=geometry, crs="EPSG:4326")

    geojson_path = output_path / "taxi_dropoffs_weighted_sample.geojson"
    gdf_sample.to_file(geojson_path, driver="GeoJSON")
    logger.info(f"Saved GeoJSON sample: {geojson_path} ({len(df_sample):,} records)")

    # Save summary statistics
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
        }
    }

    import json
    summary_path = output_path / "taxi_processing_summary.json"
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    logger.info(f"Saved summary: {summary_path}")

    # Print summary
    print("\n" + "="*60)
    print("TAXI DATA PROCESSING - SUMMARY")
    print("="*60)
    print(f"Total processed trips: {len(df):,}")
    print(f"Date range: {summary['date_range']['start']} to {summary['date_range']['end']}")
    print(f"\nTemporal distribution:")
    print(f"  Breakfast (7-10): {summary['temporal_distribution']['breakfast']:,} trips")
    print(f"  Lunch (11-14): {summary['temporal_distribution']['lunch']:,} trips")
    print(f"  Dinner (17-22): {summary['temporal_distribution']['dinner']:,} trips")
    print(f"  Late night (22-01): {summary['temporal_distribution']['late_night']:,} trips")
    print(f"\nWeight statistics:")
    print(f"  Mean: {summary['weight_stats']['mean']:.3f}")
    print(f"  Range: [{summary['weight_stats']['min']:.1f}, {summary['weight_stats']['max']:.1f}]")
    print("="*60 + "\n")


def main():
    """
    Main execution function.
    """
    logger.info("="*60)
    logger.info("TAXI DATA PROCESSING PIPELINE")
    logger.info("="*60)

    # Load configuration
    config = load_config()

    # Define paths
    taxi_dir = "data/raw/taxi"
    boundary_path = "data/external/boundaries/nybb.shp"
    output_dir = "data/interim"

    # -----------------------------------------------
    # START: 这是替换后的新代码
    # -----------------------------------------------

    # Step 1: 找到所有文件
    logger.info("\n[Step 1/5] Finding taxi data files...")
    data_path = Path(taxi_dir)
    parquet_files = sorted(data_path.glob("*.parquet"))
    logger.info(f"Found {len(parquet_files)} files to process in batches.")

    processed_dfs = [] # 我们将把每个月的结果存在这里

    # Step 2-6: 在循环中处理每一个文件
    for i, file in enumerate(parquet_files):
        logger.info("\n" + "="*50)
        logger.info(f"STARTING BATCH {i+1} / {len(parquet_files)}: {file.name}")
        logger.info("="*50)

        try:
            # 2.1: 只加载 *一个* 文件
            df = pd.read_parquet(file)
            logger.info(f"Loaded {len(df):,} trips")

            # 2.2: 标准化
            logger.info("[Step 2/5] Standardizing columns...")
            df = standardize_columns(df)

            # 2.3: 转换 ID (我们的多进程优化)
            logger.info("[Step 2.5/5] Converting LocationIDs to coordinates...")
            taxi_zones_path = "data/external/boundaries/taxi_zones.shp"
            df = convert_ids_to_coords(df, taxi_zones_path)

            # 2.4: 过滤边界 (我们的向量化优化)
            logger.info("[Step 3/5] Filtering to NYC boundaries...")
            df = filter_to_nyc_bounds(df, boundary_path)

            # 2.5: 过滤时间
            logger.info("[Step 4/5] Filtering to dining hours...")
            df = filter_dining_hours(df)

            # 2.6: 应用权重
            logger.info("[Step 5/5] Applying temporal weights...")
            df = apply_temporal_weights(df, config)

            processed_dfs.append(df) # 把这个月干净的结果存起来
            logger.info(f"✅ BATCH {i+1} / {len(parquet_files)} COMPLETED")

        except Exception as e:
            logger.error(f"❌ FAILED BATCH {i+1} / {len(parquet_files)} ({file.name}): {e}")
            # 即使一个文件失败了，也继续处理下一个
            continue 

    # 循环结束，合并所有结果
    logger.info("\n" + "="*60)
    logger.info("All batches processed. Concatenating final dataframe...")
    if not processed_dfs:
        logger.error("No data was successfully processed. Exiting.")
        return # 退出

    final_df = pd.concat(processed_dfs, ignore_index=True)
    logger.info(f"Total processed trips from all files: {len(final_df):,}")

    # Step 6: 保存 *合并后* 的总输出
    logger.info("\n[Step 6/6] Saving FINAL outputs...")
    save_outputs(final_df, output_dir)

    logger.info("\n✅ Taxi data processing (all batches) completed successfully!")

    # -----------------------------------------------
    # END: 新代码结束
    # -----------------------------------------------

    # # Step 1: Load taxi data
    # logger.info("\n[Step 1/5] Loading taxi data...")
    # df = load_taxi_data(taxi_dir)

    # # Step 2: Standardize columns
    # logger.info("\n[Step 2/5] Standardizing columns...")
    # df = standardize_columns(df)

    # # ✨✨✨ START: 这是我们新加的代码 ✨✨✨
    # # Step 2.5: Convert LocationIDs to Coordinates
    # logger.info("\n[Step 2.5/5] Converting LocationIDs to coordinates...")
    # taxi_zones_path = "data/external/boundaries/taxi_zones.shp"  # 告诉脚本去哪里找“对照表”
    # df = convert_ids_to_coords(df, taxi_zones_path)
    # # ✨✨✨ END: 新加的代码结束 ✨✨✨

    # # Step 3: Filter to NYC bounds
    # logger.info("\n[Step 3/5] Filtering to NYC boundaries...")
    # df = filter_to_nyc_bounds(df, boundary_path)

    # # Step 4: Filter to dining hours
    # logger.info("\n[Step 4/5] Filtering to dining hours...")
    # df = filter_dining_hours(df)

    # # Step 5: Apply temporal weights
    # logger.info("\n[Step 5/5] Applying temporal weights...")
    # df = apply_temporal_weights(df, config)

    # # Step 6: Save outputs
    # logger.info("\n[Step 6/6] Saving outputs...")
    # save_outputs(df, output_dir)

    # logger.info("\n✅ Taxi data processing completed successfully!")


if __name__ == "__main__":
    main()
