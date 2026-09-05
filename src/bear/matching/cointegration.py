"""Cointegration testing for pair hedging.

Engle-Granger two-step method and spread analysis for relative-value
pair construction.
"""

from __future__ import annotations

import structlog
import numpy as np
from numpy.linalg import lstsq
from scipy import stats

logger = structlog.get_logger()


def test_cointegration(
    long_prices: pl.Series,
    candidate_prices: pl.Series,
) -> dict:
    """Engle-Granger cointegration test.

    Steps:
        1. Regress long on candidate to get residuals (hedge ratio).
        2. ADF test on residuals for stationarity.
        3. Estimate half-life from AR(1) on spread.

    Args:
        long_prices: Price series for the long leg.
        candidate_prices: Price series for the candidate short.

    Returns:
        Dict with keys:
            - cointegrated: bool (p_value < 0.05)
            - p_value: float (ADF test p-value)
            - hedge_ratio: float (beta from OLS)
            - half_life: float (days, from AR(1) on spread)
            - adf_stat: float (ADF test statistic)
    """
    result = {
        "cointegrated": False,
        "p_value": 1.0,
        "hedge_ratio": 0.0,
        "half_life": 0.0,
        "adf_stat": 0.0,
    }

    log_long = np.log(long_prices.to_numpy().astype(np.float64))
    log_cand = np.log(candidate_prices.to_numpy().astype(np.float64))

    valid = np.isfinite(log_long) & np.isfinite(log_cand)
    log_long = log_long[valid]
    log_cand = log_cand[valid]

    if len(log_long) < 30:
        return result

    X = np.column_stack([np.ones(len(log_cand)), log_cand])
    coefs = lstsq(X, log_long, rcond=None)[0]
    intercept, beta = coefs[0], coefs[1]

    result["hedge_ratio"] = float(beta)

    spread = log_long - beta * log_cand - intercept

    adf_stat, p_value = _adf_test(spread)
    result["adf_stat"] = float(adf_stat)
    result["p_value"] = float(p_value)
    result["cointegrated"] = p_value < 0.05

    half_life = _estimate_half_life(spread)
    result["half_life"] = float(half_life)

    return result


def compute_spread_features(
    long_prices: pl.Series,
    candidate_prices: pl.Series,
) -> dict:
    """Spread analysis for a pair.

    Args:
        long_prices: Price series for the long leg.
        candidate_prices: Price series for the candidate short.

    Returns:
        Dict with keys:
            - spread_zscore: current z-score of spread
            - spread_vol: annualized volatility of spread
            - half_life: mean reversion half-life in days
            - mean_reversion_speed: speed of mean reversion (phi in AR(1))
    """
    log_long = np.log(long_prices.to_numpy().astype(np.float64))
    log_cand = np.log(candidate_prices.to_numpy().astype(np.float64))

    valid = np.isfinite(log_long) & np.isfinite(log_cand)
    log_long = log_long[valid]
    log_cand = log_cand[valid]

    if len(log_long) < 30:
        return {
            "spread_zscore": 0.0,
            "spread_vol": 0.0,
            "half_life": 0.0,
            "mean_reversion_speed": 0.0,
        }

    X = np.column_stack([np.ones(len(log_cand)), log_cand])
    coefs = lstsq(X, log_long, rcond=None)[0]
    beta = coefs[1]

    spread = log_long - beta * log_cand - coefs[0]

    spread_mean = np.mean(spread)
    spread_std = np.std(spread)
    spread_vol = float(spread_std * np.sqrt(365)) if spread_std > 0 else 0.0

    current_z = (spread[-1] - spread_mean) / spread_std if spread_std > 1e-15 else 0.0

    half_life = _estimate_half_life(spread)
    phi = _ar1_coefficient(spread)

    return {
        "spread_zscore": float(current_z),
        "spread_vol": spread_vol,
        "half_life": float(half_life),
        "mean_reversion_speed": float(phi),
    }


def _adf_test(spread: np.ndarray) -> tuple[float, float]:
    """Augmented Dickey-Fuller test on a spread series.

    Returns (test_statistic, p_value). P-value is approximate using
    MacKinnon (1994) critical values for intercept-only model.
    """
    n = len(spread)
    if n < 20:
        return 0.0, 1.0

    y = np.diff(spread)
    y_lag = spread[:-1]

    X = np.column_stack([np.ones(n - 1), y_lag])
    coefs = lstsq(X, y, rcond=None)[0]
    residuals = y - X @ coefs

    se = np.sqrt(np.sum(residuals ** 2) / (n - 3))
    se_beta = se / np.sqrt(np.sum((y_lag - np.mean(y_lag)) ** 2))

    if se_beta < 1e-15:
        return 0.0, 1.0

    adf_stat = coefs[1] / se_beta

    p_value = _mac_kinnon_pvalue(adf_stat, n, model="const")

    return float(adf_stat), float(p_value)


def _mac_kinnon_pvalue(adf_stat: float, n: int, model: str = "const") -> float:
    """Approximate p-value using MacKinnon (1994) response surface.

    For intercept-only model (const).
    """
    tau_inf = -1.95 if model == "const" else -2.89
    tau_1 = -1.95 if model == "const" else -2.89
    tau_2 = -1.95 if model == "const" else -2.89

    critical_values = {
        "const": {
            0.01: -3.43,
            0.05: -2.86,
            0.10: -2.57,
        },
    }

    cv = critical_values.get(model, critical_values["const"])

    if adf_stat < cv[0.01]:
        return 0.01
    elif adf_stat < cv[0.05]:
        return 0.05
    elif adf_stat < cv[0.10]:
        return 0.10

    z_score = (adf_stat - tau_inf) / max(0.5, abs(tau_inf))
    p_value = 0.5 * (1 + np.tanh(z_score))

    return float(min(1.0, max(0.001, p_value)))


def _estimate_half_life(spread: np.ndarray) -> float:
    """Estimate half-life of mean reversion from AR(1) model.

    spread_t = phi * spread_{t-1} + epsilon
    half_life = -log(2) / log(phi)
    """
    if len(spread) < 10:
        return 0.0

    phi = _ar1_coefficient(spread)

    if phi <= 0 or phi >= 1:
        return 0.0

    half_life = -np.log(2) / np.log(phi)
    return float(max(0, half_life))


def _ar1_coefficient(spread: np.ndarray) -> float:
    """Estimate AR(1) coefficient phi."""
    if len(spread) < 10:
        return 0.0

    y = spread[1:]
    X = np.column_stack([np.ones(len(y)), spread[:-1]])
    coefs = lstsq(X, y, rcond=None)[0]
    return float(coefs[1])
