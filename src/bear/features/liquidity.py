"""Liquidity features for relative-value trading on Hyperliquid."""

from __future__ import annotations

import polars as pl
import numpy as np


def compute_liquidity_features(
    asset_contexts_df: pl.DataFrame,
    books_df: pl.DataFrame | None = None,
) -> pl.DataFrame:
    """Compute liquidity metrics for each asset.

    Args:
        asset_contexts_df: DataFrame with columns:
            - 'symbol': asset symbol
            - 'adv_usd': average daily volume in USD (24h)
            - 'open_interest_usd': total open interest in USD
            - 'spread_bps': bid-ask spread in basis points (optional)
            - 'depth_usd': total orderbook depth within 2% of mid (optional)
            - 'volume_24h_usd': 24h trading volume (alternative to adv_usd)
        books_df: Optional orderbook snapshots. DataFrame with columns:
            - 'symbol': asset symbol
            - 'bid_price', 'ask_price', 'bid_size', 'ask_size'

    Returns:
        DataFrame with 'symbol' and liquidity feature columns:
            - adv_usd: average daily volume
            - oi_adv_ratio: open interest / ADV (leverage indicator)
            - spread_bps: bid-ask spread in basis points
            - depth_adv_ratio: orderbook depth / ADV
            - liquidity_score: composite 0-100 score
            - slippage_100k: estimated slippage for $100K trade
    """
    results: list[dict] = []

    symbols = asset_contexts_df["symbol"].unique().to_list()

    for sym in symbols:
        ctx_row = asset_contexts_df.filter(pl.col("symbol") == sym)
        if ctx_row.height == 0:
            continue
        ctx = ctx_row.row(0, named=True)

        adv = ctx.get("adv_usd") or ctx.get("volume_24h_usd")
        if adv is None or adv == 0:
            adv = np.nan

        oi = ctx.get("open_interest_usd")
        spread_bps = ctx.get("spread_bps")
        depth = ctx.get("depth_usd")

        # OI/ADV ratio
        oi_adv = float(oi / adv) if (oi is not None and adv and adv > 0) else np.nan

        # Depth/ADV ratio
        depth_adv = float(depth / adv) if (depth is not None and adv and adv > 0) else np.nan

        # Slippage estimate from book
        slippage_100k = np.nan
        if books_df is not None:
            book_row = books_df.filter(pl.col("symbol") == sym)
            if book_row.height > 0:
                book = book_row.row(0, named=True)
                slippage_100k = estimate_slippage(book, 100_000.0)

        # Composite liquidity score (0-100)
        score_parts: list[float] = []

        # ADV score: higher is better
        if np.isfinite(adv):
            # Log-scale: $10M = 50, $100M = 75, $1B = 100
            adv_score = min(100, max(0, 25 * np.log10(max(adv, 1)) / 8))
            score_parts.append(adv_score)
        else:
            score_parts.append(0.0)

        # Spread score: lower is better
        if spread_bps is not None and np.isfinite(spread_bps):
            spread_score = max(0, 100 - spread_bps * 10)
            score_parts.append(spread_score)
        else:
            score_parts.append(50.0)  # Unknown spread = neutral

        # OI/ADV score: moderate is good (too high = crowded, too low = thin)
        if np.isfinite(oi_adv):
            if oi_adv < 0.1:
                oi_score = 60.0
            elif oi_adv < 0.5:
                oi_score = 80.0
            elif oi_adv < 2.0:
                oi_score = 70.0
            else:
                oi_score = max(0, 100 - oi_adv * 15)
            score_parts.append(oi_score)
        else:
            score_parts.append(50.0)

        liquidity_score = np.mean(score_parts) if score_parts else 0.0

        results.append({
            "symbol": sym,
            "adv_usd": adv,
            "oi_adv_ratio": oi_adv,
            "spread_bps": spread_bps if spread_bps is not None else np.nan,
            "depth_adv_ratio": depth_adv,
            "liquidity_score": liquidity_score,
            "slippage_100k": slippage_100k,
        })

    if not results:
        return pl.DataFrame()

    return pl.DataFrame(results)


def estimate_slippage(
    book: dict,
    notional: float,
) -> float:
    """Estimate slippage for a given trade size by walking the orderbook.

    Simulates filling a market order by consuming liquidity level by level.

    Args:
        book: Orderbook snapshot with keys:
            - 'bids': list of [price, size] or list of dicts with 'price','size'
            - 'asks': list of [price, size] or list of dicts with 'price','size'
            OR flat keys: bid_price, bid_size, ask_price, ask_size
        notional: Trade size in USD. Positive = buy (lift asks),
            negative = sell (hit bids).

    Returns:
        Slippage in basis points (bps). Positive = unfavorable price impact.
        Returns 0.0 if book is empty or notional is zero.
    """
    if notional == 0:
        return 0.0

    is_buy = notional > 0
    abs_notional = abs(notional)

    # Extract book levels
    if is_buy:
        levels = _parse_book_levels(book, side="asks")
    else:
        levels = _parse_book_levels(book, side="bids")

    if not levels:
        return 1000.0  # No liquidity = very high slippage estimate

    # Walk the book
    remaining = abs_notional
    total_cost = 0.0
    total_filled = 0.0

    for price, size in levels:
        if remaining <= 0:
            break

        level_value = price * size
        fill_value = min(level_value, remaining)
        fill_size = fill_value / price

        total_cost += fill_value
        total_filled += fill_size
        remaining -= fill_value

    if total_filled <= 0:
        return 1000.0

    avg_price = total_cost / total_filled
    mid_price = _get_mid_price(book)

    if mid_price <= 0:
        return 1000.0

    # Slippage = (avg_fill_price - mid) / mid * 10000
    if is_buy:
        slippage_bps = ((avg_price - mid_price) / mid_price) * 10_000
    else:
        slippage_bps = ((mid_price - avg_price) / mid_price) * 10_000

    return float(max(0, slippage_bps))


def _parse_book_levels(book: dict, side: str) -> list[tuple[float, float]]:
    """Extract price/size levels from a book dict.

    Handles both list-of-lists and list-of-dicts formats.
    """
    levels_raw = book.get(side, [])

    if not levels_raw:
        # Try flat format
        if side == "asks" and "ask_price" in book and "ask_size" in book:
            return [(float(book["ask_price"]), float(book["ask_size"]))]
        if side == "bids" and "bid_price" in book and "bid_size" in book:
            return [(float(book["bid_price"]), float(book["bid_size"]))]
        return []

    levels: list[tuple[float, float]] = []
    for entry in levels_raw:
        if isinstance(entry, (list, tuple)) and len(entry) >= 2:
            levels.append((float(entry[0]), float(entry[1])))
        elif isinstance(entry, dict):
            p = entry.get("price") or entry.get("p")
            s = entry.get("size") or entry.get("s")
            if p is not None and s is not None:
                levels.append((float(p), float(s)))

    # Sort: asks ascending, bids descending
    if side == "asks":
        levels.sort(key=lambda x: x[0])
    else:
        levels.sort(key=lambda x: -x[0])

    return levels


def _get_mid_price(book: dict) -> float:
    """Get mid price from book."""
    if "bid_price" in book and "ask_price" in book:
        bid = float(book["bid_price"])
        ask = float(book["ask_price"])
        if bid > 0 and ask > 0:
            return (bid + ask) / 2

    bids = _parse_book_levels(book, "bids")
    asks = _parse_book_levels(book, "asks")

    if bids and asks:
        return (bids[0][0] + asks[0][0]) / 2

    return 0.0
