"""Basket construction and scoring for relative-value pair selection.

Implements hedge fit scoring (Section 26), CLONE_GAP calculation,
and total candidate scoring (Section 28).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from bear.features.downside import (
    compute_downside_correlation,
    compute_crash_correlation,
    compute_downside_beta,
    compute_crash_beta,
    compute_joint_downside_frequency,
)
from bear.features.correlation import compute_tail_dependence
from bear.features.factors import estimate_factor_exposures, compute_factor_distance
import polars as pl


@dataclass
class HedgeFitScore:
    """Composite hedge fit score per Section 26."""
    total: float
    correlation_component: float
    beta_component: float
    downside_component: float
    tail_component: float
    factor_component: float
    regime_component: float


@dataclass
class TotalCandidateScore:
    """Total candidate score per Section 28."""
    total: float
    hedge_fit: float
    structural_short: float
    carry: float
    execution: float
    squeeze_risk: float
    data_quality: float


def compute_hedge_fit_score(
    long_returns: pl.DataFrame,
    candidate_returns: pl.DataFrame,
    btc_returns: pl.DataFrame,
    mode: str = "relative_value",
    factor_returns: pl.DataFrame | None = None,
) -> HedgeFitScore:
    """Compute weighted composite hedge fit score per Section 26.

    Components:
        - Correlation: full-sample Pearson correlation
        - Beta: OLS beta during normal periods
        - Downside: correlation when BTC < 0
        - Tail: lower tail dependence (P(B<q|A<q))
        - Factor: factor exposure distance
        - Regime: crash beta during BTC bottom decile

    Args:
        long_returns: Return series for the long leg (timestamp + return col).
        candidate_returns: Return series for the candidate short.
        btc_returns: BTC return series (market regime filter).
        mode: 'risk_hedge', 'relative_value', or 'alpha_preserve'.
        factor_returns: Optional factor return series for factor distance.

    Returns:
        HedgeFitScore with total score (0-100) and component breakdown.
    """
    # Mode-specific weights
    if mode == "risk_hedge":
        weights = {
            "correlation": 0.10,
            "beta": 0.15,
            "downside": 0.25,
            "tail": 0.25,
            "factor": 0.10,
            "regime": 0.15,
        }
    elif mode == "relative_value":
        weights = {
            "correlation": 0.25,
            "beta": 0.15,
            "downside": 0.15,
            "tail": 0.10,
            "factor": 0.20,
            "regime": 0.15,
        }
    else:  # alpha_preserve
        weights = {
            "correlation": 0.10,
            "beta": 0.10,
            "downside": 0.15,
            "tail": 0.15,
            "factor": 0.35,
            "regime": 0.15,
        }

    # Compute components
    # 1. Correlation score
    merged = _align(long_returns, candidate_returns)
    if len(merged) < 10:
        return HedgeFitScore(total=0.0, correlation_component=0.0,
                             beta_component=0.0, downside_component=0.0,
                             tail_component=0.0, factor_component=0.0,
                             regime_component=0.0)

    long_col = _col(long_returns)
    cand_col = _col(candidate_returns)
    lv = merged[long_col].to_numpy()
    cv = merged[cand_col].to_numpy()

    corr = _safe_corr(lv, cv)
    corr_score = abs(corr) * 100 if np.isfinite(corr) else 50.0

    # 2. Beta score (beta near 1 = good for RV, near 0 = good for hedge)
    beta = _safe_beta(lv, cv)
    if mode == "risk_hedge":
        beta_score = max(0, 100 - abs(beta) * 100) if np.isfinite(beta) else 50.0
    else:
        beta_score = max(0, 100 - abs(beta - 1.0) * 100) if np.isfinite(beta) else 50.0

    # 3. Downside correlation
    down_corr = compute_downside_correlation(long_returns, candidate_returns, btc_returns)
    down_score = abs(down_corr) * 100 if np.isfinite(down_corr) else 50.0

    # 4. Tail dependence
    tail = compute_tail_dependence(long_returns, candidate_returns, quantile=0.1)
    tail_dep = tail["lower_tail"]
    if mode == "risk_hedge":
        # Lower tail dependence = better hedge
        tail_score = max(0, 100 - tail_dep * 100) if np.isfinite(tail_dep) else 50.0
    else:
        tail_score = (1 - tail_dep) * 100 if np.isfinite(tail_dep) else 50.0

    # 5. Factor distance
    if factor_returns is not None:
        exp_i = estimate_factor_exposures(long_returns, factor_returns)
        exp_l = estimate_factor_exposures(candidate_returns, factor_returns)
        from bear.features.factors import compute_factor_distance
        fdist = compute_factor_distance(exp_i, exp_l)
        # Invert: lower distance = higher score
        factor_score = max(0, 100 - fdist * 50)  # Scale: 0 distance = 100, 2.0 = 0
    else:
        factor_score = 50.0

    # 6. Regime score (crash beta)
    crash_beta = compute_crash_beta(long_returns, candidate_returns, btc_returns)
    if mode == "risk_hedge":
        # Lower crash beta = better crash hedge
        regime_score = max(0, 100 - abs(crash_beta) * 100) if np.isfinite(crash_beta) else 50.0
    else:
        regime_score = max(0, 100 - abs(crash_beta - 1.0) * 100) if np.isfinite(crash_beta) else 50.0

    # Weighted composite
    total = (
        weights["correlation"] * corr_score
        + weights["beta"] * beta_score
        + weights["downside"] * down_score
        + weights["tail"] * tail_score
        + weights["factor"] * factor_score
        + weights["regime"] * regime_score
    )

    return HedgeFitScore(
        total=total,
        correlation_component=corr_score,
        beta_component=beta_score,
        downside_component=down_score,
        tail_component=tail_score,
        factor_component=factor_score,
        regime_component=regime_score,
    )


def compute_clone_gap(
    hedge_fit: float,
    structural_short_long: float,
    structural_short_candidate: float,
) -> float:
    """Compute CLONE_GAP: how different the pair is structurally.

    CLONE_GAP = |structural_short_candidate - structural_short_long| * hedge_fit / 100

    High CLONE_GAP means the candidate is structurally worse (more short-worthy)
    than the long, which is ideal for a long-short trade. The hedge_fit term
    scales the gap by how well the pair hedges.

    Args:
        hedge_fit: Hedge fit score (0-100).
        structural_short_long: Structural short score for the long asset (0-100).
        structural_short_candidate: Structural short score for the candidate (0-100).

    Returns:
        CLONE_GAP score (0-100). Higher = better opportunity.
    """
    gap = abs(structural_short_candidate - structural_short_long)
    # Scale by hedge fit: perfect hedge * max gap = 100
    clone_gap = (gap * hedge_fit) / 100.0
    return float(min(100.0, max(0.0, clone_gap)))


def compute_total_score(
    hedge_fit: float,
    structural_short: float,
    carry: float,
    execution: float,
    squeeze_risk: float,
    data_quality: float,
) -> TotalCandidateScore:
    """Compute total candidate score per Section 28.

    Combines:
        - Hedge fit: how well the pair hedges (0-100)
        - Structural short: how short-worthy the candidate is (0-100)
        - Carry: funding carry for the short position (0-100)
        - Execution: estimated execution quality (0-100, 100 = low slippage)
        - Squeeze risk: how vulnerable the short is to squeezes (0-100, 100 = safe)
        - Data quality: confidence in the data (0-100)

    Args:
        hedge_fit: Hedge fit score (0-100).
        structural_short: Structural short score for the candidate (0-100).
        carry: Annualized carry score (can be negative; normalized to 0-100).
        execution: Execution quality score (0-100).
        squeeze_risk: Squeeze risk score (0-100, higher = safer).
        data_quality: Data quality/confidence score (0-100).

    Returns:
        TotalCandidateScore with total and component breakdown.
    """
    # Weights per Section 28
    weights = {
        "hedge_fit": 0.30,
        "structural_short": 0.25,
        "carry": 0.15,
        "execution": 0.10,
        "squeeze_risk": 0.10,
        "data_quality": 0.10,
    }

    # Normalize carry: negative carry is bad for shorts, positive is good
    # Map to 0-100: -50% = 0, 0% = 50, +50% = 100
    carry_normalized = max(0, min(100, 50 + carry * 100))

    total = (
        weights["hedge_fit"] * hedge_fit
        + weights["structural_short"] * structural_short
        + weights["carry"] * carry_normalized
        + weights["execution"] * execution
        + weights["squeeze_risk"] * squeeze_risk
        + weights["data_quality"] * data_quality
    )

    return TotalCandidateScore(
        total=total,
        hedge_fit=hedge_fit,
        structural_short=structural_short,
        carry=carry_normalized,
        execution=execution,
        squeeze_risk=squeeze_risk,
        data_quality=data_quality,
    )


def _align(*dfs: pl.DataFrame) -> pl.DataFrame:
    """Inner-join DataFrames on timestamp."""
    result = dfs[0]
    for df in dfs[1:]:
        result = result.join(df, on="timestamp", how="inner")
    return result.sort("timestamp")


def _col(df: pl.DataFrame) -> str:
    """Return first non-timestamp column."""
    cols = [c for c in df.columns if c != "timestamp"]
    return cols[0] if cols else ""


def _safe_corr(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 3 or np.std(a) < 1e-15 or np.std(b) < 1e-15:
        return np.nan
    return float(np.corrcoef(a, b)[0, 1])


def _safe_beta(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 3 or np.std(x) < 1e-15:
        return np.nan
    return float(np.mean((x - np.mean(x)) * (y - np.mean(y))) / np.var(x))
