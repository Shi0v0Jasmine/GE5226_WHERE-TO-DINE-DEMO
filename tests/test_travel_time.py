import numpy as np
import pytest

from src.travel_time import BackendUnavailableError, TravelTimeCalculator


NYC_ORIGIN = (40.7580, -73.9855)
NYC_DESTINATION = (40.7280, -73.9940)


def test_proxy_nyc_od_is_finite_positive_and_mode_reasonable():
    times = {
        mode: TravelTimeCalculator(mode=mode, backend="proxy").single(
            NYC_ORIGIN,
            NYC_DESTINATION,
        )
        for mode in ("walk", "bike", "drive")
    }
    assert all(np.isfinite(value) and value > 0 for value in times.values())
    assert times["walk"] > times["bike"]
    assert times["walk"] > times["drive"]


def test_strict_osmnx_rejects_missing_graph(tmp_path):
    with pytest.raises(BackendUnavailableError):
        TravelTimeCalculator(
            mode="walk",
            backend="osmnx",
            graph_path=str(tmp_path / "missing.graphml"),
            allow_fallback=False,
        )


def test_osmnx_missing_graph_reports_proxy_fallback(tmp_path):
    calculator = TravelTimeCalculator(
        mode="walk",
        backend="osmnx",
        graph_path=str(tmp_path / "missing.graphml"),
        allow_fallback=True,
    )
    value = calculator.single(NYC_ORIGIN, NYC_DESTINATION)
    info = calculator.info()
    assert np.isfinite(value)
    assert info["requested_backend"] == "osmnx"
    assert info["effective_backend"] == "proxy"
    assert info["is_estimate"]
    assert "unavailable" in info["fallback_reason"].lower()
