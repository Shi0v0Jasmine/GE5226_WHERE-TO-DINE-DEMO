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

    # Calculate recommendation score using unified TravelTimeCalculator
    # Backend: proxy (default), osmnx (if graph available), google (if API key)
    access_method = request.args.get('access_method', 'proxy')  # proxy | osmnx | google
    user_profile = request.args.get('profile', 'balanced')
    time_profile = request.args.get('time_profile', 'any')  # any | lunch | dinner | late_night
    version = request.args.get('version', 'v2')  # v1 | v2
    travel_mode = request.args.get('mode', 'transit')  # walk | bike | drive | transit

    try:
        from src.travel_time import TravelTimeCalculator
        from src.analysis.scoring import compute_access_score_decay, get_profile_weights

        # Initialize travel time calculator with selected backend
        # Default: proxy (no dependencies). Auto-fallback if osmnx/google unavailable.
        tt = TravelTimeCalculator(
            mode=travel_mode,
            backend=access_method,
            graph_path=f"data/networks/nyc_{travel_mode}.graphml" if access_method == 'osmnx' else None,
        )

        # Compute travel times from user location to each hotspot
        user_origin = (user_lat, user_lon)
        hotspot_centroids = [
            (float(row.geometry.centroid.y), float(row.geometry.centroid.x))
            for _, row in hotspots_nearby.iterrows()
        ]
        travel_times = tt.matrix([user_origin], hotspot_centroids)[0]  # shape: (n_hotspots,)

        # Convert travel time to accessibility score (0-100)
        hotspots_nearby['accessibility_score'] = compute_access_score_decay(
            travel_times,
            max_time_min=30.0,
            decay_type='exponential',
            lambda_param=0.3
        )
        hotspots_nearby['travel_time_min'] = travel_times

        # Select popularity score version
        if version == 'v2' and 'popularity_score_v2' in hotspots_nearby.columns:
            popularity_col = 'popularity_score_v2'
        else:
            popularity_col = 'popularity_score'

        # Adjust demand score based on time profile
        base_demand = hotspots_nearby[popularity_col].values
        if time_profile == 'dinner' and 'peak_time_score' in hotspots_nearby.columns:
            # Evening: boost areas with high peak-time activity
            peak_time = hotspots_nearby['peak_time_score'].values
            demand_score = 0.7 * base_demand + 0.3 * peak_time
        elif time_profile == 'lunch' and 'restaurant_score_v2' in hotspots_nearby.columns:
            # Lunch: slightly favor restaurant quality
            poi = hotspots_nearby['restaurant_score_v2'].values
            demand_score = 0.6 * base_demand + 0.4 * poi
        else:
            demand_score = base_demand

        # Get preference profile weights
        weights = get_profile_weights(user_profile)

        # Adjust weights based on time profile
        if time_profile == 'dinner':
            weights = {'demand': 0.50, 'poi': 0.25, 'access': 0.15, 'confidence': 0.10}
        elif time_profile == 'lunch':
            weights = {'demand': 0.30, 'poi': 0.35, 'access': 0.25, 'confidence': 0.10}
        elif time_profile == 'late_night':
            weights = {'demand': 0.50, 'poi': 0.20, 'access': 0.20, 'confidence': 0.10}

        # Compute composite recommendation score
        from src.analysis.scoring import compute_composite_score
        hotspots_nearby['recommendation_score'] = compute_composite_score(
            demand_score=demand_score,
            poi_score=base_demand,
            access_score=hotspots_nearby['accessibility_score'].values,
            weights=weights
        )

    except Exception as e:
        # Fallback to legacy scoring if anything fails
        logger = logging.getLogger(__name__)
        logger.warning(f"TravelTimeCalculator failed ({e}), using legacy fallback")
        max_dist = hotspots_nearby['distance_km'].max()
        if max_dist > 0:
            hotspots_nearby['accessibility_score'] = 100 * (1 - hotspots_nearby['distance_km'] / max_dist)
        else:
            hotspots_nearby['accessibility_score'] = 100
        hotspots_nearby['recommendation_score'] = (
            0.6 * hotspots_nearby['popularity_score'] +
            0.4 * hotspots_nearby['accessibility_score']
        )
        hotspots_nearby['travel_time_min'] = hotspots_nearby['distance_km'] * 12  # rough estimate

    # Sort by recommendation score (tie-breaker via stable sort)
    hotspots_nearby = hotspots_nearby.sort_values(
        'recommendation_score',
        ascending=False,
        kind='mergesort'
    ).head(limit)

    # Prepare response with profile info
    recommendations = []
    for i, (idx, row) in enumerate(hotspots_nearby.iterrows(), start=1):
        centroid = row.geometry.centroid

        rec = {
            'rank': i,
            'popularity_score': float(row.get(popularity_col, 0)),
            'recommendation_score': float(row['recommendation_score']),
            'accessibility_score': float(row['accessibility_score']),
            'travel_time_min': float(row.get('travel_time_min', row['distance_km'] * 12)),
            'distance_km': float(row['distance_km']),
            'n_restaurants': int(row.get('n_restaurants', 0)),
            'n_taxi_dropoffs': int(row.get('n_taxi_dropoffs', 0)),
            'avg_rating': float(row.get('avg_rating', 0)) if pd.notna(row.get('avg_rating')) else None,
            'area_sqkm': float(row.get('intersection_area_sqm', 0) / 1_000_000),
            'centroid_lat': float(centroid.y),
            'centroid_lon': float(centroid.x),
            'geometry': row.geometry.__geo_interface__
        }
        # Add v2-specific fields if available
        if 'peak_time_score' in row:
            rec['peak_time_score'] = float(row['peak_time_score'])
        if 'accessibility_proxy' in row:
            rec['accessibility_proxy'] = float(row['accessibility_proxy'])
        if 'peak_hour_ratio' in row:
            rec['peak_hour_ratio'] = float(row['peak_hour_ratio'])

        recommendations.append(rec)

    return jsonify({
        "user_location": {
            "lat": user_lat,
            "lon": user_lon
        },
        "search_radius_km": max_distance_km,
        "profile": user_profile,
        "time_profile": time_profile,
        "version": version,
        "travel_mode": travel_mode,
        "access_backend": access_method,
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
