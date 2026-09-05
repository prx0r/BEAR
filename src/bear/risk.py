"""Immutable safety guardrails (AlphaForge pattern).

Hard limits that cannot be overridden by config. Every order and portfolio
state must pass through these checks before execution.

THIS IS A RESEARCH-ONLY SYSTEM. NO LIVE TRADING. NO PAPER TRADING.
SIGNALS AND DASHBOARDS ONLY.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# ── LIVE TRADING BLOCK ──────────────────────────────────────────────────
# This system is research-only. Live trading is permanently disabled.
# Do NOT remove this block. Do NOT add order submission code.
# The address below is for monitoring/research reference only.

LIVE_TRADING_ENABLED: bool = False
PAPER_TRADING_ENABLED: bool = False
WALLET_ADDRESS: str = "0xaee6516380e2c090998b050a962ad1e3daf6cdbe"

def _block_live_trading(*args: Any, **kwargs: Any) -> None:
    """Always raises. This system does not trade."""
    raise RuntimeError(
        "BEAR is a research-only system. Live trading is disabled. "
        "This module produces signals and dashboards only. "
        f"Reference wallet: {WALLET_ADDRESS}"
    )

# Block any future execution module from being imported
import importlib
_original_import = builtins_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else __import__

def _guarded_import(name: str, *args: Any, **kwargs: Any):
    forbidden = {"bear.execution", "bear.live_trader", "bear.order_manager"}
    if name in forbidden:
        raise RuntimeError(f"Module '{name}' is blocked. BEAR is research-only.")
    return _original_import(name, *args, **kwargs)

try:
    import builtins
    builtins._original_import = builtins.__import__
    builtins.__import__ = _guarded_import
except (AttributeError, TypeError):
    pass  # non-standard builtins, skip guard
# ── END LIVE TRADING BLOCK ──────────────────────────────────────────────


@dataclass(frozen=True)
class RiskGuardrails:
    """Hard limits that cannot be overridden by config."""

    max_leverage: float = 3.0
    max_short_gross: float = 1.5  # max short notional / long notional
    max_single_name_weight: float = 0.35
    max_daily_loss_pct: float = 0.05  # 5%
    max_drawdown_pct: float = 0.15  # 15%
    min_adv_usd: float = 100_000  # don't trade illiquid
    max_squeeze_risk: float = 70.0  # reject high squeeze
    kill_switch_enabled: bool = True


def check_order(
    guardrails: RiskGuardrails,
    portfolio_state: dict[str, Any],
    order: dict[str, Any],
) -> tuple[bool, str]:
    """Validate order against guardrails.

    Args:
        guardrails: Immutable risk guardrails.
        portfolio_state: Current portfolio state with keys:
            - long_exposure: float (notional long value)
            - short_exposure: float (notional short value)
            - adv_usd: float (average daily volume for the asset)
            - squeeze_risk: float (0-100 squeeze score)
            - name_weight: float (proposed weight of this name in portfolio)
        order: Proposed order with keys:
            - side: 'buy' or 'sell' (sell = open short)
            - size_usd: float (notional size in USD)

    Returns:
        (allowed, reason) tuple. If allowed is False, reason explains why.
    """
    long_exposure = portfolio_state.get("long_exposure", 0.0)
    short_exposure = portfolio_state.get("short_exposure", 0.0)
    adv_usd = portfolio_state.get("adv_usd", 0.0)
    squeeze_risk = portfolio_state.get("squeeze_risk", 0.0)
    name_weight = portfolio_state.get("name_weight", 0.0)

    side = order.get("side", "")
    size_usd = order.get("size_usd", 0.0)

    # Kill switch
    if guardrails.kill_switch_enabled and portfolio_state.get("kill_switch_triggered", False):
        return False, "kill switch triggered"

    # Liquidity check
    if adv_usd < guardrails.min_adv_usd:
        return False, f"asset ADV ${adv_usd:,.0f} below minimum ${guardrails.min_adv_usd:,.0f}"

    # Squeeze risk check
    if squeeze_risk > guardrails.max_squeeze_risk:
        return False, f"squeeze risk {squeeze_risk:.1f} exceeds maximum {guardrails.max_squeeze_risk:.1f}"

    # Single name weight check
    if name_weight > guardrails.max_single_name_weight:
        return False, (
            f"name weight {name_weight:.2%} exceeds maximum "
            f"{guardrails.max_single_name_weight:.2%}"
        )

    # Leverage check (only for new shorts)
    if side == "sell":
        new_short = short_exposure + abs(size_usd)
        if long_exposure > 0:
            leverage = (long_exposure + new_short) / long_exposure
        else:
            leverage = 1.0 + abs(size_usd) / max(long_exposure, 1.0)

        if leverage > guardrails.max_leverage:
            return False, (
                f"leverage {leverage:.2f}x would exceed maximum "
                f"{guardrails.max_leverage:.2f}x"
            )

    # Short gross ratio check
    if side == "sell" and long_exposure > 0:
        new_short_gross = (short_exposure + abs(size_usd)) / long_exposure
        if new_short_gross > guardrails.max_short_gross:
            return False, (
                f"short gross ratio {new_short_gross:.2f} would exceed maximum "
                f"{guardrails.max_short_gross:.2f}"
            )

    return True, "order allowed"


def check_portfolio_health(
    guardrails: RiskGuardrails,
    equity_curve: list[float],
) -> tuple[bool, str]:
    """Check if portfolio breached any guardrails.

    Args:
        guardrails: Immutable risk guardrails.
        equity_curve: Historical equity values (chronological order).

    Returns:
        (healthy, reason) tuple. If healthy is False, reason explains why.
    """
    if not equity_curve or len(equity_curve) < 2:
        return True, "insufficient data for health check"

    initial = equity_curve[0]
    current = equity_curve[-1]

    if initial <= 0:
        return False, "initial equity is non-positive"

    # Daily loss check (last two points)
    if len(equity_curve) >= 2:
        prev = equity_curve[-2]
        if prev > 0:
            daily_return = (current - prev) / prev
            if daily_return < -guardrails.max_daily_loss_pct:
                return False, (
                    f"daily loss {daily_return:.2%} exceeds maximum "
                    f"-{guardrails.max_daily_loss_pct:.2%}"
                )

    # Drawdown check
    peak = equity_curve[0]
    max_dd = 0.0
    for value in equity_curve:
        if value > peak:
            peak = value
        if peak > 0:
            dd = (peak - value) / peak
            if dd > max_dd:
                max_dd = dd

    if max_dd > guardrails.max_drawdown_pct:
        return False, (
            f"max drawdown {max_dd:.2%} exceeds maximum "
            f"{guardrails.max_drawdown_pct:.2%}"
        )

    return True, "portfolio healthy"
