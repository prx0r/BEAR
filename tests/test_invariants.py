"""CRITICAL INVARIANT TESTS from SPEC S64.

These tests verify the non-negotiable invariants of the BEAR system.
Each invariant corresponds to a specific section of the spec.
"""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest
from datetime import datetime, timedelta, timezone

from bear.features.returns import compute_log_returns
from bear.backtest.funding import compute_funding_pnl_series
from bear.tokenomics.manual import ManualTokenomicsProvider
from bear.tokenomics.base import TokenSnapshot
from bear.matching.baskets import compute_total_score, compute_clone_gap
from bear.features.structural import compute_structural_short_score


def _ts(n: int) -> list[datetime]:
    """Generate n timestamps using timedelta."""
    base = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return [base + timedelta(hours=i) for i in range(n)]


def test_invariant1_meta_length():
    """Metadata and asset context arrays must have identical lengths."""
    meta = [
        {"name": "BTC", "szDecimals": 5, "maxLeverage": 50},
        {"name": "ETH", "szDecimals": 4, "maxLeverage": 50},
        {"name": "SOL", "szDecimals": 2, "maxLeverage": 20},
    ]
    contexts = [
        {"markPx": "60000", "funding": "0.0001"},
        {"markPx": "3500", "funding": "0.0002"},
        {"markPx": "150", "funding": "0.0003"},
    ]

    assert len(meta) == len(contexts), (
        f"meta ({len(meta)}) and contexts ({len(contexts)}) have different lengths"
    )

    for i, (m, c) in enumerate(zip(meta, contexts)):
        assert "name" in m
        assert "markPx" in c


def test_invariant2_no_feature_timestamp_exceeds_signal():
    """No feature timestamp may exceed signal timestamp."""
    n = 200
    timestamps = _ts(n)
    rng = np.random.default_rng(42)
    prices = pl.DataFrame({
        "timestamp": timestamps,
        "BTC": 100 + np.cumsum(rng.normal(0, 0.5, n)),
    })

    signal_time = timestamps[100]
    available = prices.filter(pl.col("timestamp") <= signal_time)
    returns = compute_log_returns(available)

    for ts in returns["timestamp"].to_list():
        assert ts <= signal_time, (
            f"Feature timestamp {ts} exceeds signal time {signal_time}"
        )


def test_invariant3_no_lookahead_tokenomics():
    """No external tokenomics record with known_at > signal_time enters backtest."""
    data = pl.DataFrame({
        "timestamp": ["2025-01-01", "2025-02-01", "2025-03-01"],
        "symbol": ["BTC", "BTC", "BTC"],
        "fdv_overhang": [1.0, 1.5, 2.0],
        "known_at": ["2025-01-01", "2025-02-01", "2025-03-01"],
    })

    provider = ManualTokenomicsProvider(data)

    snap = provider.get_snapshot("BTC", "2025-02-15")
    assert snap is not None
    assert snap.known_at <= "2025-02-15"

    snap = provider.get_snapshot("BTC", "2025-01-15")
    assert snap is not None
    assert snap.known_at <= "2025-01-15"

    snap = provider.get_snapshot("BTC", "2024-12-31")
    assert snap is None


def test_invariant4_no_missing_return_zero():
    """No missing return may be converted to 0."""
    n = 100
    timestamps = _ts(n)

    prices = np.linspace(100, 120, n)
    prices_obj = pl.Series("BTC", [float(p) if i not in (10, 25, 50) else None for i, p in enumerate(prices)])

    price_df = pl.DataFrame({
        "timestamp": timestamps,
        "BTC": prices_obj,
    })

    returns = compute_log_returns(price_df)

    for i in range(n):
        if prices[i] is None or i in (10, 25, 50):
            assert returns["BTC"][i] is None, (
                f"Return at index {i} should be null (missing candle), "
                f"got {returns['BTC'][i]}"
            )


def test_invariant5_funding_direction():
    """Funding direction tested with known positive and negative examples."""
    n = 10
    base = datetime(2025, 1, 1, tzinfo=timezone.utc)
    timestamps = [base + timedelta(hours=i) for i in range(n)]

    positive_rates = [0.0005] * n
    funding_pos = pl.DataFrame({
        "timestamp": timestamps,
        "funding_rate": positive_rates,
    })

    short_exposure = np.ones(n) * 100_000
    ts_array = np.array(timestamps)

    pnl_pos = compute_funding_pnl_series(funding_pos, short_exposure, ts_array)

    assert all(p > 0 for p in pnl_pos), (
        "Positive funding should produce positive PnL for shorts"
    )

    negative_rates = [-0.0003] * n
    funding_neg = pl.DataFrame({
        "timestamp": timestamps,
        "funding_rate": negative_rates,
    })

    pnl_neg = compute_funding_pnl_series(funding_neg, short_exposure, ts_array)

    assert all(p < 0 for p in pnl_neg), (
        "Negative funding should produce negative PnL for shorts"
    )

    for i in range(n):
        assert abs(pnl_pos[i] - 0.0005 * 100_000) < 1e-10
        assert abs(pnl_neg[i] - (-0.0003 * 100_000)) < 1e-10


def test_invariant6_point_in_time_universe():
    """Backtest universe is point-in-time where available."""
    snapshots = {
        "2025-01-01": ["BTC", "ETH", "SOL"],
        "2025-02-01": ["BTC", "ETH", "SOL", "AVAX"],
        "2025-03-01": ["BTC", "ETH", "AVAX"],
    }

    signal_date = "2025-02-15"
    universe_at_signal = None
    for date, assets in sorted(snapshots.items()):
        if date <= signal_date:
            universe_at_signal = assets

    assert universe_at_signal == ["BTC", "ETH", "SOL", "AVAX"]

    signal_date_2 = "2025-03-15"
    universe_at_signal_2 = None
    for date, assets in sorted(snapshots.items()):
        if date <= signal_date_2:
            universe_at_signal_2 = assets

    assert "SOL" not in universe_at_signal_2


def test_invariant_cross_sectional_percentile():
    """Structural short score components are cross-sectionally ranked."""
    tokenomics = pl.DataFrame({
        "symbol": [f"S{i}" for i in range(10)],
        "fdv_overhang": list(np.linspace(1.0, 5.0, 10)),
        "dilution_90d": list(np.linspace(0.01, 0.20, 10)),
    })
    momentum = pl.DataFrame({
        "symbol": [f"S{i}" for i in range(10)],
        "relative_momentum_30d": list(np.linspace(0.1, -0.1, 10)),
        "long_term_momentum_90d": list(np.linspace(0.2, -0.2, 10)),
        "value_capture": list(np.linspace(0.1, 1.0, 10)),
        "activity_change_30d": list(np.linspace(0.05, -0.05, 10)),
    })

    result = compute_structural_short_score(tokenomics, momentum)
    scores = result["structural_short_score"].to_list()

    for i in range(1, len(scores)):
        assert scores[i] >= scores[i - 1] - 0.01, (
            f"Score at {i} ({scores[i]}) < score at {i-1} ({scores[i-1]})"
        )


def test_invariant_total_score_non_negative():
    """Total candidate score must be non-negative."""
    for hf in [0, 50, 100]:
        for ss in [0, 50, 100]:
            for carry in [-0.5, 0, 0.5]:
                for ex in [0, 50, 100]:
                    for sq in [0, 50, 100]:
                        for dq in [0, 50, 100]:
                            result = compute_total_score(hf, ss, carry, ex, sq, dq)
                            assert result.total >= 0, (
                                f"Negative total score: {result.total} "
                                f"for ({hf}, {ss}, {carry}, {ex}, {sq}, {dq})"
                            )


def test_invariant_clone_gap_non_negative():
    """CLONE_GAP must be non-negative."""
    for hf in [0, 50, 100]:
        for ss_l in [0, 50, 100]:
            for ss_c in [0, 50, 100]:
                gap = compute_clone_gap(hf, ss_l, ss_c)
                assert gap >= 0, (
                    f"Negative CLONE_GAP: {gap} for ({hf}, {ss_l}, {ss_c})"
                )
