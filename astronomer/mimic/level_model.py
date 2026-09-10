"""v0 level regressor: predict stated level (as log-ratio to spot) from market state.

Online AdaGrad linear regression on log(level/spot). Time split 70/30:
train online on first 70%, freeze, score frozen on last 30% (+ online continued
as comparator). Must beat SWING baseline (medAE 0.0136). Stdlib only.
Usage: cd astronomer && python3 -m mimic.level_model
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mimic.features import MarketState
from mimic.online import AdaGradLogistic  # reuse adaptive machinery via logit trick

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class AdaGradReg:
    def __init__(self, lr=0.1, l2=1e-5):
        self.w, self.g2, self.lr, self.l2 = {}, {}, lr, l2

    def pred(self, x):
        return sum(self.w.get(k, 0.0) * v for k, v in x.items())

    def learn_one(self, x, y):
        p = self.pred(x)
        err = p - y
        for k, v in x.items():
            self.g2[k] = self.g2.get(k, 0.0) + (err * v) ** 2
            step = self.lr / math.sqrt(self.g2[k] + 1e-8)
            self.w[k] = self.w.get(k, 0.0) - step * (err * v + self.l2 * self.w.get(k, 0.0))
        return p


def main():
    rows = [r for r in json.load(open(os.path.join(ROOT, "astronomer", "data", "levels_all.json")))
            if r["tier1"]]
    rows.sort(key=lambda r: r["ms"])
    cut = rows[int(len(rows) * 0.7)]["ms"]
    tr = [r for r in rows if r["ms"] < cut]
    te = [r for r in rows if r["ms"] >= cut]
    print(f"train={len(tr)} test={len(te)} split=70/30 time")
    ms = MarketState()
    mem = {"hours_since_post": 24.0}
    model = AdaGradReg(lr=0.1)
    for r in tr:
        x = ms.vector(r["ms"], mem)
        model.learn_one(x, math.log(r["ratio"]))
    import copy
    frozen = copy.deepcopy(model)
    ea = ef = []
    ea, ef = [], []
    for r in te:
        x = ms.vector(r["ms"], mem)
        ya = abs(math.exp(model.learn_one(x, math.log(r["ratio"]))) - r["ratio"])
        yf = abs(math.exp(frozen.pred(x)) - r["ratio"])
        ea.append(ya)
        ef.append(yf)
    ea.sort()
    ef.sort()
    print(f"test MAE: adaptive={sum(ea)/len(ea):.4f} medAE={ea[len(ea)//2]:.4f} | "
          f"frozen={sum(ef)/len(ef):.4f} medAE={ef[len(ef)//2]:.4f}")
    print("baselines to beat: swing MAE=0.0535 medAE=0.0136 | spot MAE=0.0752")
    json.dump({"n_test": len(te), "adaptive": {"mae": sum(ea) / len(ea), "medae": ea[len(ea) // 2]},
               "frozen": {"mae": sum(ef) / len(ef), "medae": ef[len(ef) // 2]},
               "baselines": {"swing": {"mae": 0.0535, "medae": 0.0136}, "spot": {"mae": 0.0752}}},
              open(os.path.join(ROOT, "astronomer", "data", "mimic_trials", "level_model_v0.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
