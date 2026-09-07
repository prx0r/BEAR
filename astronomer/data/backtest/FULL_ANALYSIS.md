# BEAR — Complete Source Analysis (2026-09-07)

**36 accounts | 3,736 tweets | 21 source cards**

**Budget: $39.38 remaining | 750 API calls used ($0.77)**

## Backtestable: 13 accounts (66 total outcomes)
## Not backtestable: 8 accounts (VIEW/OBSERVATION only)

## Backtestable Accounts — Ranked by 4h Mean Return

| Account | Category | N | 4h Win | 4h Mean | 24h Win | 24h Mean | Sharpe |
|---------|----------|---|--------|---------|---------|----------|--------|
| @EmberCN | onchain | 2 | 100% | +3.35% | 50% | +6.06% | 16.1 |
| @DeItaone | news | 3 | 100% | +0.61% | 100% | +0.36% | 17.8 |
| @OnchainLens | onchain | 31 | 68% | +0.40% | 55% | +0.25% | 9.0 |
| @lookonchain | onchain | 5 | 60% | +0.37% | 100% | +1.72% | 10.0 |
| @kingfisher_btc | derivative | 11 | 36% | +0.10% | 73% | +0.39% | 2.2 |
| @exitpumpBTC | derivative | 2 | 50% | +0.00% | 0% | -1.43% | 0.1 |
| @PeckShieldAlert | security | 1 | 0% | -0.11% | 0% | -2.45% | 0.0 |
| @laevitas1 | derivative | 5 | 20% | -0.16% | 60% | +1.10% | -9.5 |
| @SubnetStats | tao | 1 | 0% | -0.44% | 0% | -2.51% | 0.0 |
| @ki_young_ju | onchain | 2 | 50% | -0.61% | 50% | -1.06% | -5.7 |
| @TAOTemplar | tao | 1 | 0% | -0.79% | 0% | -2.01% | 0.0 |
| @hyblockcapital | derivative | 1 | 0% | -0.98% | 0% | -0.66% | 0.0 |
| @Tokenomist_ai | fundamental | 1 | 0% | -3.36% | 0% | -2.56% | 0.0 |

## Key Findings

### 1. Horizon Follows Economic Mechanism
- laevitas1: 20% win at 4h, 60% win at 24h — derivatives need longer
- kingfisher_btc: 36% win at 4h, 73% win at 24h — same pattern
- Timeless: 62% at both — tactical directional trades at any horizon

### 2. OnchainLens Has Largest Sample
- n=31, 68% 4h win, +0.40% mean — statistically meaningful
- Only account with n>30 in the backtest

### 3. Breaking News Has Momentum
- DeItaone: 100% win at 4h (n=3) — breaking news creates short-term momentum
- But n=3 is too small to conclude

### 4. Most Accounts Are NOT Directional Traders
- 17 accounts produce VIEW/OBSERVATION, not calls
- They need event study evaluation, not directional backtest
- FarsideUK: 80 ETF flow reports (needs event study)
- Zachxbt: 86 security investigations (needs event study)

### 5. Meme Traders Need Chain Index
- theunipcs: 344 tweets, 44 meme events, 25 unique tokens
- No price data on GeckoTerminal for August
- Pump.fun Carbon is the solution (cloned, decoders compiled)

## Not Backtestable Accounts

| Account | Category | Tweets | Events | Why |
|---------|----------|--------|--------|-----|
| @FirstSquawk | news | 400 | 400 | Mostly VIEW |
| @zachxbt | security | 86 | 86 | Mostly VIEW |
| @HyperliquidR | hl | 81 | 81 | Mostly VIEW |
| @FarsideUK | flow | 80 | 80 | Mostly VIEW |
| @EleanorTerrett | news | 64 | 64 | Mostly VIEW |
| @josephwang | macro | 61 | 61 | Mostly VIEW |
| @crossbordercap | macro | 19 | 19 | Mostly VIEW |
| @CertiKAlert | security | 18 | 18 | Mostly VIEW |

---
*Report generated: 2026-09-07*