# NYC 2014 Controlled Spatial-Resolution Experiment

## Question

How much dining-hotspot information is lost when precise taxi drop-off coordinates
are replaced by taxi-zone centroids?

The primary experiment uses Yellow Taxi trips with drop-offs from `2014-01-06
00:00:00` through `2014-01-13 00:00:00`. Both branches contain exactly the same
trip IDs and filters:

- `coordinate`: original drop-off longitude/latitude.
- `centroidized`: spatially join each point to its TLC zone, then replace the
  coordinate with that zone's projected centroid.

The 2024 zone-only result is a supplementary real-world limitation case, not the
control group, because its year and sample size differ.

## Data Contract

The daily downloader writes one Parquet file per half-open UTC/local dataset day,
supports chunk resume, retries failed pages, removes duplicate records, and
produces a manifest with row counts, bounds, file sizes, and SHA256 checksums.

Required active days:

```text
2014-01-06, 2014-01-07, 2014-01-08, 2014-01-09,
2014-01-10, 2014-01-11, 2014-01-12
```

Raw files and temporary experiment Parquet are ignored by Git. The deterministic
fixture, manifests, metrics JSON, and output GeoJSON are committed.

## Clustering

HDBSCAN remains the primary exploratory model:

- fixed random seed `42`;
- day-stratified training sample, maximum 300,000 points;
- `prediction_data=True`;
- remaining points assigned with `approximate_predict`;
- original temporal weights retained for counts and ranking.

For each branch report cluster count, noise share, DBCV, silhouette,
Davies-Bouldin, mean area, compactness, POI IoU, and airport hotspot count.

## Statistical Validation

Aggregate weighted arrivals to H3 resolution 10. Add the immediate zero-value
neighbor ring before calculating local Getis-Ord Gi*. Repeat at resolutions 9 and
11 to expose scale sensitivity. Output observed and analysis-cell counts,
z-scores, permutation p-values, and 95% hotspot flags.

No fixed threshold determines a winner. The result is interpreted from effect
size, stability, and spatial plausibility.

## Known Dining Districts

Use six positive reference districts:

- Chinatown
- Koreatown
- East Village
- Little Italy
- Williamsburg
- Astoria

Report coverage@10, coverage@20, nearest-hotspot distance, and the number of days
each district is hit by a daily top-20 H3 cell. ROC/AUC is not used because the
reference list contains no defensible negative examples.

## Airport Policy

TLC zones 132 (JFK) and 138 (LaGuardia) are tagged. Airport clusters remain in
diagnostic files and are excluded from all product rankings and API results.

## Citi Bike Validation

Use same-week end-station arrivals and map them to H3 resolution 10. Calculate
taxi-bike percentile consensus only inside the station convex hull plus a 1 km
buffer. Cells outside 2014 Citi Bike coverage remain `null`; they are not
penalized.

## Outputs

`data/processed/controlled_2014/` contains:

- branch hotspot GeoJSON files;
- Gi* GeoJSON for resolutions 9, 10, and 11;
- taxi-bike consensus GeoJSON when bike data is available;
- `controlled_resolution_metrics.json`.

The Streamlit dashboard only reads these outputs and never launches clustering
inside an HTTP request.

## Commands

```powershell
python scripts/download_2014_taxi_month.py --start 2014-01-06 --end 2014-01-13
python scripts/download_citibike_2014.py --start 2014-01-06 --end 2014-01-13
python src/data_processing/10_process_2014_taxi_data.py
python -m src.experiments.run_controlled_resolution_experiment
```

The experiment must fail if it does not find exactly seven active days or if the
trip-ID vectors differ between branches.
