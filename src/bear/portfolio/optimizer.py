"""Basket optimizer — minimizes hedged relative-value cost function.

Objective (Section 30-31):
    minimize  Σ_t weight_t * (y_t - X_t @ w)^2
              + λ_div * ||w||^2
              + λ_turnover * turnover(w, w_prev)
              + λ_cost * expected_cost(w)
              - λ_shortquality * q^T w
              - λ_carry * carry^T w

Subject to:
    w_i >= 0
    Σ w_i <= max_names (sparsity via cardinality relaxation)
    w_i <= max_name_weight
    short_gross in [min_short_gross_ratio * long_gross, max_short_gross_ratio * long_gross]
    liquidity: w_i * portfolio_value <= max_pct_of_adv * adv_i
    squeeze: exclude names with squeeze_risk > threshold
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.optimize import minimize

from bear.portfolio.constraints import PortfolioConstraints

logger = logging.getLogger(__name__)


@dataclass
class OptimizeResult:
    weights: Dict[str, float]
    objective_value: float
    stress_returns: np.ndarray
    hedge_residual: np.ndarray
    turnover: float
    expected_cost: float
    short_gross: float
    long_gross: float
    net_exposure: float
    names: List[str]
    success: bool
    message: str


def _stress_weight_vector(
    stress_labels: np.ndarray,
    stress_map: Dict[str, float],
) -> np.ndarray:
    """Map per-observation stress labels to scalar weights."""
    return np.array([stress_map.get(s, 1.0) for s in stress_labels])


def _expected_cost(
    weights: np.ndarray,
    adv: np.ndarray,
    maker_fee_bps: float,
    taker_fee_bps: float,
) -> float:
    """Rough expected execution cost: fee * (size / adv) impact."""
    if adv is None or len(adv) == 0:
        return 0.0
    fee = (maker_fee_bps + taker_fee_bps) / 2.0 / 10_000.0
    impact = np.abs(weights) / np.maximum(adv, 1.0)
    return float(np.sum(fee * np.abs(weights) + 0.1 * impact * np.abs(weights)))


def _turnover_cost(
    w_new: np.ndarray,
    w_prev: Optional[np.ndarray],
) -> float:
    """One-way turnover cost."""
    if w_prev is None:
        return float(np.sum(np.abs(w_new)))
    return float(np.sum(np.abs(w_new - w_prev)) / 2.0)


def optimize_basket(
    long_returns: np.ndarray,
    candidate_returns: np.ndarray,
    candidate_scores: np.ndarray,
    constraints: Optional[PortfolioConstraints] = None,
    *,
    prev_weights: Optional[Dict[str, float]] = None,
    adv: Optional[np.ndarray] = None,
    carry: Optional[np.ndarray] = None,
    squeeze_risk: Optional[np.ndarray] = None,
    stress_labels: Optional[np.ndarray] = None,
    portfolio_value: float = 1_000_000.0,
) -> OptimizeResult:
    """Optimize hedge basket weights.

    Args:
        long_returns: (T,) array of long portfolio returns per period.
        candidate_returns: (T, N) array of candidate short returns per period.
        candidate_scores: (N,) quality/lending scores per candidate.
        constraints: Portfolio limits.
        prev_weights: Previous weights for turnover calc.
        adv: (N,) average daily volume in USD per candidate.
        carry: (N,) carry/funding yield per candidate (positive = beneficial).
        squeeze_risk: (N,) squeeze risk score per candidate [0, 1].
        stress_labels: (T,) stress regime labels per observation.
        portfolio_value: Notional portfolio value in USD.

    Returns:
        OptimizeResult with optimal weights and diagnostics.
    """
    if constraints is None:
        constraints = PortfolioConstraints()

    errors = constraints.validate()
    if errors:
        raise ValueError(f"Invalid constraints: {errors}")

    T, N = candidate_returns.shape
    if len(long_returns) != T:
        raise ValueError(f"long_returns length {len(long_returns)} != T {T}")
    if len(candidate_scores) != N:
        raise ValueError(f"candidate_scores length {len(candidate_scores)} != N {N}")

    # Pre-filter: exclude illiquid and high-squeeze candidates
    eligible = np.ones(N, dtype=bool)
    if adv is not None:
        eligible &= adv >= constraints.min_adv_usd
    if squeeze_risk is not None:
        eligible &= squeeze_risk <= constraints.max_squeeze_risk

    eligible_idx = np.where(eligible)[0]
    N_elig = len(eligible_idx)

    if N_elig == 0:
        return OptimizeResult(
            weights={},
            objective_value=0.0,
            stress_returns=long_returns,
            hedge_residual=long_returns.copy(),
            turnover=0.0,
            expected_cost=0.0,
            short_gross=0.0,
            long_gross=0.0,
            net_exposure=1.0,
            names=[],
            success=True,
            message="No eligible candidates",
        )

    # Slice to eligible
    C = candidate_returns[:, eligible_idx]
    q = candidate_scores[eligible_idx]
    adv_elig = adv[eligible_idx] if adv is not None else np.ones(N_elig)
    carry_elig = carry[eligible_idx] if carry is not None else np.zeros(N_elig)
    sq_elig = squeeze_risk[eligible_idx] if squeeze_risk is not None else np.zeros(N_elig)

    # Stress weights
    if stress_labels is not None:
        sw = _stress_weight_vector(stress_labels, constraints.stress_weights)
    else:
        sw = np.ones(T)

    w_prev = None
    if prev_weights is not None:
        w_prev = np.zeros(N_elig)
        for i, idx in enumerate(eligible_idx):
            name = str(idx)
            if name in prev_weights:
                w_prev[i] = prev_weights[name]

    # Build objective
    def objective(w: np.ndarray) -> float:
        residual = long_returns - C @ w
        # Stress-weighted hedging error
        hedging_error = float(sw @ (residual ** 2))

        # L2 regularization
        div_cost = constraints.l2_weight_penalty * float(np.sum(w ** 2))

        # Turnover
        turn = _turnover_cost(w, w_prev)
        turn_cost = constraints.turnover_penalty * turn

        # Expected cost
        ec = _expected_cost(w, adv_elig, constraints.maker_fee_bps, constraints.taker_fee_bps)
        cost_term = constraints.expected_cost_penalty * ec

        # Short quality bonus (negative = improvement)
        quality_bonus = constraints.short_quality_penalty * float(q @ w)

        # Carry bonus (negative = improvement)
        carry_bonus = constraints.carry_penalty * float(carry_elig @ w)

        return hedging_error + div_cost + turn_cost + cost_term - quality_bonus - carry_bonus

    # Constraints for SLSQP
    scipy_constraints = []

    # Names budget: sum of binary w_i <= max_names (approximate via L1 bound)
    # We use a soft sparsity via L2, but also add a hard cardinality relaxation:
    # sum(w) <= max_name_weight * max_names
    max_total = constraints.max_name_weight * constraints.max_names
    scipy_constraints.append({
        "type": "ineq",
        "fun": lambda w: max_total - float(np.sum(w)),
    })

    # Max per-name weight
    def max_name_con(w, idx=i) -> float:
        return constraints.max_name_weight - w[idx]

    for i in range(N_elig):
        scipy_constraints.append({
            "type": "ineq",
            "fun": max_name_con,
            "args": (),
        })

    # Liquidity: w_i * portfolio_value <= max_pct_of_adv * adv_i
    if adv is not None:
        for i in range(N_elig):
            adv_limit = constraints.max_pct_of_adv * adv_elig[i] / portfolio_value
            scipy_constraints.append({
                "type": "ineq",
                "fun": lambda w, j=i, lim=adv_limit: lim - w[j],
            })

    # Bounds: w_i >= 0
    bounds = [(0.0, constraints.max_weight)] * N_elig

    # Initial guess: equal weight among eligible
    w0 = np.ones(N_elig) / max(N_elig, 1) * min(constraints.max_name_weight, 1.0 / N_elig)

    result = minimize(
        objective,
        w0,
        method="SLSQP",
        bounds=bounds,
        options={"maxiter": 1000, "ftol": 1e-12},
    )

    # Add inequality constraints one-by-one (SLSQP handles them via constraints list)
    # Rebuild with all constraints properly
    result = minimize(
        objective,
        w0,
        method="SLSQP",
        bounds=bounds,
        constraints=scipy_constraints,
        options={"maxiter": 1000, "ftol": 1e-12},
    )

    w_opt = result.x

    # Zero out tiny weights
    w_opt[w_opt < 1e-6] = 0.0

    # Renormalize if needed (keep within max_names)
    nonzero = np.sum(w_opt > 0)
    if nonzero > constraints.max_names:
        # Keep top max_names by weight
        top_idx = np.argsort(w_opt)[::-1][: constraints.max_names]
        mask = np.zeros(N_elig, dtype=bool)
        mask[top_idx] = True
        w_opt[~mask] = 0.0
        total = np.sum(w_opt)
        if total > 0:
            w_opt *= min(1.0, max_total) / total

    # Build output
    names = []
    weights_dict = {}
    for i, idx in enumerate(eligible_idx):
        if w_opt[i] > 1e-8:
            name = f"candidate_{idx}"
            names.append(name)
            weights_dict[name] = float(w_opt[i])

    short_gross = float(np.sum(w_opt))
    long_gross = float(np.sum(np.abs(long_returns))) / T if T > 0 else 0.0
    # Normalize: long_gross = 1.0 (fully invested long)
    long_gross = 1.0
    net_exposure = long_gross - short_gross

    residual = long_returns - C @ w_opt

    return OptimizeResult(
        weights=weights_dict,
        objective_value=float(result.fun),
        stress_returns=long_returns,
        hedge_residual=residual,
        turnover=_turnover_cost(w_opt, w_prev),
        expected_cost=_expected_cost(w_opt, adv_elig, constraints.maker_fee_bps, constraints.taker_fee_bps),
        short_gross=short_gross,
        long_gross=long_gross,
        net_exposure=net_exposure,
        names=names,
        success=result.success,
        message=result.message,
    )
