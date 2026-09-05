"""Derivation helpers for converting raw Hyperliquid API data into
clean, usable structures.

All functions take raw API response dicts (as returned by the client)
and return clean dicts suitable for downstream consumption.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from bear.hyperliquid.models import AssetCtx, AssetMeta


def _d(val: Any, default: str = "0") -> Decimal:
    """Coerce a value to Decimal, returning default on failure."""
    if val is None or val == "":
        return Decimal(default)
    try:
        return Decimal(str(val))
    except Exception:
        return Decimal(default)


def to_universe_entries(
    meta_items: list[dict[str, Any]],
    ctx_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Convert raw meta+contexts into clean market dicts.

    Args:
        meta_items: Raw universe list from metaAndAssetCtxs[0].
        ctx_items: Raw asset contexts list from metaAndAssetCtxs[1].

    Returns:
        List of dicts, one per asset, with clean keys and Decimal values:
        {
            "name": "BTC",
            "sz_decimals": 5,
            "max_leverage": 50,
            "only_isolated": False,
            "is_delisted": False,
            "margin_table_id": 0,
            "mark_px": Decimal("84000"),
            "mid_px": Decimal("83999"),
            "oracle_px": Decimal("84001"),
            "prev_day_px": Decimal("83200"),
            "funding": Decimal("0.0001"),
            "premium": None,
            "open_interest": Decimal("1234567890"),
            "day_ntl_vlm": Decimal("9876543210"),
            "impact_bid": Decimal("83995"),
            "impact_ask": Decimal("84005"),
        }
    """
    entries: list[dict[str, Any]] = []

    for i, meta in enumerate(meta_items):
        name = meta.get("name", "")
        if not name:
            continue

        ctx = ctx_items[i] if i < len(ctx_items) else {}
        impact = ctx.get("impactPxs") or []

        entries.append({
            "name": name,
            "sz_decimals": int(meta.get("szDecimals", 0)),
            "max_leverage": int(meta.get("maxLeverage", 1)),
            "only_isolated": bool(meta.get("onlyIsolated", False)),
            "is_delisted": bool(meta.get("isDelisted", False)),
            "margin_table_id": int(meta.get("marginTableId", 0)),
            "mark_px": _d(ctx.get("markPx")),
            "mid_px": _d(ctx.get("midPx")) if ctx.get("midPx") else None,
            "oracle_px": _d(ctx.get("oraclePx")),
            "prev_day_px": _d(ctx.get("prevDayPx")),
            "funding": _d(ctx.get("funding")),
            "premium": _d(ctx.get("premium")) if ctx.get("premium") else None,
            "open_interest": _d(ctx.get("openInterest")),
            "day_ntl_vlm": _d(ctx.get("dayNtlVlm")),
            "impact_bid": _d(impact[0]) if len(impact) > 0 else Decimal("0"),
            "impact_ask": _d(impact[1]) if len(impact) > 1 else Decimal("0"),
        })

    return entries


def to_leaderboard(
    ctx_items: list[dict[str, Any]],
    meta_items: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Sort assets by 24h notional volume and assign ranks.

    Args:
        ctx_items: Raw asset contexts list.
        meta_items: Optional raw universe list for name resolution.

    Returns:
        List of dicts sorted by dayNtlVlm descending, each with:
        {
            "rank": 1,
            "coin": "BTC",
            "mark_px": Decimal("84000"),
            "change_24h_pct": Decimal("0.023"),
            "day_volume": Decimal("9876543210"),
            "open_interest": Decimal("1234567890"),
            "funding": Decimal("0.0001"),
        }
    """
    name_map: dict[int, str] = {}
    if meta_items:
        for i, m in enumerate(meta_items):
            name_map[i] = m.get("name", f"ASSET_{i}")

    entries: list[dict[str, Any]] = []

    for i, ctx in enumerate(ctx_items):
        name = name_map.get(i, f"ASSET_{i}")
        mark = _d(ctx.get("markPx"))
        prev = _d(ctx.get("prevDayPx"))
        day_vlm = _d(ctx.get("dayNtlVlm"))

        # 24h change percentage
        change_pct = Decimal("0")
        if prev > 0:
            change_pct = ((mark - prev) / prev * 100).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

        entries.append({
            "coin": name,
            "mark_px": mark,
            "change_24h_pct": change_pct,
            "day_volume": day_vlm,
            "open_interest": _d(ctx.get("openInterest")),
            "funding": _d(ctx.get("funding")),
        })

    # Sort by 24h volume descending, assign ranks
    entries.sort(key=lambda e: e["day_volume"], reverse=True)
    for rank, entry in enumerate(entries, start=1):
        entry["rank"] = rank

    return entries


def compute_oi_adv(ctx: dict[str, Any]) -> Decimal:
    """Compute OI/ADV ratio from a single asset context.

    Args:
        ctx: Raw asset context dict from the API.

    Returns:
        OI divided by ADV (24h notional volume). Returns Decimal("0") if
        ADV is zero to avoid division by zero.

    A high OI/ADV ratio indicates crowded positioning relative to liquidity.
    Values > 1.0 suggest the market is illiquid relative to open interest.
    """
    oi = _d(ctx.get("openInterest"))
    adv = _d(ctx.get("dayNtlVlm"))

    if adv <= 0:
        return Decimal("0")

    return (oi / adv).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def compute_spread_bps(
    bids: list[list[Any]],
    asks: list[list[Any]],
) -> Decimal:
    """Compute bid-ask spread in basis points.

    Args:
        bids: List of [price, size] levels, best bid first.
        asks: List of [price, size] levels, best ask first.

    Returns:
        Spread in basis points.
    """
    if not bids or not asks:
        return Decimal("0")

    best_bid = _d(bids[0][0])
    best_ask = _d(asks[0][0])
    mid = (best_bid + best_ask) / 2

    if mid <= 0:
        return Decimal("0")

    return ((best_ask - best_bid) / mid * 10000).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def funding_annualized(hourly_rate: Decimal | float | str) -> Decimal:
    """Annualize an hourly funding rate.

    Hyperliquid has 8 funding periods per day (every 3 hours).
    This function takes the raw hourly rate and annualizes it.

    Args:
        hourly_rate: Raw funding rate (positive = long pays short).

    Returns:
        Annualized rate as a percentage.
    """
    rate = _d(hourly_rate)
    # rate * 8 periods/day * 365 days/year * 100 for percentage
    return (rate * 8 * 365 * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def parse_price_change(prev_day_px: str | Decimal | float, mark_px: str | Decimal | float) -> Decimal:
    """Compute 24h price change percentage.

    Args:
        prev_day_px: Previous day's price.
        mark_px: Current mark price.

    Returns:
        Percentage change, e.g. Decimal("2.35") for +2.35%.
    """
    prev = _d(prev_day_px)
    mark = _d(mark_px)

    if prev <= 0:
        return Decimal("0")

    return ((mark - prev) / prev * 100).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
