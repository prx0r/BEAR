"""Squeeze risk score (SPEC section 24).

Composite 0-100 score measuring vulnerability to short squeezes.
Inputs: funding, OI, price momentum, order book depth, volatility.
"""

from __future__ import annotations

import structlog
import numpy as np
import polars as pl

logger = structlog.get_logger()


def compute_squeeze_risk(
    funding_df: pl.DataFrame,
    oi_history: pl.DataFrame,
    prices_df: pl.DataFrame,
    books: pl.DataFrame | None = None,
) -> pl.DataFrame:
    """Compute SQUEEZE_RISK 0-100.

    Higher score = higher squeeze risk for shorts.

    Component signals:
        - extremely negative funding → higher squeeze risk
        - rapidly rising OI → higher
        - high OI/ADV → higher
        - positive price momentum → higher
        - thin order book → higher
        - high volatility → higher

    Args:
        funding_df: DataFrame with columns:
            - symbol: asset ticker
            - funding_rate: current instantaneous funding rate
        oi_history: DataFrame with columns:
            - symbol: asset ticker
            - timestamp: datetime
            - open_interest_usd: OI in USD
            - adv_usd: average daily volume (optional, for OI/ADV)
        prices_df: DataFrame with columns:
            - symbol: asset ticker
            - timestamp: datetime
            - close: daily close price
        books: Optional orderbook DataFrame with columns:
            - symbol: asset ticker
            - bid_depth_usd: total bid-side depth within 2% of mid
            - ask_depth_usd: total ask-side depth within 2% of mid

    Returns:
        DataFrame with columns:
            - symbol: asset ticker
            - squeeze_risk: 0-100 composite score
    """
    required_funding = {"symbol", "funding_rate"}
    missing_funding = required_funding - set(funding_df.columns)
    if missing_funding:
        raise ValueError(f"funding_df missing required columns: {missing_funding}")

    required_oi = {"symbol", "timestamp", "open_interest_usd"}
    missing_oi = required_oi - set(oi_history.columns)
    if missing_oi:
        raise ValueError(f"oi_history missing required columns: {missing_oi}")

    required_prices = {"symbol", "timestamp", "close"}
    missing_prices = required_prices - set(prices_df.columns)
    if missing_prices:
        raise ValueError(f"prices_df missing required columns: {missing_prices}")

    symbols = funding_df["symbol"].unique().to_list()
    results: list[dict] = []

    for sym in symbols:
        funding_row = funding_df.filter(pl.col("symbol") == sym)
        if funding_row.height == 0:
            continue
        current_funding = funding_row["funding_rate"][-1]

        sym_oi = (
            oi_history
            .filter(pl.col("symbol") == sym)
            .sort("timestamp")
        )

        oi_current = sym_oi["open_interest_usd"][-1] if sym_oi.height > 0 else 0.0
        adv = None
        if "adv_usd" in sym_oi.columns:
            adv = sym_oi["adv_usd"][-1]

        oi_rising = _oi_momentum(sym_oi)

        sym_prices = (
            prices_df
            .filter(pl.col("symbol") == sym)
            .sort("timestamp")
        )

        momentum = _price_momentum(sym_prices)
        volatility = _realized_volatility(sym_prices)

        book_thin = 0.0
        if books is not None:
            book_row = books.filter(pl.col("symbol") == sym)
            if book_row.height > 0:
                book_thin = _book_thinness(book_row.row(0, named=True))

        risk = _compute_score(
            funding=current_funding,
            oi_rising=oi_rising,
            oi_adv=(oi_current / adv) if adv and adv > 0 else None,
            momentum=momentum,
            book_thin=book_thin,
            volatility=volatility,
        )

        results.append({
            "symbol": sym,
            "squeeze_risk": risk,
        })

    return pl.DataFrame(results)


def _oi_momentum(sym_oi: pl.DataFrame) -> float:
    """OI change rate over last 14 days."""
    if sym_oi.height < 15:
        return 0.0

    oi_14d_ago = sym_oi["open_interest_usd"][-15]
    oi_now = sym_oi["open_interest_usd"][-1]

    if oi_14d_ago and oi_14d_ago > 0 and oi_now:
        return (oi_now - oi_14d_ago) / oi_14d_ago
    return 0.0


def _price_momentum(sym_prices: pl.DataFrame) -> float:
    """14-day price momentum (log return)."""
    if sym_prices.height < 15:
        return 0.0

    p_14d_ago = sym_prices["close"][-15]
    p_now = sym_prices["close"][-1]

    if p_14d_ago and p_14d_ago > 0 and p_now and p_now > 0:
        return float(np.log(p_now / p_14d_ago))
    return 0.0


def _realized_volatility(sym_prices: pl.DataFrame) -> float:
    """30-day annualized realized volatility."""
    if sym_prices.height < 31:
        return 0.0

    prices = sym_prices["close"][-31:].to_numpy().astype(np.float64)
    valid = prices[np.isfinite(prices) & (prices > 0)]

    if len(valid) < 10:
        return 0.0

    returns = np.diff(np.log(valid))
    return float(np.std(returns) * np.sqrt(365))


def _book_thinness(book: dict) -> float:
    """Order book thinness score 0-1 (1 = very thin)."""
    bid_depth = book.get("bid_depth_usd") or 0.0
    ask_depth = book.get("ask_depth_usd") or 0.0
    total_depth = bid_depth + ask_depth

    if total_depth <= 0:
        return 1.0

    if total_depth < 10_000:
        return 1.0
    elif total_depth < 50_000:
        return 0.8
    elif total_depth < 200_000:
        return 0.5
    elif total_depth < 1_000_000:
        return 0.2
    else:
        return 0.0


def _compute_score(
    funding: float,
    oi_rising: float,
    oi_adv: float | None,
    momentum: float,
    book_thin: float,
    volatility: float,
) -> float:
    """Composite squeeze risk score 0-100."""
    score = 0.0

    if funding < -0.001:
        score += min(25, max(0, -funding * 5000))
    elif funding < 0:
        score += min(10, max(0, -funding * 2000))

    score += min(20, max(0, oi_rising * 40))

    if oi_adv is not None:
        if oi_adv > 2.0:
            score += min(15, (oi_adv - 2.0) * 7.5)
        elif oi_adv > 1.0:
            score += min(8, (oi_adv - 1.0) * 8)

    if momentum > 0:
        score += min(15, momentum * 50)

    score += min(15, book_thin * 15)

    if volatility > 1.0:
        score += min(10, (volatility - 1.0) * 10)

    return min(100.0, max(0.0, score))
