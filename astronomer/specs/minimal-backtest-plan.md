# Minimal Backtest Plan — What We Need

*Figure this out before spending 100K API calls.*

---

## What We Already Have

| Data | Status | Coverage |
|------|--------|----------|
| BTC hourly OHLCV | ✅ | 2024-01-01 to now (23,520 candles) |
| ETH hourly OHLCV | ✅ | 2024-01-01 to now |
| SOL hourly OHLCV | ✅ | 2024-01-01 to now |
| TAO hourly OHLCV | ✅ | 2024-01-01 to now |
| X tweets (sample) | ✅ | 154 signals from 12 accounts (Aug 2026 only) |
| X recon data | ✅ | 64 accounts profiled |
| Backtest engine | ✅ | 523-line walk-forward engine |
| Death score model | ✅ | 5 signals, backtested |

## What We Need (Minimal)

### For X Signal Backtest

```
MINIMAL DATA:
- 1 month × 5 accounts × 30 posts/day = 4,500 posts
- ~225 API calls (at 20 posts/call)
- Cost: $0.225

WHAT TO EXTRACT PER POST:
- timestamp
- author
- direction (LONG/SHORT/NEUTRAL)
- assets (BTC, ETH, SOL)
- levels (entry, target, stop)
- conviction (high/medium/low)
- event_kind (PREDICTION, OBSERVATION, etc.)

WHAT TO MATCH TO:
- Price at signal_time + 1h (entry)
- Price at signal_time + 4h, 24h, 7d (outcomes)
- MFE, MAE at each horizon
```

### For Death Token Backtest

```
MINIMAL DATA:
- 20 tokens × 6 months × daily OHLCV
- Volume data for death signals
- Funding rates (if available)
- Already have: BTC/ETH/SOL/TAO hourly

WHAT TO COMPUTE:
- death_score per token per day
- forward returns at 7/30/90d
- walk-forward evaluation
```

### For Meta/Regime Detection

```
MINIMAL DATA:
- BTC regime (already have hourly OHLCV)
- Alt breadth (% alts > EMA)
- Funding rates (need Hyperliquid API)
- Volume profile

WHAT TO COMPUTE:
- Regime classification (UPTREND/RANGE/DOWNTREND)
- Meta stage (SEED/ACCELERATION/SATURATION)
- Attention metrics (if available)
```

## The Minimal Experiment

### Step 1: X Signals → Price Outcomes (1 month)

```python
# For each signal:
# - Get price at signal_time + 1h
# - Get price at signal_time + 4h, 24h, 7d
# - Compute returns
# - Compute MFE, MAE

# For each author × asset × direction:
# - Win rate
# - Avg return
# - Sharpe
```

**Data needed:** 225 API calls + 4 hourly price files (already have)
**Cost:** $0.225

### Step 2: Death Score Validation (already done)

We already have death_score backtested:
- Sharpe: 1.106
- Win rate: 71.4%
- Total return: 102.9%

**This is DONE.** We just need to add regime conditioning.

### Step 3: Regime Detection (minimal)

```python
# From BTC hourly OHLCV (already have):
# - EMA20, EMA50, EMA200
# - ATR percentile
# - Volume trend

# Regime:
# - UPTREND: price > EMA200_4h
# - DOWNTREND: price < EMA200_4h
# - RANGE: between
# - HIGH_VOL: ATR > 90th percentile
```

**Data needed:** Already have (BTC hourly)
**Cost:** $0

## What NOT to Do Yet

- ❌ Don't fetch 100K tweets
- ❌ Don't build complex ML models
- ❌ Don't implement full MiningSpec
- ❌ Don't build regime engine from scratch
- ❌ Don't add more accounts

## What TO Do

1. **Fix the pagination bug** in pipeline.py
2. **Run 1-month X backtest** on 5 accounts (225 calls, $0.225)
3. **Test if X signals predict returns** (simple win rate)
4. **Test regime conditioning** (does death score work better in DOWNTREND?)
5. **Only then** expand to more data

## The Minimal Backtest Pipeline

```python
# Step 1: Fetch 1 month × 5 accounts
for account in [astronomer, Timeless, XO, exitpump, 0xaporia]:
    tweets = fetch(account, since="2026-08-01", until="2026-08-31")

# Step 2: Extract signals
signals = extract(tweets)  # direction, assets, levels, event_kind

# Step 3: Match to outcomes
for signal in signals:
    entry_price = get_price(signal.timestamp + 1h)
    for horizon in [4h, 24h, 7d]:
        outcome = get_price(signal.timestamp + horizon)
        signal[f'return_{horizon}'] = (outcome - entry_price) / entry_price

# Step 4: Score by author
for author in authors:
    author_signals = [s for s in signals if s.author == author]
    win_rate = sum(1 for s in author_signals if s.return_4h > 0) / len(author_signals)
    avg_return = np.mean([s['return_4h'] for s in author_signals])
    print(f"@{author}: {win_rate:.0%} win, {avg_return:+.2f}% avg")
```

## Key Question to Answer

> **Do X signals contain forward return information?**

If yes → expand to full corpus
If no → the whole X intelligence layer is wrong

## Budget for This Experiment

| Item | Calls | Cost |
|------|-------|------|
| 5 accounts × 1 month | 75 | $0.075 |
| Buffer | 25 | $0.025 |
| **Total** | **100** | **$0.10** |

**Remaining after: $39.57**

This is the minimum viable experiment. Do this first, then decide whether to scale.
