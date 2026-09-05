"""Funding history acquisition and analytics for Hyperliquid perp markets.

Fetches hourly funding, persists to Parquet, and computes derived metrics:
- funding_1h: most recent hourly rate
- funding_24h_sum: rolling 24h sum
- funding_7d_mean: 7-day mean
- funding_30d_mean: 30-day mean
- funding_z_30d: z-score over 30d window
- funding_z_90d: z-score over 90d window
- annualized_recent_funding: annualized from recent rate

Sign convention: positive funding = long pays short.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import polars as pl
import structlog

from bear.hyperliquid.client import HyperliquidClient
from bear.data.schemas import FUNDING_SCHEMA

logger = structlog.get_logger(__name__)

# Max entries per funding request
MAX_FUNDING_PER_REQ = 5000

# Default parquet base path
DEFAULT_PARQUET_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "raw" / "funding"


class FundingManager:
    """Acquires and stores funding history for Hyperliquid perp coins.

    Features:
        - Paginated backfill
        - Never re-fetches existing data (checks last timestamp)
        - Persists to Parquet: data/raw/funding/{coin}.parquet
        - Computes derived funding analytics
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

    def _parquet_path(self, coin: str) -> Path:
        coin_dir = self.parquet_dir / coin.upper()
        coin_dir.mkdir(parents=True, exist_ok=True)
        return coin_dir / "hourly.parquet"

    def _load_existing(self, coin: str) -> pl.DataFrame | None:
        path = self._parquet_path(coin)
        if not path.exists():
            return None
        try:
            df = pl.read_parquet(path)
            return df if df.height > 0 else None
        except Exception as exc:
            logger.warning("parquet_read_error", coin=coin, error=str(exc))
            return None

    # -- Fetch --------------------------------------------------------------

    async def fetch_funding(
        self,
        coin: str,
        start_time_ms: int,
    ) -> list[dict]:
        """Fetch funding history from Hyperliquid, paginating as needed."""
        all_entries: list[dict] = []
        cursor = start_time_ms

        while True:
            raw = await self.client.get_funding_history(coin=coin, start_time=cursor)
            if not raw:
                break

            all_entries.extend(raw)

            # Move cursor past last entry
            last_t = raw[-1].get("time", cursor)
            if isinstance(last_t, (int, float)):
                cursor = int(last_t) + 1
            else:
                break

            if len(raw) < MAX_FUNDING_PER_REQ:
                break

        return all_entries

    async def backfill(
        self,
        coin: str,
        start_time_ms: int,
        end_time_ms: int | None = None,
        *,
        force: bool = False,
    ) -> pl.DataFrame:
        """Backfill funding for a coin, appending to existing Parquet.

        Args:
            coin: e.g. "BTC"
            start_time_ms: epoch ms to start from
            end_time_ms: epoch ms to end at (default: now)
            force: if True, re-fetch everything

        Returns:
            Complete funding DataFrame for this coin.
        """
        coin = coin.upper()
        if end_time_ms is None:
            end_time_ms = int(time.time() * 1000)

        existing = self._load_existing(coin) if not force else None

        # Determine actual start
        if existing is not None and existing.height > 0 and not force:
            last_ts = existing["timestamp"].max()
            if last_ts is not None:
                last_ms = int(last_ts.timestamp() * 1000)
                actual_start = last_ms + 1
                if actual_start >= end_time_ms:
                    logger.info("funding_up_to_date", coin=coin)
                    return existing
                logger.info("funding_resuming", coin=coin, from_ms=actual_start)
                start_time_ms = actual_start

        # Fetch
        logger.info("funding_backfill_start", coin=coin, from_ms=start_time_ms, to_ms=end_time_ms)

        raw = await self.fetch_funding(coin, start_time_ms)

        if not raw:
            return existing if existing is not None else pl.DataFrame(schema=FUNDING_SCHEMA)

        new_df = self._raw_to_df(raw, coin)

        if existing is not None and existing.height > 0:
            combined = pl.concat([existing, new_df]).unique(
                subset=["symbol", "timestamp"],
                keep="last",
            ).sort("timestamp")
        else:
            combined = new_df.sort("timestamp")

        # Persist
        out_path = self._parquet_path(coin)
        combined.write_parquet(out_path, use_pyarrow=True, compression="zstd")

        logger.info("funding_backfill_complete", coin=coin, rows=combined.height)

        return combined

    def _raw_to_df(self, raw: list[dict], coin: str) -> pl.DataFrame:
        """Convert raw funding dicts to Polars DataFrame."""
        now_ms = int(time.time() * 1000)
        rows = []
        for entry in raw:
            ts_ms = int(entry.get("time", 0))
            rate = float(entry.get("rate", 0))
            rows.append({
                "symbol": coin.upper(),
                "timestamp": datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc),
                "rate": rate,
                "funding_rate": rate,
            })

        if not rows:
            return pl.DataFrame(schema=FUNDING_SCHEMA)

        return pl.DataFrame(rows)

    # -- Query --------------------------------------------------------------

    def load_funding(
        self,
        coin: str,
        start: datetime | int | None = None,
    ) -> pl.DataFrame:
        """Load funding from Parquet with optional time range filter."""
        df = self._load_existing(coin.upper())
        if df is None:
            return pl.DataFrame(schema=FUNDING_SCHEMA)

        if start is not None:
            if isinstance(start, int):
                start = datetime.fromtimestamp(start / 1000, tz=timezone.utc)
            df = df.filter(pl.col("timestamp") >= start)

        return df

    # -- Analytics ----------------------------------------------------------

    def compute_funding_metrics(self, coin: str) -> dict[str, float]:
        """Compute derived funding metrics from stored data.

        Returns dict with keys:
            funding_1h, funding_24h_sum, funding_7d_mean, funding_30d_mean,
            funding_z_30d, funding_z_90d, annualized_recent_funding
        """
        df = self._load_existing(coin.upper())
        if df is None or df.height == 0:
            return {k: 0.0 for k in [
                "funding_1h", "funding_24h_sum", "funding_7d_mean",
                "funding_30d_mean", "funding_z_30d", "funding_z_90d",
                "annualized_recent_funding",
            ]}

        now = datetime.now(timezone.utc)

        # Ensure timestamp is a datetime column
        if df["timestamp"].dtype == pl.Utf8:
            df = df.with_columns(pl.col("timestamp").str.to_datetime())

        # funding_1h: most recent rate
        latest = df.sort("timestamp", descending=True).head(1)
        funding_1h = float(latest["rate"][0]) if latest.height > 0 else 0.0

        # Rolling windows
        df = df.with_columns(
            (pl.col("timestamp").cast(pl.Int64) / 1000).alias("_ts_s")
        )

        now_s = now.timestamp()

        # 24h sum: last 24 entries (hourly) or sum of rates where timestamp >= now - 24h
        df_24h = df.filter(pl.col("_ts_s") >= now_s - 86400)
        funding_24h_sum = float(df_24h["rate"].sum()) if df_24h.height > 0 else 0.0

        # 7d mean
        df_7d = df.filter(pl.col("_ts_s") >= now_s - 7 * 86400)
        funding_7d_mean = float(df_7d["rate"].mean()) if df_7d.height > 0 else 0.0

        # 30d mean
        df_30d = df.filter(pl.col("_ts_s") >= now_s - 30 * 86400)
        funding_30d_mean = float(df_30d["rate"].mean()) if df_30d.height > 0 else 0.0

        # 90d stats
        df_90d = df.filter(pl.col("_ts_s") >= now_s - 90 * 86400)
        funding_90d_mean = float(df_90d["rate"].mean()) if df_90d.height > 0 else 0.0
        funding_90d_std = float(df_90d["rate"].std()) if df_90d.height > 1 else 0.0

        # Z-scores: (recent - mean) / std
        funding_z_30d = 0.0
        if df_30d.height > 1:
            std_30d = float(df_30d["rate"].std())
            if std_30d > 1e-12:
                funding_z_30d = (funding_7d_mean - funding_30d_mean) / std_30d

        funding_z_90d = 0.0
        if funding_90d_std > 1e-12:
            funding_z_90d = (funding_7d_mean - funding_90d_mean) / funding_90d_std

        # Annualized: daily rate * 365 (8 funding periods per day on Hyperliquid)
        # Hourly rate * 24 * 365
        annualized_recent_funding = funding_1h * 24 * 365

        return {
            "funding_1h": funding_1h,
            "funding_24h_sum": funding_24h_sum,
            "funding_7d_mean": funding_7d_mean,
            "funding_30d_mean": funding_30d_mean,
            "funding_z_30d": funding_z_30d,
            "funding_z_90d": funding_z_90d,
            "annualized_recent_funding": annualized_recent_funding,
        }
