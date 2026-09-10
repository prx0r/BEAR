# A-report A-T4 — tournament seed1.1
Task: implement 3 justified changes, run, compare vs seed1.
Evidence: `*_seed1.1_20260910.json` + `a-logs/20260910-seed1.1-tournament.md`.
Validation: same harness, same splits, only seed diffs vary (isolated effects ✓).
Results: prior-change MIXED (helps XO, hurts astro via drift), rerank MIXED (helps
Timeless only), transfer REJECTED (0.29 vs 0.23, 0.23 vs 0.16).
Verdict: REJECT wholesale; promote adaptive-priors + per-handle-rerank to seed1.2
candidates. Falsifications logged, not buried.
