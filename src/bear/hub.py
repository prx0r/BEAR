"""BEAR Hub — Central data orchestrator for Hyperliquid.

Owns all data components, manages async lifecycles, provides an event bus,
health tracking, and a staleness watchdog. Single entry point that wires
everything together.

Usage:
    hub = BearHub()
    await hub.start()
    ...
    state = await hub.snapshot()
    await hub.stop()
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable

import structlog

from bear.hyperliquid.books import BookManager
from bear.hyperliquid.candles import CandleManager
from bear.hyperliquid.client import HyperliquidClient
from bear.hyperliquid.funding import FundingManager
from bear.hyperliquid.universe import UniverseManager
from bear.hyperliquid.websocket import HyperliquidWS

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Health status enum
# ---------------------------------------------------------------------------

CONNECTED = "connected"
STALE = "stale"
OFFLINE = "offline"
ERROR = "error"


@dataclass
class ComponentHealth:
    """Health state for a single data component."""
    name: str
    status: str = OFFLINE
    last_update: float = 0.0
    error: str | None = None
    reconnect_count: int = 0


@dataclass
class HubStatus:
    """Aggregate status of every component."""
    started_at: float = 0.0
    uptime_seconds: float = 0.0

    universe: ComponentHealth = field(default_factory=lambda: ComponentHealth("universe"))
    candles: ComponentHealth = field(default_factory=lambda: ComponentHealth("candles"))
    funding: ComponentHealth = field(default_factory=lambda: ComponentHealth("funding"))
    books: ComponentHealth = field(default_factory=lambda: ComponentHealth("books"))
    ws: ComponentHealth = field(default_factory=lambda: ComponentHealth("websocket"))

    # Event counters
    events_new_candle: int = 0
    events_new_funding: int = 0
    events_universe_update: int = 0
    events_price_update: int = 0

    @property
    def all_connected(self) -> bool:
        return all(
            h.status == CONNECTED
            for h in [self.universe, self.candles, self.funding, self.books, self.ws]
        )

    @property
    def degraded(self) -> bool:
        return not self.all_connected and any(
            h.status == CONNECTED
            for h in [self.universe, self.candles, self.funding, self.books, self.ws]
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "started_at": self.started_at,
            "uptime_seconds": round(self.uptime_seconds, 1),
            "all_connected": self.all_connected,
            "degraded": self.degraded,
            "components": {
                h.name: {"status": h.status, "error": h.error}
                for h in [self.universe, self.candles, self.funding, self.books, self.ws]
            },
            "events": {
                "new_candle": self.events_new_candle,
                "new_funding": self.events_new_funding,
                "universe_update": self.events_universe_update,
                "price_update": self.events_price_update,
            },
        }


# ---------------------------------------------------------------------------
# Event bus
# ---------------------------------------------------------------------------

_EVENT_TYPES = frozenset({"new_candle", "new_funding", "universe_update", "price_update"})


class EventBus:
    """Lightweight typed event bus for hub events."""

    def __init__(self) -> None:
        self._subs: dict[str, list[Callable[..., Any]]] = {}

    def on(self, event_type: str, callback: Callable[..., Any]) -> None:
        if event_type not in _EVENT_TYPES:
            raise ValueError(f"Unknown event type: {event_type}")
        self._subs.setdefault(event_type, []).append(callback)

    def off(self, event_type: str, callback: Callable[..., Any]) -> None:
        if event_type in self._subs:
            self._subs[event_type] = [cb for cb in self._subs[event_type] if cb is not callback]

    async def emit(self, event_type: str, *args: Any, **kwargs: Any) -> None:
        for cb in self._subs.get(event_type, []):
            try:
                result = cb(*args, **kwargs)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                logger.exception("event_callback_error", event_type=event_type)


# ---------------------------------------------------------------------------
# Hub
# ---------------------------------------------------------------------------

class BearHub:
    """Central orchestrator for all BEAR data components.

    Owns the Hyperliquid client, WebSocket, and all managers. Provides
    start/stop lifecycle, event bus, health tracking, and staleness watchdog.
    """

    def __init__(
        self,
        *,
        stale_timeout: float = 60.0,
        refresh_interval: float = 30.0,
        watchdog_interval: float = 5.0,
    ) -> None:
        self.stale_timeout = stale_timeout
        self.refresh_interval = refresh_interval
        self.watchdog_interval = watchdog_interval

        # Core client
        self.client = HyperliquidClient()
        self.ws = HyperliquidWS()

        # Data managers
        self.universe_mgr = UniverseManager(self.client)
        self.candle_mgr = CandleManager(self.client)
        self.funding_mgr = FundingManager(self.client)
        self.book_mgr = BookManager(self.client)

        # State
        self.status = HubStatus()
        self.events = EventBus()
        self._running = False
        self._tasks: list[asyncio.Task] = []

    # ── Lifecycle ──────────────────────────────────────────────────────

    async def start(self) -> None:
        """Start all components and background loops."""
        if self._running:
            return
        self._running = True
        self.status.started_at = time.time()

        logger.info("hub_starting")

        # 1) Initial universe fetch (required — we can't run without it)
        try:
            await self.universe_mgr.refresh()
            self.status.universe.status = CONNECTED
            self.status.universe.last_update = time.time()
        except Exception as exc:
            self.status.universe.status = ERROR
            self.status.universe.error = str(exc)
            logger.exception("hub_universe_start_failed")

        # 2) Connect WebSocket
        self._tasks.append(asyncio.create_task(self._ws_connect_loop(), name="ws-connect"))

        # 3) Background loops
        self._tasks.append(asyncio.create_task(
            self._universe_refresh_loop(), name="universe-refresh"
        ))
        self._tasks.append(asyncio.create_task(
            self._watchdog_loop(), name="watchdog"
        ))

        logger.info(
            "hub_started",
            universe=self.status.universe.status,
        )

    async def stop(self) -> None:
        """Graceful shutdown of all components."""
        self._running = False

        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

        try:
            await self.ws.disconnect()
        except Exception:
            pass
        try:
            await self.client.close()
        except Exception:
            pass

        self.status.ws.status = OFFLINE
        logger.info("hub_stopped")

    # ── Snapshot ───────────────────────────────────────────────────────

    async def snapshot(self) -> dict[str, Any]:
        """Return current state of all components."""
        self.status.uptime_seconds = time.time() - self.status.started_at

        snap: dict[str, Any] = self.status.as_dict()

        # Universe summary
        univ = self.universe_mgr.snapshot
        if univ:
            snap["universe"] = {
                "total_assets": len(univ.assets),
                "active_assets": len(univ.active_assets),
                "timestamp": univ.timestamp,
            }

        return snap

    # ── WebSocket connect loop ─────────────────────────────────────────

    async def _ws_connect_loop(self) -> None:
        """Run WebSocket with auto-reconnect."""
        try:
            await self.ws.connect()
        except asyncio.CancelledError:
            pass
        except Exception:
            self.status.ws.status = ERROR
            self.status.ws.error = "connect loop exited"
            logger.exception("ws_connect_loop_failed")

    # ── Universe refresh loop ──────────────────────────────────────────

    async def _universe_refresh_loop(self) -> None:
        """Periodically refresh universe and asset contexts."""
        while self._running:
            try:
                snapshot = await self.universe_mgr.refresh()
                self.status.universe.status = CONNECTED
                self.status.universe.last_update = time.time()
                self.status.universe.error = None

                # Emit universe_update for each active asset
                for asset in snapshot.active_assets:
                    await self.events.emit("universe_update", asset)
                    self.status.events_universe_update += 1

            except asyncio.CancelledError:
                break
            except Exception as exc:
                self.status.universe.status = ERROR
                self.status.universe.error = str(exc)
                logger.exception("universe_refresh_error")

            await asyncio.sleep(self.refresh_interval)

    # ── Staleness watchdog ─────────────────────────────────────────────

    async def _watchdog_loop(self) -> None:
        """Check component freshness and attempt reconnects on staleness."""
        while self._running:
            try:
                now = time.time()
                self._check_staleness(now)

            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("watchdog_error")

            await asyncio.sleep(self.watchdog_interval)

    def _check_staleness(self, now: float) -> None:
        """Mark stale components and trigger reconnects."""
        for health in [self.status.universe, self.status.candles, self.status.funding, self.status.books]:
            if health.status == CONNECTED and health.last_update > 0:
                age = now - health.last_update
                if age > self.stale_timeout:
                    health.status = STALE
                    logger.warning(
                        "component_stale",
                        component=health.name,
                        age_seconds=round(age, 1),
                    )

        # WebSocket staleness check
        if self.status.ws.status == CONNECTED and self.status.ws.last_update > 0:
            ws_age = now - self.status.ws.last_update
            if ws_age > self.stale_timeout * 2:
                self.status.ws.status = STALE
                self.status.ws.reconnect_count += 1
                logger.warning(
                    "ws_stale_forcing_reconnect",
                    age_seconds=round(ws_age, 1),
                    reconnect_count=self.status.ws.reconnect_count,
                )

    # ── Internal event dispatchers ─────────────────────────────────────

    async def dispatch_new_candle(self, coin: str, interval: str, candle: dict) -> None:
        """Dispatch a new candle event."""
        self.status.candles.last_update = time.time()
        self.status.candles.status = CONNECTED
        self.status.events_new_candle += 1
        await self.events.emit("new_candle", coin, interval, candle)

    async def dispatch_new_funding(self, coin: str, entry: dict) -> None:
        """Dispatch a new funding event."""
        self.status.funding.last_update = time.time()
        self.status.funding.status = CONNECTED
        self.status.events_new_funding += 1
        await self.events.emit("new_funding", coin, entry)

    async def dispatch_price_update(self, mids: dict[str, Any]) -> None:
        """Dispatch a mid-price update."""
        self.status.ws.last_update = time.time()
        self.status.ws.status = CONNECTED
        self.status.events_price_update += 1
        await self.events.emit("price_update", mids)

    async def dispatch_book_update(self, coin: str, book: dict) -> None:
        """Dispatch an L2 book update."""
        self.status.books.last_update = time.time()
        self.status.books.status = CONNECTED
