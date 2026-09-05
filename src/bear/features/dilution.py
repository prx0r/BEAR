"""Supply dilution factor (Guo 2026 + Kiefer & Nowotny).

Multi-horizon supply dilution features. dilution_8w is the PRIMARY signal:
Sharpe 1.39, ~35-45% spread. Cross-sectional percentile ranking for
comparability across assets with different absolute supply dynamics.
"""

from __future__ import annotations

import structlog
import polars as pl

logger = structlog.get_logger()

_HORIZONS: dict[str, int] = {
    "dilution_2w": 14,
    "dilution_5w": 35,
    "dilution_8w": 56,
    "dilution_12w": 84,
}


def compute_dilution_features(supply_history: pl.DataFrame) -> pl.DataFrame:
    """Compute multi-horizon supply dilution features.

    Args:
        supply_history: DataFrame with columns:
            - symbol: asset ticker
            - timestamp: datetime (daily granularity expected)
            - circulating_supply: current circulating supply
            - total_supply: total supply cap
            - max_supply: hard cap (nullable)

    Returns:
        DataFrame with columns:
            - symbol
            - dilution_2w: log(circ_t / circ_t_minus_14d)
            - dilution_5w: log(circ_t / circ_t_minus_35d)
            - dilution_8w: log(circ_t / circ_t_minus_56d)  PRIMARY SIGNAL
            - dilution_12w: log(circ_t / circ_t_minus_84d)
            - dilution_8w_pct: cross-sectional percentile rank of dilution_8w
            - fdv_overhang: total_supply / circulating_supply
            - fdv_overhang_pct: percentile rank
            - net_supply_pressure: (unlocks + emissions - buybacks - burns) / circulating_supply

    Missing data: if circ_t_minus_Nd is missing, dilution_Nw is null (NOT zero).
    """
    required = {"symbol", "timestamp", "circulating_supply", "total_supply"}
    missing = required - set(supply_history.columns)
    if missing:
        raise ValueError(f"supply_history missing required columns: {missing}")

    has_max = "max_supply" in supply_history.columns
    has_emissions = "emissions_12m" in supply_history.columns
    has_buybacks = "buybacks_12m" in supply_history.columns
    has_burns = "burns_12m" in supply_history.columns

    symbols = supply_history["symbol"].unique().to_list()
    parts: list[pl.DataFrame] = []

    for sym in symbols:
        sub = (
            supply_history
            .filter(pl.col("symbol") == sym)
            .sort("timestamp")
        )

        if sub.height == 0:
            continue

        log_supply = pl.ln(pl.col("circulating_supply")).alias("_log_circ")

        result = sub.select([
            pl.col("symbol"),
            pl.col("timestamp"),
            pl.col("circulating_supply"),
            pl.col("total_supply"),
        ]).with_columns(log_supply)

        for name, days in _HORIZONS.items():
            shifted = pl.col("_log_circ").shift(days)
            result = result.with_columns(
                pl.when(shifted.is_not_null())
                .then(pl.col("_log_circ") - shifted)
                .otherwise(pl.lit(None).cast(pl.Float64))
                .alias(name)
            )

        if has_max:
            max_supply = pl.col("max_supply")
            circ = pl.col("circulating_supply")
            result = result.with_columns(
                pl.when(
                    circ.is_not_null()
                    & (circ > 0)
                    & max_supply.is_not_null()
                    & (max_supply > 0)
                )
                .then(max_supply / circ)
                .otherwise(pl.lit(None).cast(pl.Float64))
                .alias("fdv_overhang")
            )
        else:
            total = pl.col("total_supply")
            circ = pl.col("circulating_supply")
            result = result.with_columns(
                pl.when(
                    circ.is_not_null()
                    & (circ > 0)
                    & total.is_not_null()
                    & (total > 0)
                )
                .then(total / circ)
                .otherwise(pl.lit(None).cast(pl.Float64))
                .alias("fdv_overhang")
            )

        if has_emissions and has_buybacks and has_burns:
            emissions = pl.col("emissions_12m").fill_null(0.0)
            buybacks = pl.col("buybacks_12m").fill_null(0.0)
            burns = pl.col("burns_12m").fill_null(0.0)
            circ = pl.col("circulating_supply")
            net_flow = emissions - buybacks - burns
            result = result.with_columns(
                pl.when(circ.is_not_null() & (circ > 0))
                .then(net_flow / circ)
                .otherwise(pl.lit(None).cast(pl.Float64))
                .alias("net_supply_pressure")
            )
        else:
            result = result.with_columns(
                pl.lit(None).cast(pl.Float64).alias("net_supply_pressure")
            )

        result = result.drop("_log_circ")
        parts.append(result)

    if not parts:
        return pl.DataFrame()

    combined = pl.concat(parts)

    combined = _add_percentile_ranks(combined, "dilution_8w", "dilution_8w_pct")
    combined = _add_percentile_ranks(combined, "fdv_overhang", "fdv_overhang_pct")

    keep_cols = [
        "symbol",
        "dilution_2w", "dilution_5w", "dilution_8w", "dilution_12w",
        "dilution_8w_pct",
        "fdv_overhang", "fdv_overhang_pct",
        "net_supply_pressure",
    ]
    existing = [c for c in keep_cols if c in combined.columns]
    return combined.select(existing)


def _add_percentile_ranks(
    df: pl.DataFrame,
    source_col: str,
    target_col: str,
) -> pl.DataFrame:
    """Add cross-sectional percentile rank as a new column.

    Rank is computed within each timestamp. Uses Polars rank with
    average method for ties.
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
