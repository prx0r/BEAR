"""Pair discovery for relative-value trading.

Finds behavioral neighbors for a long asset across three modes:
risk_hedge, relative_value, and alpha_preserve.
"""

from __future__ import annotations

from dataclasses import dataclass

import polars as pl
import numpy as np


@dataclass
class CandidatePair:
    """A candidate pair for relative-value trading."""
    long_symbol: str
    candidate_symbol: str
    mode: str
    fit_score: float
    rank: int
    # Component scores
    correlation_score: float = 0.0
    beta_score: float = 0.0
    factor_distance_score: float = 0.0
    tail_dependence_score: float = 0.0
    sector_score: float = 0.0


# Mode-specific weight configurations per spec Section 26
_MODE_WEIGHTS: dict[str, dict[str, float]] = {
    "risk_hedge": {
        "correlation": 0.15,
        "beta": 0.20,
        "factor_distance": 0.25,
        "tail_dependence": 0.25,
        "sector": 0.05,
        "downside_corr": 0.10,
    },
    "relative_value": {
        "correlation": 0.25,
        "beta": 0.10,
        "factor_distance": 0.15,
        "tail_dependence": 0.10,
        "sector": 0.15,
        "downside_corr": 0.10,
        "structural_short_gap": 0.15,
    },
    "alpha_preserve": {
        "correlation": 0.10,
        "beta": 0.15,
        "factor_distance": 0.30,
        "tail_dependence": 0.15,
        "sector": 0.05,
        "downside_corr": 0.10,
        "momentum_divergence": 0.15,
    },
}


def find_nearest_neighbors(
    long_returns: pl.DataFrame,
    all_returns: pl.DataFrame,
    taxonomy: dict[str, str],
    mode: str = "relative_value",
    top_k: int = 10,
    min_history: int = 30,
) -> list[CandidatePair]:
    """Find behavioral neighbors for a long asset.

    Args:
        long_returns: Return series for the long asset (timestamp + return col).
        all_returns: Return series for all assets (timestamp + return cols).
        taxonomy: Mapping of symbol -> sector name.
        mode: One of 'risk_hedge', 'relative_value', 'alpha_preserve'.
        top_k: Number of top candidates to return.
        min_history: Minimum aligned observations required.

    Returns:
        List of CandidatePair sorted by fit_score descending.
    """
    if mode not in _MODE_WEIGHTS:
        raise ValueError(f"mode must be one of {list(_MODE_WEIGHTS.keys())}, got '{mode}'")

    weights = _MODE_WEIGHTS[mode]

    long_cols = [c for c in long_returns.columns if c != "timestamp"]
    if not long_cols:
        return []
    long_sym = long_cols[0]

    all_asset_cols = [c for c in all_returns.columns if c != "timestamp"]
    candidates = [c for c in all_asset_cols if c != long_sym]

    if not candidates:
        return []

    # Merge long with each candidate
    merged = (
        long_returns.select(["timestamp", long_sym])
        .join(all_returns.select(["timestamp"] + candidates), on="timestamp", how="inner")
        .sort("timestamp")
    )

    if len(merged) < min_history:
        return []

    long_vals = merged[long_sym].to_numpy().astype(np.float64)
    long_sector = taxonomy.get(long_sym, "unknown")

    candidate_scores: list[CandidatePair] = []

    for cand_sym in candidates:
        cand_vals = merged[cand_sym].to_numpy().astype(np.float64)

        # Filter valid observations
        valid = np.isfinite(long_vals) & np.isfinite(cand_vals)
        if valid.sum() < min_history:
            continue

        lv = long_vals[valid]
        cv = cand_vals[valid]

        # Correlation score (higher absolute corr = higher score, capped at 1.0)
        corr = _safe_corr(lv, cv)
        correlation_score = abs(corr) * 100 if np.isfinite(corr) else 50.0

        # Beta score: prefer beta near 1.0 for relative_value, near 0 for risk_hedge
        beta = _safe_beta(lv, cv)
        if mode == "risk_hedge":
            # Lower beta = better hedge
            beta_score = max(0, 100 - abs(beta) * 100) if np.isfinite(beta) else 50.0
        elif mode == "relative_value":
            # Beta near 1 = same market exposure (good for RV)
            beta_score = max(0, 100 - abs(beta - 1.0) * 100) if np.isfinite(beta) else 50.0
        else:
            # alpha_preserve: moderate beta
            beta_score = max(0, 100 - abs(beta) * 50) if np.isfinite(beta) else 50.0

        # Factor distance score (inverted: lower distance = higher score)
        # Approximate using correlation as proxy
        factor_distance_score = correlation_score  # Simplified

        # Tail dependence: lower tail dependence = better for risk_hedge
        lower_tail = _safe_tail_dependence(lv, cv, quantile=0.1)
        if mode == "risk_hedge":
            tail_dependence_score = max(0, 100 - lower_tail * 100) if np.isfinite(lower_tail) else 50.0
        else:
            tail_dependence_score = (1 - lower_tail) * 100 if np.isfinite(lower_tail) else 50.0

        # Sector score
        cand_sector = taxonomy.get(cand_sym, "unknown")
        if mode == "risk_hedge":
            # Same sector = better hedge
            sector_score = 90.0 if cand_sector == long_sector else 40.0
        elif mode == "relative_value":
            # Same sector preferred (RV within sector)
            sector_score = 80.0 if cand_sector == long_sector else 50.0
        else:
            # alpha_preserve: different sector = more alpha
            sector_score = 40.0 if cand_sector == long_sector else 80.0

        # Downside correlation score
        down_mask = lv < 0
        if down_mask.sum() >= 5:
            downside_corr = _safe_corr(lv[down_mask], cv[down_mask])
            downside_score = abs(downside_corr) * 100 if np.isfinite(downside_corr) else 50.0
        else:
            downside_score = 50.0

        # Weighted composite
        available_weights = {}
        score_map = {
            "correlation": correlation_score,
            "beta": beta_score,
            "factor_distance": factor_distance_score,
            "tail_dependence": tail_dependence_score,
            "sector": sector_score,
            "downside_corr": downside_score,
        }

        total_w = 0.0
        weighted_sum = 0.0
        for w_name, w_val in weights.items():
            if w_name in score_map:
                available_weights[w_name] = w_val
                total_w += w_val

        if total_w > 0:
            for w_name, w_val in available_weights.items():
                weighted_sum += (w_val / total_w) * score_map.get(w_name, 50.0)

        fit_score = weighted_sum

        candidate_scores.append(CandidatePair(
            long_symbol=long_sym,
            candidate_symbol=cand_sym,
            mode=mode,
            fit_score=fit_score,
            rank=0,
            correlation_score=correlation_score,
            beta_score=beta_score,
            factor_distance_score=factor_distance_score,
            tail_dependence_score=tail_dependence_score,
            sector_score=sector_score,
        ))

    # Sort and rank
    candidate_scores.sort(key=lambda c: c.fit_score, reverse=True)
    for i, c in enumerate(candidate_scores[:top_k]):
        c.rank = i + 1

    return candidate_scores[:top_k]


def _safe_corr(a: np.ndarray, b: np.ndarray) -> float:
    """Pearson correlation returning NaN on degenerate input."""
    if len(a) < 3 or np.std(a) < 1e-15 or np.std(b) < 1e-15:
        return np.nan
    return float(np.corrcoef(a, b)[0, 1])


def _safe_beta(x: np.ndarray, y: np.ndarray) -> float:
    """OLS beta of y on x."""
    if len(x) < 3 or np.std(x) < 1e-15:
        return np.nan
    cov_xy = np.mean((x - np.mean(x)) * (y - np.mean(y)))
    var_x = np.var(x)
    return float(cov_xy / var_x) if var_x > 1e-15 else np.nan


def _safe_tail_dependence(a: np.ndarray, b: np.ndarray, quantile: float = 0.1) -> float:
    """Lower tail dependence P(B < q | A < q)."""
    if len(a) < 10:
        return np.nan

    a_q = np.percentile(a, quantile * 100)
    mask = a <= a_q
    if mask.sum() == 0:
        return np.nan

    b_q = np.percentile(b, quantile * 100)
    return float((b[mask] <= b_q).mean())
