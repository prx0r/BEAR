"""MOCK-LIVE harness: train on past, simulate live on future. No API calls.

Split by TIME (never shuffle). Phase 1 warms models on train window.
Phase 2 walks the mock-live window hour by hour, exactly like production:
predict -> commit -> reveal -> score -> update. Two copies scored:
  frozen (train weights, true OOS generalization)
  live   (keeps learning, = deployed performance)
Plus text-retrieval: nearest train post by market-state vs actual (Jaccard),
  baselined against a random train post.
And transfer: astro-fitted direction weights scored on this handle.

Usage: cd astronomer && python3 -m mimic.mocklive --handle Timeless_Crypto [--split 2025-06-02]
"""
import argparse
import copy
import json
import math
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mimic.features import MarketState
from mimic.online import AdaGradLogistic, ScoreTracker, commit

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOK = lambda t: set(re.findall(r"[a-z0-9$]+", (t or "").lower()))


def load_posts(handle):
    d = json.load(open(os.path.join(ROOT, "astronomer", "data", "backtest", "raw", f"{handle}_2yr.json")))
    out = []
    for t in d["tweets"]:
        try:
            ts = int(parsedate_to_datetime(t["createdAt"]).timestamp() * 1000)
        except Exception:
            continue
        out.append((ts, t.get("text", "")))
    out.sort(key=lambda r: r[0])
    return out


def load_strict(handle):
    s = [x for x in json.load(open(os.path.join(ROOT, "astronomer", "data", "core3", "normalized", "strict_calls.json")))
         if x["handle"] == handle]
    s.sort(key=lambda x: x["published_at"])
    out = []
    for x in s:
        try:
            t = int(datetime.fromisoformat(x["published_at"]).timestamp() * 1000)
        except ValueError:
            continue
        out.append((t, 1 if x["direction"] == "BULLISH" else 0))
    return out


def nearest(train_vecs, x):
    best, bj = 0, -1.0
    for i, (v, _) in enumerate(train_vecs):
        d = sum((v.get(k, 0.0) - x.get(k, 0.0)) ** 2 for k in x)
        s = 1.0 / (1.0 + math.sqrt(d))
        if s > bj:
            bj, best = s, i
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--handle", required=True)
    ap.add_argument("--split", default="mid")
    ap.add_argument("--prior", type=float, default=None)
    ap.add_argument("--json-out", default=None)
    a = ap.parse_args()

    ms = MarketState()
    posts = load_posts(a.handle)
    strict = load_strict(a.handle)
    t0, t1 = posts[0][0], posts[-1][0]
    if a.split == "mid":
        cut = posts[len(posts) // 2][0]
    else:
        cut = int(datetime.fromisoformat(a.split).replace(tzinfo=timezone.utc).timestamp() * 1000)
    cut_d = datetime.fromtimestamp(cut / 1000, tz=timezone.utc).date()
    print(f"{a.handle}: n={len(posts)} split={cut_d} train={((cut-t0)/86400000):.0f}d mocklive={((t1-cut)/86400000):.0f}d")

    # ---- Phase 1: train window ----
    act = AdaGradLogistic(lr=0.2, prior_p=a.prior or (sum(1 for t, _ in posts if t < cut) / max(1, (cut - t0) / 3600000)))
    dmodel = AdaGradLogistic(lr=0.3, prior_p=0.5)
    mem = {"hours_since_post": 24.0, "last_dir": 0, "bull_streak": 0, "bear_streak": 0}
    train_vecs = []  # (vector, text) of train posts for retrieval
    h = t0 - (t0 % 3600000)
    post_set = {t - (t % 3600000) for t, _ in posts}
    si = 0
    while h < cut:
        y = 1 if h in post_set else 0
        x = ms.vector(h, mem)
        act.learn_one(x, y)
        if y:
            for t, txt in posts:
                if t - (t % 3600000) == h:
                    train_vecs.append((x, txt))
                    break
        mem["hours_since_post"] = 0.0 if y else mem.get("hours_since_post", 24.0) + 1.0
        h += 3600000
    for t, y in strict:
        if t < cut:
            x = ms.vector(t, mem)
            dmodel.learn_one(x, y)
            mem["bull_streak"] = mem.get("bull_streak", 0) + 1 if y else 0
            mem["bear_streak"] = mem.get("bear_streak", 0) + 1 if not y else 0
            mem["last_dir"] = 1 if y else -1
    # train-window base rates (frozen baselines)
    train_hours = max(1, int((cut - t0) / 3600000))
    base_act = sum(1 for t, _ in posts if t < cut) / train_hours
    base_dir = sum(y for t, y in strict if t < cut) / max(1, sum(1 for t, y in strict if t < cut))
    print(f"train: base_act={base_act:.3f} base_dir={base_dir:.3f} train_posts={len(train_vecs)}")

    # ---- Phase 2: mock-live ----
    frozen_act = copy.deepcopy(act)
    frozen_dir = copy.deepcopy(dmodel)
    s_act_live, s_act_froz, s_act_base = ScoreTracker(), ScoreTracker(), ScoreTracker()
    s_dir_live, s_dir_froz, s_dir_base = ScoreTracker(), ScoreTracker(), ScoreTracker()
    j_ret, j_rnd, n_txt = 0.0, 0.0, 0
    import random
    random.seed(7)
    mem_l = dict(mem)
    h = cut - (cut % 3600000)
    n_act = n_dir = 0
    while h <= t1:
        y = 1 if h in post_set else 0
        x = ms.vector(h, mem_l)
        commit({"handle": a.handle, "mocklive": True, "bucket": h, "p_post": round(act.proba(x), 4)})
        s_act_live.add(act.learn_one(x, y), y)
        s_act_froz.add(frozen_act.proba(x), y)
        s_act_base.add(base_act, y)
        n_act += 1
        if y:
            actual = next((txt for t, txt in posts if t - (t % 3600000) == h), "")
            if train_vecs and actual:
                j = nearest(train_vecs, x)
                j_ret += len(TOK(train_vecs[j][1]) & TOK(actual)) / max(1, len(TOK(train_vecs[j][1]) | TOK(actual)))
                r = train_vecs[random.randrange(len(train_vecs))][1]
                j_rnd += len(TOK(r) & TOK(actual)) / max(1, len(TOK(r) | TOK(actual)))
                n_txt += 1
        mem_l["hours_since_post"] = 0.0 if y else mem_l.get("hours_since_post", 24.0) + 1.0
        h += 3600000
    for t, y in strict:
        if t >= cut:
            x = ms.vector(t, mem_l)
            s_dir_live.add(dmodel.learn_one(x, y), y)
            s_dir_froz.add(frozen_dir.proba(x), y)
            s_dir_base.add(base_dir, y)
            n_dir += 1

    print(f"MOCK-LIVE activity hrs={n_act}: live={s_act_live.brier:.4f} frozen={s_act_froz.brier:.4f} base={s_act_base.brier:.4f}")
    print(f"MOCK-LIVE direction n={n_dir}: live={s_dir_live.brier:.4f} frozen={s_dir_froz.brier:.4f} base={s_dir_base.brier:.4f} ece_live={s_dir_live.ece:.4f}")
    if n_txt:
        print(f"MOCK-LIVE text n={n_txt}: retrieval_jaccard={j_ret/n_txt:.3f} random_baseline={j_rnd/n_txt:.3f}")

    report = {
        "handle": a.handle, "split": cut_d.isoformat(), "n_posts": len(posts),
        "train": {"base_act": base_act, "base_dir": base_dir, "train_posts": len(train_vecs)},
        "activity": {"n": n_act, "live": s_act_live.brier, "frozen": s_act_froz.brier, "base": s_act_base.brier},
        "direction": {"n": n_dir, "live": s_dir_live.brier, "frozen": s_dir_froz.brier,
                      "base": s_dir_base.brier, "ece_live": s_dir_live.ece},
        "text": {"n": n_txt, "retrieval": j_ret / n_txt if n_txt else None,
                 "random": j_rnd / n_txt if n_txt else None},
    }

    # ---- transfer: astro-fitted direction weights on this handle ----
    try:
        astro_w = json.load(open(os.path.join(ROOT, "astronomer", "data", "mimic_transfer_astro_dir.json")))
        s_tr = ScoreTracker()
        n_tr = 0
        for t, y in strict:
            if t >= cut:
                x = ms.vector(t, mem)
                z = sum(astro_w.get(k, 0.0) * v for k, v in x.items())
                s_tr.add(1.0 / (1.0 + math.exp(-max(-60.0, min(60.0, z)))), y)
                n_tr += 1
        print(f"TRANSFER astro-> {a.handle}: brier={s_tr.brier:.4f} n={n_tr} (vs own frozen {s_dir_froz.brier:.4f})")
    except FileNotFoundError:
        print("TRANSFER: no astro weight file (run --handle astronomer_zero --save-weights first)")

    if a.json_out:
        os.makedirs(os.path.dirname(a.json_out) or ".", exist_ok=True)
        json.dump(report, open(a.json_out, "w"), indent=1)
        print(f"report -> {a.json_out}")


if __name__ == "__main__":
    main()
