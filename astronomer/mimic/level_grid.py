"""v1 grid classifier: WHICH round-$1k grid point does the trader state?

75.9% of stated levels sit exactly on $1k multiples (vs ~0.1% null) — so predict
k in -5..+5 where level = round(spot/1000)*1000 + k*1000. Eleven one-vs-rest
online AdaGrad logistics on market-state features. Time split 70/30, frozen
scored. Must beat NEAREST-ROUND (k=0) and SWING baselines. Stdlib only.
Usage: cd astronomer && python3 -m mimic.level_grid
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mimic.features import MarketState
from mimic.online import AdaGradLogistic

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KS = list(range(-5, 6))


def main():
    rows = [r for r in json.load(open(os.path.join(ROOT, "astronomer", "data", "levels_all.json")))
            if r["tier1"]]
    rows.sort(key=lambda r: r["ms"])
    cut = rows[int(len(rows) * 0.7)]["ms"]
    tr = [r for r in rows if r["ms"] < cut]
    te = [r for r in rows if r["ms"] >= cut]
    print(f"train={len(tr)} test={len(te)}")
    ms = MarketState()
    mem = {"hours_since_post": 24.0}
    models = {k: AdaGradLogistic(lr=0.2) for k in KS}
    for r in tr:
        x = ms.vector(r["ms"], mem)
        ktrue = int(round((r["level"] - round(r["spot"] / 1000) * 1000) / 1000))
        ktrue = max(-5, min(5, ktrue))
        for k in KS:
            models[k].learn_one(x, 1 if k == ktrue else 0)
    import copy
    frozen = {k: copy.deepcopy(m) for k, m in models.items()}
    hits = {"model": 0, "round0": 0, "swing": 0}
    mae = {"model": [], "round0": [], "swing": []}
    d = json.load(open(os.path.join(ROOT, "astronomer", "data", "prices", "BTCUSDT_1h.json")))
    import bisect
    ts = sorted([(c["timestamp"], float(c["close"]), float(c["high"]), float(c["low"])) for c in d])
    T = [t for t, _, _, _ in ts]
    n = 0
    for r in te:
        x = ms.vector(r["ms"], mem)
        scores = {k: frozen[k].proba(x) for k in KS}
        khat = max(scores, key=scores.get)
        base = round(r["spot"] / 1000) * 1000
        pred, actual = base + khat * 1000, r["level"]
        i = bisect.bisect_right(T, r["ms"]) - 1
        swh = max(h for _, _, h, _ in ts[max(0, i - 60):i + 1]) if i >= 0 else base
        swl = min(l for _, _, _, l in ts[max(0, i - 60):i + 1]) if i >= 0 else base
        sw = swh if abs(swh - actual) < abs(swl - actual) else swl
        hits["model"] += abs(pred - actual) < 500
        hits["round0"] += abs(base - actual) < 500
        hits["swing"] += abs(sw - actual) < 500
        mae["model"].append(abs(pred - actual) / r["spot"])
        mae["round0"].append(abs(base - actual) / r["spot"])
        mae["swing"].append(abs(sw - actual) / r["spot"])
        n += 1
    for k in ("model", "round0", "swing"):
        v = sorted(mae[k])
        print(f"  {k}: within-$500={hits[k]/n:.1%} MAE={sum(v)/n:.4f} medAE={v[n//2]:.4f} (n={n})")
    json.dump({"n": n, "hit500": {k: hits[k] / n for k in hits},
               "mae": {k: sum(sorted(mae[k])) / n for k in mae}},
              open(os.path.join(ROOT, "astronomer", "data", "mimic_trials", "level_grid_v1.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
