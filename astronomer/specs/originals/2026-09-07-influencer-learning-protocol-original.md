# User Message — 2026-09-07 (Word-for-Word)

*Saved strictly word for word. No summarization. No condensation.*

---

Yes. **Entrant-only evaluation is the correct architecture.** Re-running every historical source whenever you add one person wastes compute, invites accidental methodology drift, and makes provenance harder. Freeze the canonical market-state/outcome tables; process only the new entrant; then rerun the cheap marginal-comparison/confluence layer.

There is one more important simplification: **do not actually use RL to learn whether Aporia or Timeless is good yet.** After a prediction horizon expires, we can observe what would have happened for every source, whether we traded it or not. That is a *full-information expert-learning* problem, not a bandit problem. "Sleeping/specialist expert" algorithms are almost tailor-made for influencers who speak only occasionally or only in certain regimes. ([arXiv][1]) RL/contextual bandits become useful one layer later, when BEAR must decide which strategy to allocate real risk to and therefore only experiences the PnL path produced by its actual actions.

### First canonical onboarding: 0xaporia

The existing pipeline has actually falsified its own previous conclusion about him. Current results treat three Aporia posts as directional CALLs and report excellent 4h performance.  But inspection of the original posts shows:

* **August 6:** he explicitly describes Bitcoin as grinding sideways with "no real direction" and compares it to the summer-2022 range. That's a genuine `REGIME=RANGE/CHOP` observation, even though the current extractor threw the whole post into retrospective content.
* **August 20:** the supposedly bullish CALL is actually a methodological argument that trend-following strategies should avoid fixed targets because their edge comes from open-ended winners. The word "long" appears in "as long as the trend is intact." It is **not a trade call at all**.
* **August 20:** "take the risk of buying the top" is better interpreted as a `TREND_CONTINUATION/RISK_ACCEPTANCE` view than a specific executable BTC call.
* **August 21:** he explicitly says the market is being driven by trend/momentum and argues for owning current strength rather than laggards. That's simultaneously `REGIME_TRENDING` and `CROSS_SECTIONAL_MOMENTUM/LEADER_SELECTION`.
* He also gives a genuinely interesting **breadth observation**: aggregate alt market cap can look healthy while an equal-weight alt basket is weak, meaning headline alt-cap performance can be driven by relatively few leaders.
* **August 28:** the extractor calls him BEARISH because the evidence span is "sell." The complete sentence is essentially "you waited months for breakout and now you're going to sell on escape velocity? bear market has corrupted you." This is almost certainly a **bullish trend-persistence view**, not a bearish call.

So the previous "`0xaporia = 100% 4h trader`" result is discarded. His much more interesting hypothesis is:

> **Aporia may be a low-frequency TREND/REGIME/BREADTH specialist who identifies when the correct meta changes from chop → trend and emphasizes concentration in leaders rather than trying to bottom-fish laggards.**

That's what we should test.

I attempted to write this directly into BEAR, but the GitHub connection returned `403 Resource not accessible by integration`, so I cannot honestly claim the repository mutation is complete. The following is the exact operating specification I would have the coding agent commit.

# BEAR Influencer Learning Protocol v1

## 1. Core model

An influencer is NOT a strategy.

An influencer is a noisy sensor of one or more market primitives.

The hierarchy is:

```text
RAW SOURCE
   ↓
PRIMITIVE OBSERVATION
   ↓
EMPIRICAL SOURCE×PRIMITIVE RELIABILITY
   ↓
GRAPH STATE
   ↓
META / REGIME
   ↓
STRATEGY ACTIVATION
   ↓
TRADE
   ↓
PNL
```

Examples:

```text
Aporia
→ REGIME / TREND / BREADTH

Timeless
→ TACTICAL DIRECTION / ENTRIES

52kskew
→ ORDER FLOW

Laevitas
→ DERIVATIVES / CROWDING

Lookonchain
→ ONCHAIN CAPITAL FLOW

Binance trader
→ REAL-MONEY POSITIONING

Tokenomist / BEAR fundamentals
→ STRUCTURAL SUPPLY
```

They must not share the same reward function.

---

# 2. Do not use RL where ordinary learning is sufficient

Influencer reputation is initially a **full-information online expert problem**.

After the relevant horizon passes, BEAR can score every prediction, including predictions it did not trade.

Therefore use:

```text
Bayesian updating
or
discounted exponential expert weights
```

conditioned on:

```text
source
× primitive
× asset/scope
× regime
× horizon
× event subtype
```

Use a "sleeping expert" formulation:

```text
If source says nothing → expert inactive.
If source speaks outside its validated specialty → expert inactive.
If source emits relevant event → expert participates.
```

RL is reserved for:

```text
strategy activation
portfolio allocation
position sizing
capital/risk allocation
```

where actions affect the realized portfolio path.

---

# 3. Source lifecycle

Every entrant has exactly these states:

```text
DISCOVERED
SAMPLED
RESEARCH_ONBOARDED
VALIDATING
VALIDATED
SHADOW
ACTIVE
DOWNWEIGHTED
RETIRED
```

No source jumps from X discovery to trading weight.

`RESEARCH_ONBOARDED` means:

* we know why we want them;
* we know which primitive they supposedly measure;
* we possess raw data;
* a falsifiable evaluation contract exists.

It does NOT mean they have alpha.

---

# 4. Entrant-only processing

When adding source N+1:

DO NOT recompute sources 1…N.

Frozen shared assets:

```text
posts schema
market_state(t)
market outcomes
regime labels
price histories
cost model
existing source event tables
existing source posteriors
```

Run only:

```text
NEW SOURCE
   ↓
raw acquisition
   ↓
normalization
   ↓
primitive classification
   ↓
source-specific extraction
   ↓
semantic QA
   ↓
primitive-specific outcome calculation
   ↓
baseline comparison
   ↓
existing graph + source comparison
   ↓
posterior update
   ↓
confluence recalculation
```

Full historical rebuild occurs ONLY when:

```text
schema_version changes
extractor_version changes materially
outcome semantics change
market-state construction changes
cost model changes materially
```

---

# 5. Every entrant requires a hypothesis BEFORE outcome inspection

Example:

```json
{
  "source": "0xaporia",
  "primary_primitive": "REGIME_TREND",
  "secondary_primitives": [
    "ALT_BREADTH",
    "CROSS_SECTIONAL_MOMENTUM"
  ],

  "hypothesis":
    "Aporia identifies transitions between chop and persistent trend and correctly emphasizes leader participation when breadth is narrow.",

  "mechanism":
    "Trend persistence and cross-sectional concentration affect which strategies and assets should receive risk.",

  "expected_role": [
    "STRATEGY_ACTIVATION",
    "STRATEGY_VETO",
    "ASSET_SELECTION"
  ],

  "falsification":
    "Aporia adds no predictive or gating value beyond a simple price/breadth regime model."
}
```

This file is created BEFORE looking at source outcomes.

---

# 6. Primitive reward contracts

## REGIME / TREND

Example source:

```text
0xaporia
macrocephalopod
```

They predict STATE, not trades.

Output:

```text
RISK_ON
RISK_OFF
TREND_UP
TREND_DOWN
RANGE
TRANSITION
HIGH_VOL
LOW_VOL
```

Scopes:

```text
BTC
CRYPTO_BETA
ALT_BREADTH
MEME
```

### Baseline

Point-in-time machine regime:

```text
past returns
trend efficiency
volatility
breadth
correlation
```

No fancy HMM required initially.

### Rewards

Primary:

```text
Brier skill
log-loss improvement
transition lead/lag
```

Most economically important:

```text
ΔEV of downstream strategy gating
```

Example:

```text
DEATH_TOKEN baseline EV
vs
DEATH_TOKEN + Aporia regime veto EV
```

### Falsification

A regime influencer is LOW SIGNAL if:

```text
source does not improve baseline regime forecast
AND
source does not improve downstream strategy EV
```

Even if their posts sound intelligent.

---

# 7. TACTICAL TRADER

Example:

```text
Timeless
Trader_XO
```

Output:

```text
LONG
SHORT
CONDITIONAL
ENTRY
STOP
TARGET
REDUCE
EXIT
```

### Reward

Actual executable:

```text
net PnL
expectancy
profit factor
MFE/MAE
R multiple
latency sensitivity
```

After:

```text
fees
slippage
funding
```

Benchmark against:

```text
always long
momentum
reversal
regime
random regime-matched entry
```

Main quantity:

```text
ΔEV(source call | baseline market state)
```

Not raw win rate.

---

# 8. MEME / ALT SCOUT

This is especially clean.

The question is:

> Did they identify the right asset before it became an obvious winner?

Source emits:

```text
TOKEN
POSITIVE/NEGATIVE VIEW
TIMESTAMP
CONVICTION
NARRATIVE if explicit
```

Freeze the contemporaneously tradeable universe.

Evaluate:

```text
1h
4h
24h
3d
7d
```

against:

```text
BTC
equal-weight crypto universe
sector
simple momentum rank
simple attention rank
```

Metrics:

```text
rank IC
precision@K
top-decile winner hit rate
excess return
max adverse excursion
liquidity-adjusted realized PnL
```

Critical falsification:

```text
influencer picks must outperform simple momentum/attention
```

because saying "buy the already viral coin" is not necessarily proprietary information.

Twitter attention has documented short-horizon predictive relationships in crypto, so simple attention itself must be a baseline rather than credited to the influencer.

---

# 9. LEVEL / MARKET STRUCTURE SOURCE

Examples:

```text
Trader_XO
```

Do not score:

> support at 75k

as an immediate long.

Wait until interaction with level.

Evaluate:

```text
P(rejection | touch)
P(break | touch)
MFE after interaction
MAE after interaction
PnL of explicitly stated condition
```

Baseline:

```text
random nearby volatility-scaled levels
round numbers
recent highs/lows
```

Important falsification:

A person posting dozens of levels eventually gets some correct.

Reward must penalize level density.

---

# 10. ORDER FLOW source

Examples:

```text
52kskew
exitpump
```

Do NOT demand a directional CALL.

Possible predictions:

```text
continuation
reversal
volatility expansion
absorption
liquidation risk
entry confirmation
trade veto
```

Test each stated mechanism.

Example:

```text
existing LONG has EV = +x
existing LONG + bearish spot/perp divergence veto has EV = +y
```

Reward:

```text
ΔEV = y - x
```

A flow source can be extremely valuable while having terrible standalone tweet-direction accuracy.

---

# 11. DERIVATIVES source

Examples:

```text
Laevitas
```

Primitive outputs:

```text
funding crowding
OI expansion/contraction
basis
liquidations
options skew
squeeze risk
```

Reward should answer:

```text
Did interpretation add information beyond raw funding/OI data?
```

Baseline:

```text
BEAR's raw funding
BEAR's raw OI
BEAR's price
BEAR's regime
```

Candidate:

```text
baseline + influencer interpretation
```

If candidate does not improve:

source interpretation weight = 0.

This prevents paying for someone merely narrating data BEAR already has.

---

# 12. REAL POSITION source

Examples:

```text
Binance Smart Money
Hyperliquid wallets
```

Events:

```text
OPEN_LONG
ADD_LONG
REDUCE_LONG
CLOSE_LONG

OPEN_SHORT
ADD_SHORT
REDUCE_SHORT
CLOSE_SHORT

FLIP
```

Reward:

```text
forward abnormal return
realized position PnL if reconstructable
asset×regime×horizon expectancy
marginal graph value
```

These receive a stronger research PRIOR than tweets because they are revealed behavior.

They do NOT receive an automatically higher empirical weight.

---

# 13. ONCHAIN

Example:

```text
Lookonchain
```

Predict primitives:

```text
exchange inflow
exchange outflow
whale accumulation
distribution
stablecoin flow
bridge flow
```

Do not assign generic:

```text
whale buy = LONG
```

Run event studies conditional on:

```text
asset
regime
flow destination
wallet type
size relative to liquidity
```

Reward:

```text
abnormal return
volatility response
flow persistence
ΔEV in strategies
```

---

# 14. STRUCTURAL / FUNDAMENTALS

This powers DEATH_TOKEN.

Inputs:

```text
dilution
FDV
emissions
unlocks
treasury selling
revenue
fees
users
liquidity
relative weakness
insider concentration
```

Evaluate slowly:

```text
1w
4w
12w
```

Rewards:

```text
cross-sectional rank IC
future relative underperformance
drawdown hazard
liquidity decay
DEATH_TOKEN ΔEV
```

Recent 2026 research reporting a dilution-related cross-sectional return effect makes dilution an economically justified primitive to test rather than an arbitrary feature.

---

# 15. ATTENTION / NARRATIVE / META

Outputs:

```text
narrative emerging
accelerating
crowded
exhausted
rotation A → B
```

Reward:

```text
future attention share
future volume share
cross-sectional rank movement
abnormal return
volatility
```

Then test whether:

```text
META
+
REGIME
+
TRADER CONFLUENCE
```

improves actual entries.

---

# 16. The hierarchy we ultimately want

This is where BEAR becomes powerful.

## Layer 1 — REGIME

```text
What type of market are we in?
```

Examples:

```text
Aporia
machine regime
macro
breadth
```

Produce:

```text
P(TREND)
P(CHOP)
P(RISK_ON)
P(RISK_OFF)
```

---

## Layer 2 — META

Conditional on regime:

```text
What is capital rewarding?
```

Examples:

```text
BTC
L1
AI
memes
privacy
DeFi
```

Produce:

```text
P(meta winning | regime)
```

---

## Layer 3 — ASSET SELECTION

Conditional on regime + meta:

```text
Which assets are leaders?
```

Combine:

```text
meme scouts
relative strength
attention
flows
smart-money positions
```

---

## Layer 4 — TRADE

Conditional on everything above:

```text
where/how do we enter?
```

Combine:

```text
Timeless
XO
order flow
OI/funding
levels
```

---

## Layer 5 — RISK

```text
Should this strategy receive capital?
```

Examples:

```text
DEATH_TOKEN ON/OFF
MEME_MOMENTUM ON/OFF
BTC_TACTICAL ON/OFF
FLOW_REVERSAL ON/OFF
```

That hierarchy is:

```text
REGIME
   ↓
META
   ↓
LEADERS
   ↓
TRADE
   ↓
EXECUTION
```

Exactly the structure we want.

---

# 17. Confluence

Never:

```text
5 bullish people = score 5
```

Instead:

```text
5 independent information lineages
```

Each event contributes:

```text
source primitive reliability
× contextual reliability
× novelty
```

If three people quote the same Lookonchain transfer:

```text
1 ONCHAIN OBSERVATION
+
3 INTERPRETATIONS
```

not four independent observations.

---

# 18. Online updating

Each source has specialist posteriors.

Example:

```text
Aporia:
    REGIME/TREND/BTC/3D
    REGIME/TREND/BTC/7D
    BREADTH/ALTS/7D

Timeless:
    DIRECTION/BTC/LONG/4H
    DIRECTION/BTC/SHORT/4H
    DIRECTION/BTC/SHORT/DOWN_REGIME/4H
```

Never:

```text
Aporia score = 0.86
```

---

# 19. Decay

Skill can disappear.

Apply time decay to evidence.

Recent observations count more than very old observations.

But store lifetime reputation separately.

Track:

```text
lifetime posterior
rolling posterior
prospective posterior
```

Large disagreement between them is a concept-drift warning.

---

# 20. Candidate acquisition policy

The next influencer is selected by:

```text
value_of_information =
primitive_importance
× primitive_uncertainty
× candidate_independence
× expected_event_density
× mechanism_strength
÷ acquisition_cost
```

Example:

If BEAR already has five tactical BTC traders but weak derivatives interpretation:

```text
sixth directional trader = LOW priority
excellent derivatives specialist = HIGH priority
```

Even if directional trader has more followers.

---

# 21. Canonical job model

Do not make `nohup` itself the architecture.

Every run gets:

```text
job_id
source_id
primitive
date range
hypothesis_id
code_sha
schema_version
extractor_version
dataset hashes
status
started_at
completed_at
stdout_path
stderr_path
output_hash
```

Then local execution can be:

```bash
nohup python -m bear.research.onboard \
  --source 0xaporia \
  --primitive regime_trend \
  --from 2026-08-01 \
  --to 2026-08-31 \
  --job-id ONBOARD-0XAPORIA-001 \
  > runs/ONBOARD-0XAPORIA-001.log 2>&1 &
```

But the job manifest is canonical.

The PID is not.

---

# 22. Aporia onboarding record

Commit this:

```json
{
  "source_id": "x:1292508532823252994",
  "handle": "0xaporia",

  "status": "RESEARCH_ONBOARDED",

  "raw_data": {
    "2026-08": "astronomer/data/backtest/raw/0xaporia_aug2026.json"
  },

  "primary_primitive": "REGIME_TREND",

  "secondary_primitives": [
    "ALT_BREADTH",
    "CROSS_SECTIONAL_MOMENTUM"
  ],

  "roles": [
    "STRATEGY_ACTIVATION",
    "STRATEGY_VETO",
    "ASSET_SELECTION"
  ],

  "empirical_weight": 0.0,

  "hypothesis":
    "Aporia identifies chop-to-trend changes and correctly emphasizes current leaders when market breadth is narrow.",

  "falsification":
    "No improvement over price/breadth-only regime model and no positive downstream strategy delta-EV.",

  "current_call_backtest_status": "INVALIDATED",

  "invalidated_reason":
    "August CALL extractor semantically inverted or misclassified multiple posts.",

  "required_evaluation_contract": "REGIME_TREND_V1"
}
```

---

# 23. Aporia August re-extraction

At minimum these events should be represented approximately as:

```text
2026-08-06
BTC
REGIME
RANGE/CHOP
explicit:
"Price grinding sideways, no real direction"

2026-08-20
GENERAL CRYPTO
TRADING_METHOD / TREND
NOT A CALL
trend-following payoff requires uncapped winners

2026-08-20
CRYPTO_BETA
TREND
BULLISH/TREND_CONTINUATION
not executable
"take the risk of buying the top"

2026-08-21
CRYPTO_BETA
REGIME
TRENDING/MOMENTUM

2026-08-21
ALTS
CROSS_SECTIONAL_SELECTION
PREFER_LEADERS / AVOID_LAGGARDS

late August
ALTS
BREADTH
NARROW / CAP_WEIGHTED_STRENGTH

2026-08-28
CRYPTO_BETA
TREND
BULLISH_CONTINUATION
NOT BEARISH CALL
breakout / escape velocity
```

These must be human-checked against the complete raw corpus.

---

# 24. Aporia's actual experiment

Pre-register:

```text
H0:
Aporia contains no incremental regime information.

H1:
Aporia regime/trend events improve prediction of
3d/7d trend persistence, transition state, or downstream
strategy activation relative to a price-only baseline.
```

Run:

### Experiment A — State

```text
baseline:
lagged price + volatility + breadth

candidate:
baseline + Aporia state
```

Score:

```text
Brier
log loss
```

---

### Experiment B — Trend persistence

When Aporia says TREND:

measure:

```text
future return / trailing volatility
directional efficiency
maximum drawdown
trend persistence at 1d/3d/7d
```

Compare to all contemporaneous periods where baseline regime was the same.

---

### Experiment C — Transition

When Aporia changes:

```text
CHOP → TREND
TREND → CHOP
RISK_ON → RISK_OFF
```

calculate:

```text
source transition timestamp
-
objective transition timestamp
```

Distribution gives:

```text
lead
coincident
lag
```

---

### Experiment D — Downstream PnL

This matters most.

Test Aporia as:

```text
TREND_STRATEGY activator
DEATH_TOKEN veto
ALT_MOMENTUM activator
```

Example:

```text
ALT_MOMENTUM baseline

vs

ALT_MOMENTUM only when
Aporia=TREND
```

Then:

```text
ΔEV
ΔSharpe
Δdrawdown
```

Aporia graduates only if incremental economics survive.

---

# 25. Current Aporia verdict

```text
SOURCE:
0xaporia

OLD LABEL:
high-win-rate directional trader

OLD LABEL STATUS:
REJECTED

NEW PRIMARY ROLE:
REGIME_TREND

SECONDARY:
ALT_BREADTH
CROSS_SECTIONAL_MOMENTUM

AUGUST DATA:
ENOUGH TO ONBOARD
NOT ENOUGH TO VALIDATE

GRAPH TRADING WEIGHT:
0

RESEARCH PRIOR:
HIGH

NEXT ACTION:
re-extract August using REGIME_TREND_V1
then run the four experiments above
```

That is a successful onboarding.

Finding that the previous test was wrong is part of the protocol working.

---

# 26. Then onboard Timeless

The second source should deliberately be different.

```text
0xaporia
→ REGIME protocol

Timeless
→ TACTICAL TRADER protocol
```

That validates that BEAR truly supports heterogeneous specialists.

After that:

```text
meme scout
→ CROSS_SECTIONAL protocol

52kskew
→ ORDER_FLOW protocol

Laevitas
→ DERIVATIVES protocol

Lookonchain
→ ONCHAIN protocol
```

Once those five fundamentally different sensor types work, the architecture is real.

---

# 27. Final invariant

For every influencer BEAR must answer:

```text
WHY DID WE ADD THEM?
    ↓
WHAT PRIMITIVE DO THEY MEASURE?
    ↓
WHAT EXACTLY COUNTS AS A SIGNAL FOR THIS PRIMITIVE?
    ↓
WHAT OUTCOME WOULD MAKE IT USEFUL?
    ↓
WHAT OUTCOME WOULD FALSIFY IT?
    ↓
WHAT SIMPLE BASELINE MUST IT BEAT?
    ↓
WHAT DOES IT ADD TO THE EXISTING GRAPH?
    ↓
HOW DOES THAT ADDITION CHANGE PNL?
```

Only then does the source receive weight.

The score is never:

"smart guy = 1.4"

The score is:

"this source has empirically demonstrated conditional information value for this primitive in this state."

This also gives us the beautiful hierarchy you described. **Regime consensus determines what game is playable; meta/narrative identifies where capital is flowing; scouts and relative strength determine the leaders; traders determine entries; flow/derivatives decide whether to confirm or veto; structural information determines slower strategies like DEATH_TOKEN.**

Two research details reinforce this architecture. First, 2026 work surveying regime methods argues that financial research badly conflates incompatible meanings of "regime", so BEAR absolutely should define the prediction/reward contract explicitly rather than asking an LLM vaguely whether someone "predicted the regime." ([SSRN][2]) Second, crypto momentum evidence is state-sensitive and highly dependent on realistic assumptions; a 2026 revision finds stronger time-series momentum evidence but much weaker cross-sectional results under realistic liquidation/path assumptions, while another 2026 study specifically finds cross-sectional dispersion relevant to momentum breakdown. ([SSRN][3]) That is precisely why `MEME_SCOUT`, `TREND_REGIME`, and `TACTICAL_TRADE` need different tests.

For the next entrant I would deliberately choose **Timeless** and run the tactical-trader contract. After Aporia + Timeless work end-to-end, add one genuine memecoin/alt scout. Those three establish the first full chain:

**Aporia: is trend regime active? → meme/meta scout: what is winning? → Timeless: where do we actually enter?**

That is already recognizably the BEAR graph rather than a Twitter leaderboard.

[1]: https://arxiv.org/abs/0902.4127 "https://arxiv.org/abs/0902.4127"
[2]: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6493762 "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6493762"
[3]: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4675565 "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4675565"

---

*Timestamp: 2026-09-07*
*Source: User message to BEAR agent*
*Saved word for word. No summarization. No condensation.*
