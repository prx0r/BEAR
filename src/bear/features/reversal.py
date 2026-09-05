"""8-10 week reversal factor (Reversal in Crypto Returns 2026).

In crypto, 8-10 week winners revert. High rev_8w = recent winner = short candidate.
This is INDEPENDENT of dilution (correlation ~-0.03).
"""

from __future__ import annotations

import structlog
import polars as pl

logger = structlog.get_logger()

_HORIZONS: dict[str, int] = {
    "rev_4w": 28,
    "rev_8w": 56,
    "rev_10w": 70,
}


def compute_reversal_features(prices_df: pl.DataFrame) -> pl.DataFrame:
    """Compute medium-term reversal features.

    Args:
        prices_df: DataFrame with columns:
            - symbol: asset ticker
            - timestamp: datetime
            - close: daily close price

    Returns:
        DataFrame with columns:
            - symbol
            - rev_8w: log(price_t / price_t_minus_56d)  PRIMARY
            - rev_10w: log(price_t / price_t_minus_70d)
            - rev_4w: log(price_t / price_t_minus_28d)
            - rev_8w_pct: cross-sectional percentile rank
                HIGH = recent winner = SHORT candidate
    """
    required = {"symbol", "timestamp", "close"}
    missing = required - set(prices_df.columns)
    if missing:
        raise ValueError(f"prices_df missing required columns: {missing}")

    symbols = prices_df["symbol"].unique().to_list()
    parts: list[pl.DataFrame] = []

    for sym in symbols:
        sub = (
            prices_df
            .filter(pl.col("symbol") == sym)
            .sort("timestamp")
        )

        if sub.height == 0:
            continue

        log_close = pl.ln(pl.col("close")).alias("_log_close")

        result = sub.select([
            pl.col("symbol"),
            pl.col("timestamp"),
        ]).with_columns(log_close)

        for name, days in _HORIZONS.items():
            shifted = pl.col("_log_close").shift(days)
            result = result.with_columns(
                pl.when(shifted.is_not_null())
                .then(pl.col("_log_close") - shifted)
                .otherwise(pl.lit(None).cast(pl.Float64))
                .alias(name)
            )

        result = result.drop("_log_close")
        parts.append(result)

    if not parts:
        return pl.DataFrame()

    combined = pl.concat(parts)

    combined = _add_percentile_rank(combined, "rev_8w", "rev_8w_pct")

    keep_cols = ["symbol", "rev_8w", "rev_10w", "rev_4w", "rev_8w_pct"]
    existing = [c for c in keep_cols if c in combined.columns]
    return combined.select(existing)


def _add_percentile_rank(
    df: pl.DataFrame,
    source_col: str,
    target_col: str,
) -> pl.DataFrame:
    """Add cross-sectional percentile rank as a new column.

    Rank is computed within each timestamp.
    """
    if source_col not in df.columns:
        return df.with_columns(pl.lit(None).cast(pl.Float64).alias(target_col))

    ranked = df.with_columns(
        pl.col(source_col)
        .rank(method="ordinal", descending=False)
        .over("timestamp")
        .alias("_rank_raw")
    )

    count = ranked.select(
        pl.col("_rank_raw").count().over("timestamp").alias("_n")
    )

    ranked = ranked.hstack(count)

    result = ranked.with_columns(
        pl.when(pl.col("_n") > 1)
        .then((pl.col("_rank_raw") - 1) / (pl.col("_n") - 1) * 100)
        .when(pl.col("_n") == 1)
        .then(pl.lit(50.0))
        .otherwise(pl.lit(None).cast(pl.Float64))
        .alias(target_col)
    ).drop(["_rank_raw", "_n"])

    return result
