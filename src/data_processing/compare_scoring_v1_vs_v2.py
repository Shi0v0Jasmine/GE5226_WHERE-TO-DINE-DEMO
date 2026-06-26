"""
Quick Scoring V1 vs V2 vs V3 Comparison on Taxi Hotspots
============================================================

A lightweight comparison script that applies three scoring methods to the
existing taxi_hotspots, then compares the resulting rankings.

V1: max-normalization (legacy)
V2: z-score + winsorization + fixed 0.5/0.5 weights
V3: entropy-weighted TOPSIS

Input:
    - data/processed/taxi_hotspots.geojson

Output:
    - data/processed/scoring_v1_v2_v3.json
    - outputs/figures/scoring_v1_v2_v3_*.png

Author: Where to DINE Project
Date: 2026-06-26
"""

import geopandas as gpd
import pandas as pd
import numpy as np
from pathlib import Path
import json
import logging
from scipy import stats
import sys

sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.analysis.scoring import (
    normalize_zscore_to_100,
    compute_tiebreaker_rank,
    compute_entropy_weights,
    compute_topsis_ranking
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_taxi_hotspots(path: str) -> gpd.GeoDataFrame:
    """Load taxi hotspots with n_dropoffs and area."""
    gdf = gpd.read_file(path)
    logger.info(f"Loaded {len(gdf)} taxi hotspots")
    return gdf


def apply_v1_scoring(gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    """Apply legacy v1 max-normalization scoring."""
    df = gdf[['hotspot_id', 'n_dropoffs', 'total_weight', 'area_sqkm']].copy()

    df['density'] = df['n_dropoffs'] / df['area_sqkm'].replace(0, np.nan).fillna(1e-6)

    max_density = df['density'].max()
    df['score_v1'] = 100 * df['density'] / max_density if max_density > 0 else 0

    df['rank_v1'] = df['score_v1'].rank(ascending=False, method='dense').astype(int)

    return df


def apply_v2_scoring(gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    """Apply robust v2 z-score + winsorization scoring."""
    df = gdf[['hotspot_id', 'n_dropoffs', 'total_weight', 'area_sqkm']].copy()

    df['density'] = df['n_dropoffs'] / df['area_sqkm'].replace(0, np.nan).fillna(1e-6)

    df['score_v2'] = normalize_zscore_to_100(
        df['density'].values,
        winsorize=True,
        winsorize_pct=(0.01, 0.99)
    )

    df = df.sort_values(
        by=['score_v2', 'density', 'n_dropoffs'],
        ascending=[False, False, False],
        kind='mergesort'
    ).reset_index(drop=True)
    df['rank_v2'] = np.arange(1, len(df) + 1)

    return df


def apply_v3_scoring(gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    """Apply entropy-weighted TOPSIS scoring (v3)."""
    df = gdf[['hotspot_id', 'n_dropoffs', 'total_weight', 'area_sqkm']].copy()

    df['density'] = df['n_dropoffs'] / df['area_sqkm'].replace(0, np.nan).fillna(1e-6)

    indicators = np.column_stack([
        df['density'].values,
        df['total_weight'].values
    ])
    indicators = np.clip(indicators, 0, None)

    entropy_w = compute_entropy_weights(indicators)
    topsis_scores = compute_topsis_ranking(
        indicators,
        weights=entropy_w,
        benefit_criteria=[0, 1]
    )
    df['score_v3'] = topsis_scores * 100.0
    df['entropy_w_density'] = entropy_w[0]
    df['entropy_w_weight'] = entropy_w[1]

    df = df.sort_values(
        by=['score_v3', 'density', 'n_dropoffs'],
        ascending=[False, False, False],
        kind='mergesort'
    ).reset_index(drop=True)
    df['rank_v3'] = np.arange(1, len(df) + 1)

    return df


def compare_pair(df_a, df_b, label_a, label_b):
    """Compare two scoring versions."""
    merged = df_a[['hotspot_id', f'score_{label_a}', f'rank_{label_a}']].merge(
        df_b[['hotspot_id', f'score_{label_b}', f'rank_{label_b}']],
        on='hotspot_id'
    )

    spearman_rho, spearman_p = stats.spearmanr(
        merged[f'score_{label_a}'], merged[f'score_{label_b}']
    )
    kendall_tau, kendall_p = stats.kendalltau(
        merged[f'rank_{label_a}'], merged[f'rank_{label_b}']
    )
    rank_shift = (merged[f'rank_{label_a}'] - merged[f'rank_{label_b}']).abs()
    large_shifts = (rank_shift > 3).sum()
    ties_a = merged[f'score_{label_a}'].duplicated().sum()
    ties_b = merged[f'score_{label_b}'].duplicated().sum()

    def _stats(col):
        return {
            'mean': float(col.mean()),
            'std': float(col.std()),
            'min': float(col.min()),
            'max': float(col.max()),
            'median': float(col.median()),
            'skew': float(stats.skew(col)),
            'kurtosis': float(stats.kurtosis(col))
        }

    return {
        'spearman_rho': float(spearman_rho),
        'spearman_p': float(spearman_p),
        'kendall_tau': float(kendall_tau),
        'kendall_p': float(kendall_p),
        'avg_rank_shift': float(rank_shift.mean()),
        'max_rank_shift': int(rank_shift.max()),
        'large_shifts': int(large_shifts),
        'pct_large_shifts': float(large_shifts / len(merged) * 100),
        'ties_a': int(ties_a),
        'ties_b': int(ties_b),
        'score_stats_a': _stats(merged[f'score_{label_a}']),
        'score_stats_b': _stats(merged[f'score_{label_b}'])
    }


def generate_figures(df_v1, df_v2, df_v3, output_dir):
    """Generate comparison figures for V1, V2, V3."""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        logger.warning("matplotlib not available, skipping figures")
        return

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    merged = df_v1[['hotspot_id', 'score_v1', 'rank_v1']].merge(
        df_v2[['hotspot_id', 'score_v2', 'rank_v2']],
        on='hotspot_id'
    ).merge(
        df_v3[['hotspot_id', 'score_v3', 'rank_v3']],
        on='hotspot_id'
    )

    # Figure 1: Score distribution
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(merged['score_v1'], bins=30, alpha=0.5, label='V1 (max-normalization)', color='steelblue')
    ax.hist(merged['score_v2'], bins=30, alpha=0.5, label='V2 (z-score + winsorize)', color='coral')
    ax.hist(merged['score_v3'], bins=30, alpha=0.5, label='V3 (entropy-TOPSIS)', color='seagreen')
    ax.set_xlabel('Score')
    ax.set_ylabel('Count')
    ax.set_title('Score Distribution: V1 vs V2 vs V3')
    ax.legend()
    fig.savefig(output_path / 'scoring_v1_v2_v3_distribution.png', dpi=150, bbox_inches='tight')
    plt.close(fig)

    # Figure 2: V1 vs V3 rank scatter
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.scatter(merged['rank_v1'], merged['rank_v3'], alpha=0.6, s=50, color='seagreen')
    ax.plot([1, merged['rank_v1'].max()], [1, merged['rank_v1'].max()], 'k--', label='Perfect agreement')
    ax.set_xlabel('V1 Rank')
    ax.set_ylabel('V3 Rank')
    ax.set_title('Rank Comparison: V1 vs V3 (Entropy-TOPSIS)')
    ax.legend()
    fig.savefig(output_path / 'scoring_v1_vs_v3_ranks.png', dpi=150, bbox_inches='tight')
    plt.close(fig)

    logger.info(f"Saved figures to {output_path}")


def main():
    """Main comparison function."""
    logger.info("=" * 60)
    logger.info("QUICK SCORING V1 vs V2 vs V3 COMPARISON")
    logger.info("=" * 60)

    input_path = "data/processed/taxi_hotspots.geojson"
    output_dir = "data/processed"
    figure_dir = "outputs/figures"

    if not Path(input_path).exists():
        logger.error(f"Input not found: {input_path}")
        return 1

    gdf = load_taxi_hotspots(input_path)

    # Apply v1
    logger.info("\n[Step 1/4] Applying v1 scoring (max-normalization)...")
    df_v1 = apply_v1_scoring(gdf)
    logger.info(f"  V1 ties: {df_v1['score_v1'].duplicated().sum()}")

    # Apply v2
    logger.info("\n[Step 2/4] Applying v2 scoring (z-score + winsorization)...")
    df_v2 = apply_v2_scoring(gdf)
    logger.info(f"  V2 ties: {df_v2['score_v2'].duplicated().sum()}")

    # Apply v3
    logger.info("\n[Step 3/4] Applying v3 scoring (entropy-TOPSIS)...")
    df_v3 = apply_v3_scoring(gdf)
    logger.info(f"  V3 ties: {df_v3['score_v3'].duplicated().sum()}")
    logger.info(f"  Entropy weights: density={df_v3['entropy_w_density'].iloc[0]:.3f}, weight={df_v3['entropy_w_weight'].iloc[0]:.3f}")

    # Compare all pairs
    logger.info("\n[Step 4/4] Comparing rankings...")
    r12 = compare_pair(df_v1, df_v2, 'v1', 'v2')
    r13 = compare_pair(df_v1, df_v3, 'v1', 'v3')
    r23 = compare_pair(df_v2, df_v3, 'v2', 'v3')

    results = {
        'v1_vs_v2': r12,
        'v1_vs_v3': r13,
        'v2_vs_v3': r23,
        'score_stats_v1': r12['score_stats_a'],
        'score_stats_v2': r12['score_stats_b'],
        'score_stats_v3': r13['score_stats_b'],
    }

    output_path = Path(output_dir) / "scoring_v1_v2_v3.json"
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    logger.info(f"\nResults saved to {output_path}")

    generate_figures(df_v1, df_v2, df_v3, figure_dir)

    print("\n" + "=" * 60)
    print("SCORING V1 vs V2 vs V3 COMPARISON SUMMARY")
    print("=" * 60)
    print(f"V1 (max-normalization):")
    for k, v in results['score_stats_v1'].items():
        print(f"  {k}: {v:.3f}")
    print(f"\nV2 (z-score + winsorize):")
    for k, v in results['score_stats_v2'].items():
        print(f"  {k}: {v:.3f}")
    print(f"\nV3 (entropy-TOPSIS):")
    for k, v in results['score_stats_v3'].items():
        print(f"  {k}: {v:.3f}")
    print(f"\nV1 vs V2:")
    print(f"  Spearman rho: {results['v1_vs_v2']['spearman_rho']:.3f} (p={results['v1_vs_v2']['spearman_p']:.3f})")
    print(f"  Kendall tau: {results['v1_vs_v2']['kendall_tau']:.3f} (p={results['v1_vs_v2']['kendall_p']:.3f})")
    print(f"  Avg rank shift: {results['v1_vs_v2']['avg_rank_shift']:.1f}")
    print(f"\nV1 vs V3:")
    print(f"  Spearman rho: {results['v1_vs_v3']['spearman_rho']:.3f} (p={results['v1_vs_v3']['spearman_p']:.3f})")
    print(f"  Kendall tau: {results['v1_vs_v3']['kendall_tau']:.3f} (p={results['v1_vs_v3']['kendall_p']:.3f})")
    print(f"  Avg rank shift: {results['v1_vs_v3']['avg_rank_shift']:.1f}")
    print(f"\nV2 vs V3:")
    print(f"  Spearman rho: {results['v2_vs_v3']['spearman_rho']:.3f} (p={results['v2_vs_v3']['spearman_p']:.3f})")
    print(f"  Kendall tau: {results['v2_vs_v3']['kendall_tau']:.3f} (p={results['v2_vs_v3']['kendall_p']:.3f})")
    print(f"  Avg rank shift: {results['v2_vs_v3']['avg_rank_shift']:.1f}")
    print(f"\nTie-breaking:")
    print(f"  V1 ties: {results['v1_vs_v2']['ties_a']}")
    print(f"  V2 ties: {results['v1_vs_v2']['ties_b']}")
    print(f"  V3 ties: {results['v1_vs_v3']['ties_b']}")
    print("=" * 60 + "\n")

    logger.info("Comparison completed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
