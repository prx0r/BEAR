"""Execution cost model (Section 42).

Provides realistic cost estimation across three scenarios:
  - Maker optimistic: passive fill, low impact
  - Taker realistic: aggressive fill, moderate impact
  - Stressed: high vol, thin book, large impact
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class CostEstimate:
    """Breakdown of estimated execution cost."""

    spread_cost: float
    market_impact: float
    fee: float
    total: float
    scenario: str


@dataclass
class MarketDepth:
    """Order book depth snapshot."""

    bid_price: float
    ask_price: float
    bid_depth_usd: float
    ask_depth_usd: float
    mid_price: float
    spread_bps: float


def _market_impact(
    trade_size: float,
    adv: float,
    spread_bps: float,
    depth_usd: float,
    participation_rate: float = 0.1,
    volatility: float = 0.02,
) -> float:
    """Square-root market impact model.

    impact = sigma * sqrt(participation) * sqrt(trade / depth)
    """
    if adv <= 0 or depth_usd <= 0:
        return abs(trade_size) * spread_bps / 10_000.0 * 2.0

    participation = min(abs(trade_size) / adv, 1.0)
    vol_impact = volatility * np.sqrt(participation)
    depth_impact = np.sqrt(abs(trade_size) / max(depth_usd, 1.0))
    return float(vol_impact * depth_impact * abs(trade_size))


def estimate_cost(
    trade_size: float,
    adv: float,
    spread: float,
    depth: Optional[float] = None,
    *,
    scenario: str = "taker_realistic",
    fee_rate: Optional[float] = None,
    volatility: float = 0.02,
    mid_price: float = 1.0,
) -> CostEstimate:
    """Estimate execution cost for a trade.

    Args:
        trade_size: Signed trade size in USD (positive = buy).
        adv: Average daily volume in USD.
        spread: Bid-ask spread in USD (absolute).
        depth: Order book depth in USD at best bid/ask.
        scenario: One of 'maker_optimistic', 'taker_realistic', 'stressed'.
        fee_rate: Override fee rate (fraction of notional).
        volatility: Daily volatility for impact model.
        mid_price: Mid price for spread conversion.

    Returns:
        CostEstimate with breakdown.
    """
    if mid_price <= 0:
        mid_price = 1.0
    if adv <= 0:
        adv = 1_000_000.0
    if depth is None:
        depth = adv * 0.01

    spread_bps = (spread / mid_price) * 10_000.0 if mid_price > 0 else 0.0
    abs_size = abs(trade_size)

    # Scenario parameters
    params = {
        "maker_optimistic": {
            "spread_mult": 0.3,
            "impact_mult": 0.5,
            "fee_override": fee_rate if fee_rate else 0.0001,
        },
        "taker_realistic": {
            "spread_mult": 0.7,
            "impact_mult": 1.0,
            "fee_override": fee_rate if fee_rate else 0.00035,
        },
        "stressed": {
            "spread_mult": 1.5,
            "impact_mult": 2.0,
            "fee_override": fee_rate if fee_rate else 0.0005,
        },
    }

    p = params.get(scenario, params["taker_realistic"])

    spread_cost = abs_size * spread_bps / 10_000.0 * p["spread_mult"]
    impact = _market_impact(trade_size, adv, spread_bps, depth, volatility=volatility) * p["impact_mult"]
    fee = abs_size * p["fee_override"]

    return CostEstimate(
        spread_cost=spread_cost,
        market_impact=impact,
        fee=fee,
        total=spread_cost + impact + fee,
        scenario=scenario,
    )


def estimate_rebalancing_cost(
    current_weights: np.ndarray,
    target_weights: np.ndarray,
    adv: np.ndarray,
    spread: np.ndarray,
    depth: Optional[np.ndarray] = None,
    portfolio_value: float = 1_000_000.0,
    scenario: str = "taker_realistic",
) -> float:
    """Estimate total cost of rebalancing from current to target weights.

    Args:
        current_weights: (N,) current portfolio weights.
        target_weights: (N,) target portfolio weights.
        adv: (N,) average daily volumes.
        spread: (N,) bid-ask spreads.
        depth: (N,) order book depths.
        portfolio_value: Total portfolio value in USD.
        scenario: Cost scenario.

    Returns:
        Total rebalancing cost in USD.
    """
    delta = target_weights - current_weights
    total_cost = 0.0

    for i in range(len(delta)):
        if abs(delta[i]) < 1e-8:
            continue
        trade_usd = delta[i] * portfolio_value
        d = float(depth[i]) if depth is not None else None
        cost = estimate_cost(
            trade_usd,
            float(adv[i]),
            float(spread[i]),
            d,
            scenario=scenario,
            mid_price=1.0,
        )
        total_cost += cost.total

    return total_cost
