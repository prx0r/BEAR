# Alpha Mining Protocol v2

*Discover what each source uniquely knows. Extract it losslessly. Only afterward determine if it predicts anything.*

---

## Core Principle

> **Alpha type cannot be hardcoded before recon.**

The protocol doesn't ask "does this account say LONG/SHORT?"
It asks: **"What information does this account appear unusually good at expressing, and in what form?"**

## The Pipeline

```
SOURCE (X account, Telegram, wallet, etc.)
  │
  ▼
① LOSSLESS RECON
  │  "What nuggets are here?"
  ▼
② ALPHA DISCOVERY
  │  "What uniquely valuable info does this source emit?"
  ▼
③ MINING SPEC (freeze)
  │  "Here's what we're extracting and how"
  ▼
④ FULL LOSSLESS CORPUS
  │  Every post, reply, thread, media, article
  ▼
⑤ SPEC-DRIVEN EXTRACTION
  │  Apply the frozen spec to the corpus
  ▼
⑥ EXTRACTION QA
  │  precision, recall, false positives
  │  NO PRICE OUTCOMES YET
  ▼
⑦ PRICE BLIND LINE
  │  ────── nothing above knows prices ──────
  ▼
⑧ OBJECTIVE LABELS / MARKET JOIN
  │  Match to price outcomes
  ▼
⑨ WALK-FORWARD EVALUATION
  │  Does this alpha predict returns?
  ▼
⑩ REPUTATION BY ALPHA TYPE × REGIME × HORizon
  │
  ▼
⑪ LIVE SAME-SPEC EXTRACTION
```

## Alpha Channel Primitives

Standard families (extensible):

```
TRADE_INTENT          directional calls, entries, exits
PRICE_MAP             support, resistance, targets, invalidation
CONDITIONAL_SETUP     "if X then Y" structures
POSITION_UPDATE       adds, closes, conviction changes

ORDER_FLOW            CVD, OI, bid/ask, depth, walls
DERIVATIVES_STATE     funding, leverage, liquidation
ONCHAIN_FLOW          whale movements, exchange flows

CATALYST               unlocks, listings, delistings, events
FUNDAMENTAL            revenue, TVL, users, fees
TOKENOMICS             supply, emissions, vesting

REGIME                  trend, range, volatility state
NARRATIVE               meta, theme, rotation
ATTENTION_SHIFT         social volume, creator count

TOKEN_DISCOVERY         early calls, new token identification
META_DISCOVERY          who finds the finders

INVALIDATION            level breaks, thesis negation
EXIT                    position closure, conviction loss
```

**The protocol MUST be allowed to invent new channels.**

If an account's alpha is "identifies when CZ changes profile picture," that becomes:

```
primitive = SOCIAL_GRAPH_EVENT
subtype = founder_profile_symbol_change
```

## The MiningSpec

```yaml
account: Timeless_Crypto
source_type: x_account
corpus_hash: abc123
protocol_version: 2.0

alpha_channels:
  - id: directional_short_conviction
    description: "Bearish trade views at local exhaustion"
    primitive: TRADE_INTENT
    evidence_forms: [text, reply, chart]
    likely_horizons: [4h, 24h]
    needs_media: true

  - id: chart_price_map
    description: "Entry/invalidation/target in chart annotations"
    primitive: PRICE_MAP
    evidence_forms: [image]
    needs_media: true

  - id: position_management
    description: "Adds, closes, invalidations"
    primitive: POSITION_UPDATE
    evidence_forms: [reply, self_thread]
    requires_context: true

noise_patterns:
  - generic commentary
  - retrospective victory posts
  - promotional content

unknown_channels:
  - preserve for later discovery
```

## Key Changes From v1

| v1 (Current) | v2 (New) |
|---------------|----------|
| Hardcoded keywords (LONG/SHORT) | Discover keywords from content |
| Fixed asset list | Discover assets from content |
| Filter replies before extraction | Extract from all content types |
| Backtest during discovery | Separate discovery from evaluation |
| Signal = immediate trade idea | Signal = any information with potential predictive value |
| Single signal type | Multiple alpha channels per account |
| Price outcomes in validation | Price outcomes only after extraction QA |

## The Meme Protocol Extension

Same pipeline, different source type:

```
SOURCE: FOMO wallet, Telegram, X scout
  │
  ▼
ALPHA DISCOVERY:
  "This person consistently identifies tokens
   before they reach $1M market cap"
  │
  ▼
MINING SPEC:
  token_discovery:
    evidence: [tweet, wallet_action]
    metrics:
      - time_before_major_move
      - market_cap_at_call
      - multiple_after_call
      - repeatability
  │
  ▼
LIFECYCLE TRACKING:
  STAGE_0: UNKNOWN
  STAGE_1: SEED
  STAGE_2: SMART_SCOUT_CLUSTER
  STAGE_3: NARRATIVE_FORMATION
  STAGE_4: KOL_AMPLIFICATION
  STAGE_5: LIQUIDITY_BREAKOUT
  STAGE_6: MAINSTREAM
  STAGE_7: SATURATION
```

## The Alpha Lead Metric

For meme tokens:

```
originator_score
attention_lead_hours
entry_mcap_percentile
multiple_after_first_call
drawdown_after_call
false_discovery_rate
repeatability
```

## FOMO Wallet Integration

```
X CLAIM → FOMO WALLET ACTION → ONCHAIN OUTCOME

Tweet 12:01: "this is going to billions"
Wallet 11:58: buys $8,000
Day 3: wallet exits +430%

= VERIFIED POSITION CALL

Tweet 12:01: "this is going to billions"
Wallet 11:59: SELLING

= EXIT SIGNAL
```

## Source Types (Extensible)

The protocol works for ANY information source:

```bash
bear protocol run --source x:@Timeless_Crypto
bear protocol run --source x:@0xPickleCati
bear protocol run --source fomo_wallet:0x...
bear protocol run --source telegram:@channel
bear protocol run --source binance_announcements
bear protocol run --source robinhood_trenches
```

Each discovers its own alpha grammar.

## Separation of Concerns

```
EXTRACTION VALIDATION (no prices)
  precision, recall, false positives
  thread accuracy, asset resolution
  ↓
FREEZE MiningSpec v1
  ↓
EVALUATION (with prices)
  does alpha_channel X predict Y?
  ↓
  If extraction needs redesign → MiningSpec v2
  ↓
  New OOS period required
```

---

*Protocol version: 2.0*
