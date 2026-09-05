"""Active-address value factor and valuation ratios.

Computes sector-relative value badness: network expensiveness, FDV/revenue,
FDV/fees, FDV/TVL, buyback yield, and net issuance yield.
"""

from __future__ import annotations

import numpy as np
import structlog
import polars as pl

logger = structlog.get_logger()


def compute_value_features(
    fundamentals: pl.DataFrame,
    sector_taxonomy: dict[str, str],
) -> pl.DataFrame:
    """Compute value badness features within sectors.

    Args:
        fundamentals: DataFrame with columns:
            - symbol: asset ticker
            - market_cap: current market cap
            - fdv: fully diluted valuation
            - active_addresses_30d: 30-day active address count
            - annualized_revenue: annualized protocol revenue
            - annualized_fees: annualized protocol fees
            - tvl: total value locked
            - buybacks_12m: buyback amount over last 12 months (nullable)
            - burns_12m: burn amount over last 12 months (nullable)
        sector_taxonomy: Mapping of symbol -> sector name.

    Returns:
        DataFrame with columns:
            - symbol
            - network_expensiveness: market_cap / active_addresses_30d
            - network_expensiveness_pct: sector-percentile rank
            - fdv_to_revenue: fdv / annualized_revenue (within sector)
            - fdv_to_fees: fdv / annualized_fees (within sector)
            - fdv_to_tvl: fdv / tvl (within sector)
            - buyback_yield: buybacks_12m / market_cap
            - net_issuance_yield: (supply_growth_12m - buybacks_12m) / circulating_supply
    """
    required = {"symbol", "market_cap", "fdv", "active_addresses_30d"}
    missing = required - set(fundamentals.columns)
    if missing:
        raise ValueError(f"fundamentals missing required columns: {missing}")

    has_revenue = "annualized_revenue" in fundamentals.columns
    has_fees = "annualized_fees" in fundamentals.columns
    has_tvl = "tvl" in fundamentals.columns
    has_buybacks = "buybacks_12m" in fundamentals.columns
    has_burns = "burns_12m" in fundamentals.columns
    has_supply_growth = "supply_growth_12m" in fundamentals.columns
    has_circ = "circulating_supply" in fundamentals.columns

    df = fundamentals.clone()

    market_cap = pl.col("market_cap")
    active_addr = pl.col("active_addresses_30d")

    df = df.with_columns(
        pl.when(
            active_addr.is_not_null()
            & (active_addr > 0)
            & market_cap.is_not_null()
            & (market_cap > 0)
        )
        .then(market_cap / active_addr)
        .otherwise(pl.lit(None).cast(pl.Float64))
        .alias("network_expensiveness")
    )

    if has_revenue:
        fdv = pl.col("fdv")
        revenue = pl.col("annualized_revenue")
        df = df.with_columns(
            pl.when(
                fdv.is_not_null()
                & (fdv > 0)
                & revenue.is_not_null()
                & (revenue > 0)
            )
            .then(fdv / revenue)
            .otherwise(pl.lit(None).cast(pl.Float64))
            .alias("fdv_to_revenue")
        )
    else:
        df = df.with_columns(pl.lit(None).cast(pl.Float64).alias("fdv_to_revenue"))

    if has_fees:
        fdv = pl.col("fdv")
        fees = pl.col("annualized_fees")
        df = df.with_columns(
            pl.when(
                fdv.is_not_null()
                & (fdv > 0)
                & fees.is_not_null()
                & (fees > 0)
            )
            .then(fdv / fees)
            .otherwise(pl.lit(None).cast(pl.Float64))
            .alias("fdv_to_fees")
        )
    else:
        df = df.with_columns(pl.lit(None).cast(pl.Float64).alias("fdv_to_fees"))

    if has_tvl:
        fdv = pl.col("fdv")
        tvl = pl.col("tvl")
        df = df.with_columns(
            pl.when(
                fdv.is_not_null()
                & (fdv > 0)
                & tvl.is_not_null()
                & (tvl > 0)
            )
            .then(fdv / tvl)
            .otherwise(pl.lit(None).cast(pl.Float64))
            .alias("fdv_to_tvl")
        )
    else:
        df = df.with_columns(pl.lit(None).cast(pl.Float64).alias("fdv_to_tvl"))

    if has_buybacks:
        buybacks = pl.col("buybacks_12m").fill_null(0.0)
        df = df.with_columns(
            pl.when(
                market_cap.is_not_null()
                & (market_cap > 0)
            )
            .then(buybacks / market_cap)
            .otherwise(pl.lit(None).cast(pl.Float64))
            .alias("buyback_yield")
        )
    else:
        df = df.with_columns(pl.lit(None).cast(pl.Float64).alias("buyback_yield"))

    if has_supply_growth and has_circ and has_buybacks:
        supply_growth = pl.col("supply_growth_12m").fill_null(0.0)
        buybacks = pl.col("buybacks_12m").fill_null(0.0)
        circ = pl.col("circulating_supply")
        df = df.with_columns(
            pl.when(
                circ.is_not_null()
                & (circ > 0)
            )
            .then((supply_growth - buybacks) / circ)
            .otherwise(pl.lit(None).cast(pl.Float64))
            .alias("net_issuance_yield")
        )
    else:
        df = df.with_columns(pl.lit(None).cast(pl.Float64).alias("net_issuance_yield"))

    df = _add_sector_percentile(df, "network_expensiveness", "network_expensiveness_pct", sector_taxonomy)
    df = _add_sector_percentile(df, "fdv_to_revenue", "fdv_to_revenue_pct", sector_taxonomy)
    df = _add_sector_percentile(df, "fdv_to_fees", "fdv_to_fees_pct", sector_taxonomy)
    df = _add_sector_percentile(df, "fdv_to_tvl", "fdv_to_tvl_pct", sector_taxonomy)

    keep_cols = [
        "symbol",
        "network_expensiveness", "network_expensiveness_pct",
        "fdv_to_revenue", "fdv_to_fees", "fdv_to_tvl",
        "buyback_yield", "net_issuance_yield",
    ]
    pct_cols = [c for c in df.columns if c.endswith("_pct")]
    all_cols = keep_cols + [c for c in pct_cols if c not in keep_cols]
    existing = [c for c in all_cols if c in df.columns]
    return df.select(existing)


def _add_sector_percentile(
    df: pl.DataFrame,
    source_col: str,
    target_col: str,
    taxonomy: dict[str, str],
) -> pl.DataFrame:
    """Add sector-relative percentile rank for a given column.

    Higher percentile = more expensive within sector.
    """
    if source_col not in df.columns:
        return df.with_columns(pl.lit(None).cast(pl.Float64).alias(target_col))

    symbols = df["symbol"].to_list()
    sectors = [taxonomy.get(s, "unknown") for s in symbols]
    sector_arr = pl.Series("_sector", sectors)

    df_with_sector = df.with_columns(sector_arr)

    ranked = df_with_sector.with_columns(
        pl.col(source_col)
        .rank(method="ordinal", descending=False)
        .over("_sector")
        .alias("_rank_raw")
    )

    count = ranked.select(
        pl.col("_rank_raw").count().over("_sector").alias("_n")
    )

    ranked = ranked.hstack(count)

    result = ranked.with_columns(
        pl.when(pl.col("_n") > 1)
        .then((pl.col("_rank_raw") - 1) / (pl.col("_n") - 1) * 100)
        .when(pl.col("_n") == 1)
        .then(pl.lit(50.0))
        .otherwise(pl.lit(None).cast(pl.Float64))
        .alias(target_col)
    ).drop(["_rank_raw", "_n", "_sector"])

    return result
