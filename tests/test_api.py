import geopandas as gpd
from shapely.geometry import box

import app as product_app


def _hotspots():
    return gpd.GeoDataFrame(
        {
            "hotspot_id": ["dining", "airport"],
            "is_airport": [False, True],
            "dropoff_count": [1_000, 5_000],
            "restaurant_count": [25, 10],
            "avg_rating": [4.3, 3.5],
            "bayesian_rating": [4.1, 3.6],
            "rating_coverage": [0.9, 0.5],
            "peak_time_score": [70.0, 50.0],
            "lunch_peak_score": [65.0, 50.0],
            "data_confidence": [90.0, 80.0],
            "area_quality_score": [82.0, 70.0],
            "composite_score": [75.0, 80.0],
            "topsis_score": [0.75, 0.8],
        },
        geometry=[
            box(-74.01, 40.70, -74.00, 40.71),
            box(-73.79, 40.64, -73.78, 40.65),
        ],
        crs="EPSG:4326",
    )


def test_invalid_mode_returns_400():
    product_app.hotspots_data = _hotspots()
    client = product_app.app.test_client()
    response = client.post(
        "/api/recommend?mode=transit",
        json={"lat": 40.72, "lon": -74.0},
    )
    assert response.status_code == 400


def test_v3_proxy_excludes_airport_and_returns_components():
    product_app.hotspots_data = _hotspots()
    client = product_app.app.test_client()
    response = client.post(
        "/api/recommend?backend=proxy&score_version=v3",
        json={"lat": 40.72, "lon": -74.0},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["excluded_counts"]["airport"] == 1
    assert payload["effective_backend"] == "proxy"
    assert payload["recommendations"][0]["hotspot_id"] == "dining"
    assert "score_components" in payload["recommendations"][0]
    assert payload["recommendations"][0]["is_estimate"]


def test_strict_osmnx_missing_graph_returns_503(monkeypatch):
    product_app.hotspots_data = _hotspots()

    class MissingBackend:
        def __init__(self, *args, **kwargs):
            raise product_app.BackendUnavailableError("missing graph")

    monkeypatch.setattr(product_app, "TravelTimeCalculator", MissingBackend)
    client = product_app.app.test_client()
    response = client.post(
        "/api/recommend?backend=osmnx&allow_fallback=false",
        json={"lat": 40.72, "lon": -74.0},
    )
    assert response.status_code == 503


def test_legacy_parameter_aliases():
    product_app.hotspots_data = _hotspots()
    client = product_app.app.test_client()
    response = client.post(
        "/api/recommend?access_method=proxy&version=v1",
        json={"lat": 40.72, "lon": -74.0},
    )
    assert response.status_code == 200
    assert response.get_json()["score_version"] == "v1_legacy"
