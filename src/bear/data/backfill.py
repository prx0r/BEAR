"""Backfill orchestration for BEAR data acquisition.

Coordinates candle and funding backfill across the universe with:
- Rate-limited fetching
- Progress tracking
- Resume capability (checks what's already stored)
- Date range specification
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from pathlib import Path

import polars as pl
import structlog

from bear.hyperliquid.client import HyperliquidClient, RateLimiter
from bear.hyperliquid.universe import UniverseManager, UniverseSnapshot
from bear.hyperliquid.candles import CandleManager, INTERVAL_MS
from bear.hyperliquid.funding import FundingManager
from bear.data.store import DataStore

logger = structlog.get_logger(__name__)


class BackfillProgress:
    """Track backfill progress across coins and intervals."""

    def __init__(self) -> None:
        self.total_coins: int = 0
        self.completed_coins: int = 0
        self.current_coin: str = ""
        self.current_interval: str = ""
        self.errors: list[dict] = []

    def summary(self) -> dict:
        return {
            "total": self.total_coins,
            "completed": self.completed_coins,
            "current": f"{self.current_coin}/{self.current_interval}",
            "errors": len(self.errors),
        }


class BackfillManager:
    """Coordinates candle and funding backfill for the Hyperliquid universe.

    Features:
        - Resumes from where it left off (checks existing Parquet/DuckDB)
        - Rate-limited fetching via shared RateLimiter
        - Progress tracking and error reporting
        - Configurable date range and coin selection
    """

    def __init__(
        self,
        client: HyperliquidClient,
        universe_mgr: UniverseManager,
        candle_mgr: CandleManager,
        funding_mgr: FundingManager,
        store: DataStore,
    ) -> None:
        self.client = client
        self.universe_mgr = universe_mgr
        self.candle_mgr = candle_mgr
        self.funding_mgr = funding_mgr
        self.store = store
        self.progress = BackfillProgress()

    async def backfill_candles(
        self,
        coins: list[str] | None = None,
        intervals: list[str] | None = None,
        start_ms: int | None = None,
        end_ms: int | None = None,
        *,
        force: bool = False,
    ) -> dict:
        """Backfill candle data for specified coins and intervals.

        Args:
            coins: list of coin names (default: all active from universe)
            intervals: list of intervals (default: ["1h", "4h", "1d"])
            start_ms: epoch ms start (default: 90 days ago)
            end_ms: epoch ms end (default: now)
            force: re-fetch everything

        Returns:
            Progress summary dict.
        """
        # Ensure universe is loaded
        snapshot = await self.universe_mgr.get_or_refresh()

        if coins is None:
            coins = [a.name for a in snapshot.active_assets]

        if intervals is None:
            intervals = ["1h", "4h", "1d"]

        if start_ms is None:
            start_ms = int((time.time() - 90 * 86400) * 1000)

        if end_ms is None:
            end_ms = int(time.time() * 1000)

        self.progress = BackfillProgress()
        self.progress.total_coins = len(coins)

        logger.info(
            "candle_backfill_started",
            coins=len(coins),
            intervals=intervals,
            start=datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc).isoformat(),
            end=datetime.fromtimestamp(end_ms / 1000, tz=timezone.utc).isoformat(),
        )

        for coin in coins:
            self.progress.current_coin = coin
            for interval in intervals:
                self.progress.current_interval = interval
                try:
                    df = await self.candle_mgr.backfill(
                        coin=coin,
                        interval=interval,
                        start_time_ms=start_ms,
                        end_time_ms=end_ms,
                        force=force,
                    )

                    # Also persist to DuckDB
                    if df.height > 0:
                        self.store.save_candles(df)

                    logger.info(
                        "candle_backfill_coin_done",
                        coin=coin,
                        interval=interval,
                        rows=df.height,
                    )
                except Exception as exc:
                    error = {"coin": coin, "interval": interval, "error": str(exc)}
                    self.progress.errors.append(error)
                    logger.error(
                        "candle_backfill_error",
                        coin=coin,
                        interval=interval,
                        error=str(exc),
                    )

            self.progress.completed_coins += 1

        summary = self.progress.summary()
        logger.info("candle_backfill_complete", **summary)
        return summary

    async def backfill_funding(
        self,
        coins: list[str] | None = None,
        start_ms: int | None = None,
        end_ms: int | None = None,
        *,
        force: bool = False,
    ) -> dict:
        """Backfill funding data for specified coins.

        Args:
            coins: list of coin names (default: all active from universe)
            start_ms: epoch ms start (default: 90 days ago)
            end_ms: epoch ms end (default: now)
            force: re-fetch everything

        Returns:
            Progress summary dict.
        """
        snapshot = await self.universe_mgr.get_or_refresh()

        if coins is None:
            coins = [a.name for a in snapshot.active_assets]

        if start_ms is None:
            start_ms = int((time.time() - 90 * 86400) * 1000)

        if end_ms is None:
            end_ms = int(time.time() * 1000)

        self.progress = BackfillProgress()
        self.progress.total_coins = len(coins)

        logger.info(
            "funding_backfill_started",
            coins=len(coins),
            start=datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc).isoformat(),
        )

        for coin in coins:
            self.progress.current_coin = coin
            self.progress.current_interval = "hourly"
            try:
                df = await self.funding_mgr.backfill(
                    coin=coin,
                    start_time_ms=start_ms,
                    end_time_ms=end_ms,
                    force=force,
                )

                if df.height > 0:
                    self.store.save_funding(df)

                logger.info("funding_backfill_coin_done", coin=coin, rows=df.height)
            except Exception as exc:
                error = {"coin": coin, "error": str(exc)}
                self.progress.errors.append(error)
                logger.error("funding_backfill_error", coin=coin, error=str(exc))

            self.progress.completed_coins += 1

        summary = self.progress.summary()
        logger.info("funding_backfill_complete", **summary)
        return summary

    async def backfill_all(
        self,
        coins: list[str] | None = None,
        intervals: list[str] | None = None,
        days: int = 90,
        *,
        force: bool = False,
    ) -> dict:
        """Full backfill: candles + funding for all coins.

        Args:
            coins: coin names (default: all active)
            intervals: candle intervals (default: ["1h", "4h", "1d"])
            days: how many days of history
            force: re-fetch everything

        Returns:
            Combined progress summary.
        """
        now_ms = int(time.time() * 1000)
        start_ms = int((time.time() - days * 86400) * 1000)

        logger.info(
            "full_backfill_started",
            days=days,
            coins=coins or "all active",
        )

        # Candles
        candle_result = await self.backfill_candles(
            coins=coins,
            intervals=intervals,
            start_ms=start_ms,
            end_ms=now_ms,
            force=force,
        )

        # Funding
        funding_result = await self.backfill_funding(
            coins=coins,
            start_ms=start_ms,
            end_ms=now_ms,
            force=force,
        )

        # Save markets to DuckDB
        market_rows = self.universe_mgr.to_market_rows()
        if market_rows:
            markets_df = pl.DataFrame(market_rows)
            self.store.save_markets(markets_df)

        # Final stats
        stats = self.store.table_stats()

        result = {
            "candles": candle_result,
            "funding": funding_result,
            "db_stats": stats,
        }

        logger.info("full_backfill_complete", **result)
        return result
