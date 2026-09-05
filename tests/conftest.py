"""Shared fixtures for BEAR test suite.

Generates realistic synthetic data using Polars DataFrames and numpy
random walks. No network calls — all data is self-contained.
"""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest
from datetime import datetime, timedelta, timezone


SYMBOLS = ["BTC", "ETH", "TAO", "UNI", "FET"]
N_DAYS = 90
N_HOURS = N_DAYS * 24  # 2160 hourly candles per symbol


def _random_walk(
    n: int,
    start_price: float,
    drift: float,
    vol: float,
    seed: int,
) -> np.ndarray:
    """Generate a random walk price series."""
    rng = np.random.default_rng(seed)
    returns = rng.normal(drift, vol, n)
    log_prices = np.log(start_price) + np.cumsum(returns)
    return np.exp(log_prices)


def _make_timestamps(n: int, freq_hours: int = 1) -> list[datetime]:
    """Generate timestamps using timedelta to avoid hour overflow."""
    base = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return [base + timedelta(hours=freq_hours * i) for i in range(n)]


@pytest.fixture
def sample_prices() -> pl.DataFrame:
    """Close prices only for return calculations.

    DataFrame with 'timestamp' column and one column per symbol (BTC, ETH,
    TAO, UNI, FET).  Each column contains close prices generated via
    random walk with different drift/vol parameters.
    """
    timestamps = _make_timestamps(N_HOURS)
    params = {
        "BTC": (60_000.0, 0.00005, 0.015, 100),
        "ETH": (3_500.0, 0.00004, 0.020, 200),
        "TAO": (600.0, 0.00006, 0.035, 300),
        "UNI": (12.0, 0.00003, 0.025, 400),
        "FET": (2.5, 0.00004, 0.030, 500),
    }
    data = {"timestamp": timestamps}
    for sym, (start, drift, vol, seed) in params.items():
        data[sym] = _random_walk(N_HOURS, start, drift, vol, seed)

    return pl.DataFrame(data)


@pytest.fixture
def sample_candles_df(sample_prices: pl.DataFrame) -> pl.DataFrame:
    """90 days of hourly OHLCV for 5 symbols (BTC, ETH, TAO, UNI, FET).

    Expands close prices into full OHLCV candle records. High/low are
    derived by adding/subtracting a small random fraction of the close.
    """
    rng = np.random.default_rng(999)
    rows = []

    prices_dict = {sym: sample_prices[sym].to_list() for sym in SYMBOLS}
    timestamps = sample_prices["timestamp"].to_list()

    for i, ts in enumerate(timestamps):
        for sym in SYMBOLS:
            c = prices_dict[sym][i]
            noise = rng.uniform(0.001, 0.015)
            h = c * (1 + noise)
            lo = c * (1 - noise)
            o = c * (1 + rng.uniform(-0.005, 0.005))
            vol = rng.uniform(500_000, 5_000_000)
            tc = int(rng.integers(100, 5000))
            rows.append({
                "symbol": sym,
                "interval": "1h",
                "open_time": ts,
                "close_time": ts + timedelta(hours=1),
                "open": o,
                "high": h,
                "low": lo,
                "close": c,
                "volume": vol,
                "trade_count": tc,
                "ingested_at": datetime.now(timezone.utc),
            })

    return pl.DataFrame(rows)


@pytest.fixture
def sample_funding_df() -> pl.DataFrame:
    """90 days of hourly funding for 5 symbols.

    Funding rates are generated around a small positive mean with occasional
    spikes, reflecting realistic Hyperliquid funding dynamics.
    """
    rng = np.random.default_rng(777)
    timestamps = _make_timestamps(N_HOURS)
    rows = []

    base_rates = {
        "BTC": 0.00005,
        "ETH": 0.00008,
        "TAO": 0.00012,
        "UNI": 0.00003,
        "FET": 0.00010,
    }

    for sym in SYMBOLS:
        base = base_rates[sym]
        for ts in timestamps:
            rate = base + rng.normal(0, base * 2)
            rows.append({
                "symbol": sym,
                "timestamp": ts,
                "funding_rate": rate,
            })

    return pl.DataFrame(rows)


@pytest.fixture
def sample_market_data() -> pl.DataFrame:
    """Mock universe with all required fields for a market context."""
    rows = []
    for sym in SYMBOLS:
        rows.append({
            "symbol": sym,
            "adv_usd": 50_000_000.0,
            "open_interest_usd": 100_000_000.0,
            "spread_bps": 1.5,
            "depth_usd": 5_000_000.0,
            "mark_px": {"BTC": 60000, "ETH": 3500, "TAO": 600, "UNI": 12, "FET": 2.5}[sym],
            "funding": 0.0001,
            "structural_short_score": 50.0,
            "squeeze_score": 20.0,
        })
    return pl.DataFrame(rows)


@pytest.fixture
def sample_tokenomics() -> pl.DataFrame:
    """Mock tokenomics data for structural short scoring."""
    rows = [
        {
            "symbol": "BTC",
            "fdv_overhang": 1.0,
            "dilution_90d": 0.001,
            "unlock_to_adv": 0.01,
            "insider_unlock_share": 0.0,
            "emission_rate": 0.0,
            "relative_momentum_30d": 0.05,
            "long_term_momentum_90d": 0.15,
            "value_capture": 0.1,
            "activity_change_30d": 0.02,
        },
        {
            "symbol": "ETH",
            "fdv_overhang": 1.02,
            "dilution_90d": 0.003,
            "unlock_to_adv": 0.05,
            "insider_unlock_share": 0.01,
            "emission_rate": 0.005,
            "relative_momentum_30d": 0.03,
            "long_term_momentum_90d": 0.10,
            "value_capture": 0.2,
            "activity_change_30d": 0.01,
        },
        {
            "symbol": "TAO",
            "fdv_overhang": 2.5,
            "dilution_90d": 0.05,
            "unlock_to_adv": 0.30,
            "insider_unlock_share": 0.15,
            "emission_rate": 0.08,
            "relative_momentum_30d": -0.10,
            "long_term_momentum_90d": -0.05,
            "value_capture": 0.8,
            "activity_change_30d": -0.03,
        },
        {
            "symbol": "UNI",
            "fdv_overhang": 1.8,
            "dilution_90d": 0.02,
            "unlock_to_adv": 0.15,
            "insider_unlock_share": 0.08,
            "emission_rate": 0.03,
            "relative_momentum_30d": -0.02,
            "long_term_momentum_90d": 0.05,
            "value_capture": 0.5,
            "activity_change_30d": -0.01,
        },
        {
            "symbol": "FET",
            "fdv_overhang": 3.0,
            "dilution_90d": 0.08,
            "unlock_to_adv": 0.50,
            "insider_unlock_share": 0.25,
            "emission_rate": 0.12,
            "relative_momentum_30d": -0.15,
            "long_term_momentum_90d": -0.20,
            "value_capture": 1.2,
            "activity_change_30d": -0.05,
        },
    ]
    return pl.DataFrame(rows)


@pytest.fixture
def sample_returns_df(sample_prices: pl.DataFrame) -> pl.DataFrame:
    """Log returns computed from sample_prices."""
    from bear.features.returns import compute_log_returns
    return compute_log_returns(sample_prices)


@pytest.fixture
def sample_btc_returns(sample_returns_df: pl.DataFrame) -> pl.DataFrame:
    """BTC return series as a standalone DataFrame."""
    return sample_returns_df.select(["timestamp", "BTC"])


@pytest.fixture
def sample_eth_returns(sample_returns_df: pl.DataFrame) -> pl.DataFrame:
    """ETH return series as a standalone DataFrame."""
    return sample_returns_df.select(["timestamp", "ETH"])
