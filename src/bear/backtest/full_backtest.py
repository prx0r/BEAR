"""Full backtest: 3 trades on dead tokens + quality spot.

TRADE 1: Squeeze Long
  When: death high + funding negative + price starting to rise + UP→UP
  Hold: 1-7 days (short horizon)
  Exit: funding normalizes, OI drops, or time stop

TRADE 2: Reload Short
  When: squeeze exhausted, death still high, funding reset, price rolling over
  Hold: 2-8 weeks
  Exit: death drops, price recovers, or time stop

TRADE 3: Quality RSI Outperformers (spot long)
  When: UP→UP regime, asset showing strength
  Hold: while trend intact
  Exit: trend breaks

Each trade has its own sizing and risk management.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

DATA_DIR = Path("/root/BEAR/data/binance")

BLUE_CHIPS = {"BTC", "ETH", "SOL", "HYPE", "BNB", "XRP", "ADA", "AVAX", "DOT",
              "LINK", "UNI", "AAVE", "MKR", "SNX", "CRV", "LDO", "PENDLE"}


def load_assets() -> dict[str, dict]:
    assets = {}
    for f in sorted(DATA_DIR.glob("*.json")):
        sym = f.stem.replace("USDT", "")
        with open(f) as fh:
            raw = json.load(fh)
        if len(raw) < 100:
            continue
        closes = np.array([d["close"] for d in raw], dtype=np.float64)
        volumes = np.array([d["volume"] for d in raw], dtype=np.float64)
        timestamps = np.array([d["open_time"] for d in raw], dtype=np.int64)
        if np.all(closes > 0):
            assets[sym] = {"closes": closes, "volumes": volumes, "timestamps": timestamps, "n": len(raw)}
    return assets


def compute_death(closes: np.ndarray, volumes: np.ndarray) -> np.ndarray:
    n = len(closes)
    score = np.full(n, np.nan)
    for i in range(89, n):
        vol_7d = np.mean(volumes[max(0, i-6):i+1])
        vol_peak = np.max(volumes[max(0, i-89):i+1])
        if vol_peak > 0:
            score[i] = (1.0 - vol_7d / vol_peak) * 100
    return score


def compute_funding_proxy(closes: np.ndarray, volumes: np.ndarray, window: int = 30) -> np.ndarray:
    n = len(closes)
    proxy = np.full(n, np.nan)
    returns = np.full(n, np.nan)
    for i in range(1, n):
        if closes[i] > 0 and closes[i-1] > 0:
            returns[i] = np.log(closes[i] / closes[i-1])
    for i in range(window, n):
        w_ret = returns[i-window+1:i+1]
        w_vol = volumes[i-window+1:i+1]
        valid = np.isfinite(w_ret)
        if valid.sum() < 10:
            continue
        vol_sum = np.sum(w_vol[valid])
        if vol_sum > 0:
            proxy[i] = np.sum(w_ret[valid] * w_vol[valid]) / vol_sum
    return proxy


def compute_rsi(closes: np.ndarray, period: int = 14) -> np.ndarray:
    n = len(closes)
    rsi = np.full(n, 50.0)
    for i in range(period, n):
        gains = []
        losses = []
        for j in range(i - period + 1, i + 1):
            if closes[j] > closes[j-1]:
                gains.append(closes[j] - closes[j-1])
                losses.append(0)
            else:
                gains.append(0)
                losses.append(closes[j-1] - closes[j])
        avg_gain = np.mean(gains) if gains else 0
        avg_loss = np.mean(losses) if losses else 0
        if avg_loss > 0:
            rs = avg_gain / avg_loss
            rsi[i] = 100 - (100 / (1 + rs))
        else:
            rsi[i] = 100
    return rsi


def compute_up_up_regime(btc_closes: np.ndarray) -> np.ndarray:
    n = len(btc_closes)
    regime = np.zeros(n, dtype=bool)
    for i in range(56, n):
        ret_4w = (btc_closes[i] - btc_closes[i-28]) / btc_closes[i-28]
        ret_prev_4w = (btc_closes[i-28] - btc_closes[i-56]) / btc_closes[i-56]
        regime[i] = ret_4w > 0 and ret_prev_4w > 0
    return regime


# ---------------------------------------------------------------------------
# TRADE 1: Squeeze Long
# ---------------------------------------------------------------------------

class SqueezeLongBacktest:
    """Backtest the squeeze long trade."""

    def __init__(self, assets: dict[str, dict]):
        self.assets = assets
        self.btc = assets["BTC"]
        self.death_cache = {}
        self.fund_cache = {}
        self.rsi_cache = {}

        for sym, data in assets.items():
            if sym == "BTC" or data["n"] < 100:
                continue
            self.death_cache[sym] = compute_death(data["closes"], data["volumes"])
            self.fund_cache[sym] = compute_funding_proxy(data["closes"], data["volumes"])
            self.rsi_cache[sym] = compute_rsi(data["closes"])

    def run(self) -> dict[str, Any]:
        btc_closes = self.btc["closes"]
        n = self.btc["n"]
        regime = compute_up_up_regime(btc_closes)

        capital = 100.0
        equity = []
        trades = []
        position = None  # {sym, entry_day, entry_price, size, direction}

        for t in range(90, n - 1):
            # Close existing position
            if position is not None:
                sym = position["sym"]
                if sym in self.assets and t < self.assets[sym]["n"]:
                    current = self.assets[sym]["closes"][t]
                    entry = position["entry_price"]
                    age = t - position["entry_day"]

                    # Exit conditions
                    should_exit = False
                    reason = ""

                    if position["direction"] == "long":
                        # Squeeze long exits
                        pnl_pct = (current - entry) / entry
                        if pnl_pct > 0.20:  # +20% take profit
                            should_exit = True
                            reason = "take_profit"
                        elif pnl_pct < -0.10:  # -10% stop loss
                            should_exit = True
                            reason = "stop_loss"
                        elif age >= 7:  # 7 day time stop
                            should_exit = True
                            reason = "time_stop"
                        # Funding normalization exit
                        fund = self.fund_cache.get(sym)
                        if fund is not None and t < len(fund) and np.isfinite(fund[t]):
                            if fund[t] > -0.001:  # funding normalized
                                should_exit = True
                                reason = "funding_normalized"
                    else:
                        # Squeeze long shouldn't be short, but handle anyway
                        should_exit = True
                        reason = "error"

                    if should_exit:
                        if position["direction"] == "long":
                            pnl = position["size"] * (current - entry) / entry
                        else:
                            pnl = position["size"] * (entry - current) / entry

                        capital += position["size"] + pnl
                        trades.append({
                            "sym": sym,
                            "direction": position["direction"],
                            "entry_day": position["entry_day"],
                            "exit_day": t,
                            "entry_price": entry,
                            "exit_price": current,
                            "pnl_pct": round((current - entry) / entry * 100, 2) if position["direction"] == "long" else round((entry - current) / entry * 100, 2),
                            "reason": reason,
                            "age_days": age,
                        })
                        position = None

            # Look for new entry
            if position is None:
                is_risk_on = regime[t] if t < len(regime) else False
                if not is_risk_on:
                    equity.append({"day": t, "equity": round(capital, 4)})
                    continue

                best = None
                best_score = 0

                for sym, data in self.assets.items():
                    if sym in BLUE_CHIPS or sym == "BTC":
                        continue
                    if data["n"] <= t or t < 90:
                        continue

                    death = self.death_cache.get(sym)
                    fund = self.fund_cache.get(sym)
                    if death is None or fund is None:
                        continue
                    if t >= len(death) or t >= len(fund):
                        continue
                    if np.isnan(death[t]) or np.isnan(fund[t]):
                        continue

                    # Conditions
                    death_high = death[t] >= 60
                    funding_neg = fund[t] < -0.003

                    closes = data["closes"]
                    if t < 7 or closes[t-7] <= 0:
                        continue
                    ret_7d = (closes[t] - closes[t-7]) / closes[t-7]
                    price_rising = ret_7d > 0

                    # Don't chase vertical moves
                    not_vertical = ret_7d < 0.25

                    if death_high and funding_neg and price_rising and not_vertical:
                        # Score: higher death + more negative funding + moderate rise = better
                        score = death[t] * 0.4 + abs(fund[t]) * 1000 * 0.3 + min(ret_7d * 100, 15) * 0.3
                        if score > best_score:
                            best_score = score
                            best = sym

                if best is not None:
                    position = {
                        "sym": best,
                        "entry_day": t,
                        "entry_price": self.assets[best]["closes"][t],
                        "size": capital * 0.10,  # 10% per trade
                        "direction": "long",
                    }
                    capital -= position["size"]

            equity.append({"day": t, "equity": round(capital + (
                position["size"] * (self.assets[position["sym"]]["closes"][t] - position["entry_price"]) / position["entry_price"]
                if position and position["sym"] in self.assets and t < self.assets[position["sym"]]["n"]
                else 0
            ), 4)})

        # Metrics
        eq = [e["equity"] for e in equity]
        returns = np.diff(eq) / np.array(eq[:-1])
        total_return = (eq[-1] - eq[0]) / eq[0]
        sharpe = float(np.mean(returns) / np.std(returns) * np.sqrt(365)) if np.std(returns) > 1e-10 else 0

        win_trades = [t for t in trades if t["pnl_pct"] > 0]
        win_rate = len(win_trades) / len(trades) * 100 if trades else 0
        avg_win = np.mean([t["pnl_pct"] for t in win_trades]) if win_trades else 0
        lose_trades = [t for t in trades if t["pnl_pct"] <= 0]
        avg_loss = np.mean([t["pnl_pct"] for t in lose_trades]) if lose_trades else 0

        return {
            "trade": "SQUEEZE_LONG",
            "total_return_pct": round(total_return * 100, 2),
            "sharpe_ratio": round(sharpe, 3),
            "total_trades": len(trades),
            "win_rate": round(win_rate, 1),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "avg_holding_days": round(np.mean([t["age_days"] for t in trades]), 1) if trades else 0,
            "trades": trades,
            "equity_curve": equity,
        }


# ---------------------------------------------------------------------------
# TRADE 2: Reload Short
# ---------------------------------------------------------------------------

class ReloadShortBacktest:
    """Backtest the reload short trade (post-squeeze)."""

    def __init__(self, assets: dict[str, dict]):
        self.assets = assets
        self.btc = assets["BTC"]
        self.death_cache = {}
        self.fund_cache = {}

        for sym, data in assets.items():
            if sym == "BTC" or data["n"] < 100:
                continue
            self.death_cache[sym] = compute_death(data["closes"], data["volumes"])
            self.fund_cache[sym] = compute_funding_proxy(data["closes"], data["volumes"])

    def run(self) -> dict[str, Any]:
        btc_closes = self.btc["closes"]
        n = self.btc["n"]

        capital = 100.0
        equity = []
        trades = []
        position = None

        for t in range(120, n - 1):
            # Close existing position
            if position is not None:
                sym = position["sym"]
                if sym in self.assets and t < self.assets[sym]["n"]:
                    current = self.assets[sym]["closes"][t]
                    entry = position["entry_price"]
                    age = t - position["entry_day"]
                    pnl_pct = (entry - current) / entry  # short PnL

                    should_exit = False
                    reason = ""

                    if pnl_pct > 0.15:  # +15% take profit
                        should_exit = True
                        reason = "take_profit"
                    elif pnl_pct < -0.10:  # -10% stop loss
                        should_exit = True
                        reason = "stop_loss"
                    elif age >= 42:  # 6 week time stop
                        should_exit = True
                        reason = "time_stop"
                    # Exit if death drops (fundamentals improving)
                    death = self.death_cache.get(sym)
                    if death is not None and t < len(death) and np.isfinite(death[t]):
                        if death[t] < 40:
                            should_exit = True
                            reason = "death_improving"

                    if should_exit:
                        pnl = position["size"] * pnl_pct
                        capital += position["size"] + pnl
                        trades.append({
                            "sym": sym,
                            "entry_day": position["entry_day"],
                            "exit_day": t,
                            "entry_price": entry,
                            "exit_price": current,
                            "pnl_pct": round(pnl_pct * 100, 2),
                            "reason": reason,
                            "age_days": age,
                        })
                        position = None

            # Look for new entry
            if position is None:
                best = None
                best_score = 0

                for sym, data in self.assets.items():
                    if sym in BLUE_CHIPS or sym == "BTC":
                        continue
                    if data["n"] <= t or t < 120:
                        continue

                    death = self.death_cache.get(sym)
                    fund = self.fund_cache.get(sym)
                    if death is None or fund is None:
                        continue
                    if t >= len(death) or t >= len(fund):
                        continue
                    if np.isnan(death[t]) or np.isnan(fund[t]):
                        continue

                    closes = data["closes"]
                    # RELOAD conditions
                    # 1. Death still high
                    death_high = death[t] >= 60

                    # 2. Price well above 30d ago (squeeze happened)
                    if closes[t-30] <= 0:
                        continue
                    price_ratio = closes[t] / closes[t-30]
                    squeeze_happened = price_ratio > 1.3

                    # 3. Price rolling over from high
                    high_30d = np.max(closes[max(0, t-29):t+1])
                    from_high = (closes[t] - high_30d) / high_30d if high_30d > 0 else 0
                    rolling_over = from_high < -0.05

                    # 4. Funding normalized
                    fund_window = fund[max(0, t-29):t+1]
                    valid_fund = fund_window[np.isfinite(fund_window)]
                    if len(valid_fund) < 5:
                        continue
                    fund_p10 = np.percentile(valid_fund, 10)
                    fund_normalized = fund[t] > fund_p10

                    if death_high and squeeze_happened and rolling_over and fund_normalized:
                        score = death[t] * 0.3 + (price_ratio - 1) * 20 * 0.3 + abs(from_high) * 100 * 0.2 + (1 if fund_normalized else 0) * 10 * 0.2
                        if score > best_score:
                            best_score = score
                            best = sym

                if best is not None:
                    position = {
                        "sym": best,
                        "entry_day": t,
                        "entry_price": self.assets[best]["closes"][t],
                        "size": capital * 0.15,  # 15% per trade
                        "direction": "short",
                    }
                    capital -= position["size"]

            unrealized = 0
            if position and position["sym"] in self.assets and t < self.assets[position["sym"]]["n"]:
                current = self.assets[position["sym"]]["closes"][t]
                unrealized = position["size"] * (position["entry_price"] - current) / position["entry_price"]

            equity.append({"day": t, "equity": round(capital + unrealized, 4)})

        eq = [e["equity"] for e in equity]
        returns = np.diff(eq) / np.array(eq[:-1])
        total_return = (eq[-1] - eq[0]) / eq[0]
        sharpe = float(np.mean(returns) / np.std(returns) * np.sqrt(365)) if np.std(returns) > 1e-10 else 0

        win_trades = [t for t in trades if t["pnl_pct"] > 0]
        win_rate = len(win_trades) / len(trades) * 100 if trades else 0
        avg_win = np.mean([t["pnl_pct"] for t in win_trades]) if win_trades else 0
        lose_trades = [t for t in trades if t["pnl_pct"] <= 0]
        avg_loss = np.mean([t["pnl_pct"] for t in lose_trades]) if lose_trades else 0

        return {
            "trade": "RELOAD_SHORT",
            "total_return_pct": round(total_return * 100, 2),
            "sharpe_ratio": round(sharpe, 3),
            "total_trades": len(trades),
            "win_rate": round(win_rate, 1),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "avg_holding_days": round(np.mean([t["age_days"] for t in trades]), 1) if trades else 0,
            "trades": trades,
            "equity_curve": equity,
        }


# ---------------------------------------------------------------------------
# TRADE 3: Quality RSI Outperformers
# ---------------------------------------------------------------------------

class QualityRSIBacktest:
    """Backtest quality RSI outperformers (spot long)."""

    def __init__(self, assets: dict[str, dict]):
        self.assets = assets
        self.btc = assets["BTC"]
        self.rsi_cache = {}
        self.ret_cache = {}

        for sym, data in assets.items():
            if data["n"] < 100:
                continue
            self.rsi_cache[sym] = compute_rsi(data["closes"])
            rets = np.zeros(data["n"])
            for i in range(1, data["n"]):
                if data["closes"][i-1] > 0:
                    rets[i] = (data["closes"][i] - data["closes"][i-1]) / data["closes"][i-1]
            self.ret_cache[sym] = rets

    def run(self) -> dict[str, Any]:
        btc_closes = self.btc["closes"]
        n = self.btc["n"]
        regime = compute_up_up_regime(btc_closes)

        capital = 100.0
        equity = []
        trades = []
        positions = {}  # sym -> {entry_day, entry_price, size}

        for t in range(90, n - 1):
            is_risk_on = regime[t] if t < len(regime) else False

            # Close positions that should exit
            to_close = []
            for sym, pos in list(positions.items()):
                if sym not in self.assets or t >= self.assets[sym]["n"]:
                    to_close.append(sym)
                    continue

                current = self.assets[sym]["closes"][t]
                entry = pos["entry_price"]
                age = t - pos["entry_day"]
                pnl_pct = (current - entry) / entry

                should_exit = False
                reason = ""

                if pnl_pct > 0.25:  # +25% take profit
                    should_exit = True
                    reason = "take_profit"
                elif pnl_pct < -0.10:  # -10% stop loss
                    should_exit = True
                    reason = "stop_loss"
                elif age >= 30:  # 30 day time stop
                    should_exit = True
                    reason = "time_stop"
                elif not is_risk_on:  # regime change
                    should_exit = True
                    reason = "regime_change"
                # Exit if RSI drops below 50 (momentum fading)
                rsi = self.rsi_cache.get(sym)
                if rsi is not None and t < len(rsi) and rsi[t] < 45:
                    should_exit = True
                    reason = "rsi_weak"

                if should_exit:
                    pnl = pos["size"] * pnl_pct
                    capital += pos["size"] + pnl
                    trades.append({
                        "sym": sym,
                        "entry_day": pos["entry_day"],
                        "exit_day": t,
                        "entry_price": entry,
                        "exit_price": current,
                        "pnl_pct": round(pnl_pct * 100, 2),
                        "reason": reason,
                        "age_days": age,
                    })
                    to_close.append(sym)

            for sym in to_close:
                if sym in positions:
                    del positions[sym]

            # Open new positions (max 5)
            if is_risk_on and len(positions) < 5:
                candidates = []
                for sym, data in self.assets.items():
                    if sym in BLUE_CHIPS or sym == "BTC":
                        continue
                    if data["n"] <= t or t < 90:
                        continue
                    if sym in positions:
                        continue

                    rsi = self.rsi_cache.get(sym)
                    if rsi is None or t >= len(rsi):
                        continue

                    # Quality + momentum: RSI > 60, not overextended
                    if rsi[t] > 60 and rsi[t] < 80:
                        # Relative strength vs BTC
                        rets = self.ret_cache.get(sym)
                        if rets is not None and t >= 28:
                            asset_ret = np.sum(rets[t-27:t+1])
                            btc_ret = (btc_closes[t] - btc_closes[t-28]) / btc_closes[t-28]
                            rel_strength = asset_ret - btc_ret
                            if rel_strength > 0:  # outperforming BTC
                                candidates.append((sym, rsi[t], rel_strength))

                # Sort by relative strength
                candidates.sort(key=lambda x: x[2], reverse=True)

                for sym, rsi_val, rel in candidates[:max(0, 5 - len(positions))]:
                    size = capital * 0.10  # 10% per position
                    if size > 0:
                        positions[sym] = {
                            "entry_day": t,
                            "entry_price": self.assets[sym]["closes"][t],
                            "size": size,
                        }
                        capital -= size

            # Compute equity
            unrealized = 0
            for sym, pos in positions.items():
                if sym in self.assets and t < self.assets[sym]["n"]:
                    current = self.assets[sym]["closes"][t]
                    unrealized += pos["size"] * (current - pos["entry_price"]) / pos["entry_price"]

            equity.append({"day": t, "equity": round(capital + unrealized, 4)})

        # Close remaining positions
        for sym, pos in positions.items():
            if sym in self.assets:
                current = self.assets[sym]["closes"][-1]
                pnl_pct = (current - pos["entry_price"]) / pos["entry_price"]
                pnl = pos["size"] * pnl_pct
                capital += pos["size"] + pnl
                trades.append({
                    "sym": sym,
                    "entry_day": pos["entry_day"],
                    "exit_day": n - 1,
                    "entry_price": pos["entry_price"],
                    "exit_price": current,
                    "pnl_pct": round(pnl_pct * 100, 2),
                    "reason": "end_of_data",
                    "age_days": n - 1 - pos["entry_day"],
                })

        eq = [e["equity"] for e in equity]
        returns = np.diff(eq) / np.array(eq[:-1])
        total_return = (eq[-1] - eq[0]) / eq[0]
        sharpe = float(np.mean(returns) / np.std(returns) * np.sqrt(365)) if np.std(returns) > 1e-10 else 0

        win_trades = [t for t in trades if t["pnl_pct"] > 0]
        win_rate = len(win_trades) / len(trades) * 100 if trades else 0
        avg_win = np.mean([t["pnl_pct"] for t in win_trades]) if win_trades else 0
        lose_trades = [t for t in trades if t["pnl_pct"] <= 0]
        avg_loss = np.mean([t["pnl_pct"] for t in lose_trades]) if lose_trades else 0

        return {
            "trade": "QUALITY_RSI",
            "total_return_pct": round(total_return * 100, 2),
            "sharpe_ratio": round(sharpe, 3),
            "total_trades": len(trades),
            "win_rate": round(win_rate, 1),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "avg_holding_days": round(np.mean([t["age_days"] for t in trades]), 1) if trades else 0,
            "trades": trades,
            "equity_curve": equity,
        }


# ---------------------------------------------------------------------------
# Combined lifecycle
# ---------------------------------------------------------------------------

def run_combined() -> dict[str, Any]:
    """Run all three trades and combine."""
    assets = load_assets()
    print(f"Loaded {len(assets)} assets")

    print("\nRunning SQUEEZE_LONG backtest...")
    squeeze = SqueezeLongBacktest(assets).run()

    print("Running RELOAD_SHORT backtest...")
    reload = ReloadShortBacktest(assets).run()

    print("Running QUALITY_RSI backtest...")
    quality = QualityRSIBacktest(assets).run()

    # Combined: allocate capital across all three
    # Squeeze: 10% allocation, Reload: 15% allocation, Quality: 15% allocation, Cash: 60%
    btc_closes = assets["BTC"]["closes"]
    n = assets["BTC"]["n"]
    regime = compute_up_up_regime(btc_closes)

    capital = 100.0
    combined_equity = []

    for t in range(90, n - 1):
        is_risk_on = regime[t] if t < len(regime) else False

        # Get equity from each strategy
        s_eq = next((e["equity"] for e in squeeze["equity_curve"] if e["day"] == t), capital * 0.10)
        r_eq = next((e["equity"] for e in reload["equity_curve"] if e["day"] == t), capital * 0.15)
        q_eq = next((e["equity"] for e in quality["equity_curve"] if e["day"] == t), capital * 0.15)

        # Combined equity (simplified: sum of normalized equities)
        combined = s_eq + r_eq + q_eq + (capital - 0.10 * capital - 0.15 * capital - 0.15 * capital)
        combined_equity.append({"day": t, "equity": round(combined, 4)})

    eq = [e["equity"] for e in combined_equity]
    returns = np.diff(eq) / np.array(eq[:-1])
    total_return = (eq[-1] - eq[0]) / eq[0]
    sharpe = float(np.mean(returns) / np.std(returns) * np.sqrt(365)) if np.std(returns) > 1e-10 else 0

    return {
        "squeeze_long": {k: v for k, v in squeeze.items() if k != "trades" and k != "equity_curve"},
        "reload_short": {k: v for k, v in reload.items() if k != "trades" and k != "equity_curve"},
        "quality_rsi": {k: v for k, v in quality.items() if k != "trades" and k != "equity_curve"},
        "combined": {
            "total_return_pct": round(total_return * 100, 2),
            "sharpe_ratio": round(sharpe, 3),
            "final_equity": round(eq[-1], 2),
        },
    }


if __name__ == "__main__":
    print("=" * 70)
    print("FULL BACKTEST: 3 TRADES ON DEAD TOKENS + QUALITY SPOT")
    print("=" * 70)

    result = run_combined()

    for trade_name, data in result.items():
        print(f"\n{'=' * 50}")
        print(f"  {trade_name}")
        print(f"{'=' * 50}")
        for k, v in data.items():
            print(f"    {k}: {v}")

    Path("/root/BEAR/data/full_backtest.json").write_text(
        json.dumps(result, indent=2, default=str)
    )
    print(f"\nSaved to data/full_backtest.json")
