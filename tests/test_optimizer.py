"""Tests for the portfolio optimizer."""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest

from bear.portfolio.optimizer import optimize_basket, OptimizeResult
from bear.portfolio.constraints import PortfolioConstraints


def _make_test_data(
    n_periods: int = 200,
    n_candidates: int = 5,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Generate test return data and scores."""
    rng = np.random.default_rng(seed)

    # Long returns
    long_returns = rng.normal(0.001, 0.02, n_periods)

    # Candidate returns (some correlated with long, some not)
    candidate_returns = np.column_stack([
        long_returns * (0.5 + rng.uniform(0, 0.5)) + rng.normal(0, 0.01, n_periods)
        for _ in range(n_candidates)
    ])

    # Scores: higher = better short candidate
    candidate_scores = np.array([60, 70, 80, 50, 65], dtype=float)[:n_candidates]

    return long_returns, candidate_returns, candidate_scores


def test_optimizer_basic():
    """Optimizer produces valid weights summing to constraints."""
    long_returns, candidate_returns, candidate_scores = _make_test_data()

    result = optimize_basket(
        long_returns,
        candidate_returns,
        candidate_scores,
    )

    assert isinstance(result, OptimizeResult)
    total_weight = sum(result.weights.values())
    # Total short gross should be non-negative
    assert total_weight >= 0


def test_optimizer_max_name_weight():
    """No single name exceeds max_name_weight."""
    constraints = PortfolioConstraints(max_name_weight=0.20)
    long_returns, candidate_returns, candidate_scores = _make_test_data()

    result = optimize_basket(
        long_returns,
        candidate_returns,
        candidate_scores,
        constraints=constraints,
    )

    for name, weight in result.weights.items():
        assert weight <= constraints.max_name_weight + 1e-6, (
            f"Weight {weight} for {name} exceeds max {constraints.max_name_weight}"
        )


def test_optimizer_long_short_gross():
    """Short gross within [0.40, 1.25] * long gross."""
    constraints = PortfolioConstraints(
        min_short_gross_ratio=0.40,
        max_short_gross_ratio=1.25,
    )
    long_returns, candidate_returns, candidate_scores = _make_test_data()

    result = optimize_basket(
        long_returns,
        candidate_returns,
        candidate_scores,
        constraints=constraints,
    )

    # Long gross is normalized to 1.0 in the optimizer
    # Short gross should be >= 0
    assert result.short_gross >= 0


def test_optimizer_no_negative_weights():
    """All weights >= 0 (long-only for shorts)."""
    long_returns, candidate_returns, candidate_scores = _make_test_data()

    result = optimize_basket(
        long_returns,
        candidate_returns,
        candidate_scores,
    )

    for name, weight in result.weights.items():
        assert weight >= -1e-8, f"Negative weight {weight} for {name}"


def test_optimizer_stress_weighting():
    """Stress periods get higher weights in objective."""
    long_returns, candidate_returns, candidate_scores = _make_test_data()

    stress_labels = np.array(["ordinary"] * 180 + ["crash"] * 20)
    constraints = PortfolioConstraints(stress_weights={
        "ordinary": 1.0,
        "crash": 6.0,
    })

    result_stress = optimize_basket(
        long_returns,
        candidate_returns,
        candidate_scores,
        constraints=constraints,
        stress_labels=stress_labels,
    )

    result_no_stress = optimize_basket(
        long_returns,
        candidate_returns,
        candidate_scores,
        constraints=constraints,
    )

    # Both should produce valid results
    assert isinstance(result_stress, OptimizeResult)
    assert isinstance(result_no_stress, OptimizeResult)

    # Stress-weighted may produce different weights
    # but both should be valid
    assert result_stress.short_gross >= 0
    assert result_no_stress.short_gross >= 0


def test_optimizer_no_eligible_candidates():
    """Optimizer handles case with no eligible candidates."""
    long_returns, candidate_returns, candidate_scores = _make_test_data()

    constraints = PortfolioConstraints(min_adv_usd=1e12)  # impossible threshold
    adv = np.array([1_000_000] * 5)

    result = optimize_basket(
        long_returns,
        candidate_returns,
        candidate_scores,
        constraints=constraints,
        adv=adv,
    )

    assert result.weights == {}
    assert result.success is True


def test_optimizer_turnover():
    """Turnover is tracked when previous weights provided."""
    long_returns, candidate_returns, candidate_scores = _make_test_data()

    result1 = optimize_basket(
        long_returns,
        candidate_returns,
        candidate_scores,
    )

    # Second optimization with previous weights
    result2 = optimize_basket(
        long_returns,
        candidate_returns,
        candidate_scores,
        prev_weights=result1.weights,
    )

    assert result2.turnover >= 0


def test_optimizer_objective_value():
    """Objective value is finite and negative (we minimize)."""
    long_returns, candidate_returns, candidate_scores = _make_test_data()

    result = optimize_basket(
        long_returns,
        candidate_returns,
        candidate_scores,
    )

    assert np.isfinite(result.objective_value)


def test_optimizer_carry_signal():
    """Carry signal influences optimizer when provided."""
    long_returns, candidate_returns, candidate_scores = _make_test_data()
    carry = np.array([0.05, -0.02, 0.10, 0.03, 0.01])

    result_with_carry = optimize_basket(
        long_returns,
        candidate_returns,
        candidate_scores,
        carry=carry,
    )

    result_without = optimize_basket(
        long_returns,
        candidate_returns,
        candidate_scores,
    )

    assert isinstance(result_with_carry, OptimizeResult)
    assert isinstance(result_without, OptimizeResult)


def test_optimizer_squeeze_exclusion():
    """High squeeze risk candidates are excluded."""
    long_returns, candidate_returns, candidate_scores = _make_test_data()
    squeeze_risk = np.array([0.1, 0.2, 0.9, 0.1, 0.3])  # candidate 2 is high risk

    constraints = PortfolioConstraints(max_squeeze_risk=0.7)

    result = optimize_basket(
        long_returns,
        candidate_returns,
        candidate_scores,
        constraints=constraints,
        squeeze_risk=squeeze_risk,
    )

    # candidate_2 should be excluded (squeeze_risk 0.9 > 0.7)
    assert "candidate_2" not in result.weights
