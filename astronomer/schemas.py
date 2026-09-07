"""Pydantic models for X signal backtesting studio."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SignalType(str, Enum):
    NO_SIGNAL = "NO_SIGNAL"
    DIRECTIONAL_CALL = "DIRECTIONAL_CALL"
    EXACT_LEVEL_CALL = "EXACT_LEVEL_CALL"
    CONDITIONAL_SETUP = "CONDITIONAL_SETUP"
    BREAKOUT_CALL = "BREAKOUT_CALL"
    MEAN_REVERSION_CALL = "MEAN_REVERSION_CALL"
    RANGE_CALL = "RANGE_CALL"
    ORDERFLOW_SIGNAL = "ORDERFLOW_SIGNAL"
    MARKET_STRUCTURE = "MARKET_STRUCTURE"
    FUNDING_SIGNAL = "FUNDING_SIGNAL"
    OI_SIGNAL = "OI_SIGNAL"
    LIQUIDATION_SIGNAL = "LIQUIDATION_SIGNAL"
    MACRO_SIGNAL = "MACRO_SIGNAL"
    TOKEN_FUNDAMENTAL = "TOKEN_FUNDAMENTAL"
    POSTMORTEM = "POSTMORTEM"
    POSITION_UPDATE = "POSITION_UPDATE"
    CLOSE_SIGNAL = "CLOSE_SIGNAL"
    INVALIDATION = "INVALIDATION"
    OBSERVATION = "OBSERVATION"


class Direction(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"
    OBSERVE = "OBSERVE"


class EntryType(str, Enum):
    MARKET = "MARKET"
    ZONE = "ZONE"
    LEVEL = "LEVEL"
    CONDITIONAL = "CONDITIONAL"


class BTCRegime(str, Enum):
    UPTREND = "UPTREND"
    DOWNTREND = "DOWNTREND"
    RANGE = "RANGE"
    LOW_VOL = "LOW_VOL"
    NORMAL_VOL = "NORMAL_VOL"
    HIGH_VOL = "HIGH_VOL"
    CRASH = "CRASH"


class VolumeState(str, Enum):
    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"


class FundingState(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"
    EXTREME_POSITIVE = "EXTREME_POSITIVE"
    EXTREME_NEGATIVE = "EXTREME_NEGATIVE"


class OITrend(str, Enum):
    EXPANDING = "EXPANDING"
    CONTRACTING = "CONTRACTING"
    FLAT = "FLAT"


class VolumeState(str, Enum):
    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"


class Confidence(str, Enum):
    SUFFICIENT = "sufficient"       # n >= 30
    LIMITED = "limited"             # n >= 10
    INSUFFICIENT = "insufficient"   # n < 10


class DeathEventType(str, Enum):
    UNLOCK_ANNOUNCEMENT = "UNLOCK_ANNOUNCEMENT"
    DELISTING = "DELISTING"
    SECURITY_EXPLOIT = "SECURITY_EXPLOIT"
    FUNDAMENTAL_DECAY = "FUNDAMENTAL_DECAY"
    ONSHAIN_FLOW = "ONCHAIN_FLOW"
    SUPPLY_STRUCTURE = "SUPPLY_STRUCTURE"
    DERIVATIVES_SIGNAL = "DERIVATIVES_SIGNAL"
    EXCHANGE_STATUS = "EXCHANGE_STATUS"
    MONITORING_TAG = "MONITORING_TAG"


# ---------------------------------------------------------------------------
# Core Data Classes
# ---------------------------------------------------------------------------

@dataclass
class Post:
    """Immutable X post."""
    tweet_id: str
    author_handle: str
    author_id: str
    conversation_id: str
    text: str
    lang: str
    created_at: str
    created_at_ms: int
    fetched_at: str
    is_reply: bool = False
    is_quote: bool = False
    is_retweet: bool = False
    in_reply_to_id: Optional[str] = None
    quoted_tweet_id: Optional[str] = None
    like_count: int = 0
    retweet_count: int = 0
    reply_count: int = 0
    quote_count: int = 0
    view_count: int = 0
    bookmark_count: int = 0
    hashtags: list[str] = field(default_factory=list)
    cashtags: list[str] = field(default_factory=list)
    mentions: list[str] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)
    has_media: bool = False
    media_types: list[str] = field(default_factory=list)
    media_urls: list[str] = field(default_factory=list)
    author_followers: int = 0
    author_following: int = 0
    author_verified: bool = False
    source_query: str = ""
    page_number: int = 0
    raw_payload_path: str = ""


@dataclass
class Signal:
    """Extracted trading signal."""
    signal_id: str
    tweet_id: str
    author_handle: str
    signal_type: SignalType
    direction: Direction
    call_type: str = ""              # BREAKOUT, REVERSAL, SWING, SCALP, ORDERFLOW
    assets: list[str] = field(default_factory=list)
    primary_asset: str = "BTC"
    entry_type: EntryType = EntryType.MARKET
    entry_price: Optional[float] = None
    entry_low: Optional[float] = None
    entry_high: Optional[float] = None
    trigger_price: Optional[float] = None  # price that activates trade
    stop_price: Optional[float] = None
    invalidation_price: Optional[float] = None  # explicit invalidation level
    target_prices: list[float] = field(default_factory=list)
    horizon_text: str = ""
    horizon_seconds: int = 0
    explicit_confidence: Optional[str] = None
    implicit_confidence: float = 0.5
    requires_condition: bool = False
    is_conditional: bool = False
    condition_text: Optional[str] = None
    thesis: Optional[str] = None
    timeframes: list[str] = field(default_factory=list)  # ["4h", "1d"]
    extraction_version: str = "1.0"
    extraction_confidence: float = 0.5
    source_text: str = ""
    extracted_at: str = ""
    likes_at_fetch: int = 0
    views_at_fetch: int = 0


@dataclass
class DeathEvent:
    """Death token observation."""
    event_id: str
    tweet_id: str
    author_handle: str
    event_type: DeathEventType
    token: str
    unlock_usd: Optional[float] = None
    unlock_pct_mcap: Optional[float] = None
    unlock_pct_float: Optional[float] = None
    days_until_unlock: Optional[int] = None
    exploit_usd: Optional[float] = None
    exploit_pct_tvl: Optional[float] = None
    exchange_count: Optional[int] = None
    exchange_count_change_30d: Optional[int] = None
    monitoring_tag: bool = False
    entity_type: Optional[str] = None
    flow_action: Optional[str] = None
    flow_amount_usd: Optional[float] = None
    funding_rate: Optional[float] = None
    oi_change: Optional[float] = None
    liquidation_notional: Optional[float] = None
    event_at: str = ""
    published_at: str = ""
    ingested_at: str = ""
    source_text: str = ""
    extraction_confidence: float = 0.5


@dataclass
class SignalOutcome:
    """Signal matched to price outcomes."""
    signal_id: str
    
    # Execution timestamps
    decision_timestamp: int = 0     # when signal was generated
    execution_timestamp: int = 0    # when simulated fill happened
    reference_price: float = 0.0    # price at decision time
    
    # Entry
    entry_price: float = 0.0
    entry_latency_sec: int = 0
    
    # Simulated fill
    simulated_fill: float = 0.0     # actual fill after latency
    spread: float = 0.0             # spread cost
    fee: float = 0.0                # exchange fee
    slippage: float = 0.0           # execution slippage
    
    # Returns at horizons
    return_1m: Optional[float] = None
    return_5m: Optional[float] = None
    return_15m: Optional[float] = None
    return_1h: Optional[float] = None
    return_4h: Optional[float] = None
    return_12h: Optional[float] = None
    return_24h: Optional[float] = None
    return_3d: Optional[float] = None
    return_7d: Optional[float] = None
    
    # Excursion
    mfe_1h: Optional[float] = None
    mae_1h: Optional[float] = None
    mfe_24h: Optional[float] = None
    mae_24h: Optional[float] = None
    
    # Outcome
    exit_price: Optional[float] = None
    direction_correct: bool = False
    target_hit: bool = False
    stop_hit: bool = False
    target_before_stop: Optional[bool] = None
    
    # Net
    net_return: Optional[float] = None
    net_return_1h: Optional[float] = None
    net_return_24h: Optional[float] = None
    
    # Regime at signal time
    btc_regime: str = ""
    btc_ema20_1h: float = 0.0
    btc_ema50_4h: float = 0.0
    btc_ema200_4h: float = 0.0
    
    # Derivatives state
    funding_state: str = ""         # POSITIVE, NEGATIVE, NEUTRAL
    funding_rate: Optional[float] = None
    oi_trend: str = ""              # EXPANDING, CONTRACTING, FLAT
    oi_change_pct: Optional[float] = None
    
    # Volume state
    volume_state: str = ""          # HIGH, NORMAL, LOW
    volume_percentile: Optional[float] = None


@dataclass
class ThreadEvent:
    """Individual event in a thread sequence."""
    event_id: str
    signal_id: str
    tweet_id: str
    author_handle: str
    event_type: str                  # CREATE, ADD_STOP, REDUCE, CLOSE, INVALIDATE
    timestamp: str
    timestamp_ms: int
    text: str
    stop_price: Optional[float] = None
    target_price: Optional[float] = None
    size_change_pct: Optional[float] = None  # + = add, - = reduce


@dataclass
class BacktestTrade:
    """A single simulated trade."""
    trade_id: str
    signal_id: str
    author_handle: str
    asset: str
    direction: str                   # LONG, SHORT
    
    # Timestamps
    signal_time: str
    decision_time: str
    execution_time: str
    
    # Prices
    signal_price: float
    reference_price: float
    simulated_fill: float
    
    # Exit
    exit_price: Optional[float] = None
    exit_time: Optional[str] = None
    exit_reason: str = ""            # TARGET, STOP, TIME, REGIME_CHANGE
    
    # Costs
    fee: float = 0.0
    slippage: float = 0.0
    spread: float = 0.0
    funding: float = 0.0
    
    # Returns
    gross_return: float = 0.0
    net_return: float = 0.0
    
    # Excursion
    mfe: float = 0.0
    mae: float = 0.0
    
    # Regime
    btc_regime: str = ""
    funding_state: str = ""
    oi_trend: str = ""
    
    # Strategy
    strategy_id: str = ""


@dataclass
class AuthorStats:
    """Per author × asset × direction × horizon reputation."""
    author_handle: str
    asset: str
    direction: str
    signal_type: str
    horizon: str
    n_signals: int = 0
    n_wins: int = 0
    win_rate: float = 0.0
    avg_return: float = 0.0
    median_return: float = 0.0
    profit_factor: float = 0.0
    sharpe: float = 0.0
    sortino: float = 0.0
    max_drawdown: float = 0.0
    bayesian_win_rate: float = 0.5
    confidence: str = "insufficient"
    median_mfe: float = 0.0
    median_mae: float = 0.0
    avg_holding_period_sec: float = 0.0
    half_life_hours: float = 0.0
    computed_at: str = ""


@dataclass
class FetchLog:
    """API call log entry."""
    timestamp: str
    handle: str
    endpoint: str
    query: str
    pages_fetched: int
    posts_returned: int
    cost_usd: float
    credits_before: float
    credits_after: float
    response_status: int
    error: Optional[str] = None
