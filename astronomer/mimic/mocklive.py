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
import random
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
    try:
        s += [x for x in json.load(open(os.path.join(ROOT, "astronomer", "data", "core3", "normalized", "strict_NEW.json")))
              if x["handle"] == handle]
    except FileNotFoundError:
        pass
    if not s:
        # fallback: direction rows straight from normalized CALL events
        # (strict_calls.json only covers astro/Timeless/XO)
        try:
            fh = open(os.path.join(ROOT, "astronomer", "data", "core3", "normalized", f"{handle}_events.jsonl"))
        except FileNotFoundError:
            return []
        for l in fh:
            r = json.loads(l)
            if r.get("semantic_kind") == "CALL" and r.get("direction") in ("BULLISH", "BEARISH") and r.get("asset"):
                s.append({"handle": handle, "published_at": r["published_at"],
                          "direction": r["direction"], "asset": r["asset"], "_from": "events"})
    s.sort(key=lambda x: x["published_at"])
    out = []
    for x in s:
        try:
            t = int(datetime.fromisoformat(x["published_at"]).timestamp() * 1000)
        except ValueError:
            continue
        out.append((t, 1 if x["direction"] == "BULLISH" else 0))
    return out


def nearest3(train_vecs, x):
    scored = []
    for i, (v, _) in enumerate(train_vecs):
        d = sum((v.get(k, 0.0) - x.get(k, 0.0)) ** 2 for k in x)
        scored.append((1.0 / (1.0 + math.sqrt(d)), i))
    scored.sort(reverse=True)
    return [i for _, i in scored[:3]]


def struct_feats(text):
    t = (text or "").lower()
    return {"len": len(t) / 500.0,
            "cash": len(re.findall(r"\$[a-z]{2,10}\b", t)) / 5.0,
            "nums": len(re.findall(r"\d[\d,\.]*k?\b", t)) / 10.0,
            "emoji": len(re.findall(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]", t)) / 5.0,
            "bias": 1.0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--handle", required=True)
    ap.add_argument("--split", default="mid")
    ap.add_argument("--prior", type=float, default=None)
    ap.add_argument("--json-out", default=None)
    ap.add_argument("--save-weights", action="store_true")
    ap.add_argument("--seed", default="seed1")
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
    train_strict = [(t, y) for t, y in strict if t < cut]
    base_dir_train = sum(y for _, y in train_strict) / max(1, len(train_strict))
    act = AdaGradLogistic(lr=0.2, prior_p=a.prior or (sum(1 for t, _ in posts if t < cut) / max(1, (cut - t0) / 3600000)))
    dmodel = AdaGradLogistic(lr=0.3, prior_p=0.5)
    trail = []  # trailing (up to 20) train labels, causal recency memory
    disc = AdaGradLogistic(lr=0.1, prior_p=0.5)  # structural authorship: this handle vs others
    others = []
    for h in ["astronomer_zero", "Timeless_Crypto", "Trader_XO", "CryptoBheem"]:
        if h == a.handle:
            continue
        try:
            d = json.load(open(os.path.join(ROOT, "astronomer", "data", "backtest", "raw", f"{h}_2yr.json")))
        except FileNotFoundError:
            continue
        for t in d.get("tweets", []):
            try:
                ts = int(parsedate_to_datetime(t["createdAt"]).timestamp() * 1000)
            except Exception:
                continue
            if ts < cut:
                others.append(t.get("text", ""))
    random.seed(7)
    neg = random.sample(others, min(len(others), 2 * sum(1 for t, _ in posts if t < cut)))
    for t, txt in posts:
        if t < cut:
            disc.learn_one(struct_feats(txt), 1)
    for txt in neg:
        disc.learn_one(struct_feats(txt), 0)
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
    _train_resid = []
    for t, y in strict:
        if t < cut:
            x = ms.vector(t, mem)
            _train_resid.append(y - dmodel.proba(x))
            dmodel.learn_one(x, y)
            mem["bull_streak"] = mem.get("bull_streak", 0) + 1 if y else 0
            mem["bear_streak"] = mem.get("bear_streak", 0) + 1 if not y else 0
            mem["last_dir"] = 1 if y else -1
            trail.append(y)
            mem["trail"] = trail[-20:]
    # seed1.4: train-fitted intercept (frozen copy uses this; live uses trailing)
    frozen_bias_corr = sum(_train_resid) / max(1, len(_train_resid))
    live_resid = []
    # train-window base rates (frozen baselines)
    train_hours = max(1, int((cut - t0) / 3600000))
    base_act = sum(1 for t, _ in posts if t < cut) / train_hours
    base_dir = sum(y for t, y in strict if t < cut) / max(1, sum(1 for t, y in strict if t < cut))
    print(f"train: base_act={base_act:.3f} base_dir={base_dir:.3f} train_posts={len(train_vecs)}")

    # ---- Phase 2: mock-live (VALIDATION first 70%, SECRET last 30%) ----
    # Models update throughout (deployed behavior); verdicts use SECRET only.
    val_cut = cut + int((t1 - cut) * 0.7)
    frozen_act = copy.deepcopy(act)
    frozen_dir = copy.deepcopy(dmodel)
    tracks = {}
    for task in ("act", "dir"):
        for copying in ("live", "froz", "base"):
            for window in ("val", "sec"):
                tracks[(task, copying, window)] = ScoreTracker()
    j_ret, j_rerank, j_rnd, n_txt = 0.0, 0.0, 0.0, 0
    jv_ret, jv_rerank, jv_n = 0.0, 0.0, 0  # validation-window text scores
    use_rerank = False  # decided at val_cut: per-handle gate
    random.seed(7)
    mem_l = dict(mem)
    h = cut - (cut % 3600000)
    n_act = n_dir = 0
    while h <= t1:
        w = "val" if h < val_cut else "sec"
        y = 1 if h in post_set else 0
        x = ms.vector(h, mem_l)
        commit({"handle": a.handle, "mocklive": True, "bucket": h, "p_post": round(act.proba(x), 4)})
        tracks[("act", "live", w)].add(act.learn_one(x, y), y)
        tracks[("act", "froz", w)].add(frozen_act.proba(x), y)
        tracks[("act", "base", w)].add(base_act, y)
        n_act += 1
        if y:
            actual = next((txt for t, txt in posts if t - (t % 3600000) == h), "")
            if train_vecs and actual:
                top3 = nearest3(train_vecs, x)
                j = top3[0]
                jk1 = len(TOK(train_vecs[j][1]) & TOK(actual)) / max(1, len(TOK(train_vecs[j][1]) | TOK(actual)))
                rr = max(top3, key=lambda i: disc.proba(struct_feats(train_vecs[i][1])))
                jrr = len(TOK(train_vecs[rr][1]) & TOK(actual)) / max(1, len(TOK(train_vecs[rr][1]) | TOK(actual)))
                if w == "val":
                    jv_ret += jk1
                    jv_rerank += jrr
                    jv_n += 1
                    use_rerank = (jv_rerank / jv_n) > (jv_ret / jv_n)
                j_ret += jk1
                j_rerank += jrr if (use_rerank or w == "val") else jk1
                r = train_vecs[random.randrange(len(train_vecs))][1]
                j_rnd += len(TOK(r) & TOK(actual)) / max(1, len(TOK(r) | TOK(actual)))
                n_txt += 1
        mem_l["hours_since_post"] = 0.0 if y else mem_l.get("hours_since_post", 24.0) + 1.0
        h += 3600000
    for t, y in strict:
        if t >= cut:
            w = "val" if t < val_cut else "sec"
            x = ms.vector(t, mem_l)
            p_live_raw = dmodel.learn_one(x, y)
            p_froz_raw = frozen_dir.proba(x)
            live_corr = sum(live_resid[-20:]) / max(1, len(live_resid[-20:])) if len(live_resid) >= 5 else 0.0
            p_live = min(0.99, max(0.01, p_live_raw + live_corr))
            p_froz = min(0.99, max(0.01, p_froz_raw + frozen_bias_corr))
            live_resid.append(y - p_live_raw)
            tracks[("dir", "live", w)].add(p_live, y)
            tracks[("dir", "froz", w)].add(p_froz, y)
            tracks[("dir", "base", w)].add(base_dir, y)
            n_dir += 1
            mem_l.setdefault("trail", [])
            mem_l["trail"].append(y)
            mem_l["trail"] = mem_l["trail"][-20:]

    def rep(task, copying, window):
        s = tracks[(task, copying, window)]
        return {"brier": round(s.brier, 4), "n": s.n,
                "logloss": round(s.logloss, 4), "ece": round(s.ece, 4)}

    for window in ("val", "sec"):
        la, fa, ba = (rep("act", c, window)["brier"] for c in ("live", "froz", "base"))
        print(f"MOCK-LIVE activity {window} hrs={tracks[('act','live',window)].n}: "
              f"live={la:.4f} frozen={fa:.4f} base={ba:.4f}")
        ld, fd, bd = (rep("dir", c, window)["brier"] for c in ("live", "froz", "base"))
        print(f"MOCK-LIVE direction n={tracks[('dir','live',window)].n}: "
              f"live={ld:.4f} frozen={fd:.4f} base={bd:.4f}")
    from mimic.gates import check_gate
    sec = tracks[("dir", "live", "sec")]
    gate_pass, gate_reasons = check_gate(
        sec.brier, tracks[("dir", "base", "sec")].brier,
        tracks[("dir", "froz", "sec")].brier, sec.n)
    print(f"GATE direction: {'PASS' if gate_pass else 'FAIL'} {gate_reasons}")
    if n_txt:
        print(f"MOCK-LIVE text n={n_txt}: k1={j_ret/n_txt:.3f} rerank={j_rerank/n_txt:.3f} random={j_rnd/n_txt:.3f} "
              f"use_rerank={use_rerank} (val {jv_n}: k1={jv_ret/max(1,jv_n):.3f} rr={jv_rerank/max(1,jv_n):.3f})")

    report = {
        "seed": a.seed, "handle": a.handle, "split": cut_d.isoformat(), "n_posts": len(posts),
        "val_cut": datetime.fromtimestamp(val_cut / 1000, tz=timezone.utc).isoformat(),
        "train": {"base_act": base_act, "base_dir": base_dir, "train_posts": len(train_vecs)},
        "activity": {w: {c: rep("act", c, w) for c in ("live", "froz", "base")} for w in ("val", "sec")},
        "direction": {w: {c: rep("dir", c, w) for c in ("live", "froz", "base")} for w in ("val", "sec")},
        "gate": {"pass": gate_pass, "reasons": gate_reasons, "scope": "direction-secret"},
        "text": {"n": n_txt, "retrieval": j_ret / n_txt if n_txt else None,
                 "rerank": j_rerank / n_txt if n_txt else None,
                 "random": j_rnd / n_txt if n_txt else None,
                 "use_rerank": use_rerank},
    }

    if a.save_weights:
        wp = os.path.join(ROOT, "astronomer", "data", f"mimic_transfer_{a.handle}_dir.json")
        json.dump(dmodel.w, open(wp, "w"))
        print(f"weights -> {wp}")

    # ---- transfer: astro-fitted direction weights on this handle ----
    try:
        astro_w = json.load(open(os.path.join(ROOT, "astronomer", "data", "mimic_transfer_astronomer_zero_dir.json")))
        s_tr = ScoreTracker()
        n_tr = 0
        for t, y in strict:
            if t >= cut:
                x = ms.vector(t, mem)
                z = sum(astro_w.get(k, 0.0) * v for k, v in x.items())
                s_tr.add(1.0 / (1.0 + math.exp(-max(-60.0, min(60.0, z)))), y)
                n_tr += 1
        print(f"TRANSFER astro-> {a.handle}: brier={s_tr.brier:.4f} n={n_tr} (vs own frozen {tracks[('dir', 'froz', 'sec')].brier:.4f})")
    except FileNotFoundError:
        print("TRANSFER: no astro weight file (run --handle astronomer_zero --save-weights first)")

    if a.json_out:
        import hashlib
        import subprocess
        os.makedirs(os.path.dirname(a.json_out) or ".", exist_ok=True)
        body = json.dumps(report, sort_keys=True).encode()
        try:
            head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                                  cwd=ROOT, timeout=10).stdout.strip()
        except Exception:
            head = "nogit"
        seed_raw = open(os.path.join(ROOT, "astronomer", "mimic", "seed.json"), "rb").read() \
            if os.path.exists(os.path.join(ROOT, "astronomer", "mimic", "seed.json")) else b""
        report["receipt"] = {"sha256": hashlib.sha256(seed_raw + head.encode() + body).hexdigest(),
                             "git_head": head}
        json.dump(report, open(a.json_out, "w"), indent=1)
        print(f"report -> {a.json_out} sha={report['receipt']['sha256'][:12]}")


if __name__ == "__main__":
    main()
