"""Round-trip reconstructor v0 — temporal entry→partial→flip chains (no thread linkage exists).

Cues (regex, audited — every link stores evidence text):
  ENTRY: shorted/longed in live time | I'm short/long again | flipped A into B (closes old, opens new)
         | long/short here | entered | position on | CALL direction with no open position
  PARTIAL: closed NN% | TP 1/2/3 (hit|here) | took profit | half | booked
  CLOSE: flat now | out of (the|my) | closed all | flipped (implies close of old side)
Prices: next-1h-candle close after post; MFE/MAE over holding window (direction-signed).
Output: data/roundtrips_{handle}.json. Usage: cd astronomer && python3 -m mimic.roundtrips [HANDLE]
"""
import bisect
import json
import os
import re
import sys
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ENTRY = re.compile(r"(?i)\b(shorted|longed)( in live time)?\b|i['’]m (short|long) again|flipped the (long|short) into a (short|long)|(?:^|\s)(long|short) here\b|entered\b|position (on|opened)|opened (a|the|my)?\s?(long|short)|bought|sold short\b")
PARTIAL = re.compile(r"(?i)\bclosed (\d{1,3}\s?%|just under half|half|almost all)|TP\s?[123]\b.{0,20}(here|hit)|took (some |most )?profit|booked|secured|partially closed|trimmed\b")
FLIP = re.compile(r"(?i)\bflipp\w+ the (long|short) into a (short|long)\b|flipp\w+ (long|short)\b")
CLOSE = re.compile(r"(?i)\bflat now\b|out of (the |my )?(long|short|position)|closed (all|everything|full)|no longer (long|short|in)\b")
DIRW = re.compile(r"(?i)\b(shorts?|longs?)\b")
NUMW = re.compile(r"\$?\d[\d,\.]*k?\b")
MAXHOLD_MS = 30 * 86400000


def guess_dir(text, default=None):
    shorts = len(re.findall(r"(?i)\bshorts?\b", text))
    longs = len(re.findall(r"(?i)\blong(?:s|ing)?\b", text))
    if shorts > longs:
        return -1
    if longs > shorts:
        return 1
    return default


def load_prices():
    d = json.load(open(os.path.join(ROOT, "astronomer", "data", "prices", "BTCUSDT_1h.json")))
    ts = sorted([(r["timestamp"], float(r["close"]), float(r["high"]), float(r["low"])) for r in d])
    return ts


def px_next(ts_full, t_ms):
    ts = [t for t, _, _, _ in ts_full]
    i = bisect.bisect_right(ts, t_ms)
    return ts_full[i] if i < len(ts_full) else None


def main():
    handle = sys.argv[1] if len(sys.argv) > 1 else "astronomer_zero"
    d = json.load(open(os.path.join(ROOT, "astronomer", "data", "backtest", "raw", f"{handle}_2yr.json")))
    def _ts(t):
        try:
            return int(parsedate_to_datetime(t["createdAt"]).timestamp() * 1000)
        except Exception:
            return -1
    tw = sorted((t for t in d["tweets"] if _ts(t) >= 0), key=_ts)
    ts_full = load_prices()
    trips, open_pos, n_partial = [], None, 0

    def close_pos(t_ms, text, why):
        global n_partial
        e = px_next(ts_full, open_pos["entry_ms"])
        x = px_next(ts_full, t_ms)
        if not e or not x:
            return None
        _, ec, _, _ = e
        _, xc, xh, xl = x
        m = open_pos["dir"]
        ret = (xc / ec - 1) * m
        win = [c for t, c, _, _ in ts_full if open_pos["entry_ms"] < t <= t_ms]
        mfe = (max(c for c in win) / ec - 1) * m if win else ret
        mae = (min(c for c in win) / ec - 1) * m if win else ret
        return {"asset": "BTC", "dir": "SHORT" if m < 0 else "LONG",
                "entry_ms": open_pos["entry_ms"], "entry_price": ec,
                "entry_text": open_pos["entry_text"][:200],
                "partials": open_pos["partials"], "exit_ms": t_ms, "exit_price": xc,
                "exit_why": why, "exit_text": text[:200],
                "return": round(ret, 5), "mfe": round(mfe, 5), "mae": round(mae, 5),
                "hold_h": round((t_ms - open_pos["entry_ms"]) / 3600000, 1)}

    for t in tw:
        text = t.get("text", "")
        try:
            ms = int(parsedate_to_datetime(t["createdAt"]).timestamp() * 1000)
        except Exception:
            continue
        m_flip = FLIP.search(text)
        if m_flip and open_pos:
            trips.append(close_pos(ms, text, "flip"))
            g = m_flip.group(2) or m_flip.group(3) or ""
            open_pos = {"dir": -1 if "short" in g.lower() else 1, "entry_ms": ms,
                        "entry_text": text, "partials": []}
            continue
        if open_pos and (CLOSE.search(text) or (PARTIAL.search(text) and
                re.search(r"(?i)\b(all|everything|full|flat|rest|remainder)\b", text))):
            trips.append(close_pos(ms, text, "close"))
            open_pos = None
            continue
        if open_pos and PARTIAL.search(text):
            pm = re.search(r"(\d{1,3})\s?%", text)
            frac = int(pm.group(1)) / 100.0 if pm else None
            if frac is None:
                low = text.lower()
                for pat, val in [("just under half", 0.45), ("almost all", 0.9),
                                 ("half", 0.5), ("quarter", 0.25), ("most", 0.75),
                                 ("rest", 1.0), ("remainder", 1.0), ("full", 1.0)]:
                    if pat in low:
                        frac = val
                        break
            open_pos["partials"].append({"ms": ms, "frac": frac, "text": text[:200]})
            n_partial += 1
            continue
        if not open_pos and (ENTRY.search(text) or (DIRW.search(text) and NUMW.search(text))):
            dd = guess_dir(text)
            if dd:
                open_pos = {"dir": dd, "entry_ms": ms, "entry_text": text, "partials": []}
            continue
        if open_pos and ms - open_pos["entry_ms"] > MAXHOLD_MS:
            trips.append(close_pos(ms, text, "maxhold-30d"))
            open_pos = None
            continue
    trips = [t for t in trips if t]
    json.dump({"handle": handle, "roundtrips": trips, "n_posts": len(tw)},
              open(os.path.join(ROOT, "astronomer", "data", f"roundtrips_{handle}.json"), "w"))
    wins = sum(1 for t in trips if t["return"] > 0)
    print(f"{handle}: posts={len(tw)} roundtrips={len(trips)} partials={n_partial} "
          f"win={wins}/{len(trips)} avg_ret={sum(t['return'] for t in trips)/max(1,len(trips)):+.3%} "
          f"avg_hold={sum(t['hold_h'] for t in trips)/max(1,len(trips)):.0f}h")


if __name__ == "__main__":
    main()
