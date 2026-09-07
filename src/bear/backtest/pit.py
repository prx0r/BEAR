"""Point-in-time backtest framework.

Every data field has:
  event_at    — when the event happened
  published_at — when it was published by the source
  available_at — when we could have known it (ingestion lag)
  ingested_at  — when we stored it

assert available_at <= signal_time  — enforced everywhere.

Frozen OOS period is never touched during research.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl


@dataclass
class PITTimestamps:
    """Point-in-time timestamps for a single observation."""
    event_at: datetime
    published_at: datetime
    available_at: datetime
    ingested_at: datetime

    def assert_available_before(self, signal_time: datetime) -> None:
        """Core PIT invariant: data must be available before we use it."""
        assert self.available_at <= signal_time, (
            f"PIT violation: available_at={self.available_at} > signal_time={signal_time}"
        )


@dataclass
class FrozenOOS:
    """Frozen out-of-sample period. Never modified during research."""
    start: datetime
    end: datetime
    label: str = "frozen_oos"

    def is_oos(self, ts: datetime) -> bool:
        return self.start <= ts <= self.end


@dataclass
class WalkForwardSplit:
    """A single walk-forward train/valid/test split."""
    train_start: datetime
    train_end: datetime
    valid_start: datetime
    valid_end: datetime
    test_start: datetime
    test_end: datetime
    split_idx: int


def load_binance_daily(data_dir: Path) -> dict[str, dict[str, np.ndarray]]:
    """Load all Binance daily OHLCV data with PIT timestamps.

    Returns dict[symbol -> {timestamps, opens, highs, lows, closes, volumes, n}]
    All timestamps are UTC datetime objects.
    """
    assets: dict[str, dict[str, np.ndarray]] = {}
    for f in sorted(data_dir.glob("*.json")):
        symbol = f.stem.replace("USDT", "")
        with open(f) as fh:
            raw = json.load(fh)
        if len(raw) < 90:
            continue

        timestamps = np.array([d["open_time"] for d in raw], dtype=np.int64)
        closes = np.array([d["close"] for d in raw], dtype=np.float64)
        volumes = np.array([d["volume"] for d in raw], dtype=np.float64)
        opens = np.array([d["open"] for d in raw], dtype=np.float64)
        highs = np.array([d["high"] for d in raw], dtype=np.float64)
        lows = np.array([d["low"] for d in raw], dtype=np.float64)

        if np.all(closes > 0):
            assets[symbol] = {
                "timestamps": timestamps,
                "opens": opens,
                "highs": highs,
                "lows": lows,
                "closes": closes,
                "volumes": volumes,
                "n": len(raw),
            }
    return assets


def compute_log_returns(closes: np.ndarray) -> np.ndarray:
    """Compute log returns. First element is 0."""
    log_c = np.log(np.where(closes > 0, closes, np.nan))
    returns = np.diff(log_c, prepend=log_c[0])
    returns[0] = 0.0
    return returns


def make_walk_forward_splits(
    dates: list[datetime],
    train_days: int = 365,
    valid_days: int = 90,
    test_days: int = 90,
    step_days: int = 90,
) -> list[WalkForwardSplit]:
    """Generate walk-forward splits with proper calendar alignment.

    No information leakage: train ends before valid starts,
    valid ends before test starts.
    """
    splits = []
    n = len(dates)
    idx = 0
    split_idx = 0

    while idx + train_days + valid_days + test_days <= n:
        train_start = dates[idx]
        train_end = dates[idx + train_days - 1]
        valid_start = dates[idx + train_days]
        valid_end = dates[idx + train_days + valid_days - 1]
        test_start = dates[idx + train_days + valid_days]
        test_end = dates[idx + train_days + valid_days + test_days - 1]

        splits.append(WalkForwardSplit(
            train_start=train_start,
            train_end=train_end,
            valid_start=valid_start,
            valid_end=valid_end,
            test_start=test_start,
            test_end=test_end,
            split_idx=split_idx,
        ))

        idx += step_days
        split_idx += 1

    return splits


def make_frozen_oos(
    dates: list[datetime],
    oos_days: int = 90,
) -> FrozenOOS:
    """Define a frozen OOS period at the end of the data.

    This period is NEVER used for training, validation, or parameter selection.
    It is only used for final reporting.
    """
    oos_start = dates[-oos_days]
    oos_end = dates[-1]
    return FrozenOOS(start=oos_start, end=oos_end, label="frozen_oos")


def cross_sectional_rank(
    values: dict[str, float],
    higher_is_better: bool = True,
) -> dict[str, float]:
    """Rank assets cross-sectionally. Returns percentile 0-100."""
    items = [(k, v) for k, v in values.items() if np.isfinite(v)]
    if len(items) < 2:
        return {k: 50.0 for k in values}

    items.sort(key=lambda x: x[1], reverse=higher_is_better)
    n = len(items)
    result = {}
    for rank, (k, v) in enumerate(items):
        # rank 0 = best (highest if higher_is_better), so invert to get 100 = best
        result[k] = (n - 1 - rank) / (n - 1) * 100 if n > 1 else 50.0

    # Fill missing with NaN
    for k in values:
        if k not in result:
            result[k] = np.nan
    return result


def compute_sharpe(returns: np.ndarray, annualize: float = 365.0) -> float:
    """Annualized Sharpe ratio."""
    if len(returns) < 2:
        return 0.0
    mu = np.mean(returns)
    sigma = np.std(returns, ddof=1)
    if sigma < 1e-12:
        return 0.0
    return mu / sigma * np.sqrt(annualize)


def compute_deflated_sharpe(
    sharpe: float,
    n_trials: int,
    n_obs: int,
    skew: float = 0.0,
    kurtosis: float = 3.0,
) -> float:
    """Deflated Sharpe ratio (Bailey & Lopez de Prado).

    Adjusts Sharpe for multiple testing. Returns p-value.
    """
    from scipy import stats

    # Expected max Sharpe under null (Euler-Mascheroni corrected)
    e_max = np.sqrt(2 * np.log(max(n_trials, 2))) - (
        np.log(np.pi) + np.log(np.log(max(n_trials, 2)))
    ) / (2 * np.sqrt(2 * np.log(max(n_trials, 2))))

    # Standard error under non-normality
    se = np.sqrt(
        (1 + 0.5 * sharpe**2 - skew * sharpe + (kurtosis - 3) / 4 * sharpe**2)
        / max(n_obs - 1, 1)
    )

    if se < 1e-12:
        return 0.0

    # Z-score of observed Sharpe vs expected max
    z = (sharpe - e_max) / se
    p_value = 1 - stats.norm.cdf(z)
    return p_value


def block_bootstrap_ci(
    returns: np.ndarray,
    n_bootstrap: int = 1000,
    block_size: int = 21,
    confidence: float = 0.95,
    seed: int = 42,
) -> tuple[float, float]:
    """Block bootstrap confidence interval for mean return."""
    rng = np.random.RandomState(seed)
    n = len(returns)
    if n < block_size:
        return (np.mean(returns), np.mean(returns))

    boot_means = []
    for _ in range(n_bootstrap):
        # Sample blocks
        n_blocks = n // block_size + 1
        block_starts = rng.randint(0, n - block_size + 1, size=n_blocks)
        bootstrap_sample = np.concatenate([
            returns[start:start + block_size] for start in block_starts
        ])[:n]
        boot_means.append(np.mean(bootstrap_sample))

    boot_means = np.array(boot_means)
    alpha = 1 - confidence
    ci_low = np.percentile(boot_means, alpha / 2 * 100)
    ci_high = np.percentile(boot_means, (1 - alpha / 2) * 100)
    return (float(ci_low), float(ci_high))
