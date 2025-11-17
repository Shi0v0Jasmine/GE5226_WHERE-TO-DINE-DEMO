# Project File Dependency Analysis

## Overview

This document provides a detailed explanation of all file dependencies in the **GE5226 WHERE-TO-DINE** project, including:
- Code module dependencies (import relationships)
- Data flow dependencies (input/output files)
- Execution order dependencies

---

## I. System Architecture Dependency Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interface Layer                      │
│  ┌──────────────┐                 ┌─────────────────────┐  │
│  │  app.py      │ ◄───uses────────│ templates/          │  │
│  │ (Flask Web)  │                 │   index.html        │  │
│  └──────┬───────┘                 └─────────────────────┘  │
│         │ reads                                             │
└─────────┼───────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│                    Data Output Layer                         │
│         data/processed/final_hotspots.geojson                │
└─────────────────────────────────────────────────────────────┘
          ▲
          │ generates
┌─────────┴───────────────────────────────────────────────────┐
│                  Data Processing Pipeline Layer              │
│                                                               │
│  ┌────────────────────────────────────────────────────┐    │
│  │        run_pipeline.py (Pipeline Controller)        │    │
│  │              sequentially calls↓                     │    │
│  └────────────────────────────────────────────────────┘    │
│                                                               │
│  [Phase 1]  02_process_taxi_data.py                         │
│               ↓ outputs: taxi_dropoffs_weighted.parquet     │
│                                                               │
│  [Phase 2]  02_merge_restaurants.py                         │
│               ↓ outputs: restaurants_merged.geojson         │
│                                                               │
│  [Phase 3]  06_cluster_restaurants.py                       │
│               ↓ inputs: restaurants_merged.geojson          │
│               ↓ outputs: dining_zones.geojson               │
│               ↓       restaurants_clustered.geojson         │
│                                                               │
│  [Phase 4]  07_cluster_taxi_dropoffs.py                     │
│               ↓ inputs: taxi_dropoffs_weighted.parquet      │
│               ↓ outputs: taxi_hotspots.geojson              │
│                                                               │
│  [Phase 5]  08_spatial_intersection.py                      │
│               ↓ inputs: dining_zones.geojson                │
│               ↓       taxi_hotspots.geojson                  │
│               ↓ outputs: final_hotspots.geojson             │
│                                                               │
└───────────────────────────────────────────────────────────────┘
          │ all modules depend on
          ▼
┌─────────────────────────────────────────────────────────────┐
│                    Utility Module Layer                      │
│  ┌─────────────────────┐      ┌────────────────────────┐   │
│  │ src/utils/          │      │ src/analysis/          │   │
│  │  config_loader.py   │      │  clustering.py         │   │
│  │ (Config Loading)    │      │  isochrone.py          │   │
│  └─────────────────────┘      └────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
          ▲
          │ reads
┌─────────┴───────────────────────────────────────────────────┐
│                    Configuration Layer                       │
│              config/config.yaml                              │
└─────────────────────────────────────────────────────────────┘
```

---

## II. Detailed File Dependencies

### 2.1 Entry File Dependencies

#### **app.py** (Web Application)

**Direct Dependencies:**
```python
from flask import Flask, render_template, request, jsonify
import geopandas, pandas, numpy, shapely, json
```

**File Dependencies:**
- **Reads**: `data/processed/final_hotspots.geojson`
- **Uses**: `templates/index.html`

**Dependents:** None (top-level application)

---

#### **run_pipeline.py** (Pipeline Controller)

**Direct Dependencies:**
```python
import subprocess, sys, logging, pathlib, time, datetime
```

**Execution Order:**
1. `src/data_processing/02_process_taxi_data.py`
2. `src/data_processing/02_merge_restaurants.py`
3. `src/data_processing/06_cluster_restaurants.py`
4. `src/data_processing/07_cluster_taxi_dropoffs.py`
5. `src/data_processing/08_spatial_intersection.py`

**Checks Files:**
- `config/config.yaml`
- `data/external/boundaries/nybb.shp`
- `data/raw/taxi/` (directory)
- `data/raw/restaurants/` (directory)

**Dependents:** None (top-level controller)

---

### 2.2 Utility Module Dependencies

#### **src/utils/config_loader.py**

**Direct Dependencies:**
```python
import yaml, pathlib
```

**File Dependencies:**
- **Reads**: `config/config.yaml`

**Dependents:**
- `02_process_taxi_data.py`
- `02_merge_restaurants.py`
- `06_cluster_restaurants.py`
- `07_cluster_taxi_dropoffs.py`
- `08_spatial_intersection.py`
- `clustering.py`

**Core Functions:**
- `load_config()` - Load YAML configuration
- `get_data_path()` - Get data file paths
- `get_config_value()` - Get configuration values

---

#### **src/analysis/clustering.py**

**Direct Dependencies:**
```python
import numpy, pandas, geopandas, hdbscan
from sklearn.metrics import silhouette_score, davies_bouldin_score
from src.utils.config_loader import load_config
```

**Dependents:**
- Theoretically importable, but processing scripts implement clustering inline rather than importing this module
- Provides reference implementation and test code

---

#### **src/analysis/isochrone.py**

**Direct Dependencies:**
```python
import networkx, osmnx, geopandas, shapely
```

**File Dependencies:**
- **Reads**: `data/processed/networks/network_walk.gpickle` (optional)

**Dependents:** Independent functional module, not called by other scripts

**Status:** Optional feature (for accessibility analysis)

---

### 2.3 Data Processing Pipeline Dependencies

#### **Phase 1: 02_process_taxi_data.py**

**Code Dependencies:**
```python
import pandas, geopandas, numpy, shapely
from pathlib import Path
from pandarallel import pandarallel
from src.utils.config_loader import load_config, get_config_value
```

**Input Files:**
- `data/raw/taxi/*.parquet` (12 months)
- `data/external/boundaries/nybb.shp` (NYC boundaries)
- `data/external/boundaries/taxi_zones.shp` (taxi zones)
- `config/config.yaml`

**Output Files:**
- `data/interim/taxi_dropoffs_weighted.parquet` ✅ **Main Output**
- `data/interim/taxi_dropoffs_weighted_sample.geojson`
- `data/interim/taxi_processing_summary.json`

**Key Processing:**
1. Batch load 12 months of Parquet files
2. LocationID → lat/lon conversion (using taxi_zones.shp)
3. Filter to dining hours (breakfast, lunch, dinner, late-night)
4. Apply temporal weights (weekend dinner 1.5x, weekday dinner 1.0x, etc.)
5. Filter to NYC boundaries

**Dependents:** `07_cluster_taxi_dropoffs.py`

---

#### **Phase 2: 02_merge_restaurants.py**

**Code Dependencies:**
```python
import pandas, geopandas, shapely
from scipy.spatial import cKDTree
from fuzzywuzzy import fuzz
```

**Input Files:**
- `data/raw/restaurants/restaurants_nyc_googlemaps.csv`
- `data/raw/restaurants/restaurants_nyc_osm.csv`

**Output Files:**
- `data/interim/restaurants_merged.geojson` ✅ **Main Output**
- `data/interim/restaurants_merged.csv`

**Key Processing:**
1. Load Google Maps and OSM restaurant data
2. Standardize fields (name, lat, lon, rating, etc.)
3. Deduplication (spatial distance <50m + name similarity >80%)
4. Use KDTree for optimized spatial search

**Dependents:** `06_cluster_restaurants.py`

---

#### **Phase 3: 06_cluster_restaurants.py**

**Code Dependencies:**
```python
import pandas, geopandas, numpy
from pathlib import Path
from shapely.geometry import MultiPoint
from hdbscan import HDBSCAN
from sklearn.metrics import silhouette_score, davies_bouldin_score
from src.utils.config_loader import load_config, get_config_value
```

**Input Files:**
- `data/interim/restaurants_merged.geojson` ← Phase 2
- `config/config.yaml`

**Output Files:**
- `data/processed/dining_zones.geojson` ✅ **Main Output**
- `data/processed/restaurants_clustered.geojson`
- `data/processed/clustering_metrics.json`

**Key Processing:**
1. Project to EPSG:2263 (metric coordinates)
2. HDBSCAN clustering (min_cluster_size=30, epsilon=200m)
3. Generate convex hull + buffer (100m) → dining zones
4. Calculate validation metrics (Silhouette, Davies-Bouldin)

**Dependents:** `08_spatial_intersection.py`

---

#### **Phase 4: 07_cluster_taxi_dropoffs.py**

**Code Dependencies:**
```python
import pandas, geopandas, numpy
from shapely.geometry import MultiPoint
from hdbscan import HDBSCAN
from sklearn.metrics import silhouette_score, davies_bouldin_score
from src.utils.config_loader import load_config, get_config_value
```

**Input Files:**
- `data/interim/taxi_dropoffs_weighted.parquet` ← Phase 1
- `config/config.yaml`

**Output Files:**
- `data/processed/taxi_hotspots.geojson` ✅ **Main Output**
- `data/processed/taxi_dropoffs_clustered.parquet`
- `data/processed/taxi_clustering_metrics.json`

**Key Processing:**
1. Load weighted taxi data
2. Optional H3 aggregation (reduce data size)
3. Weight-based point duplication (weight=1.5 → duplicate 2 times)
4. HDBSCAN clustering (min_cluster_size=50, epsilon=250m)
5. Generate convex hull + buffer (150m) → taxi hotspots

**Dependents:** `08_spatial_intersection.py`

---

#### **Phase 5: 08_spatial_intersection.py**

**Code Dependencies:**
```python
import geopandas, pandas, numpy
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
from src.utils.config_loader import load_config, get_config_value
```

**Input Files:**
- `data/processed/dining_zones.geojson` ← Phase 3
- `data/processed/taxi_hotspots.geojson` ← Phase 4
- `config/config.yaml`

**Output Files:**
- `data/processed/final_hotspots.geojson` ✅ **Final Output**
- `data/processed/intersection_analysis.json`

**Key Processing:**
1. Spatial intersection: dining_zones ∩ taxi_hotspots
2. Filtering criteria:
   - Minimum area ≥ 10,000 m²
   - Minimum overlap ratio ≥ 15%
3. Calculate composite scores:
   - restaurant_score (normalized restaurant density)
   - taxi_score (normalized taxi density)
   - popularity_score = 0.5×restaurant + 0.5×taxi
4. Rank and output top N

**Dependents:** `app.py`, `01_visualize_results.py`

---

### 2.4 Visualization Module Dependencies

#### **src/visualization/01_visualize_results.py**

**Code Dependencies:**
```python
import geopandas, pandas, folium
from folium import plugins
```

**Input Files:**
- `data/processed/restaurants_clustered.geojson`
- `data/processed/dining_zones.geojson`
- `data/processed/taxi_hotspots.geojson`
- `data/processed/final_hotspots.geojson`

**Output Files:**
- `maps/01_restaurants_clusters.html`
- `maps/02_taxi_hotspots.html`
- `maps/03_final_hotspots.html`

**Dependents:** Independent execution, not depended on by other modules

---

## III. Data Flow Dependency Diagram

### 3.1 Complete Data Flow

```
Raw Data Sources
├─ data/raw/taxi/*.parquet (12 months)
├─ data/raw/restaurants/restaurants_nyc_googlemaps.csv
├─ data/raw/restaurants/restaurants_nyc_osm.csv
├─ data/external/boundaries/nybb.shp
└─ data/external/boundaries/taxi_zones.shp
        │
        ▼
┌────────────────────────────────────────────────┐
│  Phase 1: 02_process_taxi_data.py             │
│  └─→ data/interim/taxi_dropoffs_weighted.parquet
└────────────────────────────────────────────────┘
        │
        │                   ┌────────────────────────────────────┐
        │                   │ Phase 2: 02_merge_restaurants.py    │
        │                   │ └─→ data/interim/restaurants_merged.geojson
        │                   └────────────────────────────────────┘
        │                                   │
        ▼                                   ▼
┌─────────────────────────────┐   ┌──────────────────────────────┐
│ Phase 4:                    │   │ Phase 3:                     │
│ 07_cluster_taxi_dropoffs.py │   │ 06_cluster_restaurants.py    │
│ └─→ taxi_hotspots.geojson   │   │ └─→ dining_zones.geojson     │
└─────────────────────────────┘   └──────────────────────────────┘
        │                                   │
        └───────────┬───────────────────────┘
                    ▼
        ┌───────────────────────────────────────┐
        │ Phase 5:                              │
        │ 08_spatial_intersection.py            │
        │ └─→ data/processed/                   │
        │     final_hotspots.geojson            │
        └───────────────────────────────────────┘
                    │
        ┌───────────┴────────────┐
        ▼                        ▼
┌───────────────────┐   ┌────────────────────────┐
│ app.py            │   │ 01_visualize_results.py│
│ (Web App)         │   │ (Visualization)        │
│ → 127.0.0.1:5000  │   │ → maps/*.html          │
└───────────────────┘   └────────────────────────┘
```

---

### 3.2 Key Data File Dependency Matrix

| Output File | Used By Which Scripts | Depends On Which Input Files |
|---------|---------------|----------------|
| `taxi_dropoffs_weighted.parquet` | 07_cluster_taxi_dropoffs.py | raw/taxi/*.parquet, boundaries/nybb.shp, taxi_zones.shp |
| `restaurants_merged.geojson` | 06_cluster_restaurants.py | raw/restaurants/*.csv |
| `dining_zones.geojson` | 08_spatial_intersection.py, 01_visualize_results.py | restaurants_merged.geojson |
| `taxi_hotspots.geojson` | 08_spatial_intersection.py, 01_visualize_results.py | taxi_dropoffs_weighted.parquet |
| `final_hotspots.geojson` | app.py, 01_visualize_results.py | dining_zones.geojson, taxi_hotspots.geojson |

---

## IV. Configuration File Dependencies

### **config/config.yaml**

Read by all processing scripts:
- `02_process_taxi_data.py` - Temporal weights, CRS configuration
- `06_cluster_restaurants.py` - HDBSCAN parameters, buffer distance
- `07_cluster_taxi_dropoffs.py` - HDBSCAN parameters, H3 configuration
- `08_spatial_intersection.py` - Filtering thresholds

**Key Configuration Items:**
```yaml
clustering:
  restaurants:
    min_cluster_size: 30
    min_samples: 10
    cluster_selection_epsilon: 200  # meters

  taxi:
    min_cluster_size: 50
    min_samples: 15
    cluster_selection_epsilon: 250  # meters

temporal:
  weights:
    weekend_dinner: 1.5
    weekday_dinner: 1.0
    weekday_lunch: 0.8
    breakfast: 0.5

intersection:
  min_area_sqm: 10000
  min_overlap_ratio: 0.15
```

---

## V. Third-Party Library Dependencies

### 5.1 Core Data Processing
```
pandas>=2.0.0          # Data framework
numpy>=1.24.0          # Numerical computation
geopandas>=0.14.0      # Geospatial data
shapely>=2.0.0         # Geometric operations
pyproj>=3.6.0          # Projection conversion
```

### 5.2 Machine Learning
```
hdbscan>=0.8.33        # Density clustering
scikit-learn>=1.3.0    # Validation metrics
scipy>=1.10.0          # KDTree spatial indexing
```

### 5.3 Data Loading
```
pyarrow>=12.0.0        # Parquet file support
fiona>=1.9.0           # Shapefile support
```

### 5.4 Web & Visualization
```
flask>=2.3.0           # Web framework
folium>=0.14.0         # Interactive maps
```

### 5.5 Optimization Libraries (Optional)
```
pandarallel>=1.6.0     # Parallel pandas operations
h3>=3.7.6              # Hexagonal spatial indexing
rtree>=1.0.1           # R-tree spatial indexing
```

---

## VI. Execution Order Constraints

### 6.1 Must Execute Sequentially

```
1. 02_process_taxi_data.py        ← Must execute first
   │
2. 02_merge_restaurants.py        ← Can run in parallel with step 1
   │
   ├─→ 3. 06_cluster_restaurants.py
   │
   └─→ 4. 07_cluster_taxi_dropoffs.py  ← Steps 3, 4 can run in parallel
   │
5. 08_spatial_intersection.py     ← Must execute after steps 3, 4 complete
```

### 6.2 Optional Execution

- `01_visualize_results.py` - Anytime (needs processed data)
- `app.py` - Anytime (needs final_hotspots.geojson)

---

## VII. Caching Mechanism

### **cache/** Directory

Contains multiple `.json` cache files (hash-named), used for:
- API request caching (possibly from Google Maps API)
- Intermediate computation result caching

**Dependencies:** No direct code dependencies, transparently managed by system

---

## VIII. Dependency Relationship Summary

### 8.1 Strong Dependencies (Required)

```
run_pipeline.py
  ↓
  ├─ config/config.yaml
  ├─ src/utils/config_loader.py
  ├─ data/raw/* (all raw data)
  └─ data/external/boundaries/*.shp

app.py
  ↓
  └─ data/processed/final_hotspots.geojson
```

### 8.2 Weak Dependencies (Optional)

```
src/analysis/isochrone.py
  ↓ (optional)
  └─ data/processed/networks/*.gpickle

01_visualize_results.py
  ↓ (optional)
  └─ data/processed/*.geojson
```

### 8.3 No Dependencies (Independent)

- `templates/index.html` - Pure HTML template
- `docs/*.md` - Documentation files
- `outputs/*` - Output directory

---

## IX. Dependency Failure Risk Analysis

### High Risk Dependencies

| If Deleted/Corrupted... | Impact Scope |
|----------------|---------|
| `config/config.yaml` | 🔴 **All processing scripts fail** |
| `src/utils/config_loader.py` | 🔴 **All processing scripts fail** |
| `data/interim/taxi_dropoffs_weighted.parquet` | 🔴 Phase 4-5 fail |
| `data/interim/restaurants_merged.geojson` | 🔴 Phase 3 fails → Phase 5 fails |
| `data/processed/final_hotspots.geojson` | 🔴 Web app cannot start |

### Medium Risk Dependencies

| If Deleted/Corrupted... | Impact Scope |
|----------------|---------|
| `data/external/boundaries/taxi_zones.shp` | 🟡 Phase 1 fails (LocationID conversion) |
| `data/processed/dining_zones.geojson` | 🟡 Phase 5 fails |
| `data/processed/taxi_hotspots.geojson` | 🟡 Phase 5 fails |

### Low Risk Dependencies

| If Deleted/Corrupted... | Impact Scope |
|----------------|---------|
| `01_visualize_results.py` | ⚪ Only visualization fails |
| `src/analysis/isochrone.py` | ⚪ No impact (not used) |
| `cache/*.json` | ⚪ Only performance degradation, requires recalculation |

---

## X. Dependency Optimization Recommendations

### 10.1 Modularization Improvement

**Current Issue:** Clustering code duplicated across scripts

**Suggestion:** Unify using `src/analysis/clustering.py`
```python
# Replace current inline HDBSCAN code
from src.analysis.clustering import cluster_restaurants, cluster_taxi_dropoffs
```

### 10.2 Configuration Management

**Current:** Hardcoded file paths

**Suggestion:** All paths managed through configuration
```python
# Replace "data/interim/taxi_dropoffs_weighted.parquet"
from src.utils.config_loader import get_data_path
input_path = get_data_path("interim.taxi_filtered")
```

### 10.3 Dependency Injection

**Current:** run_pipeline.py directly calls subprocess

**Suggestion:** Use function imports
```python
# Replace subprocess.run([sys.executable, script_path])
from src.data_processing.process_taxi import main as process_taxi
process_taxi()
```

---

## XI. Quick Dependency Lookup

### Q: "If I modify restaurant data, which scripts need to be rerun?"

**A:**
```
1. 02_merge_restaurants.py           (re-merge)
2. 06_cluster_restaurants.py         (re-cluster)
3. 08_spatial_intersection.py        (re-intersect)
```

### Q: "If I only want to update web app display, do I need to reprocess data?"

**A:** No, only need to modify:
- `app.py` (backend logic)
- `templates/index.html` (frontend display)

### Q: "If I modify clustering parameters, which outputs are affected?"

**A:**
- Modify `clustering.restaurants.*` → affects `dining_zones.geojson` → affects `final_hotspots.geojson`
- Modify `clustering.taxi.*` → affects `taxi_hotspots.geojson` → affects `final_hotspots.geojson`

---

## XII. Dependency Checklist

### Pre-Launch Checklist
```bash
# 1. Configuration file
✓ config/config.yaml

# 2. Raw data
✓ data/raw/taxi/*.parquet (12 files)
✓ data/raw/restaurants/restaurants_nyc_googlemaps.csv
✓ data/raw/restaurants/restaurants_nyc_osm.csv

# 3. Boundary data
✓ data/external/boundaries/nybb.shp
✓ data/external/boundaries/taxi_zones.shp

# 4. Python environment
✓ All libraries in requirements.txt installed
```

### Post-Execution Checklist
```bash
# Phase 1 output
✓ data/interim/taxi_dropoffs_weighted.parquet

# Phase 2 output
✓ data/interim/restaurants_merged.geojson

# Phase 3 output
✓ data/processed/dining_zones.geojson
✓ data/processed/restaurants_clustered.geojson

# Phase 4 output
✓ data/processed/taxi_hotspots.geojson

# Phase 5 output (final)
✓ data/processed/final_hotspots.geojson
```

---

**Document Version:** v1.0
**Last Updated:** 2025-11-17
**Maintainer:** WHERE-TO-DINE Project Team
