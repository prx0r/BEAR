"""Order book and liquidity analytics for Hyperliquid perp markets.

Fetches L2 books and computes:
- spread_bps: bid-ask spread in basis points
- ADV_24h: 24h quote volume
- OI_notional: open interest in notional terms
- OI_to_ADV: OI / ADV ratio
- Execution slippage estimates for $1k/$5k/$10k/$25k/$50k
- Depth at 10/25/50 bps from mid
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import polars as pl
import structlog

from bear.hyperliquid.client import HyperliquidClient
from bear.hyperliquid.universe import UniverseSnapshot, AssetInfo

logger = structlog.get_logger(__name__)

# Liquidity buckets in USD notional
SLIPPAGE_SIZES_USD: list[int] = [1_000, 5_000, 10_000, 25_000, 50_000]


@dataclass
class BookSnapshot:
    """L2 book snapshot with computed liquidity metrics."""

    coin: str
    timestamp: int  # epoch ms
    best_bid: Decimal
    best_ask: Decimal
    mid: Decimal
    spread_bps: Decimal

    # From asset context
    adv_24h: Decimal  # dayNtlVlm
    oi_notional: Decimal  # openInterest
    oi_to_adv: Decimal  # ratio

    # Depth at distance from mid (in notional USD)
    depth_10bps: Decimal
    depth_25bps: Decimal
    depth_50bps: Decimal

    # Estimated slippage for each size bucket (buy and sell, in bps)
    buy_slippage_1k: Decimal
    buy_slippage_5k: Decimal
    buy_slippage_10k: Decimal
    buy_slippage_25k: Decimal
    buy_slippage_50k: Decimal
    sell_slippage_1k: Decimal
    sell_slippage_5k: Decimal
    sell_slippage_10k: Decimal
    sell_slippage_25k: Decimal
    sell_slippage_50k: Decimal


def _estimate_slippage(
    levels: list[list],
    notional_usd: float,
    mid: float,
) -> float:
    """Walk the book to estimate average execution price for a given notional.

    Args:
        levels: list of [price_str, size_str] sorted best-first
        notional_usd: target USD notional
        mid: mid price for bps calculation

    Returns:
        Slippage in basis points (positive = worse than mid).
    """
    if not levels or mid <= 0 or notional_usd <= 0:
        return 0.0

    remaining = notional_usd
    total_cost = 0.0
    total_size = 0.0

    for price_str, size_str in levels:
        try:
            price = float(price_str)
            size = float(size_str)
        except (ValueError, TypeError):
            continue

        level_notional = price * size
        if level_notional <= 0:
            continue

        take = min(remaining, level_notional)
        fraction = take / level_notional if level_notional > 0 else 0
        qty = size * fraction

        total_cost += qty * price
        total_size += qty
        remaining -= take

        if remaining <= 0:
            break

    if total_size <= 0:
        return 0.0

    avg_price = total_cost / total_size
    slippage_bps = abs(avg_price - mid) / mid * 10_000
    return slippage_bps


def _depth_at_bps(
    levels: list[list],
    mid: float,
    target_bps: float,
) -> float:
    """Sum the notional depth within `target_bps` of mid price.

    Args:
        levels: list of [price_str, size_str]
        mid: mid price
        target_bps: distance from mid in basis points

    Returns:
        Total notional (USD) within the band.
    """
    if not levels or mid <= 0:
        return 0.0

    threshold = mid * target_bps / 10_000
    total = 0.0

    for price_str, size_str in levels:
        try:
            price = float(price_str)
            size = float(size_str)
        except (ValueError, TypeError):
            continue

        if abs(price - mid) <= threshold:
            total += price * size

    return total


class BookManager:
    """Fetches L2 books and computes liquidity metrics for all coins."""

    def __init__(self, client: HyperliquidClient) -> None:
        self.client = client

    async def snapshot_book(
        self,
        coin: str,
        asset: AssetInfo | None = None,
    ) -> BookSnapshot:
        """Fetch L2 book and compute all liquidity metrics.

        Args:
            coin: e.g. "BTC"
            asset: optional AssetInfo for OI/ADV context
        """
        raw = await self.client.get_l2_book(coin)

        bids = raw.get("bids", [])
        asks = raw.get("asks", [])

        # Best bid/ask
        best_bid = Decimal("0")
        best_ask = Decimal("0")
        if bids:
            best_bid = Decimal(str(bids[0][0]))
        if asks:
            best_ask = Decimal(str(asks[0][0]))

        mid = (best_bid + best_ask) / 2 if (best_bid and best_ask) else Decimal("0")
        spread_bps = ((best_ask - best_bid) / mid * 10000) if mid > 0 else Decimal("0")

        # Context data
        adv_24h = Decimal("0")
        oi_notional = Decimal("0")
        if asset:
            adv_24h = asset.day_ntl_vlm
            oi_notional = asset.open_interest

        oi_to_adv = (oi_notional / adv_24h) if adv_24h > 0 else Decimal("0")

        mid_f = float(mid)

        # Depth at bps
        depth_10 = _depth_at_bps(bids + asks, mid_f, 10)
        depth_25 = _depth_at_bps(bids + asks, mid_f, 25)
        depth_50 = _depth_at_bps(bids + asks, mid_f, 50)

        # Slippage estimates
        buy_slippages = []
        sell_slippages = []
        for size_usd in SLIPPAGE_SIZES_USD:
            buy_slippages.append(_estimate_slippage(asks, size_usd, mid_f))
            sell_slippages.append(_estimate_slippage(bids, size_usd, mid_f))

        now_ms = int(time.time() * 1000)

        return BookSnapshot(
            coin=coin,
            timestamp=now_ms,
            best_bid=best_bid,
            best_ask=best_ask,
            mid=mid,
            spread_bps=spread_bps,
            adv_24h=adv_24h,
            oi_notional=oi_notional,
            oi_to_adv=oi_to_adv,
            depth_10bps=Decimal(str(round(depth_10, 2))),
            depth_25bps=Decimal(str(round(depth_25, 2))),
            depth_50bps=Decimal(str(round(depth_50, 2))),
            buy_slippage_1k=Decimal(str(round(buy_slippages[0], 2))),
            buy_slippage_5k=Decimal(str(round(buy_slippages[1], 2))),
            buy_slippage_10k=Decimal(str(round(buy_slippages[2], 2))),
            buy_slippage_25k=Decimal(str(round(buy_slippages[3], 2))),
            buy_slippage_50k=Decimal(str(round(buy_slippages[4], 2))),
            sell_slippage_1k=Decimal(str(round(sell_slippages[0], 2))),
            sell_slippage_5k=Decimal(str(round(sell_slippages[1], 2))),
            sell_slippage_10k=Decimal(str(round(sell_slippages[2], 2))),
            sell_slippage_25k=Decimal(str(round(sell_slippages[3], 2))),
            sell_slippage_50k=Decimal(str(round(sell_slippages[4], 2))),
        )

    async def snapshot_all(
        self,
        universe: UniverseSnapshot,
        *,
        active_only: bool = True,
    ) -> list[BookSnapshot]:
        """Snapshot all coins in the universe.

        Rate-limited: each book request costs 2 weight.
        """
        assets = universe.active_assets if active_only else universe.assets
        results: list[BookSnapshot] = []

        for asset in assets:
            try:
                snap = await self.snapshot_book(asset.name, asset=asset)
                results.append(snap)
            except Exception as exc:
                logger.warning("book_snapshot_error", coin=asset.name, error=str(exc))

        logger.info("book_snapshots_complete", count=len(results))
        return results

    def to_dataframe(self, snapshots: list[BookSnapshot]) -> pl.DataFrame:
        """Convert BookSnapshot list to a Polars DataFrame."""
        if not snapshots:
            return pl.DataFrame()

        rows = []
        for s in snapshots:
            rows.append({
                "coin": s.coin,
                "timestamp": s.timestamp,
                "best_bid": float(s.best_bid),
                "best_ask": float(s.best_ask),
                "mid": float(s.mid),
                "spread_bps": float(s.spread_bps),
                "adv_24h": float(s.adv_24h),
                "oi_notional": float(s.oi_notional),
                "oi_to_adv": float(s.oi_to_adv),
                "depth_10bps": float(s.depth_10bps),
                "depth_25bps": float(s.depth_25bps),
                "depth_50bps": float(s.depth_50bps),
                "buy_slippage_1k": float(s.buy_slippage_1k),
                "buy_slippage_5k": float(s.buy_slippage_5k),
                "buy_slippage_10k": float(s.buy_slippage_10k),
                "buy_slippage_25k": float(s.buy_slippage_25k),
                "buy_slippage_50k": float(s.buy_slippage_50k),
                "sell_slippage_1k": float(s.sell_slippage_1k),
                "sell_slippage_5k": float(s.sell_slippage_5k),
                "sell_slippage_10k": float(s.sell_slippage_10k),
                "sell_slippage_25k": float(s.sell_slippage_25k),
                "sell_slippage_50k": float(s.sell_slippage_50k),
            })

        return pl.DataFrame(rows)
