# BEAR August Exemplar Backtesting & Graph Crystallization Protocol v1

*Word-for-word from user, 2026-09-07. Timestamped.*

---

The latest push is directionally correct. It identifies the real bottleneck: **the backtester is currently mostly testing the extractor, not the traders.** The new methodology correctly calls out semantic false positives, missing levels, latency/cost assumptions, retrospective posts, conditionals and thread context.

There are three additional hard issues I would fix before trusting August at all:

* **Never default an unknown asset to BTC.** The current `Signal` schema defaults `asset="BTC"`, and the historical backtester explicitly maps `HYPE → BTCUSDT` as a fallback. That can manufacture apparent prediction performance.
* **One asset × one event × one outcome.** The current August data includes multi-asset records and still contains identical duplicate rows.
* **Do not throw away observations/interpretations.** They should not be scored as executed trades, but they absolutely should be backtested as graph features.

The web research strongly supports using evidence-grounded extraction rather than trusting an LLM's fluent JSON. Recent ACL work finds that forcing verification against explicit source spans improves hallucination detection; another 2026 benchmark finds multi-stage claim → evidence → verification pipelines materially outperform one-shot LLM judging. Clinical extraction systems use the same useful pattern: extracted values are returned together with source locations so errors can be traced. There is also a particularly relevant warning: LLMs sometimes "correct" source material rather than faithfully extracting it, so **source fidelity must outrank what the model thinks is true.**

For the financial side, August should explicitly be treated as a **development/exemplar month**, not an OOS proof month. Backtest overfitting is especially easy when you inspect many sources, horizons and combinations and then select the winner; proper chronological holdouts and a timestamped record of hypotheses are the correct defense.

---

## 0. Objective

August 2026 is the development month.

For every source, answer:

1. How active were they?
2. What kinds of information did they produce?
3. When did they make genuinely actionable calls?
4. When were they merely expressing a directional view?
5. What objective market observations did they surface?
6. How did their stance change as the market regime changed?
7. Did they anticipate important moves or react afterward?
8. Which observations added useful information beyond the market state BEAR already knew?
9. Can recurring combinations be turned into a precise, executable strategy?
10. Can that strategy survive untouched out-of-sample data?

The product is not a trader leaderboard.

The product is:

`source → typed evidence → conditional predictive value → graph edge → crystallized strategy`

---

## 1. Keep the ontology small

Do not invent 30 post classes.

Every market-relevant post produces one or more `MarketEvent`s.

### semantic_kind

Exactly one:

* `CALL`
* `VIEW`
* `OBSERVATION`
* `INTERPRETATION`
* `RETROSPECTIVE`
* `NON_SIGNAL`

### call_state

* `DIRECT`
* `CONDITIONAL`
* `UPDATE`
* `EXIT`
* `NONE`

### target_variable

* `PRICE_DIRECTION`
* `VOLATILITY`
* `FUNDING`
* `OPEN_INTEREST`
* `ORDER_FLOW`
* `SPOT_FLOW`
* `PERP_FLOW`
* `BASIS`
* `LIQUIDATIONS`
* `LIQUIDITY`
* `WHALE_POSITIONING`
* `ETF_FLOW`
* `TOKEN_SUPPLY`
* `RELATIVE_STRENGTH`
* `VALUATION`
* `REGIME`
* `NARRATIVE`
* `OTHER`

---

## 2. Canonical raw-post schema

```json
{
  "post_id": "x:123456",
  "provider_post_id": "123456",
  "author_id": "immutable-x-user-id",
  "author_handle_observed": "Trader_XO",
  "created_at": "2026-08-14T13:22:11Z",
  "observed_at": "2026-08-14T13:23:02Z",
  "text": "raw exact post text",
  "text_sha256": "...",
  "conversation_id": "...",
  "reply_to_post_id": null,
  "quoted_post_id": null,
  "media": [],
  "raw_blob_path": "...",
  "ingestion_version": "x-v2"
}
```

---

## 3. Canonical extracted-event schema

```json
{
  "event_id": "evt_...",
  "post_id": "x:123456",
  "semantic_kind": "CALL",
  "call_state": "DIRECT",
  "target_variable": "PRICE_DIRECTION",
  "asset": "BTC",
  "direction": "BULLISH",
  "timeframe": {"value": "4h", "explicit": true},
  "entry": {"type": "MARKET", "price": null, "low": null, "high": null},
  "stop": null,
  "targets": [],
  "condition": null,
  "conviction_language": "high",
  "relation": {"parent_event_id": null, "supersedes_event_id": null},
  "evidence": [{"field": "direction", "post_id": "x:123456", "quote": "Long BTC here", "start_char": 0, "end_char": 13}],
  "extraction": {"model_version": "...", "schema_version": "2.0", "status": "VERIFIED"}
}
```

---

## 4. Two evaluation lanes

### Lane A — Trade backtesting
Only `CALL + DIRECT` and triggered `CALL + CONDITIONAL` become simulated trades.

### Lane B — Information backtesting
`VIEW`, `OBSERVATION` and `INTERPRETATION` are graph evidence evaluated against future market states.

---

## 5. Regime classification

Build regime independently from market data:

```python
if close > EMA50 and EMA20 > EMA50 and 24h_return > 0:
    trend = "UP"
elif close < EMA50 and EMA20 < EMA50 and 24h_return < 0:
    trend = "DOWN"
else:
    trend = "RANGE"

vol = "HIGH" if realized_vol > trailing_90th_percentile else "NORMAL"
```

Regime transition requires 3 consecutive 4h observations.

---

## 6. Evidence-grounded extraction

Every non-null factual field must include an exact supporting span from the source post.

If the extractor cannot point to the supporting text:

`value = null`

Do not let the model fill gaps.

Source fidelity must outrank what the model thinks is true.

---

## 7. Execution timing

Do not arbitrarily select one-hour latency.

For explicit market calls produce a latency sensitivity table:
- next available 1m bar
- +5m, +15m, +60m

If the strategy only works at impossible execution latency, reject it.

---

## 8. Costs

Every simulated trade must have:
- fee_bps
- slippage_bps
- funding

Results contain gross_return AND net_return. Never just one.

---

## 9. Deduplication invariant

`UNIQUE(event_id, asset)` must hold.

Duplicate event → pipeline FAIL. Not warning. FAIL.

---

## 10. Gold extraction benchmark

Before trusting August:

Manually label ~200-300 representative posts.

Measure:
- semantic_kind precision/recall
- direction precision/recall
- asset precision/recall
- numeric-level precision/recall

For executable trade fields optimize **precision over recall**.

---

## 11. Binary release gates

Before August performance numbers are valid:

```
[ ] 100% raw posts have canonical IDs
[ ] 100% have immutable author_id
[ ] 100% have created_at
[ ] 0 default BTC assets
[ ] 0 symbol fallbacks
[ ] 0 duplicate event outcomes
[ ] 0 future-thread leakage
[ ] every explicit numeric field has evidence
[ ] every direct direction has evidence
[ ] every outcome maps to exactly one asset
```

---

## 12. Statistical treatment

Report:
```
n = 7
wins = 6
posterior directional accuracy
credible interval
median signed return
bootstrap interval
```

Small samples: Bayesian shrinkage toward domain baseline.

Source reputation conditional on:
```
source × target_variable × asset × regime × horizon
```

---

## 13. Crystallized strategy schema

```yaml
id: DEATH_TOKEN
version: 1.0
thesis: structurally decaying tokens underperform when market conditions do not overwhelm token-specific weakness
inputs: [death_score, btc_regime, funding_state]
activation:
  all:
    - death_score >= 0.75
    - btc_regime != UPTREND
    - funding_state != EXTREME_NEGATIVE
entry:
  side: SHORT
  timing: next_valid_execution
exit:
  conditions:
    - death_score < 0.50
    - btc_regime == UPTREND
risk:
  risk_per_trade: 0.01
  max_positions: 5
status: CRYSTALLIZED
```

---

## 14. Minimal implementation sequence

1. Kill current invalid assumptions (asset defaults, duplicates)
2. Introduce schema v2
3. Build evidence-grounded extractor
4. Build deterministic validator
5. Build gold set (200-300 posts)
6. Measure extractor
7. Re-extract August from raw corpus
8. Build August regime timeline
9. Backtest direct calls
10. Backtest views/observations
11. Generate standardized source cards
12. Generate hypothesis registry
13. Crystallize only simple candidates
14. Lock and test out of sample

---

## 15. Final invariant

At any point BEAR must be able to answer:

> Why does this graph edge exist?

with:

```
these exact raw posts
→ these exact quoted spans
→ this extraction version
→ these exact typed events
→ this exact point-in-time market state
→ these exact future outcomes
→ this measured conditional relationship
```

No undocumented intuition exists between those steps.

---

*Timestamp: 2026-09-07*
*Source: User message to BEAR agent*
