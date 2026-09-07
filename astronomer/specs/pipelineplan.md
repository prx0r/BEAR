Yes. **The one-month pilot should come first.** GetXAPI’s advanced search explicitly supports `from:... since:... until:...` historical chunking at $0.001 per ~20 posts, whereas its “complete timeline” route is limited to the recent ~3,200-item window. At the quoted rate, $10 corresponds to roughly **200,000 raw search results** before extra thread/detail calls, so there is no reason to burn the full budget before validating the pipeline. ([GetXAPI Docs][1])

For market truth, use Hyperliquid where practical but don't constrain the research to its REST history: Hyperliquid only exposes the most recent 5,000 candles through `candleSnapshot`; its official historical S3 contains L2/order/trade data but is requester-pays and can have gaps. Binance's public archive gives free daily/monthly 1-minute USD-M futures data and trades back years, making it an excellent high-resolution reference dataset for the research layer. ([Hyperliquid][2])

Here is the spec I would give the coding agent.

# X Trader Alpha Research Engine

## Mission

Build a research system that answers one question rigorously:

**Do the selected X accounts contain exploitable forward information, and under exactly what circumstances?**

Do not build a live trading bot yet.

First build a reproducible historical dataset and experimentation framework capable of discovering:

* which traders genuinely predict returns;
* which assets each trader is best at;
* whether their exact entries/targets/stops are useful;
* whether simple directional interpretation works better;
* how quickly each trader's alpha decays;
* which types of calls each trader excels at;
* which combinations of independent traders produce stronger signals;
* which market regimes validate or invalidate particular calls;
* whether classical technical filters improve expectancy;
* whether order-flow/funding/OI conditions improve expectancy;
* whether the result survives fees, latency and realistic execution assumptions;
* which strategies remain profitable out of sample.

The immediate deliverable is a **2026-08-01 → 2026-09-07 pilot study** across the current account universe.

Only after that works should historical X ingestion expand toward two years / maximum available history.

---

# 1. Account universe

Create:

`config/accounts.yaml`

Initial universe:

```yaml
accounts:
  # original directional traders
  - astronomer_zero
  - Timeless_Crypto
  - Trader_XO
  - CryptoBheem
  - lBattleRhino
  - calvintsaikm
  - GreatMattsby

  # rabbit-hole additions
  - PriorXBT
  - Husslin_
  - exitpumpBTC
  - TheSpeculator0
  - liquiditygoblin
  - HangukQuant
  - 52kskew
  - 0xLoris
  - skyquake_1
  - crypto_hades
  - chameleon_jeff
  - 0xdoug
  - quant_arb
  - 0xLightcycle
  - DeFiSquared
  - thiccyth0t
  - fiddybps1
  - CL207
  - TheFlowHorse
  - macrocephalopod
```

Do not hard-code account weights.

Weights are an output of research, not an input.

---

# 2. Repository structure

```text
xalpha/
├── README.md
├── pyproject.toml
├── config/
│   ├── accounts.yaml
│   ├── assets.yaml
│   ├── experiments/
│   └── prompts/
│
├── src/xalpha/
│   ├── ingest/
│   │   ├── getxapi.py
│   │   ├── pagination.py
│   │   ├── threads.py
│   │   ├── media.py
│   │   └── coverage.py
│   │
│   ├── signals/
│   │   ├── schema.py
│   │   ├── classifier.py
│   │   ├── extractor.py
│   │   ├── lifecycle.py
│   │   ├── assets.py
│   │   └── validator.py
│   │
│   ├── market/
│   │   ├── hyperliquid.py
│   │   ├── hyperliquid_s3.py
│   │   ├── binance.py
│   │   ├── normalization.py
│   │   └── features.py
│   │
│   ├── research/
│   │   ├── event_study.py
│   │   ├── levels.py
│   │   ├── returns.py
│   │   ├── mae_mfe.py
│   │   ├── confluence.py
│   │   ├── regimes.py
│   │   ├── filters.py
│   │   ├── controls.py
│   │   └── significance.py
│   │
│   ├── backtest/
│   │   ├── engine.py
│   │   ├── execution.py
│   │   ├── fees.py
│   │   ├── portfolios.py
│   │   └── metrics.py
│   │
│   ├── models/
│   │   ├── author_edge.py
│   │   ├── calibration.py
│   │   └── ensemble.py
│   │
│   └── reports/
│       ├── leaderboard.py
│       ├── plots.py
│       └── html.py
│
├── data/
│   ├── raw/
│   ├── normalized/
│   ├── market/
│   └── derived/
│
├── notebooks/
├── reports/
└── tests/
```

Recommended local stack:

* Python 3.12+
* Polars
* DuckDB
* Parquet
* Pydantic
* httpx
* Typer
* scipy
* numpy
* scikit-learn

Do not require Postgres initially.

DuckDB + partitioned Parquet is ideal for this dataset.

---

# 3. Phase 0 — ultra-cheap smoke test

Before scraping all accounts:

Use GetXAPI's free/new-account credits or a maximum hard spend of `$0.10`.

Sample:

```text
5 accounts
7 days
tweets + replies
```

Suggested accounts:

```text
PriorXBT
exitpumpBTC
Trader_XO
52kskew
Timeless_Crypto
```

Purpose:

1. validate API pagination;
2. inspect actual response fields;
3. estimate posts/account/day;
4. validate thread handling;
5. validate media frequency;
6. validate signal extractor.

Calculate:

```text
posts fetched
pages fetched
USD spent
posts/account/day
signal candidates/account/day
media posts/account/day
thread candidates/account/day
```

Then project expected cost for:

```text
27 accounts × 38 days
27 accounts × 2 years
```

Never guess scrape cost.

Measure it.

---

# 4. GetXAPI historical ingestion

Use:

```text
/twitter/tweet/advanced_search
```

with queries such as:

```text
from:Trader_XO since:2026-08-01 until:2026-08-02
```

GetXAPI specifically recommends `since:` / `until:` chunks for large historical pulls. ([GetXAPI Docs][1])

Default historical chunk size:

```text
1 day
```

If daily volume is tiny, allow:

```text
7 day
```

chunks.

Never use one giant cursor chain for two years.

---

# 5. Preserve raw X data immutably

Every API response must be stored before normalization.

Example:

```text
data/raw/x/
  author=Trader_XO/
    date=2026-08-01/
      page_0001.json.zst
```

Never overwrite raw responses.

Store ingestion metadata:

```text
fetch_id
fetched_at
endpoint
query
cursor
next_cursor
account
range_start
range_end
response_status
api_cost_usd
sha256
```

The GetXAPI `/account/me` endpoint returns current balances and usage and is free, so use it to implement budget guards. ([GetXAPI Docs][3])

Before and after each batch:

```text
credits_before
credits_after
actual_batch_cost
```

Implement:

```text
--budget-usd
```

Hard stop when exceeded.

---

# 6. Store every useful X field

Normalized post schema should retain at least:

```text
tweet_id
author_id
author_handle
created_at
text

source
language

is_reply
in_reply_to_id
in_reply_to_user_id
conversation_id

quoted_tweet_id
quoted_tweet_author
quoted_tweet_text

retweet_count
reply_count
like_count
quote_count
view_count
bookmark_count

hashtags[]
cashtags[]
mentions[]
urls[]

media[]
media_type
media_url

author_followers_snapshot
author_following_snapshot
author_bio_snapshot

fetched_at
raw_payload_path
```

GetXAPI exposes these engagement, author, media and entity fields in its tweet responses. ([GetXAPI Docs][4])

## Critical leakage rule

Historical:

```text
likeCount
viewCount
followers
retweets
bookmarks
```

are observed **when we fetch the historical tweet**, not necessarily when the tweet was posted.

Therefore:

**NEVER use these as historical predictive features.**

Store them for descriptive analysis only.

Otherwise the model gets future information.

---

# 7. Replies must be collected

Do not scrape only profile Posts.

Some of the highest-signal observations happen as replies.

Keep:

```text
standalone tweets
replies
quote tweets
self-thread continuations
```

but classify them separately.

---

# 8. Threads require event sourcing

This is extremely important.

Example:

```text
13:00
"BTC long here"

13:20
"stop 110.8"

14:00
"taking half off"

15:00
"invalidated"
```

Do NOT combine all four posts and pretend the 13:00 signal contained the later information.

Represent:

```text
THESIS #123

13:00 CREATE
14:20 ADD_STOP
14:00 REDUCE
15:00 CLOSE
```

Every self-reply is a new information event.

Historical replay must only know what existed at that timestamp.

GetXAPI's thread endpoint costs $0.005 per request, so don't expand every post. Expand only likely trading theses/self-threads. ([GetXAPI][5])

---

# 9. Media is first-class data

Many traders put the useful information in charts.

For every image:

```text
download media
calculate SHA256
preserve original
```

Run a vision extraction pass looking for:

```text
ticker
timeframe
annotated entry
support
resistance
targets
stop
invalidation
trend lines
direction arrows
labels
```

Never overwrite text extraction.

Store:

```text
text_signal
visual_signal
combined_signal
```

separately so later experiments can determine whether chart interpretation adds value.

---

# 10. Signal taxonomy

Every post gets one primary classification:

```text
NO_SIGNAL
DIRECTIONAL_CALL
EXACT_LEVEL_CALL
CONDITIONAL_SETUP
BREAKOUT_CALL
MEAN_REVERSION_CALL
RANGE_CALL
ORDERFLOW_SIGNAL
MARKET_STRUCTURE
FUNDING_SIGNAL
OI_SIGNAL
LIQUIDATION_SIGNAL
MACRO_SIGNAL
TOKEN_FUNDAMENTAL
POSTMORTEM
POSITION_UPDATE
CLOSE_SIGNAL
INVALIDATION
```

Also attach zero or more tags.

---

# 11. Structured signal schema

Example:

```json
{
  "signal_id": "...",
  "tweet_id": "...",
  "author": "Trader_XO",
  "created_at": "...",

  "assets": ["BTC"],
  "side": "LONG",

  "call_type": "EXACT_LEVEL_CALL",

  "entry_type": "ZONE",
  "entry_low": 111500,
  "entry_high": 112000,

  "trigger": null,
  "invalidation": 110800,

  "targets": [
    114000,
    116000
  ],

  "horizon_text": "this week",
  "horizon_seconds_estimate": 604800,

  "explicit_confidence": null,
  "implicit_confidence": 0.8,

  "timeframes": ["4h", "1d"],

  "requires_condition": false,

  "source_text": "...",
  "extraction_confidence": 0.96
}
```

Always preserve:

```text
source_text
```

for auditing.

---

# 12. Separate forecast from observation

This distinction matters enormously.

Example:

> Spot CVD is declining while OI rises.

That is an observation.

Example:

> I think this squeezes higher.

That is a forecast.

Store both:

```text
observations[]
forecasts[]
```

Then research whether observations themselves predict returns even when the author doesn't explicitly make a trade call.

This could be more valuable than copying trades.

---

# 13. Market data — pilot

For August 1–September 7:

## Hyperliquid

Download:

```text
15m OHLCV
funding history
```

for every referenced Hyperliquid asset.

Hyperliquid provides funding history plus mark/current funding/OI data through the info API. ([Hyperliquid][6])

Hyperliquid REST candle history is limited to the most recent 5,000 bars, so 15m works for roughly the pilot window whereas 1m does not. ([Hyperliquid][2])

## Binance

Use official public USD-M futures data for:

```text
1m klines
aggTrades where required
markPriceKlines
premiumPriceKlines
```

Binance publishes public daily/monthly archives, with daily data normally appearing the next day. ([GitHub][7])

Use Binance primarily for:

```text
high-resolution path
exact level touches
intrabar stop/target ordering
historical technical indicators
```

## Hyperliquid S3

For the most interesting experiments, optionally pull:

```text
L2
trades/fills
asset context
```

from official Hyperliquid archives.

Official docs state that this data is requester-pays and historical archive data can be incomplete. ([Hyperliquid][8])

Do not make the entire research project dependent on S3 availability.

---

# 14. Asset symbol registry

Create canonical identifiers:

```text
BTC
ETH
SOL
HYPE
TAO
DOGE
...
```

Map:

```text
canonical
x_aliases[]
hyperliquid_symbol
binance_symbol
```

Examples:

```text
$BTC
BTC
Bitcoin
btc
```

all resolve to:

```text
BTC
```

Never silently map unknown tickers.

Flag ambiguous assets for review.

---

# 15. Experiment 1 — raw directional alpha

Simplest possible experiment.

For every directional call:

```text
LONG → subsequent return
SHORT → negative subsequent return
```

Calculate:

```text
return_1m
return_5m
return_15m
return_30m
return_1h
return_4h
return_12h
return_24h
return_3d
return_7d
```

This answers:

**Does the author predict direction at all?**

Do not optimize exits yet.

---

# 16. Latency sensitivity

Historical tweets make it tempting to assume execution at the exact tweet timestamp.

Do not do that.

Evaluate every signal under synthetic delays:

```text
0 sec
15 sec
30 sec
60 sec
2 min
5 min
10 min
15 min
30 min
```

Produce:

```text
alpha_decay(author, signal_type, asset)
```

This may reveal:

```text
exitpumpBTC:
strong 0–5m
dead after 20m

Trader_XO:
still useful 4–12h later
```

This is critical for determining whether a signal can actually be automated.

---

# 17. Experiment 2 — exact levels vs direction

This is one of the most important experiments.

For posts with entries/levels, test independent strategies.

## A. Immediate directional

```text
enter at first market price after signal
```

## B. Exact level

```text
wait until author's entry price/zone is touched
```

## C. Near level

```text
fill within configurable tolerance:
10bps
25bps
50bps
100bps
```

## D. Break-and-retest

If the author gives a level:

```text
require crossing
then first retest
```

Compare:

```text
trade count
fill rate
win rate
expectancy
MFE
MAE
profit factor
drawdown
```

This directly answers:

> Should we trust their actual levels or just their direction?

---

# 18. Experiment 3 — author's stops

For signals with explicit invalidations:

Test:

```text
author stop
0.5 ATR
1 ATR
1.5 ATR
2 ATR
fixed %
time stop
no stop
```

Determine whether author's invalidations contain information.

Some traders may be superb at direction but terrible at stop placement.

Others may have exceptional risk-defined setups.

Treat these as different skills.

---

# 19. Experiment 4 — author's targets

Compare:

```text
author target
fixed 1R
fixed 2R
fixed 3R
trailing stop
time exit
```

Measure:

```text
target hit probability
time-to-target
maximum excursion before target
probability stop hit before target
```

---

# 20. Intrabar ambiguity

If a 15m candle contains both:

```text
stop
target
```

you cannot know which happened first.

Mark:

```text
AMBIGUOUS
```

Then resolve using:

```text
1m data
```

or tick trades.

Never assume favorable execution.

---

# 21. Experiment 5 — MAE/MFE

Calculate:

```text
MFE = maximum favorable excursion
MAE = maximum adverse excursion
```

for every horizon.

Aggregate by:

```text
author
asset
signal_type
market_regime
```

This is how we discover whether a trader is:

```text
accurate + clean
accurate + painful
early
late
good at entries
good at targets
```

---

# 22. Experiment 6 — trader specialization

Build matrix:

```text
author × asset_category
```

Categories:

```text
BTC
ETH
SOL
HYPE

large-cap alts
mid-cap alts
small-cap alts
memecoins

majors
alts
```

Calculate separate skill.

Desired result:

```text
BTC king       = X
alts king      = Y
scalp king     = Z
swing king     = Q
levels king    = ...
timing king    = ...
breakouts king = ...
short king     = ...
```

---

# 23. Never rank traders by win rate alone

Leaderboard metrics:

```text
N
hit_rate
avg_return
median_return
expectancy
profit_factor

MFE
MAE

Sharpe
Sortino
max_drawdown

avg_holding_period
signal_frequency

performance_after_fees
performance_after_latency

stability
```

Also calculate Bayesian/shrunk estimates.

A trader with:

```text
4/5 winners
```

should not outrank:

```text
118/190 winners
```

without uncertainty penalties.

---

# 24. Define multiple trader leaderboards

Produce:

```text
BEST_DIRECTION
BEST_ENTRY
BEST_TARGETS
BEST_STOPS
BEST_TIMING
BEST_BTC
BEST_ETH
BEST_SOL
BEST_ALTS
BEST_SHORTS
BEST_LONGS
BEST_BREAKOUTS
BEST_REVERSALS
BEST_ORDERFLOW
BEST_RISK_ADJUSTED
BEST_RAW_EXPECTANCY
MOST_CONSISTENT
```

There is probably no single "best trader."

Different specialists should emerge.

---

# 25. Experiment 7 — independent confluence

Cluster signals by:

```text
asset
direction
time window
```

Example:

```text
BTC LONG
±30 minutes
```

Then test:

```text
1 author
2 authors
3 authors
4+ authors
```

But correct for dependence.

---

# 26. Influencer dependence model

Three traders repeating the same source is not three independent signals.

Calculate relationships from:

```text
quote tweets
replies
mentions
timestamp ordering
text similarity
historical signal correlation
```

Create:

```text
independence_score
```

Example:

```text
3 unrelated BTC longs = high confidence

A tweets
B quotes A
C repeats B

= approximately one source
```

---

# 27. Confluence experiments

Test:

```text
count_confluence
weighted_confluence
independence_adjusted_confluence
specialist_confluence
cross-domain_confluence
```

Particularly important:

```text
technical trader bullish
+
orderflow trader bullish
+
microstructure trader bullish
```

That may be more valuable than three TA traders saying the same thing.

---

# 28. Experiment 8 — classical technical filters

Build binary market-state features at every signal timestamp.

Do not optimize them initially.

Generate simple features:

## Trend

```text
price > EMA20
price > EMA50
price > EMA100
price > EMA200

EMA20 > EMA50
EMA50 > EMA200

EMA20 slope positive
EMA50 slope positive
EMA200 slope positive
```

Across:

```text
5m
15m
1h
4h
1d
```

## Momentum

```text
RSI14 > 50
RSI14 > 60
RSI14 < 40

price > previous day high
price < previous day low
```

## Volatility

```text
ATR percentile
realized-vol percentile
range expansion
range contraction
```

## Volume

```text
volume > moving average
volume z-score
```

Then ask simple questions:

```text
Are Trader_XO longs profitable only above 1h EMA200?

Are BattleRhino alt longs garbage when BTC < 4h EMA50?

Are Timeless shorts significantly better below daily EMA20?

Does exitpump orderflow work only during high realized volume?
```

Exactly the playground we want.

---

# 29. Experiment 9 — derivatives filters

Use:

```text
funding
funding percentile
funding sign
OI change
OI acceleration
mark/oracle premium
perp premium
volume
```

Features:

```text
funding_positive
funding_extreme_positive
funding_negative

oi_1h_up
oi_4h_up

price_up_oi_up
price_up_oi_down
price_down_oi_up
price_down_oi_down

premium_positive
premium_negative
```

Hyperliquid exposes historical funding and current asset contexts including mark, funding and OI. ([Hyperliquid][6])

---

# 30. Experiment 10 — BTC regime for alt calls

Every alt signal must also receive BTC context.

Example features:

```text
BTC > EMA20 1h
BTC > EMA50 4h
BTC > EMA200 4h
BTC daily return

BTC realized volatility
BTC funding
BTC OI trend
BTC regime
```

This may be huge.

A trader can be excellent at selecting strong alts but still lose because BTC is collapsing.

Test:

```text
alt signal alone
vs
alt signal + BTC regime filter
```

---

# 31. Regime classification

Start deterministic.

```text
UPTREND
DOWNTREND
RANGE

LOW_VOL
NORMAL_VOL
HIGH_VOL
CRASH

OI_EXPANDING
OI_CONTRACTING

POSITIVE_FUNDING
NEGATIVE_FUNDING
```

Later allow clustering/models.

Do not start with ML.

---

# 32. Control groups

Every result needs controls.

For each real signal, generate matched controls:

```text
same asset
same hour-of-day
similar volatility
same regime
random nearby date
```

Question:

> Did the influencer actually add information beyond simply buying BTC during a bull market?

This prevents us from declaring someone a genius because every alt went up that month.

---

# 33. Relative performance

For alt calls calculate:

```text
asset_return
BTC_return
ETH_return

asset_minus_BTC
asset_minus_market
```

An altcoin caller saying "long everything" during an alt rally should not receive the same credit as somebody consistently selecting outperformers.

---

# 34. Post-hoc claims

Explicitly classify:

```text
BEFORE_MOVE
DURING_MOVE
AFTER_MOVE
POSTMORTEM
```

Example:

> Told you guys BTC was going up.

after a +7% move gets **zero predictive credit**.

This is an extremely important filter.

---

# 35. Chase measurement

At tweet time:

```text
reference_price
```

Then calculate:

```text
move_last_1m
move_last_5m
move_last_15m
move_last_1h
```

Determine whether a trader:

```text
predicts moves
```

or:

```text
announces moves already underway
```

Also test:

```text
enter immediately
wait for pullback
skip if price moved > X since tweet
```

---

# 36. Signal half-life

For every:

```text
author × signal_type
```

estimate alpha decay.

Example output:

```text
PriorXBT/MM_FLOW
half-life: ~8m

Trader_XO/SWING_LEVEL
half-life: ~11h

Timeless/ALT_BREAKOUT
half-life: ~90m
```

This will later determine polling frequency and execution urgency.

---

# 37. Experiment 11 — author combinations

Once individual stats exist, test pairs.

Example:

```text
XO + exitpump
XO + PriorXBT
exitpump + 52kskew
Timeless + BattleRhino
```

Then triples.

Do not brute-force thousands of combinations without controls.

Require minimum sample counts.

Apply multiple-testing correction or holdout validation.

---

# 38. Experiment 12 — disagreement

Disagreement may be useful too.

Example:

```text
TA bullish
orderflow bearish
```

Measure what happens.

Possible finding:

```text
technical bullish
+
microstructure bearish

= avoid trade
```

This could be more valuable than confluence.

---

# 39. Strategy families

Maintain separate strategy definitions.

```text
S0_RANDOM_CONTROL

S1_RAW_DIRECTION
S2_EXACT_LEVELS
S3_DIRECTION_WITH_AUTHOR_STOP
S4_DIRECTION_WITH_ATR_STOP

S5_BEST_AUTHOR_ONLY
S6_ASSET_SPECIALISTS
S7_SIGNAL_TYPE_SPECIALISTS

S8_CONFLUENCE
S9_INDEPENDENT_CONFLUENCE

S10_TECHNICAL_FILTERED
S11_DERIVATIVES_FILTERED
S12_TECH_PLUS_DERIVATIVES

S13_FULL_ENSEMBLE
```

Every strategy must run against the same event database.

---

# 40. Do not introduce position sizing yet

Initial tests:

```text
$1 equal notional per call
```

The point is to identify alpha.

Then compare:

```text
equal notional
equal volatility
equal risk-to-stop
```

Only after signal quality is demonstrated should position sizing enter the system.

Otherwise sizing can disguise a bad predictor.

---

# 41. Backtest execution assumptions

Each trade stores:

```text
decision_timestamp
execution_timestamp
reference_price
simulated_fill
spread
fee
slippage
funding
exit_price
net_return
```

Initial research can use simple prices.

But maintain interfaces capable of later using real book simulation.

---

# 42. PnL attribution

Every PnL event needs attribution:

```text
author
asset
call_type
strategy
market_regime

contributing_authors[]
filters_passed[]
filters_failed[]
```

The system must be able to answer:

> Exactly why did this strategy make money?

---

# 43. Walk-forward validation

Never randomly shuffle historical time series.

Later two-year research should use:

```text
train months 1-6
test month 7

train months 2-7
test month 8
...
```

Weights at timestamp T can only use data prior to T.

No future reputation leakage.

---

# 44. Model progression

Do not start with neural networks.

Order:

```text
1. descriptive statistics
2. conditional tables
3. logistic regression
4. regularized regression
5. tree models
6. ensemble
```

The goal is understanding first.

Example:

```text
P(call succeeds |
  author,
  asset,
  call_type,
  regime,
  signal_age,
  technical_state,
  funding,
  OI,
  confluence)
```

---

# 45. Dynamic author weights

Ultimate weight should look like:

```text
W(
  author,
  asset,
  signal_type,
  direction,
  horizon,
  regime
)
```

Not:

```text
W(author)
```

Example:

```text
Trader_XO:
BTC_SWING        1.42
ALT_SCALP        0.81
FOMC             0.64

exitpumpBTC:
BTC_ORDERFLOW    1.55
ALT_DIRECTION    0.63

PriorXBT:
MM_FLOW          1.62
SWING_DIRECTION  0.91
```

---

# 46. Small-sample shrinkage

Never allow tiny samples to dominate.

Use:

```text
minimum N
confidence intervals
Bayesian shrinkage
```

Small samples regress toward baseline.

A 5/5 record should not automatically become maximum weight.

---

# 47. Pilot output

Create:

```text
reports/pilot_2026-08-01_2026-09-07/
```

Containing:

```text
README.md

raw_signal_count.csv
signal_classification.csv

author_leaderboard.csv
author_asset_matrix.csv
author_calltype_matrix.csv

directional_returns.csv
exact_levels_vs_direction.csv
stops_comparison.csv
targets_comparison.csv

lag_decay.csv
mae_mfe.csv

confluence.csv
pair_confluence.csv
disagreement.csv

technical_filters.csv
derivatives_filters.csv
btc_alt_filters.csv

best_calls.csv
worst_calls.csv
missed_moves.csv

strategy_comparison.csv

signals.parquet
signal_events.parquet
backtest_trades.parquet

report.html
```

---

# 48. Pilot HTML report

Top page should answer immediately:

```text
WHO WAS ACTUALLY GOOD?

Best BTC trader
Best alt trader
Best direction
Best entries
Best exits
Best timing
Best short trader
Best orderflow signaler

Who added no detectable value?

Who was merely trend-following?

Whose signal vanished after 5 minutes?

Do exact levels beat simple direction?

Does confluence improve results?

Which pair was strongest?

Which technical filters added value?

Which filters destroyed good signals?
```

Then drill down.

---

# 49. Individual trader page

Each account gets:

```text
N signals

long / short
asset breakdown
signal types

win rate
expectancy
MFE
MAE

1m / 5m / 15m / 1h / 4h / 24h forward return

lag-decay graph

best asset
worst asset

best regime
worst regime

best call type
worst call type

exact-level performance

top 10 calls
bottom 10 calls
```

Include links to original X posts.

---

# 50. Missed-move analysis

Don't only analyze tweets.

Analyze major market moves and ask:

```text
Who called it before it happened?
Who called it during it?
Who missed it?
Who faded it incorrectly?
```

Define events such as:

```text
BTC +3%
BTC -3%
ALT +10%
ALT -10%
large liquidation
breakout
reversal
```

This is how we determine who actually "caught the BTC move."

---

# 51. Major-move score

Create:

```text
MOVE_CAPTURE_SCORE
```

Reward:

```text
early
correct direction
high conviction
good level
good risk definition
```

Penalize:

```text
late
vague
post-hoc
deleted/invalidation after move
```

This creates another leaderboard:

```text
BEST BIG-MOVE CALLER
```

---

# 52. Extraction audit

LLM extraction will make mistakes.

Randomly sample:

```text
100 signal posts
100 non-signal posts
```

Manually verify:

```text
precision
recall
asset extraction
direction extraction
level extraction
target extraction
stop extraction
```

Require roughly:

```text
>95% direction accuracy
>95% asset accuracy
```

before trusting aggregated backtests.

---

# 53. Every experiment is configuration

Example:

```yaml
name: xo_btc_long_ema_filter

universe:
  authors:
    - Trader_XO
  assets:
    - BTC

signal:
  sides:
    - LONG

entry:
  mode: immediate
  lag_seconds: 60

filters:
  - price_above_ema:
      timeframe: 1h
      period: 200

exit:
  mode: horizon
  horizon: 4h
```

Researcher should be able to create new experiments without touching engine code.

---

# 54. Experiment registry

Every run stores:

```text
experiment_id
git_commit
config_hash
dataset_hash
start
end
created_at
results
```

This prevents "we got a great result yesterday but don't know what settings produced it."

---

# 55. Reproducibility

Every derived dataset needs lineage:

```text
X raw hashes
market-data hashes
extractor version
prompt version
code commit
```

The dataset itself is the moat.

Treat it accordingly.

---

# 56. CLI

Required commands:

```bash
xalpha x estimate-cost \
  --start 2026-08-01 \
  --end 2026-09-07

xalpha x scrape \
  --start 2026-08-01 \
  --end 2026-09-07 \
  --budget-usd 2

xalpha x enrich-threads

xalpha x enrich-media

xalpha signals extract

xalpha market sync \
  --start 2026-08-01 \
  --end 2026-09-07

xalpha research event-study

xalpha experiment run baseline_directional

xalpha experiment run exact_levels

xalpha experiment run confluence

xalpha report pilot
```

---

# 57. Tests

At minimum:

```text
pagination does not skip pages
pagination does not duplicate posts
tweet IDs dedupe correctly
UTC timestamps correct

no future thread events leak backwards

market timestamp alignment correct

LONG return sign correct
SHORT return sign correct

level touch detection correct

stop-before-target detection correct
target-before-stop detection correct
ambiguous candles handled correctly

EMA uses only prior candles
funding feature uses only prior observations

latency applied correctly

future engagement never exposed to models
```

---

# 58. Phase 1 acceptance criteria

Before buying/pulling two years:

The pilot must demonstrate:

```text
all 27 accounts successfully ingested
coverage report generated
raw data preserved

signal classifier audited
market-data joins reliable

baseline directional study works
exact-level experiment works
lag-decay experiment works
author leaderboard works
asset specialization works
confluence works
technical filters work

all experiments reproducible
```

Most importantly:

**at least one statistically interesting signal should emerge.**

Not necessarily profitable yet.

Examples:

```text
author X BTC calls show positive 4h forward expectancy

author Y exact levels outperform immediate entries

two independent orderflow + TA calls materially outperform either alone

BTC trend filter removes a large fraction of losing alt calls
```

If nothing emerges, do not spend more merely because the project is interesting.

---

# 59. Phase 2 — maximum historical X dataset

Once pilot passes:

Target approximately:

```text
2024-09-01 → present
```

or maximum history GetXAPI/X search reliably returns.

Use:

```text
daily/weekly date chunks
cursor pagination
deduplication
coverage manifests
budget guard
```

Do not assume historical completeness.

Record:

```text
expected date ranges
returned post counts
empty periods
API failures
retry counts
```

A two-year search through GetXAPI should use `advanced_search`, not the recent timeline endpoint. GetXAPI explicitly documents date-chunking for large historical pulls. ([GetXAPI Docs][1])

---

# 60. Spend intelligently

Advanced search:

```text
$0.001 / ~20 results
≈ $0.05 / 1,000 posts
```

according to current GetXAPI pricing. ([GetXAPI][9])

Therefore:

```text
$1 ≈ 20,000 posts
$5 ≈ 100,000 posts
$10 ≈ 200,000 posts
```

roughly, before extra enrichment calls.

Do NOT call:

```text
tweet/detail
thread
replies
```

for every historical tweet.

Instead:

```text
cheap bulk search
        ↓
candidate classifier
        ↓
expensive enrichment only on useful posts
```

That is the economical pipeline.

---

# 61. Phase 3 — paper strategy search

Only once historical edges are identified.

Create parallel paper portfolios:

```text
RAW_DIRECTION
BEST_AUTHORS
SPECIALISTS
EXACT_LEVELS
CONFLUENCE
CONFLUENCE_FILTERED
FULL_MODEL
```

Every signal goes through all strategies simultaneously.

Use `$1 normalized notional`.

---

# 62. Phase 4 — live shadow collection

Start recording live Hyperliquid:

```text
trades
l2Book
allMids
funding
asset context
```

from now onward.

Hyperliquid provides WebSocket subscriptions for live trades and L2 books. ([Hyperliquid][10])

This creates our own perfect future archive instead of depending indefinitely on third-party historical sources.

---

# 63. Phase 5 — tiny Hyperliquid canary

Only after:

```text
out-of-sample profitability
realistic fees
realistic latency
stable parameters
paper-forward validation
```

enable tiny mainnet execution.

That is a separate phase.

Do not implement it during the pilot.

---

# 64. Core philosophy

Do not ask:

> Which influencer should we copy?

Ask:

> Which information source has measurable predictive power for which market, horizon, regime and setup?

The final system should eventually learn structures such as:

```text
Trader_XO
+
BTC
+
4h technical setup
+
price above EMA200
+
normal funding

= strong
```

while simultaneously learning:

```text
Trader_XO
+
small alt
+
1m scalp
+
BTC below major trend
+
extreme volatility

= ignore
```

And:

```text
exitpumpBTC orderflow
+
PriorXBT market-maker confirmation
+
independent TA reclaim

= unusually high confidence
```

That conditional intelligence is the real asset.

---

# Immediate implementation order

Do these sequentially:

```text
1. repository + schemas
2. GetXAPI budget-aware scraper
3. 5-account / 7-day smoke test
4. signal extractor
5. extraction audit
6. all-27-account Aug 1–Sep 7 scrape
7. Binance 1m market-data downloader
8. Hyperliquid 15m + funding downloader
9. timestamp/asset joining
10. raw directional event study
11. exact levels study
12. latency/alpha-decay study
13. author × asset leaderboard
14. author × signal-type leaderboard
15. MAE/MFE
16. confluence
17. technical/regime filters
18. HTML report
19. review pilot results
20. only then authorize two-year scrape
```

## Definition of done for the first milestone

The coding agent should stop and produce results when it can answer, from August 1–September 7 data:

1. **Who made the best BTC calls?**
2. **Who made the best alt calls?**
3. **Who caught the largest moves before they happened?**
4. **Whose calls were late?**
5. **Whose exact levels added value?**
6. **Whose levels made their calls worse?**
7. **Who had the best risk/reward after their stated stop?**
8. **How fast did each person's alpha decay?**
9. **Which independent pair/group had the strongest confluence?**
10. **Did EMA/trend/funding/OI filters improve any trader materially?**
11. **Which accounts had no statistically useful edge?**
12. **Is the result promising enough to justify the two-year dataset?**

Do not proceed to optimization or live trading until those twelve questions have concrete, reproducible answers.

One detail in that spec is especially important: **keep later self-replies as new events rather than letting them rewrite the original call**. Otherwise it becomes very easy to accidentally backtest a trader with hindsight. The same applies to present-day likes/views/follower counts on historical posts—they must never become historical model features.

The pilot could be surprisingly revealing even before ML: a simple `author × call_type × asset × horizon × regime` cube should immediately expose whether there are genuine specialists or whether the apparent geniuses are mostly benefiting from the same market beta.

[1]: https://docs.getxapi.com/docs/tweets/advanced-search "Twitter Advanced Search API | GetXAPI Docs"
[2]: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint?utm_source=chatgpt.com "Info endpoint | Hyperliquid Docs"
[3]: https://docs.getxapi.com/docs/account/account-info "Get GetXAPI Account Info API | GetXAPI Docs"
[4]: https://docs.getxapi.com/docs/users/user-tweets?utm_source=chatgpt.com "Get User Tweets API | GetXAPI Docs"
[5]: https://www.getxapi.com/changelog?utm_source=chatgpt.com "Changelog: GetXAPI API Updates & New Endpoints 2026"
[6]: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint/perpetuals?utm_source=chatgpt.com "Perpetuals | Hyperliquid Docs"
[7]: https://github.com/binance/binance-public-data?utm_source=chatgpt.com "GitHub - binance/binance-public-data: Details on how to get Binance public data · GitHub"
[8]: https://hyperliquid.gitbook.io/hyperliquid-docs/historical-data?utm_source=chatgpt.com "Historical data | Hyperliquid Docs"
[9]: https://www.getxapi.com/pricing?utm_source=chatgpt.com "GetXAPI Pricing, Twitter API at $0.05 per 1K Tweets"
[10]: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket/subscriptions?utm_source=chatgpt.com "Subscriptions | Hyperliquid Docs"
