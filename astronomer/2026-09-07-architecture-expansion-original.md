# Paywalled Data Exhaust + US Macro + Graph Architecture

*Word-for-word from user, 2026-09-07. Timestamped.*

---

## What X Cannot Reliably Replace

| Information | X gives us | What it cannot guarantee |
|-------------|------------|--------------------------|
| Order book | Expert screenshots, absorption/imbalance | Complete tick-by-tick historical L2/L3 |
| Liquidations | Heatmaps, predicted clusters | Proprietary model inputs / continuous exact map history |
| Options | GEX/skew/flow snapshots | True dealer inventory, real-time complete options state |
| On-chain | Wallet alerts and labels | Correct identity of every wallet |
| Macro | Excellent interpretations of releases | Vintage economic database + every revision |
| Crypto CEX | OI/funding/CVD observations | Internal exchange inventory/client positioning |

**The interpretation may be more valuable than the raw data.**

---

## Paywalled-Data Exhaust (New Primitive Category)

```text
primitive: DERIVED_PREMIUM_DATA

subtypes:
  LIQUIDATION_MAP
  ORDERBOOK_IMBALANCE
  OPTIONS_GEX
  OPTIONS_FLOW
  DEALER_POSITIONING
  FUNDING_BASIS
  VOL_SURFACE
  MACRO_POSITIONING
  PASSIVE_FLOW
  ONCHAIN_COHORT
```

### Key Sources

| Account | What they leak |
|---------|----------------|
| @hyblockcapital | GBAR (Global Bid Ask Ratio), OI clusters, liquidation zones |
| @laevitas1 | OI, funding, liquidations, options flow, HIP-3 reports |
| @kingfisher_btc | Liquidation maps, leverage ratios, target clusters |
| @MenthorQpro | GEX states, support/pivot/resistance zones |
| @snorlax_uw | Option OI changes, large trades |
| @unusual_whales | Options flow, dark pools, congressional trades |

---

## US Macro Panel

| Account | Primitive |
|---------|-----------|
| @EPBResearch | BUSINESS_CYCLE_SEQUENCE |
| @dampedspring | LIQUIDITY / POSITIONING / RISK_PREMIUM |
| @josephwang | FED / TREASURY / BANK_RESERVES |
| @WarrenPies | FED / GROWTH / INFLATION / CROSS-ASSET |
| @jam_croissant | VOLATILITY / DEALER_FLOW / MACRO |

---

## Five Vertical Layers

```
L0 — WORLD STATE (US growth, inflation, Fed, rates, liquidity)
         │
L1 — ASSET-CLASS REGIMES (US equities, BTC, crypto, bonds, gold)
         │
L2 — CAPITAL ROTATION (BTC→alts, stocks→crypto, sector rotation)
         │
L3 — META / ECOSYSTEM (Robinhood memes, cat meta, AI agents, TAO)
         │
L4 — INSTRUMENT (BTC, TAO, HYPE, PONS, NVDA, TSLA)
```

Plus four horizontal evidence planes:

```
ATTENTION
CAPITAL / WALLET
MARKET STRUCTURE
FUNDAMENTALS / EVENTS
```

---

## Key Architecture Change

Separate two kinds of graph edges:

**Structural dependencies** (how the world works):
```
TOKEN → INSTANCE_OF → META
META → BELONGS_TO → ECOSYSTEM
STRATEGY → DEPENDS_ON → REGIME
```

**Learned dependencies** (empirically estimated):
```
SOURCE_A → PREDICTS → META_ONSET
US_10Y → LEADS → BTC_VOL
HYBLOCK_GBAR → PREDICTS → BTC_RETURN_1H
```

Never mix them.

---

## The Final Architecture

```
                 WORLD
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
    RAW DATA              HUMAN BRAINS
 exchange/onchain             X
 macro APIs                research
 options                    interpretation
 wallets                     theses
        │                     │
        └──────────┬──────────┘
                   ▼
              PRIMITIVES
                   │
                   ▼
            TEMPORAL GRAPH
                   │
       ┌───────────┼────────────┐
       ▼           ▼            ▼
     REGIME      CAUSES?       META
     MODEL       EXPLAINER     MODEL
       │           │            │
       └───────────┼────────────┘
                   ▼
             STRATEGY GRAPH
                   │
                   ▼
          ATTENTION CONTROLLER
                   │
         "what matters NOW?"
                   │
          ┌────────┴────────┐
          ▼                 ▼
       RESEARCH           TRADE
          │                 │
          └────────┬────────┘
                   ▼
               OUTCOMES
                   │
                   ▼
               LEARNING
```

**BEAR isn't continuously looking for trades. It is continuously maintaining its best probabilistic model of what is happening in the global risk economy, and trades are downstream consequences of that model.**

---

*Timestamp: 2026-09-07*
*Source: User message to BEAR agent*
