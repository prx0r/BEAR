"""BEAR lifecycle state machine.

Cash → BEAR SHORT / BEAR TRAP / QUALITY TREND → RELOAD → repeat

Tracks which sleeve is active and manages capital allocation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np


class State(Enum):
    CASH = "CASH"
    BEAR_SHORT = "BEAR_SHORT"
    BEAR_TRAP = "BEAR_TRAP"
    QUALITY_TREND = "QUALITY_TREND"
    RELOAD = "RELOAD"


@dataclass
class Position:
    symbol: str
    direction: str  # "long" or "short"
    entry_day: int
    entry_price: float
    size: float
    stop_loss: float = 0.0
    take_profit: float = 0.0


@dataclass
class LifecycleState:
    current_state: State = State.CASH
    capital: float = 100.0
    positions: list[Position] = field(default_factory=list)
    equity_curve: list[dict] = field(default_factory=list)
    state_history: list[dict] = field(default_factory=list)
    trade_log: list[dict] = field(default_factory=list)

    # Sleeve allocations (typical)
    cash_reserve: float = 0.80  # 80% cash
    bear_short_gross: float = 0.0
    bear_trap_gross: float = 0.0
    quality_trend_gross: float = 0.0


class LifecycleMachine:
    """State machine managing the full BEAR lifecycle."""

    def __init__(self, initial_capital: float = 100.0):
        self.state = LifecycleState(capital=initial_capital)

    def decide_state(
        self,
        btc_ret_4w: float,
        btc_ret_prev_4w: float,
        death_tokens_shortable: int,
        death_tokens_squeezing: int,
        death_tokens_reloading: int,
        quality_trending: int,
    ) -> State:
        """Decide which state to enter based on conditions."""
        s = self.state

        # UP→UP regime
        is_risk_on = btc_ret_4w > 0 and btc_ret_prev_4w > 0

        # DOWN regime
        is_risk_off = btc_ret_4w < -0.05

        # Current positions matter
        has_positions = len(s.positions) > 0

        # State transitions
        if s.current_state == State.CASH:
            if is_risk_off and death_tokens_shortable > 0:
                return State.BEAR_SHORT
            elif is_risk_on and death_tokens_squeezing > 0:
                return State.BEAR_TRAP
            elif is_risk_on and quality_trending > 0:
                return State.QUALITY_TREND

        elif s.current_state == State.BEAR_SHORT:
            if not is_risk_off or death_tokens_shortable == 0:
                return State.CASH
            if death_tokens_squeezing > 2:
                return State.BEAR_TRAP  # squeeze starting, switch

        elif s.current_state == State.BEAR_TRAP:
            if not is_risk_on:
                return State.CASH
            # Squeeze exhausts → reload
            if death_tokens_reloading > 0:
                return State.RELOAD

        elif s.current_state == State.QUALITY_TREND:
            if not is_risk_on:
                return State.CASH

        elif s.current_state == State.RELOAD:
            if is_risk_off:
                return State.BEAR_SHORT
            if not has_positions:
                return State.CASH

        return s.current_state

    def get_allocation(self, state: State) -> dict[str, float]:
        """Get capital allocation for each sleeve."""
        if state == State.CASH:
            return {"cash": 1.0, "bear_short": 0, "bear_trap": 0, "quality": 0}
        elif state == State.BEAR_SHORT:
            return {"cash": 0.20, "bear_short": 0.80, "bear_trap": 0, "quality": 0}
        elif state == State.BEAR_TRAP:
            return {"cash": 0.85, "bear_short": 0, "bear_trap": 0.10, "quality": 0.05}
        elif state == State.QUALITY_TREND:
            return {"cash": 0.85, "bear_short": 0, "bear_trap": 0, "quality": 0.15}
        elif state == State.RELOAD:
            return {"cash": 0.20, "bear_short": 0.80, "bear_trap": 0, "quality": 0}
        return {"cash": 1.0, "bear_short": 0, "bear_trap": 0, "quality": 0}


# ---------------------------------------------------------------------------
# Backtest with state machine
# ---------------------------------------------------------------------------

def run_lifecycle_backtest() -> dict[str, Any]:
    """Run the full lifecycle backtest."""
    from bear.models.bear_trap import (
        load_all_daily,
        detect_up_up_regime,
        compute_volume_death,
        compute_bear_trap_signal,
        compute_bear_reload_signal,
    )

    assets = load_all_daily()
    btc = assets.get("BTC")
    if btc is None:
        return {"error": "No BTC data"}

    n = btc["n"]
    btc_closes = btc["closes"]

    # Compute regime
    regime = detect_up_up_regime(btc_closes)

    # Run lifecycle
    machine = LifecycleMachine(initial_capital=100.0)

    for t in range(90, n - 1):
        # Regime
        is_risk_on = regime[t] if t < len(regime) else False

        # Count opportunities
        trap_signals = compute_bear_trap_signal(assets, t)
        reload_signals = compute_bear_reload_signal(assets, t)

        squeeze_count = sum(1 for s in trap_signals if s["signal"] == "SQUEEZE_STARTING")
        reload_count = sum(1 for s in reload_signals if s["signal"] == "RELOAD_SHORT")
        shortable_count = sum(1 for s in trap_signals if s["death_hazard"] >= 60)

        # BTC regime
        btc_ret_4w = (btc_closes[t] - btc_closes[t - 28]) / btc_closes[t - 28] if t >= 28 else 0
        btc_ret_prev_4w = (btc_closes[t - 28] - btc_closes[t - 56]) / btc_closes[t - 56] if t >= 56 else 0

        # Decide state
        new_state = machine.decide_state(
            btc_ret_4w, btc_ret_prev_4w,
            shortable_count, squeeze_count, reload_count,
            0,  # quality_trending (simplified)
        )

        if new_state != machine.state.current_state:
            machine.state.state_history.append({
                "day": t,
                "from": machine.state.current_state.value,
                "to": new_state.value,
                "btc_4w": round(btc_ret_4w, 4),
            })
            machine.state.current_state = new_state

        # Allocation
        alloc = machine.get_allocation(new_state)

        # Compute daily return
        btc_ret = (btc_closes[t + 1] - btc_closes[t]) / btc_closes[t]

        # Simplified: cash earns nothing, bear short earns -btc_ret (short), trap earns btc_ret * small
        daily_return = (
            alloc["cash"] * 0.0
            + alloc["bear_short"] * (-btc_ret * 0.5)  # partial hedge
            + alloc["bear_trap"] * (btc_ret * 0.3)     # small long exposure
            + alloc["quality"] * (btc_ret * 0.8)        # quality long
        )

        machine.state.capital *= (1 + daily_return)
        machine.state.equity_curve.append({
            "day": t,
            "equity": round(machine.state.capital, 4),
            "state": new_state.value,
            "btc_ret": round(btc_ret, 4),
        })

    # Summary
    eq = [e["equity"] for e in machine.state.equity_curve]
    if len(eq) > 1:
        returns = np.diff(eq) / eq[:-1]
        total_return = (eq[-1] - eq[0]) / eq[0]
        sharpe = float(np.mean(returns) / np.std(returns) * np.sqrt(365)) if np.std(returns) > 1e-10 else 0
    else:
        total_return = 0
        sharpe = 0

    # Time in each state
    state_counts = {}
    for e in machine.state.equity_curve:
        s = e["state"]
        state_counts[s] = state_counts.get(s, 0) + 1
    total_days = len(machine.state.equity_curve)
    state_pcts = {k: round(v / total_days * 100, 1) for k, v in state_counts.items()}

    return {
        "total_return_pct": round(total_return * 100, 2),
        "sharpe_ratio": round(sharpe, 3),
        "final_equity": round(eq[-1], 2),
        "total_days": total_days,
        "state_allocation": state_pcts,
        "state_transitions": machine.state.state_history[:20],
        "equity_curve": machine.state.equity_curve,
    }


if __name__ == "__main__":
    import json as _json

    print("=" * 70)
    print("BEAR LIFECYCLE BACKTEST")
    print("=" * 70)

    result = run_lifecycle_backtest()

    print(f"\n  Total Return: {result['total_return_pct']:+.2f}%")
    print(f"  Sharpe Ratio: {result['sharpe_ratio']:.3f}")
    print(f"  Final Equity: ${result['final_equity']:.2f}")
    print(f"  Period: {result['total_days']} days")
    print(f"\n  State allocation:")
    for state, pct in result.get("state_allocation", {}).items():
        print(f"    {state}: {pct}%")
    print(f"\n  State transitions:")
    for t in result.get("state_transitions", [])[:10]:
        print(f"    Day {t['day']}: {t['from']} → {t['to']} (BTC 4w: {t['btc_4w']:+.1%})")

    Path("/root/BEAR/data/lifecycle_backtest.json").write_text(
        _json.dumps(result, indent=2, default=str)
    )
    print(f"\nSaved to data/lifecycle_backtest.json")
