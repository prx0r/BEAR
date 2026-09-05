"""Polars schemas for all BEAR data tables."""

from __future__ import annotations

import polars as pl
from datetime import datetime


# ---------------------------------------------------------------------------
# Candles
# ---------------------------------------------------------------------------

CANDLES_SCHEMA: dict[str, pl.DataType] = {
    "symbol": pl.Utf8,
    "interval": pl.Utf8,
    "open_time": pl.Datetime(time_unit="ms", time_zone="UTC"),
    "close_time": pl.Datetime(time_unit="ms", time_zone="UTC"),
    "open": pl.Decimal(precision=18, scale=8),
    "high": pl.Decimal(precision=18, scale=8),
    "low": pl.Decimal(precision=18, scale=8),
    "close": pl.Decimal(precision=18, scale=8),
    "volume": pl.Decimal(precision=18, scale=8),
    "trade_count": pl.Int64,
    "ingested_at": pl.Datetime(time_unit="ms", time_zone="UTC"),
}

CANDLES_DTYPES: dict[str, pl.DataType] = {
    "symbol": pl.Utf8,
    "interval": pl.Utf8,
    "open_time": pl.Datetime(time_unit="ms", time_zone="UTC"),
    "close_time": pl.Datetime(time_unit="ms", time_zone="UTC"),
    "open": pl.Float64,
    "high": pl.Float64,
    "low": pl.Float64,
    "close": pl.Float64,
    "volume": pl.Float64,
    "trade_count": pl.Int64,
    "ingested_at": pl.Datetime(time_unit="ms", time_zone="UTC"),
}


# ---------------------------------------------------------------------------
# Funding
# ---------------------------------------------------------------------------

FUNDING_SCHEMA: dict[str, pl.DataType] = {
    "symbol": pl.Utf8,
    "timestamp": pl.Datetime(time_unit="ms", time_zone="UTC"),
    "rate": pl.Decimal(precision=18, scale=10),
}

FUNDING_DTYPES: dict[str, pl.DataType] = {
    "symbol": pl.Utf8,
    "timestamp": pl.Datetime(time_unit="ms", time_zone="UTC"),
    "rate": pl.Float64,
}


# ---------------------------------------------------------------------------
# Asset contexts (snapshots)
# ---------------------------------------------------------------------------

ASSET_CONTEXTS_SCHEMA: dict[str, pl.DataType] = {
    "symbol": pl.Utf8,
    "timestamp": pl.Datetime(time_unit="ms", time_zone="UTC"),
    "mark_px": pl.Decimal(precision=18, scale=8),
    "mid_px": pl.Decimal(precision=18, scale=8),
    "oracle_px": pl.Decimal(precision=18, scale=8),
    "funding": pl.Decimal(precision=18, scale=10),
    "premium": pl.Decimal(precision=18, scale=10),
    "open_interest": pl.Decimal(precision=18, scale=8),
    "day_volume": pl.Decimal(precision=18, scale=8),
}

ASSET_CONTEXTS_DTYPES: dict[str, pl.DataType] = {
    "symbol": pl.Utf8,
    "timestamp": pl.Datetime(time_unit="ms", time_zone="UTC"),
    "mark_px": pl.Float64,
    "mid_px": pl.Float64,
    "oracle_px": pl.Float64,
    "funding": pl.Float64,
    "premium": pl.Float64,
    "open_interest": pl.Float64,
    "day_volume": pl.Float64,
}


# ---------------------------------------------------------------------------
# Markets (static universe)
# ---------------------------------------------------------------------------

MARKETS_SCHEMA: dict[str, pl.DataType] = {
    "symbol": pl.Utf8,
    "name": pl.Utf8,
    "dex": pl.Utf8,
    "sz_decimals": pl.Int32,
    "max_leverage": pl.Int32,
    "is_delisted": pl.Boolean,
    "margin_table_id": pl.Int32,
    "category": pl.Utf8,
}

MARKETS_DTYPES: dict[str, pl.DataType] = {
    "symbol": pl.Utf8,
    "name": pl.Utf8,
    "dex": pl.Utf8,
    "sz_decimals": pl.Int32,
    "max_leverage": pl.Int32,
    "is_delisted": pl.Boolean,
    "margin_table_id": pl.Int32,
    "category": pl.Utf8,
}


def empty_candles_df() -> pl.DataFrame:
    """Return an empty DataFrame with the candles schema."""
    return pl.DataFrame(schema=CANDLES_SCHEMA)


def empty_funding_df() -> pl.DataFrame:
    """Return an empty DataFrame with the funding schema."""
    return pl.DataFrame(schema=FUNDING_SCHEMA)


def empty_asset_contexts_df() -> pl.DataFrame:
    """Return an empty DataFrame with the asset contexts schema."""
    return pl.DataFrame(schema=ASSET_CONTEXTS_SCHEMA)


def empty_markets_df() -> pl.DataFrame:
    """Return an empty DataFrame with the markets schema."""
    return pl.DataFrame(schema=MARKETS_SCHEMA)
