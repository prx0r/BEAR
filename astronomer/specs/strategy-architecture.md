# Strategy Architecture — Crystallized Entities

*Binary activation, continuous graph. The edge is predicting when strategies turn on.*

---

## The Core Insight

```
                    CONTINUOUS GRAPH
                    (weighted, probabilistic)
                           │
                           ▼
                    REGIME DETECTION
                    (what conditions exist NOW?)
                           │
                           ▼
                    ACTIVATION RULES
                    (binary: ON or OFF)
                           │
                           ▼
                    STRATEGY ENTITIES
                    (crystallized, independent)
                           │
                           ▼
                    EXECUTION
```

## The Separation

| Layer | Type | What It Does |
|-------|------|--------------|
| **Graph** | Continuous, weighted | Tracks conditions, computes probabilities |
| **Activation** | Binary | Turns strategies ON/OFF based on graph state |
| **Strategies** | Crystallized entities | Independent, testable, versioned |

## Example: DeathToken Strategy

```yaml
strategy: DEATH_TOKEN
version: 1.0
status: ACTIVE

activation_rules:
  - regime: DOWNTREND or RANGE
  - death_score > 0.75
  - funding_state: NEGATIVE or NEUTRAL
  - btc_regime: not CRASH
  - not already in CRASH recovery

deactivation_rules:
  - regime: UPTREND
  - death_score < 0.50
  - funding_state: EXTREME_NEGATIVE (squeeze risk)
  - btc_regime: CRASH (wait for capitulation)

position_sizing:
  risk_per_trade: 1%
  max_positions: 5
  max_drawdown: 10%
```

## The Edge

**Not: "short dead tokens"**

But: **"the probability that the DEATH_TOKEN strategy should be active RIGHT NOW is 0.82, based on current graph state"**

That probability prediction IS the edge.

## Strategy Entity Structure

```yaml
id: DEATH_TOKEN
version: 1.0
status: ACTIVE | INACTIVE | PAUSED

# Binary activation rules
activation:
  conditions:
    - metric: btc_regime
      operator: in
      values: [DOWNTREND, RANGE]
    - metric: death_score
      operator: >
      threshold: 0.75
    - metric: funding_state
      operator: in
      values: [NEGATIVE, NEUTRAL]
  min_conditions: 3
  cooldown_hours: 24

# Deactivation rules
deactivation:
  conditions:
    - metric: btc_regime
      operator: eq
      value: UPTREND
    - metric: funding_state
      operator: eq
      value: EXTREME_NEGATIVE

# Position management
sizing:
  risk_per_trade: 0.01
  max_positions: 5
  max_drawdown: 0.10

# Backtest results
backtest:
  sharpe: 1.106
  win_rate: 0.714
  total_return: 1.029
  n_trades: 251
  period: 2024-01-01 to 2026-09-07
```

## The Graph Tracks Changing Conditions

```
CONTINUOUS GRAPH STATE:
  btc_regime: DOWNTREND (0.82)
  death_score: 0.78 (↑)
  funding_state: NEGATIVE
  alt_breadth: CONTRACTING
  meta_stage: WARM
  
  → DEATH_TOKEN activation: ON (3/3 conditions met)
  → ALTCALLS activation: OFF (regime filter blocks)
```

The graph continuously computes:

```
P(strategy should be active) = f(current conditions)
```

## The Edge

**Not "short dead tokens"**

But: **"the probability that DEATH_TOKEN should be active RIGHT NOW is 0.82, and the probability it should become inactive in 24h is 0.15"**

That probability prediction is the edge. The graph learns when conditions are likely to change, and the strategies respond.

## Multiple Strategies, Binary Activation

```
STRATEGY          ACTIVATION CONDITION           CURRENT STATE
──────────────────────────────────────────────────────────────
DEATH_TOKEN       death_score > 0.75            ON (0.82)
                  AND regime ≠ UPTREND
                  AND funding ≠ EXTREME_NEG

ALTCALLS          meta_stage = HOT              OFF (regime blocks)
                  AND breadth > 0.6

FLOW_CATCH        flow_agreement > 0.7          ON (0.91)
                  AND regime = RANGE

BREAKOUT          price > EMA200               OFF (not in range)
                  AND volume_expanding

MEAN_REVERSION    price < -2σ from mean        ON (0.68)
                  AND regime = RANGE
```

## The Prediction Layer

**The edge is not the strategies. The edge is predicting when they activate.**

```
P(DEATH_TOKEN activates in next 24h) = 0.82
P(DEATH_TOKEN deactivates in next 24h) = 0.15

P(ALTCALLS activates in next 24h) = 0.12
P(ALTCALLS deactivates in next 24h) = 0.45
```

If you can predict activation probability better than random, you can:
- Size positions appropriately
- Prepare for strategy transitions
- Avoid being caught flat-footed when regime changes

## The Complete Picture

```
                    CONTINUOUS GRAPH
                    (weights, probabilities)
                           │
                           ▼
                    REGIME STATE
                    (UPTREND | RANGE | DOWNTREND | CRASH)
                           │
                           ▼
                    ACTIVATION PROBABILITIES
                    P(strategy ON in 24h)
                           │
                    ┌──────┼──────┐
                    ▼      ▼      ▼
              DEATH   ALTCALLS  FLOW
              TOKEN
                    │      │      │
                    ▼      ▼      ▼
              EXECUTION (binary: ON/OFF)
```

## The Real Product

**Not:** "Here's a trading bot"

**But:** "BEAR predicts which strategies should be active with 82% accuracy, and adjusts position sizing based on predicted activation probability"

That's a fundamentally different product than copy-trading.
