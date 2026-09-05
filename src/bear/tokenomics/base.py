"""Tokenomics provider abstraction (Section 10-14)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import polars as pl


@dataclass
class TokenSnapshot:
    """Point-in-time tokenomics snapshot."""

    timestamp: str
    symbol: str

    # Valuation
    market_cap: Optional[float] = None
    fdv: Optional[float] = None

    # Supply
    circulating_supply: Optional[float] = None
    total_supply: Optional[float] = None
    max_supply: Optional[float] = None

    # Supply changes
    supply_change_7d: Optional[float] = None
    supply_change_30d: Optional[float] = None
    supply_change_90d: Optional[float] = None

    # Unlocks
    next_unlock_time: Optional[str] = None
    next_unlock_tokens: Optional[float] = None
    next_unlock_usd: Optional[float] = None
    unlock_pct_float: Optional[float] = None

    # Emission
    annual_emission_pct: Optional[float] = None

    # Cash flows
    protocol_fees: Optional[float] = None
    protocol_revenue: Optional[float] = None
    buybacks: Optional[float] = None
    burns: Optional[float] = None

    # Meta
    known_at: Optional[str] = None
    effective_at: Optional[str] = None


@dataclass
class UnlockEvent:
    """Token unlock event."""

    timestamp: str
    symbol: str
    unlock_time: str
    tokens: float
    usd_value: Optional[float] = None
    pct_of_supply: Optional[float] = None
    cliff: bool = False
    vesting: bool = False


class TokenomicsProvider(ABC):
    """Abstract base for tokenomics data providers."""

    @abstractmethod
    def get_snapshot(
        self,
        symbol: str,
        timestamp: str,
    ) -> Optional[TokenSnapshot]:
        """Get point-in-time tokenomics snapshot.

        Args:
            symbol: Token symbol.
            timestamp: Point-in-time (ISO format).

        Returns:
            TokenSnapshot if available, None otherwise.
        """

    @abstractmethod
    def get_unlocks(
        self,
        symbol: str,
        start: str,
        end: str,
    ) -> List[UnlockEvent]:
        """Get unlock events in a date range.

        Args:
            symbol: Token symbol.
            start: Start date (ISO format).
            end: End date (ISO format).

        Returns:
            List of UnlockEvent sorted by time.
        """

    @abstractmethod
    def has_data(self, symbol: str) -> bool:
        """Check if provider has data for this symbol."""

    @abstractmethod
    def symbols(self) -> List[str]:
        """List all symbols with available data."""


class CompositeTokenomicsProvider(TokenomicsProvider):
    """Falls through multiple providers in order."""

    def __init__(self, providers: List[TokenomicsProvider]):
        self._providers = providers

    def get_snapshot(self, symbol: str, timestamp: str) -> Optional[TokenSnapshot]:
        for provider in self._providers:
            snapshot = provider.get_snapshot(symbol, timestamp)
            if snapshot is not None:
                return snapshot
        return None

    def get_unlocks(self, symbol: str, start: str, end: str) -> List[UnlockEvent]:
        for provider in self._providers:
            unlocks = provider.get_unlocks(symbol, start, end)
            if unlocks:
                return unlocks
        return []

    def has_data(self, symbol: str) -> bool:
        return any(p.has_data(symbol) for p in self._providers)

    def symbols(self) -> List[str]:
        all_symbols: set = set()
        for p in self._providers:
            all_symbols.update(p.symbols())
        return sorted(all_symbols)
