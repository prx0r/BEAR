# CT Signal Intelligence System — Full Architecture

*Expert-reputation engine where every call becomes a timestamped prediction and every trader earns or loses weight from what happened afterward.*

---

## Core Principle

The roster should be **dynamic**. Binance provides continuously refreshed discovery of genuinely profitable Futures accounts, while X provides their reasoning.

## The Four Cohorts

| Account | Role | Evidence | Status |
|---------|------|----------|--------|
| **@0xPickleCati** | Discretionary / swing | Binance Smart Money-linked; historically elite PnL | **Core** |
| **@Shangus_Capital** | Long-history discretionary | Direct Binance profile: ~$977k lifetime PnL, 2,291 active days | **Core** |
| **@BitcoinLiangGe** | Active Binance whale | Multi-million AUM copy portfolio, strong recent PnL/Sharpe | **Core** |
| **@0xMax98** | Futures | Recent Binance Top Trader by 30D profit | **Core** |
| **@Oldman__Crypto** | Active futures | Current Binance Top 30D Profit + Volume badges | **Core** |
| **@cryptobullmaker** | Alt/catalyst trader | Current Binance Top 30D Profit + Volume; explicit buy theses | **Core** |
| **@zhngq318294** | High-frequency | Current Binance Top 30D Profit + Volume; Binance labels high-frequency | **Core** |
| **@0xJe3x** | Futures / leverage | Previously mapped to Binance 90D PnL #7; active trade commentary | **Core** |
| **@huntbui89** | Futures | Binance profile linked to X + Top 30D PnL badge | **Candidate** |
| **@0xCryptoChan** | Cycle/on-chain trader | Binance Top 7D PnL badge; explicit cycle signals | **Candidate** |
| **@calvintsaikm** | Quant/stat-arb | Historically identified in Binance Smart Money top cohort | **Quant context** |
| **@ApexMirror** | Quant | Historically very high Binance Smart Money rank | Historical benchmark |
| **@PopcornKirby** | Discretionary | Historically top Binance Smart Money account | Historical benchmark |
| **@haemulcoin** | Short/catalyst | Historical Binance Smart Money; notable short-side history | Historical benchmark |
| **@MandangoCrypto** | Futures | Previously mapped to Binance 30D PnL leaderboard | Candidate |
| **@CryptoBheem** | Macro/liquidity | Extremely scoreable public calls: levels, position sizing, PnL, targets | **Core despite unverified Binance PnL** |
| **@Trader_XO** | Structure / discretionary | Frequent explicit market levels and directional theses | **Core experiment** |
| **@eliz883** | High-frequency CT | Huge historical post corpus; lots of explicit positioning/calls | **Core experiment** |
| **@lBattleRhino** | Discretionary | Your discovered candidate | **Let backtest decide** |

### Separate Context Feeds

These should never be treated like another Trader_XO vote:

| Feed | What it contributes |
|------|---------------------|
| **@Tree_of_Alpha / @TreeNewsFeed** | catalyst/news timing |
| **@ki_young_ju** | on-chain / whale regime |
| **@glassnode** | structural on-chain data |
| **@GreeksLive** | options positioning |
| **@BTC__options** | options-vol specialist commentary |
| **@coinalyzetool** | funding/OI/liquidation context |
| **Binance Smart Signal directly** | actual profitable-account positioning |

## The Signal Architecture

```
TRADER INTENT                         ACTUAL BEHAVIOUR
      X                                     Binance
      │                                        │
      ├── thesis                              ├── position
      ├── direction                           ├── entry
      ├── confidence                          ├── PnL
      ├── target                              └── flow
      └── invalidation                           │
                  \                            /
                   \                          /
                    ─── SIGNAL ENGINE ───────
```

### Evidence Weights

| Evidence | Initial weight |
|----------|---------------|
| Tweet saying "bullish TAO" | 0.25 |
| Tweet explicitly saying "long TAO @ $280" | 0.50 |
| Binance trader opens long | **1.00** |
| Binance trader materially adds | **1.25** |
| Multiple proven Binance traders add | **2.0+** |
| Proven on-chain wallet buys | **1.0** |

## Backtest Every Historical Call

### Call Storage Format

```json
{
  "author": "CryptoBheem",
  "tweet_id": "...",
  "timestamp": "2026-...",
  "asset": "BTC",
  "direction": "short",
  "entry": [88000, 90000],
  "targets": [82000, 76000],
  "stop": 91500,
  "horizon": "days",
  "call_type": "directional",
  "conditional": false,
  "author_confidence": 0.8,
  "parser_confidence": 0.97,
  "thesis_id": "..."
}
```

### Call Scoring

At timestamp (t), take the **first realistically executable price after publication** (next 1-minute open/close + 5-30 seconds latency).

Calculate across horizons: 15m, 1h, 4h, 12h, 1d, 3d, 7d, 30d.

**Normalized directional return:**

```
Z = direction × ln(P_{t+h} / P_t) / (σ_t × √h)
```

Being right by +4% on BTC isn't treated the same as +4% on a memecoin.

**Also save:**
- endpoint return
- maximum favorable excursion (MFE)
- maximum adverse excursion (MAE)
- time spent profitable
- target hit?
- stop hit?
- target-before-stop?
- BTC-relative excess return
- market-relative excess return

### Conditional Calls

> "Long BTC **if 100k is reclaimed**."

BTC crashes without reclaiming 100k.

This isn't a failed long. It's:

```
TRIGGERED = false
OUTCOME = NO TRADE
```

Untriggered conditional forecasts receive neither reward nor penalty.

### Cluster Posts into Theses

Don't score individual tweets. Cluster posts into:

```
author + asset + direction + approximate horizon + continuous position/thesis
```

until the author exits, invalidates, reverses, or thesis expires.

## The Trader Reputation Model

### Contextual Skill Tensor

```
Skill = f(trader, asset, direction, horizon, regime, callType)
```

Not one score per trader. Per-dimension scores:

```
CryptoBheem
 BTC / short / 1-7D / high-volatility = excellent
 BTC / long / 1-7D / high-volatility  = good
 alt / intraday                       = unknown

Trader_XO
 BTC / 4H                             = strong
 ETH / swing                          = strong
 small-cap longs                      = weak

PickleCati
 BTC / swing / trend                  = excellent
 BTC / chop                           = average
```

### Bayesian Shrinkage

4 wins / 4 calls should NOT outrank 421 wins / 690 calls.

For binary win rate:

```
p_i = (wins_i + α) / (n_i + α + β)
```

Hierarchical model:

```
global trader population
        ↓
individual trader
        ↓
trader × BTC
        ↓
trader × BTC × short
        ↓
trader × BTC × short × 1D
        ↓
trader × BTC × short × high-vol regime
```

Sparse bottom-level observations inherit information from levels above.

### Adaptive Weights

Online expert aggregation:

```
w_{i,t+1} ∝ w_{i,t} × exp(-η × L_{i,t})
```

**Multiple memory horizons simultaneously:**
- very recent
- recent
- medium-term
- long history

Let another online aggregator decide which memory horizon currently predicts best.

### Regime Conditioning

Regime vector:
```
BTC trend:       up / flat / down
realized vol:    low / normal / high
funding:         negative / neutral / positive
OI:              expanding / contracting
breadth:         broad / narrow
liquidity:       improving / deteriorating
```

Calculate historical skill **conditional on comparable regimes**.

## Confidence Calibration

Track three different things:

| Variable | Meaning |
|----------|---------|
| `parser_confidence` | Are we sure we understood the tweet correctly? |
| `author_conviction` | How strongly did the trader express the call? |
| `historical_reliability` | How often have comparable calls actually worked? |

Then test whether **their confidence itself is calibrated**:

```
Trader A:
"maybe long" calls       51% correct
"bullish" calls          58%
"high conviction long"   73%

Trader B:
"high conviction"        48%
```

Trader A's conviction contains information. Trader B's doesn't.

Use proper probability scoring (Brier score/log loss), not raw accuracy.

## Skin in the Game

```
tweet: "shorting ETH"
               +
Binance account opens ETH short at same time
               ↓
        VERIFIED POSITION CALL

versus:

tweet: "ETH looks weak"
no corresponding position
               ↓
        COMMENTARY ONLY
```

The first is extraordinarily strong evidence about conviction.

## Historical Data

### X Historical Backfill

TwitterAPI.io claims full historical Advanced Search back to 2006 at $0.15/1,000 tweets.

500,000 historical tweets ≈ **$75**

### Binance Historical Data

Binance publishes downloadable historical spot and USDⓈ/COIN-M futures klines, trades and aggregate trades — clean price truth set.

### Deleted Losing Calls

This is critical: someone can historically look brilliant because winning tweets survive and losing tweets get deleted.

**Backfill history now, but begin permanent live capture immediately.**

Persist every original post immutably. If it later disappears:

```
deleted = true
```

But **never remove it from your evaluation dataset**.

## Validation Against Existing Products

### CallRank Comparison

| CallRank | Ours |
|----------|------|
| one overall trader score | contextual trader skill |
| equal 25% component weights | learned out-of-sample weights |
| mainly X | X + actual Binance positioning |
| daily scrape | continuous immutable capture |
| general ranking | executable trading signal |
| fixed scoring | online adaptive reputation |
| largely independent trader scoring | correlation/copy-network adjustment |
| past performance | regime-conditioned performance |

## Avoiding Overfitting

If you try 300 traders, 12 horizons, 20 weighting schemes and 15 regime definitions and then choose whatever historical configuration has the best Sharpe, you **will** discover fake alpha.

Use:

```
TRAIN
historical calls → develop extraction/features

VALIDATION
choose weights/models

SEALED TEST
never touched during development

THEN
live paper-trading forward test
```

Record **every experiment**, including failures. Don't reset the test set.

## The Seven-Stage Architecture

1. **Discovery:** scrape Binance Top 100 across 7D/30D/90D/1Y/all-time every day; resolve their X identities; add persistent performers to the candidate universe.

2. **Capture:** continuously archive every candidate's X posts, replies, quotes and media, keyed by immutable X user ID rather than handle.

3. **Parse:** multimodal model converts text + charts + thread context into structured calls; ambiguous posts remain `NO_CALL`.

4. **Resolve:** use Binance historical minute data to determine price path, MFE, MAE, endpoints and target/stop resolution.

5. **Reputation:** maintain Bayesian/contextual skill distributions per trader × asset × direction × horizon × regime, with sample-size shrinkage and recency decay.

6. **Aggregate:** online exponential expert weighting combines only currently active/competent experts, then combines the trader ensemble with Binance positioning, derivatives and macro channels.

7. **Validate:** CPCV/PBO-style robustness tests + untouched forward paper-trading before allowing the ensemble to influence real positions.

## The Final Signal Output

```
BTC
Horizon: 1–3 days

Direction: SHORT
Probability: 68%
Confidence: MEDIUM-HIGH

Trader ensemble       -0.52
Binance Smart Money   -0.34
Derivatives           -0.19
On-chain              +0.08
Catalysts             -0.05

Agreement: 72%
Historical analogues: 417
Regime: high-volatility / downtrend

Most influential:
CryptoBheem     bearish    weight 0.91
0xPickleCati    bearish    weight 0.83
Trader_XO       neutral    weight 0.71
```

## Key Insight

Don't decide today whether @lBattleRhino is better than @CryptoBheem. Ingest both. Six months of timestamped calls should make that question empirically answerable — including *what assets, directions, horizons and regimes each person is actually good at*.

Because Binance continually surfaces new profitable accounts, the roster itself becomes an evolving **talent-discovery system**, not a static list of CT celebrities.

---

*Sources: Binance Smart Money docs, CallRank methodology, arXiv online expert aggregation, Probability of Backtest Overfitting literature*
