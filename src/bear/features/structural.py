"""Structural short score (Section 20 of spec).

Computes a weighted percentile-rank score (0-100) measuring how structurally
unfavorable an asset is for long holders. Higher = more short-friendly.
"""

from __future__ import annotations

import polars as pl
import numpy as np


# Component weights per spec Section 20
_COMPONENT_WEIGHTS: dict[str, float] = {
    "fdv_overhang": 0.18,
    "dilution_90d": 0.18,
    "unlock_to_adv": 0.16,
    "insider_unlock_share": 0.10,
    "emission_rate": 0.10,
    "weak_relative_momentum": 0.08,
    "weak_long_term_momentum": 0.08,
    "poor_value_capture": 0.06,
    "declining_activity": 0.06,
}


def compute_structural_short_score(
    tokenomics_df: pl.DataFrame,
    momentum_df: pl.DataFrame,
) -> pl.DataFrame:
    """Compute structural short score per Section 20.

    Each component is converted to a 0-100 percentile rank across the
    cross-section of assets. Missing features are excluded and weights
    are dynamically renormalized over observed components.

    Args:
        tokenomics_df: DataFrame with columns:
            - 'symbol': asset symbol
            - 'fdv_overhang': float (circulating supply / FDV, higher = more dilution risk)
            - 'dilution_90d': float (expected dilution over 90 days, fraction)
            - 'unlock_to_adv': float (upcoming unlocks / ADV, higher = more sell pressure)
            - 'insider_unlock_share': float (fraction of unlocks going to insiders)
            - 'emission_rate': float (annual emission rate as fraction of supply)
        momentum_df: DataFrame with columns:
            - 'symbol': asset symbol
            - 'relative_momentum_30d': float (return vs BTC, negative = weak)
            - 'long_term_momentum_90d': float (absolute 90d return, negative = weak)
            - 'value_capture': float (price vs TVL or revenue ratio, high = overvalued)
            - 'activity_change_30d': float (change in active addresses or txns)

    Returns:
        DataFrame with columns:
            - 'symbol': asset symbol
            - 'structural_short_score': 0-100 composite score
            - 'confidence': 0-100 data confidence
            - 'feature_coverage': fraction of components with non-null data
            - Individual component scores (e.g., 'score_fdv_overhang')
    """
    # Merge tokenomics and momentum
    merged = tokenomics_df.join(momentum_df, on="symbol", how="outer", coalesce=True)

    symbols = merged["symbol"].to_list()

    # Raw component values
    components = {
        "fdv_overhang": merged["fdv_overhang"].to_list() if "fdv_overhang" in merged.columns else [None] * len(symbols),
        "dilution_90d": merged["dilution_90d"].to_list() if "dilution_90d" in merged.columns else [None] * len(symbols),
        "unlock_to_adv": merged["unlock_to_adv"].to_list() if "unlock_to_adv" in merged.columns else [None] * len(symbols),
        "insider_unlock_share": merged["insider_unlock_share"].to_list() if "insider_unlock_share" in merged.columns else [None] * len(symbols),
        "emission_rate": merged["emission_rate"].to_list() if "emission_rate" in merged.columns else [None] * len(symbols),
        "weak_relative_momentum": [
            -v if v is not None else None
            for v in (merged["relative_momentum_30d"].to_list() if "relative_momentum_30d" in merged.columns else [None] * len(symbols))
        ],
        "weak_long_term_momentum": [
            -v if v is not None else None
            for v in (merged["long_term_momentum_90d"].to_list() if "long_term_momentum_90d" in merged.columns else [None] * len(symbols))
        ],
        "poor_value_capture": merged["value_capture"].to_list() if "value_capture" in merged.columns else [None] * len(symbols),
        "declining_activity": [
            -v if v is not None else None
            for v in (merged["activity_change_30d"].to_list() if "activity_change_30d" in merged.columns else [None] * len(symbols))
        ],
    }

    n = len(symbols)
    result_scores: list[float] = []
    result_confidence: list[float] = []
    result_coverage: list[float] = []
    component_scores: dict[str, list[float | None]] = {k: [None] * n for k in _COMPONENT_WEIGHTS}

    for i in range(n):
        # Collect available components for this asset
        available: dict[str, tuple[float, float, float]] = {}  # name -> (raw, weight, percentile_score)

        for comp_name, raw_values in components.items():
            val = raw_values[i]
            if val is not None and np.isfinite(val):
                available[comp_name] = (val, _COMPONENT_WEIGHTS[comp_name], 0.0)

        coverage = len(available) / len(_COMPONENT_WEIGHTS) if _COMPONENT_WEIGHTS else 0.0

        if not available:
            result_scores.append(50.0)
            result_confidence.append(0.0)
            result_coverage.append(0.0)
            continue

        # Percentile rank each component cross-sectionally
        for comp_name in available:
            raw_vals_all = [
                v for v in components[comp_name] if v is not None and np.isfinite(v)
            ]
            if len(raw_vals_all) < 2:
                available[comp_name] = (available[comp_name][0], available[comp_name][1], 50.0)
                continue

            raw_val = available[comp_name][0]
            # Percentile rank: fraction of values <= this value
            rank = sum(1 for v in raw_vals_all if v <= raw_val) / len(raw_vals_all)
            available[comp_name] = (available[comp_name][0], available[comp_name][1], rank * 100)

        # Renormalize weights over available components
        total_weight = sum(w for _, w, _ in available.values())
        if total_weight < 1e-15:
            total_weight = 1.0

        # Weighted composite score
        composite = sum(
            (w / total_weight) * score
            for _, w, score in available.values()
        )

        # Confidence: based on coverage and data quality
        confidence = min(100, coverage * 100 * (1.0 if len(raw_vals_all) >= 30 else 0.7))

        result_scores.append(float(composite))
        result_confidence.append(float(confidence))
        result_coverage.append(float(coverage))

        # Record individual component scores
        for comp_name in _COMPONENT_WEIGHTS:
            if comp_name in available:
                component_scores[comp_name][i] = available[comp_name][2]

    # Build result DataFrame
    result_dict = {
        "symbol": symbols,
        "structural_short_score": result_scores,
        "confidence": result_confidence,
        "feature_coverage": result_coverage,
    }

    for comp_name, scores in component_scores.items():
        result_dict[f"score_{comp_name}"] = scores

    return pl.DataFrame(result_dict)
