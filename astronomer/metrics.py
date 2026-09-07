"""Performance metrics for event-level backtest.

Adapted from BEAR/src/bear/backtest/metrics.py (Sharpe, Sortino, drawdown, etc.)
and fleece/fleece/eval/gates.py (Wilson score, bootstrap CI).

No numpy dependency — pure Python for now.
"""

import math
import random
import statistics
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PerformanceMetrics:
    """Full performance report for a set of trade outcomes."""
    n: int = 0
    wins: int = 0
    total_return: float = 0.0
    mean_return: float = 0.0
    median_return: float = 0.0
    std_return: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    calmar_ratio: float = 0.0
    profit_factor: float = 0.0
    hit_rate: float = 0.0
    avg_winner: float = 0.0
    avg_loser: float = 0.0
    best_trade: float = 0.0
    worst_trade: float = 0.0
    var_95: float = 0.0
    cvar_95: float = 0.0
    skewness: float = 0.0
    kurtosis: float = 0.0
    expected_value: float = 0.0
    bayesian_win_rate: float = 0.5
    wilson_ci_lo: Optional[float] = None
    wilson_ci_hi: Optional[float] = None


def compute_metrics(returns: list[float], risk_free_rate: float = 0.0,
                    periods_per_year: int = 365,
                    bayesian_alpha: int = 2, bayesian_beta: int = 2) -> PerformanceMetrics:
    """Compute full performance metrics from a list of returns.

    Args:
        returns: List of net returns as decimals (0.00338 = 0.338%).
        risk_free_rate: Annual risk-free rate.
        periods_per_year: Trading periods per year.
        bayesian_alpha: Prior wins for Bayesian shrinkage.
        bayesian_beta: Prior losses for Bayesian shrinkage.
    """
    if not returns:
        return PerformanceMetrics()

    n = len(returns)
    wins = sum(1 for r in returns if r > 0)
    losers = sum(1 for r in returns if r < 0)

    total_return = sum(returns)
    mean_return = statistics.mean(returns)
    median_return = statistics.median(returns)

    std_return = statistics.stdev(returns) if n > 1 else 0.0

    # Sharpe (annualized)
    excess = mean_return - risk_free_rate / periods_per_year
    sharpe = (excess / max(std_return, 1e-10)) * math.sqrt(periods_per_year) if std_return > 0 else 0.0

    # Sortino
    downside = [r for r in returns if r < 0]
    downside_dev = statistics.stdev(downside) if len(downside) > 1 else 1e-10
    sortino = (mean_return / max(downside_dev, 1e-10)) * math.sqrt(periods_per_year) if downside_dev > 0 else 0.0

    # Drawdown from cumulative returns
    cumulative = []
    running = 1.0
    for r in returns:
        running *= (1 + r)
        cumulative.append(running)
    peak = cumulative[0]
    max_dd = 0.0
    for c in cumulative:
        if c > peak:
            peak = c
        dd = (c - peak) / peak if peak > 0 else 0.0
        if dd < max_dd:
            max_dd = dd

    calmar = total_return / abs(max_dd) if abs(max_dd) > 1e-10 else 0.0

    # Profit factor
    gross_profit = sum(r for r in returns if r > 0)
    gross_loss = abs(sum(r for r in returns if r < 0))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    # Win/loss stats
    hit_rate = wins / n if n > 0 else 0.0
    avg_winner = statistics.mean([r for r in returns if r > 0]) if wins > 0 else 0.0
    avg_loser = statistics.mean([r for r in returns if r < 0]) if losers > 0 else 0.0
    best_trade = max(returns) if returns else 0.0
    worst_trade = min(returns) if returns else 0.0

    # VaR / CVaR
    sorted_returns = sorted(returns)
    var_idx = max(0, int(0.05 * n) - 1)
    var_95 = sorted_returns[var_idx]
    tail = sorted_returns[:var_idx + 1]
    cvar_95 = statistics.mean(tail) if tail else var_95

    # Higher moments
    if n > 2 and std_return > 0:
        m3 = statistics.mean((r - mean_return) ** 3 for r in returns)
        skewness = m3 / (std_return ** 3)
        m4 = statistics.mean((r - mean_return) ** 4 for r in returns)
        kurtosis = m4 / (std_return ** 4) - 3.0
    else:
        skewness = 0.0
        kurtosis = 0.0

    # Expected value (per trade)
    expected_value = mean_return

    # Bayesian win rate with Beta(2,2) prior
    bayesian_wr = (wins + bayesian_alpha) / (n + bayesian_alpha + bayesian_beta)

    # Wilson score interval
    wilson_lo, wilson_hi = wilson(wins, n)

    return PerformanceMetrics(
        n=n,
        wins=wins,
        total_return=total_return,
        mean_return=mean_return,
        median_return=median_return,
        std_return=std_return,
        sharpe_ratio=sharpe,
        sortino_ratio=sortino,
        max_drawdown=max_dd,
        calmar_ratio=calmar,
        profit_factor=profit_factor,
        hit_rate=hit_rate,
        avg_winner=avg_winner,
        avg_loser=avg_loser,
        best_trade=best_trade,
        worst_trade=worst_trade,
        var_95=var_95,
        cvar_95=cvar_95,
        skewness=skewness,
        kurtosis=kurtosis,
        expected_value=expected_value,
        bayesian_win_rate=bayesian_wr,
        wilson_ci_lo=wilson_lo,
        wilson_ci_hi=wilson_hi,
    )


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[Optional[float], Optional[float]]:
    """Wilson score interval for binomial proportion.

    From fleece/fleece/eval/gates.py.
    """
    if n <= 0:
        return (None, None)
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z / denom) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, center - half), min(1.0, center + half))


def bootstrap_ci(deltas: list[float], n_boot: int = 2000, alpha: float = 0.05,
                 seed: int = 7) -> tuple[float, float]:
    """Bootstrap confidence interval for mean delta.

    From fleece/fleece/eval/gates.py.
    """
    rng = random.Random(seed)
    if not deltas:
        return (float("nan"), float("nan"))
    means = sorted(statistics.mean(deltas[rng.randrange(len(deltas))]
                                   for _ in range(len(deltas)))
                   for _ in range(n_boot))
    return (means[int(alpha / 2 * n_boot)],
            means[min(int((1 - alpha / 2) * n_boot), n_boot - 1)])


def non_inferior_paired(baseline: list[float], candidate: list[float],
                        margin: float = 0.005, seed: int = 7) -> dict:
    """Test if candidate is non-inferior to baseline.

    From fleece/fleece/eval/gates.py.
    """
    deltas = [c - b for b, c in zip(baseline, candidate)]
    lo, hi = bootstrap_ci(deltas, seed=seed)
    mean_delta = statistics.mean(deltas) if deltas else 0.0
    return {
        "mean_delta": mean_delta,
        "ci95": [lo, hi],
        "lcb": lo,
        "margin": margin,
        "non_inferior": lo >= -margin - 1e-12,
        "n_pairs": len(deltas),
    }


@dataclass
class SourceReportCard:
    """Standardized report card for one source."""
    source_handle: str
    source_id: str = ""

    # Activity
    total_posts: int = 0
    market_events: int = 0
    events_per_day: float = 0.0

    # Event mix
    calls: int = 0
    views: int = 0
    observations: int = 0
    interpretations: int = 0
    retrospectives: int = 0

    # Trade calls
    trade_call_n: int = 0
    trade_call_metrics: Optional[PerformanceMetrics] = None

    # Views (event study)
    view_n: int = 0
    view_signed_return_4h: float = 0.0
    view_signed_return_24h: float = 0.0
    view_abnormal_return_4h: float = 0.0

    # Regime behavior
    regime_up_n: int = 0
    regime_down_n: int = 0
    regime_range_n: int = 0
    transition_lead_lag_hours: Optional[float] = None

    # Primitive coverage
    primitives: list[str] = field(default_factory=list)

    # Highest value
    highest_value_primitive: str = ""
    highest_value_horizon: str = ""
    highest_value_direction: str = ""
    highest_value_asset: str = ""

    # Data quality
    extraction_precision: Optional[float] = None
    unresolved_asset_fraction: float = 0.0
    evidence_coverage: float = 0.0


def format_metrics_table(metrics: PerformanceMetrics, label: str = "") -> str:
    """Format metrics as a readable table."""
    lines = []
    if label:
        lines.append(f"=== {label} ===")
    lines.append(f"  N:              {metrics.n}")
    lines.append(f"  Wins:           {metrics.wins}")
    lines.append(f"  Hit rate:       {metrics.hit_rate:.1%} (Bayesian: {metrics.bayesian_win_rate:.1%})")
    lines.append(f"  Wilson CI:      [{metrics.wilson_ci_lo:.1%}, {metrics.wilson_ci_hi:.1%}]" if metrics.wilson_ci_lo is not None else "")
    lines.append(f"  Mean return:    {metrics.mean_return * 100:.3f}%")
    lines.append(f"  Median return:  {metrics.median_return * 100:.3f}%")
    lines.append(f"  Sharpe:         {metrics.sharpe_ratio:.2f}")
    lines.append(f"  Sortino:        {metrics.sortino_ratio:.2f}")
    lines.append(f"  Max drawdown:   {metrics.max_drawdown * 100:.2f}%")
    lines.append(f"  Profit factor:  {metrics.profit_factor:.2f}")
    lines.append(f"  EV per trade:   {metrics.expected_value * 100:.3f}%")
    lines.append(f"  Best trade:     {metrics.best_trade * 100:.2f}%")
    lines.append(f"  Worst trade:    {metrics.worst_trade * 100:.2f}%")
    lines.append(f"  VaR 95%:        {metrics.var_95 * 100:.3f}%")
    lines.append(f"  CVaR 95%:       {metrics.cvar_95 * 100:.3f}%")
    return "\n".join(lines)
