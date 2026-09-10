"""Normalize new-range GOAT posts: raw 2yr -> events (append, dedupe by post_id).

Appends to {h}_events.jsonl only posts not already present. Same row schema as
normalize.py. Then rebuilds strict_NEW + outcomes_NEW additions via canonical
backtest.evaluate_event. Run with VENV python (httpx dep).
Usage: ~/.venvs/bear/bin/python astronomer/mimic/normalize_goats.py
"""
import json
import os
import sys
from datetime import timezone
from email.utils import parsedate_to_datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from extractor_v2 import classify_event

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
NORM = os.path.join(ROOT, "astronomer", "data", "core3", "normalized")
RAW = os.path.join(ROOT, "astronomer", "data", "backtest", "raw")
MEDIA = os.path.join(ROOT, "astronomer", "data", "media")
HANDLES = ["Trader_XO", "CryptoBheem"]  # Timeless complete; astro gap pending API


def iso(created):
    try:
        return parsedate_to_datetime(created).astimezone(timezone.utc).isoformat()
    except Exception:
        return None


def main():
    from backtest import evaluate_event, load_all_prices
    from regime import load_regime_timeline
    from schemas import MarketEvent, SemanticKind, CallState, SignalDirection
    prices = load_all_prices()
    regime = load_regime_timeline()
    new_events, new_strict, new_outcomes = 0, 0, 0
    strict_all = json.load(open(os.path.join(NORM, "strict_NEW.json")))
    outcomes_all = json.load(open(os.path.join(NORM, "outcomes_NEW.json")))
    for h in HANDLES:
        efn = os.path.join(NORM, f"{h}_events.jsonl")
        have = set()
        if os.path.exists(efn):
            for l in open(efn):
                try:
                    have.add(json.loads(l)["post_id"])
                except Exception:
                    pass
        else:
            have = set()
        d = json.load(open(os.path.join(RAW, f"{h}_2yr.json")))
        fresh = [t for t in d.get("tweets", []) if str(t.get("id")) not in have]
        print(f"{h}: {len(fresh)} new posts to classify")
        rows = []
        for t in fresh:
            pid = str(t.get("id"))
            author = t.get("author") or {}
            try:
                evs = classify_event(t.get("text", ""), pid, author.get("userName", h))
            except Exception:
                continue
            media = t.get("media") or []
            mfiles = []
            for m in media:
                base = os.path.basename((m.get("url") or "").split("?")[0])
                fp = os.path.join(MEDIA, h, base)
                if base and os.path.exists(fp):
                    mfiles.append(f"astronomer/data/media/{h}/{base}")
            pub = iso(t.get("createdAt", ""))
            if not pub:
                continue
            for j, e in enumerate(evs):
                rows.append({
                    "post_id": pid, "author_handle": h, "author_id": str(author.get("id", "")),
                    "published_at": pub, "date": pub[:10], "hour": int(pub[11:13]),
                    "is_reply": bool(t.get("isReply")),
                    "conversation_id": str(t.get("conversationId", pid)),
                    "event_id": f"evt_{pid}_{str(getattr(e, 'semantic_kind', 'view')).lower()}" + (f"_{j}" if j else ""),
                    "semantic_kind": str(getattr(e, "semantic_kind", "VIEW")),
                    "call_state": str(getattr(e, "call_state", "NONE")),
                    "asset": getattr(e, "asset", None), "direction": getattr(e, "direction", None),
                    "text": t.get("text", ""), "text_length": len(t.get("text", "")),
                    "has_media": bool(media), "media_count": len(media),
                    "media_urls": [m.get("url") for m in media if m.get("url")],
                    "media_files": mfiles,
                    "evidence_count": len(getattr(e, "evidence", []) or [])})
        if rows:
            with open(efn, "a") as f:
                for r in rows:
                    f.write(json.dumps(r) + "\n")
        new_events += len(rows)
        for r in rows:
            if r["direction"] in ("BULLISH", "BEARISH") and r["asset"]:
                strict_all.append({"asset": r["asset"], "date": r["date"], "direction": r["direction"],
                                   "handle": h, "published_at": r["published_at"], "text": r["text"][:200]})
                new_strict += 1
                if r["semantic_kind"] == "CALL" and r["call_state"] in ("DIRECT", "CONDITIONAL"):
                    try:
                        me = MarketEvent(event_id=r["event_id"], post_id=r["post_id"], author_id=r["author_id"],
                                         author_handle=h, published_at=r["published_at"],
                                         semantic_kind=SemanticKind(r["semantic_kind"]),
                                         call_state=CallState(r["call_state"]), asset=r["asset"],
                                         direction=SignalDirection(r["direction"]))
                        oc = evaluate_event(me, prices, regime)
                        if oc:
                            d = oc.__dict__ if hasattr(oc, "__dict__") else dict(oc)
                            d["author_handle"] = h
                            outcomes_all.append(d)
                            new_outcomes += 1
                    except Exception:
                        pass
        print(f"{h}: +{len(rows)} events")
    json.dump(strict_all, open(os.path.join(NORM, "strict_NEW.json"), "w"))
    json.dump(outcomes_all, open(os.path.join(NORM, "outcomes_NEW.json"), "w"))
    print(f"TOTAL new: events={new_events} strict={new_strict} outcomes={new_outcomes}")


if __name__ == "__main__":
    main()
