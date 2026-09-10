"""Market-state feature vector at time t (stdlib only, causal).

Uses 1h closes (BTC/ETH/SOL) + BTC regime timeline. All lookups are
as-of-t: binary search for last candle with open_time <= t.
"""
import bisect
import json
import os
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "astronomer", "data")


def _load_closes(symbol: str) -> tuple[list[int], list[float]]:
    p = os.path.join(DATA, "prices", f"{symbol}USDT_1h.json")
    d = json.load(open(p))
    rows = d if isinstance(d, list) else d.get("data", d.get("candles", []))
    ts, cl = [], []
    for r in rows:
        if isinstance(r, dict):
            t = r.get("open_time", r.get("timestamp", r.get("time")))
            c = r.get("close")
        else:
            t, c = r[0], r[4]
        if isinstance(t, str):
            t = int(datetime.fromisoformat(t).replace(tzinfo=timezone.utc).timestamp() * 1000)
        ts.append(int(t))
        cl.append(float(c))
    return ts, cl


class MarketState:
    def __init__(self):
        self.btc_t, self.btc_c = _load_closes("BTC")
        self.eth_t, self.eth_c = _load_closes("ETH")
        self.m5_t, self.m5_c, self.m5_h, self.m5_l = self._load_5m("BTCUSDT")
        tl = os.path.join(DATA, "regime", "timeline.json")
        self.timeline = json.load(open(tl)) if os.path.exists(tl) else []
        self.fut = {}
        fdir = os.path.join(DATA, "futures")
        for fn in ["BTCUSDT_fundingRate_fund", "BTCUSDT_openInterestHist_1h",
                   "BTCUSDT_globalLongShortAccountRatio_15m",
                   "BTCUSDT_topLongShortAccountRatio_15m",
                   "BTCUSDT_takerlongshortRatio_15m"]:
            p = os.path.join(fdir, fn + ".json")
            if os.path.exists(p):
                rows = json.load(open(p))
                ts, vs = [], []
                for r in rows:
                    t = r.get("timestamp", r.get("fundingTime", r.get("funding_time")))
                    if t is None:
                        continue
                    v = r.get("fundingRate", r.get("sumOpenInterest", r.get("longShortRatio",
                        r.get("buySellRatio", r.get("topLongShortAccountRatio")))))
                    try:
                        ts.append(int(t)); vs.append(float(v))
                    except (TypeError, ValueError):
                        continue
                order = sorted(range(len(ts)), key=lambda i: ts[i])
                self.fut[fn] = ([ts[i] for i in order], [vs[i] for i in order])

    def _fut_at(self, key, t_ms, lookback_h=25):
        if key not in self.fut:
            return 0.0
        ts, vs = self.fut[key]
        i = bisect.bisect_right(ts, t_ms) - 1
        if i < 0:
            return 0.0
        return vs[i]

    def _ret(self, ts, cl, t_ms, hours):
        i = bisect.bisect_right(ts, t_ms) - 1
        j = bisect.bisect_right(ts, t_ms - hours * 3600_000) - 1
        if i <= 0 or j < 0 or cl[j] == 0:
            return 0.0
        return cl[i] / cl[j] - 1.0

    def _load_5m(self, symbol: str):
        import json as _j
        p = os.path.join(DATA, "prices", f"{symbol}_5m.json")
        if not os.path.exists(p):
            return [], [], [], []
        rows = _j.load(open(p))
        return ([r["open_time"] for r in rows], [r["close"] for r in rows],
                [r["high"] for r in rows], [r["low"] for r in rows])

    def _mret(self, t_ms, minutes):
        if not self.m5_t:
            return 0.0
        i = bisect.bisect_right(self.m5_t, t_ms) - 1
        j = bisect.bisect_right(self.m5_t, t_ms - minutes * 60_000) - 1
        if i <= 0 or j < 0 or self.m5_c[j] == 0:
            return 0.0
        return self.m5_c[i] / self.m5_c[j] - 1.0

    def _mrange(self, t_ms, minutes):
        if not self.m5_t:
            return 0.0
        i = bisect.bisect_right(self.m5_t, t_ms) - 1
        j = max(0, bisect.bisect_right(self.m5_t, t_ms - minutes * 60_000) - 1)
        if i <= j or self.m5_c[i] == 0:
            return 0.0
        return (max(self.m5_h[j:i + 1]) - min(self.m5_l[j:i + 1])) / self.m5_c[i]

    def regime_at(self, t_ms) -> str:
        if not self.timeline:
            return "RANGE"
        ts = [e.get("timestamp_ms", e.get("open_time", 0)) for e in self.timeline]
        i = bisect.bisect_right(ts, t_ms) - 1
        if i < 0:
            return "RANGE"
        return self.timeline[i].get("regime", self.timeline[i].get("state", "RANGE"))

    def vector(self, t_ms, mem: dict) -> dict[str, float]:
        """mem: hours_since_post, last_dir (+1/-1/0), bull_streak, bear_streak."""
        dt = datetime.fromtimestamp(t_ms / 1000, tz=timezone.utc)
        reg = self.regime_at(t_ms)
        M = __import__("math")
        ha = 2 * M.pi * (dt.hour + dt.minute / 60.0) / 24.0
        da = 2 * M.pi * dt.weekday() / 7.0
        return {
            "bias": 1.0,
            "btc_r1": self._ret(self.btc_t, self.btc_c, t_ms, 1),
            "btc_r4": self._ret(self.btc_t, self.btc_c, t_ms, 4),
            "btc_r24": self._ret(self.btc_t, self.btc_c, t_ms, 24),
            "eth_r4": self._ret(self.eth_t, self.eth_c, t_ms, 4),
            "eth_btc_24": self._ret(self.eth_t, self.eth_c, t_ms, 24)
            - self._ret(self.btc_t, self.btc_c, t_ms, 24),
            "reg_up": 1.0 if reg == "UP" else 0.0,
            "reg_down": 1.0 if reg == "DOWN" else 0.0,
            "hour_sin": M.sin(ha),
            "hour_cos": M.cos(ha),
            "dow_sin": M.sin(da),
            "dow_cos": M.cos(da),
            "weekend": 1.0 if dt.weekday() >= 5 else 0.0,
            "quiet_16_20": 1.0 if 16 <= dt.hour <= 20 else 0.0,
            "log_hours_since": __import__("math").log1p(mem.get("hours_since_post", 24.0)),
            "last_bull": 1.0 if mem.get("last_dir") == 1 else 0.0,
            "last_bear": 1.0 if mem.get("last_dir") == -1 else 0.0,
            "bull_streak": min(mem.get("bull_streak", 0), 5) / 5.0,
            "bear_streak": min(mem.get("bear_streak", 0), 5) / 5.0,
            "funding": max(-0.01, min(0.01, self._fut_at("BTCUSDT_fundingRate_fund", t_ms))) * 100.0,
            "ls_ratio": self._fut_at("BTCUSDT_globalLongShortAccountRatio_15m", t_ms) - 1.0,
            "top_ls": self._fut_at("BTCUSDT_topLongShortAccountRatio_15m", t_ms) - 1.0,
            "taker_bs": self._fut_at("BTCUSDT_takerlongshortRatio_15m", t_ms) - 1.0,
            "m5_r15": self._mret(t_ms, 15),
            "m5_r60": self._mret(t_ms, 60),
            "m5_range60": self._mrange(t_ms, 60),
        }
