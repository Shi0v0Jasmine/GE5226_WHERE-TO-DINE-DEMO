# Search Log: Urban Dining District Identification Literature Review

**Date:** 2026-06-12  
**Project:** Portfolio-Grade WebGIS for NYC Urban Dining District Identification  
**Search Engine:** mshtools-web_search (parallel queries)  

---

## Search Round 1: Taxi GPS as Revealed-Preference Signals
**Timestamp:** 2026-06-12  
**Queries:**
- `taxi GPS trajectory revealed preference urban activity detection hotspot identification peer-reviewed`
- `POI density mobility demand urban hotspot identification restaurant dining district clustering`
- `DBSCAN HDBSCAN spatial clustering urban POI hotspot detection taxi GPS trajectory 2020-2024`
- `taxi drop-off data urban land use inference activity recognition spatial analysis paper`

**Results:** 11 total results  
**Key Finds:**
- Li, Shi & Zhang (2021) — ST-HDBSCAN two-phase clustering for urban hotspot detection in Shanghai [^1^]
- Du, Meng & Liu (2024) — HDBSCAN+KDE fusion algorithm, 15.85% noise detection vs DBSCAN 7.31% [^2^][^5^]
- Zhao et al. (2019) — Network distance graph partitioning for taxi hotspot detection [^6^]
- Chen et al. (2021) — Local Maximum Density method for taxi stop hotspots [^8^]
- Zhang et al. (2018) — Comparative analysis of K-Means, DBSCAN, CFSFDP, KDE for taxi data [^12^][^18^]

**Thinking:** Strong coverage on taxi trajectory clustering. Need more on ST-DBSCAN specifically, Getis-Ord Gi*, and NYC-specific studies.

---

## Search Round 2: ST-DBSCAN and Spatiotemporal Clustering
**Timestamp:** 2026-06-12  
**Queries:**
- `ST-DBSCAN spatiotemporal clustering urban hotspot detection taxi trajectory paper 2019-2024`
- `kernel density estimation KDE network-constrained hotspot detection urban taxi trajectory`
- `Getis-Ord Gi* spatial hotspot statistics taxi drop-off urban activity cluster analysis`

**Results:** 12 total results  
**Key Finds:**
- ST-HDBSCAN details from Li 2021 paper (Phase 1: ST-HDBSCAN, Phase 2: network filter) [^1^]
- Qin et al. (2017) — Spatiotemporal data field clustering comparison with Getis-Ord Gi* and ST-DBSCAN [^17^]
- Hu 2020 — KDE surface networks with critical points and ridgelines for taxi hotspots [^14^]
- Network KDE (NKDE) formulation from Tang et al. (2016) and Xie & Yan (2008) [^16^]
- Zhang PhD thesis — Space-Time Kernel Density Estimation (STKDE) [^13^]

**Thinking:** Good coverage on KDE variants. Need Getis-Ord Gi* specifically for urban/taxi data, and more on accessibility methods.

---

## Search Round 3: Accessibility Methods and R5/r5py
**Timestamp:** 2026-06-12  
**Queries:**
- `2SFCA two-step floating catchment area accessibility restaurant food access urban gravity model`
- `R5 r5py multimodal accessibility routing python open-source Conveyal`
- `cumulative opportunities gravity model accessibility urban dining restaurant POI comparison`
- `multi-criteria decision analysis MCDA TOPSIS entropy weight urban hotspot scoring ranking`

**Results:** 26 total results  
**Key Finds:**
- Chen & Jia (2019) — Systematic comparison of 24 2SFCA variants with 6 distance decay functions [^43^][^45^]
- r5py documentation and tutorials [^24^][^28^][^31^][^36^]
- Conveyal R5 — 2025 TRB Impactful Research Award [^33^]
- Fink et al. (2022) — r5py: Rapid Realistic Routing with R5 in Python [^24^]
- Hansen (1959) gravity model and Luo & Wang (2003) 2SFCA [^137^][^147^]

**Thinking:** Excellent coverage on accessibility. R5/r5py is clearly the recommended tool. Need more on MCDA/TOPSIS specifically and multimodal data fusion.

---

## Search Round 4: HDBSCAN Foundational Papers
**Timestamp:** 2026-06-12  
**Queries:**
- `HDBSCAN Campello 2013 density-based clustering hierarchical algorithm JOSS`
- `McInnes 2017 hdbscan hierarchical density based clustering JOSS software paper`
- `TOPSIS entropy weight method urban evaluation hotspot ranking multi-criteria decision making geographic`
- `taxi trajectory bike sharing data integration multimodal urban mobility analysis paper`

**Results:** 41 total results  
**Key Finds:**
- Campello, Moulavi & Sander (2013) — HDBSCAN original PAKDD paper [^50^]
- McInnes, Healy & Astels (2017) — hdbscan JOSS software paper [^72^][^84^]
- HDBSCAN widely cited across astronomy, ecology, NLP, geospatial [^48^][^52^][^57^]
- MCDA with entropy weight and TOPSIS for urban spatial analysis [^129^][^130^][^133^]

**Thinking:** HDBSCAN is well-established. MCDA coverage is good but mostly from engineering/materials science — need more urban planning applications.

---

## Search Round 5: DBSCAN Original and Getis-Ord Gi*
**Timestamp:** 2026-06-12  
**Queries:**
- `Ester 1996 DBSCAN density-based clustering algorithm KDD original paper`
- `Getis Ord Gi* hotspot analysis spatial statistics urban point data crime disease`
- `NYC yellow taxi Citi Bike food restaurant accessibility spatial analysis urban`
- `multisource urban mobility data fusion taxi GPS bike-sharing ride-hailing integration`

**Results:** 24 total results  
**Key Finds:**
- Ester et al. (1996) — DBSCAN original, 2014 SIGKDD Test of Time Award [^98^][^99^][^107^]
- Getis-Ord Gi* guides and applications [^132^][^142^][^143^][^146^]
- Liao et al. — DBSCAN + Getis-Ord Gi* for tourist attraction hotspots [^4^]
- NYC searches returned 0 relevant results
- Multimodal data fusion: ride-sourcing DCM approach [^118^], MaaS integration [^149^]

**Thinking:** DBSCAN and Gi* are well-covered. NYC-specific searches continue to return no results — need different query strategies.

---

## Search Round 6: ST-DBSCAN Original and Distance Decay
**Timestamp:** 2026-06-12  
**Queries:**
- `Birant Kut 2007 ST-DBSCAN spatiotemporal data clustering algorithm Data Knowledge Engineering`
- `Getis Ord Gi* hotspot analysis spatial statistics point pattern`
- `food environment accessibility restaurant healthy food mapping GIS 2SFCA Chen`
- `multi-source mobility data taxi bike ride-hailing fusion urban demand estimation`

**Results:** 20 total results  
**Key Finds:**
- Birant & Kut (2007) — ST-DBSCAN original paper [^111^][^112^][^120^]
- stdbscan R package on CRAN [^114^][^115^]
- Chen (2019) — 2SFCA for SNAP food access [^131^]
- Chen & Jia (2019) — 24 2SFCA variants comparison [^45^]
- Data fusion for ride-sourcing demand [^118^]

**Thinking:** ST-DBSCAN is well-documented. Food access applications of 2SFCA are directly relevant. Need more on normalization methods and NYC-specific work.

---

## Search Round 7: Getis-Ord Gi* and NYC Studies
**Timestamp:** 2026-06-12  
**Queries:**
- `Getis Ord Gi* applied taxi trajectory urban hotspot detection spatial clustering`
- `NYC yellow taxi data spatial analysis restaurant food destination dining pattern`
- `gravity model accessibility urban Hansen 1959 potential model cumulative opportunities`
- `taxi and bike sharing combined demand urban mobility multimodal integration paper`

**Results:** 21 total results  
**Key Finds:**
- Getis-Ord Gi* with DBSCAN for tourist hotspot analysis [^4^]
- Getis-Ord Gi* urban analysis guides [^146^]
- Hansen (1959) gravity model [^137^][^138^][^147^]
- Roper et al. (2023) WalkTHERE with exponential decay [^158^][^164^]
- Wu et al. (2022) — Selection probability-based accessibility with taxi data [^157^][^161^]

**Thinking:** NYC-specific searches still return 0 results. May need to use Google Scholar or academic databases directly. The Wu et al. paper using taxi data for accessibility is highly relevant.

---

## Search Round 8: Activity Inference and Normalization
**Timestamp:** 2026-06-12  
**Queries:**
- `New York City TLC taxi data spatial analysis restaurant dining destination land use inference`
- `taxi destination inference land use POI classification urban activity identification revealed preference`
- `distance decay parameter accessibility urban service Gaussian exponential power function selection`
- `Z-score min-max normalization multi-criteria scoring urban hotspot ranking composite index`

**Results:** 16 total results  
**Key Finds:**
- Gong et al. (2019) — Bayesian activity inference from taxi data [^165^][^166^]
- Chen et al. (2021) — Local Maximum Density hotspots [^8^]
- Chen & Jia (2019) — Distance decay function comparison [^45^]
- Roper et al. (2023) — Exponential decay for walkability [^158^]
- Min-max vs. z-score normalization comparison [^159^][^167^][^170^]

**Thinking:** Good coverage on normalization and distance decay. Activity inference from taxi data is well-supported. Ready to synthesize.

---

## Search Round 9: Foundational Accessibility Papers
**Timestamp:** 2026-06-12  
**Queries:**
- `Luo Wang 2003 2SFCA two-step floating catchment area method accessibility health care`
- `Hu 2020 taxi trajectory KDE surface network hotspot peak ridgeline Shanghai`
- `Qin 2017 spatiotemporal data field taxi trajectory hotspot detection Wuhan`
- `Zhao 2019 network distance graph partitioning taxi hotspot detection road network`

**Results:** 17 total results  
**Key Finds:**
- Luo & Wang (2003) — 2SFCA original paper [^171^][^172^][^173^][^183^]
- Hu 2020 — KDE surface networks for taxi hotspots [^177^]
- Enhanced 2SFCA (E2SFCA) by Luo & Qi (2009) [^178^][^184^]
- Hierarchical 2SFCA for healthcare [^176^]
- Calibration studies for 2SFCA parameters [^173^]

**Thinking:** Strong coverage on 2SFCA family. All key accessibility papers are identified. Synthesis can proceed.

---

## Search Round 10: Supplementary Searches
**Timestamp:** 2026-06-12  
**Queries:**
- `Schuurman 2010 distance decay 2SFCA Gaussian function parameter`
- `Wan 2012 Gaussian 2SFCA enhanced floating catchment area`
- `Dai 2011 kernel density 2SFCA accessibility`

**Results:** Various  
**Key Finds:**
- Multiple distance decay function references in Chen & Jia (2019) [^45^]
- Gaussian, exponential, inverse-power, negative-linear, kernel density, and rectangular decay functions
- Schuurman et al. (2010) — Distance decay in Canadian healthcare access

**Thinking:** All six justification areas have sufficient coverage. Ready to finalize report.

---

## Summary Statistics

| Metric | Count |
|---|---|
| Total search rounds | 10 |
| Total queries executed | 40 |
| Total results reviewed | 200+ |
| Primary sources selected | 25 |
| Peer-reviewed papers | 22 |
| Official documentation/tools | 3 |

## Coverage by Justification Area

| Justification Area | Sources | Coverage Assessment |
|---|---|---|
| 1. Taxi GPS as revealed preference | 5 | Strong — Li 2021, Du 2024, Hu 2020, Gong 2019, Chen 2021 |
| 2. POI + mobility demand for hotspots | 2 | Moderate — validation approaches well-documented |
| 3. Clustering algorithm selection | 8 | Strong — DBSCAN, HDBSCAN, ST-DBSCAN, KDE, Gi*, NKDE |
| 4. Scoring with MCDA and decay | 4 | Moderate-Strong — entropy-TOPSIS, 6 decay functions |
| 5. Accessibility (2SFCA, gravity, R5) | 6 | Strong — Hansen 1959, Luo 2003, Chen 2019, r5py |
| 6. Multimodal data fusion | 3 | Moderate — MaaS principles, DCM fusion, normalization |

## Gaps and Future Searches

1. **NYC-specific case studies:** Web search did not return NYC-specific taxi+restaurant papers. Recommended follow-up: Google Scholar search for "NYC yellow taxi restaurant" or "New York City dining district spatial analysis."
2. **Citi Bike + taxi combined analysis:** No direct papers found on combining these two NYC-specific datasets. The general multimodal fusion literature must be adapted.
3. **Real-time WebGIS implementation:** Literature focuses on batch analysis. Real-time clustering and scoring require additional engineering sources.
4. **Restaurant POI quality assessment:** Need sources on OpenStreetMap vs. commercial POI data quality for NYC.
