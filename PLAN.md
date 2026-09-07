# BEAR Signal Intelligence — Plan & Process

*Peer review document. What we're building, what we might be missing, what's actually cool.*

---

## Current State

### What We Have

| Component | Status | Data |
|-----------|--------|------|
| X signal scraping | ✅ Working | 800+ posts, 4 accounts |
| Signal extraction | ✅ Working | 145 directional signals |
| Price matching | ✅ Working | 591 outcomes |
| Batch processor | ✅ Working | 10-call batches with review |
| API server | ✅ Running | 6 endpoints on port 8877 |
| GetXAPI Pro | ✅ Active | $40 balance, 40K calls |
| Canonical registry | ✅ Created | 20 accounts, data structures |

### What We've Proven

| Finding | Evidence |
|---------|----------|
| Timeless SHORT is real | 29 signals, 55% win 4h, +0.20% avg |
| XO has structural levels | May posts with 76s, 78s, 81.5 |
| Bheem = Tier B | 34 posts total, too sparse |
| Low-engagement beats high | 62% vs 36% win rate |
| 9am-11am UTC is best | 64% win rate |

---

## The Honest Question: Are We Missing Anything?

### Option A: Extract Everything First, Query Later

**Pros:**
- Simple pipeline
- No premature optimization
- Can always re-query later
- Less code to maintain

**Cons:**
- May waste API calls on low-signal data
- No early feedback on what works
- Storage costs (Parquet adds up)

### Option B: Staged Extraction with Backtesting

**Pros:**
- Test hypotheses early
- Refine filters before scaling
- Learn what works before committing budget
- More scientific approach

**Cons:**
- More complex pipeline
- May over-optimize on small samples
- Slower to get full dataset

### My Assessment

**We're currently doing Option B** (staged batches with review). This is correct for the research phase.

**But we should switch to Option A once we validate the pipeline.** The 10-call batch review is slowing us down. With $40 in credits, we should:

1. Run a 100-call test batch (validate pipeline)
2. If clean, run full historical backfill (2,000+ calls)
3. Then query and backtest

**The bottleneck is not data collection — it's signal extraction quality.** We can collect 40K tweets, but if the extractor can't distinguish "long BTC" from "my course is launching," the data is worthless.

---

## What Might We Be Missing?

### 1. Graph-Based Structures

**The idea:** Map who replies to whom, who quotes whom, who follows whom. Build a social graph of CT. Find hidden clusters of signal.

**Is it worth it?**
- We have reply/quote data in our raw tweets
- We could build: `author A replies to author B` → influence graph
- This could identify: "when 3 unconnected traders all post bullish, it's stronger than 3 people quoting each other"

**Verdict: Yes, but defer.** We already have the independence weighting in the pipeline plan. Build the graph after we have 6+ months of data.

### 2. Chart/Image Extraction

**The idea:** Many traders put levels in charts, not text. Extract tickers, support/resistance, trend lines from images.

**Is it worth it?**
- GetXAPI returns `media[]` with image URLs
- We could run vision models on charts
- But: this is hard, expensive, and error-prone

**Verdict: Defer.** Text extraction covers 80% of value. Chart extraction is the last 20% and hardest to implement.

### 3. Thread Context

**The idea:** When a trader posts "entry 78k" in a thread, the previous tweet might have the thesis. Get the full thread for context.

**Is it worth it?**
- GetXAPI has `/tweet/thread` endpoint ($0.005/call)
- Could dramatically improve signal extraction
- But: most signals are standalone posts, not threads

**Verdict: Yes, implement later.** After we have the basic pipeline working, add thread context for high-value signals.

### 4. Reply Context

**The idea:** When a trader replies to someone with "agree, short here," that's a signal hidden in a reply.

**Is it worth it?**
- GetXAPI has `/tweet/replies` endpoint ($0.001/call)
- Could catch signals we're missing
- But: replies are noisy, lots of "thanks" and "great call"

**Verdict: Defer.** Not enough signal density in replies to justify the cost.

### 5. Follower Graph Mining

**The idea:** Find who the good traders follow. Those accounts might also be good.

**Is it worth it?**
- GetXAPI has `/user/following` endpoint ($0.001/call)
- Could discover new signal sources
- But: we already have 20 accounts, enough for now

**Verdict: Defer.** Do this when we need to expand the universe.

### 6. Regime-Aware Extraction

**The idea:** Extract different signal types depending on BTC regime. In UPTREND, focus on LONG signals. In DOWNTREND, focus on SHORT signals.

**Is it worth it?**
- Could improve signal quality
- But: regime detection itself is noisy
- And: we don't have enough data to test this yet

**Verdict: Defer.** Need 6+ months of data before regime-aware extraction makes sense.

---

## What's Actually Cool That We're Not Using

### 1. Real-Time Monitoring (Pro Plan Feature)

**This is the biggest untapped opportunity.**

GetXAPI Pro includes real-time webhooks at NO per-call cost. We can:

```python
# Set up once
POST /monitor/webhook/create → get webhook_id
POST /monitor/add → watch astronomer_zero

# Then tweets arrive automatically
POST /webhook/x → process signal → store
```

**Benefit:** 2s latency, no polling costs, no missed tweets.

**Implementation:** Already added `/webhook/x` endpoint. Need to:
1. Create webhook
2. Add monitors for Tier S accounts
3. Process incoming tweets

### 2. Tweet Thread Resolution

**The idea:** When a trader posts "entry 78k" → "stop 76k" → "target 82k" → "TP hit", get the full thread for context.

**GetXAPI:** `/tweet/thread` ($0.005/call)

**Benefit:** Turns fragmented posts into structured trade logs.

**Implementation:** After extracting a signal, check if it's part of a thread. If so, fetch the full thread for entry/stop/target context.

### 3. MCP Server

**The idea:** Expose all our data via MCP protocol so AI agents can query it.

**GetXAPI has MCP support built in.** We could:
- Add our own MCP server on top
- Let Claude/Cursor query our signal database
- Build natural language interfaces to the data

**Implementation:** Already have endpoints. Need MCP wrapper.

### 4. User Search for Discovery

**The idea:** Find new signal sources by searching for accounts that post about specific topics.

**GetXAPI:** `/user/search` ($0.001/call)

```python
# Find accounts that post about "BTC orderflow"
GET /twitter/user/search?q=orderflow+BTC+lang:en
```

**Benefit:** Automated discovery of new signal sources.

### 5. Trends for Regime Detection

**The idea:** Track trending topics to detect regime changes.

**GetXAPI:** `/twitter/trends` ($0.001/call)

```python
# Get current trending topics
GET /twitter/trends
```

**Benefit:** When "crypto" trends with negative sentiment → potential DETERIORATION regime.

---

## The Plan (What I'd Actually Build)

### Phase 1: Data Collection (Week 1)

```
1. Backfill core accounts (4 × 24 months)
   - ~4,320 calls = $2.16
   - Store in data/raw/ as Parquet

2. Set up real-time monitoring
   - Create webhook
   - Add monitors for 8 Tier S accounts
   - Process incoming tweets automatically

3. Test thread extraction
   - For high-value signals, fetch full thread
   - Store thread context alongside signal
```

### Phase 2: Signal Extraction (Week 2)

```
1. Run full extraction on all data
   - Multi-class: DIRECTIONAL, LEVELS, FLOW, OBSERVATION
   - Store in data/extracted/ as Parquet

2. Match to price outcomes
   - 1h, 4h, 24h returns
   - MFE, MAE
   - Regime context

3. Build author reputation scores
   - Per asset × direction × horizon × regime
   - Bayesian shrinkage for small samples
```

### Phase 3: Backtesting (Week 3)

```
1. Test basic strategies
   - Raw directional
   - Author-filtered
   - Regime-filtered

2. Test confluence
   - Multi-author agreement
   - Independence weighting

3. Test relative value
   - Long strong alts + short weak tokens
```

### Phase 4: Dashboard + MCP (Week 4)

```
1. Update dashboard with signal performance
2. Add MCP server for AI agent access
3. Set up automated reporting
```

---

## What We're NOT Missing

| Idea | Why Not Now |
|------|-------------|
| Graph structures | Need 6+ months data |
| Chart extraction | Too hard, text covers 80% |
| Regime-aware extraction | Need regime detection first |
| Follower mining | 20 accounts is enough |
| Complex ML models | Start with descriptive stats |

**The biggest risk is overcomplicating.** We have a working pipeline. The next step is to USE it, not build more infrastructure.

---

## The One-Page Summary

```
WHAT: X signal intelligence for crypto trading
HOW: Scrape → Extract → Backtest → Rank → Allocate
WHY: Find information edges before they're priced in

CURRENT STATE:
- 800 posts, 145 signals, 591 outcomes
- Timeless SHORT validated (55% win, +0.20% avg)
- GetXAPI Pro active ($40 balance)
- API server running

NEXT STEPS:
1. Backfill 2 years of data (4,320 calls)
2. Set up real-time monitoring (free with Pro)
3. Run full backtest
4. Build dashboard

BUDGET:
- Historical backfill: ~$5.40
- Ongoing monitoring: $0 (webhooks)
- Total remaining: ~$34
```

---

*This is what we're building. Poke holes in it.*
