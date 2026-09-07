# Targeted Data Acquisition — Spec

*Buy data where our strategies are weak. Don't buy data we don't need.*

---

## The Problem

We have 4 signals that work:
- **Astronomer** — BTC directional (48% win 4h)
- **Timeless** — BTC SHORT conviction (89% win 4h)
- **XO** — Structural levels (67% win 4h, small sample)
- **CryptoBheem** — BTC directional (50% win 4h, tiny sample)

But we don't know:
- Do these work in different regimes?
- Do they work on alts?
- Which accounts are weak where?
- What data would make them better?

## The Solution: Targeted Acquisition

Instead of scraping everything, **identify weaknesses and buy data to fix them**.

```
BACKTEST EXISTING SIGNALS
        │
        ▼
IDENTIFY WEAKNESSES
        │
        ▼
TARGETED DATA ACQUISITION
        │
        ▼
IMPROVE → RE-BACKTEST
```

## Step 1: Map Weaknesses

From our 38 signals:

```
@astronomer_zero:
  Win 4h: 48% — weak
  Win 24h: 30% — terrible
  Avg 4h: +0.001% — barely positive
  Weakness: SHORT signals bad, LONG signals ok
  Missing: regime context, flow data

@Timeless_Crypto:
  Win 4h: 89% — strong
  Win 24h: 44% — mediocre
  Avg 4h: +0.001% — barely positive
  Weakness: Can't hold through 24h
  Missing: When to take profits, regime filter

@CryptoBheem:
  Win 4h: 50% — coin flip
  Win 24h: 100% — great (but n=2)
  Weakness: Too few signals
  Missing: More data needed

@Trader_XO:
  Win 4h: 67% — strong
  Weakness: Only 6 signals
  Missing: More data needed
```

## Step 2: What Data Fixes Each Weakness?

| Weakness | Fix | Data Source | Cost |
|----------|-----|-------------|------|
| Astronomer SHORT bad | Add regime filter | BTC hourly (have) | $0 |
| Astronomer SHORT bad | Add flow confirmation | @exitpumpBTC, @52kskew | $0.05 |
| Timeless can't hold 24h | Add profit-taking rules | Timeless more data | $0.02 |
| CryptoBheem too sparse | Get more historical data | CryptoBheem Jul-Sep | $0.01 |
| XO too sparse | Get more historical data | XO Jul-Sep | $0.01 |
| Alt coverage missing | Fetch alt-specific signals | @lBattleRhino, @eliz883 | $0.02 |
| Regime context missing | Fetch regime data | BTC hourly (have) | $0 |
| Flow confirmation missing | Fetch orderflow data | @exitpumpBTC | $0.01 |

**Total targeted acquisition: ~$0.07**

## Step 3: What to Fetch

### Priority 1: Fill Data Gaps
```
CryptoBheem Jul-Sep: 3 months × ~20 posts/month = 60 posts = 3 calls
XO Jul-Sep: 3 months × ~20 posts/month = 60 posts = 3 calls
Total: 6 calls = $0.006
```

### Priority 2: Add Flow Confirmation
```
exitpumpBTC Aug: 1 month = 100 posts = 5 calls
52kskew Aug: 1 month = 100 posts = 5 calls
Total: 10 calls = $0.010
```

### Priority 3: Alt Coverage
```
lBattleRhino Aug: 1 month = 100 posts = 5 calls
eliz883 Aug: 1 month = 100 posts = 5 calls
Total: 10 calls = $0.010
```

### Total: 16 calls = $0.016

## Step 4: Run Backtest With New Data

After fetching:
1. Extract signals from all accounts
2. Match to price outcomes
3. Test: does adding flow confirmation improve Astronomer?
4. Test: does adding regime filter improve Timeless?
5. Test: does CryptoBheem with more data still look good?
6. Test: do alts have signal at all?

## Step 5: Measure Improvement

```
BEFORE:
  Astronomer: 48% win 4h, +0.001% avg
  Timeless: 89% win 4h, +0.001% avg

AFTER adding flow:
  Astronomer: ??% win 4h, ??% avg
  Timeless: ??% win 4h, ??% avg

AFTER adding regime:
  Astronomer: ??% win 4h, ??% avg
  Timeless: ??% win 4h, ??% avg
```

If improvement is significant → continue
If not → the signal layer is wrong

## Budget

| Phase | Calls | Cost |
|-------|-------|------|
| Fill data gaps | 6 | $0.006 |
| Add flow confirmation | 10 | $0.010 |
| Add alt coverage | 10 | $0.010 |
| Buffer | 14 | $0.014 |
| **Total** | **40** | **$0.040** |

**Remaining: $39.60**

## The Key Insight

Don't scrape everything. **Scrape what fixes our weaknesses.**

- Astronomer SHORT is bad → add flow data
- Timeless can't hold 24h → add profit-taking rules
- CryptoBheem too sparse → get more data
- No alt coverage → fetch alt accounts

Each acquisition has a clear hypothesis:
> "Adding X data will improve Y metric by Z%"

That's targeted, testable, and cheap.
