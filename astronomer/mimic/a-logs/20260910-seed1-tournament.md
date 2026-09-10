# A-log seed1 tournament (2026-09-10, branch `seed1` @ b0e44f6)

Config: `mimic/seed.json` (seed1). Determinism check: numbers reproduce prior runs.

## Results (mock-live only)

| Handle | Activity live/frozen/base | Direction live/frozen/base | Text retr/rand |
|---|---|---|---|
| astro (84d/67d) | 0.1500/0.1499/0.1546 | 0.1874/0.2533/0.2273 | 0.096/0.092 |
| Timeless (273d/456d) | 0.0620/0.0629/0.0838 | 0.2184/0.2269/0.2123 | 0.060/0.055 |
| XO (232d/240d) | 0.0501/0.0509/0.1688-base | 0.1705/0.1590/0.1688 | 0.045/0.045 |

Reports: `data/mimic_trials/*_seed1_20260910.json`, `discriminator_seed1.json`
(struct 0.73 SIGNAL), `bridge_seed1.json` (best BEARISH/DOWN 31/55, no cell clears).

## Analysis → seed1.1 justifications

1. Direction prior 0.5 → per-handle train base rates (astro 0.837!). Frozen astro
   direction implodes partly from prior mismatch; train rates are free + causal.
2. Retrieval k1 → k3 + structural-discriminator rerank. Retrieval ≈ random;
   rerank tests shape-filtering for $0 before LoRA.
3. Implement `--save-weights` + transfer scoring (mocklive.py references a file
   that was never written — dead code path, now built).
4. Nothing else changes (isolates effects).
