# New Agent Context — What I Understand

*Simulated new agent perspective after reading AGENTS.md + HANDOVER.md.*

---

## What I Know

### Identity
I am BEAR's autonomous operator. I discover information sources, crystallize strategies, and track when they should be active. I am not an assistant.

### The Edge
The edge is NOT "which token to buy." It's: **predicting WHEN crystallized strategies should turn on, based on continuous graph state.**

### Current State
- $39.53 in GetXAPI credits
- 119 accounts in the graph
- 182 events extracted from August
- 26 matched outcomes
- 42 gold-set posts for validation
- Price data: BTC/ETH/SOL/TAO hourly

### What's Been Proven
- @0xaporia: 100% win 4h — BUT n=3, too small, could be luck
- @Timeless: 89% win 4h — n=9, better but still small
- @lookonchain: 67% win 4h — onchain flow validated
- Only 15% of posts are PREDICTION (properly classified)

### What's NOT Been Proven
- No strategy has survived out-of-sample testing
- No crystallized strategy exists yet
- The 100% win rate is based on 3 signals (not statistically significant)
- The 86% win rate was inflated by regex keyword matching

---

## What I Should NOT Do

1. **Don't claim anything is "proven" or "validated"** — we have 26 matched outcomes, not a backtest
2. **Don't treat n=3 as alpha** — 0xaporia's 100% win rate is a coin flip with small sample bias
3. **Don't skip the gold set validation** — extraction quality is the bottleneck
4. **Don't assume "S-tier" means "proven"** — S-tier means highest expected information value, not proven profitability
5. **Don't hardcode API keys** — Rule 0, incident on 2026-09-07
6. **Don't filter during ingestion** — Rule 1, store everything

---

## What I Should Do First

### Step 1: Validate Extraction (30 min)
1. Read `astronomer/specs/originals/2026-09-07-backtest-protocol-original.md` — this is the gospel
2. Open `astronomer/data/backtest/gold_set.json` — 42 posts to manually label
3. Run `astronomer/extractor_v2.py` on them
4. Compare extractor output to manual labels
5. Measure precision/recall
6. Fix until >90% precision

### Step 2: Build Hypothesis Registry (1 hour)
1. Every strategy idea gets timestamped
2. Store in `astronomer/data/backtest/hypothesis_registry.jsonl`
3. Track: inputs, rule, entry, exit, reason, development_period

### Step 3: Regime Timeline (30 min)
1. Build deterministic BTC regime from hourly data
2. EMA20, EMA50, 24h return, 7d vol
3. Store in `astronomer/data/backtest/regime_timeline.json`

### Step 4: Full Backtest (1 hour)
1. Re-extract August with v2 extractor
2. Match 37 CALL events to outcomes
3. Compare to baseline (BTC buy-and-hold)
4. Generate source cards

---

## Key Files I Need to Read

| File | Why |
|------|-----|
| `AGENTS.md` | The rules I must follow |
| `QUALITY.md` | What standard I'm held to |
| `specs/originals/2026-09-07-backtest-protocol-original.md` | The protocol (gospel) |
| `extractor_v2.py` | The code I need to validate |
| `data/backtest/gold_set.json` | The 42 posts I need to label |
| `data/backtest/extracted_august_v2.json` | The 182 events I need to verify |

---

## What Success Looks Like

After my first session:

```
1. Gold set precision > 90%
2. 37 CALL events properly classified
3. Regime timeline built
4. Hypothesis registry started
5. At least one crystallized strategy candidate
```

**Not:**
- "I found a 100% win rate" (sample too small)
- "I scraped 10,000 tweets" (quantity ≠ quality)
- "I built a trading bot" (too early)

---

## The One Rule

**Source fidelity outranks what the model thinks is true.**

Every extracted field must have an evidence span. If the extractor can't point to supporting text, the value is null.

---

## What I Don't Know Yet

- Which accounts actually have predictive power (need n>30)
- Whether regime detection works (need more data)
- Whether the crystallized strategy architecture is correct (need testing)
- Whether X signals contain alpha at all (need proper backtest)

**The answer to all of these is: run the protocol and find out.**

---

*This is what I understand. This is what I should do. This is what I should NOT assume.*
