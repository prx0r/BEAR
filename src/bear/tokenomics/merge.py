"""Merge tokenomics with market data (point-in-time)."""

from __future__ import annotations

import logging
from typing import Optional

import polars as pl

logger = logging.getLogger(__name__)


def merge_tokenomics(
    market_df: pl.DataFrame,
    tokenomics_df: pl.DataFrame,
    *,
    market_timestamp_col: str = "timestamp",
    market_symbol_col: str = "symbol",
    tokenomics_timestamp_col: str = "timestamp",
    tokenomics_symbol_col: str = "symbol",
    known_at_col: str = "known_at",
    as_of: Optional[str] = None,
) -> pl.DataFrame:
    """Merge tokenomics data with market data using point-in-time join.

    For each market observation (timestamp, symbol), picks the most recent
    tokenomics snapshot where known_at <= market timestamp.

    Args:
        market_df: Market data with timestamp and symbol columns.
        tokenomics_df: Tokenomics data with timestamp and symbol columns.
        market_timestamp_col: Timestamp column in market data.
        market_symbol_col: Symbol column in market data.
        tokenomics_timestamp_col: Timestamp column in tokenomics data.
        tokenomics_symbol_col: Symbol column in tokenomics data.
        known_at_col: Point-in-time column in tokenomics (used if available).
        as_of: Override cutoff timestamp (if None, uses market timestamp).

    Returns:
        Merged DataFrame with tokenomics columns appended.
    """
    if tokenomics_df.is_empty():
        logger.warning("Empty tokenomics DataFrame, returning market data as-is")
        return market_df

    # Prepare tokenomics: use known_at for PIT, fall back to timestamp
    tok = tokenomics_df.clone()
    if known_at_col in tok.columns:
        tok = tok.with_columns(
            pl.col(known_at_col).fill_null(pl.col(tokenomics_timestamp_col)).alias("_pit_time")
        )
    else:
        tok = tok.with_columns(
            pl.col(tokenomics_timestamp_col).alias("_pit_time")
        )

    tok = tok.sort(["symbol", "_pit_time"])

    # Get tokenomics columns (exclude join keys)
    tok_cols = [c for c in tok.columns if c not in ("_pit_time",)]
    tok_for_join = tok.select(["symbol", "_pit_time"] + [c for c in tok_cols if c != "symbol" and c != tokenomics_timestamp_col])

    # Rename tokenomics timestamp to avoid collision
    tok_for_join = tok_for_join.rename({tokenomics_timestamp_col: "tok_timestamp"})

    # Cross join with inequality for PIT matching, then take latest
    # Use a more efficient approach: join on symbol, filter where tok_time <= market_time
    market_with_key = market_df.with_columns(
        pl.col(market_symbol_col).alias("_join_symbol"),
        pl.col(market_timestamp_col).alias("_join_time"),
    )

    # Join on symbol
    merged = market_with_key.join(
        tok_for_join,
        left_on="_join_symbol",
        right_on="symbol",
        how="left",
    )

    # Filter to point-in-time: tok_time <= market_time
    if as_of is not None:
        merged = merged.filter(
            (pl.col("_pit_time").is_null()) |
            (pl.col("_pit_time") <= as_of)
        )
    else:
        merged = merged.filter(
            (pl.col("_pit_time").is_null()) |
            (pl.col("_pit_time") <= pl.col("_join_time"))
        )

    # For each (market_time, symbol), keep only the latest tokenomics
    merged = merged.sort(["_join_symbol", "_join_time", "_pit_time"])
    merged = merged.group_by(["_join_symbol", "_join_time"]).agg([
        pl.col("*").last(),
    ])

    # Clean up temp columns
    drop_cols = ["_join_symbol", "_join_time", "_pit_time", "tok_timestamp"]
    for col in drop_cols:
        if col in merged.columns:
            merged = merged.drop(col)

    logger.info(
        "Merged %d market rows with tokenomics: %d result rows",
        market_df.height,
        merged.height,
    )
    return merged


def merge_tokenomics_simple(
    market_df: pl.DataFrame,
    tokenomics_df: pl.DataFrame,
    on: str = "symbol",
) -> pl.DataFrame:
    """Simple left join on symbol (latest tokenomics for each symbol).

    Use when point-in-time is not needed and you just want
    the most recent tokenomics per symbol.
    """
    if tokenomics_df.is_empty():
        return market_df

    # Get latest tokenomics per symbol
    latest = (
        tokenomics_df
        .sort("timestamp", descending=True)
        .group_by("symbol")
        .agg(pl.col("*").first())
    )

    return market_df.join(latest, on=on, how="left", suffix="_tok")
