# GE5226 WHERE-TO-DINE-DEMO Project Structure

## Project Overview
A NYC restaurant recommendation system based on real data, using taxi dropoff data as a "voting with feet" popularity indicator, combined with spatial analysis and clustering algorithms to identify and recommend dining hotspots.

---

## Directory Structure Tree

```
GE5226_WHERE-TO-DINE-DEMO/
│
├── 📄 Core Files
│   ├── app.py                      # Flask Web Application Entry Point
│   ├── run_pipeline.py             # Data Processing Pipeline Controller
│   ├── requirements.txt            # Python Dependencies List
│   ├── .gitattributes             # Git LFS Configuration (Large File Management)
│   ├── README_DEMO.md             # Web Demo Documentation
│   └── WEB_DEMO_GUIDE.md          # Web Demo User Guide
│
├── 📁 src/                        # Source Code Directory
│   ├── __init__.py
│   │
│   ├── data_processing/           # Data Processing Module
│   │   ├── __init__.py
│   │   ├── 02_process_taxi_data.py       # Taxi Data Processing
│   │   ├── 02_merge_restaurants.py       # Restaurant Data Merging
│   │   ├── 06_cluster_restaurants.py     # Restaurant Clustering Analysis
│   │   ├── 07_cluster_taxi_dropoffs.py   # Taxi Dropoff Clustering
│   │   └── 08_spatial_intersection.py    # Spatial Intersection Analysis
│   │
│   ├── analysis/                  # Analysis Algorithm Module
│   │   ├── __init__.py
│   │   ├── clustering.py          # Clustering Algorithms (HDBSCAN)
│   │   └── isochrone.py          # Isochrone Analysis (Accessibility)
│   │
│   ├── visualization/             # Visualization Module
│   │   ├── __init__.py
│   │   └── 01_visualize_results.py  # Results Visualization
│   │
│   └── utils/                     # Utility Functions
│       ├── __init__.py
│       └── config_loader.py       # Configuration File Loader
│
├── 📁 data/                       # Data Directory
│   │
│   ├── raw/                       # Raw Data
│   │   ├── taxi/                  # Taxi Data (2024 Jan-Dec)
│   │   │   ├── yellow_tripdata_2024-01.parquet
│   │   │   ├── yellow_tripdata_2024-02.parquet
│   │   │   ├── ...
│   │   │   └── yellow_tripdata_2024-12.parquet
│   │   │
│   │   ├── restaurants/           # Restaurant Data
│   │   │   ├── restaurants_nyc_osm.geojson
│   │   │   ├── restaurants_nyc_osm.csv
│   │   │   └── restaurants_nyc_googlemaps.csv
│   │   │
│   │   ├── gtfs/                  # GTFS Transit Data
│   │   │   ├── gtfs_subway.zip    # Subway
│   │   │   ├── gtfs_b.zip         # Brooklyn Bus
│   │   │   ├── gtfs_bx.zip        # Bronx Bus
│   │   │   ├── gtfs_m.zip         # Manhattan Bus
│   │   │   ├── gtfs_q.zip         # Queens Bus
│   │   │   ├── gtfs_si.zip        # Staten Island Bus
│   │   │   ├── gtfs_busco.zip     # Other Buses
│   │   │   └── README.txt
│   │   │
│   │   └── osm/                   # OpenStreetMap Data
│   │       └── new-york-251104.osm.pbf
│   │
│   ├── interim/                   # Intermediate Processing Data
│   │   ├── taxi_dropoffs_weighted.parquet
│   │   ├── taxi_dropoffs_weighted_sample.geojson
│   │   ├── taxi_processing_summary.json
│   │   ├── restaurants_merged.csv
│   │   └── restaurants_merged.geojson
│   │
│   ├── processed/                 # Final Processed Data
│   │   ├── final_hotspots.geojson           # Final Recommended Hotspots
│   │   ├── dining_zones.geojson             # Dining Zones
│   │   ├── restaurants_clustered.geojson    # Clustered Restaurants
│   │   ├── taxi_dropoffs_clustered.parquet  # Clustered Taxi Data
│   │   ├── taxi_hotspots.geojson           # Taxi Hotspots
│   │   ├── taxi_clustering_metrics.json     # Taxi Clustering Metrics
│   │   ├── clustering_metrics.json          # Clustering Evaluation Metrics
│   │   └── intersection_analysis.json       # Spatial Intersection Analysis Results
│   │
│   └── external/                  # External Reference Data
│       └── boundaries/            # Boundary Data
│           ├── nybb.shp           # NYC Borough Boundaries
│           ├── nybb.dbf
│           ├── nybb.prj
│           ├── nybb.shx
│           ├── nybb.shp.xml
│           ├── taxi_zones.shp     # Taxi Zone Boundaries
│           ├── taxi_zones.dbf
│           ├── taxi_zones.prj
│           ├── taxi_zones.shx
│           ├── taxi_zones.sbn
│           ├── taxi_zones.sbx
│           └── taxi_zones.shp.xml
│
├── 📁 outputs/                    # Output Results Directory
│   ├── figures/                   # Figures
│   ├── maps/                      # Maps
│   ├── reports/                   # Reports
│   └── tables/                    # Data Tables
│
├── 📁 templates/                  # Web Templates
│   └── index.html                 # Web Application Main Page
│
├── 📁 config/                     # Configuration Files Directory
│
├── 📁 cache/                      # Cache Files (JSON format)
│   └── [Multiple cache files.json]
│
└── 📁 docs/                       # Documentation Directory
    ├── ACADEMIC_EVALUATION.md           # Academic Evaluation Document
    ├── DATA_PROCESSING_PIPELINE.md      # Data Processing Pipeline Description
    ├── DIRECTORY_STRUCTURE.md           # Directory Structure Description
    ├── FINAL_REPORT_TEMPLATE.md         # Final Report Template
    ├── PIPELINE_OVERVIEW.md             # Pipeline Overview
    ├── PRESENTATION_GUIDE.md            # Presentation Guide
    ├── PRESENTATION_SPEECH.md           # Presentation Speech
    ├── SYSTEM_ARCHITECTURE.md           # System Architecture Document
    ├── TASK_CHECKLIST.md               # Task Checklist
    │
    └── methodology/                     # Methodology Documents
        ├── isochrone_thresholds.md      # Isochrone Threshold Settings
        ├── recommendation_scoring.md     # Recommendation Scoring Algorithm
        ├── spatial_intersection_criteria.md  # Spatial Intersection Criteria
        └── temporal_weighting.md        # Temporal Weighting Calculation
```

---

## Core Module Description

### 1. Web Application Layer (app.py)
- **Tech Stack**: Flask + Leaflet.js
- **Features**:
  - Interactive map displaying dining hotspots
  - Click-on-map to get nearby recommendations
  - Smart ranking based on distance and popularity
  - Real-time display of top 10 recommendations

### 2. Data Processing Pipeline (run_pipeline.py + src/data_processing/)
Data processing executed in numbered order:

1. **02_merge_restaurants.py** - Merge OSM and Google Maps restaurant data
2. **02_process_taxi_data.py** - Process 2024 full-year taxi dropoff data
3. **06_cluster_restaurants.py** - Use HDBSCAN for restaurant spatial clustering
4. **07_cluster_taxi_dropoffs.py** - Cluster analysis of taxi dropoff points
5. **08_spatial_intersection.py** - Spatial intersection analysis to identify true dining hotspots

### 3. Analysis Algorithms (src/analysis/)
- **clustering.py**: HDBSCAN clustering algorithm implementation
- **isochrone.py**: OSM road network-based isochrone accessibility analysis

### 4. Visualization (src/visualization/)
- **01_visualize_results.py**: Generate various maps and charts

---

## Data Flow Diagram

```
Raw Data (raw/)
    │
    ├─> Taxi Data (12 months Parquet) ──┐
    ├─> Restaurant Data (OSM + Google) ───┤
    ├─> GTFS Transit Data ──────────────┤
    └─> OSM Road Network Data ───────────┤
                                   │
                                   ↓
                          Intermediate Processing (interim/)
                                   │
                ┌──────────────────┴──────────────────┐
                ↓                                     ↓
         Restaurant Data Merging                Taxi Data Processing
         restaurants_merged                    taxi_dropoffs_weighted
                │                                     │
                ↓                                     ↓
            Restaurant Clustering                Taxi Clustering
         (HDBSCAN)                               (HDBSCAN)
                │                                     │
                └──────────────┬──────────────────────┘
                               ↓
                        Spatial Intersection Analysis
                    (Spatial Intersection)
                               │
                               ↓
                      Final Results (processed/)
                               │
                    ┌──────────┴──────────┐
                    ↓                     ↓
              final_hotspots        clustering_metrics
                    │                     │
                    └──────────┬──────────┘
                               ↓
                         Web Application Display
                          (app.py)
```

---

## Technology Stack Summary

### Backend Technologies
- **Python 3.9+**: Primary development language
- **Flask**: Web framework
- **GeoPandas**: Geospatial data processing
- **HDBSCAN**: Density-based clustering algorithm
- **OSMnx**: OpenStreetMap road network analysis
- **Pandas/NumPy**: Data processing

### Frontend Technologies
- **Leaflet.js**: Interactive maps
- **HTML/CSS/JavaScript**: Basic web technologies

### Data Formats
- **Parquet**: Efficient columnar storage (taxi data)
- **GeoJSON**: Geospatial data exchange format
- **Shapefile**: GIS standard format (boundary data)
- **CSV**: Universal data format

### Dependency Management
- **Git LFS**: Large file version control (.parquet, .pbf files)

---

## Key Algorithms

### 1. HDBSCAN Clustering
- Hierarchical density-based clustering
- Automatically discovers clusters of varying densities
- Can identify noise points

### 2. Spatial Intersection Analysis
- Restaurant Clusters ∩ Taxi Hotspots
- Identifies high-popularity dining areas

### 3. Recommendation Scoring
- Combines distance and popularity
- Considers temporal weights
- Multi-dimensional evaluation

---

## Project Features

1. **Real Data-Driven**: Uses 2024 full-year NYC taxi data (~140 million records)
2. **Multi-Source Data Fusion**: Integrates OSM, Google Maps, GTFS, and other data sources
3. **Academic Rigor**: Complete methodology documentation and evaluation metrics
4. **Practicality**: Provides interactive web demo application
5. **Extensibility**: Modular design, easy to extend and maintain

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run data processing pipeline
python run_pipeline.py

# 3. Start web application
python app.py

# 4. Visit http://localhost:5000
```

---

## Documentation Navigation

- **Development Documentation**: `/docs/SYSTEM_ARCHITECTURE.md`
- **Data Pipeline**: `/docs/DATA_PROCESSING_PIPELINE.md`
- **Methodology**: `/docs/methodology/`
- **Demo Guide**: `/WEB_DEMO_GUIDE.md`
- **Academic Evaluation**: `/docs/ACADEMIC_EVALUATION.md`

---

**Project Type**: GE5226 Course Project - Geographic Information Systems and Spatial Analysis
**Topic**: NYC Restaurant Recommendation System (Where to DINE)
**Data Scale**: ~140 million taxi records + tens of thousands of restaurant POIs
**Technical Difficulty**: Advanced (Big Data Processing + Spatial Analysis + Web Development)
