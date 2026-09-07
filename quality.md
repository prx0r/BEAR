# Quality Assessment — Current vs Standard

*Comparing what we have against what the protocol requires.*

---

## My Current Quality vs The Standard

| Area | Current State | Standard Required | Gap |
|------|---------------|-------------------|-----|
| **Event Kind** | Regex keyword matching | 6 typed event kinds with evidence | CRITICAL |
| **Asset handling** | Default BTC fallback | null for unknown, never BTC default | FIXED |
| **Direction extraction** | "long" = LONG signal | Provenance class (EXPLICIT/INFERRED/UNKNOWN) | LARGE |
| **Evidence spans** | None | Every field must have quote + char offsets | CRITICAL |
| **Thread handling** | Merge all posts | Chronological events, no future leak | LARGE |
| **Conditional calls** | Ignored | CONDITIONAL + trigger + NOT_TRIGGERED | LARGE |
| **Retrospective filter** | Basic keyword | Proper past-tense + "I told you so" detection | MEDIUM |
| **Execution costs** | None | fee, slippage, funding per trade | LARGE |
| **Latency testing** | Fixed 1h | Multiple latencies (1m, 5m, 15m, 60m) | LARGE |
| **Gold set** | 42 posts | 200-300 posts | LARGE |
| **Regime classification** | Regex heuristic | Deterministic EMA-based with persistence | LARGE |
| **Outcome schema** | Multi-asset rows | One asset per outcome, no fallback | FIXED |
| **Deduplication** | Basic | UNIQUE(event_id, asset) invariant | MEDIUM |
| **Statistical reporting** | "86% win rate" | Posterior, credible interval, shrinkage | LARGE |
| **Hypothesis registry** | None | Timestamped log of every hypothesis tried | LARGE |

## What's Actually Good

| Area | Status |
|------|--------|
| Architecture design | ✅ Correct |
| Source universe | ✅ Strong |
| Data architecture spec | ✅ Correct direction |
| Price data | ✅ 23K+ candles |
| API integration | ✅ GetXAPI working |
| Budget tracking | ✅ Logged |
| Graph structure | ✅ 119 nodes |

## What Needs Fixing

| Priority | Fix |
|----------|-----|
| P0 | Replace Signal abstraction (mixes trade + outlook + levels) |
| P0 | Evidence spans for every field |
| P0 | No BTC default |
| P0 | One asset per outcome |
| P1 | Thread chronological events |
| P1 | Conditional call handling |
| P1 | Retrospective filter |
| P1 | Execution cost model |
| P2 | Latency sensitivity testing |
| P2 | Gold set expansion (42 → 200-300) |
| P2 | Regime classification |
| P2 | Hypothesis registry |
| P3 | LLM extraction with evidence verification |
| P3 | Dual evaluation lanes |

## The Core Issue

**We're currently testing the extractor, not the traders.**

The 86% win rate was:
- Inflated by default BTC
- Inflated by keyword matching "long volatility" as LONG
- Inflated by not accounting for execution costs
- Not validated against a gold set

**Real signal density: 15% of posts are PREDICTION.**
**Real backtestable posts: 19 (after fixing defaults).**

## The Path Forward

1. Fix remaining assumptions (multi-asset, duplicates)
2. Build evidence-grounded extractor (schema v2)
3. Build gold set (200-300 posts)
4. Validate extractor (>90% precision)
5. Re-extract August with proper schema
6. THEN backtest

**Not before.**
