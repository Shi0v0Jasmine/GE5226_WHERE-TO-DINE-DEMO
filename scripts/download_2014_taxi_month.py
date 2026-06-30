"""Resumable daily downloader for NYC 2014 Yellow Taxi coordinate data."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, Optional

import pandas as pd
import requests


logger = logging.getLogger(__name__)
SODA_ENDPOINT = "https://data.cityofnewyork.us/resource/gkne-dk5s.json"
FIELDS = [
    "pickup_longitude",
    "pickup_latitude",
    "dropoff_longitude",
    "dropoff_latitude",
    "dropoff_datetime",
    "pickup_datetime",
    "passenger_count",
    "trip_distance",
]
NUMERIC_FIELDS = [
    "pickup_longitude",
    "pickup_latitude",
    "dropoff_longitude",
    "dropoff_latitude",
    "passenger_count",
    "trip_distance",
]
PAGE_SIZE = 50_000


def iter_days(start: date, end: date) -> Iterable[date]:
    """Yield dates in the half-open interval [start, end)."""
    current = start
    while current < end:
        yield current
        current += timedelta(days=1)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize_page(records: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(records)
    for column in FIELDS:
        if column not in frame.columns:
            frame[column] = pd.NA
    for column in NUMERIC_FIELDS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    for column in ("pickup_datetime", "dropoff_datetime"):
        frame[column] = pd.to_datetime(frame[column], errors="coerce")
    return frame[FIELDS]


def request_page(
    session: requests.Session,
    day: date,
    offset: int,
    page_size: int = PAGE_SIZE,
    retries: int = 5,
) -> list[dict]:
    start = f"{day.isoformat()}T00:00:00"
    end = f"{(day + timedelta(days=1)).isoformat()}T00:00:00"
    params = {
        "$select": ",".join(FIELDS),
        "$where": f"dropoff_datetime >= '{start}' AND dropoff_datetime < '{end}'",
        "$order": "dropoff_datetime,pickup_datetime",
        "$limit": page_size,
        "$offset": offset,
    }
    for attempt in range(retries):
        try:
            response = session.get(
                SODA_ENDPOINT,
                params=params,
                timeout=120,
            )
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            if attempt == retries - 1:
                raise RuntimeError(
                    f"Failed downloading {day} at offset {offset}"
                ) from exc
            delay = min(2 ** attempt, 30)
            logger.warning(
                "Retrying %s offset %s in %ss: %s",
                day,
                offset,
                delay,
                exc,
            )
            time.sleep(delay)
    return []


def existing_chunk_offset(chunk_dir: Path) -> int:
    total = 0
    for chunk in sorted(chunk_dir.glob("chunk_*.parquet")):
        total += len(pd.read_parquet(chunk, columns=["dropoff_datetime"]))
    return total


def merge_day_chunks(chunk_dir: Path, output_path: Path) -> Dict[str, object]:
    chunks = sorted(chunk_dir.glob("chunk_*.parquet"))
    if not chunks:
        raise RuntimeError(f"No chunks found in {chunk_dir}")
    frame = pd.concat(
        [pd.read_parquet(path) for path in chunks],
        ignore_index=True,
    )
    before_dedup = len(frame)
    frame = frame.drop_duplicates(subset=FIELDS).sort_values(
        ["dropoff_datetime", "pickup_datetime"],
        kind="mergesort",
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(output_path, compression="snappy", index=False)
    for chunk in chunks:
        chunk.unlink()
    chunk_dir.rmdir()
    return {
        "rows": int(len(frame)),
        "duplicates_removed": int(before_dedup - len(frame)),
        "date_min": str(frame["dropoff_datetime"].min()),
        "date_max": str(frame["dropoff_datetime"].max()),
        "size_bytes": int(output_path.stat().st_size),
        "sha256": file_sha256(output_path),
    }


def validate_existing_day(
    output_path: Path,
    day: date,
) -> Dict[str, object]:
    """Validate, deduplicate, and repair an existing daily file if necessary."""
    frame = pd.read_parquet(output_path)
    timestamps = pd.to_datetime(frame["dropoff_datetime"], errors="coerce")
    start = pd.Timestamp(day)
    end = start + pd.Timedelta(days=1)
    valid = timestamps.ge(start) & timestamps.lt(end)
    before = len(frame)
    frame = frame.loc[valid].copy()
    frame["dropoff_datetime"] = timestamps.loc[valid]
    if "pickup_datetime" in frame:
        frame["pickup_datetime"] = pd.to_datetime(
            frame["pickup_datetime"],
            errors="coerce",
        )
    frame = frame.drop_duplicates(subset=FIELDS).sort_values(
        ["dropoff_datetime", "pickup_datetime"],
        kind="mergesort",
    )
    removed = before - len(frame)
    if removed:
        frame.to_parquet(output_path, compression="snappy", index=False)
    return {
        "rows": int(len(frame)),
        "duplicates_removed": int(removed),
        "date_min": str(frame["dropoff_datetime"].min()),
        "date_max": str(frame["dropoff_datetime"].max()),
        "size_bytes": int(output_path.stat().st_size),
        "sha256": file_sha256(output_path),
        "status": "existing_repaired" if removed else "existing",
    }


def download_day(
    day: date,
    output_dir: Path,
    chunk_root: Path,
    session: Optional[requests.Session] = None,
    page_size: int = PAGE_SIZE,
) -> Dict[str, object]:
    output_path = output_dir / f"yellow_tripdata_{day.isoformat()}.parquet"
    if output_path.exists():
        return validate_existing_day(output_path, day)

    session = session or requests.Session()
    chunk_dir = chunk_root / day.isoformat()
    chunk_dir.mkdir(parents=True, exist_ok=True)
    offset = existing_chunk_offset(chunk_dir)
    page = len(list(chunk_dir.glob("chunk_*.parquet")))

    while True:
        records = request_page(session, day, offset, page_size=page_size)
        if not records:
            break
        page += 1
        normalized = normalize_page(records)
        normalized.to_parquet(
            chunk_dir / f"chunk_{page:04d}.parquet",
            compression="snappy",
            index=False,
        )
        offset += len(normalized)
        logger.info("%s: page=%s rows=%s", day, page, offset)
        if len(records) < page_size:
            break

    stats = merge_day_chunks(chunk_dir, output_path)
    stats["status"] = "downloaded"
    return stats


def write_fixture(
    files: list[Path],
    output_path: Path,
    fixture_size: int,
) -> None:
    frames = [pd.read_parquet(path) for path in files]
    combined = pd.concat(frames, ignore_index=True)
    sample_size = min(fixture_size, len(combined))
    fixture = combined.sample(sample_size, random_state=42).sort_values(
        ["dropoff_datetime", "pickup_datetime"],
        kind="mergesort",
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fixture.to_parquet(output_path, compression="snappy", index=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2014-01-06")
    parser.add_argument("--end", default="2014-01-13")
    parser.add_argument("--output-dir", default="data/raw/taxi_2014")
    parser.add_argument("--chunk-dir", default="data/raw/taxi_2014/chunks")
    parser.add_argument("--manifest-dir", default="data/manifests")
    parser.add_argument(
        "--fixture",
        default="data/fixtures/nyc_2014_taxi_week_sample.parquet",
    )
    parser.add_argument("--fixture-size", type=int, default=10_000)
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    args = parse_args()
    start = datetime.strptime(args.start, "%Y-%m-%d").date()
    end = datetime.strptime(args.end, "%Y-%m-%d").date()
    if end <= start:
        raise ValueError("--end must be after --start")

    output_dir = Path(args.output_dir)
    chunk_root = Path(args.chunk_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_days: Dict[str, Dict[str, object]] = {}
    session = requests.Session()

    for day in iter_days(start, end):
        manifest_days[day.isoformat()] = download_day(
            day,
            output_dir,
            chunk_root,
            session=session,
        )

    files = [
        output_dir / f"yellow_tripdata_{day.isoformat()}.parquet"
        for day in iter_days(start, end)
    ]
    write_fixture(files, Path(args.fixture), args.fixture_size)

    manifest = {
        "dataset": "NYC Open Data 2014 Yellow Taxi Trip Data",
        "dataset_id": "gkne-dk5s",
        "source": SODA_ENDPOINT,
        "start_date_inclusive": start.isoformat(),
        "end_date_exclusive": end.isoformat(),
        "fields": FIELDS,
        "days": manifest_days,
        "total_rows": int(sum(item["rows"] for item in manifest_days.values())),
        "fixture": {
            "path": args.fixture,
            "rows": min(args.fixture_size, sum(item["rows"] for item in manifest_days.values())),
            "sha256": file_sha256(Path(args.fixture)),
        },
        "generated_at": datetime.now().astimezone().isoformat(),
    }
    manifest_dir = Path(args.manifest_dir)
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / (
        f"nyc_2014_taxi_{start.isoformat()}_{end.isoformat()}.json"
    )
    manifest_path.write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )
    logger.info("Wrote manifest: %s", manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
