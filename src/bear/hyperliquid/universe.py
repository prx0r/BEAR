"""Universe management for Hyperliquid perp markets.

Fetches meta + asset contexts, builds canonical market IDs, and maintains
a taxonomy of asset categories.
"""

from __future__ import annotations

import structlog
from decimal import Decimal
from dataclasses import dataclass, field
from typing import Any

from bear.hyperliquid.client import HyperliquidClient

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Default taxonomy
# ---------------------------------------------------------------------------

DEFAULT_TAXONOMY: dict[str, list[str]] = {
    "bitcoin": ["btc"],
    "ethereum": ["eth", "steth", "weth", "reth", "mkr"],
    "l1": [
        "sol", "avax", "near", "apt", "sui", "sei", "trx", "hbar",
        "ftm", "celo", "ron", "kas", "tia", "mnt", "ondo",
    ],
    "l2": ["arb", "op", "strk", "metis", "zro", "base"],
    "defi": [
        "aave", "uni", "link", "crv", "comp", "sushi", "dydx",
        "pendle", "jup", "ray", "kamino", "drift",
    ],
    "dex": ["jto", "jup", "ray", "drift", "kamino", "w"],
    "ai": ["render", "fet", "ocean", "arkm", "virtual", "ai16z", "spec"],
    "bittensor": ["tao"],
    "meme": [
        "doge", "shib", "pepe", "floki", "bonk", "wif", "brett",
        "bome", "mew", "popcat", "mog", "neiro", "trump",
    ],
    "gaming": ["ron", "pixel", "pixels", "illuvium", "imx", "enj"],
    "privacy": ["xmr", "zec", "dcr"],
    "exchange": ["bnb", "okb", "cbbtc"],
    "oracle": ["link", "band", "api3", "trb"],
    "rwa": ["ondo", "polyx", "cfg", "mnt"],
    "storage": ["fil", "ar", "storj", "blz"],
    "index": ["defi", "meme", "ai"],
    "commodity": ["xau", "xag", "oil"],
    "forex": ["eur", "gbp", "jpy", "chf"],
    "stock": ["tsla", "nvda", "aapl", "amzn", "meta", "goog", "msft", "gme"],
}


def _categorise(name: str, taxonomy: dict[str, list[str]] | None = None) -> str:
    """Return the first category match for a coin name, or 'other'."""
    tax = taxonomy or DEFAULT_TAXONOMY
    name_lower = name.lower()
    for category, coins in tax.items():
        if name_lower in coins:
            return category
    return "other"


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------

@dataclass
class AssetInfo:
    """Static + dynamic info for a single perp asset."""

    name: str
    market_id: str  # e.g. "core:TAO"
    sz_decimals: int
    max_leverage: int
    only_isolated: bool
    is_delisted: bool
    margin_table_id: int
    category: str

    # Dynamic (from asset context)
    mark_px: Decimal = field(default_factory=lambda: Decimal("0"))
    mid_px: Decimal = field(default_factory=lambda: Decimal("0"))
    oracle_px: Decimal = field(default_factory=lambda: Decimal("0"))
    prev_day_px: Decimal = field(default_factory=lambda: Decimal("0"))
    funding: Decimal = field(default_factory=lambda: Decimal("0"))
    premium: Decimal = field(default_factory=lambda: Decimal("0"))
    open_interest: Decimal = field(default_factory=lambda: Decimal("0"))
    day_ntl_vlm: Decimal = field(default_factory=lambda: Decimal("0"))
    impact_bid: Decimal = field(default_factory=lambda: Decimal("0"))
    impact_ask: Decimal = field(default_factory=lambda: Decimal("0"))


@dataclass
class UniverseSnapshot:
    """Point-in-time snapshot of the full Hyperliquid perp universe."""

    timestamp: int  # epoch ms
    assets: list[AssetInfo]
    asset_map: dict[str, AssetInfo]  # name -> AssetInfo
    market_id_map: dict[str, AssetInfo]  # market_id -> AssetInfo

    @property
    def active_assets(self) -> list[AssetInfo]:
        return [a for a in self.assets if not a.is_delisted]

    def by_category(self, category: str) -> list[AssetInfo]:
        return [a for a in self.active_assets if a.category == category]

    def by_name(self, name: str) -> AssetInfo | None:
        return self.asset_map.get(name.upper())

    def by_market_id(self, market_id: str) -> AssetInfo | None:
        return self.market_id_map.get(market_id)


# ---------------------------------------------------------------------------
# Universe manager
# ---------------------------------------------------------------------------

class UniverseManager:
    """Fetches and maintains the Hyperliquid perp universe.

    Builds canonical market IDs of the form ``DEX:COIN`` (e.g. ``core:TAO``).
    Both the meta universe array and the asset contexts array are accessed
    positionally — never reordered.
    """

    def __init__(
        self,
        client: HyperliquidClient,
        *,
        taxonomy: dict[str, list[str]] | None = None,
        dex_override: str | None = None,
    ) -> None:
        self.client = client
        self.taxonomy = taxonomy or DEFAULT_TAXONOMY
        self.dex_override = dex_override
        self._snapshot: UniverseSnapshot | None = None

    async def refresh(self) -> UniverseSnapshot:
        """Fetch fresh meta+contexts and build a UniverseSnapshot."""
        universe_list, asset_contexts = await self.client.get_meta_and_asset_contexts()

        # The meta object may have a 'dex' field or we use override
        # universe_list items have keys like: name, szDecimals, maxLeverage,
        # onlyIsolated, isDelisted, marginTableId, etc.
        # asset_contexts items have: markPx, midPx, oraclePx, funding,
        # premium, openInterest, dayNtlVlm, impactPxs, etc.

        assets: list[AssetInfo] = []
        asset_map: dict[str, AssetInfo] = {}
        market_id_map: dict[str, AssetInfo] = {}

        now_ms = int(__import__("time").time() * 1000)

        for i, meta_item in enumerate(universe_list):
            name = meta_item.get("name", "")
            if not name:
                continue

            ctx = asset_contexts[i] if i < len(asset_contexts) else {}

            # Determine DEX prefix
            dex = self.dex_override or meta_item.get("dex", "core")

            # Build canonical market_id
            market_id = f"{dex}:{name.upper()}"

            # Parse all numeric strings to Decimal
            def _d(val: Any, default: str = "0") -> Decimal:
                if val is None or val == "":
                    return Decimal(default)
                try:
                    return Decimal(str(val))
                except Exception:
                    return Decimal(default)

            impact_pxs = ctx.get("impactPxs") or [0, 0]

            asset = AssetInfo(
                name=name.upper(),
                market_id=market_id,
                sz_decimals=int(meta_item.get("szDecimals", 0)),
                max_leverage=int(meta_item.get("maxLeverage", 1)),
                only_isolated=bool(meta_item.get("onlyIsolated", False)),
                is_delisted=bool(meta_item.get("isDelisted", False)),
                margin_table_id=int(meta_item.get("marginTableId", 0)),
                category=_categorise(name, self.taxonomy),
                mark_px=_d(ctx.get("markPx")),
                mid_px=_d(ctx.get("midPx")),
                oracle_px=_d(ctx.get("oraclePx")),
                prev_day_px=_d(ctx.get("prevDayPx")),
                funding=_d(ctx.get("funding")),
                premium=_d(ctx.get("premium")),
                open_interest=_d(ctx.get("openInterest")),
                day_ntl_vlm=_d(ctx.get("dayNtlVlm")),
                impact_bid=_d(impact_pxs[0]) if len(impact_pxs) > 0 else Decimal("0"),
                impact_ask=_d(impact_pxs[1]) if len(impact_pxs) > 1 else Decimal("0"),
            )

            assets.append(asset)
            asset_map[asset.name] = asset
            market_id_map[asset.market_id] = asset

        self._snapshot = UniverseSnapshot(
            timestamp=now_ms,
            assets=assets,
            asset_map=asset_map,
            market_id_map=market_id_map,
        )

        logger.info(
            "universe_refreshed",
            total=len(assets),
            active=len([a for a in assets if not a.is_delisted]),
        )

        return self._snapshot

    @property
    def snapshot(self) -> UniverseSnapshot | None:
        return self._snapshot

    async def get_or_refresh(self) -> UniverseSnapshot:
        """Return cached snapshot or fetch fresh one."""
        if self._snapshot is None:
            return await self.refresh()
        return self._snapshot

    def to_market_rows(self) -> list[dict]:
        """Convert current snapshot to list of dicts suitable for DataStore."""
        if not self._snapshot:
            return []
        rows = []
        for a in self._snapshot.assets:
            rows.append({
                "symbol": a.market_id,
                "name": a.name,
                "dex": a.market_id.split(":")[0] if ":" in a.market_id else "core",
                "sz_decimals": a.sz_decimals,
                "max_leverage": a.max_leverage,
                "is_delisted": a.is_delisted,
                "margin_table_id": a.margin_table_id,
                "category": a.category,
            })
        return rows
