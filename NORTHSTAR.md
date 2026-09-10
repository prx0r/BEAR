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

`seed1`, `seed1.1`, `seed2`, … — one branch per generation, cut from prior seed
branch. Master only receives reviewed merges (H-approval).
