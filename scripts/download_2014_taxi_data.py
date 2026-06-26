"""
Download 2014 NYC Yellow Taxi Trip Data from SODA API
======================================================

Downloads coordinate-level taxi data (with pickup_longitude, pickup_latitude,
dropoff_longitude, dropoff_latitude) from NYC Open Data SODA API.

Data source: https://data.cityofnewyork.us/Transportation/2014-Yellow-Taxi-Trip-Data/gkne-dk5s

Usage:
    # Check record count only
    python scripts/download_2014_taxi_data.py --start 2014-01-01 --end 2014-01-31 --check-only

    # Download full date range
    python scripts/download_2014_taxi_data.py --start 2014-01-01 --end 2014-01-07

    # Download with custom page size
    python scripts/download_2014_taxi_data.py --start 2014-01-01 --end 2014-01-31 --limit 50000

Output:
    - data/raw/taxi_2014/yellow_tripdata_2014_YYYYMMDD_YYYYMMDD.parquet

Author: Where to DINE Project
Date: 2026-06-25
"""

import argparse
import requests
import pandas as pd
import time
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

SODA_ENDPOINT = "https://data.cityofnewyork.us/resource/gkne-dk5s.json"
FIELDS = [
    "pickup_longitude", "pickup_latitude",
    "dropoff_longitude", "dropoff_latitude",
    "dropoff_datetime", "pickup_datetime",
    "passenger_count", "trip_distance"
]


def count_records(start_date, end_date):
    """Count total records for a date range using SODA $select=count(*)."""
    url = f"{SODA_ENDPOINT}?$select=count(*)&$where=dropoff_datetime%20between%20'{start_date}'%20and%20'{end_date}'"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        return int(data[0]['count'])
    except Exception as e:
        logger.error(f"Failed to count records: {e}")
        return None


def download_batch(start_date, end_date, limit=50000, offset=0):
    """Download one batch (page) of records from SODA API."""
    params = {
        "$select": ",".join(FIELDS),
        "$limit": limit,
        "$offset": offset,
        "$where": f"dropoff_datetime between '{start_date}' and '{end_date}'",
        "$order": "dropoff_datetime"
    }

    try:
        response = requests.get(SODA_ENDPOINT, params=params, timeout=120)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Download failed at offset {offset}: {e}")
        return None


def download_all(start_date, end_date, output_path, limit=50000):
    """
    Download all records for a date range with pagination.

    Parameters:
    -----------
    start_date, end_date : str
        ISO datetime strings (e.g. '2014-01-01T00:00:00')
    output_path : str
        Output parquet file path
    limit : int
        SODA API page size (max 50,000)

    Returns:
    --------
    pd.DataFrame or None
    """
    total = count_records(start_date, end_date)
    if total is None:
        logger.error("Could not determine record count. Aborting.")
        return None

    if total == 0:
        logger.error("No records found for the specified date range.")
        return None

    logger.info(f"Estimated {total:,} records for {start_date} to {end_date}")
    logger.info(f"Page size: {limit:,} (~{total // limit + 1} pages)")
    est_time_min = (total // limit + 1) * 0.5 / 60
    logger.info(f"Estimated download time: ~{est_time_min:.1f} minutes")

    all_records = []
    offset = 0
    page = 1
    total_pages = total // limit + 1

    while True:
        logger.info(f"[Page {page}/{total_pages}] Downloading offset {offset:,}...")
        records = download_batch(start_date, end_date, limit=limit, offset=offset)

        if records is None:
            logger.error(f"Download failed at page {page}. Saving partial data...")
            break

        if not records:
            logger.info("No more records. Download complete.")
            break

        all_records.extend(records)
        offset += len(records)
        page += 1

        if len(records) < limit:
            logger.info("Last page reached.")
            break

        # Rate limiting: be nice to SODA API
        time.sleep(0.3)

    if not all_records:
        logger.error("No records downloaded.")
        return None

    logger.info(f"Downloaded {len(all_records):,} records total")

    # Convert to DataFrame
    df = pd.DataFrame(all_records)

    # Convert numeric columns
    numeric_cols = [
        'pickup_longitude', 'pickup_latitude',
        'dropoff_longitude', 'dropoff_latitude',
        'passenger_count', 'trip_distance'
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Convert datetime
    df['dropoff_datetime'] = pd.to_datetime(df['dropoff_datetime'], errors='coerce')
    df['pickup_datetime'] = pd.to_datetime(df['pickup_datetime'], errors='coerce')

    # Save
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_parquet(output_path, compression='snappy', index=False)
    size_mb = output_path.stat().st_size / 1_048_576
    logger.info(f"Saved to {output_path} ({size_mb:.1f} MB)")

    # Summary
    logger.info(f"Records: {len(df):,}")
    logger.info(f"Date range: {df['dropoff_datetime'].min()} to {df['dropoff_datetime'].max()}")
    invalid_coords = df[
        (df['dropoff_longitude'] == 0) | (df['dropoff_latitude'] == 0) |
        df['dropoff_longitude'].isna() | df['dropoff_latitude'].isna()
    ].shape[0]
    logger.info(f"Invalid coordinates (0 or NaN): {invalid_coords:,} ({invalid_coords/len(df)*100:.1f}%)")

    return df


def main():
    parser = argparse.ArgumentParser(
        description='Download 2014 NYC Yellow Taxi coordinate data from SODA API'
    )
    parser.add_argument('--start', default='2014-01-01',
                        help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', default='2014-01-07',
                        help='End date (YYYY-MM-DD)')
    parser.add_argument('--output',
                        default='data/raw/taxi_2014/yellow_tripdata_2014.parquet',
                        help='Output parquet path')
    parser.add_argument('--limit', type=int, default=50000,
                        help='SODA API page size (max 50000)')
    parser.add_argument('--check-only', action='store_true',
                        help='Only count records, do not download')

    args = parser.parse_args()

    start_dt = f"{args.start}T00:00:00"
    end_dt = f"{args.end}T23:59:59"

    if args.check_only:
        total = count_records(start_dt, end_dt)
        if total is not None:
            print(f"\n{total:,} records available for {args.start} to {args.end}")
            print(f"Pages at 50,000/page: ~{total // 50000 + 1}")
            print(f"Est. download time: ~{(total // 50000 + 1) * 0.5 / 60:.1f} minutes")
        return

    download_all(start_dt, end_dt, args.output, limit=args.limit)


if __name__ == "__main__":
    main()
