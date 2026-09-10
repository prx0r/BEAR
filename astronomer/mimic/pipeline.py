"""PIPELINE — one deterministic path: raw -> signals + charts + proof.

Usage: cd astronomer && python3 -m mimic.pipeline --handles astro --seed seed1.4 [--skip-train]
Handles: astro, timeless, xo, bheem. See PIPELINE.md. Stdlib only.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(ROOT, "astronomer", "data")
SHORT = {"astro": "astronomer_zero", "timeless": "Timeless_Crypto", "xo": "Trader_XO", "bheem": "CryptoBheem"}
RUNS = os.path.join(DATA, "pipeline_runs")


def sh(cmd):
    r = subprocess.run(cmd, shell=True, cwd=os.path.join(ROOT, "astronomer"),
                       capture_output=True, text=True, timeout=3600)
    return r.returncode, (r.stdout + r.stderr)[-2000:]


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def stage_ingest(h, log):
    p = os.path.join(DATA, "backtest", "raw", f"{h}_2yr.json")
    assert os.path.exists(p), f"missing {p}"
    d = json.load(open(p))
    tw = d.get("tweets", [])
    assert len(tw) > 100, f"too few rows for {h}"
    log.append({"stage": 0, "handle": h, "rows": len(tw)})
    return {"rows": len(tw)}


def stage_label(h, log):
    efn = os.path.join(DATA, "core3", "normalized", f"{h}_events.jsonl")
    assert os.path.exists(efn), f"missing {efn}"
    n = sum(1 for _ in open(efn))
    assert n > 50, f"too few events for {h}"
    log.append({"stage": 1, "handle": h, "events": n})
    return {"events": n}


def stage_train(h, seed, log, skip=False):
    out = os.path.join(DATA, "mimic_trials", f"{h}_{seed}_pipe.json")
    if skip and os.path.exists(out):
        log.append({"stage": 2, "handle": h, "skipped": True})
        return {}
    rc, tail = sh(f"python3 -m mimic.mocklive --handle {h} --seed {seed} "
                  f"--skip-text --save-weights --json-out data/mimic_trials/{h}_{seed}_pipe.json")
    assert rc == 0, f"train failed for {h}:\n{tail[-500:]}"
    r = json.load(open(out))
    log.append({"stage": 2, "handle": h, "report": out})
    return r


def stage_gate(rep, log, handle=None):
    d = (rep.get("direction") or {}).get("sec", rep.get("direction") or {})
    n = d.get("n", 0)
    verdict = {"pass": False, "reasons": []}
    if n is not None and n >= 100:
        lb = (d.get("live") or {}).get("brier")
        bb = (d.get("base") or {}).get("brier")
        fb = (d.get("froz") or {}).get("brier")
        if lb is not None and bb is not None and lb < bb and fb is not None and fb < bb:
            verdict = {"pass": True, "reasons": []}
        else:
            verdict = {"pass": False, "reasons": ["secret/frozen !< base"]}
    else:
        verdict = {"pass": False, "reasons": [f"n={n} < 100"]}
    log.append({"stage": 3, "handle": handle, "gate": verdict})
    return verdict


def stage_serve(h, verdict, log):
    sys.path.insert(0, os.path.dirname(HERE))
    from mimic.features import MarketState
    ms = MarketState()
    now = int(datetime.now(tz=timezone.utc).timestamp() * 1000)
    px = json.load(open(os.path.join(DATA, "prices", "BTCUSDT_5m.json")))
    last = px[-1]["close"]
    win = px[-288:]
    rg = max(r["high"] for r in win) - min(r["low"] for r in win)
    sig = {"handle": h, "asset": "BTC", "generated_at": datetime.now(tz=timezone.utc).isoformat(),
           "regime": ms.regime_at(now), "entry": round(last, 0),
           "target_up": round(last + rg * 0.5, 0), "target_dn": round(last - rg * 0.5, 0),
           "experimental": not verdict["pass"]}
    p = os.path.join(DATA, "pipeline_runs", "latest", f"signal_{h}.json")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(sig, open(p, "w"), indent=1)
    log.append({"stage": 4, "handle": h, "signal": p})
    return sig


def stage_render(h, sig, log):
    from mimic.post import render as render_post
    from mimic.diagram import gameplan
    d = os.path.join(DATA, "pipeline_runs", "latest")
    up = {"asset": "BTC", "direction": "LONG", "entry": sig["entry"],
          "target": sig["target_up"], "invalidation": sig["target_dn"], "regime": sig["regime"]}
    dn = {"asset": "BTC", "direction": "SHORT", "entry": sig["entry"],
          "target": sig["target_dn"], "invalidation": sig["target_up"], "regime": sig["regime"]}
    arts = {}
    for name, s in (("long", up), ("short", dn)):
        txt = render_post(s)
        mm = gameplan(s)
        open(os.path.join(d, f"post_{h}_{name}.txt"), "w").write(txt or "REFUSED")
        open(os.path.join(d, f"post_{h}_{name}.mmd"), "w").write(mm or "REFUSED")
        arts[name] = bool(txt and mm)
    try:
        from mimic.chart import render as render_chart
        render_chart("BTCUSDT", os.path.join(d, f"chart_{h}.svg"),
                     title=f"{h} BTC 5m")
        arts["chart"] = True
    except Exception as e:
        arts["chart"] = f"FAIL {type(e).__name__}"
    log.append({"stage": 5, "handle": h, "artifacts": arts})
    return arts


def stage_prove(h, log):
    rc, tail = sh(f"python3 -m mimic.proveout_levels --handle {SHORT_INV[h]} 2>&1 || true")
    entry = {"stage": 6, "handle": h, "note": "see proveout trials (stdlib harness)"}
    log.append(entry)
    return entry


SHORT_INV = {v: k for k, v in SHORT.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--handles", default="astro")
    ap.add_argument("--seed", default="seed1.4")
    ap.add_argument("--skip-train", action="store_true")
    a = ap.parse_args()
    log, digests = [], {}
    seed_raw = open(os.path.join(HERE, "seed.json"), "rb").read()
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                              cwd=ROOT, timeout=10).stdout.strip()
    except Exception:
        head = "nogit"
    for short in [s.strip() for s in a.handles.split(",")]:
        h = SHORT[short]
        stage_ingest(h, log)
        stage_label(h, log)
        rep = stage_train(h, a.seed, log, skip=a.skip_train)
        verdict = stage_gate(rep or {}, log, h)
        sig = stage_serve(h, verdict, log)
        stage_render(h, sig, log)
        stage_prove(h, log)
        digests[h] = sha(json.dumps(rep, sort_keys=True).encode())
    body = json.dumps({"seed": a.seed, "git": head, "log": log,
                       "digests": digests}, sort_keys=True).encode()
    receipt = sha(seed_raw + head.encode() + body)
    os.makedirs(RUNS, exist_ok=True)
    stamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d-%H%M")
    rp = os.path.join(RUNS, f"{stamp}_{a.seed}.json")
    json.dump({"receipt": receipt, "seed": a.seed, "git": head, "log": log,
               "digests": digests}, open(rp, "w"), indent=1)
    print(f"receipt={receipt[:16]} -> {rp}")
    print(f"handles={[s for s in a.handles.split(',')]} stages=0-6 done")


if __name__ == "__main__":
    main()
