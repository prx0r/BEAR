"""Historical candle acquisition for Hyperliquid perp markets.

Fetches candles via the REST API, persists to Parquet, and supports
incremental backfill with gap detection.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import polars as pl
import structlog

from bear.hyperliquid.client import HyperliquidClient
from bear.data.schemas import CANDLES_SCHEMA

logger = structlog.get_logger(__name__)

# Supported intervals and their ms durations
INTERVAL_MS: dict[str, int] = {
    "1m": 60_000,
    "5m": 300_000,
    "15m": 900_000,
    "1h": 3_600_000,
    "4h": 14_400_000,
    "1d": 86_400_000,
}

# Maximum candles per request (Hyperliquid limit)
MAX_CANDLES_PER_REQ = 5000

# Default parquet base path
DEFAULT_PARQUET_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "raw" / "candles"


class CandleManager:
    """Acquires and stores historical candles for Hyperliquid perp coins.

    Features:
        - Paginated backfill for large date ranges
        - Never re-fetches existing candles (checks last timestamp in Parquet)
        - Persists to Parquet files: data/raw/candles/{coin}/{interval}.parquet
        - Rate-limited via the shared HyperliquidClient
    """

    def __init__(
        self,
        client: HyperliquidClient,
        *,
        parquet_dir: Path | str | None = None,
    ) -> None:
        self.client = client
        self.parquet_dir = Path(parquet_dir) if parquet_dir else DEFAULT_PARQUET_DIR

    # -- Path helpers -------------------------------------------------------

    def _parquet_path(self, coin: str, interval: str) -> Path:
        coin_dir = self.parquet_dir / coin.upper()
        coin_dir.mkdir(parents=True, exist_ok=True)
        return coin_dir / f"{interval}.parquet"

    def _load_existing(self, coin: str, interval: str) -> pl.DataFrame | None:
        path = self._parquet_path(coin, interval)
        if not path.exists():
            return None
        try:
            df = pl.read_parquet(path)
            if df.height == 0:
                return None
            return df
        except Exception as exc:
            logger.warning("parquet_read_error", coin=coin, interval=interval, error=str(exc))
            return None

    # -- Core fetch ---------------------------------------------------------

    async def fetch_candles(
        self,
        coin: str,
        interval: str,
        start_time_ms: int,
        end_time_ms: int,
    ) -> list[dict]:
        """Fetch candles from Hyperliquid for a single paginated request."""
        if interval not in INTERVAL_MS:
            raise ValueError(f"Unsupported interval: {interval}. Use one of {list(INTERVAL_MS)}")

        all_candles: list[dict] = []
        cursor_start = start_time_ms

        while cursor_start < end_time_ms:
            batch_end = min(cursor_start + MAX_CANDLES_PER_REQ * INTERVAL_MS[interval], end_time_ms)

            raw = await self.client.get_candles(
                coin=coin,
                interval=interval,
                start_time=cursor_start,
                end_time=batch_end,
            )

            if not raw:
                break

            all_candles.extend(raw)

            # Move cursor past the last candle
            last_t = raw[-1].get("t", cursor_start)
            if isinstance(last_t, (int, float)):
                cursor_start = int(last_t) + INTERVAL_MS[interval]
            else:
                # If it's a string datetime, advance by one interval
                cursor_start = batch_end

            # Safety: if we got fewer than expected, we've hit the end
            if len(raw) < MAX_CANDLES_PER_REQ:
                break

        return all_candles

    async def backfill(
        self,
        coin: str,
        interval: str,
        start_time_ms: int,
        end_time_ms: int | None = None,
        *,
        force: bool = False,
    ) -> pl.DataFrame:
        """Backfill candles for a coin, appending to existing Parquet.

        Args:
            coin: e.g. "BTC"
            interval: "1h", "4h", "1d"
            start_time_ms: epoch ms to start from
            end_time_ms: epoch ms to end at (default: now)
            force: if True, re-fetch everything ignoring existing data

        Returns:
            Complete DataFrame for this coin+interval.
        """
        coin = coin.upper()
        if end_time_ms is None:
            end_time_ms = int(time.time() * 1000)

        existing = self._load_existing(coin, interval) if not force else None

        # Determine actual start: after last existing candle
        if existing is not None and existing.height > 0 and not force:
            last_open = existing["open_time"].max()
            if last_open is not None:
                # Start from the next candle after the last one
                last_ms = int(last_open.timestamp() * 1000)
                actual_start = last_ms + INTERVAL_MS[interval]
                if actual_start >= end_time_ms:
                    logger.info("backfill_up_to_date", coin=coin, interval=interval)
                    return existing
                logger.info(
                    "backfill_resuming",
                    coin=coin,
                    interval=interval,
                    from_ms=actual_start,
                )
                start_time_ms = actual_start

        # Fetch new candles
        logger.info(
            "backfill_start",
            coin=coin,
            interval=interval,
            from_ms=start_time_ms,
            to_ms=end_time_ms,
        )

        raw_candles = await self.fetch_candles(coin, interval, start_time_ms, end_time_ms)

        if not raw_candles:
            if existing is not None:
                return existing
            return pl.DataFrame(schema=CANDLES_SCHEMA)

        # Build new DataFrame from raw
        new_df = self._raw_to_df(raw_candles, coin, interval)

        # Concat with existing
        if existing is not None and existing.height > 0:
            combined = pl.concat([existing, new_df]).unique(
                subset=["symbol", "interval", "open_time"],
                keep="last",
            ).sort("open_time")
        else:
            combined = new_df.sort("open_time")

        # Persist
        out_path = self._parquet_path(coin, interval)
        combined.write_parquet(out_path, use_pyarrow=True, compression="zstd")

        logger.info(
            "backfill_complete",
            coin=coin,
            interval=interval,
            rows=combined.height,
            path=str(out_path),
        )

        return combined

    def _raw_to_df(self, raw: list[dict], coin: str, interval: str) -> pl.DataFrame:
        """Convert raw candle dicts from Hyperliquid into a Polars DataFrame."""
        now_ms = int(time.time() * 1000)
        rows = []
        for c in raw:
            open_time_ms = int(c.get("t", 0))
            close_time_ms = open_time_ms + INTERVAL_MS.get(interval, 3_600_000) - 1
            rows.append({
                "symbol": coin.upper(),
                "interval": interval,
                "open_time": datetime.fromtimestamp(open_time_ms / 1000, tz=timezone.utc),
                "close_time": datetime.fromtimestamp(close_time_ms / 1000, tz=timezone.utc),
                "open": float(c.get("o", 0)),
                "high": float(c.get("h", 0)),
                "low": float(c.get("l", 0)),
                "close": float(c.get("c", 0)),
                "volume": float(c.get("v", 0)),
                "trade_count": int(c.get("n", 0)),
                "ingested_at": datetime.fromtimestamp(now_ms / 1000, tz=timezone.utc),
            })

        if not rows:
            return pl.DataFrame(schema=CANDLES_SCHEMA)

        df = pl.DataFrame(rows)
        # Cast to match schema
        df = df.cast({
            "open": pl.Float64,
            "high": pl.Float64,
            "low": pl.Float64,
            "close": pl.Float64,
            "volume": pl.Float64,
        })
        return df

    # -- Query helpers ------------------------------------------------------

    def load_candles(
        self,
        coin: str,
        interval: str,
        start: datetime | int | None = None,
        end: datetime | int | None = None,
    ) -> pl.DataFrame:
        """Load candles from Parquet with optional time range filter."""
        df = self._load_existing(coin.upper(), interval)
        if df is None:
            return pl.DataFrame(schema=CANDLES_SCHEMA)

        if start is not None:
            if isinstance(start, int):
                start = datetime.fromtimestamp(start / 1000, tz=timezone.utc)
            df = df.filter(pl.col("open_time") >= start)

        if end is not None:
            if isinstance(end, int):
                end = datetime.fromtimestamp(end / 1000, tz=timezone.utc)
            df = df.filter(pl.col("open_time") <= end)

        return df

    def last_timestamp(self, coin: str, interval: str) -> int | None:
        """Return the last open_time as epoch ms, or None if no data."""
        df = self._load_existing(coin.upper(), interval)
        if df is None or df.height == 0:
            return None
        last = df["open_time"].max()
        if last is None:
            return None
        return int(last.timestamp() * 1000)
