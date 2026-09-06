"""Paper trading engine for the regime-filtered death token strategy.

Runs the strategy daily (or on demand). Checks regime filter, computes death
scores, selects shorts, and tracks hypothetical PnL.

⚠️  RESEARCH-ONLY — NO LIVE TRADING ⚠️
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl

DATA_DIR = Path("/root/BEAR/data/binance")
STATE_PATH = Path("/root/BEAR/data/paper_state.json")

# Backtested optimal weights (Sharpe 1.11, win rate 71.4%)
DEATH_WEIGHTS = {
    "volume_death": 0.10,
    "deep_decline": 0.10,
    "reversal_8w": 0.15,
    "funding_pressure": 0.55,
    "momentum": 0.10,
}

# Assets to skip (blue-chips and quality categories)
BLUE_CHIPS = {
    "BTC", "ETH", "SOL", "HYPE", "BNB", "XRP", "ADA", "AVAX", "DOT",
    "LINK", "UNI", "AAVE", "MKR", "SNX", "CRV", "LDO", "PENDLE",
    "INJ", "TIA", "SEI", "NEAR", "FIL", "AR", "HBAR", "XLM",
    "ONDO", "PAXG", "TRX", "TON", "ICP", "ETC", "BCH", "LTC",
    "DASH", "XMR", "ZEC", "BSV",
}


def load_daily_data() -> dict[str, dict]:
    """Load all Binance daily OHLCV data as numpy arrays."""
    assets: dict[str, dict] = {}
    for f in sorted(DATA_DIR.glob("*.json")):
        symbol = f.stem.replace("USDT", "")
        with open(f) as fh:
            raw = json.load(fh)
        if len(raw) < 90:
            continue
        closes = np.array([d["close"] for d in raw], dtype=np.float64)
        volumes = np.array([d["volume"] for d in raw], dtype=np.float64)
        timestamps = np.array([d["open_time"] for d in raw], dtype=np.int64)
        if np.all(closes > 0):
            assets[symbol] = {
                "closes": closes,
                "volumes": volumes,
                "timestamps": timestamps,
                "n": len(raw),
            }
    return assets


def signal_volume_death(volumes: np.ndarray, window_peak: int = 90) -> np.ndarray:
    """Volume death: ratio of recent volume to peak volume (0-100)."""
    n = len(volumes)
    scores = np.full(n, np.nan)
    if n < window_peak:
        return scores

    peak_vol = np.full(n, np.nan)
    for i in range(window_peak - 1, n):
        w = volumes[max(0, i - window_peak + 1): i + 1]
        vv = w[np.isfinite(w)]
        peak_vol[i] = np.max(vv) if len(vv) > 0 else np.nan

    recent_vol = np.full(n, np.nan)
    for i in range(6, n):
        w = volumes[max(0, i - 6): i + 1]
        vv = w[np.isfinite(w)]
        recent_vol[i] = np.mean(vv) if len(vv) > 0 else np.nan

    ratio = np.where(
        np.isfinite(peak_vol) & np.isfinite(recent_vol) & (peak_vol > 0),
        recent_vol / peak_vol, np.nan,
    )
    return np.where(np.isfinite(ratio), np.clip((1.0 - ratio) * 100, 0, 100), np.nan)


def signal_deep_decline(closes: np.ndarray, peak_window: int = 180) -> np.ndarray:
    """Deep decline: drawdown from peak + 90d return (0-100)."""
    n = len(closes)
    scores = np.full(n, np.nan)
    if n < 90:
        return scores

    dd = np.full(n, np.nan)
    for i in range(peak_window - 1, n):
        w = closes[max(0, i - peak_window + 1): i + 1]
        vv = w[np.isfinite(w)]
        if len(vv) > 0 and vv.max() > 0:
            dd[i] = (closes[i] - vv.max()) / vv.max()

    ret_90d = np.full(n, np.nan)
    for i in range(89, n):
        if np.isfinite(closes[i]) and np.isfinite(closes[i - 89]) and closes[i - 89] > 0:
            ret_90d[i] = (closes[i] - closes[i - 89]) / closes[i - 89]

    dd_s = np.where(np.isfinite(dd), np.clip((-dd) * 100, 0, 100), np.nan)
    r90_s = np.where(np.isfinite(ret_90d), np.clip((-ret_90d) * 100, 0, 100), np.nan)
    return np.where(
        np.isfinite(dd_s) & np.isfinite(r90_s), 0.6 * dd_s + 0.4 * r90_s,
        np.where(np.isfinite(dd_s), dd_s, np.where(np.isfinite(r90_s), r90_s, np.nan)),
    )


def signal_funding_pressure(closes: np.ndarray, volumes: np.ndarray) -> np.ndarray:
    """Funding pressure proxy: vol stress + volume decline (0-100)."""
    n = len(closes)
    scores = np.full(n, np.nan)
    if n < 30:
        return scores

    returns = np.full(n, np.nan)
    for i in range(1, n):
        if np.isfinite(closes[i]) and np.isfinite(closes[i - 1]) and closes[i - 1] > 0:
            returns[i] = (closes[i] - closes[i - 1]) / closes[i - 1]

    vol_30d = np.full(n, np.nan)
    for i in range(29, n):
        w = returns[max(1, i - 29): i + 1]
        vv = w[np.isfinite(w)]
        vol_30d[i] = np.std(vv) if len(vv) > 5 else np.nan

    vol_ma = np.full(n, np.nan)
    for i in range(29, n):
        w = volumes[max(0, i - 29): i + 1]
        vv = w[np.isfinite(w)]
        vol_ma[i] = np.mean(vv) if len(vv) > 0 else np.nan

    vol_recent = np.full(n, np.nan)
    for i in range(6, n):
        w = volumes[max(0, i - 6): i + 1]
        vv = w[np.isfinite(w)]
        vol_recent[i] = np.mean(vv) if len(vv) > 0 else np.nan

    vol_ratio = np.where(
        np.isfinite(vol_ma) & np.isfinite(vol_recent) & (vol_ma > 0),
        vol_recent / vol_ma, np.nan,
    )
    vs = np.where(np.isfinite(vol_30d), np.clip(vol_30d * 500, 0, 100), np.nan)
    ds = np.where(np.isfinite(vol_ratio), np.clip((1.0 - vol_ratio) * 100, 0, 100), np.nan)
    return np.where(
        np.isfinite(vs) & np.isfinite(ds), 0.5 * vs + 0.5 * ds,
        np.where(np.isfinite(vs), vs, np.where(np.isfinite(ds), ds, np.nan)),
    )


def signal_momentum(closes: np.ndarray) -> np.ndarray:
    """7-day return as cross-sectional percentile (0-100)."""
    n = len(closes)
    scores = np.full(n, np.nan)
    if n < 7:
        return scores

    ret_7d = np.full(n, np.nan)
    for i in range(6, n):
        if np.isfinite(closes[i]) and np.isfinite(closes[i - 6]) and closes[i - 6] > 0:
            ret_7d[i] = (closes[i] - closes[i - 6]) / closes[i - 6]

    valid_mask = np.isfinite(ret_7d)
    if valid_mask.sum() < 10:
        return scores

    valid_vals = ret_7d[valid_mask]
    ranks = np.searchsorted(np.sort(valid_vals), valid_vals)
    percentile = ranks / len(valid_vals) * 100

    result = np.full(n, np.nan)
    result[valid_mask] = percentile
    return result


def signal_reversal_8w(closes: np.ndarray) -> np.ndarray:
    """8-week return as cross-sectional percentile (0-100)."""
    n = len(closes)
    scores = np.full(n, np.nan)
    if n < 56:
        return scores

    ret_8w = np.full(n, np.nan)
    for i in range(55, n):
        if np.isfinite(closes[i]) and np.isfinite(closes[i - 55]) and closes[i - 55] > 0:
            ret_8w[i] = (closes[i] - closes[i - 55]) / closes[i - 55]

    valid_mask = np.isfinite(ret_8w)
    if valid_mask.sum() < 10:
        return scores

    valid_vals = ret_8w[valid_mask]
    ranks = np.searchsorted(np.sort(valid_vals), valid_vals)
    percentile = ranks / len(valid_vals) * 100

    result = np.full(n, np.nan)
    result[valid_mask] = percentile
    return result


def compute_death_score_at(assets: dict[str, dict], t: int) -> list[dict]:
    """Compute death scores for all assets at time index t."""
    results = []
    for sym, data in assets.items():
        if sym in BLUE_CHIPS:
            continue
        n = data["n"]
        if t >= n or t < 90:
            continue

        c = data["closes"][:t + 1]
        v = data["volumes"][:t + 1]

        s_vol = signal_volume_death(v)
        s_dd = signal_deep_decline(c)
        s_rev = signal_reversal_8w(c)
        s_fund = signal_funding_pressure(c, v)
        s_mom = signal_momentum(c)

        vals = {
            "volume_death": s_vol[t] if np.isfinite(s_vol[t]) else None,
            "deep_decline": s_dd[t] if np.isfinite(s_dd[t]) else None,
            "reversal_8w": s_rev[t] if np.isfinite(s_rev[t]) else None,
            "funding_pressure": s_fund[t] if np.isfinite(s_fund[t]) else None,
            "momentum": s_mom[t] if np.isfinite(s_mom[t]) else None,
        }

        valid = {k: v for k, v in vals.items() if v is not None}
        if len(valid) < 3:
            continue

        score = sum(DEATH_WEIGHTS[k] * v for k, v in valid.items()) / sum(DEATH_WEIGHTS[k] for k in valid) * sum(DEATH_WEIGHTS.values())

        results.append({
            "symbol": sym,
            "score": round(score, 2),
            "signals": {k: round(v, 2) for k, v in valid.items()},
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results


class PaperTrader:
    """Paper trading engine for the regime-filtered death token strategy."""

    def __init__(self, initial_capital: float = 100.0):
        self.capital = initial_capital
        self.positions: list[dict] = []
        self.equity_curve: list[dict] = []
        self.trades: list[dict] = []
        self.regime_history: list[dict] = []

    def check_regime(self, btc_30d_return: float) -> str:
        """Returns 'SHORT', 'LONG', or 'SKIP' based on BTC 30d return.
        
        Optimal thresholds (backtested, Sharpe 2.65):
        - SHORT when BTC < 0% (flat/declining)
        - LONG when BTC > +5% (rallying)
        - SKIP in between
        """
        if btc_30d_return < 0.0:
            return "SHORT"
        elif btc_30d_return > 0.05:
            return "LONG"
        return "SKIP"

    def compute_btc_30d_return(self, assets: dict[str, dict], t: int) -> float | None:
        """Compute BTC 30d return at time index t."""
        btc = assets.get("BTC")
        if btc is None or t < 30 or t >= btc["n"]:
            return None
        c = btc["closes"]
        if c[t - 30] > 0:
            return (c[t] - c[t - 30]) / c[t - 30]
        return None

    def close_positions(self, assets: dict[str, dict], t: int) -> list[dict]:
        """Close positions that have been held for 30 days."""
        closed = []
        remaining = []
        for pos in self.positions:
            if t - pos["entry_t"] >= 30:
                sym = pos["symbol"]
                if sym in assets and t < assets[sym]["n"]:
                    exit_price = assets[sym]["closes"][t]
                    pnl = pos["size"] * (pos["entry_price"] - exit_price) / pos["entry_price"]
                    self.capital += pnl
                    trade = {
                        "symbol": sym,
                        "entry_t": pos["entry_t"],
                        "exit_t": t,
                        "entry_price": pos["entry_price"],
                        "exit_price": float(exit_price),
                        "pnl": round(pnl, 4),
                        "pnl_pct": round(pnl / pos["size"] * 100, 2),
                        "holding_days": t - pos["entry_t"],
                    }
                    self.trades.append(trade)
                    closed.append(trade)
                else:
                    remaining.append(pos)
            else:
                remaining.append(pos)
        self.positions = remaining
        return closed

    def open_shorts(self, scores: list[dict], t: int, assets: dict[str, dict], top_pct: float = 0.20) -> list[dict]:
        """If ACTIVE, short top 20% by death score."""
        if not scores:
            return []

        n_short = max(1, int(len(scores) * top_pct))
        top = scores[:n_short]

        opened = []
        per_position = self.capital / max(len(top), 1)

        for item in top:
            sym = item["symbol"]
            if sym not in assets or t >= assets[sym]["n"]:
                continue
            price = assets[sym]["closes"][t]
            if price <= 0:
                continue

            self.positions.append({
                "symbol": sym,
                "entry_t": t,
                "entry_price": float(price),
                "size": per_position,
                "death_score": item["score"],
            })
            opened.append({
                "symbol": sym,
                "entry_price": float(price),
                "size": round(per_position, 4),
                "death_score": item["score"],
            })

        return opened

    def open_longs(self, scores: list[dict], t: int, assets: dict[str, dict], top_pct: float = 0.10) -> list[dict]:
        """Long top 10% by death score (inverse strategy)."""
        if not scores:
            return []

        n_long = max(1, int(len(scores) * top_pct))
        top = scores[:n_long]

        opened = []
        per_position = self.capital / max(len(top), 1)

        for item in top:
            sym = item["symbol"]
            if sym not in assets or t >= assets[sym]["n"]:
                continue
            price = assets[sym]["closes"][t]
            if price <= 0:
                continue

            self.positions.append({
                "symbol": sym,
                "entry_t": t,
                "entry_price": float(price),
                "size": per_position,
                "death_score": item["score"],
                "direction": "long",
            })
            opened.append({
                "symbol": sym,
                "entry_price": float(price),
                "size": round(per_position, 4),
                "death_score": item["score"],
            })

        return opened

    def get_position_pnl(self, assets: dict[str, dict], t: int) -> float:
        """Compute unrealized PnL of open positions."""
        total = 0.0
        for pos in self.positions:
            sym = pos["symbol"]
            if sym in assets and t < assets[sym]["n"]:
                current_price = assets[sym]["closes"][t]
                direction = pos.get("direction", "short")
                if direction == "long":
                    pnl = pos["size"] * (current_price - pos["entry_price"]) / pos["entry_price"]
                else:
                    pnl = pos["size"] * (pos["entry_price"] - current_price) / pos["entry_price"]
                total += pnl
        return total

    def snapshot_equity(self, assets: dict[str, dict], t: int) -> float:
        """Current equity = capital + unrealized PnL."""
        unrealized = self.get_position_pnl(assets, t)
        return self.capital + unrealized

    def run(
        self,
        assets: dict[str, dict] | None = None,
        start_day: int = 365,
        end_day: int | None = None,
        rebalance_freq: int = 30,
    ) -> dict[str, Any]:
        """Run the paper trading simulation.

        Args:
            assets: Pre-loaded asset data. If None, loads from disk.
            start_day: First day to start trading (need history for signals).
            end_day: Last day to simulate. If None, uses all available data.
            rebalance_freq: Days between rebalances.

        Returns:
            Summary dict with regime, trades, equity curve, etc.
        """
        if assets is None:
            assets = load_daily_data()

        btc = assets.get("BTC")
        if btc is None:
            return {"error": "No BTC data available"}

        max_n = btc["n"]
        if end_day is None:
            end_day = max_n - 1

        self.__init__()  # reset

        for t in range(start_day, end_day + 1):
            # Close mature positions
            closed = self.close_positions(assets, t)

            # Check regime
            btc_ret_30d = self.compute_btc_30d_return(assets, t)
            regime = self.check_regime(btc_ret_30d) if btc_ret_30d is not None else "SKIP"

            self.regime_history.append({
                "day": t,
                "btc_30d_return": round(btc_ret_30d, 4) if btc_ret_30d is not None else None,
                "regime": regime,
            })

            # Rebalance every N days
            if (t - start_day) % rebalance_freq == 0:
                scores = compute_death_score_at(assets, t)
                if regime == "SHORT":
                    opened = self.open_shorts(scores, t, assets)
                elif regime == "LONG":
                    opened = self.open_longs(scores, t, assets)
                else:
                    opened = []

            # Snapshot equity
            equity = self.snapshot_equity(assets, t)
            self.equity_curve.append({
                "day": t,
                "equity": round(equity, 4),
                "capital": round(self.capital, 4),
                "n_positions": len(self.positions),
                "regime": regime,
            })

        # Compute summary stats
        eq_vals = [e["equity"] for e in self.equity_curve]
        if len(eq_vals) > 1:
            returns = [(eq_vals[i] - eq_vals[i - 1]) / eq_vals[i - 1] for i in range(1, len(eq_vals)) if eq_vals[i - 1] > 0]
            total_return = (eq_vals[-1] - eq_vals[0]) / eq_vals[0] if eq_vals[0] > 0 else 0
            mean_ret = np.mean(returns) if returns else 0
            std_ret = np.std(returns) if len(returns) > 1 else 1
            sharpe = (mean_ret / std_ret * np.sqrt(365)) if std_ret > 1e-10 else 0
        else:
            total_return = 0
            sharpe = 0

        win_trades = [t for t in self.trades if t["pnl"] > 0]
        win_rate = len(win_trades) / len(self.trades) * 100 if self.trades else 0

        active_days = sum(1 for r in self.regime_history if r["regime"] == "ACTIVE")
        skip_days = sum(1 for r in self.regime_history if r["regime"] == "SKIP")

        return {
            "summary": {
                "initial_capital": self.initial_capital if hasattr(self, "initial_capital") else 100,
                "final_equity": round(eq_vals[-1], 2) if eq_vals else 100,
                "total_return_pct": round(total_return * 100, 2),
                "sharpe_ratio": round(float(sharpe), 4),
                "win_rate_pct": round(win_rate, 1),
                "total_trades": len(self.trades),
                "total_days": end_day - start_day + 1,
                "active_days": active_days,
                "skip_days": skip_days,
            },
            "current_regime": self.regime_history[-1] if self.regime_history else None,
            "equity_curve": self.equity_curve,
            "trades": self.trades,
            "regime_history": self.regime_history,
        }

    def save_state(self, assets: dict[str, dict] | None = None, t: int | None = None) -> None:
        """Save current paper trading state to disk."""
        if assets is None:
            assets = load_daily_data()

        btc = assets.get("BTC")
        max_n = btc["n"] if btc else 0
        current_t = t if t is not None else max_n - 1

        # Compute current death scores
        current_scores = compute_death_score_at(assets, current_t) if current_t >= 90 else []
        btc_ret = self.compute_btc_30d_return(assets, current_t)
        regime = self.check_regime(btc_ret) if btc_ret is not None else "SKIP"

        state = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "capital": round(self.capital, 4),
            "positions": self.positions,
            "equity_curve_len": len(self.equity_curve),
            "trades_len": len(self.trades),
            "current_regime": regime,
            "btc_30d_return": round(btc_ret, 4) if btc_ret is not None else None,
            "btc_30d_threshold": 0.10,
            "current_scores_top10": current_scores[:10],
            "would_short": [s["symbol"] for s in current_scores[:max(1, int(len(current_scores) * 0.20))]],
        }

        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_PATH, "w") as f:
            json.dump(state, f, indent=2, default=str)
        print(f"Saved paper state to {STATE_PATH}")


def run_once() -> dict[str, Any]:
    """Run the paper trader once and save state."""
    assets = load_daily_data()
    btc = assets.get("BTC")
    if btc is None:
        return {"error": "No BTC data"}

    trader = PaperTrader(initial_capital=100.0)
    result = trader.run(assets)
    trader.save_state(assets)

    print(f"\n{'=' * 60}")
    print("PAPER TRADING RESULTS")
    print(f"{'=' * 60}")
    s = result["summary"]
    print(f"  Total Return:  {s['total_return_pct']:+.2f}%")
    print(f"  Sharpe Ratio:  {s['sharpe_ratio']:.4f}")
    print(f"  Win Rate:      {s['win_rate_pct']:.1f}%")
    print(f"  Total Trades:  {s['total_trades']}")
    print(f"  Active Days:   {s['active_days']} / {s['total_days']}")
    print(f"  Skip Days:     {s['skip_days']} / {s['total_days']}")
    print(f"  Final Equity:  ${s['final_equity']:.2f}")
    print(f"{'=' * 60}")

    cr = result["current_regime"]
    if cr:
        ret_str = f"{cr['btc_30d_return'] * 100:+.1f}%" if cr["btc_30d_return"] is not None else "N/A"
        print(f"  Current Regime: {cr['regime']} (BTC 30d: {ret_str}, threshold: +10%)")
        print(f"{'=' * 60}")

    return result


if __name__ == "__main__":
    run_once()
