"""Prove-out: 20 paper posts end-to-end (frozen seed1.4 weights), scored.

For each astro mock-window strict event WITH a 24h outcome: predict direction
with frozen weights -> build full post (template text + game-plan mermaid +
SVG chart, levels from price structure) -> score model-direction 24h return
vs the actual post's direction return. Wilson CIs on both.
Output: data/proveout_astro.json + data/proveout_posts/ (txt/mmd/svg per post).
Usage: cd astronomer && python3 -m mimic.proveout [--n 20]
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
from mimic.post import render as render_post
from mimic.diagram import gameplan

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
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--handle", default="astronomer_zero")
    ap.add_argument("--full", action="store_true")
    a = ap.parse_args()
    H = a.handle
    ms = MarketState()
    w = json.load(open(os.path.join(ROOT, "astronomer", "data", f"mimic_transfer_{H}_dir.json")))

    strict = [x for x in json.load(open(os.path.join(
        ROOT, "astronomer", "data", "core3", "normalized", "strict_calls.json")))
        if x["handle"] == H]
    try:
        strict += [x for x in json.load(open(os.path.join(
            ROOT, "astronomer", "data", "core3", "normalized", "strict_NEW.json")))
            if x["handle"] == H]
    except FileNotFoundError:
        pass
    strict.sort(key=lambda x: x["published_at"])
    out = json.load(open(os.path.join(ROOT, "astronomer", "data", "core3", "normalized",
                                      "all_outcomes_EXPANDED.json")))
    try:
        _new = json.load(open(os.path.join(ROOT, "astronomer", "data", "core3", "normalized",
                                           "outcomes_NEW.json")))
        _have = {o.get("event_id") for o in out}
        out = out + [o for o in _new if o.get("event_id") not in _have]
    except FileNotFoundError:
        pass
    ret24 = {}
    for o in out:
        if o.get("author_handle") == H and o.get("return_24h") is not None:
            ret24[o["event_id"]] = o["return_24h"]
    evts = {}
    for l in open(os.path.join(ROOT, "astronomer", "data", "core3", "normalized",
                               f"{H}_events.jsonl")):
        if not l.strip():
            continue
        r = json.loads(l)
        evts[(r["author_handle"], r["published_at"])] = r

    mem = {"hours_since_post": 0.0, "last_dir": 0, "bull_streak": 0, "bear_streak": 0, "trail": []}
    posts, mw, mh, aw, ah, n = [], 0, 0, 0, 0, 0
    ddir = os.path.join(ROOT, "astronomer", "data", f"proveout_posts_{H}")
    os.makedirs(ddir, exist_ok=True)
    for s in strict:
        if not a.full and n >= a.n:
            break
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
        ev = evts.get((s["handle"], s["published_at"]))
        if not ev:
            continue
        x = ms.vector(t, mem)
        z = sum(w.get(k, 0.0) * v for k, v in x.items())
        p = 1.0 / (1.0 + math.exp(-max(-60.0, min(60.0, z))))
        model_dir = "BULLISH" if p >= 0.5 else "BEARISH"
        # levels from 5m structure around t
        m5 = ms.m5_t and ms.m5_c
        entry = None
        if m5:
            i = bisect.bisect_right(ms.m5_t, t)
            if i < len(ms.m5_t):
                entry = ms.m5_c[i]
                win = ms.m5_c[max(0, i - 288):i] or [entry]
                rg = max(win) - min(win)
                up = model_dir == "BULLISH"
                sig = {"asset": s.get("asset") or "BTC", "direction": model_dir,
                       "entry": round(entry, 0), "target": round(entry + rg * 0.5, 0) if up else round(entry - rg * 0.5, 0),
                       "invalidation": round(entry - rg * 0.5, 0) if up else round(entry + rg * 0.5, 0),
                       "regime": ms.regime_at(t), "p_bullish": round(p, 2), "horizon_h": 24}
                txt = render_post(sig)
                mm = gameplan(sig)
                pid = ev["post_id"]
                open(os.path.join(ddir, f"{pid}.txt"), "w").write(txt or "REFUSED")
                open(os.path.join(ddir, f"{pid}.mmd"), "w").write(mm or "REFUSED")
        # score vs actual outcome Funk
        eo = [o for o in out if o.get("author_handle") == H
              and o.get("return_24h") is not None]
        match = None
        for o in out:
            if o.get("event_id") == ev["event_id"] and o.get("return_24h") is not None:
                match = o
                break
        if match and entry:
            # model-direction return ~= sign-flip actual if disagree
            agree = model_dir == s["direction"]
            mr = match["return_24h"] if agree else -match["return_24h"]
            oos = t >= CUT
            mw += mr > 0; mh += 1
            aw += match["return_24h"] > 0; ah += 1
            n += 1
            posts.append({"post_id": ev["post_id"], "published_at": s["published_at"],
                          "oos": oos,
                          "model_dir": model_dir, "actual_dir": s["direction"],
                          "model_ret24": round(mr, 5), "actual_ret24": match["return_24h"]})
        if s["direction"] == "BULLISH":
            mem["bull_streak"] += 1; mem["bear_streak"] = 0
        else:
            mem["bear_streak"] += 1; mem["bull_streak"] = 0
        mem["last_dir"] = 1 if s["direction"] == "BULLISH" else -1
        mem.setdefault("trail", []).append(1 if s["direction"] == "BULLISH" else 0)
        mem["trail"] = mem["trail"][-20:]
    def _split(key, val):
        o = [p for p in posts if p["oos"] == (key == "oos")]
        w = sum(1 for p in o if p[val] > 0)
        return {"wins": w, "n": len(o),
                "rate": round(w / max(1, len(o)), 3), "ci": wilson(w, len(o))}

    rep = {"n": n, "model": {"wins": mw, "n": mh, "rate": round(mw / max(1, mh), 3),
                             "ci": wilson(mw, mh)},
           "actual": {"wins": aw, "n": ah, "rate": round(aw / max(1, ah), 3),
                      "ci": wilson(aw, ah)},
           "model_oos": _split("oos", "model_ret24"), "model_ins": _split("ins", "model_ret24"),
           "actual_oos": _split("oos", "actual_ret24"), "actual_ins": _split("ins", "actual_ret24"),
           "posts": posts}
    json.dump(rep, open(os.path.join(ROOT, "astronomer", "data", f"proveout_{H}.json"), "w"), indent=1)
    print(f"prove-out n={n}: MODEL {mw}/{mh}={mw/max(1,mh):.0%} CI{wilson(mw,mh)} vs "
          f"ACTUAL {aw}/{ah}={aw/max(1,ah):.0%} CI{wilson(aw,ah)}")
    print(f"artifacts: {ddir} ({len(posts)} posts txt+mmd)")


if __name__ == "__main__":
    main()
