"""Download and prepare Citi Bike arrivals for the controlled 2014 week."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import zipfile
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests


logger = logging.getLogger(__name__)
SOURCE_URL = "https://s3.amazonaws.com/tripdata/201401-citibike-tripdata.zip"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download(url: str, destination: Path) -> None:
    if destination.exists():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    with requests.get(url, stream=True, timeout=120) as response:
        response.raise_for_status()
        with partial.open("wb") as handle:
            for chunk in response.iter_content(1024 * 1024):
                if chunk:
                    handle.write(chunk)
    partial.replace(destination)


def load_archive(archive: Path) -> pd.DataFrame:
    with zipfile.ZipFile(archive) as bundle:
        csv_names = [
            name for name in bundle.namelist()
            if name.lower().endswith(".csv")
        ]
        if not csv_names:
            raise RuntimeError(f"No CSV found in {archive}")
        with bundle.open(csv_names[0]) as handle:
            return pd.read_csv(handle)


def normalize(frame: pd.DataFrame) -> pd.DataFrame:
    aliases = {
        "stoptime": "ended_at",
        "end station id": "end_station_id",
        "end station name": "end_station_name",
        "end station latitude": "end_lat",
        "end station longitude": "end_lon",
    }
    normalized = frame.rename(columns=aliases)
    required = [
        "ended_at",
        "end_station_id",
        "end_station_name",
        "end_lat",
        "end_lon",
    ]
    missing = [column for column in required if column not in normalized.columns]
    if missing:
        raise ValueError(f"Citi Bike archive is missing columns: {missing}")
    normalized["ended_at"] = pd.to_datetime(
        normalized["ended_at"],
        errors="coerce",
    )
    for column in ("end_lat", "end_lon"):
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce")
    return normalized[required].dropna(
        subset=["ended_at", "end_lat", "end_lon"]
    )


def filter_week(
    frame: pd.DataFrame,
    start: str,
    end: str,
) -> pd.DataFrame:
    start_dt = pd.Timestamp(start)
    end_dt = pd.Timestamp(end)
    frame = frame[
        (frame["ended_at"] >= start_dt)
        & (frame["ended_at"] < end_dt)
    ].copy()
    hour = frame["ended_at"].dt.hour
    dining = (
        hour.between(7, 9)
        | hour.between(11, 13)
        | hour.between(17, 23)
        | hour.eq(0)
    )
    frame = frame[dining].copy()
    frame["hour"] = frame["ended_at"].dt.hour
    frame["day_of_week"] = frame["ended_at"].dt.dayofweek
    frame["trip_id"] = pd.util.hash_pandas_object(
        frame[
            [
                "ended_at",
                "end_station_id",
                "end_lat",
                "end_lon",
            ]
        ],
        index=False,
    ).astype(str)
    return frame.drop_duplicates("trip_id")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2014-01-06")
    parser.add_argument("--end", default="2014-01-13")
    parser.add_argument(
        "--output-dir",
        default="data/raw/citibike_2014",
    )
    parser.add_argument(
        "--manifest-dir",
        default="data/manifests",
    )
    parser.add_argument(
        "--fixture",
        default="data/fixtures/citibike_2014_week_sample.parquet",
    )
    parser.add_argument("--fixture-size", type=int, default=5_000)
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    args = parse_args()
    output_dir = Path(args.output_dir)
    archive = output_dir / "201401-citibike-tripdata.zip"
    download(SOURCE_URL, archive)
    frame = filter_week(
        normalize(load_archive(archive)),
        args.start,
        args.end,
    )
    output = output_dir / (
        f"citibike_arrivals_{args.start}_{args.end}.parquet"
    )
    frame.to_parquet(output, compression="snappy", index=False)

    fixture_size = min(args.fixture_size, len(frame))
    fixture = frame.sample(fixture_size, random_state=42)
    fixture_path = Path(args.fixture)
    fixture_path.parent.mkdir(parents=True, exist_ok=True)
    fixture.to_parquet(fixture_path, compression="snappy", index=False)

    manifest = {
        "dataset": "Citi Bike Trip History",
        "source": SOURCE_URL,
        "start_date_inclusive": args.start,
        "end_date_exclusive": args.end,
        "dining_arrivals": int(len(frame)),
        "active_days": int(frame["ended_at"].dt.date.nunique()),
        "output_sha256": sha256(output),
        "fixture": {
            "path": args.fixture,
            "rows": fixture_size,
            "sha256": sha256(fixture_path),
        },
        "generated_at": datetime.now().astimezone().isoformat(),
    }
    manifest_dir = Path(args.manifest_dir)
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / (
        f"citibike_2014_{args.start}_{args.end}.json"
    )
    manifest_path.write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )
    logger.info("Wrote %s arrivals and manifest %s", len(frame), manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
