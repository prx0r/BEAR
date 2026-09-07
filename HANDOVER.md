# Handover — BEAR Signal Intelligence

*For the next agent. Everything you need to know.*

---

## Current State

| Metric | Value |
|--------|-------|
| Balance | $39.53 (primary key) |
| Accounts tracked | 119 nodes |
| Graph edges | 100 |
| August backtest | 37 CALL events, 26 matched |
| Top performer | @0xaporia (100% win 4h, n=3) |
| Gold set | 42 posts for extraction validation |

## What We Built

### Core System
- `AGENTS.md` — Control plane (10 rules, 5 procedures)
- `astronomer/crystallized-protocol.md` — Binary activation, continuous graph
- `astronomer/strategy-architecture.md` — Strategy entity structure
- `astronomer/extractor_v2.py` — Evidence-grounded extractor
- `astronomer/backtest.py` — Signal → price outcomes

### Data
- `astronomer/data/backtest/raw/` — 12 JSON files (cached API responses)
- `astronomer/data/prices/` — BTC/ETH/SOL/TAO hourly OHLCV
- `astronomer/data/backtest/extracted_august_v2.json` — 182 events
- `astronomer/data/backtest/backtest_august_v2.json` — 26 outcomes
- `astronomer/data/backtest/gold_set.json` — 42 validation posts

### Docs
- `AGENTS.md` — Control plane
- `quality.md` — Current vs standard assessment
- `astronomer/specs/originals/` — User messages (word-for-word)
- `astronomer/pipelineplan.md` — Full pipeline (3641 lines)

## What's Working

| Component | Status |
|-----------|--------|
| GetXAPI integration | ✅ $39.53 remaining |
| Evidence-grounded extractor | ✅ 182 events extracted |
| August backtest | ✅ 37 CALL events, 26 matched |
| Gold set | ✅ 42 posts for validation |
| Account ranking | ✅ Top 3 identified |
| Regime detection | ✅ BGeometrics integration |

## What's Not Working

| Issue | Status |
|-------|--------|
| 86% win rate inflated | FIXED (now 19 backtestable posts) |
| Default BTC fallback | FIXED (73 posts removed) |
| Multi-asset rows | FIXED (expanded to 186 rows) |
| Evidence spans | PARTIAL (55% have evidence) |
| Thread context | NOT IMPLEMENTED |
| Conditional calls | NOT IMPLEMENTED |
| Latency testing | NOT IMPLEMENTED |
| Hypothesis registry | NOT IMPLEMENTED |

## Next Agent Should Do

### Priority 1: Validate Extraction (30 min)
1. Manually label 50 posts from gold set
2. Run extractor_v2.py on them
3. Measure precision/recall
4. Fix until >90% precision

### Priority 2: Build Hypothesis Registry (1 hour)
1. Every strategy idea gets timestamped
2. Store in `astronomer/data/backtest/hypothesis_registry.jsonl`
3. Track: inputs, rule, entry, exit, reason, development_period

### Priority 3: Regime Timeline (30 min)
1. Build deterministic BTC regime from hourly data
2. EMA20, EMA50, 24h return, 7d vol
3. Store in `astronomer/data/backtest/regime_timeline.json`

### Priority 4: Full Backtest (1 hour)
1. Re-extract August with v2 extractor
2. Match 37 CALL events to outcomes
3. Compare to baseline (BTC buy-and-hold)
4. Generate source cards

### Priority 5: Crystallize (if edge exists)
1. Pick best strategy candidate
2. Define activation rules
3. Store as crystallized entity
4. Test out of sample

## Key Files

| File | Purpose |
|------|---------|
| `AGENTS.md` | Control plane — read this first |
| `quality.md` | Current vs standard assessment |
| `astronomer/specs/originals/2026-09-07-backtest-protocol-original.md` | The protocol (gospel) |
| `astronomer/extractor_v2.py` | Evidence-grounded extractor |
| `astronomer/data/backtest/gold_set.json` | 42 validation posts |
| `astronomer/data/backtest/extracted_august_v2.json` | 182 extracted events |
| `astronomer/data/backtest/backtest_august_v2.json` | 26 matched outcomes |

## API Key

```
Primary: get-x-api-0d101a57d43f429a69ff8dd821186eeb2f889406859be720
Balance: $39.53
```

## The One Rule

**Source fidelity outranks what the model thinks is true.**

Every extracted field must have an evidence span. If the extractor can't point to supporting text, the value is null.

## What Success Looks Like

After the next agent runs:

```
1. Gold set precision > 90%
2. 37 CALL events backtested with evidence
3. Regime timeline built
4. Hypothesis registry started
5. At least one crystallized strategy candidate
```
