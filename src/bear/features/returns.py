"""Return calculations for relative-value trading."""

from __future__ import annotations

import polars as pl
import numpy as np


def compute_log_returns(prices_df: pl.DataFrame) -> pl.DataFrame:
    """Compute log returns from close prices.

    Args:
        prices_df: DataFrame with 'timestamp' column and one or more price
            columns named after the asset symbol. Each column contains close prices.

    Returns:
        DataFrame with 'timestamp' column and log-return columns for each asset.
        Null prices produce null returns — never zero fills.
    """
    if "timestamp" not in prices_df.columns:
        raise ValueError("prices_df must contain a 'timestamp' column")

    price_cols = [c for c in prices_df.columns if c != "timestamp"]
    if not price_cols:
        raise ValueError("prices_df must contain at least one price column besides 'timestamp'")

    result_cols: list[pl.Expr] = [pl.col("timestamp")]

    for col in price_cols:
        shifted = pl.col(col).shift(1)
        result_cols.append(
            pl.when(shifted.is_not_null() & (shifted > 0) & pl.col(col).is_not_null() & (pl.col(col) > 0))
            .then(pl.ln(pl.col(col) / shifted))
            .otherwise(pl.lit(None).cast(pl.Float64))
            .alias(col)
        )

    return prices_df.select(result_cols)


def compute_returns_at_intervals(
    candles_df: pl.DataFrame,
    intervals: list[int] | None = None,
) -> pl.DataFrame:
    """Compute returns at different horizons from OHLCV candle data.

    Args:
        candles_df: Must contain 'timestamp', 'close', and 'symbol' columns.
        intervals: List of candle-gap intervals to compute returns over.
            Defaults to [1, 4, 24].

    Returns:
        Wide DataFrame with 'timestamp' and columns named
        '<symbol>_ret_<interval>' for each symbol and interval.
        Null when insufficient history exists for the interval.
    """
    if intervals is None:
        intervals = [1, 4, 24]

    required = {"timestamp", "close", "symbol"}
    missing = required - set(candles_df.columns)
    if missing:
        raise ValueError(f"candles_df missing required columns: {missing}")

    symbols = candles_df["symbol"].unique().to_list()
    result_dfs: list[pl.DataFrame] = []

    for symbol in symbols:
        sym_df = (
            candles_df
            .filter(pl.col("symbol") == symbol)
            .sort("timestamp")
            .select(["timestamp", "close"])
        )

        interval_exprs: list[pl.Expr] = [pl.col("timestamp")]

        for interval in intervals:
            shifted_close = pl.col("close").shift(interval)
            col_name = f"{symbol}_ret_{interval}"

            interval_exprs.append(
                pl.when(
                    shifted_close.is_not_null()
                    & (shifted_close > 0)
                    & pl.col("close").is_not_null()
                    & (pl.col("close") > 0)
                )
                .then(pl.ln(pl.col("close") / shifted_close))
                .otherwise(pl.lit(None).cast(pl.Float64))
                .alias(col_name)
            )

        result_dfs.append(sym_df.select(interval_exprs))

    if not result_dfs:
        return pl.DataFrame({"timestamp": [], "symbol": []})

    merged = result_dfs[0]
    for df in result_dfs[1:]:
        merged = merged.join(df, on="timestamp", how="full", coalesce=True)

    return merged.sort("timestamp")
