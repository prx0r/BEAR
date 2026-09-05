"""Hyperliquid API response models and parsing.

Provides typed dataclasses for parsing Hyperliquid /info responses and
converting raw JSON into structured Python objects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AssetMeta:
    """Metadata for a single Hyperliquid perp asset."""

    name: str
    sz_decimals: int = 0
    max_leverage: int = 0
    only_isolated: bool = False
    is_delisted: bool = False
    margin_table_id: int = 0


@dataclass
class AssetContext:
    """Live market context for a single asset."""

    mark_px: float = 0.0
    mid_px: float = 0.0
    oracle_px: float = 0.0
    prev_day_px: float = 0.0
    funding: float = 0.0
    premium: float = 0.0
    open_interest: float = 0.0
    day_ntl_vlm: float = 0.0
    impact_pxs: list[float] = field(default_factory=list)


@dataclass
class ParsedUniverse:
    """Parsed result from metaAndAssetCtxs response."""

    assets: list[AssetMeta]
    contexts: list[AssetContext]
    timestamp: str = ""

    @property
    def active_assets(self) -> list[AssetMeta]:
        """Return non-delisted assets."""
        return [a for a in self.assets if not a.is_delisted]

    def get_context(self, name: str) -> AssetContext | None:
        """Get context by asset name."""
        for meta, ctx in zip(self.assets, self.contexts):
            if meta.name == name:
                return ctx
        return None


def parse_meta_and_contexts(raw: list[list[Any]]) -> ParsedUniverse:
    """Parse the metaAndAssetCtxs response.

    The response is [meta_array, asset_ctx_array] where both arrays are
    positionally aligned. We parse numeric strings into floats immediately.

    Args:
        raw: Raw response from {"type": "metaAndAssetCtxs"}.

    Returns:
        ParsedUniverse with typed dataclasses.

    Raises:
        ValueError: If raw structure is invalid.
    """
    if not isinstance(raw, list) or len(raw) < 2:
        raise ValueError(f"Expected [meta, contexts] list, got {type(raw)} with len={len(raw) if isinstance(raw, list) else '?'}")

    meta_raw = raw[0]
    ctx_raw = raw[1]

    if not isinstance(meta_raw, list) or not isinstance(ctx_raw, list):
        raise ValueError("meta and contexts must both be lists")

    if len(meta_raw) != len(ctx_raw):
        raise ValueError(f"meta ({len(meta_raw)}) and contexts ({len(ctx_raw)}) have different lengths")

    assets: list[AssetMeta] = []
    contexts: list[AssetContext] = []

    for m, c in zip(meta_raw, ctx_raw):
        asset = AssetMeta(
            name=str(m.get("name", "")),
            sz_decimals=int(m.get("szDecimals", 0)),
            max_leverage=int(m.get("maxLeverage", 0)),
            only_isolated=bool(m.get("onlyIsolated", False)),
            is_delisted=bool(m.get("isDelisted", False)),
            margin_table_id=int(m.get("marginTableId", 0)),
        )
        assets.append(asset)

        ctx = AssetContext(
            mark_px=_to_float(c.get("markPx", "0")),
            mid_px=_to_float(c.get("midPx", "0")),
            oracle_px=_to_float(c.get("oraclePx", "0")),
            prev_day_px=_to_float(c.get("prevDayPx", "0")),
            funding=_to_float(c.get("funding", "0")),
            premium=_to_float(c.get("premium", "0")),
            open_interest=_to_float(c.get("openInterest", "0")),
            day_ntl_vlm=_to_float(c.get("dayNtlVlm", "0")),
            impact_pxs=[_to_float(p) for p in (c.get("impactPxs") or [])],
        )
        contexts.append(ctx)

    return ParsedUniverse(assets=assets, contexts=contexts)


def _to_float(val: Any) -> float:
    """Convert a value to float, handling strings and numeric types."""
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        try:
            return float(val)
        except (ValueError, TypeError):
            return 0.0
    return 0.0
