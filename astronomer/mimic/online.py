"""Online logistic (AdaGrad/FTRL-style) + proper-score tracking + commit log.

Stdlib only. learn_one/predict_proba_one mirror River's API.
"""
import hashlib
import json
import math
import os
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PRED_LOG = os.path.join(ROOT, "astronomer", "data", "mimic_predictions.jsonl")


class AdaGradLogistic:
    def __init__(self, lr=0.5, l1=1e-4, l2=1e-5, prior_p: float | None = None):
        self.w: dict[str, float] = {}
        self.g2: dict[str, float] = {}
        self.lr, self.l1, self.l2 = lr, l1, l2
        if prior_p is not None:
            # start at the base rate instead of p=0.5 (rare events)
            self.w["bias"] = math.log(prior_p / (1 - prior_p))

    def proba(self, x: dict[str, float]) -> float:
        z = sum(self.w.get(k, 0.0) * v for k, v in x.items())
        return 1.0 / (1.0 + math.exp(-max(-60.0, min(60.0, z))))

    def learn_one(self, x: dict[str, float], y: int) -> float:
        p = self.proba(x)
        err = p - y
        for k, v in x.items():
            self.g2[k] = self.g2.get(k, 0.0) + (err * v) ** 2
            step = self.lr / math.sqrt(self.g2[k] + 1e-8)
            w = self.w.get(k, 0.0) - step * (err * v + self.l2 * self.w.get(k, 0.0))
            # L1 truncation
            if abs(w) < self.l1 * step:
                w = 0.0
            else:
                w -= math.copysign(self.l1 * step, w)
            self.w[k] = w
        return p


class ScoreTracker:
    """Running Brier + log-loss + 10-bin ECE, strictly online."""

    def __init__(self):
        self.n = 0
        self.brier = 0.0
        self.logloss = 0.0
        self.bins: list[list[int]] = [[0, 0] for _ in range(10)]  # [pos, tot]

    def add(self, p: float, y: int):
        p = min(0.999, max(0.001, p))
        self.n += 1
        self.brier += ((p - y) ** 2 - self.brier) / self.n
        self.logloss += ((-math.log(p) if y else -math.log(1 - p)) - self.logloss) / self.n
        b = min(9, int(p * 10))
        self.bins[b][1] += 1
        self.bins[b][0] += y

    @property
    def ece(self) -> float:
        e = 0.0
        for pos, tot in self.bins:
            if tot:
                e += tot / self.n * abs(pos / tot - (self.bins.index([pos, tot]) + 0.5) / 10)
        return e


def commit(pred: dict, nonce: str | None = None) -> str:
    """SHA256 commit of a prediction BEFORE the outcome window. Returns hex digest."""
    nonce = nonce or os.urandom(8).hex()
    body = json.dumps(pred, sort_keys=True) + "|" + nonce
    digest = hashlib.sha256(body.encode()).hexdigest()
    rec = {"committed_at": time.time(), "sha256": digest, "nonce": nonce, "pred": pred}
    os.makedirs(os.path.dirname(PRED_LOG), exist_ok=True)
    with open(PRED_LOG, "a") as f:
        f.write(json.dumps(rec) + "\n")
    return digest
