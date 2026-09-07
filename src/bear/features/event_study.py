"""Unlock event study — forward returns around token unlock dates.

Uses supply data to estimate dilution pressure and measure returns
in the T-30…T+30 window around estimated unlock periods.

Per the 72-Hour Shock paper: 46/52 unlocks negative within 72h.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

DATA_DIR = Path("/root/BEAR/data/binance")
SUPPLY_CACHE = Path("/root/BEAR/data/supply_cache.json")


def load_assets() -> dict[str, dict]:
    """Load Binance daily OHLCV data."""
    assets = {}
    for f in sorted(DATA_DIR.glob("*.json")):
        sym = f.stem.replace("USDT", "")
        with open(f) as fh:
            raw = json.load(fh)
        if len(raw) < 100:
            continue
        closes = np.array([d["close"] for d in raw], dtype=np.float64)
        volumes = np.array([d["volume"] for d in raw], dtype=np.float64)
        timestamps = np.array([d["open_time"] for d in raw], dtype=np.int64)
        if np.all(closes > 0):
            assets[sym] = {"closes": closes, "volumes": volumes, "timestamps": timestamps, "n": len(raw)}
    return assets


def load_supply() -> dict[str, dict]:
    """Load supply cache."""
    if SUPPLY_CACHE.exists():
        return json.loads(SUPPLY_CACHE.read_text())
    return {}


def estimate_unlock_events(supply: dict[str, dict], assets: dict[str, dict]) -> list[dict]:
    """Estimate unlock events from supply dynamics.

    Since we don't have real unlock schedules, we estimate from:
    1. Tokens with high remaining supply (more unlock pressure coming)
    2. Sudden volume spikes (potential unlock selling)
    3. Price drops with volume spikes (unlock event signature)
    """
    events = []

    for sym, s in supply.items():
        if sym not in assets:
            continue
        remaining = s.get("remaining_pct", 0)
        if remaining < 10:
            continue

        data = assets[sym]
        closes = data["closes"]
        volumes = data["volumes"]
        n = data["n"]

        # Look for volume spike + price drop events (unlock signature)
        vol_ma = np.full(n, np.nan)
        for i in range(29, n):
            w = volumes[max(0, i - 29): i + 1]
            valid = w[np.isfinite(w) & (w > 0)]
            vol_ma[i] = np.mean(valid) if len(valid) > 0 else np.nan

        for i in range(30, n - 30):
            if not np.isfinite(vol_ma[i]) or vol_ma[i] <= 0:
                continue
            vol_ratio = volumes[i] / vol_ma[i]
            price_change = (closes[i] - closes[i - 1]) / closes[i - 1] if closes[i - 1] > 0 else 0

            # Unlock signature: volume spike + price drop
            if vol_ratio > 2.0 and price_change < -0.05:
                # Forward returns
                fwd_1d = (closes[i + 1] - closes[i]) / closes[i] if i + 1 < n else None
                fwd_3d = (closes[min(i + 3, n - 1)] - closes[i]) / closes[i]
                fwd_7d = (closes[min(i + 7, n - 1)] - closes[i]) / closes[i]
                fwd_30d = (closes[min(i + 30, n - 1)] - closes[i]) / closes[i]

                # Backward context
                bwd_7d = (closes[i] - closes[max(0, i - 7)]) / closes[max(0, i - 7)]
                bwd_30d = (closes[i] - closes[max(0, i - 30)]) / closes[max(0, i - 30)]

                events.append({
                    "symbol": sym,
                    "day": int(i),
                    "remaining_supply_pct": remaining,
                    "fdv_overhang": s.get("fdv_overhang"),
                    "vol_spike": round(float(vol_ratio), 1),
                    "price_drop": round(float(price_change) * 100, 1),
                    "fwd_1d": round(float(fwd_1d) * 100, 1) if fwd_1d is not None else None,
                    "fwd_3d": round(float(fwd_3d) * 100, 1),
                    "fwd_7d": round(float(fwd_7d) * 100, 1),
                    "fwd_30d": round(float(fwd_30d) * 100, 1),
                    "bwd_7d": round(float(bwd_7d) * 100, 1),
                    "bwd_30d": round(float(bwd_30d) * 100, 1),
                })

    events.sort(key=lambda x: x["day"])
    return events


def run_event_study() -> dict:
    """Run the full unlock event study."""
    assets = load_assets()
    supply = load_supply()

    print(f"Assets: {len(assets)}, Supply data: {len(supply)}")

    events = estimate_unlock_events(supply, assets)
    print(f"Estimated unlock events: {len(events)}")

    if not events:
        return {"events": [], "summary": {}}

    # Aggregate returns
    fwd_3d = [e["fwd_3d"] for e in events if e["fwd_3d"] is not None]
    fwd_7d = [e["fwd_7d"] for e in events]
    fwd_30d = [e["fwd_30d"] for e in events]

    summary = {
        "n_events": len(events),
        "n_symbols": len(set(e["symbol"] for e in events)),
        "mean_fwd_3d": round(float(np.mean(fwd_3d)), 2) if fwd_3d else None,
        "mean_fwd_7d": round(float(np.mean(fwd_7d)), 2) if fwd_7d else None,
        "mean_fwd_30d": round(float(np.mean(fwd_30d)), 2) if fwd_30d else None,
        "median_fwd_7d": round(float(np.median(fwd_7d)), 2) if fwd_7d else None,
        "negative_7d_pct": round(float(np.mean([1 for r in fwd_7d if r < 0]) / len(fwd_7d) * 100), 1) if fwd_7d else None,
    }

    # By remaining supply bucket
    high_remaining = [e for e in events if e["remaining_supply_pct"] > 30]
    low_remaining = [e for e in events if e["remaining_supply_pct"] <= 30]

    if high_remaining:
        summary["high_dilution_events"] = len(high_remaining)
        summary["high_dilution_mean_fwd_7d"] = round(float(np.mean([e["fwd_7d"] for e in high_remaining])), 2)
    if low_remaining:
        summary["low_dilution_events"] = len(low_remaining)
        summary["low_dilution_mean_fwd_7d"] = round(float(np.mean([e["fwd_7d"] for e in low_remaining])), 2)

    print(f"\nEvent Study Results:")
    print(f"  Mean fwd 3d: {summary.get('mean_fwd_3d', 'N/A')}%")
    print(f"  Mean fwd 7d: {summary.get('mean_fwd_7d', 'N/A')}%")
    print(f"  Mean fwd 30d: {summary.get('mean_fwd_30d', 'N/A')}%")
    print(f"  Negative 7d: {summary.get('negative_7d_pct', 'N/A')}%")
    if high_remaining:
        print(f"  High dilution (>30% remaining) fwd 7d: {summary.get('high_dilution_mean_fwd_7d', 'N/A')}%")
    if low_remaining:
        print(f"  Low dilution (<=30% remaining) fwd 7d: {summary.get('low_dilution_mean_fwd_7d', 'N/A')}%")

    # Top events
    print(f"\nTop 10 events by volume spike:")
    top = sorted(events, key=lambda x: x["vol_spike"], reverse=True)[:10]
    for e in top:
        print(f"  {e['symbol']:>6s} day={e['day']:>4d} vol={e['vol_spike']:.1f}x drop={e['price_drop']:+.1f}% fwd7d={e['fwd_7d']:+.1f}% remaining={e['remaining_supply_pct']:.0f}%")

    return {"events": events[:50], "summary": summary}


if __name__ == "__main__":
    result = run_event_study()
    Path("/root/BEAR/data/event_study.json").write_text(
        json.dumps(result, indent=2, default=str)
    )
    print(f"\nSaved to data/event_study.json")
