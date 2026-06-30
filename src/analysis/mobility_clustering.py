"""Scalable mobility-point clustering for the controlled resolution experiment."""

from __future__ import annotations

from typing import Dict, Tuple

import geopandas as gpd
import numpy as np
import pandas as pd
from hdbscan import HDBSCAN, approximate_predict
from pyproj import Transformer
from shapely.geometry import MultiPoint
from sklearn.metrics import davies_bouldin_score, silhouette_score


PROJECTED_CRS = "EPSG:32618"


def stratified_sample_indices(
    frame: pd.DataFrame,
    sample_cap: int = 300_000,
    random_state: int = 42,
) -> np.ndarray:
    """Sample proportionally by day while keeping the result deterministic."""
    if len(frame) <= sample_cap:
        return np.arange(len(frame))
    days = pd.to_datetime(frame["dropoff_datetime"]).dt.date
    rng = np.random.default_rng(random_state)
    selected = []
    for _, indices in pd.Series(np.arange(len(frame))).groupby(days).groups.items():
        group = np.asarray(list(indices), dtype=int)
        quota = max(1, int(round(sample_cap * len(group) / len(frame))))
        selected.extend(rng.choice(group, size=min(quota, len(group)), replace=False))
    selected = np.asarray(selected, dtype=int)
    if len(selected) > sample_cap:
        selected = rng.choice(selected, size=sample_cap, replace=False)
    elif len(selected) < sample_cap:
        remaining = np.setdiff1d(np.arange(len(frame)), selected, assume_unique=False)
        fill = rng.choice(
            remaining,
            size=min(sample_cap - len(selected), len(remaining)),
            replace=False,
        )
        selected = np.concatenate([selected, fill])
    return np.sort(selected)


def project_coordinates(
    lon: np.ndarray,
    lat: np.ndarray,
) -> np.ndarray:
    transformer = Transformer.from_crs(
        "EPSG:4326",
        PROJECTED_CRS,
        always_xy=True,
    )
    x, y = transformer.transform(lon, lat)
    return np.column_stack([x, y])


def cluster_dropoffs(
    frame: pd.DataFrame,
    min_cluster_size: int = 50,
    min_samples: int = 15,
    cluster_selection_epsilon: float = 250.0,
    sample_cap: int = 300_000,
    random_state: int = 42,
    prediction_batch_size: int = 250_000,
) -> Tuple[np.ndarray, HDBSCAN, Dict[str, float], np.ndarray]:
    """Fit HDBSCAN on a stratified sample and predict labels for all points."""
    coords = project_coordinates(
        frame["dropoff_lon"].to_numpy(dtype=float),
        frame["dropoff_lat"].to_numpy(dtype=float),
    )
    sample_indices = stratified_sample_indices(
        frame,
        sample_cap=sample_cap,
        random_state=random_state,
    )
    sample_coords = coords[sample_indices]
    model = HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        cluster_selection_epsilon=cluster_selection_epsilon,
        metric="euclidean",
        cluster_selection_method="eom",
        prediction_data=True,
    )
    sample_labels = model.fit_predict(sample_coords)

    labels = np.full(len(frame), -1, dtype=int)
    labels[sample_indices] = sample_labels
    unsampled = np.setdiff1d(
        np.arange(len(frame)),
        sample_indices,
        assume_unique=True,
    )
    for start in range(0, len(unsampled), prediction_batch_size):
        batch = unsampled[start:start + prediction_batch_size]
        predicted, _ = approximate_predict(model, coords[batch])
        labels[batch] = predicted

    metric_coords = sample_coords
    metric_labels = sample_labels
    valid = metric_labels != -1
    metric_coords = metric_coords[valid]
    metric_labels = metric_labels[valid]
    metric_sample_cap = 5_000
    if len(metric_coords) > metric_sample_cap:
        rng = np.random.default_rng(random_state)
        chosen = rng.choice(
            len(metric_coords),
            metric_sample_cap,
            replace=False,
        )
        metric_coords = metric_coords[chosen]
        metric_labels = metric_labels[chosen]

    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    metrics: Dict[str, float] = {
        "n_total": int(len(frame)),
        "n_training": int(len(sample_indices)),
        "n_clusters": int(n_clusters),
        "n_noise": int((labels == -1).sum()),
        "pct_clustered": float((labels != -1).mean() * 100.0),
        "n_metric_evaluation": int(len(metric_coords)),
        "silhouette_score": None,
        "davies_bouldin_index": None,
        "dbcv": None,
    }
    if len(set(metric_labels)) > 1:
        metrics["silhouette_score"] = float(
            silhouette_score(metric_coords, metric_labels)
        )
        metrics["davies_bouldin_index"] = float(
            davies_bouldin_score(metric_coords, metric_labels)
        )
        try:
            from hdbscan.validity import validity_index
            metrics["dbcv"] = float(validity_index(metric_coords, metric_labels))
        except Exception:
            metrics["dbcv"] = None
    return labels, model, metrics, coords


def hotspot_polygons(
    frame: pd.DataFrame,
    labels: np.ndarray,
    projected_coordinates: np.ndarray,
    resolution_label: str,
    buffer_m: float = 150.0,
    hull_sample_cap: int = 20_000,
    random_state: int = 42,
) -> gpd.GeoDataFrame:
    """Build compact hotspot polygons while preserving full-data counts."""
    rng = np.random.default_rng(random_state)
    rows = []
    dates = pd.to_datetime(frame["dropoff_datetime"]).dt.date
    weights = frame.get("weight", pd.Series(1.0, index=frame.index)).to_numpy()
    for cluster_id in sorted(set(labels)):
        if cluster_id == -1:
            continue
        indices = np.flatnonzero(labels == cluster_id)
        hull_indices = indices
        if len(indices) > hull_sample_cap:
            hull_indices = rng.choice(
                indices,
                size=hull_sample_cap,
                replace=False,
            )
        hull = MultiPoint(projected_coordinates[hull_indices]).convex_hull
        geometry = hull.buffer(buffer_m)
        area = float(geometry.area)
        perimeter = float(geometry.length)
        compactness = (
            float(4 * np.pi * area / (perimeter ** 2))
            if perimeter > 0 else 0.0
        )
        rows.append({
            "hotspot_id": int(cluster_id),
            "n_dropoffs": int(len(indices)),
            "total_weight": float(weights[indices].sum()),
            "active_days": int(pd.Series(dates.iloc[indices]).nunique()),
            "area_sqm": area,
            "area_sqkm": area / 1_000_000,
            "compactness": compactness,
            "data_resolution": resolution_label,
            "geometry": geometry,
        })
    return gpd.GeoDataFrame(rows, crs=PROJECTED_CRS).to_crs("EPSG:4326")
