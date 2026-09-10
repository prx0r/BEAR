"""Level dataset + baselines: predict the NUMBERS traders state (entries/targets).

TIER1 level = number that (a) has $/k marker or sits near a level keyword AND
(b) is within 0.5-2x concurrent BTC spot. Labels are dense: every qualifying
number is a training row (post context -> level/spot ratio).
Baselines: SPOT (predict current spot), CARRY (author's last stated level),
SWING (nearest 60-candle swing). Metric: MAE in units of spot (relative).
Usage: cd astronomer && python3 -m mimic.levels [--save]
"""
import bisect
import json
import os
import re
import sys
from email.utils import parsedate_to_datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
NUM = re.compile(r"(\$?)(\d[\d,\.]*)\s?(k)?\b", re.IGNORECASE)
LVLKW = re.compile(r"(?i)\b(entry|enter|target|support|resistance|stop|invalid|tp\b|level|zone|reclaim|break|hold|bounce|reject|top|bottom)\b")
HANDLES = ["astronomer_zero", "Timeless_Crypto", "Trader_XO", "CryptoBheem", "eliz883"]


def load_btc():
    d = json.load(open(os.path.join(ROOT, "astronomer", "data", "prices", "BTCUSDT_1h.json")))
    ts = sorted([(r["timestamp"], float(r["close"]), float(r["high"]), float(r["low"])) for r in d])
    return ts


def build():
    px = load_btc()
    T = [t for t, _, _, _ in px]
    rows = []
    for h in HANDLES:
        d = json.load(open(os.path.join(ROOT, "astronomer", "data", "backtest", "raw", f"{h}_2yr.json")))
        for t in d.get("tweets", []):
            tx = t.get("text", "")
            try:
                ms = int(parsedate_to_datetime(t["createdAt"]).timestamp() * 1000)
            except Exception:
                continue
            i = bisect.bisect_right(T, ms) - 1
            if i < 0:
                continue
            spot = T and px[i][1]
            for m in NUM.finditer(tx):
                dol, raw, k = m.group(1), m.group(2), m.group(3)
                try:
                    v = float(raw.replace(",", ""))
                except ValueError:
                    continue
                if k and v < 1000:
                    v *= 1000
                if v <= 0 or not (0.5 * spot <= v <= 2.0 * spot):
                    continue
                ctx = tx[max(0, m.start() - 40):m.end() + 10]
                tier1 = bool(dol or k or LVLKW.search(ctx))
                rows.append({"handle": h, "ms": ms, "spot": spot, "level": v,
                             "ratio": round(v / spot, 4), "tier1": tier1,
                             "post_id": str(t.get("id")), "text": tx[:300]})
    rows.sort(key=lambda r: r["ms"])
    return rows, px


def baselines(rows, px):
    T = [t for t, _, _, _ in px]
    C = [c for _, c, _, _ in px]
    H = [h for _, _, h, _ in px]
    L = [l for _, _, _, l in px]
    last = {}
    se = {"spot": [], "carry": [], "swing": []}
    for r in rows:
        if not r["tier1"]:
            continue
        i = bisect.bisect_right(T, r["ms"]) - 1
        s = C[i]
        se["spot"].append(abs(r["level"] - s) / s)
        if r["handle"] in last:
            se["carry"].append(abs(r["level"] - last[r["handle"]]) / s)
        last[r["handle"]] = r["level"]
        j0 = max(0, i - 60)
        sw = min(H[j0:i + 1] + L[j0:i + 1], key=lambda p: abs(p - r["level"]))
        se["swing"].append(abs(r["level"] - sw) / s)
    out = {}
    for k, v in se.items():
        v.sort()
        out[k] = {"n": len(v), "mae": round(sum(v) / max(1, len(v)), 4),
                  "medae": round(v[len(v) // 2], 4) if v else None}
    return out


def main():
    rows, px = build()
    t1 = sum(1 for r in rows if r["tier1"])
    print(f"levels: {len(rows)} total, TIER1={t1}")
    from collections import Counter
    print("tier1 by handle:", dict(Counter(r["handle"] for r in rows if r["tier1"])))
    b = baselines(rows, px)
    for k, v in b.items():
        print(f"  {k}: n={v['n']} MAE={v['mae']} medAE={v['medae']}")
    if "--save" in sys.argv:
        json.dump(rows, open(os.path.join(ROOT, "astronomer", "data", "levels_all.json"), "w"))
        json.dump(b, open(os.path.join(ROOT, "astronomer", "data", "mimic_trials", "levels_baselines.json"), "w"), indent=1)
        print("saved levels_all.json + baselines")


if __name__ == "__main__":
    main()
