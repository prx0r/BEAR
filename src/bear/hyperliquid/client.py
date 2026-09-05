"""Rate-limited HTTP client for Hyperliquid REST API.

The Hyperliquid /info endpoint has a weight-based rate limit:
- max 100 weight per second
- different endpoints have different weights

This module implements a weighted token-bucket rate limiter with
exponential backoff + jitter on 429s, plus a TTL cache to avoid
redundant fetches.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import random
import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

import httpx
import structlog

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------

# Endpoint weights (observed from Hyperliquid docs / community)
ENDPOINT_WEIGHTS: dict[str, int] = {
    "metaAndAssetCtxs": 5,
    "allMids": 1,
    "l2Book": 2,
    "candleSnapshot": 3,
    "fundingHistory": 2,
    "perpDexs": 1,
}


class RateLimiter:
    """Weighted token-bucket rate limiter.

    Refills at `rate` tokens/second, bucket capacity `max_tokens`.
    Each request consumes `weight` tokens for its endpoint type.
    """

    def __init__(self, max_tokens: float = 100.0, rate: float = 100.0) -> None:
        self.max_tokens = max_tokens
        self.rate = rate
        self._tokens = max_tokens
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self.max_tokens, self._tokens + elapsed * self.rate)
        self._last_refill = now

    async def acquire(self, weight: int = 1) -> None:
        """Wait until enough tokens are available, then consume them."""
        while True:
            async with self._lock:
                self._refill()
                if self._tokens >= weight:
                    self._tokens -= weight
                    return
                # Time until enough tokens are available
                wait = (weight - self._tokens) / self.rate
            # Sleep outside the lock so other coroutines can proceed
            await asyncio.sleep(wait)


# ---------------------------------------------------------------------------
# TTL cache entry
# ---------------------------------------------------------------------------

@dataclass
class _CacheEntry:
    data: Any
    expires_at: float


# ---------------------------------------------------------------------------
# HTTP client
# ---------------------------------------------------------------------------

class HyperliquidClient:
    """Async HTTP client for Hyperliquid /info endpoint.

    Features:
        - Weighted token-bucket rate limiting
        - Exponential backoff + jitter on 429s
        - TTL-based response caching
        - Automatic Decimal conversion for numeric strings
    """

    BASE_URL = "https://api.hyperliquid.xyz"
    INFO_PATH = "/info"

    def __init__(
        self,
        *,
        rate_limiter: RateLimiter | None = None,
        default_ttl: float = 30.0,
        max_retries: int = 5,
        base_timeout: float = 15.0,
    ) -> None:
        self.rate_limiter = rate_limiter or RateLimiter()
        self.default_ttl = default_ttl
        self.max_retries = max_retries
        self.base_timeout = base_timeout
        self._cache: dict[str, _CacheEntry] = {}
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                timeout=httpx.Timeout(self.base_timeout),
                headers={"Content-Type": "application/json"},
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # -- internal helpers ---------------------------------------------------

    def _cache_key(self, payload: dict) -> str:
        raw = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    def _get_cache(self, key: str) -> Any | None:
        entry = self._cache.get(key)
        if entry and time.time() < entry.expires_at:
            return entry.data
        if entry:
            del self._cache[key]
        return None

    def _set_cache(self, key: str, data: Any, ttl: float | None = None) -> None:
        ttl = ttl if ttl is not None else self.default_ttl
        self._cache[key] = _CacheEntry(data=data, expires_at=time.time() + ttl)

    @staticmethod
    def _coerce_decimals(obj: Any) -> Any:
        """Recursively convert numeric strings to Decimal."""
        if isinstance(obj, str):
            try:
                return Decimal(obj)
            except Exception:
                return obj
        if isinstance(obj, list):
            return [HyperliquidClient._coerce_decimals(item) for item in obj]
        if isinstance(obj, dict):
            return {k: HyperliquidClient._coerce_decimals(v) for k, v in obj.items()}
        return obj

    async def _post(
        self,
        payload: dict,
        *,
        weight: int = 1,
        ttl: float | None = None,
    ) -> Any:
        """POST to /info with rate limiting, caching, and retries."""
        cache_key = self._cache_key(payload)
        cached = self._get_cache(cache_key)
        if cached is not None:
            logger.debug("cache_hit", payload_type=payload.get("type"))
            return cached

        last_exc: Exception | None = None
        for attempt in range(self.max_retries):
            await self.rate_limiter.acquire(weight)
            client = await self._get_client()

            try:
                resp = await client.post(self.INFO_PATH, json=payload)
            except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                last_exc = exc
                if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 429:
                    # Exponential backoff + jitter
                    delay = min(2 ** attempt, 30) + random.uniform(0, 1)
                    logger.warning(
                        "rate_limited",
                        attempt=attempt,
                        delay=round(delay, 2),
                    )
                    await asyncio.sleep(delay)
                    continue
                # Non-429 errors: backoff but keep trying
                delay = min(2 ** attempt, 10) + random.uniform(0, 0.5)
                await asyncio.sleep(delay)
                continue

            if resp.status_code == 429:
                delay = min(2 ** attempt, 30) + random.uniform(0, 1)
                logger.warning(
                    "rate_limited",
                    attempt=attempt,
                    delay=round(delay, 2),
                )
                await asyncio.sleep(delay)
                continue

            resp.raise_for_status()
            data = resp.json()
            coerced = self._coerce_decimals(data)
            self._set_cache(cache_key, coerced, ttl=ttl)
            return coerced

        raise RuntimeError(
            f"Failed after {self.max_retries} retries: {last_exc}"
        ) from last_exc

    # -- public API methods -------------------------------------------------

    async def get_meta_and_asset_contexts(self) -> tuple[list, list]:
        """Fetch the universe (meta) and per-asset contexts.

        Returns:
            (universe_list, asset_contexts_list) — positional, do not reorder.
        """
        payload = {"type": "metaAndAssetCtxs"}
        data = await self._post(payload, weight=ENDPOINT_WEIGHTS["metaAndAssetCtxs"])
        # data is a 2-element list: [meta_dict, [ctx1, ctx2, ...]]
        meta = data[0]
        asset_contexts = data[1]
        # meta contains 'universe' list and other fields
        universe = meta.get("universe", [])
        return universe, asset_contexts

    async def get_perp_dexs(self) -> list[dict]:
        """Fetch list of builder DEXs."""
        payload = {"type": "perpDexs"}
        data = await self._post(payload, weight=ENDPOINT_WEIGHTS["perpDexs"])
        return data if isinstance(data, list) else data.get("dexs", [])

    async def get_candles(
        self,
        coin: str,
        interval: str,
        start_time: int,
        end_time: int,
    ) -> list[dict]:
        """Fetch candle history for a coin.

        Args:
            coin: e.g. "BTC", "ETH"
            interval: "1h", "4h", "1d"
            start_time: epoch ms
            end_time: epoch ms

        Returns:
            List of candle dicts with keys: t, o, h, l, c, v, n
        """
        payload = {
            "type": "candleSnapshot",
            "req": {
                "coin": coin,
                "interval": interval,
                "startTime": start_time,
                "endTime": end_time,
            },
        }
        data = await self._post(payload, weight=ENDPOINT_WEIGHTS["candleSnapshot"])
        return data if isinstance(data, list) else []

    async def get_funding_history(
        self,
        coin: str,
        start_time: int,
    ) -> list[dict]:
        """Fetch funding history for a coin.

        Args:
            coin: e.g. "BTC"
            start_time: epoch ms

        Returns:
            List of funding entry dicts.
        """
        payload = {
            "type": "fundingHistory",
            "coin": coin,
            "startTime": start_time,
        }
        data = await self._post(payload, weight=ENDPOINT_WEIGHTS["fundingHistory"])
        return data if isinstance(data, list) else []

    async def get_l2_book(self, coin: str) -> dict:
        """Fetch L2 order book snapshot.

        Returns:
            Dict with 'bids' and 'asks' lists, each entry [price, size].
        """
        payload = {
            "type": "l2Book",
            "coin": coin,
        }
        data = await self._post(payload, weight=ENDPOINT_WEIGHTS["l2Book"], ttl=5.0)
        return data

    async def get_all_mids(self) -> dict[str, Decimal]:
        """Fetch mid prices for all coins.

        Returns:
            Dict of coin -> mid price (Decimal).
        """
        payload = {"type": "allMids"}
        data = await self._post(payload, weight=ENDPOINT_WEIGHTS["allMids"], ttl=5.0)
        # data is dict: {"BTC": "67543.21", ...}
        return data

    async def get_asset_context(self, coin: str) -> dict:
        """Get a single asset's context from the meta+contexts endpoint.

        Useful when you only need one coin's data but the endpoint is cached.
        """
        universe, contexts = await self.get_meta_and_asset_contexts()
        for i, asset in enumerate(universe):
            if asset.get("name") == coin:
                return contexts[i] if i < len(contexts) else {}
        return {}
