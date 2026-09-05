"""Factor combination search and weighting.

Provides greedy forward selection, Lasso-based feature selection, and
IC-weighted combination methods for building composite alpha signals.

Functions:
    greedy_forward_search: Iteratively add factors by marginal ICIR gain.
    lasso_select: LassoCV with TimeSeriesSplit for sparse factor selection.
    equal_weight_combo: Simple equal-weight combination of selected factors.
    ic_weight_combo: IC-weighted combination of factors.
    search_best_combo: Orchestrate search → filter → combine → return best.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import polars as pl
import structlog

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ComboResult:
    """Result of a factor combination search.

    Attributes:
        name: Combo identifier (method + count).
        factors: Selected factor column names.
        weights: Mapping of factor -> weight.
        method: Combination method used.
        icir: Composite ICIR of the combined signal.
        metadata: Extra info (alphas, n_samples, etc.).
    """

    name: str
    factors: list[str]
    weights: dict[str, float]
    method: str
    icir: float = 0.0
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _rank_ic(fv: np.ndarray, ret: np.ndarray) -> float:
    """Spearman rank IC via Pearson of ranks (fast vectorised)."""
    n = len(fv)
    if n < 10:
        return 0.0
    # argsort-based ranking
    rank_f = fv.argsort().argsort().astype(np.float64)
    rank_r = ret.argsort().argsort().astype(np.float64)
    rank_f -= rank_f.mean()
    rank_r -= rank_r.mean()
    denom = np.sqrt((rank_f**2).sum() * (rank_r**2).sum())
    if denom < 1e-15:
        return 0.0
    return float((rank_f * rank_r).sum() / denom)


def _compute_factor_icir(
    factor_matrix: pl.DataFrame,
    returns: pl.Series,
    factor_cols: list[str],
    window: int = 252,
) -> dict[str, float]:
    """Compute rolling ICIR for every factor column.

    Args:
        factor_matrix: DataFrame with factor columns only (same row index).
        returns: Forward return series aligned with factor_matrix.
        factor_cols: Column names to evaluate.
        window: Rolling window for IC series.

    Returns:
        Mapping of factor name -> ICIR.
    """
    ret_np = returns.to_numpy().astype(np.float64)
    icir_map: dict[str, float] = {}

    for col in factor_cols:
        fv = factor_matrix.get_column(col).to_numpy().astype(np.float64)
        valid = np.isfinite(fv) & np.isfinite(ret_np)
        fv_v, ret_v = fv[valid], ret_np[valid]
        n = len(fv_v)
        if n < window + 10:
            icir_map[col] = 0.0
            continue
        # subsample for speed
        step = max(1, (n - window) // 2000)
        ics: list[float] = []
        for i in range(window, n, step):
            ics.append(_rank_ic(fv_v[i - window : i], ret_v[i - window : i]))
        if len(ics) < 5:
            icir_map[col] = 0.0
            continue
        arr = np.array(ics)
        std = arr.std()
        icir_map[col] = float(arr.mean() / std) if std > 0 else 0.0

    return icir_map


def _combo_icir(
    factor_matrix: pl.DataFrame,
    returns: pl.Series,
    factors: list[str],
    weights: dict[str, float],
    window: int = 252,
) -> float:
    """Estimate ICIR of a weighted factor combination."""
    if not factors:
        return 0.0
    ret_np = returns.to_numpy().astype(np.float64)
    combo = np.zeros(len(ret_np), dtype=np.float64)
    w_sum = 0.0
    for col in factors:
        w = weights.get(col, 0.0)
        fv = factor_matrix.get_column(col).to_numpy().astype(np.float64)
        valid = np.isfinite(fv)
        fv_clean = np.where(valid, fv, 0.0)
        combo += fv_clean * w
        if valid.all():
            w_sum += abs(w)
    if w_sum < 1e-15:
        return 0.0
    combo /= w_sum
    valid = np.isfinite(combo) & np.isfinite(ret_np)
    fv_v, ret_v = combo[valid], ret_np[valid]
    n = len(fv_v)
    if n < window + 10:
        return 0.0
    step = max(1, (n - window) // 2000)
    ics = [_rank_ic(fv_v[i - window : i], ret_v[i - window : i]) for i in range(window, n, step)]
    if len(ics) < 5:
        return 0.0
    arr = np.array(ics)
    std = arr.std()
    return float(arr.mean() / std) if std > 0 else 0.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def greedy_forward_search(
    factor_matrix: pl.DataFrame,
    returns: pl.Series,
    max_factors: int = 10,
    ic_threshold: float = 0.02,
    window: int = 252,
) -> ComboResult:
    """Greedy forward selection by marginal ICIR improvement.

    Iteratively adds the factor that gives the largest ICIR gain to the
    composite signal, stopping when no factor improves ICIR above
    ``ic_threshold`` or ``max_factors`` is reached.

    Args:
        factor_matrix: DataFrame with factor columns (no 'timestamp').
        returns: Forward return series aligned with factor_matrix rows.
        max_factors: Maximum number of factors to include.
        ic_threshold: Minimum ICIR improvement required to add a factor.
        window: Rolling window for IC computation.

    Returns:
        ComboResult with selected factors and their normalised weights.
    """
    factor_cols = [c for c in factor_matrix.columns]
    if not factor_cols or len(factor_matrix) < window + 10:
        logger.warning("greedy_forward_search: insufficient data or no factors")
        return ComboResult(name="greedy_0f", factors=[], weights={}, method="greedy")

    icir_map = _compute_factor_icir(factor_matrix, returns, factor_cols, window)
    # rank by absolute ICIR descending
    ranked = sorted(
        [(c, icir_map.get(c, 0.0)) for c in factor_cols],
        key=lambda x: -abs(x[1]),
    )

    selected: list[str] = []
    best_icir = 0.0

    for col, _ in ranked:
        if len(selected) >= max_factors:
            break
        candidate = selected + [col]
        w = {c: 1.0 for c in candidate}
        combo_icir = _combo_icir(factor_matrix, returns, candidate, w, window)
        gain = combo_icir - best_icir
        if gain >= ic_threshold:
            selected.append(col)
            best_icir = combo_icir
            logger.debug(
                "greedy_forward_search: added %s, gain=%.4f, icir=%.4f",
                col, gain, best_icir,
            )
        else:
            logger.debug(
                "greedy_forward_search: skipped %s, gain=%.4f < threshold",
                col, gain,
            )

    # normalise weights to sum=1
    n = len(selected)
    weights = {c: round(1.0 / n, 6) for c in selected} if n > 0 else {}
    name = f"greedy_{n}f"
    return ComboResult(
        name=name,
        factors=selected,
        weights=weights,
        method="greedy",
        icir=best_icir,
        metadata={"ic_threshold": ic_threshold, "max_factors": max_factors},
    )


def lasso_select(
    factor_matrix: pl.DataFrame,
    returns: pl.Series,
    alphas: list[float] | None = None,
    n_splits: int = 5,
) -> ComboResult:
    """Select factors via LassoCV with TimeSeriesSplit.

    Fits LassoCV on standardised factor values, returning factors with
    non-zero coefficients.

    Args:
        factor_matrix: DataFrame with factor columns.
        returns: Forward return series.
        alphas: Candidate regularisation strengths. None uses sklearn default.
        n_splits: Number of TimeSeriesSplit folds.

    Returns:
        ComboResult with Lasso-selected factors and normalised weights.
    """
    from sklearn.linear_model import LassoCV
    from sklearn.model_selection import TimeSeriesSplit
    from sklearn.preprocessing import StandardScaler

    factor_cols = factor_matrix.columns
    if not factor_cols or len(factor_matrix) < 100:
        logger.warning("lasso_select: insufficient data")
        return ComboResult(name="lasso_0f", factors=[], weights={}, method="lasso")

    # build arrays, drop rows with any NaN
    mask = factor_matrix.select(
        pl.all_horizontal(pl.all().is_not_null())
    ).to_series().to_numpy()
    valid_ret = returns.to_numpy().astype(np.float64)
    mask &= np.isfinite(valid_ret)
    X = factor_matrix.filter(pl.Series(mask)).select(factor_cols).to_numpy().astype(np.float64)
    y = valid_ret[mask]

    if len(X) < 100:
        logger.warning("lasso_select: only %d valid samples", len(X))
        return ComboResult(name="lasso_0f", factors=[], weights={}, method="lasso")

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    tscv = TimeSeriesSplit(n_splits=n_splits)
    kwargs = {"cv": tscv, "max_iter": 10_000, "random_state": 42}
    if alphas is not None:
        kwargs["alphas"] = alphas

    model = LassoCV(**kwargs)
    model.fit(X_scaled, y)

    coefs = model.coef_
    selected: list[str] = []
    raw_w: dict[str, float] = {}
    for col, coef in zip(factor_cols, coefs):
        if abs(coef) > 1e-8:
            selected.append(col)
            raw_w[col] = abs(float(coef))

    # normalise
    w_sum = sum(raw_w.values())
    weights = {k: round(v / w_sum, 6) for k, v in raw_w.items()} if w_sum > 0 else {}

    icir = _combo_icir(factor_matrix, returns, selected, weights) if selected else 0.0
    name = f"lasso_{len(selected)}f"
    return ComboResult(
        name=name,
        factors=selected,
        weights=weights,
        method="lasso",
        icir=icir,
        metadata={"alpha": float(model.alpha_), "n_samples": len(X)},
    )


def equal_weight_combo(selected_factors: list[str]) -> ComboResult:
    """Simple equal-weight combination of pre-selected factors.

    Args:
        selected_factors: Factor column names to include.

    Returns:
        ComboResult with equal 1/n weights.
    """
    n = len(selected_factors)
    weights = {f: round(1.0 / n, 6) for f in selected_factors} if n > 0 else {}
    return ComboResult(
        name=f"ew_{n}f",
        factors=list(selected_factors),
        weights=weights,
        method="equal_weight",
    )


def ic_weight_combo(
    factor_matrix: pl.DataFrame,
    ic_values: dict[str, float],
) -> ComboResult:
    """Weight factors proportional to their absolute IC values.

    Factors with IC < 0 are included but their weights use |IC|.
    The sign is tracked so the consumer can flip if needed.

    Args:
        factor_matrix: DataFrame with factor columns.
        ic_values: Mapping of factor name -> mean IC.

    Returns:
        ComboResult with IC-weighted normalised weights.
    """
    abs_ics = {k: abs(v) for k, v in ic_values.items() if k in factor_matrix.columns}
    total = sum(abs_ics.values())
    weights = {k: round(v / total, 6) for k, v in abs_ics.items()} if total > 0 else {}
    selected = [k for k in weights if weights[k] > 0]
    return ComboResult(
        name=f"icw_{len(selected)}f",
        factors=selected,
        weights=weights,
        method="ic_weight",
        metadata={"raw_ics": {k: round(ic_values[k], 6) for k in selected}},
    )


def search_best_combo(
    factor_matrix: pl.DataFrame,
    returns: pl.Series,
    method: str = "greedy",
    ic_threshold: float = 0.02,
    max_factors: int = 10,
    window: int = 252,
) -> ComboResult:
    """Orchestrate: evaluate factors → filter → combine → return best.

    Pipeline:
        1. Compute per-factor ICIR.
        2. Filter out factors with |ICIR| < ``ic_threshold``.
        3. Apply the chosen combination method.
        4. Return the best ComboResult.

    Args:
        factor_matrix: DataFrame with factor columns.
        returns: Forward return series.
        method: One of ``'greedy'``, ``'lasso'``, ``'equal_weight'``, ``'ic_weight'``.
        ic_threshold: Minimum |ICIR| for a factor to be considered.
        max_factors: Cap for greedy/lasso methods.
        window: Rolling IC window.

    Returns:
        Best ComboResult found.
    """
    factor_cols = factor_matrix.columns
    if not factor_cols:
        logger.warning("search_best_combo: no factor columns")
        return ComboResult(name="none_0f", factors=[], weights={}, method="none")

    # Step 1: compute ICIR per factor
    icir_map = _compute_factor_icir(factor_matrix, returns, factor_cols, window)

    # Step 2: filter by threshold
    passed = {k: v for k, v in icir_map.items() if abs(v) >= ic_threshold}
    logger.info(
        "search_best_combo: %d/%d factors pass ICIR threshold %.3f",
        len(passed), len(factor_cols), ic_threshold,
    )
    if not passed:
        return ComboResult(name="none_0f", factors=[], weights={}, method="none")

    # build filtered matrix
    filtered_cols = list(passed.keys())
    filtered_matrix = factor_matrix.select(filtered_cols)

    # Step 3: apply method
    if method == "greedy":
        return greedy_forward_search(
            filtered_matrix, returns,
            max_factors=max_factors, ic_threshold=0.0, window=window,
        )
    elif method == "lasso":
        return lasso_select(filtered_matrix, returns)
    elif method == "equal_weight":
        return equal_weight_combo(filtered_cols)
    elif method == "ic_weight":
        ic_subset = {k: icir_map[k] for k in filtered_cols}
        return ic_weight_combo(filtered_matrix, ic_subset)
    else:
        logger.warning("search_best_combo: unknown method '%s', falling back to greedy", method)
        return greedy_forward_search(
            filtered_matrix, returns,
            max_factors=max_factors, ic_threshold=0.0, window=window,
        )
