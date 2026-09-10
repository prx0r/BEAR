# NORTHSTAR — versioned tournament loop (set 2026-09-10)

Goal: the whole mimic pipeline runs as a clean autonomous loop over versioned
seeds. seed1 = current pipeline. Each generation: run tournament → analyze →
justify changes → cut seedN+1 on its own git branch → re-run → compare.
a-logs are the evidence; an A-task is done only when its a-log exists AND its
a-report states validation evidence a peer can re-check. Loop stops when every
A-task has a passing a-report. No money, no M-tasks in this loop.

## Seed definition (`astronomer/mimic/seed.json`)

A seed pins: handles, split rule, model hypers (lr, prior, L1/L2), feature list,
retrieval method, commit/eval protocol. Anything not in seed.json is not part of
the experiment. Tournament = `trial.sh` × handles + discriminator + bridge,
all reading the seed.

## Tournament outputs (per generation, per handle)

`data/mimic_trials/<handle>_<seed>.json` + `a-logs/<date>-<seed>.md` +
`a-reports/<task>.md` (validation evidence for peer review).

## Stop rule

For each A-task: a-log exists AND a-report quotes its validation numbers AND a
peer (human or agent pass) finds no hallucination. All A-tasks passing = stop,
output peer-review pack. Anything failing goes back with the discrepancy noted.

## Branch convention

`seed0` (IMMUTABLE reference — full-logic snapshot, never tuned, never re-run for
decisions; all seeds compare against it, not each other), then `seed1`, `seed1.1`,
`seed2`, … — one branch per generation, cut from prior seed branch. Master only
receives reviewed merges (H-approval).

## Hard lessons (from reviewing `~/cg` cogymkernel + our own seed1.1)

1. **Secret holdout (cg's dev/validation/secret layering).** Our seed1.1 was tuned
   ON mock-live numbers — that window is now contaminated. Fix: split mock-live
   into VALIDATION (tune here) + SECRET (final verdict only, touched once per
   generation). No seed ships on validation numbers alone.
2. **Gates as hard constraints, not advice** (cg `eval/gates.py` pattern):
   promote a change ONLY if Wilson lower-bound improves at n≥30 AND frozen-copy
   check passes; else auto-reject. Our seed1.1 rejection was judgment — encode it.
3. **Content-addressed receipts** (cg blake3 run-ids): trial reports gain a
   sha256 over (seed.json + code version + data manifest) so any rerun is
   provably identical. Implement in `trial.sh`.
4. **Small-n seed hacking**: XO n=55 — seed deltas at that n are noise until
   proven otherwise. Minimum n for promotion decisions: 100, or pooled test.

## Reuse verdict on `~/cg`

Steal ideas + discipline (above), NOT the framework: cg needs pydantic/httpx/
HydraDB scheduler weight our stdlib box can't and shouldn't carry. Revisit only
if we outgrow single-machine trials. `cge` (expanded variant) unchecked —
evaluate only on a concrete need.
