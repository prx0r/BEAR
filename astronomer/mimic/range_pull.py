"""Backfill a date range into an existing *_2yr.json (dedupe by id, $0.001/page).
Usage: range_pull.py HANDLE SINCE(YYYY-MM-DD) UNTIL(YYYY-MM-DD)  (2-week chunks)
Logs every call. Key via GETXAPI_KEY env (never printed)."""
import json, os, sys, time, urllib.request, urllib.parse
from datetime import date, timedelta

BASE = "https://api.getxapi.com"
KEY = os.environ.get("GETXAPI_KEY", "")
OUT = "/home/ubuntu/BEAR/astronomer/data/backtest/raw"
LOG = "/home/ubuntu/BEAR/astronomer/data/budgets/fetch_log.jsonl"


def call(path, params, tries=4):
    url = BASE + path + "?" + urllib.parse.urlencode(params)
    last = None
    for a in range(tries):
        try:
            req = urllib.request.Request(url, headers={"Authorization": f"Bearer {KEY}"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception as e:
            last = e
            time.sleep(3 * (a + 1))
    raise last


def main():
    handle, since_s, until_s = sys.argv[1], sys.argv[2], sys.argv[3]
    since = date.fromisoformat(since_s)
    until = date.fromisoformat(until_s)
    fn = os.path.join(OUT, f"{handle}_2yr.json")
    d = json.load(open(fn))
    have = {str(t.get("id")) for t in d.get("tweets", [])}
    new, calls = 0, 0
    cur = since
    while cur < until:
        nxt = min(cur + timedelta(days=14), until)
        cursor = None
        for _ in range(25):
            p = {"q": f"from:{handle} since:{cur.isoformat()} until:{nxt.isoformat()}", "product": "Latest"}
            if cursor:
                p["cursor"] = cursor
            try:
                r = call("/twitter/tweet/advanced_search", p)
            except Exception as e:
                print(f"  {cur}: {type(e).__name__}"); break
            calls += 1
            open(LOG, "a").write(json.dumps({"ts": time.time(), "endpoint": "advanced_search",
                "handle": handle, "since": cur.isoformat(), "n": len(r.get("tweets", [])), "cost": 0.001}) + "\n")
            for t in r.get("tweets", []):
                if str(t.get("id")) not in have:
                    have.add(str(t.get("id")))
                    d["tweets"].append(t)
                    new += 1
            if not r.get("has_more") or not r.get("next_cursor"):
                break
            cursor = r["next_cursor"]
        cur = nxt
    json.dump(d, open(fn, "w"))
    print(f"{handle}: +{new} posts in {calls} calls (${calls*0.001:.3f}), total={len(d['tweets'])}")


if __name__ == "__main__":
    main()
