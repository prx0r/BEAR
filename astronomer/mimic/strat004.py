"""STRAT-004 engine: regime -> voter -> structure levels -> artifacts + paper ledger.

Rules (validated: 169 trades, 59.2%, +69.4% 2yr):
  DOWN  -> follow Trader_XO calls, 4h horizon
  RANGE -> follow Timeless_Crypto calls, 24h horizon
  UP    -> NO TRADE
Paper run: walk last 30d daily; each day apply rule to that day's voter calls;
resolve at horizon from 1h candles; append receipts to data/paper_ledger.jsonl.
Stdlib only. Usage: cd astronomer && python3 -m mimic.strat004 [--paper|--signal]
"""
import argparse
import bisect
import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mimic.features import MarketState

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "astronomer", "data")
RULES = {"DOWN": ("Trader_XO", 4), "RANGE": ("Timeless_Crypto", 24)}


def load_calls():
    rows = []
    for fn in ["core3/normalized/strict_calls.json", "core3/normalized/strict_NEW.json"]:
        p = os.path.join(DATA, fn)
        if os.path.exists(p):
            rows += json.load(open(p))
    out = []
    for r in rows:
        if r.get("handle") in ("Trader_XO", "Timeless_Crypto") and r.get("direction") in ("BULLISH", "BEARISH"):
            try:
                out.append((int(datetime.fromisoformat(r["published_at"]).timestamp() * 1000), r))
            except ValueError:
                pass
    out.sort()
    return out


def load_btc():
    d = json.load(open(os.path.join(DATA, "prices", "BTCUSDT_1h.json")))
    ts = sorted([(c["timestamp"], float(c["close"]), float(c["high"]), float(c["low"])) for c in d])
    return ts


def levels_at(ts, t_ms, direction):
    T = [t for t, _, _, _ in ts]
    i = bisect.bisect_right(T, t_ms)
    if i >= len(T):
        return None
    e = ts[i][1]
    j0 = max(0, i - 60)
    up = direction == "BULLISH"
    tgt = max(h for _, _, h, _ in ts[j0:i + 1]) if up else min(l for _, _, _, l in ts[j0:i + 1])
    stp = min(l for _, _, _, l in ts[j0:i + 1]) if up else max(h for _, _, h, _ in ts[j0:i + 1])
    if (tgt - e) * (1 if up else -1) <= 0 or (e - stp) * (1 if up else -1) <= 0:
        return None
    return {"entry": e, "entry_ms": ts[i][0], "target": tgt, "stop": stp}


def resolve(ts, entry_ms, tgt, stp, direction, horizon_h):
    T = [t for t, _, _, _ in ts]
    i = bisect.bisect_right(T, entry_ms) - 1
    end = entry_ms + horizon_h * 3600000
    up = direction == "BULLISH"
    for k in range(i + 1, len(T)):
        if T[k] > end:
            return {"result": "timeout", "ret": 0.0}
        _, _, h, l = ts[k]
        ht = (h >= tgt) if up else (l <= tgt)
        hs = (l <= stp) if up else (h >= stp)
        if ht and hs:
            return {"result": "both", "ret": 0.0}
        if ht:
            return {"result": "target", "ret": (tgt / ts[i][1] - 1) * (1 if up else -1)}
        if hs:
            return {"result": "stopped", "ret": (stp / ts[i][1] - 1) * (1 if up else -1)}
    return {"result": "timeout", "ret": 0.0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper", action="store_true")
    ap.add_argument("--signal", action="store_true")
    ap.add_argument("--days", type=int, default=30)
    a = ap.parse_args()
    ms = MarketState()
    calls = load_calls()
    ts = load_btc()
    if a.signal or not (a.paper or a.signal):
        now = int(datetime.now(tz=timezone.utc).timestamp() * 1000)
        reg = ms.regime_at(now)
        rule = RULES.get(reg)
        sig = {"generated_at": datetime.now(tz=timezone.utc).isoformat(), "regime": reg,
               "rule": f"follow {rule[0]} {rule[1]}h" if rule else "NO TRADE (UP)",
               "paper": True, "note": "paper only, not financial advice"}
        print(json.dumps(sig, indent=1))
        json.dump(sig, open(os.path.join(DATA, "strat004_signal.json"), "w"), indent=1)
    if a.paper or not (a.paper or a.signal):
        start = int((datetime.now(tz=timezone.utc) - timedelta(days=a.days)).timestamp() * 1000)
        n = w = 0
        ret_sum = 0.0
        lp = os.path.join(DATA, "paper_ledger.jsonl")
        for t_ms, r in calls:
            if t_ms < start:
                continue
            reg = ms.regime_at(t_ms)
            if reg not in RULES:
                continue
            handle, hz = RULES[reg]
            if r["handle"] != handle:
                continue
            lv = levels_at(ts, t_ms, r["direction"])
            if not lv:
                continue
            out = resolve(ts, lv["entry_ms"], lv["target"], lv["stop"], r["direction"], hz)
            rec = {"ts": t_ms, "date": r["published_at"][:10], "regime": reg, "handle": handle,
                   "direction": r["direction"], "entry": round(lv["entry"], 1),
                   "target": round(lv["target"], 1), "stop": round(lv["stop"], 1),
                   "horizon_h": hz, "result": out["result"], "ret": round(out["ret"], 5)}
            rec["receipt"] = hashlib.sha256(json.dumps(rec, sort_keys=True).encode()).hexdigest()[:16]
            open(lp, "a").write(json.dumps(rec) + "\n")
            n += 1
            w += out["result"] == "target"
            ret_sum += out["ret"]
        print(f"paper {a.days}d: {n} trades, {w} targets hit ({w/max(1,n):.0%}), total {ret_sum:+.2%}")


if __name__ == "__main__":
    main()
