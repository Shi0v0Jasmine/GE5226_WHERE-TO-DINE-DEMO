# Complete Data Processing Pipeline
## "Where to DINE" - Step-by-Step Workflow

**Purpose**: Visual guide to the entire data processing workflow from raw data to final recommendations

---

## 📊 Pipeline Overview Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         PHASE 0: SETUP                           │
│  ⏱️ Time: 30 min | 💾 Data: 0 GB                                │
├─────────────────────────────────────────────────────────────────┤
│  1. Create directory structure                                   │
│  2. Install Python dependencies (pip install -r requirements.txt)│
│  3. Configure parameters (config/config.yaml)                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    PHASE 1: DATA ACQUISITION                     │
│  ⏱️ Time: 2-4 hours | 💾 Data: ~70 GB                           │
├─────────────────────────────────────────────────────────────────┤
│  INPUT: None (download from web)                                 │
│  SCRIPTS:                                                         │
│    - scripts/download_taxi_data.sh                               │
│    - scripts/download_gtfs_data.sh                               │
│    - (Restaurant data: already provided)                         │
│                                                                   │
│  OUTPUT:                                                          │
│    ✓ data/raw/taxi/*.parquet (12 files, ~50-70 GB)              │
│    ✓ data/raw/gtfs/*.zip (7 files, ~100 MB)                     │
│    ✓ data/raw/restaurants/*.csv (2 files, ~5 MB)                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              PHASE 2: TAXI DATA PREPROCESSING                    │
│  ⏱️ Time: 30-60 min | 💾 Input: 70 GB → Output: 5 GB (90% ↓)   │
├─────────────────────────────────────────────────────────────────┤
│  INPUT: data/raw/taxi/*.parquet                                  │
│  SCRIPT: src/data_processing/01_extract_taxi_data.py            │
│                                                                   │
│  OPERATIONS:                                                      │
│    1. Load each month's Parquet file                             │
│    2. Temporal filter: Keep only dining hours                    │
│       (7-10 AM, 11-2 PM, 5-10 PM, 10 PM-1 AM)                   │
│    3. Spatial filter: Keep only NYC bounds                       │
│       (lat: 40.48-40.92, lon: -74.26 to -73.70)                 │
│    4. Quality filter: Remove nulls, invalid coordinates          │
│    5. Add temporal columns: hour, day_of_week                    │
│    6. Concatenate all months                                     │
│                                                                   │
│  OUTPUT:                                                          │
│    ✓ data/interim/taxi_filtered_dining_hours.parquet (~5 GB)    │
│    ✓ ~20-30 million records (from 50M)                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│            PHASE 3: RESTAURANT DATA PREPROCESSING                │
│  ⏱️ Time: 5-10 min | 💾 Input: 5 MB → Output: 3 MB              │
├─────────────────────────────────────────────────────────────────┤
│  INPUT:                                                           │
│    - data/raw/restaurants/restaurants_nyc_googlemaps.csv         │
│    - data/raw/restaurants/restaurants_nyc_osm.csv                │
│  SCRIPT: src/data_processing/02_merge_restaurants.py            │
│                                                                   │
│  OPERATIONS:                                                      │
│    1. Load both CSV files                                        │
│    2. Standardize schemas (common columns)                       │
│    3. Convert to GeoDataFrame (lat/lon → Point geometry)         │
│    4. Project to EPSG:2263 (meters for distance calculation)    │
│    5. Spatial deduplication:                                     │
│       - Find pairs within 50 meters                              │
│       - Calculate name similarity (Levenshtein distance)         │
│       - If distance < 50m AND similarity > 80%: merge            │
│    6. Transform back to WGS84                                    │
│                                                                   │
│  OUTPUT:                                                          │
│    ✓ data/interim/restaurants_merged.geojson (~18,500 records)  │
│    ✓ data/interim/restaurants_merged.csv (for compatibility)    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│               PHASE 4: GTFS DATA PREPROCESSING                   │
│  ⏱️ Time: 2-5 min | 💾 Input: 100 MB → Output: 100 MB          │
├─────────────────────────────────────────────────────────────────┤
│  INPUT: data/raw/gtfs/*.zip                                      │
│  SCRIPT: src/data_processing/03_process_gtfs.py                 │
│                                                                   │
│  OPERATIONS:                                                      │
│    1. Unzip all GTFS files                                       │
│    2. Parse stops.txt → GeoDataFrame                            │
│    3. Parse routes.txt                                           │
│    4. (Optional) Convert to network using peartree              │
│                                                                   │
│  OUTPUT:                                                          │
│    ✓ data/interim/gtfs_unpacked/ (directories)                  │
│    ✓ data/processed/transit_stops_subway.geojson                │
│    ✓ data/processed/transit_stops_bus.geojson                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│             PHASE 5: OSM NETWORK EXTRACTION                      │
│  ⏱️ Time: 10-20 min | 💾 Output: 50-100 MB                      │
├─────────────────────────────────────────────────────────────────┤
│  INPUT: None (download via osmnx API)                            │
│  SCRIPT: src/data_processing/04_build_osm_network.py            │
│                                                                   │
│  OPERATIONS:                                                      │
│    1. Define NYC bounding box                                    │
│    2. Download drive network (osmnx.graph_from_bbox)            │
│    3. Download walk network                                      │
│    4. Add travel time attributes to edges:                       │
│       time_min = (length_m / 1000) / speed_kmh × 60             │
│    5. Save as GraphML                                            │
│                                                                   │
│  OUTPUT:                                                          │
│    ✓ data/processed/network_dataset/osm_drive_network.graphml   │
│    ✓ data/processed/network_dataset/osm_walk_network.graphml    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│          PHASE 6: RESTAURANT CLUSTERING (HDBSCAN)                │
│  ⏱️ Time: 5-10 min | 💾 Output: 1-2 MB                          │
├─────────────────────────────────────────────────────────────────┤
│  INPUT: data/interim/restaurants_merged.geojson                  │
│  SCRIPT: src/analysis/clustering.py (function: cluster_restaurants)│
│                                                                   │
│  OPERATIONS:                                                      │
│    1. Load restaurant GeoDataFrame                               │
│    2. Project to EPSG:2263 (meters)                             │
│    3. Extract coordinates as numpy array                         │
│    4. Run HDBSCAN:                                               │
│       - min_cluster_size = 30                                    │
│       - min_samples = 10                                         │
│       - cluster_selection_epsilon = 200 (meters)                 │
│    5. Add cluster_id column                                      │
│    6. Calculate validation metrics (silhouette, Davies-Bouldin) │
│    7. Create cluster polygons (convex hull + 100m buffer)       │
│                                                                   │
│  OUTPUT:                                                          │
│    ✓ data/processed/dining_zones.geojson (~30 clusters)         │
│    ✓ Validation metrics logged                                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│      PHASE 7: TAXI DROP-OFF CLUSTERING (WITH WEIGHTING)          │
│  ⏱️ Time: 15-30 min | 💾 Input: 5 GB → Output: 2 MB             │
├─────────────────────────────────────────────────────────────────┤
│  INPUT: data/interim/taxi_filtered_dining_hours.parquet          │
│  SCRIPT: src/analysis/clustering.py (function: cluster_taxi_dropoffs)│
│                                                                   │
│  OPERATIONS:                                                      │
│    1. Load taxi data                                             │
│    2. Apply temporal weighting function w(t, d)                  │
│    3. Aggregate to H3 hexagons (resolution 10):                 │
│       - 50M points → 500k hexagons (96% reduction!)             │
│    4. Project hexagon centroids to EPSG:2263                    │
│    5. Run HDBSCAN:                                               │
│       - min_cluster_size = 50                                    │
│       - min_samples = 15                                         │
│       - cluster_selection_epsilon = 250                          │
│    6. Calculate total weighted drops per cluster                │
│    7. Create cluster polygons (convex hull + 150m buffer)       │
│                                                                   │
│  OUTPUT:                                                          │
│    ✓ data/processed/taxi_hotspot_areas.geojson (~50 clusters)   │
│    ✓ Each with 'total_weight' attribute                         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│         PHASE 8: SPATIAL INTERSECTION (FINAL HOTSPOTS)           │
│  ⏱️ Time: 1-2 min | 💾 Output: 500 KB                           │
├─────────────────────────────────────────────────────────────────┤
│  INPUT:                                                           │
│    - data/processed/dining_zones.geojson                         │
│    - data/processed/taxi_hotspot_areas.geojson                   │
│  SCRIPT: src/analysis/hotspot_identification.py                 │
│                                                                   │
│  OPERATIONS:                                                      │
│    1. Load both polygon layers                                   │
│    2. Nested loop: for each dining zone × taxi zone:            │
│       a. Compute geometric intersection                          │
│       b. Skip if empty                                           │
│       c. Check filters:                                          │
│          - area(intersection) ≥ 10,000 m²                       │
│          - overlap_ratio ≥ 0.15 (15%)                           │
│       d. If passes: add to final hotspots list                  │
│    3. Calculate composite scores:                                │
│       hotspot_score = 0.5 × restaurant_score + 0.5 × taxi_score│
│    4. Normalize to [0, 100]                                      │
│                                                                   │
│  OUTPUT:                                                          │
│    ✓ data/processed/dining_hotspots_final.geojson (~47 hotspots)│
│    ✓ Each with: num_restaurants, total_weight, hotspot_score    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              PHASE 9: VALIDATION & ANALYSIS                      │
│  ⏱️ Time: 10-20 min | 💾 Output: Reports & figures              │
├─────────────────────────────────────────────────────────────────┤
│  INPUT: data/processed/dining_hotspots_final.geojson             │
│  SCRIPT: src/analysis/validation.py                             │
│                                                                   │
│  OPERATIONS:                                                      │
│    1. Ground truth comparison:                                   │
│       - Load known dining districts (Chinatown, Koreatown, etc.)│
│       - Calculate spatial overlap                                │
│       - Compute accuracy metrics                                 │
│    2. Statistical validation:                                    │
│       - Correlation tests (taxi vs. restaurant density)          │
│       - Clustering significance (Monte Carlo simulation)         │
│    3. Generate validation visualizations                         │
│                                                                   │
│  OUTPUT:                                                          │
│    ✓ outputs/reports/validation_metrics.json                     │
│    ✓ outputs/figures/ground_truth_comparison.png                │
│    ✓ outputs/figures/cluster_validation.png                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│         PHASE 10: VISUALIZATION & PRESENTATION                   │
│  ⏱️ Time: 20-30 min | 💾 Output: HTML maps, PNG figures         │
├─────────────────────────────────────────────────────────────────┤
│  INPUT: All processed data                                       │
│  SCRIPTS:                                                         │
│    - src/visualization/maps.py                                   │
│    - src/visualization/plots.py                                  │
│    - notebooks/06_final_demo.ipynb                              │
│                                                                   │
│  OPERATIONS:                                                      │
│    1. Create interactive maps (Folium):                          │
│       - All hotspots with scores                                 │
│       - Clustering results comparison                            │
│       - Isochrone examples                                       │
│    2. Create static figures (Matplotlib):                        │
│       - Temporal distribution charts                             │
│       - Cluster validation plots                                 │
│       - Score distribution histograms                            │
│    3. Generate presentation demo                                 │
│                                                                   │
│  OUTPUT:                                                          │
│    ✓ outputs/maps/final_hotspots_map.html                       │
│    ✓ outputs/maps/clustering_comparison.html                    │
│    ✓ outputs/figures/*.png (publication-quality)                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│       PHASE 11: RECOMMENDATION ENGINE (INTERACTIVE)              │
│  ⏱️ Time: Real-time (2-5 sec per query) | 💾 Output: JSON       │
├─────────────────────────────────────────────────────────────────┤
│  INPUT:                                                           │
│    - User location (lat, lon)                                    │
│    - Mode (walk, drive, transit)                                 │
│    - Max time (minutes)                                          │
│  SCRIPT: src/analysis/recommendation.py                         │
│                                                                   │
│  OPERATIONS:                                                      │
│    1. Load network graph (for selected mode)                     │
│    2. Find nearest network node to user location                 │
│    3. Calculate isochrone (Dijkstra shortest path with cutoff)  │
│    4. Spatial query: hotspots intersecting isochrone             │
│    5. For each accessible hotspot:                               │
│       a. Calculate exact travel time                             │
│       b. Compute accessibility_score = 100 × (1 - t/t_max)     │
│       c. Compute final_score = α·P + β·A                        │
│    6. Sort by final_score descending                             │
│    7. Return top K results                                       │
│                                                                   │
│  OUTPUT:                                                          │
│    ✓ JSON with ranked hotspots                                   │
│    ✓ Isochrone polygon (GeoJSON)                                │
└─────────────────────────────────────────────────────────────────┘

```

---

## 📋 Quick Reference: File Dependencies

### Input → Script → Output Chain

```
RAW DATA FILES
├── taxi/*.parquet (70 GB)
├── restaurants/*.csv (5 MB)
└── gtfs/*.zip (100 MB)
       ↓
PROCESSING SCRIPTS (src/data_processing/)
├── 01_extract_taxi_data.py
├── 02_merge_restaurants.py
├── 03_process_gtfs.py
└── 04_build_osm_network.py
       ↓
INTERIM DATA FILES
├── taxi_filtered_dining_hours.parquet (5 GB)
├── restaurants_merged.geojson (3 MB)
└── gtfs_unpacked/* (100 MB)
       ↓
ANALYSIS SCRIPTS (src/analysis/)
├── clustering.py → dining_zones.geojson, taxi_hotspot_areas.geojson
├── hotspot_identification.py → dining_hotspots_final.geojson
├── network_analysis.py → (loads networks)
├── service_area.py → (generates isochrones)
└── recommendation.py → (returns recommendations)
       ↓
FINAL OUTPUTS
├── data/processed/dining_hotspots_final.geojson (500 KB)
├── outputs/maps/*.html
├── outputs/figures/*.png
└── outputs/reports/*.json
```

---

## 🎯 Execution Order: Master Script

**Option 1**: Run each script manually
```bash
# Phase 2
python src/data_processing/01_extract_taxi_data.py

# Phase 3
python src/data_processing/02_merge_restaurants.py

# Phase 4
python src/data_processing/03_process_gtfs.py

# Phase 5
python src/data_processing/04_build_osm_network.py

# Phase 6-8 (combined in one script)
python src/analysis/run_full_analysis.py

# Phase 9
python src/analysis/validation.py

# Phase 10
python src/visualization/generate_all_maps.py
```

**Option 2**: Run master script (I can create this)
```bash
python run_full_pipeline.py
```

---

## ⚡ Performance Summary

| Phase | Time | Bottleneck | Optimization |
|-------|------|------------|--------------|
| Data download | 2-4 hours | Network I/O | Use fast internet |
| Taxi filtering | 30-60 min | Disk I/O | Use SSD, Parquet format |
| Restaurant merge | 5-10 min | Spatial join | R-tree index |
| GTFS parsing | 2-5 min | Unzip | - |
| OSM download | 10-20 min | API rate limit | Retry logic |
| Restaurant clustering | 5-10 min | HDBSCAN | Already fast for 18k points |
| Taxi clustering | 15-30 min | HDBSCAN | **H3 aggregation (critical!)** |
| Intersection | 1-2 min | Geometry ops | R-tree index |
| Validation | 10-20 min | - | - |
| Visualization | 20-30 min | - | - |
| **TOTAL** | **4-6 hours** | - | - |

---

## 🔍 Critical Decision Points

### Decision 1: Do you have the taxi data?
- **YES** → Proceed with full pipeline
- **NO** → Start with restaurant clustering only (Phase 6)

### Decision 2: Do you want to download OSM networks?
- **YES** → Proceed with Phase 5
- **NO (use pre-computed)** → Skip to Phase 6

### Decision 3: Do you want transit routing?
- **YES** → Include Phase 4 (GTFS)
- **NO (walk + drive only)** → Skip Phase 4, simpler implementation

### Decision 4: Do you want a web app?
- **YES** → Add Phase 12 (Flask/FastAPI)
- **NO (Jupyter demo only)** → Stop at Phase 10

---

## 📦 What I Can Code For You Now

I can immediately write:

### **Essential Scripts** (Must Have):
1. ✅ `01_extract_taxi_data.py` - Taxi filtering
2. ✅ `02_merge_restaurants.py` - Restaurant deduplication
3. ✅ `03_process_gtfs.py` - GTFS parsing
4. ✅ `04_build_osm_network.py` - OSM download
5. ✅ `clustering.py` - HDBSCAN wrapper
6. ✅ `hotspot_identification.py` - Spatial intersection
7. ✅ `recommendation.py` - Recommendation engine

### **Utility Scripts** (Very Helpful):
8. ✅ `temporal_utils.py` - Weighting functions
9. ✅ `spatial_utils.py` - CRS transforms, distance calculations
10. ✅ `run_full_pipeline.py` - Master orchestration script

### **Analysis Scripts** (Nice to Have):
11. ✅ `validation.py` - Statistical validation
12. ✅ `generate_all_maps.py` - Visualization pipeline

### **Notebooks** (For Exploration):
13. ✅ `01_EDA_taxi_data.ipynb`
14. ✅ `02_EDA_restaurants.ipynb`
15. ✅ `03_clustering_experiments.ipynb`
16. ✅ `06_final_demo.ipynb`

---

## 🚀 Recommended Starting Point

### **If you have NO data yet**:
Start with: **Mock data testing**
- I'll create synthetic data generators
- Test the entire pipeline with fake data
- Verify code works before downloading 70 GB

### **If you have restaurant data only**:
Start with: **Phase 3 + Phase 6**
- Merge restaurants
- Cluster restaurants
- Visualize dining zones

### **If you have all data**:
Start with: **Full pipeline**
- I'll write all scripts in order
- We run each phase sequentially
- Debug as we go

---

## ❓ Tell Me Your Situation

**Answer these questions:**

1. **Do you have the data?**
   - [ ] Yes, I have taxi data (all 12 months)
   - [ ] Yes, I have restaurant data
   - [ ] Yes, I have GTFS data
   - [ ] No, I have nothing yet

2. **What's your priority?**
   - [ ] Get something working ASAP (start small)
   - [ ] Build complete system (take time)
   - [ ] Just test concepts (mock data)

3. **What do you want first?**
   - [ ] Data processing scripts (Phase 2-5)
   - [ ] Analysis scripts (Phase 6-8)
   - [ ] Visualization (Phase 10)
   - [ ] Everything in order (Phase 2 → Phase 11)

**Tell me and I'll start writing code immediately!** 🚀
