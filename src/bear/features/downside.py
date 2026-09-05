"""Downside-specific correlation and beta features for relative-value trading."""

from __future__ import annotations

import polars as pl
import numpy as np


def _align_series(
    *dfs: pl.DataFrame,
) -> pl.DataFrame:
    """Align multiple DataFrames on timestamp, inner join."""
    if len(dfs) == 0:
        return pl.DataFrame()

    result = dfs[0]
    for df in dfs[1:]:
        result = result.join(df, on="timestamp", how="inner")
    return result.sort("timestamp")


def _resolve_col(df: pl.DataFrame) -> str:
    """Return the first non-timestamp column."""
    cols = [c for c in df.columns if c != "timestamp"]
    if not cols:
        raise ValueError(f"DataFrame has no return columns (only: {df.columns})")
    return cols[0]


def _safe_corr(a: np.ndarray, b: np.ndarray) -> float:
    """Pearson correlation returning NaN on degenerate input."""
    mask = np.isfinite(a) & np.isfinite(b)
    a_f, b_f = a[mask], b[mask]
    if len(a_f) < 3 or np.std(a_f) < 1e-15 or np.std(b_f) < 1e-15:
        return np.nan
    return float(np.corrcoef(a_f, b_f)[0, 1])


def _safe_beta(x: np.ndarray, y: np.ndarray) -> float:
    """OLS beta of y on x (slope), returning NaN on degenerate input."""
    mask = np.isfinite(x) & np.isfinite(y)
    x_f, y_f = x[mask], y[mask]
    if len(x_f) < 3 or np.std(x_f) < 1e-15:
        return np.nan
    cov_xy = np.mean((x_f - np.mean(x_f)) * (y_f - np.mean(y_f)))
    var_x = np.var(x_f)
    return float(cov_xy / var_x) if var_x > 1e-15 else np.nan


def compute_downside_correlation(
    returns_long: pl.DataFrame,
    returns_candidate: pl.DataFrame,
    btc_returns: pl.DataFrame,
) -> float:
    """Correlation between long and candidate when BTC returns are negative.

    This is the key metric for a long-short pair: if the candidate holds up
    when the market (BTC) is down, it provides genuine downside protection.

    Args:
        returns_long: Return series for the long leg.
        returns_candidate: Return series for the candidate short.
        btc_returns: BTC return series (market regime filter).

    Returns:
        Pearson correlation during BTC-down periods. NaN if insufficient data.
    """
    merged = _align_series(returns_long, returns_candidate, btc_returns)
    if len(merged) < 5:
        return np.nan

    long_col = _resolve_col(returns_long)
    cand_col = _resolve_col(returns_candidate)
    btc_col = _resolve_col(btc_returns)

    btc_down = merged[btc_col].to_numpy() < 0
    if btc_down.sum() < 3:
        return np.nan

    long_vals = merged[long_col].to_numpy()
    cand_vals = merged[cand_col].to_numpy()

    return _safe_corr(long_vals[btc_down], cand_vals[btc_down])


def compute_crash_correlation(
    returns_long: pl.DataFrame,
    returns_candidate: pl.DataFrame,
    btc_returns: pl.DataFrame,
    percentile: float = 0.1,
) -> float:
    """Correlation between long and candidate during BTC crash periods.

    A crash period is defined as the bottom `percentile` of BTC returns.
    This captures the most extreme market stress.

    Args:
        returns_long: Return series for the long leg.
        returns_candidate: Return series for the candidate short.
        btc_returns: BTC return series.
        percentile: Bottom percentile threshold (0.1 = bottom 10%).

    Returns:
        Pearson correlation during crash periods. NaN if insufficient data.
    """
    merged = _align_series(returns_long, returns_candidate, btc_returns)
    if len(merged) < 10:
        return np.nan

    long_col = _resolve_col(returns_long)
    cand_col = _resolve_col(returns_candidate)
    btc_col = _resolve_col(btc_returns)

    btc_vals = merged[btc_col].to_numpy()
    threshold = np.nanpercentile(btc_vals, percentile * 100)
    crash_mask = btc_vals <= threshold

    if crash_mask.sum() < 3:
        return np.nan

    long_vals = merged[long_col].to_numpy()
    cand_vals = merged[cand_col].to_numpy()

    return _safe_corr(long_vals[crash_mask], cand_vals[crash_mask])


def compute_downside_beta(
    returns_long: pl.DataFrame,
    returns_candidate: pl.DataFrame,
) -> float:
    """Beta of candidate returns during periods where long returns are negative.

    A candidate with low downside beta is a better hedge — it doesn't
    amplify losses when the long leg is losing.

    Args:
        returns_long: Return series for the long leg.
        returns_candidate: Return series for the candidate.

    Returns:
        OLS beta (candidate ~ long) during long-down periods. NaN if insufficient data.
    """
    merged = _align_series(returns_long, returns_candidate)
    if len(merged) < 5:
        return np.nan

    long_col = _resolve_col(returns_long)
    cand_col = _resolve_col(returns_candidate)

    long_vals = merged[long_col].to_numpy()
    cand_vals = merged[cand_col].to_numpy()

    down_mask = long_vals < 0
    if down_mask.sum() < 3:
        return np.nan

    return _safe_beta(long_vals[down_mask], cand_vals[down_mask])


def compute_crash_beta(
    returns_long: pl.DataFrame,
    returns_candidate: pl.DataFrame,
    btc_returns: pl.DataFrame,
    percentile: float = 0.1,
) -> float:
    """Beta of candidate returns during BTC crash periods.

    Crash beta measures how the candidate behaves in the worst market
    conditions. Low crash beta = better crash hedge.

    Args:
        returns_long: Return series for the long leg.
        returns_candidate: Return series for the candidate.
        btc_returns: BTC return series.
        percentile: Bottom percentile threshold for crash definition.

    Returns:
        OLS beta (candidate ~ long) during BTC crashes. NaN if insufficient data.
    """
    merged = _align_series(returns_long, returns_candidate, btc_returns)
    if len(merged) < 10:
        return np.nan

    long_col = _resolve_col(returns_long)
    cand_col = _resolve_col(returns_candidate)
    btc_col = _resolve_col(btc_returns)

    btc_vals = merged[btc_col].to_numpy()
    threshold = np.nanpercentile(btc_vals, percentile * 100)
    crash_mask = btc_vals <= threshold

    if crash_mask.sum() < 3:
        return np.nan

    long_vals = merged[long_col].to_numpy()
    cand_vals = merged[cand_col].to_numpy()

    return _safe_beta(long_vals[crash_mask], cand_vals[crash_mask])


def compute_joint_downside_frequency(
    returns_a: pl.DataFrame,
    returns_b: pl.DataFrame,
) -> float:
    """Fraction of time periods where both assets have negative returns.

    High joint downside frequency means the pair tends to fail together,
    which is bad for a long-short trade (both legs lose simultaneously).

    Args:
        returns_a: Return series for asset A.
        returns_b: Return series for asset B.

    Returns:
        Fraction of aligned periods where both returns are negative (0.0 to 1.0).
        NaN if insufficient data.
    """
    merged = _align_series(returns_a, returns_b)
    if len(merged) < 3:
        return np.nan

    col_a = _resolve_col(returns_a)
    col_b = _resolve_col(returns_b)

    a_vals = merged[col_a].to_numpy()
    b_vals = merged[col_b].to_numpy()

    both_down = np.isfinite(a_vals) & np.isfinite(b_vals) & (a_vals < 0) & (b_vals < 0)
    valid = np.isfinite(a_vals) & np.isfinite(b_vals)

    n_valid = valid.sum()
    if n_valid == 0:
        return np.nan

    return float(both_down.sum() / n_valid)
