"""Async WebSocket client for Hyperliquid real-time data streams.

Supports subscriptions to: allMids, bbo, candle, activeAssetCtx.
Auto-reconnects with exponential backoff and sends periodic heartbeats.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Callable, Awaitable

import structlog

logger = structlog.get_logger(__name__)

try:
    import websockets
    from websockets.asyncio.client import ClientConnection
except ImportError:
    websockets = None  # type: ignore[assignment]
    ClientConnection = None  # type: ignore[assignment,misc]


class HyperliquidWS:
    """Async WebSocket client for Hyperliquid real-time data.

    Features:
        - Auto-reconnect with exponential backoff (1s → 2s → 4s → 8s, max 30s)
        - Periodic heartbeat ping every 30s
        - Event-based callback registration
        - Thread-safe subscribe/unsubscribe
    """

    DEFAULT_URL = "wss://api.hyperliquid.xyz/ws"
    HEARTBEAT_INTERVAL = 30.0
    MAX_BACKOFF = 30.0
    INITIAL_BACKOFF = 1.0

    def __init__(self, url: str | None = None) -> None:
        if websockets is None:
            raise ImportError(
                "websockets package is required: pip install websockets"
            )
        self.url = url or self.DEFAULT_URL
        self._callbacks: dict[str, list[Callable[..., Awaitable[None]]]] = {}
        self._running = False
        self._ws: ClientConnection | None = None
        self._recv_task: asyncio.Task | None = None
        self._heartbeat_task: asyncio.Task | None = None
        self._backoff = self.INITIAL_BACKOFF
        self._subscribed: list[dict] = []

    # ── Connection lifecycle ──────────────────────────────────────────────

    async def connect(self) -> None:
        """Connect to the WebSocket with auto-reconnect."""
        self._running = True
        while self._running:
            try:
                logger.info("ws_connecting", url=self.url)
                async with websockets.connect(self.url) as ws:
                    self._ws = ws
                    self._backoff = self.INITIAL_BACKOFF
                    logger.info("ws_connected", url=self.url)

                    # Re-subscribe after reconnect
                    for sub in self._subscribed:
                        await self._send(sub)

                    # Start heartbeat and receive loops
                    self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
                    self._recv_task = asyncio.create_task(self._recv_loop())

                    # Wait until either task finishes (disconnect or error)
                    done, pending = await asyncio.wait(
                        [self._recv_task, self._heartbeat_task],
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                    for task in pending:
                        task.cancel()

            except Exception as exc:
                logger.warning(
                    "ws_disconnected",
                    error=str(exc),
                    backoff=self._backoff,
                )
            finally:
                self._ws = None

            if not self._running:
                break

            # Exponential backoff before reconnect
            logger.info("ws_reconnecting", delay=self._backoff)
            await asyncio.sleep(self._backoff)
            self._backoff = min(self._backoff * 2, self.MAX_BACKOFF)

    async def disconnect(self) -> None:
        """Clean shutdown."""
        self._running = False
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
        for task in [self._recv_task, self._heartbeat_task]:
            if task and not task.done():
                task.cancel()
        logger.info("ws_disconnected_clean")

    # ── Subscription ─────────────────────────────────────────────────────

    async def subscribe(self, subscription: dict) -> None:
        """Subscribe to a channel.

        Args:
            subscription: Dict with at minimum {'type': '<channel>'}.
                Supported channels: 'allMids', 'bbo', 'candle', 'activeAssetCtx'.
                Example: {'type': 'bbo', 'coin': 'BTC'}
        """
        msg = {"method": "subscribe", "subscription": subscription}
        self._subscribed.append(subscription)
        await self._send(msg)
        logger.info("ws_subscribed", subscription=subscription)

    async def unsubscribe(self, subscription: dict) -> None:
        """Unsubscribe from a channel."""
        msg = {"method": "unsubscribe", "subscription": subscription}
        self._subscribed = [
            s for s in self._subscribed if s != subscription
        ]
        await self._send(msg)
        logger.info("ws_unsubscribed", subscription=subscription)

    # ── Callbacks ────────────────────────────────────────────────────────

    async def on(self, event_type: str, callback: Callable[..., Awaitable[None]]) -> None:
        """Register an async callback for an event type.

        Event types:
            - 'allMids': mid price updates
            - 'bbo': best bid/offer updates
            - 'candle': candle updates
            - 'activeAssetCtx': asset context updates
            - 'subscriptionResponse': subscription acknowledgements
            - 'error': error messages
        """
        self._callbacks.setdefault(event_type, []).append(callback)

    async def off(self, event_type: str, callback: Callable[..., Awaitable[None]]) -> None:
        """Remove a callback."""
        if event_type in self._callbacks:
            self._callbacks[event_type] = [
                cb for cb in self._callbacks[event_type] if cb is not callback
            ]

    # ── Internal loops ───────────────────────────────────────────────────

    async def _recv_loop(self) -> None:
        """Receive messages and dispatch to callbacks."""
        assert self._ws is not None
        try:
            async for raw in self._ws:
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8")
                await self._handle_message(raw)
        except websockets.ConnectionClosed as exc:
            logger.info("ws_connection_closed", code=exc.code, reason=exc.reason)
        except asyncio.CancelledError:
            pass

    async def _heartbeat_loop(self) -> None:
        """Send periodic pings to keep the connection alive."""
        try:
            while self._running:
                await asyncio.sleep(self.HEARTBEAT_INTERVAL)
                if self._ws and self._ws.open:
                    await self._ws.ping()
                    logger.debug("ws_heartbeat_sent")
        except asyncio.CancelledError:
            pass

    async def _handle_message(self, raw: str) -> None:
        """Parse a raw WebSocket message and dispatch to callbacks."""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("ws_invalid_json", raw=raw[:200])
            return

        channel = data.get("channel")
        if channel is None:
            # Subscription response or error
            if "error" in data:
                await self._dispatch("error", data)
            elif "channel" in data or "data" in data:
                await self._dispatch("subscriptionResponse", data)
            return

        # Dispatch based on channel type
        await self._dispatch(channel, data)

    async def _dispatch(self, event_type: str, data: dict) -> None:
        """Dispatch data to all registered callbacks for an event type."""
        callbacks = self._callbacks.get(event_type, [])
        for cb in callbacks:
            try:
                await cb(data)
            except Exception as exc:
                logger.error(
                    "ws_callback_error",
                    event_type=event_type,
                    error=str(exc),
                )

    async def _send(self, msg: dict) -> None:
        """Send a JSON message over the WebSocket."""
        if self._ws and self._ws.open:
            await self._ws.send(json.dumps(msg))
        else:
            logger.debug("ws_send_not_connected", msg_type=msg.get("method"))
