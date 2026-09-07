# BEAR Influencer Learning Protocol v1

*The binding architecture for onboarding and evaluating information sources.*

---

## 1. Core Model

An influencer is NOT a strategy.

An influencer is a noisy sensor of one or more market primitives.

The hierarchy is:

```
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

```
Aporia → REGIME / TREND / BREADTH
Timeless → TACTICAL DIRECTION / ENTRIES
52kskew → ORDER FLOW
Laevitas → DERIVATIVES / CROWDING
Lookonchain → ONCHAIN CAPITAL FLOW
Binance trader → REAL-MONEY POSITIONING
Tokenomist / BEAR fundamentals → STRUCTURAL SUPPLY
```

They must not share the same reward function.

---

## 2. Do Not Use RL Where Ordinary Learning Is Sufficient

Influencer reputation is initially a **full-information online expert problem**.

After the relevant horizon passes, BEAR can score every prediction, including predictions it did not trade.

Therefore use:

```
Bayesian updating
or
discounted exponential expert weights
```

conditioned on:

```
source × primitive × asset/scope × regime × horizon × event subtype
```

Use a "sleeping expert" formulation:

```
If source says nothing → expert inactive.
If source speaks outside its validated specialty → expert inactive.
If source emits relevant event → expert participates.
```

RL is reserved for:

```
strategy activation
portfolio allocation
position sizing
capital/risk allocation
```

where actions affect the realized portfolio path.

---

## 3. Source Lifecycle

Every entrant has exactly these states:

```
DISCOVERED → SAMPLED → RESEARCH_ONBOARDED → VALIDATING → VALIDATED → SHADOW → ACTIVE → DOWNWEIGHTED → RETIRED
```

No source jumps from discovery to trading weight.

`RESEARCH_ONBOARDED` means:
- we know why we want them
- we know which primitive they supposedly measure
- we possess raw data
- a falsifiable evaluation contract exists

It does NOT mean they have alpha.

---

## 4. Entrant-Only Processing

When adding source N+1: DO NOT recompute sources 1…N.

Frozen shared assets:
- posts schema
- market_state(t)
- market outcomes
- regime labels
- price histories
- cost model
- existing source event tables
- existing source posteriors

Run only: NEW SOURCE → raw acquisition → normalization → primitive classification → extraction → QA → outcomes → baselines → comparison → posterior update → confluence recalculation.

Full historical rebuild occurs ONLY when schema/extractor/outcome semantics/cost model change materially.

---

## 5. Every Entrant Requires a Hypothesis BEFORE Outcome Inspection

```json
{
  "source": "0xaporia",
  "primary_primitive": "REGIME_TREND",
  "secondary_primitives": ["ALT_BREADTH", "CROSS_SECTIONAL_MOMENTUM"],
  "hypothesis": "Aporia identifies chop-to-trend changes and emphasizes current leaders when breadth is narrow.",
  "mechanism": "Trend persistence and cross-sectional concentration affect which strategies and assets receive risk.",
  "expected_role": ["STRATEGY_ACTIVATION", "STRATEGY_VETO", "ASSET_SELECTION"],
  "falsification": "No improvement over price/breadth-only regime model and no positive downstream strategy delta-EV."
}
```

---

## 6-16. Primitive Reward Contracts

### REGIME / TREND (0xaporia)
- Output: RISK_ON, RISK_OFF, TREND_UP, TREND_DOWN, RANGE, TRANSITION
- Baseline: lagged price + volatility + breadth
- Reward: Brier skill, log-loss improvement, transition lead/lag, ΔEV of downstream strategy gating
- Falsification: source does not improve baseline regime forecast AND does not improve downstream strategy EV

### TACTICAL TRADER (Timeless)
- Output: LONG, SHORT, CONDITIONAL, ENTRY, STOP, TARGET, REDUCE, EXIT
- Reward: net PnL, expectancy, profit factor, MFE/MAE, R multiple, latency sensitivity
- Benchmark: always long, momentum, reversal, regime, random regime-matched entry
- Main quantity: ΔEV(source call | baseline market state)

### MEME / ALT SCOUT
- Output: TOKEN, POSITIVE/NEGANT VIEW, TIMESTAMP, CONVICTION
- Reward: rank IC, precision@K, top-decile winner hit rate, excess return, liquidity-adjusted PnL
- Falsification: influencer picks must outperform simple momentum/attention

### LEVEL / MARKET STRUCTURE (Trader_XO)
- Output: support/resistance levels with conditions
- Reward: P(rejection|touch), P(break|touch), MFE/MAE after interaction
- Falsification: must penalize level density

### ORDER FLOW (52kskew, exitpump)
- Output: continuation, reversal, volatility expansion, absorption, veto
- Reward: ΔEV of adding flow veto to existing strategy
- Key: flow source can be valuable with terrible standalone direction accuracy

### DERIVATIVES (Laevitas)
- Output: funding crowding, OI expansion, basis, liquidations, squeeze risk
- Reward: Did interpretation add information beyond raw funding/OI data?
- Baseline: BEAR's raw funding + OI + price + regime

### REAL POSITION (Binance/HL wallets)
- Output: OPEN_LONG, ADD, REDUCE, CLOSE, FLIP
- Reward: forward abnormal return, realized position PnL, asset×regime×horizon expectancy
- Prior: stronger than tweets (revealed behavior), but empirical weight must still be learned

### ONCHAIN (Lookonchain)
- Output: exchange inflow/outflow, whale accumulation/distribution
- Reward: abnormal return, volatility response, flow persistence, ΔEV
- Must be conditional on asset, regime, flow destination, wallet type, size

### STRUCTURAL / FUNDAMENTALS (Tokenomics)
- Output: dilution, emissions, unlocks, revenue, fees, users
- Evaluate at: 1w, 4w, 12w horizons
- Reward: cross-sectional rank IC, future relative underperformance, DEATH_TOKEN ΔEV

### ATTENTION / NARRATIVE / META
- Output: narrative emerging, accelerating, crowded, exhausted, rotation
- Reward: future attention share, volume share, cross-sectional rank movement
- Test: META + REGIME + TRADER CONFLUENCE improves actual entries

---

## 17-19. Confluence, Online Updating, Decay

### Confluence
Never: 5 bullish people = score 5
Instead: 5 independent information lineages, each weighted by source primitive reliability × contextual reliability × novelty

### Online Updating
Each source has specialist posteriors at (source × primitive × asset × regime × horizon × subtype). Never collapse to single score.

### Decay
Apply time decay to evidence. Track lifetime, rolling, and prospective posteriors. Large disagreement = concept-drift warning.

---

## 20. Candidate Acquisition Policy

```
value_of_information = primitive_importance × primitive_uncertainty × candidate_independence × expected_event_density × mechanism_strength ÷ acquisition_cost
```

---

## 21. Canonical Job Model

Every run gets: job_id, source_id, primitive, date range, hypothesis_id, code_sha, schema_version, extractor_version, dataset hashes, status, started_at, completed_at, stdout_path, stderr_path, output_hash.

```bash
nohup python -m bear.research.onboard \
  --source 0xaporia \
  --primitive regime_trend \
  --from 2026-08-01 \
  --to 2026-08-31 \
  --job-id ONBOARD-0XAPORIA-001 \
  > runs/ONBOARD-0XAPORIA-001.log 2>&1 &
```

The job manifest is canonical. The PID is not.

---

## 22-25. 0xaporia Onboarding Record

See: `research/source_cards/0xaporia.json`

Previous label "high-win-rate directional trader" is REJECTED.

New role: REGIME_TREND specialist with secondary ALT_BREADTH and CROSS_SECTIONAL_MOMENTUM.

Required evaluation: REGIME_TREND_V1 (four experiments: state prediction, trend persistence, transition lead/lag, downstream PnL).

---

## 26. Onboarding Order

1. 0xaporia → REGIME protocol (first)
2. Timeless → TACTICAL TRADER protocol (second, validates heterogeneous specialists)
3. Memecoin scout → CROSS_SECTIONAL protocol
4. 52kskew → ORDER_FLOW protocol
5. Laevitas → DERIVATIVES protocol
6. Lookonchain → ONCHAIN protocol

After Aporia + Timeless + memecoin scout: first full chain:
**Aporia: is trend active? → scout: what is winning? → Timeless: where do we enter?**

---

## 27. Final Invariant

For every influencer BEAR must answer:

```
WHY DID WE ADD THEM?
WHAT PRIMITIVE DO THEY MEASURE?
WHAT EXACTLY COUNTS AS A SIGNAL FOR THIS PRIMITIVE?
WHAT OUTCOME WOULD MAKE IT USEFUL?
WHAT OUTCOME WOULD FALSIFY IT?
WHAT SIMPLE BASELINE MUST IT BEAT?
WHAT DOES IT ADD TO THE EXISTING GRAPH?
HOW DOES THAT ADDITION CHANGE PNL?
```

Only then does the source receive weight.

The score is never: "smart guy = 1.4"
The score is: "this source has empirically demonstrated conditional information value for this primitive in this state."

---

*Protocol version: 1.0 — 2026-09-07*
