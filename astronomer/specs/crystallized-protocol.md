# Crystallized Strategy Protocol

*Binary activation, continuous graph. The edge is predicting when strategies turn on.*

---

## The Workflow

```
1. DISCOVER signal source (X account, onchain, etc.)
2. SAMPLE posts (3-5 tweets, validate signal density)
3. EXTRACT structured data (direction, assets, levels, event_kind)
4. BACKTEST against price outcomes (win rate, avg return)
5. CRYSTALLIZE into strategy entity (if edge exists)
6. DEFINE activation rules (binary conditions)
7. MONITOR graph (continuous weights)
8. ACTIVATE strategy (when conditions met)
9. TRACK PnL (per strategy, per regime)
10. ADJUST weights (based on performance)
```

## Step 1: Discover Signal Source

```
INPUT: X handle or onchain address

SCOUT (3 API calls):
  - Fetch 3 pages of tweets
  - Classify: replies, standalone, media
  - Measure: signal_density = (directional + levels) / standalone
  - Check: language, engagement pattern, post frequency

DECIDE:
  signal_density > 0.3  → PROCEED to extract
  signal_density 0.1-0.3 → PROCEED with caution
  signal_density < 0.1  → SKIP
```

## Step 2: Sample & Validate

```
FETCH 1 month of data (5-10 API calls)

EXTRACT per post:
  - direction (LONG/SHORT/NEUTRAL)
  - assets (BTC, ETH, SOL...)
  - levels (entry, target, stop)
  - event_kind (PREDICTION, OBSERVATION, etc.)
  - conviction (high/medium/low)

MATCH to price outcomes:
  - entry_price = price at signal + 1h
  - return_4h, return_24h, return_7d
  - MFE, MAE at each horizon

SCORE by author:
  - win_rate_4h
  - avg_return_4h
  - n_signals (sample size)
```

## Step 3: Crystallize Strategy

If backtest shows edge:

```
CRYSTALLIZE:
  strategy_id: {author}_{direction}_{asset}
  version: 1.0
  status: ACTIVE

  backtest:
    sharpe: X
    win_rate: X
    avg_return: X
    n_trades: X
    period: {start} to {end}

  activation_rules:
    conditions:
      - metric: btc_regime
        operator: in
        values: [DOWNTREND, RANGE]
      - metric: {author}_signal
        operator: >
        threshold: 0.5
    min_conditions: 2

  deactivation_rules:
    conditions:
      - metric: btc_regime
        operator: eq
        value: UPTREND

  sizing:
    risk_per_trade: 0.01
    max_positions: 5
```

## Step 4: Monitor & Activate

```
CONTINUOUSLY:
  1. Update graph state (regime, flow, etc.)
  2. For each strategy:
     - Check activation conditions
     - If all conditions met → ACTIVATE
     - If any deactivation condition met → DEACTIVATE
  3. Track PnL per strategy
  4. Weekly: adjust weights based on performance
```

## Step 5: The Edge

**Not:** "short dead tokens"
**But:** "probability DEATH_TOKEN should be active RIGHT NOW = 0.82"

The graph predicts:
- P(strategy activates in 24h)
- P(strategy deactivates in 24h)

That probability prediction IS the edge.

---

## Current Strategies (Crystallized)

| Strategy | Activation | Deactivation | Status |
|----------|------------|--------------|--------|
| DEATH_TOKEN | death_score > 0.75 AND regime ≠ UPTREND | regime = UPTREND | ✅ ACTIVE |
| ALTCALLS | meta_stage = HOT AND breadth > 0.6 | meta_stage = COLD | ⏸️ WAITING |
| FLOW_CATCH | flow_agreement > 0.7 AND regime = RANGE | regime ≠ RANGE | ✅ ACTIVE |
| BREAKOUT | price > EMA200 AND volume expanding | price < EMA200 | ⏸️ WAITING |
| MEAN_REVERSION | price < -2σ AND regime = RANGE | price > mean | ✅ ACTIVE |

---

## Budget: Backtest First, Then Scale

```
MINIMAL BACKTEST:
  3 training accounts × 1 month = 20 calls = $0.02
  (already done: Timeless 89% win, Astronomer 48%, Bheem 50%)

TARGETED ACQUISITION:
  Fill gaps + add flow + add alts = 16 calls = $0.016
  (identified weaknesses, acquire what fixes them)

FULL HISTORICAL:
  Only after backtest shows edge
  27 accounts × 12 months = ~500 calls = $0.50

TOTAL BUDGET NEEDED: ~$0.55
REMAINING: $39.60
```

---

*Protocol version: 3.0 — Crystallized strategy architecture*
