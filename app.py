"""
Where to DINE - Web Demo Application
=====================================

Simple Flask web application for interactive dining hotspot recommendations.

Features:
- Display final hotspots on interactive map
- Click anywhere to get nearby recommendations
- View hotspot details and rankings

Author: Where to DINE Project
Date: 2025-11-09
"""

from flask import Flask, render_template, request, jsonify
import geopandas as gpd
import pandas as pd
from pathlib import Path
from shapely.geometry import Point
import numpy as np
import json

app = Flask(__name__)

# Global variable to store hotspots data
hotspots_data = None


def load_hotspots():
    """Load final hotspots data on startup."""
    global hotspots_data

    hotspots_path = Path("data/processed/final_hotspots.geojson")

    if not hotspots_path.exists():
        print("❌ Error: final_hotspots.geojson not found!")
        print("Please run the pipeline first: python run_pipeline.py")
        return None

    hotspots_data = gpd.read_file(hotspots_path)
    print(f"✅ Loaded {len(hotspots_data)} hotspots")

    return hotspots_data


@app.route('/')
def index():
    """Render the main page."""
    if hotspots_data is None or len(hotspots_data) == 0:
        return """
        <html>
        <head><title>Where to DINE - Error</title></head>
        <body style="font-family: Arial; padding: 50px;">
            <h1>❌ No Data Available</h1>
            <p>Please run the data processing pipeline first:</p>
            <pre>python run_pipeline.py</pre>
            <p>Then restart this application.</p>
        </body>
        </html>
        """

    return render_template('index.html')


@app.route('/api/hotspots', methods=['GET'])
def get_all_hotspots():
    """
    Get all hotspots for initial map display.

    Returns:
    --------
    JSON: GeoJSON FeatureCollection of all hotspots
    """
    if hotspots_data is None:
        return jsonify({"error": "No data loaded"}), 500

    # Convert to GeoJSON
    geojson = json.loads(hotspots_data.to_json())

    return jsonify(geojson)


@app.route('/api/recommend', methods=['POST'])
def get_recommendations():
    """
    Get hotspot recommendations near a user-selected location.

    Input (JSON):
    -------------
    {
        "lat": 40.7589,
        "lon": -73.9851,
        "max_distance_km": 2.0,  # optional, default 2km
        "limit": 10              # optional, default 10
    }

    Returns:
    --------
    JSON: List of recommended hotspots with distances
    """
    if hotspots_data is None:
        return jsonify({"error": "No data loaded"}), 500

    # Parse request
    data = request.json
    user_lat = data.get('lat')
    user_lon = data.get('lon')
    max_distance_km = data.get('max_distance_km', 2.0)
    limit = data.get('limit', 10)

    if user_lat is None or user_lon is None:
        return jsonify({"error": "Missing lat/lon"}), 400

    # Create user location point
    user_point = Point(user_lon, user_lat)
    user_gdf = gpd.GeoDataFrame(
        [{'geometry': user_point}],
        crs="EPSG:4326"
    )

    # Reproject to meters for accurate distance calculation
    user_gdf_proj = user_gdf.to_crs("EPSG:2263")
    hotspots_proj = hotspots_data.to_crs("EPSG:2263")

    # Calculate distances from user location to each hotspot centroid
    user_point_proj = user_gdf_proj.geometry.iloc[0]

    distances = []
    for idx, hotspot in hotspots_proj.iterrows():
        # Distance to hotspot centroid
        centroid = hotspot.geometry.centroid
        distance_m = user_point_proj.distance(centroid)
        distance_km = distance_m / 1000.0

        distances.append({
            'index': idx,
            'distance_km': distance_km
        })

    # Create DataFrame with distances
    distances_df = pd.DataFrame(distances)

    # Merge with hotspots data
    hotspots_with_dist = hotspots_data.copy()
    hotspots_with_dist['distance_km'] = distances_df['distance_km'].values

    # Filter by max distance
    hotspots_nearby = hotspots_with_dist[
        hotspots_with_dist['distance_km'] <= max_distance_km
    ].copy()

    if len(hotspots_nearby) == 0:
        return jsonify({
            "message": f"No hotspots found within {max_distance_km} km",
            "recommendations": []
        })

    # Calculate recommendation score
    # Combined score: popularity (60%) + accessibility (40% based on inverse distance)
    max_dist = hotspots_nearby['distance_km'].max()
    if max_dist > 0:
        hotspots_nearby['accessibility_score'] = 100 * (1 - hotspots_nearby['distance_km'] / max_dist)
    else:
        hotspots_nearby['accessibility_score'] = 100

    hotspots_nearby['recommendation_score'] = (
        0.6 * hotspots_nearby['popularity_score'] +
        0.4 * hotspots_nearby['accessibility_score']
    )

    # Sort by recommendation score
    hotspots_nearby = hotspots_nearby.sort_values(
        'recommendation_score',
        ascending=False
    ).head(limit)

    # Prepare response
    recommendations = []
    for idx, row in hotspots_nearby.iterrows():
        centroid = row.geometry.centroid

        recommendations.append({
            'rank': int(row.get('rank', 0)),
            'popularity_score': float(row.get('popularity_score', 0)),
            'recommendation_score': float(row['recommendation_score']),
            'distance_km': float(row['distance_km']),
            'n_restaurants': int(row.get('n_restaurants', 0)),
            'n_taxi_dropoffs': int(row.get('n_taxi_dropoffs', 0)),
            'avg_rating': float(row.get('avg_rating', 0)) if pd.notna(row.get('avg_rating')) else None,
            'area_sqkm': float(row.get('intersection_area_sqm', 0) / 1_000_000),
            'centroid_lat': float(centroid.y),
            'centroid_lon': float(centroid.x),
            'geometry': row.geometry.__geo_interface__
        })

    return jsonify({
        "user_location": {
            "lat": user_lat,
            "lon": user_lon
        },
        "search_radius_km": max_distance_km,
        "total_found": len(recommendations),
        "recommendations": recommendations
    })


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """
    Get overall statistics about the hotspots dataset.

    Returns:
    --------
    JSON: Statistics summary
    """
    if hotspots_data is None:
        return jsonify({"error": "No data loaded"}), 500

    stats = {
        "total_hotspots": int(len(hotspots_data)),
        "total_restaurants": int(hotspots_data['n_restaurants'].sum()),
        "total_taxi_dropoffs": int(hotspots_data['n_taxi_dropoffs'].sum()),
        "avg_popularity_score": float(hotspots_data['popularity_score'].mean()),
        "top_hotspot_score": float(hotspots_data['popularity_score'].max()),
        "total_area_sqkm": float(hotspots_data['intersection_area_sqm'].sum() / 1_000_000)
    }

    return jsonify(stats)


if __name__ == '__main__':
    print("="*60)
    print("WHERE TO DINE - Web Demo")
    print("="*60)

    # Load data on startup
    if load_hotspots() is None:
        print("\n⚠️  Warning: Running without data")
        print("Please run the pipeline first: python run_pipeline.py\n")
    else:
        print(f"\n✅ Ready! Open http://127.0.0.1:5000 in your browser\n")

    # Run Flask app
    app.run(
        host='127.0.0.1',
        port=5000,
        debug=True
    )
