# Data Processing Pipeline
## Comprehensive Processing Workflow for "Where to DINE" Project

**Version**: 1.0
**Last Updated**: 2025-11-09
**Purpose**: Document all data extraction, transformation, and loading (ETL) operations

---

## Overview

This document specifies the complete data processing pipeline, from raw data acquisition to analysis-ready datasets. Each processing step is numbered sequentially and includes:

1. **Input**: Source data files
2. **Processing**: Transformations applied
3. **Output**: Generated files
4. **Validation**: Quality checks
5. **Dependencies**: Required libraries
6. **Script**: Corresponding code file

---

## Pipeline Architecture

```
RAW DATA
    ├── Taxi (50-70 GB)
    ├── Restaurants (5 MB)
    ├── GTFS (100 MB)
    └── OSM (50-100 MB)
           ↓
    DATA EXTRACTION & CLEANING
           ↓
    INTERIM DATA
    ├── Filtered taxi records
    ├── Merged restaurants
    ├── Parsed GTFS
    └── OSM network graphs
           ↓
    ANALYSIS PROCESSING
    ├── HDBSCAN clustering
    ├── Spatial intersection
    └── Network dataset creation
           ↓
    PROCESSED DATA (Analysis-ready)
    ├── dining_hotspots_final.geojson
    ├── network_dataset/
    └── validation_metrics.json
```

---

## PHASE 1: Data Acquisition

### 1.1 NYC Taxi Data Download

**Source**: NYC TLC Trip Record Data
**URL**: https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page

**Files to Download** (12 files, ~50-70 GB total):
```bash
# Yellow Taxi 2024 (example for January)
https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-01.parquet
https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-02.parquet
# ... continue for all 12 months
```

**Download Script**:
```bash
#!/bin/bash
# scripts/download_taxi_data.sh

BASE_URL="https://d37ci6vzurychx.cloudfront.net/trip-data"
OUTPUT_DIR="data/raw/taxi"
mkdir -p $OUTPUT_DIR

for month in {01..12}; do
    wget -P $OUTPUT_DIR "${BASE_URL}/yellow_tripdata_2024-${month}.parquet"
done
```

**Validation**:
- [ ] Verify 12 files downloaded
- [ ] Check file sizes (each ~4-6 GB)
- [ ] Test readability with `pandas.read_parquet()`

---

### 1.2 Restaurant Data (Already Provided)

**Files**:
- `restaurants_nyc_googlemaps.csv` (14,330 records)
- `restaurants_nyc_osm.csv` (7,723 records)
- `restaurants_nyc_osm.geojson` (7,723 records)

**Location**: `data/raw/restaurants/`

**Validation**:
- [ ] Verify record counts match specifications
- [ ] Check coordinate ranges (lat: 40.5-40.9, lon: -74.3 to -73.7)
- [ ] Inspect for missing values

---

### 1.3 GTFS Transit Data Download

**Source**: MTA GTFS Feeds
**URL**: https://new.mta.info/developers

**Files to Download**:
```bash
#!/bin/bash
# scripts/download_gtfs_data.sh

OUTPUT_DIR="data/raw/gtfs"
mkdir -p $OUTPUT_DIR

# Subway
wget -O $OUTPUT_DIR/gtfs_subway.zip http://web.mta.info/developers/data/nyct/subway/google_transit.zip

# Buses (by borough)
wget -O $OUTPUT_DIR/gtfs_bx.zip http://web.mta.info/developers/data/nyct/bus/google_transit_bronx.zip
wget -O $OUTPUT_DIR/gtfs_b.zip http://web.mta.info/developers/data/nyct/bus/google_transit_brooklyn.zip
wget -O $OUTPUT_DIR/gtfs_q.zip http://web.mta.info/developers/data/nyct/bus/google_transit_queens.zip
wget -O $OUTPUT_DIR/gtfs_si.zip http://web.mta.info/developers/data/nyct/bus/google_transit_staten_island.zip
wget -O $OUTPUT_DIR/gtfs_m.zip http://web.mta.info/developers/data/nyct/bus/google_transit_manhattan.zip
wget -O $OUTPUT_DIR/gtfs_busco.zip http://web.mta.info/developers/data/nyct/bus/google_transit_mta_bus_company.zip
```

**Validation**:
- [ ] Verify 7 ZIP files downloaded
- [ ] Test unzip: `unzip -t gtfs_subway.zip`
- [ ] Verify standard GTFS files present: `stops.txt`, `routes.txt`, `trips.txt`, etc.

---

### 1.4 OpenStreetMap Data Extraction

**Method**: Use `osmnx` library (programmatic download)

**Script**: `src/data_processing/04_build_osm_network.py`

**Code Example**:
```python
import osmnx as ox

# Define NYC bounding box
north, south, east, west = 40.9176, 40.4774, -73.7004, -74.2591

# Download road network
G_drive = ox.graph_from_bbox(north, south, east, west, network_type='drive')
ox.save_graphml(G_drive, "data/raw/osm/nyc_drive_network.graphml")

# Download pedestrian network
G_walk = ox.graph_from_bbox(north, south, east, west, network_type='walk')
ox.save_graphml(G_walk, "data/raw/osm/nyc_walk_network.graphml")
```

**Validation**:
- [ ] Networks contain nodes and edges
- [ ] Coordinate ranges match NYC
- [ ] Networks are connected (no isolated components)

---

## PHASE 2: Data Cleaning & Preprocessing

### 2.1 Taxi Data Filtering

**Script**: `src/data_processing/01_extract_taxi_data.py`

**Objective**: Reduce 50-70 GB to manageable size by filtering for dining-relevant trips.

#### 2.1.1 Schema Inspection

**Input**: `data/raw/taxi/yellow_tripdata_2024-01.parquet`

**Expected Columns**:
- `tpep_pickup_datetime`
- `tpep_dropoff_datetime`
- `pickup_longitude`, `pickup_latitude`
- `dropoff_longitude`, `dropoff_latitude`
- `passenger_count`
- `trip_distance`
- `fare_amount`

**Code**:
```python
import pandas as pd

# Read one file to inspect schema
df_sample = pd.read_parquet("data/raw/taxi/yellow_tripdata_2024-01.parquet", nrows=1000)
print(df_sample.columns.tolist())
print(df_sample.dtypes)
print(df_sample.describe())
```

#### 2.1.2 Temporal Filtering

**Dining Hours Definition**:
- **Breakfast**: 7:00 AM - 10:00 AM
- **Lunch**: 11:00 AM - 2:00 PM
- **Dinner**: 5:00 PM - 10:00 PM
- **Late Night**: 10:00 PM - 1:00 AM

**Code**:
```python
def filter_dining_hours(df):
    """Filter taxi trips to dining-relevant time windows."""
    df['dropoff_datetime'] = pd.to_datetime(df['tpep_dropoff_datetime'])
    df['hour'] = df['dropoff_datetime'].dt.hour
    df['day_of_week'] = df['dropoff_datetime'].dt.dayofweek  # 0=Monday, 6=Sunday

    # Define dining hours
    dining_hours = (
        ((df['hour'] >= 7) & (df['hour'] < 10)) |   # Breakfast
        ((df['hour'] >= 11) & (df['hour'] < 14)) |  # Lunch
        ((df['hour'] >= 17) & (df['hour'] < 22)) |  # Dinner
        ((df['hour'] >= 22) | (df['hour'] < 1))     # Late night
    )

    return df[dining_hours]
```

#### 2.1.3 Spatial Filtering

**Objective**: Keep only drop-offs within NYC proper.

**NYC Bounding Box**:
- Latitude: [40.4774, 40.9176]
- Longitude: [-74.2591, -73.7004]

**Code**:
```python
def filter_nyc_bounds(df):
    """Filter to NYC geographic extent."""
    return df[
        (df['dropoff_latitude'] >= 40.4774) &
        (df['dropoff_latitude'] <= 40.9176) &
        (df['dropoff_longitude'] >= -74.2591) &
        (df['dropoff_longitude'] <= -73.7004)
    ]
```

#### 2.1.4 Data Quality Filters

**Remove invalid records**:
- Null coordinates
- Zero passenger count
- Unrealistic trip distances (> 50 miles)
- Zero fare amount (test trips)

**Code**:
```python
def clean_taxi_data(df):
    """Apply data quality filters."""
    df = df.dropna(subset=['dropoff_latitude', 'dropoff_longitude'])
    df = df[df['passenger_count'] > 0]
    df = df[df['trip_distance'] > 0]
    df = df[df['trip_distance'] < 50]  # Remove unrealistic trips
    df = df[df['fare_amount'] > 0]
    return df
```

#### 2.1.5 Full Processing Pipeline

**Input**: 12 monthly Parquet files (~50-70 GB)
**Output**: `data/interim/taxi_filtered_dining_hours.parquet` (~5-10 GB)

**Code**:
```python
import glob
import pandas as pd

def process_all_taxi_data():
    """Process all 12 months of taxi data."""
    all_files = glob.glob("data/raw/taxi/yellow_tripdata_2024-*.parquet")

    filtered_dfs = []

    for file in all_files:
        print(f"Processing {file}...")
        df = pd.read_parquet(file)

        # Apply filters
        df = clean_taxi_data(df)
        df = filter_nyc_bounds(df)
        df = filter_dining_hours(df)

        # Keep only necessary columns
        df = df[['dropoff_latitude', 'dropoff_longitude',
                 'tpep_dropoff_datetime', 'hour', 'day_of_week']]

        filtered_dfs.append(df)

    # Concatenate all months
    df_final = pd.concat(filtered_dfs, ignore_index=True)

    # Save to interim
    df_final.to_parquet("data/interim/taxi_filtered_dining_hours.parquet",
                        compression='snappy')

    print(f"Saved {len(df_final):,} filtered records")
    return df_final

# Execute
df_taxi = process_all_taxi_data()
```

**Validation**:
- [ ] Output file size: 5-10 GB (90% reduction)
- [ ] All timestamps within dining hours
- [ ] All coordinates within NYC bounds
- [ ] No null values
- [ ] Record count: ~20-30 million (estimated)

---

### 2.2 Restaurant Data Merging

**Script**: `src/data_processing/02_merge_restaurants.py`

**Objective**: Merge Google Maps and OSM datasets, remove duplicates.

#### 2.2.1 Load Both Datasets

**Code**:
```python
import pandas as pd
import geopandas as gpd

# Load Google Maps data
df_google = pd.read_csv("data/raw/restaurants/restaurants_nyc_googlemaps.csv")

# Load OSM data
df_osm = pd.read_csv("data/raw/restaurants/restaurants_nyc_osm.csv")

print(f"Google: {len(df_google)} records")
print(f"OSM: {len(df_osm)} records")
```

#### 2.2.2 Standardize Schema

**Target Schema**:
```python
{
    'name': str,
    'latitude': float,
    'longitude': float,
    'rating': float,
    'cuisine': str,
    'source': str,  # 'google' or 'osm'
    'place_id': str  # Google place_id or OSM node_id
}
```

**Code**:
```python
def standardize_google(df):
    """Standardize Google Maps schema."""
    return pd.DataFrame({
        'name': df['name'],
        'latitude': df['latitude'],
        'longitude': df['longitude'],
        'rating': df['rating'],
        'cuisine': df.get('category', None),
        'source': 'google',
        'place_id': df['place_id']
    })

def standardize_osm(df):
    """Standardize OSM schema."""
    return pd.DataFrame({
        'name': df['name'],
        'latitude': df['latitude'],
        'longitude': df['longitude'],
        'rating': None,  # OSM doesn't have ratings
        'cuisine': df.get('cuisine', None),
        'source': 'osm',
        'place_id': df.index.astype(str)  # Use index as ID
    })

df_google_std = standardize_google(df_google)
df_osm_std = standardize_osm(df_osm)
```

#### 2.2.3 Spatial Deduplication

**Method**: Consider two restaurants duplicates if:
- Within 50 meters of each other
- Name similarity > 0.8 (Levenshtein distance)

**Code**:
```python
from shapely.geometry import Point
from scipy.spatial import cKDTree
from fuzzywuzzy import fuzz

def deduplicate_restaurants(df1, df2, distance_threshold=50):
    """
    Remove duplicate restaurants between two datasets.

    Args:
        df1: First dataframe (prioritized)
        df2: Second dataframe
        distance_threshold: Maximum distance in meters to consider duplicate

    Returns:
        Merged dataframe with duplicates removed
    """
    # Convert to GeoDataFrames
    gdf1 = gpd.GeoDataFrame(
        df1,
        geometry=gpd.points_from_xy(df1.longitude, df1.latitude),
        crs="EPSG:4326"
    )
    gdf2 = gpd.GeoDataFrame(
        df2,
        geometry=gpd.points_from_xy(df2.longitude, df2.latitude),
        crs="EPSG:4326"
    )

    # Project to meters (NAD83 / New York Long Island)
    gdf1_proj = gdf1.to_crs("EPSG:2263")
    gdf2_proj = gdf2.to_crs("EPSG:2263")

    # Extract coordinates
    coords1 = list(zip(gdf1_proj.geometry.x, gdf1_proj.geometry.y))
    coords2 = list(zip(gdf2_proj.geometry.x, gdf2_proj.geometry.y))

    # Build spatial index
    tree = cKDTree(coords1)

    # Find nearby pairs
    duplicates = []
    for idx2, coord2 in enumerate(coords2):
        distances, indices = tree.query(coord2, k=1)

        if distances < distance_threshold:
            idx1 = indices
            # Check name similarity
            name1 = str(gdf1.iloc[idx1]['name']).lower()
            name2 = str(gdf2.iloc[idx2]['name']).lower()
            similarity = fuzz.ratio(name1, name2)

            if similarity > 80:  # 80% similarity
                duplicates.append(idx2)

    # Remove duplicates from df2
    gdf2_unique = gdf2.drop(gdf2.index[duplicates])

    # Concatenate
    gdf_merged = pd.concat([gdf1, gdf2_unique], ignore_index=True)

    return gdf_merged

# Execute deduplication
gdf_merged = deduplicate_restaurants(df_google_std, df_osm_std)
print(f"Merged: {len(gdf_merged)} unique restaurants")
```

#### 2.2.4 Save Merged Dataset

**Output**: `data/interim/restaurants_merged.geojson`

**Code**:
```python
# Convert to GeoDataFrame if not already
gdf_final = gpd.GeoDataFrame(
    gdf_merged,
    geometry=gpd.points_from_xy(gdf_merged.longitude, gdf_merged.latitude),
    crs="EPSG:4326"
)

# Save as GeoJSON
gdf_final.to_file("data/interim/restaurants_merged.geojson", driver="GeoJSON")

# Also save as CSV for compatibility
gdf_final.drop(columns='geometry').to_csv("data/interim/restaurants_merged.csv", index=False)
```

**Validation**:
- [ ] Record count: 18,000-20,000 (after deduplication)
- [ ] No null coordinates
- [ ] Coordinate ranges within NYC bounds
- [ ] Duplicate check: `gdf_final.duplicated(subset=['latitude', 'longitude']).sum() == 0`

---

### 2.3 GTFS Data Processing

**Script**: `src/data_processing/03_process_gtfs.py`

**Objective**: Unzip GTFS files and parse into GIS-compatible formats.

#### 2.3.1 Unzip All GTFS Files

**Code**:
```python
import zipfile
import os

gtfs_files = [
    "gtfs_subway.zip",
    "gtfs_bx.zip", "gtfs_b.zip", "gtfs_q.zip",
    "gtfs_si.zip", "gtfs_m.zip", "gtfs_busco.zip"
]

for gtfs_file in gtfs_files:
    input_path = f"data/raw/gtfs/{gtfs_file}"
    output_dir = f"data/interim/gtfs_unpacked/{gtfs_file.replace('.zip', '')}"

    os.makedirs(output_dir, exist_ok=True)

    with zipfile.ZipFile(input_path, 'r') as zip_ref:
        zip_ref.extractall(output_dir)

    print(f"Extracted {gtfs_file} to {output_dir}")
```

#### 2.3.2 Load and Validate GTFS Components

**Standard GTFS Files**:
- `agency.txt`: Transit agency info
- `stops.txt`: Stop locations (lat/lon)
- `routes.txt`: Route definitions
- `trips.txt`: Individual trip instances
- `stop_times.txt`: Stop sequences for each trip
- `calendar.txt`: Service schedules
- `shapes.txt`: Route geometries (optional)

**Code**:
```python
def load_gtfs(gtfs_dir):
    """Load GTFS text files into DataFrames."""
    gtfs = {}

    files = ['stops', 'routes', 'trips', 'stop_times', 'calendar']

    for file in files:
        file_path = f"{gtfs_dir}/{file}.txt"
        if os.path.exists(file_path):
            gtfs[file] = pd.read_csv(file_path)
            print(f"Loaded {file}: {len(gtfs[file])} records")
        else:
            print(f"WARNING: {file}.txt not found")

    return gtfs

# Load subway GTFS
gtfs_subway = load_gtfs("data/interim/gtfs_unpacked/gtfs_subway")
```

#### 2.3.3 Create Stops GeoDataFrame

**Code**:
```python
def create_stops_geodataframe(gtfs_dict):
    """Convert GTFS stops to GeoDataFrame."""
    stops = gtfs_dict['stops']

    gdf_stops = gpd.GeoDataFrame(
        stops,
        geometry=gpd.points_from_xy(stops.stop_lon, stops.stop_lat),
        crs="EPSG:4326"
    )

    # Select relevant columns
    gdf_stops = gdf_stops[['stop_id', 'stop_name', 'stop_lat', 'stop_lon', 'geometry']]

    return gdf_stops

gdf_stops_subway = create_stops_geodataframe(gtfs_subway)
gdf_stops_subway.to_file("data/processed/transit_stops_subway.geojson", driver="GeoJSON")
```

#### 2.3.4 (Advanced) Convert GTFS to Routable Network

**Challenge**: GTFS is schedule-based, not network-based.

**Options**:
1. **Use specialized library**: `r5py`, `gtfs_kit`, or `peartree`
2. **Simplify**: Create "typical weekday" network ignoring schedules
3. **Outsource**: Use external routing API (Google Directions, Mapbox)

**Example using `peartree`**:
```python
import peartree as pt

# Load GTFS feed
path_gtfs = "data/interim/gtfs_unpacked/gtfs_subway"
feed = pt.get_representative_feed(path_gtfs)

# Convert to NetworkX graph
G_transit = pt.load_feed_as_graph(feed, start_time=7*3600, end_time=10*3600)  # 7-10 AM

# Save as GraphML
import networkx as nx
nx.write_graphml(G_transit, "data/processed/network_dataset/transit_network.graphml")
```

**Note**: This is complex and may require significant debugging. Consider simplifying to stops-only for initial implementation.

**Validation**:
- [ ] All stops have valid coordinates
- [ ] Stop counts match expected (subway: ~400+, buses: 5000+)
- [ ] Routes cover all 5 boroughs

---

### 2.4 OSM Network Extraction

**Script**: `src/data_processing/04_build_osm_network.py` (partially shown in 1.4)

**Objective**: Extract routable road and pedestrian networks.

#### 2.4.1 Download Networks

**Code** (from earlier):
```python
import osmnx as ox

north, south, east, west = 40.9176, 40.4774, -73.7004, -74.2591

# Drive network
G_drive = ox.graph_from_bbox(north, south, east, west, network_type='drive')

# Walk network
G_walk = ox.graph_from_bbox(north, south, east, west, network_type='walk')

# Save
ox.save_graphml(G_drive, "data/processed/network_dataset/osm_drive_network.graphml")
ox.save_graphml(G_walk, "data/processed/network_dataset/osm_walk_network.graphml")
```

#### 2.4.2 Add Edge Travel Times

**Code**:
```python
def add_travel_times(G, speed_kmh):
    """Add travel time attributes to network edges."""
    for u, v, k, data in G.edges(keys=True, data=True):
        length_m = data.get('length', 0)
        length_km = length_m / 1000
        time_hours = length_km / speed_kmh
        time_minutes = time_hours * 60
        data['travel_time_min'] = time_minutes
    return G

# Assume average speeds
G_drive_timed = add_travel_times(G_drive, speed_kmh=25)  # Urban driving
G_walk_timed = add_travel_times(G_walk, speed_kmh=4.8)   # Walking

ox.save_graphml(G_drive_timed, "data/processed/network_dataset/osm_drive_network.graphml")
ox.save_graphml(G_walk_timed, "data/processed/network_dataset/osm_walk_network.graphml")
```

**Validation**:
- [ ] Networks are strongly connected (or have large main component)
- [ ] Travel times are reasonable (no negative or zero times)
- [ ] Coordinate ranges match NYC

---

## PHASE 3: Hotspot Identification

### 3.1 HDBSCAN Clustering on Restaurants

**Script**: `src/analysis/clustering.py` → called by `src/analysis/hotspot_identification.py`

**Objective**: Identify dense restaurant zones.

#### 3.1.1 Load Restaurant Data

**Code**:
```python
import geopandas as gpd

gdf_restaurants = gpd.read_file("data/interim/restaurants_merged.geojson")

# Project to meters for distance-based clustering
gdf_restaurants_proj = gdf_restaurants.to_crs("EPSG:2263")

# Extract coordinates
coords = list(zip(gdf_restaurants_proj.geometry.x, gdf_restaurants_proj.geometry.y))
```

#### 3.1.2 Run HDBSCAN

**Code**:
```python
import hdbscan
import numpy as np

# HDBSCAN parameters (CRITICAL: needs tuning/justification)
clusterer = hdbscan.HDBSCAN(
    min_cluster_size=30,      # Minimum 30 restaurants for a cluster
    min_samples=10,           # Conservative estimate
    cluster_selection_epsilon=200,  # 200 meters
    metric='euclidean',       # Already projected to meters
    cluster_selection_method='eom'
)

# Fit
cluster_labels = clusterer.fit_predict(np.array(coords))

# Add to GeoDataFrame
gdf_restaurants_proj['cluster_id'] = cluster_labels

print(f"Found {cluster_labels.max() + 1} clusters")
print(f"Noise points: {(cluster_labels == -1).sum()}")
```

#### 3.1.3 Validate Clusters

**Code**:
```python
from sklearn.metrics import silhouette_score, davies_bouldin_score

# Exclude noise (-1 labels)
valid_mask = cluster_labels != -1
coords_valid = np.array(coords)[valid_mask]
labels_valid = cluster_labels[valid_mask]

if len(set(labels_valid)) > 1:
    sil_score = silhouette_score(coords_valid, labels_valid)
    db_score = davies_bouldin_score(coords_valid, labels_valid)

    print(f"Silhouette Score: {sil_score:.3f} (higher is better, range [-1, 1])")
    print(f"Davies-Bouldin Score: {db_score:.3f} (lower is better)")
else:
    print("WARNING: Only one cluster found, cannot compute validation metrics")
```

**Validation Thresholds**:
- Silhouette > 0.3 (moderate clustering)
- Davies-Bouldin < 1.5 (good separation)

#### 3.1.4 Create Dining Zone Polygons

**Method**: Generate convex hulls or alpha shapes around clusters.

**Code**:
```python
from shapely.ops import unary_union
from shapely.geometry import Point, Polygon

def create_cluster_polygons(gdf, buffer_meters=100):
    """Create polygon for each cluster using convex hull + buffer."""
    polygons = []

    for cluster_id in gdf['cluster_id'].unique():
        if cluster_id == -1:  # Skip noise
            continue

        cluster_points = gdf[gdf['cluster_id'] == cluster_id]

        if len(cluster_points) < 3:  # Need 3+ points for polygon
            continue

        # Create convex hull
        hull = cluster_points.geometry.unary_union.convex_hull

        # Buffer to smooth boundaries
        buffered = hull.buffer(buffer_meters)

        polygons.append({
            'cluster_id': cluster_id,
            'num_restaurants': len(cluster_points),
            'geometry': buffered
        })

    gdf_zones = gpd.GeoDataFrame(polygons, crs=gdf.crs)
    return gdf_zones

gdf_dining_zones = create_cluster_polygons(gdf_restaurants_proj)

# Transform back to WGS84
gdf_dining_zones = gdf_dining_zones.to_crs("EPSG:4326")

# Save
gdf_dining_zones.to_file("data/processed/dining_zones.geojson", driver="GeoJSON")
```

**Validation**:
- [ ] All polygons are valid geometries
- [ ] Number of polygons matches number of clusters
- [ ] Visual inspection: Do zones align with known dining districts?

---

### 3.2 HDBSCAN Clustering on Taxi Drop-offs

**Script**: `src/analysis/hotspot_identification.py`

**Objective**: Identify taxi drop-off hotspots with temporal weighting.

#### 3.2.1 Load and Weight Taxi Data

**Code**:
```python
import pandas as pd

df_taxi = pd.read_parquet("data/interim/taxi_filtered_dining_hours.parquet")

# Define temporal weights
def assign_temporal_weight(row):
    """
    Assign weight based on time desirability for dining.

    Weights:
    - Weekday dinner (Mon-Thu 6-9 PM): 1.0 (baseline)
    - Weekend dinner (Fri-Sun 6-10 PM): 1.5 (higher preference)
    - Lunch (Mon-Fri 12-2 PM): 0.8
    - Breakfast: 0.5
    - Late night: 0.7
    """
    hour = row['hour']
    dow = row['day_of_week']  # 0=Mon, 6=Sun

    is_weekend = (dow >= 4)  # Fri, Sat, Sun

    # Dinner time
    if 18 <= hour <= 21:
        return 1.5 if is_weekend else 1.0
    # Lunch
    elif 12 <= hour <= 14:
        return 0.8 if dow < 5 else 1.0  # Weekday lunch vs weekend brunch
    # Breakfast
    elif 7 <= hour <= 10:
        return 0.5
    # Late night
    elif hour >= 22 or hour < 1:
        return 0.7 if is_weekend else 0.4
    else:
        return 0.3  # Off-peak

df_taxi['weight'] = df_taxi.apply(assign_temporal_weight, axis=1)
```

#### 3.2.2 Aggregate to Spatial Grid (Optional for Performance)

For 20-30 million points, direct clustering may be slow. Consider pre-aggregating to H3 hexagons:

**Code** (using H3):
```python
import h3

def latlon_to_h3(row, resolution=10):
    """Convert lat/lon to H3 hexagon (resolution 10 ≈ 15m edge length)."""
    return h3.geo_to_h3(row['dropoff_latitude'], row['dropoff_longitude'], resolution)

df_taxi['h3_cell'] = df_taxi.apply(latlon_to_h3, axis=1)

# Aggregate weights by hexagon
df_h3_agg = df_taxi.groupby('h3_cell').agg({'weight': 'sum'}).reset_index()

# Convert H3 back to lat/lon
df_h3_agg['lat'] = df_h3_agg['h3_cell'].apply(lambda x: h3.h3_to_geo(x)[0])
df_h3_agg['lon'] = df_h3_agg['h3_cell'].apply(lambda x: h3.h3_to_geo(x)[1])

print(f"Reduced {len(df_taxi):,} points to {len(df_h3_agg):,} hexagons")
```

**Alternative**: Sample if still too large (e.g., 10% random sample).

#### 3.2.3 Run HDBSCAN on Weighted Drop-offs

**Code**:
```python
# Create GeoDataFrame
gdf_taxi = gpd.GeoDataFrame(
    df_h3_agg,
    geometry=gpd.points_from_xy(df_h3_agg.lon, df_h3_agg.lat),
    crs="EPSG:4326"
)

# Project to meters
gdf_taxi_proj = gdf_taxi.to_crs("EPSG:2263")

# Extract coordinates
coords_taxi = list(zip(gdf_taxi_proj.geometry.x, gdf_taxi_proj.geometry.y))
weights = gdf_taxi_proj['weight'].values

# HDBSCAN (note: standard HDBSCAN doesn't use weights directly)
# Workaround: Duplicate points proportional to weight (simplified)
# OR use density-weighted distance metric (advanced)

# Simplified approach: use weight as multiplier for min_cluster_size
clusterer_taxi = hdbscan.HDBSCAN(
    min_cluster_size=50,
    min_samples=15,
    cluster_selection_epsilon=250,  # 250 meters
    metric='euclidean'
)

cluster_labels_taxi = clusterer_taxi.fit_predict(np.array(coords_taxi))

gdf_taxi_proj['cluster_id'] = cluster_labels_taxi

print(f"Found {cluster_labels_taxi.max() + 1} taxi hotspot clusters")
```

#### 3.2.4 Create Hotspot Arrival Area Polygons

**Code**:
```python
gdf_hotspot_areas = create_cluster_polygons(gdf_taxi_proj, buffer_meters=150)

# Calculate total weight per cluster
for idx, row in gdf_hotspot_areas.iterrows():
    cluster_id = row['cluster_id']
    cluster_weight = gdf_taxi_proj[gdf_taxi_proj['cluster_id'] == cluster_id]['weight'].sum()
    gdf_hotspot_areas.loc[idx, 'total_weight'] = cluster_weight

# Transform back to WGS84
gdf_hotspot_areas = gdf_hotspot_areas.to_crs("EPSG:4326")

# Save
gdf_hotspot_areas.to_file("data/processed/taxi_hotspot_areas.geojson", driver="GeoJSON")
```

**Validation**:
- [ ] Clusters align with known high-traffic areas (Times Square, Financial District, etc.)
- [ ] Visual comparison with restaurant clusters

---

### 3.3 Spatial Intersection to Identify Final Dining Hotspots

**Script**: `src/analysis/hotspot_identification.py`

**Objective**: Combine dining zones and taxi hotspots.

#### 3.3.1 Perform Spatial Intersection

**Code**:
```python
# Load both polygon layers
gdf_dining_zones = gpd.read_file("data/processed/dining_zones.geojson")
gdf_hotspot_areas = gpd.read_file("data/processed/taxi_hotspot_areas.geojson")

# Spatial intersection
gdf_intersection = gpd.overlay(
    gdf_dining_zones,
    gdf_hotspot_areas,
    how='intersection',
    keep_geom_type=True
)

print(f"Intersection produced {len(gdf_intersection)} hotspot polygons")
```

#### 3.3.2 Filter by Minimum Overlap

**Code**:
```python
# Calculate area (in projected CRS)
gdf_intersection_proj = gdf_intersection.to_crs("EPSG:2263")
gdf_intersection_proj['area_sqm'] = gdf_intersection_proj.geometry.area

# Filter: Keep only polygons > 10,000 sqm (0.01 sq km)
MIN_AREA_SQM = 10000
gdf_final_hotspots = gdf_intersection_proj[gdf_intersection_proj['area_sqm'] > MIN_AREA_SQM]

print(f"Final hotspots after area filter: {len(gdf_final_hotspots)}")
```

#### 3.3.3 Calculate Hotspot Scores

**Code**:
```python
# Combine restaurant count and taxi weight
gdf_final_hotspots['restaurant_score'] = gdf_final_hotspots['num_restaurants'] / gdf_final_hotspots['num_restaurants'].max()
gdf_final_hotspots['taxi_score'] = gdf_final_hotspots['total_weight'] / gdf_final_hotspots['total_weight'].max()

# Composite score (equal weighting for now)
gdf_final_hotspots['hotspot_score'] = (
    0.5 * gdf_final_hotspots['restaurant_score'] +
    0.5 * gdf_final_hotspots['taxi_score']
)

# Normalize to [0, 100]
gdf_final_hotspots['hotspot_score'] = (gdf_final_hotspots['hotspot_score'] * 100).round(1)
```

#### 3.3.4 Save Final Hotspots

**Code**:
```python
# Transform back to WGS84
gdf_final_hotspots = gdf_final_hotspots.to_crs("EPSG:4326")

# Select relevant columns
gdf_final_hotspots = gdf_final_hotspots[[
    'cluster_id_1',  # From dining zones
    'cluster_id_2',  # From taxi hotspots
    'num_restaurants',
    'total_weight',
    'area_sqm',
    'hotspot_score',
    'geometry'
]]

# Save
gdf_final_hotspots.to_file("data/processed/dining_hotspots_final.geojson", driver="GeoJSON")

print("Final dining hotspots saved!")
```

**Validation**:
- [ ] Ground truth comparison: Do hotspots include Koreatown, Little Italy, Chinatown, Financial District, Williamsburg?
- [ ] Statistical validation: Cross-validation with held-out data
- [ ] Visual inspection on map

---

## PHASE 4: Network Analysis & Accessibility

### 4.1 Build Integrated Multi-Modal Network

**Challenge**: This is the most complex component.

**Recommended Approach**:

**Option A**: Use specialized library (`r5py` for Python, mimics R's `r5r`)
**Option B**: Use external API (Mapbox Directions, Google Directions)
**Option C**: Simplify to walk + drive only (skip transit initially)

#### Option C Example: Walk + Drive Networks

**Code**:
```python
import networkx as nx
import osmnx as ox

# Load networks
G_walk = ox.load_graphml("data/processed/network_dataset/osm_walk_network.graphml")
G_drive = ox.load_graphml("data/processed/network_dataset/osm_drive_network.graphml")

# Already have travel times from section 2.4.2
```

### 4.2 Isochrone Generation

**Script**: `src/analysis/service_area.py`

**Objective**: For a given origin point, calculate areas reachable within time thresholds.

#### 4.2.1 Define Isochrone Function

**Code**:
```python
import networkx as nx
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

def calculate_isochrone(G, origin_point, max_time_min, travel_time_attr='travel_time_min'):
    """
    Calculate isochrone polygon for a given origin.

    Args:
        G: NetworkX graph with travel times
        origin_point: (lat, lon) tuple
        max_time_min: Maximum travel time in minutes
        travel_time_attr: Edge attribute containing travel time

    Returns:
        Polygon representing reachable area
    """
    # Find nearest node to origin
    nearest_node = ox.distance.nearest_nodes(G, origin_point[1], origin_point[0])

    # Calculate shortest paths to all nodes
    lengths = nx.single_source_dijkstra_path_length(
        G,
        nearest_node,
        cutoff=max_time_min,
        weight=travel_time_attr
    )

    # Get nodes within time threshold
    reachable_nodes = list(lengths.keys())

    # Extract node coordinates
    node_coords = [(G.nodes[node]['y'], G.nodes[node]['x']) for node in reachable_nodes]

    # Create convex hull or alpha shape
    points = [Point(lon, lat) for lat, lon in node_coords]

    if len(points) < 3:
        return None

    # Option 1: Convex hull (simple but overestimates)
    # from shapely.ops import unary_union
    # polygon = unary_union(points).convex_hull

    # Option 2: Alpha shape (more accurate)
    from shapely.geometry import MultiPoint
    multipoint = MultiPoint([(lon, lat) for lat, lon in node_coords])
    polygon = multipoint.convex_hull  # Simplified; true alpha shape requires alphashape library

    return polygon

# Example usage
origin = (40.7589, -73.9851)  # Times Square
iso_walk_15min = calculate_isochrone(G_walk, origin, max_time_min=15)
```

#### 4.2.2 Pre-compute Isochrones for Common Locations (Optional)

For a web app, pre-computing isochrones on a grid speeds up response times.

**Code**:
```python
# Create grid of points across NYC
from shapely.geometry import box
import numpy as np

nyc_bbox = box(-74.2591, 40.4774, -73.7004, 40.9176)

# Create 1km grid
lons = np.arange(-74.2591, -73.7004, 0.01)  # ~1 km spacing
lats = np.arange(40.4774, 40.9176, 0.01)

grid_points = [(lat, lon) for lat in lats for lon in lons]

# Calculate isochrones for each grid point
isochrones = []

for point in grid_points:
    iso = calculate_isochrone(G_walk, point, max_time_min=15)
    if iso:
        isochrones.append({
            'origin_lat': point[0],
            'origin_lon': point[1],
            'geometry': iso
        })

gdf_isochrones = gpd.GeoDataFrame(isochrones, crs="EPSG:4326")
gdf_isochrones.to_file("data/processed/isochrones/walk_15min_grid.geojson", driver="GeoJSON")
```

**Note**: This is computationally expensive. Consider parallelization or GPU acceleration.

---

### 4.3 Recommendation Engine

**Script**: `src/analysis/recommendation.py`

**Objective**: Given user location, return ranked hotspots.

#### 4.3.1 Define Recommendation Function

**Code**:
```python
import geopandas as gpd

def recommend_dining_hotspots(user_location, mode='walk', max_time_min=15):
    """
    Recommend dining hotspots accessible from user location.

    Args:
        user_location: (lat, lon) tuple
        mode: 'walk', 'drive', or 'transit'
        max_time_min: Maximum acceptable travel time

    Returns:
        GeoDataFrame of recommended hotspots, ranked by score
    """
    # Load network
    if mode == 'walk':
        G = ox.load_graphml("data/processed/network_dataset/osm_walk_network.graphml")
    elif mode == 'drive':
        G = ox.load_graphml("data/processed/network_dataset/osm_drive_network.graphml")
    else:
        raise ValueError("Transit mode not yet implemented")

    # Calculate isochrone
    isochrone = calculate_isochrone(G, user_location, max_time_min)

    if isochrone is None:
        return gpd.GeoDataFrame()  # Empty result

    # Load hotspots
    gdf_hotspots = gpd.read_file("data/processed/dining_hotspots_final.geojson")

    # Spatial filter: hotspots within isochrone
    gdf_hotspots['within_reach'] = gdf_hotspots.geometry.intersects(isochrone)
    gdf_accessible = gdf_hotspots[gdf_hotspots['within_reach']]

    # Calculate travel time to each hotspot centroid
    for idx, row in gdf_accessible.iterrows():
        hotspot_centroid = row.geometry.centroid
        centroid_coords = (hotspot_centroid.y, hotspot_centroid.x)

        # Find nearest node
        nearest_node = ox.distance.nearest_nodes(G, centroid_coords[1], centroid_coords[0])
        user_nearest_node = ox.distance.nearest_nodes(G, user_location[1], user_location[0])

        # Shortest path length
        try:
            travel_time = nx.shortest_path_length(
                G, user_nearest_node, nearest_node, weight='travel_time_min'
            )
        except nx.NetworkXNoPath:
            travel_time = max_time_min + 1  # Unreachable

        gdf_accessible.loc[idx, 'travel_time_min'] = travel_time

    # Filter out unreachable
    gdf_accessible = gdf_accessible[gdf_accessible['travel_time_min'] <= max_time_min]

    # Normalize scores
    max_travel = gdf_accessible['travel_time_min'].max()
    gdf_accessible['accessibility_score'] = 100 * (1 - gdf_accessible['travel_time_min'] / max_travel)

    # Combined score (60% popularity, 40% accessibility - from config)
    ALPHA = 0.6
    BETA = 0.4

    gdf_accessible['final_score'] = (
        ALPHA * gdf_accessible['hotspot_score'] +
        BETA * gdf_accessible['accessibility_score']
    )

    # Sort by final score
    gdf_accessible = gdf_accessible.sort_values('final_score', ascending=False)

    return gdf_accessible[['num_restaurants', 'hotspot_score', 'travel_time_min',
                           'accessibility_score', 'final_score', 'geometry']]

# Example
user_loc = (40.7589, -73.9851)  # Times Square
recommendations = recommend_dining_hotspots(user_loc, mode='walk', max_time_min=15)
print(recommendations.head())
```

**Validation**:
- [ ] Test with known locations (Times Square, Brooklyn Bridge, etc.)
- [ ] Verify scores are reasonable
- [ ] Check that closer hotspots rank higher (if popularity similar)

---

## PHASE 5: Validation & Testing

### 5.1 Statistical Validation

**Script**: `src/analysis/validation.py`

**Code**:
```python
# Cross-validation: Hold out 20% of taxi data
from sklearn.model_selection import train_test_split

df_taxi_full = pd.read_parquet("data/interim/taxi_filtered_dining_hours.parquet")

df_train, df_test = train_test_split(df_taxi_full, test_size=0.2, random_state=42)

# Re-run clustering on training set
# ... (repeat HDBSCAN steps)

# Test: Do holdout points fall within predicted hotspots?
# Calculate precision, recall, F1
```

### 5.2 Ground Truth Comparison

**Code**:
```python
# Define known dining districts
known_districts = gpd.GeoDataFrame({
    'name': ['Koreatown', 'Little Italy', 'Chinatown'],
    'geometry': [
        Point(-73.9869, 40.7484).buffer(0.005),  # Simplified polygons
        Point(-73.9976, 40.7188).buffer(0.003),
        Point(-73.9977, 40.7158).buffer(0.004)
    ]
}, crs="EPSG:4326")

# Check overlap with predicted hotspots
gdf_hotspots = gpd.read_file("data/processed/dining_hotspots_final.geojson")

for idx, district in known_districts.iterrows():
    overlap = gdf_hotspots.geometry.intersects(district.geometry).sum()
    print(f"{district['name']}: {overlap} hotspots overlap")
```

---

## Summary Checklist

**Data Acquisition**:
- [ ] Downloaded 12 months taxi data (~50-70 GB)
- [ ] Downloaded all GTFS files (7 ZIP files)
- [ ] Extracted OSM networks (drive, walk)
- [ ] Restaurant data in place

**Data Processing**:
- [ ] Filtered taxi data to dining hours (~5-10 GB)
- [ ] Merged and deduplicated restaurant datasets
- [ ] Unpacked GTFS files
- [ ] Created network datasets with travel times

**Analysis**:
- [ ] HDBSCAN clustering on restaurants (validated with silhouette score)
- [ ] HDBSCAN clustering on weighted taxi drop-offs
- [ ] Spatial intersection to create final hotspots
- [ ] Isochrone calculation functional
- [ ] Recommendation engine returns ranked results

**Validation**:
- [ ] Cross-validation with held-out data
- [ ] Ground truth comparison with known districts
- [ ] Visual inspection of all outputs

---

**Total Estimated Processing Time**: 4-8 hours on modern hardware (8+ GB RAM, multi-core CPU)

**Computational Bottlenecks**:
1. Taxi data filtering: ~1-2 hours
2. HDBSCAN on taxi data: ~1-3 hours (depending on aggregation)
3. Isochrone calculation: Minutes to hours (depends on pre-computation strategy)

---

**Next Steps**: Proceed to code development phase using this pipeline as specification.
