# Backtest Results — August 2026 (Preliminary)

*Extracted with regex-based extractor_v2. Sample sizes too small for conclusions.*

---

## What We Ran

- 383 raw posts from 10 accounts (August 2026)
- 47 CALL events extracted by regex
- 30 CALL events with asset identified (17 skipped — asset unknown)
- 28 outcomes generated (2 skipped — no timestamp or price data)
- BTC hourly data for regime context

## Overall (n=28)

| Metric | Value |
|--------|-------|
| Win rate | 57.1% (Bayesian: 56.2%) |
| Wilson CI | [39.1%, 73.5%] |
| Mean 4h return | 0.331% |
| Median 4h return | 0.192% |
| Sharpe | 7.71 |
| Sortino | 26.99 |
| Profit factor | 3.48 |
| EV per trade | 0.331% |

## Baseline Comparison (4h, same 28 timestamps)

| Baseline | Win% | Mean 4h | Sharpe |
|----------|------|---------|--------|
| Always long BTC | 64.3% | 0.090% | 2.12 |
| Always short BTC | 35.7% | -0.090% | -2.12 |
| Random direction | 57.1% | 0.140% | 3.30 |
| Momentum 24h | 35.7% | 0.013% | 0.31 |
| **Our signals** | **57.1%** | **0.331%** | **7.71** |

## Per-Author (4h returns)

| Author | N | Win% | Mean | Sharpe | PF |
|--------|---|------|------|--------|----|
| @Timeless_Crypto | 8 | 62% | 0.240% | 14.31 | 11.4 |
| @astronomer_zero | 8 | 50% | 0.596% | 8.21 | 3.3 |
| @lookonchain | 5 | 60% | 0.373% | 9.98 | 3.7 |
| @CryptoBheem | 2 | 50% | 0.271% | 8.93 | 4.9 |
| @exitpumpBTC | 2 | 50% | 0.001% | 0.05 | 1.0 |
| @laevitas1 | 2 | 50% | 0.053% | 2.36 | 1.4 |
| @koolkrypto223 | 1 | 100% | 0.064% | - | inf |

## Per-Author (24h returns)

| Author | N | Win% | Mean | Sharpe | PF |
|--------|---|------|------|--------|----|
| @lookonchain | 5 | 100% | 1.721% | 44.75 | inf |
| @laevitas1 | 2 | 100% | 3.643% | 44.99 | inf |
| @Timeless_Crypto | 8 | 62% | 0.131% | 1.61 | 1.3 |
| @astronomer_zero | 8 | 50% | -0.531% | -6.67 | 0.4 |
| @CryptoBheem | 2 | 50% | 0.220% | 4.14 | 1.9 |
| @exitpumpBTC | 2 | 0% | -1.426% | -32.97 | 0.0 |

## Honest Assessment

**What looks interesting:**
- Mean return 0.331% per trade vs 0.090% baseline (3.7x better)
- Lookonchain 100% win at 24h (but n=5)
- Laevitas 100% win at 24h (but n=2)

**Why you should NOT trust these numbers:**

1. **n=28 total.** The Wilson CI is [39.1%, 73.5%]. True win rate could be 50%. We cannot distinguish signal from noise.

2. **n=1-8 per author.** Every per-author number is meaningless at this sample size. A coin flip produces 100% on 1/1 tosses.

3. **August 2026 was bullish BTC.** Always-long baseline got 64.3% win rate. Some of our "edge" is just being long in an up market.

4. **17/47 CALL events had no asset detected.** The regex extractor misses assets in 36% of calls. This is selection bias — we're only testing posts where the asset was explicitly mentioned.

5. **279/383 posts had no asset at all.** These are posts where the author discusses markets but doesn't name a specific asset. We can't evaluate them.

6. **Sharpe ratios of 7-14 are artifacts of small samples.** With 28 data points, a few winning trades in a row produces absurd Sharpe. This is the multiple-testing problem the protocol warns about.

## What We Actually Learned

1. **The regex extractor works for ~64% of CALL events** (30/47). The rest mention markets but not specific assets.
2. **The backtest pipeline works end-to-end** — extract → match → outcomes → metrics.
3. **We need a real extractor** (LLM-based or better regex) to handle the 36% of calls with unresolved assets.
4. **We need n>30 per author per regime** before any conclusion is valid.
5. **Always-long is a strong baseline in August** — any edge must be measured against it.

## Next Steps

1. Build gold set (250 posts, manually labeled) for extractor QA
2. Fix extractor precision (currently unknown — need gold set)
3. Fetch more data (September posts, or earlier months)
4. Only then: claim any source has edge

---

*Results generated: 2026-09-07*
*Extractor: regex-based v2 (no LLM)*
*Backtest: canonical engine (next-candle entry, no BTC default)*
