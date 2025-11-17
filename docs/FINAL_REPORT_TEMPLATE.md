# Final Report Template
## "Where to DINE": NYC Restaurant Recommendation System

**Author**: [Your Name]
**Institution**: [Your University]
**Course**: [Course Name & Number]
**Date**: [Submission Date]

---

## ABSTRACT (200-300 words)

[Concise summary of the entire project]

**Structure**:
- Problem statement (1-2 sentences)
- Methodology overview (2-3 sentences)
- Key findings (2-3 sentences)
- Implications (1-2 sentences)

**Example**:
> Existing restaurant recommendation systems rely heavily on subjective user reviews and fail to incorporate spatial accessibility constraints. This study develops a novel geospatial recommendation system for New York City dining areas by integrating revealed preference data from taxi drop-off patterns with multi-modal accessibility analysis. We apply HDBSCAN clustering to 50 million taxi trip records and 18,000+ restaurant locations to identify statistically significant dining hotspots. A multi-modal transportation network incorporating OSM road data and MTA GTFS transit schedules enables isochrone-based accessibility scoring. The final recommendation engine ranks hotspots using a weighted combination of popularity (taxi traffic) and accessibility (travel time). Cross-validation demonstrates 79% F1-score accuracy, and ground-truth comparison shows 87% overlap with known dining districts. This approach provides more objective, spatially-aware recommendations compared to review-based systems, with applications in urban planning and tourism.

**Keywords**: Geospatial analysis, HDBSCAN clustering, multi-modal routing, accessibility analysis, restaurant recommendation, NYC

---

## 1. INTRODUCTION

### 1.1 Background and Motivation

[2-3 paragraphs]

**Topics to cover**:
- Why restaurant recommendations matter (tourism, urban planning, daily life)
- Limitations of current systems (Yelp, Google Maps, etc.)
- The "subjective reviews" problem
- The "spatial context" gap
- Your novel contribution: "voting with feet"

**Example opening**:
> In an increasingly mobile urban society, finding suitable dining options is a daily challenge for residents and tourists alike. Traditional recommendation systems such as Yelp, Google Maps, and Dianping (大众点评) rely primarily on user-generated ratings and reviews...

### 1.2 Problem Statement

[1 paragraph]

**Clearly state**:
- What problem you're solving
- Why existing solutions are inadequate
- What gap your research fills

### 1.3 Research Questions

[Numbered list]

**Example**:
1. Can taxi drop-off patterns accurately identify popular dining areas?
2. How do density-based clustering methods (HDBSCAN) perform compared to traditional hotspot analysis?
3. Does incorporating multi-modal accessibility improve recommendation relevance?
4. What is the relationship between restaurant density and taxi traffic during dining hours?

### 1.4 Contributions

[Bulleted list]

**Example**:
- Novel integration of mobility data with restaurant location data
- Rigorous statistical validation of clustering results
- First multi-modal accessibility analysis for restaurant recommendations in NYC
- Reproducible open-source pipeline for similar urban analysis

### 1.5 Report Structure

[Brief outline of remaining sections]

---

## 2. LITERATURE REVIEW

### 2.1 Spatial Clustering Methods

[2-3 pages]

**Key topics**:
- DBSCAN (Ester et al., 1996)
- HDBSCAN (Campello et al., 2013)
- Applications in urban analysis
- Parameter selection strategies
- Validation metrics

**Essential citations** (30-50 papers total):
- Campello, R. J., Moulavi, D., & Sander, J. (2013). Density-based clustering based on hierarchical density estimates. *Pacific-Asia Conference on Knowledge Discovery and Data Mining*.
- Ester, M., Kriegel, H. P., Sander, J., & Xu, X. (1996). A density-based algorithm for discovering clusters in large spatial databases with noise. *KDD*, 96(34), 226-231.
- Anselin, L. (1995). Local indicators of spatial association—LISA. *Geographical Analysis*, 27(2), 93-115.

### 2.2 Point-of-Interest Recommendation Systems

[1-2 pages]

**Key topics**:
- Location-based recommendation approaches
- Review-based vs. behavior-based systems
- Collaborative filtering for POIs
- Spatial context in recommendations

### 2.3 Urban Mobility Analysis

[1-2 pages]

**Key topics**:
- Taxi data in urban studies
- Revealed preference vs. stated preference
- Temporal patterns in urban movement
- Big data approaches to mobility

### 2.4 Accessibility Analysis

[1-2 pages]

**Key topics**:
- Isochrone analysis
- Multi-modal routing
- GTFS data utilization
- Network-based accessibility metrics
- Gravity models and distance decay

**Essential citations**:
- Delling, D., Pajor, T., & Werneck, R. F. (2015). Round-based public transit routing. *Transportation Science*, 49(3), 591-604.
- Hess, D. B., et al. (2007). Walking to the bus: perceived versus actual walking distance to bus stops. *Journal of Public Transportation*, 10(2).

### 2.5 Gaps in Existing Literature

[1 paragraph]

**Explicitly state**:
- What hasn't been done before
- Why your approach is novel
- How your work builds on prior research

---

## 3. DATA

### 3.1 Data Sources

[Table format]

| Dataset | Source | Records | Timespan | Attributes |
|---------|--------|---------|----------|------------|
| NYC TLC Taxi | NYC Open Data | ~50M | Jan-Dec 2024 | pickup/dropoff coords, datetime, fare |
| Restaurants (Google) | Google Maps API | 14,330 | 2024 | name, rating, price, cuisine, coords |
| Restaurants (OSM) | OpenStreetMap | 7,723 | 2024 | name, cuisine, coords |
| GTFS Transit | MTA | ~8,000 stops | 2024 | routes, schedules, stop coords |
| OSM Networks | OpenStreetMap | ~500k edges | 2024 | roads, sidewalks, geometries |

### 3.2 Data Acquisition

[1-2 pages]

**For each dataset**:
- Download procedure
- API usage (if applicable)
- Date of acquisition
- Version/snapshot information

### 3.3 Data Characteristics

#### 3.3.1 Taxi Trip Data

[Statistics table]

**Before filtering**:
- Total trips: ~50 million
- Spatial extent: NYC + suburbs
- Temporal coverage: Full year 2024
- Average trip distance: X miles
- Average fare: $Y

**After filtering** (dining hours + NYC bounds):
- Filtered trips: ~20 million (40% retained)
- Temporal windows: 7-10 AM, 11-2 PM, 5-10 PM, 10 PM-1 AM
- Spatial extent: [40.4774, 40.9176] lat, [-74.2591, -73.7004] lon

#### 3.3.2 Restaurant Data

[Statistics]

**Google Maps API**:
- Total: 14,330 restaurants
- With ratings: 13,509 (94.3%)
- Average rating: 4.15/5.0
- Price level distribution: [chart]

**OpenStreetMap**:
- Total: 7,723 restaurants
- With names: 7,591 (98.3%)
- Top cuisines: Chinese (710), Pizza (657), Italian (636)

**Merged dataset** (after deduplication):
- Total unique restaurants: ~18,500
- Duplicate pairs identified: ~3,500
- Spatial distribution: [map]

#### 3.3.3 Transit Data (GTFS)

[Statistics]

- Subway stops: ~472
- Bus stops: ~5,800
- Total routes: ~300
- Daily trips: ~10,000

### 3.4 Data Quality Assessment

[1-2 pages]

**Issues identified**:
- Missing coordinates: X%
- Null values in key fields: [table]
- Spatial outliers: Y restaurants outside NYC
- Temporal anomalies: Z trips with impossible durations

**Resolution strategies**:
- [List how each issue was addressed]

### 3.5 Ethical Considerations

[1 paragraph]

- Privacy: Taxi data is anonymized
- Data use policy compliance: NYC TLC terms
- Potential biases: Income, tourism effects
- Responsible use statement

---

## 4. METHODOLOGY

### 4.1 Overall Workflow

[Flowchart + narrative]

**Three-phase approach**:
1. Hotspot Identification
2. Accessibility Analysis
3. Recommendation Engine

### 4.2 Phase 1: Hotspot Identification

#### 4.2.1 Restaurant Clustering

**Algorithm**: HDBSCAN

**Procedure**:
1. Load restaurant point data (N = 18,500)
2. Project to EPSG:2263 (meters)
3. Extract coordinates: X = [(x₁, y₁), ..., (xₙ, yₙ)]
4. Apply HDBSCAN with parameters:
   - `min_cluster_size = 30`
   - `min_samples = 10`
   - `cluster_selection_epsilon = 200` (meters)
   - `metric = 'euclidean'`
5. Generate cluster labels: C = [c₁, c₂, ..., cₙ]
6. Create dining zone polygons via convex hull + 100m buffer

**Parameter Justification** (CRITICAL):
- `min_cluster_size = 30`: Based on minimum viable "dining district" size
- `epsilon = 200m`: Corresponds to ~2 city blocks in Manhattan
- Sensitivity analysis: [Show results for different parameter values]

**Validation**:
- Silhouette score: [value] (> 0.3 acceptable)
- Davies-Bouldin index: [value] (< 1.5 acceptable)
- Visual inspection: [map showing clusters]

#### 4.2.2 Temporal Weighting of Taxi Data

**Weighting Function**:

```
w(t, d) = {
    1.5,  if d ∈ {Fri, Sat, Sun} and 18 ≤ t < 22  (weekend dinner)
    1.0,  if d ∈ {Mon-Thu} and 18 ≤ t < 22        (weekday dinner)
    0.8,  if d ∈ {Mon-Fri} and 12 ≤ t < 14        (weekday lunch)
    1.0,  if d ∈ {Sat, Sun} and 12 ≤ t < 14       (weekend brunch)
    0.5,  if 7 ≤ t < 10                            (breakfast)
    0.7,  if d ∈ {Fri, Sat, Sun} and (t ≥ 22 or t < 1)  (late night weekend)
    0.4,  if d ∈ {Mon-Thu} and (t ≥ 22 or t < 1)  (late night weekday)
    0.3,  otherwise                                (off-peak)
}
```

Where:
- `t` = hour of day (24-hour format)
- `d` = day of week

**Justification**:
- Weekend dinner weighted highest due to dining culture
- Weekday lunch lower due to shorter time budgets
- Empirical validation: [compare with Yelp check-in patterns]

#### 4.2.3 Taxi Drop-off Clustering

**Procedure**:
1. Load filtered taxi data (N ≈ 20 million)
2. Apply temporal weights: w(tᵢ, dᵢ)
3. Aggregate to H3 hexagons (resolution 10, ~15m) to reduce data size
4. For each hexagon h: weight_h = Σ w(tᵢ, dᵢ) for all trips in h
5. Project hexagon centroids to EPSG:2263
6. Apply HDBSCAN with parameters:
   - `min_cluster_size = 50`
   - `min_samples = 15`
   - `cluster_selection_epsilon = 250` (meters)
7. Create hotspot arrival area polygons

**Data Reduction**:
- Original: 20M points
- After H3 aggregation: ~500k hexagons (96% reduction)
- Computational time: [report actual time]

#### 4.2.4 Spatial Intersection

**Procedure**:
1. Overlay dining zones (Dz) and hotspot arrival areas (Ha)
2. Compute intersection: H = Dz ∩ Ha
3. Filter by minimum area: keep only if area(H) > 10,000 m²
4. Calculate composite score:
   - restaurant_score = n_restaurants / max(n_restaurants)
   - taxi_score = Σ weights / max(Σ weights)
   - hotspot_score = 0.5 × restaurant_score + 0.5 × taxi_score

**Result**: N_hotspots = [number] final dining hotspots

### 4.3 Phase 2: Accessibility Analysis

#### 4.3.1 Network Construction

**OSM Road Network**:
- Downloaded via OSMnx (Boeing, 2017)
- Network type: 'drive' and 'walk'
- Bounding box: NYC extent
- Edges: ~500k (drive), ~650k (walk)

**Travel Time Calculation**:
```
travel_time (min) = (edge_length_meters / 1000) / speed_kmh × 60
```

Where:
- `speed_kmh (drive) = 25` (urban average)
- `speed_kmh (walk) = 4.8` (standard walking speed)

**GTFS Integration** (if implemented):
- Library: peartree / r5py
- Representative time window: 7-10 AM weekday
- Transfer penalty: 5 minutes
- Maximum wait time: 15 minutes

#### 4.3.2 Isochrone Generation

**Algorithm**: Dijkstra's shortest path with cutoff

**Procedure**:
1. Given origin point (lat, lon)
2. Find nearest network node
3. Compute shortest paths to all reachable nodes within time threshold
4. Extract reachable node coordinates
5. Generate convex hull or alpha shape
6. Return polygon

**Time Thresholds**:
- Walk: 5, 10, 15 minutes
- Drive: 10, 20, 30 minutes
- Transit: 15, 30, 45 minutes

**Validation**:
- Compare with Google Maps / Mapbox isochrones
- Sample test: Times Square to [point] via walk
  - Our result: X minutes
  - Google Maps: Y minutes
  - Difference: Z% (acceptable if < 15%)

### 4.4 Phase 3: Recommendation Engine

#### 4.4.1 Scoring Algorithm

**Input**:
- User location: (lat_user, lon_user)
- Travel mode: {walk, drive, transit}
- Max time: T_max (minutes)

**Procedure**:
1. Generate isochrone I for (lat_user, lon_user, mode, T_max)
2. Spatial query: H_accessible = {h ∈ Hotspots | h.intersects(I)}
3. For each h ∈ H_accessible:
   - Calculate travel time: t_h = shortest_path(user, h.centroid)
   - accessibility_score_h = 100 × (1 - t_h / T_max)
   - final_score_h = α × popularity_score_h + β × accessibility_score_h
4. Sort by final_score descending
5. Return top K hotspots

**Parameter Selection**:
- α (popularity weight) = 0.6
- β (accessibility weight) = 0.4
- Justification: Prioritize quality (popularity) slightly over convenience

**Sensitivity Analysis**:
- Vary α, β ∈ {0.3, 0.4, 0.5, 0.6, 0.7}
- User study: Which values produce most satisfying recommendations?

---

## 5. RESULTS

### 5.1 Clustering Results

#### 5.1.1 Restaurant Clusters

- Number of clusters: [N]
- Silhouette score: [value]
- Davies-Bouldin index: [value]
- Noise points: [X%]

**Distribution by Borough** [table]:

| Borough | # Clusters | Avg Restaurants/Cluster |
|---------|------------|-------------------------|
| Manhattan | X | Y |
| Brooklyn | X | Y |
| Queens | X | Y |
| Bronx | X | Y |
| Staten Island | X | Y |

**Visualization**: [Insert map showing all restaurant clusters]

#### 5.1.2 Taxi Hotspot Clusters

- Number of clusters: [N]
- Total weighted drops in clusters: [M]
- Silhouette score: [value]

**Top 10 Hotspots by Taxi Traffic** [table]:

| Rank | Location | Weighted Drops | Cluster Size |
|------|----------|----------------|--------------|
| 1 | Times Square | X | Y |
| 2 | Financial District | X | Y |
| ... | ... | ... | ... |

**Visualization**: [Insert heatmap of taxi drop-offs + cluster boundaries]

#### 5.1.3 Final Dining Hotspots

- Total hotspots identified: [N]
- Coverage: [X%] of NYC area
- Average hotspot area: [Y] km²

**Top 20 Final Hotspots** [table]:

| Rank | Name | Restaurants | Taxi Score | Hotspot Score | Borough |
|------|------|-------------|------------|---------------|---------|
| 1 | Times Square | 127 | 95.3 | 92.1 | Manhattan |
| 2 | Financial Dist. | 89 | 87.2 | 85.6 | Manhattan |
| ... | ... | ... | ... | ... | ... |

**Visualization**: [Insert final hotspots map with scores as color gradient]

### 5.2 Validation Results

#### 5.2.1 Cross-Validation

**Setup**:
- Train/test split: 80/20
- Metric: F1 score, precision, recall

**Results**:
- Precision: [value]
- Recall: [value]
- F1 score: [value]

**Interpretation**: [Discuss what this means]

#### 5.2.2 Ground Truth Comparison

**Known Dining Districts** [table]:

| District | Identified? | Overlap % | Score Rank |
|----------|-------------|-----------|------------|
| Koreatown | ✓ | 92% | 4 |
| Little Italy | ✓ | 87% | 8 |
| Chinatown | ✓ | 95% | 3 |
| Williamsburg | ✓ | 78% | 6 |
| Financial Dist. | ✓ | 88% | 2 |

**Overall**: [X out of Y] known districts correctly identified ([Z%])

#### 5.2.3 Statistical Significance Tests

**Hypothesis 1**: Taxi drop-offs correlate with restaurant ratings
- Spearman's ρ: [value]
- p-value: [value]
- Interpretation: [Significant? / Not significant?]

**Hypothesis 2**: Clusters are non-random
- Monte Carlo simulation (1000 iterations)
- Observed clustering index: [value]
- Random expectation: [mean ± SD]
- p-value: [value]

### 5.3 Recommendation Engine Performance

**Test Scenarios** [table]:

| Origin | Mode | Time Limit | # Recommendations | Top Recommendation | Travel Time |
|--------|------|------------|-------------------|---------------------|-------------|
| Times Square | Walk | 15 min | 3 | Koreatown | 12 min |
| Brooklyn Bridge | Drive | 20 min | 7 | Chinatown | 8 min |
| Central Park | Transit | 30 min | 12 | UWS Dining | 22 min |

**Visualization**: [Interactive map demo screenshots]

---

## 6. DISCUSSION

### 6.1 Interpretation of Results

#### 6.1.1 Hotspot Patterns

[2-3 paragraphs]

**Key findings**:
- Manhattan dominates (expected due to density)
- Outer borough hotspots concentrated near transit
- Waterfront areas underrepresented (limited taxi access)

**Comparison to literature**:
- Aligns with [Author, Year] findings on urban dining geography
- Novel contribution: Quantitative ranking vs. qualitative descriptions

#### 6.1.2 Temporal Patterns

[If analyzed]
- Weekend vs. weekday differences
- Seasonal variations (if data permits)

#### 6.1.3 Accessibility Impact

- How does multi-modal routing change recommendations vs. distance-only?
- Example: Location X ranks #10 by popularity but #3 by accessibility

### 6.2 Comparison with Existing Systems

**Yelp vs. Our System** [table]:

| Criterion | Yelp | Where to DINE |
|-----------|------|---------------|
| Data Source | User reviews | Taxi drop-offs |
| Bias | Subjective ratings | Income/tourism bias |
| Spatial Context | Distance only | Multi-modal isochrones |
| Hotspot Discovery | None | HDBSCAN clusters |
| Temporal Weighting | None | Time-of-day/day-of-week |

**Advantages of our approach**:
- Less susceptible to review manipulation
- Explicit spatial accessibility
- Reveals actual behavior vs. stated preferences

**Limitations**:
- Taxi users ≠ general population
- New restaurants undervalued
- Requires more complex data processing

### 6.3 Methodological Considerations

#### 6.3.1 HDBSCAN Performance

- Advantages over K-means: Handles varying densities, identifies noise
- Advantages over DBSCAN: No manual epsilon selection
- Limitations: Sensitive to parameter choices, computationally intensive

#### 6.3.2 Temporal Weighting Assumptions

- Current weights are heuristic, not empirically derived
- Future work: Optimize weights via machine learning

#### 6.3.3 Network Simplifications

- Assumed constant speeds (ignores traffic)
- Schedule-based transit not fully implemented
- Walking network may not reflect true accessibility (hills, safety)

### 6.4 Limitations

[CRITICAL SECTION - Be honest]

1. **Data Representativeness**:
   - Taxi users skew higher income
   - Tourists overrepresented in Manhattan
   - Pandemic effects may bias 2024 data

2. **Temporal Scope**:
   - Single year analysis
   - No seasonal validation
   - Trends may not generalize

3. **Technical Limitations**:
   - Transit routing simplified (no true schedule-based routing)
   - Road network doesn't account for traffic
   - Cold start problem for new restaurants

4. **Validation Constraints**:
   - Ground truth limited to well-known districts
   - No user study for recommendation quality
   - Cross-validation on same dataset (not independent)

5. **Generalizability**:
   - NYC-specific (different cities have different patterns)
   - Taxi-centric (not applicable to cities with different transit modes)

### 6.5 Implications

#### 6.5.1 Practical Applications

- **Tourism**: Provide visitors with data-driven dining recommendations
- **Urban Planning**: Identify underserved areas for restaurant development
- **Business Intelligence**: Optimal restaurant location siting
- **Transportation**: Understand dining-related mobility patterns

#### 6.5.2 Theoretical Contributions

- Demonstrates utility of revealed preference data
- Validates HDBSCAN for urban hotspot analysis
- Framework for multi-modal accessibility-aware recommendations

---

## 7. CONCLUSIONS

### 7.1 Summary of Findings

[1-2 paragraphs summarizing entire project]

**Key takeaways**:
1. Taxi drop-offs are valid proxy for dining popularity
2. HDBSCAN effectively identifies dining hotspots
3. Multi-modal accessibility significantly impacts recommendations
4. 87% validation accuracy demonstrates robustness

### 7.2 Contributions

**Methodological**:
- Novel integration of clustering + accessibility
- Rigorous validation framework

**Practical**:
- Working recommendation system
- Reproducible open-source pipeline

### 7.3 Future Work

1. **Enhanced Transit Routing**:
   - Implement true schedule-based routing (r5py)
   - Real-time GTFS-RT integration

2. **Machine Learning Enhancements**:
   - Learn optimal temporal weights from data
   - Personalized recommendations (cuisine preferences)

3. **Expanded Validation**:
   - User study with survey participants
   - Comparison with actual trip outcomes

4. **Generalization**:
   - Apply to other cities (SF, Chicago, Boston)
   - Adapt for other POI types (bars, cafes, cultural venues)

5. **Dynamic Analysis**:
   - Track hotspot evolution over time
   - Predict emerging dining areas

---

## 8. REFERENCES

[Use citation management software - Zotero, Mendeley]

**Format**: APA, IEEE, or Chicago (check your course requirements)

**Example entries**:

Campello, R. J., Moulavi, D., & Sander, J. (2013). Density-based clustering based on hierarchical density estimates. In *Pacific-Asia Conference on Knowledge Discovery and Data Mining* (pp. 160-172). Springer.

Ester, M., Kriegel, H. P., Sander, J., & Xu, X. (1996). A density-based algorithm for discovering clusters in large spatial databases with noise. In *KDD* (Vol. 96, No. 34, pp. 226-231).

Boeing, G. (2017). OSMnx: New methods for acquiring, constructing, analyzing, and visualizing complex street networks. *Computers, Environment and Urban Systems*, 65, 126-139.

[... 30-50 total references ...]

---

## APPENDICES

### Appendix A: Code Listings

[Key code snippets - not entire codebase]

**Example**: HDBSCAN clustering function
```python
def cluster_restaurants(gdf, config):
    # [Include well-commented code]
    ...
```

### Appendix B: Additional Figures

[Maps, charts not in main text]

### Appendix C: Parameter Sensitivity Analysis

[Detailed tables showing results for different parameter values]

### Appendix D: Data Processing Logs

[Sample logs showing data pipeline execution]

---

**Total Page Target**: 30-50 pages (including figures and references)

**Last Updated**: 2025-11-09
