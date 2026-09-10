# Session report — mimic autonomous run (2026-09-10)

Operator directive: work autonomously on highest-ROI activities. All offline, $0 API spend
(total session spend to date: ~$0.06 — recon $0.01 + test ticks ~$0.05; live infra paused).

## 1. Label expansion (premise corrected)

- Premise "283 → 940 outcomes" was wrong: canonical `all_outcomes.json` (460 rows,
  450 unique event_ids) already covers 100% of evaluable calls (0 missing, 0 extra).
- Real gap: 234 asset-None CALLs. Recovered 25 via unambiguous single-symbol
  entities+cashtags, daily-candle next-day-entry protocol (24h/7d horizons only).
- New: `data/core3/normalized/all_outcomes_EXPANDED.json` (485 rows),
  `data/core3/normalized/asset_recovery_map.json`. Canonical file untouched.
- Recovered alts: 48% 24h win (n=25, coin flip). Remaining: 155 symbol-less
  (need chart-reading), 52 no-price alts (need kline pulls), 2 multi-symbol (skipped).
- Incidental: canonical file has 10 duplicate event_ids (460 rows / 450 unique). Not fixed.

## 2. Mock-live matrix (`mimic/trial.sh`, reports in `data/mimic_trials/`)

| Handle | Split | Activity live/frozen/base | Direction live/frozen/base | Text retr/rand |
|---|---|---|---|---|
| astronomer_zero | 2026-07-01 (84d/67d) | 0.150/0.150/0.155 | 0.198/0.253/0.227 | 0.096/0.092 |
| Timeless_Crypto | 2025-06-02 (273d/456d) | 0.062/0.063/0.084 | 0.219/0.226/0.212 | 0.060/0.055 |
| Trader_XO | 2026-01-09 (232d/240d) | 0.050/0.051/0.053 | 0.162/0.159/0.169 | 0.045/0.045 |

Findings:
- Activity models beat base everywhere (Timeless: 26% better). Adaptive ≥ frozen.
- Frozen direction loses to base 2/3 (drift is real — deployed models must keep learning).
- Retrieval-text ≈ random on all three. Text stage needs discriminator + LoRA.

## 3. Direction→returns bridge (`data/mimic_trials/bridge_24h.json`)

485 labels, direction × regime cells: NONE clears 50% Wilson lower bound
(best BEARISH/DOWN 31/55=56% CI[43%,69%]). Blanket direction-following has no
measurable 24h edge. Gate stays source × regime × horizon (STRAT-004). The naive
"sell raw direction" product is dead.

## 4. Bugs caught and fixed (trials re-run clean)

1. `mocklive.py load_posts` sorted `createdAt` strings lexicographically (weekday
   names) instead of by timestamp — split landed mid-history. Fixed: parse then sort.
2. `inbox_pull.py` overwrote model weights with empty state, dropping the
   base-rate prior (commits at 0.500 instead of 0.171). Fixed: keep prior on fresh state.
3. `features.py` typo `_load Closes` (syntax error). Fixed.

## 5. Files created / changed (uncommitted)

- `astronomer/mimic/mocklive.py` (+`--json-out`), `expand_labels.py`, `trial.sh`,
  `handles.json`, `features.py`, `online.py`, `replay.py`, `inbox_pull.py`
- `astronomer/data/mimic_trials/` (3 trial JSONs + bridge JSON)
- `cloudflare/astro-poll/` (worker, cron schedules deleted = paused)
- `mimichartastro.md` (§7 → mimichart), `AGENTS.md` (mimic + Serving index)
- `~/mimichart/README.md` (model → x402 blueprint), `~/x402`, `~/x4022` cloned

## 6. Next ROI rank

1. Authorship discriminator (unblocks text, no GPU)
2. Brain API `:8789` serving frozen models (unblocks paywall)
3. 1m/5m klines (upgrades L1 features) + price pulls for 52 no-price alts

## 7. A-task loop run 2 (2026-09-10, all $0)

- A16: scout criteria adopted into ONBOARD_SOURCE (yield gate + role signatures + pipeline rule).
- A5b: 5m closes wired (`m5_r15/r60/range60`); m5 fields land top-8 weights immediately.
- A6: 6 new alt daily files (XPL/ASTER/PENGU/PUMP/LUNA/HAEDAL); labels 485→501 (+16, alts 25% 24h win).
- A10: two-bot wiring spec (`mimic/twobots.md`).
- A12 regression: trials stable (astro act 0.150/dir 0.187; Timeless 0.062/0.218; XO 0.050/0.171).
- A17: AuthorMix pair structure (`data/mimic_pairs_astro.json`,  rule-based neutralizer v0).
- Blocked: A3 (no httpx/pandas), A9 (backfills), A11 (no VLM runner), PNG export (no chromium).
