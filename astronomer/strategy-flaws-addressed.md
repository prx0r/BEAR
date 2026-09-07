# Strategy Flaws — Addressed

*Solutions for every identified flaw in the combined AltCalls + Death strategy.*

---

## Flaw 1: 6-state machine needs 6× backtest data

**Problem:** Each state needs enough samples. 1-month pilot won't have enough CRASH/CAPITULATION events.

**Solution:** Use a hierarchical approach.

```
PHASE 1 (1 month):
  Only test 3 states: RISK_ON, DETERIORATION, BEAR
  Pool CRASH/CAPITULATION/RECOVERY as "extreme" regime
  Require minimum 20 signals per state

PHASE 2 (3 months):
  Separate CRASH from CAPITULATION
  Require minimum 30 signals per state

PHASE 3 (12 months):
  Full 6-state model
  Require minimum 50 signals per state
```

**Minimum sample thresholds:**

| State | Minimum signals | Why |
|-------|----------------|-----|
| RISK_ON | 20 | Most common, fills fast |
| DETERIORATION | 15 | Less common, needs detection |
| BEAR | 15 | Needs enough for Death to work |
| CRASH | 5 | Rare, pool with CAPITULATION initially |
| CAPITULATION | 5 | Rare, pool with CRASH initially |
| RECOVERY | 10 | Moderate frequency |

**If a state has <5 signals:** Don't include it in the model. Report it as "insufficient data" rather than making up a regime.

---

## Flaw 2: Transition detection is noisy

**Problem:** Breadth/dispersion/funding signals might trigger too often (false positives) or too late.

**Solution: Multi-signal consensus + cooldowns.**

### Don't rely on one indicator. Require 3+ of 5:

```
BREADTH_SIGNAL:
  % alts > EMA50_4h dropped >15% in 48h
  median alt return < 0 for 3 consecutive days

DISPERSION_SIGNAL:
  cross-sectional dispersion > 75th percentile
  dispersion increasing for 5+ days

FUNDING_SIGNAL:
  BTC funding positive but price declining for 3+ days
  OI increasing while price flat/down

TECHNICAL_SIGNAL:
  BTC formed lower high on 4h
  BTC failed to reclaim 50% of recent range

VOLUME_SIGNAL:
  BTC volume declining while price holds
  Alt volume declining faster than BTC
```

**Decision rule:**

```
TRANSITION_DETECTED = 
  (breadth_signal + dispersion_signal + funding_signal + 
   technical_signal + volume_signal) >= 3
```

### Cooldowns prevent whipsaw:

```
After DETERIORATION detected:
  MINIMUM_HOLD = 72 hours
  
After BEAR confirmed:
  MINIMUM_HOLD = 5 days
  
After CAPITULATION:
  MINIMUM_HOLD = 48 hours
```

### Hysteresis (already in the plan):

```
enter BEAR when score > .65
exit BEAR only when score < .45

enter DETERIORATION when score > .55
exit DETERIORATION only when score < .40
```

This means the system doesn't oscillate at boundaries.

---

## Flaw 3: Death short funding can eat you

**Problem:** Shorting a token with -200% annualized funding bleeds even if the token eventually dies.

**Solution: Funding cost budgeting + funding veto.**

### Funding cost model:

```
daily_funding_cost = |funding_rate| × position_size × 365

Example:
  funding_rate = -0.1% (daily)
  position_size = $10,000
  
  daily_cost = 0.001 × 10,000 = $10
  monthly_cost = $300
  annual_cost = $3,650
```

### Funding veto rules:

```
IF funding_rate < -0.05% (daily):
  → NEW SHORT: VETO
  → EXISTING SHORT: HOLD (but increase stop urgency)

IF funding_rate < -0.15% (daily):
  → ANY SHORT: CLOSE
  → Reason: cost exceeds expected alpha

IF funding_rate > +0.10% (daily):
  → Death short gets PAID funding
  → EXTREMELY attractive entry
```

### The asymmetry:

```
POSITIVE funding + Death signal = GREAT short
  (you get paid to short a dying token)

NEGATIVE funding + Death signal = DANGEROUS
  (you're paying to short a dying token — squeeze risk)
```

This maps directly to the P_R component:

```
High negative funding → high P_R → DON'T SHORT
High positive funding → low P_R → GOOD SHORT
```

---

## Flaw 4: Relative-value spread has basis risk

**Problem:** Long SOL + short token X works if SOL outperforms X. But if both crash together (correlated beta), the spread doesn't help.

**Solution: Beta-neutral construction.**

### Beta-neutral basket:

```
LONG basket:
  beta-weighted to match market beta
  
SHORT basket:
  beta-weighted to match market beta

net_beta = 0
```

**Example:**

```
LONG:
  SOL (beta 1.2)     $5,000
  HYPE (beta 1.5)    $3,000
  TAO (beta 1.8)     $2,000
  weighted beta:      1.38

SHORT:
  Token A (beta 0.8) -$3,000
  Token B (beta 0.6) -$2,000
  Token C (beta 1.0) -$5,000
  weighted beta:      0.84

NOT beta-neutral → long side has more market exposure
```

To make it beta-neutral:

```
scale short basket by:
  long_beta / short_beta = 1.38 / 0.84 = 1.64

short notional = $12,400 instead of $10,000
```

Now the spread expresses:

```
SOL/HYPE/TAO outperformance
vs
Token A/B/C underperformance
```

with zero net market beta.

### But crypto correlations are high

During crashes, correlations converge to 1.0. Beta-neutral doesn't help in a crash.

**That's why the BTC hedge exists separately.** The spread is for normal/transition regimes. The BTC hedge handles crash correlation.

---

## Flaw 5: CAPITULATION detection is extremely hard

**Problem:** How do you know when "OI/funding flush" has happened vs. still happening?

**Solution: Use 3 lagging + 1 leading indicator.**

### Lagging indicators (confirm capitulation happened):

```
1. FUNDING_FLUSH:
   funding_percentile drops from >90 to <20 within 7 days
   → Shorts have been forced out

2. OI_FLUSH:
   OI drops >30% from recent peak
   → Leverage has been removed

3. LIQUIDATION_SPIKE:
   24h liquidation notional > 3× 30d average
   → Forced selling has occurred
```

### Leading indicator (suggests capitulation is ending):

```
4. REVERSAL_PATTERN:
   15m candle: higher low after flush
   OR
   spot CVD turning positive
   OR
   large bid appearing at level
```

### Decision rule:

```
CAPITULATION_CONFIRMED = 
  (funding_flush + oi_flush + liquidation_spike) >= 2
  AND
  reversal_pattern = TRUE
```

**Wait for at least 2 of 3 lagging indicators + 1 leading indicator.**

This prevents covering too early (before flush completes) or too late (after bounce already happened).

---

## Flaw 6: Experiment matrix is ambitious

**Problem:** P0-P6 requires 7 parallel portfolios. 1-month pilot can't support all.

**Solution: Sequential testing with early stopping.**

```
MONTH 1:
  P0 (AltCalls alone)
  P1 (Death alone)
  → If either shows no edge, STOP

MONTH 2:
  P2 (fixed 1:1 spread)
  → If P2 beats max(P0, P1), continue

MONTH 3:
  P3 (BTC regime)
  → If P3 beats P2, continue

MONTH 4+:
  P4 (transition-aware)
  P5 (beta-targeted)
  P6 (specialists)
```

**Early stopping rule:**

```
After each month:
  IF best_strategy.sharpe < 0.3:
    → "No statistically interesting signal found"
    → STOP unless theoretical conviction is very high
  IF best_strategy.sharpe > 0.3:
    → Continue to next experiment
```

This prevents burning months on a dead strategy.

---

## Flaw 7: Position sizing per regime

**Problem:** The document says "gross exposure" but doesn't size individual positions.

**Solution: Risk parity within each sleeve.**

### AltCalls sizing:

```
per position risk = target_risk / n_positions

if target_risk = 2% of portfolio per position:
  n_positions = 5
  → each position gets 2% risk budget
  → actual notional = risk_budget / stop_distance
```

### Death sizing:

```
per position risk = target_risk / n_positions

if target_risk = 1.5% of portfolio per position:
  n_positions = 3-5
  → each position gets 1.5% risk budget
```

### Regime multipliers:

```
RISK_ON:
  alt_risk_per_position = 2.0%
  death_risk_per_position = 1.0%
  max_positions = 8

DETERIORATION:
  alt_risk_per_position = 1.5%
  death_risk_per_position = 1.5%
  max_positions = 6

BEAR:
  alt_risk_per_position = 0.5%
  death_risk_per_position = 2.0%
  max_positions = 5

CRASH:
  alt_risk_per_position = 0%
  death_risk_per_position = 1.0% (existing only)
  max_positions = 3
```

---

## Flaw 8: Correlation management

**Problem:** AltCalls might pick 5 alts that are all correlated with BTC.

**Solution: Correlation-adjusted diversification.**

### Correlation matrix:

```
compute rolling 30d correlation between all candidate alts
and BTC
```

### Selection rule:

```
FOR each AltCalls candidate:
  correlation_with_BTC = corr(alt_returns, btc_returns, 30d)
  
IF correlation_with_BTC > 0.7:
  → high beta contribution
  → acceptable in RISK_ON (you WANT beta)
  → penalty in BEAR (you DON'T want beta)

SELECT top N by AltCalls score
THEN remove if:
  → >3 positions with correlation > 0.8
  → portfolio_beta > 1.5 in DETERIORATION/BEAR
```

### Diversification constraint:

```
max correlation between any 2 positions = 0.75
max portfolio beta to BTC = 1.5 (RISK_ON), 0.5 (BEAR)
```

---

## Flaw 9: Drawdown limits

**Problem:** No mention of max drawdown per strategy or per regime.

**Solution: Layered drawdown controls.**

### Per-position stop:

```
ATR-based stop (already in strategy)
```

### Per-sleeve stop:

```
IF AltCalls sleeve drawdown > 15% from peak:
  → reduce to 50% of target allocation
  → require 2 additional confirmation signals for new entries

IF Death sleeve drawdown > 10% from peak:
  → close worst performer
  → reduce new entries by 50%

IF Death sleeve drawdown > 20% from peak:
  → close all Death positions
  → wait for regime change
```

### Portfolio-level stop:

```
IF portfolio drawdown > 25% from peak:
  → reduce ALL positions by 50%
  → go flat until regime reclassifies

IF portfolio drawdown > 35% from peak:
  → close everything
  → wait 7 days minimum
  → require 3 regime confirmations to re-enter
```

### Daily loss limit:

```
IF daily PnL < -3% of portfolio:
  → stop trading for the day
  → review positions
  → only close losing positions, no new entries
```

---

## Flaw 10: Transaction costs

**Problem:** Rebalancing between regimes has costs. Need to estimate turnover and slippage.

**Solution: Cost-aware rebalancing.**

### Turnover model:

```
regime_change_frequency = ~1-2 per month (estimated)

when regime changes:
  need to adjust:
    - close/add AltCalls positions
    - close/add Death positions
    - adjust BTC hedge

estimated turnover per regime change:
  ~30-50% of portfolio

cost per turnover:
  spread: 2-5 bps
  fee: 4.5 bps (taker)
  slippage: 3-8 bps (depending on liquidity)
  
total cost per turnover: ~10-17 bps
```

### Monthly cost estimate:

```
regime changes: 1-2
turnover per change: 40%
cost per turnover: 15 bps

monthly cost: 1.5 × 0.4 × 0.15% = 0.09% = 9 bps

annual cost: ~1.1%
```

### Cost-aware rebalancing:

```
don't rebalance everything at once

prioritize:
1. closing positions with adverse funding
2. closing positions that violate new regime constraints
3. adding positions with best risk/reward in new regime

skip:
- positions with <5% weight change
- positions with <24h holding period (too costly to churn)
```

### Break-even analysis:

```
strategy needs to generate > 1.1% annual alpha
just to cover rebalancing costs

if sharpe < 0.3 after costs → strategy is not viable
```

---

## Summary: All Flaws Addressed

| Flaw | Solution |
|------|----------|
| Insufficient data | Hierarchical 3→6 state testing, min sample thresholds |
| Noisy transitions | Multi-signal consensus (3/5), cooldowns, hysteresis |
| Funding bleed | Funding veto rules, funding cost budgeting, asymmetry |
| Basis risk | Beta-neutral construction, separate BTC hedge |
| Capitulation detection | 3 lagging + 1 leading indicators |
| Ambitious experiments | Sequential testing with early stopping |
| No position sizing | Risk parity per sleeve, regime multipliers |
| Correlation | Max correlation 0.75, portfolio beta limits |
| No drawdown limits | Per-position, per-sleeve, portfolio-level stops |
| Transaction costs | Cost-aware rebalancing, 1.1% annual cost estimate |

---

*Strategy is now robust enough to backtest. The flaws don't invalidate the approach — they define the guardrails.*
