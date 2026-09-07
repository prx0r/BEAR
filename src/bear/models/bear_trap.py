"""BEAR TRAP — short-squeeze harvesting sleeve.

Detects when fundamentally doomed tokens have crowded shorts that are
starting to lose control. Tactical long with short holding horizon.

Signal:
  HIGH DEATH HAZARD
  + DEEPLY NEGATIVE FUNDING (shorts paying longs)
  + PRICE REFUSES TO FALL (strength despite being garbage)
  + OI INCREASING (new shorts entering = more fuel)
  + MARKET IN UP→UP REGIME (risk-on environment)

Per the research:
  - Extreme negative funding → +0.506% avg 24h BTC return (AIJMR 2026)
  - Crypto momentum concentrated in UP→UP states (ScienceDirect 2026)
  - Don't chase: avoid entries when 1h Bollinger already extreme (SSRN 2026)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

DATA_DIR = Path("/root/BEAR/data/binance")


def load_all_daily() -> dict[str, dict]:
    """Load all Binance daily OHLCV."""
    assets = {}
    for f in sorted(DATA_DIR.glob("*.json")):
        sym = f.stem.replace("USDT", "")
        with open(f) as fh:
            raw = json.load(fh)
        if len(raw) < 90:
            continue
        closes = np.array([d["close"] for d in raw], dtype=np.float64)
        volumes = np.array([d["volume"] for d in raw], dtype=np.float64)
        timestamps = np.array([d["open_time"] for d in raw], dtype=np.int64)
        if np.all(closes > 0):
            assets[sym] = {
                "closes": closes,
                "volumes": volumes,
                "timestamps": timestamps,
                "n": len(raw),
            }
    return assets


# ---------------------------------------------------------------------------
# Regime detector: UP→UP state
# ---------------------------------------------------------------------------

def detect_up_up_regime(
    btc_closes: np.ndarray,
    lookback_days: int = 28,
) -> np.ndarray:
    """Detect persistent UP→UP regime.

    UP state = positive cumulative return over preceding 4 weeks.
    UP→UP = current week is UP AND previous week was UP.

    Returns boolean array.
    """
    n = len(btc_closes)
    regime = np.zeros(n, dtype=bool)

    # Weekly returns
    for i in range(lookback_days * 2, n):
        # Current 4-week return
        curr_4w = (btc_closes[i] - btc_closes[i - lookback_days]) / btc_closes[i - lookback_days]
        # Previous 4-week return
        prev_4w = (btc_closes[i - lookback_days] - btc_closes[i - lookback_days * 2]) / btc_closes[i - lookback_days * 2]

        # UP→UP: both positive
        regime[i] = curr_4w > 0 and prev_4w > 0

    return regime


# ---------------------------------------------------------------------------
# Funding proxy (from daily data)
# ---------------------------------------------------------------------------

def compute_funding_proxy(
    closes: np.ndarray,
    volumes: np.ndarray,
    window: int = 30,
) -> np.ndarray:
    """Compute funding pressure proxy from daily data.

    Negative funding proxy = volume-weighted price decline intensity.
    When price drops with high volume, shorts are likely profitable,
    which correlates with negative funding (shorts paying longs).

    Returns: proxy where more negative = more crowded short.
    """
    n = len(closes)
    proxy = np.full(n, np.nan)

    returns = np.full(n, np.nan)
    for i in range(1, n):
        if closes[i] > 0 and closes[i - 1] > 0:
            returns[i] = np.log(closes[i] / closes[i - 1])

    for i in range(window, n):
        w_ret = returns[i - window + 1: i + 1]
        w_vol = volumes[i - window + 1: i + 1]
        valid = np.isfinite(w_ret)
        if valid.sum() < 10:
            continue

        # Weighted return (volume-weighted)
        vol_sum = np.sum(w_vol[valid])
        if vol_sum > 0:
            vw_return = np.sum(w_ret[valid] * w_vol[valid]) / vol_sum
            # Negative return = shorts profitable = likely negative funding
            proxy[i] = vw_return

    return proxy


# ---------------------------------------------------------------------------
# Death hazard (simplified from models/death_hazard.py)
# ---------------------------------------------------------------------------

def compute_volume_death(closes: np.ndarray, volumes: np.ndarray) -> np.ndarray:
    """Simple volume death score 0-100."""
    n = len(closes)
    score = np.full(n, np.nan)

    for i in range(89, n):
        vol_7d = np.mean(volumes[max(0, i - 6): i + 1])
        vol_peak = np.max(volumes[max(0, i - 89): i + 1])
        if vol_peak > 0:
            score[i] = (1.0 - vol_7d / vol_peak) * 100

    return score


# ---------------------------------------------------------------------------
# OI proxy (from volume)
# ---------------------------------------------------------------------------

def compute_oi_proxy(volumes: np.ndarray, window: int = 14) -> np.ndarray:
    """Proxy for OI change using volume momentum.

    Rising volume in a declining market suggests new shorts entering.
    """
    n = len(volumes)
    oi_change = np.full(n, np.nan)

    vol_ma = np.full(n, np.nan)
    for i in range(window, n):
        vol_ma[i] = np.mean(volumes[max(0, i - window): i + 1])

    for i in range(window + 7, n):
        if vol_ma[i] > 0 and vol_ma[i - 7] > 0:
            oi_change[i] = (vol_ma[i] - vol_ma[i - 7]) / vol_ma[i - 7]

    return oi_change


# ---------------------------------------------------------------------------
# BEAR TRAP signal
# ---------------------------------------------------------------------------

def compute_bear_trap_signal(
    assets: dict[str, dict],
    t: int,
) -> list[dict[str, Any]]:
    """Compute BEAR TRAP signals at time t.

    Identifies death tokens where shorts are trapped and squeeze is imminent.
    """
    btc = assets.get("BTC")
    if btc is None or btc["n"] <= t:
        return []

    btc_closes = btc["closes"][:t + 1]
    regime = detect_up_up_regime(btc_closes)
    is_risk_on = regime[-1] if len(regime) > 0 else False

    results = []

    BLUE_CHIPS = {"BTC", "ETH", "SOL", "HYPE", "BNB", "XRP", "ADA", "AVAX", "DOT",
                  "LINK", "UNI", "AAVE", "MKR", "SNX", "CRV", "LDO", "PENDLE"}

    for sym, data in assets.items():
        if sym in BLUE_CHIPS or sym == "BTC":
            continue
        if data["n"] <= t or t < 90:
            continue

        closes = data["closes"][:t + 1]
        volumes = data["volumes"][:t + 1]

        # Death hazard
        death = compute_volume_death(closes, volumes)
        death_val = death[-1] if np.isfinite(death[-1]) else 50

        # Funding proxy (more negative = more crowded short)
        fund_proxy = compute_funding_proxy(closes, volumes)
        fund_val = fund_proxy[-1] if np.isfinite(fund_proxy[-1]) else 0

        # OI proxy (rising = new shorts entering)
        oi_change = compute_oi_proxy(volumes)
        oi_val = oi_change[-1] if np.isfinite(oi_change[-1]) else 0

        # Price strength: 7d return (positive despite being garbage = squeeze forming)
        ret_7d = (closes[-1] - closes[-8]) / closes[-8] if t >= 8 and closes[-8] > 0 else 0

        # Relative strength vs BTC
        btc_ret_7d = (btc_closes[-1] - btc_closes[-8]) / btc_closes[-8] if t >= 8 and btc_closes[-8] > 0 else 0
        relative_strength = ret_7d - btc_ret_7d

        # Funding percentile (trailing 30 days)
        fund_window = fund_proxy[max(0, t - 29): t + 1]
        valid_fund = fund_window[np.isfinite(fund_window)]
        if len(valid_fund) > 5:
            fund_p10 = np.percentile(valid_fund, 10)
            is_funding_extreme = fund_val <= fund_p10
        else:
            is_funding_extreme = False

        # Squeeze conditions
        # 1. Death hazard high (garbage token)
        death_high = death_val >= 60
        # 2. Funding extremely negative (shorts paying)
        # Use proxy: negative return + high volume = likely negative funding
        funding_crowded = fund_val < -0.005
        # 3. Price rising despite death
        price_rising = ret_7d > 0
        # 4. OI expanding (new shorts entering)
        oi_expanding = oi_val > 0.1
        # 5. Market risk-on
        risk_on = is_risk_on
        # 6. Not already vertical (don't chase)
        not_vertical = ret_7d < 0.30  # less than 30% in 7d

        # Composite score
        signals_firing = sum([death_high, funding_crowded, price_rising, oi_expanding, risk_on])
        trap_score = 0.0
        if death_high: trap_score += 25
        if funding_crowded: trap_score += 25
        if price_rising: trap_score += 20
        if oi_expanding: trap_score += 15
        if risk_on: trap_score += 15

        # Signal
        if signals_firing >= 4 and not_vertical:
            signal = "SQUEEZE_STARTING"
        elif signals_firing >= 3 and price_rising:
            signal = "WATCH"
        else:
            signal = "NONE"

        results.append({
            "symbol": sym,
            "trap_score": round(trap_score, 1),
            "signal": signal,
            "death_hazard": round(death_val, 1),
            "funding_proxy": round(fund_val, 4),
            "oi_change": round(oi_val, 3),
            "ret_7d": round(ret_7d * 100, 1),
            "relative_strength": round(relative_strength * 100, 1),
            "signals_firing": signals_firing,
            "is_risk_on": risk_on,
            "not_vertical": not_vertical,
        })

    results.sort(key=lambda x: x["trap_score"], reverse=True)
    return results


# ---------------------------------------------------------------------------
# BEAR RELOAD — post-squeeze short entry
# ---------------------------------------------------------------------------

def compute_bear_reload_signal(
    assets: dict[str, dict],
    t: int,
    lookback_squeeze: int = 30,
) -> list[dict[str, Any]]:
    """Detect BEAR RELOAD opportunities.

    After a squeeze exhausts, the same garbage token becomes shortable again:
      - Death hazard still high
      - Price well above pre-squeeze level
      - Funding normalized (squeezed shorts gone)
      - Volume spike declining (squeeze exhaustion)
      - Fundamentals still garbage
    """
    btc = assets.get("BTC")
    if btc is None or btc["n"] <= t:
        return []

    results = []

    BLUE_CHIPS = {"BTC", "ETH", "SOL", "HYPE", "BNB", "XRP", "ADA", "AVAX", "DOT",
                  "LINK", "UNI", "AAVE", "MKR", "SNX", "CRV", "LDO", "PENDLE"}

    for sym, data in assets.items():
        if sym in BLUE_CHIPS or sym == "BTC":
            continue
        if data["n"] <= t or t < lookback_squeeze + 30:
            continue

        closes = data["closes"][:t + 1]
        volumes = data["volumes"][:t + 1]

        # Death hazard (still high?)
        death = compute_volume_death(closes, volumes)
        death_val = death[-1] if np.isfinite(death[-1]) else 50

        # Price vs pre-squeeze level (30d ago)
        price_30d_ago = closes[t - lookback_squeeze] if t >= lookback_squeeze else closes[0]
        price_ratio = closes[-1] / price_30d_ago if price_30d_ago > 0 else 1.0

        # Funding normalized? (volume proxy: lower than recent extreme)
        fund_proxy = compute_funding_proxy(closes, volumes)
        fund_recent = fund_proxy[-1] if np.isfinite(fund_proxy[-1]) else 0
        fund_30d = fund_proxy[max(0, t - 29): t + 1]
        valid_fund = fund_30d[np.isfinite(fund_30d)]
        fund_percentile = np.searchsorted(np.sort(valid_fund), fund_recent) / max(len(valid_fund), 1) * 100 if len(valid_fund) > 0 else 50

        # Volume exhaustion (spike declining)
        vol_3d = np.mean(volumes[max(0, t - 2): t + 1])
        vol_14d = np.mean(volumes[max(0, t - 13): t + 1])
        vol_ratio = vol_3d / vol_14d if vol_14d > 0 else 1.0
        vol_exhausting = vol_ratio < 1.5  # volume spike subsiding

        # Squeeze completed: price rose significantly then started falling
        # Look for: high in last 30d, now below high
        high_30d = np.max(closes[max(0, t - 29): t + 1])
        from_high = (closes[-1] - high_30d) / high_30d if high_30d > 0 else 0
        squeeze_completed = from_high < -0.10 and price_ratio > 1.3

        # RELOAD conditions
        # 1. Death still high
        # 2. Price well above pre-squeeze (squeeze happened)
        # 3. Funding normalized (crowd cleared)
        # 4. Volume declining (exhaustion)
        # 5. Price rolling over (from high)
        conditions = [
            death_val >= 60,
            price_ratio > 1.3,
            fund_percentile > 30,  # funding not extreme anymore
            vol_exhausting,
            squeeze_completed,
        ]

        reload_score = sum(conditions) / len(conditions) * 100

        if sum(conditions) >= 4:
            signal = "RELOAD_SHORT"
        elif sum(conditions) >= 3:
            signal = "WATCH_RELOAD"
        else:
            signal = "NONE"

        results.append({
            "symbol": sym,
            "reload_score": round(reload_score, 1),
            "signal": signal,
            "death_hazard": round(death_val, 1),
            "price_ratio": round(price_ratio, 2),
            "fund_percentile": round(fund_percentile, 0),
            "vol_exhausting": vol_exhausting,
            "squeeze_completed": squeeze_completed,
            "from_high": round(from_high * 100, 1),
        })

    results.sort(key=lambda x: x["reload_score"], reverse=True)
    return results
