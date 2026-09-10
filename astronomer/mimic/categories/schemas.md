# Canonical post schemas v1.0 — strict on shape, lenient on trading content

Every ingested post becomes exactly one `MimicPost`. Validators reject rows that
fail REQUIRED; PREFERRED gaps warn; OPTIONAL gaps are fine. Philosophy from the
data: only 19% of calls state explicit levels and 6.1 numbers + 94% charted is
the CALL signature — so levels/targets stay OPTIONAL, inferrable from the chart
or price structure. Never force a post into a richer type than its evidence
(Rule: source fidelity; Skew stays STATE, never a fake CALL).

Base (`MimicPost`, all archetypes):

| Field | Req | Type | Rule |
|---|---|---|---|
| `post_id` | REQUIRED | string (Snowflake) | immutable, dedupe key |
| `handle` / `author_id` | REQUIRED | string | author_id canonical |
| `published_at` | REQUIRED | ISO-8601 UTC | ordering + point-in-time joins |
| `archetype` | REQUIRED | enum §1–9 | single label, classifier + audit trail |
| `text` | REQUIRED | string (raw, full) | never truncated (strict=200ch trap) |
| `chart_ref` | REQUIRED iff charted | rel path `data/media/…` | must exist on disk |
| `evidence` | REQUIRED | span[] | every extracted field points at text/chart region |
| `regime` / `market_snapshot` | PREFERRED | object | 1m/5m snapshot id, null if unavailable |

## 1. CALL — "buy X now/at P [, sell at T] [, invalid below I]"

REQUIRED: `asset`, `direction` ∈ {LONG, SHORT}, `entry_basis` ∈ {NOW, LEVEL,
UNKNOWN default} (measured: inferrable 60% — UNKNOWN is honest, not a gap).
OPTIONAL: `entry_range[2]`, `targets[]`, `invalidation`, `horizon_h`,
`position` ∈ {OPEN, HYPOTHETICAL, UNKNOWN default}.
RULES: no asset → recovery pipeline (entities/cashtag/chart) → still none → demote
to LEAN_TAC, never guess. No direction → not a CALL. Numbers served must verify
against market state (fail-closed).

## 2. EXIT — "took 75% off at 36, +31.5%"

REQUIRED: `asset`, `exit_zone` (price or params), `fraction` ∈ {PARTIAL, FULL, UNKNOWN}.
OPTIONAL: `entry_ref` (post_id if linked), `pnl_pct`, `reason`.
Marker: `closed` (143× lift). Rarest type — weight accordingly.

## 3. COND — "if 72k reclaims I'll turn bullish"

REQUIRED: `asset`, `trigger` (price/event condition, machine-checkable),
`action` (what happens on trigger).
OPTIONAL: `invalidation`, `expiry`.
Votes ONLY on trigger activation (conditional-vote pattern).

## 4. VERDICT — "bull market because X"

REQUIRED: `scope` ∈ {ASSET, SECTOR, MARKET}, `verdict` ∈ {BULL, BEAR, RANGE},
`because[]` (≥1 reason string).
OPTIONAL: `horizon_h`. Reason quality > verdict accuracy for training.

## 5. MACRO_STATE — "CPI hot, yields up"

REQUIRED: `topics[]` (≥1: FOMC/CPI/DXY/yields/…).
OPTIONAL: `stance`, `event_date`, `surprise` (vs consensus).
Feeds regime features, never votes.

## 6. FLOW_DATA — "ETF -$203M, funding +0.01%, OI up"

REQUIRED: `metric` ∈ {ETF_FLOW, FUNDING, OI, LS_RATIO, CVD, WHALE, UNLOCK, LIQ, HACK},
`values` (number + unit + venue?).
OPTIONAL: `asset`, `window`. Mechanical rows may lack assets — allowed here ONLY.

## 7. LEAN_TAC — directional lean, chart REQUIRED

REQUIRED: `asset`, `lean` ∈ {LONG, SHORT}, `chart_ref` (no chart → CHATTER).
RULE: text "looks good here" is unlearnable without pixels — chart-paired
training only. Promo-spam (`bitget/vip/cfd`) → SPAM, never LEAN.

## 8. EDU — reasoning teachers (Cred pattern)

REQUIRED: `concepts[]`. OPTIONAL: assets. Trains reasoning corpus, never votes,
never backtested as calls.

## 9. CHATTER — drop bucket with reason

REQUIRED: `reason` ∈ {REPLY, NO_NUMBERS, SPAM, OFF_TOPIC}.
RULE: `numbers == 0` → CHATTER (measured 0.0/post over 3,645). Excluded from
backfills; monitor-only at most.

## Sizes (measured, Jul+Aug 7,374 posts)

CALL 253 · EXIT 29 · COND 200 · VERDICT 143 · MACRO 420 · FLOW 214 ·
LEAN 2,470 (tactical 13% / data 80% / spam 7%) · CHATTER 3,645.

## Relation to `schemas.py`

Additive only: `MarketEvent` gains `call_kind` ∈ {STRICT, CONDITIONAL, STATE}
(panel directive) and optional `targets[]/invalidation/trigger/chart_ref`;
existing CALL/VIEW/RETROSPECTIVE kinds untouched. Implement in code as agent
task; this document is the contract. JSON Schema mirror: `schema.json` (this dir).
