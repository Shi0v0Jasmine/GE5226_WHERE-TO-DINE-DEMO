"""Streamlit research dashboard for precomputed Where to DINE artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import folium
import geopandas as gpd
import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_folium import st_folium


st.set_page_config(
    page_title="Where to DINE Research",
    layout="wide",
)

CONTROLLED = Path("data/processed/controlled_2014")
PROCESSED = Path("data/processed")


@st.cache_data
def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


@st.cache_data
def read_geojson(path: Path):
    return gpd.read_file(path) if path.exists() else None


def artifact_notice(path: Path):
    st.info(f"Artifact not found: `{path}`")


def hotspot_map(frames, colors):
    map_object = folium.Map(
        location=[40.7128, -74.0060],
        zoom_start=10,
        tiles="CartoDB positron",
    )
    for (name, frame), color in zip(frames, colors):
        if frame is None or len(frame) == 0:
            continue
        folium.GeoJson(
            frame,
            name=name,
            style_function=lambda _, color=color: {
                "color": color,
                "weight": 2,
                "fillOpacity": 0.18,
            },
            tooltip=folium.GeoJsonTooltip(
                fields=[
                    column for column in [
                        "hotspot_id",
                        "n_dropoffs",
                        "area_sqkm",
                        "compactness",
                    ]
                    if column in frame.columns
                ]
            ),
        ).add_to(map_object)
    folium.LayerControl(collapsed=False).add_to(map_object)
    return map_object


st.title("Where to DINE Research Console")
st.caption("Controlled spatial-resolution, scoring, stability, and multimodal diagnostics")

tabs = st.tabs([
    "Exact vs centroid",
    "Clustering and Gi*",
    "Scoring",
    "Daily stability",
    "Airport and bike",
])

metrics = read_json(CONTROLLED / "controlled_resolution_metrics.json")

with tabs[0]:
    if metrics is None:
        artifact_notice(CONTROLLED / "controlled_resolution_metrics.json")
    else:
        left, right, third = st.columns(3)
        left.metric("Trips per branch", f"{metrics['trip_count_per_branch']:,}")
        right.metric("Active days", metrics["active_days"])
        coordinate = metrics["coordinate"]
        centroid = metrics["centroidized"]
        third.metric(
            "POI IoU lift",
            f"{coordinate['poi_iou'] - centroid['poi_iou']:+.3f}",
        )
        comparison = pd.DataFrame([
            {
                "variant": "Coordinate",
                "hotspots": coordinate["n_clusters"],
                "mean area km2": coordinate["mean_area_sqkm"],
                "compactness": coordinate["mean_compactness"],
                "POI IoU": coordinate["poi_iou"],
                "DBCV": coordinate.get("dbcv"),
            },
            {
                "variant": "Centroidized",
                "hotspots": centroid["n_clusters"],
                "mean area km2": centroid["mean_area_sqkm"],
                "compactness": centroid["mean_compactness"],
                "POI IoU": centroid["poi_iou"],
                "DBCV": centroid.get("dbcv"),
            },
        ])
        st.dataframe(comparison, width="stretch", hide_index=True)

    exact = read_geojson(CONTROLLED / "coordinate_hotspots.geojson")
    centroidized = read_geojson(CONTROLLED / "centroidized_hotspots.geojson")
    if exact is not None or centroidized is not None:
        st_folium(
            hotspot_map(
                [("Coordinate", exact), ("Centroidized", centroidized)],
                ["#187d70", "#dc6a4b"],
            ),
            use_container_width=True,
            height=560,
            returned_objects=[],
        )

with tabs[1]:
    branch_col, resolution_col = st.columns(2)
    with branch_col:
        branch = st.segmented_control(
            "Spatial branch",
            options=["coordinate", "centroidized"],
            default="coordinate",
        )
    with resolution_col:
        resolution = st.segmented_control(
            "H3 resolution",
            options=[9, 10, 11],
            default=10,
        )
    gi_path = CONTROLLED / f"{branch}_gi_star_h3_r{resolution}.geojson"
    gi = read_geojson(gi_path)
    if gi is None:
        artifact_notice(gi_path)
    else:
        significant = gi[gi["gi_hotspot_95"]].copy()
        col1, col2 = st.columns(2)
        observed = int(gi["observed"].sum()) if "observed" in gi else len(gi)
        col1.metric("Observed H3 cells", f"{observed:,}")
        col2.metric("Gi* hotspots (95%)", f"{len(significant):,}")
        map_object = folium.Map(
            location=[40.7128, -74.0060],
            zoom_start=10,
            tiles="CartoDB positron",
        )
        folium.GeoJson(
            significant,
            style_function=lambda _: {
                "color": "#a6422d",
                "weight": 1,
                "fillColor": "#dc6a4b",
                "fillOpacity": 0.55,
            },
            tooltip=folium.GeoJsonTooltip(
                fields=["weighted_count", "gi_z", "gi_p_sim"],
            ),
        ).add_to(map_object)
        st_folium(
            map_object,
            use_container_width=True,
            height=560,
            returned_objects=[],
        )

with tabs[2]:
    final_path = (
        PROCESSED / "final_hotspots_v3.geojson"
        if (PROCESSED / "final_hotspots_v3.geojson").exists()
        else PROCESSED / "final_hotspots.geojson"
    )
    final = read_geojson(final_path)
    if final is None:
        artifact_notice(final_path)
    else:
        score_columns = [
            column for column in [
                "popularity_score",
                "popularity_score_v2",
                "area_quality_score_v3",
            ]
            if column in final.columns
        ]
        tidy = final[score_columns].copy()
        tidy["hotspot"] = range(1, len(tidy) + 1)
        tidy = tidy.melt(
            id_vars="hotspot",
            var_name="version",
            value_name="score",
        )
        chart = px.histogram(
            tidy,
            x="score",
            color="version",
            barmode="overlay",
            opacity=0.65,
            nbins=20,
        )
        chart.update_layout(
            margin=dict(l=0, r=0, t=20, b=0),
            legend_title_text="",
        )
        st.plotly_chart(chart, width="stretch")
        display_columns = [
            column for column in [
                "rank_v3",
                "area_quality_score_v3",
                "demand_score_v3",
                "poi_score_v3",
                "time_fit_score_v3",
                "data_confidence_v3",
                "n_restaurants",
                "n_taxi_dropoffs",
            ]
            if column in final.columns
        ]
        if display_columns:
            st.dataframe(
                final.sort_values(
                    display_columns[0],
                    ascending=display_columns[0] != "rank_v3",
                )[display_columns].head(25),
                width="stretch",
                hide_index=True,
            )

with tabs[3]:
    if metrics is None:
        artifact_notice(CONTROLLED / "controlled_resolution_metrics.json")
    else:
        variant = st.segmented_control(
            "Spatial branch",
            options=["coordinate", "centroidized"],
            default="coordinate",
            key="stability_branch",
        )
        stability = metrics["daily_stability"][variant]["top_cell_jaccard"]
        mean_jaccard = stability["mean_jaccard"]
        st.metric(
            "Mean top-cell Jaccard",
            f"{mean_jaccard:.3f}" if mean_jaccard is not None else "n/a",
        )
        pairs = pd.DataFrame(stability["pairwise_jaccard"])
        if len(pairs):
            chart = px.bar(
                pairs,
                x=pairs.apply(lambda row: f"{row.day_a} / {row.day_b}", axis=1),
                y="jaccard",
                labels={"x": "Day pair", "jaccard": "Top-cell Jaccard"},
            )
            chart.update_layout(margin=dict(l=0, r=0, t=20, b=0))
            st.plotly_chart(chart, width="stretch")

        district_rows = []
        for variant, result in metrics["known_dining_districts"].items():
            for district in result["districts"]:
                district_rows.append({"variant": variant, **district})
        st.dataframe(
            pd.DataFrame(district_rows),
            width="stretch",
            hide_index=True,
        )
        hit_summary = metrics["daily_stability"][variant][
            "known_district_hits"
        ]["district_summary"]
        st.dataframe(
            pd.DataFrame([
                {"district": name, **values}
                for name, values in hit_summary.items()
            ]),
            width="stretch",
            hide_index=True,
        )

with tabs[4]:
    airport = read_geojson(PROCESSED / "airport_hotspots_diagnostics.geojson")
    consensus = read_geojson(CONTROLLED / "taxi_bike_consensus_h3_r10.geojson")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Airport diagnostics")
        if airport is None:
            artifact_notice(PROCESSED / "airport_hotspots_diagnostics.geojson")
        else:
            st.metric("Excluded airport hotspots", len(airport))
            st.dataframe(
                airport[[
                    column for column in [
                        "airport_zone_id",
                        "airport_overlap_ratio",
                        "n_taxi_dropoffs",
                    ]
                    if column in airport.columns
                ]],
                width="stretch",
                hide_index=True,
            )
    with col2:
        st.subheader("Taxi-bike consensus")
        if consensus is None:
            artifact_notice(CONTROLLED / "taxi_bike_consensus_h3_r10.geojson")
        else:
            covered = consensus[consensus["bike_coverage"]]
            st.metric("Bike-covered H3 cells", len(covered))
            st.metric(
                "Mean consensus",
                f"{covered['mobility_consensus'].mean():.1f}",
            )
