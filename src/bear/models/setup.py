"""Setup Model — medium-horizon entry timing.

Steals from:
- Kiefer/Nowotny reversal: 8-10 week winners subsequently underperform
- Cross-sectional dispersion predicts when momentum breaks (Zhang 2026)
- Token age interactions (Fantazzini 2022)

Outputs:
  setup_score: 0-100 (higher = better short setup)
  expected_residual_return: 7/30/60/90d forward
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import polars as pl


def compute_setup_features(
    closes: np.ndarray,
    volumes: np.ndarray,
    timestamps: np.ndarray,
    btc_closes: np.ndarray | None = None,
) -> dict[str, np.ndarray]:
    """Compute medium-horizon setup features.

    These predict WHEN to short, not WHAT to short.
    """
    n = len(closes)
    features: dict[str, np.ndarray] = {}

    log_c = np.where(closes > 0, np.log(closes), np.nan)

    # --- Cross-sectional reversal (primary signal) ---
    for name, days in [("reversal_4w", 28), ("reversal_8w", 56),
                       ("reversal_10w", 70), ("reversal_12w", 84)]:
        shifted = np.roll(log_c, days)
        shifted[:days] = np.nan
        features[name] = np.where(
            np.isfinite(log_c) & np.isfinite(shifted),
            log_c - shifted,
            np.nan,
        )

    # --- Residual momentum (vs BTC) ---
    if btc_closes is not None and len(btc_closes) == n:
        btc_log = np.where(btc_closes > 0, np.log(btc_closes), np.nan)

        for name, days in [("residual_momentum_8w", 56), ("residual_momentum_12w", 84)]:
            asset_shifted = np.roll(log_c, days)
            btc_shifted = np.roll(btc_log, days)
            asset_shifted[:days] = np.nan
            btc_shifted[:days] = np.nan

            asset_ret = np.where(
                np.isfinite(log_c) & np.isfinite(asset_shifted),
                log_c - asset_shifted, np.nan,
            )
            btc_ret = np.where(
                np.isfinite(btc_log) & np.isfinite(btc_shifted),
                btc_log - btc_shifted, np.nan,
            )
            features[name] = np.where(
                np.isfinite(asset_ret) & np.isfinite(btc_ret),
                asset_ret - btc_ret,
                np.nan,
            )
    else:
        features["residual_momentum_8w"] = np.full(n, np.nan)
        features["residual_momentum_12w"] = np.full(n, np.nan)

    # --- Volatility ---
    returns = np.full(n, np.nan)
    for i in range(1, n):
        if closes[i] > 0 and closes[i - 1] > 0:
            returns[i] = np.log(closes[i] / closes[i - 1])

    for name, days in [("volatility_30d", 30), ("volatility_90d", 90)]:
        vol = np.full(n, np.nan)
        for i in range(days, n):
            w = returns[max(1, i - days + 1): i + 1]
            valid = w[np.isfinite(w)]
            if len(valid) > 5:
                vol[i] = np.std(valid) * np.sqrt(365)
        features[name] = vol

    # Volatility ratio (short-term vs long-term) — regime indicator
    features["vol_ratio_30d_90d"] = np.where(
        np.isfinite(features["volatility_30d"]) & np.isfinite(features["volatility_90d"])
        & (features["volatility_90d"] > 0),
        features["volatility_30d"] / features["volatility_90d"],
        np.nan,
    )

    # --- Price relative to moving averages ---
    for name, days in [("price_vs_sma_50", 50), ("price_vs_sma_200", 200)]:
        sma = np.full(n, np.nan)
        for i in range(days - 1, n):
            w = closes[max(0, i - days + 1): i + 1]
            valid = w[np.isfinite(w) & (w > 0)]
            sma[i] = np.mean(valid) if len(valid) > 0 else np.nan
        features[name] = np.where(
            np.isfinite(sma) & (sma > 0) & np.isfinite(closes) & (closes > 0),
            (closes - sma) / sma,
            np.nan,
        )

    # --- Days since listing (age proxy) ---
    features["days_since_first_price"] = np.arange(n, dtype=np.float64)

    # --- Volume trend ---
    vol_30d = np.full(n, np.nan)
    vol_90d = np.full(n, np.nan)
    for i in range(29, n):
        w = volumes[max(0, i - 29): i + 1]
        valid = w[np.isfinite(w) & (w > 0)]
        vol_30d[i] = np.mean(valid) if len(valid) > 0 else np.nan
    for i in range(89, n):
        w = volumes[max(0, i - 89): i + 1]
        valid = w[np.isfinite(w) & (w > 0)]
        vol_90d[i] = np.mean(valid) if len(valid) > 0 else np.nan

    features["volume_trend"] = np.where(
        np.isfinite(vol_30d) & np.isfinite(vol_90d) & (vol_90d > 0),
        vol_30d / vol_90d,
        np.nan,
    )

    return features


def compute_setup_score(
    features: dict[str, np.ndarray],
    weights: dict[str, float] | None = None,
) -> np.ndarray:
    """Compute setup score 0-100.

    Higher = better short entry setup (recent winner, elevated vol, etc.)
    """
    if weights is None:
        weights = {
            "reversal_8w_pct": 0.30,
            "reversal_10w_pct": 0.15,
            "residual_momentum_8w_pct": 0.15,
            "vol_ratio_pct": 0.10,
            "price_vs_sma_50_pct": 0.10,
            "volume_trend_pct": 0.10,
            "volatility_30d_pct": 0.10,
        }

    n = len(next(iter(features.values())))

    # Percentile rank features
    ranked = {}
    for key, vals in features.items():
        if not np.any(np.isfinite(vals)):
            ranked[key] = np.full(n, 50.0)
            continue
        valid = vals[np.isfinite(vals)]
        if len(valid) < 2:
            ranked[key] = np.full(n, 50.0)
        else:
            sorted_vals = np.sort(valid)
            ranks = np.searchsorted(sorted_vals, vals)
            ranked[key] = np.where(
                np.isfinite(vals),
                ranks / max(len(sorted_vals) - 1, 1) * 100,
                np.nan,
            )

    # Map to score components
    # NOTE: reversal_8w — HIGH return = recent winner = SHORT candidate
    # So high percentile = good short setup (no inversion needed)
    score_map = {
        "reversal_8w_pct": ranked.get("reversal_8w", np.full(n, 50.0)),
        "reversal_10w_pct": ranked.get("reversal_10w", np.full(n, 50.0)),
        "residual_momentum_8w_pct": ranked.get("residual_momentum_8w", np.full(n, 50.0)),
        "vol_ratio_pct": ranked.get("vol_ratio_30d_90d", np.full(n, 50.0)),
        "price_vs_sma_50_pct": ranked.get("price_vs_sma_50", np.full(n, 50.0)),
        "volume_trend_pct": ranked.get("volume_trend", np.full(n, 50.0)),
        "volatility_30d_pct": ranked.get("volatility_30d", np.full(n, 50.0)),
    }

    scores = np.zeros(n)
    weight_sum = np.zeros(n)

    for feat_name, weight in weights.items():
        if feat_name in score_map:
            vals = score_map[feat_name]
            mask = np.isfinite(vals)
            scores[mask] += weight * vals[mask]
            weight_sum[mask] += weight

    result = np.where(weight_sum > 0, scores / weight_sum * 100, 50.0)
    return np.clip(result, 0, 100)
