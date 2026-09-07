# Build Notes — 2026-09-07

## What We Did

### Data Acquisition
- Fetched 2yr history for 5 core traders (Timeless, XO, Astro, Bheem, EliZ)
- Total: 5,896 tweets, 940 strict calls, 2,793 backtest outcomes
- Fetched August data for 30+ additional accounts
- Spent $3.10 total (balance: $36.90)

### Key Experiments Run
1. Bearish run length optimization
2. Holding period optimization
3. Win streak continuation
4. Call frequency analysis
5. Regime transition accuracy
6. Sentiment deterioration patterns
7. Asset rotation patterns
8. MFE/MAE risk/reward analysis

### Infrastructure Built
- `agent.py` — LLM trading agent (OpenCode MiMo V2.5)
- `src/getxapi/` — Budget-enforced API client
- `backfill_core3.py` — 2yr data fetcher
- `regime.py` — BTC regime detection
- `metrics.py` — Performance metrics
- `baselines.py` — Baseline models
- Core 3 data structure (data/core3/)
- Per-source file structure (data/sources/)

### Strategies Crystallized
- STRAT-004: Confluence (XO + Timeless + regime)
- STRAT-005: Death Token optimized (death_score + trader signals)
- STRAT-003: Bheem ETH levels (79% win at 4h)

## What We Found

### Strongest Edges (n>=10)
1. XO after 3+ bullish: 78% win, +2.47% (n=9)
2. Timeless bearish run=2: 74% win, +2.53% (n=19)
3. Astro 12h: 58% win, +0.16% (n=460)
4. Timeless hot streaks: 61% continuation (n=112)

### Key Insights
- Regime is the only thing that matters — no edge without it
- Traders do NOT predict regime transitions (25-27%)
- XO's bullish streaks self-reinforce (78-86% after 3+)
- Timeless's bearish runs work at exactly 2 consecutive calls
- Both traders win on frequency, not magnitude (MFE < MAE)
- The regex classifier was lying about CryptoBheem (79% → 38%)

### Current State (Sep 15)
- BTC: $78,810, RANGE regime
- XO: cautious before FOMC Sep 15-16, hedging
- Timeless: bearish, signed off Sep 2
- Astro: local bullish, medium-term bearish
- Bheem: SOL target hit, BTC resistance 86-90k
- Action: WAIT for FOMC to resolve

## Budget
- Balance: $36.90
- Used this session: $3.10
- Remaining: $36.90
- Plan expires: 2026-10-07

## Files Modified
- AGENTS.md, HANDOVER.md, PLAN.md
- astronomer/backtest.py, regime.py, schemas.py, metrics.py, baselines.py
- astronomer/agent.py (LLM trading agent)
- astronomer/src/getxapi/ (budget-enforced API client)
- astronomer/data/core3/ (normalized data, outcomes, feature matrix)
- astronomer/research/experiments/ (5 strategies, experiment results)
- Handled: carbon/, pump-public-docs/, pump-fun-skills/ (cloned)
