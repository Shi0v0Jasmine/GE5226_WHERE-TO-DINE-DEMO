# Directory Structure Documentation

## Overview

This document explains the organization of the "Where to DINE" project repository, following best practices for reproducible geospatial research.

---

## Directory Tree

```
Where-to-dine-final-version/
├── README.md                          # Project overview and quick start guide
├── LICENSE                            # Project license (recommend MIT or Apache 2.0)
├── requirements.txt                   # Python dependencies
├── environment.yml                    # Conda environment specification
├── .gitignore                         # Git ignore rules
├── .github/                           # GitHub-specific files
│   └── workflows/                     # CI/CD workflows (optional)
│
├── config/                            # Configuration files
│   ├── config.yaml                    # Main configuration file
│   ├── clustering_params.yaml         # HDBSCAN and clustering parameters
│   ├── network_params.yaml            # Network analysis parameters
│   └── paths.yaml                     # Data paths configuration
│
├── data/                              # Data directory (LARGE - see .gitignore)
│   ├── raw/                           # Original, immutable data
│   │   ├── taxi/                      # NYC TLC taxi data
│   │   │   ├── yellow_tripdata_2024-01.parquet
│   │   │   ├── yellow_tripdata_2024-02.parquet
│   │   │   └── ...                    # (12 months total)
│   │   ├── restaurants/               # Restaurant datasets
│   │   │   ├── restaurants_nyc_googlemaps.csv
│   │   │   ├── restaurants_nyc_osm.csv
│   │   │   └── restaurants_nyc_osm.geojson
│   │   ├── gtfs/                      # Transit data
│   │   │   ├── gtfs_subway.zip
│   │   │   ├── gtfs_bx.zip            # Bronx buses
│   │   │   ├── gtfs_b.zip             # Brooklyn buses
│   │   │   ├── gtfs_q.zip             # Queens buses
│   │   │   ├── gtfs_si.zip            # Staten Island buses
│   │   │   ├── gtfs_m.zip             # Manhattan buses
│   │   │   └── gtfs_busco.zip         # MTA Bus Company
│   │   └── osm/                       # OpenStreetMap data
│   │       ├── nyc_roads.geojson      # Road network
│   │       └── nyc_pedestrian.geojson # Pedestrian network
│   │
│   ├── interim/                       # Intermediate data (cleaned, transformed)
│   │   ├── taxi_filtered_dining_hours.parquet
│   │   ├── restaurants_merged.geojson
│   │   └── gtfs_unpacked/             # Unzipped GTFS files
│   │
│   ├── processed/                     # Final data ready for analysis
│   │   ├── restaurant_clusters.geojson
│   │   ├── taxi_hotspots.geojson
│   │   ├── dining_hotspots_final.geojson
│   │   ├── network_dataset/           # Multi-modal network
│   │   └── isochrones/                # Pre-computed service areas
│   │
│   └── external/                      # External reference data
│       ├── nyc_boroughs.geojson
│       ├── nyc_neighborhoods.geojson
│       └── census_tracts.geojson
│
├── src/                               # Source code
│   ├── __init__.py
│   │
│   ├── data_processing/               # Data preprocessing scripts
│   │   ├── __init__.py
│   │   ├── 01_extract_taxi_data.py    # Extract and filter taxi data
│   │   ├── 02_merge_restaurants.py    # Merge restaurant datasets
│   │   ├── 03_process_gtfs.py         # Process GTFS data
│   │   └── 04_build_osm_network.py    # Extract OSM network
│   │
│   ├── analysis/                      # Core analysis modules
│   │   ├── __init__.py
│   │   ├── clustering.py              # HDBSCAN clustering functions
│   │   ├── hotspot_identification.py  # Hotspot detection pipeline
│   │   ├── network_analysis.py        # Multi-modal routing
│   │   ├── service_area.py            # Isochrone generation
│   │   ├── recommendation.py          # Recommendation scoring
│   │   └── validation.py              # Statistical validation
│   │
│   ├── visualization/                 # Plotting and mapping
│   │   ├── __init__.py
│   │   ├── maps.py                    # Static map generation
│   │   ├── interactive_maps.py        # Interactive Folium/Plotly maps
│   │   └── plots.py                   # Statistical plots
│   │
│   ├── web_app/                       # Web application (if implemented)
│   │   ├── __init__.py
│   │   ├── app.py                     # Flask/FastAPI application
│   │   ├── api/                       # API endpoints
│   │   ├── static/                    # CSS, JS, images
│   │   └── templates/                 # HTML templates
│   │
│   └── utils/                         # Utility functions
│       ├── __init__.py
│       ├── spatial_utils.py           # CRS transformations, distance calculations
│       ├── temporal_utils.py          # Time window filtering, weighting
│       └── config_loader.py           # Configuration file loading
│
├── notebooks/                         # Jupyter notebooks for exploration
│   ├── 01_EDA_taxi_data.ipynb
│   ├── 02_EDA_restaurants.ipynb
│   ├── 03_clustering_experiments.ipynb
│   ├── 04_network_analysis_test.ipynb
│   ├── 05_validation.ipynb
│   └── 06_final_demo.ipynb
│
├── tests/                             # Unit tests
│   ├── __init__.py
│   ├── test_clustering.py
│   ├── test_network_analysis.py
│   └── test_recommendation.py
│
├── docs/                              # Documentation
│   ├── ACADEMIC_EVALUATION.md         # Academic critique (this file)
│   ├── DIRECTORY_STRUCTURE.md         # This file
│   ├── DATA_PROCESSING_PIPELINE.md    # Detailed processing steps
│   ├── METHODOLOGY.md                 # Detailed methodology
│   ├── TASK_CHECKLIST.md              # Comprehensive task list
│   ├── PRESENTATION_GUIDE.md          # Presentation structure
│   ├── figures/                       # Figures for reports
│   ├── references/                    # BibTeX, EndNote files
│   └── methodology/                   # Detailed methodology docs
│
└── outputs/                           # Generated outputs
    ├── maps/                          # Output maps (PNG, PDF)
    ├── figures/                       # Plots and charts
    ├── tables/                        # CSV, Excel tables
    └── reports/                       # Generated reports
        ├── final_report.pdf
        └── presentation_slides.pdf

```

---

## Directory Descriptions

### 📁 `data/`

**PURPOSE**: Store all data assets. **NEVER commit large files to Git.**

#### `data/raw/`
- **Immutable**: Original data, never modified
- **Sources**: Downloaded directly from NYC Open Data, Google Maps API, OSM
- **Size**: ~50-100 GB (taxi data is large)
- **Git Strategy**: Add `data/raw/` to `.gitignore`, document download sources in README

#### `data/interim/`
- **Semi-processed**: Cleaned but not fully analyzed
- **Examples**: Filtered taxi records, merged restaurant files
- **Git Strategy**: Ignore (regenerate from raw)

#### `data/processed/`
- **Analysis-ready**: Final datasets used for modeling
- **Examples**: Identified hotspots, network datasets
- **Git Strategy**: Consider committing small final outputs (<10 MB) for reproducibility

#### `data/external/`
- **Reference data**: Administrative boundaries, census data
- **Size**: Typically small (<1 MB)
- **Git Strategy**: Commit if small, otherwise document source

---

### 📁 `src/`

**PURPOSE**: All reusable Python code.

#### `src/data_processing/`
- **Scripts**: Numbered for sequential execution (01_, 02_, etc.)
- **Input**: Raw data
- **Output**: Interim/processed data
- **Key Functions**:
  - Filter taxi data by time windows
  - Merge duplicate restaurants
  - Unzip and parse GTFS
  - Extract OSM network

#### `src/analysis/`
- **Core logic**: Clustering, routing, scoring algorithms
- **Modular design**: Each file has focused responsibility
- **Testing**: All functions should have unit tests
- **Key Modules**:
  - `clustering.py`: HDBSCAN wrapper with parameter tuning
  - `hotspot_identification.py`: Full pipeline from raw data to hotspots
  - `network_analysis.py`: Multi-modal routing using OSMnx/Pandana/r5py
  - `service_area.py`: Isochrone generation
  - `recommendation.py`: Scoring and ranking logic
  - `validation.py`: Cross-validation, statistical tests

#### `src/visualization/`
- **Static maps**: Matplotlib, Contextily for publication-quality figures
- **Interactive maps**: Folium, Plotly, Kepler.gl for web
- **Plots**: Seaborn/Matplotlib for statistical charts

#### `src/web_app/` (Optional)
- **Framework options**: Flask (simple), FastAPI (modern), Streamlit (quick)
- **API endpoints**: `/recommend`, `/isochrone`, `/hotspots`
- **Frontend**: Leaflet.js or Mapbox GL JS for map interface

---

### 📁 `notebooks/`

**PURPOSE**: Exploratory analysis, experiments, demonstrations.

**Best Practices**:
- **Numbered**: Use `01_`, `02_` prefix for logical order
- **Descriptive names**: `03_clustering_experiments.ipynb`, not `test.ipynb`
- **Narrative**: Include markdown cells explaining each step
- **Reproducible**: Clear all outputs before committing, or use `nbstripout`

---

### 📁 `tests/`

**PURPOSE**: Automated testing for code quality.

**Framework**: pytest

**Example Tests**:
- `test_clustering.py`: Verify HDBSCAN returns expected cluster count
- `test_network_analysis.py`: Test routing returns valid paths
- `test_recommendation.py`: Ensure scores are normalized [0, 1]

**Run**: `pytest tests/`

---

### 📁 `config/`

**PURPOSE**: Centralize all parameters.

**Benefits**:
- No hardcoded values in code
- Easy parameter tuning
- Document all assumptions

**Example `config.yaml`**:
```yaml
data:
  taxi_raw_dir: "data/raw/taxi/"
  restaurants_merged: "data/interim/restaurants_merged.geojson"

clustering:
  min_cluster_size: 50
  min_samples: 10
  metric: "haversine"

network:
  walking_speed_kmh: 4.8
  max_walking_time_min: 15
  transfer_penalty_min: 5

recommendation:
  alpha_popularity: 0.6  # Weight for popularity
  beta_accessibility: 0.4  # Weight for accessibility
```

---

### 📁 `docs/`

**PURPOSE**: All documentation beyond code.

**Contents**:
- Methodology details
- Literature review
- Academic evaluation
- User guides
- API documentation

---

### 📁 `outputs/`

**PURPOSE**: Generated results (maps, figures, reports).

**Git Strategy**:
- Commit final publication-ready outputs
- Ignore intermediate exploratory figures

---

## Data Size Management

### Expected Sizes:
- **Taxi data (raw)**: ~50-70 GB (12 months)
- **GTFS data**: ~100 MB (all boroughs)
- **Restaurant data**: ~5 MB
- **OSM network**: ~50-100 MB
- **Processed hotspots**: ~1-5 MB

### Git LFS (Large File Storage):
For files 10 MB - 1 GB, consider Git LFS:
```bash
git lfs track "*.parquet"
git lfs track "data/processed/*.geojson"
```

### .gitignore Strategy:
```
# Ignore all data except external reference
data/raw/
data/interim/
data/processed/taxi_*
data/processed/network_dataset/

# Exception: commit small final outputs
!data/processed/dining_hotspots_final.geojson
!data/external/
```

---

## Workflow Example

### 1. Data Acquisition:
```bash
# Download taxi data
cd data/raw/taxi/
wget https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-01.parquet
# ... (repeat for all months)

# Download GTFS
cd ../gtfs/
wget http://web.mta.info/developers/data/nyct/subway/google_transit.zip
mv google_transit.zip gtfs_subway.zip
```

### 2. Data Processing:
```bash
cd ../../..  # Back to root
python src/data_processing/01_extract_taxi_data.py
python src/data_processing/02_merge_restaurants.py
python src/data_processing/03_process_gtfs.py
python src/data_processing/04_build_osm_network.py
```

### 3. Analysis:
```bash
jupyter notebook notebooks/03_clustering_experiments.ipynb
# OR
python -c "from src.analysis.hotspot_identification import identify_hotspots; identify_hotspots()"
```

### 4. Generate Outputs:
```bash
python src/visualization/generate_all_maps.py
```

---

## Version Control Best Practices

### Commit Message Convention:
```
type(scope): subject

[optional body]
[optional footer]
```

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

**Examples**:
```
feat(clustering): implement HDBSCAN with parameter tuning
fix(network): correct CRS transformation in routing
docs(readme): add installation instructions
```

### Branch Strategy:
- `main`: Production-ready code
- `develop`: Integration branch
- `feature/*`: New features
- `fix/*`: Bug fixes

---

## Reproducibility Checklist

- [ ] All data sources documented with URLs and access dates
- [ ] `requirements.txt` or `environment.yml` provided
- [ ] Random seeds set for stochastic algorithms
- [ ] Configuration files used instead of hardcoded values
- [ ] README includes step-by-step instructions
- [ ] Computational environment documented (OS, Python version)
- [ ] Intermediate data regenerable from raw data
- [ ] All figures have source code to reproduce them

---

## Tools and Libraries (Recommended)

### Core Data Science:
- `pandas`, `numpy`, `scipy`
- `geopandas`, `shapely`, `pyproj`
- `scikit-learn`, `hdbscan`

### Geospatial:
- `osmnx` (OpenStreetMap network analysis)
- `folium` (Interactive maps)
- `contextily` (Basemaps)
- `rasterstats` (Raster operations)

### Routing:
- `pandana` (Network accessibility)
- `r5py` (Multi-modal routing with GTFS)
- `networkx` (Graph algorithms)

### Visualization:
- `matplotlib`, `seaborn`
- `plotly`, `altair`
- `kepler.gl` (Advanced web maps)

### Web:
- `flask` or `fastapi` (Backend API)
- `streamlit` (Rapid prototyping)
- `leaflet.js` or `mapbox-gl-js` (Frontend mapping)

---

## Questions or Issues?

If directory structure needs adjustment, document reasons and update this file accordingly.

**Last Updated**: 2025-11-09
