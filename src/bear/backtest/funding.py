"""Funding-aware backtest module (Section 42-44).

Applies funding at actual timestamps, tracks funding PnL separately.
Positive funding = short receives (long pays).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import polars as pl


@dataclass
class FundingState:
    """Tracks funding accrual and settlement."""

    cumulative_funding_pnl: float = 0.0
    funding_history: List[Tuple[str, float]] = field(default_factory=list)
    last_funding_rate: float = 0.0
    accrued_since_last_settlement: float = 0.0

    def apply_funding(
        self,
        timestamp: str,
        rate: float,
        short_exposure: float,
        dt_fraction: float = 1.0,
    ) -> float:
        """Apply funding for one period.

        Args:
            timestamp: ISO timestamp.
            rate: Per-period funding rate (positive = shorts receive).
            short_exposure: Total short gross exposure (positive number).
            dt_fraction: Fraction of funding period elapsed.

        Returns:
            Funding PnL for this period (positive = short receives).
        """
        self.last_funding_rate = rate
        # Funding PnL: shorts receive rate * exposure
        funding_pnl = rate * short_exposure * dt_fraction
        self.cumulative_funding_pnl += funding_pnl
        self.accrued_since_last_settlement += funding_pnl
        self.funding_history.append((timestamp, funding_pnl))
        return funding_pnl

    def settle(self) -> float:
        """Settle accrued funding and return amount."""
        amount = self.accrued_since_last_settlement
        self.accrued_since_last_settlement = 0.0
        return amount


def compute_funding_pnl_series(
    funding_rates: pl.DataFrame,
    short_exposures: np.ndarray,
    timestamps: np.ndarray,
    rate_column: str = "funding_rate",
    timestamp_column: str = "timestamp",
) -> np.ndarray:
    """Compute funding PnL for each observation timestamp.

    Funding is applied at the actual timestamp of the rate, not interpolated.

    Args:
        funding_rates: DataFrame with timestamp and rate columns.
        short_exposures: (T,) short gross exposure per period.
        timestamps: (T,) observation timestamps.
        rate_column: Name of rate column.
        timestamp_column: Name of timestamp column.

    Returns:
        (T,) funding PnL per period.
    """
    T = len(timestamps)
    funding_pnl = np.zeros(T)

    if funding_rates.is_empty():
        return funding_pnl

    # Ensure sorted
    fr = funding_rates.sort(timestamp_column)
    fr_times = fr[timestamp_column].to_list()
    fr_rates = fr[rate_column].to_list()

    # For each observation timestamp, find the applicable funding rate
    # (the most recent rate at or before the observation time)
    rate_idx = 0
    for t in range(T):
        obs_time = timestamps[t]

        # Advance rate_idx to the most recent rate <= obs_time
        while rate_idx < len(fr_times) - 1 and fr_times[rate_idx + 1] <= obs_time:
            rate_idx += 1

        rate = fr_rates[rate_idx] if rate_idx < len(fr_rates) else 0.0
        funding_pnl[t] = rate * short_exposures[t]

    return funding_pnl


def apply_funding_at_timestamps(
    equity_curve: pl.DataFrame,
    funding_rates: pl.DataFrame,
    short_weights: Dict[str, float],
    price_columns: Dict[str, str],
    rate_column: str = "funding_rate",
) -> pl.DataFrame:
    """Apply funding to equity curve at actual timestamps.

    Args:
        equity_curve: DataFrame with timestamp column.
        funding_rates: DataFrame with timestamp and rate columns.
        short_weights: {symbol: weight} mapping.
        price_columns: {symbol: price_column_name} mapping.
        rate_column: Name of funding rate column.

    Returns:
        Updated DataFrame with funding_pnl column added.
    """
    if funding_rates.is_empty():
        return equity_curve.with_columns(pl.lit(0.0).alias("funding_pnl"))

    # Compute short exposure from weights and prices
    short_gross = sum(abs(w) for w in short_weights.values())

    result = equity_curve.clone()
    fr = funding_rates.sort("timestamp")

    funding_pnl_values = []
    for row in result.iter_rows(named=True):
        obs_time = row["timestamp"]
        # Find applicable rate
        applicable = fr.filter(pl.col("timestamp") <= obs_time)
        if applicable.is_empty():
            rate = 0.0
        else:
            rate = applicable[rate_column].tail(1).item()
        funding_pnl_values.append(rate * short_gross)

    return result.with_columns(pl.Series("funding_pnl", funding_pnl_values))


def aggregate_funding_by_period(
    funding_rates: pl.DataFrame,
    period: str = "1w",
    rate_column: str = "funding_rate",
    timestamp_column: str = "timestamp",
) -> pl.DataFrame:
    """Aggregate funding rates by period.

    Args:
        funding_rates: Raw funding rates.
        period: Aggregation period ('1d', '1w', '1M').
        rate_column: Rate column name.
        timestamp_column: Timestamp column name.

    Returns:
        Aggregated funding rates per period.
    """
    return (
        funding_rates
        .with_columns(pl.col(timestamp_column).dt.truncate(period).alias("period"))
        .group_by("period")
        .agg([
            pl.col(rate_column).mean().alias("avg_rate"),
            pl.col(rate_column).max().alias("max_rate"),
            pl.col(rate_column).min().alias("min_rate"),
            pl.col(rate_column).count().alias("observations"),
        ])
        .sort("period")
    )
