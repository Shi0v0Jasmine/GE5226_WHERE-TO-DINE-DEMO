# NYC 2014 Coordinate Taxi Comparison Plan

Date: 2026-06-12
Status: Planning document

## 1. Purpose

The next milestone is to test whether precise taxi coordinates materially improve the project.

We will compare two versions of the same dining-hotspot pipeline:

- Baseline A: current 2024 NYC Yellow Taxi pipeline using `DOLocationID` mapped to taxi-zone centroids.
- Experiment B: NYC 2014 Yellow Taxi coordinate pipeline using actual `dropoff_longitude` and `dropoff_latitude`.

The core question:

> Does coordinate-level taxi data produce more spatially meaningful dining hotspots than zone-centroid taxi data?

This is also a portfolio story: the project identifies a methodological weakness, fixes it through a better data source, and validates the change.

## 2. Current Implementation Audit

### 2.1 Current Scoring

Current popularity scoring is implemented in `src/data_processing/08_spatial_intersection.py`.

It calculates:

```text
restaurant_density = n_restaurants / intersection_area
taxi_density = taxi_weight / intersection_area
restaurant_score = 100 * restaurant_density / max(restaurant_density)
taxi_score = 100 * taxi_density / max(taxi_density)
popularity_score = 0.5 * restaurant_score + 0.5 * taxi_score
```

Current recommendation scoring is implemented in `app.py`.

It calculates:

```text
accessibility_score = 100 * (1 - distance_km / max_distance_in_current_result_set)
recommendation_score = 0.6 * popularity_score + 0.4 * accessibility_score
```

### 2.2 Scoring Problems

The current scoring needs improvement before it becomes a strong portfolio artifact.

Problems:

- Max normalization is unstable. One outlier hotspot can compress all other scores.
- Popularity is normalized within the current generated hotspot set, so scores can change across pipeline runs.
- `accessibility_score` in the Flask app depends on the farthest hotspot returned in the current query, not a stable travel threshold.
- Taxi density and restaurant density are simply averaged, even though they have different uncertainty and bias.
- The current score has no confidence term for taxi spatial resolution, POI completeness, rating count, or sample size.
- Ranking tie-breakers are underdeveloped.

Recommended redesign:

```text
demand_score      = percentile_or_log_scaled(taxi_or_mobility_demand)
poi_score         = weighted mix of restaurant density, rating confidence, review volume, and cuisine diversity
access_score      = travel-time decay score using network travel time or fixed-radius proxy
confidence_score  = data-quality confidence, including coordinate precision and sample size

final_score =
    w_demand * demand_score +
    w_poi * poi_score +
    w_access * access_score +
    w_confidence * confidence_score
```

For the coordinate comparison experiment, keep the first experiment simple:

- Use one baseline score close to the current method for comparability.
- Add one improved score using log/percentile scaling.
- Compare whether the ranking and hotspot shapes become more plausible.

## 3. Do We Need Another Literature Search?

Yes. A targeted paper search is worth doing before rewriting the scoring algorithm.

Why:

- We need defensible normalization and weighting choices.
- We need evidence for using taxi drop-offs as revealed-preference or urban-activity signals.
- We need a better accessibility measure than Euclidean distance.
- We need a defensible way to combine taxi and bike signals.

This should be a focused literature pass, not an endless survey.

### 3.1 Search Keywords

Scoring and revealed preference:

- `taxi GPS trajectory urban activity hotspot POI density`
- `taxi drop-off demand point of interest land use restaurant hotspot`
- `revealed preference mobility data urban destination choice`
- `urban vitality taxi trajectory POI data`
- `mobility data place recommendation ranking`
- `spatial interaction model destination attractiveness POI taxi demand`

Normalization and ranking:

- `log normalization skewed mobility demand hotspot scoring`
- `percentile normalization urban hotspot ranking`
- `multi criteria decision analysis location recommendation TOPSIS AHP`
- `Bayesian rating average restaurant ranking review count`
- `Wilson score interval ranking ratings reviews`

Clustering:

- `HDBSCAN spatial hotspot detection GPS trajectories`
- `DBSCAN taxi trajectory hotspot detection`
- `kernel density estimation taxi pickup dropoff hotspot`
- `network kernel density estimation taxi pickup events`
- `Getis Ord Gi* mobility hotspot analysis`
- `spatiotemporal clustering taxi trajectories ST-DBSCAN`

Accessibility:

- `gravity-based accessibility measure urban opportunities travel time decay`
- `cumulative opportunities accessibility measure travel time threshold`
- `2SFCA accessibility method food access restaurants`
- `multimodal accessibility r5py R5 transport network`
- `isochrone accessibility openstreetmap gtfs routing`

Taxi + bike integration:

- `taxi bikeshare multimodal urban mobility demand hotspots`
- `bike sharing taxi mode choice urban mobility data`
- `Citi Bike taxi data urban activity centers`
- `multimodal mobility data fusion urban demand graph`
- `heterogeneous mobility data fusion taxi bike subway POI`

### 3.2 Suggested Search Prompt

Use this prompt for a literature-search agent or manual review:

```text
I am building a portfolio-grade WebGIS project that identifies and ranks urban dining districts using restaurant POIs, taxi drop-offs, bike-share trips, and accessibility. Please find peer-reviewed or official technical sources that justify:

1. using taxi drop-offs or GPS trajectories as revealed-preference / urban activity signals;
2. using POI density and mobility demand together to identify hotspots;
3. choosing HDBSCAN, DBSCAN, KDE, network KDE, Getis-Ord Gi*, or ST-DBSCAN for spatial hotspot detection;
4. scoring/ranking hotspots with robust normalization, distance decay, and multi-criteria decision analysis;
5. computing accessibility using cumulative opportunities, gravity-based accessibility, 2SFCA, or multimodal routing tools such as R5/r5py;
6. combining taxi and bike-share demand signals despite differences in mode, demographic bias, seasonality, and time period.

For each source, summarize: citation, method, data used, why it is relevant, limitations, and how it should influence our implementation. Prefer primary papers, official documentation, and reproducible open-source tools. Output a short annotated bibliography and a table mapping each project design decision to supporting references.
```

### 3.3 Where Literature Outputs Should Go

Recommended local structure:

```text
docs/literature/
  2026-06-scoring-accessibility-clustering-review.md
  search_log.md
  papers.bib
```

Do not commit full PDFs unless needed. Store links, DOIs, BibTeX, and short notes. If PDFs are downloaded, keep them outside Git or add a dedicated ignored folder later.

Initial seed references:

- HDBSCAN: Campello, Moulavi, and Sander, "Density-Based Clustering Based on Hierarchical Density Estimates" (2013), https://link.springer.com/chapter/10.1007/978-3-642-37456-2_14
- DBSCAN: Ester et al., "A Density-Based Algorithm for Discovering Clusters in Large Spatial Databases with Noise" (1996), https://cdn.aaai.org/KDD/1996/KDD96-037.pdf
- HDBSCAN implementation: https://hdbscan.readthedocs.io/en/latest/how_hdbscan_works.html
- r5py multimodal routing: https://r5py.readthedocs.io/
- r5r paper/tooling: https://findingspress.org/article/21262-r5r-rapid-realistic-routing-on-multimodal-transport-networks-with-r-5-in-r
- Citi Bike official data: https://citibikenyc.com/system-data

## 4. Current Algorithms and Better Alternatives

### 4.1 Current Clustering

Current clustering:

- Restaurant POIs: HDBSCAN on projected point coordinates.
- Taxi drop-offs: HDBSCAN on projected drop-off coordinates.
- Taxi temporal weighting: points are duplicated after rounding weights.
- Optional H3 aggregation exists in code but is disabled.
- Final hotspots: intersection of buffered restaurant-cluster polygons and buffered taxi-cluster polygons.

Strengths:

- HDBSCAN handles noise.
- HDBSCAN can capture clusters with irregular shape better than k-means.
- It is a defensible first choice for point hotspots.

Weaknesses:

- HDBSCAN parameters still need sensitivity testing.
- Duplicating points by rounded weight is a rough approximation.
- Zone-centroid taxi data creates artificial repeated points.
- Convex hull + buffer can over-generalize complex urban street patterns.
- Silhouette score is not enough for spatial hotspot validation.

Better or complementary methods:

- H3 hexagonal aggregation before clustering, especially for huge taxi/bike data.
- KDE or adaptive KDE for smooth demand surfaces.
- Network KDE when points should be interpreted along street networks.
- Getis-Ord Gi* for statistically significant hotspot/coldspot detection on grid cells.
- ST-DBSCAN or time-sliced HDBSCAN for temporal hotspot patterns.
- Bivariate or multi-layer hotspot scoring on common H3 cells instead of polygon intersection only.

Recommended next implementation:

1. Convert taxi, bike, and POI layers to a common H3 grid.
2. Compute per-cell features: taxi drop-offs, bike arrivals, restaurants, rating confidence, cuisine diversity.
3. Score or cluster cells.
4. Dissolve adjacent high-scoring cells into dining districts.
5. Compare HDBSCAN clusters against H3/KDE/Gi* outputs.

### 4.2 Current Accessibility

Current web demo accessibility:

- Euclidean distance from user point to hotspot centroid.
- The accessibility score is normalized within the current result set.

Current standalone accessibility module:

- OSMnx + NetworkX.
- Nearest network node lookup.
- Dijkstra/ego graph by `travel_time`.
- Convex hull of reachable nodes as an isochrone approximation.

Strengths:

- OSMnx/NetworkX is simple and explainable.
- Walking/driving network travel time can be implemented locally.

Weaknesses:

- The Flask demo does not use the isochrone module.
- Convex hull is a rough isochrone geometry and may include unreachable areas.
- Transit accessibility is not implemented end to end.
- `isochrone.py` has a code issue: `calculate_multiple_isochrones()` uses `pd.concat` without importing pandas at module level.
- Default network paths in `isochrone.py` do not match the paths in `config/config.yaml`.

Better options:

- For portfolio MVP: use OSMnx shortest-path travel time to hotspot centroids for walk/drive.
- For stronger multimodal analysis: use r5py/R5 with OSM + GTFS to compute origin-destination travel-time matrices.
- For scoring: use fixed travel-time decay, e.g. `access_score = exp(-lambda * travel_time)` or piecewise travel-time bins.
- For district-level accessibility: compute cumulative opportunities or gravity-based accessibility to restaurants/hotspots.

Recommended next implementation:

1. Pull scoring out of `app.py` into `src/analysis/scoring.py`.
2. Add stable access score based on selected radius or travel-time threshold.
3. Use OSMnx for first walk/drive travel-time matrix.
4. Evaluate r5py for transit once data lineage is clean.

## 5. Can Taxi and Bike Be Combined?

Yes, but they should not be blindly added together.

Taxi and bike represent different user groups, trip purposes, prices, weather sensitivity, and spatial biases. They can still be valuable together if we treat them as separate mobility signals.

Recommended framing:

> Taxi demand captures motorized destination demand and special-trip behavior. Bike arrivals capture short-distance, active-mobility destination demand. Agreement between the two increases confidence that a place is a real urban activity center.

Use cases:

- Feature fusion: taxi drop-offs and bike arrivals become separate features in the hotspot score.
- Cross-validation: bike arrivals validate whether taxi-derived dining zones are also active local destinations.
- Agreement score: cells with high taxi demand and high bike arrivals get higher confidence.
- Bias diagnosis: taxi-heavy but bike-light areas may indicate tourist, airport, nightlife, or car-oriented demand; bike-heavy but taxi-light areas may indicate local, commuter, or short-trip demand.

Time mismatch issue:

- If taxi is 2014 and bike is current, do not claim they measure the same period.
- Use bike first as a validation/robustness layer, not as equal contemporaneous evidence.
- If we want a cleaner temporal comparison, use Citi Bike data from a year close to 2014 if available, or use current taxi zone data plus current Citi Bike for a separate 2024/2025 model.

Recommended fusion design:

```text
spatial_unit = H3 cell or regular grid

taxi_signal = log1p(weighted_taxi_dropoffs)
bike_signal = log1p(weighted_bike_arrivals)
poi_signal = restaurant_density + quality/confidence

mobility_consensus =
    min(percentile(taxi_signal), percentile(bike_signal))

mobility_diversity =
    entropy_or_balance(taxi_signal, bike_signal)

final_area_score =
    w_taxi * taxi_signal +
    w_bike * bike_signal +
    w_poi * poi_signal +
    w_access * access_signal +
    w_consensus * mobility_consensus
```

The first version should keep taxi and bike as visible separate layers in the UI, not hide them inside one opaque score.

## 6. Data Plan

### 6.1 NYC 2014 Yellow Taxi Coordinate Data

Source:

- NYC Open Data 2014 Yellow Taxi Trip Data
- Dataset ID: `gkne-dk5s`
- URL: https://data.cityofnewyork.us/Transportation/2014-Yellow-Taxi-Trip-Data/gkne-dk5s

Relevant fields:

- `pickup_datetime`
- `dropoff_datetime`
- `pickup_longitude`
- `pickup_latitude`
- `dropoff_longitude`
- `dropoff_latitude`
- `trip_distance`
- `passenger_count`
- fare fields

Expected extraction:

- Query one or two months first.
- Filter invalid coordinates.
- Filter dining hours.
- Keep drop-off points for the hotspot experiment.
- Store sampled/processed files under a new experiment namespace.

Suggested local structure:

```text
data/experiments/nyc_2014_coordinate_taxi/
  raw_sample/
  interim/
  processed/
  metrics/
  maps/
```

Do not download a full year until the sample experiment is proven.

### 6.2 2024 Zone-Centroid Baseline

Use current data:

```text
data/interim/taxi_dropoffs_weighted.parquet
data/processed/taxi_hotspots.geojson
data/processed/final_hotspots.geojson
```

But first fix reproducibility:

- `final_hotspots.geojson` has 14 features.
- `intersection_analysis.json` currently reports 0 final hotspots.
- The processed outputs need to be regenerated or clearly marked as demo fixtures.

### 6.3 Citi Bike Data

Source:

- Citi Bike System Data
- URL: https://citibikenyc.com/system-data

Use first as validation, not as a same-period signal unless years match.

Suggested feature:

- End station or end coordinate arrivals during dining windows.
- Weekend/evening arrivals near dining districts.
- H3 aggregated arrivals by time window.

## 7. Experiment Design

### Phase 0: Stabilize

- Commit current cleanup checkpoint. Done: `eade833`.
- Create this plan document.
- Create a small `docs/literature/` folder when the literature review starts.

### Phase 1: Data Ingestion Prototype

- Pull one month of 2014 Yellow Taxi with coordinate fields.
- Save a small sample locally.
- Validate coordinate ranges and invalid zeros.
- Build `taxi_dropoffs_2014_weighted.parquet`.

### Phase 2: Coordinate Pipeline

Run the same core stages as the 2024 baseline:

- Dining-hour filtering.
- Temporal weighting.
- Taxi drop-off clustering or H3 aggregation.
- Spatial intersection with restaurant zones.
- Scoring.
- Output maps and metrics.

### Phase 3: Side-by-Side Comparison

Compare:

- Number of hotspots.
- Average hotspot area.
- Hotspot compactness.
- Overlap with known dining districts.
- Distance from hotspots to restaurant clusters.
- Ranking stability.
- Visual interpretability.
- Whether coordinate data reduces artificial centroid clusters.

Candidate metrics:

```text
hotspot_count
mean_area_sqkm
median_area_sqkm
restaurant_capture_rate
taxi_capture_rate
known_district_overlap
jaccard_overlap_between_2014_and_2024_outputs
rank_correlation
silhouette_or_DBCV_for_clusters
Moran_I_or_Gi_star_for_grid_hotspots
```

### Phase 4: Scoring Redesign

Implement scoring in a standalone module:

```text
src/analysis/scoring.py
```

The module should support:

- current baseline score;
- log/percentile normalized score;
- stable accessibility score;
- confidence-aware score;
- optional taxi+bike fusion score.

### Phase 5: Portfolio Reframe

Present the project as:

> An uncertainty-aware urban dining intelligence system that compares zone-level and coordinate-level mobility data for dining district discovery.

Key evidence:

- Current taxi-zone limitation diagnosed.
- Coordinate-level experiment implemented.
- Scoring improved with literature-backed methods.
- Accessibility upgraded from Euclidean distance to travel-time-aware scoring.
- Bike-share data used as independent validation or auxiliary mobility signal.

## 8. Immediate Next Tasks

1. Create literature review skeleton under `docs/literature/`.
2. Write a NYC Open Data ingestion script for a one-month 2014 taxi sample.
3. Add `src/analysis/scoring.py` with baseline and improved scoring functions.
4. Add a small comparison notebook or script:

```text
notebooks/nyc_2014_vs_2024_comparison.ipynb
```

or, if avoiding notebooks:

```text
src/experiments/compare_2014_coordinates_vs_2024_centroids.py
```

5. Decide whether the portfolio demo should be a Flask app upgrade or a new lightweight Streamlit/Folium dashboard.
