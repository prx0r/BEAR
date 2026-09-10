"""Full-signal prove-out: model direction + structure levels -> paper trades.

Per mock-window strict event with 24h outcome: entry = next-1h close,
target/stop = nearest 60-candle swing in model direction / opposite swing.
Win = target touched before stop within 24h (1h candles). Compares MODEL
direction vs ACTUAL direction on identical level logic. Stdlib only.
Usage: cd astronomer && python3 -m mimic.proveout_levels [--handle H]
"""
import argparse
import bisect
import json
import math
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mimic.features import MarketState

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CUT = int(datetime(2026, 7, 1, tzinfo=timezone.utc).timestamp() * 1000)


def wilson(k, n, z=1.96):
    if not n:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / 2 / n
    m = z * math.sqrt(p * (1 - p) / n + z * z / 4 / n / n)
    return (round(max(0, (c - m) / d), 3), round(min(1, (c + m) / d), 3))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--handle", default="astronomer_zero")
    ap.add_argument("--full", action="store_true",
                    help="score every row (no CUT gate); all tagged in-sample")
    a = ap.parse_args()
    H = a.handle
    ms = MarketState()
    w = json.load(open(os.path.join(ROOT, "astronomer", "data", f"mimic_transfer_{H}_dir.json")))
    strict = sorted(
        [x for x in json.load(open(os.path.join(ROOT, "astronomer", "data", "core3", "normalized",
                                                "strict_calls.json"))) if x["handle"] == H],
        key=lambda x: x["published_at"])
    if not strict:
        # fallback: direction rows straight from normalized CALL events
        for l in open(os.path.join(ROOT, "astronomer", "data", "core3", "normalized", f"{H}_events.jsonl")):
            r = json.loads(l)
            if r.get("semantic_kind") == "CALL" and r.get("direction") in ("BULLISH", "BEARISH") and r.get("asset"):
                strict.append({"handle": H, "published_at": r["published_at"],
                               "direction": r["direction"], "asset": r["asset"]})
        strict.sort(key=lambda x: x["published_at"])
        print(f"{H}: no strict rows, using {len(strict)} event CALLs")
    d1 = {}
    for _a, _f in (("BTC", "BTCUSDT_1h"), ("ETH", "ETHUSDT_1h"), ("SOL", "SOLUSDT_1h"),
                   ("TAO", "TAOUSDT_1h"), ("HYPE", "HYPERUSDT_1h")):
        try:
            _d = json.load(open(os.path.join(ROOT, "astronomer", "data", "prices", f"{_f}.json")))
            _ts = sorted([(r.get("timestamp", r.get("open_time")), float(r["close"]), float(r["high"]), float(r["low"])) for r in _d])
            d1[_a] = _ts
        except FileNotFoundError:
            continue
    mem = {"hours_since_post": 0.0, "last_dir": 0, "bull_streak": 0, "bear_streak": 0, "trail": []}
    MW = MA = NW = NA = 0
    R = []
    for s in strict:
        t = int(datetime.fromisoformat(s["published_at"]).timestamp() * 1000)
        if t < CUT and not a.full:
            if s["direction"] == "BULLISH":
                mem["bull_streak"] += 1; mem["bear_streak"] = 0
            else:
                mem["bear_streak"] += 1; mem["bull_streak"] = 0
            mem["last_dir"] = 1 if s["direction"] == "BULLISH" else -1
            mem.setdefault("trail", []).append(1 if s["direction"] == "BULLISH" else 0)
            mem["trail"] = mem["trail"][-20:]
            continue
        x = ms.vector(t, mem)
        z = sum(w.get(k, 0.0) * v for k, v in x.items())
        p = 1.0 / (1.0 + math.exp(-max(-60.0, min(60.0, z))))
        for who, direction in (("model", "BULLISH" if p >= 0.5 else "BEARISH"),
                               ("actual", s["direction"])):
            asset = s.get("asset") or "BTC"
            if asset not in d1:
                continue
            ts = d1[asset]
            T = [t for t, _, _, _ in ts]
            i = bisect.bisect_right(T, t)
            if i >= len(T):
                continue
            e = ts[i][1]
            j0 = max(0, i - 60)
            up = direction == "BULLISH"
            tgt = max(h for _, _, h, _ in ts[j0:i + 1]) if up else min(l for _, _, _, l in ts[j0:i + 1])
            stp = min(l for _, _, _, l in ts[j0:i + 1]) if up else max(h for _, _, h, _ in ts[j0:i + 1])
            if (tgt - e) * (1 if up else -1) <= 0 or (e - stp) * (1 if up else -1) <= 0:
                continue
            end = t + 24 * 3600000
            win = None
            for k in range(i + 1, len(T)):
                if T[k] > end:
                    break
                _, _, h, l = ts[k]
                hit_t = (h >= tgt) if up else (l <= tgt)
                hit_s = (l <= stp) if up else (h >= stp)
                if hit_t and hit_s:
                    win = None
                    break
                if hit_t:
                    win = True
                    break
                if hit_s:
                    win = False
                    break
            if win is None:
                continue
            if who == "model":
                MW += win; NW += 1
            else:
                MA += win; NA += 1
            if who == "model":
                R.append((s["published_at"], direction, tgt, stp, win))
        if s["direction"] == "BULLISH":
            mem["bull_streak"] += 1; mem["bear_streak"] = 0
        else:
            mem["bear_streak"] += 1; mem["bull_streak"] = 0
        mem["last_dir"] = 1 if s["direction"] == "BULLISH" else -1
        mem.setdefault("trail", []).append(1 if s["direction"] == "BULLISH" else 0)
        mem["trail"] = mem["trail"][-20:]
    print(f"{H} level-trades: MODEL {MW}/{NW}={MW/max(1,NW):.0%} CI{wilson(MW,NW)} vs "
          f"ACTUAL {MA}/{NA}={MA/max(1,NA):.0%} CI{wilson(MA,NA)}")
    json.dump({"handle": H, "model": {"w": MW, "n": NW, "ci": wilson(MW, NW)},
               "actual": {"w": MA, "n": NA, "ci": wilson(MA, NA)}, "trades": R},
              open(os.path.join(ROOT, "astronomer", "data", "mimic_trials", f"proveout_levels_{H}.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
