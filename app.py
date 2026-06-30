"""Flask API and Leaflet product demo for Where to DINE."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import geopandas as gpd
import numpy as np
import pandas as pd
from flask import Flask, jsonify, render_template, request
from shapely.geometry import Point

from src.analysis.scoring import (
    MODE_ACCESS_DEFAULTS,
    PRODUCT_COMPONENTS,
    PRODUCT_PROFILE_PRIORS,
    compute_access_score_half_life,
    compute_product_area_scores,
    compute_product_recommendation,
)
from src.travel_time import BackendUnavailableError, TravelTimeCalculator


logger = logging.getLogger(__name__)
app = Flask(__name__)
hotspots_data: Optional[gpd.GeoDataFrame] = None
diagnostic_airport_count = 0

ALLOWED_MODES = {"walk", "bike", "drive"}
ALLOWED_BACKENDS = {"proxy", "osmnx"}
ALLOWED_TIME_PROFILES = {"any", "lunch", "dinner", "late_night"}
VERSION_ALIASES = {
    "v1": "v1_legacy",
    "v1_legacy": "v1_legacy",
    "v2": "v2_entropy_legacy",
    "v2_entropy_legacy": "v2_entropy_legacy",
    "v3": "v3_product",
    "v3_product": "v3_product",
}


def load_hotspots(path: Optional[str] = None) -> Optional[gpd.GeoDataFrame]:
    """Load the best available hotspot artifact."""
    global hotspots_data, diagnostic_airport_count
    candidates = [
        Path(path) if path else None,
        Path("data/processed/final_hotspots_v3.geojson"),
        Path("data/processed/final_hotspots.geojson"),
    ]
    hotspot_path = next((item for item in candidates if item and item.exists()), None)
    if hotspot_path is None:
        logger.error("No hotspot artifact found. Run the spatial pipeline first.")
        hotspots_data = None
        return None
    hotspots_data = gpd.read_file(hotspot_path).to_crs("EPSG:4326")
    diagnostic_path = Path(
        "data/processed/airport_hotspots_diagnostics.geojson"
    )
    diagnostic_airport_count = (
        len(gpd.read_file(diagnostic_path))
        if diagnostic_path.exists()
        else 0
    )
    logger.info("Loaded %s hotspots from %s", len(hotspots_data), hotspot_path)
    return hotspots_data


def _parse_bool(value: Optional[str], default: bool = True) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"Invalid boolean value: {value}")


def _error(message: str, status: int):
    return jsonify({"error": message}), status


def _rankable_hotspots() -> tuple[gpd.GeoDataFrame, int]:
    if hotspots_data is None:
        return gpd.GeoDataFrame(), 0
    if "is_airport" not in hotspots_data.columns:
        return hotspots_data.copy(), diagnostic_airport_count
    mask = hotspots_data["is_airport"].fillna(False).astype(bool)
    return (
        hotspots_data[~mask].copy(),
        max(int(mask.sum()), diagnostic_airport_count),
    )


def _time_component(df: pd.DataFrame, time_profile: str) -> np.ndarray:
    if time_profile == "lunch" and "lunch_peak_score" in df.columns:
        return df["lunch_peak_score"].fillna(50.0).to_numpy(dtype=float)
    if time_profile in {"dinner", "late_night"} and "peak_time_score" in df.columns:
        return df["peak_time_score"].fillna(50.0).to_numpy(dtype=float)
    return df.get(
        "time_fit_score_v3",
        pd.Series(50.0, index=df.index)
    ).fillna(50.0).to_numpy(dtype=float)


def _product_components(
    df: pd.DataFrame,
    time_profile: str
) -> np.ndarray:
    def column(primary: str, fallback: Optional[str] = None) -> np.ndarray:
        if primary in df.columns:
            series = df[primary]
        elif fallback and fallback in df.columns:
            series = df[fallback]
        else:
            series = pd.Series(50.0, index=df.index)
        return pd.to_numeric(series, errors="coerce").fillna(50.0).to_numpy()

    return np.column_stack([
        column("demand_score_v3", "taxi_score_v2"),
        column("poi_score_v3", "restaurant_score_v2"),
        _time_component(df, time_profile),
        column("data_confidence_v3"),
    ]).astype(float)


@app.route("/")
def index():
    if hotspots_data is None or len(hotspots_data) == 0:
        return (
            "<h1>No hotspot data</h1><p>Run the processing pipeline first.</p>",
            503,
        )
    return render_template("index.html")


@app.route("/api/hotspots", methods=["GET"])
def get_all_hotspots():
    if hotspots_data is None:
        return _error("No data loaded", 503)
    try:
        include_airports = _parse_bool(
            request.args.get("include_airports"),
            default=False
        )
    except ValueError as exc:
        return _error(str(exc), 400)
    frame = hotspots_data
    if not include_airports and "is_airport" in frame.columns:
        frame = frame[~frame["is_airport"].fillna(False)]
    return jsonify(json.loads(frame.to_json()))


@app.route("/api/recommend", methods=["POST"])
def get_recommendations():
    if hotspots_data is None:
        return _error("No data loaded", 503)

    payload: Dict[str, Any] = request.get_json(silent=True) or {}
    try:
        user_lat = float(payload["lat"])
        user_lon = float(payload["lon"])
        limit = int(request.args.get("limit", payload.get("limit", 10)))
        if not (-90 <= user_lat <= 90 and -180 <= user_lon <= 180):
            raise ValueError("lat/lon are outside valid ranges")
        if not 1 <= limit <= 50:
            raise ValueError("limit must be between 1 and 50")

        mode = request.args.get("mode", "walk")
        backend = request.args.get(
            "backend",
            request.args.get("access_method", "proxy")
        )
        profile = request.args.get("profile", "balanced")
        time_profile = request.args.get("time_profile", "any")
        requested_version = request.args.get(
            "score_version",
            request.args.get("version", "v3")
        )
        score_version = VERSION_ALIASES.get(requested_version)
        allow_fallback = _parse_bool(
            request.args.get("allow_fallback"),
            default=True
        )

        if mode not in ALLOWED_MODES:
            raise ValueError(f"mode must be one of {sorted(ALLOWED_MODES)}")
        if backend not in ALLOWED_BACKENDS:
            raise ValueError(f"backend must be one of {sorted(ALLOWED_BACKENDS)}")
        if profile not in PRODUCT_PROFILE_PRIORS:
            raise ValueError(
                f"profile must be one of {sorted(PRODUCT_PROFILE_PRIORS)}"
            )
        if time_profile not in ALLOWED_TIME_PROFILES:
            raise ValueError(
                f"time_profile must be one of {sorted(ALLOWED_TIME_PROFILES)}"
            )
        if score_version is None:
            raise ValueError(
                f"score_version must be one of {sorted(VERSION_ALIASES)}"
            )

        mode_defaults = MODE_ACCESS_DEFAULTS[mode]
        max_time_min = float(
            request.args.get("max_time_min", mode_defaults["max_time_min"])
        )
        if not 1 <= max_time_min <= 180:
            raise ValueError("max_time_min must be between 1 and 180")
    except (KeyError, TypeError, ValueError) as exc:
        return _error(str(exc), 400)

    rankable, airport_excluded = _rankable_hotspots()
    if len(rankable) == 0:
        return jsonify({
            "message": "No rankable dining hotspots are available",
            "recommendations": [],
            "excluded_counts": {"airport": airport_excluded},
        })

    projected = rankable.to_crs("EPSG:32618")
    user_projected = gpd.GeoSeries(
        [Point(user_lon, user_lat)],
        crs="EPSG:4326"
    ).to_crs("EPSG:32618").iloc[0]
    rankable["distance_km"] = (
        projected.geometry.centroid.distance(user_projected) / 1000.0
    ).to_numpy()

    max_distance = payload.get("max_distance_km")
    if max_distance is not None:
        try:
            max_distance = float(max_distance)
            if max_distance <= 0:
                raise ValueError
        except (TypeError, ValueError):
            return _error("max_distance_km must be positive", 400)
        rankable = rankable[rankable["distance_km"] <= max_distance].copy()

    if len(rankable) == 0:
        return jsonify({
            "message": "No hotspots found within the requested distance",
            "recommendations": [],
            "excluded_counts": {"airport": airport_excluded},
        })

    destination_centroids = gpd.GeoSeries(
        rankable.to_crs("EPSG:32618").geometry.centroid,
        crs="EPSG:32618"
    ).to_crs("EPSG:4326")
    destinations = [
        (float(point.y), float(point.x))
        for point in destination_centroids
    ]
    graph_path = (
        f"data/networks/nyc_{mode}.graphml" if backend == "osmnx" else None
    )
    try:
        calculator = TravelTimeCalculator(
            mode=mode,
            backend=backend,
            graph_path=graph_path,
            allow_fallback=allow_fallback,
        )
        travel_times = calculator.matrix(
            [(user_lat, user_lon)],
            destinations
        )[0]
    except BackendUnavailableError as exc:
        return _error(str(exc), 503)
    except Exception:
        logger.exception("Travel-time computation failed")
        return _error("Travel-time computation failed", 500)

    rankable["travel_time_min"] = travel_times
    rankable = rankable[np.isfinite(rankable["travel_time_min"])].copy()
    rankable = rankable[rankable["travel_time_min"] <= max_time_min].copy()
    if len(rankable) == 0:
        return jsonify({
            "message": "No hotspots are reachable within the time threshold",
            "recommendations": [],
            "excluded_counts": {"airport": airport_excluded},
        })

    access_score = compute_access_score_half_life(
        rankable["travel_time_min"].to_numpy(),
        max_time_min=max_time_min,
        half_life_min=mode_defaults["half_life_min"],
    )
    rankable["accessibility_score"] = access_score

    score_components: Dict[str, np.ndarray] = {}
    effective_weights: Dict[str, float] = {}
    if score_version == "v3_product":
        all_components = _product_components(
            _rankable_hotspots()[0],
            time_profile
        )
        entropy_reference = None
        if len(all_components):
            from src.analysis.scoring import compute_entropy_weights
            entropy_reference = compute_entropy_weights(all_components)
        components = _product_components(rankable, time_profile)
        area_score, static_weights = compute_product_area_scores(
            components,
            profile_name=profile,
            entropy_weights=entropy_reference,
        )
        recommendation = compute_product_recommendation(
            area_score,
            access_score,
            profile_name=profile,
        )
        rankable["area_quality_score"] = area_score
        rankable["recommendation_score"] = recommendation
        access_weight = PRODUCT_PROFILE_PRIORS[profile]["access_weight"]
        effective_weights = {
            name: float(static_weights[idx] * (1.0 - access_weight))
            for idx, name in enumerate(PRODUCT_COMPONENTS)
        }
        effective_weights["access"] = float(access_weight)
        score_components = {
            name: components[:, idx]
            for idx, name in enumerate(PRODUCT_COMPONENTS)
        }
        for name, values in score_components.items():
            rankable[f"_component_{name}"] = values
    else:
        preferred_columns = (
            ["popularity_score_v2", "topsis_score", "popularity_score"]
            if score_version == "v2_entropy_legacy"
            else ["popularity_score", "composite_score", "topsis_score"]
        )
        column = next(
            (candidate for candidate in preferred_columns if candidate in rankable),
            None,
        )
        if column is None:
            return _error(
                f"No compatible {score_version} score column is available",
                503,
            )
        area_score = rankable[column].fillna(0.0).to_numpy(dtype=float)
        if column == "topsis_score" and np.nanmax(area_score) <= 1.0:
            area_score = area_score * 100.0
        rankable["area_quality_score"] = area_score
        rankable["recommendation_score"] = (
            0.6 * area_score + 0.4 * access_score
        )
        effective_weights = {"area_quality": 0.6, "access": 0.4}
        score_components = {"area_quality": area_score}
        rankable["_component_area_quality"] = area_score

    rankable = rankable.sort_values(
        ["recommendation_score", "area_quality_score", "accessibility_score"],
        ascending=[False, False, False],
        kind="mergesort",
    ).head(limit)

    backend_info = calculator.info()
    recommendations = []
    for rank, (idx, row) in enumerate(rankable.iterrows(), start=1):
        centroid = gpd.GeoSeries(
            [row.geometry],
            crs="EPSG:4326"
        ).to_crs("EPSG:32618").centroid.to_crs("EPSG:4326").iloc[0]
        component_payload = {
            key: float(row[f"_component_{key}"])
            for key in score_components
        }
        component_payload["access"] = float(row["accessibility_score"])
        recommendations.append({
            "rank": rank,
            "hotspot_id": str(row.get("hotspot_id", idx)),
            "recommendation_score": float(row["recommendation_score"]),
            "area_quality_score": float(row["area_quality_score"]),
            "accessibility_score": float(row["accessibility_score"]),
            "travel_time_min": float(row["travel_time_min"]),
            "distance_km": float(row["distance_km"]),
            "n_restaurants": int(row.get("n_restaurants", 0)),
            "n_taxi_dropoffs": int(row.get("n_taxi_dropoffs", 0)),
            "avg_rating": (
                float(row["avg_rating"])
                if pd.notna(row.get("avg_rating"))
                else None
            ),
            "data_confidence": float(
                row.get("data_confidence_v3", component_payload.get("confidence", 50))
            ),
            "score_components": component_payload,
            "score_weights": effective_weights,
            "is_estimate": bool(backend_info["is_estimate"]),
            "centroid_lat": float(centroid.y),
            "centroid_lon": float(centroid.x),
            "geometry": row.geometry.__geo_interface__,
        })

    return jsonify({
        "user_location": {"lat": user_lat, "lon": user_lon},
        "profile": profile,
        "time_profile": time_profile,
        "travel_mode": mode,
        "requested_backend": backend_info["requested_backend"],
        "effective_backend": backend_info["effective_backend"],
        "fallback_reason": backend_info["fallback_reason"],
        "score_version": score_version,
        "max_time_min": max_time_min,
        "excluded_counts": {"airport": airport_excluded},
        "total_found": len(recommendations),
        "recommendations": recommendations,
    })


@app.route("/api/stats", methods=["GET"])
def get_stats():
    if hotspots_data is None:
        return _error("No data loaded", 503)
    rankable, airport_excluded = _rankable_hotspots()
    score_column = (
        "area_quality_score_v3"
        if "area_quality_score_v3" in rankable.columns
        else "popularity_score"
    )
    return jsonify({
        "total_hotspots": int(len(rankable)),
        "excluded_airport_hotspots": airport_excluded,
        "total_restaurants": int(rankable["n_restaurants"].sum()),
        "total_taxi_dropoffs": int(rankable["n_taxi_dropoffs"].sum()),
        "avg_area_quality_score": float(rankable[score_column].mean()),
        "top_area_quality_score": float(rankable[score_column].max()),
        "scoring_default": "v3_product",
    })


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    load_hotspots()
    app.run(host="127.0.0.1", port=5000, debug=False)
