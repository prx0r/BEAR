# BEAR Canonical Protocol — Full Message

*Word-for-word from user, 2026-09-07. Timestamped.*

---

The recent push is moving in the right direction, but I would stop adding more backtest results until the **canonical evaluator** is fixed.

The biggest finding from reviewing HEAD is that the new semantic layer is ahead of the old backtester. The evidence-grounded extractor is a large improvement, but the 37 "properly classified" calls still have many `asset: null` records while being assigned BTC entry prices. The current `backtest.py` still defaults missing assets to BTC, still maps HYPE to BTC, enters on the signal candle, and stores multi-asset outcomes in a flat horizon dictionary.

There is also a unit error in the reporting layer: a raw return such as `0.00338` is **0.338%**, not `0.003%`.

And the latest ranking should be deleted/reclassified as provisional. It ranks `lookonchain` using an older 67% result even though the newer semantic CALL run does not evaluate it, ranks Astronomer highly partly because of signal density, and omits `0xaporia` despite the newer run reporting a tiny-sample 100%. Signal density is not alpha.

More importantly, **do not skip `exitpumpBTC` or `laevitas1` because they had poor 4h directional-call accuracy**. They represent different primitives. A flow source may be excellent as a veto or regime feature without being useful as a standalone trader, and a derivatives source may operate at 24h rather than 4h. Current market-microstructure research supports exactly this distinction: order flow has measurable predictive information in crypto, but its effect varies by horizon and requires separating persistent flow from mechanically contemporaneous price impact. On-chain signals are also asset- and flow-type-specific rather than generically bullish/bearish.

This is the final architecture I would give the coding agent.

# BEAR CANONICAL PROTOCOL

## Mission

BEAR is not an influencer-ranking engine.

BEAR is an evidence system whose job is to determine:

```
WHAT information exists
→ WHICH primitive it measures
→ WHEN that information is useful
→ WHETHER it adds information beyond what BEAR already knows
→ HOW that information affects executable PnL
→ WHICH repeatable combinations can be crystallized into strategies
→ WHEN each strategy should be active
```

The fundamental object is therefore not:

```
trader → win rate
```

It is:

```
source
× primitive
× asset
× regime
× event type
× horizon
→ marginal economic value
```

---

# PART I — FREEZE THE CURRENT BAD BACKTEST

Do not publish another account ranking until these are fixed.

Remove immediately:

```
assets defaulting to ["BTC"]
HYPE → BTCUSDT
unknown asset → BTC
same-candle entry
flat multi-asset outcome dictionary
unversioned return units
ranking by signal density
ranking by raw tiny-sample win rate
reply filtering before semantic extraction
```

Unknown means `UNKNOWN`.
Missing data means `NO_DATA`.
Neither means BTC.

One EventOutcome = one event_id × one asset × one execution interpretation.

---

# PART II — AUGUST IS THE EXEMPLAR LAB

August is where we validate extraction, understand behaviour, map sources to primitives, understand regime transitions, discover relationships, create candidate strategies, and debug the graph.

Every experiment on August is permanently logged.

Once a strategy has been influenced by August results, August can never validate that strategy.

---

# PART III — INGEST EVERY POST

Do not start with "remove replies" or "find long/short keywords."

Start with the complete source history. Keep replies — they contain stop updates, partial exits, invalidations, clarifications, new targets.

Raw data is immutable.

---

# PART IV — MARKET EVENT ONTOLOGY

Every useful post becomes one or more `MarketEvent`s.

semantic_kind: CALL, VIEW, OBSERVATION, INTERPRETATION, RETROSPECTIVE, NON_SIGNAL

call_state: DIRECT, CONDITIONAL, UPDATE, REDUCE, EXIT, NONE

stance: BULLISH, BEARISH, NEUTRAL, UNKNOWN

provenance: EXPLICIT, CONTEXT_RESOLVED, INFERRED, UNKNOWN

---

# PART V — PRIMITIVES

P1 REGIME, P2 PRICE_STRUCTURE, P3 ORDER_FLOW_LIQUIDITY, P4 DERIVATIVES_POSITIONING, P5 REAL_MONEY_POSITIONING, P6 ONCHAIN_CAPITAL_FLOW, P7 STRUCTURAL_SUPPLY_FUNDAMENTALS, P8 CATALYST_ATTENTION

---

# PART VI — EXTRACT PRIMITIVES, NOT JUST TRADES

---

# PART VII — EVIDENCE-GROUNDED EXTRACTION

Every field must have evidence span. If no evidence → null.

---

# PART VIII — GOLD SET

Build 250 stratified examples. Measure precision/recall separately.

---

# PART IX — BINARY DATA QUALITY GATES

Every run stops on violations.

---

# PART X — POINT-IN-TIME MARKET SNAPSHOT

For every event, independently capture market state.

---

# PART XI — SIMPLE REGIME MODEL

UP / DOWN / RANGE + NORMAL_VOL / HIGH_VOL. Use only lagged data.

---

# PART XII — THREE DIFFERENT BACKTESTS

A. TRADE BACKTEST (CALL + DIRECT)
B. EVENT STUDY (VIEW, OBSERVATION, INTERPRETATION)
C. INCREMENTAL FEATURE TEST (marginal value)

---

# PART XIII — ACTUAL TRADE BACKTEST

First executable market observation after publication. Sensitivity: +1m, +5m, +15m, +60m.

---

# PART XIV — REPLAY THREADS CHRONOLOGICALLY

Each post is a new event. Never let future posts inform past trades.

---

# PART XV — PNL

Store raw returns as decimal. 0.00338 = 0.338%. Never silently combine gross and net.

---

# PART XVI — PNL IS MORE THAN WIN RATE

N, win rate, mean net return, median net return, profit factor, MFE, MAE, expected value, drawdown, tail loss, latency sensitivity, turnover, cost sensitivity.

---

# PART XVII — REMOVE MARKET BETA

For alt events: abnormal_return = asset_return - rolling_beta × BTC_return.

---

# PART XVIII — HIGH-ALPHA EVENTS

Normalize by expected volatility: alpha_z = signed abnormal forward return / pre-event expected volatility.

---

# PART XIX — HOW DID THEY HANDLE AUGUST?

Stance timeline per source. Measure lead/lag, wrong-way persistence, transition accuracy, adaptation speed.

---

# PART XX — SOURCE REPORT CARD

Standardized report per source with activity, event_mix, primitive_mix, trade_calls, views, regime, highest_value, data_quality.

---

# PART XXI — SOURCE REPUTATION

Unit: source × primitive × asset × direction × regime × horizon. Bayesian shrinkage for small samples.

---

# PART XXII — MARGINAL VALUE

ΔEV = EV_with_source - EV_base. That's what matters. Not raw win rate.

---

# PART XXIII — INFORMATION COEFFICIENT

IC = correlation(signal_score, future_return). Track stability through time.

---

# PART XXIV — SOURCE INDEPENDENCE

Track information_cluster_id, origin_source, quote/repost, semantic similarity.

---

# PART XXV — HOW TO ADD NEW PEOPLE

Ask: "Which primitive is BEAR currently least informed about?" Not "who is the next best trader?"

---

# PART XXVI — THEORY PRIOR

Every candidate requires a mechanism before acquisition.

---

# PART XXVII — ACQUISITION SCORE

primitive_gap × mechanism_strength × independence × event_density × timeliness × historical_availability ÷ acquisition_cost

---

# PART XXVIII — TWO-STAGE SOURCE ONBOARDING

Stage 1: SAMPLE (20-50 posts)
Stage 2: MARGINAL BACKTEST (baseline vs baseline + candidate)

---

# PART XXIX — EXPANSION SCORE

primitive_gap × independence × extraction_quality × usable_coverage × marginal_information × stability ÷ cost

---

# PART XXX — CURRENT SOURCE PRIORITY

REGIME: 0xaporia
TACTICAL: Timeless, XO, astronomer, CryptoBheem
ORDER_FLOW: exitpumpBTC, 52kskew
DERIVATIVES: laevitas
REAL_POSITIONS: Binance/Hyperliquid
ONCHAIN: lookonchain
STRUCTURAL: BEAR native

---

# PART XXXI — SOURCES AS PNL COMPONENTS

Seven distinct ways a source creates money:
1. DIRECTION, 2. ENTRY, 3. EXIT, 4. VETO, 5. POSITION SIZE, 6. ASSET SELECTION, 7. STRATEGY ACTIVATION

---

# PART XXXII — EXPERIMENT LEDGER

Append-only. Every experiment recorded with hypothesis, mechanism, falsification, results, decision.

---

# PART XXXIII — MULTIPLE-TESTING DEFENCE

Use Deflated Sharpe Ratio and PBO. Never advertise the prettiest result among 500 attempts.

---

# PART XXXIV — DATA DIRECTORY

Canonical structure with raw/, canonical/, gold/, research/, strategies/, reports/

---

# PART XXXV — EVERY DATUM GETS A MANIFEST

Dataset ID, created_at, raw_inputs, raw_hashes, extractor_version, schema_version, git_sha, row_count, validation_checks.

---

# PART XXXVI — BASELINE MODELS

Always long, always short, random direction, recent momentum, BTC regime only, funding only, OI only. Source must beat baselines.

---

# PART XXXVII — CRYSTALLIZATION SEARCH

Only test combinations that express plausible trading mechanisms.

---

# PART XXXVIII — DEATH_TOKEN EXAMPLE

death_hazard × liquidity × (1 - squeeze_risk). Activation: death_hazard high AND BTC regime != strong uptrend AND liquidity sufficient AND funding not catastrophically negative.

---

# PART XXXIX — AN X-DERIVED STRATEGY EXAMPLE

Register hypothesis, define exact predicates, test, crystallize if promising.

---

# PART XL — CRYSTALLIZATION GATES

[ ] economic mechanism documented
[ ] all data point-in-time
[ ] deterministic rules
[ ] fixed entry/exit
[ ] costs included
[ ] baseline defined
[ ] development experiments logged
[ ] no data-integrity failures

---

# PART XLI — VALIDATION

August is development. Use other periods for historical robustness. Start prospective shadow immediately.

---

# PART XLII — MULTIPLE-TESTING DEFENCE

Maintain total_hypotheses_tested. Use Deflated Sharpe Ratio and PBO.

---

# PART XLIII — SELECTION POLICY FOR NEW SOURCES

10 questions from "which primitive gap?" to "should we buy more history?"

---

# PART XLIV — ACTIVE LEARNING LOOP

Graph uncertainty → primitive gap → candidate source → mechanism + falsification → cheap sample → extract + validate → marginal test → update posterior → register hypothesis → backtest → crystallize → shadow → activate.

---

# PART XLV — DASHBOARD SHOULD CHANGE

Delete "TOP TRADERS." Replace with Sources, Primitives, Strategies, Research Queue.

---

# PART XLVI — DO THIS NOW

24-step implementation order from "Replace old backtester" to "Begin prospective shadow validation."

---

# DEFINITION OF SUCCESS

At any moment BEAR must answer:
- Why is this source useful?
- Why is this graph edge present?
- Why did this strategy activate?
- Why was this new person added?

Nothing important may terminate in "because the LLM thought so" or "because they had an 86% win rate."

---

*Timestamp: 2026-09-07*
*Source: User message to BEAR agent*
