# Literature Import Audit

Date: 2026-06-12
Source folder: `C:\Users\21136\Downloads\Kimi_Agent_WebGIS Dining Hotspots\docs\literature`

## Imported Files

- `2026-06-scoring-accessibility-clustering-review.md`
- `search_log.md`
- `papers.bib`

These files are useful as a first literature map for the reframe, especially around clustering, accessibility, and taxi trajectory hotspot detection.

## Quality Notes

Use these files as a working bibliography, not as final academic references yet.

Issues observed:

- Some Markdown text has mojibake/encoding artifacts, such as corrupted punctuation and Greek symbols.
- Some citation details are incomplete, for example entries using `others` instead of full author lists.
- At least one BibTeX key was invalid because it contained spaces; it was renamed from `entropy topsis urban` to `entropy_topsis_urban_2023`.
- Some claims need primary-source verification before being used in the final README, resume bullets, or report.
- The review is broad and useful, but it mixes peer-reviewed papers, tool docs, reports, and general web-search findings. We should separate those in the final bibliography.

## Immediate Takeaways For This Project

The literature search supports these implementation decisions:

1. Keep HDBSCAN as a defensible baseline clustering method.
   - It is suitable for irregular spatial clusters and noisy taxi/POI data.
   - We still need sensitivity testing and an objective validation metric.

2. Add a grid/H3 layer for comparison and fusion.
   - H3/grid aggregation makes taxi, bike, and restaurant POI signals easier to combine.
   - It also supports Getis-Ord Gi* hotspot statistics and stable normalization.

3. Compare HDBSCAN with KDE or Network KDE.
   - KDE is a natural complement for smooth mobility demand surfaces.
   - Network KDE is theoretically stronger for road-constrained mobility, but more complex.

4. Improve scoring before presenting the project as portfolio-grade.
   - Current max normalization is too sensitive to outliers.
   - Use log scaling, winsorization, z-scores, percentile ranks, or MCDA methods such as entropy weighting and TOPSIS.

5. Replace Euclidean demo distance with travel-time-aware accessibility.
   - Short-term: OSMnx/NetworkX walk and drive travel times.
   - Stronger version: r5py/R5 with OSM and GTFS for transit.

6. Taxi + Citi Bike fusion is possible, but should be framed as multimodal evidence rather than a simple sum.
   - Taxi demand and bike arrivals should be normalized separately.
   - Use them as independent signals and show agreement/disagreement.
   - If years do not match, treat bike data as validation or a separate scenario.

## References To Verify First

Prioritize verifying these before implementation choices are finalized:

- Li, Shi & Zhang (2021), two-phase ST-HDBSCAN for urban hotspot detection.
- Campello, Moulavi & Sander (2013), HDBSCAN foundation.
- McInnes, Healy & Astels (2017), `hdbscan` software paper.
- Ester et al. (1996), DBSCAN foundation.
- Ord & Getis (1995), Gi* hotspot statistic.
- Chen & Jia (2019), 2SFCA distance decay comparison.
- Luo & Wang (2003), 2SFCA foundation.
- Fink et al. (2022), r5py/R5 routing.
- Any cited Taxi + Bike multimodal fusion paper, because current coverage is weaker than the clustering/accessibility coverage.

## Recommended Follow-Up

Create a cleaned, project-specific bibliography after verification:

```text
docs/literature/
  2026-06-scoring-accessibility-clustering-review.md
  2026-06-literature-import-audit.md
  2026-06-verified-methodology-bibliography.md
  search_log.md
  papers.bib
```

The verified bibliography should be shorter and directly tied to implementation decisions:

- clustering choice;
- coordinate-level taxi experiment;
- H3/grid fusion;
- scoring normalization;
- accessibility method;
- taxi-bike multimodal validation.
