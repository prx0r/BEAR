# Signal Graph Architecture

*How to weight accounts, track regimes, and trigger strategies.*

---

## The Core Insight

> **Don't ask "who is a good trader?" Ask "which information source is good at expressing which type of information in which market regime?"**

This requires a **weighted, regime-aware knowledge graph** — not a static list of accounts.

## The Graph Structure

```
                    ┌─────────────────┐
                    │  REGIME ENGINE  │
                    │  (meta-signal)  │
                    └────────┬────────┘
                             │
              weights edges based on regime
                             │
                             ▼
┌─────────────────────────────────────────────────────────┐
│                    SIGNAL GRAPH                         │
│                                                         │
│   ACCOUNTS ──────► PRIMITIVES ──────► ASSETS            │
│      │                 │                  │             │
│      │                 │                  │             │
│      ▼                 ▼                  ▼             │
│   WEIGHTS           WEIGHTS            WEIGHTS          │
│   (backtested)     (backtested)       (backtested)     │
│                                                         │
│   ┌─────────────────────────────────────────────┐       │
│   │           MARKET CONTEXT                    │       │
│   │  • BTC regime (trend/vol/funding)           │       │
│   │  • Alt breadth                              │       │
│   │  • Capital flow (ETH/BTC ratio, memecoin)   │       │
│   │  • Meta stage (seed/amplification/saturation)│       │
│   └─────────────────────────────────────────────┘       │
│                                                         │
└─────────────────────────────────────────────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  STRATEGY       │
                    │  TRIGGER        │
                    │  (sniper mode)  │
                    └─────────────────┘
```

## The Three Layers

### Layer 1: Static Graph (Account → Primitive → Asset)

This is what we built in `graph.json`. It tells us:
- Which accounts use which primitives
- Which accounts post about which assets
- How accounts relate to each other

### Layer 2: Dynamic Weights (Backtested)

Each edge gets a weight based on historical performance:

```
edge_weight(account, primitive, asset, regime) = 
    backtested_win_rate × backtested_avg_return × regime_multiplier
```

This is NOT static. The weight for:
```
Timeless × TRADE_INTENT × BTC × DOWNTREND
```
is different from:
```
Timeless × TRADE_INTENT × BTC × UPTREND
```

### Layer 3: Regime Engine (Meta-Signal)

The regime engine determines WHICH edges are active:

```
REGIME STATE:
  BTC_trend: UPTREND | RANGE | DOWNTREND
  BTC_vol: LOW | NORMAL | HIGH
  BTC_funding: POSITIVE | NEGATIVE
  alt_breadth: EXPANDING | CONTRACTING
  meta_stage: SEED | AMPLIFICATION | SATURATION
  
  → 
  ACTIVE_EDGES = regime × graph
  →
  STRATEGY = aggregate(active_edges)
```

## Regime Detection

### BTC Regime (deterministic, start here)

```python
def detect_regime(prices, funding, oi):
    # Trend
    if price > ema200_4h and price > ema50_1d:
        trend = "UPTREND"
    elif price < ema200_4h and price < ema50_1d:
        trend = "DOWNTREND"
    else:
        trend = "RANGE"
    
    # Volatility
    vol_percentile = get_vol_percentile(realized_vol, 90d)
    if vol_percentile > 90:
        vol = "HIGH"
    elif vol_percentile < 20:
        vol = "LOW"
    else:
        vol = "NORMAL"
    
    # Funding
    funding_state = "POSITIVE" if funding > 0 else "NEGATIVE"
    
    # Alt breadth
    pct_alts_above_ema50 = count_alts_above_ema50() / total_alts
    if pct_alts_above_ema50 > 0.7:
        breadth = "EXPANDING"
    elif pct_alts_above_ema50 < 0.3:
        breadth = "CONTRACTING"
    else:
        breadth = "NEUTRAL"
    
    return {
        "trend": trend,
        "vol": vol,
        "funding": funding_state,
        "breadth": breadth,
    }
```

### Regime → Active Primitives

```python
REGIME_RULES = {
    ("UPTREND", "NORMAL", "POSITIVE", "EXPANDING"): {
        "active_primitives": ["TRADE_INTENT", "ORDER_FLOW", "REGIME"],
        "weight_multiplier": {"TRADE_INTENT": 1.2, "ORDER_FLOW": 1.0},
    },
    ("DOWNTREND", "HIGH", "NEGATIVE", "CONTRACTING"): {
        "active_primitives": ["TRADE_INTENT", "ORDER_FLOW", "DERIVATIVES_STATE"],
        "weight_multiplier": {"TRADE_INTENT": 0.8, "ORDER_FLOW": 1.3},
    },
    ("RANGE", "NORMAL", "NEGATIVE", "NEUTRAL"): {
        "active_primitives": ["PRICE_MAP", "ORDER_FLOW", "POSITION_UPDATE"],
        "weight_multiplier": {"PRICE_MAP": 1.2, "ORDER_FLOW": 1.1},
    },
    # ... more regimes
}
```

### Meta Detection

```python
def detect_meta(tokens_data, social_data):
    # Token launch rate
    launches_7d = count_new_tokens_last_7d()
    launches_30d_avg = average_launches_30d()
    launch_rate = launches_7d / launches_30d_avg
    
    # Graduation rate
    graduations_7d = count_graduations_last_7d()
    
    # Social diffusion
    social_volume_change = (social_7d - social_30d_avg) / social_30d_avg
    
    # FOMO trader profitability
    fomo_win_rate = calculate_fomo_trader_win_rate()
    
    if launch_rate > 1.5 and graduations_7d > 0 and fomo_win_rate > 0.5:
        meta = "HOT"
    elif launch_rate < 0.5 or fomo_win_rate < 0.3:
        meta = "COLD"
    else:
        meta = "WARM"
    
    return {
        "meta_stage": meta,
        "launch_rate": launch_rate,
        "graduations": graduations_7d,
        "fomo_win_rate": fomo_win_rate,
    }
```

## The Weight Update Loop

```python
# Every day:
1. Detect regime
2. For each (account, primitive, asset):
   a. Get historical win rate in current regime
   b. Apply Bayesian shrinkage
   c. Update edge weight
3. Recompute consensus per asset
4. Generate signals where weight > threshold
```

## The Sniper Metaphor

```
REGIME ENGINE = Spotter
  "Market is in DOWNTREND, HIGH_VOL, CONTRACTING"
  
SIGNAL GRAPH = Rifle Selection
  "Use ORDER_FLOW + TRADE_INTENT from exitpumpBTC + Timeless"
  
STRATEGY TRIGGER = Pull Trigger
  "Execute SHORT on BTC when Timeless + exitpump agree"
```

The regime engine tells us WHEN to shoot. The graph tells us WHO to listen to. The strategy tells us WHAT to do.

## What This Unlocks

1. **Regime-aware signals:** Same trader, different weight in different regimes
2. **Capital flow tracking:** Meta detection tells us where money is rotating
3. **Cross-primitive confluence:** TRADE_INTENT + ORDER_FLOW alignment = strong signal
4. **Dynamic roster:** New accounts automatically weighted by backtested performance
5. **Missing primitive detection:** We know when we're blind (no CATALYST sources)

---

*Architecture version: 1.0*
