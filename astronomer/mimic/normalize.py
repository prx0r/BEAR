"""Normalize new accounts: raw jul+aug -> events + strict supplement + outcomes.

- classify_event() per post (extractor_v2, evidence-grounded)
- event rows match normalized/*.jsonl schema (full raw text, media_files mapped)
- strict supplement rows match strict_calls.json (direction + asset only)
- outcomes via CANONICAL backtest.evaluate_event (venv python for httpx dep)
- NEVER touches canonical files: writes {h}_events.jsonl, strict_NEW.json, outcomes_NEW.json
Usage (venv!): ~/.venvs/bear/bin/python astronomer/mimic/normalize.py [HANDLE...]
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
DEFAULT_HANDLES = ["DaanCrypto", "Crypto_Chase", "DrProfitCrypto", "JA_Maartun",
                   "FrankAFetter", "Wild_Randomness", "CrypNuevo", "AxelAdlerJr"]


def iso(created):
    try:
        return parsedate_to_datetime(created).astimezone(timezone.utc).isoformat()
    except Exception:
        return None


def main():
    handles = sys.argv[1:] or DEFAULT_HANDLES
    try:
        from backtest import evaluate_event, load_all_prices
        from regime import load_regime_timeline
        from schemas import MarketEvent, SemanticKind, CallState, SignalDirection
        can_backtest = True
    except ImportError as e:
        print("backtest unavailable:", e)
        can_backtest = False
    if can_backtest:
        prices = load_all_prices()
        regime = load_regime_timeline()
    strict_new, outcomes_new = [], []
    for h in handles:
        tweets, seen = [], set()
        for suf in ("_jul2026", "_aug2026"):
            p = os.path.join(RAW, f"{h}{suf}.json")
            if not os.path.exists(p):
                continue
            d = json.load(open(p))
            for t in (d if isinstance(d, list) else d.get("tweets", [])):
                i = str(t.get("id"))
                if i in seen:
                    continue
                seen.add(i)
                tweets.append(t)
        rows = []
        for t in tweets:
            pid = str(t.get("id"))
            author = t.get("author") or {}
            try:
                evs = classify_event(t.get("text", ""), pid, t.get("author", {}).get("userName", h))
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
            dt = pub[:10]
            for j, e in enumerate(evs):
                rows.append({
                    "post_id": pid, "author_handle": h,
                    "author_id": str(author.get("id", "")),
                    "published_at": pub, "date": dt, "hour": int(pub[11:13]),
                    "is_reply": bool(t.get("isReply")),
                    "conversation_id": str(t.get("conversationId", pid)),
                    "event_id": f"evt_{pid}_{str(getattr(e, 'semantic_kind', 'view')).lower()}" + (f"_{j}" if j else ""),
                    "semantic_kind": str(getattr(e, "semantic_kind", "VIEW")),
                    "call_state": str(getattr(e, "call_state", "NONE")),
                    "asset": getattr(e, "asset", None),
                    "direction": getattr(e, "direction", None),
                    "text": t.get("text", ""), "text_length": len(t.get("text", "")),
                    "has_media": bool(media), "media_count": len(media),
                    "media_urls": [m.get("url") for m in media if m.get("url")],
                    "media_files": mfiles,
                    "evidence_count": len(getattr(e, "evidence", []) or []),
                })
        open(os.path.join(NORM, f"{h}_events.jsonl"), "w").write(
            "\n".join(json.dumps(r) for r in rows) + "\n")
        n_calls = 0
        for r in rows:
            if r["direction"] in ("BULLISH", "BEARISH") and r["asset"]:
                strict_new.append({"asset": r["asset"], "date": r["date"], "direction": r["direction"],
                                   "handle": h, "published_at": r["published_at"], "text": r["text"][:200]})
                n_calls += 1
                if can_backtest and r["semantic_kind"] == "CALL" and r["call_state"] in ("DIRECT", "CONDITIONAL"):
                    try:
                        me = MarketEvent(
                            event_id=r["event_id"], post_id=r["post_id"], author_id=r["author_id"],
                            author_handle=h, published_at=r["published_at"],
                            semantic_kind=SemanticKind(r["semantic_kind"]),
                            call_state=CallState(r["call_state"]), asset=r["asset"],
                            direction=SignalDirection(r["direction"]))
                        oc = evaluate_event(me, prices, regime)
                        if oc:
                            outcomes_new.append(oc.__dict__ if hasattr(oc, "__dict__") else dict(oc))
                    except Exception:
                        pass
        from collections import Counter
        print(f"{h}: tweets={len(tweets)} events={len(rows)} strict-like={n_calls} "
              f"kinds={dict(Counter(r['semantic_kind'] for r in rows).most_common(4))}")
    json.dump(strict_new, open(os.path.join(NORM, "strict_NEW.json"), "w"))
    json.dump(outcomes_new, open(os.path.join(NORM, "outcomes_NEW.json"), "w"))
    print(f"strict_NEW={len(strict_new)} outcomes_NEW={len(outcomes_new)}")


if __name__ == "__main__":
    main()
