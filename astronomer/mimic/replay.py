"""Offline causal replay: train exactly as the live bot would, on history.

Task A (activity): walk every hour 2026-04-08 -> 2026-09-07, predict P(post),
  then observe and update. Baselines: constant base-rate, hourxweekday.
Task D (direction): walk 461 strict calls in time order, predict P(BULLISH),
  then observe and update. Baseline: constant 0.78.
Usage: cd astronomer && python3 -m mimic.replay
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mimic.features import MarketState
from mimic.online import AdaGradLogistic, ScoreTracker

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, "astronomer", "data", "backtest", "raw", "astronomer_zero_2yr.json")
STRICT = os.path.join(ROOT, "astronomer", "data", "core3", "normalized", "strict_calls.json")


def main():
    ms = MarketState()
    tw = json.load(open(RAW))["tweets"]
    post_ts = sorted(int(parsedate_to_datetime(t["createdAt"]).timestamp() * 1000) for t in tw)
    post_hours = {datetime.fromtimestamp(t / 1000, tz=timezone.utc).replace(minute=0, second=0, microsecond=0) for t in post_ts}

    # --- Task A: activity ---
    model = AdaGradLogistic(lr=0.2, prior_p=623 / 3638)
    tr = ScoreTracker()
    const = ScoreTracker()
    mem = {"hours_since_post": 24.0, "last_dir": 0, "bull_streak": 0, "bear_streak": 0}
    h = min(post_hours)
    end = max(post_hours)
    n = 0
    base_p = 623 / 3638
    while h <= end:
        y = 1 if h in post_hours else 0
        t_ms = int(h.timestamp() * 1000)
        x = ms.vector(t_ms, mem)
        p = model.learn_one(x, y)
        tr.add(p, y)
        const.add(base_p, y)
        mem["hours_since_post"] = 0.0 if y else mem["hours_since_post"] + 1.0
        h += timedelta(hours=1)
        n += 1
    print(f"A activity hrs={n} model_brier={tr.brier:.4f} base_brier={const.brier:.4f} "
          f"model_logloss={tr.logloss:.4f} ece={tr.ece:.4f}")

    # --- Task D: direction ---
    strict = [s for s in json.load(open(STRICT)) if s["handle"] == "astronomer_zero"]
    strict.sort(key=lambda s: s["published_at"])
    dmodel = AdaGradLogistic(lr=0.3, prior_p=0.78)
    dtr = ScoreTracker()
    dconst = ScoreTracker()
    mem = {"hours_since_post": 0.0, "last_dir": 0, "bull_streak": 0, "bear_streak": 0}
    for s in strict:
        t_ms = int(datetime.fromisoformat(s["published_at"]).timestamp() * 1000)
        x = ms.vector(t_ms, mem)
        y = 1 if s["direction"] == "BULLISH" else 0
        p = dmodel.learn_one(x, y)
        dtr.add(p, y)
        dconst.add(0.78, y)
        if y:
            mem["bull_streak"] += 1
            mem["bear_streak"] = 0
        else:
            mem["bear_streak"] += 1
            mem["bull_streak"] = 0
        mem["last_dir"] = 1 if y else -1
        mem["hours_since_post"] = 0.0
    print(f"D direction n={len(strict)} model_brier={dtr.brier:.4f} base_brier={dconst.brier:.4f} "
          f"model_logloss={dtr.logloss:.4f} ece={dtr.ece:.4f}")
    print("D weights:", {k: round(v, 3) for k, v in sorted(dmodel.w.items(), key=lambda kv: -abs(kv[1]))[:8]})
    print("A weights:", {k: round(v, 3) for k, v in sorted(model.w.items(), key=lambda kv: -abs(kv[1]))[:8]})


if __name__ == "__main__":
    main()
