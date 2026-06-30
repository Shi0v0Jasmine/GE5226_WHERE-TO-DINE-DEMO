"""Airport diagnostics and filtering for dining hotspot rankings."""

from pathlib import Path
from typing import Iterable, Tuple

import geopandas as gpd
import numpy as np


NYC_AIRPORT_ZONE_IDS = (132, 138)  # JFK, LaGuardia


def load_airport_zones(
    zones_path: str = "data/external/boundaries/taxi_zones.shp",
    zone_ids: Iterable[int] = NYC_AIRPORT_ZONE_IDS,
) -> gpd.GeoDataFrame:
    """Load the official TLC polygons used to tag airport-related hotspots."""
    path = Path(zones_path)
    if not path.exists():
        raise FileNotFoundError(f"Taxi zone shapefile not found: {zones_path}")
    zones = gpd.read_file(path)
    if "LocationID" not in zones.columns:
        raise ValueError("Taxi zone shapefile is missing LocationID")
    return zones[zones["LocationID"].isin(list(zone_ids))].copy()


def tag_airport_hotspots(
    hotspots: gpd.GeoDataFrame,
    zones_path: str = "data/external/boundaries/taxi_zones.shp",
    overlap_threshold: float = 0.25,
) -> gpd.GeoDataFrame:
    """
    Tag hotspots whose centroid is in, or whose area substantially overlaps, JFK/LGA.

    The rows remain available for research diagnostics. Product ranking code should
    filter on ``is_airport``.
    """
    result = hotspots.copy()
    if len(result) == 0:
        result["is_airport"] = []
        result["airport_overlap_ratio"] = []
        result["airport_zone_id"] = []
        return result

    airport_zones = load_airport_zones(zones_path).to_crs("EPSG:32618")
    projected = result.to_crs("EPSG:32618")
    airport_union = airport_zones.geometry.union_all()
    areas = projected.geometry.area.replace(0, np.nan)
    overlap = projected.geometry.intersection(airport_union).area / areas
    centroid_inside = projected.geometry.centroid.within(airport_union)

    result["airport_overlap_ratio"] = overlap.fillna(0.0).to_numpy()
    result["is_airport"] = (
        centroid_inside.to_numpy()
        | (result["airport_overlap_ratio"].to_numpy() >= overlap_threshold)
    )

    zone_ids = []
    for centroid in projected.geometry.centroid:
        matches = airport_zones[airport_zones.geometry.contains(centroid)]
        zone_ids.append(
            int(matches.iloc[0]["LocationID"]) if len(matches) else None
        )
    result["airport_zone_id"] = zone_ids
    return result


def split_airport_hotspots(
    hotspots: gpd.GeoDataFrame,
) -> Tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Return rankable dining hotspots and excluded airport diagnostics."""
    if "is_airport" not in hotspots.columns:
        raise ValueError("Hotspots must be tagged with tag_airport_hotspots first")
    airport = hotspots[hotspots["is_airport"].fillna(False)].copy()
    rankable = hotspots[~hotspots["is_airport"].fillna(False)].copy()
    return rankable, airport
