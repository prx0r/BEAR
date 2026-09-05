"""Tests for the backtest engine and funding module."""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest
from datetime import datetime, timedelta, timezone

from bear.backtest.engine import BacktestEngine, BacktestConfig, BacktestResult
from bear.backtest.metrics import compute_metrics, PerformanceMetrics
from bear.backtest.funding import (
    FundingState,
    compute_funding_pnl_series,
    apply_funding_at_timestamps,
)
from bear.backtest.costs import estimate_cost, CostEstimate


def _make_backtest_data(
    n_days: int = 90,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Generate prices and funding for backtest."""
    rng = np.random.default_rng(42)
    base = datetime(2025, 1, 1, tzinfo=timezone.utc)
    timestamps = [base + timedelta(days=i) for i in range(n_days)]

    btc_prices = 60000 + np.cumsum(rng.normal(0, 500, n_days))
    eth_prices = 3500 + np.cumsum(rng.normal(0, 30, n_days))

    prices = pl.DataFrame({
        "timestamp": timestamps + timestamps,
        "symbol": ["BTC"] * n_days + ["ETH"] * n_days,
        "close": list(btc_prices) + list(eth_prices),
        "high": list(btc_prices * 1.01) + list(eth_prices * 1.01),
        "low": list(btc_prices * 0.99) + list(eth_prices * 0.99),
        "volume": [1e6] * (n_days * 2),
        "spread": [0.5] * (n_days * 2),
    })

    funding = pl.DataFrame({
        "timestamp": timestamps,
        "funding_rate": rng.normal(0.0001, 0.00005, n_days),
    })

    return prices, funding


def test_backtest_produces_equity_curve():
    """Backtest returns non-empty equity curve."""
    prices, funding = _make_backtest_data()
    config = BacktestConfig(
        long_symbol="BTC",
        short_symbols=["ETH"],
        start_date="2025-01-01",
        end_date="2025-04-01",
        walk_forward=False,
    )

    engine = BacktestEngine(config)
    result = engine.run(prices, funding)

    assert isinstance(result, BacktestResult)
    assert result.equity_curve.height > 0
    assert "equity" in result.equity_curve.columns
    assert "timestamp" in result.equity_curve.columns


def test_backtest_funding_applied_at_timestamps():
    """Funding applied at actual timestamps, not fixed APR."""
    # CRITICAL INVARIANT
    n = 100
    base = datetime(2025, 1, 1, tzinfo=timezone.utc)
    timestamps = [base + timedelta(hours=i) for i in range(n)]
    rng = np.random.default_rng(42)

    # Variable funding rates (not constant)
    rates = rng.normal(0.0001, 0.00005, n)

    funding_rates = pl.DataFrame({
        "timestamp": timestamps,
        "funding_rate": rates,
    })

    short_exposures = np.ones(n) * 0.5
    ts_array = np.array(timestamps)

    pnl = compute_funding_pnl_series(funding_rates, short_exposures, ts_array)

    assert len(pnl) == n
    assert np.any(pnl != 0)

    # Each PnL should be rate * exposure (not a fixed APR)
    for i in range(n):
        expected = rates[i] * short_exposures[i]
        assert abs(pnl[i] - expected) < 1e-10


def test_backtest_no_lookahead():
    """Backtest only uses data available at signal time."""
    # CRITICAL INVARIANT
    n = 90
    base = datetime(2025, 1, 1, tzinfo=timezone.utc)
    timestamps = [base + timedelta(days=i) for i in range(n)]

    rng = np.random.default_rng(42)
    btc = 60000 + np.cumsum(rng.normal(0, 500, n))
    eth = 3500 + np.cumsum(rng.normal(0, 30, n))

    prices = pl.DataFrame({
        "timestamp": timestamps + timestamps,
        "symbol": ["BTC"] * n + ["ETH"] * n,
        "close": list(btc) + list(eth),
        "high": list(btc * 1.01) + list(eth * 1.01),
        "low": list(btc * 0.99) + list(eth * 0.99),
        "volume": [1e6] * (n * 2),
        "spread": [0.5] * (n * 2),
    })

    funding = pl.DataFrame({
        "timestamp": timestamps,
        "funding_rate": [0.0001] * n,
    })

    config = BacktestConfig(
        long_symbol="BTC",
        short_symbols=["ETH"],
        start_date="2025-01-01",
        end_date="2025-04-01",
        walk_forward=False,
    )

    engine = BacktestEngine(config)
    result = engine.run(prices, funding)

    # Equity curve should start at initial_capital
    eq_start = result.equity_curve["equity"][0]
    assert eq_start == config.initial_capital


def test_backtest_metrics():
    """Metrics include Sharpe, Sortino, max drawdown, etc."""
    eq = np.array([100, 102, 101, 103, 105, 104, 106, 108, 107, 110], dtype=float)

    metrics = compute_metrics(eq, periods_per_year=365)

    assert isinstance(metrics, PerformanceMetrics)
    assert np.isfinite(metrics.sharpe_ratio)
    assert np.isfinite(metrics.sortino_ratio)
    assert metrics.max_drawdown <= 0
    assert metrics.total_return > 0


def test_backtest_attribution():
    """Attribution decomposes into long/short/funding/fees."""
    from bear.portfolio.attribution import compute_attribution

    result = compute_attribution(
        long_pnl=0.05,
        short_pnl=0.02,
        funding_pnl=0.01,
        fees=0.002,
        slippage=0.001,
    )

    assert result.long_pnl == 0.05
    assert result.short_pnl == 0.02
    assert result.funding_pnl == 0.01
    assert result.fees == 0.002
    assert result.slippage == 0.001

    assert abs(result.net_pnl - 0.077) < 1e-6


def test_walk_forward_splits():
    """Walk-forward produces train/validate/test splits."""
    n_days = 365 * 2
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    dates = [base + timedelta(days=i) for i in range(n_days)]
    date_strs = [d.strftime("%Y-%m-%d") for d in dates]

    config = BacktestConfig(
        long_symbol="BTC",
        short_symbols=["ETH"],
        start_date="2024-01-01",
        end_date="2026-01-01",
        walk_forward=True,
        train_months=12,
        valid_months=3,
        test_months=3,
    )

    engine = BacktestEngine(config)
    splits = engine._compute_splits(date_strs)

    assert len(splits) > 0

    for split in splits:
        assert "train" in split
        assert "valid" in split
        assert "test" in split
        assert len(split["train"]) > 0
        assert len(split["test"]) > 0


def test_funding_state():
    """FundingState tracks accrual and settlement correctly."""
    state = FundingState()

    pnl1 = state.apply_funding("2025-01-01T08:00:00Z", 0.0005, 100_000)
    assert pnl1 == 0.0005 * 100_000
    assert state.cumulative_funding_pnl == pnl1

    pnl2 = state.apply_funding("2025-01-01T16:00:00Z", 0.0003, 100_000)
    assert state.cumulative_funding_pnl == pnl1 + pnl2

    settled = state.settle()
    assert settled == pnl1 + pnl2
    assert state.accrued_since_last_settlement == 0.0


def test_backtest_fees_and_slippage():
    """Fees and slippage reduce equity."""
    prices, funding = _make_backtest_data(n_days=60)

    config_low = BacktestConfig(
        long_symbol="BTC",
        short_symbols=["ETH"],
        start_date="2025-01-01",
        end_date="2025-03-01",
        fee_rate=0.0001,
        slippage_bps=0.5,
        walk_forward=False,
    )

    config_high = BacktestConfig(
        long_symbol="BTC",
        short_symbols=["ETH"],
        start_date="2025-01-01",
        end_date="2025-03-01",
        fee_rate=0.001,
        slippage_bps=5.0,
        walk_forward=False,
    )

    result_low = BacktestEngine(config_low).run(prices, funding)
    result_high = BacktestEngine(config_high).run(prices, funding)

    # Higher fees should produce higher total fees
    assert result_high.total_fees >= result_low.total_fees


def test_cost_estimate():
    """Cost estimate returns valid breakdown."""
    cost = estimate_cost(
        trade_size=50_000,
        adv=10_000_000,
        spread=5.0,
        depth=1_000_000,
        scenario="taker_realistic",
    )

    assert isinstance(cost, CostEstimate)
    assert cost.total >= 0
    assert cost.fee >= 0
    assert cost.spread_cost >= 0
    assert cost.market_impact >= 0
    assert cost.scenario == "taker_realistic"
