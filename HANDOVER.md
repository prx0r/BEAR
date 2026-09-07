# HANDOVER.md — The Operational Bible

*This document is the definitive handoff for the next agent.*
*Read this first. Then read AGENTS.md. Then check data/ for current state.*

---

## What This Project Is

**BEAR** is a signal intelligence engine that discovers which X accounts contain exploitable forward information for crypto markets, crystallizes that intelligence into executable strategies, and tracks when each strategy should be active.

**Core thesis:** Continuous graph + crystallized strategies + binary activation = the edge

**Endgame:** A machine that learns who knows what, when they know it, what evidence validates them, how information propagates through crypto, and when combinations of independent primitives become tradable.

---

## What Was Built (2026-09-07)

### Core 3 Traders
- **Timeless_Crypto** — 2yr data (2,658 tweets, 390 strict calls)
- **Trader_XO** — 2yr data (776 tweets, 89 strict calls)
- **astronomer_zero** — 2yr data (766 tweets, 461 strict calls)

### Additional Traders
- **CryptoBheem** — 2yr data (883 tweets, 72 BTC calls)
- **eliz883** — 2yr data (813 tweets, 23 BTC calls)

### Key Edges Found (2yr data, n>=10)
| Signal | N | Win | Mean | How |
|--------|---|-----|------|-----|
| XO after 3+ bullish | 9 | 78% | +2.47% | Momentum continuation |
| Timeless bearish run=2 | 19 | 74% | +2.53% | Short squeeze reversal |
| Astro 12h | 460 | 58% | +0.16% | Consistent edge |
| Timeless hot streak | 112 | 61% | +0.57% | Streaks continue |

### Strategies Crystallized
1. **STRAT-004: Confluence** — XO DOWN 4h + Timeless RANGE 24h = +69.4% over 2yr
2. **STRAT-005: Death Token Optimized** — death_score + trader regime filter
3. **STRAT-003: Bheem ETH Levels** — 79% win at 4h (but n=14, needs validation)

### LLM Agent
- `agent.py` — Reads live tweets, decides ON/OFF for strategies
- Uses OpenCode Zen MiMo V2.5
- Correctly identifies: regime UP → all short strategies OFF

---

## Current State

### Market (Sep 15, 2026)
- **BTC: $78,810** — RANGE regime
- **XO:** "Inflection points... hedging into FOMC Sep 15-16"
- **Timeless:** Bearish, signed off Sep 2
- **Astro:** "Local upside, more downside" — short-term bullish, macro bearish
- **Bheem:** SOL target hit, BTC resistance 86-90k

### Action: WAIT
FOMC Sep 15-16 is the catalyst. XO is hedging into it. No clear entry.

### Budget
- Balance: $36.90
- Plan expires: 2026-10-07

---

## Repo Layout

```
/root/BEAR/
├── AGENTS.md                    ← THE CONTROL PLANE
├── HANDOVER.md                  ← THIS FILE
├── BUILD_NOTES.md               ← Session build notes
├── PLAN.md                      ← Strategy + backtest plan
│
├── astronomer/                  ← Signal intelligence module
│   ├── agent.py                 # LLM trading agent (MiMo V2.5)
│   ├── backtest.py              # Canonical backtest engine
│   ├── regime.py                # BTC regime detection
│   ├── schemas.py               # Canonical data types
│   ├── metrics.py               # Performance metrics
│   ├── baselines.py             # Baseline models
│   ├── extractor_v2.py          # Evidence-grounded extractor
│   ├── run_backtest.py          # Full pipeline runner
│   ├── src/getxapi/             # Budget-enforced API client
│   ├── data/core3/              # Core 3 normalized data
│   │   ├── normalized/          # all_events, outcomes, feature_matrix
│   │   └── ml/                  # Experiment results
│   ├── data/backtest/           # Raw API responses, outcomes
│   ├── data/regime/             # BTC regime timeline
│   ├── data/prices/             # BTC/ETH/SOL/HYPE hourly
│   ├── data/live/               # Live monitoring feed
│   ├── research/experiments/    # Strategy files + results
│   └── specs/                   # Architecture docs + user messages
│
├── carbon/                      # Pump.fun indexer (cloned, unused)
├── pump-public-docs/            # Official Pump IDLs
├── pump-fun-skills/             # Pump agent skills
│
├── src/bear/                    # Full BEAR codebase
│   ├── backtest/                # Walk-forward backtester
│   ├── features/                # Death score signals (22 modules)
│   ├── models/                  # Death hazard model
│   └── social/                  # XReader adapter
│
└── data/
    ├── binance/                 # 65 token price files
    ├── live/                    # Dead coins, funding, pressure
    └── death_score_results.json # Death token strategy results
```

---

## How to Run

### Quick backtest
```bash
cd astronomer && python3 backtest.py
```

### Full pipeline
```bash
cd astronomer && python3 run_backtest.py
```

### LLM agent
```bash
cd astronomer && python3 agent.py
```

### Monitor live
```bash
cd astronomer && python3 monitor.py
```

### Fetch new data
```bash
cd astronomer && python3 -c "
from src.getxapi import GetXAPI
with GetXAPI() as api:
    tweets = api.user_tweets('HandleName', max_pages=50)
"
```

---

## Key Files for Next Agent

| File | Purpose |
|------|---------|
| `BUILD_NOTES.md` | What was built and found |
| `research/experiments/all_experiment_results.json` | All 8 experiment results |
| `research/experiments/STRAT-004-CONFLUENCE.json` | Best strategy (+69.4%) |
| `data/core3/normalized/strict_calls.json` | 940 properly classified calls |
| `data/core3/normalized/all_outcomes.json` | 1,876 backtest outcomes |
| `data/core3/ml/feature_matrix.json` | Feature matrix for ML |
| `agent.py` | LLM trading agent |
| `src/getxapi/client.py` | Budget-enforced API client |

---

## What NOT to Do

1. **Don't add more accounts until Core 3 is validated**
2. **Don't use regex for classification** — it lies about direction
3. **Don't skip budget checks** — every API call goes through GetXAPI
4. **Don't ignore regime** — no edge without it
5. **Don't trust small n** — n<10 is meaningless

---

## The One Rule

**Source fidelity outranks what the model thinks is true.**

Every extracted field must have an evidence span. If the extractor can't point to supporting text, the value is null.

---

*Last updated: 2026-09-15*
*Next agent: Read this, then AGENTS.md, then data/core3/normalized/ for the actual numbers.*
