# Where to DINE Project Status

Updated: 2026-06-29
Branch: `fixing`

## Delivered

- Flask + Leaflet product application with profile, time, mode, backend, score
  version, and maximum travel-time controls.
- Streamlit research dashboard with five views and precomputed-artifact-only
  execution.
- `v1_legacy`, `v2_entropy_legacy`, and default `v3_product` scoring.
- Robust v3 preprocessing, Bayesian ratings, constrained entropy/prior weights,
  explicit area-quality/accessibility separation, and profile access weights.
- OSMnx walk/bike/drive backends with mode speeds and drive edge speeds.
- Explicit backend provenance and strict HTTP 503 behavior when fallback is
  disabled.
- JFK/LGA diagnostic retention and product/API exclusion.
- Resumable daily 2014 taxi downloader with retries, boundary repair, dedup,
  SHA256 manifests, and deterministic fixture output.
- Same-week Citi Bike arrival downloader and H3 taxi-bike consensus code.
- Same-trip coordinate/centroidized experiment orchestration.
- Stratified 300,000-point HDBSCAN fitting and approximate assignment.
- H3 9/10/11 Gi* analysis with neighboring zero-value cells.
- Known dining-district coverage and daily hit stability.
- Meter-based spatial calculations using `EPSG:32618`.
- Pinned dependency lock and future GTFS/R5 implementation plan.

## Verified

- `55 passed` with pytest.
- Python compilation succeeds for app, dashboard, scripts, and source modules.
- Streamlit `AppTest`: five tabs, zero runtime exceptions.
- Flask API checked against generated v3 artifacts.
- Product artifact: 55 rankable hotspots and 7 airport diagnostics.
- API reports the 7 excluded airport hotspots.
- v3 rank is contiguous from 1 through 55.
- One-day legacy processing produces 282,165 dining-window trips with 282,165
  unique IDs and exactly one active day.

## Data Status

The formal Monday-Sunday experiment is not yet generated. The local workspace
contains only the repaired `2014-01-06` raw taxi file:

- 394,972 source rows
- `2014-01-06 00:00:00` to `2014-01-06 23:59:58`
- SHA256 `02b65ab4b6932585c9051d7746e0a6595ffaf38f2571f26a8448100fc5803001`

Its processed and clustering outputs are a legacy pipeline/UI baseline only.
They must not be used as the seven-day controlled result. This distinction is
recorded in `data/manifests/legacy_2014_one_day_manifest.json`.

The attempt to download the remaining six days was blocked before execution by
the current Codex external-network approval/usage limit. Citi Bike and OSMnx
network downloads were therefore not attempted in this run.

## Remaining Acceptance Work

1. Run both download scripts when external network access is available.
2. Re-run stage 10 and confirm exactly seven active days.
3. Run `python -m src.experiments.run_controlled_resolution_experiment`.
4. Download all three OSMnx graphs and run fixed NYC OD checks.
5. Review the generated exact/centroidized and taxi-bike results in Streamlit.
6. Complete desktop/mobile screenshot QA. The in-app browser declined local
   address access during this run, so no screenshot claim is made.

## Commands

```powershell
python scripts/download_2014_taxi_month.py --start 2014-01-06 --end 2014-01-13
python scripts/download_citibike_2014.py --start 2014-01-06 --end 2014-01-13
python src/data_processing/10_process_2014_taxi_data.py
python -m src.experiments.run_controlled_resolution_experiment
python scripts/download_nyc_network.py
python -m pytest
python app.py
streamlit run dashboard.py
```

Product: `http://127.0.0.1:5000`
Research dashboard: `http://localhost:8501`
