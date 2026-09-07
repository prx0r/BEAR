"""Deterministic BTC regime classification and point-in-time market state.

Regime is derived ONLY from lagged market data. The source's own post
cannot define the objective regime.

Simple observable states first:
  BTC trend: UP, DOWN, RANGE
  BTC vol: NORMAL_VOL, HIGH_VOL

Uses only lagged data (no future leak).
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).parent / "data"
PRICES_DIR = DATA_DIR / "prices"
REGIME_DIR = DATA_DIR / "regime"


def load_btc_hourly() -> list[dict]:
    """Load BTC hourly candles. Returns list sorted by timestamp."""
    path = PRICES_DIR / "BTCUSDT_1h.json"
    if not path.exists():
        raise FileNotFoundError(f"BTC price data not found: {path}")
    with open(path) as f:
        data = json.load(f)
    return sorted(data, key=lambda x: x["timestamp"])


def compute_ema(prices: list[float], period: int) -> list[Optional[float]]:
    """Compute EMA over a price series. Returns list same length as input.
    First (period-1) values are None."""
    if len(prices) < period:
        return [None] * len(prices)

    multiplier = 2.0 / (period + 1)
    ema = [None] * (period - 1)

    # Seed with SMA
    sma = sum(prices[:period]) / period
    ema.append(sma)

    for i in range(period, len(prices)):
        val = prices[i] * multiplier + ema[-1] * (1 - multiplier)
        ema.append(val)

    return ema


def classify_regime(closes: list[float], ema20: list[Optional[float]],
                     ema50: list[Optional[float]]) -> list[str]:
    """Classify BTC trend regime from EMAs.

    UP: price > EMA20 > EMA50
    DOWN: price < EMA20 < EMA50
    RANGE: everything else
    """
    regimes = []
    for i in range(len(closes)):
        e20 = ema20[i]
        e50 = ema50[i]
        if e20 is None or e50 is None:
            regimes.append("UNKNOWN")
            continue

        price = closes[i]
        if price > e20 > e50:
            regimes.append("UP")
        elif price < e20 < e50:
            regimes.append("DOWN")
        else:
            regimes.append("RANGE")

    return regimes


def classify_volatility(closes: list[float], window: int = 168) -> list[str]:
    """Classify BTC volatility state from realized 7-day (168h) vol.

    HIGH_VOL: realized vol > 1.5 × rolling median
    NORMAL_VOL: otherwise
    """
    if len(closes) < window + 1:
        return ["UNKNOWN"] * len(closes)

    # Compute hourly returns
    returns = [0.0]
    for i in range(1, len(closes)):
        returns.append((closes[i] - closes[i - 1]) / closes[i - 1])

    # Rolling realized vol (annualized from hourly)
    vols = []
    for i in range(len(closes)):
        if i < window:
            vols.append(None)
            continue
        window_returns = returns[i - window + 1: i + 1]
        mean_r = sum(window_returns) / len(window_returns)
        var = sum((r - mean_r) ** 2 for r in window_returns) / len(window_returns)
        vol = (var ** 0.5) * (8760 ** 0.5)  # annualize from hourly
        vols.append(vol)

    # Find median vol (from valid values)
    valid_vols = [v for v in vols if v is not None]
    if not valid_vols:
        return ["UNKNOWN"] * len(closes)
    sorted_vols = sorted(valid_vols)
    median_vol = sorted_vols[len(sorted_vols) // 2]

    vol_states = []
    for v in vols:
        if v is None:
            vol_states.append("UNKNOWN")
        elif v > median_vol * 1.5:
            vol_states.append("HIGH_VOL")
        else:
            vol_states.append("NORMAL_VOL")

    return vol_states


def build_regime_timeline() -> list[dict]:
    """Build complete BTC regime timeline from hourly data.

    Returns list of dicts with timestamp, regime, vol_state, EMAs, returns.
    """
    candles = load_btc_hourly()
    if not candles:
        return []

    closes = [c["close"] for c in candles]
    timestamps = [c["timestamp"] for c in candles]

    # Compute EMAs
    ema20 = compute_ema(closes, 20)
    ema50 = compute_ema(closes, 50)

    # Classify regimes
    trend_regimes = classify_regime(closes, ema20, ema50)
    vol_states = classify_volatility(closes)

    # Compute returns
    def get_return(idx, hours):
        if idx < hours:
            return 0.0
        return (closes[idx] - closes[idx - hours]) / closes[idx - hours]

    # 7-day realized vol
    def get_7d_vol(idx, window=168):
        if idx < window:
            return 0.0
        window_closes = closes[idx - window: idx + 1]
        rets = [(window_closes[i] - window_closes[i - 1]) / window_closes[i - 1]
                for i in range(1, len(window_closes))]
        if not rets:
            return 0.0
        mean_r = sum(rets) / len(rets)
        var = sum((r - mean_r) ** 2 for r in rets) / len(rets)
        return (var ** 0.5) * (8760 ** 0.5)

    timeline = []
    for i, candle in enumerate(candles):
        entry = {
            "timestamp_ms": timestamps[i],
            "timestamp": datetime.fromtimestamp(
                timestamps[i] / 1000, tz=timezone.utc
            ).isoformat(),
            "btc_price": closes[i],
            "btc_regime": trend_regimes[i],
            "btc_vol_state": vol_states[i],
            "btc_ema20_1h": round(ema20[i], 2) if ema20[i] else None,
            "btc_ema50_1h": round(ema50[i], 2) if ema50[i] else None,
            "btc_24h_return": round(get_return(i, 24), 6),
            "btc_7d_return": round(get_return(i, 168), 6),
            "btc_7d_vol": round(get_7d_vol(i), 6),
        }
        timeline.append(entry)

    return timeline


def get_market_state_at(timeline: list[dict], timestamp_ms: int) -> Optional[dict]:
    """Get point-in-time market state for a given timestamp.
    Uses the candle AT or JUST BEFORE the timestamp (no future leak)."""
    best = None
    for entry in timeline:
        if entry["timestamp_ms"] <= timestamp_ms:
            best = entry
        else:
            break
    return best


def get_next_candle(timeline: list[dict], timestamp_ms: int) -> Optional[dict]:
    """Get the FIRST candle AFTER a given timestamp.
    This is used for entry timing — enter on the next candle, not the signal candle."""
    for entry in timeline:
        if entry["timestamp_ms"] > timestamp_ms:
            return entry
    return None


def save_regime_timeline(timeline: list[dict]):
    """Save regime timeline to disk."""
    REGIME_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REGIME_DIR / "timeline.json"
    with open(out_path, "w") as f:
        json.dump(timeline, f, indent=2)
    print(f"Saved {len(timeline)} regime entries to {out_path}")


def load_regime_timeline() -> list[dict]:
    """Load regime timeline from disk."""
    path = REGIME_DIR / "timeline.json"
    if not path.exists():
        print("No regime timeline found. Building...")
        timeline = build_regime_timeline()
        save_regime_timeline(timeline)
        return timeline
    with open(path) as f:
        return json.load(f)


if __name__ == "__main__":
    print("Building BTC regime timeline...")
    timeline = build_regime_timeline()
    save_regime_timeline(timeline)

    # Print summary
    regimes = {}
    for entry in timeline:
        r = entry["btc_regime"]
        regimes[r] = regimes.get(r, 0) + 1

    print(f"\nRegime distribution ({len(timeline)} candles):")
    for r, count in sorted(regimes.items()):
        print(f"  {r}: {count} ({count / len(timeline) * 100:.1f}%)")

    # Show recent
    print(f"\nLast 5 entries:")
    for entry in timeline[-5:]:
        print(f"  {entry['timestamp']}: {entry['btc_regime']} | "
              f"vol={entry['btc_vol_state']} | "
              f"price={entry['btc_price']:.0f} | "
              f"24h={entry['btc_24h_return'] * 100:.2f}%")
