# Download 2014 NYC Taxi Coordinate Data (Full Month, Resumable)

> **Status**: SODA API download is slow (~3 minutes per 50,000-record page). 
> A full month requires ~300 pages = ~15 hours.
> 
> **Solution**: Use this resumable script. It saves each page as a separate chunk,
> so if interrupted, you can resume from the last page.

## Quick Start

Open PowerShell in the project directory and run:

```powershell
# Background download (won't block your terminal)
Start-Process -NoNewWindow -FilePath "python" -ArgumentList "scripts/download_2014_taxi_month.py --start 2014-01-01 --end 2014-02-01"
```

Or, to see progress in the terminal:

```powershell
python scripts/download_2014_taxi_month.py --start 2014-01-01 --end 2014-02-01
```

## What it does

1. Downloads data page-by-page (50,000 records per page) from SODA API
2. Saves each page as a separate `chunk_XXXX.parquet` file
3. If interrupted, re-run the same command — it will skip already-downloaded chunks
4. When all pages are downloaded, merges chunks into one final file
5. Deletes chunk files after merging

## Expected output

| File | Description |
|------|-------------|
| `data/raw/taxi_2014/yellow_tripdata_2014-01-01.parquet` | Final merged file (~300-400 MB for 1 month) |
| `data/raw/taxi_2014/chunks/` | Temporary chunks (auto-deleted after merge) |

## Resume after interruption

If the download is interrupted (network error, computer sleep, etc.), just re-run the same command. It will:
- Detect existing chunks
- Skip already-downloaded pages
- Continue from the last missing page

## After download completes

Run the processing pipeline:

```powershell
# Step 1: Process 2014 taxi data
python src/data_processing/10_process_2014_taxi_data.py

# Step 2: Cluster 2014 taxi dropoffs
python src/data_processing/11_cluster_2014_taxi_dropoffs.py

# Step 3: Compare 2014 vs 2024
python src/data_processing/12_compare_2014_vs_2024.py
```

## Estimated time

| Date Range | Pages | Est. Time |
|------------|-------|-----------|
| 1 day | ~8 | ~20 min |
| 3 days | ~24 | ~1 hour |
| 7 days | ~55 | ~2.5 hours |
| 1 month (Jan) | ~300 | ~15 hours |

## Alternative: Download a subset

If a full month is too long, download a shorter period that matches 2024 data volume:

```powershell
# 5 days ≈ 2M records, comparable to 2024's 2.05M
python scripts/download_2014_taxi_month.py --start 2014-01-06 --end 2014-01-11
```

## Note on SODA API vs TLC Parquet

The TLC-published 2014 Parquet files only contain `DOLocationID` (no coordinates).
The SODA API (`gkne-dk5s`) preserves the original `dropoff_longitude`/`dropoff_latitude`
fields from the 2014 data collection. This is why we use SODA API despite the slower speed.

---

*Last updated: 2026-06-26*
