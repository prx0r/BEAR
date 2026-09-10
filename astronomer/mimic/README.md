# mimic — per-expert online imitators + mock-live harness

Spec: `../../mimichartastro.md`. Categories/taxonomy: `categories/`.
Runbook: `../../RECIPES.md`. All stdlib, offline, $0 unless noted.

| File | What |
|---|---|
| `features.py` | Causal market-state vector (1h + 5m klines, regime, futures, time, memory) |
| `online.py` | AdaGrad logistic + Brier/log-loss/ECE tracker + SHA256 commit log |
| `replay.py` | Causal history replay (activity + direction vs baselines) |
| `mocklive.py` | Walk-forward train/mock-live split, frozen vs adaptive, text retrieval, transfer test |
| `trial.sh` | One-command trial: `./trial.sh HANDLE` → `data/mimic_trials/*.json` |
| `discriminator.py` | Authorship shape-filter (structural SIGNAL; trigrams hurt — see trials) |
| `validate.py` | Enforces `categories/schema.json` (selftest: `python3 -m mimic.validate`) |
| `expand_labels.py` | Asset recovery → `all_outcomes_EXPANDED.json` (canonical untouched) |
| `fetch_market.py` | Free backbone: 5m klines + funding/OI/LS histories (paced, resumable) |
| `brain.py` | Local JSON API `:8789` (`/health`, `/gate`, `/signal/latest?handle=`) |
| `chart.py` | Dark 1200px SVG candles + levels (PNG export later via headless chromium) |
| `inbox_pull.py` | Live KV-inbox drain (PAUSED infra; needs MIMIC_NS_ID + CF creds) |
| `handles.json` | 10 reconfirmed targets (IDs, cadence, roles) |
| `categories/` | Ranked lists, scout scorecard, schemas, feeds, watchlists, panel roster |
