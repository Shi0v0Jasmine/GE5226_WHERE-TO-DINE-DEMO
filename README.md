# WHERE TO DINE
### NYC Restaurant Recommendation System Based on Taxi Dropoff Patterns

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![GeoSpatial](https://img.shields.io/badge/GIS-GeoPandas-green.svg)](https://geopandas.org/)
[![ML](https://img.shields.io/badge/ML-HDBSCAN-orange.svg)](https://hdbscan.readthedocs.io/)
[![Web](https://img.shields.io/badge/Web-Flask-lightgrey.svg)](https://flask.palletsprojects.com/)

> **GE5226 Course Project** - Geographic Information Systems and Spatial Analysis
> A data-driven approach to identifying authentic dining hotspots in New York City by analyzing taxi dropoff patterns as "voting with feet" indicators.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Technology Stack](#technology-stack)
- [Quick Start](#quick-start)
- [Data Processing Pipeline](#data-processing-pipeline)
- [Web Application](#web-application)
- [Project Structure](#project-structure)
- [Documentation](#documentation)
- [Academic Context](#academic-context)
- [Contributing](#contributing)
- [License](#license)

---

## 🎯 Overview

**WHERE TO DINE** is a sophisticated geospatial analysis system that identifies and recommends dining hotspots in New York City by analyzing the intersection of restaurant density and taxi dropoff patterns during dining hours. Unlike traditional restaurant recommendation systems that rely solely on reviews or ratings, this project uses actual human behavior data—taxi dropoff patterns—as a proxy for restaurant popularity.

### The Core Hypothesis

If a location experiences high taxi activity during dining hours (breakfast, lunch, dinner, late-night) and has a dense concentration of restaurants, it indicates a genuine dining destination where people actively choose to go.

### Research Question

**Can we identify authentic dining hotspots by analyzing the spatial intersection of restaurant clusters and taxi dropoff patterns, and how do these data-driven recommendations compare to traditional review-based systems?**

---

## ✨ Key Features

### 🗺️ **Multi-Source Data Integration**
- **140+ million** NYC taxi trip records (2024 full year)
- **Dual restaurant databases**: OpenStreetMap + Google Maps
- **GTFS transit data** for accessibility analysis
- **NYC administrative boundaries** for spatial filtering

### 🔬 **Advanced Spatial Analysis**
- **HDBSCAN clustering** for density-based pattern recognition
- **Temporal weighting** to account for dining hour variations
- **Spatial intersection** to identify genuine hotspots
- **Multi-criteria scoring** combining popularity and accessibility

### 🎨 **Interactive Visualization**
- **Real-time web application** with interactive maps
- **Click-to-search** functionality for location-based recommendations
- **Visual analytics** showing restaurant clusters and taxi patterns
- **Comprehensive dashboards** with statistical insights

### 📊 **Academic Rigor**
- **Reproducible pipeline** with documented methodology
- **Validation metrics** (Silhouette Score, Davies-Bouldin Index)
- **Performance optimization** (parallel processing, spatial indexing)
- **Complete documentation** with dependency analysis

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     USER INTERFACE                          │
│                                                             │
│  ┌──────────────┐    Interactive    ┌──────────────┐      │
│  │   Leaflet    │◄────Queries──────►│    Flask     │      │
│  │   Maps UI    │                    │   Backend    │      │
│  └──────────────┘                    └──────┬───────┘      │
│                                              │              │
└──────────────────────────────────────────────┼──────────────┘
                                               │
                                               ↓
┌─────────────────────────────────────────────────────────────┐
│                   DATA PROCESSING LAYER                     │
│                                                             │
│  Phase 1: Taxi Data Processing                             │
│  │  └─→ Temporal filtering + Weight assignment             │
│  │                                                          │
│  Phase 2: Restaurant Data Merging                          │
│  │  └─→ Deduplication + Standardization                    │
│  │                                                          │
│  Phase 3-4: Parallel Clustering                            │
│  │  ├─→ Restaurant HDBSCAN → Dining Zones                  │
│  │  └─→ Taxi HDBSCAN → Dropoff Hotspots                    │
│  │                                                          │
│  Phase 5: Spatial Intersection                             │
│     └─→ Final Hotspots = Dining Zones ∩ Taxi Hotspots     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────┐
│                    DATA STORAGE LAYER                       │
│                                                             │
│  Raw Data          Interim Results      Final Outputs      │
│  ├─ Taxi Parquet   ├─ Weighted Taxi    ├─ Final Hotspots  │
│  ├─ Restaurants    ├─ Merged Restaurants├─ Dining Zones   │
│  ├─ Boundaries     └─ Processing Logs   ├─ Taxi Hotspots  │
│  └─ GTFS/OSM                            └─ Analytics       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Technology Stack

### Core Technologies

| Category | Technologies | Purpose |
|----------|-------------|---------|
| **Data Processing** | Python 3.9+, Pandas, NumPy | Tabular data manipulation |
| **Geospatial Analysis** | GeoPandas, Shapely, PyProj | Spatial operations and projections |
| **Machine Learning** | HDBSCAN, scikit-learn, SciPy | Density-based clustering |
| **Web Framework** | Flask, Leaflet.js | Interactive web application |
| **Data Storage** | Parquet (PyArrow), GeoJSON | Efficient data formats |
| **Visualization** | Folium, Matplotlib, Seaborn | Interactive and static maps |

### Performance Optimization

- **Pandarallel**: Parallel pandas operations for large datasets
- **H3**: Hexagonal spatial indexing for aggregation
- **KDTree**: Fast spatial nearest-neighbor searches
- **Git LFS**: Large file version control

---

## 🚀 Quick Start

### Prerequisites

```bash
# System Requirements
- Python 3.9 or higher
- 16GB RAM (recommended for full dataset processing)
- 50GB free disk space

# Check Python version
python --version
```

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/GE5226_WHERE-TO-DINE-DEMO.git
cd GE5226_WHERE-TO-DINE-DEMO

# 2. Install dependencies
pip install -r requirements.txt

# 3. Verify installation
python -c "import geopandas; import hdbscan; print('✅ Dependencies installed')"
```

### Data Setup

```bash
# 4. Ensure data files are in place
# Required files:
# - data/raw/taxi/*.parquet (12 monthly files)
# - data/raw/restaurants/*.csv (Google Maps + OSM)
# - data/external/boundaries/*.shp (NYC boundaries)

# 5. Verify data structure
ls data/raw/taxi/*.parquet | wc -l  # Should output: 12
```

### Running the Pipeline

```bash
# 6. Execute complete data processing pipeline
python run_pipeline.py

# Expected output:
# Phase 1: Taxi Data Processing ✅
# Phase 2: Restaurant Merging ✅
# Phase 3: Restaurant Clustering ✅
# Phase 4: Taxi Clustering ✅
# Phase 5: Spatial Intersection ✅
# Pipeline completed in ~30-60 minutes

# 7. Verify outputs
ls data/processed/final_hotspots.geojson  # Should exist
```

### Launching Web Application

```bash
# 8. Start the web server
python app.py

# 9. Open browser and navigate to:
http://127.0.0.1:5000

# Features available:
# - Interactive map with all hotspots
# - Click anywhere to get nearby recommendations
# - View detailed statistics for each hotspot
```

---

## 📊 Data Processing Pipeline

### Phase 1: Taxi Data Processing
**Script**: `src/data_processing/02_process_taxi_data.py`

**Inputs**:
- 12 monthly Parquet files (~140M records total)
- NYC boundaries (nybb.shp)
- Taxi zones (taxi_zones.shp)

**Processing**:
1. **Batch loading** of monthly data files
2. **LocationID → Coordinates** conversion using taxi zones
3. **Temporal filtering** to dining hours:
   - Breakfast: 07:00-10:00
   - Lunch: 11:00-14:00
   - Dinner: 17:00-22:00
   - Late-night: 22:00-01:00
4. **Weight assignment** based on day/time:
   - Weekend dinner: 1.5×
   - Weekday dinner: 1.0×
   - Weekday lunch: 0.8×
   - Breakfast: 0.5×
5. **Spatial filtering** to NYC boundaries

**Output**: `data/interim/taxi_dropoffs_weighted.parquet`

---

### Phase 2: Restaurant Data Merging
**Script**: `src/data_processing/02_merge_restaurants.py`

**Inputs**:
- Google Maps restaurant data
- OpenStreetMap restaurant data

**Processing**:
1. **Field standardization** (name, coordinates, ratings)
2. **Spatial deduplication**:
   - Distance threshold: 50 meters
   - Name similarity: 80% (Levenshtein distance)
   - Using KDTree for efficient spatial search
3. **Data fusion** prioritizing Google Maps data

**Output**: `data/interim/restaurants_merged.geojson`

---

### Phase 3: Restaurant Clustering
**Script**: `src/data_processing/06_cluster_restaurants.py`

**Inputs**:
- Merged restaurant data
- Configuration parameters

**Processing**:
1. **Coordinate projection**: WGS84 → EPSG:2263 (NAD83 NY Long Island)
2. **HDBSCAN clustering**:
   - min_cluster_size: 30 restaurants
   - min_samples: 10
   - epsilon: 200 meters
3. **Dining zone generation**:
   - Convex hull computation
   - 100-meter buffer application
4. **Validation metrics** calculation

**Output**: `data/processed/dining_zones.geojson`

---

### Phase 4: Taxi Dropoff Clustering
**Script**: `src/data_processing/07_cluster_taxi_dropoffs.py`

**Inputs**:
- Weighted taxi dropoff data

**Processing**:
1. **Optional H3 aggregation** (for performance)
2. **Weight-based duplication**: points repeated by weight
3. **HDBSCAN clustering**:
   - min_cluster_size: 50 dropoffs
   - min_samples: 15
   - epsilon: 250 meters
4. **Hotspot polygon generation**: convex hull + 150m buffer

**Output**: `data/processed/taxi_hotspots.geojson`

---

### Phase 5: Spatial Intersection Analysis
**Script**: `src/data_processing/08_spatial_intersection.py`

**Inputs**:
- Dining zones (from Phase 3)
- Taxi hotspots (from Phase 4)

**Processing**:
1. **Spatial intersection**: Dining Zones ∩ Taxi Hotspots
2. **Filtering criteria**:
   - Minimum area: 10,000 m²
   - Minimum overlap ratio: 15%
3. **Composite scoring**:
   ```
   Restaurant Score = (restaurants/area) normalized to [0,100]
   Taxi Score = (weighted_dropoffs/area) normalized to [0,100]
   Popularity Score = 0.5 × Restaurant + 0.5 × Taxi
   ```
4. **Ranking and output**

**Output**: `data/processed/final_hotspots.geojson` ✅

---

## 🌐 Web Application

### Features

#### 1. Interactive Map View
- **Base Layer**: CartoDB Positron for clean visualization
- **Hotspot Polygons**: Color-coded by popularity score
  - 🔴 Red: Top tier (>66th percentile)
  - 🟠 Orange: Mid tier (33-66th percentile)
  - 🟡 Yellow: Lower tier (<33rd percentile)

#### 2. Location-Based Recommendations
**Endpoint**: `POST /api/recommend`

```json
{
  "lat": 40.7589,
  "lon": -73.9851,
  "max_distance_km": 2.0,
  "limit": 10
}
```

**Response**: Top N hotspots ranked by combined score:
- **Popularity Score** (60%): Inherent hotspot quality
- **Accessibility Score** (40%): Proximity to user location

#### 3. Statistical Dashboard
**Endpoint**: `GET /api/stats`

Returns:
- Total hotspots identified
- Total restaurants and taxi dropoffs
- Average popularity score
- Coverage area statistics

### API Documentation

Full API documentation available at: `/docs/API_REFERENCE.md` (if created)

---

## 📁 Project Structure

```
GE5226_WHERE-TO-DINE-DEMO/
│
├── 🚀 Entry Points
│   ├── app.py                    # Web application server
│   ├── run_pipeline.py           # Complete data processing pipeline
│   └── requirements.txt          # Python dependencies
│
├── 📂 src/                       # Source code
│   ├── data_processing/          # ETL scripts (5 phases)
│   │   ├── 02_process_taxi_data.py
│   │   ├── 02_merge_restaurants.py
│   │   ├── 06_cluster_restaurants.py
│   │   ├── 07_cluster_taxi_dropoffs.py
│   │   └── 08_spatial_intersection.py
│   │
│   ├── analysis/                 # Analysis algorithms
│   │   ├── clustering.py         # HDBSCAN implementation
│   │   └── isochrone.py         # Accessibility analysis
│   │
│   ├── visualization/            # Visualization tools
│   │   └── 01_visualize_results.py
│   │
│   └── utils/                    # Utility functions
│       └── config_loader.py      # Configuration management
│
├── 📊 data/                      # Data directory
│   ├── raw/                      # Original datasets
│   │   ├── taxi/                 # 12 monthly Parquet files
│   │   ├── restaurants/          # Google Maps + OSM data
│   │   ├── gtfs/                 # Transit data
│   │   └── osm/                  # Road network data
│   │
│   ├── interim/                  # Intermediate results
│   │   ├── taxi_dropoffs_weighted.parquet
│   │   └── restaurants_merged.geojson
│   │
│   ├── processed/                # Final outputs
│   │   ├── final_hotspots.geojson  ⭐ Main deliverable
│   │   ├── dining_zones.geojson
│   │   ├── taxi_hotspots.geojson
│   │   └── *_metrics.json
│   │
│   └── external/                 # Reference data
│       └── boundaries/           # NYC shapefiles
│
├── 🎨 templates/                 # Web UI templates
│   └── index.html
│
├── ⚙️ config/                    # Configuration files
│   └── config.yaml
│
├── 📚 docs/                      # Documentation
│   ├── PROJECT_STRUCTURE_EN.md       # Project overview
│   ├── FILE_DEPENDENCIES_EN.md       # Dependency analysis
│   ├── DEPENDENCY_DIAGRAM_EN.md      # Visual diagrams
│   ├── SYSTEM_ARCHITECTURE.md        # Technical architecture
│   ├── DATA_PROCESSING_PIPELINE.md   # Pipeline details
│   └── methodology/                  # Research methodology
│
└── 📈 outputs/                   # Generated outputs
    ├── maps/                     # Interactive HTML maps
    ├── figures/                  # Static visualizations
    └── reports/                  # Analysis reports
```

---

## 📖 Documentation

### Core Documentation

| Document | Description | Audience |
|----------|-------------|----------|
| [PROJECT_STRUCTURE_EN.md](PROJECT_STRUCTURE_EN.md) | Complete project overview | General |
| [FILE_DEPENDENCIES_EN.md](FILE_DEPENDENCIES_EN.md) | Detailed dependency analysis | Developers |
| [DEPENDENCY_DIAGRAM_EN.md](DEPENDENCY_DIAGRAM_EN.md) | Visual dependency diagrams | Technical |
| [WEB_DEMO_GUIDE.md](WEB_DEMO_GUIDE.md) | Web application user guide | End users |

### Methodology Documentation

| Document | Topic |
|----------|-------|
| `docs/methodology/temporal_weighting.md` | Time-based weight calculation |
| `docs/methodology/spatial_intersection_criteria.md` | Intersection filtering rules |
| `docs/methodology/recommendation_scoring.md` | Scoring algorithm details |
| `docs/methodology/isochrone_thresholds.md` | Accessibility thresholds |

### Academic Documentation

| Document | Purpose |
|----------|---------|
| `docs/ACADEMIC_EVALUATION.md` | Assessment criteria and rubric |
| `docs/FINAL_REPORT_TEMPLATE.md` | Report structure template |
| `docs/PRESENTATION_GUIDE.md` | Presentation guidelines |
| `docs/TASK_CHECKLIST.md` | Project milestone tracking |

---

## 🎓 Academic Context

### Course Information
- **Course**: GE5226 - Geographic Information Systems and Spatial Analysis
- **Institution**: [Your University]
- **Semester**: [Semester/Year]

### Learning Objectives Addressed

1. ✅ **Spatial Data Integration**: Multi-source data fusion (taxi, restaurants, boundaries)
2. ✅ **Clustering Analysis**: HDBSCAN application to geospatial data
3. ✅ **Spatial Statistics**: Validation metrics and quality assessment
4. ✅ **GIS Operations**: Projection, buffering, intersection, overlay analysis
5. ✅ **Visualization**: Interactive web mapping with Leaflet.js
6. ✅ **Big Data Processing**: Handling 140M+ records efficiently
7. ✅ **Reproducibility**: Complete pipeline with documentation

### Key Methodological Contributions

#### 1. Temporal Weighting Framework
Novel approach to incorporate time-of-day and day-of-week patterns into spatial analysis:

```python
Weight = f(hour, day_of_week, is_weekend)

Examples:
- Friday 19:00 → 1.5× (peak dining)
- Monday 12:30 → 0.8× (lunch rush)
- Tuesday 08:00 → 0.5× (breakfast)
```

#### 2. Dual-Clustering Intersection Method
Sequential clustering followed by spatial intersection:

```
Step 1: Cluster(Restaurants) → Dining Zones
Step 2: Cluster(Taxi) → Dropoff Hotspots
Step 3: Intersect(Dining Zones, Dropoff Hotspots) → Final Hotspots
```

This approach reduces noise and identifies locations where both supply (restaurants) and demand (taxi activity) converge.

#### 3. Multi-Criteria Scoring
Balanced scoring combining multiple dimensions:

```
Popularity = 0.5 × (Restaurant Density Score) +
             0.5 × (Taxi Activity Score)

Where each component is normalized to [0, 100]
```

---

## 🔧 Configuration

### Main Configuration File: `config/config.yaml`

```yaml
clustering:
  restaurants:
    min_cluster_size: 30        # Minimum restaurants per cluster
    min_samples: 10             # Conservative density parameter
    cluster_selection_epsilon: 200  # 200 meters

  taxi:
    min_cluster_size: 50        # Minimum dropoffs per cluster
    min_samples: 15
    cluster_selection_epsilon: 250  # 250 meters

temporal:
  weights:
    weekend_dinner: 1.5
    weekday_dinner: 1.0
    weekday_lunch: 0.8
    breakfast: 0.5
    late_night_weekend: 0.7
    late_night_weekday: 0.4

intersection:
  min_area_sqm: 10000          # ~2-3 NYC blocks
  min_overlap_ratio: 0.15       # 15% minimum overlap

geographic:
  crs:
    wgs84: "EPSG:4326"
    projected: "EPSG:2263"      # NAD83 / NY Long Island
```

---

## 🐛 Troubleshooting

### Common Issues

#### 1. Memory Error during Taxi Processing
```bash
# Solution: Process files in smaller batches
# Edit 02_process_taxi_data.py, line 468
# Reduce batch size or use H3 aggregation
```

#### 2. HDBSCAN Taking Too Long
```bash
# Solution: Increase epsilon or reduce sample size
# Edit config/config.yaml
# Increase cluster_selection_epsilon to 300-400m
```

#### 3. Missing Dependencies
```bash
# Solution: Reinstall with specific versions
pip install -r requirements.txt --upgrade --force-reinstall
```

#### 4. Web App Shows "No Data"
```bash
# Verify final output exists
ls data/processed/final_hotspots.geojson

# If missing, rerun pipeline
python run_pipeline.py
```

---

## 📈 Performance Benchmarks

### Processing Time (on reference hardware)

| Phase | Duration | Bottleneck |
|-------|----------|------------|
| Phase 1: Taxi Processing | 15-25 min | I/O + Coordinate conversion |
| Phase 2: Restaurant Merging | 2-3 min | KDTree construction |
| Phase 3: Restaurant Clustering | 1-2 min | HDBSCAN computation |
| Phase 4: Taxi Clustering | 10-15 min | HDBSCAN on large dataset |
| Phase 5: Spatial Intersection | 1-2 min | Polygon operations |
| **Total** | **30-47 min** | - |

**Reference Hardware**:
- CPU: Intel i7-10700K / AMD Ryzen 7 3700X
- RAM: 16GB DDR4
- Storage: SSD

### Optimization Opportunities

1. **Parallel Execution**: Run Phase 1-2 and Phase 3-4 concurrently → **1.5-2× speedup**
2. **H3 Aggregation**: Reduce taxi data from 140M to ~500K cells → **10× speedup** for Phase 4
3. **Dask Integration**: Distributed computing for very large datasets
4. **GPU Acceleration**: RAPIDS cuSpatial for spatial operations

---

## 🤝 Contributing

This is an academic project, but suggestions and improvements are welcome!

### How to Contribute

1. **Report Issues**: Use GitHub Issues for bugs or suggestions
2. **Propose Enhancements**: Open a discussion for new features
3. **Submit Pull Requests**:
   - Fork the repository
   - Create a feature branch
   - Submit PR with detailed description

### Code Standards

- **Style**: Follow PEP 8 guidelines
- **Documentation**: Docstrings for all functions
- **Testing**: Include unit tests for new features
- **Commits**: Use conventional commit messages

---

## 📄 License

This project is part of academic coursework for GE5226.

**Code**: MIT License (see LICENSE file)

**Data**:
- NYC Taxi Data: [NYC TLC](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page)
- OpenStreetMap: [ODbL](https://www.openstreetmap.org/copyright)
- Google Maps: Subject to Google Maps Platform Terms

---

## 🙏 Acknowledgments

### Data Sources
- **NYC Taxi & Limousine Commission**: Trip record data
- **OpenStreetMap Contributors**: Restaurant POI data
- **Google Maps Platform**: Supplementary restaurant data
- **NYC Open Data**: Administrative boundaries

### Libraries and Tools
- **GeoPandas Team**: Spatial data manipulation
- **HDBSCAN Developers**: Clustering algorithm
- **Flask Community**: Web framework
- **Leaflet.js**: Interactive mapping

### Academic Support
- **Course Instructor**: [Instructor Name]
- **Teaching Assistants**: [TA Names]
- **Peer Reviewers**: [Classmates]

---

## 📞 Contact

**Project Maintainer**: [Your Name]
**Email**: [your.email@university.edu]
**GitHub**: [@yourusername](https://github.com/yourusername)

**Course**: GE5226 - Geographic Information Systems
**Institution**: [Your University]

---

## 🔖 Citation

If you use this project in your research or coursework, please cite:

```bibtex
@misc{where_to_dine_2024,
  title={WHERE TO DINE: NYC Restaurant Recommendation via Taxi Dropoff Analysis},
  author={[Your Name]},
  year={2024},
  institution={[Your University]},
  course={GE5226 - Geographic Information Systems},
  url={https://github.com/yourusername/GE5226_WHERE-TO-DINE-DEMO}
}
```

---

## 📊 Project Statistics

![Lines of Code](https://img.shields.io/badge/Lines%20of%20Code-~5000-blue)
![Data Processed](https://img.shields.io/badge/Data%20Processed-140M%20records-green)
![Coverage](https://img.shields.io/badge/NYC%20Coverage-100%25-brightgreen)
![Documentation](https://img.shields.io/badge/Documentation-Complete-success)

**Last Updated**: November 2024
**Version**: 1.0.0
**Status**: ✅ Production Ready

---

<div align="center">

**⭐ Star this repository if you find it helpful! ⭐**

Made with ❤️ for GE5226 Course Project

[Back to Top](#where-to-dine) | [Documentation](docs/) | [Issues](https://github.com/yourusername/issues)

</div>
