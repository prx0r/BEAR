# PIPELINE — one deterministic path: raw posts → trading signals + charts

`python3 -m mimic.pipeline --handles astro,timeless,xo,bheem --seed seed1.4`
runs every stage in order, verifies hashes, writes one run receipt. Same inputs +
same code = byte-identical outputs, or the run FAILS loudly. No independent runs.

## Stages (each declares inputs → outputs + sha256)

0. INGEST — raw 2yr JSONs + prices + media on disk? FAIL if any handle missing.
   Out: manifest of row counts + date spans.
1. LABEL — events (dedupe by post_id) → strict → outcomes (canonical backtest) →
   round-trips → levels. Out: counts + label-coverage table.
2. TRAIN — hurdle models per handle (activity, direction, level-grid) with seed-pinned
   hypers; single-threaded fixed order (no map-order nondeterminism).
   Out: `weights_<handle>.json` + train Briers.
3. GATE — hard gates on SECRET split (gates.py). No pass → stage 4 serves that
   handle's models flagged `experimental:true`, never in default rotation.
4. SERVE — signal JSON per handle: direction P + regime + structure levels
   (entry/target/stop, grid-snapped) + chart refs. Pure function of weights+state.
5. RENDER — template post + SVG candles + mermaid game-plan + PNG (mermaid.ink).
   Fail-closed: any missing number → REFUSED artifact, counted.
6. PROVE — paper-trade emitted signals at 24h; receipts with Wilson CIs;
   demotion board updated (anything below bar flagged publicly in-report).

## Determinism rules

- Fixed seeds everywhere (`random.seed(7)`); no wall-clock in outputs (timestamps
  only in run receipt, excluded from content hash).
- No threads in scoring paths (dict/set iteration order is stable in CPython,
  but keep it simple: sequential loops).
- Receipt = sha256(seed.json + git HEAD + per-stage output hashes).
- Rerun rule: skip stage iff its output hash matches manifest (idempotent).

## What this replaces

trial.sh / replay.py / ad-hoc proveout invocations / scattered a-logs become
stages of one run. a-logs attach to the run receipt, not to chat history.
