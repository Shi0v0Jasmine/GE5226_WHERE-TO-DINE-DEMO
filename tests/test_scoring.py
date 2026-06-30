"""
Unit tests for src/analysis/scoring.py

Run with:
    pytest tests/test_scoring.py -v
"""

import numpy as np
import pytest
import sys
from pathlib import Path

# Add project root to path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.analysis.scoring import (
    normalize_minmax,
    normalize_zscore,
    normalize_zscore_to_100,
    normalize_percentile,
    normalize_log1p,
    compute_access_score_decay,
    compute_access_score_euclidean,
    compute_composite_score,
    compute_tiebreaker_rank,
    compute_baseline_score,
    compute_entropy_weights,
    compute_topsis_ranking,
    get_profile_weights,
    PREFERENCE_PROFILES,
    normalize_robust_percentile,
    compute_bayesian_rating,
    compute_access_score_half_life,
    regularize_entropy_weights,
    compute_product_area_scores,
    compute_product_recommendation,
)


# ---------------------------------------------------------------------------
# Normalization tests
# ---------------------------------------------------------------------------

class TestNormalization:
    def test_minmax_basic(self):
        vals = np.array([0, 50, 100])
        result = normalize_minmax(vals)
        np.testing.assert_array_almost_equal(result, [0, 50, 100])

    def test_minmax_all_equal(self):
        vals = np.array([5, 5, 5])
        result = normalize_minmax(vals)
        assert result.min() == result.max()  # should be equal

    def test_zscore_zero_std(self):
        vals = np.array([7, 7, 7])
        result = normalize_zscore(vals)
        np.testing.assert_array_almost_equal(result, [0, 0, 0])

    def test_zscore_to_100_range(self):
        vals = np.array([1, 2, 3, 4, 100])
        result = normalize_zscore_to_100(vals, winsorize=True)
        assert result.min() >= 0
        assert result.max() <= 100

    def test_percentile_monotonic(self):
        vals = np.array([10, 20, 30])
        result = normalize_percentile(vals)
        assert np.all(np.diff(result) >= 0)  # non-decreasing

    def test_log1p_skewed(self):
        vals = np.array([0, 1, 10, 100, 1000])
        result = normalize_log1p(vals)
        assert result.min() >= 0
        assert result.max() <= 100

    def test_robust_percentile_handles_nan_and_outliers(self):
        result = normalize_robust_percentile([1, 2, np.nan, 3, 1_000_000])
        assert np.isfinite(result).all()
        assert result.min() >= 0
        assert result.max() <= 100

    def test_bayesian_rating_shrinks_low_review_items(self):
        result = compute_bayesian_rating(
            ratings=[5.0, 5.0],
            review_counts=[1, 1_000],
            global_mean=3.5,
            prior_reviews=20,
        )
        assert result[0] < result[1]


# ---------------------------------------------------------------------------
# Accessibility tests
# ---------------------------------------------------------------------------

class TestAccessibility:
    def test_half_life_decay(self):
        result = compute_access_score_half_life(
            [0, 10, 31],
            max_time_min=30,
            half_life_min=10,
        )
        np.testing.assert_allclose(result, [100, 50, 0])
    def test_decay_zero_time(self):
        score = compute_access_score_decay(0, max_time_min=15, decay_type='exponential')
        assert score == 100.0

    def test_decay_beyond_threshold(self):
        score = compute_access_score_decay(60, max_time_min=30, decay_type='exponential')
        assert score == 0.0

    def test_decay_linear_midpoint(self):
        score = compute_access_score_decay(15, max_time_min=30, decay_type='linear')
        assert score == 50.0

    def test_decay_array_input(self):
        times = np.array([0, 15, 30, 45])
        scores = compute_access_score_decay(times, max_time_min=30, decay_type='linear')
        np.testing.assert_array_almost_equal(scores, [100, 50, 0, 0])

    def test_euclidean_legacy(self):
        score = compute_access_score_euclidean(1.0, max_distance_km=2.0)
        assert score == 50.0


# ---------------------------------------------------------------------------
# Composite scoring tests
# ---------------------------------------------------------------------------

class TestCompositeScore:
    def test_equal_weights(self):
        score = compute_composite_score(
            demand_score=80, poi_score=60, access_score=40
        )
        expected = 0.35 * 80 + 0.30 * 60 + 0.25 * 40  # = 28 + 18 + 10 = 56
        assert score == pytest.approx(expected, rel=1e-6)

    def test_with_confidence(self):
        score = compute_composite_score(
            demand_score=80, poi_score=60, access_score=40, confidence_score=90
        )
        expected = 0.35 * 80 + 0.30 * 60 + 0.25 * 40 + 0.10 * 90
        assert score == pytest.approx(expected, rel=1e-6)

    def test_custom_weights(self):
        score = compute_composite_score(
            demand_score=80, poi_score=60, access_score=40,
            weights={'demand': 0.5, 'poi': 0.3, 'access': 0.2, 'confidence': 0.0}
        )
        expected = 0.5 * 80 + 0.30 * 60 + 0.20 * 40
        assert score == pytest.approx(expected, rel=1e-6)

    def test_weights_must_sum_to_one(self):
        with pytest.raises(ValueError):
            compute_composite_score(
                demand_score=80, poi_score=60, access_score=40,
                weights={'demand': 0.5, 'poi': 0.3, 'access': 0.3, 'confidence': 0.0}
            )

    def test_array_input(self):
        demand = np.array([80, 60, 40])
        poi = np.array([60, 60, 60])
        access = np.array([40, 50, 60])
        scores = compute_composite_score(demand, poi, access)
        assert scores.shape == (3,)
        assert np.all((scores >= 0) & (scores <= 100))


# ---------------------------------------------------------------------------
# Tie-breaker tests
# ---------------------------------------------------------------------------

class TestTiebreaker:
    def test_tiebreaker_basic(self):
        import pandas as pd
        df = pd.DataFrame({
            'recommendation_score': [85, 85, 70],
            'popularity_score': [90, 80, 70],
            'accessibility_score': [80, 90, 70]
        })
        result = compute_tiebreaker_rank(df)
        # Row 0 should win tie because popularity_score is higher (90 > 80)
        assert result.loc[0, 'rank'] == 1
        assert result.loc[1, 'rank'] == 2
        assert result.loc[2, 'rank'] == 3

    def test_tiebreaker_with_rating_conf(self):
        import pandas as pd
        df = pd.DataFrame({
            'recommendation_score': [85, 85, 85],
            'popularity_score': [80, 80, 80],
            'accessibility_score': [70, 70, 70],
            'rating_confidence': [0.9, 0.8, 0.7]
        })
        result = compute_tiebreaker_rank(df, rating_conf_col='rating_confidence')
        assert result.loc[0, 'rank'] == 1
        assert result.loc[1, 'rank'] == 2
        assert result.loc[2, 'rank'] == 3


# ---------------------------------------------------------------------------
# Baseline / legacy tests
# ---------------------------------------------------------------------------

class TestBaselineScore:
    def test_perfect_hotspot(self):
        score = compute_baseline_score(
            popularity_score=100, travel_time_min=0, max_time_min=15
        )
        assert score == 100.0

    def test_boundary_hotspot(self):
        score = compute_baseline_score(
            popularity_score=100, travel_time_min=15, max_time_min=15
        )
        assert score == pytest.approx(60.0, rel=1e-6)  # 0.6*100 + 0.4*0

    def test_unreachable_hotspot(self):
        score = compute_baseline_score(
            popularity_score=100, travel_time_min=20, max_time_min=15
        )
        assert score == pytest.approx(60.0, rel=1e-6)  # accessibility clipped to 0

    def test_array_input(self):
        pop = np.array([100, 80, 60])
        time = np.array([0, 7.5, 15])
        scores = compute_baseline_score(pop, time, max_time_min=15)
        expected = np.array([100.0, 0.6*80 + 0.4*50, 0.6*60 + 0.4*0])
        np.testing.assert_array_almost_equal(scores, expected)


# ---------------------------------------------------------------------------
# Preference profile tests
# ---------------------------------------------------------------------------

class TestPreferenceProfiles:
    def test_all_profiles_exist(self):
        for name in ['quality_seeker', 'balanced', 'convenience', 'local_gem', 'late_night']:
            weights = get_profile_weights(name)
            total = sum(weights.values())
            assert abs(total - 1.0) < 1e-6

    def test_unknown_profile_raises(self):
        with pytest.raises(ValueError):
            get_profile_weights('nonexistent')


# ---------------------------------------------------------------------------
# Entropy + TOPSIS tests
# ---------------------------------------------------------------------------

class TestEntropyTOPSIS:
    def test_entropy_single_row_is_equal(self):
        weights = compute_entropy_weights(np.array([[1.0, 5.0, 9.0]]))
        np.testing.assert_allclose(weights, [1 / 3, 1 / 3, 1 / 3])

    def test_regularized_weights_respect_bounds(self):
        weights = regularize_entropy_weights(
            entropy_weights=np.array([0.97, 0.01, 0.01, 0.01]),
            prior_weights=np.array([0.4, 0.3, 0.2, 0.1]),
        )
        assert weights.sum() == pytest.approx(1.0)
        assert weights.min() >= 0.10 - 1e-9
        assert weights.max() <= 0.45 + 1e-9


class TestProductScoring:
    @pytest.mark.parametrize("profile", [
        "balanced",
        "quality_seeker",
        "convenience",
        "local_gem",
        "late_night",
    ])
    def test_all_product_profiles_return_bounded_scores(self, profile):
        result = compute_product_recommendation(
            np.array([20.0, 80.0]),
            np.array([90.0, 10.0]),
            profile_name=profile,
        )
        assert np.isfinite(result).all()
        assert result.min() >= 0
        assert result.max() <= 100

    def test_constant_components_produce_neutral_score(self):
        scores, weights = compute_product_area_scores(
            np.ones((3, 4))
        )
        np.testing.assert_allclose(scores, [50, 50, 50])
        assert weights.sum() == pytest.approx(1.0)

    def test_convenience_penalizes_low_access_more(self):
        area_quality = np.array([80.0])
        accessibility = np.array([10.0])
        balanced = compute_product_recommendation(
            area_quality,
            accessibility,
            profile_name="balanced",
        )
        convenience = compute_product_recommendation(
            area_quality,
            accessibility,
            profile_name="convenience",
        )
        assert convenience[0] < balanced[0]
    def test_entropy_weights_equal_data(self):
        # Uniform data → maximum entropy → minimum weight
        X = np.ones((10, 3))
        weights = compute_entropy_weights(X)
        np.testing.assert_array_almost_equal(weights, [1/3, 1/3, 1/3])

    def test_entropy_weights_nonuniform(self):
        # More variable column should get higher weight
        X = np.array([
            [1, 10, 5],
            [2, 20, 5],
            [3, 30, 5],
            [4, 40, 5],
        ], dtype=float)
        weights = compute_entropy_weights(X)
        # Column 0 and 1 have variation, column 2 is constant → should have near-zero weight
        assert weights[2] < weights[0]
        assert weights[2] < weights[1]

    def test_topsis_simple(self):
        X = np.array([
            [80, 60, 40],
            [60, 80, 50],
            [40, 40, 90],
        ], dtype=float)
        scores = compute_topsis_ranking(X)
        assert len(scores) == 3
        assert np.all((scores >= 0) & (scores <= 1))

    def test_topsis_with_weights(self):
        X = np.array([
            [100, 0],
            [0, 100],
        ], dtype=float)
        weights = np.array([0.8, 0.2])
        scores = compute_topsis_ranking(X, weights=weights)
        # First option should win because it has high score on the heavily weighted criterion
        assert scores[0] > scores[1]
