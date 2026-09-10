"""A1: authorship discriminator prototype — astro vs other traders, stdlib only.

Hashed char-trigram logistic (AdaGrad, reuse online.py). Split BY TIME:
first 70% of each author's posts train, last 30% test (no leakage).
Reports accuracy + Brier vs 50% baseline. A test win = style signal exists,
greenlight for the full discriminator (reranker over retrieval candidates).
Usage: cd astronomer && python3 -m mimic.discriminator [--json-out PATH]
"""
import argparse
import hashlib
import json
import os
import re
import sys
from email.utils import parsedate_to_datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mimic.online import AdaGradLogistic, ScoreTracker

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
POS_HANDLE = "astronomer_zero"
NEG_HANDLES = ["Timeless_Crypto", "Trader_XO", "CryptoBheem"]
DIM = 2 ** 11
EPOCHS = 3
STRUCT_ONLY = os.environ.get("STRUCT_ONLY", "") == "1"


def feats(text):
    t = (text or "").lower()
    v = {}
    if not STRUCT_ONLY:
        chars = re.sub(r"\s+", " ", t)
        for i in range(len(chars) - 2):
            h = int(hashlib.md5(chars[i:i + 3].encode()).hexdigest(), 16) % DIM
            v[f"g{h}"] = v.get(f"g{h}", 0) + 1
    n = max(1, len(t))
    v["len"] = len(t) / 500.0
    v["cash"] = len(re.findall(r"\$[a-z]{2,10}\b", t)) / 5.0
    v["nums"] = len(re.findall(r"\d[\d,\.]*k?\b", t)) / 10.0
    v["emoji"] = len(re.findall(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]", t)) / 5.0
    v["bias"] = 1.0
    return v


def load(handle):
    p = os.path.join(ROOT, "astronomer", "data", "backtest", "raw", f"{handle}_2yr.json")
    d = json.load(open(p))
    tw = d.get("tweets", d if isinstance(d, list) else [])
    rows = []
    for t in tw:
        try:
            ts = int(parsedate_to_datetime(t["createdAt"]).timestamp())
        except Exception:
            continue
        rows.append((ts, t.get("text", "")))
    rows.sort()
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json-out", default=None)
    a = ap.parse_args()
    pos = [(t, x, 1) for t, x in load(POS_HANDLE)]
    neg = []
    for h in NEG_HANDLES:
        neg += [(t, x, 0) for t, x in load(h)]
    # balance: subsample negatives to 2x positives, evenly across authors/time
    neg.sort()
    step = max(1, len(neg) // (2 * len(pos)))
    neg = neg[::step][:2 * len(pos)]
    # stratified-by-author time split (global time split degenerates when
    # authors cover different date ranges)
    def split(rows):
        rows = sorted(rows)
        c = int(len(rows) * 0.7)
        return rows[:c], rows[c:]
    ptr, pte = split(pos)
    ntr, nte = split(neg)
    train, test = ptr + ntr, pte + nte
    test.sort()
    cutdate = test[0][0]
    import datetime as dt
    print(f"train={len(train)} test={len(test)} split={dt.datetime.fromtimestamp(cutdate, dt.timezone.utc).date()}")

    model = AdaGradLogistic(lr=0.1, prior_p=0.33)
    for _ in range(EPOCHS):
        for _, x, y in train:
            model.learn_one(feats(x), y)
    tr = ScoreTracker()
    acc = 0
    for _, x, y in test:
        p = model.proba(feats(x))
        tr.add(p, y)
        acc += (p >= 0.5) == y
    base = sum(y for _, _, y in test) / len(test)
    print(f"test acc={acc/len(test):.2f} (majority={max(base,1-base):.2f}) brier={tr.brier:.4f} ece={tr.ece:.4f}")
    top = sorted(model.w.items(), key=lambda kv: -abs(kv[1]))[:6]
    print("top weights:", [(k, round(v, 2)) for k, v in top])
    verdict = "SIGNAL" if acc / len(test) > max(base, 1 - base) + 0.05 and tr.brier < 0.25 else "WEAK"
    print("verdict:", verdict)
    if a.json_out:
        json.dump({"train": len(train), "test": len(test), "acc": acc / len(test),
                   "majority": max(base, 1 - base), "brier": tr.brier, "ece": tr.ece,
                   "verdict": verdict}, open(a.json_out, "w"), indent=1)
        print("report ->", a.json_out)


if __name__ == "__main__":
    main()
