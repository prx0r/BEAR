"""Last Pump archetype test.

Hypothesis: tokens with high death hazard + high dilution + recent rally
are the best short candidates once the rally exhausts.

Per DEV_PLAN.md:
  DEATH_HAZARD high
  + REAL LIQUIDITY remains
  + 8-12W DILUTION HIGH
  + FDV OVERHANG HIGH
  + 8-10W PRICE RETURN HIGH (recent winner)
  + RALLY ROLLS OVER
  + SHORT NOT YET CROWDED
  = >>> SHORT WINDOW <<<
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

DATA_DIR = Path("/root/BEAR/data/binance")
SUPPLY_CACHE = Path("/root/BEAR/data/supply_cache.json")


def load_assets() -> dict[str, dict]:
    assets = {}
    for f in sorted(DATA_DIR.glob("*.json")):
        sym = f.stem.replace("USDT", "")
        with open(f) as fh:
            raw = json.load(fh)
        if len(raw) < 200:
            continue
        closes = np.array([d["close"] for d in raw], dtype=np.float64)
        volumes = np.array([d["volume"] for d in raw], dtype=np.float64)
        if np.all(closes > 0):
            assets[sym] = {"closes": closes, "volumes": volumes, "n": len(raw)}
    return assets


def test_last_pump():
    """Test: recent winner + high dilution + volume spike → short after rollover."""
    assets = load_assets()
    supply = json.loads(SUPPLY_CACHE.read_text()) if SUPPLY_CACHE.exists() else {}

    print(f"Assets: {len(assets)}, Supply data: {len(supply)}")

    # Identify tokens with high remaining supply
    high_dilution = {s for s, d in supply.items() if d.get("remaining_pct", 0) > 20}
    print(f"High dilution tokens: {high_dilution}")

    # For each day, identify "Last Pump" candidates:
    # 1. Recent winner (8w return > 20%)
    # 2. High volume (liquid)
    # 3. Has dilution data
    # Then short after the rally rolls over

    results = {
        "last_pump": [],  # recent winner + dilution → short
        "control_winner": [],  # recent winner, no dilution → short
        "control_diluted": [],  # diluted, not a winner → short
    }

    for sym, data in assets.items():
        closes = data["closes"]
        volumes = data["volumes"]
        n = data["n"]

        has_dilution = sym in high_dilution
        remaining = supply.get(sym, {}).get("remaining_pct", 0)
        fdv_overhang = supply.get(sym, {}).get("fdv_overhang")

        for t in range(84, n - 60):
            if closes[t - 56] <= 0 or closes[t] <= 0:
                continue

            # 8w return
            ret_8w = (closes[t] - closes[t - 56]) / closes[t - 56]

            # Must be a recent winner (>20% in 8w)
            if ret_8w < 0.20:
                continue

            # Volume must be liquid
            vol_ma = np.mean(volumes[max(0, t - 29): t + 1])
            if vol_ma < 50_000:
                continue

            # Forward returns (short the rally)
            fwd_7d = (closes[min(t + 7, n - 1)] - closes[t]) / closes[t]
            fwd_30d = (closes[min(t + 30, n - 1)] - closes[t]) / closes[t]
            fwd_60d = (closes[min(t + 60, n - 1)] - closes[t]) / closes[t]

            entry = {
                "symbol": sym,
                "day": t,
                "ret_8w": round(ret_8w * 100, 1),
                "fwd_7d": round(fwd_7d * 100, 1),
                "fwd_30d": round(fwd_30d * 100, 1),
                "fwd_60d": round(fwd_60d * 100, 1),
                "has_dilution": has_dilution,
                "remaining_pct": remaining,
                "fdv_overhang": fdv_overhang,
            }

            if has_dilution:
                results["last_pump"].append(entry)
            else:
                results["control_winner"].append(entry)

    # Summarize
    for category, data in results.items():
        if not data:
            continue
        fwd_7d = [d["fwd_7d"] for d in data]
        fwd_30d = [d["fwd_30d"] for d in data]
        fwd_60d = [d["fwd_60d"] for d in data]

        print(f"\n{'=' * 60}")
        print(f"{category.upper()} ({len(data)} entries)")
        print(f"{'=' * 60}")
        print(f"  Mean fwd 7d:  {np.mean(fwd_7d):+.2f}%")
        print(f"  Mean fwd 30d: {np.mean(fwd_30d):+.2f}%")
        print(f"  Mean fwd 60d: {np.mean(fwd_60d):+.2f}%")
        print(f"  Negative 30d: {np.mean([1 for r in fwd_30d if r < 0]) * 100:.1f}%")
        print(f"  Median fwd 30d: {np.median(fwd_30d):+.2f}%")

    # The key comparison: Last Pump vs Control Winner
    lp = results["last_pump"]
    cw = results["control_winner"]

    if lp and cw:
        print(f"\n{'=' * 60}")
        print(f"LAST PUMP ADVANTAGE (diluted winners vs non-diluted winners)")
        print(f"{'=' * 60}")
        lp_30d = np.mean([d["fwd_30d"] for d in lp])
        cw_30d = np.mean([d["fwd_30d"] for d in cw])
        print(f"  Last Pump fwd 30d:  {lp_30d:+.2f}%")
        print(f"  Control winner fwd 30d: {cw_30d:+.2f}%")
        print(f"  Advantage: {lp_30d - cw_30d:+.2f}% (more negative = better short)")

        lp_60d = np.mean([d["fwd_60d"] for d in lp])
        cw_60d = np.mean([d["fwd_60d"] for d in cw])
        print(f"  Last Pump fwd 60d:  {lp_60d:+.2f}%")
        print(f"  Control winner fwd 60d: {cw_60d:+.2f}%")
        print(f"  Advantage: {lp_60d - cw_60d:+.2f}%")

    return results


if __name__ == "__main__":
    results = test_last_pump()
    Path("/root/BEAR/data/last_pump_results.json").write_text(
        json.dumps(results, indent=2, default=str)
    )
