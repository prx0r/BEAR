"""Funding rate features for perpetual futures relative-value trading."""

from __future__ import annotations

import polars as pl
import numpy as np


def compute_funding_features(
    funding_df: pl.DataFrame,
) -> pl.DataFrame:
    """Compute funding rate features for an asset.

    Args:
        funding_df: DataFrame with columns:
            - 'timestamp': datetime
            - 'funding_rate': instantaneous funding rate (per 8h period)
            - 'symbol': asset symbol (optional, for multi-asset DataFrames)

    Returns:
        DataFrame with 'timestamp' and feature columns:
            - funding_z_30d: z-score of current rate vs 30-day rolling window
            - funding_z_90d: z-score of current rate vs 90-day rolling window
            - funding_annualized: annualized funding rate (x3 * 365)
            - funding_carry: expected carry for shorts (positive = receive)
    """
    required = {"timestamp", "funding_rate"}
    missing = required - set(funding_df.columns)
    if missing:
        raise ValueError(f"funding_df missing required columns: {missing}")

    # Handle multi-asset vs single-asset
    has_symbol = "symbol" in funding_df.columns
    if has_symbol:
        symbols = funding_df["symbol"].unique().to_list()
        results = []
        for sym in symbols:
            sub = funding_df.filter(pl.col("symbol") == sym).sort("timestamp")
            results.append(_compute_funding_single(sub))
        return pl.concat(results)
    else:
        sorted_df = funding_df.sort("timestamp")
        return _compute_funding_single(sorted_df)


def _compute_funding_single(funding_df: pl.DataFrame) -> pl.DataFrame:
    """Compute funding features for a single asset (already sorted by timestamp)."""
    # Rolling windows in periods (assuming 8h funding intervals)
    # 30 days ≈ 90 periods, 90 days ≈ 270 periods
    window_30d = 90
    window_90d = 270

    result = funding_df.select([
        pl.col("timestamp"),
        pl.col("funding_rate"),

        # Z-score 30d
        (
            (pl.col("funding_rate") - pl.col("funding_rate").rolling_mean(window_30d))
            / pl.col("funding_rate").rolling_std(window_30d)
        ).alias("funding_z_30d"),

        # Z-score 90d
        (
            (pl.col("funding_rate") - pl.col("funding_rate").rolling_mean(window_90d))
            / pl.col("funding_rate").rolling_std(window_90d)
        ).alias("funding_z_90d"),

        # Annualized rate (hourly periods -> 24 per day -> 365 days)
        (pl.col("funding_rate") * 24 * 365).alias("funding_annualized"),

        # Carry for shorts: positive funding = long pays short = good for shorts
        # Carry = funding_rate (per period) * periods_per_year
        (pl.col("funding_rate") * 24 * 365).alias("funding_carry"),
    ])

    # If symbol column exists, preserve it
    if "symbol" in funding_df.columns:
        result = result.hstack(funding_df.select("symbol"))

    return result


def compute_carry_score(
    funding_df: pl.DataFrame,
    lookback_periods: int = 270,
) -> pl.DataFrame:
    """Compute expected carry score for short positions.

    Positive carry = funding_rate > 0 = long pays short = profitable to be short.
    We use a rolling mean to smooth out noise and capture persistent funding regimes.

    Args:
        funding_df: DataFrame with 'timestamp' and 'funding_rate' columns.
        lookback_periods: Number of funding periods to look back for expected carry.
            Default 270 ≈ 90 days (at 8h intervals).

    Returns:
        DataFrame with 'timestamp', 'carry_score', and 'carry_regime' columns.
        carry_score: expected annualized carry for shorts (positive = earn).
        carry_regime: 'positive', 'neutral', or 'negative' based on sign.
    """
    required = {"timestamp", "funding_rate"}
    missing = required - set(funding_df.columns)
    if missing:
        raise ValueError(f"funding_df missing required columns: {missing}")

    sorted_df = funding_df.sort("timestamp")

    result = sorted_df.select([
        pl.col("timestamp"),
        pl.col("funding_rate"),

        # Smoothed carry estimate: rolling mean of funding rate
        pl.col("funding_rate").rolling_mean(lookback_periods).alias("_carry_raw"),
    ])

    # Annualize
    carry_annualized = result["_carry_raw"] * 24 * 365
    result = result.with_columns([
        carry_annualized.alias("carry_score"),
        pl.when(carry_annualized > 0.05)
        .then(pl.lit("positive"))
        .when(carry_annualized < -0.05)
        .then(pl.lit("negative"))
        .otherwise(pl.lit("neutral"))
        .alias("carry_regime"),
    ]).drop("_carry_raw")

    if "symbol" in funding_df.columns:
        result = result.hstack(funding_df.select("symbol"))

    return result
