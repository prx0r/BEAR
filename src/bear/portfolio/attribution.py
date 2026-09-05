"""PnL attribution decomposition (Section 41).

Decomposes portfolio PnL into:
  - Long asset return contribution
  - Short asset return contribution
  - Market beta removed
  - Sector beta removed
  - Short-selection alpha
  - Funding income / cost
  - Trading fees
  - Slippage
  - Turnover cost
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np


@dataclass
class AttributionResult:
    """Full PnL attribution breakdown."""

    long_pnl: float
    short_pnl: float
    funding_pnl: float
    fees: float
    slippage: float
    turnover_cost: float

    # Decomposed
    long_asset_return: float = 0.0
    short_asset_return: float = 0.0
    market_beta_removed: float = 0.0
    sector_beta_removed: float = 0.0
    short_selection_alpha: float = 0.0
    funding_income: float = 0.0
    funding_cost: float = 0.0

    # Diagnostics
    hedge_efficiency: float = 0.0
    short_gross: float = 0.0
    long_gross: float = 0.0
    net_pnl: float = 0.0

    # Component contributions (per-name)
    component_pnl: Dict[str, float] = field(default_factory=dict)


def compute_attribution(
    long_pnl: float,
    short_pnl: float,
    funding_pnl: float,
    fees: float,
    slippage: float,
    *,
    long_gross: float = 1.0,
    short_gross: float = 1.0,
    market_beta: float = 0.0,
    sector_betas: Optional[Dict[str, float]] = None,
    short_returns: Optional[Dict[str, float]] = None,
    short_weights: Optional[Dict[str, float]] = None,
    sector_returns: Optional[Dict[str, float]] = None,
    turnover: float = 0.0,
    turnover_cost_rate: float = 0.001,
) -> AttributionResult:
    """Decompose PnL into attribution components.

    Args:
        long_pnl: Raw PnL from long positions.
        short_pnl: Raw PnL from short positions (positive = profitable short).
        funding_pnl: Net funding received/paid (positive = net receive).
        fees: Total trading fees paid.
        slippage: Total slippage cost.
        long_gross: Gross long exposure.
        short_gross: Gross short exposure.
        market_beta: Portfolio market beta.
        sector_betas: Per-sector betas {sector: beta}.
        short_returns: Per-name return contributions {name: return}.
        short_weights: Per-name weights {name: weight}.
        sector_returns: Per-sector return contributions {sector: return}.
        turnover: One-way turnover fraction.
        turnover_cost_rate: Cost per unit turnover.

    Returns:
        AttributionResult with full breakdown.
    """
    turnover_cost = abs(turnover) * turnover_cost_rate

    # Long asset return: direct contribution from long positions
    long_asset_return = long_pnl

    # Short asset return: direct contribution from short positions
    short_asset_return = short_pnl

    # Market beta removed: how much market risk was hedged
    market_beta_removed = market_beta * (long_gross - short_gross)

    # Sector beta removed
    sector_beta_removed = 0.0
    if sector_betas and sector_returns:
        for sector, beta in sector_betas.items():
            s_ret = sector_returns.get(sector, 0.0)
            sector_beta_removed += beta * s_ret

    # Short-selection alpha: excess return beyond beta explanation
    short_selection_alpha = short_pnl + market_beta_removed + sector_beta_removed

    # Funding split
    funding_income = max(funding_pnl, 0.0)
    funding_cost = abs(min(funding_pnl, 0.0))

    # Hedge efficiency
    if short_gross > 0:
        risk_removed = abs(short_pnl) - abs(short_selection_alpha)
        hedge_efficiency = max(0.0, risk_removed) / short_gross
    else:
        hedge_efficiency = 0.0

    net_pnl = long_pnl + short_pnl + funding_pnl - fees - slippage - turnover_cost

    return AttributionResult(
        long_pnl=long_pnl,
        short_pnl=short_pnl,
        funding_pnl=funding_pnl,
        fees=fees,
        slippage=slippage,
        turnover_cost=turnover_cost,
        long_asset_return=long_asset_return,
        short_asset_return=short_asset_return,
        market_beta_removed=market_beta_removed,
        sector_beta_removed=sector_beta_removed,
        short_selection_alpha=short_selection_alpha,
        funding_income=funding_income,
        funding_cost=funding_cost,
        hedge_efficiency=hedge_efficiency,
        short_gross=short_gross,
        long_gross=long_gross,
        net_pnl=net_pnl,
    )


def compute_attribution_timeseries(
    long_returns: np.ndarray,
    short_returns_matrix: np.ndarray,
    short_weights: np.ndarray,
    funding_rates: np.ndarray,
    fee_rate: float = 0.00035,
    slippage_bps: float = 2.0,
    turnover: Optional[np.ndarray] = None,
) -> List[AttributionResult]:
    """Compute per-period attribution for a time series.

    Args:
        long_returns: (T,) long portfolio returns per period.
        short_returns_matrix: (T, N) short name returns per period.
        short_weights: (N,) short weights (sums to short_gross).
        funding_rates: (T,) per-period funding rates (positive = short receives).
        fee_rate: Fee rate per unit traded.
        slippage_bps: Slippage in basis points.
        turnover: (T,) per-period turnover if available.

    Returns:
        List of AttributionResult, one per period.
    """
    T = len(long_returns)
    N = short_returns_matrix.shape[1]
    results = []

    for t in range(T):
        lr = float(long_returns[t])
        # Short PnL: positive when short drops
        sr = -float(short_weights @ short_returns_matrix[t])
        fr = float(funding_rates[t]) * float(np.sum(np.abs(short_weights)))
        fee = fee_rate * (abs(lr) + abs(sr))
        slip = slippage_bps / 10_000.0 * (abs(lr) + abs(sr))
        turn = float(turnover[t]) if turnover is not None else 0.0

        res = compute_attribution(
            long_pnl=lr,
            short_pnl=sr,
            funding_pnl=fr,
            fees=fee,
            slippage=slip,
            turnover=turn,
        )
        results.append(res)

    return results
