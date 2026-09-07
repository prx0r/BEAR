"""BEAR models — four independent prediction models.

Per the dev plan, these are kept SEPARATE during training:
  A. DEATH_HAZARD — slow (P(zombie))
  B. STRUCTURAL_DECAY — slow (expected underperformance)
  C. SETUP — medium horizon (entry timing)
  D. TRADEABILITY — fast (ENTER/WAIT/VETO)

Combined only at decision time via TradableDeath.
"""

from bear.models.death_hazard import DeathHazardModel, compute_zombie_target, compute_volume_floor_features
from bear.models.structural_decay import compute_structural_decay_features, compute_structural_decay_score
from bear.models.setup import compute_setup_features, compute_setup_score
from bear.models.tradeability import TradeabilitySignal, TradeabilityResult, compute_tradeability_features, assess_tradeability

__all__ = [
    "DeathHazardModel",
    "compute_zombie_target",
    "compute_volume_floor_features",
    "compute_structural_decay_features",
    "compute_structural_decay_score",
    "compute_setup_features",
    "compute_setup_score",
    "TradeabilitySignal",
    "TradeabilityResult",
    "compute_tradeability_features",
    "assess_tradeability",
]
