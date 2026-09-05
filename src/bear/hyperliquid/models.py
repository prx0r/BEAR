"""Pydantic models for Hyperliquid API responses.

Derived from the TypeScript types in hypertrack. All numeric fields use
Decimal for precision; the API delivers them as strings.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# REST: metaAndAssetCtxs
# ---------------------------------------------------------------------------

class AssetMeta(BaseModel):
    """Per-asset metadata from the perp universe."""
    name: str
    sz_decimals: int
    max_leverage: int
    only_isolated: bool = False
    is_delisted: bool = False
    margin_table_id: Optional[int] = None


class Meta(BaseModel):
    """Universe wrapper returned alongside asset contexts."""
    universe: list[AssetMeta] = Field(default_factory=list)


class AssetCtx(BaseModel):
    """Live market context for a single asset."""
    mark_px: Decimal
    mid_px: Optional[Decimal] = None
    oracle_px: Decimal
    prev_day_px: Decimal
    funding: Decimal
    premium: Optional[Decimal] = None
    open_interest: Decimal
    day_ntl_vlm: Decimal
    impact_pxs: Optional[list[Decimal]] = None


class MetaAndAssetCtxs(BaseModel):
    """Response tuple for {type:'metaAndAssetCtxs'}."""
    meta: Meta
    asset_ctxs: list[AssetCtx] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# REST: clearinghouseState
# ---------------------------------------------------------------------------

class LeverageInfo(BaseModel):
    type: str  # "cross" or "isolated"
    value: int
    raw_usd: Optional[str] = None


class CumFunding(BaseModel):
    all_time: Decimal
    since_open: Decimal
    since_change: Decimal


class AssetPosition(BaseModel):
    coin: str
    szi: Decimal  # signed size; negative = short
    entry_px: Decimal
    position_value: Decimal
    unrealized_pnl: Decimal
    return_on_equity: Decimal
    leverage: LeverageInfo
    liquidation_px: Optional[Decimal] = None
    margin_used: Decimal
    max_leverage: int
    cum_funding: CumFunding


class MarginSummary(BaseModel):
    account_value: Decimal
    total_ntl_pos: Decimal
    total_raw_usd: Decimal
    total_margin_used: Decimal


class ClearinghouseState(BaseModel):
    margin_summary: MarginSummary
    cross_margin_summary: MarginSummary
    cross_maintenance_margin_used: Decimal
    withdrawable: Decimal
    asset_positions: list[AssetPosition] = Field(default_factory=list)
    time: int


# ---------------------------------------------------------------------------
# REST: user fills
# ---------------------------------------------------------------------------

class UserFill(BaseModel):
    """A single user fill."""
    coin: str
    px: Decimal
    sz: Decimal
    side: str  # "B" (buy) or "A" (sell)
    time: int
    start_position: Decimal
    dir: str
    closed_pnl: Decimal
    hash: str
    oid: int
    crossed: bool
    fee: Decimal
    tid: int
    fee_token: str


# ---------------------------------------------------------------------------
# WebSocket payloads
# ---------------------------------------------------------------------------

class WsTrade(BaseModel):
    """A single trade print from the trades channel."""
    coin: str
    side: str  # "B" or "A"
    px: Decimal
    sz: Decimal
    time: int
    hash: str
    tid: int


class WsAllMids(BaseModel):
    """allMids channel payload: coin -> mid price."""
    mids: dict[str, Decimal] = Field(default_factory=dict)


class WsCandle(BaseModel):
    """Candle channel payload."""
    t: int
    o: Decimal
    h: Decimal
    l: Decimal
    c: Decimal
    v: Decimal
    n: int
    coin: str
    interval: str


class WsL2Book(BaseModel):
    """L2 book channel payload."""
    coin: str
    time: int
    bids: list[list[Decimal]] = Field(default_factory=list)
    asks: list[list[Decimal]] = Field(default_factory=list)


class WsActiveAssetCtx(BaseModel):
    """activeAssetCtx channel payload."""
    coin: str
    funding: Decimal
    open_interest: Decimal
    prev_day_px: Decimal
    day_ntl_vlm: Decimal
    premium: Optional[Decimal] = None
    oracle_px: Decimal
    mark_px: Decimal
    mid_px: Optional[Decimal] = None
    impact_pxs: Optional[list[Decimal]] = None


class WsMessage(BaseModel):
    """Generic inbound WS message envelope."""
    channel: str
    data: dict


# ---------------------------------------------------------------------------
# Derived view models
# ---------------------------------------------------------------------------

class LeaderboardEntry(BaseModel):
    """A single ranked entry in the alpha leaderboard."""
    rank: int
    coin: str
    mark_px: Decimal
    change_24h_pct: Decimal
    day_volume: Decimal
    open_interest: Decimal
    funding: Decimal
