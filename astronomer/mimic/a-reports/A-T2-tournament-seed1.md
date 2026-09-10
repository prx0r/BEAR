# A-report A-T2 — tournament seed1
Task: run versioned tournament (3 trials + discriminator + bridge) on seed1 branch.
Evidence: `data/mimic_trials/{astronomer_zero,Timeless_Crypto,Trader_XO}_seed1_20260910.json`,
`discriminator_seed1.json` (struct 0.73 SIGNAL), `bridge_seed1.json` (8 cells, best BEARISH/DOWN 31/55).
Validation: numbers reproduce pre-seed runs exactly (determinism ✓); all scores strictly
causal (train-only state at decision time); frozen-vs-adaptive + base triple reported, no cherry-pick.
Verdict: PASS — baseline recorded, seed1.1 justified from its deltas.
