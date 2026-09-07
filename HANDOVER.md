# HANDOVER.md — The Operational Bible

*This document is the definitive handoff for the next agent.*
*Read this first. Then read AGENTS.md. Then check data/ for current state.*

---

## What This Project Is

**BEAR** is a signal intelligence engine that discovers which X accounts contain exploitable forward information for crypto markets, crystallizes that intelligence into executable strategies, and tracks when each strategy should be active.

**Core thesis:** Continuous graph + crystallized strategies + binary activation = the edge

**Endgame:** A machine that learns who knows what, when they know it, what evidence validates them, how information propagates through crypto, and when combinations of independent primitives become tradable.

---

## Repo Layout

```
/root/BEAR/
├── AGENTS.md                    ← THE CONTROL PLANE (10 binding rules)
├── HANDOVER.md                  ← THIS FILE (operational bible)
├── QUALITY.md                   ← Current vs standard assessment
├── PLAN.md                      ← Strategy + backtest plan
│
├── astronomer/                  ← Signal intelligence module
│   ├── config/                  # Account registry, budget
│   │   ├── accounts.json        # 119 nodes, tier/weight
│   │   ├── BUDGET.md            # API tracking
│   │   └── canonical-registry.md
│   │
│   ├── specs/                   # Architecture documents
│   │   ├── crystallized-protocol.md  # Main strategy
│   │   ├── strategy-architecture.md  # Binary activation
│   │   ├── protocol.md               # Alpha Mining v2
│   │   ├── meta-science.md           # Meta lifecycle
│   │   ├── minimal-backtest-plan.md  # What data we need
│   │   ├── backtest-methodology.md   # How to score properly
│   │   ├── signal-classification-schema.md  # Event kinds
│   │   └── originals/                # User messages
│   │
│   ├── src/                       # Code
│   │   ├── extractor_v2.py        # Evidence-grounded extractor
│   │   ├── backtest.py            # Signal → outcomes
│   │   ├── pipeline.py            # Fetch pipeline
│   │   ├── regime.py              # BGeometrics regime
│   │   └── schemas.py             # Data models
│   │
│   ├── data/                      # Data + results
│   │   ├── backtest/
│   │   │   ├── raw/              # Cached API responses
│   │   │   ├── extracted_august_v2.json  # 182 events
│   │   │   ├── backtest_august_v2.json   # 26 outcomes
│   │   │   ├── gold_set.json     # 42 validation posts
│   │   │   └── classified_august.json
│   │   ├── prices/               # BTC/ETH/SOL/TAO OHLCV
│   │   └── regime/               # BTC regime detection
│   │
│   ├── archive/                  # Batch archives
│   └── docs/getxapi/            # API documentation
│
├── src/bear/
│   ├── social/                   # XReader adapter
│   ├── backtest/                 # Walk-forward backtester
│   └── hyperliquid/              # HL integration
│
└── data/                         # Price data, regime, etc.
```

---

## Current State

| Metric | Value |
|--------|-------|
| API Balance | $39.53 (primary key) |
| Accounts tracked | 119 nodes |
| Graph edges | 100 |
| August backtest | 37 CALL events, 26 matched |
| Top performer | @0xaporia (100% win 4h, n=3) |
| Gold set | 42 posts for validation |
| Price data | BTC/ETH/SOL/TAO hourly (23K+ candles) |

---

## What We Built

### Core System
- AGENTS.md — Control plane (10 rules, 5 procedures)
- crystallized-protocol.md — Binary activation, continuous graph
- strategy-architecture.md — Strategy entity structure
- extractor_v2.py — Evidence-grounded extractor
- backtest.py — Signal → price outcomes

### Data
- 12 JSON files (cached API responses)
- 182 extracted events from August
- 26 matched outcomes
- 42 gold-set posts for validation
- 23K+ hourly price candles

### Key Results
- @0xaporia: 100% win 4h (n=3) — regime specialist
- @Timeless: 89% win 4h — SHORT conviction
- @lookonchain: 67% win 4h — onchain flow
- Only 15% of posts are PREDICTION (properly classified)

---

## The Protocol (Gospel)

See: `astronomer/specs/originals/2026-09-07-backtest-protocol-original.md`

Key principles:
1. Evidence-grounded extraction (every field needs evidence span)
2. No BTC default (null for unknown assets)
3. One asset per outcome
4. Two evaluation lanes (trade vs information)
5. Regime classification from market data only
6. Gold set for extraction validation

---

## Next Agent Should

### Priority 1: Validate Extraction (30 min)
1. Manually label 50 posts from gold set
2. Run extractor_v2.py
3. Measure precision/recall
4. Fix until >90% precision

### Priority 2: Build Hypothesis Registry (1 hour)
1. Every strategy idea timestamped
2. Store in hypothesis_registry.jsonl

### Priority 3: Regime Timeline (30 min)
1. Deterministic BTC regime from hourly data
2. EMA20, EMA50, 24h return, 7d vol

### Priority 4: Full Backtest (1 hour)
1. Re-extract August with v2 extractor
2. Match 37 CALL events to outcomes
3. Compare to baseline
4. Generate source cards

---

## Key Files

| File | Purpose |
|------|---------|
| `AGENTS.md` | Control plane — read first |
| `QUALITY.md` | Current vs standard |
| `HANDOVER.md` | This file |
| `astronomer/specs/originals/2026-09-07-backtest-protocol-original.md` | The protocol |
| `astronomer/extractor_v2.py` | Evidence-grounded extractor |
| `astronomer/data/backtest/gold_set.json` | 42 validation posts |
| `astronomer/data/backtest/extracted_august_v2.json` | 182 events |

## API Key

```
Primary: get-x-api-0d101a57d43f429a69ff8dd821186eeb2f889406859be720
Balance: $39.53
```

## The One Rule

**Source fidelity outranks what the model thinks is true.**
