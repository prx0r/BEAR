"""Market regime detection (SPEC section 17).

Classifies market regime based on BTC price action.
Regimes: BULL, BEAR, HIGH_VOL, LOW_VOL, CRASH.
"""

from __future__ import annotations

import structlog
import numpy as np
import polars as pl

logger = structlog.get_logger()

_EMA_SPAN = 30
_VOL_WINDOW = 90
_CRASH_PERCENTILE = 0.1


def detect_regime(
    btc_prices: pl.DataFrame,
) -> pl.DataFrame:
    """Classify market regime based on BTC.

    Rules:
        - BTC above 30d EMA → BULL (else BEAR)
        - BTC realized vol above 75th percentile → HIGH_VOL (else LOW_VOL)
        - BTC daily return bottom decile → CRASH

    Args:
        btc_prices: DataFrame with columns:
            - timestamp: datetime
            - close: BTC daily close price

    Returns:
        DataFrame with columns:
            - timestamp
            - regime: one of BULL, BEAR, HIGH_VOL, LOW_VOL, CRASH
            - btc_ema_30d: 30-day EMA of BTC close
            - realized_vol: 30-day annualized realized volatility
            - vol_percentile: percentile rank of current vol in 90-day window
    """
    required = {"timestamp", "close"}
    missing = required - set(btc_prices.columns)
    if missing:
        raise ValueError(f"btc_prices missing required columns: {missing}")

    df = btc_prices.sort("timestamp").clone()

    log_close = pl.col("close")
    df = df.with_columns(
        pl.when(log_close.is_not_null() & (log_close > 0))
        .then(log_close)
        .otherwise(pl.lit(None).cast(pl.Float64))
        .alias("_log_close")
    )

    ema_expr = pl.col("_log_close").ewm_mean(span=_EMA_SPAN, adjust=False)
    df = df.with_columns(ema_expr.alias("_ema_30d"))

    ema_val = pl.col("_ema_30d")
    close_val = pl.col("_log_close")
    df = df.with_columns(
        pl.when(ema_val.is_not_null() & close_val.is_not_null())
        .then(pl.exp(ema_val))
        .otherwise(pl.lit(None).cast(pl.Float64))
        .alias("btc_ema_30d")
    )

    daily_return = pl.col("_log_close").diff()
    df = df.with_columns(daily_return.alias("_daily_return"))

    df = df.with_columns(
        pl.col("_daily_return")
        .rolling_std(_VOL_WINDOW)
        .alias("_vol_raw")
    )

    vol_raw = pl.col("_vol_raw")
    df = df.with_columns(
        pl.when(vol_raw.is_not_null())
        .then(vol_raw * np.sqrt(365))
        .otherwise(pl.lit(None).cast(pl.Float64))
        .alias("realized_vol")
    )

    vol_series = df["realized_vol"].to_numpy()
    n = len(vol_series)

    vol_percentiles = np.full(n, np.nan)
    for i in range(_VOL_WINDOW, n):
        window = vol_series[max(0, i - _VOL_WINDOW):i]
        valid_window = window[np.isfinite(window)]
        if len(valid_window) > 5:
            vol_percentiles[i] = float(
                np.sum(valid_window <= vol_series[i]) / len(valid_window) * 100
            )

    df = df.with_columns(
        pl.Series("vol_percentile", vol_percentiles)
    )

    regimes: list[str] = []
    close_arr = df["close"].to_numpy().astype(np.float64)
    ema_arr = df["btc_ema_30d"].to_numpy()
    vol_arr = df["realized_vol"].to_numpy()
    ret_arr = df["_daily_return"].to_numpy()

    for i in range(n):
        close_val_i = close_arr[i]
        ema_val_i = ema_arr[i] if i < len(ema_arr) else np.nan
        vol_val_i = vol_arr[i] if i < len(vol_arr) else np.nan
        ret_val_i = ret_arr[i] if i < len(ret_arr) else np.nan
        vol_pct_i = vol_percentiles[i]

        if not np.isfinite(close_val_i) or not np.isfinite(ema_val_i):
            regimes.append("LOW_VOL")
            continue

        is_bull = close_val_i > ema_val_i

        is_high_vol = False
        if np.isfinite(vol_pct_i):
            is_high_vol = vol_pct_i > 75

        is_crash = False
        if np.isfinite(ret_val_i):
            crash_threshold = np.nanpercentile(ret_arr, _CRASH_PERCENTILE * 100)
            is_crash = ret_val_i <= crash_threshold

        if is_crash:
            regimes.append("CRASH")
        elif is_high_vol:
            regimes.append("HIGH_VOL")
        elif is_bull:
            regimes.append("BULL")
        else:
            regimes.append("BEAR")

    df = df.with_columns(pl.Series("regime", regimes))

    df = df.drop(["_log_close", "_ema_30d", "_daily_return", "_vol_raw"])

    return df.select(["timestamp", "regime", "btc_ema_30d", "realized_vol", "vol_percentile"])
