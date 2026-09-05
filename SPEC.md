# HYPERLIQUID RELATIVE-VALUE / STRUCTURAL SHORT ENGINE

## 0. Mission

Build a research-first Hyperliquid trading engine whose primary question is:

> Given a portfolio of assets I deliberately want to own, identify the best Hyperliquid perpetuals to short against them so that market/sector/downside beta is removed while exposure to the long assets' idiosyncratic upside is retained.

Initial examples:

```text
LONG TAO
→ find TAO-like assets with worse economics
→ rank them
→ construct optimal short basket

LONG UNI
→ find DeFi/alt-beta assets behaving similarly
→ prefer structurally worse ones
→ calculate hedge ratio

LONG:
60% TAO
40% UNI

→ generate one joint hedge basket
→ minimize unwanted common-factor exposure
→ maximize structural-short quality
→ account for funding + execution + squeeze risk
```

This is NOT initially an autonomous trading bot.

Build, in order:

1. data acquisition
2. research database
3. feature engine
4. pair discovery
5. short-quality engine
6. portfolio optimizer
7. backtester
8. live dashboard/CLI
9. paper execution
10. optional real execution only after the research stack is validated

Do not couple research logic to execution logic.

---

# 1. Core conceptual model

For every long asset, distinguish:

```text
TOTAL RETURN
=
crypto market beta
+ altcoin beta
+ sector/narrative beta
+ asset-specific alpha
```

The goal is NOT:

```text
long TAO
short BTC
```

because that only roughly removes market beta.

The ideal trade is:

```text
LONG economically strong asset
SHORT economically weak asset/basket

where:

market exposure ≈ matched
sector exposure ≈ matched
downside behavior ≈ matched
volatility ≈ matched

BUT

token economics are strongly divergent
```

Think:

> "Find me the closest bad clone of what I want to own."

Create this as a first-class concept called:

```text
CLONE_GAP
```

High `CLONE_GAP` means:

* statistically similar exposure
* substantially worse economics
* acceptable funding
* acceptable liquidity
* manageable squeeze risk

---

# 2. Three hedge modes

Implement three modes because "similar" can mean different things.

## A. `risk_hedge`

Purpose:

Protect the long during crypto selloffs.

Maximize:

* downside correlation
* crash beta similarity
* market beta similarity
* volatility similarity

Do NOT care strongly about ordinary bull-market correlation.

Use this when:

```bash
hlhedge recommend --long TAO --mode risk_hedge
```

---

## B. `relative_value`

Purpose:

Bet that the chosen long outperforms an economically worse peer.

Maximize:

* normal correlation
* sector similarity
* common factor similarity
* tokenomics divergence

Example conceptual trade:

```text
long good AI token
short bad AI token
```

---

## C. `alpha_preserve`

This may ultimately be the best mode.

Match the long's:

* BTC beta
* ETH beta
* general alt beta
* sector beta
* downside beta

But PENALIZE excessive residual/idiosyncratic correlation.

Reason:

If the short is *too* much like TAO, a genuinely TAO-specific bullish event gets hedged away.

We want:

```text
common exposures cancelled
TAO-specific alpha retained
```

---

# 3. Build a market graph

This is one of the major features.

Every Hyperliquid market becomes a node.

Edges encode similarity:

```text
TAO ───────── FET
 │  \          |
 │   \         |
 │    ─── WLD  |
 │             |
 └──── other AI-beta assets
```

Edge weight should combine:

* 30d correlation
* 90d correlation
* downside correlation
* beta similarity
* tail dependence
* volatility similarity
* factor-loading similarity
* optional sector/category similarity

Node attributes:

```text
symbol
dex
asset_type
category
mark
ADV
OI
OI / ADV
funding
funding_z
premium
spread
impact
structural_short_score
squeeze_score
momentum
relative_momentum
history_days
```

UI should allow:

```text
select TAO
→ graph highlights closest behavioral neighbours
→ color/rank neighbours by structural weakness
```

The result visually answers:

> "Which assets live in TAO's neighborhood but have worse economics?"

---

# 4. Hyperliquid API integration

Base URL:

```text
https://api.hyperliquid.xyz
```

Testnet:

```text
https://api.hyperliquid-testnet.xyz
```

Use direct HTTP for the market-data ingestion layer.

Use the official Hyperliquid Python SDK later for authenticated execution.

Do not require a wallet for research.

## Required `/info` requests

### Universe

```json
{"type":"metaAndAssetCtxs"}
```

Parse the two arrays positionally.

Never independently reorder them.

Store:

```text
name
szDecimals
maxLeverage
onlyIsolated
isDelisted
marginTableId

markPx
midPx
oraclePx
prevDayPx
funding
premium
openInterest
dayNtlVlm
impactPxs
```

Convert all numeric strings immediately into Decimal/float representations.

Store original JSON as well.

---

## Builder DEX discovery

Call:

```json
{"type":"perpDexs"}
```

Then retrieve metadata for enabled DEXs.

Support:

```text
core Hyperliquid perps
HIP-3 builder perps
```

Canonical market ID must include DEX.

Example model:

```text
core:TAO
core:UNI
xyz:XYZ100
```

Never assume ticker alone is globally unique.

---

## Categories

Call:

```json
{"type":"perpCategories"}
```

Also support:

```json
{
  "type":"perpAnnotation",
  "coin":"..."
}
```

Cache annotations.

Do not trust deployer-supplied categories as an investment fact. Treat them as metadata only.

For native/core crypto perps, maintain our own taxonomy because HIP-3 category metadata is not sufficient.

Taxonomy examples:

```text
bitcoin
ethereum
l1
l2
defi
dex
ai
bittensor
meme
gaming
privacy
exchange
oracle
rwa
storage
index
stock
commodity
forex
other
```

Allow multiple tags.

---

# 5. Historical price acquisition

Use:

```json
{
  "type":"candleSnapshot",
  "req":{
    "coin":"TAO",
    "interval":"1h",
    "startTime":...,
    "endTime":...
  }
}
```

Primary research resolution:

```text
1h
```

Also maintain:

```text
4h
1d
```

Do NOT run hundreds of redundant candle requests continuously.

Initial backfill:

```text
1h: maximum available useful history
4h: longer-horizon studies
1d: full available structural history
```

Persist everything locally.

Never recompute candles unnecessarily.

Canonical table:

```text
candles

market_id
interval
open_time
close_time
open
high
low
close
volume
trade_count
ingested_at

PRIMARY KEY(market_id, interval, open_time)
```

---

# 6. Live market stream

Use WebSockets after initial REST bootstrap.

Required subscriptions:

```text
allMids
activeAssetCtx
bbo
candle
```

Optional:

```text
trades
l2Book
```

Don't subscribe to every expensive stream for every market unnecessarily.

Architecture:

```text
WebSocket
   ↓
event parser
   ↓
latest-state cache
   ↓
batch persistence
   ↓
feature recomputation
```

Persist an asset-context snapshot every 5 minutes initially.

This gives us historical:

```text
OI
funding
premium
mark
volume
```

that Hyperliquid's candle history alone cannot reconstruct.

---

# 7. Funding

Historical:

```json
{
  "type":"fundingHistory",
  "coin":"TAO",
  "startTime":...
}
```

Persist hourly funding.

Calculate:

```text
funding_1h
funding_24h_sum
funding_7d_mean
funding_30d_mean
funding_z_30d
funding_z_90d
annualized_recent_funding
```

IMPORTANT SIGN CONVENTION:

Positive Hyperliquid funding:

```text
long pays short
```

Negative funding:

```text
short pays long
```

Therefore for our short book:

```python
short_funding_pnl = short_notional * funding_rate
```

when funding is positive.

Never invert this accidentally.

---

# 8. Liquidity / execution features

From current context:

```text
dayNtlVlm
impactPxs
```

Compute:

```text
ADV_24h
OI_notional = openInterest * markPx
OI_to_ADV = OI_notional / dayNtlVlm
```

From BBO:

```text
spread_bps
```

From book:

calculate estimated execution for:

```text
$1k
$5k
$10k
$25k
$50k
```

as liquidity permits.

Store:

```text
buy_slippage_bps
sell_slippage_bps
depth_10bps
depth_25bps
depth_50bps
```

Do not select a theoretical hedge that can't actually be traded cheaply.

---

# 9. Research database

Use:

```text
Python
Polars
DuckDB
Parquet
```

Do not start with Kafka, Spark or other unnecessary infrastructure.

Suggested structure:

```text
hlhedge/
├── pyproject.toml
├── README.md
├── config/
│   ├── default.yaml
│   ├── taxonomy.yaml
│   └── longs.yaml
│
├── src/hlhedge/
│   ├── hyperliquid/
│   │   ├── client.py
│   │   ├── websocket.py
│   │   ├── universe.py
│   │   ├── candles.py
│   │   ├── funding.py
│   │   └── books.py
│   │
│   ├── data/
│   │   ├── schemas.py
│   │   ├── store.py
│   │   ├── backfill.py
│   │   └── snapshots.py
│   │
│   ├── tokenomics/
│   │   ├── base.py
│   │   ├── manual.py
│   │   └── merge.py
│   │
│   ├── features/
│   │   ├── returns.py
│   │   ├── correlation.py
│   │   ├── downside.py
│   │   ├── factors.py
│   │   ├── funding.py
│   │   ├── liquidity.py
│   │   ├── positioning.py
│   │   └── structural.py
│   │
│   ├── matching/
│   │   ├── pair.py
│   │   ├── graph.py
│   │   ├── baskets.py
│   │   └── regimes.py
│   │
│   ├── portfolio/
│   │   ├── optimizer.py
│   │   ├── constraints.py
│   │   └── attribution.py
│   │
│   ├── backtest/
│   │   ├── engine.py
│   │   ├── costs.py
│   │   ├── funding.py
│   │   └── metrics.py
│   │
│   ├── execution/
│   │   ├── paper.py
│   │   └── hyperliquid.py
│   │
│   ├── api/
│   │   └── server.py
│   │
│   └── cli.py
│
├── data/
│   ├── raw/
│   ├── parquet/
│   └── research.duckdb
│
└── tests/
```

---

# 10. Input portfolio

Support arbitrary desired longs.

Example:

```yaml
longs:
  TAO: 0.60
  UNI: 0.40
```

Normalize weights.

Compute portfolio return:

```text
r_long(t) =
Σ weight_j × r_j(t)
```

All subsequent hedge discovery should work against either:

```text
one long
```

or:

```text
a portfolio of longs
```

---

# 11. Returns

Use LOG RETURNS for correlation/regression:

```python
r_t = log(P_t / P_t-1)
```

Never correlate raw token prices.

Compute:

```text
1h returns
4h returns
1d returns
```

Require aligned timestamps.

Missing candles must NOT silently become zero returns.

---

# 12. Basic similarity metrics

For each candidate `S` against long portfolio `L`, calculate:

```text
corr_7d
corr_30d
corr_90d

beta_7d
beta_30d
beta_90d

vol_7d
vol_30d
vol_90d

vol_ratio

rolling_beta_std
rolling_corr_std
```

Hedge ratio:

```text
β = Cov(r_L, r_S) / Var(r_S)
```

This is a starting point only.

Do not assume β = 1.

---

# 13. Downside correlation

This should receive MORE weighting than ordinary correlation.

Calculate:

```text
corr when BTC < 0
corr when BTC is bottom 25% of observations
corr when long is negative
corr when BTC is bottom 10%
```

Create:

```text
downside_corr
crash_corr
downside_beta
crash_beta
```

A token with:

```text
normal corr = 0.75
crash corr = 0.20
```

is a poor hedge.

A token with:

```text
normal corr = 0.60
crash corr = 0.85
```

may be much more useful.

---

# 14. Tail behaviour

Compute empirical conditional tail dependence.

For example:

```text
P(candidate < its 10th percentile |
  long < its 10th percentile)
```

Also:

```text
joint downside frequency
maximum relative drawdown
worst-day co-movement
```

Create:

```text
tail_match_score ∈ [0,1]
```

---

# 15. Factor model

Do not rely purely on pairwise correlation.

Build factors from available Hyperliquid returns.

Initial factors:

```text
BTC
ETH
HYPE
ALT
```

Construct ALT using a liquidity-weighted or equal-weight basket excluding BTC/ETH/stables.

Later construct PCA factors.

For every asset estimate:

```text
r_i =
α
+ β_BTC BTC
+ β_ETH ETH_residual
+ β_ALT ALT_residual
+ ε
```

Use ridge regression if required for stability.

Store factor exposures.

Pair distance:

```text
factor_distance(i,L)
=
weighted Euclidean distance between factor beta vectors
```

---

# 16. Sector factor

Build sector baskets using taxonomy.

Examples:

```text
AI
DeFi
L1
L2
Meme
RWA
```

For TAO:

```text
TAO return =
crypto beta
+ AI beta
+ TAO-specific residual
```

For UNI:

```text
UNI return =
crypto beta
+ DeFi/DEX beta
+ UNI-specific residual
```

This allows `alpha_preserve` mode to match:

```text
crypto beta + sector beta
```

without deliberately matching the asset-specific residual.

This is central.

---

# 17. Regime-specific models

Market relationships change.

Create simple regimes:

```text
BULL
BEAR
HIGH_VOL
LOW_VOL
CRASH
```

Initial definitions can be deterministic:

```text
BTC above/below 30d EMA
BTC realized vol above/below percentile
BTC daily return bottom decile = crash
```

Calculate pair statistics independently for each regime.

Then produce:

```text
normal_fit
bear_fit
crash_fit
```

The hedge recommendation should display all three.

---

# 18. Structural-short data

Hyperliquid DOES NOT provide complete token unlock/tokenomics fundamentals.

Do not fake this.

Create a provider abstraction:

```python
class TokenomicsProvider:
    def get_snapshot(symbol, timestamp): ...
    def get_unlocks(symbol, start, end): ...
```

MVP provider:

```text
manual CSV / JSON
```

This makes the system immediately testable.

Expected fields:

```text
timestamp
symbol

market_cap
fdv

circulating_supply
total_supply
max_supply

supply_change_7d
supply_change_30d
supply_change_90d

next_unlock_time
next_unlock_tokens
next_unlock_usd
unlock_pct_float
unlock_pct_marketcap
unlock_to_adv

team_unlock_usd
investor_unlock_usd
ecosystem_unlock_usd

annual_emission_pct

protocol_fees
protocol_revenue
tokenholder_revenue
buybacks
burns
```

Make every field nullable.

The engine must work even with only a subset.

Later adapters can use external providers.

---

# 19. Point-in-time requirement

This is non-negotiable.

Every tokenomics observation must include:

```text
known_at
effective_at
```

Backtesting MAY ONLY use information where:

```text
known_at <= rebalance_time
```

Never use today's:

```text
current supply
current FDV
current unlock schedule
```

to reconstruct an old signal.

That creates lookahead bias.

---

# 20. Structural Short Score

All components should first be transformed into cross-sectional percentile ranks or robust z-scores.

Initial score:

```text
STRUCTURAL_SHORT =
0.18 * FDV_overhang
+ 0.18 * dilution_90d
+ 0.16 * unlock_to_ADV
+ 0.10 * insider_unlock_share
+ 0.10 * emission_rate
+ 0.08 * weak_relative_momentum
+ 0.08 * weak_long_term_momentum
+ 0.06 * poor_value_capture
+ 0.06 * declining_activity
```

Where:

```text
FDV_overhang = FDV / market_cap
```

Do not hard-code unavailable fundamentals as zero.

Instead dynamically renormalize weights over observed features.

Return:

```text
score 0–100
confidence 0–100
feature_coverage
```

Example:

```text
WLD
structural_short = 84
confidence = 72
```

---

# 21. Unlock pressure

Important feature:

```text
unlock_to_ADV
=
unlock_usd / average_daily_volume
```

Also calculate:

```text
unlock_to_marketcap
unlock_to_float
insider_unlock_to_ADV
days_until_unlock
```

The engine should learn whether the optimum entry occurs:

```text
60d before
30d before
14d before
7d before
at unlock
after unlock
```

Do not assume unlock day itself is the trade.

---

# 22. Relative weakness

We are especially interested in:

```text
bad token already underperforming
```

Calculate:

```text
candidate_return - BTC_return
candidate_return - sector_return
candidate_return - matched_long_return
```

for:

```text
7d
30d
90d
```

Call:

```text
residual_momentum
```

A candidate whose fundamentals suck AND whose residual return has rolled over is more compelling than a fundamentally bad token in a powerful uptrend.

---

# 23. Positioning engine

From Hyperliquid snapshots calculate:

```text
OI_notional
OI_to_ADV

OI_change_1h
OI_change_24h
OI_change_7d

funding
funding_z

premium
premium_z

price_change
OI_change
```

Classify:

```text
price ↑ + OI ↑
price ↑ + OI ↓
price ↓ + OI ↑
price ↓ + OI ↓
```

Do not mechanically interpret this as bullish/bearish.

Store it as positioning context.

---

# 24. Squeeze Risk Score

A fundamentally attractive short can still be a terrible trade.

Create:

```text
SQUEEZE_RISK 0–100
```

Inputs:

```text
extremely negative funding
rapidly rising OI
high OI / ADV
positive price momentum
large positive residual momentum
thin order book
high volatility
young listing
recent vertical price move
short-side crowding
```

Example:

```text
structural_short = 92
squeeze_risk = 91

→ DO NOT rank as best immediate trade
```

This separation is crucial:

```text
BAD ASSET ≠ GOOD SHORT ENTRY
```

---

# 25. Carry Score

Shorts receive positive funding and pay negative funding.

Calculate expected carry using multiple windows:

```text
funding_24h
funding_7d
funding_30d
```

Avoid blindly annualizing a single current hourly observation.

Output:

```text
expected_short_carry
carry_confidence
```

Score candidates higher when:

```text
fundamentally weak
AND
shorts are being paid
```

Penalize candidates when:

```text
fundamentally weak
BUT
short funding is catastrophically expensive
```

---

# 26. Hedge Fit Score

Normalize components 0–1.

Initial:

```text
HEDGE_FIT =

0.25 downside_match
+0.15 crash_match
+0.15 factor_similarity
+0.10 normal_corr
+0.10 beta_stability
+0.10 volatility_similarity
+0.05 sector_similarity
+0.05 liquidity_similarity
+0.05 tail_match
```

Modify weights according to mode.

### `risk_hedge`

Increase:

```text
downside
crash
tail
```

### `relative_value`

Increase:

```text
ordinary correlation
sector
structural divergence
```

### `alpha_preserve`

Increase:

```text
factor similarity
```

and add penalty for excessive asset-specific residual similarity.

---

# 27. Clone Gap

Implement:

```text
CLONE_GAP =
HEDGE_FIT
×
max(
    STRUCTURAL_SHORT(candidate)
    - STRUCTURAL_SHORT(long),
    0
)
```

Conceptually:

```text
How similar is it to my long?
×
How much worse is it economically?
```

This should be one of the headline rankings.

---

# 28. Total candidate score

Keep individual sub-scores visible.

Never expose only one black-box number.

Initial ranking:

```text
TOTAL_SCORE =

0.40 * hedge_fit
+0.30 * structural_short
+0.10 * carry_score
+0.10 * execution_score
+0.10 * entry_timing_score

- squeeze_penalty
- data_quality_penalty
```

Every recommendation must show WHY it scored highly.

---

# 29. Single-pair output

Command:

```bash
hlhedge recommend --long TAO
```

Output:

```text
LONG: TAO

Candidate       Fit   Badness   Carry  Squeeze  Total
------------------------------------------------------
TOKEN_A          88      91       72      31      86
TOKEN_B          91      78       81      22      84
TOKEN_C          84      95       41      67      73
```

Then:

```text
TAO / TOKEN_A

90d correlation:       0.74
downside correlation:  0.86
crash correlation:     0.90

TAO beta:               ...
TOKEN_A beta:           ...

recommended hedge:
$1 TAO long
$0.73 TOKEN_A short

estimated residual BTC beta:
0.08

expected short funding:
...

structural divergence:
...

squeeze risk:
...
```

---

# 30. Basket optimizer

This is likely better than individual pairs.

Given candidate return matrix:

```text
X
```

and desired-long return:

```text
y
```

solve:

```text
minimize

Σ_t regime_weight_t × (y_t - X_t w)^2

+ λ_diversification × ||w||²
+ λ_turnover × turnover
+ λ_cost × expected_cost(w)

- λ_shortquality × qᵀw
- λ_carry × carryᵀw
```

Subject to:

```text
w_i >= 0

w_i <= max_name_weight

min_short_gross <= Σw_i <= max_short_gross

liquidity constraints

squeeze constraints

asset exclusions
```

Start with `scipy.optimize`.

Do not add CVXPY unless genuinely required.

Initial defaults:

```text
max basket names:       5
max name share:         35%
short gross range:      0.40–1.25 × long gross
minimum history:        45 days
minimum 24h ADV:        configurable
```

---

# 31. Stress-weight the optimizer

Do NOT give every historical hour equal importance.

Example:

```text
ordinary observation: weight 1
BTC bottom quartile:   weight 2
BTC bottom decile:     weight 4
major crash:           weight 6
```

This makes the selected basket specifically better at hedging the states we care about.

Expose this as:

```yaml
optimizer:
  stress_weighting: true
```

---

# 32. Portfolio factor neutrality

After optimization calculate:

```text
BTC beta before hedge
BTC beta after hedge

ETH beta before
ETH beta after

ALT beta before
ALT beta after

sector beta before
sector beta after
```

Example:

```text
60% TAO
40% UNI

BEFORE
BTC beta: 1.42
ALT beta: 1.71

AFTER
BTC beta: 0.11
ALT beta: 0.18
```

This is much more useful than merely reporting dollar neutrality.

---

# 33. Hedge efficiency

Create:

```text
hedge_efficiency =
risk_removed / short_gross
```

Prefer:

```text
$0.65 short gross
removing 90% market risk
```

over:

```text
$1.20 short gross
removing 91%
```

all else equal.

---

# 34. Dynamic hedge ratios

Relationships drift.

Calculate:

```text
7d beta
30d beta
90d beta
EWMA beta
```

Initial live recommendation:

```text
60% weight EWMA/30d
40% weight 90d
```

Later experiment with:

```text
Kalman-filter dynamic beta
```

but do NOT start there.

---

# 35. Hedge replacement engine

Very useful feature.

Suppose:

```text
TAO long
TOKEN_A short
```

TOKEN_A funding suddenly becomes deeply negative.

The system should answer:

> "What is the closest replacement hedge right now?"

Calculate:

```text
replacement_cost
factor exposure change
correlation difference
funding improvement
execution cost
```

Generate:

```text
Replace TOKEN_A → TOKEN_B
```

only when the improvement exceeds a configurable turnover threshold.

This avoids endlessly churning the short book.

---

# 36. Spread monitor

For every pair calculate hedge-adjusted spread:

```text
spread_t =
log(P_long_t)
- β × log(P_short_t)
```

Track:

```text
spread z-score
spread momentum
spread volatility
```

Do NOT blindly assume mean reversion.

Run diagnostics such as:

```text
ADF
half-life estimate
parameter stability
```

Use these as metadata, not proof that the spread must revert.

---

# 37. Dispersion mode

Implement:

```bash
hlhedge dispersion --sector AI
```

Within a cluster:

```text
LONG top economic-quality names
SHORT worst economic-quality names
```

while keeping:

```text
sector beta ≈ 0
market beta ≈ 0
```

This is arguably the purest version of the thesis.

Examples:

```text
AI dispersion
DeFi dispersion
L1 dispersion
L2 dispersion
```

---

# 38. "Trash index"

Create a synthetic index:

```text
GARBAGE10
```

consisting of the 10 highest-confidence structural-short assets meeting liquidity requirements.

Weight by:

```text
inverse volatility
```

or constrained equal-risk weighting.

Then allow:

```text
TAO vs GARBAGE10
UNI vs GARBAGE10
LONG_BOOK vs GARBAGE10
```

Backtest whether a diversified loser basket is more robust than individual shorts.

---

# 39. Quality-vs-trash factor

Construct:

```text
QUALITY_FACTOR =
long top structural quality decile
short bottom structural quality decile
```

Track its cumulative performance independently.

This answers the fundamental research question:

> Is token economic quality actually producing a persistent cross-sectional return factor on the Hyperliquid universe?

If it doesn't, don't trade it.

---

# 40. Funding-neutral garbage factor

Construct another factor that removes the possibility that results are merely funding carry.

Match short candidates on funding or explicitly subtract funding.

Compare:

```text
price alpha
funding alpha
combined alpha
```

This prevents us mistaking carry for predictive tokenomics.

---

# 41. Counterfactual attribution

Every strategy report MUST decompose:

```text
LONG-ONLY PNL

versus

HEDGED PNL
```

Then:

```text
long asset return
short asset return
market beta removed
sector beta removed
short-selection alpha
funding income/cost
trading fees
slippage
turnover cost
```

This is mandatory.

We need to know whether the engine:

```text
A) actually picks losers
```

or merely:

```text
B) lowers portfolio volatility
```

Both are useful, but they are different effects.

---

# 42. Backtesting

Portfolio return:

```text
R_portfolio =
R_long
- Σ(w_i × R_short_i)
+ short_funding
- long_funding_if_using_perps
- fees
- slippage
```

Funding must be applied at its actual timestamps.

Do NOT simply subtract a fixed APR.

---

# 43. Backtest schedules

Test:

```text
hourly signals / daily rebalance
daily signal / daily rebalance
daily signal / weekly rebalance
weekly signal / weekly rebalance
```

The thesis is structural.

Do not automatically optimize for hyperactive trading.

Turnover should be explicitly penalized.

---

# 44. Walk-forward testing

Never optimize the complete historical period and report the same period.

Use:

```text
TRAIN
VALIDATION
TEST
```

then walk forward.

Example:

```text
train 180d
validate 60d
trade/test next 30d
roll forward
```

If insufficient history:

```text
train 90d
validate 30d
test 30d
```

Report limited confidence.

---

# 45. Survivorship bias

Current Hyperliquid listings are NOT a valid historical universe.

Store daily:

```text
universe_snapshot
```

including:

```text
listed
delisted
DEX
metadata
```

From today onward this gives clean point-in-time universes.

For older studies investigate Hyperliquid historical asset contexts/S3.

Never present a backtest over "today's surviving tokens" as an unbiased historical cross-sectional test.

---

# 46. Execution costs

Backtest at least:

```text
maker optimistic
taker realistic
stressed
```

Use actual wallet fees from:

```text
userFees
```

when a wallet is configured.

Otherwise expose configurable fee assumptions.

Slippage model should depend on:

```text
position size
ADV
spread
observed depth
```

---

# 47. Research metrics

Every run reports:

```text
CAGR
total return
annualized vol
Sharpe
Sortino
max drawdown
Calmar

long-only return
hedged return

market beta
downside beta

average short gross
turnover
funding PnL
fees
slippage

hit rate
average winner
average loser

worst day
worst week
worst squeeze event
```

For pair strategies additionally:

```text
relative spread return
hedge-ratio stability
correlation stability
```

---

# 48. Squeeze stress test

Simulate:

```text
short asset +25%
short asset +50%
short asset +100%

while long:
flat
+10%
-10%
```

Also stress:

```text
all short names squeeze simultaneously
```

Report portfolio loss.

This matters more than normal volatility metrics for concentrated crypto short books.

---

# 49. Data quality

For every feature include:

```text
value
timestamp
source
confidence
```

Generate:

```text
DATA_CONFIDENCE 0–100
```

Penalize:

* insufficient history
* missing candles
* missing funding
* thin volume
* recently listed contracts
* stale tokenomics
* uncertain symbol mapping

A flashy score built from bad data should rank below a less exciting but high-confidence candidate.

---

# 50. Symbol mapping

This will become an annoying source of silent bugs.

Canonical entity model:

```text
asset_id
canonical_symbol
hyperliquid_market_id
dex
coingecko_id
tokenomics_id
chain
contract_address
asset_type
```

Never join external data using ticker alone.

`UNI` is safe until someday it isn't.

Use explicit mappings.

---

# 51. CLI

Implement:

```bash
hlhedge sync universe
hlhedge sync candles
hlhedge sync funding
hlhedge sync all

hlhedge markets
hlhedge inspect TAO

hlhedge neighbors TAO
hlhedge neighbors UNI

hlhedge rank-shorts
hlhedge recommend --long TAO
hlhedge recommend --long UNI

hlhedge recommend \
  --portfolio config/longs.yaml

hlhedge recommend \
  --long TAO \
  --mode alpha_preserve

hlhedge backtest \
  --long TAO \
  --start 2026-01-01

hlhedge dispersion --sector ai
hlhedge report
```

---

# 52. `neighbors TAO`

This command should be excellent.

Example:

```text
Nearest behavioral neighbours of TAO

             Fit   Downside   Factor   Sector   Corr90
FET           91      93        88      100      82
XYZ           85      89        86       90      74
ABC           81      84        87       80      71
```

Then add economics:

```text
             Fit   Structural Short   Clone Gap
FET           91          43              39
XYZ           85          91              77
ABC           81          76              62
```

Now the interesting asset becomes obvious.

---

# 53. REST API

Expose a lightweight FastAPI service.

Endpoints:

```text
GET /markets
GET /markets/{symbol}

GET /neighbors/{symbol}

GET /shorts/ranking

POST /hedge/single
POST /hedge/portfolio

POST /backtest

GET /graph
GET /health
```

Do not make the UI depend directly on Hyperliquid.

Everything goes through our service.

---

# 54. Dashboard

After CLI works, create simple frontend.

Main screen:

```text
┌──────────────────────────────────────┐
│ LONG BOOK                            │
│ TAO 60%                              │
│ UNI 40%                              │
├──────────────────────────────────────┤
│ Current beta                         │
│ BTC: 1.38                            │
│ ALT: 1.61                            │
│ DeFi: .34                            │
│ AI: .61                              │
├──────────────────────────────────────┤
│ RECOMMENDED SHORT BASKET             │
│ BAD1 32%                             │
│ BAD2 27%                             │
│ BAD3 18%                             │
├──────────────────────────────────────┤
│ Residual BTC beta: .09               │
│ Expected carry: +x                   │
│ Hedge fit: 89                        │
│ Structural weakness: 86             │
│ Squeeze risk: 29                     │
└──────────────────────────────────────┘
```

Tabs:

```text
Portfolio
Pairs
Short Radar
Market Graph
Unlocks
Funding
Backtests
Attribution
```

---

# 55. Alerts

Generate machine-readable events:

```text
NEW_TOP_SHORT
HEDGE_REPLACEMENT
FUNDING_FLIP
SQUEEZE_RISK
BETA_DRIFT
CORRELATION_BREAK
UNLOCK_APPROACHING
OI_SPIKE
SPREAD_EXTREME
LIQUIDITY_DETERIORATION
```

Example:

```json
{
  "type": "HEDGE_REPLACEMENT",
  "long": "TAO",
  "old_short": "A",
  "new_short": "B",
  "reason": {
    "funding_improvement": 0.22,
    "fit_change": -0.01,
    "squeeze_reduction": 18
  }
}
```

---

# 56. Live recalculation cadence

Not everything needs realtime recalculation.

Suggested:

```text
mids: websocket
BBO: websocket
asset context: websocket / 1–5 min
OI features: 5 min
funding: hourly
correlations: hourly
factor model: every 4h
tokenomics: daily
unlock schedule: daily
portfolio optimizer: hourly or on material event
```

Efficient, not obsessive.

---

# 57. Hyperliquid rate limiting

Implement a weighted request limiter centrally.

Never scatter sleeps around the code.

Have:

```python
RateLimiter.consume(weight)
```

and retries with:

```text
exponential backoff
jitter
```

REST traffic should be heavily cache-aware.

Prefer WebSockets for realtime information.

---

# 58. Historical archive

Create optional S3 downloader for deeper research.

Support Hyperliquid's published:

```text
hyperliquid-archive/market_data
hyperliquid-archive/asset_ctxs
```

Do NOT make S3 mandatory for MVP.

Phase 1 works from API + data collected prospectively.

---

# 59. Paper portfolio

Only after backtests work.

Maintain:

```text
paper_positions
paper_orders
paper_fills
paper_funding
paper_equity
```

Use actual market BBO/book to create plausible simulated fills.

Paper mode should run continuously and make the same decisions the real strategy would have made.

---

# 60. Real execution

DO NOT enable by default.

Use official:

```text
hyperliquid-python-sdk
```

Use an API wallet.

Never store private keys in repository/config tracked by git.

Environment only.

Required modes:

```text
DRY_RUN=true
PAPER=true
LIVE=false
```

Live cannot start accidentally.

---

# 61. Order safety

If/when live execution exists:

* enforce max portfolio notional
* enforce max short name size
* enforce max leverage
* enforce maximum permitted slippage
* reject stale market data
* reject stale optimizer output
* reject insufficient liquidity
* kill switch
* idempotent client order IDs
* verify actual fills
* reconcile positions against Hyperliquid

Pair orders create legging risk.

If one leg fills and another fails:

```text
detect immediately
either complete intended hedge
or flatten unintended exposure
```

Never assume both succeeded.

---

# 62. Testnet

All order/execution development happens against Hyperliquid testnet first.

Market research can remain mainnet-read-only.

Architecture:

```text
MAINNET READS
+
TESTNET WRITES
```

until execution code passes.

---

# 63. Testing

Required unit tests:

```text
test_meta_alignment
test_numeric_conversion
test_market_ids
test_missing_candles
test_log_returns
test_beta
test_downside_beta
test_funding_sign
test_funding_pnl
test_factor_model
test_structural_score
test_missing_structural_fields
test_squeeze_score
test_pair_ranking
test_optimizer_constraints
test_point_in_time_features
test_no_lookahead
test_cost_model
test_pnl_attribution
```

Integration:

```text
test_hl_meta_mainnet
test_hl_candles_mainnet
test_hl_funding_mainnet
test_hl_websocket_mainnet
```

Execution integration:

```text
TESTNET ONLY
```

---

# 64. Critical invariant tests

Create assertions for things that could quietly ruin the entire strategy.

### Invariant 1

Metadata and asset context arrays must have identical lengths before positional merge.

### Invariant 2

No feature timestamp may exceed signal timestamp.

### Invariant 3

No external tokenomics record with:

```text
known_at > signal_time
```

may enter a backtest.

### Invariant 4

No missing return may be converted to `0`.

### Invariant 5

Funding direction must be tested with known positive and negative examples.

### Invariant 6

Backtest universe must be the point-in-time universe where available.

---

# 65. First experiment

Before adding fancy ML, answer one question:

> Does economically weak-token selection improve a correlation-matched short hedge?

Build:

### Strategy A

```text
LONG TAO
SHORT BTC-beta-matched basket
```

### Strategy B

```text
LONG TAO
SHORT highest-correlation basket
```

### Strategy C

```text
LONG TAO
SHORT correlation-matched + structural-weakness basket
```

### Strategy D

```text
LONG TAO
SHORT correlation + weakness + carry + squeeze-filtered basket
```

Compare.

Repeat with:

```text
UNI
HYPE
BTC
ETH
```

The incremental benefit from B → C is the actual economic thesis.

C → D measures whether derivatives timing improves it.

---

# 66. Second experiment

Portfolio:

```text
60% TAO
40% UNI
```

Compare:

```text
long only
BTC short hedge
ETH/BTC hedge
generic alt basket hedge
optimized behavioral hedge
optimized behavioral + structural-short hedge
```

Measure:

```text
return
drawdown
Sharpe
market beta
funding
short alpha
```

---

# 67. Third experiment: downside matching

Compare pair discovery based on:

```text
normal correlation
```

against:

```text
downside correlation
```

against:

```text
factor + downside + tail matching
```

The hypothesis is that ordinary correlation systematically overstates hedge quality during stress.

Test it.

---

# 68. Fourth experiment: single vs basket

For every target long:

```text
best one short
best two shorts
best three shorts
best five shorts
```

Measure:

```text
hedge quality
squeeze drawdown
turnover
cost
funding
```

My expectation is 3–5 names will dominate single-name hedges for robustness, but prove this rather than assuming it.

---

# 69. Fifth experiment: funding

Take identical short scores and split by:

```text
short receives funding
neutral funding
short pays funding
```

Measure subsequent return.

Determine whether positive carry gives us useful selection information or merely improves realized PnL.

---

# 70. Sixth experiment: crowding

For structurally weak assets test outcomes conditioned on:

```text
normal funding
very negative funding

low OI/ADV
high OI/ADV

weak momentum
strong momentum
```

This should tell us when:

```text
"correct fundamental thesis"
```

becomes:

```text
"terrible immediate short"
```

---

# 71. No ML initially

Do not use neural networks.

Do not use an LLM to generate numerical trading scores.

Start with transparent statistics.

Later consider:

```text
gradient boosted ranking model
survival/hazard models around unlocks
regime classifier
```

only after a strong clean dataset exists.

The LLM can explain results.

It must not fabricate the underlying data.

---

# 72. LLM research layer — later

Once numerical engine works, an agent can receive:

```json
{
  "long": "TAO",
  "candidate": "XYZ",
  "hedge_fit": 0.88,
  "structural_short": 0.91,
  "squeeze": 0.23,
  "funding": 0.000012,
  "unlock_days": 17
}
```

and investigate:

```text
Why is this token weak?
What upcoming catalysts invalidate the short?
Has tokenomics changed?
Is there governance introducing buybacks?
Is there a major launch imminent?
```

This is a qualitative veto/research layer.

It does not replace the quantitative engine.

---

# 73. Recommendation object

Canonical output:

```json
{
  "timestamp": "...",
  "long_portfolio": {
    "TAO": 0.6,
    "UNI": 0.4
  },
  "mode": "alpha_preserve",
  "shorts": [
    {
      "market": "TOKEN_A",
      "weight": 0.31,
      "hedge_fit": 88.2,
      "structural_short": 91.4,
      "clone_gap": 79.8,
      "carry": 72.1,
      "squeeze_risk": 23.4,
      "execution": 94.0
    }
  ],
  "before": {
    "btc_beta": 1.37,
    "alt_beta": 1.61
  },
  "after": {
    "btc_beta": 0.09,
    "alt_beta": 0.14
  },
  "confidence": 82
}
```

Everything should be machine readable first.

Pretty reports come second.

---

# 74. MVP definition

MVP is complete when this works:

```bash
hlhedge sync all

hlhedge neighbors TAO

hlhedge recommend --long TAO

hlhedge recommend --long UNI

hlhedge recommend \
  --portfolio config/longs.yaml

hlhedge backtest --long TAO
```

And recommendations use:

```text
actual Hyperliquid prices
actual Hyperliquid funding
actual Hyperliquid OI
actual Hyperliquid liquidity
historical correlations
downside correlations
factor exposures
manual tokenomics input
```

No live trading is required for MVP.

---

# 75. Implementation order

## Phase 1 — exchange data

Build:

```text
client
universe
candles
funding
database
CLI
```

Stop and test.

## Phase 2 — behavioral matching

Build:

```text
returns
correlation
beta
downside beta
tail match
neighbor ranking
```

Stop and inspect TAO/UNI outputs manually.

## Phase 3 — factor model

Build:

```text
BTC/ETH/ALT factors
sector factors
alpha-preserve matching
```

## Phase 4 — structural shorts

Build:

```text
tokenomics schema
manual imports
structural-short score
clone gap
```

## Phase 5 — derivatives timing

Build:

```text
funding
OI changes
premium
squeeze score
carry
```

## Phase 6 — baskets

Build optimizer.

## Phase 7 — backtester

Funding + fees + slippage + point-in-time enforcement.

## Phase 8 — UI

Graph + rankings + portfolio dashboard.

## Phase 9 — paper engine

## Phase 10 — optional testnet/live execution

Do not skip directly to Phase 10.

---

# 76. README thesis

Document the system with this sentence:

> The engine does not attempt to predict the direction of crypto as a whole. It attempts to identify assets with desirable idiosyncratic exposure, then hedge their common market exposures using behaviorally similar assets with inferior economics.

And the key mental model:

```text
DON'T ASK:

"Will TAO go up?"

ASK:

"Will TAO outperform the cheapest basket of bad assets
that reproduces the risks I don't want?"
```

That is the product.
