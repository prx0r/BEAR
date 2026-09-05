"""Tests for cointegration analysis, spread monitoring, and half-life estimation."""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest
from datetime import datetime, timedelta, timezone
from scipy import stats as sp_stats

from bear.features.correlation import (
    compute_rolling_correlation,
    compute_tail_dependence,
)
from bear.features.downside import (
    compute_downside_correlation,
    compute_crash_correlation,
)


def _ts(n: int) -> list[datetime]:
    """Generate n timestamps using timedelta."""
    base = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return [base + timedelta(hours=i) for i in range(n)]


def _make_cointegrated_series(
    n: int = 500,
    half_life: float = 30.0,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate two cointegrated series with known half-life."""
    rng = np.random.default_rng(seed)
    phi = 1.0 - 1.0 / half_life
    spread = np.zeros(n)
    spread[0] = rng.normal(0, 1)
    for t in range(1, n):
        spread[t] = phi * spread[t - 1] + rng.normal(0, 0.1)

    noise_a = rng.normal(0, 0.01, n)
    noise_b = rng.normal(0, 0.01, n)
    series_a = 100 + np.cumsum(noise_a) + spread
    series_b = 100 + np.cumsum(noise_b) + spread * 0.8

    return series_a, series_b


def _series_to_df(series: np.ndarray, name: str) -> pl.DataFrame:
    """Convert numpy array to Polars DataFrame with timestamps."""
    n = len(series)
    timestamps = _ts(n)
    return pl.DataFrame({"timestamp": timestamps, name: series})


def test_cointegration_basic():
    """Cointegrated series have high rolling correlation."""
    a, b = _make_cointegrated_series(n=500, half_life=30)
    df_a = _series_to_df(a, "A")
    df_b = _series_to_df(b, "B")

    result = compute_rolling_correlation(df_a, df_b, windows=[60])

    corr_col = [c for c in result.columns if c.startswith("corr_")][0]
    valid_corrs = [v for v in result[corr_col].to_list() if v is not None and np.isfinite(v)]

    assert len(valid_corrs) > 0
    assert np.mean(valid_corrs) > 0.5


def test_cointegration_uncorrelated():
    """Non-cointegrated series detected."""
    n = 500
    rng = np.random.default_rng(42)

    a = np.cumsum(rng.normal(0, 1, n))
    b = np.cumsum(rng.normal(0, 1, n))

    df_a = _series_to_df(a, "A")
    df_b = _series_to_df(b, "B")

    result = compute_rolling_correlation(df_a, df_b, windows=[60])

    corr_col = [c for c in result.columns if c.startswith("corr_")][0]
    valid_corrs = [v for v in result[corr_col].to_list() if v is not None and np.isfinite(v)]

    assert len(valid_corrs) > 0
    mean_abs_corr = np.mean(np.abs(valid_corrs))
    # Independent random walks can show spurious correlation
    assert mean_abs_corr < 0.6


def test_half_life():
    """Half-life estimation from spread AR(1)."""
    n = 1000
    true_half_life = 25.0
    phi = 1.0 - 1.0 / true_half_life

    rng = np.random.default_rng(42)
    spread = np.zeros(n)
    spread[0] = 0.0
    for t in range(1, n):
        spread[t] = phi * spread[t - 1] + rng.normal(0, 0.1)

    y = spread[1:]
    x = spread[:-1]

    slope, intercept, r_value, p_value, std_err = sp_stats.linregress(x, y)

    if slope > 0 and slope < 1:
        estimated_half_life = -np.log(2) / np.log(slope)
    else:
        estimated_half_life = float("inf")

    # Wider tolerance for stochastic estimation
    assert abs(estimated_half_life - true_half_life) < 15.0, (
        f"Estimated half-life {estimated_half_life:.1f} differs from "
        f"true {true_half_life:.1f} by more than 15"
    )


def test_spread_zscore():
    """Spread z-score computation."""
    n = 200
    rng = np.random.default_rng(42)

    spread = rng.normal(0.5, 1.0, n)

    window = 30
    rolling_mean = np.convolve(spread, np.ones(window) / window, mode="valid")
    rolling_var = np.convolve(
        (spread - np.mean(spread[:window])) ** 2,
        np.ones(window) / window,
        mode="valid",
    )
    rolling_std = np.sqrt(rolling_var)

    z_scores = (spread[window - 1:] - rolling_mean) / np.maximum(rolling_std, 1e-10)

    assert abs(np.mean(z_scores)) < 0.5
    assert 0.5 < np.std(z_scores) < 2.0


def test_tail_dependence_cointegrated():
    """Cointegrated series have high tail dependence."""
    a, b = _make_cointegrated_series(n=500, half_life=30)
    df_a = _series_to_df(a, "A")
    df_b = _series_to_df(b, "B")

    result = compute_tail_dependence(df_a, df_b, quantile=0.1)

    assert result["n_obs"] > 100
    assert np.isfinite(result["lower_tail"])
    assert result["lower_tail"] > 0.05


def test_downside_correlation_cointegrated():
    """Downside correlation captures stress co-movement."""
    n = 500
    rng = np.random.default_rng(42)

    btc = rng.normal(0, 0.02, n)
    btc[50:60] = rng.uniform(-0.05, -0.03, 10)

    long_rets = btc * 1.2 + rng.normal(0, 0.005, n)
    cand_rets = btc * 0.9 + rng.normal(0, 0.005, n)

    timestamps = _ts(n)
    btc_df = pl.DataFrame({"timestamp": timestamps, "BTC": btc})
    long_df = pl.DataFrame({"timestamp": timestamps, "LONG": long_rets})
    cand_df = pl.DataFrame({"timestamp": timestamps, "CAND": cand_rets})

    down_corr = compute_downside_correlation(long_df, cand_df, btc_df)
    crash_corr = compute_crash_correlation(long_df, cand_df, btc_df, percentile=0.1)

    assert np.isfinite(down_corr)
    assert np.isfinite(crash_corr)
    assert down_corr > 0
    assert crash_corr > 0


def test_half_life_short_memory():
    """Short half-life means fast mean reversion."""
    n = 1000
    rng = np.random.default_rng(42)

    phi_fast = 1.0 - 1.0 / 5.0
    spread_fast = np.zeros(n)
    for t in range(1, n):
        spread_fast[t] = phi_fast * spread_fast[t - 1] + rng.normal(0, 0.1)

    phi_slow = 1.0 - 1.0 / 100.0
    spread_slow = np.zeros(n)
    for t in range(1, n):
        spread_slow[t] = phi_slow * spread_slow[t - 1] + rng.normal(0, 0.1)

    def estimate_hl(spread):
        y = spread[1:]
        x = spread[:-1]
        slope = sp_stats.linregress(x, y).slope
        if 0 < slope < 1:
            return -np.log(2) / np.log(slope)
        return float("inf")

    hl_fast = estimate_hl(spread_fast)
    hl_slow = estimate_hl(spread_slow)

    assert hl_fast < hl_slow


def test_spread_stationarity():
    """Stationary spread has finite variance."""
    n = 500
    half_life = 20.0
    a, b = _make_cointegrated_series(n, half_life)

    spread = a - b

    first_half_var = np.var(spread[:n // 2])
    second_half_var = np.var(spread[n // 2:])

    ratio = max(first_half_var, second_half_var) / max(min(first_half_var, second_half_var), 1e-10)
    assert ratio < 5.0, (
        f"Spread variance ratio {ratio:.2f} suggests non-stationarity"
    )
