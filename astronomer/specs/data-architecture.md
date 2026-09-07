# Data Architecture — Backtesting Studio

*Complete schema for X posts, signals, market data, outcomes, and reputation.*

---

## Directory Structure

```
BEAR/astronomer/data/
├── raw/
│   ├── x/
│   │   └── {handle}/
│   │       └── {YYYY-MM}/
│   │           ├── page_001.json.zst
│   │           ├── page_002.json.zst
│   │           └── manifest.json          # fetch metadata
│   ├── market/
│   │   ├── binance/
│   │   │   └── {SYMBOL}_{interval}.parquet
│   │   ├── hyperliquid/
│   │   │   ├── funding.parquet
│   │   │   ├── oi.parquet
│   │   │   └── liquidations.parquet
│   │   └── meta/
│   │       └── asset_registry.json
│   └── death/
│       └── {handle}/
│           └── {YYYY-MM}/
│               ├── page_001.json.zst
│               └── manifest.json
│
├── extracted/
│   ├── posts.parquet              # all posts with metadata
│   ├── signals.parquet            # extracted trading signals
│   ├── death_events.parquet       # death token observations
│   └── extraction_log.json        # audit trail
│
├── joined/
│   ├── signal_outcomes.parquet    # signals + price outcomes
│   └── death_outcomes.parquet     # death events + price outcomes
│
├── reputation/
│   ├── author_stats.parquet       # per author × asset × direction × horizon
│   ├── author_regime.parquet      # per author × regime
│   └── author_calltype.parquet    # per author × signal_type
│
├── experiments/
│   └── {experiment_id}/
│       ├── config.yaml
│       ├── trades.parquet
│       ├── metrics.json
│       └── report.html
│
└── budgets/
    └── fetch_log.jsonl            # every API call logged
```

---

## 1. X Posts Schema (posts.parquet)

Immutable. Every post ever fetched.

```python
class Post(TypedDict):
    # Identity
    tweet_id: str                    # unique
    author_handle: str               # lowercase
    author_id: str                   # numeric X user ID
    conversation_id: str             # thread ID
    
    # Content
    text: str                        # full text
    lang: str                        # language code
    
    # Timestamps
    created_at: str                  # ISO 8601
    created_at_ms: int               # milliseconds since epoch
    fetched_at: str                  # when we fetched it
    
    # Type
    is_reply: bool
    is_quote: bool
    is_retweet: bool
    in_reply_to_id: Optional[str]
    quoted_tweet_id: Optional[str]
    
    # Engagement (descriptive only — NOT predictive features)
    like_count: int
    retweet_count: int
    reply_count: int
    quote_count: int
    view_count: int
    bookmark_count: int
    
    # Entities
    hashtags: list[str]
    cashtags: list[str]              # $BTC, $ETH etc
    mentions: list[str]
    urls: list[str]
    
    # Media
    has_media: bool
    media_types: list[str]           # photo, video, animated_gif
    media_urls: list[str]
    
    # Author snapshot (at fetch time)
    author_followers: int
    author_following: int
    author_verified: bool
    
    # Provenance
    source_query: str                # the API query that returned this
    page_number: int
    raw_payload_path: str            # path to raw JSON
```

---

## 2. Extracted Signals Schema (signals.parquet)

Every actionable observation extracted from posts.

```python
class Signal(TypedDict):
    # Identity
    signal_id: str                   # unique (hash of tweet_id + extraction_version)
    tweet_id: str                    # links to posts.parquet
    author_handle: str
    
    # Classification
    signal_type: str                 # DIRECTIONAL_CALL, EXACT_LEVEL_CALL, 
                                     # CONDITIONAL_SETUP, ORDERFLOW_SIGNAL,
                                     # MARKET_STRUCTURE, FUNDING_SIGNAL,
                                     # OI_SIGNAL, TOKEN_FUNDAMENTAL,
                                     # POSITION_UPDATE, CLOSE_SIGNAL,
                                     # INVALIDATION, OBSERVATION
    
    # Direction
    direction: str                   # LONG, SHORT, NEUTRAL, OBSERVE
    
    # Assets
    assets: list[str]                # ["BTC"], ["ETH", "SOL"]
    primary_asset: str               # main asset
    
    # Levels
    entry_type: str                  # MARKET, ZONE, LEVEL, CONDITIONAL
    entry_price: Optional[float]
    entry_low: Optional[float]
    entry_high: Optional[float]
    stop_price: Optional[float]
    target_prices: list[float]
    
    # Timing
    horizon_text: str                # "1h", "this week", "swing"
    horizon_seconds: int             # estimated in seconds
    
    # Confidence
    explicit_confidence: Optional[str]  # "high conviction", "maybe"
    implicit_confidence: float          # 0-1, inferred from language
    
    # Context
    is_conditional: bool             # "if X happens then..."
    condition_text: Optional[str]
    thesis: Optional[str]            # reasoning
    
    # Metadata
    extraction_version: str          # parser version
    extraction_confidence: float     # 0-1, how sure we are about extraction
    source_text: str                 # original post text (for audit)
    extracted_at: str                # ISO timestamp
    
    # Engagement (descriptive)
    likes_at_fetch: int
    views_at_fetch: int
```

---

## 3. Death Token Events Schema (death_events.parquet)

Structured observations from death-token accounts.

```python
class DeathEvent(TypedDict):
    # Identity
    event_id: str
    tweet_id: str
    author_handle: str
    
    # Event type
    event_type: str                  # UNLOCK_ANNOUNCEMENT, DELISTING,
                                     # SECURITY_EXPLOIT, FUNDAMENTAL_DECAY,
                                     # ONSHAIN_FLOW, SUPPLY_STRUCTURE,
                                     # DERIVATIVES_SIGNAL, EXCHANGE_STATUS
    
    # Token
    token: str                       # canonical symbol
    
    # Numeric features
    unlock_usd: Optional[float]
    unlock_pct_mcap: Optional[float]
    unlock_pct_float: Optional[float]
    days_until_unlock: Optional[int]
    
    exploit_usd: Optional[float]
    exploit_pct_tvl: Optional[float]
    
    exchange_count: Optional[int]
    exchange_count_change_30d: Optional[int]
    monitoring_tag: bool
    
    # On-chain
    entity_type: Optional[str]       # TEAM, VC, WHALE, MM
    flow_action: Optional[str]       # CEX_DEPOSIT, SELL, BUY
    flow_amount_usd: Optional[float]
    
    # Derivatives
    funding_rate: Optional[float]
    oi_change: Optional[float]
    liquidation_notional: Optional[float]
    
    # Timing
    event_at: str                    # when the event happened
    published_at: str                # when it was posted
    ingested_at: str                 # when we fetched it
    
    # Raw
    source_text: str
    extraction_confidence: float
```

---

## 4. Market Data Schema

### Binance Klines (binance/{SYMBOL}_{interval}.parquet)

```python
class Kline(TypedDict):
    timestamp: int                   # open time ms
    open: float
    high: float
    low: float
    close: float
    volume: float
    close_time: int
    quote_volume: float
    trades: int
    taker_buy_volume: float
    taker_buy_quote_volume: float
```

### Hyperliquid Funding (funding.parquet)

```python
class FundingSnapshot(TypedDict):
    timestamp: int
    symbol: str
    funding_rate: float
    predicted_rate: Optional[float]
```

### Hyperliquid OI (oi.parquet)

```python
class OISnapshot(TypedDict):
    timestamp: int
    symbol: str
    open_interest: float
    open_interest_usd: float
```

---

## 5. Signal Outcomes Schema (signal_outcomes.parquet)

Computed from signals + market data.

```python
class SignalOutcome(TypedDict):
    # Identity
    signal_id: str
    
    # Entry
    entry_price: float               # price at signal + latency
    entry_latency_sec: int           # how long after signal
    entry_timestamp: int
    
    # Returns at horizons
    return_1m: Optional[float]
    return_5m: Optional[float]
    return_15m: Optional[float]
    return_1h: Optional[float]
    return_4h: Optional[float]
    return_12h: Optional[float]
    return_24h: Optional[float]
    return_3d: Optional[float]
    return_7d: Optional[float]
    
    # Excursion
    mfe_1h: Optional[float]         # max favorable excursion
    mae_1h: Optional[float]         # max adverse excursion
    mfe_24h: Optional[float]
    mae_24h: Optional[float]
    
    # Outcome
    direction_correct: bool
    target_hit: bool
    stop_hit: bool
    target_before_stop: Optional[bool]
    
    # Costs
    estimated_fees: float
    estimated_slippage: float
    
    # Net
    net_return_1h: Optional[float]
    net_return_24h: Optional[float]
    
    # Regime at signal time
    btc_regime: str                  # UPTREND, DOWNTREND, RANGE, CRASH
    btc_ema20_1h: float
    btc_ema50_4h: float
    btc_ema200_4h: float
    funding_state: str               # POSITIVE, NEGATIVE, NEUTRAL
    oi_trend: str                    # EXPANDING, CONTRACTING, FLAT
```

---

## 6. Author Reputation Schema (author_stats.parquet)

Computed from signal_outcomes.

```python
class AuthorStats(TypedDict):
    # Identity
    author_handle: str
    asset: str                       # BTC, ETH, SOL, ALL
    direction: str                   # LONG, SHORT, ALL
    signal_type: str                 # DIRECTIONAL, LEVELS, ORDERFLOW, ALL
    horizon: str                     # 1h, 4h, 24h, 7d, ALL
    
    # Sample
    n_signals: int
    n_wins: int
    
    # Performance (raw)
    win_rate: float
    avg_return: float
    median_return: float
    profit_factor: float
    
    # Performance (risk-adjusted)
    sharpe: float
    sortino: float
    max_drawdown: float
    
    # Bayesian shrinkage
    bayesian_win_rate: float         # shrunk toward prior
    confidence: str                 # sufficient (n>=30), limited (n>=10), insufficient (n<10)
    
    # MAE/MFE
    median_mfe: float
    median_mae: float
    avg_holding_period_sec: float
    
    # Decay
    half_life_hours: float          # how fast alpha decays
    
    # Last updated
    computed_at: str
```

---

## 7. Budget Log Schema (fetch_log.jsonl)

Every API call logged for cost tracking.

```python
class FetchLog(TypedDict):
    timestamp: str
    handle: str
    endpoint: str                    # /twitter/tweet/advanced_search
    query: str
    pages_fetched: int
    posts_returned: int
    cost_usd: float
    credits_before: float
    credits_after: float
    response_status: int
    error: Optional[str]
```

---

## 8. Experiment Config Schema (experiments/{id}/config.yaml)

```yaml
name: xo_btc_long_ema_filter
description: "Test if XO's BTC longs work better above EMA200"

universe:
  authors: [Trader_XO]
  assets: [BTC]
  date_range: [2026-08-01, 2026-09-07]

signal:
  sides: [LONG]
  signal_types: [DIRECTIONAL_CALL, EXACT_LEVEL_CALL]

entry:
  mode: immediate                   # immediate, level_touch, break_retest
  lag_seconds: 60

exit:
  mode: horizon
  horizon: 4h                       # 1m, 5m, 15m, 1h, 4h, 24h, 3d, 7d

filters:
  - type: technical
    name: price_above_ema
    timeframe: 1h
    period: 200

risk:
  stop_mode: atr                    # author_stop, atr, fixed_pct, none
  atr_multiplier: 1.5
  max_holding_seconds: 86400

costs:
  fee_bps: 4.5
  slippage_bps: 2.0
  latency_seconds: 60

controls:
  random_seed: 42
  min_signals: 10
  holdout_months: 1
```

---

## Key Invariants

1. **Raw data is immutable.** Never overwrite fetched posts.
2. **Engagement is descriptive, not predictive.** Never use like_count as a feature.
3. **Thread events are sequential.** Don't combine thread posts into one signal.
4. **Market alignment is critical.** Use entry_price at signal_time + latency, not tweet_time.
5. **Every experiment is reproducible.** Config hash + git commit + data hash.

---

## Parquet vs JSONL

| Data | Format | Why |
|------|--------|-----|
| Raw X posts | JSON.zst | Compressed, append-only, verbatim |
| Extracted signals | Parquet | Columnar, fast reads, typed |
| Market data | Parquet | Columnar, time-series optimized |
| Signal outcomes | Parquet | Columnar, joined with signals |
| Reputation scores | Parquet | Small, frequently queried |
| Budget logs | JSONL | Append-only, simple |
| Experiment configs | YAML | Human-readable, version-controlled |

---

*Schema version: 1.0 — 2026-09-07*
