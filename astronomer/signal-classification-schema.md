# Signal Classification Schema

*Reference guide for classifying X posts. Use this to manually classify, not as an ML model.*

---

## Event Kind (MANDATORY for every post)

| Kind | Definition | Example | Backtest? |
|------|------------|---------|-----------|
| **PREDICTION** | Explicit trade call with direction | "BTC long here" | ✅ YES |
| **OBSERVATION** | Market data without direction | "whale bought $15M HYPE" | ❌ NO |
| **INTERPRETATION** | Analysis without explicit call | "OI looks like chasing longs" | ❌ NO |
| **RETROSPECTIVE** | Past tense, already happened | "I told you so" | ❌ NO |
| **PROMOTION** | Course, product, service | "my course launching" | ❌ NO |
| **POSITION_UPDATE** | Existing position change | "took half off" | ⚠️ MAYBE |

## Direction (only for PREDICTION)

| Direction | Definition | Example |
|-----------|------------|---------|
| **LONG** | Expects price to rise | "BTC long here" |
| **SHORT** | Expects price to fall | "shorting 80k" |
| **NEUTRAL** | No directional call | "waiting for setup" |

## Negation Detection (CRITICAL)

```
"long volatility"           → NOT a BTC long (it's volatility)
"not one long taken"        → NOT a long (negation)
"shorting support"          → IS a short (but risky)
"market looks bullish"      → NOT specific BTC call
"BTC looks bullish"         → IS a directional view
"I'm not long here"         → NOT a long (negation)
"shorting into strength"    → IS a short (contrarian)
```

**Rule:** If the word "long/short" appears but is negated or refers to something other than the asset, do NOT classify as PREDICTION.

## Asset Resolution

```
$BTC / BTC / Bitcoin     → BTC
$ETH / ETH / Ethereum   → ETH
$SOL / SOL / Solana     → SOL
$HYPE / HYPE            → HYPE
$TAO / TAO              → TAO
"the market"             → BTC (default)
"alts"                   → ALTS basket
```

**Rule:** If no specific asset mentioned, default to BTC. If multiple assets, list all.

## Entry/Target/Stop Extraction

```python
# Entry
"long at 78k"           → entry_price = 78000
"long zone 77-78k"      → entry_low=77000, entry_high=78000
"long here"             → entry_type = MARKET (use current price)

# Target
"target 82k"            → target_prices = [82000]
"targets 80k, 85k"      → target_prices = [80000, 85000]
"tp at 80k"             → target_prices = [80000]

# Stop
"stop 76k"              → stop_price = 76000
"invalid below 76k"     → stop_price = 76000
"SL 76k"                → stop_price = 76000
```

## Conditional Detection

```
"If BTC reclaims 80k, I'm long"
→ is_conditional = True
→ condition = "BTC > 80000"
→ direction = LONG (but only if condition met)

"long above 78k"
→ is_conditional = True
→ entry_type = LEVEL
→ entry_price = 78000
```

**Rule:** Conditional signals are NOT PREDICTION until the condition is met. Store as OBSERVATION with conditional flag.

## Retrospective Filter

```
EXCLUDE if:
- past tense: "was", "were", "did", "told you"
- after the move: "see, I was right"
- no forward projection
- only commentary about what happened
```

## Confidence Levels

```
HIGH:   Explicit entry + stop + target + horizon
MEDIUM: Direction + some levels
LOW:    Direction only, no levels
```

## The Schema In Code

```python
@dataclass
class ClassifiedPost:
    tweet_id: str
    author: str
    timestamp_ms: int
    
    # Event kind (MANDATORY)
    event_kind: str  # PREDICTION, OBSERVATION, INTERPRETATION, RETROSPECTIVE, PROMOTION
    
    # If PREDICTION:
    direction: Optional[str]  # LONG, SHORT, NEUTRAL
    assets: list[str]         # ["BTC", "ETH"]
    entry_type: str           # MARKET, ZONE, LEVEL, CONDITIONAL
    entry_price: Optional[float]
    entry_low: Optional[float]
    entry_high: Optional[float]
    stop_price: Optional[float]
    target_prices: list[float]
    horizon_seconds: int
    conviction: str           # HIGH, MEDIUM, LOW
    is_conditional: bool
    
    # Metadata
    source_text: str
    extraction_confidence: float
```
