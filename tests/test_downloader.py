from datetime import date
import importlib.util
from pathlib import Path

import pandas as pd
import requests


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "download_2014_taxi_month.py"
)
SPEC = importlib.util.spec_from_file_location("taxi_downloader", MODULE_PATH)
downloader = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(downloader)


class FakeResponse:
    def __init__(self, records):
        self.records = records

    def raise_for_status(self):
        return None

    def json(self):
        return self.records


class FakeSession:
    def __init__(self, pages):
        self.pages = pages
        self.params = []

    def get(self, _url, params, timeout):
        self.params.append(params)
        return FakeResponse(self.pages.get(params["$offset"], []))


class RetrySession:
    def __init__(self, records):
        self.records = records
        self.calls = 0

    def get(self, _url, params, timeout):
        self.calls += 1
        if self.calls == 1:
            raise requests.ConnectionError("temporary")
        return FakeResponse(self.records)


def _record(hour, longitude="-73.99"):
    return {
        "pickup_longitude": longitude,
        "pickup_latitude": "40.70",
        "dropoff_longitude": "-73.98",
        "dropoff_latitude": "40.71",
        "dropoff_datetime": f"2014-01-06T{hour}:00:00",
        "pickup_datetime": f"2014-01-06T{hour}:50:00",
        "passenger_count": "2",
        "trip_distance": "1.5",
    }


def test_iter_days_is_half_open():
    days = list(downloader.iter_days(date(2014, 1, 6), date(2014, 1, 8)))
    assert days == [date(2014, 1, 6), date(2014, 1, 7)]


def test_normalize_page_coerces_types():
    frame = downloader.normalize_page([_record("12")])
    assert pd.api.types.is_float_dtype(frame["pickup_longitude"])
    assert pd.api.types.is_datetime64_any_dtype(frame["dropoff_datetime"])


def test_request_page_retries_transient_failure(monkeypatch):
    session = RetrySession([_record("12")])
    monkeypatch.setattr(downloader.time, "sleep", lambda _: None)
    records = downloader.request_page(
        session,
        date(2014, 1, 6),
        offset=0,
        retries=2,
    )
    assert records == [_record("12")]
    assert session.calls == 2


def test_download_day_paginates_and_deduplicates(tmp_path):
    duplicate = _record("12")
    session = FakeSession(
        {
            0: [duplicate, _record("13")],
            2: [duplicate],
        }
    )
    stats = downloader.download_day(
        date(2014, 1, 6),
        tmp_path / "output",
        tmp_path / "chunks",
        session=session,
        page_size=2,
    )
    assert stats["rows"] == 2
    assert stats["duplicates_removed"] == 1
    assert [item["$offset"] for item in session.params] == [0, 2]


def test_download_day_resumes_existing_chunks(tmp_path):
    chunk_dir = tmp_path / "chunks" / "2014-01-06"
    chunk_dir.mkdir(parents=True)
    downloader.normalize_page([_record("12")]).to_parquet(
        chunk_dir / "chunk_0001.parquet",
        index=False,
    )
    session = FakeSession({1: [_record("13")]})
    stats = downloader.download_day(
        date(2014, 1, 6),
        tmp_path / "output",
        tmp_path / "chunks",
        session=session,
        page_size=2,
    )
    assert stats["rows"] == 2
    assert session.params[0]["$offset"] == 1


def test_existing_day_is_repaired_to_half_open_boundary(tmp_path):
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    path = output_dir / "yellow_tripdata_2014-01-06.parquet"
    downloader.normalize_page([
        _record("12"),
        {
            **_record("12"),
            "dropoff_datetime": "2014-01-07T00:00:00",
        },
    ]).to_parquet(path, index=False)

    stats = downloader.download_day(
        date(2014, 1, 6),
        output_dir,
        tmp_path / "chunks",
    )

    assert stats["status"] == "existing_repaired"
    assert stats["rows"] == 1
    assert pd.read_parquet(path)["dropoff_datetime"].max() < pd.Timestamp(
        "2014-01-07"
    )
