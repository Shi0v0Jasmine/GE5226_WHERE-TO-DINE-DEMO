"""
Isochrone (Service Area) Calculation
=====================================

Calculate travel time isochrones from a given location using OSM networks.

Supports:
- Walking isochrones (5, 10, 15 minutes)
- Driving isochrones (10, 20, 30 minutes)

Uses OSMnx and NetworkX for network-based routing.

Author: Where to DINE Project
Date: 2025-11-09
"""

import networkx as nx
import osmnx as ox
import geopandas as gpd
from shapely.geometry import Point, Polygon
from pathlib import Path
import logging
from typing import Tuple, List
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_network(network_path: str) -> nx.MultiDiGraph:
    """
    Load pre-downloaded network graph.

    Parameters:
    -----------
    network_path : str
        Path to network file (.gpickle or .graphml)

    Returns:
    --------
    nx.MultiDiGraph
        Network graph
    """
    network_file = Path(network_path)

    if not network_file.exists():
        raise FileNotFoundError(f"Network file not found: {network_path}")

    logger.info(f"Loading network from {network_path}...")

    if network_path.endswith('.gpickle'):
        G = nx.read_gpickle(network_path)
    elif network_path.endswith('.graphml'):
        G = ox.load_graphml(network_path)
    else:
        raise ValueError(f"Unsupported file format: {network_path}")

    logger.info(f"Loaded network: {len(G.nodes)} nodes, {len(G.edges)} edges")

    return G


def get_nearest_node(G: nx.MultiDiGraph, lat: float, lon: float) -> int:
    """
    Find nearest network node to a given coordinate.

    Parameters:
    -----------
    G : nx.MultiDiGraph
        Network graph
    lat : float
        Latitude
    lon : float
        Longitude

    Returns:
    --------
    int
        Nearest node ID
    """
    return ox.distance.nearest_nodes(G, lon, lat)


def calculate_isochrone(
    G: nx.MultiDiGraph,
    origin_lat: float,
    origin_lon: float,
    travel_time_minutes: int = 15,
    speed_kmh: float = 4.8
) -> gpd.GeoDataFrame:
    """
    Calculate isochrone polygon for a given travel time.

    Parameters:
    -----------
    G : nx.MultiDiGraph
        Network graph with travel_time edge attributes
    origin_lat : float
        Origin latitude
    origin_lon : float
        Origin longitude
    travel_time_minutes : int
        Maximum travel time in minutes
    speed_kmh : float
        Travel speed in km/h (default: 4.8 for walking)

    Returns:
    --------
    gpd.GeoDataFrame
        Isochrone polygon
    """
    logger.info(f"Calculating {travel_time_minutes}-minute isochrone from ({origin_lat}, {origin_lon})...")

    # Find nearest node
    origin_node = get_nearest_node(G, origin_lat, origin_lon)

    # Convert travel time to seconds
    travel_time_seconds = travel_time_minutes * 60

    # Calculate shortest paths from origin within time limit
    # Using Dijkstra's algorithm with travel_time as weight
    try:
        subgraph = nx.ego_graph(
            G,
            origin_node,
            radius=travel_time_seconds,
            distance='travel_time'
        )
    except:
        # Fallback: use simpler approach
        logger.warning("Using fallback isochrone calculation...")
        lengths = nx.single_source_dijkstra_path_length(
            G,
            origin_node,
            cutoff=travel_time_seconds,
            weight='travel_time'
        )
        reachable_nodes = list(lengths.keys())
        subgraph = G.subgraph(reachable_nodes)

    # Get node coordinates
    node_points = []
    for node in subgraph.nodes():
        node_data = G.nodes[node]
        node_points.append(Point(node_data['x'], node_data['y']))

    # Create convex hull polygon
    if len(node_points) < 3:
        logger.warning(f"Only {len(node_points)} reachable nodes - creating small buffer")
        origin_point = Point(origin_lon, origin_lat)
        # Create small circle as fallback (approximate distance)
        buffer_meters = (speed_kmh * 1000 / 60) * travel_time_minutes
        gdf_origin = gpd.GeoDataFrame(
            [{'geometry': origin_point}],
            crs="EPSG:4326"
        )
        gdf_proj = gdf_origin.to_crs("EPSG:2263")
        polygon_proj = gdf_proj.geometry.iloc[0].buffer(buffer_meters)
        gdf_result = gpd.GeoDataFrame(
            [{'geometry': polygon_proj}],
            crs="EPSG:2263"
        )
        polygon_wgs84 = gdf_result.to_crs("EPSG:4326").geometry.iloc[0]
    else:
        from shapely.ops import unary_union
        multi_point = unary_union(node_points)
        polygon_wgs84 = multi_point.convex_hull

    # Create GeoDataFrame
    gdf_isochrone = gpd.GeoDataFrame(
        [{
            'travel_time_minutes': travel_time_minutes,
            'origin_lat': origin_lat,
            'origin_lon': origin_lon,
            'n_reachable_nodes': len(subgraph.nodes()),
            'geometry': polygon_wgs84
        }],
        crs="EPSG:4326"
    )

    logger.info(f"Isochrone created: {len(subgraph.nodes())} reachable nodes")

    return gdf_isochrone


def calculate_multiple_isochrones(
    G: nx.MultiDiGraph,
    origin_lat: float,
    origin_lon: float,
    travel_times: List[int],
    speed_kmh: float = 4.8
) -> gpd.GeoDataFrame:
    """
    Calculate multiple isochrones for different travel times.

    Parameters:
    -----------
    G : nx.MultiDiGraph
        Network graph
    origin_lat : float
        Origin latitude
    origin_lon : float
        Origin longitude
    travel_times : List[int]
        List of travel times in minutes (e.g., [5, 10, 15])
    speed_kmh : float
        Travel speed in km/h

    Returns:
    --------
    gpd.GeoDataFrame
        Multiple isochrone polygons
    """
    isochrones = []

    for travel_time in sorted(travel_times):
        isochrone = calculate_isochrone(
            G,
            origin_lat,
            origin_lon,
            travel_time,
            speed_kmh
        )
        isochrones.append(isochrone)

    # Combine into single GeoDataFrame
    gdf_all = pd.concat(isochrones, ignore_index=True)

    return gdf_all


# Convenience functions for different modes

def calculate_walk_isochrone(
    origin_lat: float,
    origin_lon: float,
    travel_time_minutes: int = 15,
    network_path: str = "data/processed/networks/network_walk.gpickle"
) -> gpd.GeoDataFrame:
    """
    Calculate walking isochrone.

    Parameters:
    -----------
    origin_lat : float
        Origin latitude
    origin_lon : float
        Origin longitude
    travel_time_minutes : int
        Travel time in minutes (default: 15)
    network_path : str
        Path to walking network file

    Returns:
    --------
    gpd.GeoDataFrame
        Isochrone polygon
    """
    G_walk = load_network(network_path)

    return calculate_isochrone(
        G_walk,
        origin_lat,
        origin_lon,
        travel_time_minutes,
        speed_kmh=4.8
    )


def calculate_drive_isochrone(
    origin_lat: float,
    origin_lon: float,
    travel_time_minutes: int = 30,
    network_path: str = "data/processed/networks/network_drive.gpickle"
) -> gpd.GeoDataFrame:
    """
    Calculate driving isochrone.

    Parameters:
    -----------
    origin_lat : float
        Origin latitude
    origin_lon : float
        Origin longitude
    travel_time_minutes : int
        Travel time in minutes (default: 30)
    network_path : str
        Path to driving network file

    Returns:
    --------
    gpd.GeoDataFrame
        Isochrone polygon
    """
    G_drive = load_network(network_path)

    return calculate_isochrone(
        G_drive,
        origin_lat,
        origin_lon,
        travel_time_minutes,
        speed_kmh=25
    )


# Example usage
if __name__ == "__main__":
    import pandas as pd

    # Example: Calculate 15-minute walking isochrone from Times Square
    try:
        isochrone = calculate_walk_isochrone(
            origin_lat=40.7589,
            origin_lon=-73.9851,
            travel_time_minutes=15
        )

        print("\n15-Minute Walking Isochrone from Times Square:")
        print(isochrone)

        # Save to file
        output_path = Path("data/processed/example_isochrone.geojson")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        isochrone.to_file(output_path, driver="GeoJSON")
        print(f"\nSaved to: {output_path}")

    except FileNotFoundError as e:
        print(f"\nError: {e}")
        print("Please run 03_build_network.py first to download OSM networks.")
