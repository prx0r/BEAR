"""Unlock pressure factor with recipient weighting (Delphi Digital 2026).

Measures expected sell pressure from token unlock events weighted by
recipient type. Team/insider unlocks carry higher sell pressure than
community/ecosystem unlocks.
"""

from __future__ import annotations

from datetime import datetime, timezone

import structlog
import polars as pl

logger = structlog.get_logger()

_DEFAULT_RECIPIENT_WEIGHTS: dict[str, float] = {
    "team": 1.0,
    "investor": 0.8,
    "foundation": 0.4,
    "community": 0.25,
    "ecosystem": 0.1,
}


def compute_unlock_pressure(
    unlock_schedule: pl.DataFrame,
    market_data: pl.DataFrame,
    recipient_weights: dict[str, float] | None = None,
) -> pl.DataFrame:
    """Compute unlock pressure features.

    Args:
        unlock_schedule: DataFrame with columns:
            - symbol: asset ticker
            - unlock_time: datetime of unlock event
            - tokens: number of tokens unlocked
            - usd_value: USD value at unlock time
            - team_tokens: tokens going to team (nullable)
            - investor_tokens: tokens going to investors (nullable)
            - foundation_tokens: tokens going to foundation (nullable)
            - community_tokens: tokens going to community (nullable)
            - ecosystem_tokens: tokens going to ecosystem (nullable)
        market_data: DataFrame with columns:
            - symbol: asset ticker
            - market_cap: current market cap
            - adv_usd: average daily volume in USD
            - open_interest_usd: total open interest (nullable)
        recipient_weights: Optional override for recipient type weights.
            Default: team=1.0, investor=0.8, foundation=0.4,
            community=0.25, ecosystem=0.1.

    Returns:
        DataFrame with columns:
            - symbol
            - unlock_adv_ratio: next unlock USD / ADV
            - insider_unlock_adv: (team_usd + investor_usd) / ADV
            - unlock_mcap_ratio: next unlock USD / market_cap
            - unlock_oi_ratio: next unlock USD / open_interest_usd
            - days_to_unlock: min days until next unlock
            - recipient_pressure: weighted sum / ADV
    """
    weights = recipient_weights or _DEFAULT_RECIPIENT_WEIGHTS

    required_unlock = {"symbol", "unlock_time", "usd_value"}
    missing_unlock = required_unlock - set(unlock_schedule.columns)
    if missing_unlock:
        raise ValueError(f"unlock_schedule missing required columns: {missing_unlock}")

    required_market = {"symbol", "market_cap", "adv_usd"}
    missing_market = required_market - set(market_data.columns)
    if missing_market:
        raise ValueError(f"market_data missing required columns: {missing_market}")

    now = datetime.now(timezone.utc)

    symbols = market_data["symbol"].unique().to_list()
    results: list[dict] = []

    for sym in symbols:
        market_row = market_data.filter(pl.col("symbol") == sym)
        if market_row.height == 0:
            continue
        mkt = market_row.row(0, named=True)

        adv = mkt.get("adv_usd")
        if adv is None or adv <= 0:
            adv = None
        mcap = mkt.get("market_cap")
        oi = mkt.get("open_interest_usd")

        sym_unlocks = (
            unlock_schedule
            .filter(pl.col("symbol") == sym)
            .filter(pl.col("unlock_time") > pl.lit(now))
            .sort("unlock_time")
        )

        if sym_unlocks.height == 0:
            results.append({
                "symbol": sym,
                "unlock_adv_ratio": 0.0,
                "insider_unlock_adv": 0.0,
                "unlock_mcap_ratio": 0.0,
                "unlock_oi_ratio": 0.0,
                "days_to_unlock": 999.0,
                "recipient_pressure": 0.0,
            })
            continue

        next_unlock = sym_unlocks.row(0, named=True)
        unlock_usd = next_unlock.get("usd_value") or 0.0

        unlock_time = next_unlock["unlock_time"]
        if hasattr(unlock_time, "tzinfo") and unlock_time.tzinfo is None:
            unlock_time = unlock_time.replace(tzinfo=timezone.utc)
        days_to_unlock = max(0.0, (unlock_time - now).total_seconds() / 86400)

        team_tokens = next_unlock.get("team_tokens") or 0.0
        investor_tokens = next_unlock.get("investor_tokens") or 0.0
        foundation_tokens = next_unlock.get("foundation_tokens") or 0.0
        community_tokens = next_unlock.get("community_tokens") or 0.0
        ecosystem_tokens = next_unlock.get("ecosystem_tokens") or 0.0

        team_usd = _estimate_usd_share(team_tokens, next_unlock.get("tokens"), unlock_usd)
        investor_usd = _estimate_usd_share(investor_tokens, next_unlock.get("tokens"), unlock_usd)
        foundation_usd = _estimate_usd_share(foundation_tokens, next_unlock.get("tokens"), unlock_usd)
        community_usd = _estimate_usd_share(community_tokens, next_unlock.get("tokens"), unlock_usd)
        ecosystem_usd = _estimate_usd_share(ecosystem_tokens, next_unlock.get("tokens"), unlock_usd)

        insider_usd = team_usd + investor_usd

        unlock_adv = unlock_usd / adv if adv and adv > 0 else 0.0
        insider_adv = insider_usd / adv if adv and adv > 0 else 0.0
        unlock_mcap = unlock_usd / mcap if mcap and mcap > 0 else 0.0
        unlock_oi = unlock_usd / oi if oi and oi > 0 else 0.0

        weighted_sum = (
            team_usd * weights.get("team", 1.0)
            + investor_usd * weights.get("investor", 0.8)
            + foundation_usd * weights.get("foundation", 0.4)
            + community_usd * weights.get("community", 0.25)
            + ecosystem_usd * weights.get("ecosystem", 0.1)
        )
        recipient_pressure = weighted_sum / adv if adv and adv > 0 else 0.0

        results.append({
            "symbol": sym,
            "unlock_adv_ratio": unlock_adv,
            "insider_unlock_adv": insider_adv,
            "unlock_mcap_ratio": unlock_mcap,
            "unlock_oi_ratio": unlock_oi,
            "days_to_unlock": days_to_unlock,
            "recipient_pressure": recipient_pressure,
        })

    return pl.DataFrame(results)


def _estimate_usd_share(
    token_share: float,
    total_tokens: float | None,
    total_usd: float,
) -> float:
    """Estimate USD value of a recipient's token allocation."""
    if token_share <= 0 or total_usd <= 0:
        return 0.0
    if total_tokens and total_tokens > 0:
        return (token_share / total_tokens) * total_usd
    return 0.0
