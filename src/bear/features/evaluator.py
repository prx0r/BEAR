"""Factor evaluation metrics for alpha signal quality.

Computes Spearman rank IC, rolling IC series, ICIR, Newey-West t-statistics,
Benjamini-Hochberg FDR correction, and factor ranking. All data in Polars;
stats via numpy/scipy.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import polars as pl
from scipy import stats as sp_stats

try:
    import structlog

    _log = structlog.get_logger("bear.evaluator")
except ImportError:
    import logging

    _log = logging.getLogger("bear.evaluator")


@dataclass
class FactorEvaluation:
    """Single-factor evaluation result."""

    name: str
    rank_ic: float
    icir: float
    t_stat: float
    p_value: float
    fdr_p_value: float | None = None
    coverage: float = 0.0
    n_periods: int = 0


@dataclass
class EvaluatorConfig:
    """Configuration for factor evaluation."""

    ic_window: int = 252
    newey_west_lags: int | None = None
    min_periods: int = 30
    horizons: list[int] = field(default_factory=lambda: [1, 5, 10, 20])


def compute_rank_ic(
    factor_values: pl.Series,
    forward_returns: pl.Series,
) -> float:
    """Spearman rank correlation between factor values and forward returns.

    Args:
        factor_values: Factor signal values.
        forward_returns: Forward-looking return series aligned to factor.

    Returns:
        Rank IC value. Returns 0.0 if insufficient valid data.
    """
    valid_idx = factor_values.is_not_null() & forward_returns.is_not_null()
    fv = factor_values.filter(valid_idx).to_numpy().astype(float)
    fr = forward_returns.filter(valid_idx).to_numpy().astype(float)

    if len(fv) < 2:
        _log.debug("rank_ic_skipped", n_valid=len(fv))
        return 0.0

    ic, _ = sp_stats.spearmanr(fv, fr)
    return float(ic) if np.isfinite(ic) else 0.0


def compute_ic_series(
    factor_values: pl.Series,
    forward_returns: pl.Series,
    window: int = 252,
) -> pl.Series:
    """Rolling Spearman rank IC over time.

    Computes rank IC within a sliding window, returning one IC value per period.

    Args:
        factor_values: Factor signal values.
        forward_returns: Forward-looking returns.
        window: Rolling window size in periods.

    Returns:
        Polars Series of rolling IC values.
    """
    fv = factor_values.to_numpy().astype(float)
    fr = forward_returns.to_numpy().astype(float)

    n = len(fv)
    if n < window:
        _log.debug("ic_series_short", n=n, window=window)
        return pl.Series("ic_series", [], dtype=pl.Float64)

    ic_values = np.full(n, np.nan)
    for i in range(window, n):
        chunk_f = fv[i - window : i]
        chunk_r = fr[i - window : i]
        mask = np.isfinite(chunk_f) & np.isfinite(chunk_r)
        if mask.sum() >= 2:
            ic, _ = sp_stats.spearmanr(chunk_f[mask], chunk_r[mask])
            ic_values[i] = ic

    return pl.Series("ic_series", ic_values).drop_nulls()


def compute_ic_ir(ic_series: pl.Series) -> float:
    """IC information ratio: mean(IC) / std(IC).

    Args:
        ic_series: Series of IC values (e.g., from compute_ic_series).

    Returns:
        ICIR value. Returns 0.0 if std is zero or series is empty.
    """
    vals = ic_series.to_numpy().astype(float)
    vals = vals[np.isfinite(vals)]
    if len(vals) < 2:
        return 0.0
    std = float(np.std(vals, ddof=1))
    if std < 1e-12:
        return 0.0
    return float(np.mean(vals)) / std


def compute_newey_west_tstat(
    ic_series: pl.Series,
    lags: int | None = None,
) -> tuple[float, float]:
    """Newey-West HAC t-statistic for IC mean.

    Adjusts the standard error for autocorrelation and heteroscedasticity
    in the IC series when testing H0: mean(IC) = 0.

    Args:
        ic_series: Series of IC values.
        lags: Number of lags. None uses floor(T^(1/3)).

    Returns:
        (t_stat, p_value) tuple. Returns (0.0, 1.0) on failure.
    """
    vals = ic_series.to_numpy().astype(float)
    vals = vals[np.isfinite(vals)]
    n = len(vals)

    if n < 10:
        _log.debug("nw_tstat_skipped", n=n)
        return 0.0, 1.0

    if lags is None:
        lags = max(1, int(n ** (1 / 3)))

    mean_ic = float(np.mean(vals))
    demeaned = vals - mean_ic

    gamma_0 = float(np.mean(demeaned**2))
    nw_var = gamma_0

    for lag in range(1, lags + 1):
        w = 1 - lag / (lags + 1)  # Bartlett kernel weight
        gamma_lag = float(np.mean(demeaned[lag:] * demeaned[:-lag]))
        nw_var += 2 * w * gamma_lag

    se = np.sqrt(max(nw_var / n, 1e-20))
    t_stat = mean_ic / se

    # Two-tailed p-value from t-distribution
    p_value = 2 * sp_stats.t.sf(abs(t_stat), df=n - 1)

    return float(t_stat), float(p_value)


def apply_fdr_correction(p_values: list[float]) -> list[float | None]:
    """Benjamini-Hochberg FDR correction for multiple testing.

    Args:
        p_values: Raw p-values (may contain None).

    Returns:
        Adjusted p-values. None entries remain None.
    """
    valid = [(i, p) for i, p in enumerate(p_values) if p is not None]
    if not valid:
        return [None] * len(p_values)

    indices, raw_pvals = zip(*valid)
    raw = np.array(raw_pvals)
    m = len(raw)

    # BH step-up procedure
    order = np.argsort(raw)
    adjusted = np.empty(m)
    adjusted[-1] = raw[order[-1]]

    for i in range(m - 2, -1, -1):
        rank = i + 1
        adjusted[i] = min(
            raw[order[i]] * m / rank,
            adjusted[i + 1],
        )

    adjusted = np.clip(adjusted, 0, 1)

    result: list[float | None] = [None] * len(p_values)
    for rank_pos, orig_idx in enumerate(order):
        result[indices[orig_idx]] = float(adjusted[rank_pos])

    return result


def evaluate_factor(
    factor_df: pl.DataFrame,
    returns_df: pl.DataFrame,
    config: EvaluatorConfig | None = None,
    factor_col: str = "factor",
    return_col: str = "forward_return",
) -> FactorEvaluation:
    """Full evaluation of a single factor against forward returns.

    Computes rank IC (full-sample), IC series, ICIR, Newey-West t-stat,
    and coverage ratio.

    Args:
        factor_df: DataFrame with a column of factor values.
        returns_df: DataFrame with a column of forward returns.
        config: Evaluation configuration.
        factor_col: Column name for factor values in factor_df.
        return_col: Column name for forward returns in returns_df.

    Returns:
        FactorEvaluation with all computed metrics.
    """
    config = config or EvaluatorConfig()

    # Ensure alignment — both must have same length or be index-aligned
    fv = factor_df[factor_col]
    fr = returns_df[return_col]

    # Full-sample rank IC
    rank_ic = compute_rank_ic(fv, fr)

    # Rolling IC series
    ic_series = compute_ic_series(fv, fr, window=config.ic_window)

    # ICIR
    icir = compute_ic_ir(ic_series)

    # Newey-West t-stat
    nw_lags = config.newey_west_lags
    t_stat, p_value = compute_newey_west_tstat(ic_series, lags=nw_lags)

    # Coverage
    valid_mask = fv.is_not_null() & fr.is_not_null()
    total = len(fv)
    n_valid = int(valid_mask.sum())
    coverage = n_valid / total if total > 0 else 0.0

    _log.info(
        "factor_evaluated",
        rank_ic=round(rank_ic, 4),
        icir=round(icir, 4),
        t_stat=round(t_stat, 4),
        p_value=round(p_value, 6),
        coverage=round(coverage, 4),
        n_periods=n_valid,
    )

    return FactorEvaluation(
        name=factor_col,
        rank_ic=rank_ic,
        icir=icir,
        t_stat=t_stat,
        p_value=p_value,
        coverage=coverage,
        n_periods=n_valid,
    )


def rank_factors(
    evaluations: list[FactorEvaluation],
    fdr_alpha: float = 0.05,
) -> list[FactorEvaluation]:
    """Rank factors by ICIR with BH FDR filtering.

    Factors with FDR-adjusted p-value > alpha receive None for fdr_p_value
    and are not considered significant.

    Args:
        evaluations: List of FactorEvaluation results.
        fdr_alpha: Significance threshold after FDR correction.

    Returns:
        Sorted list of FactorEvaluation (descending ICIR).
        fdr_p_value populated; non-significant factors kept but flagged.
    """
    if not evaluations:
        return []

    raw_pvals = [e.p_value for e in evaluations]
    adjusted = apply_fdr_correction(raw_pvals)

    result = []
    for eval_, adj_p in zip(evaluations, adjusted):
        ev = FactorEvaluation(
            name=eval_.name,
            rank_ic=eval_.rank_ic,
            icir=eval_.icir,
            t_stat=eval_.t_stat,
            p_value=eval_.p_value,
            fdr_p_value=adj_p,
            coverage=eval_.coverage,
            n_periods=eval_.n_periods,
        )
        result.append(ev)

    result.sort(key=lambda e: e.icir, reverse=True)

    n_sig = sum(1 for e in result if e.fdr_p_value is not None and e.fdr_p_value <= fdr_alpha)
    _log.info(
        "factors_ranked",
        total=len(result),
        significant=n_sig,
        fdr_alpha=fdr_alpha,
    )

    return result
