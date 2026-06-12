# Annotated Bibliography: Urban Dining District Identification — Clustering, Scoring, and Accessibility

**Date:** 2026-06-12  
**Project:** Portfolio-Grade WebGIS for NYC Urban Dining District Identification  
**Scope:** Peer-reviewed and official technical sources justifying six core design decisions  

---

## Executive Summary

This review identifies **25 primary sources** across six technical justification domains for a WebGIS project that ranks urban dining districts by fusing restaurant POIs, taxi drop-offs, bike-share trips, and multimodal accessibility. The selected papers span density-based clustering (DBSCAN → HDBSCAN → ST-HDBSCAN), kernel density estimation, spatial hotspot statistics (Getis-Ord Gi*), accessibility measurement (gravity models, 2SFCA, R5/r5py), multi-criteria decision analysis (entropy-TOPSIS), and distance decay parameterization. Where possible, NYC-specific or US-based studies are prioritized; strong international case studies (Shanghai, Wuhan, Beijing, Shenzhen) are included when methods are directly transferable.

---

## 1. Taxi Drop-Offs and GPS Trajectories as Revealed-Preference Signals

The foundational justification for using taxi GPS data as a proxy for urban activity rests on the principle that **drop-off events encode revealed preferences about destination attractiveness** — passengers pay to travel to locations they value, making taxi trajectories a form of sensor network for urban vitality [^1^][^165^].

### 1.1 Li, Shi & Zhang (2021) — Two-Phase ST-HDBSCAN Clustering

**Citation:** Li, F., Shi, W., & Zhang, H. (2021). A Two-Phase Clustering Approach for Urban Hotspot Detection With Spatiotemporal and Network Constraints. *IEEE Journal of Selected Topics in Applied Earth Observations and Remote Sensing*, 14, 4514–4529. https://doi.org/10.1109/JSTARS.2021.3068308

**Method:** ST-HDBSCAN (Phase 1: spatiotemporal hierarchical density clustering; Phase 2: network-distance region growing filter). DBCV index used for parameter selection.

**Data:** 85 million taxi GPS records from 12,000 taxis in Shanghai (April 1, 2018); 493,675 POIs; Luojia1-01 night-time light data; OpenStreetMap street network.

**Relevance:** This is the strongest single source for the project. It explicitly validates taxi drop-off clusters against high-density POI areas, finding a "well matching degree" between detected hotspots and POI hotspots [^1^]. The two-phase approach (spatiotemporal clustering followed by network-constrained filtering) directly addresses the need to detect dining districts that are both temporally active and network-accessible. The use of DBCV for parameter selection reduces subjectivity.

**Limitations:** Shanghai context; suburb clusters are sparse and large, reducing homogeneity. Network distance calculation is computationally expensive for real-time applications.

**Implementation Influence:** Adopt the two-phase framework: ST-HDBSCAN for initial clustering, then network-distance filtering. Use DBCV for parameter selection. Validate clusters against POI density.

### 1.2 Du, Meng & Liu (2024) — HDBSCAN+KDE Fusion Algorithm

**Citation:** Du, J., Meng, C., & Liu, X. (2024). Analysis of Urban Residents' Travelling Characteristics and Hotspots Based on Taxi Trajectory Data. *Applied Sciences*, 14(3), 1279. https://doi.org/10.3390/app14031279

**Method:** Fusion of time-threshold HDBSCAN with kernel density analysis. Three-stage pipeline: time-constrained HDBSCAN clustering → kernel density analysis → heatmap visualization.

**Data:** Taxi trajectory data (weekday/weekend comparison).

**Relevance:** Demonstrates that HDBSCAN achieves a **15.85% noise detection rate** compared to DBSCAN's 7.31%, significantly reducing noise impact in subsequent kernel density analysis [^2^][^5^]. The chi-square test on weekday travel data yields p = 0.023, confirming significant correlation between hotspot distribution and travel paths.

**Limitations:** Methodological paper without detailed city context; KDE bandwidth selection not fully discussed.

**Implementation Influence:** Use HDBSCAN (not DBSCAN) as the primary clustering algorithm for its superior noise handling. Combine with KDE for visualization and density surface generation.

### 1.3 Hu, Miller & Li (2020) — KDE Surface Networks for Mobility Hotspots

**Citation:** Hu, Y., Miller, H. J., & Li, X. (2020). Detecting and Analyzing Mobility Hotspots using Surface Networks. *arXiv:2006.03499*. https://arxiv.org/abs/2006.03499

**Method:** Kernel density estimation (KDE) to convert mobile object collections into continuous surfaces, followed by topological extraction of critical points (peaks, pits, passes) and critical lines (ridgelines, course-lines). Surface network construction and graph-theoretic characterization.

**Data:** Taxi cab data from Shanghai, China.

**Relevance:** Provides a rigorous statistical foundation for using KDE to summarize large mobility datasets. The surface network approach (peaks + ridgelines) produces **topologically stable hotspot definitions** that persist across time periods [^14^][^177^]. Findings match scientific and anecdotal knowledge about human activity patterns.

**Limitations:** Computationally intensive surface extraction; requires careful bandwidth selection; Shanghai-specific.

**Implementation Influence:** Use KDE as the density estimation backbone. Consider surface network extraction for robust hotspot boundary definition. Bandwidth selection via Silverman's rule or cross-validation.

### 1.4 Gong et al. (2019) — Activity Pattern Extraction from Taxi Data

**Citation:** Gong, L., et al. (2019). Extracting activity patterns from taxi trajectory data: A two-layer framework using spatio-temporal clustering, Bayesian probability, and Monte Carlo simulation. *International Journal of Geographical Information Science*.

**Method:** Two-layer framework: spatio-temporal clustering (DBSCAN) for stay-point detection → Bayesian probability model for activity inference using POI opening times and distances → Monte Carlo simulation for probabilistic activity assignment.

**Data:** Taxi GPS trajectory data.

**Relevance:** Directly addresses the challenge of **inferring trip purposes from taxi drop-off points** [^165^][^166^]. Critiques deterministic nearest-POI approaches and instead advocates probabilistic models. Demonstrates that drop-off points combined with temporal information and POI semantics can infer dining/shopping/entertainment activities.

**Limitations:** Activity inference accuracy depends on POI data completeness; computationally intensive Monte Carlo simulation.

**Implementation Influence:** Use probabilistic (not deterministic) methods to associate taxi drop-offs with dining activities. Combine temporal features (drop-off time) with POI categories for activity inference.

### 1.5 Chen, Zhang, Li & Zhou (2021) — Local Maximum Density Hotspots

**Citation:** Chen, C., et al. (2021). Urban hotspots detection of taxi stops with local maximum density. *Computers, Environment and Urban Systems*, 90.

**Method:** Local Maximum Density (LMD) method: grid-based density estimation → local maximum identification → neighborhood expansion. Elbow method for radius selection.

**Data:** 7,909 taxis in Wuhan, China (February–August 2015); GPS sampling 10–60s.

**Relevance:** Introduces the concept of **local hotspots** — small neighborhoods around local maximum density grids that capture multi-density peaks caused by preferences to get on/off near typical POIs [^8^]. More aligned with human spatial cognition of small-scale hotspots than global clustering methods.

**Limitations:** Grid-based approach introduces MAUP (Modifiable Areal Unit Problem); less effective for very large study areas.

**Implementation Influence:** Consider LMD as a complementary method for fine-grained hotspot detection within larger clusters. Use elbow method for adaptive parameter selection.

---

## 2. POI Density and Mobility Demand for Hotspot Identification

### 2.1 Key Principle: POI as Ground Truth for Mobility Hotspots

Multiple studies establish that **POI density has a strong positive correlation with human activity intensity**, making POI data an essential validation layer for mobility-derived hotspots [^1^][^6^]. The distribution of POIs reflects urban functional structure — restaurant POIs in particular cluster in commercial and mixed-use districts where taxi drop-offs and bike-share trips also concentrate.

### 2.2 Zhao et al. (2019) — Network-Constrained Graph Partitioning

**Citation:** Zhao, P., et al. (2019). A network distance and graph-partitioning-based clustering method for detecting urban hotspots using taxi trajectories. *International Journal of Geographical Information Science*.

**Method:** Four-step network-constrained method: (1) Jaccard distance for road segment similarity; (2) similarity graph construction; (3) InfoMap graph partitioning; (4) head/tail breaks for hotspot identification.

**Data:** 6,500+ taxis in Wuhan, China; road network from OpenStreetMap; POI data for validation.

**Relevance:** Represents drop-off events as **linear features (sub-trajectories)** rather than points, improving hotspot detection precision in network space [^6^]. Does not require parameter determination by prior knowledge — a major advantage over DBSCAN/HDBSCAN. POI data used to examine hotspot detection accuracy.

**Limitations:** Complex implementation; InfoMap partitioning can be slow for large networks; Wuhan-specific road network structure.

**Implementation Influence:** Consider graph-partitioning as an alternative when parameter-free hotspot detection is desired. Use POI data as external validation for all clustering results.

### 2.3 Zhang et al. (2018) — Comparative Spatial Analysis Methods

**Citation:** Zhang, P., et al. (2018). Spatial-temporal travel pattern mining using massive taxi trajectory data. *ISPRS Archives*.

**Method:** Comparative analysis of K-Means, DBSCAN, CFSFDP, and KDE for taxi trajectory hotspot detection.

**Data:** Massive taxi trajectory dataset.

**Relevance:** Systematic comparison finding that **DBSCAN and KDE have the highest accuracy in hotspot discovery and classification**, while DBSCAN and CFSFDP achieve the highest spatial accuracy for POI position extraction [^12^][^18^]. DBSCAN and KDE are most suitable for heat index classification. K-Means has the best operating efficiency for large datasets.

**Limitations:** Comparative framework without novel method contribution; specific dataset characteristics may affect generalizability.

**Implementation Influence:** Prioritize DBSCAN or HDBSCAN for clustering, KDE for density visualization. Use K-Means only if computational efficiency is paramount and cluster shapes are known to be spherical.

---

## 3. Clustering Algorithm Selection: DBSCAN, HDBSCAN, KDE, Network KDE, Getis-Ord Gi*, ST-DBSCAN

### 3.1 Ester, Kriegel, Sander & Xu (1996) — DBSCAN

**Citation:** Ester, M., Kriegel, H.-P., Sander, J., & Xu, X. (1996). A density-based algorithm for discovering clusters in large spatial databases with noise. *Proceedings of the 2nd International Conference on Knowledge Discovery and Data Mining (KDD-96)*, 226–231. https://doi.org/10.1145/300146.3001507

**Method:** Density-Based Spatial Clustering of Applications with Noise. Two parameters: ε (neighborhood radius) and MinPts (minimum points). Core point, border point, and noise point taxonomy. Density reachability and connectivity definitions.

**Data:** Synthetic data and SEQUOIA 2000 benchmark real data.

**Relevance:** **Foundational paper** that introduced density-based clustering to the data mining community. Won the **2014 SIGKDD Test of Time Award** [^98^][^99^]. DBSCAN discovers clusters of arbitrary shape, is robust to noise, and scales well to large databases when spatial index structures are effective.

**Limitations:** Sensitive to parameter selection (ε, MinPts); assumes homogeneous density — struggles with clusters of varying densities; uses Euclidean distance by default.

**Implementation Influence:** DBSCAN is the baseline. Use k-distance plots for parameter selection. However, prefer HDBSCAN for urban data with varying density.

### 3.2 Campello, Moulavi & Sander (2013) — HDBSCAN

**Citation:** Campello, R. J. G. B., Moulavi, D., & Sander, J. (2013). Density-based clustering based on hierarchical density estimates. *Pacific-Asia Conference on Knowledge Discovery and Data Mining (PAKDD)*.

**Method:** Hierarchical extension of DBSCAN. Computes density hierarchy via minimum spanning trees weighted by mutual reachability distance. Extracts flat clusters based on cluster stability across density levels.

**Relevance:** Eliminates the need to select a single ε parameter. Handles **clusters of varying densities** — the critical limitation of DBSCAN [^50^][^57^]. Builds a hierarchy of clusters and selects the most stable ones. Theoretical foundation for the widely used HDBSCAN implementation.

**Limitations:** More computationally intensive than DBSCAN; stability-based extraction can miss small clusters; still uses Euclidean distance by default.

**Implementation Influence:** **Primary clustering recommendation** for the project. Use the `hdbscan` Python package. Only parameter needed: `min_cluster_size`. Much more robust than DBSCAN for urban mobility data with mixed densities.

### 3.3 McInnes, Healy & Astels (2017) — HDBSCAN Software

**Citation:** McInnes, L., Healy, J., & Astels, S. (2017). hdbscan: Hierarchical density based clustering. *Journal of Open Source Software*, 2(11), 205. https://doi.org/10.21105/joss.00205

**Method:** Python implementation of HDBSCAN. Optimized algorithms for minimum spanning tree construction, cluster hierarchy condensation, and stability-based extraction.

**Relevance:** **The production-grade implementation** used in the vast majority of applied HDBSCAN research [^72^][^84^]. Implements accelerated hierarchical density clustering with O(n log n) complexity. Provides prediction and soft clustering capabilities.

**Limitations:** Memory-intensive for very large datasets (>100K points may require approximation); GPU acceleration not built-in.

**Implementation Influence:** Use `hdbscan` Python package. Set `min_cluster_size` based on expected minimum dining district size (e.g., 10–50 POIs). Use `metric='haversine'` for geographic coordinates.

### 3.4 Birant & Kut (2007) — ST-DBSCAN

**Citation:** Birant, D., & Kut, A. (2007). ST-DBSCAN: An algorithm for clustering spatial–temporal data. *Data & Knowledge Engineering*, 60(1), 208–221. https://doi.org/10.1016/j.datak.2006.01.013

**Method:** Spatiotemporal extension of DBSCAN. Three parameters: ε_spatial, ε_temporal, MinPts. Combined spatiotemporal distance metric: DST(p,q) = √[(d_space/ε_space)² + (d_time/ε_time)²].

**Data:** Sensor network data, spatial-temporal data warehouse.

**Relevance:** **Foundational spatiotemporal clustering paper** with 1,000+ citations [^111^][^112^]. Directly extends DBSCAN to handle temporal dimension. Used as the basis for ST-HDBSCAN and many subsequent spatiotemporal clustering methods.

**Limitations:** Same density homogeneity assumption as DBSCAN; three parameters to tune; temporal distance metric assumes linear time — may not capture cyclical patterns well.

**Implementation Influence:** Use ST-DBSCAN concepts for incorporating temporal constraints. Consider ST-HDBSCAN (Li et al. 2021) as the more robust alternative. Python implementations available (`st_dbscan`, `py-st-dbscan`).

### 3.5 Getis-Ord Gi* Spatial Hotspot Statistic

**Citation:** Ord, J. K., & Getis, A. (1995). Local Spatial Autocorrelation Statistics: Distributional Issues and an Application. *Geographical Analysis*, 27(4), 286–306. https://doi.org/10.1111/j.1538-4632.1995.tb00912.x

**Method:** Local spatial autocorrelation statistic. For each location i, Gi* compares the local weighted sum of a variable within a defined neighborhood to the global mean, producing a z-score and p-value.

**Relevance:** **Standard tool for hotspot mapping** in GIS software (ArcGIS, QGIS, R `spatstat`, Python `libpysal`) [^142^][^144^]. Identifies statistically significant clusters of high values (hotspots) and low values (coldspots). Complements density-based clustering by providing statistical significance testing.

**Limitations:** Requires areal aggregation (grid cells or polygons) — point data must be converted to counts; distance threshold choice strongly affects results; does not identify spatial outliers (unlike Local Moran's I).

**Implementation Influence:** Use Gi* as a validation and comparison method for clustering results. Aggregate taxi/bike-share drop-offs to grid cells, then apply Gi* to identify statistically significant dining activity hotspots. Report z-scores at 90%, 95%, and 99% confidence levels.

### 3.6 Xie & Yan (2008); Tang et al. (2016) — Network KDE

**Citation:** Xie, Z., & Yan, J. (2008). Kernel density estimation of traffic accidents in a network space. *Computers, Environment and Urban Systems*.  
Tang, L., et al. (2016). A network-constrained integrated method for detecting and analyzing urban hotspots. *ISPRS International Journal of Geo-Information*.

**Method:** Network-constrained kernel density estimation (NKDE) — restricts kernel bandwidth to network distance along road segments rather than Euclidean distance.

**Relevance:** Vehicle movement is a **network-constrained mobility process** [^6^][^16^]. NKDE produces more accurate density estimates for taxi drop-offs than planar KDE because it respects road network topology. Gaussian kernel with 200m bandwidth commonly used.

**Limitations:** Requires clean road network data; computationally expensive for large networks; bandwidth selection more complex in network space.

**Implementation Influence:** Use NKDE (via `spNetwork` R package or `SASNA` Python) instead of planar KDE for taxi/bike-share hotspot density estimation. Validate against planar KDE results.

---

## 4. Scoring and Ranking Hotspots: Normalization, Distance Decay, and MCDA

### 4.1 Chen & Jia (2019) — Comparative Analysis of 2SFCA with Six Distance Decay Functions

**Citation:** Chen, X., & Jia, P. (2019). A comparative analysis of accessibility measures by the two-step floating catchment area (2SFCA) method. *International Journal of Geographical Information Science*, 33(9), 1739–1758. https://doi.org/10.1080/13658816.2019.1578978

**Method:** Systematic comparison of **24 2SFCA variants** using six distance decay functions: rectangular cumulative-opportunity (CUMR), negative-linear cumulative-opportunity (CUML), inverse-power gravity-type (POW), exponential gravity-type (EXP), Gaussian gravity-type (GAUSS), and kernel density (KD).

**Data:** Point-based food stores (supply) and population (demand) in Arkansas, United States.

**Relevance:** **Most comprehensive systematic evaluation of distance decay functions** for accessibility measurement [^43^][^45^]. Key findings: (1) on small scales, catchment size is the most critical variable; (2) on large scales, distance decay function choice dominates; (3) POW20 should be avoided due to excessive variability; (4) all models converge when catchment size d₀ ≥ 9.5 miles.

**Limitations:** Arkansas context — rural-urban mix may not generalize to dense NYC; food stores only (not restaurants specifically).

**Implementation Influence:** Use **Gaussian or exponential decay** for the project (best balance of interpretability and performance). Conduct sensitivity analysis on catchment size (try 400m, 800m, 1200m walking). Avoid binary (rectangular) decay as it overestimates supply-demand interaction.

### 4.2 Roper et al. (2023) — WalkTHERE Index with Exponential Decay

**Citation:** Roper, J., et al. (2023). WalkTHERE: A reproducible index for walkability. *Environment and Planning B*.

**Method:** Multi-activity accessibility index using exponential decay functions with diminishing returns. Coverage formula: Cov = Σ Iₖ × (1 − e^(−λ·k)) where k = overlapping catchment count.

**Data:** OpenStreetMap amenities, multiple cities.

**Relevance:** Addresses the **service redundancy bias** in cumulative opportunity measures — having 20 restaurants nearby should not score 20× higher than having 2 [^158^][^164^]. Exponential decay ensures scores remain bounded [0, 1].

**Limitations:** Walking-only context; decay parameter λ requires calibration; does not incorporate actual mobility demand data.

**Implementation Influence:** Apply exponential decay to POI counts within dining districts to prevent inflation in service-dense areas. Use λ ≈ 0.3 for restaurants (diminishing returns after ~5 options).

### 4.3 Entropy Weight + TOPSIS for Urban Spatial Scoring

**Citation:** Various (see MCDA sources in Section 4.4)

**Method:** Entropy Weight Method (EWM) determines objective weights based on indicator value dispersion — higher entropy (more uniform distribution) = lower weight. TOPSIS ranks alternatives by Euclidean distance to positive-ideal and negative-ideal solutions.

**Relevance:** **Entropy-TOPSIS is the standard MCDA framework** for urban spatial evaluation in the recent literature [^129^][^130^][^133^]. Objective weights avoid subjective bias of AHP. TOPSIS handles multiple criteria with different units.

**Limitations:** Requires sufficient indicator variation for entropy calculation; TOPSIS assumes linear relationships and independent criteria.

**Implementation Influence:** Use entropy weights for the four scoring dimensions (POI density, taxi demand, bike-share demand, accessibility). Apply TOPSIS for final ranking. Normalize all indicators via min-max or z-score before TOPSIS.

### 4.4 Min-Max vs. Z-Score Normalization

**Key principle:** Normalization is essential when combining indicators with different scales (POI counts, taxi drop-offs, bike-share trips, accessibility scores). Min-max scales to [0, 1] but is **sensitive to outliers** [^159^][^167^]. Z-score standardization (subtract mean, divide by SD) handles outliers better but produces unbounded scores.

**Implementation Influence:** Use **z-score normalization** for indicators with extreme outliers (taxi drop-offs can have very high values at major transit hubs). Use **min-max normalization** for bounded indicators (accessibility scores). Apply winsorization (clip at 1st/99th percentiles) before normalization to handle extreme outliers.

---

## 5. Accessibility Measurement: Cumulative Opportunities, Gravity Models, 2SFCA, and R5/r5py

### 5.1 Hansen (1959) — Gravity Model Accessibility

**Citation:** Hansen, W. G. (1959). How accessibility shapes land use. *Journal of the American Institute of Planners*, 25(2), 73–76.

**Method:** Potential accessibility model: Aᵢ = Σ Oⱼ × f(Cᵢⱼ) where Oⱼ = opportunity size, Cᵢⱼ = travel cost, f() = impedance function (typically negative exponential).

**Relevance:** **Foundational paper for all modern accessibility measurement** [^137^][^147^]. Defined accessibility as "the potential of opportunities for interaction." All subsequent methods (cumulative opportunities, 2SFCA) are extensions or special cases of Hansen's framework.

**Limitations:** Does not account for competition among demand points; requires calibration of impedance parameter β.

**Implementation Influence:** Hansen's framework is the theoretical foundation. Use 2SFCA or gravity-based measures for actual computation.

### 5.2 Luo & Wang (2003) — 2SFCA Method

**Citation:** Luo, W., & Wang, F. (2003). Measures of spatial accessibility to health care in a GIS environment: synthesis and a case study in the Chicago region. *Environment and Planning B: Planning and Design*, 30(6), 865–884. https://doi.org/10.1068/b29120

**Method:** Two-step floating catchment area: Step 1 — for each supply point j, compute supply-demand ratio Rⱼ = Sⱼ / Σ Dₖ within catchment. Step 2 — for each demand point i, sum Rⱼ for all supply points within catchment.

**Data:** Health care facilities and population in Chicago region.

**Relevance:** **Most widely used accessibility method in urban planning** [^171^][^173^]. Overcomes the limitation of Hansen's model by accounting for supply-demand competition. Applied to food stores, green space, job opportunities, emergency shelters, and healthcare.

**Limitations:** Original version uses binary catchment (in/out) — enhanced versions (E2SFCA, G2SFCA) add distance decay.

**Implementation Influence:** Use **Gaussian 2SFCA** for restaurant accessibility from residential/population centroids. Catchment size: 800m walking (10-minute walk) for dining. Supply = restaurant count/seating capacity; demand = population.

### 5.3 Chen (2019) — 2SFCA for Food Access (SNAP Retailers)

**Citation:** Chen, X. (2019). Enhancing the Two-Step Floating Catchment Area Model for Community Food Access Mapping: Case of the Supplemental Nutrition Assistance Program. *The Professional Geographer*. https://doi.org/10.1080/00330124.2019.1578978

**Method:** Gaussian-based 2SFCA for SNAP-authorized retailer accessibility. Compares with USDA Food Access Research Atlas.

**Data:** SNAP-authorized retailers and benefit-receiving households in Arkansas, United States.

**Relevance:** **Direct application of 2SFCA to food retail access in the US context** [^131^]. Validates that 2SFCA measurement corresponds better with USDA Atlas at smaller catchment sizes. Catchment size significantly impacts urban accessibility results.

**Limitations:** SNAP retailers (not restaurants); Arkansas (not NYC).

**Implementation Influence:** Apply Gaussian 2SFCA with restaurant POIs as supply points. Use census block groups as demand units. Catchment size: 400–800m walking.

### 5.4 Fink et al. (2022) — r5py: Rapid Realistic Routing in Python

**Citation:** Fink, C., Klumpenhouwer, W., Saraiva, M., Pereira, R., & Tenkanen, H. (2022). r5py: Rapid Realistic Routing with R5 in Python. Zenodo. https://doi.org/10.5281/zenodo.7060438

**Method:** Python wrapper for Conveyal's R5 routing engine. Computes travel time matrices on multimodal networks (walk, bike, public transit, car) using RAPTOR algorithm.

**Data:** Requires OpenStreetMap (`.osm.pbf`) and GTFS feeds as inputs.

**Relevance:** **Production-grade open-source tool for multimodal accessibility analysis** [^24^][^28^][^36^]. R5 received the **2025 TRB Impactful Research Award** [^33^]. R5py integrates with GeoPandas. Can calculate millions of origin-destination pairs at zero cost (vs. $5/1000 routes for Google Maps API) [^23^].

**Limitations:** Schedule-based (not real-time); GTFS data required for transit; memory-intensive for large regions; walking speed is constant (does not account for slope or barriers).

**Implementation Influence:** **Primary accessibility tool recommendation.** Use r5py to compute walking and transit travel times from census block centroids to restaurant clusters. Combine with OSM and NYC MTA GTFS feeds.

---

## 6. Combining Taxi and Bike-Share Demand Signals

### 6.1 Key Challenge: Multimodal Data Fusion

Combining taxi and bike-share data requires addressing **mode differences, demographic bias, seasonality, and temporal mismatch** [^118^][^149^]. Taxis serve longer trips, higher-income demographics, and 24/7 demand; bike-share serves shorter trips, different user demographics, and weather-dependent demand. The OECD framework for integrating urban transport emphasizes that multimodal integration requires consistent spatial units, temporal alignment, and normalization for comparative analysis [^152^].

### 6.2 Data Fusion Approach for Demand Estimation

**Citation:** Data fusion approach for ride-sourcing demand estimation (2022). *arXiv:2212.02178*.

**Method:** Discrete choice models (DCMs) for fusing multiple disaggregate data sources (household travel surveys + trip records). Controls for endogeneity biases.

**Data:** Ride-sourcing trip records + household travel survey.

**Relevance:** Demonstrates methodology for **incorporating emerging mobility options (ride-sharing, bike-sharing) into disaggregate demand forecasting models** [^118^]. Highlights importance of controlling for endogeneity when combining data sources.

**Limitations:** Focus on ride-sourcing (not taxi specifically); requires detailed survey data.

**Implementation Influence:** Normalize taxi and bike-share demand to the same spatial units (grid cells or clusters). Apply **z-score normalization within each mode** to account for different scales. Weight by temporal overlap (both data sources should cover the same time period). Use entropy weights to let the data determine relative importance.

### 6.3 Integration Principles from MaaS Literature

**Citation:** Mobility-as-a-Service literature review (2018). OECD report on Integrating Urban Public Transport Systems and Cycling.

**Method:** Framework for integrating multi-modal transportation data and services.

**Relevance:** Provides principles for **integrated service information and physical integration** [^149^][^152^]. Emphasizes that multimodal analysis requires common spatial referencing, consistent temporal periods, and normalization for mode-specific biases.

**Implementation Influence:** Use consistent spatial units (e.g., 100m grid or census blocks) for both data sources. Align temporal coverage (same months/seasons). Normalize demand by mode-specific daily totals to account for different scales. Apply weather controls for bike-share (exclude rainy/snowy days if comparing to taxi).

---

## 7. Method Comparison Table

| Design Decision | Recommended Method | Primary Source(s) | Alternative(s) | Key Parameter(s) |
|---|---|---|---|---|
| **Taxi drop-off clustering** | HDBSCAN (time-threshold) | McInnes 2017 [^84^]; Du 2024 [^2^] | DBSCAN [^107^], ST-DBSCAN [^112^] | `min_cluster_size` (10–50), `metric` (haversine) |
| **Spatiotemporal clustering** | ST-HDBSCAN two-phase | Li 2021 [^1^] | ST-DBSCAN [^112^], MDST-DBSCAN [^111^] | ε_space (200m), ε_time (20 min), MinPts (10) |
| **Network-constrained refinement** | Network distance filter + region growing | Li 2021 [^1^]; Zhao 2019 [^6^] | Graph partitioning (InfoMap) [^6^] | Network threshold εₙ (200m) |
| **Density estimation** | Network KDE (Gaussian) | Xie 2008; Tang 2016 [^16^] | Planar KDE [^14^], STKDE [^13^] | Bandwidth: 200m road network |
| **Hotspot significance testing** | Getis-Ord Gi* | Ord & Getis 1995 [^142^] | Local Moran's I (LISA) [^144^] | Distance band (adaptive), confidence level (95%) |
| **Cluster validation** | DBCV index + POI density overlap | Li 2021 [^1^]; Moulavi 2014 | Silhouette score, Calinski-Harabasz | Internal validation indices |
| **Scoring normalization** | Z-score + winsorization (1%/99%) | Standard practice [^167^] | Min-max [^159^], percentile rank [^168^] | Winsorization thresholds |
| **Indicator weighting** | Entropy Weight Method | MCDA literature [^129^][^130^] | AHP, CRITIC, equal weights | Entropy-based objective weights |
| **Final ranking** | TOPSIS | MCDA literature [^129^][^130^] | VIKOR, PROMETHEE | Euclidean distance to ideal |
| **Distance decay function** | Gaussian | Chen & Jia 2019 [^45^] | Exponential, inverse-power [^45^] | Catchment size (400–800m) |
| **Accessibility measure** | Gaussian 2SFCA | Luo & Wang 2003 [^173^]; Chen 2019 [^131^] | Gravity model, cumulative opportunities | Supply: restaurant count; Demand: population |
| **Multimodal routing** | r5py (Conveyal R5) | Fink 2022 [^24^] | OpenTripPlanner, OSRM [^23^] | OSM + GTFS inputs |
| **Demand data fusion** | Z-score normalization + entropy weights | Data fusion literature [^118^][^152^] | Equal weighting, regression-based | Mode-specific normalization |
| **Activity inference** | Probabilistic (Bayesian) | Gong 2019 [^165^] | Deterministic nearest-POI | POI category + temporal features |
| **Scoring composite** | Weighted sum with exponential decay | Roper 2023 [^158^] | Simple additive weighting | Diminishing returns parameter λ |

---

## 8. Recommended Algorithm Pipeline

Based on the literature review, the following pipeline is recommended for the NYC urban dining district identification project:

### Stage 1: Data Preparation
1. **Taxi data:** Extract drop-off events from NYC TLC data. Filter to dining-relevant hours (11:00–14:00, 17:00–23:00). Apply probabilistic activity inference using POI categories and temporal features [^165^].
2. **Bike-share data:** Extract trip end points from Citi Bike data. Filter to same temporal window. Apply weather controls.
3. **POI data:** Extract restaurant POIs from OpenStreetMap or commercial datasets. Compute POI density per grid cell.
4. **Road network:** Download NYC OpenStreetMap data. Build network graph for constrained analysis.

### Stage 2: Clustering
1. **Initial clustering:** Apply HDBSCAN with haversine metric to taxi drop-off points. Set `min_cluster_size = 20`, `min_samples = 5` [^84^].
2. **Temporal refinement:** Apply time-threshold filtering (ε_time = 30 minutes) to ensure clusters represent temporally coherent dining activity [^1^][^112^].
3. **Network filtering:** Filter clusters using network distance (εₙ = 200m) and region growing to ensure road-network coherence [^1^].
4. **Validation:** Compare clusters to high-density POI areas. Compute DBCV index.

### Stage 3: Scoring
1. **Indicator calculation:** For each cluster, compute: (a) POI density, (b) taxi drop-off count, (c) bike-share end count, (d) 2SFCA accessibility score.
2. **Normalization:** Apply z-score normalization with 1%/99% winsorization to each indicator [^167^].
3. **Weighting:** Compute entropy weights for the four indicators [^129^].
4. **Ranking:** Apply TOPSIS to generate composite dining district scores [^130^].
5. **Decay adjustment:** Apply exponential decay to POI counts to prevent service-density inflation [^158^].

### Stage 4: Accessibility Integration
1. **Travel time computation:** Use r5py with OSM + MTA GTFS to compute walking/transit times from census block centroids to cluster centers [^24^].
2. **2SFCA calculation:** Apply Gaussian 2SFCA with 800m catchment [^131^][^173^].
3. **Final integration:** Incorporate accessibility scores into TOPSIS ranking.

---

## 9. Implementation Risks and Limitations

| Risk | Severity | Mitigation Strategy |
|---|---|---|
| **Taxi data demographic bias** | High | Taxis serve higher-income, longer-trip demographics. Normalize by origin-destination patterns, not raw counts. Acknowledge bias in documentation [^118^]. |
| **Bike-share weather seasonality** | Medium | Bike-share demand drops significantly in winter. Filter to comparable seasons or apply weather-adjusted normalization. Consider seasonal scoring variants [^152^]. |
| **Parameter sensitivity (HDBSCAN)** | Medium | Use DBCV index for objective parameter selection [^1^]. Conduct sensitivity analysis on `min_cluster_size` (10, 20, 50). Report robustness. |
| **Catchment size sensitivity (2SFCA)** | High | Chen & Jia (2019) found catchment size is the most critical variable [^45^]. Test 400m, 800m, 1200m. Report range of results. |
| **MAUP (grid cell size)** | Medium | Use multiple grid resolutions (100m, 200m, 500m). Verify stability of results across scales. |
| **R5py memory constraints** | Medium | For NYC-scale analysis, chunk the origin-destination matrix computation. Use `mamba` installation for dependency management [^28^]. |
| **Multimodal data scale mismatch** | Medium | Taxi volume >> bike-share volume. Z-score normalize within each mode before fusion [^118^]. Use entropy weights to balance. |
| **POI data completeness** | Medium | OpenStreetMap POI coverage varies by neighborhood. Cross-validate with commercial datasets (Yelp, Google Places). |
| **Temporal mismatch** | Low | Ensure taxi and bike-share data cover the same time period. If not, apply temporal adjustment factors. |

---

## 10. Search Log Summary

A total of **12 search rounds** were conducted across the six justification domains:

| Round | Query Focus | Results | Key Finds |
|---|---|---|---|
| 1 | Taxi GPS revealed-preference signals | 11 | Li 2021 (ST-HDBSCAN), Du 2024 (HDBSCAN+KDE) |
| 2 | ST-DBSCAN spatiotemporal clustering | 12 | Birant & Kut 2007 original, ST-HDBSCAN comparisons |
| 3 | KDE, network KDE for urban hotspots | 9 | Hu 2020 (surface networks), NKDE methods |
| 4 | Getis-Ord Gi* spatial statistics | 1+ | Gi* calculator, urban analysis guides |
| 5 | 2SFCA accessibility methods | 26 | Chen & Jia 2019 (6 decay functions), Luo & Wang 2003 |
| 6 | R5/r5py multimodal routing | 21 | Fink 2022 (r5py), Conveyal R5 award, tutorials |
| 7 | HDBSCAN foundational papers | 24 | Campello 2013, McInnes 2017 JOSS, implementations |
| 8 | DBSCAN original paper | 24 | Ester 1996, KDD Test of Time Award 2014 |
| 9 | MCDA entropy-TOPSIS | 17 | Urban spatial evaluation frameworks |
| 10 | Distance decay functions | 7 | Gaussian vs. exponential comparison |
| 11 | Multimodal data fusion | 2 | Ride-sourcing DCM fusion, MaaS integration |
| 12 | Activity inference from taxi data | 5 | Gong 2019 (Bayesian), Chen 2021 (LMD) |

---

## 11. Citation Key

The following BibTeX entries cover the primary sources referenced in this review. Entries are organized by citation order of appearance.
