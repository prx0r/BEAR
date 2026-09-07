"""Baseline models for comparison.

Every claimed alpha must beat something embarrassingly simple.

Baselines:
1. Always long BTC
2. Always short BTC
3. Random direction
4. Recent momentum (BTC trend)
5. Regime-only (UP→long, DOWN→short, RANGE→flat)
"""

import json
import random
from pathlib import Path
from typing import Optional

from metrics import PerformanceMetrics, compute_metrics


def load_btc_hourly() -> list[dict]:
    """Load BTC hourly candles."""
    path = Path(__file__).parent / "data" / "prices" / "BTCUSDT_1h.json"
    if not path.exists():
        return []
    with open(path) as f:
        return json.load(f)


def always_long_btc(candles: list[dict], entry_ts_ms: int,
                    horizon_hours: int = 4) -> Optional[float]:
    """Always long BTC. Returns the forward return."""
    horizon_ms = horizon_hours * 3600 * 1000
    entry = None
    exit_price = None

    for c in candles:
        if c["timestamp"] > entry_ts_ms and entry is None:
            entry = c["close"]
        if c["timestamp"] >= entry_ts_ms + horizon_ms and entry is not None:
            exit_price = c["close"]
            break

    if entry and exit_price and entry > 0:
        return (exit_price - entry) / entry
    return None


def always_short_btc(candles: list[dict], entry_ts_ms: int,
                     horizon_hours: int = 4) -> Optional[float]:
    """Always short BTC."""
    r = always_long_btc(candles, entry_ts_ms, horizon_hours)
    return -r if r is not None else None


def random_direction_btc(candles: list[dict], entry_ts_ms: int,
                         horizon_hours: int = 4, seed: int = 42) -> Optional[float]:
    """Random direction on BTC."""
    rng = random.Random(seed + entry_ts_ms)
    direction = 1 if rng.random() > 0.5 else -1
    r = always_long_btc(candles, entry_ts_ms, horizon_hours)
    return direction * r if r is not None else None


def momentum_btc(candles: list[dict], entry_ts_ms: int,
                 horizon_hours: int = 4, lookback_hours: int = 24) -> Optional[float]:
    """Go long if BTC was up over lookback, short if down."""
    lookback_ms = lookback_hours * 3600 * 1000

    # Find current and lookback prices
    current_price = None
    lookback_price = None

    for c in candles:
        if c["timestamp"] > entry_ts_ms and current_price is None:
            current_price = c["close"]
        if c["timestamp"] > entry_ts_ms - lookback_ms and lookback_price is None:
            lookback_price = c["close"]

    if current_price and lookback_price and lookback_price > 0:
        recent_return = (current_price - lookback_price) / lookback_price
        direction = 1 if recent_return > 0 else -1

        forward = always_long_btc(candles, entry_ts_ms, horizon_hours)
        if forward is not None:
            return direction * forward
    return None


def evaluate_baselines(outcomes: list[dict], horizon_hours: int = 4) -> dict[str, PerformanceMetrics]:
    """Evaluate all baselines on the same timestamps as the outcomes.

    Args:
        outcomes: List of outcome dicts with 'entry_time' (ISO) or timestamp info.
        horizon_hours: Forward return horizon.

    Returns:
        Dict mapping baseline name to PerformanceMetrics.
    """
    btc_candles = load_btc_hourly()
    if not btc_candles:
        return {}

    # Extract entry timestamps from outcomes
    timestamps_ms = []
    for o in outcomes:
        entry_time = o.get("entry_time", "")
        if entry_time:
            try:
                from datetime import datetime, timezone
                dt = datetime.fromisoformat(entry_time.replace("Z", "+00:00"))
                timestamps_ms.append(int(dt.timestamp() * 1000))
            except (ValueError, TypeError):
                pass

    if not timestamps_ms:
        return {}

    baselines = {}

    # 1. Always long
    returns = [r for ts in timestamps_ms
               if (r := always_long_btc(btc_candles, ts, horizon_hours)) is not None]
    if returns:
        baselines["always_long"] = compute_metrics(returns)

    # 2. Always short
    returns = [r for ts in timestamps_ms
               if (r := always_short_btc(btc_candles, ts, horizon_hours)) is not None]
    if returns:
        baselines["always_short"] = compute_metrics(returns)

    # 3. Random direction
    returns = [r for ts in timestamps_ms
               if (r := random_direction_btc(btc_candles, ts, horizon_hours)) is not None]
    if returns:
        baselines["random"] = compute_metrics(returns)

    # 4. Momentum
    returns = [r for ts in timestamps_ms
               if (r := momentum_btc(btc_candles, ts, horizon_hours)) is not None]
    if returns:
        baselines["momentum_24h"] = compute_metrics(returns)

    return baselines


def print_baselines(baselines: dict[str, PerformanceMetrics]):
    """Print baseline comparison table."""
    print("\n=== Baseline Comparison ===")
    print(f"{'Baseline':<20} {'N':>4} {'Win%':>7} {'Mean':>8} {'Median':>8} {'Sharpe':>7} {'EV':>8}")
    print("-" * 60)
    for name, m in sorted(baselines.items()):
        print(f"{name:<20} {m.n:>4} {m.hit_rate:>6.1%} "
              f"{m.mean_return * 100:>7.3f}% {m.median_return * 100:>7.3f}% "
              f"{m.sharpe_ratio:>7.2f} {m.expected_value * 100:>7.3f}%")
