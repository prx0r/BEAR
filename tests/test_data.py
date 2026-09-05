"""Tests for the data store layer (DuckDB)."""

from __future__ import annotations

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import polars as pl
import pytest

from bear.data.store import DataStore
from bear.data.schemas import CANDLES_DTYPES, FUNDING_DTYPES, MARKETS_DTYPES


@pytest.fixture
def temp_store():
    """Create a temporary DataStore with in-memory DuckDB."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.duckdb"
        store = DataStore(db_path)
        yield store
        store.close()


def _make_candles_df(symbol: str = "BTC", n: int = 10) -> pl.DataFrame:
    """Create a small candles DataFrame."""
    base = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return pl.DataFrame({
        "symbol": [symbol] * n,
        "interval": ["1h"] * n,
        "open_time": [base + timedelta(hours=i) for i in range(n)],
        "close_time": [base + timedelta(hours=i + 1) for i in range(n)],
        "open": [60000.0 + i * 10 for i in range(n)],
        "high": [60100.0 + i * 10 for i in range(n)],
        "low": [59900.0 + i * 10 for i in range(n)],
        "close": [60050.0 + i * 10 for i in range(n)],
        "volume": [1e6] * n,
        "trade_count": [1000] * n,
        "ingested_at": [datetime.now(timezone.utc)] * n,
    })


def _make_funding_df(symbol: str = "BTC", n: int = 10) -> pl.DataFrame:
    """Create a small funding DataFrame matching the DuckDB table schema."""
    base = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return pl.DataFrame({
        "symbol": [symbol] * n,
        "timestamp": [base + timedelta(hours=i * 8) for i in range(n)],
        "rate": [0.0001 * (i + 1) for i in range(n)],
        "funding_rate": [0.0001 * (i + 1) for i in range(n)],
    })


def _make_markets_df() -> pl.DataFrame:
    """Create a small markets DataFrame."""
    return pl.DataFrame({
        "symbol": ["BTC", "ETH", "SOL"],
        "name": ["Bitcoin", "Ethereum", "Solana"],
        "dex": ["core", "core", "core"],
        "sz_decimals": [5, 4, 2],
        "max_leverage": [50, 50, 20],
        "is_delisted": [False, False, False],
        "margin_table_id": [0, 0, 0],
        "category": ["bitcoin", "ethereum", "l1"],
    })


def test_store_save_load_candles():
    """Round-trip candles through DuckDB store."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_candles.duckdb"
        store = DataStore(db_path)

        df = _make_candles_df("BTC", 20)
        rows = store.save_candles(df)
        assert rows == 20

        loaded = store.load_candles("BTC", "1h")
        assert loaded.height == 20
        assert "close" in loaded.columns
        assert "open" in loaded.columns

        store.close()


def test_store_save_load_funding():
    """Round-trip funding through store."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_funding.duckdb"
        store = DataStore(db_path)

        df = _make_funding_df("ETH", 15)
        rows = store.save_funding(df)
        assert rows == 15

        loaded = store.load_funding("ETH")
        assert loaded.height == 15
        assert "rate" in loaded.columns

        store.close()


def test_store_market_schema():
    """Markets loaded with correct schema."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_markets.duckdb"
        store = DataStore(db_path)

        df = _make_markets_df()
        rows = store.save_markets(df)
        assert rows == 3

        loaded = store.load_markets()
        assert loaded.height == 3

        for col in ["symbol", "name", "dex", "category"]:
            assert col in loaded.columns

        store.close()


def test_no_duplicate_market_ids():
    """No duplicate symbols in universe."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_dup.duckdb"
        store = DataStore(db_path)

        df = _make_markets_df()
        store.save_markets(df)

        # Upsert duplicates
        store.save_markets(df)

        loaded = store.load_markets()
        symbols = loaded["symbol"].to_list()
        assert len(symbols) == len(set(symbols)), (
            f"Duplicate symbols found: {symbols}"
        )

        store.close()


def test_table_stats():
    """table_stats returns correct row counts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_stats.duckdb"
        store = DataStore(db_path)

        store.save_candles(_make_candles_df("BTC", 10))
        store.save_funding(_make_funding_df("BTC", 5))
        store.save_markets(_make_markets_df())

        stats = store.table_stats()
        assert stats["candles"] == 10
        assert stats["funding"] == 5
        assert stats["markets"] == 3

        store.close()


def test_load_empty():
    """Loading from empty tables returns empty DataFrames."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_empty.duckdb"
        store = DataStore(db_path)

        candles = store.load_candles("NONEXISTENT", "1h")
        assert candles.height == 0

        funding = store.load_funding("NONEXISTENT")
        assert funding.height == 0

        markets = store.load_markets()
        assert markets.height == 0

        store.close()


def test_upsert_candles():
    """Upserting candles replaces existing records."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_upsert.duckdb"
        store = DataStore(db_path)

        df1 = _make_candles_df("BTC", 5)
        store.save_candles(df1)

        df2 = df1.with_columns(pl.col("close") * 1.1)
        store.save_candles(df2)

        loaded = store.load_candles("BTC", "1h")
        assert loaded.height == 5

        first_close = loaded["close"][0]
        assert first_close > 60000.0

        store.close()
