"""DuckDB + Parquet storage layer for BEAR.

Provides a unified DataStore backed by DuckDB for queries and Parquet
files for bulk storage. Tables:

- candles: OHLCV candle data
- funding: hourly funding rates
- asset_contexts: point-in-time asset snapshots
- markets: static market metadata
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import polars as pl
import structlog

from bear.data.schemas import (
    CANDLES_SCHEMA,
    FUNDING_SCHEMA,
    ASSET_CONTEXTS_SCHEMA,
    MARKETS_SCHEMA,
)

logger = structlog.get_logger(__name__)

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent.parent.parent / "data" / "research.duckdb"


class DataStore:
    """Unified data store using DuckDB for queries and Parquet for bulk I/O.

    DuckDB database file: data/research.duckdb
    Parquet files: data/raw/{table}/{market_id}.parquet
    """

    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: duckdb.DuckDBPyConnection | None = None
        self._ensure_tables()

    @property
    def conn(self) -> duckdb.DuckDBPyConnection:
        if self._conn is None:
            self._conn = duckdb.connect(str(self.db_path))
        return self._conn

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def _ensure_tables(self) -> None:
        """Create tables if they don't exist."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS candles (
                symbol VARCHAR,
                interval VARCHAR,
                open_time TIMESTAMP,
                close_time TIMESTAMP,
                open DOUBLE,
                high DOUBLE,
                low DOUBLE,
                close DOUBLE,
                volume DOUBLE,
                trade_count BIGINT,
                ingested_at TIMESTAMP,
                PRIMARY KEY (symbol, interval, open_time)
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS funding (
                symbol VARCHAR,
                timestamp TIMESTAMP,
                rate DOUBLE,
                funding_rate DOUBLE,
                PRIMARY KEY (symbol, timestamp)
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS asset_contexts (
                symbol VARCHAR,
                timestamp TIMESTAMP,
                mark_px DOUBLE,
                mid_px DOUBLE,
                oracle_px DOUBLE,
                funding DOUBLE,
                premium DOUBLE,
                open_interest DOUBLE,
                day_volume DOUBLE,
                PRIMARY KEY (symbol, timestamp)
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS markets (
                symbol VARCHAR PRIMARY KEY,
                name VARCHAR,
                dex VARCHAR,
                sz_decimals INTEGER,
                max_leverage INTEGER,
                is_delisted BOOLEAN,
                margin_table_id INTEGER,
                category VARCHAR
            )
        """)

    # -- Candles ------------------------------------------------------------

    def save_candles(self, df: pl.DataFrame) -> int:
        """Upsert candle DataFrame into DuckDB. Returns rows affected."""
        if df.height == 0:
            return 0

        # Ensure correct types
        df = df.cast({
            "open": pl.Float64,
            "high": pl.Float64,
            "low": pl.Float64,
            "close": pl.Float64,
            "volume": pl.Float64,
        })

        # Register as temporary view and upsert
        self.conn.register("_tmp_candles", df.to_arrow())

        # Delete existing rows for same symbols, then insert
        symbols = df["symbol"].unique().to_list()
        for sym in symbols:
            self.conn.execute(
                "DELETE FROM candles WHERE symbol = ?", [sym]
            )
        self.conn.execute("""
            INSERT INTO candles SELECT * FROM _tmp_candles
        """)

        rows = df.height
        self.conn.unregister("_tmp_candles")
        logger.info("candles_saved", rows=rows)
        return rows

    def load_candles(
        self,
        market_id: str,
        interval: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> pl.DataFrame:
        """Load candles from DuckDB with optional time range filter."""
        query = "SELECT * FROM candles WHERE symbol = ? AND interval = ?"
        params: list = [market_id, interval]

        if start:
            query += " AND open_time >= ?"
            params.append(start)
        if end:
            query += " AND open_time <= ?"
            params.append(end)

        query += " ORDER BY open_time"

        result = self.conn.execute(query, params).fetchdf()
        if result.empty:
            return pl.DataFrame(schema=CANDLES_SCHEMA)

        return pl.from_pandas(result)

    # -- Funding ------------------------------------------------------------

    def save_funding(self, df: pl.DataFrame) -> int:
        """Upsert funding DataFrame into DuckDB."""
        if df.height == 0:
            return 0

        self.conn.register("_tmp_funding", df.to_arrow())
        # Delete existing rows for this symbol, then insert
        symbols = df["symbol"].unique().to_list()
        for sym in symbols:
            self.conn.execute(
                "DELETE FROM funding WHERE symbol = ?", [sym]
            )
        self.conn.execute("""
            INSERT INTO funding SELECT * FROM _tmp_funding
        """)

        rows = df.height
        self.conn.unregister("_tmp_funding")
        logger.info("funding_saved", rows=rows)
        return rows

    def load_funding(
        self,
        market_id: str,
        start: datetime | None = None,
    ) -> pl.DataFrame:
        """Load funding from DuckDB with optional start filter."""
        query = "SELECT * FROM funding WHERE symbol = ?"
        params: list = [market_id]

        if start:
            query += " AND timestamp >= ?"
            params.append(start)

        query += " ORDER BY timestamp"

        result = self.conn.execute(query, params).fetchdf()
        if result.empty:
            return pl.DataFrame(schema=FUNDING_SCHEMA)

        return pl.from_pandas(result)

    # -- Asset contexts -----------------------------------------------------

    def save_asset_contexts(self, df: pl.DataFrame) -> int:
        """Upsert asset context snapshots into DuckDB."""
        if df.height == 0:
            return 0

        self.conn.register("_tmp_ctx", df.to_arrow())
        # Delete by symbol, then insert all
        symbols = df["symbol"].unique().to_list()
        for sym in symbols:
            self.conn.execute(
                "DELETE FROM asset_contexts WHERE symbol = ?", [sym]
            )
        self.conn.execute("""
            INSERT INTO asset_contexts SELECT * FROM _tmp_ctx
        """)

        rows = df.height
        self.conn.unregister("_tmp_ctx")
        logger.info("asset_contexts_saved", rows=rows)
        return rows

    def load_asset_contexts(
        self,
        market_id: str,
        start: datetime | None = None,
    ) -> pl.DataFrame:
        """Load asset contexts from DuckDB with optional start filter."""
        query = "SELECT * FROM asset_contexts WHERE symbol = ?"
        params: list = [market_id]

        if start:
            query += " AND timestamp >= ?"
            params.append(start)

        query += " ORDER BY timestamp"

        result = self.conn.execute(query, params).fetchdf()
        if result.empty:
            return pl.DataFrame(schema=ASSET_CONTEXTS_SCHEMA)

        return pl.from_pandas(result)

    # -- Markets ------------------------------------------------------------

    def save_markets(self, df: pl.DataFrame) -> int:
        """Upsert market metadata into DuckDB."""
        if df.height == 0:
            return 0

        self.conn.register("_tmp_markets", df.to_arrow())
        # Delete existing, then insert
        symbols = df["symbol"].unique().to_list()
        for sym in symbols:
            self.conn.execute(
                "DELETE FROM markets WHERE symbol = ?", [sym]
            )
        self.conn.execute("""
            INSERT INTO markets SELECT * FROM _tmp_markets
        """)

        rows = df.height
        self.conn.unregister("_tmp_markets")
        logger.info("markets_saved", rows=rows)
        return rows

    def load_markets(self) -> pl.DataFrame:
        """Load all market metadata from DuckDB."""
        result = self.conn.execute("SELECT * FROM markets ORDER BY symbol").fetchdf()
        if result.empty:
            return pl.DataFrame(schema=MARKETS_SCHEMA)

        return pl.from_pandas(result)

    # -- Utility ------------------------------------------------------------

    def table_stats(self) -> dict[str, int]:
        """Return row counts for all tables."""
        stats = {}
        for table in ["candles", "funding", "asset_contexts", "markets"]:
            result = self.conn.execute(f"SELECT count(*) FROM {table}").fetchone()
            stats[table] = result[0] if result else 0
        return stats
