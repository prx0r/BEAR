"""Positioning features for relative-value trading.

Tracks open interest changes and classifies price-OI regimes.
"""

from __future__ import annotations

import polars as pl
import numpy as np


def compute_positioning_features(
    oi_history: pl.DataFrame,
    price_history: pl.DataFrame,
    windows: list[int] | None = None,
) -> pl.DataFrame:
    """Compute positioning features from OI and price history.

    Classifies the market into four regimes based on the joint behavior
    of price and open interest:
        - price_up_oi_up:   Longs building, bullish conviction
        - price_up_oi_down:  Shorts closing, short squeeze risk
        - price_down_oi_up:  Shorts building, bearish conviction
        - price_down_oi_down: Both sides unwinding, deleveraging

    Args:
        oi_history: DataFrame with 'timestamp', 'symbol', 'open_interest'.
        price_history: DataFrame with 'timestamp', 'symbol', 'close'.
        windows: Lookback windows for change calculations. Defaults to [1, 7, 30].

    Returns:
        DataFrame with 'timestamp', 'symbol', and positioning feature columns:
            - oi_change_<w>d: fractional change in OI over w periods
            - price_change_<w>d: fractional price change over w periods
            - regime: one of [long_build, short_squeeze, short_build, deleveraging, neutral]
            - regime_confidence: 0-1 confidence in the regime classification
    """
    if windows is None:
        windows = [1, 7, 30]

    required_oi = {"timestamp", "symbol", "open_interest"}
    required_price = {"timestamp", "symbol", "close"}

    missing_oi = required_oi - set(oi_history.columns)
    missing_price = required_price - set(price_history.columns)
    if missing_oi:
        raise ValueError(f"oi_history missing columns: {missing_oi}")
    if missing_price:
        raise ValueError(f"price_history missing columns: {missing_price}")

    # Merge OI and price on (timestamp, symbol)
    merged = (
        oi_history.select(["timestamp", "symbol", "open_interest"])
        .join(
            price_history.select(["timestamp", "symbol", "close"]),
            on=["timestamp", "symbol"],
            how="inner",
        )
        .sort(["symbol", "timestamp"])
    )

    result_exprs: list[pl.Expr] = [
        pl.col("timestamp"),
        pl.col("symbol"),
        pl.col("open_interest"),
        pl.col("close"),
    ]

    for w in windows:
        oi_shifted = pl.col("open_interest").shift(w).over("symbol")
        price_shifted = pl.col("close").shift(w).over("symbol")

        # OI change
        result_exprs.append(
            pl.when(
                oi_shifted.is_not_null()
                & (oi_shifted > 0)
                & pl.col("open_interest").is_not_null()
            )
            .then((pl.col("open_interest") - oi_shifted) / oi_shifted)
            .otherwise(pl.lit(None).cast(pl.Float64))
            .alias(f"oi_change_{w}d")
        )

        # Price change
        result_exprs.append(
            pl.when(
                price_shifted.is_not_null()
                & (price_shifted > 0)
                & pl.col("close").is_not_null()
            )
            .then((pl.col("close") - price_shifted) / price_shifted)
            .otherwise(pl.lit(None).cast(pl.Float64))
            .alias(f"price_change_{w}d")
        )

    # Regime classification using 7d changes (or shortest available)
    ref_window = 7 if 7 in windows else windows[0] if windows else 1

    oi_chg = pl.col(f"oi_change_{ref_window}d")
    price_chg = pl.col(f"price_change_{ref_window}d")

    # Regime logic
    regime_expr = (
        pl.when(price_chg.is_not_null() & oi_chg.is_not_null())
        .then(
            pl.when((price_chg > 0.01) & (oi_chg > 0.05))
            .then(pl.lit("long_build"))
            .when((price_chg > 0.01) & (oi_chg < -0.05))
            .then(pl.lit("short_squeeze"))
            .when((price_chg < -0.01) & (oi_chg > 0.05))
            .then(pl.lit("short_build"))
            .when((price_chg < -0.01) & (oi_chg < -0.05))
            .then(pl.lit("deleveraging"))
            .otherwise(pl.lit("neutral"))
        )
        .otherwise(pl.lit(None).cast(pl.Utf8))
    )

    result_exprs.append(regime_expr.alias("regime"))

    # Confidence: based on magnitude of changes (larger = more confident)
    confidence_expr = (
        pl.when(price_chg.is_not_null() & oi_chg.is_not_null())
        .then(
            (pl.min_horizontal(
                (price_chg.abs() * 10).clip(0, 1),
                (oi_chg.abs() * 5).clip(0, 1),
            ) * 0.5 + 0.5)
        )
        .otherwise(pl.lit(0.0))
        .alias("regime_confidence")
    )

    result_exprs.append(confidence_expr)

    return merged.select(result_exprs)
