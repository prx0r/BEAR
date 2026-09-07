"""Death Hazard Model — P(zombie within N days).

Replicates the zombie crypto prediction approach (2026):
- Volume floor collapse is the dominant signal (84% balanced accuracy)
- Random forest/XGBoost justified by nonlinear relationships
- Age-specific hazard models (Fantazzini 2022)

Outputs:
  P(zombie_28d)  — probability of becoming untradeable within 28 days
  P(zombie_90d)  — probability within 90 days
  P(zombie_180d) — probability within 180 days

Target variable: asset becomes "zombie" when:
  - Volume drops below 10% of peak for 14+ consecutive days
  - OR delisted / removed from exchange
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import polars as pl


# ---------------------------------------------------------------------------
# Target variable construction
# ---------------------------------------------------------------------------

def compute_zombie_target(
    volumes: np.ndarray,
    timestamps: np.ndarray,
    forward_days: int = 28,
    volume_threshold: float = 0.10,
    min_zombie_days: int = 14,
) -> np.ndarray:
    """Compute forward-looking zombie label.

    An asset is labeled zombie=1 at time t if, within the next `forward_days`,
    its 7-day rolling volume drops below `volume_threshold` * peak volume
    and stays there for `min_zombie_days` consecutive days.

    Returns: binary array (1=zombie, 0=safe)
    """
    n = len(volumes)
    target = np.zeros(n, dtype=np.float64)

    # Compute rolling 7-day average volume
    vol_7d = np.full(n, np.nan)
    for i in range(6, n):
        w = volumes[max(0, i - 6): i + 1]
        valid = w[np.isfinite(w)]
        vol_7d[i] = np.mean(valid) if len(valid) > 0 else np.nan

    # Compute rolling peak volume (trailing 180 days)
    peak_vol = np.full(n, np.nan)
    for i in range(min(27, n - 1), n):  # start from 28d so we can compute 28d zombie
        w = volumes[max(0, i - min(179, i)): i + 1]
        valid = w[np.isfinite(w)]
        peak_vol[i] = np.max(valid) if len(valid) > 0 else np.nan

    # For each day, check if zombie occurs within forward window
    for t in range(n - forward_days):
        if not np.isfinite(peak_vol[t]) or peak_vol[t] <= 0:
            continue

        threshold_vol = peak_vol[t] * volume_threshold
        consecutive = 0

        for future_t in range(t + 1, min(t + forward_days + 1, n)):
            if np.isfinite(vol_7d[future_t]) and vol_7d[future_t] < threshold_vol:
                consecutive += 1
                if consecutive >= min_zombie_days:
                    target[t] = 1.0
                    break
            else:
                consecutive = 0

    return target


# ---------------------------------------------------------------------------
# Feature engineering — volume floor signals
# ---------------------------------------------------------------------------

def compute_volume_floor_features(
    volumes: np.ndarray,
    closes: np.ndarray,
    timestamps: np.ndarray,
) -> dict[str, np.ndarray]:
    """Compute volume floor and inactivity features.

    These are the strongest predictors from the zombie paper.
    """
    n = len(volumes)
    features: dict[str, np.ndarray] = {}

    # --- Volume floor features ---

    # min_volume_28d / cross_sectional_ADV
    min_vol_28d = np.full(n, np.nan)
    for i in range(27, n):
        w = volumes[max(0, i - 27): i + 1]
        valid = w[np.isfinite(w) & (w > 0)]
        min_vol_28d[i] = np.min(valid) if len(valid) > 0 else np.nan
    features["min_volume_28d"] = min_vol_28d

    # min_volume_182d
    min_vol_182d = np.full(n, np.nan)
    for i in range(181, n):
        w = volumes[max(0, i - 181): i + 1]
        valid = w[np.isfinite(w) & (w > 0)]
        min_vol_182d[i] = np.min(valid) if len(valid) > 0 else np.nan
    features["min_volume_182d"] = min_vol_182d

    # median_volume_7d / median_volume_90d
    med_vol_7d = np.full(n, np.nan)
    for i in range(6, n):
        w = volumes[max(0, i - 6): i + 1]
        valid = w[np.isfinite(w)]
        med_vol_7d[i] = np.median(valid) if len(valid) > 0 else np.nan

    med_vol_90d = np.full(n, np.nan)
    for i in range(89, n):
        w = volumes[max(0, i - 89): i + 1]
        valid = w[np.isfinite(w)]
        med_vol_90d[i] = np.median(valid) if len(valid) > 0 else np.nan

    features["volume_ratio_7d_90d"] = np.where(
        np.isfinite(med_vol_7d) & np.isfinite(med_vol_90d) & (med_vol_90d > 0),
        med_vol_7d / med_vol_90d,
        np.nan,
    )

    # median_volume_30d / max_volume_182d
    med_vol_30d = np.full(n, np.nan)
    for i in range(29, n):
        w = volumes[max(0, i - 29): i + 1]
        valid = w[np.isfinite(w)]
        med_vol_30d[i] = np.median(valid) if len(valid) > 0 else np.nan

    max_vol_182d = np.full(n, np.nan)
    for i in range(181, n):
        w = volumes[max(0, i - 181): i + 1]
        valid = w[np.isfinite(w)]
        max_vol_182d[i] = np.max(valid) if len(valid) > 0 else np.nan

    features["volume_ratio_30d_182d_max"] = np.where(
        np.isfinite(med_vol_30d) & np.isfinite(max_vol_182d) & (max_vol_182d > 0),
        med_vol_30d / max_vol_182d,
        np.nan,
    )

    # volume_floor_slope: slope of min volume over 28d windows
    # Negative = collapsing floor
    features["volume_floor_slope"] = _compute_slope(min_vol_28d, window=56)

    # days_since_volume_peak
    features["days_since_volume_peak"] = _days_since_peak(volumes, window=182)

    # --- Return features ---

    # median return over 182d (zombie paper: median historical returns)
    returns = np.full(n, np.nan)
    for i in range(1, n):
        if closes[i] > 0 and closes[i - 1] > 0:
            returns[i] = np.log(closes[i] / closes[i - 1])

    med_ret_182d = np.full(n, np.nan)
    for i in range(181, n):
        w = returns[max(1, i - 181): i + 1]
        valid = w[np.isfinite(w)]
        med_ret_182d[i] = np.median(valid) if len(valid) > 0 else np.nan
    features["median_return_182d"] = med_ret_182d

    # volatility_30d
    features["volatility_30d"] = _rolling_volatility(closes, window=30)

    # --- Liquidity death composite ---
    # Combine volume decline + return decline into a single "ghostness" score
    vol_death = np.where(
        np.isfinite(features.get("volume_ratio_7d_90d", np.full(n, np.nan))),
        np.clip((1.0 - features["volume_ratio_7d_90d"]) * 100, 0, 100),
        np.nan,
    )
    ret_death = np.where(
        np.isfinite(med_ret_182d),
        np.clip((-med_ret_182d) * 100, 0, 100),
        np.nan,
    )
    features["liquidity_death_composite"] = np.where(
        np.isfinite(vol_death) & np.isfinite(ret_death),
        0.6 * vol_death + 0.4 * ret_death,
        np.where(np.isfinite(vol_death), vol_death,
                 np.where(np.isfinite(ret_death), ret_death, np.nan)),
    )

    return features


# ---------------------------------------------------------------------------
# Simple tree-based model (no sklearn dependency for now)
# ---------------------------------------------------------------------------

@dataclass
class DeathHazardModel:
    """Simple death hazard model using percentile-rank scoring.

    For full ML, use the experimental runner with sklearn/xgboost.
    This provides a deterministic baseline.
    """
    # Feature weights (learned from backtest or hand-tuned)
    weights: dict[str, float] | None = None
    age_months: float = 12.0  # asset age in months (for age interaction)

    def __post_init__(self):
        if self.weights is None:
            self.weights = {
                "volume_ratio_7d_90d_inv": 0.25,
                "min_volume_28d_inv": 0.15,
                "volume_floor_slope_inv": 0.15,
                "median_return_182d_inv": 0.10,
                "volatility_30d": 0.10,
                "liquidity_death_composite": 0.15,
                "days_since_volume_peak": 0.10,
            }

    def predict(
        self,
        features: dict[str, np.ndarray],
        asset_age_days: float | None = None,
    ) -> np.ndarray:
        """Predict death hazard score 0-100."""
        n = len(next(iter(features.values())))
        scores = np.zeros(n)
        weight_sum = np.zeros(n)

        age = asset_age_days / 30.0 if asset_age_days else 12.0

        for feat_name, weight in self.weights.items():
            if feat_name.endswith("_inv"):
                base_name = feat_name[:-4]
                if base_name not in features:
                    continue
                vals = features[base_name]
                if "ratio" in base_name or "volume" in base_name.lower():
                    transformed = np.where(
                        np.isfinite(vals),
                        np.clip((1.0 - vals) * 100, 0, 100),
                        np.nan,
                    )
                else:
                    transformed = np.where(
                        np.isfinite(vals),
                        np.clip((-vals) * 100, 0, 100),
                        np.nan,
                    )
            else:
                if feat_name not in features:
                    continue
                vals = features[feat_name]
                transformed = np.where(np.isfinite(vals), np.clip(vals, 0, 100), np.nan)

            mask = np.isfinite(transformed)
            age_mult = 1.2 if age < 12 else (1.0 if age < 36 else 0.8)
            scores[mask] += weight * age_mult * transformed[mask]
            weight_sum[mask] += weight * age_mult

        # Normalize
        result = np.where(weight_sum > 0, scores / weight_sum * 100, 50.0)
        return np.clip(result, 0, 100)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compute_slope(arr: np.ndarray, window: int = 56) -> np.ndarray:
    """Linear slope over rolling window. Negative = declining."""
    n = len(arr)
    slope = np.full(n, np.nan)
    x = np.arange(window, dtype=np.float64)

    for i in range(window - 1, n):
        w = arr[max(0, i - window + 1): i + 1]
        valid_mask = np.isfinite(w)
        if valid_mask.sum() < window // 2:
            continue
        y = w[valid_mask]
        x_valid = x[:len(y)]
        if len(y) < 3:
            continue
        # Simple least-squares slope
        x_mean = np.mean(x_valid)
        y_mean = np.mean(y)
        ss_xx = np.sum((x_valid - x_mean) ** 2)
        ss_xy = np.sum((x_valid - x_mean) * (y - y_mean))
        if ss_xx > 0:
            slope[i] = ss_xy / ss_xx

    return slope


def _days_since_peak(arr: np.ndarray, window: int = 182) -> np.ndarray:
    """Days since the rolling peak value."""
    n = len(arr)
    result = np.full(n, np.nan)

    for i in range(window - 1, n):
        w = arr[max(0, i - window + 1): i + 1]
        valid = w[np.isfinite(w)]
        if len(valid) == 0:
            continue
        peak_idx = np.argmax(w[np.isfinite(w)])
        result[i] = i - max(0, i - window + 1) - peak_idx

    return result


def _rolling_volatility(closes: np.ndarray, window: int = 30) -> np.ndarray:
    """Rolling annualized volatility of log returns."""
    n = len(closes)
    vol = np.full(n, np.nan)
    log_ret = np.full(n, np.nan)

    for i in range(1, n):
        if closes[i] > 0 and closes[i - 1] > 0:
            log_ret[i] = np.log(closes[i] / closes[i - 1])

    for i in range(window, n):
        w = log_ret[max(1, i - window + 1): i + 1]
        valid = w[np.isfinite(w)]
        if len(valid) > 5:
            vol[i] = np.std(valid) * np.sqrt(365)

    return vol
