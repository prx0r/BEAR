"""Multi-signal death score — combines price, fundamental, and on-chain signals.

Signals (all 0-100, higher = more likely dead):
1. volume_death: vol_now / vol_peak < threshold
2. deep_decline: DD from peak + 90d negative return
3. reversal_8w: 8-week return (cross-sectional percentile)
4. funding_pressure: extreme negative funding (crowded short)
5. momentum: 7-day return (cross-sectional percentile)

Weights are optimized via backtest (see backtest script).
"""

from __future__ import annotations

import numpy as np
import polars as pl


# ---------------------------------------------------------------------------
# Individual signal computations (0-100 scale each)
# ---------------------------------------------------------------------------


def signal_volume_death(prices_df: pl.DataFrame, window_peak: int = 90) -> pl.Series:
    """Volume death: ratio of recent volume to peak volume.

    Low ratio = dead. Maps to 0-100 where 100 = volume collapsed.
    Requires columns: timestamp, volume, symbol.
    """
    if "volume" not in prices_df.columns:
        return pl.lit(50.0).alias("volume_death")

    vol = prices_df.get_column("volume").to_numpy().astype(np.float64)
    n = len(vol)

    if n < window_peak:
        return pl.lit(50.0).alias("volume_death")

    # Rolling peak volume over window_peak
    peak_vol = np.full(n, np.nan)
    for i in range(window_peak - 1, n):
        window = vol[max(0, i - window_peak + 1): i + 1]
        valid = window[np.isfinite(window)]
        peak_vol[i] = np.max(valid) if len(valid) > 0 else np.nan

    # Recent volume = 7-day mean
    recent_vol = np.full(n, np.nan)
    for i in range(6, n):
        window = vol[max(0, i - 6): i + 1]
        valid = window[np.isfinite(window)]
        recent_vol[i] = np.mean(valid) if len(valid) > 0 else np.nan

    # Ratio: low ratio = high death score
    ratio = np.where(
        np.isfinite(peak_vol) & np.isfinite(recent_vol) & (peak_vol > 0),
        recent_vol / peak_vol,
        np.nan,
    )

    # Map to 0-100: ratio=1.0 -> 0 (alive), ratio=0.0 -> 100 (dead)
    scores = np.where(
        np.isfinite(ratio),
        np.clip((1.0 - ratio) * 100, 0, 100),
        np.nan,
    )

    return pl.Series("volume_death", scores, dtype=pl.Float64)


def signal_deep_decline(prices_df: pl.DataFrame, peak_window: int = 180) -> pl.Series:
    """Deep decline: drawdown from peak + 90d negative return.

    Combines:
    - Drawdown from all-time-high (within peak_window)
    - 90-day return (negative = more dead)
    Maps to 0-100.
    Requires columns: timestamp, close.
    """
    if "close" not in prices_df.columns:
        return pl.lit(50.0).alias("deep_decline")

    close = prices_df.get_column("close").to_numpy().astype(np.float64)
    n = len(close)

    if n < 90:
        return pl.lit(50.0).alias("deep_decline")

    # Drawdown from rolling peak
    dd = np.full(n, np.nan)
    for i in range(peak_window - 1, n):
        window = close[max(0, i - peak_window + 1): i + 1]
        valid = window[np.isfinite(window)]
        if len(valid) > 0 and valid.max() > 0:
            dd[i] = (close[i] - valid.max()) / valid.max()
        else:
            dd[i] = np.nan

    # 90-day return
    ret_90d = np.full(n, np.nan)
    for i in range(89, n):
        if np.isfinite(close[i]) and np.isfinite(close[i - 89]) and close[i - 89] > 0:
            ret_90d[i] = (close[i] - close[i - 89]) / close[i - 89]
        else:
            ret_90d[i] = np.nan

    # Combine: negative dd + negative ret = high score
    # dd is negative (e.g. -0.95 = -95%), ret_90d is negative when declining
    # Score = mean of two components, each 0-100
    dd_score = np.where(
        np.isfinite(dd),
        np.clip((-dd) * 100, 0, 100),  # -(-0.95) = 0.95 * 100 = 95
        np.nan,
    )
    ret_score = np.where(
        np.isfinite(ret_90d),
        np.clip((-ret_90d) * 100, 0, 100),
        np.nan,
    )

    # Weighted average: 60% drawdown, 40% 90d return
    scores = np.where(
        np.isfinite(dd_score) & np.isfinite(ret_score),
        0.6 * dd_score + 0.4 * ret_score,
        np.where(
            np.isfinite(dd_score),
            dd_score,
            np.where(np.isfinite(ret_score), ret_score, np.nan),
        ),
    )

    return pl.Series("deep_decline", scores, dtype=pl.Float64)


def signal_reversal_8w(prices_df: pl.DataFrame) -> pl.Series:
    """8-week reversal: cross-sectional percentile of 56-day return.

    High return = recent winner = likely to revert = higher death score.
    Maps to 0-100 via percentile ranking.
    Requires columns: timestamp, close.
    """
    if "close" not in prices_df.columns:
        return pl.lit(50.0).alias("reversal_8w")

    close = prices_df.get_column("close").to_numpy().astype(np.float64)
    n = len(close)

    if n < 56:
        return pl.lit(50.0).alias("reversal_8w")

    ret_8w = np.full(n, np.nan)
    for i in range(55, n):
        if np.isfinite(close[i]) and np.isfinite(close[i - 55]) and close[i - 55] > 0:
            ret_8w[i] = (close[i] - close[i - 55]) / close[i - 55]
        else:
            ret_8w[i] = np.nan

    # Cross-sectional percentile within this asset (rank over time)
    valid_mask = np.isfinite(ret_8w)
    if valid_mask.sum() < 10:
        return pl.lit(50.0).alias("reversal_8w")

    valid_vals = ret_8w[valid_mask]
    ranks = np.searchsorted(np.sort(valid_vals), valid_vals)
    percentile = ranks / len(valid_vals) * 100

    scores = np.full(n, np.nan)
    scores[valid_mask] = percentile

    return pl.Series("reversal_8w", scores, dtype=pl.Float64)


def signal_funding_pressure(prices_df: pl.DataFrame) -> pl.Series:
    """Funding pressure: extreme negative funding = crowded short.

    Since daily OHLCV data doesn't contain funding rates, we proxy using
    volume-weighted price decline intensity. Sharp decline with high volume
    suggests crowded shorts.

    Falls back to price-based proxy when funding data unavailable.
    Maps to 0-100.
    """
    if "close" not in prices_df.columns or "volume" not in prices_df.columns:
        return pl.lit(50.0).alias("funding_pressure")

    close = prices_df.get_column("close").to_numpy().astype(np.float64)
    volume = prices_df.get_column("volume").to_numpy().astype(np.float64)
    n = len(close)

    if n < 30:
        return pl.lit(50.0).alias("funding_pressure")

    # 30-day rolling volatility of returns (high vol = stress)
    returns = np.full(n, np.nan)
    for i in range(1, n):
        if np.isfinite(close[i]) and np.isfinite(close[i - 1]) and close[i - 1] > 0:
            returns[i] = (close[i] - close[i - 1]) / close[i - 1]

    vol_30d = np.full(n, np.nan)
    for i in range(29, n):
        window = returns[max(1, i - 29): i + 1]
        valid = window[np.isfinite(window)]
        vol_30d[i] = np.std(valid) if len(valid) > 5 else np.nan

    # Volume trend: declining volume = apathy
    vol_ma = np.full(n, np.nan)
    for i in range(29, n):
        window = volume[max(0, i - 29): i + 1]
        valid = window[np.isfinite(window)]
        vol_ma[i] = np.mean(valid) if len(valid) > 0 else np.nan

    # Recent volume vs long-term
    vol_recent = np.full(n, np.nan)
    for i in range(6, n):
        window = volume[max(0, i - 6): i + 1]
        valid = window[np.isfinite(window)]
        vol_recent[i] = np.mean(valid) if len(valid) > 0 else np.nan

    vol_ratio = np.where(
        np.isfinite(vol_ma) & np.isfinite(vol_recent) & (vol_ma > 0),
        vol_recent / vol_ma,
        np.nan,
    )

    # Combine: high vol_30d (stressed) + low vol_ratio (dying volume)
    vol_score = np.where(
        np.isfinite(vol_30d),
        np.clip(vol_30d * 500, 0, 100),  # scale vol to 0-100
        np.nan,
    )
    decline_score = np.where(
        np.isfinite(vol_ratio),
        np.clip((1.0 - vol_ratio) * 100, 0, 100),
        np.nan,
    )

    scores = np.where(
        np.isfinite(vol_score) & np.isfinite(decline_score),
        0.5 * vol_score + 0.5 * decline_score,
        np.where(
            np.isfinite(vol_score), vol_score,
            np.where(np.isfinite(decline_score), decline_score, np.nan),
        ),
    )

    return pl.Series("funding_pressure", scores, dtype=pl.Float64)


def signal_momentum(prices_df: pl.DataFrame) -> pl.Series:
    """Momentum: 7-day return as cross-sectional percentile.

    Negative momentum = more dead. Maps to 0-100.
    Requires columns: timestamp, close.
    """
    if "close" not in prices_df.columns:
        return pl.lit(50.0).alias("momentum")

    close = prices_df.get_column("close").to_numpy().astype(np.float64)
    n = len(close)

    if n < 7:
        return pl.lit(50.0).alias("momentum")

    ret_7d = np.full(n, np.nan)
    for i in range(6, n):
        if np.isfinite(close[i]) and np.isfinite(close[i - 6]) and close[i - 6] > 0:
            ret_7d[i] = (close[i] - close[i - 6]) / close[i - 6]
        else:
            ret_7d[i] = np.nan

    # Cross-sectional percentile ranking over time for this asset
    valid_mask = np.isfinite(ret_7d)
    if valid_mask.sum() < 10:
        return pl.lit(50.0).alias("momentum")

    valid_vals = ret_7d[valid_mask]
    ranks = np.searchsorted(np.sort(valid_vals), valid_vals)
    percentile = ranks / len(valid_vals) * 100

    scores = np.full(n, np.nan)
    scores[valid_mask] = percentile

    return pl.Series("momentum", scores, dtype=pl.Float64)


# ---------------------------------------------------------------------------
# Combined death score
# ---------------------------------------------------------------------------


def compute_death_score(
    prices_df: pl.DataFrame,
    weights: dict[str, float] | None = None,
) -> pl.DataFrame:
    """Compute the combined multi-signal death score.

    Args:
        prices_df: DataFrame with columns: timestamp, close, volume, symbol.
            Can be single-asset or multi-asset.
        weights: Signal weights. Keys: volume_death, deep_decline, reversal_8w,
            funding_pressure, momentum. Must sum to 1.0.
            Default: equal weights (0.20 each).

    Returns:
        DataFrame with timestamp, symbol (if present), individual signal scores,
        and combined death_score (0-100, higher = more likely dead).
    """
    if weights is None:
        weights = {
            "volume_death": 0.20,
            "deep_decline": 0.20,
            "reversal_8w": 0.20,
            "funding_pressure": 0.20,
            "momentum": 0.20,
        }

    w_total = sum(weights.values())
    if abs(w_total - 1.0) > 0.01:
        weights = {k: v / w_total for k, v in weights.items()}

    has_symbol = "symbol" in prices_df.columns

    if has_symbol:
        symbols = prices_df["symbol"].unique().to_list()
        parts = []
        for sym in symbols:
            sub = prices_df.filter(pl.col("symbol") == sym).sort("timestamp")
            scored = _compute_score_single(sub, weights)
            scored = scored.with_columns(pl.lit(sym).alias("symbol"))
            parts.append(scored)
        if not parts:
            return pl.DataFrame()
        return pl.concat(parts)
    else:
        scored = _compute_score_single(prices_df.sort("timestamp"), weights)
        return scored


def _compute_score_single(
    df: pl.DataFrame,
    weights: dict[str, float],
) -> pl.DataFrame:
    """Compute death score for a single-asset DataFrame (sorted by timestamp)."""
    s_vol = signal_volume_death(df)
    s_dd = signal_deep_decline(df)
    s_rev = signal_reversal_8w(df)
    s_fund = signal_funding_pressure(df)
    s_mom = signal_momentum(df)

    result = df.select([pl.col("timestamp")]).with_columns([
        s_vol.alias("volume_death"),
        s_dd.alias("deep_decline"),
        s_rev.alias("reversal_8w"),
        s_fund.alias("funding_pressure"),
        s_mom.alias("momentum"),
    ])

    # Compute weighted combination
    n = result.height
    combined = np.zeros(n)
    weight_sum = np.zeros(n)

    for sig_name, w in weights.items():
        if sig_name in result.columns:
            vals = result.get_column(sig_name).to_numpy().astype(np.float64)
            mask = np.isfinite(vals)
            combined[mask] += w * vals[mask]
            weight_sum[mask] += w

    # Normalize by total weight actually applied
    scores = np.where(weight_sum > 0, combined / weight_sum * sum(weights.values()), np.nan)
    scores = np.clip(scores, 0, 100)

    result = result.with_columns(pl.Series("death_score", scores, dtype=pl.Float64))

    return result
