"""Structural Decay Model — expected structural underperformance.

Steals from:
- Guo 2026: FDV overhang + 12-week dilution → 25-32% LS spread
- Kiefer/Nowotny: 8-week discretionary issuance → 1.39 Sharpe
- Management Science 2026: active-address valuation

Outputs:
  structural_decay_score: 0-100 (higher = more structurally doomed)
  fdv_overhang: FDV / market_cap
  dilution_12w: log(circ_t / circ_{t-84d})
  dilution_acceleration: dilution_4w - dilution_12w/3
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import polars as pl


def compute_structural_decay_features(
    closes: np.ndarray,
    volumes: np.ndarray,
    timestamps: np.ndarray,
    supply_data: dict[str, np.ndarray] | None = None,
    fundamentals: dict[str, np.ndarray] | None = None,
) -> dict[str, np.ndarray]:
    """Compute structural decay features.

    Args:
        closes: daily close prices
        volumes: daily volumes
        timestamps: daily timestamps (ms)
        supply_data: optional dict with keys:
            circulating_supply, total_supply, max_supply
        fundamentals: optional dict with keys:
            active_addresses, revenue, fees, tvl

    Returns: dict of feature arrays
    """
    n = len(closes)
    features: dict[str, np.ndarray] = {}

    # --- FDV Overhang ---
    if supply_data and "circulating_supply" in supply_data:
        circ = supply_data["circulating_supply"]
        total = supply_data.get("total_supply", circ)
        max_s = supply_data.get("max_supply")

        denominator = np.where(
            np.isfinite(max_s) & (max_s > 0), max_s,
            np.where(np.isfinite(total) & (total > 0), total, circ),
        )
        features["fdv_overhang"] = np.where(
            np.isfinite(circ) & (circ > 0) & np.isfinite(denominator) & (denominator > 0),
            denominator / circ,
            np.nan,
        )
    else:
        features["fdv_overhang"] = np.full(n, np.nan)

    # --- Multi-horizon dilution ---
    if supply_data and "circulating_supply" in supply_data:
        circ = supply_data["circulating_supply"]
        log_circ = np.where(circ > 0, np.log(circ), np.nan)

        for name, days in [("dilution_2w", 14), ("dilution_4w", 28),
                           ("dilution_8w", 56), ("dilution_12w", 84),
                           ("dilution_26w", 182)]:
            shifted = np.roll(log_circ, days)
            shifted[:days] = np.nan
            features[name] = np.where(
                np.isfinite(log_circ) & np.isfinite(shifted),
                log_circ - shifted,
                np.nan,
            )

        # Dilution acceleration: recent dilution rate accelerating
        d4w = features.get("dilution_4w", np.full(n, np.nan))
        d12w = features.get("dilution_12w", np.full(n, np.nan))
        features["dilution_acceleration"] = np.where(
            np.isfinite(d4w) & np.isfinite(d12w),
            d4w - d12w / 3.0,
            np.nan,
        )

        # Discretionary vs programmatic split (proxy: volatility of supply changes)
        # Higher variance in supply changes = more discretionary
        supply_returns = np.full(n, np.nan)
        for i in range(1, n):
            if circ[i] > 0 and circ[i - 1] > 0:
                supply_returns[i] = np.log(circ[i] / circ[i - 1])

        vol_supply_30d = np.full(n, np.nan)
        for i in range(29, n):
            w = supply_returns[max(1, i - 29): i + 1]
            valid = w[np.isfinite(w)]
            vol_supply_30d[i] = np.std(valid) if len(valid) > 5 else np.nan

        features["discretionary_issuance_proxy"] = vol_supply_30d
    else:
        for name in ["dilution_2w", "dilution_4w", "dilution_8w",
                      "dilution_12w", "dilution_26w", "dilution_acceleration",
                      "discretionary_issuance_proxy"]:
            features[name] = np.full(n, np.nan)

    # --- Active-address valuation (ghost valuation) ---
    if fundamentals and "active_addresses" in fundamentals:
        active = fundamentals["active_addresses"]
        # We need market cap — use price * supply as proxy
        if supply_data and "circulating_supply" in supply_data:
            mcap = closes * supply_data["circulating_supply"]
            features["ghost_valuation"] = np.where(
                np.isfinite(mcap) & (mcap > 0) & np.isfinite(active) & (active > 0),
                mcap / active,
                np.nan,
            )
        else:
            features["ghost_valuation"] = np.full(n, np.nan)
    else:
        features["ghost_valuation"] = np.full(n, np.nan)

    # --- Momentum decay ---
    # Weak relative momentum (underperforming = structurally bad)
    for name, days in [("momentum_30d", 30), ("momentum_90d", 90)]:
        log_c = np.where(closes > 0, np.log(closes), np.nan)
        shifted = np.roll(log_c, days)
        shifted[:days] = np.nan
        features[name] = np.where(
            np.isfinite(log_c) & np.isfinite(shifted),
            log_c - shifted,
            np.nan,
        )

    return features


def compute_structural_decay_score(
    features: dict[str, np.ndarray],
    weights: dict[str, float] | None = None,
) -> np.ndarray:
    """Compute composite structural decay score 0-100.

    Higher = more structurally doomed = better short candidate.
    """
    if weights is None:
        weights = {
            "fdv_overhang_pct": 0.20,
            "dilution_12w_pct": 0.20,
            "dilution_acceleration_pct": 0.10,
            "discretionary_issuance_pct": 0.10,
            "ghost_valuation_pct": 0.15,
            "momentum_30d_inv": 0.10,
            "momentum_90d_inv": 0.10,
            "volume_death_pct": 0.05,
        }

    n = len(next(iter(features.values())))

    # Cross-sectional percentile rank each feature
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
            # Percentile rank
            ranks = np.searchsorted(sorted_vals, vals)
            ranked[key] = np.where(
                np.isfinite(vals),
                ranks / max(len(sorted_vals) - 1, 1) * 100,
                np.nan,
            )

    # Map feature names to percentile versions
    score_map = {
        "fdv_overhang_pct": ranked.get("fdv_overhang", np.full(n, 50.0)),
        "dilution_12w_pct": ranked.get("dilution_12w", np.full(n, 50.0)),
        "dilution_acceleration_pct": ranked.get("dilution_acceleration", np.full(n, 50.0)),
        "discretionary_issuance_pct": ranked.get("discretionary_issuance_proxy", np.full(n, 50.0)),
        "ghost_valuation_pct": ranked.get("ghost_valuation", np.full(n, 50.0)),
        "momentum_30d_inv": 100 - ranked.get("momentum_30d", np.full(n, 50.0)),
        "momentum_90d_inv": 100 - ranked.get("momentum_90d", np.full(n, 50.0)),
        "volume_death_pct": ranked.get("liquidity_death_composite", np.full(n, 50.0)),
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
