import geopandas as gpd
import pandas as pd
from shapely.geometry import box

from src.experiments.run_controlled_resolution_experiment import (
    centroidize_same_trips,
)


def test_controlled_branches_retain_identical_trip_ids(tmp_path):
    zones = gpd.GeoDataFrame(
        {"LocationID": [1, 2]},
        geometry=[
            box(-74.02, 40.70, -74.00, 40.72),
            box(-74.00, 40.70, -73.98, 40.72),
        ],
        crs="EPSG:4326",
    )
    zone_path = tmp_path / "zones.geojson"
    zones.to_file(zone_path, driver="GeoJSON")
    exact = pd.DataFrame({
        "trip_id": ["a", "b", "outside"],
        "dropoff_lon": [-74.01, -73.99, -73.0],
        "dropoff_lat": [40.71, 40.71, 41.5],
        "dropoff_datetime": pd.to_datetime([
            "2014-01-06 12:00:00",
            "2014-01-06 13:00:00",
            "2014-01-06 14:00:00",
        ]),
        "weight": [1.0, 1.0, 1.0],
    })

    exact_branch, centroid_branch = centroidize_same_trips(
        exact,
        str(zone_path),
        chunk_size=2,
    )

    assert exact_branch["trip_id"].tolist() == ["a", "b"]
    assert exact_branch["trip_id"].equals(centroid_branch["trip_id"])
    assert not exact_branch["dropoff_lon"].equals(
        centroid_branch["dropoff_lon"]
    )
