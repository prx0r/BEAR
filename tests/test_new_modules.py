"""Tests for newly created modules: risk, combo, hub, hl_models.

Uses synthetic data only. No network calls. Fixtures from conftest.py where possible.
"""

from __future__ import annotations

import asyncio

import numpy as np
import polars as pl
import pytest
from datetime import datetime, timedelta, timezone

from bear.risk import RiskGuardrails, check_order, check_portfolio_health
from bear.combo import greedy_forward_search, lasso_select, SelectionResult
from bear.hub import EventBus, HubStatus, ComponentHealth, CONNECTED, STALE, OFFLINE
from bear.hl_models import parse_meta_and_contexts, ParsedUniverse, AssetMeta, AssetContext
from bear.features.evaluator import (
    compute_rank_ic,
    compute_ic_series,
    compute_ic_ir,
    apply_fdr_correction,
    evaluate_factor,
    EvaluatorConfig,
)
from bear.backtest.engine import BacktestEngine, BacktestConfig


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_returns() -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Synthetic long and candidate returns for combo/backtest tests."""
    rng = np.random.default_rng(42)
    T, N = 200, 5
    long = rng.normal(0.001, 0.02, T)
    cands = np.column_stack([
        long * (0.5 + rng.uniform(0, 0.5)) + rng.normal(0, 0.01, T)
        for _ in range(N)
    ])
    names = ["ALPHA", "BETA", "GAMMA", "DELTA", "EPSILON"]
    return long, cands, names


@pytest.fixture
def sample_equity_curve() -> list[float]:
    """Equity curve starting at 1M, growing with a drawdown."""
    rng = np.random.default_rng(99)
    eq = [1_000_000.0]
    for _ in range(99):
        ret = rng.normal(0.0005, 0.01)
        eq.append(eq[-1] * (1 + ret))
    return eq


# ---------------------------------------------------------------------------
# Evaluator: IC computation
# ---------------------------------------------------------------------------

def test_evaluator_ic_computation():
    """compute_rank_ic returns a finite Spearman correlation."""
    rng = np.random.default_rng(42)
    n = 500
    factor = pl.Series("factor", rng.normal(0, 1, n))
    # Forward returns correlated with factor
    returns = pl.Series("ret", factor.to_numpy() * 0.3 + rng.normal(0, 0.5, n))

    ic = compute_rank_ic(factor, returns)

    assert np.isfinite(ic)
    assert -1.0 <= ic <= 1.0
    # Should be positive since we induced correlation
    assert ic > 0.1


def test_evaluator_ic_series():
    """compute_ic_series produces rolling IC values."""
    rng = np.random.default_rng(42)
    n = 300
    factor = pl.Series("f", rng.normal(0, 1, n))
    returns = pl.Series("r", factor.to_numpy() * 0.2 + rng.normal(0, 0.5, n))

    ic_series = compute_ic_series(factor, returns, window=50)

    assert len(ic_series) > 0
    vals = ic_series.to_list()
    # IC series may contain NaN for degenerate windows; most should be finite
    finite_count = sum(1 for v in vals if np.isfinite(v))
    assert finite_count > len(vals) // 2


def test_evaluator_ic_ir():
    """compute_ic_ir is mean/std of IC series."""
    rng = np.random.default_rng(42)
    ic_vals = rng.normal(0.05, 0.02, 100)
    ic_series = pl.Series("ic", ic_vals)

    icir = compute_ic_ir(ic_series)

    expected = float(np.mean(ic_vals) / np.std(ic_vals, ddof=1))
    assert abs(icir - expected) < 1e-6


# ---------------------------------------------------------------------------
# Evaluator: FDR correction
# ---------------------------------------------------------------------------

def test_evaluator_fdr_correction():
    """apply_fdr_correction adjusts p-values via BH procedure."""
    raw_pvals = [0.01, 0.04, 0.03, 0.50, 0.80]

    adjusted = apply_fdr_correction(raw_pvals)

    assert len(adjusted) == len(raw_pvals)
    assert all(a is not None for a in adjusted)
    # BH correction should increase small p-values
    assert adjusted[0] >= raw_pvals[0]
    # All adjusted values should be <= 1.0
    assert all(a <= 1.0 for a in adjusted if a is not None)
    # Ordering: smaller raw p-values should get smaller adjusted p-values
    assert adjusted[0] <= adjusted[3]


def test_evaluator_fdr_correction_with_none():
    """FDR correction preserves None entries."""
    raw_pvals = [0.01, None, 0.03, None, 0.80]

    adjusted = apply_fdr_correction(raw_pvals)

    assert adjusted[1] is None
    assert adjusted[3] is None
    assert adjusted[0] is not None
    assert adjusted[2] is not None


def test_evaluator_full_evaluate():
    """evaluate_factor produces a FactorEvaluation with all fields."""
    from bear.features.evaluator import FactorEvaluation

    rng = np.random.default_rng(42)
    n = 500
    factor_df = pl.DataFrame({"factor": rng.normal(0, 1, n)})
    returns_df = pl.DataFrame({"forward_return": rng.normal(0, 0.02, n) + rng.normal(0, 1, n) * 0.01})

    config = EvaluatorConfig(ic_window=100, min_periods=30)
    result = evaluate_factor(factor_df, returns_df, config=config)

    assert isinstance(result, FactorEvaluation)
    assert result.name == "factor"
    assert np.isfinite(result.rank_ic)
    assert np.isfinite(result.t_stat)
    assert result.n_periods > 0


# ---------------------------------------------------------------------------
# Combo: greedy forward search
# ---------------------------------------------------------------------------

def test_combo_greedy_search(sample_returns):
    """Greedy forward search selects names and produces valid weights."""
    long, cands, names = sample_returns

    result = greedy_forward_search(long, cands, names, max_names=3)

    assert isinstance(result, SelectionResult)
    assert len(result.selected_indices) <= 3
    assert len(result.selected_names) == len(result.selected_indices)
    assert len(result.weights) > 0
    assert result.n_iterations > 0
    assert len(result.objective_history) > 0

    # Objective should decrease (hedging error shrinks)
    for i in range(1, len(result.objective_history)):
        assert result.objective_history[i] <= result.objective_history[i - 1] + 1e-10

    # Selected names should be from the input
    for name in result.selected_names:
        assert name in names


def test_combo_greedy_search_max_names(sample_returns):
    """Greedy search respects max_names limit."""
    long, cands, names = sample_returns

    result = greedy_forward_search(long, cands, names, max_names=2)

    assert len(result.selected_indices) <= 2


def test_combo_greedy_search_insufficient_candidates():
    """Greedy search handles case with no valid candidates."""
    rng = np.random.default_rng(42)
    long = rng.normal(0, 0.02, 100)
    cands = np.zeros((100, 3))
    names = ["A", "B", "C"]

    result = greedy_forward_search(long, cands, names, max_names=3)

    # All candidates are zero, no improvement possible
    assert len(result.selected_indices) == 0


# ---------------------------------------------------------------------------
# Combo: LASSO selection
# ---------------------------------------------------------------------------

def test_combo_lasso_select(sample_returns):
    """LASSO selection produces sparse basket."""
    long, cands, names = sample_returns

    result = lasso_select(long, cands, names, alpha=0.01)

    assert isinstance(result, SelectionResult)
    assert len(result.selected_indices) <= len(names)
    assert result.n_iterations > 0
    assert len(result.objective_history) == 1

    # Weights for selected names should be finite
    for name, w in result.weights.items():
        assert np.isfinite(w)
        assert name in names


def test_combo_lasso_select_high_alpha_is_sparser(sample_returns):
    """Higher alpha produces sparser solutions."""
    long, cands, names = sample_returns

    result_low = lasso_select(long, cands, names, alpha=0.001)
    result_high = lasso_select(long, cands, names, alpha=1.0)

    # Higher alpha should select fewer or equal names
    assert len(result_high.selected_indices) <= len(result_low.selected_indices)


# ---------------------------------------------------------------------------
# Vectorized backtest: returns
# ---------------------------------------------------------------------------

def test_vectorized_backtest_returns(sample_prices):
    """Backtest engine produces equity curve from prices."""
    from bear.backtest.costs import CostEstimate

    prices = sample_prices
    # Convert wide price format to long format for backtest engine
    symbols = ["BTC", "ETH"]
    rows = []
    for sym in symbols:
        for i in range(prices.height):
            rows.append({
                "timestamp": prices["timestamp"][i],
                "symbol": sym,
                "close": prices[sym][i],
                "high": prices[sym][i] * 1.01,
                "low": prices[sym][i] * 0.99,
                "volume": 1e6,
                "spread": 0.5,
            })
    long_df = pl.DataFrame(rows)

    funding = pl.DataFrame({
        "timestamp": prices["timestamp"].to_list(),
        "funding_rate": [0.0001] * prices.height,
    })

    config = BacktestConfig(
        long_symbol="BTC",
        short_symbols=["ETH"],
        start_date="2025-01-01",
        end_date="2025-04-01",
        walk_forward=False,
    )

    engine = BacktestEngine(config)
    result = engine.run(long_df, funding)

    assert result.equity_curve.height > 0
    assert "equity" in result.equity_curve.columns
    assert result.metrics.total_return != 0 or result.equity_curve.height <= 1


# ---------------------------------------------------------------------------
# Vectorized backtest: funding
# ---------------------------------------------------------------------------

def test_vectorized_backtest_funding():
    """Funding PnL series is correctly computed for each timestamp."""
    from bear.backtest.funding import compute_funding_pnl_series

    n = 50
    base = datetime(2025, 1, 1, tzinfo=timezone.utc)
    ts_list = [base + timedelta(hours=i) for i in range(n)]
    timestamps = np.array(ts_list)
    rng = np.random.default_rng(42)

    funding_rates = pl.DataFrame({
        "timestamp": ts_list,
        "funding_rate": rng.normal(0.0001, 0.00005, n),
    })

    short_exposures = np.ones(n) * 0.5
    pnl = compute_funding_pnl_series(funding_rates, short_exposures, timestamps)

    assert len(pnl) == n
    assert np.any(pnl != 0)
    # Each PnL should equal rate * exposure
    for i in range(n):
        expected = float(funding_rates["funding_rate"][i]) * short_exposures[i]
        assert abs(pnl[i] - expected) < 1e-10


# ---------------------------------------------------------------------------
# Risk guardrails: check_order
# ---------------------------------------------------------------------------

def test_risk_guardrails_check_order():
    """Order passes guardrails when within limits."""
    guardrails = RiskGuardrails()

    portfolio = {
        "long_exposure": 1_000_000.0,
        "short_exposure": 200_000.0,
        "adv_usd": 50_000_000.0,
        "squeeze_risk": 30.0,
        "name_weight": 0.10,
    }

    order = {"side": "sell", "size_usd": 100_000.0}

    allowed, reason = check_order(guardrails, portfolio, order)

    assert allowed is True
    assert reason == "order allowed"


def test_risk_guardrails_check_order_liquidity():
    """Order rejected when ADV too low."""
    guardrails = RiskGuardrails(min_adv_usd=500_000)

    portfolio = {
        "long_exposure": 1_000_000.0,
        "short_exposure": 0.0,
        "adv_usd": 100_000.0,  # below minimum
        "squeeze_risk": 20.0,
        "name_weight": 0.05,
    }

    order = {"side": "sell", "size_usd": 50_000.0}

    allowed, reason = check_order(guardrails, portfolio, order)

    assert allowed is False
    assert "ADV" in reason


def test_risk_guardrails_check_order_squeeze():
    """Order rejected when squeeze risk too high."""
    guardrails = RiskGuardrails(max_squeeze_risk=50.0)

    portfolio = {
        "long_exposure": 1_000_000.0,
        "short_exposure": 0.0,
        "adv_usd": 50_000_000.0,
        "squeeze_risk": 75.0,
        "name_weight": 0.05,
    }

    order = {"side": "sell", "size_usd": 50_000.0}

    allowed, reason = check_order(guardrails, portfolio, order)

    assert allowed is False
    assert "squeeze" in reason


def test_risk_guardrails_check_order_leverage():
    """Order rejected when leverage would exceed max."""
    guardrails = RiskGuardrails(max_leverage=2.0)

    portfolio = {
        "long_exposure": 100_000.0,
        "short_exposure": 150_000.0,
        "adv_usd": 50_000_000.0,
        "squeeze_risk": 20.0,
        "name_weight": 0.10,
    }

    order = {"side": "sell", "size_usd": 100_000.0}

    allowed, reason = check_order(guardrails, portfolio, order)

    assert allowed is False
    assert "leverage" in reason


def test_risk_guardrails_check_order_kill_switch():
    """Order rejected when kill switch is triggered."""
    guardrails = RiskGuardrails(kill_switch_enabled=True)

    portfolio = {
        "long_exposure": 1_000_000.0,
        "short_exposure": 0.0,
        "adv_usd": 50_000_000.0,
        "squeeze_risk": 20.0,
        "name_weight": 0.05,
        "kill_switch_triggered": True,
    }

    order = {"side": "sell", "size_usd": 50_000.0}

    allowed, reason = check_order(guardrails, portfolio, order)

    assert allowed is False
    assert "kill switch" in reason


# ---------------------------------------------------------------------------
# Risk guardrails: portfolio health (drawdown breach)
# ---------------------------------------------------------------------------

def test_risk_guardrails_drawdown_breach():
    """Portfolio health check detects drawdown breach."""
    guardrails = RiskGuardrails(max_drawdown_pct=0.10, max_daily_loss_pct=0.50)

    # Equity curve: peak at 1.1M, trough at 0.95M = 13.6% drawdown
    # (1.1M - 0.95M) / 1.1M = 13.6%
    equity_curve = [1_000_000, 1_020_000, 1_040_000, 1_060_000, 1_080_000,
                    1_100_000, 1_080_000, 1_060_000, 1_040_000, 950_000]

    healthy, reason = check_portfolio_health(guardrails, equity_curve)

    assert healthy is False
    assert "drawdown" in reason


def test_risk_guardrails_daily_loss_breach():
    """Portfolio health check detects daily loss breach."""
    guardrails = RiskGuardrails(max_daily_loss_pct=0.05)

    # Last two points: 1M -> 0.94M = -6% daily loss
    equity_curve = [1_000_000, 1_010_000, 940_000]

    healthy, reason = check_portfolio_health(guardrails, equity_curve)

    assert healthy is False
    assert "daily loss" in reason


def test_risk_guardrails_healthy_portfolio():
    """Portfolio health check passes for healthy equity curve."""
    guardrails = RiskGuardrails(max_drawdown_pct=0.20, max_daily_loss_pct=0.10)

    equity_curve = [1_000_000, 1_020_000, 1_015_000, 1_030_000, 1_025_000]

    healthy, reason = check_portfolio_health(guardrails, equity_curve)

    assert healthy is True
    assert reason == "portfolio healthy"


def test_risk_guardrails_empty_equity():
    """Empty equity curve is treated as healthy (insufficient data)."""
    guardrails = RiskGuardrails()

    healthy, reason = check_portfolio_health(guardrails, [])

    assert healthy is True
    assert "insufficient" in reason


def test_risk_guardrails_frozen():
    """RiskGuardrails is immutable (frozen dataclass)."""
    guardrails = RiskGuardrails()

    with pytest.raises(AttributeError):
        guardrails.max_leverage = 10.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Hub: event bus
# ---------------------------------------------------------------------------

def test_hub_event_bus():
    """EventBus dispatches events to subscribers."""
    bus = EventBus()
    received: list[str] = []

    def on_candle(coin, interval, candle):
        received.append(coin)

    bus.on("new_candle", on_candle)

    asyncio.run(bus.emit("new_candle", "BTC", "1h", {"close": 60000}))

    assert received == ["BTC"]


def test_hub_event_bus_multiple_subscribers():
    """EventBus notifies all subscribers for an event type."""
    bus = EventBus()
    results_a: list[int] = []
    results_b: list[int] = []

    bus.on("price_update", lambda mids: results_a.append(1))
    bus.on("price_update", lambda mids: results_b.append(2))

    asyncio.run(bus.emit("price_update", {"BTC": 60000}))

    assert results_a == [1]
    assert results_b == [2]


def test_hub_event_bus_off():
    """EventBus.off removes a subscriber."""
    bus = EventBus()
    received: list[str] = []

    def handler(coin):
        received.append(coin)

    bus.on("new_funding", handler)
    bus.off("new_funding", handler)

    asyncio.run(bus.emit("new_funding", "ETH"))

    assert received == []


def test_hub_event_bus_invalid_event():
    """EventBus raises on unknown event type."""
    bus = EventBus()

    with pytest.raises(ValueError, match="Unknown event type"):
        bus.on("invalid_event", lambda: None)


# ---------------------------------------------------------------------------
# Hub: health tracking
# ---------------------------------------------------------------------------

def test_hub_health_tracking():
    """HubStatus tracks component health and aggregate status."""
    status = HubStatus()

    # Initially all offline
    assert not status.all_connected
    assert not status.degraded

    # Set all to connected
    for h in [status.universe, status.candles, status.funding, status.books, status.ws]:
        h.status = CONNECTED

    assert status.all_connected
    assert not status.degraded


def test_hub_health_degraded():
    """HubStatus detects degraded state (some connected, some not)."""
    status = HubStatus()

    status.universe.status = CONNECTED
    status.candles.status = CONNECTED
    status.funding.status = STALE
    status.books.status = OFFLINE
    status.ws.status = CONNECTED

    assert not status.all_connected
    assert status.degraded


def test_hub_health_as_dict():
    """HubStatus.as_dict produces serializable output."""
    status = HubStatus()
    d = status.as_dict()

    assert "started_at" in d
    assert "all_connected" in d
    assert "degraded" in d
    assert "components" in d
    assert "events" in d
    assert isinstance(d["components"], dict)


def test_hub_component_health():
    """ComponentHealth tracks per-component status."""
    h = ComponentHealth("candles")

    assert h.name == "candles"
    assert h.status == OFFLINE
    assert h.last_update == 0.0
    assert h.error is None

    h.status = CONNECTED
    h.last_update = 12345.0
    h.error = "test error"

    assert h.status == CONNECTED
    assert h.last_update == 12345.0
    assert h.error == "test error"


# ---------------------------------------------------------------------------
# HL models: parse
# ---------------------------------------------------------------------------

def test_hl_models_parse():
    """parse_meta_and_contexts produces typed objects from raw JSON."""
    raw = [
        [
            {"name": "BTC", "szDecimals": 5, "maxLeverage": 50, "isDelisted": False},
            {"name": "ETH", "szDecimals": 4, "maxLeverage": 50, "isDelisted": False},
        ],
        [
            {"markPx": "60000", "funding": "0.0001", "openInterest": "5000000"},
            {"markPx": "3500", "funding": "0.0002", "openInterest": "2000000"},
        ],
    ]

    universe = parse_meta_and_contexts(raw)

    assert isinstance(universe, ParsedUniverse)
    assert len(universe.assets) == 2
    assert len(universe.contexts) == 2

    btc_meta = universe.assets[0]
    assert isinstance(btc_meta, AssetMeta)
    assert btc_meta.name == "BTC"
    assert btc_meta.sz_decimals == 5
    assert btc_meta.max_leverage == 50

    btc_ctx = universe.contexts[0]
    assert isinstance(btc_ctx, AssetContext)
    assert btc_ctx.mark_px == 60000.0
    assert btc_ctx.funding == 0.0001
    assert btc_ctx.open_interest == 5_000_000.0


def test_hl_models_parse_numeric_strings():
    """Parsing converts all numeric strings to floats."""
    raw = [
        [{"name": "SOL", "szDecimals": 2, "maxLeverage": 20}],
        [{"markPx": "150.5", "funding": "-0.0003", "dayNtlVlm": "1000000"}],
    ]

    universe = parse_meta_and_contexts(raw)

    assert universe.contexts[0].mark_px == 150.5
    assert universe.contexts[0].funding == -0.0003
    assert universe.contexts[0].day_ntl_vlm == 1_000_000.0


def test_hl_models_active_assets():
    """active_assets filters out delisted assets."""
    raw = [
        [
            {"name": "BTC", "szDecimals": 5, "maxLeverage": 50, "isDelisted": False},
            {"name": "OLD", "szDecimals": 2, "maxLeverage": 10, "isDelisted": True},
        ],
        [
            {"markPx": "60000"},
            {"markPx": "10"},
        ],
    ]

    universe = parse_meta_and_contexts(raw)

    assert len(universe.assets) == 2
    assert len(universe.active_assets) == 1
    assert universe.active_assets[0].name == "BTC"


def test_hl_models_get_context():
    """get_context returns the correct context by name."""
    raw = [
        [
            {"name": "BTC", "szDecimals": 5, "maxLeverage": 50},
            {"name": "ETH", "szDecimals": 4, "maxLeverage": 50},
        ],
        [
            {"markPx": "60000"},
            {"markPx": "3500"},
        ],
    ]

    universe = parse_meta_and_contexts(raw)

    ctx = universe.get_context("ETH")
    assert ctx is not None
    assert ctx.mark_px == 3500.0

    missing = universe.get_context("SOL")
    assert missing is None


def test_hl_models_parse_invalid():
    """parse_meta_and_contexts raises on invalid structure."""
    with pytest.raises(ValueError, match="Expected"):
        parse_meta_and_contexts("not a list")

    with pytest.raises(ValueError, match="different lengths"):
        parse_meta_and_contexts([["BTC"], [{"markPx": "1"}, {"markPx": "2"}]])
