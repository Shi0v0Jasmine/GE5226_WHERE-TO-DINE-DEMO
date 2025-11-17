"""
Interactive Map Visualization of Results
=========================================

Purpose: Create interactive maps showing the complete pipeline results

Outputs:
    - maps/01_restaurants_clusters.html - Restaurant clustering visualization
    - maps/02_taxi_hotspots.html - Taxi hotspot visualization
    - maps/03_final_hotspots.html - Final dining hotspots (comprehensive)
    - maps/04_comparison.html - Side-by-side comparison

Author: Where to DINE Project
Date: 2025-11-09
"""

import geopandas as gpd
import pandas as pd
import folium
from folium import plugins
from pathlib import Path
import logging
import json
from typing import Dict, List

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_base_map(center_lat: float = 40.7128, center_lon: float = -74.0060, zoom: int = 11) -> folium.Map:
    """
    Create a base Folium map centered on NYC.

    Parameters:
    -----------
    center_lat : float
        Center latitude (default: NYC)
    center_lon : float
        Center longitude (default: NYC)
    zoom : int
        Initial zoom level (default: 11)

    Returns:
    --------
    folium.Map
        Base map object
    """
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=zoom,
        tiles='CartoDB positron',
        control_scale=True
    )

    # Add layer control
    folium.LayerControl(position='topright', collapsed=False).add_to(m)

    return m


def visualize_restaurant_clusters(
    restaurants_path: str,
    dining_zones_path: str,
    output_path: str
):
    """
    Visualize restaurant clusters and dining zones.

    Parameters:
    -----------
    restaurants_path : str
        Path to restaurants_clustered.geojson
    dining_zones_path : str
        Path to dining_zones.geojson
    output_path : str
        Output HTML file path
    """
    logger.info("Creating restaurant clusters visualization...")

    # Load data
    gdf_restaurants = gpd.read_file(restaurants_path)
    gdf_zones = gpd.read_file(dining_zones_path)

    # Create base map
    m = create_base_map()

    # Add dining zones (polygons)
    zone_layer = folium.FeatureGroup(name='Dining Zones', show=True)

    for idx, row in gdf_zones.iterrows():
        popup_html = f"""
        <b>Dining Zone {row.get('cluster_id', idx)}</b><br>
        Restaurants: {row.get('n_restaurants', 'N/A')}<br>
        Area: {row.get('area_sqkm', 0):.3f} km²<br>
        Avg Rating: {row.get('avg_rating', 'N/A'):.2f if pd.notna(row.get('avg_rating')) else 'N/A'}
        """

        folium.GeoJson(
            row.geometry,
            style_function=lambda x: {
                'fillColor': '#FFA500',
                'color': '#FF6600',
                'weight': 2,
                'fillOpacity': 0.3
            },
            tooltip=f"Zone {row.get('cluster_id', idx)}: {row.get('n_restaurants', 0)} restaurants",
            popup=folium.Popup(popup_html, max_width=250)
        ).add_to(zone_layer)

    zone_layer.add_to(m)

    # Add restaurant markers (sample)
    restaurant_layer = folium.FeatureGroup(name='Restaurants (Sample)', show=False)

    # Sample restaurants for visualization (max 1000 to avoid slowness)
    gdf_sample = gdf_restaurants.sample(n=min(1000, len(gdf_restaurants)), random_state=42)

    for idx, row in gdf_sample.iterrows():
        cluster_id = row.get('cluster', -1)
        color = 'red' if cluster_id == -1 else 'blue'

        popup_html = f"""
        <b>{row.get('name', 'Unknown')}</b><br>
        Rating: {row.get('rating', 'N/A')}<br>
        Cluster: {cluster_id}<br>
        Source: {row.get('source', 'N/A')}
        """

        folium.CircleMarker(
            location=[row.geometry.y, row.geometry.x],
            radius=3,
            color=color,
            fill=True,
            fillOpacity=0.6,
            popup=folium.Popup(popup_html, max_width=200)
        ).add_to(restaurant_layer)

    restaurant_layer.add_to(m)

    # Add title
    title_html = '''
    <div style="position: fixed;
                top: 10px; left: 50px; width: 400px; height: 60px;
                background-color: white; border:2px solid grey; z-index:9999;
                font-size:16px; padding: 10px">
    <b>Restaurant Clusters & Dining Zones</b><br>
    <span style="font-size:12px">Orange polygons: Dining zones | Blue: Clustered restaurants</span>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(title_html))

    # Save
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    m.save(output_path)
    logger.info(f"Saved: {output_path}")


def visualize_taxi_hotspots(
    taxi_hotspots_path: str,
    output_path: str
):
    """
    Visualize taxi hotspot areas.

    Parameters:
    -----------
    taxi_hotspots_path : str
        Path to taxi_hotspots.geojson
    output_path : str
        Output HTML file path
    """
    logger.info("Creating taxi hotspots visualization...")

    # Load data
    gdf_hotspots = gpd.read_file(taxi_hotspots_path)

    # Create base map
    m = create_base_map()

    # Add hotspots
    hotspot_layer = folium.FeatureGroup(name='Taxi Hotspots', show=True)

    for idx, row in gdf_hotspots.iterrows():
        popup_html = f"""
        <b>Taxi Hotspot {row.get('hotspot_id', idx)}</b><br>
        Dropoffs: {row.get('n_dropoffs', 'N/A'):,}<br>
        Weighted Dropoffs: {row.get('total_weight', 0):,.0f}<br>
        Area: {row.get('area_sqkm', 0):.3f} km²
        """

        folium.GeoJson(
            row.geometry,
            style_function=lambda x: {
                'fillColor': '#00FF00',
                'color': '#00AA00',
                'weight': 2,
                'fillOpacity': 0.4
            },
            tooltip=f"Hotspot {row.get('hotspot_id', idx)}: {row.get('n_dropoffs', 0):,} dropoffs",
            popup=folium.Popup(popup_html, max_width=250)
        ).add_to(hotspot_layer)

    hotspot_layer.add_to(m)

    # Add title
    title_html = '''
    <div style="position: fixed;
                top: 10px; left: 50px; width: 400px; height: 60px;
                background-color: white; border:2px solid grey; z-index:9999;
                font-size:16px; padding: 10px">
    <b>Taxi Dropoff Hotspots</b><br>
    <span style="font-size:12px">Green polygons: High taxi activity areas (dining hours)</span>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(title_html))

    # Save
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    m.save(output_path)
    logger.info(f"Saved: {output_path}")


def visualize_final_hotspots(
    final_hotspots_path: str,
    output_path: str
):
    """
    Visualize final dining hotspots with rankings.

    Parameters:
    -----------
    final_hotspots_path : str
        Path to final_hotspots.geojson
    output_path : str
        Output HTML file path
    """
    logger.info("Creating final hotspots visualization...")

    # Load data
    gdf_hotspots = gpd.read_file(final_hotspots_path)

    if len(gdf_hotspots) == 0:
        logger.warning("No final hotspots to visualize!")
        return

    # Create base map
    m = create_base_map()

    # Color scale based on popularity score
    max_score = gdf_hotspots['popularity_score'].max()
    min_score = gdf_hotspots['popularity_score'].min()

    def get_color(score: float) -> str:
        """Map score to color (red = high, yellow = low)"""
        if max_score == min_score:
            return '#FFA500'
        normalized = (score - min_score) / (max_score - min_score)
        if normalized > 0.66:
            return '#FF0000'  # Red - high
        elif normalized > 0.33:
            return '#FFA500'  # Orange - medium
        else:
            return '#FFFF00'  # Yellow - low

    # Add hotspots
    hotspot_layer = folium.FeatureGroup(name='Final Dining Hotspots', show=True)

    for idx, row in gdf_hotspots.iterrows():
        color = get_color(row['popularity_score'])

        popup_html = f"""
        <b>Hotspot Rank #{row.get('rank', 'N/A')}</b><br>
        <b>Popularity Score: {row.get('popularity_score', 0):.1f}/100</b><br>
        <hr>
        <b>Restaurants:</b> {row.get('n_restaurants', 0)}<br>
        <b>Taxi Dropoffs:</b> {row.get('n_taxi_dropoffs', 0):,}<br>
        <b>Avg Rating:</b> {row.get('avg_rating', 'N/A'):.2f if pd.notna(row.get('avg_rating')) else 'N/A'}<br>
        <b>Area:</b> {row.get('intersection_area_sqm', 0)/1000:.2f} × 1000 m²<br>
        <hr>
        <b>Restaurant Score:</b> {row.get('restaurant_score', 0):.1f}<br>
        <b>Taxi Score:</b> {row.get('taxi_score', 0):.1f}
        """

        folium.GeoJson(
            row.geometry,
            style_function=lambda x, color=color: {
                'fillColor': color,
                'color': '#000000',
                'weight': 2,
                'fillOpacity': 0.5
            },
            tooltip=f"Rank #{row.get('rank')}: Score {row.get('popularity_score', 0):.1f}",
            popup=folium.Popup(popup_html, max_width=300)
        ).add_to(hotspot_layer)

        # Add rank label at centroid
        centroid = row.geometry.centroid
        folium.Marker(
            location=[centroid.y, centroid.x],
            icon=folium.DivIcon(html=f'''
                <div style="font-size: 14pt; font-weight: bold; color: black;
                            text-shadow: 1px 1px white, -1px -1px white, 1px -1px white, -1px 1px white;">
                #{int(row.get('rank', 0))}
                </div>
            ''')
        ).add_to(hotspot_layer)

    hotspot_layer.add_to(m)

    # Add legend
    legend_html = '''
    <div style="position: fixed;
                bottom: 50px; right: 50px; width: 200px; height: 120px;
                background-color: white; border:2px solid grey; z-index:9999;
                font-size:14px; padding: 10px">
    <b>Hotspot Quality</b><br>
    <i class="fa fa-square" style="color:#FF0000"></i> High (Top 33%)<br>
    <i class="fa fa-square" style="color:#FFA500"></i> Medium (33-66%)<br>
    <i class="fa fa-square" style="color:#FFFF00"></i> Low (Bottom 33%)<br>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))

    # Add title
    title_html = f'''
    <div style="position: fixed;
                top: 10px; left: 50px; width: 500px; height: 80px;
                background-color: white; border:2px solid grey; z-index:9999;
                font-size:16px; padding: 10px">
    <b>Final Dining Hotspots - NYC</b><br>
    <span style="font-size:12px">
    Total Hotspots: {len(gdf_hotspots)} |
    Avg Score: {gdf_hotspots['popularity_score'].mean():.1f} |
    Top Score: {max_score:.1f}
    </span>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(title_html))

    # Save
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    m.save(output_path)
    logger.info(f"Saved: {output_path}")


def main():
    """
    Main execution function.
    """
    logger.info("="*60)
    logger.info("VISUALIZATION GENERATION")
    logger.info("="*60)

    # Define paths
    restaurants_path = "data/processed/restaurants_clustered.geojson"
    dining_zones_path = "data/processed/dining_zones.geojson"
    taxi_hotspots_path = "data/processed/taxi_hotspots.geojson"
    final_hotspots_path = "data/processed/final_hotspots.geojson"

    output_dir = "maps"

    # Check if files exist
    files_to_check = [
        ('restaurants_clustered.geojson', restaurants_path),
        ('dining_zones.geojson', dining_zones_path),
        ('taxi_hotspots.geojson', taxi_hotspots_path),
        ('final_hotspots.geojson', final_hotspots_path)
    ]

    missing_files = []
    for name, path in files_to_check:
        if not Path(path).exists():
            missing_files.append(name)

    if missing_files:
        logger.error("❌ Missing required files:")
        for file in missing_files:
            logger.error(f"  - {file}")
        logger.error("\nPlease run the data processing pipeline first (run_pipeline.py)")
        return

    # Generate visualizations
    logger.info("\n[1/3] Creating restaurant clusters visualization...")
    visualize_restaurant_clusters(
        restaurants_path,
        dining_zones_path,
        f"{output_dir}/01_restaurants_clusters.html"
    )

    logger.info("\n[2/3] Creating taxi hotspots visualization...")
    visualize_taxi_hotspots(
        taxi_hotspots_path,
        f"{output_dir}/02_taxi_hotspots.html"
    )

    logger.info("\n[3/3] Creating final hotspots visualization...")
    visualize_final_hotspots(
        final_hotspots_path,
        f"{output_dir}/03_final_hotspots.html"
    )

    logger.info("\n" + "="*60)
    logger.info("✅ VISUALIZATION COMPLETE")
    logger.info("="*60)
    logger.info(f"\nGenerated maps in '{output_dir}/':")
    logger.info("  1. 01_restaurants_clusters.html - Restaurant clustering")
    logger.info("  2. 02_taxi_hotspots.html - Taxi activity hotspots")
    logger.info("  3. 03_final_hotspots.html - Final dining recommendations")
    logger.info("\nOpen these HTML files in your web browser to view interactive maps.")
    logger.info("="*60 + "\n")


if __name__ == "__main__":
    main()
