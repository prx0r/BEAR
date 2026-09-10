# Temporal Alpha Knowledge Graph — Complete Architecture

*The unit is the primitive observation, not the influencer.*

---

## What This Becomes

> **A machine that learns who knows what, when they know it, what evidence validates them, how information propagates through crypto, and when combinations of independent primitives become tradable.**

---

## Node Types

```
SOURCE        person / bot / project / wallet / API
POST          tweet / reply / chart / article / thread / transaction
PRIMITIVE     standardized economic observation
ENTITY        BTC / HYPE / PONS / Solana / Robinhood / Base / Virtuals
NARRATIVE     Robinhood memes / cat meta / tokenized equities / AI agents
REGIME        macro risk-on / meme-hot / alt-hot / BTC dominance
ACTION        BUY / SELL / ADD / REDUCE / HOLD / ABSTAIN
OUTCOME       return / MFE / MAE / liquidity / adoption / narrative growth
```

## Edge Types (Time-Aware)

```
SOURCE ──EMITS──────────────▶ PRIMITIVE
SOURCE ──OWNS/TRADES────────▶ WALLET
POST   ──REFERENCES─────────▶ TOKEN
POST   ──AMPLIFIES──────────▶ NARRATIVE
SOURCE ──DISCOVERS──────────▶ NARRATIVE
SOURCE ──PRECEDES───────────▶ SOURCE
WALLET ──BUYS───────────────▶ TOKEN
WALLET ──SELLS──────────────▶ TOKEN
PRIMITIVE ──VALIDATED_BY────▶ ONCHAIN_EVENT
NARRATIVE ──BELONGS_TO──────▶ ECOSYSTEM
REGIME ──ENABLES────────────▶ STRATEGY
```

Every edge needs:
```
effective_at
known_at
observed_at
confidence
source
```

## Primitive Vector Per Account

```text
@yeon__
  META_DISCOVERY          0.94
  TOKEN_DISCOVERY         0.88
  NARRATIVE_THESIS        0.91
  EARLY_ENTRY             0.86
  PRICE_LEVEL             0.22

@52kskew
  ORDERFLOW               0.95
  CVD                     0.93
  OI                      0.88
  LIQUIDITY_STRUCTURE     0.91
```

## Regime Detection

```python
REGIME = {
    "BTC_trend": UPTREND | RANGE | DOWNTREND,
    "BTC_vol": LOW | NORMAL | HIGH,
    "BTC_funding": POSITIVE | NEGATIVE,
    "alt_breadth": EXPANDING | CONTRACTING,
    "meta_stage": SEED | AMPLIFICATION | SATURATION,
}
```

## Regime → Active Primitives

```python
("UPTREND", "NORMAL", "POSITIVE", "EXPANDING"):
    active: [TRADE_INTENT, ORDER_FLOW, REGIME]
    
("DOWNTREND", "HIGH", "NEGATIVE", "CONTRACTING"):
    active: [TRADE_INTENT, ORDER_FLOW, DERIVATIVES_STATE]
```

## Information Hierarchy

```
MACRO LIQUIDITY
       │
       ▼
CRYPTO RISK REGIME
       │
       ▼
CHAIN ROTATION
       │
  ┌────┼────┐
  ▼    ▼    ▼
SOL  ROBINHOOD  BASE  BNB  HYPERLIQUID
       │
       ▼
     META
       │
  ┌────┼────┐
  ▼    ▼    ▼
cats  stocks  agents
       │
       ▼
    LEADERS
       │
       ▼
 INDIVIDUAL TOKEN
```

## Meme Lifecycle Stages

```
STAGE_0: UNKNOWN
STAGE_1: SEED
STAGE_2: SMART_SCOUT_CLUSTER
STAGE_3: NARRATIVE_FORMATION
STAGE_4: KOL_AMPLIFICATION
STAGE_5: LIQUIDITY_BREAKOUT
STAGE_6: MAINSTREAM / LISTING
STAGE_7: SATURATION / DISTRIBUTION
```

## Alpha Lead Metric

```
originator_score
attention_lead_hours
entry_mcap_percentile
multiple_after_first_call
drawdown_after_call
false_discovery_rate
repeatability
```

## The Product

```
PRIVATE SIGNAL (T=0)
    │
    │  signal JSON
    │  Merkle proof
    │  calibrated probability
    ▼
PUBLIC RELEASE (T+30min)
    │
    │  beautiful card
    │  verifiable timestamp
    │  evidence breakdown
    ▼
OUTCOME ENGINE
    │
    ▼
RESULT CARD
    │  private-entry return
    │  public-entry return
    │  MFE / MAE
    │  benchmark comparison
```

## Sources by Ecosystem

### Robinhood / Memes
yeon__, SevaFTW, 0xnobi, kenjidgn, PhilOnChain, Wolves_Techml, theunipcs, blknoiz06, Overdose_AI, 2442lll, rasmr_eth, MoneyPrinter0x, KookCapitalLLC

### Onchain Intelligence
ai_9684xtpa, OnchainLens, lookonchain, bubblemaps, DefiSquared

### Hyperliquid
NMTD8, 0xBroze, HyperliquidR, chameleon_jeff, _stevenhl, iliensinc, xulian_hl, GLC_Research, FourPillarsFP

### Base
jessepollak, base, zora, virtuals_io, bankrbot, aixbt_agent, davidtsocy

### AI Agents
0xJeff, ethermage, virtuals_io, bankrbot, aixbt_agent, truth_terminal, AndyAyrey

### Solana
mert, rajgokal, aeyakovenko, weremeow, solana, JupiterExchange, RaydiumEco, blknoiz06

### Macro / Market Structure
Trader_XO, 52kskew, exitpumpBTC, Husslin_, macrocephalopod, Timeless_Crypto, astronomer_zero, chrono_chartist

---

## The Key Insight

**The important unit is no longer the influencer. It is the primitive observation.**

When 3 independent sources emit:
```
TOKEN_DISCOVERY
META_DISCOVERY
SMART_WALLET_ACCUMULATION
```

about the same token, the graph produces:
```
CAT_META_EARLY = 0.82
```

No one source said that. The system inferred it from independent evidence.

That's the actual moat.

---

*Architecture version: 2.0 — Complete*
