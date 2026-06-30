"""
Scoring Engine
==============

Robust scoring module for hotspot ranking and recommendation.

Replaces the ad-hoc scoring embedded in `app.py` with a configurable,
testable scoring framework that supports:
- Baseline (legacy) score for backward compatibility
- Z-score + winsorization normalization
- Entropy-weighted TOPSIS
- Stable travel-time decay for accessibility
- Deterministic tie-breakers

Author: Where to DINE Project
Date: 2026-06-25
Version: 2.0
"""

import numpy as np
import pandas as pd
from typing import Union, List, Dict, Optional, Sequence, Tuple
import logging

logger = logging.getLogger(__name__)

PRODUCT_COMPONENTS = ('demand', 'poi', 'time', 'confidence')


def _as_finite_array(
    values: Union[np.ndarray, pd.Series, Sequence[float]],
    fill_value: Optional[float] = None
) -> np.ndarray:
    """Convert values to float and replace non-finite entries deterministically."""
    arr = np.asarray(values, dtype=float)
    finite = np.isfinite(arr)
    if finite.all():
        return arr

    if fill_value is None:
        fill_value = float(np.nanmedian(arr[finite])) if finite.any() else 0.0
    return np.where(finite, arr, fill_value)


# ---------------------------------------------------------------------------
# Normalization utilities
# ---------------------------------------------------------------------------

def normalize_minmax(
    values: Union[np.ndarray, pd.Series],
    clip: bool = True
) -> np.ndarray:
    """
    Min-max normalize to [0, 100].

    Parameters
    ----------
    values : array-like
        Raw values
    clip : bool
        If True, clips max to avoid 0-division when all values are equal.

    Returns
    -------
    np.ndarray
        Scaled values in [0, 100]
    """
    arr = _as_finite_array(values)
    if arr.size == 0:
        return arr
    vmin = float(arr.min())
    vmax = float(arr.max())

    if vmax == vmin:
        if clip:
            return np.full_like(arr, 50.0)
        return np.zeros_like(arr)

    return 100.0 * (arr - vmin) / (vmax - vmin)


def normalize_zscore(
    values: Union[np.ndarray, pd.Series],
    winsorize: bool = False,
    winsorize_pct: tuple = (0.01, 0.99)
) -> np.ndarray:
    """
    Z-score standardization, optionally with winsorization.

    Parameters
    ----------
    values : array-like
        Raw values
    winsorize : bool
        If True, clip extreme values at the given percentiles before scaling.
    winsorize_pct : tuple
        Lower and upper percentiles for winsorization (default: 1%, 99%).

    Returns
    -------
    np.ndarray
        Z-scores (not bounded to [0, 100])
    """
    arr = _as_finite_array(values)
    if arr.size == 0:
        return arr

    if winsorize:
        lower = np.nanpercentile(arr, winsorize_pct[0] * 100)
        upper = np.nanpercentile(arr, winsorize_pct[1] * 100)
        arr = np.clip(arr, lower, upper)

    mu = np.nanmean(arr)
    sigma = np.nanstd(arr)

    if sigma == 0:
        return np.zeros_like(arr)

    return (arr - mu) / sigma


def normalize_zscore_to_100(
    values: Union[np.ndarray, pd.Series],
    winsorize: bool = False,
    winsorize_pct: tuple = (0.01, 0.99)
) -> np.ndarray:
    """
    Z-score + min-max rescale to [0, 100].

    This is the recommended robust normalization for skewed mobility data.
    """
    z = normalize_zscore(values, winsorize=winsorize, winsorize_pct=winsorize_pct)
    return normalize_minmax(z)


def normalize_percentile(
    values: Union[np.ndarray, pd.Series]
) -> np.ndarray:
    """
    Percentile-rank normalization to [0, 100].

    Completely robust to outliers but loses magnitude information.
    """
    arr = _as_finite_array(values)
    if arr.size == 0:
        return arr
    ranks = pd.Series(arr).rank(method='average', pct=True)
    return 100.0 * ranks.to_numpy()


def normalize_log1p(
    values: Union[np.ndarray, pd.Series]
) -> np.ndarray:
    """
    log1p transform followed by min-max rescale to [0, 100].

    Useful for highly skewed count data (taxi drop-offs, etc.).
    """
    arr = np.clip(_as_finite_array(values), 0, None)
    arr = np.log1p(arr)
    return normalize_minmax(arr)


def normalize_robust_percentile(
    values: Union[np.ndarray, pd.Series],
    log_transform: bool = False,
    winsorize_pct: Tuple[float, float] = (0.01, 0.99)
) -> np.ndarray:
    """Winsorize, optionally log-transform, then percentile-rank to [0, 100]."""
    arr = _as_finite_array(values)
    if arr.size == 0:
        return arr
    lower = float(np.quantile(arr, winsorize_pct[0]))
    upper = float(np.quantile(arr, winsorize_pct[1]))
    arr = np.clip(arr, lower, upper)
    if log_transform:
        arr = np.log1p(np.clip(arr, 0, None))
    return normalize_percentile(arr)


def compute_bayesian_rating(
    ratings: Union[np.ndarray, pd.Series],
    review_counts: Union[np.ndarray, pd.Series],
    global_mean: Optional[float] = None,
    prior_reviews: float = 50.0
) -> np.ndarray:
    """Shrink low-volume ratings toward the global mean."""
    rating_arr = _as_finite_array(ratings)
    reviews = np.clip(_as_finite_array(review_counts, fill_value=0.0), 0, None)
    if global_mean is None:
        valid = rating_arr[(rating_arr >= 1.0) & (rating_arr <= 5.0)]
        global_mean = float(valid.mean()) if valid.size else 3.5
    rating_arr = np.where(
        (rating_arr >= 1.0) & (rating_arr <= 5.0),
        rating_arr,
        global_mean
    )
    return (
        (reviews / (reviews + prior_reviews)) * rating_arr
        + (prior_reviews / (reviews + prior_reviews)) * global_mean
    )


# ---------------------------------------------------------------------------
# Accessibility scoring
# ---------------------------------------------------------------------------

def compute_access_score_decay(
    travel_time_min: Union[float, np.ndarray, pd.Series],
    max_time_min: float = 30.0,
    decay_type: str = 'exponential',
    lambda_param: float = 0.3
) -> Union[float, np.ndarray]:
    """
    Compute accessibility score from travel time using a fixed decay function.

    This is **stable** — the score depends only on the travel time and the
    chosen threshold, not on the other hotspots in the current result set.

    Parameters
    ----------
    travel_time_min : float or array-like
        Travel time in minutes
    max_time_min : float
        Maximum acceptable travel time (threshold). Beyond this, score = 0.
    decay_type : str
        'exponential' | 'gaussian' | 'linear' | 'inverse'
    lambda_param : float
        Decay parameter for exponential decay.

    Returns
    -------
    float or np.ndarray
        Accessibility score in [0, 100]
    """
    arr = np.asarray(travel_time_min, dtype=float)
    arr = np.clip(arr, 0, None)  # No negative travel times

    if decay_type == 'exponential':
        score = 100.0 * np.exp(-lambda_param * arr)
    elif decay_type == 'gaussian':
        sigma = max_time_min / 3.0
        score = 100.0 * np.exp(-0.5 * (arr / sigma) ** 2)
    elif decay_type == 'linear':
        score = 100.0 * np.clip(1 - arr / max_time_min, 0, 1)
    elif decay_type == 'inverse':
        # Hansen-style gravity potential
        score = 100.0 * np.exp(-lambda_param * arr)  # same as exponential
    else:
        raise ValueError(f"Unknown decay_type: {decay_type}")

    # Apply hard threshold
    score = np.where(arr > max_time_min, 0.0, score)
    return score


MODE_ACCESS_DEFAULTS = {
    'walk': {'max_time_min': 30.0, 'half_life_min': 10.0},
    'bike': {'max_time_min': 35.0, 'half_life_min': 15.0},
    'drive': {'max_time_min': 45.0, 'half_life_min': 20.0},
}


def compute_access_score_half_life(
    travel_time_min: Union[float, np.ndarray, pd.Series],
    max_time_min: float,
    half_life_min: float
) -> Union[float, np.ndarray]:
    """Stable exponential decay where the score halves at ``half_life_min``."""
    if max_time_min <= 0 or half_life_min <= 0:
        raise ValueError("max_time_min and half_life_min must be positive")
    arr = np.clip(_as_finite_array(travel_time_min), 0, None)
    score = 100.0 * np.exp(-np.log(2.0) * arr / half_life_min)
    return np.where(arr > max_time_min, 0.0, score)


def compute_access_score_euclidean(
    distance_km: Union[float, np.ndarray],
    max_distance_km: float = 2.0
) -> Union[float, np.ndarray]:
    """
    Legacy accessibility score based on Euclidean distance (for backward compat).

    WARNING: This is **unstable** — the score depends on max_distance_km,
    which in the original app.py was the max distance in the *current* result set.
    Use `compute_access_score_decay` for production.
    """
    arr = np.asarray(distance_km, dtype=float)
    arr = np.clip(arr, 0, None)
    return 100.0 * np.clip(1 - arr / max_distance_km, 0, 1)


# ---------------------------------------------------------------------------
# Composite scoring
# ---------------------------------------------------------------------------

def compute_composite_score(
    demand_score: Union[float, np.ndarray],
    poi_score: Union[float, np.ndarray],
    access_score: Union[float, np.ndarray],
    confidence_score: Optional[Union[float, np.ndarray]] = None,
    weights: Optional[Dict[str, float]] = None
) -> Union[float, np.ndarray]:
    """
    Compute weighted composite score.

    Default weights (inspired by TOPSIS + entropy weighting literature):
    - demand: 0.35
    - poi: 0.30
    - access: 0.25
    - confidence: 0.10

    Parameters
    ----------
    demand_score : float or array-like
        Normalized mobility demand score [0, 100]
    poi_score : float or array-like
        Normalized POI quality/density score [0, 100]
    access_score : float or array-like
        Normalized accessibility score [0, 100]
    confidence_score : float or array-like, optional
        Data-quality confidence score [0, 100]
    weights : dict, optional
        Custom weights. Must sum to 1.0.

    Returns
    -------
    float or np.ndarray
        Composite score in [0, 100]
    """
    if weights is None:
        weights = {
            'demand': 0.35,
            'poi': 0.30,
            'access': 0.25,
            'confidence': 0.10
        }

    total = sum(weights.values())
    if abs(total - 1.0) > 1e-6:
        raise ValueError(f"Weights must sum to 1.0, got {total}")

    demand = np.asarray(demand_score, dtype=float)
    poi = np.asarray(poi_score, dtype=float)
    access = np.asarray(access_score, dtype=float)

    score = (
        weights['demand'] * demand +
        weights['poi'] * poi +
        weights['access'] * access
    )

    if confidence_score is not None and weights.get('confidence', 0) > 0:
        conf = np.asarray(confidence_score, dtype=float)
        score += weights['confidence'] * conf

    return np.clip(score, 0, 100)


PRODUCT_PROFILE_PRIORS = {
    'balanced': {
        'prior': np.array([0.35, 0.35, 0.15, 0.15]),
        'access_weight': 0.30,
    },
    'quality_seeker': {
        'prior': np.array([0.35, 0.45, 0.10, 0.10]),
        'access_weight': 0.10,
    },
    'convenience': {
        'prior': np.array([0.25, 0.30, 0.15, 0.30]),
        'access_weight': 0.50,
    },
    'local_gem': {
        'prior': np.array([0.15, 0.50, 0.15, 0.20]),
        'access_weight': 0.20,
    },
    'late_night': {
        'prior': np.array([0.30, 0.20, 0.40, 0.10]),
        'access_weight': 0.20,
    },
}


def regularize_entropy_weights(
    entropy_weights: Union[np.ndarray, Sequence[float]],
    prior_weights: Union[np.ndarray, Sequence[float]],
    blend: float = 0.5,
    floor: float = 0.10,
    cap: float = 0.45
) -> np.ndarray:
    """Blend data-driven weights with a prior, clamp, and renormalize."""
    if not 0 <= blend <= 1:
        raise ValueError("blend must be between 0 and 1")
    if not 0 <= floor < cap <= 1:
        raise ValueError("weight bounds must satisfy 0 <= floor < cap <= 1")

    entropy = _as_finite_array(entropy_weights)
    prior = _as_finite_array(prior_weights)
    if entropy.shape != prior.shape:
        raise ValueError("entropy_weights and prior_weights must have equal shapes")
    if entropy.size == 0:
        return entropy

    entropy = entropy / entropy.sum() if entropy.sum() > 0 else np.ones_like(entropy) / len(entropy)
    prior = prior / prior.sum() if prior.sum() > 0 else np.ones_like(prior) / len(prior)
    weights = blend * entropy + (1.0 - blend) * prior
    weights = np.clip(weights, floor, cap)
    for _ in range(100):
        difference = 1.0 - weights.sum()
        if abs(difference) < 1e-12:
            break
        if difference > 0:
            adjustable = weights < cap - 1e-12
        else:
            adjustable = weights > floor + 1e-12
        if not adjustable.any():
            raise ValueError("Weight bounds cannot produce a unit-sum vector")
        weights[adjustable] += difference / adjustable.sum()
        weights = np.clip(weights, floor, cap)
    return weights


def compute_product_area_scores(
    components: np.ndarray,
    profile_name: str = 'balanced',
    entropy_weights: Optional[np.ndarray] = None
) -> Tuple[np.ndarray, np.ndarray]:
    """Compute constrained product-area TOPSIS scores and effective weights."""
    X = np.asarray(components, dtype=float)
    if X.ndim != 2 or X.shape[1] != len(PRODUCT_COMPONENTS):
        raise ValueError(
            f"components must have shape (n, {len(PRODUCT_COMPONENTS)})"
        )
    if profile_name not in PRODUCT_PROFILE_PRIORS:
        raise ValueError(f"Unknown profile: {profile_name}")
    if len(X) == 0:
        return np.array([], dtype=float), np.ones(4) / 4

    X = np.nan_to_num(X, nan=50.0, posinf=100.0, neginf=0.0)
    X = np.clip(X, 0.0, 100.0)
    if entropy_weights is None:
        entropy_weights = compute_entropy_weights(X)
    prior = PRODUCT_PROFILE_PRIORS[profile_name]['prior']
    weights = regularize_entropy_weights(entropy_weights, prior)
    scores = compute_topsis_ranking(
        X,
        weights=weights,
        benefit_criteria=list(range(X.shape[1]))
    )
    return 100.0 * scores, weights


def compute_product_recommendation(
    area_quality_score: Union[np.ndarray, pd.Series],
    access_score: Union[np.ndarray, pd.Series],
    profile_name: str = 'balanced'
) -> np.ndarray:
    """Blend static area quality with request-specific accessibility."""
    if profile_name not in PRODUCT_PROFILE_PRIORS:
        raise ValueError(f"Unknown profile: {profile_name}")
    access_weight = PRODUCT_PROFILE_PRIORS[profile_name]['access_weight']
    area = np.clip(_as_finite_array(area_quality_score), 0, 100)
    access = np.clip(_as_finite_array(access_score), 0, 100)
    return (1.0 - access_weight) * area + access_weight * access


# ---------------------------------------------------------------------------
# Tie-breaking
# ---------------------------------------------------------------------------

def compute_tiebreaker_rank(
    df: pd.DataFrame,
    score_col: str = 'recommendation_score',
    access_col: str = 'accessibility_score',
    popularity_col: str = 'popularity_score',
    rating_conf_col: Optional[str] = None,
    review_count_col: Optional[str] = None
) -> pd.DataFrame:
    """
    Add deterministic tie-breaker rank to a DataFrame of hotspots.

    Breaks ties by (in order):
    1. Higher popularity score
    2. Higher accessibility score
    3. Higher rating confidence (if available)
    4. Higher review count (if available)
    5. Original index order (stable fallback)

    Parameters
    ----------
    df : pd.DataFrame
        Hotspots with at least score_col, access_col, popularity_col
    score_col : str
        Primary composite score column
    access_col : str
        Accessibility score column
    popularity_col : str
        Popularity score column
    rating_conf_col : str, optional
        Rating confidence column
    review_count_col : str, optional
        Review count column

    Returns
    -------
    pd.DataFrame
        DataFrame with added 'rank' column (1 = best)
    """
    sort_keys = [score_col, popularity_col, access_col]
    ascending_flags = [False, False, False]

    if rating_conf_col and rating_conf_col in df.columns:
        sort_keys.append(rating_conf_col)
        ascending_flags.append(False)

    if review_count_col and review_count_col in df.columns:
        sort_keys.append(review_count_col)
        ascending_flags.append(False)

    df_sorted = df.sort_values(
        by=sort_keys,
        ascending=ascending_flags,
        kind='mergesort'  # stable sort
    ).reset_index(drop=True)

    df_sorted['rank'] = np.arange(1, len(df_sorted) + 1)
    return df_sorted


# ---------------------------------------------------------------------------
# Preference profiles (inspired by Amap Street Rank)
# ---------------------------------------------------------------------------

PREFERENCE_PROFILES = {
    'quality_seeker': {
        'demand': 0.55, 'poi': 0.30, 'access': 0.10, 'confidence': 0.05,
        'description': 'Prioritize popular, high-demand areas even if far away'
    },
    'balanced': {
        'demand': 0.35, 'poi': 0.30, 'access': 0.25, 'confidence': 0.10,
        'description': 'Balanced quality and convenience (default)'
    },
    'convenience': {
        'demand': 0.20, 'poi': 0.25, 'access': 0.45, 'confidence': 0.10,
        'description': 'Prioritize nearby, easily accessible options'
    },
    'local_gem': {
        'demand': 0.15, 'poi': 0.50, 'access': 0.25, 'confidence': 0.10,
        'description': 'Prioritize high-quality POI signals (diversity, ratings)'
    },
    'late_night': {
        'demand': 0.40, 'poi': 0.30, 'access': 0.20, 'confidence': 0.10,
        'description': 'Weighted toward late-night demand signals'
    }
}


def get_profile_weights(profile_name: str) -> Dict[str, float]:
    """Get weights for a named preference profile."""
    if profile_name not in PREFERENCE_PROFILES:
        raise ValueError(
            f"Unknown profile: {profile_name}. "
            f"Available: {list(PREFERENCE_PROFILES.keys())}"
        )
    profile = PREFERENCE_PROFILES[profile_name].copy()
    # Remove description before returning weights
    profile.pop('description', None)
    return profile


# ---------------------------------------------------------------------------
# Legacy / backward compatibility
# ---------------------------------------------------------------------------

def compute_baseline_score(
    popularity_score: Union[float, np.ndarray],
    travel_time_min: Union[float, np.ndarray],
    max_time_min: float = 30.0,
    alpha: float = 0.6,
    beta: float = 0.4
) -> Union[float, np.ndarray]:
    """
    Compute the original baseline score (legacy, for comparison only).

    Score = alpha * popularity + beta * accessibility
    where accessibility = 100 * (1 - travel_time / max_time)

    This is the formula used in the original app.py and
    docs/methodology/recommendation_scoring.md.
    """
    arr_time = np.asarray(travel_time_min, dtype=float)
    arr_pop = np.asarray(popularity_score, dtype=float)

    accessibility = 100.0 * np.clip(1 - arr_time / max_time_min, 0, 1)
    return alpha * arr_pop + beta * accessibility


# ---------------------------------------------------------------------------
# Entropy weights + TOPSIS (optional advanced)
# ---------------------------------------------------------------------------

def compute_entropy_weights(
    indicators: np.ndarray,
    epsilon: float = 1e-12
) -> np.ndarray:
    """
    Compute objective weights using Entropy Weight Method (EWM).

    Parameters
    ----------
    indicators : np.ndarray, shape (n_samples, n_criteria)
        Indicator matrix (all values should be >= 0)
    epsilon : float
        Small value to avoid log(0)

    Returns
    -------
    np.ndarray
        Weights for each criterion, summing to 1.0
    """
    X = np.asarray(indicators, dtype=float)
    if X.ndim != 2:
        raise ValueError("indicators must be a two-dimensional matrix")
    if X.shape[1] == 0:
        return np.array([], dtype=float)
    if X.shape[0] <= 1:
        return np.ones(X.shape[1], dtype=float) / X.shape[1]
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

    if X.min() < 0:
        raise ValueError("Entropy weights require non-negative indicators")

    # Normalize to [0, 1] per column
    col_sums = X.sum(axis=0, keepdims=True)
    col_sums = np.where(col_sums == 0, epsilon, col_sums)
    P = X / col_sums

    # Entropy
    P = np.clip(P, epsilon, 1.0)  # avoid log(0)
    E = -np.sum(P * np.log(P), axis=0) / np.log(X.shape[0])

    # Redundancy = 1 - E
    D = 1 - E
    if not np.isfinite(D).all() or D.sum() <= epsilon:
        return np.ones(X.shape[1], dtype=float) / X.shape[1]
    weights = D / D.sum()

    return weights


def compute_topsis_ranking(
    indicators: np.ndarray,
    weights: Optional[np.ndarray] = None,
    benefit_criteria: Optional[List[int]] = None
) -> np.ndarray:
    """
    Compute TOPSIS (Technique for Order Preference by Similarity to Ideal Solution)
    ranking scores.

    Parameters
    ----------
    indicators : np.ndarray, shape (n_samples, n_criteria)
        Decision matrix
    weights : np.ndarray, optional
        Criterion weights. If None, uses equal weights.
    benefit_criteria : list of int, optional
        Indices of criteria where higher is better (default: all).

    Returns
    -------
    np.ndarray
        TOPSIS scores in [0, 1], higher = better
    """
    X = np.asarray(indicators, dtype=float)
    if X.ndim != 2:
        raise ValueError("indicators must be a two-dimensional matrix")
    n, m = X.shape
    if n == 0:
        return np.array([], dtype=float)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

    if weights is None:
        weights = np.ones(m) / m

    # Step 1: Normalize (vector normalization)
    norms = np.linalg.norm(X, axis=0)
    norms = np.where(norms == 0, 1, norms)
    R = X / norms

    # Step 2: Weighted normalized matrix
    V = R * weights

    # Step 3: Ideal and anti-ideal solutions
    if benefit_criteria is None:
        benefit_criteria = list(range(m))
    cost_criteria = [i for i in range(m) if i not in benefit_criteria]

    V_ideal = np.zeros(m)
    V_anti = np.zeros(m)

    for j in range(m):
        if j in benefit_criteria:
            V_ideal[j] = V[:, j].max()
            V_anti[j] = V[:, j].min()
        else:
            V_ideal[j] = V[:, j].min()
            V_anti[j] = V[:, j].max()

    # Step 4: Distances
    D_ideal = np.linalg.norm(V - V_ideal, axis=1)
    D_anti = np.linalg.norm(V - V_anti, axis=1)

    # Step 5: Score
    denominator = D_ideal + D_anti
    score = np.divide(
        D_anti,
        denominator,
        out=np.full_like(D_anti, 0.5),
        where=denominator > 1e-12,
    )
    return score
