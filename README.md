# Where to DINE

Where to DINE is a NYC dining-area discovery project built from mobility demand,
restaurant POIs, time patterns, and network accessibility. It has two interfaces:

- A Flask + Leaflet product demo for user-facing recommendations.
- A Streamlit research dashboard for comparing methods and diagnostics.

The research question is whether precise taxi drop-off coordinates identify more
meaningful dining hotspots than taxi-zone centroids. The controlled experiment
uses the same Yellow Taxi trips from `2014-01-06` through `2014-01-12` in both
branches, changing only spatial precision.

## Current Method

The experiment produces:

- `coordinate`: original 2014 drop-off coordinates.
- `centroidized`: the same trip IDs mapped to TLC taxi-zone centroids.
- HDBSCAN clusters trained on a day-stratified sample of at most 300,000 points;
  remaining points are assigned with HDBSCAN approximate prediction.
- H3 resolution 10 Gi* validation, with resolutions 9 and 11 for sensitivity.
- Known-district validation for Chinatown, Koreatown, East Village, Little Italy,
  Williamsburg, and Astoria.
- Same-week Citi Bike arrival consensus within the 2014 bike service area.

JFK and LaGuardia taxi zones (`LocationID` 132 and 138) remain in research
diagnostics but are excluded from product rankings.

## Scoring

Three score versions are retained:

- `v1_legacy`: original max-normalized score.
- `v2_entropy_legacy`: Entropy-TOPSIS reproduction.
- `v3_product`: robust product score used by default.

`v3_product` separates static area quality from request-time accessibility:

```text
area quality = mobility demand + POI quality + time fit + data confidence
recommendation = (1 - access weight) * area quality
               + access weight * network accessibility
```

Inputs use `log1p`, 1st/99th percentile winsorization, and percentile scaling.
Entropy weights are blended 50/50 with profile priors and constrained to
`0.10-0.45`. POI quality combines restaurant density, Bayesian rating, and rating
coverage. Accessibility uses a mode-specific half-life decay.

## Setup

Python 3.11 is the target runtime; Python 3.12 is also supported.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-lock.txt
python -m pytest
```

## Product Demo

```powershell
python app.py
```

Open `http://127.0.0.1:5000`. The UI supports profile, time profile, travel mode,
routing backend, score version, and time threshold controls.

The recommendation endpoint is:

```http
POST /api/recommend?profile=balanced&time_profile=dinner&mode=walk&backend=proxy&score_version=v3&max_time_min=30&limit=10&allow_fallback=true
Content-Type: application/json

{"lat": 40.728, "lon": -73.994}
```

OSMnx requests report `requested_backend`, `effective_backend`,
`fallback_reason`, and `is_estimate`. With `allow_fallback=false`, a missing or
failed graph returns HTTP 503 instead of silently using a proxy.

## Research Dashboard

```powershell
streamlit run dashboard.py
```

The dashboard reads precomputed artifacts only. Its five views cover controlled
resolution comparison, HDBSCAN/Gi*, score versions, daily stability, and
airport/taxi-bike diagnostics.

## Reproduce the Seven-Day Experiment

```powershell
python scripts/download_2014_taxi_month.py --start 2014-01-06 --end 2014-01-13
python scripts/download_citibike_2014.py --start 2014-01-06 --end 2014-01-13
python src/data_processing/10_process_2014_taxi_data.py
python -m src.experiments.run_controlled_resolution_experiment
```

Download OSMnx graphs separately:

```powershell
python scripts/download_nyc_network.py
```

Raw taxi, Citi Bike, and GraphML files are intentionally excluded from Git.
Manifests, fixed fixtures, processed GeoJSON, and metrics JSON are the
reproducibility contract.

## Repository Map

```text
app.py                              Flask API and product UI
dashboard.py                        Read-only Streamlit research dashboard
src/analysis/                       Scoring, clustering, H3/Gi*, validation
src/experiments/                    Controlled experiment orchestration
src/travel_time/                    Proxy and OSMnx routing backends
scripts/                            Resumable data and network downloads
data/manifests/                     Checksums and row-count manifests
data/fixtures/                      Deterministic small samples
data/processed/controlled_2014/     Research outputs
docs/                               Method and future-work documentation
tests/                              Unit, downloader, airport, and API tests
```

See [the controlled experiment design](docs/NYC_2014_COORDINATE_TAXI_COMPARISON_PLAN.md)
and [the future R5 transit plan](docs/FUTURE_TRANSIT_R5_PLAN.md).
