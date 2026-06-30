"""H3, Gi*, multimodal consensus, and dining-district validation helpers."""

from __future__ import annotations

from itertools import combinations
from typing import Dict, Iterable, Optional

import geopandas as gpd
import h3
import numpy as np
import pandas as pd
from esda.getisord import G_Local
from libpysal.weights import W
from shapely.geometry import Point, Polygon


KNOWN_DINING_DISTRICTS = {
    "Chinatown": (40.7158, -73.9977, 0.45),
    "Koreatown": (40.7484, -73.9869, 0.35),
    "East Village": (40.7265, -73.9815, 0.65),
    "Little Italy": (40.7191, -73.9973, 0.35),
    "Williamsburg": (40.7081, -73.9571, 0.70),
    "Astoria": (40.7644, -73.9235, 0.75),
}


def add_h3_cell(
    frame: pd.DataFrame,
    lat_col: str,
    lon_col: str,
    resolution: int,
) -> pd.Series:
    return pd.Series([
        h3.latlng_to_cell(lat, lon, resolution)
        for lat, lon in zip(frame[lat_col], frame[lon_col])
    ], index=frame.index, dtype="string")


def h3_polygon(cell: str) -> Polygon:
    boundary = h3.cell_to_boundary(cell)
    return Polygon([(lon, lat) for lat, lon in boundary])


def aggregate_h3(
    frame: pd.DataFrame,
    lat_col: str,
    lon_col: str,
    resolution: int,
    weight_col: Optional[str] = None,
) -> gpd.GeoDataFrame:
    cells = add_h3_cell(frame, lat_col, lon_col, resolution)
    values = (
        frame[weight_col].to_numpy(dtype=float)
        if weight_col and weight_col in frame.columns
        else np.ones(len(frame), dtype=float)
    )
    grouped = pd.DataFrame({"h3_cell": cells, "value": values}).groupby(
        "h3_cell",
        as_index=False,
    ).agg(count=("value", "size"), weighted_count=("value", "sum"))
    return gpd.GeoDataFrame(
        grouped,
        geometry=[h3_polygon(cell) for cell in grouped["h3_cell"]],
        crs="EPSG:4326",
    )


def getis_ord_gi_star(
    cells: gpd.GeoDataFrame,
    value_col: str = "weighted_count",
    permutations: int = 99,
) -> gpd.GeoDataFrame:
    result = cells.copy()
    observed_ids = set(result["h3_cell"])
    analysis_ids = set(observed_ids)
    for cell in observed_ids:
        analysis_ids.update(h3.grid_disk(cell, 1))
    missing_ids = sorted(analysis_ids - observed_ids)
    if missing_ids:
        missing = gpd.GeoDataFrame(
            {
                "h3_cell": missing_ids,
                "count": 0,
                value_col: 0.0,
                "observed": False,
            },
            geometry=[h3_polygon(cell) for cell in missing_ids],
            crs=cells.crs,
        )
        result["observed"] = True
        result = pd.concat([result, missing], ignore_index=True)
        result = gpd.GeoDataFrame(result, geometry="geometry", crs=cells.crs)
    else:
        result["observed"] = True

    ids = list(result["h3_cell"])
    id_set = set(ids)
    neighbors = {
        cell: [
            neighbor for neighbor in h3.grid_disk(cell, 1)
            if neighbor != cell and neighbor in id_set
        ]
        for cell in ids
    }
    weights = W(neighbors, id_order=ids, silence_warnings=True)
    statistic = G_Local(
        result[value_col].to_numpy(dtype=float),
        weights,
        transform="B",
        permutations=permutations,
        star=True,
        seed=42,
    )
    result["gi_z"] = np.nan_to_num(statistic.Zs, nan=0.0)
    result["gi_p_sim"] = np.nan_to_num(statistic.p_sim, nan=1.0)
    result["gi_hotspot_95"] = (
        (result["gi_z"] > 1.96) & (result["gi_p_sim"] < 0.05)
    )
    return result


def daily_district_hit_stability(
    frame: pd.DataFrame,
    resolution: int = 10,
    top_n: int = 20,
) -> Dict[str, object]:
    """Report daily top-cell hits for each known dining district."""
    working = frame.copy()
    working["day"] = pd.to_datetime(
        working["dropoff_datetime"]
    ).dt.date.astype(str)
    working["h3_cell"] = add_h3_cell(
        working,
        "dropoff_lat",
        "dropoff_lon",
        resolution,
    )
    daily = (
        working.groupby(["day", "h3_cell"])["weight"]
        .sum()
        .reset_index()
    )
    rows = []
    for day, group in daily.groupby("day"):
        top_cells = group.nlargest(top_n, "weight")["h3_cell"]
        centers = gpd.GeoSeries(
            [
                Point(
                    h3.cell_to_latlng(cell)[1],
                    h3.cell_to_latlng(cell)[0],
                )
                for cell in top_cells
            ],
            crs="EPSG:4326",
        ).to_crs("EPSG:32618")
        for name, (lat, lon, radius_km) in KNOWN_DINING_DISTRICTS.items():
            district = gpd.GeoSeries(
                [Point(lon, lat)],
                crs="EPSG:4326",
            ).to_crs("EPSG:32618").iloc[0]
            nearest = float(centers.distance(district).min() / 1000.0)
            rows.append({
                "day": day,
                "district": name,
                "hit": nearest <= radius_km,
                "nearest_top_cell_km": nearest,
            })
    summary = {}
    for name in KNOWN_DINING_DISTRICTS:
        district_rows = [row for row in rows if row["district"] == name]
        summary[name] = {
            "hit_days": int(sum(row["hit"] for row in district_rows)),
            "active_days": len(district_rows),
            "hit_rate": float(np.mean([row["hit"] for row in district_rows])),
        }
    return {"top_n": top_n, "daily": rows, "district_summary": summary}


def percentile(values: pd.Series) -> pd.Series:
    return values.rank(method="average", pct=True).fillna(0.0)


def taxi_bike_consensus(
    taxi: pd.DataFrame,
    bike: pd.DataFrame,
    resolution: int = 10,
) -> gpd.GeoDataFrame:
    taxi_cells = aggregate_h3(
        taxi,
        "dropoff_lat",
        "dropoff_lon",
        resolution,
        "weight",
    ).rename(columns={"weighted_count": "taxi_weighted_count"})
    bike_cells = aggregate_h3(
        bike,
        "end_lat",
        "end_lon",
        resolution,
    ).rename(columns={"weighted_count": "bike_arrivals"})

    joined = taxi_cells[
        ["h3_cell", "taxi_weighted_count", "geometry"]
    ].merge(
        bike_cells[["h3_cell", "bike_arrivals"]],
        on="h3_cell",
        how="left",
    )
    joined["bike_arrivals"] = joined["bike_arrivals"].fillna(0.0)

    station_points = gpd.GeoSeries(
        gpd.points_from_xy(bike["end_lon"], bike["end_lat"]),
        crs="EPSG:4326",
    ).to_crs("EPSG:32618")
    service_area = station_points.union_all().convex_hull.buffer(1_000)
    centers = gpd.GeoSeries(
        [
            Point(
                h3.cell_to_latlng(cell)[1],
                h3.cell_to_latlng(cell)[0],
            )
            for cell in joined["h3_cell"]
        ],
        crs="EPSG:4326",
    ).to_crs("EPSG:32618")
    joined["bike_coverage"] = centers.within(service_area).to_numpy()
    joined["taxi_percentile"] = percentile(joined["taxi_weighted_count"])
    joined["bike_percentile"] = percentile(joined["bike_arrivals"])
    joined["mobility_consensus"] = np.where(
        joined["bike_coverage"],
        np.sqrt(
            joined["taxi_percentile"] * joined["bike_percentile"]
        ) * 100.0,
        np.nan,
    )
    return gpd.GeoDataFrame(joined, geometry="geometry", crs="EPSG:4326")


def district_validation(
    hotspots: gpd.GeoDataFrame,
    score_col: str,
    top_values: Iterable[int] = (10, 20),
) -> Dict[str, object]:
    projected = hotspots.to_crs("EPSG:32618").sort_values(
        score_col,
        ascending=False,
    )
    district_rows = []
    for name, (lat, lon, radius_km) in KNOWN_DINING_DISTRICTS.items():
        center = gpd.GeoSeries(
            [Point(lon, lat)],
            crs="EPSG:4326",
        ).to_crs("EPSG:32618").iloc[0]
        distances = projected.geometry.distance(center) / 1000.0
        row = {
            "name": name,
            "radius_km": radius_km,
            "nearest_hotspot_km": float(distances.min()),
        }
        for top_n in top_values:
            row[f"covered_at_{top_n}"] = bool(
                (distances.iloc[:top_n] <= radius_km).any()
            )
        district_rows.append(row)
    return {
        "districts": district_rows,
        **{
            f"coverage_at_{top_n}": float(
                np.mean([row[f"covered_at_{top_n}"] for row in district_rows])
            )
            for top_n in top_values
        },
    }


def daily_top_cell_stability(
    frame: pd.DataFrame,
    resolution: int = 10,
    top_n: int = 20,
) -> Dict[str, object]:
    working = frame.copy()
    working["day"] = pd.to_datetime(working["dropoff_datetime"]).dt.date.astype(str)
    working["h3_cell"] = add_h3_cell(
        working,
        "dropoff_lat",
        "dropoff_lon",
        resolution,
    )
    daily = (
        working.groupby(["day", "h3_cell"])["weight"]
        .sum()
        .reset_index()
    )
    top = {
        day: set(group.nlargest(top_n, "weight")["h3_cell"])
        for day, group in daily.groupby("day")
    }
    jaccard = []
    for day_a, day_b in combinations(sorted(top), 2):
        union = top[day_a] | top[day_b]
        value = len(top[day_a] & top[day_b]) / len(union) if union else 1.0
        jaccard.append({"day_a": day_a, "day_b": day_b, "jaccard": value})
    return {
        "top_n": top_n,
        "days": sorted(top),
        "pairwise_jaccard": jaccard,
        "mean_jaccard": float(np.mean([item["jaccard"] for item in jaccard]))
        if jaccard else None,
    }
