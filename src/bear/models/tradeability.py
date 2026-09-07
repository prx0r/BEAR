"""Tradeability Model — fast entry/exit decision.

Steals from:
- 15-min crypto reversal (arXiv 2026): taker flow exhaustion timer
- Liquidation cascade heterogeneity (arXiv 2026): no universal squeeze indicator
- Crypto carry (Management Science 2026): funding is carry, not death

Outputs:
  tradeability_signal: ENTER / WAIT / VETO
  crowd_score: 0-100 (higher = more crowded short)
  carry_score: expected funding carry
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

import numpy as np
import polars as pl


class TradeabilitySignal(Enum):
    ENTER = "ENTER"
    WAIT = "WAIT"
    VETO = "VETO"


@dataclass
class TradeabilityResult:
    """Result of tradeability assessment."""
    signal: TradeabilitySignal
    crowd_score: float  # 0-100, higher = more crowded
    carry_score: float  # expected annualized carry
    veto_reasons: list[str]
    entry_urgency: float  # 0-1, higher = enter now


def compute_tradeability_features(
    closes: np.ndarray,
    volumes: np.ndarray,
    funding_rates: np.ndarray | None = None,
    oi_data: np.ndarray | None = None,
    btc_closes: np.ndarray | None = None,
) -> dict[str, np.ndarray]:
    """Compute tradeability features (fast horizon).

    These determine ENTER/WAIT/VETO for a candidate.
    """
    n = len(closes)
    features: dict[str, np.ndarray] = {}

    # --- Crowding signals ---
    # Short-term reversal (15m/1h proxy using daily)
    # Strong recent rally = potentially crowded long = good short entry
    returns_1d = np.full(n, np.nan)
    for i in range(1, n):
        if closes[i] > 0 and closes[i - 1] > 0:
            returns_1d[i] = np.log(closes[i] / closes[i - 1])

    # Recent return burst (3d, 7d)
    for name, days in [("return_3d", 3), ("return_7d", 7)]:
        shifted = np.roll(returns_1d, days)
        shifted[:days] = 0
        features[name] = np.nancumsum(returns_1d) - np.nancumsum(shifted)

    # Actually compute properly
    log_c = np.where(closes > 0, np.log(closes), np.nan)
    for name, days in [("return_3d", 3), ("return_7d", 7)]:
        shifted = np.roll(log_c, days)
        shifted[:days] = np.nan
        features[name] = np.where(
            np.isfinite(log_c) & np.isfinite(shifted),
            log_c - shifted,
            np.nan,
        )

    # --- Volume climax ---
    vol_7d = np.full(n, np.nan)
    vol_30d = np.full(n, np.nan)
    for i in range(6, n):
        w = volumes[max(0, i - 6): i + 1]
        valid = w[np.isfinite(w) & (w > 0)]
        vol_7d[i] = np.mean(valid) if len(valid) > 0 else np.nan
    for i in range(29, n):
        w = volumes[max(0, i - 29): i + 1]
        valid = w[np.isfinite(w) & (w > 0)]
        vol_30d[i] = np.mean(valid) if len(valid) > 0 else np.nan

    features["volume_climax"] = np.where(
        np.isfinite(vol_7d) & np.isfinite(vol_30d) & (vol_30d > 0),
        vol_7d / vol_30d,
        np.nan,
    )

    # --- Funding (if available) ---
    if funding_rates is not None and len(funding_rates) == n:
        features["funding_rate"] = funding_rates
        features["funding_abs"] = np.abs(funding_rates)
        features["funding_negative"] = np.where(funding_rates < 0, -funding_rates, 0.0)
    else:
        features["funding_rate"] = np.full(n, np.nan)
        features["funding_abs"] = np.full(n, np.nan)
        features["funding_negative"] = np.full(n, np.nan)

    # --- OI signals (if available) ---
    if oi_data is not None and len(oi_data) == n:
        oi_change_7d = np.full(n, np.nan)
        for i in range(7, n):
            if oi_data[i - 7] > 0:
                oi_change_7d[i] = (oi_data[i] - oi_data[i - 7]) / oi_data[i - 7]
        features["oi_change_7d"] = oi_change_7d

        # OI / ADV proxy (using volume)
        features["oi_to_volume"] = np.where(
            np.isfinite(oi_data) & np.isfinite(vol_30d) & (vol_30d > 0),
            oi_data / vol_30d,
            np.nan,
        )
    else:
        features["oi_change_7d"] = np.full(n, np.nan)
        features["oi_to_volume"] = np.full(n, np.nan)

    # --- BTC regime ---
    if btc_closes is not None and len(btc_closes) == n:
        btc_log = np.where(btc_closes > 0, np.log(btc_closes), np.nan)
        btc_30d = np.full(n, np.nan)
        for i in range(29, n):
            if np.isfinite(btc_log[i]) and np.isfinite(btc_log[i - 29]):
                btc_30d[i] = btc_log[i] - btc_log[i - 29]
        features["btc_30d_return"] = btc_30d
    else:
        features["btc_30d_return"] = np.full(n, np.nan)

    # --- Volatility regime ---
    vol_30d_arr = np.full(n, np.nan)
    for i in range(29, n):
        w = returns_1d[max(1, i - 29): i + 1]
        valid = w[np.isfinite(w)]
        if len(valid) > 5:
            vol_30d_arr[i] = np.std(valid) * np.sqrt(365)
    features["realized_vol_30d"] = vol_30d_arr

    return features


def assess_tradeability(
    features: dict[str, np.ndarray],
    index: int,
    min_volume_usd: float = 50_000,
    max_funding_penalty: float = -0.005,
    max_oi_adv_ratio: float = 3.0,
) -> TradeabilityResult:
    """Assess tradeability at a specific time index.

    Hard vetoes (per liquidation literature — no universal squeeze indicator):
      1. Funding extremely negative (shorts paying too much)
      2. OI/ADV extreme (crowded)
      3. Positive residual momentum (squeeze risk)
      4. BTC rallying hard (regime filter)
    """
    veto_reasons: list[str] = []
    crowd_score = 0.0

    # --- VETO 1: Funding catastrophe ---
    funding = features.get("funding_rate", np.array([np.nan]))[index]
    if np.isfinite(funding) and funding < max_funding_penalty:
        veto_reasons.append(f"funding_catastrophic ({funding:.4f})")
        crowd_score += 30

    # --- VETO 2: OI/ADV crowding ---
    oi_vol = features.get("oi_to_volume", np.array([np.nan]))[index]
    if np.isfinite(oi_vol) and oi_vol > max_oi_adv_ratio:
        veto_reasons.append(f"oi_adv_extreme ({oi_vol:.2f})")
        crowd_score += 25

    # --- VETO 3: BTC rallying ---
    btc_30d = features.get("btc_30d_return", np.array([np.nan]))[index]
    if np.isfinite(btc_30d) and btc_30d > 0.10:
        veto_reasons.append(f"btc_rallying ({btc_30d:.1%})")
        crowd_score += 20

    # --- Crowd signals ---
    ret_7d = features.get("return_7d", np.array([np.nan]))[index]
    if np.isfinite(ret_7d) and ret_7d > 0.15:
        crowd_score += 15  # Big recent rally = potentially crowded long

    vol_climax = features.get("volume_climax", np.array([np.nan]))[index]
    if np.isfinite(vol_climax) and vol_climax > 2.0:
        crowd_score += 10  # Volume climax = exhaustion risk

    oi_change = features.get("oi_change_7d", np.array([np.nan]))[index]
    if np.isfinite(oi_change) and oi_change > 0.50:
        crowd_score += 10  # Rapid OI build

    crowd_score = min(100.0, crowd_score)

    # --- Carry score ---
    funding_val = features.get("funding_rate", np.array([np.nan]))[index]
    if np.isfinite(funding_val):
        # Positive funding = shorts receive carry
        carry_annualized = funding_val * 3 * 365  # 8h funding -> annualized
    else:
        carry_annualized = 0.0

    # --- Entry urgency ---
    # Higher when: recent rally + volume climax + not vetoed
    urgency = 0.5
    if np.isfinite(ret_7d):
        urgency += min(0.3, ret_7d * 2)
    if np.isfinite(vol_climax) and vol_climax > 1.5:
        urgency += 0.1
    if veto_reasons:
        urgency *= 0.1  # Vetoed = no urgency
    urgency = min(1.0, max(0.0, urgency))

    # --- Signal ---
    if veto_reasons:
        signal = TradeabilitySignal.VETO
    elif crowd_score > 60:
        signal = TradeabilitySignal.WAIT
    else:
        signal = TradeabilitySignal.ENTER

    return TradeabilityResult(
        signal=signal,
        crowd_score=crowd_score,
        carry_score=carry_annualized,
        veto_reasons=veto_reasons,
        entry_urgency=urgency,
    )
