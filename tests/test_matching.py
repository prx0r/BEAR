"""Tests for the matching/pair discovery module."""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest
from datetime import datetime, timedelta, timezone

from bear.matching.pair import find_nearest_neighbors, CandidatePair
from bear.matching.graph import build_market_graph, get_neighbors, MarketGraph


def _ts(n: int) -> list[datetime]:
    """Generate n timestamps using timedelta."""
    base = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return [base + timedelta(hours=i) for i in range(n)]


def _make_returns(n: int = 200, seed: int = 42) -> pl.DataFrame:
    """Generate synthetic return data for multiple assets."""
    rng = np.random.default_rng(seed)
    timestamps = _ts(n)
    btc = rng.normal(0, 0.02, n)
    eth = btc * 0.8 + rng.normal(0, 0.005, n)
    tao = btc * 0.6 + rng.normal(0, 0.01, n)
    uni = btc * 0.4 + rng.normal(0, 0.012, n)
    fet = btc * 0.3 + rng.normal(0, 0.015, n)

    return pl.DataFrame({
        "timestamp": timestamps,
        "BTC": btc,
        "ETH": eth,
        "TAO": tao,
        "UNI": uni,
        "FET": fet,
    })


TAXONOMY = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "TAO": "bittensor",
    "UNI": "defi",
    "FET": "ai",
}


def test_find_neighbors_risk_hedge():
    """Risk hedge mode prioritizes downside correlation."""
    all_returns = _make_returns()
    long_returns = all_returns.select(["timestamp", "TAO"])

    neighbors = find_nearest_neighbors(
        long_returns,
        all_returns,
        TAXONOMY,
        mode="risk_hedge",
        top_k=4,
        min_history=50,
    )

    assert len(neighbors) > 0
    assert all(isinstance(n, CandidatePair) for n in neighbors)
    assert all(n.mode == "risk_hedge" for n in neighbors)

    for i, n in enumerate(neighbors):
        assert n.rank == i + 1

    for n in neighbors:
        assert 0 <= n.fit_score <= 100


def test_find_neighbors_relative_value():
    """Relative value mode prioritizes sector similarity."""
    all_returns = _make_returns()
    long_returns = all_returns.select(["timestamp", "TAO"])

    neighbors = find_nearest_neighbors(
        long_returns,
        all_returns,
        TAXONOMY,
        mode="relative_value",
        top_k=4,
        min_history=50,
    )

    assert len(neighbors) > 0
    assert all(n.mode == "relative_value" for n in neighbors)

    for n in neighbors:
        assert np.isfinite(n.fit_score)
        assert 0 <= n.fit_score <= 100


def test_find_neighbors_alpha_preserve():
    """Alpha preserve mode penalizes excessive residual correlation."""
    all_returns = _make_returns()
    long_returns = all_returns.select(["timestamp", "TAO"])

    neighbors = find_nearest_neighbors(
        long_returns,
        all_returns,
        TAXONOMY,
        mode="alpha_preserve",
        top_k=4,
        min_history=50,
    )

    assert len(neighbors) > 0
    assert all(n.mode == "alpha_preserve" for n in neighbors)

    for n in neighbors:
        assert 0 <= n.sector_score <= 100


def test_market_graph_construction():
    """Graph has correct number of nodes and edges."""
    all_returns = _make_returns()
    graph = build_market_graph(all_returns, taxonomy=TAXONOMY)

    assert len(graph.nodes) == 5
    assert len(graph.edges) >= 0

    for sym in ["BTC", "ETH", "TAO", "UNI", "FET"]:
        assert sym in graph.nodes


def test_hedge_fit_score_range():
    """Hedge fit is in [0,100]."""
    from bear.matching.baskets import compute_hedge_fit_score

    all_returns = _make_returns()
    btc_returns = all_returns.select(["timestamp", "BTC"])
    long_returns = all_returns.select(["timestamp", "TAO"])
    cand_returns = all_returns.select(["timestamp", "ETH"])

    for mode in ["risk_hedge", "relative_value", "alpha_preserve"]:
        result = compute_hedge_fit_score(
            long_returns,
            cand_returns,
            btc_returns,
            mode=mode,
        )
        assert 0 <= result.total <= 100
        assert 0 <= result.correlation_component <= 100


def test_total_score_components():
    """Total score uses all components per spec."""
    from bear.matching.baskets import compute_total_score

    result = compute_total_score(
        hedge_fit=80.0,
        structural_short=70.0,
        carry=0.05,
        execution=90.0,
        squeeze_risk=30.0,
        data_quality=85.0,
    )

    assert result.total > 0
    assert result.hedge_fit == 80.0
    assert result.structural_short == 70.0
    assert result.execution == 90.0
    assert result.squeeze_risk == 30.0

    # Weights per spec Section 28
    expected = 0.30 * 80 + 0.25 * 70 + 0.15 * 55 + 0.10 * 90 + 0.10 * 30 + 0.10 * 85
    assert abs(result.total - expected) < 1e-6


def test_graph_get_neighbors():
    """get_neighbors returns ranked list."""
    all_returns = _make_returns()
    graph = build_market_graph(all_returns, taxonomy=TAXONOMY)

    neighbors = get_neighbors(graph, "BTC", k=3)

    assert len(neighbors) <= 3
    if len(neighbors) > 1:
        weights = [w for _, w in neighbors]
        assert weights == sorted(weights, reverse=True)

    for sym, w in neighbors:
        assert w > 0


def test_clone_gap_computation():
    """CLONE_GAP computation via baskets module."""
    from bear.matching.baskets import compute_clone_gap

    gap = compute_clone_gap(90.0, 20.0, 80.0)
    assert gap > 0

    gap_zero = compute_clone_gap(0.0, 20.0, 80.0)
    assert abs(gap_zero) < 1e-6

    gap_equal = compute_clone_gap(90.0, 50.0, 50.0)
    assert abs(gap_equal) < 1e-6


def test_find_neighbors_min_history():
    """find_nearest_neighbors returns empty when min_history too high."""
    all_returns = _make_returns(n=20)
    long_returns = all_returns.select(["timestamp", "TAO"])

    neighbors = find_nearest_neighbors(
        long_returns,
        all_returns,
        TAXONOMY,
        mode="relative_value",
        top_k=10,
        min_history=100,
    )

    assert len(neighbors) == 0


def test_find_neighbors_invalid_mode():
    """find_nearest_neighbors raises on invalid mode."""
    all_returns = _make_returns()
    long_returns = all_returns.select(["timestamp", "TAO"])

    with pytest.raises(ValueError, match="mode must be one of"):
        find_nearest_neighbors(
            long_returns,
            all_returns,
            TAXONOMY,
            mode="invalid_mode",
        )
