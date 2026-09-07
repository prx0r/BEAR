# Backtest Methodology — How We Score Signals

*What we're actually doing, what's wrong, and how to fix it.*

---

## What We're Currently Doing (And Why It's Flawed)

### The Current Pipeline

```
X POST → regex "long/short" → assume trade call → match to price → win rate
```

### Problems

| Problem | Impact | Fix |
|---------|--------|-----|
| Regex catches "long volatility" as LONG | False positives | Semantic extraction |
| Regex catches "not one long taken" as LONG | False positives | Negation detection |
| No entry/target/stop extraction | Can't test exact levels | Level extraction |
| 1h latency assumed | May not be realistic | Test multiple latencies |
| No execution costs | Overstates returns | Add fees/slippage |
| PREDICTION vs OBSERVATION mixed | Treating observations as signals | Event classification |

### The Core Issue

**This is a data classification problem, not a backtest problem.**

We need to classify EACH post into:

```
PREDICTION     "BTC long here" — actionable trade
OBSERVATION    "whale just bought $15M HYPE" — market data
INTERPRETATION "OI looks like chasing longs" — analysis
RETROSPECTIVE  "I told you so" — past tense
PROMOTION      "my course is launching" — not signal
```

Only PREDICTION posts should be backtested as trade calls.

---

## The Correct Backtest Methodology

### Step 1: Classify Every Post

```
POST
  │
  ├── event_kind (MANDATORY)
  │   ├── PREDICTION
  │   ├── OBSERVATION
  │   ├── INTERPRETATION
  │   ├── RETROSPECTIVE
  │   └── PROMOTION
  │
  ├── If PREDICTION:
  │   ├── direction (LONG/SHORT)
  │   ├── assets (BTC, ETH, SOL)
  │   ├── entry_type (MARKET, ZONE, LEVEL)
  │   ├── entry_price / entry_low / entry_high
  │   ├── trigger_price (if conditional)
  │   ├── stop_price
  │   ├── target_prices[]
  │   ├── horizon_text ("1h", "this week")
  │   ├── conviction (high/medium/low)
  │   └── is_conditional (if/when statement)
  │
  └── If OBSERVATION/INTERPRETATION:
      ├── data_type (FLOW, WHALE, FUNDING, etc.)
      ├── values (numerical data)
      └── interpretation (what it means)
```

### Step 2: Only Backtest PREDICTION Posts

```python
predictions = [p for p in posts if p['event_kind'] == 'PREDICTION']
```

### Step 3: Extract Exact Trade Parameters

```python
for prediction in predictions:
    entry = prediction['entry_price']  # or market price at signal + latency
    stop = prediction['stop_price']    # if specified
    targets = prediction['target_prices']  # if specified
    horizon = prediction['horizon_seconds']
    
    # Calculate outcomes
    for h in horizons:
        future_price = get_price(symbol, prediction['timestamp'] + h)
        return = (future_price - entry) / entry * direction_mult
```

### Step 4: Account for Realistic Execution

```python
# Latency
entry_price = get_price(symbol, signal_time + latency_seconds)

# Fees
net_return = gross_return - fee_rate  # ~0.045% taker

# Slippage
net_return = net_return - slippage_bps / 10000

# Funding (for perps)
net_return = net_return - funding_cost
```

### Step 5: Only Then Score

```python
for author in authors:
    author_predictions = [p for p in predictions if p.author == author]
    win_rate = sum(1 for p in author_predictions if p.net_return > 0) / len(author_predictions)
    avg_return = mean([p.net_return for p in author_predictions])
```

---

## What Makes This Hard

### 1. Semantic Extraction

The hardest part is distinguishing:

```
"long volatility"        → NOT a BTC long signal
"not one long taken"     → NOT a long signal (negation)
"I'm short"              → IS a short signal
"shorting support"       → IS a short signal (but risky)
"BTC looks bullish"      → IS a directional view
"market looks bullish"  → NOT a specific BTC call
```

This requires:
- Negation detection
- Context understanding
- Asset resolution
- Confidence estimation

### 2. Thread Context

```
13:00: "BTC long here"
13:20: "stop 110.8"
14:00: "taking half off"
15:00: "invalidated"
```

We can't just extract the 13:00 post. We need the full thread to know:
- Entry was at 13:00
- Stop was at 110.8
- Half was closed at 14:00
- Full close at 15:00

### 3. Conditional Calls

```
"If BTC reclaims 80k, I'm long"
```

This is NOT a trade call yet. It's a conditional. We need to:
1. Detect the condition
2. Wait for the condition to trigger
3. Only then evaluate the trade

### 4. Retrospective Posts

```
"Told you guys BTC was going up"
```

This has ZERO predictive value. It's posted AFTER the move. We must filter these out.

### 5. Execution Realism

Even if the signal is perfect:
- Can we actually enter at the exact price?
- What's the spread?
- What's the slippage?
- What's the funding cost?

A 0.05% edge with 0.045% taker fees = basically nothing.

---

## What We Need To Build

### 1. Post Classifier (LLM or Rules)

```
Input: raw tweet text
Output: event_kind, direction, assets, levels, etc.
```

### 2. Thread Resolver

```
Input: tweet_id
Output: full thread with all posts in order
```

### 3. Level Extractor

```
Input: tweet text + chart (if any)
Output: entry, stop, targets, horizon
```

### 4. Conditional Detector

```
Input: tweet text
Output: is_conditional, condition_text, trigger_price
```

### 5. Retrospective Filter

```
Input: tweet text + market context
Output: is_retrospective (bool)
```

### 6. Execution Cost Model

```
Input: signal + market state
Output: net_return after fees/slippage/funding
```

---

## The Minimal Valid Backtest

Before claiming any signal works, we need:

```
1. Classify 100+ posts into event_kind
2. Extract exact trade parameters from PREDICTION posts
3. Match to price outcomes with realistic latency
4. Account for execution costs
5. Only THEN compute win rates
```

**Currently we're at step 0 (regex keyword matching).**
**We need to get to step 5 before trusting any results.**

---

## What The Data Shows Right Now

Our 68 "signals" from August include:
- 0 posts with extracted levels
- 0 posts with targets
- 0 posts with stops
- Many posts that are observations, not predictions

The 86% win rate for 0xaporia is likely inflated because:
- We're counting observations as signals
- We're not accounting for execution costs
- We're using 1h latency (may not be realistic)

**The real win rate after proper classification and execution costs might be 50-60%.**

---

## Bottom Line

**We cannot claim "X is higher signal than Y" until we:**

1. Classify posts correctly (PREDICTION vs OBSERVATION)
2. Extract exact trade parameters
3. Account for execution costs
4. Test with realistic latency

Until then, our backtest numbers are **directional hints**, not validated edges.

The data classification problem is the real bottleneck. Not the API, not the graph, not the regime engine.
