"""Performance metrics (Section 47).

Standard and pair-specific metrics for evaluating backtest performance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np


@dataclass
class PerformanceMetrics:
    """Full performance report."""

    # Standard
    total_return: float = 0.0
    cagr: float = 0.0
    annual_volatility: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_duration_days: int = 0
    calmar_ratio: float = 0.0

    # Risk
    var_95: float = 0.0
    cvar_95: float = 0.0
    skewness: float = 0.0
    kurtosis: float = 0.0

    # Trade quality
    hit_rate: float = 0.0
    avg_winner: float = 0.0
    avg_loser: float = 0.0
    profit_factor: float = 0.0
    worst_day: float = 0.0
    worst_week: float = 0.0
    worst_squeeze_event: float = 0.0
    best_day: float = 0.0
    best_week: float = 0.0

    # Pair-specific
    avg_relative_spread_return: float = 0.0
    hedge_ratio_stability: float = 0.0
    correlation_stability: float = 0.0

    # Comparison
    long_only_return: float = 0.0
    hedged_return: float = 0.0
    hedge_benefit: float = 0.0

    # Period breakdown
    monthly_returns: Dict[str, float] = field(default_factory=dict)
    yearly_returns: Dict[str, float] = field(default_factory=dict)


def compute_metrics(
    equity_curve: np.ndarray,
    long_only_curve: Optional[np.ndarray] = None,
    spread_returns: Optional[np.ndarray] = None,
    hedge_ratios: Optional[np.ndarray] = None,
    correlations: Optional[np.ndarray] = None,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 365,
    squash_events: Optional[np.ndarray] = None,
) -> PerformanceMetrics:
    """Compute full performance metrics from equity curve.

    Args:
        equity_curve: (T,) portfolio equity values.
        long_only_curve: (T,) long-only equity for comparison.
        spread_returns: (T,) relative spread returns per period.
        hedge_ratios: (T,) hedge ratio time series.
        correlations: (T,) correlation time series.
        risk_free_rate: Annual risk-free rate.
        periods_per_year: Trading periods per year.
        squash_events: (T,) binary indicator of squeeze events.

    Returns:
        PerformanceMetrics with all computed metrics.
    """
    if len(equity_curve) < 2:
        return PerformanceMetrics()

    eq = np.asarray(equity_curve, dtype=np.float64)
    returns = np.diff(eq) / eq[:-1]
    returns = np.nan_to_num(returns, nan=0.0, posinf=0.0, neginf=0.0)

    T = len(returns)

    # Basic returns
    total_return = float((eq[-1] / eq[0]) - 1.0)
    years = T / periods_per_year
    cagr = float(((1.0 + total_return) ** (1.0 / max(years, 1e-10))) - 1.0) if total_return > -1.0 else -1.0

    # Volatility
    annual_vol = float(np.std(returns) * np.sqrt(periods_per_year))

    # Sharpe
    excess = returns - risk_free_rate / periods_per_year
    sharpe = float(np.mean(excess) / max(np.std(excess, ddof=1), 1e-10) * np.sqrt(periods_per_year))

    # Sortino
    downside = excess[excess < 0]
    downside_dev = float(np.std(downside, ddof=1)) if len(downside) > 1 else 1e-10
    sortino = float(np.mean(excess) / max(downside_dev, 1e-10) * np.sqrt(periods_per_year))

    # Drawdown
    cummax = np.maximum.accumulate(eq)
    drawdowns = (eq - cummax) / np.maximum(cummax, 1e-10)
    max_dd = float(np.min(drawdowns))

    # Max drawdown duration
    in_dd = eq < cummax
    dd_durations = np.diff(np.where(np.concatenate(([0], in_dd.astype(int), [0])))[0])
    max_dd_duration = int(np.max(dd_durations)) if len(dd_durations) > 0 else 0

    # Calmar
    calmar = float(cagr / abs(max_dd)) if abs(max_dd) > 1e-10 else 0.0

    # VaR / CVaR
    var_95 = float(np.percentile(returns, 5))
    cvar_95 = float(np.mean(returns[returns <= var_95])) if np.any(returns <= var_95) else var_95

    # Higher moments
    skew = float(np.mean(returns ** 3) / max(np.std(returns) ** 3, 1e-10))
    kurt = float(np.mean(returns ** 4) / max(np.std(returns) ** 4, 1e-10) - 3.0)

    # Trade quality
    winners = returns[returns > 0]
    losers = returns[returns < 0]
    hit_rate = float(len(winners) / max(T, 1))
    avg_win = float(np.mean(winners)) if len(winners) > 0 else 0.0
    avg_los = float(np.mean(losers)) if len(losers) > 0 else 0.0
    profit_factor = float(np.sum(winners) / abs(np.sum(losers))) if np.sum(losers) != 0 else float("inf")

    worst_day = float(np.min(returns))
    best_day = float(np.max(returns))

    # Weekly (assuming daily)
    if T >= 5:
        weekly_returns = np.array([
            np.prod(1 + returns[i:i + 5]) - 1
            for i in range(0, T - 4, 5)
        ])
        worst_week = float(np.min(weekly_returns)) if len(weekly_returns) > 0 else 0.0
        best_week = float(np.max(weekly_returns)) if len(weekly_returns) > 0 else 0.0
    else:
        worst_week = worst_day
        best_week = best_day

    # Squeeze events
    worst_squeeze = 0.0
    if squash_events is not None:
        se = np.asarray(squash_events, dtype=bool)
        if np.any(se):
            worst_squeeze = float(np.min(returns[se]))

    # Pair-specific
    avg_spread = float(np.mean(spread_returns)) if spread_returns is not None else 0.0
    hedge_stability = float(1.0 - np.std(hedge_ratios)) if hedge_ratios is not None and len(hedge_ratios) > 1 else 0.0
    corr_stability = float(1.0 - np.std(correlations)) if correlations is not None and len(correlations) > 1 else 0.0

    # Long-only comparison
    lo_return = 0.0
    hedged_ret = total_return
    if long_only_curve is not None and len(long_only_curve) > 1:
        lo_eq = np.asarray(long_only_curve, dtype=np.float64)
        lo_return = float((lo_eq[-1] / lo_eq[0]) - 1.0)
    hedge_benefit = total_return - lo_return

    return PerformanceMetrics(
        total_return=total_return,
        cagr=cagr,
        annual_volatility=annual_vol,
        sharpe_ratio=sharpe,
        sortino_ratio=sortino,
        max_drawdown=max_dd,
        max_drawdown_duration_days=max_dd_duration,
        calmar_ratio=calmar,
        var_95=var_95,
        cvar_95=cvar_95,
        skewness=skew,
        kurtosis=kurt,
        hit_rate=hit_rate,
        avg_winner=avg_win,
        avg_loser=avg_los,
        profit_factor=profit_factor,
        worst_day=worst_day,
        worst_week=worst_week,
        worst_squeeze_event=worst_squeeze,
        best_day=best_day,
        best_week=best_week,
        avg_relative_spread_return=avg_spread,
        hedge_ratio_stability=hedge_stability,
        correlation_stability=corr_stability,
        long_only_return=lo_return,
        hedged_return=hedged_ret,
        hedge_benefit=hedge_benefit,
    )
