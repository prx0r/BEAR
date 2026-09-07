"""Calendar-aligned panel data — fixes the fundamental PIT issue.

All assets are aligned on the same UTC calendar dates.
Cross-sectional ranking happens only among assets genuinely available
on the same date. No row-index guessing.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

DATA_DIR = Path("/root/BEAR/data/binance")


def build_calendar_panel() -> dict[int, dict[str, dict]]:
    """Build a calendar-aligned panel.

    Returns: dict[timestamp_ms -> dict[symbol -> {close, volume, index}]]
    Only dates where at least 10 assets are available are included.
    """
    # Load all assets with their timestamps
    raw_assets: dict[str, dict] = {}
    for f in sorted(DATA_DIR.glob("*.json")):
        sym = f.stem.replace("USDT", "")
        with open(f) as fh:
            data = json.load(fh)
        if len(data) < 90:
            continue
        timestamps = [d["open_time"] for d in data]
        closes = [d["close"] for d in data]
        volumes = [d["volume"] for d in data]
        raw_assets[sym] = {
            "timestamps": timestamps,
            "closes": closes,
            "volumes": volumes,
            "n": len(data),
        }

    # Build timestamp → symbol → data mapping
    all_timestamps: set[int] = set()
    for data in raw_assets.values():
        all_timestamps.update(data["timestamps"])

    panel: dict[int, dict[str, dict]] = {}
    for ts in sorted(all_timestamps):
        assets_on_date = {}
        for sym, data in raw_assets.items():
            try:
                idx = data["timestamps"].index(ts)
                assets_on_date[sym] = {
                    "close": data["closes"][idx],
                    "volume": data["volumes"][idx],
                    "index": idx,
                }
            except ValueError:
                continue
        if len(assets_on_date) >= 10:
            panel[ts] = assets_on_date

    return panel


def get_btc_series(panel: dict[int, dict[str, dict]]) -> tuple[list[int], list[float]]:
    """Extract BTC close series from panel, aligned to calendar."""
    timestamps = []
    closes = []
    for ts in sorted(panel.keys()):
        if "BTC" in panel[ts]:
            timestamps.append(ts)
            closes.append(panel[ts]["BTC"]["close"])
    return timestamps, closes


def get_returns(panel: dict[int, dict[str, dict]], sym: str) -> tuple[list[int], list[float]]:
    """Get calendar-aligned returns for a symbol."""
    timestamps = []
    closes = []
    for ts in sorted(panel.keys()):
        if sym in panel[ts]:
            timestamps.append(ts)
            closes.append(panel[ts][sym]["close"])

    returns = []
    ret_timestamps = []
    for i in range(1, len(closes)):
        if closes[i - 1] > 0:
            returns.append((closes[i] - closes[i - 1]) / closes[i - 1])
            ret_timestamps.append(timestamps[i])

    return ret_timestamps, returns


def cross_sectional_rank_on_date(
    panel: dict[int, dict[str, dict]],
    timestamp: int,
    values: dict[str, float],
    higher_is_better: bool = True,
) -> dict[str, float]:
    """Rank assets cross-sectionally on a specific calendar date.

    Only ranks among assets actually available on that date.
    Returns percentile 0-100.
    """
    available = {s: v for s, v in values.items() if s in panel.get(timestamp, {})}
    if len(available) < 2:
        return {s: 50.0 for s in values}

    sorted_items = sorted(available.items(), key=lambda x: x[1], reverse=higher_is_better)
    n = len(sorted_items)
    ranks = {}
    for rank, (sym, _) in enumerate(sorted_items):
        ranks[sym] = rank / (n - 1) * 100 if n > 1 else 50.0

    # Fill missing with NaN
    for s in values:
        if s not in ranks:
            ranks[s] = np.nan
    return ranks


def compute_rolling_window(
    values: list[float],
    window: int,
) -> list[float | None]:
    """Compute rolling window statistic (last value in window)."""
    result = []
    for i in range(len(values)):
        if i < window - 1:
            result.append(None)
        else:
            result.append(values[i])
    return result


if __name__ == "__main__":
    print("Building calendar panel...")
    panel = build_calendar_panel()
    timestamps = sorted(panel.keys())
    print(f"Panel: {len(timestamps)} dates, {len(panel[timestamps[0]])} assets on first date")

    # Check BTC alignment
    btc_ts, btc_closes = get_btc_series(panel)
    print(f"BTC: {len(btc_ts)} dates")
    print(f"Date range: {btc_ts[0]} to {btc_ts[-1]}")

    # Check a specific date
    ts = timestamps[-1]
    assets_today = list(panel[ts].keys())
    print(f"Latest date ({ts}): {len(assets_today)} assets available")
