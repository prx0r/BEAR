"""TAO/UNI long vs matched terminal-token shorts backtest.

The full frozen architecture strategy:
  LONG: TAO (60%) + UNI (40%)
  SHORT: Best terminal-token matches ranked by TradableDeath
  GOAL: Remove market beta, capture idiosyncratic alpha from both sides
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

DATA_DIR = Path("/root/BEAR/data/binance")
SUPPLY_CACHE = Path("/root/BEAR/data/supply_cache.json")


def load_assets() -> dict[str, dict]:
    assets = {}
    for f in sorted(DATA_DIR.glob("*.json")):
        sym = f.stem.replace("USDT", "")
        with open(f) as fh:
            raw = json.load(fh)
        if len(raw) < 200:
            continue
        closes = np.array([d["close"] for d in raw], dtype=np.float64)
        volumes = np.array([d["volume"] for d in raw], dtype=np.float64)
        if np.all(closes > 0):
            assets[sym] = {"closes": closes, "volumes": volumes, "n": len(raw)}
    return assets


def compute_death_scores(assets: dict[str, dict], t: int) -> dict[str, float]:
    """Compute volume-death score at time t for each asset."""
    scores = {}
    for sym, data in assets.items():
        if data["n"] <= t or t < 90:
            continue
        closes = data["closes"][:t + 1]
        volumes = data["volumes"][:t + 1]
        n = len(closes)

        # Volume death: recent vs peak
        vol_7d = float(np.mean(volumes[max(0, n - 7):]))
        vol_peak = float(np.max(volumes[max(0, n - 90):]))
        vol_death = 1.0 - vol_7d / max(vol_peak, 1e-10) if vol_peak > 0 else 0

        # Price decline
        ret_90d = (closes[-1] - closes[-90]) / closes[-90] if closes[-90] > 0 else 0

        # Composite death score
        death = vol_death * 50 + max(-ret_90d, 0) * 50
        scores[sym] = min(100, max(0, death))

    return scores


def run_backtest():
    """Run the TAO/UNI long vs terminal-token shorts backtest."""
    assets = load_assets()
    supply = json.loads(SUPPLY_CACHE.read_text()) if SUPPLY_CACHE.exists() else {}

    btc = assets.get("BTC")
    tao = assets.get("TAO")
    uni = assets.get("UNI")

    if not btc or not tao or not uni:
        print("Missing BTC, TAO, or UNI data")
        return

    n = min(btc["n"], tao["n"], uni["n"])
    print(f"Backtest period: {n} days")

    # Parameters
    lookback = 90
    rebalance_freq = 14  # rebalance every 2 weeks
    long_tao_weight = 0.60
    long_uni_weight = 0.40
    short_gross_target = 0.80  # 80% hedge ratio

    # Equity tracking
    long_equity = 1.0
    hedged_equity = 1.0
    long_history = []
    hedged_history = []
    trade_log = []

    for t in range(lookback, n - 1):
        # ── Long side ──
        tao_ret = (tao["closes"][t] - tao["closes"][t - 1]) / tao["closes"][t - 1]
        uni_ret = (uni["closes"][t] - uni["closes"][t - 1]) / uni["closes"][t - 1]
        long_ret = long_tao_weight * tao_ret + long_uni_weight * uni_ret

        long_equity *= (1 + long_ret)
        long_history.append(long_equity)

        # ── Short selection (every rebalance_freq days) ──
        if (t - lookback) % rebalance_freq == 0:
            death_scores = compute_death_scores(assets, t)

            # Filter: must be liquid, not blue chip
            blue_chips = {"BTC", "ETH", "SOL", "HYPE", "BNB", "XRP", "ADA", "AVAX", "DOT",
                         "LINK", "UNI", "AAVE", "MKR", "SNX", "CRV", "LDO", "PENDLE"}
            candidates = {s: score for s, score in death_scores.items()
                         if s not in blue_chips and s != "TAO"
                         and assets[s]["volumes"][t] > 100_000}

            # Top 5 by death score
            ranked = sorted(candidates.items(), key=lambda x: x[1], reverse=True)[:5]
            short_syms = [s for s, _ in ranked]
            short_weights = {s: 1.0 / len(short_syms) for s in short_syms}

        # ── Short side ──
        short_ret = 0.0
        for s in short_syms:
            if s in assets and t < assets[s]["n"]:
                s_ret = (assets[s]["closes"][t] - assets[s]["closes"][t - 1]) / assets[s]["closes"][t - 1]
                # Short profits when price drops
                short_ret += short_weights[s] * (-s_ret)

        # ── Hedged portfolio ──
        # Net: long + short_gross * short_return
        # Short gives us funding income (approx 0.01% per day for high-funding tokens)
        # For simplicity, assume shorts collect 0.005% daily carry
        carry_income = short_gross_target * 0.00005

        hedged_ret = long_ret + short_gross_target * short_ret + carry_income
        hedged_equity *= (1 + hedged_ret)
        hedged_history.append(hedged_equity)

        if (t - lookback) % rebalance_freq == 0:
            trade_log.append({
                "day": t,
                "shorts": short_syms,
                "death_scores": {s: round(candidates.get(s, 0), 1) for s in short_syms},
            })

    # ── Metrics ──
    long_returns = np.diff(long_history) / long_history[:-1]
    hedged_returns = np.diff(hedged_history) / hedged_history[:-1]

    def sharpe(rets):
        if len(rets) < 2 or np.std(rets) < 1e-12:
            return 0.0
        return np.mean(rets) / np.std(rets) * np.sqrt(365)

    def max_dd(equity):
        peak = equity[0]
        max_dd = 0
        for v in equity:
            if v > peak:
                peak = v
            dd = (peak - v) / peak
            if dd > max_dd:
                max_dd = dd
        return max_dd

    long_total = (long_history[-1] - long_history[0]) / long_history[0]
    hedged_total = (hedged_history[-1] - hedged_history[0]) / hedged_history[0]

    # BTC beta
    btc_rets = np.diff(btc["closes"][lookback:n]) / btc["closes"][lookback:n - 1]
    long_btc_beta = np.cov(long_returns[:len(btc_rets)], btc_rets[:len(long_returns)])[0, 1] / np.var(btc_rets[:len(long_returns)]) if len(btc_rets) >= len(long_returns) else 0

    print(f"\n{'=' * 70}")
    print(f"BACKTEST: TAO/UNI Long vs Terminal-Token Shorts")
    print(f"{'=' * 70}")
    print(f"  Period: {n - lookback} days")
    print(f"  Long: 60% TAO + 40% UNI")
    print(f"  Short: Top 5 death tokens, {short_gross_target:.0%} gross")
    print(f"  Rebalance: every {rebalance_freq} days")
    print()
    print(f"  {'Metric':<25s} {'Long Only':>12s} {'Hedged':>12s}")
    print(f"  {'-' * 50}")
    print(f"  {'Total Return':<25s} {long_total:>+11.2%} {hedged_total:>+11.2%}")
    print(f"  {'Annualized Return':<25s} {sharpe(long_returns) * np.std(long_returns) * np.sqrt(365):>+11.2%} {sharpe(hedged_returns) * np.std(hedged_returns) * np.sqrt(365):>+11.2%}")
    print(f"  {'Sharpe Ratio':<25s} {sharpe(long_returns):>11.3f} {sharpe(hedged_returns):>11.3f}")
    print(f"  {'Max Drawdown':<25s} {max_dd(np.array(long_history)):>11.2%} {max_dd(np.array(hedged_history)):>11.2%}")
    print(f"  {'Volatility (ann.)':<25s} {np.std(long_returns) * np.sqrt(365):>11.2%} {np.std(hedged_returns) * np.sqrt(365):>11.2%}")
    print(f"  {'BTC Beta':<25s} {long_btc_beta:>11.3f} {'< 0.1 (target)':>12s}")
    print()

    # Recent short selections
    print("  Recent short selections:")
    for trade in trade_log[-3:]:
        syms = trade["shorts"]
        scores = trade["death_scores"]
        print(f"    Day {trade['day']}: {', '.join(f'{s}({scores[s]})' for s in syms)}")

    return {
        "long_total": long_total,
        "hedged_total": hedged_total,
        "long_sharpe": sharpe(long_returns),
        "hedged_sharpe": sharpe(hedged_returns),
        "long_max_dd": max_dd(np.array(long_history)),
        "hedged_max_dd": max_dd(np.array(hedged_history)),
        "trades": trade_log,
    }


if __name__ == "__main__":
    result = run_backtest()
