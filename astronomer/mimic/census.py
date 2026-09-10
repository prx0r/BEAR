"""Data census: every dataset -> rows, span, size, integrity flags. Stdlib only.
Writes astronomer/data/CENSUS.json. Usage: python3 /tmp/opencode/census.py"""
import json, os, glob
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from collections import Counter

ROOT = "/home/ubuntu/BEAR"
out = {"generated_at": datetime.now(tz=timezone.utc).isoformat(), "raw": {}, "flags": []}


def parse_ts(tw, formats=("createdAt", "created_at")):
    ts = []
    for t in tw:
        for fk in formats:
            s = t.get(fk) if isinstance(t, dict) else None
            if s:
                try:
                    ts.append(int(parsedate_to_datetime(s).timestamp() * 1000))
                except Exception:
                    try:
                        ts.append(int(datetime.fromisoformat(s).timestamp() * 1000))
                    except Exception:
                        pass
                break
    return sorted(ts)


for fn in sorted(glob.glob(f"{ROOT}/astronomer/data/backtest/raw/*.json")):
    h = os.path.basename(fn)
    try:
        d = json.load(open(fn))
    except Exception as e:
        out["raw"][h] = {"error": type(e).__name__}
        continue
    tw = d if isinstance(d, list) else d.get("tweets", [])
    if isinstance(tw, dict) or not tw:
        out["raw"][h] = {"rows": 0 if not tw else "?", "note": "empty/dict",
                         "bytes": os.path.getsize(fn)}
        if isinstance(tw, list) and not tw:
            out["flags"].append(f"{h}: EMPTY STUB")
        continue
    ts = parse_ts(tw)
    ids = [str(t.get("id")) for t in tw if isinstance(t, dict)]
    dupes = len(ids) - len(set(ids))
    if not ts:
        out["raw"][h] = {"rows": len(tw), "dates": "UNPARSEABLE", "bytes": os.path.getsize(fn)}
        out["flags"].append(f"{h}: dates unparseable")
        continue
    f = datetime.fromtimestamp(ts[0] / 1000, tz=timezone.utc).date().isoformat()
    l = datetime.fromtimestamp(ts[-1] / 1000, tz=timezone.utc).date().isoformat()
    media = sum(1 for t in tw if isinstance(t, dict) and t.get("media"))
    out["raw"][h] = {"rows": len(tw), "from": f, "to": l,
                     "span_d": (ts[-1] - ts[0]) // 86400000,
                     "dupes": dupes, "media": media, "bytes": os.path.getsize(fn)}
    if dupes:
        out["flags"].append(f"{h}: {dupes} duplicate ids")

# normalized events
out["normalized"] = {}
for fn in sorted(glob.glob(f"{ROOT}/astronomer/data/core3/normalized/*_events.jsonl")):
    h = os.path.basename(fn).replace("_events.jsonl", "")
    n = 0
    kinds = Counter()
    with open(fn) as f:
        for line in f:
            try:
                r = json.loads(line)
            except Exception:
                continue
            n += 1
            kinds[r.get("semantic_kind")] += 1
    out["normalized"][h] = {"rows": n, "kinds": dict(kinds), "bytes": os.path.getsize(fn)}

# outcomes + prices + media + trials
for name, path in [("outcomes", f"{ROOT}/astronomer/data/core3/normalized/all_outcomes.json"),
                   ("outcomes_expanded", f"{ROOT}/astronomer/data/core3/normalized/all_outcomes_EXPANDED.json"),
                   ("strict", f"{ROOT}/astronomer/data/core3/normalized/strict_calls.json")]:
    try:
        d = json.load(open(path))
        out[name] = {"rows": len(d), "bytes": os.path.getsize(path)}
    except Exception as e:
        out[name] = {"error": type(e).__name__}
out["prices"] = {}
for fn in sorted(glob.glob(f"{ROOT}/astronomer/data/prices/*.json")) + sorted(glob.glob(f"{ROOT}/data/binance/*.json")):
    try:
        d = json.load(open(fn))
        rows = d if isinstance(d, list) else d.get("data", [])
        t0 = rows[0].get("timestamp", rows[0].get("open_time"))
        t1 = rows[-1].get("timestamp", rows[-1].get("open_time"))
        f0 = datetime.fromtimestamp(t0 / 1000, tz=timezone.utc).date().isoformat()
        f1 = datetime.fromtimestamp(t1 / 1000, tz=timezone.utc).date().isoformat()
        out["prices"][os.path.basename(fn)] = {"rows": len(rows), "from": f0, "to": f1}
    except Exception as e:
        out["prices"][os.path.basename(fn)] = {"error": type(e).__name__}
out["media_dirs"] = {}
for dp in sorted(glob.glob(f"{ROOT}/astronomer/data/media/*/")):
    try:
        fs = os.listdir(dp)
        out["media_dirs"][os.path.basename(dp.rstrip("/"))] = len(fs)
    except Exception:
        pass
json.dump(out, open(f"{ROOT}/astronomer/data/CENSUS.json", "w"), indent=1)
print("files:", len(out["raw"]), "| flags:", len(out["flags"]))
for fl in out["flags"][:20]:
    print(" FLAG:", fl)
