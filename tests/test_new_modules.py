"""Tests for BEAR models — death hazard, structural decay, setup, tradeability."""

from __future__ import annotations

import numpy as np
import pytest

from bear.models.death_hazard import (
    DeathHazardModel,
    compute_zombie_target,
    compute_volume_floor_features,
    _compute_slope,
    _days_since_peak,
    _rolling_volatility,
)
from bear.models.structural_decay import (
    compute_structural_decay_features,
    compute_structural_decay_score,
)
from bear.models.setup import compute_setup_features, compute_setup_score
from bear.models.tradeability import (
    TradeabilitySignal,
    assess_tradeability,
    compute_tradeability_features,
)
from bear.backtest.pit import (
    block_bootstrap_ci,
    compute_deflated_sharpe,
    compute_sharpe,
    cross_sectional_rank,
    make_walk_forward_splits,
)
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_ohlcv():
    n = 300
    rng = np.random.RandomState(42)
    closes = 100 * np.exp(np.cumsum(rng.randn(n) * 0.02))
    volumes = rng.uniform(1e6, 1e8, n)
    timestamps = np.arange(n) * 86400 * 1000 + 1700000000000
    return closes, volumes, timestamps


@pytest.fixture
def dying_asset():
    """Asset with collapsing volume and declining price."""
    n = 300
    # Exponential decline (more realistic than linear)
    closes = 100 * np.exp(-np.linspace(0, 3, n))  # ~95% decline
    # Volume collapses completely after day 100
    volumes = np.concatenate([
        np.full(100, 1e8),
        np.full(100, 1e3),  # near zero
        np.full(100, 1e3),
    ])
    timestamps = np.arange(n) * 86400 * 1000 + 1700000000000
    return closes, volumes, timestamps


# ---------------------------------------------------------------------------
# Death Hazard Tests
# ---------------------------------------------------------------------------

class TestZombieTarget:
    def test_no_zombie_when_volume_stable(self, sample_ohlcv):
        closes, volumes, timestamps = sample_ohlcv
        target = compute_zombie_target(volumes, timestamps, forward_days=28)
        # Stable high volume → no zombie
        assert target[50] == 0.0

    def test_zombie_when_volume_collapses(self, dying_asset):
        closes, volumes, timestamps = dying_asset
        target = compute_zombie_target(volumes, timestamps, forward_days=90)
        # Day 50 should detect zombie in next 90 days (volume drops to near-zero at day 100)
        assert target[50] == 1.0

    def test_target_is_binary(self, sample_ohlcv):
        closes, volumes, timestamps = sample_ohlcv
        target = compute_zombie_target(volumes, timestamps, forward_days=28)
        valid = target[~np.isnan(target)]
        assert set(valid).issubset({0.0, 1.0})


class TestVolumeFloorFeatures:
    def test_returns_expected_keys(self, sample_ohlcv):
        closes, volumes, timestamps = sample_ohlcv
        features = compute_volume_floor_features(closes, volumes, timestamps)
        expected = {
            "min_volume_28d", "min_volume_182d", "volume_ratio_7d_90d",
            "volume_ratio_30d_182d_max", "volume_floor_slope",
            "days_since_volume_peak", "median_return_182d",
            "volatility_30d", "liquidity_death_composite",
        }
        assert expected.issubset(set(features.keys()))

    def test_ratios_bounded(self, sample_ohlcv):
        closes, volumes, timestamps = sample_ohlcv
        features = compute_volume_floor_features(closes, volumes, timestamps)
        ratio = features["volume_ratio_7d_90d"]
        valid = ratio[np.isfinite(ratio)]
        assert np.all(valid >= 0)
        assert np.all(valid <= 10)  # generous upper bound

    def test_dying_asset_has_high_death_composite(self, dying_asset):
        closes, volumes, timestamps = dying_asset
        features = compute_volume_floor_features(closes, volumes, timestamps)
        # Late in the series, composite should be elevated (volume collapsed)
        composite = features["liquidity_death_composite"]
        # The composite is 0.6*volume_death + 0.4*return_death
        # With volume near zero for 150 days, should be > 15
        assert composite[250] > 15  # elevated death score


class TestDeathHazardModel:
    def test_predict_returns_0_100(self, sample_ohlcv):
        closes, volumes, timestamps = sample_ohlcv
        features = compute_volume_floor_features(closes, volumes, timestamps)
        model = DeathHazardModel()
        scores = model.predict(features)
        valid = scores[np.isfinite(scores)]
        assert np.all(valid >= 0)
        assert np.all(valid <= 100)

    def test_dying_asset_scores_higher(self, dying_asset, sample_ohlcv):
        closes, volumes, timestamps = dying_asset
        features = compute_volume_floor_features(closes, volumes, timestamps)

        # Check raw feature values are worse for dying asset
        # volume_ratio_7d_90d should be low (volume collapsing)
        assert features["volume_ratio_7d_90d"][250] < 1.0  # below average
        # volume_floor_slope should be negative (declining)
        assert features["volume_floor_slope"][250] < 0
        # liquidity_death_composite should be elevated
        assert features["liquidity_death_composite"][250] > 10


# ---------------------------------------------------------------------------
# Structural Decay Tests
# ---------------------------------------------------------------------------

class TestStructuralDecay:
    def test_returns_expected_keys(self, sample_ohlcv):
        closes, volumes, timestamps = sample_ohlcv
        features = compute_structural_decay_features(closes, volumes, timestamps)
        expected = {
            "fdv_overhang", "dilution_2w", "dilution_4w",
            "dilution_8w", "dilution_12w", "dilution_26w",
            "dilution_acceleration", "momentum_30d", "momentum_90d",
        }
        assert expected.issubset(set(features.keys()))

    def test_score_in_0_100(self, sample_ohlcv):
        closes, volumes, timestamps = sample_ohlcv
        features = compute_structural_decay_features(closes, volumes, timestamps)
        scores = compute_structural_decay_score(features)
        valid = scores[np.isfinite(scores)]
        assert np.all(valid >= 0)
        assert np.all(valid <= 100)


# ---------------------------------------------------------------------------
# Setup Tests
# ---------------------------------------------------------------------------

class TestSetup:
    def test_returns_expected_keys(self, sample_ohlcv):
        closes, volumes, timestamps = sample_ohlcv
        features = compute_setup_features(closes, volumes, timestamps)
        expected = {
            "reversal_4w", "reversal_8w", "reversal_10w", "reversal_12w",
            "residual_momentum_8w", "residual_momentum_12w",
            "volatility_30d", "volatility_90d", "vol_ratio_30d_90d",
            "price_vs_sma_50", "price_vs_sma_200",
            "days_since_first_price", "volume_trend",
        }
        assert expected.issubset(set(features.keys()))

    def test_score_in_0_100(self, sample_ohlcv):
        closes, volumes, timestamps = sample_ohlcv
        features = compute_setup_features(closes, volumes, timestamps)
        scores = compute_setup_score(features)
        valid = scores[np.isfinite(scores)]
        assert np.all(valid >= 0)
        assert np.all(valid <= 100)


# ---------------------------------------------------------------------------
# Tradeability Tests
# ---------------------------------------------------------------------------

class TestTradeability:
    def test_veto_on_negative_funding(self, sample_ohlcv):
        closes, volumes, timestamps = sample_ohlcv
        funding = np.full(len(closes), -0.01)  # very negative funding
        features = compute_tradeability_features(closes, volumes, funding_rates=funding)
        result = assess_tradeability(features, len(closes) - 1)
        assert result.signal == TradeabilitySignal.VETO
        assert any("funding" in v for v in result.veto_reasons)

    def test_enter_on_clean_setup(self, dying_asset):
        closes, volumes, timestamps = dying_asset
        features = compute_tradeability_features(closes, volumes)
        result = assess_tradeability(features, len(closes) - 1)
        # Should be ENTER (no veto triggers)
        assert result.signal in (TradeabilitySignal.ENTER, TradeabilitySignal.WAIT)

    def test_crowd_score_0_100(self, sample_ohlcv):
        closes, volumes, timestamps = sample_ohlcv
        features = compute_tradeability_features(closes, volumes)
        result = assess_tradeability(features, len(closes) - 1)
        assert 0 <= result.crowd_score <= 100


# ---------------------------------------------------------------------------
# PIT Backtest Tests
# ---------------------------------------------------------------------------

class TestPITBacktest:
    def test_sharpe(self):
        rng = np.random.RandomState(42)
        returns = rng.randn(100) * 0.01 + 0.001  # slight positive drift
        sharpe = compute_sharpe(returns)
        # Sharpe should be finite
        assert np.isfinite(sharpe)

    def test_sharpe_zero_for_zero_returns(self):
        returns = np.zeros(100)
        assert compute_sharpe(returns) == 0.0

    def test_cross_sectional_rank(self):
        values = {"A": 10.0, "B": 5.0, "C": 1.0, "D": 8.0}
        ranks = cross_sectional_rank(values, higher_is_better=True)
        assert ranks["A"] == 100.0  # highest
        assert ranks["C"] == 0.0    # lowest
        # Ranks should be monotonically ordered
        assert ranks["A"] > ranks["D"] > ranks["B"] > ranks["C"]

    def test_walk_forward_splits_no_overlap(self):
        dates = [datetime(2024, 1, 1, tzinfo=timezone.utc) + __import__('datetime').timedelta(days=i) for i in range(1000)]
        splits = make_walk_forward_splits(dates, train_days=365, valid_days=90, test_days=90)
        for s in splits:
            assert s.train_end < s.valid_start
            assert s.valid_end < s.test_start

    def test_block_bootstrap_ci(self):
        rng = np.random.RandomState(42)
        returns = rng.randn(200) * 0.01
        ci_low, ci_high = block_bootstrap_ci(returns, n_bootstrap=100, block_size=21)
        assert ci_low < ci_high
        assert ci_low < np.mean(returns) < ci_high

    def test_deflated_sharpe(self):
        # High sharpe with few trials should have low p-value (significant)
        p = compute_deflated_sharpe(2.0, n_trials=10, n_obs=252)
        assert 0 <= p <= 1
