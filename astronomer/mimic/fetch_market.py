"""Free market-data backbone: 5m klines + futures histories (funding, OI, LS).
All endpoints public, no key. Paced (≤30 req/min), resumable (skip-if-exists).
~450 calls total, $0. Usage: cd astronomer && python3 -m mimic.fetch_market
"""
import json
import os
import sys
import time
import urllib.request

FAPI = "https://fapi.binance.com"
SPOT = "https://api.binance.com"
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PX = os.path.join(ROOT, "astronomer", "data", "prices")
FUT = os.path.join(ROOT, "astronomer", "data", "futures")

DAY = 86_400_000


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url), timeout=30) as r:
        return json.load(r)


def save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(data, open(path, "w"))
    print(f"  saved {path} ({len(data)} rows)")


def klines_5m(symbol, start_ms, end_ms):
    """Full 5m history via forward pagination. 1000/call."""
    out, s = [], start_ms
    while True:
        u = (f"{SPOT}/api/v3/klines?symbol={symbol}&interval=5m&limit=1000"
             f"&startTime={s}&endTime={end_ms}")
        batch = get(u)
        if not batch:
            break
        out += batch
        s = batch[-1][0] + 300_000
        if len(batch) < 1000 or s >= end_ms:
            break
        time.sleep(0.25)
    return [{"open_time": c[0], "open": float(c[1]), "high": float(c[2]),
             "low": float(c[3]), "close": float(c[4]), "volume": float(c[5])} for c in out]


def fut_hist(path, symbol, period="1h", limit=500, start=None, end=None):
    """Generic /futures/data paginator keyed by startTime."""
    out, s = [], start
    while True:
        u = f"{FAPI}{path}?symbol={symbol}&limit={limit}"
        if period:
            u += f"&period={period}"
        if s:
            u += f"&startTime={s}"
        if end:
            u += f"&endTime={end}"
        batch = get(u)
        if not batch:
            break
        out += batch
        if len(batch) < limit:
            break
        last = batch[-1]
        s = (last.get("timestamp") or last.get("fundingTime") or last.get("funding_time")) + 1
        if s >= (end or 9e15):
            break
        time.sleep(0.25)
    return out


def main():
    t1 = 1725148800000  # 2024-09-01
    t2 = int(time.time() * 1000)
    for sym in ["BTCUSDT", "ETHUSDT"]:
        p = os.path.join(PX, f"{sym}_5m.json")
        if os.path.exists(p):
            print(f"  skip {p} (exists)")
        else:
            print(f"klines 5m {sym}...")
            save(p, klines_5m(sym, t1, t2))
    specs = [
        # (name, path, period, start_arg) — OI/LS histories retain ~30d only
        ("fundingRate", "/fapi/v1/fundingRate", None, t1),
        ("openInterestHist", "/futures/data/openInterestHist", "1h", t2 - 30 * DAY),
        ("globalLongShortAccountRatio", "/futures/data/globalLongShortAccountRatio", "15m", t2 - 30 * DAY),
        ("topLongShortAccountRatio", "/futures/data/topLongShortAccountRatio", "15m", t2 - 30 * DAY),
        ("takerlongshortRatio", "/futures/data/takerlongshortRatio", "15m", t2 - 30 * DAY),
    ]
    for sym in ["BTCUSDT", "ETHUSDT"]:
        for name, path, period, start in specs:
            p = os.path.join(FUT, f"{sym}_{name}_{period or 'fund'}.json")
            if os.path.exists(p):
                print(f"  skip {p} (exists)")
                continue
            print(f"{name} {sym}...")
            try:
                save(p, fut_hist(path, sym, period, 1000, start, t2))
            except Exception as e:
                print(f"  FAIL {name} {sym}: {type(e).__name__}")
            time.sleep(0.5)
    print("DONE")


if __name__ == "__main__":
    main()
