import geopandas as gpd
from shapely.geometry import box

from src.analysis.airports import split_airport_hotspots, tag_airport_hotspots


def test_airport_hotspots_are_tagged_and_split(tmp_path):
    zones = gpd.GeoDataFrame(
        {"LocationID": [132, 138, 1]},
        geometry=[box(0, 0, 1, 1), box(2, 2, 3, 3), box(10, 10, 11, 11)],
        crs="EPSG:4326",
    )
    zone_path = tmp_path / "zones.geojson"
    zones.to_file(zone_path, driver="GeoJSON")
    hotspots = gpd.GeoDataFrame(
        {"hotspot_id": ["jfk", "dining"]},
        geometry=[box(0.1, 0.1, 0.9, 0.9), box(5, 5, 6, 6)],
        crs="EPSG:4326",
    )

    tagged = tag_airport_hotspots(hotspots, zones_path=zone_path)
    rankable, diagnostic = split_airport_hotspots(tagged)

    assert tagged.set_index("hotspot_id").loc["jfk", "is_airport"]
    assert list(rankable["hotspot_id"]) == ["dining"]
    assert list(diagnostic["hotspot_id"]) == ["jfk"]
