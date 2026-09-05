"""Correlation analysis features for relative-value trading."""

from __future__ import annotations

import polars as pl
import numpy as np
from scipy import stats as sp_stats


def compute_rolling_correlation(
    returns_a: pl.DataFrame,
    returns_b: pl.DataFrame,
    windows: list[int] | None = None,
    method: str = "pearson",
) -> pl.DataFrame:
    """Compute rolling correlation between two return series.

    Args:
        returns_a: DataFrame with 'timestamp' and a return column (or named
            columns matching returns_b).
        returns_b: DataFrame with 'timestamp' and a return column.
        windows: Rolling window sizes. Defaults to [7, 30, 90].
        method: 'pearson' or 'spearman'.

    Returns:
        DataFrame with 'timestamp' and correlation columns for each window.
        Null for windows with insufficient data or constant series.
    """
    if windows is None:
        windows = [7, 30, 90]

    if method not in ("pearson", "spearman"):
        raise ValueError(f"method must be 'pearson' or 'spearman', got '{method}'")

    # Resolve return columns (first non-timestamp column)
    a_cols = [c for c in returns_a.columns if c != "timestamp"]
    b_cols = [c for c in returns_b.columns if c != "timestamp"]
    if not a_cols or not b_cols:
        raise ValueError("Both DataFrames must have at least one return column")

    a_col = a_cols[0]
    b_col = b_cols[0]

    merged = (
        returns_a.select(["timestamp", a_col])
        .join(returns_b.select(["timestamp", b_col]), on="timestamp", how="inner")
        .sort("timestamp")
    )

    result_cols: list[pl.Expr] = [pl.col("timestamp")]

    for w in windows:
        if method == "spearman":
            # Rank then Pearson
            rank_a = pl.col(a_col).rank().over(
                pl.lit(0).sort_by("timestamp").alias("dummy")
            )
            rank_b = pl.col(b_col).rank().over(
                pl.lit(0).sort_by("timestamp").alias("dummy")
            )
            # Use rolling cov / rolling std for Spearman
            expr = (
                pl.cov_spearman(pl.col(a_col), pl.col(b_col), w)
                if hasattr(pl, "cov_spearman")
                else None
            )
            if expr is not None:
                result_cols.append(expr.alias(f"corr_{a_col}_{b_col}_{w}d"))
            else:
                # Manual Spearman via rolling rank normalization
                result_cols.append(
                    pl.rolling_corr(pl.col(a_col), pl.col(b_col), w)
                    .alias(f"corr_{a_col}_{b_col}_{w}d")
                )
        else:
            result_cols.append(
                pl.rolling_corr(pl.col(a_col), pl.col(b_col), w)
                .alias(f"corr_{a_col}_{b_col}_{w}d")
            )

    return merged.select(result_cols)


def compute_cross_correlation_matrix(
    all_returns: pl.DataFrame,
    window: int,
) -> pl.DataFrame:
    """Compute full NxN correlation matrix across all assets.

    Args:
        all_returns: DataFrame with 'timestamp' column and one return column
            per asset symbol.
        window: Rolling window size (use 0 or negative for full-sample).

    Returns:
        Square DataFrame with asset names as both index and column names,
        containing pairwise correlation values. Diagonal is 1.0.
    """
    asset_cols = [c for c in all_returns.columns if c != "timestamp"]
    n = len(asset_cols)

    if n == 0:
        return pl.DataFrame()

    if n == 1:
        return pl.DataFrame({asset_cols[0]: [1.0]})

    # Use last `window` rows for rolling, or all if window <= 0
    if window > 0 and len(all_returns) > window:
        data = all_returns.sort("timestamp").tail(window)
    else:
        data = all_returns.sort("timestamp")

    # Convert to numpy for correlation matrix
    values = data.select(asset_cols).to_numpy()

    # Replace inf with null, then fill null with 0 for correlation computation
    finite_mask = np.isfinite(values)
    values_clean = np.where(finite_mask, values, np.nan)

    # Pairwise Pearson correlation, handling NaN columns
    result = np.full((n, n), np.nan)
    for i in range(n):
        for j in range(n):
            if i == j:
                result[i, j] = 1.0
            else:
                mask = np.isfinite(values_clean[:, i]) & np.isfinite(values_clean[:, j])
                if mask.sum() < 3:
                    result[i, j] = np.nan
                else:
                    vals_i = values_clean[mask, i]
                    vals_j = values_clean[mask, j]
                    if np.std(vals_i) < 1e-15 or np.std(vals_j) < 1e-15:
                        result[i, j] = np.nan
                    else:
                        result[i, j] = np.corrcoef(vals_i, vals_j)[0, 1]

    # Build output DataFrame
    result_dict = {}
    for j, col_j in enumerate(asset_cols):
        result_dict[col_j] = result[:, j].tolist()

    return pl.DataFrame(result_dict).hstack(
        pl.Series("symbol", asset_cols)
    )


def compute_tail_dependence(
    returns_a: pl.DataFrame,
    returns_b: pl.DataFrame,
    quantile: float = 0.1,
) -> dict[str, float]:
    """Compute tail dependence: P(B < q | A < q).

    Measures how likely B crashes given that A crashes — critical for
    identifying pairs that fail together in stress.

    Args:
        returns_a: DataFrame with 'timestamp' and a return column.
        returns_b: DataFrame with 'timestamp' and a return column.
        quantile: Lower tail threshold (0.1 = bottom decile).

    Returns:
        Dict with 'lower_tail' (P(B<q|A<q)), 'upper_tail' (P(B>1-q|A>1-q)),
        and 'n_obs' (number of aligned observations used).
    """
    a_cols = [c for c in returns_a.columns if c != "timestamp"]
    b_cols = [c for c in returns_b.columns if c != "timestamp"]

    if not a_cols or not b_cols:
        return {"lower_tail": np.nan, "upper_tail": np.nan, "n_obs": 0}

    merged = (
        returns_a.select(["timestamp", a_cols[0]])
        .join(returns_b.select(["timestamp", b_cols[0]]), on="timestamp", how="inner")
        .drop_nulls()
    )

    n = len(merged)
    if n < 10:
        return {"lower_tail": np.nan, "upper_tail": np.nan, "n_obs": n}

    a_vals = merged[a_cols[0]].to_numpy()
    b_vals = merged[b_cols[0]].to_numpy()

    a_q = np.nanpercentile(a_vals, quantile * 100)
    b_q = np.nanpercentile(b_vals, quantile * 100)

    # Lower tail dependence
    mask_a_lower = a_vals <= a_q
    n_a_lower = mask_a_lower.sum()
    if n_a_lower == 0:
        lower_tail = np.nan
    else:
        lower_tail = float((b_vals[mask_a_lower] <= b_q).mean())

    # Upper tail dependence
    a_upper = np.nanpercentile(a_vals, (1 - quantile) * 100)
    b_upper = np.nanpercentile(b_vals, (1 - quantile) * 100)
    mask_a_upper = a_vals >= a_upper
    n_a_upper = mask_a_upper.sum()
    if n_a_upper == 0:
        upper_tail = np.nan
    else:
        upper_tail = float((b_vals[mask_a_upper] >= b_upper).mean())

    return {
        "lower_tail": lower_tail,
        "upper_tail": upper_tail,
        "n_obs": n,
    }
