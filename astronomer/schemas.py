"""Canonical data types for BEAR signal intelligence.

These are the ONLY types used in the backtest pipeline.
No defaults to BTC. No flat multi-asset outcomes. No guesswork.

Source fidelity outranks what the model thinks is true.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SemanticKind(str, Enum):
    CALL = "CALL"
    VIEW = "VIEW"
    OBSERVATION = "OBSERVATION"
    INTERPRETATION = "INTERPRETATION"
    RETROSPECTIVE = "RETROSPECTIVE"
    NON_SIGNAL = "NON_SIGNAL"
    MEME = "MEME"


class MemeAction(str, Enum):
    ENTRY = "ENTRY"
    ADD = "ADD"
    BULLISH_THESIS = "BULLISH_THESIS"
    HOLD = "HOLD"
    TARGET = "TARGET"
    REDUCE = "REDUCE"
    EXIT = "EXIT"
    BEARISH = "BEARISH"
    RETROSPECTIVE = "RETROSPECTIVE"
    MENTION = "MENTION"
    IGNORE = "IGNORE"


class CallState(str, Enum):
    DIRECT = "DIRECT"
    CONDITIONAL = "CONDITIONAL"
    UPDATE = "UPDATE"
    REDUCE = "REDUCE"
    EXIT = "EXIT"
    NONE = "NONE"


class Stance(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"
    UNKNOWN = "UNKNOWN"


class Provenance(str, Enum):
    EXPLICIT = "EXPLICIT"
    CONTEXT_RESOLVED = "CONTEXT_RESOLVED"
    INFERRED = "INFERRED"
    UNKNOWN = "UNKNOWN"


class Primitive(str, Enum):
    REGIME = "REGIME"
    PRICE_STRUCTURE = "PRICE_STRUCTURE"
    ORDER_FLOW_LIQUIDITY = "ORDER_FLOW_LIQUIDITY"
    DERIVATIVES_POSITIONING = "DERIVATIVES_POSITIONING"
    REAL_MONEY_POSITIONING = "REAL_MONEY_POSITIONING"
    ONCHAIN_CAPITAL_FLOW = "ONCHAIN_CAPITAL_FLOW"
    STRUCTURAL_SUPPLY_FUNDAMENTALS = "STRUCTURAL_SUPPLY_FUNDAMENTALS"
    CATALYST_ATTENTION = "CATALYST_ATTENTION"
    OTHER = "OTHER"


class SignalDirection(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"
    UNKNOWN = "UNKNOWN"


# ---------------------------------------------------------------------------
# Core Data Classes
# ---------------------------------------------------------------------------

@dataclass
class EvidenceSpan:
    """Exact quote supporting a field value. Required for every non-null field."""
    field: str
    post_id: str
    quote: str
    start_char: int
    end_char: int
    provenance: str = "EXPLICIT"  # Provenance enum value


@dataclass
class AssetRef:
    """Generic crypto asset reference. Dynamic, not hardcoded."""
    symbol: Optional[str] = None
    contract_address: Optional[str] = None
    chain: Optional[str] = None
    name: Optional[str] = None
    resolution_status: str = "UNRESOLVED"  # UNRESOLVED, RESOLVED, AMBIGUOUS, NO_PRICE_DATA


@dataclass
class MemeEvent:
    """Meme-specific event with campaign tracking."""
    event_id: str
    post_id: str
    author_id: str
    author_handle: str
    published_at: str

    # Action
    action: MemeAction
    asset: AssetRef = field(default_factory=AssetRef)

    # Campaign
    campaign_id: str = ""       # {handle}:{symbol}:{month}
    is_first_call: bool = False

    # Content
    conviction: str = "MEDIUM"  # LOW, MEDIUM, HIGH
    explicit_entry: bool = False
    entry_price: Optional[float] = None
    target_price: Optional[float] = None

    # Evidence
    evidence: list[EvidenceSpan] = field(default_factory=list)

    # Provenance
    extraction_version: str = "meme_v1"


@dataclass
class MemeCampaign:
    """Collapsed campaign for a single token by a single trader."""
    campaign_id: str            # {handle}:{symbol}:{month}
    handle: str
    symbol: str
    chain: Optional[str] = None
    contract_address: Optional[str] = None
    pool_address: Optional[str] = None

    # Lifecycle
    first_call_at: str = ""
    first_action: str = ""
    actions: list[dict] = field(default_factory=list)  # [{timestamp, action, price}]

    # Outcomes (filled after price data available)
    entry_price: Optional[float] = None
    return_1h: Optional[float] = None
    return_4h: Optional[float] = None
    return_24h: Optional[float] = None
    return_3d: Optional[float] = None
    return_7d: Optional[float] = None
    max_multiple: Optional[float] = None
    hit_2x: bool = False
    hit_5x: bool = False
    hit_10x: bool = False

    # Metadata
    entry_market_cap: Optional[float] = None
    entry_liquidity: Optional[float] = None


@dataclass
class RawPost:
    """Immutable X post. This is the source of truth. Never filtered during ingestion."""
    tweet_id: str
    author_id: str
    author_handle: str
    created_at: str            # ISO 8601 UTC
    created_at_ms: int
    text: str
    conversation_id: str
    reply_to_id: Optional[str] = None
    quote_id: Optional[str] = None
    repost_of_id: Optional[str] = None
    media_ids: list[str] = field(default_factory=list)
    raw_sha256: str = ""
    provider: str = ""         # getxapi, twitterapi_io, etc.
    ingestion_version: str = "2.0"
    observed_at: str = ""      # when we fetched it


@dataclass
class MarketEvent:
    """Extracted market event from a post. One post can yield multiple events."""
    event_id: str
    post_id: str
    author_id: str
    author_handle: str
    published_at: str          # ISO 8601 UTC (from post.created_at)

    # Classification
    semantic_kind: SemanticKind
    call_state: CallState = CallState.NONE
    stance: Stance = Stance.UNKNOWN
    primitive: Primitive = Primitive.OTHER

    # Asset — NULL means UNKNOWN. NEVER default to BTC.
    asset: Optional[str] = None

    # Direction
    direction: Optional[SignalDirection] = None

    # Entry
    entry_type: Optional[str] = None       # MARKET, ZONE, LEVEL, CONDITIONAL
    entry_price: Optional[float] = None
    entry_low: Optional[float] = None
    entry_high: Optional[float] = None

    # Stop / target
    stop_price: Optional[float] = None
    target_prices: list[float] = field(default_factory=list)

    # Conditional
    trigger_price: Optional[float] = None
    condition_text: Optional[str] = None

    # Timeframe
    horizon_hours: Optional[int] = None
    horizon_explicit: bool = False

    # Conviction
    conviction: str = "MEDIUM"

    # Features (for non-trade primitives)
    features: dict = field(default_factory=dict)
    # e.g. {"oi": "RISING", "spot_confirmation": "ABSENT", "crowding": "LONG"}

    # Evidence — REQUIRED for all non-null fields
    evidence: list[EvidenceSpan] = field(default_factory=list)

    # Provenance
    extraction_version: str = "2.0"
    git_sha: str = ""


@dataclass
class EventOutcome:
    """One event × one asset × one execution interpretation.

    INVARIANT: one EventOutcome = one event_id × one asset.
    Never multi-asset in a flat dictionary.
    """
    event_id: str
    asset: str                 # NEVER null. UNKNOWN if not determined.

    # Execution
    entry_time: str = ""       # ISO 8601 UTC — first candle AFTER publication
    entry_price: float = 0.0   # close of entry candle
    direction: str = ""        # BULLISH or BEARISH from the event

    # Returns — stored as decimal. 0.00338 = 0.338%, NOT 0.003%.
    return_1h: Optional[float] = None
    return_4h: Optional[float] = None
    return_24h: Optional[float] = None
    return_7d: Optional[float] = None

    # Abnormal returns (beta-adjusted)
    abnormal_return_4h: Optional[float] = None
    abnormal_return_24h: Optional[float] = None

    # Excursion
    mfe_4h: Optional[float] = None
    mae_4h: Optional[float] = None
    mfe_24h: Optional[float] = None
    mae_24h: Optional[float] = None

    # Direction correctness
    direction_correct_4h: Optional[bool] = None
    direction_correct_24h: Optional[bool] = None

    # Execution status
    trigger_status: str = "EXECUTED"  # EXECUTED, NOT_TRIGGERED, EXPIRED
    trigger_time: Optional[str] = None

    # Costs
    fee_rate: float = 0.001    # 0.1% round trip
    slippage_rate: float = 0.0005
    net_return_4h: Optional[float] = None
    net_return_24h: Optional[float] = None

    # Market state at event time (point-in-time)
    btc_price_at_event: Optional[float] = None
    btc_regime: Optional[str] = None     # UP, DOWN, RANGE
    btc_vol_state: Optional[str] = None  # NORMAL_VOL, HIGH_VOL
    btc_ema20: Optional[float] = None
    btc_ema50: Optional[float] = None
    funding_state: Optional[str] = None
    oi_trend: Optional[str] = None
    volume_state: Optional[str] = None

    # Metadata
    outcome_version: str = "2.0"
    git_sha: str = ""


@dataclass
class SourceReputation:
    """Source × primitive × asset × direction × regime × horizon.

    This is the canonical reputation unit. Never collapse dimensions.
    """
    source_handle: str
    source_id: str
    primitive: str
    asset: str
    direction: str
    regime: str
    horizon: str

    n: int = 0
    wins: int = 0
    win_rate: float = 0.0
    mean_return: float = 0.0
    median_return: float = 0.0
    profit_factor: float = 0.0
    mfe: float = 0.0
    mae: float = 0.0
    expected_value: float = 0.0
    bayesian_win_rate: float = 0.5
    confidence: str = "insufficient"  # sufficient, limited, insufficient


@dataclass
class ExperimentRecord:
    """Append-only experiment log entry."""
    experiment_id: str
    created_at: str
    hypothesis: str
    economic_mechanism: str
    falsification_rule: str
    development_period: str
    sources: list[str] = field(default_factory=list)
    primitives: list[str] = field(default_factory=list)
    baseline_features: list[str] = field(default_factory=list)
    candidate_features: list[str] = field(default_factory=list)
    target: str = ""
    horizon: str = ""
    entry_rule: str = ""
    exit_rule: str = ""
    cost_model: str = ""
    extractor_version: str = ""
    dataset_version: str = ""
    git_sha: str = ""
    trials_before_this: int = 0
    decision_rule_predeclared: str = ""
    results: dict = field(default_factory=dict)
    decision: str = ""  # KEEP, REJECT, INCONCLUSIVE


@dataclass
class MarketStateSnapshot:
    """Point-in-time market state at event publication time.

    The source's own post cannot define the objective regime.
    This is captured independently from market data.
    """
    timestamp: str            # ISO 8601 UTC
    timestamp_ms: int

    # BTC trend
    btc_price: float = 0.0
    btc_regime: str = ""      # UP, DOWN, RANGE
    btc_vol_state: str = ""   # NORMAL_VOL, HIGH_VOL
    btc_ema20_1h: float = 0.0
    btc_ema50_1h: float = 0.0
    btc_24h_return: float = 0.0
    btc_7d_return: float = 0.0
    btc_7d_vol: float = 0.0

    # Asset-specific (if asset != BTC)
    asset_price: Optional[float] = None
    asset_regime: Optional[str] = None
    asset_24h_return: Optional[float] = None
    asset_btc_beta: Optional[float] = None

    # Derivatives (if available)
    funding_rate: Optional[float] = None
    funding_state: str = "UNKNOWN"
    oi_change_24h: Optional[float] = None
    oi_trend: str = "UNKNOWN"

    # Volume
    volume_state: str = "UNKNOWN"
    volume_percentile: Optional[float] = None
