"""Recover return labels for asset-None CALLs with unambiguous single symbols.

Protocol (documented deviation: daily candles, so 24h/7d horizons only):
  entry = first daily candle with open_time > publication (next-day entry)
  ret24 = direction-signed (close[entry+1d]/close[entry]-1)
  ret168 = direction-signed (close[entry+7d]/close[entry]-1)
Writes NEW files only; canonical all_outcomes.json untouched.
Usage: cd astronomer && python3 -m mimic.expand_labels
"""
import json
import os
import re
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
NORM = os.path.join(ROOT, "astronomer", "data", "core3", "normalized")


def load_daily(sym):
    p = os.path.join(ROOT, "data", "binance", f"{sym}USDT.json")
    if not os.path.exists(p):
        return None
    d = json.load(open(p))
    rows = d if isinstance(d, list) else d.get("data", [])
    return sorted(rows, key=lambda r: r["open_time"])


def main():
    need = {}
    for h in ["Timeless_Crypto", "Trader_XO", "astronomer_zero", "CryptoBheem", "eliz883"]:
        for l in open(os.path.join(NORM, f"{h}_events.jsonl")):
            r = json.loads(l)
            if r.get("semantic_kind") == "CALL" and r.get("direction") in ("BULLISH", "BEARISH") and not r.get("asset"):
                need[r["post_id"]] = r
    rawsym = {}
    for h in ["Timeless_Crypto", "Trader_XO", "astronomer_zero", "CryptoBheem", "eliz883"]:
        p = os.path.join(ROOT, "astronomer", "data", "backtest", "raw", f"{h}_2yr.json")
        if not os.path.exists(p):
            continue
        for t in json.load(open(p)).get("tweets", []):
            pid = str(t.get("id"))
            if pid in need:
                syms = {s.get("text", "").upper() if isinstance(s, dict) else str(s).upper()
                        for s in ((t.get("entities") or {}).get("symbols") or [])}
                cash = set(re.findall(r"\$([A-Z]{2,10})\b", need[pid].get("text", "")))
                rawsym[pid] = syms | cash

    daily_cache, new_outcomes, mapping = {}, [], {}
    for pid, r in need.items():
        syms = rawsym.get(pid, set())
        if len(syms) != 1:
            continue
        sym = next(iter(syms))
        if sym in ("BTC", "ETH", "SOL", "TAO", "HYPE") or not os.path.exists(
                os.path.join(ROOT, "data", "binance", f"{sym}USDT.json")):
            continue
        if sym not in daily_cache:
            daily_cache[sym] = load_daily(sym)
        rows = daily_cache[sym]
        try:
            pub = int(datetime.fromisoformat(r["published_at"]).timestamp() * 1000)
        except ValueError:
            continue
        idx = next((i for i, c in enumerate(rows) if c["open_time"] > pub), None)
        if idx is None or idx + 7 >= len(rows):
            continue
        entry = rows[idx]["close"]
        if entry <= 0:
            continue
        mult = 1.0 if r["direction"] == "BULLISH" else -1.0
        ret24 = round(mult * (rows[idx + 1]["close"] / entry - 1), 6)
        ret168 = round(mult * (rows[idx + 7]["close"] / entry - 1), 6)
        new_outcomes.append({
            "event_id": r["event_id"], "asset": sym, "author_handle": r["author_handle"],
            "direction": r["direction"], "entry_price": entry, "method": "daily-next-day",
            "return_24h": ret24, "return_7d": ret168,
            "direction_correct_24h": ret24 > 0, "direction_correct_7d": ret168 > 0,
        })
        mapping[pid] = {"asset": sym, "method": "single-symbol entities+cashtag"}

    base = json.load(open(os.path.join(NORM, "all_outcomes.json")))
    have = {o["event_id"] for o in base}
    fresh = [o for o in new_outcomes if o["event_id"] not in have]
    json.dump(base + fresh, open(os.path.join(NORM, "all_outcomes_EXPANDED.json"), "w"))
    json.dump(mapping, open(os.path.join(NORM, "asset_recovery_map.json"), "w"), indent=1)
    from collections import Counter
    print(f"recovered: {len(fresh)} (base {len(base)} -> expanded {len(base)+len(fresh)})")
    print("assets:", dict(Counter(o["asset"] for o in fresh)))
    w24 = sum(1 for o in fresh if o["direction_correct_24h"])
    print(f"24h win: {w24}/{len(fresh)} = {w24/max(1,len(fresh)):.0%}")


if __name__ == "__main__":
    sys.exit(main())
