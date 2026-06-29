#!/usr/bin/env python3
"""
Download NYC Street Network Graph for OSMnx
==============================================

Downloads the NYC street network from OpenStreetMap and saves as
GraphML files for walk, drive, and bike modes.

Output:
    data/networks/nyc_walk.graphml
    data/networks/nyc_drive.graphml
    data/networks/nyc_bike.graphml

Usage:
    python scripts/download_nyc_network.py

Requirements:
    pip install osmnx networkx

Warning:
    - NYC full network is ~500-800 MB for walk mode
    - Download may take 5-15 minutes depending on connection
    - OSM data is live; results may vary from run to run

Author: Where to DINE Project
Date: 2026-06-26
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

import osmnx as ox
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


OUTPUT_DIR = Path("data/networks")
PLACE_NAME = "New York City, New York, USA"

NETWORK_TYPES = {
    'walk': 'walk',
    'drive': 'drive',
    'bike': 'bike',
}


def download_network(network_type: str, output_path: Path):
    """Download and save a single OSMnx network."""
    logger.info(f"Downloading NYC {network_type} network...")
    logger.info(f"  This may take 5-15 minutes...")
    
    G = ox.graph_from_place(
        PLACE_NAME,
        network_type=network_type,
        simplify=True,
        retain_all=False,
    )
    
    logger.info(f"  Nodes: {G.number_of_nodes()}, Edges: {G.number_of_edges()}")
    
    # Add travel time attribute based on speed
    speed_kmh = {
        'walk': 5.0,
        'bike': 15.0,
        'drive': 30.0,  # NYC average
    }.get(network_type, 5.0)
    speed_mps = speed_kmh * 1000 / 3600
    
    for u, v, k, data in G.edges(keys=True, data=True):
        length_m = data.get('length', 0)
        data['travel_time'] = length_m / speed_mps
    
    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ox.save_graphml(G, output_path)
    logger.info(f"  Saved: {output_path}")
    
    return G


def main():
    """Download all three NYC networks."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    logger.info("=" * 60)
    logger.info("NYC STREET NETWORK DOWNLOAD")
    logger.info("=" * 60)
    
    for mode_name, network_type in NETWORK_TYPES.items():
        output_path = OUTPUT_DIR / f"nyc_{mode_name}.graphml"
        
        if output_path.exists():
            logger.info(f"{mode_name}: Already exists at {output_path}, skipping")
            continue
        
        try:
            download_network(network_type, output_path)
        except Exception as e:
            logger.error(f"Failed to download {mode_name}: {e}")
            continue
    
    logger.info("\n" + "=" * 60)
    logger.info("Download complete!")
    logger.info("=" * 60)
    logger.info(f"Graphs saved to: {OUTPUT_DIR.absolute()}")
    logger.info("\nTo use OSMnx backend:")
    logger.info("  from src.travel_time import TravelTimeCalculator")
    logger.info("  tt = TravelTimeCalculator(mode='walk', backend='osmnx')")


if __name__ == "__main__":
    main()
