# Future Transit Accessibility Plan: GTFS + R5

## Scope

Transit is intentionally outside the current implementation. The product supports
walk, bike, and drive through OSMnx. This document defines a reproducible R5
backend without presenting a distance proxy as public-transit routing.

## Required Inputs

- A dated New York regional OSM PBF extract, stored outside Git.
- MTA static GTFS feeds for subway, bus, and relevant commuter services.
- Feed metadata, download URLs, retrieval timestamps, SHA256 checksums, and
  service-date coverage in `data/manifests/transit_sources.json`.
- A Java runtime compatible with the selected R5/r5py release.
- Python 3.11 environment with a pinned r5py version.

OSM and GTFS snapshots must describe compatible dates. Real-time GTFS is not part
of the first transit backend.

## Build Workflow

1. Validate each GTFS archive with MobilityData GTFS Validator.
2. Build one R5 transport network from the PBF and all accepted GTFS feeds.
3. Record Java, R5/r5py, PBF, GTFS, build duration, and network checksum.
4. Persist the built network in `data/networks/r5/`, excluded from Git.
5. Run smoke routes before generating any OD matrix.

## Travel-Time Definition

- Origins: user point or a fixed evaluation grid.
- Destinations: rankable hotspot centroids.
- Departure windows: weekday lunch 11:30-13:30, weekday dinner 18:00-20:00,
  weekend dinner 18:00-21:00, and late night 22:00-00:00.
- Sample every 10 minutes within the selected window.
- Include access walk, initial wait, in-vehicle time, transfer walk, transfer
  wait, and egress walk.
- Report median and 90th-percentile travel time across departure samples.
- Default maximum: 60 minutes; maximum two transfers.
- Unreachable OD pairs remain null/infinite and never become zero.

## OD Matrix and Cache

Cache keys must include:

```text
network_checksum
service_date
departure_window
origin_h3_r10
destination_hotspot_id
max_trip_duration
max_transfers
walk_speed
```

Store partitioned Parquet under `data/cache/r5_od/`. A cache entry includes the
median, p90, number of sampled departures, reachability rate, and creation time.
Changing any network, schedule, or routing parameter invalidates the key.

## Backend Contract

Implement `R5TravelTime` behind the existing travel-time interface:

```python
matrix(origins, destinations) -> np.ndarray
single(origin, destination) -> float
is_available() -> bool
info() -> dict
```

`info()` must expose `requested_backend`, `effective_backend`, network/feed
checksums, service date, departure window, and whether a fallback occurred.
Research mode fails when R5 is unavailable. Product mode may use a proxy only
when `allow_fallback=true`, with `is_estimate=true` and a concrete reason.

## Validation

- Hand-check fixed OD pairs against the MTA trip planner for the same time.
- Verify that later-night service changes are reflected.
- Test unreachable destinations, missing service dates, DST, midnight crossing,
  and disconnected street access.
- Compare median absolute error and rank correlation against reference journeys.
- Keep OSMnx walk access and R5 transit results separately visible in diagnostics.

## Delivery Gate

Transit may be enabled in the UI only after source manifests, a reproducible
network build, fixed-OD tests, cache invalidation tests, and backend provenance
are complete.
