"""Post-listing decay and delisting risk features.

Young tokens exhibit systematic post-listing decay. Delisting risk
is estimated from volume decline, drawdown, and volatility patterns.
"""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import structlog
import polars as pl

logger = structlog.get_logger()


def compute_listing_features(
    listing_dates: pl.DataFrame,
    prices_df: pl.DataFrame,
) -> pl.DataFrame:
    """Compute post-listing decay features.

    Args:
        listing_dates: DataFrame with columns:
            - symbol: asset ticker
            - listing_date: datetime of first listing
            - first_day_close: close price on first trading day
            - exchange: exchange name (optional)
        prices_df: DataFrame with columns:
            - symbol: asset ticker
            - timestamp: datetime
            - close: daily close price

    Returns:
        DataFrame with columns:
            - symbol
            - age_days: (today - listing_date).days
            - listing_return: log(price_now / first_day_close)
            - young_weight: max(0, 1 - age_days / 365)
            - cohort_return_30d: mean return of tokens listed in same 30d window
            - cohort_return_90d: mean return of tokens listed in same 90d window
            - cohort_return_180d: mean return of tokens listed in same 180d window
    """
    required_listing = {"symbol", "listing_date", "first_day_close"}
    missing_listing = required_listing - set(listing_dates.columns)
    if missing_listing:
        raise ValueError(f"listing_dates missing required columns: {missing_listing}")

    required_prices = {"symbol", "timestamp", "close"}
    missing_prices = required_prices - set(prices_df.columns)
    if missing_prices:
        raise ValueError(f"prices_df missing required columns: {missing_prices}")

    now = datetime.now(timezone.utc)
    symbols = listing_dates["symbol"].unique().to_list()
    results: list[dict] = []

    for sym in symbols:
        listing_row = listing_dates.filter(pl.col("symbol") == sym)
        if listing_row.height == 0:
            continue
        ld = listing_row.row(0, named=True)

        listing_date = ld["listing_date"]
        if hasattr(listing_date, "tzinfo") and listing_date.tzinfo is None:
            listing_date = listing_date.replace(tzinfo=timezone.utc)

        age_days = (now - listing_date).days
        young_weight = max(0.0, 1.0 - age_days / 365.0)

        first_day_close = ld.get("first_day_close")

        sym_prices = (
            prices_df
            .filter(pl.col("symbol") == sym)
            .sort("timestamp")
        )

        listing_return = 0.0
        if sym_prices.height > 0 and first_day_close and first_day_close > 0:
            latest_price = sym_prices["close"][-1]
            if latest_price and latest_price > 0:
                listing_return = float(np.log(latest_price / first_day_close))

        same_cohort = _find_cohort(
            listing_dates, listing_date, window_days=30, exclude_sym=sym
        )
        cohort_30d = _mean_cohort_return(prices_df, same_cohort)

        same_cohort_90 = _find_cohort(
            listing_dates, listing_date, window_days=90, exclude_sym=sym
        )
        cohort_90d = _mean_cohort_return(prices_df, same_cohort_90)

        same_cohort_180 = _find_cohort(
            listing_dates, listing_date, window_days=180, exclude_sym=sym
        )
        cohort_180d = _mean_cohort_return(prices_df, same_cohort_180)

        results.append({
            "symbol": sym,
            "age_days": float(age_days),
            "listing_return": listing_return,
            "young_weight": young_weight,
            "cohort_return_30d": cohort_30d,
            "cohort_return_90d": cohort_90d,
            "cohort_return_180d": cohort_180d,
        })

    return pl.DataFrame(results)


def compute_delisting_features(
    market_data: pl.DataFrame,
    volume_history: pl.DataFrame,
) -> pl.DataFrame:
    """Compute delisting risk features.

    Features: drawdown_10d, drawdown_30d, volume_decline_30d,
    volume_decline_90d, volatility_30d

    Args:
        market_data: DataFrame with columns:
            - symbol: asset ticker
            - market_cap: current market cap
            - adv_usd: average daily volume
        volume_history: DataFrame with columns:
            - symbol: asset ticker
            - timestamp: datetime
            - volume_usd: daily trading volume
            - close: daily close price

    Returns:
        DataFrame with columns:
            - symbol
            - delist_risk_score: 0-100 (higher = more likely to delist)
            - drawdown_10d: max drawdown over last 10 days
            - drawdown_30d: max drawdown over last 30 days
            - volume_decline_30d: volume change over 30 days
            - volume_decline_90d: volume change over 90 days
            - volatility_30d: annualized 30-day volatility
    """
    required_market = {"symbol", "market_cap", "adv_usd"}
    missing_market = required_market - set(market_data.columns)
    if missing_market:
        raise ValueError(f"market_data missing required columns: {missing_market}")

    required_vol = {"symbol", "timestamp", "volume_usd", "close"}
    missing_vol = required_vol - set(volume_history.columns)
    if missing_vol:
        raise ValueError(f"volume_history missing required columns: {missing_vol}")

    symbols = market_data["symbol"].unique().to_list()
    results: list[dict] = []

    for sym in symbols:
        sym_vol = (
            volume_history
            .filter(pl.col("symbol") == sym)
            .sort("timestamp")
        )

        if sym_vol.height < 10:
            results.append({
                "symbol": sym,
                "delist_risk_score": 0.0,
                "drawdown_10d": 0.0,
                "drawdown_30d": 0.0,
                "volume_decline_30d": 0.0,
                "volume_decline_90d": 0.0,
                "volatility_30d": 0.0,
            })
            continue

        prices = sym_vol["close"].to_numpy().astype(np.float64)
        volumes = sym_vol["volume_usd"].to_numpy().astype(np.float64)

        dd_10 = _max_drawdown(prices[-10:]) if len(prices) >= 10 else 0.0
        dd_30 = _max_drawdown(prices[-30:]) if len(prices) >= 30 else 0.0

        vol_30_now = float(np.mean(volumes[-30:])) if len(volumes) >= 30 else np.nan
        vol_30_prev = float(np.mean(volumes[-60:-30])) if len(volumes) >= 60 else np.nan
        vol_90_now = float(np.mean(volumes[-90:])) if len(volumes) >= 90 else np.nan
        vol_90_prev = float(np.mean(volumes[-180:-90])) if len(volumes) >= 180 else np.nan

        vol_decline_30 = (
            (vol_30_now - vol_30_prev) / vol_30_prev
            if np.isfinite(vol_30_now) and np.isfinite(vol_30_prev) and vol_30_prev > 0
            else 0.0
        )
        vol_decline_90 = (
            (vol_90_now - vol_90_prev) / vol_90_prev
            if np.isfinite(vol_90_now) and np.isfinite(vol_90_prev) and vol_90_prev > 0
            else 0.0
        )

        recent_returns = np.diff(np.log(prices[-31:])) if len(prices) >= 31 else np.array([])
        realized_vol = (
            float(np.std(recent_returns) * np.sqrt(365))
            if len(recent_returns) > 5
            else 0.0
        )

        risk_score = _compute_delist_score(
            dd_10, dd_30, vol_decline_30, vol_decline_90, realized_vol
        )

        results.append({
            "symbol": sym,
            "delist_risk_score": risk_score,
            "drawdown_10d": dd_10,
            "drawdown_30d": dd_30,
            "volume_decline_30d": vol_decline_30,
            "volume_decline_90d": vol_decline_90,
            "volatility_30d": realized_vol,
        })

    return pl.DataFrame(results)


def _find_cohort(
    listing_dates: pl.DataFrame,
    reference_date: datetime,
    window_days: int = 30,
    exclude_sym: str | None = None,
) -> list[str]:
    """Find tokens listed within window_days of reference_date."""
    sub = listing_dates
    if exclude_sym:
        sub = sub.filter(pl.col("symbol") != exclude_sym)

    if "listing_date" not in sub.columns:
        return []

    results = sub.filter(
        (pl.col("listing_date") - pl.lit(reference_date)).dt.total_days().abs() <= window_days
    )["symbol"].to_list()

    return results


def _mean_cohort_return(
    prices_df: pl.DataFrame,
    cohort_symbols: list[str],
) -> float:
    """Mean listing return for a cohort of symbols."""
    if not cohort_symbols:
        return 0.0

    returns: list[float] = []
    for sym in cohort_symbols:
        sym_prices = prices_df.filter(pl.col("symbol") == sym).sort("timestamp")
        if sym_prices.height < 2:
            continue
        first_price = sym_prices["close"][0]
        last_price = sym_prices["close"][-1]
        if first_price and first_price > 0 and last_price and last_price > 0:
            returns.append(float(np.log(last_price / first_price)))

    return float(np.mean(returns)) if returns else 0.0


def _max_drawdown(prices: np.ndarray) -> float:
    """Compute max drawdown from price series. Returns negative value."""
    if len(prices) < 2:
        return 0.0
    cummax = np.maximum.accumulate(prices)
    drawdowns = np.where(cummax > 0, (prices - cummax) / cummax, 0.0)
    return float(np.min(drawdowns))


def _compute_delist_score(
    dd_10: float,
    dd_30: float,
    vol_decline_30: float,
    vol_decline_90: float,
    realized_vol: float,
) -> float:
    """Heuristic delisting risk score 0-100."""
    score = 0.0

    score += min(25, max(0, -dd_10 * 250))
    score += min(25, max(0, -dd_30 * 125))
    score += min(20, max(0, -vol_decline_30 * 50))
    score += min(15, max(0, -vol_decline_90 * 25))
    score += min(15, max(0, realized_vol * 10 - 30))

    return min(100.0, max(0.0, score))
