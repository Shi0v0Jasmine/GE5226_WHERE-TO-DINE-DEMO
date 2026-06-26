"""
Download 2014 NYC Yellow Taxi data for a full month (incremental, resumable).

Writes each page to a separate Parquet chunk, then merges at the end.
This avoids loading all ~15M records into memory at once.

Usage:
    python scripts/download_2014_taxi_month.py --start 2014-01-01 --end 2014-02-01

Output:
    data/raw/taxi_2014/yellow_tripdata_2014_YYYY-MM.parquet

Author: Where to DINE Project
Date: 2026-06-26
"""

import argparse
import requests
import pandas as pd
import time
import logging
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq

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
PAGE_SIZE = 50000


def download_and_save(start_date, end_date, output_dir, chunk_dir):
    """
    Download all records for a date range, saving each page as a separate Parquet chunk.

    Returns:
    --------
    int : total records downloaded
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    chunk_path = Path(chunk_dir)
    chunk_path.mkdir(parents=True, exist_ok=True)

    offset = 0
    page = 0
    total_records = 0
    empty_page_count = 0

    while True:
        params = {
            "$select": ",".join(FIELDS),
            "$limit": PAGE_SIZE,
            "$offset": offset,
            "$where": f"dropoff_datetime between '{start_date}' and '{end_date}'",
            "$order": "dropoff_datetime"
        }

        try:
            response = requests.get(SODA_ENDPOINT, params=params, timeout=120)
            response.raise_for_status()
            records = response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Download failed at offset {offset}: {e}")
            break

        if not records:
            empty_page_count += 1
            if empty_page_count >= 3:
                logger.info("3 consecutive empty pages. Download complete.")
                break
            time.sleep(1)
            continue

        empty_page_count = 0
        total_records += len(records)
        page += 1

        # Convert to DataFrame
        df = pd.DataFrame(records)
        for col in ['pickup_longitude', 'pickup_latitude',
                    'dropoff_longitude', 'dropoff_latitude',
                    'passenger_count', 'trip_distance']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        df['dropoff_datetime'] = pd.to_datetime(df['dropoff_datetime'], errors='coerce')
        df['pickup_datetime'] = pd.to_datetime(df['pickup_datetime'], errors='coerce')

        # Save chunk
        chunk_file = chunk_path / f"chunk_{page:04d}.parquet"
        df.to_parquet(chunk_file, compression='snappy', index=False)

        logger.info(f"[Page {page}] Downloaded {len(records):,} records (total: {total_records:,})")

        if len(records) < PAGE_SIZE:
            logger.info("Last page reached.")
            break

        offset += len(records)
        time.sleep(0.3)

    return total_records, page


def merge_chunks(chunk_dir, output_file):
    """Merge all chunk Parquet files into one."""
    chunk_path = Path(chunk_dir)
    chunks = sorted(chunk_path.glob("chunk_*.parquet"))

    if not chunks:
        logger.error("No chunk files found to merge.")
        return None

    logger.info(f"Merging {len(chunks)} chunks into {output_file}...")

    # Read first chunk to get schema
    first_df = pd.read_parquet(chunks[0])
    schema = pa.Table.from_pandas(first_df).schema

    writer = pq.ParquetWriter(output_file, schema, compression='snappy')

    for chunk_file in chunks:
        df = pd.read_parquet(chunk_file)
        table = pa.Table.from_pandas(df, schema=schema)
        writer.write_table(table)
        chunk_file.unlink()  # Delete chunk after writing
        logger.info(f"  Merged {chunk_file.name}")

    writer.close()
    logger.info(f"Merged {len(chunks)} chunks into {output_file}")

    return pd.read_parquet(output_file)


def main():
    parser = argparse.ArgumentParser(description='Download 2014 NYC Yellow Taxi data for a full month')
    parser.add_argument('--start', default='2014-01-01', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', default='2014-02-01', help='End date (YYYY-MM-DD)')
    parser.add_argument('--output-dir', default='data/raw/taxi_2014', help='Output directory')
    parser.add_argument('--chunk-dir', default='data/raw/taxi_2014/chunks', help='Temporary chunk directory')

    args = parser.parse_args()

    start_dt = f"{args.start}T00:00:00"
    end_dt = f"{args.end}T00:00:00"
    output_file = f"{args.output_dir}/yellow_tripdata_{args.start}.parquet"

    logger.info("=" * 60)
    logger.info(f"Downloading 2014 taxi data: {args.start} to {args.end}")
    logger.info("=" * 60)

    # Download
    total, pages = download_and_save(start_dt, end_dt, args.output_dir, args.chunk_dir)
    logger.info(f"Downloaded {total:,} records in {pages} pages")

    if total == 0:
        logger.error("No records downloaded. Aborting.")
        return 1

    # Merge
    df = merge_chunks(args.chunk_dir, output_file)
    if df is None:
        return 1

    # Summary
    size_mb = Path(output_file).stat().st_size / 1_048_576
    logger.info(f"\n{'='*60}")
    logger.info(f"DOWNLOAD COMPLETE")
    logger.info(f"{'='*60}")
    logger.info(f"File: {output_file}")
    logger.info(f"Records: {len(df):,}")
    logger.info(f"Size: {size_mb:.1f} MB")
    logger.info(f"Date range: {df['dropoff_datetime'].min()} to {df['dropoff_datetime'].max()}")
    logger.info(f"Invalid coords: {((df['dropoff_longitude'] == 0) | (df['dropoff_latitude'] == 0) | df['dropoff_longitude'].isna() | df['dropoff_latitude'].isna()).sum():,}")
    logger.info(f"{'='*60}")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
