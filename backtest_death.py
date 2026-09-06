#!/usr/bin/env python3
"""Backtest combined death score on Binance historical data.

Pre-computes all signal scores once as matrices, then grid searches weights
via fast numpy dot products.

Usage:
    python3 backtest_death.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from itertools import product

import numpy as np

DATA_DIR = Path(__file__).parent / "data" / "binance"
RESULTS_DIR = Path(__file__).parent / "data"


def load_all_assets() -> dict[str, dict]:
    """Load all assets as numpy arrays."""
    assets = {}
    for f in sorted(DATA_DIR.glob("*.json")):
        symbol = f.stem
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


def precompute_all_signals(assets: dict[str, dict]) -> dict:
    """Pre-compute all 5 signal matrices for all assets."""
    symbols = sorted(assets.keys())
    n_assets = len(symbols)
    max_n = max(d["n"] for d in assets.values())

    # Matrices: n_assets x max_n
    vol_death_mat = np.full((n_assets, max_n), np.nan)
    deep_decline_mat = np.full((n_assets, max_n), np.nan)
    reversal_raw_mat = np.full((n_assets, max_n), np.nan)
    funding_mat = np.full((n_assets, max_n), np.nan)
    momentum_raw_mat = np.full((n_assets, max_n), np.nan)
    asset_n = np.array([assets[s]["n"] for s in symbols])

    for si, sym in enumerate(symbols):
        c = assets[sym]["closes"]
        v = assets[sym]["volumes"]
        n = len(c)

        # --- volume_death ---
        window_peak = 90
        peak_vol = np.full(n, np.nan)
        for i in range(window_peak - 1, n):
            w = v[max(0, i - window_peak + 1): i + 1]
            vv = w[np.isfinite(w)]
            peak_vol[i] = np.max(vv) if len(vv) > 0 else np.nan
        recent_vol = np.full(n, np.nan)
        for i in range(6, n):
            w = v[max(0, i - 6): i + 1]
            vv = w[np.isfinite(w)]
            recent_vol[i] = np.mean(vv) if len(vv) > 0 else np.nan
        ratio = np.where(
            np.isfinite(peak_vol) & np.isfinite(recent_vol) & (peak_vol > 0),
            recent_vol / peak_vol, np.nan
        )
        vol_death_mat[si, :n] = np.where(np.isfinite(ratio), np.clip((1.0 - ratio) * 100, 0, 100), np.nan)

        # --- deep_decline ---
        peak_window = 180
        dd = np.full(n, np.nan)
        for i in range(peak_window - 1, n):
            w = c[max(0, i - peak_window + 1): i + 1]
            vv = w[np.isfinite(w)]
            if len(vv) > 0 and vv.max() > 0:
                dd[i] = (c[i] - vv.max()) / vv.max()
        ret_90d = np.full(n, np.nan)
        for i in range(89, n):
            if np.isfinite(c[i]) and np.isfinite(c[i - 89]) and c[i - 89] > 0:
                ret_90d[i] = (c[i] - c[i - 89]) / c[i - 89]
        dd_s = np.where(np.isfinite(dd), np.clip((-dd) * 100, 0, 100), np.nan)
        r90_s = np.where(np.isfinite(ret_90d), np.clip((-ret_90d) * 100, 0, 100), np.nan)
        deep_decline_mat[si, :n] = np.where(
            np.isfinite(dd_s) & np.isfinite(r90_s), 0.6 * dd_s + 0.4 * r90_s,
            np.where(np.isfinite(dd_s), dd_s, np.where(np.isfinite(r90_s), r90_s, np.nan))
        )

        # --- reversal_8w raw ---
        ret_8w = np.full(n, np.nan)
        for i in range(55, n):
            if np.isfinite(c[i]) and np.isfinite(c[i - 55]) and c[i - 55] > 0:
                ret_8w[i] = (c[i] - c[i - 55]) / c[i - 55]
        reversal_raw_mat[si, :n] = ret_8w

        # --- funding_pressure ---
        returns = np.full(n, np.nan)
        for i in range(1, n):
            if np.isfinite(c[i]) and np.isfinite(c[i - 1]) and c[i - 1] > 0:
                returns[i] = (c[i] - c[i - 1]) / c[i - 1]
        vol_30d = np.full(n, np.nan)
        for i in range(29, n):
            w = returns[max(1, i - 29): i + 1]
            vv = w[np.isfinite(w)]
            vol_30d[i] = np.std(vv) if len(vv) > 5 else np.nan
        vol_ma = np.full(n, np.nan)
        for i in range(29, n):
            w = v[max(0, i - 29): i + 1]
            vv = w[np.isfinite(w)]
            vol_ma[i] = np.mean(vv) if len(vv) > 0 else np.nan
        vol_recent = np.full(n, np.nan)
        for i in range(6, n):
            w = v[max(0, i - 6): i + 1]
            vv = w[np.isfinite(w)]
            vol_recent[i] = np.mean(vv) if len(vv) > 0 else np.nan
        vol_ratio = np.where(
            np.isfinite(vol_ma) & np.isfinite(vol_recent) & (vol_ma > 0),
            vol_recent / vol_ma, np.nan
        )
        vs = np.where(np.isfinite(vol_30d), np.clip(vol_30d * 500, 0, 100), np.nan)
        ds = np.where(np.isfinite(vol_ratio), np.clip((1.0 - vol_ratio) * 100, 0, 100), np.nan)
        funding_mat[si, :n] = np.where(
            np.isfinite(vs) & np.isfinite(ds), 0.5 * vs + 0.5 * ds,
            np.where(np.isfinite(vs), vs, np.where(np.isfinite(ds), ds, np.nan))
        )

        # --- momentum raw ---
        ret_7d = np.full(n, np.nan)
        for i in range(6, n):
            if np.isfinite(c[i]) and np.isfinite(c[i - 6]) and c[i - 6] > 0:
                ret_7d[i] = (c[i] - c[i - 6]) / c[i - 6]
        momentum_raw_mat[si, :n] = ret_7d

    # Cross-sectional rank for reversal and momentum
    ranked_rev = np.full((n_assets, max_n), np.nan)
    ranked_mom = np.full((n_assets, max_n), np.nan)
    for t in range(max_n):
        rv = reversal_raw_mat[:, t]
        mv = momentum_raw_mat[:, t]
        vr = np.isfinite(rv)
        vm = np.isfinite(mv)
        if vr.sum() >= 3:
            o = np.argsort(rv[vr])
            r = np.empty(int(vr.sum()))
            r[o] = np.arange(int(vr.sum()))
            ranked_rev[vr, t] = r / vr.sum() * 100
        if vm.sum() >= 3:
            o = np.argsort(mv[vm])
            r = np.empty(int(vm.sum()))
            r[o] = np.arange(int(vm.sum()))
            ranked_mom[vm, t] = r / vm.sum() * 100

    return {
        "symbols": symbols,
        "n_assets": n_assets,
        "max_n": max_n,
        "asset_n": asset_n,
        "vol_death": vol_death_mat,
        "deep_decline": deep_decline_mat,
        "reversal": ranked_rev,
        "funding": funding_mat,
        "momentum": ranked_mom,
    }


def score_at_time(sig: dict, si: int, t: int, w_vec: np.ndarray) -> float:
    """Compute death score for asset si at time t with weight vector."""
    vals = np.array([
        sig["vol_death"][si, t],
        sig["deep_decline"][si, t],
        sig["reversal"][si, t],
        sig["funding"][si, t],
        sig["momentum"][si, t],
    ])
    valid = np.isfinite(vals)
    if valid.sum() < 3:
        return np.nan
    return float(np.dot(vals[valid], w_vec[valid]) / w_vec[valid].sum())


def backtest_with_weights(
    assets: dict[str, dict],
    sig: dict,
    w_vec: np.ndarray,
    lookback: int = 365,
    forward: int = 30,
    top_pct: float = 0.20,
    rebalance_freq: int = 30,
) -> dict:
    """Run backtest given precomputed signals and weight vector."""
    symbols = sig["symbols"]
    n_assets = sig["n_assets"]
    max_n = sig["max_n"]
    asset_n = sig["asset_n"]

    first_valid = lookback
    last_valid = max_n - forward - 1
    if first_valid >= last_valid:
        return {"sharpe": 0.0, "total_return": 0.0, "win_rate": 0.0, "n_trades": 0, "n_periods": 0}

    rebalance_dates = list(range(first_valid, last_valid, rebalance_freq))
    portfolio_returns = []
    total_trades = 0

    for rebal_idx in rebalance_dates:
        scores = []
        valid_indices = []

        for si in range(n_assets):
            if asset_n[si] < rebal_idx + 1:
                continue
            sc = score_at_time(sig, si, rebal_idx, w_vec)
            if np.isfinite(sc):
                scores.append(sc)
                valid_indices.append(si)

        if len(valid_indices) < 5:
            continue

        scores = np.array(scores)
        n_short = max(1, int(len(valid_indices) * top_pct))
        top_idx = np.argsort(-scores)[:n_short]

        period_returns = []
        for idx in top_idx:
            si = valid_indices[idx]
            sym = symbols[si]
            n = asset_n[si]
            if n >= rebal_idx + forward + 1:
                c = assets[sym]["closes"]
                p_now = c[rebal_idx]
                p_fwd = c[rebal_idx + forward]
                if p_now > 0:
                    fwd_ret = (p_fwd - p_now) / p_now
                    period_returns.append(-fwd_ret)  # short
                    total_trades += 1

        if period_returns:
            portfolio_returns.append(np.mean(period_returns))

    if not portfolio_returns:
        return {"sharpe": 0.0, "total_return": 0.0, "win_rate": 0.0, "n_trades": 0, "n_periods": 0}

    port_arr = np.array(portfolio_returns)
    total_return = float(np.prod(1 + port_arr) - 1)
    mean_ret = float(np.mean(port_arr))
    std_ret = float(np.std(port_arr)) if len(port_arr) > 1 else 1.0
    periods_per_year = 365 / rebalance_freq
    sharpe = (mean_ret / std_ret * np.sqrt(periods_per_year)) if std_ret > 1e-10 else 0.0
    win_rate = float(np.mean(port_arr > 0))

    return {
        "sharpe": round(float(sharpe), 4),
        "total_return": round(total_return * 100, 2),
        "win_rate": round(win_rate * 100, 2),
        "mean_period_return": round(mean_ret * 100, 4),
        "annualized_return": round(float(mean_ret * periods_per_year) * 100, 2),
        "n_trades": total_trades,
        "n_periods": len(port_arr),
    }


def grid_search(assets: dict[str, dict], sig: dict, **kwargs) -> dict:
    """Grid search weight combinations to maximize Sharpe."""
    best_sharpe = -999
    best_weights = None
    best_result = None
    results = []

    w1_range = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35]
    w2_range = [0.10, 0.15, 0.20, 0.25, 0.30]
    w3_range = [0.10, 0.15, 0.20, 0.25, 0.30]
    w5_range = [0.10, 0.15, 0.20]

    combos = [(w1, w2, w3, w5)
              for w1, w2, w3, w5 in product(w1_range, w2_range, w3_range, w5_range)
              if 1.0 - w1 - w2 - w3 - w5 >= 0.05]

    print(f"    Testing {len(combos)} weight combinations...")

    for ci, (w1, w2, w3, w5) in enumerate(combos):
        w4 = round(1.0 - w1 - w2 - w3 - w5, 3)
        w_vec = np.array([w1, w2, w3, w4, w5])

        labels = ["volume_death", "deep_decline", "reversal", "funding_pressure", "momentum"]
        weights_dict = dict(zip(labels, [round(x, 3) for x in w_vec]))

        result = backtest_with_weights(assets, sig, w_vec, **kwargs)
        sharpe = result["sharpe"]

        results.append({"weights": weights_dict, **result})

        if sharpe > best_sharpe:
            best_sharpe = sharpe
            best_weights = weights_dict
            best_result = result

        if (ci + 1) % 50 == 0:
            print(f"    {ci+1}/{len(combos)} tested, best Sharpe: {best_sharpe:.4f}")

    results.sort(key=lambda x: -x["sharpe"])
    return {
        "best_sharpe": best_sharpe,
        "best_weights": best_weights,
        "best_result": best_result,
        "top_20": results[:20],
        "total_combos_tested": len(combos),
    }


def validate_tokens(assets: dict[str, dict], sig: dict, w_vec: np.ndarray) -> list[dict]:
    """Validate against tokens that had significant declines in our data."""
    symbols = sig["symbols"]
    asset_n = sig["asset_n"]
    results = []

    # Find tokens with worst peak-to-trough declines
    for si, sym in enumerate(symbols):
        n = asset_n[si]
        if n < 180:
            continue

        c = assets[sym]["closes"]
        # Find max drawdown and when it happened
        running_peak = c[0]
        max_dd = 0
        max_dd_end = 0
        max_dd_start = 0
        peak_idx = 0

        for i in range(1, n):
            if c[i] > running_peak:
                running_peak = c[i]
                peak_idx = i
            dd = (c[i] - running_peak) / running_peak
            if dd < max_dd:
                max_dd = dd
                max_dd_end = i
                max_dd_start = peak_idx

        # Only include tokens with >80% decline
        if max_dd > -0.80:
            continue

        # Compute death score at various points before the trough
        check_points = [
            max(90, max_dd_end - 180),
            max(90, max_dd_end - 120),
            max(90, max_dd_end - 90),
            max(90, max_dd_end - 60),
            max(90, max_dd_end - 30),
        ]

        pre_scores = []
        for cp in check_points:
            if cp >= n:
                continue
            sc = score_at_time(sig, si, cp, w_vec)
            if np.isfinite(sc):
                pre_scores.append({
                    "days_before_trough": max_dd_end - cp,
                    "death_score": round(sc, 2),
                })

        # Score at trough
        at_trough = score_at_time(sig, si, max_dd_end, w_vec)
        decline_pct = round(max_dd * 100, 1)

        results.append({
            "symbol": sym,
            "decline_pct": decline_pct,
            "death_score_at_trough": round(float(at_trough), 2) if np.isfinite(at_trough) else None,
            "pre_trough_scores": pre_scores,
            "flagged_early": any(s["death_score"] > 70 for s in pre_scores),
        })

    # Sort by decline severity
    results.sort(key=lambda x: x["decline_pct"])
    return results[:20]


def main():
    print("=" * 70)
    print("DEATH SCORE BACKTEST — Binance Historical Data")
    print("=" * 70)

    # Load
    print("\n[1] Loading Binance data...")
    assets = load_all_assets()
    print(f"    Loaded {len(assets)} assets with >= 90 days of data")

    # Precompute
    print("\n[2] Pre-computing all signals...")
    sig = precompute_all_signals(assets)
    print(f"    {sig['n_assets']} assets x {sig['max_n']} days")
    print(f"    Signals: vol_death, deep_decline, reversal, funding_pressure, momentum")

    # Equal weight baseline
    print("\n[3] Running EQUAL WEIGHT baseline...")
    ew = np.array([0.20, 0.20, 0.20, 0.20, 0.20])
    ew_result = backtest_with_weights(assets, sig, ew, lookback=365, forward=30, top_pct=0.20)
    print(f"    Sharpe:  {ew_result['sharpe']:.4f}")
    print(f"    Return:  {ew_result['total_return']:.2f}%")
    print(f"    Win:     {ew_result['win_rate']:.1f}%")
    print(f"    Trades:  {ew_result['n_trades']} ({ew_result['n_periods']} periods)")

    # Grid search
    print("\n[4] Grid searching optimal weights...")
    grid = grid_search(assets, sig, lookback=365, forward=30, top_pct=0.20)
    print(f"\n    Tested {grid['total_combos_tested']} combos")
    print(f"\n    BEST (Sharpe={grid['best_sharpe']:.4f}):")
    for k, v in grid["best_weights"].items():
        print(f"      {k}: {v:.3f}")
    b = grid["best_result"]
    print(f"    Return: {b['total_return']:.2f}% | Win: {b['win_rate']:.1f}% | Periods: {b['n_periods']}")

    # Top 10
    print("\n    Top 10 combos:")
    for i, r in enumerate(grid["top_20"][:10]):
        w = r["weights"]
        print(f"    #{i+1}: S={r['sharpe']:.4f} R={r['total_return']:.1f}% W={r['win_rate']:.0f}% | "
              f"vol={w['volume_death']:.2f} dd={w['deep_decline']:.2f} "
              f"rev={w['reversal']:.2f} fund={w['funding_pressure']:.2f} mom={w['momentum']:.2f}")

    # Validate
    print("\n[5] Validating against severely declined tokens...")
    best_w = np.array([
        grid["best_weights"]["volume_death"],
        grid["best_weights"]["deep_decline"],
        grid["best_weights"]["reversal"],
        grid["best_weights"]["funding_pressure"],
        grid["best_weights"]["momentum"],
    ])
    dead = validate_tokens(assets, sig, best_w)
    for r in dead:
        flag = "DETECTED" if r["flagged_early"] else "MISSED"
        trough_score = r["death_score_at_trough"]
        pre = r["pre_trough_scores"]
        pre_str = " | ".join(f"{s['days_before_trough']}d={s['death_score']}" for s in pre) if pre else "N/A"
        print(f"    {r['symbol']}: {flag} | Decline: {r['decline_pct']}% | Trough: {trough_score}")
        print(f"      History: {pre_str}")

    # Save
    output = {
        "equal_weight_backtest": ew_result,
        "grid_search": {
            "best_sharpe": grid["best_sharpe"],
            "best_weights": grid["best_weights"],
            "best_result": grid["best_result"],
            "top_10": grid["top_20"][:10],
            "total_combos": grid["total_combos_tested"],
        },
        "token_validation": dead,
        "config": {
            "lookback": 365,
            "forward": 30,
            "top_pct": 0.20,
            "n_assets": len(assets),
            "data_days": sig["max_n"],
        },
    }
    out_path = RESULTS_DIR / "death_score_results.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n[6] Saved to {out_path}")

    print("\n" + "=" * 70)
    print("DONE")
    print("=" * 70)


if __name__ == "__main__":
    main()
