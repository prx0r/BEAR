"""Optimizer constraints for the basket optimizer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class PortfolioConstraints:
    """All limits governing portfolio construction."""

    max_names: int = 5
    max_name_weight: float = 0.35
    min_name_weight: float = 0.0

    # Gross limits (short gross as fraction of long gross)
    min_short_gross_ratio: float = 0.40
    max_short_gross_ratio: float = 1.25

    # Long gross is implicit: sum of long weights
    min_long_gross: float = 0.0
    max_long_gross: float = 1.0

    # Net exposure
    min_net_exposure: float = -0.5
    max_net_exposure: float = 1.0

    # Per-name weight bounds
    min_weight: float = 0.0
    max_weight: float = 1.0

    # Liquidity constraints
    min_adv_usd: float = 100_000.0
    max_pct_of_adv: float = 0.05  # max position as fraction of ADV

    # Squeeze constraints
    max_squeeze_risk: float = 0.7  # exclude names above this
    squeeze_penalty: float = 0.0  # soft penalty in objective

    # Sector concentration
    max_sector_weight: Optional[float] = None  # e.g. 0.50
    sector_limits: Dict[str, float] = field(default_factory=dict)

    # Turnover
    max_turnover: float = 0.50  # max daily turnover as fraction of portfolio
    turnover_penalty: float = 0.01  # lambda for turnover cost

    # Regularization
    l2_weight_penalty: float = 0.01  # lambda_div

    # Cost model
    expected_cost_penalty: float = 0.005  # lambda_cost
    maker_fee_bps: float = 1.0
    taker_fee_bps: float = 3.5

    # Quality / carry signals
    short_quality_penalty: float = 0.0  # lambda_shortquality
    carry_penalty: float = 0.0  # lambda_carry

    # Stress weighting
    stress_weights: Dict[str, float] = field(default_factory=lambda: {
        "ordinary": 1.0,
        "btc_bottom_quartile": 2.0,
        "btc_bottom_decile": 4.0,
        "crash": 6.0,
    })

    # Allow negative weights (shorts)
    allow_short: bool = True

    def validate(self) -> List[str]:
        errors: List[str] = []
        if self.max_names < 1:
            errors.append("max_names must be >= 1")
        if not 0 < self.max_name_weight <= 1.0:
            errors.append("max_name_weight must be in (0, 1]")
        if self.min_short_gross_ratio < 0:
            errors.append("min_short_gross_ratio must be >= 0")
        if self.min_short_gross_ratio > self.max_short_gross_ratio:
            errors.append("min_short_gross_ratio <= max_short_gross_ratio")
        if self.min_adv_usd <= 0:
            errors.append("min_adv_usd must be > 0")
        return errors
