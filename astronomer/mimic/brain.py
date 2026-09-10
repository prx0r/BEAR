"""A2: brain API v0 — plain JSON on :8789 (no paywall; x402 front comes later).

Warms per-handle activity models by causal replay at startup (~2 min),
then serves frozen P(post next hour) + regime + STRAT-004 gate + trial stats.
Stdlib only. Usage: cd astronomer && nohup python3 -m mimic.brain >> data/brain.log 2>&1 &
"""
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mimic.features import MarketState
from mimic.online import AdaGradLogistic

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HANDLES = ["astronomer_zero", "Timeless_Crypto", "Trader_XO"]
PRIORS = {"astronomer_zero": 0.171, "Timeless_Crypto": 0.203, "Trader_XO": 0.070}


def load_posts(handle):
    from email.utils import parsedate_to_datetime
    d = json.load(open(os.path.join(ROOT, "astronomer", "data", "backtest", "raw", f"{handle}_2yr.json")))
    ts = sorted(int(parsedate_to_datetime(t["createdAt"]).timestamp() * 1000) for t in d["tweets"])
    return ts


print("warming models...", flush=True)
MS = MarketState()
MODELS = {}
for h in HANDLES:
    ts = load_posts(h)
    post_h = {datetime.fromtimestamp(t / 1000, tz=timezone.utc).replace(minute=0, second=0, microsecond=0) for t in ts}
    m = AdaGradLogistic(lr=0.2, prior_p=PRIORS[h])
    mem = {"hours_since_post": 24.0}
    hh = min(post_h)
    end = max(post_h)
    while hh <= end:
        y = 1 if hh in post_h else 0
        m.learn_one(MS.vector(int(hh.timestamp() * 1000), mem), y)
        mem["hours_since_post"] = 0.0 if y else mem["hours_since_post"] + 1.0
        hh += timedelta(hours=1)
    MODELS[h] = (m, {"hours_since_post": 24.0})
    print(f"  {h} warmed ({len(ts)} posts)", flush=True)

try:
    import glob
    TRIALS = {}
    for h in HANDLES:
        cands = sorted(glob.glob(os.path.join(ROOT, "astronomer", "data", "mimic_trials", f"{h}_*.json")),
                       key=os.path.getmtime)
        cands = [c for c in cands if "proveout" not in c and "discriminator" not in c and "bridge" not in c]
        if cands:
            TRIALS[h] = json.load(open(cands[-1]))
except Exception:
    TRIALS = {}


def gate_now():
    now_ms = int(time.time() * 1000)
    reg = MS.regime_at(now_ms)
    rule = {"DOWN": "follow Trader_XO 4h", "RANGE": "follow Timeless_Crypto 24h"}.get(reg, "NO TRADE (UP)")
    return {"regime": reg, "rule": rule, "strategy": "STRAT-004-CONFLUENCE",
            "generated_at": datetime.now(tz=timezone.utc).isoformat()}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path == "/health":
            return self.send({"ok": True, "handles": HANDLES})
        if u.path == "/gate":
            return self.send(gate_now())
        if u.path == "/signal/latest":
            h = q.get("handle", ["astronomer_zero"])[0]
            if h not in MODELS:
                return self.send({"error": f"unknown handle (try {HANDLES})"}, 404)
            m, mem = MODELS[h]
            now = datetime.now(tz=timezone.utc).replace(minute=0, second=0, microsecond=0)
            p = m.proba(MS.vector(int(now.timestamp() * 1000), mem))
            t = TRIALS.get(h, {})
            act = (t.get("activity") or {})
            sec_live = (act.get("sec") or {}).get("live", {})
            return self.send({
                "handle": h, "p_post_next_hour": round(p, 4),
                "gate": gate_now(),
                "mocklive_brier": (sec_live or {}).get("brier") if isinstance(sec_live, dict) else sec_live,
                "trial_seed": t.get("seed"), "trial_report": t.get("receipt", {}).get("sha256", "")[:12] if isinstance(t.get("receipt"), dict) else None,
                "model": "mimic-activity-v0", "note": "paper only, not financial advice",
            })
        return self.send({"error": "unknown route"}, 404)


if __name__ == "__main__":
    srv = HTTPServer(("127.0.0.1", 8789), H)
    print("brain live at http://127.0.0.1:8789", flush=True)
    srv.serve_forever()
