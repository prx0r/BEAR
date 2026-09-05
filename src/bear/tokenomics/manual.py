"""Manual CSV/JSON tokenomics import."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import polars as pl

from bear.tokenomics.base import (
    TokenSnapshot,
    TokenomicsProvider,
    UnlockEvent,
)

logger = logging.getLogger(__name__)

# All tokenomics fields (nullable)
TOKENOMICS_FIELDS = [
    "timestamp", "symbol",
    "market_cap", "fdv",
    "circulating_supply", "total_supply", "max_supply",
    "supply_change_7d", "supply_change_30d", "supply_change_90d",
    "next_unlock_time", "next_unlock_tokens", "next_unlock_usd",
    "unlock_pct_float", "annual_emission_pct",
    "protocol_fees", "protocol_revenue", "buybacks", "burns",
    "known_at", "effective_at",
]


def load_tokenomics_from_csv(path: str | Path) -> pl.DataFrame:
    """Load tokenomics data from CSV.

    Required columns: timestamp, symbol.
    All other fields are optional/nullable.

    Args:
        path: Path to CSV file.

    Returns:
        Polars DataFrame with tokenomics data.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Tokenomics CSV not found: {path}")

    df = pl.read_csv(path, null_values=["", "null", "None", "NA", "N/A"])

    # Ensure required columns
    required = {"timestamp", "symbol"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Cast timestamp
    df = df.with_columns(pl.col("timestamp").cast(pl.Utf8))

    # Fill missing columns with nulls
    for field in TOKENOMICS_FIELDS:
        if field not in df.columns:
            df = df.with_columns(pl.lit(None).alias(field))

    # Validate no lookahead: known_at <= timestamp
    if "known_at" in df.columns:
        invalid = df.filter(
            (pl.col("known_at").is_not_null()) &
            (pl.col("timestamp").is_not_null()) &
            (pl.col("known_at") > pl.col("timestamp"))
        )
        if invalid.height > 0:
            logger.warning(
                "Found %d rows where known_at > timestamp (possible lookahead)",
                invalid.height,
            )

    logger.info("Loaded %d tokenomics records from %s", df.height, path)
    return df


def load_tokenomics_from_json(path: str | Path) -> pl.DataFrame:
    """Load tokenomics data from JSON (array of objects).

    Args:
        path: Path to JSON file.

    Returns:
        Polars DataFrame with tokenomics data.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Tokenomics JSON not found: {path}")

    with open(path) as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("JSON must be an array of objects")

    df = pl.DataFrame(data)

    # Ensure required columns
    required = {"timestamp", "symbol"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df = df.with_columns(pl.col("timestamp").cast(pl.Utf8))

    for field in TOKENOMICS_FIELDS:
        if field not in df.columns:
            df = df.with_columns(pl.lit(None).alias(field))

    logger.info("Loaded %d tokenomics records from %s", df.height, path)
    return df


class ManualTokenomicsProvider(TokenomicsProvider):
    """Tokenomics provider backed by CSV/JSON files."""

    def __init__(self, data: pl.DataFrame):
        """Initialize with tokenomics DataFrame.

        Args:
            data: DataFrame with columns from TOKENOMICS_FIELDS.
        """
        self._data = data
        self._snapshots: Dict[str, List[TokenSnapshot]] = {}
        self._build_index()

    def _build_index(self) -> None:
        """Build per-symbol sorted index for point-in-time lookup."""
        for row in self._data.iter_rows(named=True):
            symbol = row["symbol"]
            if symbol not in self._snapshots:
                self._snapshots[symbol] = []
            self._snapshots[symbol].append(
                TokenSnapshot(
                    timestamp=row.get("timestamp", ""),
                    symbol=symbol,
                    market_cap=row.get("market_cap"),
                    fdv=row.get("fdv"),
                    circulating_supply=row.get("circulating_supply"),
                    total_supply=row.get("total_supply"),
                    max_supply=row.get("max_supply"),
                    supply_change_7d=row.get("supply_change_7d"),
                    supply_change_30d=row.get("supply_change_30d"),
                    supply_change_90d=row.get("supply_change_90d"),
                    next_unlock_time=row.get("next_unlock_time"),
                    next_unlock_tokens=row.get("next_unlock_tokens"),
                    next_unlock_usd=row.get("next_unlock_usd"),
                    unlock_pct_float=row.get("unlock_pct_float"),
                    annual_emission_pct=row.get("annual_emission_pct"),
                    protocol_fees=row.get("protocol_fees"),
                    protocol_revenue=row.get("protocol_revenue"),
                    buybacks=row.get("buybacks"),
                    burns=row.get("burns"),
                    known_at=row.get("known_at"),
                    effective_at=row.get("effective_at"),
                )
            )

        # Sort each symbol's snapshots by timestamp
        for symbol in self._snapshots:
            self._snapshots[symbol].sort(key=lambda s: s.timestamp)

    def get_snapshot(self, symbol: str, timestamp: str) -> Optional[TokenSnapshot]:
        """Get point-in-time snapshot (most recent known_at <= timestamp)."""
        if symbol not in self._snapshots:
            return None

        snapshots = self._snapshots[symbol]
        best = None
        for snap in snapshots:
            # Use known_at for point-in-time enforcement
            check_time = snap.known_at or snap.timestamp
            if check_time <= timestamp:
                best = snap
            else:
                break

        return best

    def get_unlocks(self, symbol: str, start: str, end: str) -> List[UnlockEvent]:
        """Extract unlock events from tokenomics data."""
        if symbol not in self._snapshots:
            return []

        events = []
        for snap in self._snapshots[symbol]:
            if snap.next_unlock_time and start <= snap.next_unlock_time <= end:
                events.append(UnlockEvent(
                    timestamp=snap.timestamp,
                    symbol=symbol,
                    unlock_time=snap.next_unlock_time,
                    tokens=snap.next_unlock_tokens or 0.0,
                    usd_value=snap.next_unlock_usd,
                    pct_of_supply=snap.unlock_pct_float,
                ))

        return sorted(events, key=lambda e: e.unlock_time)

    def has_data(self, symbol: str) -> bool:
        return symbol in self._snapshots

    def symbols(self) -> List[str]:
        return sorted(self._snapshots.keys())

    @classmethod
    def from_csv(cls, path: str | Path) -> ManualTokenomicsProvider:
        """Create provider from CSV file."""
        data = load_tokenomics_from_csv(path)
        return cls(data)

    @classmethod
    def from_json(cls, path: str | Path) -> ManualTokenomicsProvider:
        """Create provider from JSON file."""
        data = load_tokenomics_from_json(path)
        return cls(data)
