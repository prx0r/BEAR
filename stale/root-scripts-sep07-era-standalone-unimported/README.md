# STALE — Sep-07-era standalone root scripts, imported by nothing

Moved here 2026-09-10 during repo-beautify audit. Verified via repo-wide grep:
no module imports any of these; no code opens them. They run standalone only,
and several assume the old `/root/BEAR` path or the DuckDB/parquet stack.

- `backtest_death.py` — death-token backtest printout script. Superseded by
  `astronomer/backtest.py` (canonical engine) + `mimic/mocklive.py`.
- `research_runner.py` — old research runner. Superseded by `mimic/trial.sh`.
- `github_activity_decline.py`, `llama_tvl_decline.py` — one-off decline studies.
  Data baked into `data/`; rerun via DeFiLlama free API (see
  `astronomer/mimic/categories/data-feeds.md`).

To run one: copy (don't move) back to root and fix paths. Do not re-add to root.
