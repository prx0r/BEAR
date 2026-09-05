"""Combo selection strategies for short basket construction.

Greedy forward selection and LASSO-based feature selection for building
optimal hedge baskets from candidate short assets.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class SelectionResult:
    """Result of a basket selection algorithm."""

    selected_indices: list[int]
    selected_names: list[str]
    weights: dict[str, float]
    objective_history: list[float] = field(default_factory=list)
    n_iterations: int = 0


def greedy_forward_search(
    long_returns: np.ndarray,
    candidate_returns: np.ndarray,
    candidate_names: list[str],
    max_names: int = 5,
    min_improvement: float = 1e-6,
) -> SelectionResult:
    """Greedy forward selection for hedge basket.

    At each step, adds the candidate that most reduces hedging error
    (residual variance of long minus weighted short basket).

    Args:
        long_returns: (T,) long portfolio returns per period.
        candidate_returns: (T, N) candidate short returns per period.
        candidate_names: Names for each candidate column.
        max_names: Maximum number of names to select.
        min_improvement: Minimum variance reduction to continue.

    Returns:
        SelectionResult with selected names and weights.
    """
    T, N = candidate_returns.shape
    selected: list[int] = []
    remaining = list(range(N))
    weights: dict[str, float] = {}
    objective_history: list[float] = []

    current_residual = long_returns.copy()

    for step in range(min(max_names, N)):
        best_idx = -1
        best_improvement = -np.inf
        best_w = 0.0

        for idx in remaining:
            cand = candidate_returns[:, idx]

            # Optimal weight for this candidate: minimize ||long - w * cand||^2
            denom = float(np.dot(cand, cand))
            if denom < 1e-15:
                continue
            w = float(np.dot(current_residual, cand)) / denom

            # Variance reduction
            new_residual = current_residual - w * cand
            improvement = float(np.dot(current_residual, current_residual) - np.dot(new_residual, new_residual))

            if improvement > best_improvement:
                best_improvement = improvement
                best_idx = idx
                best_w = w

        if best_idx < 0 or best_improvement < min_improvement:
            break

        selected.append(best_idx)
        remaining.remove(best_idx)
        weights[candidate_names[best_idx]] = best_w
        current_residual = current_residual - best_w * candidate_returns[:, best_idx]
        objective_history.append(float(np.dot(current_residual, current_residual)))

    return SelectionResult(
        selected_indices=selected,
        selected_names=[candidate_names[i] for i in selected],
        weights=weights,
        objective_history=objective_history,
        n_iterations=len(selected),
    )


def lasso_select(
    long_returns: np.ndarray,
    candidate_returns: np.ndarray,
    candidate_names: list[str],
    alpha: float = 0.01,
    max_iter: int = 1000,
    tol: float = 1e-6,
) -> SelectionResult:
    """LASSO (L1-penalized) regression for basket selection.

    Solves: min_w ||long - X w||^2 / (2T) + alpha * ||w||_1

    Uses coordinate descent (soft-thresholding) for efficiency.

    Args:
        long_returns: (T,) long portfolio returns.
        candidate_returns: (T, N) candidate short returns.
        candidate_names: Names for each candidate.
        alpha: L1 regularization strength. Higher = more sparsity.
        max_iter: Maximum coordinate descent iterations.
        tol: Convergence tolerance on weight changes.

    Returns:
        SelectionResult with LASSO-selected names and weights.
    """
    T, N = candidate_returns.shape

    # Standardize candidates
    X = candidate_returns.copy()
    X_std = np.std(X, axis=0)
    X_std[X_std < 1e-15] = 1.0
    X_norm = X / X_std

    y = long_returns.copy()

    # OLS warm start
    XtX = X_norm.T @ X_norm
    Xty = X_norm.T @ y
    w = np.zeros(N)

    for iteration in range(max_iter):
        w_old = w.copy()

        for j in range(N):
            # Partial residual
            residual = y - X_norm @ w + X_norm[:, j] * w[j]
            rho = float(X_norm[:, j] @ residual)

            # Soft-thresholding
            if rho > alpha * T:
                w[j] = (rho - alpha * T) / float(XtX[j, j])
            elif rho < -alpha * T:
                w[j] = (rho + alpha * T) / float(XtX[j, j])
            else:
                w[j] = 0.0

        # Check convergence
        if np.max(np.abs(w - w_old)) < tol:
            break

    # Un-normalize weights
    w_unnorm = w / X_std

    # Build result: only non-zero weights
    selected_indices = [i for i in range(N) if abs(w_unnorm[i]) > 1e-10]
    selected_names = [candidate_names[i] for i in selected_indices]
    weights = {candidate_names[i]: float(w_unnorm[i]) for i in selected_indices}

    # Compute objective history
    residual = long_returns - candidate_returns @ w_unnorm
    obj = float(np.dot(residual, residual) / (2 * T) + alpha * np.sum(np.abs(w_unnorm)))

    return SelectionResult(
        selected_indices=selected_indices,
        selected_names=selected_names,
        weights=weights,
        objective_history=[obj],
        n_iterations=iteration + 1,
    )
