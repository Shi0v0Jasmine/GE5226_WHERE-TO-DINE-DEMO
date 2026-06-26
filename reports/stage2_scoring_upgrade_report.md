# Stage 2 Scoring Upgrade Report

## 1. P0 Bug Fix: Empty final_hotspots

**Problem**: `final_hotspots.geojson` was empty (0 records) because the `min_overlap_ratio` threshold in `config.yaml` was too strict (0.15) for zone-centroid data. Since restaurant clusters and taxi hotspots are derived from zone centroids, their geometric overlap is naturally very small.

**Fix**: Lowered `min_overlap_ratio` from 0.15 to 0.05 in `config/config.yaml`.

**Result**: Pipeline now produces **2 valid hotspots** instead of 0:
- Hotspot #1: Score 100.0 | 52 restaurants | 121 taxi dropoffs | 0.420 km^2
- Hotspot #2: Score 16.5 | 39 restaurants | 81 taxi dropoffs | 1.818 km^2

---

## 2. P1 Upgrade: Entropy-Weighted TOPSIS Scoring

**Problem**: V2 scoring used fixed 0.5/0.5 weights for restaurant and taxi density, which is arbitrary and does not adapt to the data's information content.

**Solution**: Replaced fixed weighting with **Entropy Weight Method + TOPSIS** (Technique for Order Preference by Similarity to Ideal Solution):

1. **Entropy Weights**: Objective weights computed from the information entropy of each indicator. Higher variance = higher weight.
2. **TOPSIS**: Multi-criteria decision method that ranks alternatives by their geometric distance to the positive-ideal and negative-ideal solutions.

**Implementation**: Updated `calculate_composite_scores_v2()` in `src/data_processing/08_spatial_intersection.py`:
- Builds indicator matrix `[restaurant_score_v2, taxi_score_v2]`
- `compute_entropy_weights()` → objective weights
- `compute_topsis_ranking()` → scores in [0, 1]
- Rescaled to [0, 100] for consistency
- Added `entropy_weight_restaurant` and `entropy_weight_taxi` columns for transparency

---

## 3. V1 vs V2 vs V3 Comparison Results

Applied all three scoring methods to 233 taxi hotspots:

| Metric | V1 (max-norm) | V2 (z-score + winsorize) | V3 (entropy-TOPSIS) |
|--------|--------------|--------------------------|---------------------|
| Mean | 8.975 | 11.692 | 9.101 |
| Std | 18.011 | 22.858 | 18.190 |
| Median | 0.702 | 0.931 | 0.709 |
| Skew | 2.539 | 2.286 | 2.493 |
| Kurtosis | 6.330 | 4.307 | 5.967 |
| **Ties** | **10** | **14** | **1** |

### Ranking Stability

| Pair | Spearman ρ | Kendall τ | Avg Rank Shift |
|------|-----------|-----------|----------------|
| V1 vs V2 | 1.000 | 1.000 | 2.1 |
| V1 vs V3 | 0.981 | 0.964 | 5.0 |
| V2 vs V3 | 0.981 | 0.963 | 3.5 |

### Key Findings

1. **Tie-breaking**: V3 (entropy-TOPSIS) reduced ties from 14 (V2) to **1**, a 93% improvement. TOPSIS's continuous geometric distance metric naturally breaks ties that occur with linear weighted sums.

2. **Ranking Stability**: V3 maintains high correlation with both V1 (ρ=0.981) and V2 (ρ=0.981), confirming that the upgrade preserves the overall ranking structure while improving discrimination.

3. **Entropy Weights**: For the taxi hotspot dataset, entropy weights were `density=0.503, weight=0.497` — nearly balanced, indicating both indicators carry similar information content.

4. **Distribution**: V3's distribution is closer to V1 than V2, with kurtosis 5.967 (vs V1's 6.330 and V2's 4.307), suggesting it retains more of the original shape while reducing outlier sensitivity.

---

## 4. Files Modified

- `config/config.yaml` — lowered `min_overlap_ratio` from 0.15 → 0.05
- `src/data_processing/08_spatial_intersection.py` — upgraded V2 scoring to entropy-TOPSIS
- `src/data_processing/compare_scoring_v1_vs_v2.py` — expanded to V1 vs V2 vs V3 comparison

## 5. Next Steps

- Stage 3: OSMnx travel-time matrix integration into Flask API
- Stage 4: H3 grid multi-source fusion
- Stage 5: Streamlit dashboard + ground-truth validation
