"""Run the same-trip 2014 coordinate vs zone-centroid experiment."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Dict, Tuple

import geopandas as gpd
import numpy as np
import pandas as pd

from src.analysis.airports import tag_airport_hotspots
from src.analysis.mobility_clustering import (
    cluster_dropoffs,
    hotspot_polygons,
)
from src.analysis.spatial_validation import (
    aggregate_h3,
    daily_district_hit_stability,
    daily_top_cell_stability,
    district_validation,
    getis_ord_gi_star,
    taxi_bike_consensus,
)
from src.utils.config_loader import load_config


logger = logging.getLogger(__name__)


def centroidize_same_trips(
    exact: pd.DataFrame,
    zones_path: str,
    chunk_size: int = 250_000,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Replace exact coordinates with TLC-zone centroids, retaining matching IDs."""
    zones = gpd.read_file(zones_path).to_crs("EPSG:4326")
    zones_projected = zones.to_crs("EPSG:32618")
    centroids = gpd.GeoSeries(
        zones_projected.geometry.centroid,
        crs="EPSG:32618",
    ).to_crs("EPSG:4326")
    zones = zones[["LocationID", "geometry"]].copy()
    zones["zone_lon"] = centroids.x.to_numpy()
    zones["zone_lat"] = centroids.y.to_numpy()

    chunks = []
    for start in range(0, len(exact), chunk_size):
        part = exact.iloc[start:start + chunk_size].copy()
        points = gpd.GeoDataFrame(
            part,
            geometry=gpd.points_from_xy(part["dropoff_lon"], part["dropoff_lat"]),
            crs="EPSG:4326",
        )
        joined = gpd.sjoin(
            points,
            zones,
            predicate="within",
            how="inner",
        ).drop(columns=["geometry", "index_right"])
        joined["dropoff_lon"] = joined["zone_lon"]
        joined["dropoff_lat"] = joined["zone_lat"]
        chunks.append(joined.drop(columns=["zone_lon", "zone_lat"]))

    centroidized = pd.concat(chunks, ignore_index=True).drop_duplicates("trip_id")
    matched_ids = set(centroidized["trip_id"])
    exact_matched = exact[exact["trip_id"].isin(matched_ids)].copy()
    exact_matched = exact_matched.sort_values("trip_id").reset_index(drop=True)
    centroidized = centroidized.sort_values("trip_id").reset_index(drop=True)
    if not exact_matched["trip_id"].equals(centroidized["trip_id"]):
        raise AssertionError("Coordinate and centroid branches do not share trip IDs")
    return exact_matched, centroidized


def poi_iou(
    hotspots: gpd.GeoDataFrame,
    dining_zones: gpd.GeoDataFrame,
) -> float:
    if len(hotspots) == 0 or len(dining_zones) == 0:
        return 0.0
    hotspot_union = hotspots.to_crs("EPSG:32618").geometry.union_all()
    dining_union = dining_zones.to_crs("EPSG:32618").geometry.union_all()
    union = hotspot_union.union(dining_union).area
    return float(hotspot_union.intersection(dining_union).area / union) if union else 0.0


def cluster_variant(
    frame: pd.DataFrame,
    name: str,
    config: dict,
    output_dir: Path,
) -> Tuple[gpd.GeoDataFrame, Dict[str, object]]:
    params = config["clustering"]["taxi"]
    labels, _, metrics, coords = cluster_dropoffs(
        frame,
        min_cluster_size=int(params["min_cluster_size"]),
        min_samples=int(params["min_samples"]),
        cluster_selection_epsilon=float(params["cluster_selection_epsilon"]),
        sample_cap=300_000,
        random_state=42,
    )
    hotspots = hotspot_polygons(
        frame,
        labels,
        coords,
        resolution_label=name,
        buffer_m=float(config["clustering"]["taxi_hotspot_buffer"]),
    )
    hotspots = tag_airport_hotspots(hotspots)
    output_dir.mkdir(parents=True, exist_ok=True)
    hotspots.to_file(
        output_dir / f"{name}_hotspots.geojson",
        driver="GeoJSON",
    )
    metrics["mean_area_sqkm"] = float(hotspots["area_sqkm"].mean())
    metrics["mean_compactness"] = float(hotspots["compactness"].mean())
    metrics["airport_hotspots"] = int(hotspots["is_airport"].sum())
    return hotspots, metrics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="data/interim/taxi_dropoffs_2014_weighted.parquet",
    )
    parser.add_argument(
        "--bike-input",
        default=(
            "data/raw/citibike_2014/"
            "citibike_arrivals_2014-01-06_2014-01-13.parquet"
        ),
    )
    parser.add_argument(
        "--zones",
        default="data/external/boundaries/taxi_zones.shp",
    )
    parser.add_argument(
        "--dining-zones",
        default="data/processed/dining_zones.geojson",
    )
    parser.add_argument(
        "--output-dir",
        default="data/processed/controlled_2014",
    )
    parser.add_argument(
        "--interim-dir",
        default="data/interim/controlled_2014",
    )
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    args = parse_args()
    exact = pd.read_parquet(args.input)
    if exact["dropoff_datetime"].dt.date.nunique() != 7:
        raise ValueError("Controlled experiment requires exactly seven active days")
    exact, centroidized = centroidize_same_trips(exact, args.zones)

    interim = Path(args.interim_dir)
    interim.mkdir(parents=True, exist_ok=True)
    exact.to_parquet(interim / "coordinate.parquet", index=False)
    centroidized.to_parquet(interim / "centroidized.parquet", index=False)

    config = load_config()
    output = Path(args.output_dir)
    coordinate_hotspots, coordinate_metrics = cluster_variant(
        exact,
        "coordinate",
        config,
        output,
    )
    centroid_hotspots, centroid_metrics = cluster_variant(
        centroidized,
        "centroidized",
        config,
        output,
    )
    dining = gpd.read_file(args.dining_zones)
    coordinate_metrics["poi_iou"] = poi_iou(coordinate_hotspots, dining)
    centroid_metrics["poi_iou"] = poi_iou(centroid_hotspots, dining)

    validation = {
        "coordinate": district_validation(
            coordinate_hotspots[
                ~coordinate_hotspots["is_airport"].fillna(False)
            ],
            "total_weight",
        ),
        "centroidized": district_validation(
            centroid_hotspots[
                ~centroid_hotspots["is_airport"].fillna(False)
            ],
            "total_weight",
        ),
    }
    stability = {
        "coordinate": {
            "top_cell_jaccard": daily_top_cell_stability(
                exact, resolution=10, top_n=20
            ),
            "known_district_hits": daily_district_hit_stability(
                exact, resolution=10, top_n=20
            ),
        },
        "centroidized": {
            "top_cell_jaccard": daily_top_cell_stability(
                centroidized, resolution=10, top_n=20
            ),
            "known_district_hits": daily_district_hit_stability(
                centroidized, resolution=10, top_n=20
            ),
        },
    }

    h3_summary = {"coordinate": {}, "centroidized": {}}
    for branch_name, branch_frame in (
        ("coordinate", exact),
        ("centroidized", centroidized),
    ):
        for resolution in (9, 10, 11):
            grid = aggregate_h3(
                branch_frame,
                "dropoff_lat",
                "dropoff_lon",
                resolution,
                "weight",
            )
            gi = getis_ord_gi_star(grid)
            gi.to_file(
                output / f"{branch_name}_gi_star_h3_r{resolution}.geojson",
                driver="GeoJSON",
            )
            h3_summary[branch_name][str(resolution)] = {
                "observed_cells": int(gi["observed"].sum()),
                "analysis_cells": int(len(gi)),
                "significant_hotspots_95": int(gi["gi_hotspot_95"].sum()),
            }

    consensus_summary = None
    bike_path = Path(args.bike_input)
    if bike_path.exists():
        bike = pd.read_parquet(bike_path)
        consensus = taxi_bike_consensus(exact, bike, resolution=10)
        consensus.to_file(
            output / "taxi_bike_consensus_h3_r10.geojson",
            driver="GeoJSON",
        )
        covered = consensus[consensus["bike_coverage"]]
        consensus_summary = {
            "bike_arrivals": int(len(bike)),
            "covered_cells": int(len(covered)),
            "mean_consensus": float(covered["mobility_consensus"].mean()),
        }

    report = {
        "design": "same 2014 trips: exact coordinates vs TLC-zone centroids",
        "trip_count_per_branch": int(len(exact)),
        "active_days": int(exact["dropoff_datetime"].dt.date.nunique()),
        "coordinate": coordinate_metrics,
        "centroidized": centroid_metrics,
        "branch_differences": {
            key: float(coordinate_metrics[key] - centroid_metrics[key])
            for key in (
                "n_clusters",
                "mean_area_sqkm",
                "mean_compactness",
                "poi_iou",
                "dbcv",
            )
            if key in coordinate_metrics and key in centroid_metrics
        },
        "known_dining_districts": validation,
        "daily_stability": stability,
        "h3_gi_star": h3_summary,
        "taxi_bike_consensus": consensus_summary,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "controlled_resolution_metrics.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )
    logger.info("Controlled experiment complete: %s", output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
