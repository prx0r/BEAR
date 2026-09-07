#!/usr/bin/env python3
"""BEAR Research Runner — literature-informed experiments.

Runs the experiments in order from DEV_PLAN.md:
  1. Zombie paper replication (P(zombie_28d))
  2. Guo replication (FDV/MC + 12w dilution)
  3. Kiefer/Nowotny replication (8-10w reversal)
  4. 2D dilution x return sorts
  5. Token age interactions
  6. All 4 models on real data
  7. TradableDeath combination

Usage:
    python research_runner.py --all
    python research_runner.py --experiment zombie
    python research_runner.py --experiment guo
    python research_runner.py --experiment reversal
    python research_runner.py --experiment combined
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

DATA_DIR = Path("/root/BEAR/data/binance")
RESULTS_DIR = Path("/root/BEAR/data/research_results")


def load_all_assets() -> dict[str, dict]:
    """Load all Binance daily data."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent / "src"))
    from bear.backtest.pit import load_binance_daily
    return load_binance_daily(DATA_DIR)


def run_zombie_replication(assets: dict[str, dict]) -> dict:
    """Experiment 1: Replicate zombie paper.

    Hypothesis: volume floor collapse is the strongest predictor.
    Method: compute P(zombie_28d) using volume features only.
    """
    print("\n" + "=" * 70)
    print("EXPERIMENT 1: ZOMBIE PAPER REPLICATION")
    print("=" * 70)

    from bear.models.death_hazard import (
        compute_zombie_target,
        compute_volume_floor_features,
    )

    results = {}
    btc = assets.get("BTC")
    btc_closes = btc["closes"] if btc else None

    for sym, data in assets.items():
        if sym == "BTC":
            continue
        if data["n"] < 200:
            continue

        closes = data["closes"]
        volumes = data["volumes"]
        timestamps = data["timestamps"]

        # Compute forward-looking zombie label
        target_28d = compute_zombie_target(volumes, timestamps, forward_days=28)
        target_90d = compute_zombie_target(volumes, timestamps, forward_days=90)

        # Compute features
        features = compute_volume_floor_features(closes, volumes, timestamps)

        # Evaluate: what fraction become zombie?
        valid_mask = ~np.isnan(target_28d)
        if valid_mask.sum() < 30:
            continue

        zombie_rate_28d = np.nanmean(target_28d)
        zombie_rate_90d = np.nanmean(target_90d)

        # Feature-target correlation (the key test)
        correlations = {}
        for feat_name, feat_vals in features.items():
            both_valid = valid_mask & ~np.isnan(feat_vals)
            if both_valid.sum() > 30:
                corr = np.corrcoef(feat_vals[both_valid], target_28d[both_valid])[0, 1]
                correlations[feat_name] = float(corr) if np.isfinite(corr) else 0.0

        results[sym] = {
            "n_days": int(data["n"]),
            "zombie_rate_28d": float(zombie_rate_28d),
            "zombie_rate_90d": float(zombie_rate_90d),
            "correlations_with_zombie_28d": correlations,
        }

    # Summary
    if results:
        avg_zombie_28d = np.mean([r["zombie_rate_28d"] for r in results.values()])
        avg_zombie_90d = np.mean([r["zombie_rate_90d"] for r in results.values()])

        # Rank features by average absolute correlation
        all_corrs = {}
        for r in results.values():
            for feat, corr in r["correlations_with_zombie_28d"].items():
                if feat not in all_corrs:
                    all_corrs[feat] = []
                all_corrs[feat].append(abs(corr))

        avg_corrs = {k: np.mean(v) for k, v in all_corrs.items()}
        ranked_features = sorted(avg_corrs.items(), key=lambda x: x[1], reverse=True)

        print(f"\nAssets analyzed: {len(results)}")
        print(f"Avg zombie rate (28d): {avg_zombie_28d:.1%}")
        print(f"Avg zombie rate (90d): {avg_zombie_90d:.1%}")
        print(f"\nFeature importance (avg |correlation| with zombie_28d):")
        for feat, corr in ranked_features[:10]:
            print(f"  {feat:40s}  {corr:.4f}")

    return {"results": results, "summary": {
        "n_assets": len(results),
        "avg_zombie_rate_28d": float(np.mean([r["zombie_rate_28d"] for r in results.values()])) if results else 0,
    }}


def run_guo_replication(assets: dict[str, dict]) -> dict:
    """Experiment 2: Replicate Guo — FDV overhang + dilution predict returns.

    Hypothesis: tokens with high FDV/MC and high recent dilution underperform.
    Test: quintile sorts on dilution_12w, measure forward returns.
    """
    print("\n" + "=" * 70)
    print("EXPERIMENT 2: GUO REPLICATION (DILUTION FACTOR)")
    print("=" * 70)

    from bear.models.structural_decay import compute_structural_decay_features

    # Build cross-sectional panel
    all_data = []
    for sym, data in assets.items():
        if data["n"] < 200:
            continue
        all_data.append({
            "symbol": sym,
            "closes": data["closes"],
            "volumes": data["volumes"],
            "timestamps": data["timestamps"],
            "n": data["n"],
        })

    if len(all_data) < 10:
        print("Not enough assets for cross-sectional test")
        return {"error": "insufficient_assets"}

    # For each day, rank by dilution and measure forward 30d return
    n_days = min(d["n"] for d in all_data)
    min_history = 182  # need 26 weeks for dilution_12w

    quintile_returns = {1: [], 2: [], 3: [], 4: [], 5: []}

    for t in range(min_history, n_days - 30):
        # Get dilution_12w for each asset at time t
        dilutions = {}
        forward_returns = {}

        for d in all_data:
            sym = d["symbol"]
            closes = d["closes"]
            volumes = d["volumes"]
            timestamps = d["timestamps"]

            # Compute dilution proxy: volume-weighted price decline
            # (We don't have supply data, so use price momentum as proxy)
            if t < 84 or t + 30 >= len(closes):
                continue

            # Simple dilution proxy: high volume + declining price = sell pressure
            vol_mean = np.mean(volumes[max(0, t - 84): t + 1])
            vol_recent = np.mean(volumes[max(0, t - 14): t + 1])
            price_change_12w = (closes[t] - closes[t - 84]) / closes[t - 84] if closes[t - 84] > 0 else 0

            # "Dilution" proxy: volume surge + price decline
            dilution_proxy = vol_recent / max(vol_mean, 1e-10) * max(-price_change_12w, 0)
            dilutions[sym] = dilution_proxy

            # Forward 30d return
            if t + 30 < len(closes) and closes[t] > 0:
                forward_returns[sym] = (closes[t + 30] - closes[t]) / closes[t]

        if len(dilutions) < 5:
            continue

        # Quintile sort
        syms = sorted(dilutions.keys(), key=lambda s: dilutions[s])
        n = len(syms)
        quintile_size = max(1, n // 5)

        for q in range(5):
            start = q * quintile_size
            end = start + quintile_size if q < 4 else n
            q_syms = syms[start:end]
            q_rets = [forward_returns[s] for s in q_syms if s in forward_returns]
            if q_rets:
                quintile_returns[q + 1].append(float(np.mean(q_rets)))

    # Summary
    print("\nDilution Quintile Sort (forward 30d returns):")
    print(f"{'Quintile':>10s}  {'Mean Return':>12s}  {'N periods':>10s}")
    print("-" * 40)

    quintile_summary = {}
    for q in range(1, 6):
        if quintile_returns[q]:
            mean_ret = float(np.mean(quintile_returns[q]))
            n_periods = len(quintile_returns[q])
            print(f"{q:>10d}  {mean_ret:>11.2%}  {n_periods:>10d}")
            quintile_summary[q] = {"mean_return": mean_ret, "n_periods": n_periods}
        else:
            print(f"{q:>10d}  {'N/A':>12s}  {'0':>10d}")

    # Long-short spread: Q5 (most dilute) vs Q1 (least dilute)
    if quintile_returns[1] and quintile_returns[5]:
        q1_mean = np.mean(quintile_returns[1])
        q5_mean = np.mean(quintile_returns[5])
        ls_spread = q1_mean - q5_mean  # long least dilute, short most dilute
        annualized_spread = ls_spread * 12
        print(f"\nLong-Short spread (Q1-Q5): {ls_spread:.2%} monthly, {annualized_spread:.2%} annualized")

    return {"quintile_returns": {k: [float(x) for x in v] for k, v in quintile_returns.items()},
            "quintile_summary": quintile_summary}


def run_reversal_replication(assets: dict[str, dict]) -> dict:
    """Experiment 3: Replicate Kiefer/Nowotny — 8-10w cross-sectional reversal.

    Hypothesis: 8-10 week winners subsequently underperform.
    Test: rank by past return, measure forward returns at multiple horizons.
    """
    print("\n" + "=" * 70)
    print("EXPERIMENT 3: KIEFER/NOWOTNY REPLICATION (REVERSAL)")
    print("=" * 70)

    # Build cross-sectional panel
    valid_assets = [(sym, data) for sym, data in assets.items()
                    if data["n"] >= 200]

    if len(valid_assets) < 10:
        print("Not enough assets")
        return {"error": "insufficient_assets"}

    min_history = 84  # 12 weeks
    n_days = min(d["n"] for _, d in valid_assets)

    results_by_horizon = {}

    for fwd_days, fwd_label in [(7, "7d"), (14, "14d"), (30, "30d"), (60, "60d"), (90, "90d")]:
        quintile_returns = {1: [], 2: [], 3: [], 4: [], 5: []}

        for lookback_days in [28, 56, 70, 84]:  # 4w, 8w, 10w, 12w
            for t in range(min_history, n_days - fwd_days):
                # Get past return for each asset
                past_returns = {}
                forward_returns = {}

                for sym, data in valid_assets:
                    closes = data["closes"]
                    if t < lookback_days or t + fwd_days >= len(closes):
                        continue
                    if closes[t - lookback_days] <= 0 or closes[t] <= 0:
                        continue

                    past_ret = (closes[t] - closes[t - lookback_days]) / closes[t - lookback_days]
                    fwd_ret = (closes[t + fwd_days] - closes[t]) / closes[t]

                    past_returns[sym] = past_ret
                    forward_returns[sym] = fwd_ret

                if len(past_returns) < 5:
                    continue

                # Quintile sort on past return
                syms = sorted(past_returns.keys(), key=lambda s: past_returns[s])
                n = len(syms)
                quintile_size = max(1, n // 5)

                for q in range(5):
                    start = q * quintile_size
                    end = start + quintile_size if q < 4 else n
                    q_syms = syms[start:end]
                    q_rets = [forward_returns[s] for s in q_syms if s in forward_returns]
                    if q_rets:
                        quintile_returns[q + 1].append(float(np.mean(q_rets)))

        # Summary for this horizon
        print(f"\nForward {fwd_label} returns by past-return quintile:")
        print(f"{'Quintile':>10s}  {'Mean Return':>12s}  {'N periods':>10s}")
        print("-" * 40)

        horizon_summary = {}
        for q in range(1, 6):
            if quintile_returns[q]:
                mean_ret = float(np.mean(quintile_returns[q]))
                n_periods = len(quintile_returns[q])
                print(f"{q:>10d}  {mean_ret:>11.2%}  {n_periods:>10d}")
                horizon_summary[q] = {"mean_return": mean_ret, "n_periods": n_periods}

        # Q1 (losers) vs Q5 (winners) spread
        if quintile_returns[1] and quintile_returns[5]:
            q1 = np.mean(quintile_returns[1])
            q5 = np.mean(quintile_returns[5])
            ls_spread = q5 - q1  # long winners, short losers? or reverse?
            # Actually: we want to know if winners REVERT
            # If Q5 (winners) have LOWER forward returns, that's reversal
            reversal_signal = q1 - q5  # positive = winners underperform losers
            print(f"\nReversal signal (Q1-Q5): {reversal_signal:.2%}")
            horizon_summary["reversal_signal"] = float(reversal_signal)

        results_by_horizon[fwd_label] = horizon_summary

    return {"results_by_horizon": results_by_horizon}


def run_2d_sort(assets: dict[str, dict]) -> dict:
    """Experiment 4: 2D dilution x return sorts.

    Tests the hypothesis: recent winner + heavy issuer = worst performer.
    """
    print("\n" + "=" * 70)
    print("EXPERIMENT 4: 2D DILUTION x RETURN SORTS")
    print("=" * 70)

    valid_assets = [(sym, data) for sym, data in assets.items()
                    if data["n"] >= 200]

    n_days = min(d["n"] for _, d in valid_assets)
    min_history = 84

    # 5x5 sort results
    sort_results = np.zeros((5, 5))
    sort_counts = np.zeros((5, 5))

    for t in range(min_history, n_days - 30):
        past_returns = {}
        volume_surchges = {}

        for sym, data in valid_assets:
            closes = data["closes"]
            volumes = data["volumes"]
            if t < 84 or t + 30 >= len(closes):
                continue
            if closes[t - 84] <= 0 or closes[t] <= 0:
                continue

            # 12-week return (past performance)
            ret_12w = (closes[t] - closes[t - 84]) / closes[t - 84]
            past_returns[sym] = ret_12w

            # Volume surge proxy for dilution
            vol_mean = np.mean(volumes[max(0, t - 84): t + 1])
            vol_recent = np.mean(volumes[max(0, t - 14): t + 1])
            vol_surge = vol_recent / max(vol_mean, 1e-10)
            volume_surchges[sym] = vol_surge

        if len(past_returns) < 10:
            continue

        # 5x5 sort
        syms = list(past_returns.keys())
        rets_arr = np.array([past_returns[s] for s in syms])
        vol_arr = np.array([volume_surchges[s] for s in syms])

        ret_quintiles = np.searchsorted(
            np.percentile(rets_arr, [20, 40, 60, 80]),
            rets_arr,
        )
        vol_quintiles = np.searchsorted(
            np.percentile(vol_arr, [20, 40, 60, 80]),
            vol_arr,
        )

        for i, sym in enumerate(syms):
            rq = ret_quintiles[i] + 1  # 1-5
            vq = vol_quintiles[i] + 1

            # Forward return
            data = dict(valid_assets)[sym]
            if t + 30 < len(data["closes"]) and data["closes"][t] > 0:
                fwd = (data["closes"][t + 30] - data["closes"][t]) / data["closes"][t]
                sort_results[rq - 1, vq - 1] += fwd
                sort_counts[rq - 1, vq - 1] += 1

    # Normalize
    with np.errstate(divide='ignore', invalid='ignore'):
        sort_avg = np.where(sort_counts > 0, sort_results / sort_counts, np.nan)

    print("\n5x5 Sort: Past Return (rows) x Volume Surge (columns)")
    print("Cell values = mean forward 30d return")
    print(f"{'':>8s}  {'Vol Q1':>8s}  {'Vol Q2':>8s}  {'Vol Q3':>8s}  {'Vol Q4':>8s}  {'Vol Q5':>8s}")
    print("-" * 60)
    for rq in range(5):
        row = f"Ret Q{rq+1:>2d}"
        for vq in range(5):
            val = sort_avg[rq, vq]
            if np.isfinite(val):
                row += f"  {val:>7.2%}"
            else:
                row += f"  {'N/A':>8s}"
        print(row)

    # Key test: Q5 return x Q5 volume (winner + surge) vs Q1 return x Q1 volume
    if np.isfinite(sort_avg[4, 4]) and np.isfinite(sort_avg[0, 0]):
        print(f"\nWinner+Surge (Q5xQ5): {sort_avg[4, 4]:.2%}")
        print(f"Loser+Stable (Q1xQ1): {sort_avg[0, 0]:.2%}")
        print(f"Difference: {sort_avg[4, 4] - sort_avg[0, 0]:.2%}")

    return {"sort_avg": sort_avg.tolist(), "sort_counts": sort_counts.tolist()}


def run_combined_model(assets: dict[str, dict]) -> dict:
    """Run all 4 models and combine via TradableDeath.

    Key: cross-sectional ranking across ALL assets at each time point.
    """
    print("\n" + "=" * 70)
    print("EXPERIMENT 7: COMBINED 4-MODEL + TRADEABLE DEATH")
    print("=" * 70)

    from bear.models.death_hazard import (
        DeathHazardModel,
        compute_volume_floor_features,
    )
    from bear.models.tradeability import (
        compute_tradeability_features,
        assess_tradeability,
        TradeabilitySignal,
    )

    btc = assets.get("BTC")
    btc_closes = btc["closes"] if btc else None

    model = DeathHazardModel()

    # Step 1: Compute raw feature values for each asset at latest time point
    raw_scores = {}
    for sym, data in assets.items():
        if sym == "BTC":
            continue
        if data["n"] < 200:
            continue

        closes = data["closes"]
        volumes = data["volumes"]
        timestamps = data["timestamps"]
        t = data["n"] - 1

        # A. Death Hazard — raw score
        vol_features = compute_volume_floor_features(closes, volumes, timestamps)
        death_scores = model.predict(vol_features, asset_age_days=float(data["n"]))
        death_raw = float(death_scores[t])

        # B. Structural Decay — raw features
        # Use volume-weighted price decline as dilution proxy
        vol_mean_84d = float(np.mean(volumes[max(0, t - 84): t + 1])) if t >= 84 else 1.0
        vol_recent_14d = float(np.mean(volumes[max(0, t - 14): t + 1]))
        vol_surge = vol_recent_14d / max(vol_mean_84d, 1e-10)

        price_change_12w = float((closes[t] - closes[t - 84]) / closes[t - 84]) if t >= 84 and closes[t - 84] > 0 else 0.0
        price_change_4w = float((closes[t] - closes[t - 28]) / closes[t - 28]) if t >= 28 and closes[t - 28] > 0 else 0.0

        # Volume death ratio
        vol_7d = float(np.mean(volumes[max(0, t - 6): t + 1]))
        vol_90d = float(np.mean(volumes[max(0, t - 89): t + 1]))
        vol_death_ratio = vol_7d / max(vol_90d, 1e-10)

        # C. Setup — reversal signal
        reversal_8w = price_change_12w  # 12-week return
        reversal_10w = float((closes[t] - closes[t - 70]) / closes[t - 70]) if t >= 70 and closes[t - 70] > 0 else 0.0

        # Residual momentum (vs BTC)
        if btc_closes is not None and t < len(btc_closes):
            btc_ret_8w = float((btc_closes[t] - btc_closes[t - 56]) / btc_closes[t - 56]) if t >= 56 and btc_closes[t - 56] > 0 else 0.0
            residual_mom = reversal_8w - btc_ret_8w
        else:
            residual_mom = reversal_8w

        # Volatility
        returns = np.diff(np.log(np.where(closes > 0, closes, np.nan)))
        vol_30d = float(np.nanstd(returns[max(0, t - 29): t + 1]) * np.sqrt(365)) if t >= 29 else 0.0

        # D. Tradeability
        trade_features = compute_tradeability_features(closes, volumes, btc_closes=btc_closes)
        trade_result = assess_tradeability(trade_features, t)

        raw_scores[sym] = {
            "death_raw": death_raw,
            "vol_surge": vol_surge,
            "price_change_12w": price_change_12w,
            "price_change_4w": price_change_4w,
            "vol_death_ratio": vol_death_ratio,
            "reversal_8w": reversal_8w,
            "reversal_10w": reversal_10w,
            "residual_mom": residual_mom,
            "vol_30d": vol_30d,
            "volume": float(volumes[t]),
            "tradeability": trade_result.signal.value,
            "crowd_score": trade_result.crowd_score,
            "carry_score": trade_result.carry_score,
            "veto_reasons": trade_result.veto_reasons,
            "n_days": data["n"],
        }

    if not raw_scores:
        return {"error": "no valid assets"}

    # Step 2: Cross-sectional percentile rank each feature across ALL assets
    def cross_sectional_rank(scores: dict[str, float], higher_is_worse: bool = True) -> dict[str, float]:
        items = [(k, v) for k, v in scores.items() if np.isfinite(v)]
        if len(items) < 2:
            return {k: 50.0 for k in scores}
        items.sort(key=lambda x: x[1], reverse=higher_is_worse)
        n = len(items)
        result = {}
        for rank, (k, v) in enumerate(items):
            result[k] = rank / (n - 1) * 100 if n > 1 else 50.0
        for k in scores:
            if k not in result:
                result[k] = np.nan
        return result

    # Rank features (higher = worse for short candidate)
    death_ranks = cross_sectional_rank({s: r["death_raw"] for s, r in raw_scores.items()})
    vol_surge_ranks = cross_sectional_rank({s: r["vol_surge"] for s, r in raw_scores.items()})
    reversal_ranks = cross_sectional_rank({s: r["reversal_8w"] for s, r in raw_scores.items()})  # high return = recent winner
    vol_death_ranks = cross_sectional_rank({s: 1.0 - r["vol_death_ratio"] for s, r in raw_scores.items()})  # low ratio = bad
    vol_ranks = cross_sectional_rank({s: r["vol_30d"] for s, r in raw_scores.items()})

    # Step 3: Combine with weights from DEV_PLAN
    results = {}
    for sym in raw_scores:
        r = raw_scores[sym]

        # Death Hazard weight: 0.35
        death_component = death_ranks.get(sym, 50.0) * 0.35

        # Structural decay (volume surge + price change): 0.25
        struct_component = (vol_surge_ranks.get(sym, 50.0) * 0.5 +
                           vol_death_ranks.get(sym, 50.0) * 0.5) * 0.25

        # Setup (reversal = recent winner): 0.25
        setup_component = reversal_ranks.get(sym, 50.0) * 0.25

        # Volatility (higher = more squeeze risk but also more opportunity): 0.15
        vol_component = vol_ranks.get(sym, 50.0) * 0.15

        composite = death_component + struct_component + setup_component + vol_component

        # Liquidity filter
        p_l = 1.0 if r["volume"] > 50_000 else 0.5 if r["volume"] > 10_000 else 0.1

        # TradableDeath = composite * liquidity * (1 - crowd_penalty)
        crowd_penalty = r["crowd_score"] / 200.0
        tradable_death = composite * p_l * (1 - crowd_penalty) / 100.0

        results[sym] = {
            "death_hazard_rank": float(death_ranks.get(sym, 50.0)),
            "structural_rank": float((vol_surge_ranks.get(sym, 50.0) + vol_death_ranks.get(sym, 50.0)) / 2),
            "setup_rank": float(reversal_ranks.get(sym, 50.0)),
            "vol_rank": float(vol_ranks.get(sym, 50.0)),
            "composite": float(composite),
            "tradeability": r["tradeability"],
            "crowd_score": r["crowd_score"],
            "carry_score": r["carry_score"],
            "veto_reasons": r["veto_reasons"],
            "tradable_death": float(tradable_death),
            "volume": r["volume"],
            "n_days": r["n_days"],
        }

    # Rank by TradableDeath
    ranked = sorted(results.items(), key=lambda x: x[1]["tradable_death"], reverse=True)

    print("\nTop 20 short candidates by TradableDeath:")
    print(f"{'Symbol':>8s}  {'Death':>6s}  {'Struct':>6s}  {'Setup':>6s}  {'Vol':>6s}  {'Trade':>8s}  {'TD':>6s}  {'Vol$':>10s}")
    print("-" * 80)
    for sym, r in ranked[:20]:
        print(f"{sym:>8s}  {r['death_hazard_rank']:5.1f}  {r['structural_rank']:5.1f}  "
              f"{r['setup_rank']:5.1f}  {r['vol_rank']:5.1f}  {r['tradeability']:>8s}  "
              f"{r['tradable_death']:5.3f}  ${r['volume']:>9.0f}")

    print(f"\nTotal assets ranked: {len(results)}")
    vetoed = sum(1 for r in results.values() if r["tradeability"] == "VETO")
    enter = sum(1 for r in results.values() if r["tradeability"] == "ENTER")
    wait = sum(1 for r in results.values() if r["tradeability"] == "WAIT")
    print(f"Tradeability: {enter} ENTER, {wait} WAIT, {vetoed} VETO")

    return {"ranked": [(s, r) for s, r in ranked[:30]], "all_results": results}


def main():
    parser = argparse.ArgumentParser(description="BEAR Research Runner")
    parser.add_argument("--experiment", "-e",
                        choices=["zombie", "guo", "reversal", "2d_sort", "combined", "all"],
                        default="all")
    parser.add_argument("--save", action="store_true", default=True)
    args = parser.parse_args()

    print("Loading assets...")
    assets = load_all_assets()
    print(f"Loaded {len(assets)} assets")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    all_results = {}

    if args.experiment in ("zombie", "all"):
        all_results["zombie"] = run_zombie_replication(assets)

    if args.experiment in ("guo", "all"):
        all_results["guo"] = run_guo_replication(assets)

    if args.experiment in ("reversal", "all"):
        all_results["reversal"] = run_reversal_replication(assets)

    if args.experiment in ("2d_sort", "all"):
        all_results["2d_sort"] = run_2d_sort(assets)

    if args.experiment in ("combined", "all"):
        all_results["combined"] = run_combined_model(assets)

    if args.save:
        out_path = RESULTS_DIR / f"research_{int(time.time())}.json"
        # Convert numpy types for JSON serialization
        def convert(obj):
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                return float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            return obj

        with open(out_path, "w") as f:
            json.dump(all_results, f, indent=2, default=convert)
        print(f"\nResults saved to {out_path}")

    print("\nDone.")


if __name__ == "__main__":
    main()
