"""Paper trading engine — 4-model architecture (TradableDeath).

Runs the literature-informed strategy daily:
  A. DEATH_HAZARD — volume floor collapse
  B. STRUCTURAL_DECAY — dilution, FDV/MC
  C. SETUP — 8-10w reversal (recent winners revert)
  D. TRADEABILITY — crowding vetoes, BTC regime

Combined via: TradableDeath = P_D × P_L × (1 - P_R)

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


# ---------------------------------------------------------------------------
# Model A: Death Hazard (volume floor collapse)
# ---------------------------------------------------------------------------

def compute_death_hazard_at(assets: dict[str, dict], t: int) -> list[dict]:
    """Compute death hazard scores at time t for all assets.

    Uses volume floor features from the zombie paper replication.
    """
    from bear.models.death_hazard import DeathHazardModel, compute_volume_floor_features

    model = DeathHazardModel()
    scores = []

    for sym, data in assets.items():
        if sym in BLUE_CHIPS or sym == "BTC":
            continue
        if data["n"] <= t or t < 182:
            continue

        closes = data["closes"][:t + 1]
        volumes = data["volumes"][:t + 1]
        timestamps = data["timestamps"][:t + 1]

        features = compute_volume_floor_features(closes, volumes, timestamps)
        hazard = model.predict(features, asset_age_days=float(t))

        scores.append({
            "symbol": sym,
            "death_hazard": float(hazard[-1]),
            "volume_ratio": float(features["volume_ratio_7d_90d"][-1])
                if np.isfinite(features["volume_ratio_7d_90d"][-1]) else None,
            "volume_floor_slope": float(features["volume_floor_slope"][-1])
                if np.isfinite(features["volume_floor_slope"][-1]) else None,
        })

    scores.sort(key=lambda x: x["death_hazard"], reverse=True)
    return scores


# ---------------------------------------------------------------------------
# Model B: Structural Decay (dilution proxy)
# ---------------------------------------------------------------------------

def compute_structural_decay_at(assets: dict[str, dict], t: int) -> list[dict]:
    """Compute structural decay scores at time t.

    Uses volume surge × price decline as dilution proxy.
    """
    scores = []

    for sym, data in assets.items():
        if sym in BLUE_CHIPS or sym == "BTC":
            continue
        if data["n"] <= t or t < 84:
            continue

        closes = data["closes"][:t + 1]
        volumes = data["volumes"][:t + 1]

        # Dilution proxy: volume surge × price decline
        vol_mean_84d = float(np.mean(volumes[max(0, t - 84): t + 1]))
        vol_recent_14d = float(np.mean(volumes[max(0, t - 14): t + 1]))
        vol_surge = vol_recent_14d / max(vol_mean_84d, 1e-10)

        price_change_12w = float((closes[t] - closes[t - 84]) / closes[t - 84]) if closes[t - 84] > 0 else 0.0

        # Volume death
        vol_7d = float(np.mean(volumes[max(0, t - 6): t + 1]))
        vol_90d = float(np.mean(volumes[max(0, t - 89): t + 1]))
        vol_death = 1.0 - vol_7d / max(vol_90d, 1e-10)

        # Composite: higher = more structurally doomed
        struct_score = (vol_surge * 30 + max(-price_change_12w, 0) * 50 + vol_death * 20)
        struct_score = min(100.0, max(0.0, struct_score))

        scores.append({
            "symbol": sym,
            "structural_decay": round(struct_score, 1),
            "vol_surge": round(vol_surge, 3),
            "price_change_12w": round(price_change_12w, 4),
            "vol_death": round(vol_death, 3),
        })

    scores.sort(key=lambda x: x["structural_decay"], reverse=True)
    return scores


# ---------------------------------------------------------------------------
# Model C: Setup (8-10w reversal)
# ---------------------------------------------------------------------------

def compute_setup_at(assets: dict[str, dict], t: int, btc_closes: np.ndarray | None = None) -> list[dict]:
    """Compute setup scores at time t.

    Recent winners revert at 60-90d horizons (Kiefer/Nowotny 2026).
    """
    scores = []

    for sym, data in assets.items():
        if sym in BLUE_CHIPS or sym == "BTC":
            continue
        if data["n"] <= t or t < 84:
            continue

        closes = data["closes"][:t + 1]

        # 8w and 10w reversal
        reversal_8w = float((closes[t] - closes[t - 56]) / closes[t - 56]) if closes[t - 56] > 0 else 0.0
        reversal_10w = float((closes[t] - closes[t - 70]) / closes[t - 70]) if t >= 70 and closes[t - 70] > 0 else 0.0

        # Residual momentum (vs BTC)
        residual_mom = reversal_8w
        if btc_closes is not None and t < len(btc_closes) and t >= 56:
            btc_ret = float((btc_closes[t] - btc_closes[t - 56]) / btc_closes[t - 56]) if btc_closes[t - 56] > 0 else 0.0
            residual_mom = reversal_8w - btc_ret

        # Setup score: high reversal = good short setup
        setup_score = max(0.0, min(100.0, reversal_8w * 100 + 50))

        scores.append({
            "symbol": sym,
            "setup_score": round(setup_score, 1),
            "reversal_8w": round(reversal_8w, 4),
            "reversal_10w": round(reversal_10w, 4),
            "residual_momentum": round(residual_mom, 4),
        })

    scores.sort(key=lambda x: x["setup_score"], reverse=True)
    return scores


# ---------------------------------------------------------------------------
# Model D: Tradeability (crowding vetoes)
# ---------------------------------------------------------------------------

def compute_tradeability_at(
    assets: dict[str, dict],
    t: int,
    btc_closes: np.ndarray | None = None,
) -> list[dict]:
    """Compute tradeability signals at time t.

    ENTER / WAIT / VETO based on crowding and regime.
    """
    results = []

    for sym, data in assets.items():
        if sym in BLUE_CHIPS or sym == "BTC":
            continue
        if data["n"] <= t or t < 30:
            continue

        closes = data["closes"][:t + 1]
        volumes = data["volumes"][:t + 1]

        # Crowding signals
        ret_7d = float((closes[t] - closes[t - 7]) / closes[t - 7]) if closes[t - 7] > 0 else 0.0
        crowd_score = 0.0
        veto_reasons = []

        # VETO: BTC rallying
        if btc_closes is not None and t < len(btc_closes) and t >= 30:
            btc_30d = float((btc_closes[t] - btc_closes[t - 30]) / btc_closes[t - 30]) if btc_closes[t - 30] > 0 else 0.0
            if btc_30d > 0.10:
                veto_reasons.append(f"btc_rallying ({btc_30d:.1%})")
                crowd_score += 20

        # Crowd: big recent rally
        if ret_7d > 0.15:
            crowd_score += 15

        # Crowd: volume climax
        vol_7d = float(np.mean(volumes[max(0, t - 6): t + 1]))
        vol_30d = float(np.mean(volumes[max(0, t - 29): t + 1]))
        vol_climax = vol_7d / max(vol_30d, 1e-10)
        if vol_climax > 2.0:
            crowd_score += 10

        crowd_score = min(100.0, crowd_score)

        # Signal
        if veto_reasons:
            signal = "VETO"
        elif crowd_score > 60:
            signal = "WAIT"
        else:
            signal = "ENTER"

        results.append({
            "symbol": sym,
            "tradeability": signal,
            "crowd_score": round(crowd_score, 1),
            "veto_reasons": veto_reasons,
            "ret_7d": round(ret_7d, 4),
        })

    return results


# ---------------------------------------------------------------------------
# TradableDeath combination
# ---------------------------------------------------------------------------

def compute_tradable_death_at(assets: dict[str, dict], t: int) -> list[dict]:
    """Compute TradableDeath scores at time t.

    TradableDeath = P_D × P_L × (1 - P_R)
    """
    btc = assets.get("BTC")
    btc_closes = btc["closes"] if btc and btc["n"] > t else None

    # Get all model scores
    death_scores = compute_death_hazard_at(assets, t)
    struct_scores = compute_structural_decay_at(assets, t)
    setup_scores = compute_setup_at(assets, t, btc_closes)
    trade_scores = compute_tradeability_at(assets, t, btc_closes)

    # Merge by symbol
    by_sym: dict[str, dict] = {}
    for s in death_scores:
        by_sym.setdefault(s["symbol"], {}).update(s)
    for s in struct_scores:
        by_sym.setdefault(s["symbol"], {}).update(s)
    for s in setup_scores:
        by_sym.setdefault(s["symbol"], {}).update(s)
    for s in trade_scores:
        by_sym.setdefault(s["symbol"], {}).update(s)

    # Cross-sectional percentile rank each component
    def pct_rank(vals: dict[str, float]) -> dict[str, float]:
        items = [(k, v) for k, v in vals.items() if np.isfinite(v)]
        if len(items) < 2:
            return {k: 50.0 for k in vals}
        items.sort(key=lambda x: x[1])
        n = len(items)
        return {k: (rank / (n - 1) * 100) for rank, (k, _) in enumerate(items)}

    death_vals = {s: d.get("death_hazard", 50) for s, d in by_sym.items()}
    struct_vals = {s: d.get("structural_decay", 50) for s, d in by_sym.items()}
    setup_vals = {s: d.get("setup_score", 50) for s, d in by_sym.items()}

    death_ranks = pct_rank(death_vals)
    struct_ranks = pct_rank(struct_vals)
    setup_ranks = pct_rank(setup_vals)

    # Combine
    results = []
    for sym, data in by_sym.items():
        dr = death_ranks.get(sym, 50.0)
        sr = struct_ranks.get(sym, 50.0)
        ur = setup_ranks.get(sym, 50.0)

        # Weighted composite
        composite = dr * 0.35 + sr * 0.25 + ur * 0.25 + 50 * 0.15

        # Liquidity filter
        vol = assets.get(sym, {}).get("volumes", np.array([0]))[min(t, len(assets.get(sym, {}).get("volumes", [])) - 1)] if sym in assets else 0
        p_l = 1.0 if vol > 50_000 else 0.5 if vol > 10_000 else 0.1

        # Crowd penalty
        crowd = data.get("crowd_score", 0)
        crowd_penalty = crowd / 200.0

        tradable_death = composite * p_l * (1 - crowd_penalty) / 100.0

        results.append({
            "symbol": sym,
            "death_hazard": round(dr, 1),
            "structural_decay": round(sr, 1),
            "setup_score": round(ur, 1),
            "composite": round(composite, 1),
            "tradable_death": round(tradable_death, 4),
            "tradeability": data.get("tradeability", "VETO"),
            "crowd_score": data.get("crowd_score", 0),
            "veto_reasons": data.get("veto_reasons", []),
            "reversal_8w": data.get("reversal_8w"),
            "volume_ratio": data.get("volume_ratio"),
            "vol_surge": data.get("vol_surge"),
        })

    results.sort(key=lambda x: x["tradable_death"], reverse=True)
    return results


# ---------------------------------------------------------------------------
# Paper trading simulation
# ---------------------------------------------------------------------------

class PaperTrader:
    """Paper trader using 4-model TradableDeath architecture."""

    def __init__(self, initial_capital: float = 100.0):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.positions: list[dict] = []
        self.trades: list[dict] = []
        self.equity_curve: list[dict] = []
        self.regime_history: list[dict] = []

    def check_regime(self, btc_ret_30d: float) -> str:
        """Regime filter: only short when BTC not rallying."""
        if btc_ret_30d > 0.10:
            return "SKIP"
        elif btc_ret_30d < -0.05:
            return "AGGRESSIVE"
        else:
            return "ACTIVE"

    def run(
        self,
        assets: dict[str, dict] | None = None,
        start_day: int = 365,
        end_day: int | None = None,
        rebalance_freq: int = 30,
    ) -> dict[str, Any]:
        """Run paper trading simulation with 4-model architecture."""
        if assets is None:
            assets = load_daily_data()

        btc = assets.get("BTC")
        if btc is None:
            return {"error": "No BTC data"}

        max_n = btc["n"]
        if end_day is None:
            end_day = max_n - 1

        self.__init__()

        for t in range(start_day, end_day + 1):
            # Close mature positions (>30 days old)
            self._close_positions(assets, t)

            # Check regime
            btc_ret_30d = None
            if t >= 30 and btc["closes"][t - 30] > 0:
                btc_ret_30d = (btc["closes"][t] - btc["closes"][t - 30]) / btc["closes"][t - 30]

            regime = self.check_regime(btc_ret_30d) if btc_ret_30d is not None else "SKIP"

            self.regime_history.append({
                "day": t,
                "btc_30d_return": round(btc_ret_30d, 4) if btc_ret_30d is not None else None,
                "regime": regime,
            })

            # Rebalance
            if (t - start_day) % rebalance_freq == 0:
                if regime in ("ACTIVE", "AGGRESSIVE"):
                    candidates = compute_tradable_death_at(assets, t)
                    # Only ENTER candidates
                    enterable = [c for c in candidates if c["tradeability"] == "ENTER"]
                    # Top 5 by TradableDeath
                    for c in enterable[:5]:
                        self._open_short(c["symbol"], t, assets)

            # Snapshot equity
            equity = self._snapshot_equity(assets, t)
            self.equity_curve.append({
                "day": t,
                "equity": round(equity, 4),
                "capital": round(self.capital, 4),
                "n_positions": len(self.positions),
                "regime": regime,
            })

        # Summary
        eq_vals = [e["equity"] for e in self.equity_curve]
        if len(eq_vals) > 1:
            returns = [(eq_vals[i] - eq_vals[i - 1]) / eq_vals[i - 1]
                       for i in range(1, len(eq_vals)) if eq_vals[i - 1] > 0]
            total_return = (eq_vals[-1] - eq_vals[0]) / eq_vals[0] if eq_vals[0] > 0 else 0
            mean_ret = np.mean(returns) if returns else 0
            std_ret = np.std(returns) if len(returns) > 1 else 1
            sharpe = (mean_ret / std_ret * np.sqrt(365)) if std_ret > 1e-10 else 0
        else:
            total_return = 0
            sharpe = 0

        win_trades = [t for t in self.trades if t.get("pnl", 0) > 0]
        win_rate = len(win_trades) / len(self.trades) * 100 if self.trades else 0
        active_days = sum(1 for r in self.regime_history if r["regime"] in ("ACTIVE", "AGGRESSIVE"))
        skip_days = sum(1 for r in self.regime_history if r["regime"] == "SKIP")

        return {
            "summary": {
                "initial_capital": self.initial_capital,
                "final_equity": round(eq_vals[-1], 2) if eq_vals else self.initial_capital,
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

    def _open_short(self, symbol: str, t: int, assets: dict) -> None:
        """Open a short position."""
        if symbol not in assets:
            return
        price = float(assets[symbol]["closes"][t])
        if price <= 0:
            return

        position_size = self.capital * 0.02  # 2% per trade
        self.positions.append({
            "symbol": symbol,
            "entry_day": t,
            "entry_price": price,
            "size": position_size,
        })
        self.capital -= position_size * 0.001  # entry cost

    def _close_positions(self, assets: dict, t: int) -> None:
        """Close positions older than 30 days."""
        closed = []
        for pos in self.positions[:]:
            age = t - pos["entry_day"]
            if age >= 30:
                if pos["symbol"] in assets and t < len(assets[pos["symbol"]]["closes"]):
                    current_price = float(assets[pos["symbol"]]["closes"][t])
                    entry_price = pos["entry_price"]
                    if entry_price > 0:
                        # Short PnL: (entry - current) / entry
                        pnl = pos["size"] * (entry_price - current_price) / entry_price
                        self.capital += pos["size"] + pnl
                        self.trades.append({
                            "symbol": pos["symbol"],
                            "entry_day": pos["entry_day"],
                            "exit_day": t,
                            "entry_price": entry_price,
                            "exit_price": current_price,
                            "pnl": round(pnl, 4),
                            "pnl_pct": round((entry_price - current_price) / entry_price * 100, 2),
                            "size": pos["size"],
                        })
                closed.append(pos)

        for pos in closed:
            self.positions.remove(pos)

    def _snapshot_equity(self, assets: dict, t: int) -> float:
        """Current equity = capital + unrealized PnL."""
        unrealized = 0.0
        for pos in self.positions:
            if pos["symbol"] in assets and t < len(assets[pos["symbol"]]["closes"]):
                current = float(assets[pos["symbol"]]["closes"][t])
                entry = pos["entry_price"]
                if entry > 0:
                    unrealized += pos["size"] * (entry - current) / entry
        return self.capital + unrealized


def run_once() -> dict[str, Any]:
    """Run the paper trader once and save state."""
    assets = load_daily_data()
    btc = assets.get("BTC")
    if btc is None:
        return {"error": "No BTC data"}

    trader = PaperTrader(initial_capital=100.0)
    result = trader.run(assets)

    # Save state
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": result["summary"],
        "current_regime": result["current_regime"],
    }
    STATE_PATH.write_text(json.dumps(state, indent=2, default=str))

    print(f"\n{'=' * 60}")
    print("PAPER TRADING RESULTS (4-Model Architecture)")
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
        print(f"  Current Regime: {cr['regime']} (BTC 30d: {ret_str})")
        print(f"{'=' * 60}")

    return result


if __name__ == "__main__":
    run_once()
