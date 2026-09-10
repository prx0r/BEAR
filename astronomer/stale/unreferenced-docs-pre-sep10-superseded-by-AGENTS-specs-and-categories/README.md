# STALE — pre-Sep-10 astronomer design docs, unreferenced and superseded

Moved here 2026-09-10 during repo-beautify audit. Verified: zero inbound
references from any live doc or code (only historical mentions inside
`specs/originals/`). Each file's live successor:

- `api-budget-engine.md` → `src/getxapi/` (budget-enforced client) + `RECIPES.md`
- `backtest-methodology.md` → `backtest.py` header + `specs/*backtest-protocol*`
- `canonical-accounts.md` → `mimic/handles.json` + `mimic/categories/panel.md`
- `complete-architecture.md` → `AGENTS.md` architecture reference
- `dynamic-protocol.md` → `AGENTS.md` procedures (ONBOARD_SOURCE etc.)
- `scraping-review.md` → GetXAPI docs in `astronomer/docs/getxapi/`
- `signal-classification-schema.md` → `mimic/categories/schemas.md` + `schema.json`
- `tool-registry.md` → `RECIPES.md`

Note: `astronomer/stale/` already held old backtest JSONs — same convention extended.
