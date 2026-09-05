"""Factor model features for relative-value trading.

Builds systematic risk factors (BTC, ETH, HYPE, ALT basket) and estimates
per-asset factor exposures using ridge regression.
"""

from __future__ import annotations

import polars as pl
import numpy as np
from numpy.linalg import lstsq


# Known stablecoins to exclude from the ALT basket
_STABLECOINS = frozenset({
    "USDC", "USDT", "DAI", "USDe", "USDS", "PYUSD",
    "FRAX", "LUSD", "sUSD", "crvUSD", "GHO", "mkUSD",
    "USDH", "USDP", "TUSD", "BUSD", "FDUSD",
})

# Default weight for ridge regression penalty
_RIDGE_ALPHA = 1e-2


def build_btc_eth_alt_factors(
    all_returns: pl.DataFrame,
    weights: dict[str, float] | None = None,
) -> pl.DataFrame:
    """Build BTC, ETH, HYPE, and ALT factor return series.

    Factors:
        - BTC: Bitcoin return
        - ETH: Ethereum return
        - HYPE: Hyperliquid native token return
        - ALT: Liquidity-weighted basket of remaining assets (ex BTC, ETH, stables)

    Args:
        all_returns: DataFrame with 'timestamp' and one return column per asset.
            Column names should be uppercase symbols (e.g., 'BTC', 'ETH').
        weights: Optional mapping of symbol -> weight for ALT basket construction.
            If None, uses equal weighting (1/n) over available assets.

    Returns:
        DataFrame with 'timestamp' and columns ['BTC', 'ETH', 'HYPE', 'ALT'].
        Missing factors produce null returns.
    """
    asset_cols = [c for c in all_returns.columns if c != "timestamp"]

    # Define factor columns
    btc_col = "BTC" if "BTC" in asset_cols else None
    eth_col = "ETH" if "ETH" in asset_cols else None
    hype_col = "HYPE" if "HYPE" in asset_cols else None

    # ALT basket: everything except BTC, ETH, HYPE, and stablecoins
    alt_cols = [
        c for c in asset_cols
        if c not in {"BTC", "ETH", "HYPE"} and c not in _STABLECOINS
    ]

    result_exprs: list[pl.Expr] = [pl.col("timestamp")]

    # BTC factor
    if btc_col:
        result_exprs.append(pl.col(btc_col).alias("BTC"))
    else:
        result_exprs.append(pl.lit(None).cast(pl.Float64).alias("BTC"))

    # ETH factor
    if eth_col:
        result_exprs.append(pl.col(eth_col).alias("ETH"))
    else:
        result_exprs.append(pl.lit(None).cast(pl.Float64).alias("ETH"))

    # HYPE factor
    if hype_col:
        result_exprs.append(pl.col(hype_col).alias("HYPE"))
    else:
        result_exprs.append(pl.lit(None).cast(pl.Float64).alias("HYPE"))

    # ALT basket: weighted mean of remaining assets
    if alt_cols:
        if weights is not None:
            # Use provided weights, normalizing to sum to 1
            alt_w = np.array([weights.get(c, 0.0) for c in alt_cols])
            w_sum = alt_w.sum()
            if w_sum > 1e-15:
                alt_w = alt_w / w_sum
            else:
                alt_w = np.ones(len(alt_cols)) / len(alt_cols)
        else:
            alt_w = np.ones(len(alt_cols)) / len(alt_cols)

        # Weighted sum of return columns
        alt_expr = pl.lit(0.0)
        for col, w in zip(alt_cols, alt_w):
            alt_expr = alt_expr + pl.col(col).fill_null(0.0) * w

        # Only count assets with actual data — re-normalize per row
        valid_count = pl.lit(0)
        for col in alt_cols:
            valid_count = valid_count + pl.col(col).is_not_null().cast(pl.Float64)

        # If no ALT assets have data, return null
        result_exprs.append(
            pl.when(valid_count > 0)
            .then(alt_expr / valid_count * len(alt_cols))
            .otherwise(pl.lit(None).cast(pl.Float64))
            .alias("ALT")
        )
    else:
        result_exprs.append(pl.lit(None).cast(pl.Float64).alias("ALT"))

    return all_returns.select(result_exprs)


def estimate_factor_exposures(
    returns_i: pl.DataFrame,
    factor_returns: pl.DataFrame,
    ridge_alpha: float = _RIDGE_ALPHA,
) -> dict[str, float]:
    """Estimate factor exposures (betas) for an asset via ridge regression.

    Solves: r_i = alpha + beta_btc * BTC + beta_eth * ETH + beta_hype * HYPE
            + beta_alt * ALT + epsilon

    Uses ridge regression (L2 penalty) for numerical stability when factors
    are correlated.

    Args:
        returns_i: Return series for asset i, with 'timestamp' and one return column.
        factor_returns: Factor return series with 'timestamp' and factor columns.
        ridge_alpha: Ridge penalty strength. Higher = more shrinkage toward zero.

    Returns:
        Dict mapping factor name to exposure coefficient. Includes 'intercept'.
        Returns all-zero exposures if insufficient data.
    """
    factor_cols = [c for c in factor_returns.columns if c != "timestamp"]
    asset_cols = [c for c in returns_i.columns if c != "timestamp"]
    asset_col = asset_cols[0] if asset_cols else None

    if not asset_col or not factor_cols:
        return {f: 0.0 for f in factor_cols} | {"intercept": 0.0}

    merged = (
        returns_i.select(["timestamp", asset_col])
        .join(factor_returns.select(["timestamp"] + factor_cols), on="timestamp", how="inner")
        .drop_nulls()
    )

    if len(merged) < 10:
        return {f: 0.0 for f in factor_cols} | {"intercept": 0.0}

    y = merged[asset_col].to_numpy().astype(np.float64)
    X = merged.select(factor_cols).to_numpy().astype(np.float64)

    # Standardize factors
    X_std = np.std(X, axis=0)
    X_std[X_std < 1e-15] = 1.0
    X_norm = X / X_std

    # Add intercept column
    X_design = np.column_stack([np.ones(len(X_norm)), X_norm])

    # Ridge regression: (X^T X + alpha I)^{-1} X^T y
    I = np.eye(X_design.shape[1])
    I[0, 0] = 0.0  # Don't penalize intercept
    coefs = lstsq(X_design.T @ X_design + ridge_alpha * I, X_design.T @ y, rcond=None)[0]

    # Un-normalize factor betas
    betas = coefs[1:] / X_std
    intercept = coefs[0]

    result = {"intercept": float(intercept)}
    for name, beta in zip(factor_cols, betas):
        result[name] = float(beta)

    return result


def compute_factor_distance(
    exposure_i: dict[str, float],
    exposure_l: dict[str, float],
) -> float:
    """Euclidean distance between two factor exposure vectors.

    Lower distance means assets have similar risk profiles, which is
    desirable for a relative-value pair (same systematic risk, idiosyncratic
    alpha separation).

    Args:
        exposure_i: Factor exposures for asset i (from estimate_factor_exposures).
        exposure_l: Factor exposures for asset l.

    Returns:
        Euclidean distance. Returns 0.0 if both are empty/identical.
    """
    # Align on common factor keys (exclude intercept)
    all_keys = sorted(set(
        k for k in list(exposure_i.keys()) + list(exposure_l.keys())
        if k != "intercept"
    ))

    if not all_keys:
        return 0.0

    vec_i = np.array([exposure_i.get(k, 0.0) for k in all_keys])
    vec_l = np.array([exposure_l.get(k, 0.0) for k in all_keys])

    return float(np.sqrt(np.sum((vec_i - vec_l) ** 2)))


def compute_sector_baskets(
    returns: pl.DataFrame,
    taxonomy: dict[str, str],
) -> pl.DataFrame:
    """Compute sector-level return baskets.

    Aggregates individual asset returns into sector returns using the
    provided taxonomy mapping.

    Args:
        returns: DataFrame with 'timestamp' and one return column per asset.
        taxonomy: Mapping of asset symbol -> sector name.
            e.g., {"BTC": "L1", "ETH": "L1", "UNI": "DeFi", "AAVE": "DeFi"}

    Returns:
        DataFrame with 'timestamp' and one column per sector, containing
        the equal-weighted mean return of assets in that sector.
    """
    asset_cols = [c for c in returns.columns if c != "timestamp"]

    # Group assets by sector
    sectors: dict[str, list[str]] = {}
    for asset in asset_cols:
        sector = taxonomy.get(asset, "other")
        sectors.setdefault(sector, []).append(asset)

    result_exprs: list[pl.Expr] = [pl.col("timestamp")]

    for sector, assets in sorted(sectors.items()):
        valid_assets = [a for a in assets if a in asset_cols]
        if not valid_assets:
            result_exprs.append(pl.lit(None).cast(pl.Float64).alias(sector))
            continue

        # Equal-weighted mean, ignoring nulls
        count_expr = pl.lit(0)
        sum_expr = pl.lit(0.0)
        for asset in valid_assets:
            count_expr = count_expr + pl.col(asset).is_not_null().cast(pl.Float64)
            sum_expr = sum_expr + pl.col(asset).fill_null(0.0)

        result_exprs.append(
            pl.when(count_expr > 0)
            .then(sum_expr / count_expr)
            .otherwise(pl.lit(None).cast(pl.Float64))
            .alias(sector)
        )

    return returns.select(result_exprs)
