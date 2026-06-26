"""
Quick Scoring V1 vs V2 Comparison on Taxi Hotspots
===================================================

A lightweight comparison script that applies both v1 (max-normalization)
and v2 (z-score + winsorization) scoring to the existing taxi_hotspots,
then compares the resulting rankings.

This does not require re-running the full pipeline (which currently
produces 0 intersections due to strict overlap filtering).

Input:
    - data/processed/taxi_hotspots.geojson

Output:
    - data/processed/scoring_v1_vs_v2.json
    - outputs/figures/scoring_comparison_*.png

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

from src.analysis.scoring import normalize_zscore_to_100, compute_tiebreaker_rank

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

    # Density = dropoffs per km²
    df['density'] = df['n_dropoffs'] / df['area_sqkm'].replace(0, np.nan).fillna(1e-6)

    # Max-normalization
    max_density = df['density'].max()
    df['score_v1'] = 100 * df['density'] / max_density if max_density > 0 else 0

    # Dense rank (v1 default)
    df['rank_v1'] = df['score_v1'].rank(ascending=False, method='dense').astype(int)

    return df


def apply_v2_scoring(gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    """Apply robust v2 z-score + winsorization scoring."""
    df = gdf[['hotspot_id', 'n_dropoffs', 'total_weight', 'area_sqkm']].copy()

    # Density = dropoffs per km²
    df['density'] = df['n_dropoffs'] / df['area_sqkm'].replace(0, np.nan).fillna(1e-6)

    # Z-score + winsorization + rescale to [0, 100]
    df['score_v2'] = normalize_zscore_to_100(
        df['density'].values,
        winsorize=True,
        winsorize_pct=(0.01, 0.99)
    )

    # Deterministic tie-breaker (by density, then n_dropoffs)
    df = df.sort_values(
        by=['score_v2', 'density', 'n_dropoffs'],
        ascending=[False, False, False],
        kind='mergesort'
    ).reset_index(drop=True)
    df['rank_v2'] = np.arange(1, len(df) + 1)

    return df


def compare_versions(df_v1: pd.DataFrame, df_v2: pd.DataFrame) -> dict:
    """Compare v1 and v2 rankings."""
    merged = df_v1[['hotspot_id', 'score_v1', 'rank_v1']].merge(
        df_v2[['hotspot_id', 'score_v2', 'rank_v2']],
        on='hotspot_id'
    )

    # Spearman & Kendall
    spearman_rho, spearman_p = stats.spearmanr(merged['score_v1'], merged['score_v2'])
    kendall_tau, kendall_p = stats.kendalltau(merged['score_v1'], merged['score_v2'])

    # Rank shift
    rank_shift = (merged['rank_v1'] - merged['rank_v2']).abs()
    large_shifts = (rank_shift > 3).sum()

    # Tie counts
    ties_v1 = merged['score_v1'].duplicated().sum()
    ties_v2 = merged['score_v2'].duplicated().sum()

    # Score distribution stats
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
        'ties_v1': int(ties_v1),
        'ties_v2': int(ties_v2),
        'score_stats_v1': _stats(merged['score_v1']),
        'score_stats_v2': _stats(merged['score_v2'])
    }


def generate_figures(df_v1, df_v2, output_dir):
    """Generate comparison figures."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        logger.warning("matplotlib not available, skipping figures")
        return

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    merged = df_v1[['hotspot_id', 'score_v1', 'rank_v1']].merge(
        df_v2[['hotspot_id', 'score_v2', 'rank_v2']],
        on='hotspot_id'
    )

    # Figure 1: Score distribution
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(merged['score_v1'], bins=30, alpha=0.5, label='V1 (max-normalization)', color='steelblue')
    ax.hist(merged['score_v2'], bins=30, alpha=0.5, label='V2 (z-score + winsorize)', color='coral')
    ax.set_xlabel('Score')
    ax.set_ylabel('Count')
    ax.set_title('Score Distribution: V1 vs V2')
    ax.legend()
    fig.savefig(output_path / 'scoring_v1_vs_v2_distribution.png', dpi=150, bbox_inches='tight')
    plt.close(fig)

    # Figure 2: Rank scatter
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.scatter(merged['rank_v1'], merged['rank_v2'], alpha=0.6, s=50)
    ax.plot([1, merged['rank_v1'].max()], [1, merged['rank_v1'].max()], 'k--', label='Perfect agreement')
    ax.set_xlabel('V1 Rank')
    ax.set_ylabel('V2 Rank')
    ax.set_title('Rank Comparison: V1 vs V2')
    ax.legend()
    fig.savefig(output_path / 'scoring_v1_vs_v2_ranks.png', dpi=150, bbox_inches='tight')
    plt.close(fig)

    logger.info(f"Saved figures to {output_path}")


def main():
    """Main comparison function."""
    logger.info("=" * 60)
    logger.info("QUICK SCORING V1 vs V2 COMPARISON")
    logger.info("=" * 60)

    input_path = "data/processed/taxi_hotspots.geojson"
    output_dir = "data/processed"
    figure_dir = "outputs/figures"

    if not Path(input_path).exists():
        logger.error(f"Input not found: {input_path}")
        return 1

    # Load
    gdf = load_taxi_hotspots(input_path)

    # Apply v1
    logger.info("\n[Step 1/3] Applying v1 scoring (max-normalization)...")
    df_v1 = apply_v1_scoring(gdf)
    logger.info(f"  V1 ties: {df_v1['score_v1'].duplicated().sum()}")

    # Apply v2
    logger.info("\n[Step 2/3] Applying v2 scoring (z-score + winsorization)...")
    df_v2 = apply_v2_scoring(gdf)
    logger.info(f"  V2 ties: {df_v2['score_v2'].duplicated().sum()}")

    # Compare
    logger.info("\n[Step 3/3] Comparing rankings...")
    results = compare_versions(df_v1, df_v2)

    # Save JSON
    output_path = Path(output_dir) / "scoring_v1_vs_v2.json"
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    logger.info(f"\nResults saved to {output_path}")

    # Figures
    generate_figures(df_v1, df_v2, figure_dir)

    # Print summary
    print("\n" + "=" * 60)
    print("SCORING V1 vs V2 COMPARISON SUMMARY")
    print("=" * 60)
    print(f"V1 (max-normalization):")
    for k, v in results['score_stats_v1'].items():
        print(f"  {k}: {v:.3f}")
    print(f"\nV2 (z-score + winsorize):")
    for k, v in results['score_stats_v2'].items():
        print(f"  {k}: {v:.3f}")
    print(f"\nRanking Stability:")
    print(f"  Spearman rho: {results['spearman_rho']:.3f} (p={results['spearman_p']:.3f})")
    print(f"  Kendall tau: {results['kendall_tau']:.3f} (p={results['kendall_p']:.3f})")
    print(f"  Avg rank shift: {results['avg_rank_shift']:.1f}")
    print(f"  Max rank shift: {results['max_rank_shift']}")
    print(f"  Large shifts (>3): {results['large_shifts']} ({results['pct_large_shifts']:.1f}%)")
    print(f"\nTie-breaking:")
    print(f"  V1 ties: {results['ties_v1']}")
    print(f"  V2 ties: {results['ties_v2']}")
    print("=" * 60 + "\n")

    logger.info("Comparison completed!")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
