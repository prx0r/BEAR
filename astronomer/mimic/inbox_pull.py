"""VPS drain for the multi-handle Cloudflare poll inbox (stdlib only, cron every minute).

Per handle (astronomer/mimic/handles.json):
1. Emits SHA256-committed P(post next hour) from that handle's activity model.
2. Drains {handle}/inbox from KV, replays elapsed hour buckets online,
   persists per-handle weights to data/mimic_state_{handle}.json.
3. Queues tweets to data/mimic_pending.jsonl (with handle) for strict labeling.

Env (from vault at runtime, never logged):
  CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_TOKEN, MIMIC_NS_ID
Usage:  * * * * *  cd /home/ubuntu/BEAR/astronomer && python3 -m mimic.inbox_pull
"""
import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mimic.features import MarketState
from mimic.online import AdaGradLogistic, ScoreTracker, commit

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HANDLES_FILE = os.path.join(ROOT, "astronomer", "mimic", "handles.json")
PENDING = os.path.join(ROOT, "astronomer", "data", "mimic_pending.jsonl")
PRIORS = {"astronomer_zero": 0.171}


def vault(name: str) -> str:
    if os.environ.get(name):
        return os.environ[name]
    try:
        r = subprocess.run(
            ["agent-vault", "vault", "credential", "get", name, "--vault", "oracle"],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except Exception:
        pass
    return ""


def kv(acct, ns, token, key, body=None):
    url = (f"https://api.cloudflare.com/client/v4/accounts/{acct}/storage/kv/namespaces/{ns}/values/{key}")
    req = urllib.request.Request(url, data=(body.encode() if body is not None else None),
                                 method="PUT" if body is not None else "GET",
                                 headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode()


def load_state(handle):
    p = os.path.join(ROOT, "astronomer", "data", f"mimic_state_{handle}.json")
    if os.path.exists(p):
        return json.load(open(p)), p
    return {"w": {}, "g2": {}, "mem": {"hours_since_post": 24.0}, "last_bucket": None, "n": 0, "brier": 0.0}, p


def run_handle(ms, h, acct, ns, token, now):
    st, path = load_state(h["handle"])
    model = AdaGradLogistic(lr=0.2, prior_p=PRIORS.get(h["handle"], 0.05))
    if st["w"]:
        model.w, model.g2 = st["w"], st["g2"]
    mem = st["mem"]

    p_next = model.proba(ms.vector(int(now.timestamp() * 1000), mem))
    digest = commit({"handle": h["handle"], "bucket": now.isoformat(), "p_post": round(p_next, 4)})

    try:
        inbox = json.loads(kv(acct, ns, token, f"{h['handle']}/inbox") or "[]")
    except Exception as e:
        return f"{h['handle']}: inbox read failed ({type(e).__name__})"
    new_posts = sorted(inbox, key=lambda t: t.get("id", ""))
    # exactly-once across key migrations / redeliveries: skip IDs already queued
    seen = set()
    if os.path.exists(PENDING):
        with open(PENDING) as f:
            for line in f:
                try:
                    seen.add(json.loads(line).get("id"))
                except Exception:
                    pass
    new_posts = [t for t in new_posts if t.get("id") not in seen]

    last = datetime.fromisoformat(st["last_bucket"]) if st["last_bucket"] else now - timedelta(hours=1)
    post_hours = set()
    for t in new_posts:
        try:
            post_hours.add(parsedate_to_datetime(t["createdAt"]).replace(minute=0, second=0, microsecond=0))
        except Exception:
            pass
    tr = ScoreTracker()
    hh = last + timedelta(hours=1)
    while hh <= now:
        y = 1 if hh in post_hours else 0
        tr.add(model.learn_one(ms.vector(int(hh.timestamp() * 1000), mem), y), y)
        mem["hours_since_post"] = 0.0 if y else mem.get("hours_since_post", 24.0) + 1.0
        hh += timedelta(hours=1)
    if tr.n:
        st["brier"] = (st["brier"] * st["n"] + tr.brier * tr.n) / (st["n"] + tr.n) if (st["n"] + tr.n) else tr.brier
        st["n"] += tr.n
    if new_posts:
        with open(PENDING, "a") as f:
            for t in new_posts:
                f.write(json.dumps({"handle": h["handle"], "id": t.get("id"), "createdAt": t.get("createdAt"),
                                    "text": t.get("text"), "media": bool(t.get("media"))}) + "\n")
        kv(acct, ns, token, f"{h['handle']}/inbox", "[]")
    st["w"], st["g2"], st["mem"] = model.w, model.g2, mem
    st["last_bucket"] = now.isoformat()
    json.dump(st, open(path, "w"))
    return (f"{h['handle']}: p_next={p_next:.3f} sha={digest[:8]} inbox={len(new_posts)} "
            f"replayed={tr.n} brier={st['brier']:.4f}")


def main():
    acct, ns, token = vault("CLOUDFLARE_ACCOUNT_ID"), os.environ.get("MIMIC_NS_ID", ""), vault("CLOUDFLARE_API_TOKEN")
    if not (acct and ns and token):
        print("missing CF env; dry-run only")
        return 2
    ms = MarketState()
    now = datetime.now(tz=timezone.utc).replace(minute=0, second=0, microsecond=0)
    for h in json.load(open(HANDLES_FILE))["handles"]:
        try:
            print(run_handle(ms, h, acct, ns, token, now))
        except Exception as e:
            print(f"{h['handle']}: ERROR {type(e).__name__}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
