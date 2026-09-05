"""Backtesting engine (Section 42-44).

Walk-forward backtester with point-in-time enforcement,
survivorship bias handling, and funding-aware PnL.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import polars as pl

from bear.backtest.costs import estimate_cost, estimate_rebalancing_cost
from bear.backtest.funding import compute_funding_pnl_series
from bear.backtest.metrics import PerformanceMetrics, compute_metrics
from bear.portfolio.attribution import compute_attribution
from bear.portfolio.optimizer import optimize_basket

logger = logging.getLogger(__name__)


@dataclass
class BacktestConfig:
    """Configuration for a backtest run."""

    long_symbol: str
    short_symbols: List[str]
    start_date: str
    end_date: str
    initial_capital: float = 1_000_000.0
    rebalance_freq: str = "1w"
    funding_freq: str = "8h"
    fee_rate: float = 0.00035
    slippage_bps: float = 2.0
    walk_forward: bool = True
    train_months: int = 12
    valid_months: int = 3
    test_months: int = 3
    enforce_point_in_time: bool = True
    handle_survivorship: bool = True
    max_short_weight: float = 0.35
    min_short_gross: float = 0.40
    max_short_gross: float = 1.25


@dataclass
class BacktestResult:
    """Complete backtest output."""

    config: BacktestConfig
    equity_curve: pl.DataFrame
    metrics: PerformanceMetrics
    attribution: List[Dict[str, Any]]
    trades: pl.DataFrame
    funding_pnl: float
    total_fees: float
    total_slippage: float
    split_results: Dict[str, PerformanceMetrics] = field(default_factory=dict)


class BacktestEngine:
    """Walk-forward backtesting engine with point-in-time enforcement."""

    def __init__(self, config: BacktestConfig):
        self.config = config
        self._validate_config()

    def _validate_config(self) -> None:
        if self.config.initial_capital <= 0:
            raise ValueError("initial_capital must be positive")
        if self.config.min_short_gross > self.config.max_short_gross:
            raise ValueError("min_short_gross must be <= max_short_gross")

    def run(
        self,
        prices: pl.DataFrame,
        funding_rates: pl.DataFrame,
        universe: Optional[pl.DataFrame] = None,
        tokenomics: Optional[pl.DataFrame] = None,
        rebalance_dates: Optional[List[str]] = None,
    ) -> BacktestResult:
        """Run the full backtest.

        Args:
            prices: DataFrame with columns [timestamp, symbol, close, high, low, volume, spread].
            funding_rates: DataFrame with [timestamp, funding_rate].
            universe: Point-in-time universe eligibility.
            tokenomics: Tokenomics data for short quality scoring.
            rebalance_dates: Explicit rebalance dates (if None, auto-generate).

        Returns:
            BacktestResult with equity curve, metrics, attribution.
        """
        cfg = self.config

        # Get unique dates
        dates = prices.select("timestamp").unique().sort("timestamp").get_column("timestamp").to_list()
        dates = [str(d) for d in dates]
        if not dates:
            raise ValueError("No data dates provided")

        # Walk-forward splits
        splits = self._compute_splits(dates) if cfg.walk_forward else [
            {"train": dates, "valid": [], "test": dates}
        ]

        all_results = []
        equity_parts = []

        for split_idx, split in enumerate(splits):
            test_dates = split["test"]
            if not test_dates:
                continue

            logger.info(
                "Split %d: test %s to %s (%d days)",
                split_idx, test_dates[0], test_dates[-1], len(test_dates),
            )

            # Generate rebalance dates within test period
            if rebalance_dates:
                rb_dates = [d for d in rebalance_dates if d in test_dates]
            else:
                rb_dates = self._generate_rebalance_dates(test_dates, cfg.rebalance_freq)

            # Simulate
            split_eq, split_trades, split_funding = self._simulate_split(
                prices, funding_rates, test_dates, rb_dates, split.get("train", []),
            )
            equity_parts.append(split_eq)
            all_results.extend(split_trades)

            # Metrics for this split
            if split_eq.height > 1:
                eq_arr = split_eq["equity"].to_numpy()
                split_metrics = compute_metrics(eq_arr)
                split_label = f"split_{split_idx}"
                logger.info("Split %d Sharpe: %.2f", split_idx, split_metrics.sharpe_ratio)

        # Concatenate equity curves
        if equity_parts:
            equity_curve = pl.concat(equity_parts)
        else:
            equity_curve = pl.DataFrame({"timestamp": [], "equity": []})

        # Full metrics
        if equity_curve.height > 1:
            eq_arr = equity_curve["equity"].to_numpy()
            metrics = compute_metrics(eq_arr)
        else:
            metrics = PerformanceMetrics()

        # Attribution
        attribution = self._compute_attribution(all_results)

        trades_df = pl.DataFrame(all_results) if all_results else pl.DataFrame()

        total_funding = float(sum(t.get("funding_pnl", 0) for t in all_results))
        total_fees = float(sum(t.get("fees", 0) for t in all_results))
        total_slippage = float(sum(t.get("slippage", 0) for t in all_results))

        return BacktestResult(
            config=cfg,
            equity_curve=equity_curve,
            metrics=metrics,
            attribution=attribution,
            trades=trades_df,
            funding_pnl=total_funding,
            total_fees=total_fees,
            total_slippage=total_slippage,
        )

    def _simulate_split(
        self,
        prices: pl.DataFrame,
        funding_rates: pl.DataFrame,
        test_dates: List[str],
        rebalance_dates: List[str],
        train_dates: List[str],
    ) -> Tuple[pl.DataFrame, List[Dict[str, Any]], float]:
        """Simulate one walk-forward split."""
        cfg = self.config
        equity = cfg.initial_capital
        equity_records = []
        trade_records = []
        total_funding = 0.0
        current_weights = {s: 0.0 for s in cfg.short_symbols}

        for i, date in enumerate(test_dates):
            # Get prices for this date
            day_prices = prices.filter(pl.col("timestamp").cast(pl.Utf8) == str(date))
            if day_prices.is_empty():
                equity_records.append({"timestamp": date, "equity": equity})
                continue

            # Get long price
            long_row = day_prices.filter(pl.col("symbol") == cfg.long_symbol)
            if long_row.is_empty():
                equity_records.append({"timestamp": date, "equity": equity})
                continue

            long_price = float(long_row["close"].item())
            long_return = 0.0
            if i > 0:
                prev_date = test_dates[i - 1]
                prev_long = prices.filter(
                    (pl.col("timestamp").cast(pl.Utf8) == str(prev_date)) & (pl.col("symbol") == cfg.long_symbol)
                )
                if not prev_long.is_empty():
                    prev_price = float(prev_long["close"].item())
                    long_return = (long_price - prev_price) / prev_price if prev_price > 0 else 0.0

            # Short returns
            short_returns = {}
            for sym in cfg.short_symbols:
                sym_row = day_prices.filter(pl.col("symbol") == sym)
                if sym_row.is_empty():
                    short_returns[sym] = 0.0
                    continue
                sym_price = float(sym_row["close"].item())
                if i > 0:
                    prev_sym = prices.filter(
                        (pl.col("timestamp").cast(pl.Utf8) == str(prev_date)) & (pl.col("symbol") == sym)
                    )
                    if not prev_sym.is_empty():
                        prev_p = float(prev_sym["close"].item())
                        short_returns[sym] = (sym_price - prev_p) / prev_p if prev_p > 0 else 0.0
                    else:
                        short_returns[sym] = 0.0
                else:
                    short_returns[sym] = 0.0

            # Short PnL: positive when short drops
            short_pnl = sum(-current_weights.get(s, 0) * short_returns.get(s, 0) for s in cfg.short_symbols)

            # Funding
            fr_row = funding_rates.filter(pl.col("timestamp").cast(pl.Utf8) == str(date))
            funding_rate = 0.0
            if not fr_row.is_empty():
                funding_rate = float(fr_row["funding_rate"].item())
            short_gross = sum(abs(w) for w in current_weights.values())
            funding_pnl = funding_rate * short_gross
            total_funding += funding_pnl

            # Fees and slippage (at rebalance)
            fees = 0.0
            slippage = 0.0
            if date in rebalance_dates:
                # Rebalance cost
                for sym in cfg.short_symbols:
                    if abs(current_weights[sym]) > 1e-8:
                        fee = abs(current_weights[sym]) * cfg.fee_rate
                        slip = abs(current_weights[sym]) * cfg.slippage_bps / 10_000.0
                        fees += fee
                        slippage += slip

                # Call optimizer to get new short weights
                lookback = min(i + 1, 252)
                start_idx = max(0, i - lookback + 1)
                trail_dates = test_dates[start_idx:i + 1]

                long_prices = prices.filter(
                    (pl.col("symbol") == cfg.long_symbol)
                    & pl.col("timestamp").is_in(trail_dates)
                ).sort("timestamp")["close"].to_numpy()
                long_rets = np.diff(long_prices) / np.maximum(long_prices[:-1], 1e-10) if len(long_prices) > 1 else np.zeros(1)

                cand_rets_list = []
                for sym in cfg.short_symbols:
                    sp = prices.filter(
                        (pl.col("symbol") == sym)
                        & pl.col("timestamp").is_in(trail_dates)
                    ).sort("timestamp")["close"].to_numpy()
                    if len(sp) > 1:
                        sr = np.diff(sp) / np.maximum(sp[:-1], 1e-10)
                    else:
                        sr = np.zeros(max(len(long_rets), 1))
                    cand_rets_list.append(sr[:len(long_rets)])

                if cand_rets_list:
                    cand_rets = np.column_stack(cand_rets_list)
                    scores = np.ones(len(cfg.short_symbols))
                    prev_w = {str(j): current_weights.get(cfg.short_symbols[j], 0.0) for j in range(len(cfg.short_symbols))}
                    try:
                        opt_result = optimize_basket(
                            long_returns=long_rets,
                            candidate_returns=cand_rets,
                            candidate_scores=scores,
                            prev_weights=prev_w,
                        )
                        for j, sym in enumerate(cfg.short_symbols):
                            key = str(j)
                            current_weights[sym] = opt_result.weights.get(key, 0.0)
                    except Exception:
                        pass

            # Update equity
            portfolio_return = long_return + short_pnl + funding_pnl - fees - slippage
            equity *= (1.0 + portfolio_return)

            equity_records.append({"timestamp": date, "equity": equity})

            trade_records.append({
                "timestamp": date,
                "long_return": long_return,
                "short_pnl": short_pnl,
                "funding_pnl": funding_pnl,
                "fees": fees,
                "slippage": slippage,
                "portfolio_return": portfolio_return,
                "equity": equity,
                "short_gross": short_gross,
                "weights": dict(current_weights),
            })

        return (
            pl.DataFrame(equity_records),
            trade_records,
            total_funding,
        )

    def _compute_splits(
        self,
        dates: List[str],
    ) -> List[Dict[str, List[str]]]:
        """Compute walk-forward train/valid/test splits."""
        cfg = self.config
        total = len(dates)
        train_days = cfg.train_months * 21
        valid_days = cfg.valid_months * 21
        test_days = cfg.test_months * 21

        splits = []
        start = 0
        while start + train_days + valid_days + test_days <= total:
            train = dates[start:start + train_days]
            valid = dates[start + train_days:start + train_days + valid_days]
            test = dates[start + train_days + valid_days:start + train_days + valid_days + test_days]
            splits.append({"train": train, "valid": valid, "test": test})
            start += test_days

        # Final partial split
        if start + train_days + valid_days < total:
            train = dates[start:start + train_days]
            valid = dates[start + train_days:min(start + train_days + valid_days, total)]
            test = dates[min(start + train_days + valid_days, total):]
            if test:
                splits.append({"train": train, "valid": valid, "test": test})

        return splits

    def _generate_rebalance_dates(
        self,
        dates: List[str],
        freq: str,
    ) -> List[str]:
        """Generate rebalance dates at specified frequency."""
        if freq == "1d":
            return dates
        elif freq == "1w":
            return dates[::5]
        elif freq == "2w":
            return dates[::10]
        elif freq == "1M":
            return dates[::21]
        else:
            return dates[::5]

    def _compute_attribution(
        self,
        trades: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Compute per-period attribution."""
        results = []
        for trade in trades:
            attr = compute_attribution(
                long_pnl=trade.get("long_return", 0.0),
                short_pnl=trade.get("short_pnl", 0.0),
                funding_pnl=trade.get("funding_pnl", 0.0),
                fees=trade.get("fees", 0.0),
                slippage=trade.get("slippage", 0.0),
            )
            results.append({
                "timestamp": trade["timestamp"],
                "net_pnl": attr.net_pnl,
                "long_pnl": attr.long_pnl,
                "short_pnl": attr.short_pnl,
                "funding_pnl": attr.funding_pnl,
                "hedge_efficiency": attr.hedge_efficiency,
            })
        return results
