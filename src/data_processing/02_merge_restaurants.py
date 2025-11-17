"""
Restaurant Data Merging and Deduplication
==========================================

Purpose: Merge Google Maps and OSM restaurant datasets, removing duplicates

Input:
    - data/raw/restaurants/restaurants_nyc_googlemaps.csv
    - data/raw/restaurants/restaurants_nyc_osm.csv

Output:
    - data/interim/restaurants_merged.geojson
    - data/interim/restaurants_merged.csv

Author: Where to DINE Project
Date: 2025-11-09
"""

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from scipy.spatial import cKDTree
from fuzzywuzzy import fuzz
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_google_maps_data(filepath: str) -> pd.DataFrame:
    """
    Load and standardize Google Maps restaurant data.

    Parameters:
    -----------
    filepath : str
        Path to CSV file

    Returns:
    --------
    pd.DataFrame
        Standardized restaurant data
    """
    logger.info(f"Loading Google Maps data from {filepath}")

    df = pd.read_csv(filepath)

    # Standardize column names
    df_std = pd.DataFrame({
        'name': df['name'],
        'latitude': df['latitude'],
        'longitude': df['longitude'],
        'rating': df.get('rating', None),
        'user_ratings_total': df.get('user_ratings_total', None),
        'price_level': df.get('price_level', None),
        'cuisine': df.get('category', None),
        'source': 'google',
        'place_id': df.get('place_id', df.index.astype(str))
    })

    logger.info(f"Loaded {len(df_std)} restaurants from Google Maps")

    return df_std


def load_osm_data(filepath: str) -> pd.DataFrame:
    """
    Load and standardize OSM restaurant data.

    Parameters:
    -----------
    filepath : str
        Path to CSV file

    Returns:
    --------
    pd.DataFrame
        Standardized restaurant data
    """
    logger.info(f"Loading OSM data from {filepath}")

    df = pd.read_csv(filepath)

    # Standardize column names
    df_std = pd.DataFrame({
        'name': df['name'],
        'latitude': df['latitude'],
        'longitude': df['longitude'],
        'rating': None,  # OSM doesn't have ratings
        'user_ratings_total': None,
        'price_level': None,
        'cuisine': df.get('cuisine', None),
        'source': 'osm',
        'place_id': df.index.astype(str)
    })

    logger.info(f"Loaded {len(df_std)} restaurants from OSM")

    return df_std


def create_geodataframe(df: pd.DataFrame, crs: str = "EPSG:4326") -> gpd.GeoDataFrame:
    """
    Convert DataFrame to GeoDataFrame with Point geometries.

    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame with latitude, longitude columns
    crs : str
        Coordinate reference system (default: WGS84)

    Returns:
    --------
    gpd.GeoDataFrame
    """
    # Remove rows with null coordinates
    df_clean = df.dropna(subset=['latitude', 'longitude'])

    # Create geometry
    geometry = [Point(lon, lat) for lon, lat in zip(df_clean['longitude'], df_clean['latitude'])]

    gdf = gpd.GeoDataFrame(df_clean, geometry=geometry, crs=crs)

    logger.info(f"Created GeoDataFrame with {len(gdf)} valid geometries")

    return gdf


def deduplicate_restaurants(
    gdf_primary: gpd.GeoDataFrame,
    gdf_secondary: gpd.GeoDataFrame,
    distance_threshold: float = 50.0,
    name_similarity_threshold: int = 80
) -> gpd.GeoDataFrame:
    """
    Remove duplicate restaurants between two datasets.

    Duplicates are identified by:
    1. Spatial proximity (< distance_threshold meters)
    2. Name similarity (> name_similarity_threshold %)

    Parameters:
    -----------
    gdf_primary : gpd.GeoDataFrame
        Primary dataset (prioritized in case of duplicates)
    gdf_secondary : gpd.GeoDataFrame
        Secondary dataset (duplicates removed from this)
    distance_threshold : float
        Maximum distance in meters to consider as duplicate (default: 50m)
    name_similarity_threshold : int
        Minimum Levenshtein similarity percentage (default: 80%)

    Returns:
    --------
    gpd.GeoDataFrame
        Merged dataset with duplicates removed
    """
    logger.info("Starting deduplication process...")
    logger.info(f"Distance threshold: {distance_threshold}m, Name similarity: {name_similarity_threshold}%")

    # Project to meters for accurate distance calculation
    crs_projected = "EPSG:2263"  # NAD83 / New York Long Island
    gdf1_proj = gdf_primary.to_crs(crs_projected)
    gdf2_proj = gdf_secondary.to_crs(crs_projected)

    # Extract coordinates
    coords1 = list(zip(gdf1_proj.geometry.x, gdf1_proj.geometry.y))
    coords2 = list(zip(gdf2_proj.geometry.x, gdf2_proj.geometry.y))

    # Build spatial index using KDTree
    logger.info("Building spatial index...")
    tree = cKDTree(coords1)

    # Find duplicates
    duplicates = []

    logger.info("Identifying duplicates...")
    for idx2, coord2 in enumerate(coords2):
        # Query nearest neighbor in primary dataset
        distance, idx1 = tree.query(coord2, k=1)

        # Check if within distance threshold
        if distance < distance_threshold:
            # Check name similarity
            name1 = str(gdf1_proj.iloc[idx1]['name']).lower()
            name2 = str(gdf2_proj.iloc[idx2]['name']).lower()

            similarity = fuzz.ratio(name1, name2)

            if similarity >= name_similarity_threshold:
                duplicates.append(idx2)
                logger.debug(f"Duplicate found: '{name2}' (OSM) ≈ '{name1}' (Google), "
                           f"distance: {distance:.1f}m, similarity: {similarity}%")

    logger.info(f"Found {len(duplicates)} duplicates")

    # Remove duplicates from secondary dataset
    gdf2_unique = gdf2_proj.drop(gdf2_proj.index[duplicates]).reset_index(drop=True)

    # Combine datasets
    logger.info("Merging datasets...")
    gdf_merged = pd.concat([gdf1_proj, gdf2_unique], ignore_index=True)

    # Transform back to WGS84
    gdf_merged = gdf_merged.to_crs("EPSG:4326")

    logger.info(f"Final merged dataset: {len(gdf_merged)} unique restaurants")
    logger.info(f"  - From primary (Google): {len(gdf_primary)}")
    logger.info(f"  - From secondary (OSM): {len(gdf2_unique)}")
    logger.info(f"  - Duplicates removed: {len(duplicates)}")

    return gdf_merged


def save_outputs(gdf: gpd.GeoDataFrame, output_dir: str):
    """
    Save merged restaurant data in multiple formats.

    Parameters:
    -----------
    gdf : gpd.GeoDataFrame
        Merged restaurant data
    output_dir : str
        Output directory path
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Save as GeoJSON
    geojson_path = output_path / "restaurants_merged.geojson"
    gdf.to_file(geojson_path, driver="GeoJSON")
    logger.info(f"Saved GeoJSON: {geojson_path}")

    # Save as CSV (without geometry for compatibility)
    csv_path = output_path / "restaurants_merged.csv"
    df_csv = gdf.drop(columns='geometry')
    df_csv.to_csv(csv_path, index=False)
    logger.info(f"Saved CSV: {csv_path}")

    # Print summary statistics
    print("\n" + "="*60)
    print("RESTAURANT DATA MERGE - SUMMARY")
    print("="*60)
    print(f"Total restaurants: {len(gdf)}")
    print(f"  - Google Maps: {(gdf['source'] == 'google').sum()}")
    print(f"  - OpenStreetMap: {(gdf['source'] == 'osm').sum()}")
    print(f"\nWith ratings: {gdf['rating'].notna().sum()} ({gdf['rating'].notna().sum()/len(gdf)*100:.1f}%)")
    print(f"Average rating: {gdf['rating'].mean():.2f}")
    print(f"\nWith cuisine info: {gdf['cuisine'].notna().sum()} ({gdf['cuisine'].notna().sum()/len(gdf)*100:.1f}%)")
    print(f"\nSpatial extent:")
    print(f"  Latitude: [{gdf['latitude'].min():.4f}, {gdf['latitude'].max():.4f}]")
    print(f"  Longitude: [{gdf['longitude'].min():.4f}, {gdf['longitude'].max():.4f}]")
    print("="*60 + "\n")


def main():
    """
    Main execution function.
    """
    logger.info("="*60)
    logger.info("RESTAURANT DATA MERGING PIPELINE")
    logger.info("="*60)

    # Define paths
    google_path = "data/raw/restaurants/restaurants_nyc_googlemaps.csv"
    osm_path = "data/raw/restaurants/restaurants_nyc_osm.csv"
    output_dir = "data/interim"

    # Step 1: Load data
    logger.info("\n[Step 1/4] Loading restaurant data...")
    df_google = load_google_maps_data(google_path)
    df_osm = load_osm_data(osm_path)

    # Step 2: Create GeoDataFrames
    logger.info("\n[Step 2/4] Creating geographic datasets...")
    gdf_google = create_geodataframe(df_google)
    gdf_osm = create_geodataframe(df_osm)

    # Step 3: Deduplicate
    logger.info("\n[Step 3/4] Deduplicating restaurants...")
    gdf_merged = deduplicate_restaurants(
        gdf_google,
        gdf_osm,
        distance_threshold=50.0,
        name_similarity_threshold=80
    )

    # Step 4: Save outputs
    logger.info("\n[Step 4/4] Saving outputs...")
    save_outputs(gdf_merged, output_dir)

    logger.info("\n✅ Restaurant data merging completed successfully!")


if __name__ == "__main__":
    main()
