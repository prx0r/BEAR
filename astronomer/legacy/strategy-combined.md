# BEAR Adaptive Alpha — Regime-Long/Short Strategy

*The combined strategy: own the strongest alts when risk appetite is expanding; progressively replace with structurally weak shorts as conditions deteriorate; preserve profitable shorts through the break; cover as capitulation/squeeze risk rises.*

---

## Architecture

```
┌─────────────────────────────────────────────┐
│            PORTFOLIO CONTROLLER             │
│         (regime-adaptive allocation)        │
└──────────────────┬──────────────────────────┘
                   │
       ┌───────────┼───────────┐
       ▼           ▼           ▼
  ALTCALLS       DEATH       MACRO HEDGE
  long alpha    short alpha   BTC/ETH beta
       │           │           │
       └───────────┼───────────┘
                   ▼
            FINAL PORTFOLIO
```

## The Three Alpha Sources

| Source | What it does | Input |
|--------|--------------|-------|
| **AltCalls** | Find unusually strong longs | X trader signals |
| **Death** | Find unusually weak shorts | X data + on-chain + fundamentals |
| **Macro** | Control portfolio beta | BTC regime + transition detection |

**Key insight:** Alpha models don't need to know about each other. The regime engine allocates between them.

---

## The 6-State Regime Machine

```
                  ┌─────────────┐
                  │   RISK ON   │
                  │ AltCalls+++ │
                  └──────┬──────┘
                         │
                  breadth weakening
                  dispersion rising
                         │
                         ▼
                ┌────────────────┐
                │ DETERIORATION  │
                │ AltCalls ↓     │
                │ Death ↑        │
                │ Hedge ↑        │
                └───────┬────────┘
                        │
                  trend confirms
                        ▼
                ┌────────────────┐
                │      BEAR      │
                │ Death ++++     │
                └───────┬────────┘
                        │
                 disorderly break
                        ▼
                ┌────────────────┐
                │     CRASH      │
                │ no new risk    │
                │ trail shorts   │
                └───────┬────────┘
                        │
                 OI/funding flush
                        ▼
                ┌────────────────┐
                │ CAPITULATION   │
                │ cover Death    │
                │ mostly cash    │
                └───────┬────────┘
                        │
                  breadth recovers
                        ▼
                ┌────────────────┐
                │    RECOVERY    │
                │ AltCalls ↑     │
                └───────┬────────┘
                        │
                        ▼
                     RISK ON
```

## Portfolio Allocation by Regime

| Regime | AltCalls | Death | BTC Hedge | Cash |
|--------|----------|-------|-----------|------|
| **RISK ON** | ++++++ | + | - | + |
| **DETERIORATION** | ++++ | --- | -- | ++ |
| **BEAR** | + | ------ | — | ++ |
| **CRASH** | 0 (no new) | trail existing | 0 | +++ |
| **CAPITULATION** | 0 | cover | 0 | ++++ |
| **RECOVERY** | +++ | -- | — | ++ |

## Key Improvements Over Simple Bull/Bear

### 1. DETERIORATION regime (the missing piece)

Not just "bull or bear" — identify the transition BEFORE everyone recognizes it:

```
BTC: still above EMA200
but:
  % alts above EMA50: 78% → 34%
  dispersion rising
  funding still positive but price weakening
  OI increasing while price flat

= DETERIORATION
```

### 2. Continuous allocation (not hard switches)

Instead of `if score > 0.5: SHORT EVERYTHING`:

```
P(RISK_ON)          .20
P(DETERIORATION)    .58
P(BEAR)             .17
P(CRASH)            .05

→ AltCalls +45%, Death -35%, Hedge -10%, net ~0%
```

Add hysteresis to prevent whipsaw:
```
enter BEAR when score > .65
exit BEAR only when score < .45
```

### 3. Volatility scaling

```
target_gross ∝ target_vol / realized_vol

normal:   gross 150%
high vol: gross 80%
crash:    gross 30%
```

### 4. Death shorts survive crashes

Don't close existing Death shorts when CRASH is detected — they're the insurance. Only stop NEW entries.

### 5. Relative-value experiment

Test:
```
LONG strong AltCall
SHORT terminal Death token
```

This expresses "strong coin outperforms broken coin" rather than "crypto must fall."

---

## Transition Detection Features

### BTC trend
```
price / EMA20 1h
price / EMA50 1h
price / EMA20 4h
price / EMA50 4h
price / EMA200 4h
EMA slopes
distance from 24h/7d high
lower-high flag
lower-low flag
```

### Alt breadth (more important than BTC)
```
% HL alts > EMA20 1h
% HL alts > EMA50 4h
% HL alts > EMA200 4h
median alt 4h return
median alt residual return vs BTC
new highs
new lows
```

### Cross-sectional dispersion
```
DISPERSION ↑↑ = momentum strategy should shrink
```

### Derivatives
```
funding positive + price weakening + OI high = trapped longs
negative extreme funding + huge shorts = DON'T SHORT (squeeze danger)
```

---

## The Regime Features

### BTC Regime
```
price > EMA200_4h AND price > EMA50_1d → UPTREND
price < EMA200_4h AND price < EMA50_1d → DOWNTREND
ATR percentile > 90 → CRASH (if downtrend) or HIGH_VOL
otherwise → RANGE
```

### Transition Probability
```
P(BULL → BEAR next 24h) = f(
    breadth_change,
    dispersion_change,
    funding_weakness,
    OI_divergence,
    lower_high_count
)
```

---

## Experiment Matrix

| Portfolio | Long | Short | Regime |
|-----------|------|-------|--------|
| P0 | AltCalls | — | — |
| P1 | — | Death | — |
| P2 | AltCalls | Death | fixed 1:1 |
| P3 | AltCalls | Death | BTC regime |
| P4 | AltCalls | Death | transition-aware |
| P5 | AltCalls | Death + BTC | beta-targeted |
| P6 | AltCalls specialists | Death specialists | full model |

### Metrics to Report

```
CAGR, Sharpe, Deflated Sharpe, Sortino
max DD, worst day, worst week
bull-market return, bear-market return, crash return, recovery return
long contribution, Death contribution, hedge contribution
gross exposure, net exposure, BTC beta
funding, fees, turnover
crash capture, upside capture
```

### The Killer Test

```
UP CAPTURE = strategy return / BTC return during positive BTC periods
DOWN CAPTURE = strategy return during negative BTC periods

Target: strong UP CAPTURE + very low/negative DOWN CAPTURE
```

---

## The Thesis

> Don't try to predict crypto direction with one model. Continuously rank the market's strongest opportunities and weakest opportunities independently, then use a separate regime engine to determine the portfolio's net market exposure.

**When everything is healthy:** own the geniuses' best longs.

**When internals begin cracking:** reduce longs, introduce terminal shorts.

**When the turn happens fast:** Death sleeve absorbs part of the hit.

**When bear trend established:** Death becomes primary alpha engine.

**When panic arrives:** stop chasing fresh shorts, let existing winners pay, progressively cash out as resurrection risk explodes.

**When market recovers:** AltCalls engine takes over again.

---

## Core Edge

**Cross-sectional selection + adaptive beta**, with the transition itself being a major research target.

$$
R = R_{AltCalls} + R_{Death} + R_{Macro}
$$

Three independent alpha sources. Clean statistics. Clean attribution.

---

*Sources: Wiley (common risk factors), ScienceDirect (cross-sectional interactions), SSRN (dispersion), Springer (momentum volatility management)*
