# Open threads (2026-09-10, audited — IDs unique, statuses current)

*RULE: anything spending money or touching prod/canonical needs HUMAN approval.
Agent works the autonomous list top-down. $0 items only.
TAXONOMY: A-Task = agent ($0) · H-Task = human action/decision · M-Task = money
(explicit approval with amount). No H/M-task executes without a clear go.
Full spec (definitions, classifier, prioritizer, approval protocol): `TASKSPEC.md`.*

## A. Agent-autonomous ($0, offline) — priority order

| Pri | # | Thread | Status / next |
|---|---|---|---|
| P0 | A1 | Authorship discriminator | DONE (structural SIGNAL 0.73/0.188; trigrams hurt) → ships as shape-filter; voice needs LoRA |
| P0 | A2 | Brain API `:8789` | DONE, live (health/gate/signal, curl-verified) |
| P0 | A3 | 221-post pending queue → strict labels | BLOCKED: needs httpx/pandas (box has neither, no pip) — or H-approve `apt install python3-pip` |
| P0 | A4 | Chart renderer | DONE SVG (120 candles, levels); PNG export pending (needs headless chromium) |
| P1 | A5 | 5m klines (213k×BTC+ETH on disk) + futures wired | DONE data; futures fields live in MarketState (lift ≈ 0, honest); 5m→features wiring open |
| P1 | A6 | 52 no-price alts → kline pulls + daily labels | OPEN |
| P1 | A7 | Panel quality matrix (50-file rank) | DONE — DrProfit > astro > Daan > Timeless > kingfisher* > Chase |
| P1 | A8 | July confirms graduated three | DONE ($0.020) — formats stable, custom-extractor note for Chase |
| P1 | A9 | E2E matrix experiment | BLOCKED: needs backfill histories (H6) |
| P1 | A10 | Two-bot split (SIGNALS vs REGIME) | OPEN — roles defined (`categories/panel.md`), wiring spec unwritten |
| P1 | A11 | 155 symbol-less CALLs → VLM detect | OPEN (CPU VLM, free download) |
| P1 | A12 | Mock-live regression (`trial.sh`) | ONGOING — re-run after each change |
| P1 | A13 | Canonical schemas v1.0 | DONE (`schemas.md` + `schema.json` + validator 3/3); `schemas.py` change staged as spec |
| P1 | A14 | Free feeds + dream-shelf maps | DONE (`data-feeds.md`, `onchain-price-map.md`) |
| P1 | A15 | Bazaar recon (CDP+Circle, `bazaar_recon.json`) | DONE — n0brains bar 61%; test-buys ranked (H7) |
| P1 | A16 | Adopt scout criteria + LEAN-split into ONBOARD_SOURCE | OPEN (docs PR into AGENTS procedure) |
| P2 | A17 | AuthorMix training-data packaging | OPEN (GPU train stays H2) |
| P2 | A18 | Cosmetic manifest fixes | OPEN, do last |

## B. Human-gated (money, prod, judgment) — priority order

| Pri | # | Thread | Gate | Cost / decision |
|---|---|---|---|---|
| P0 | H0 | Rotate pasted R2 token (chat history) | SECURITY | Console rotation |
| P0 | H1 | Resume live infra (15-min cadence) | SPEND | ~$0.10–0.30/day |
| P1 | H2 | StyleTuned LoRA GPU rental | SPEND (UNBLOCKED — A1 bar set) | $1–3 one-off |
| P1 | H3 | Domain choice for signal server | DECISION | Needed before Caddy/HTTPS |
| P1 | H4 | Fund spend wallet `0x90CE…115` | MONEY | $5 USDC + gas |
| P1 | H5 | Monitoring-plan decision | SPEND | Flat vs per-call at 10+ handles |
| P1 | H6 | Backfills: JAM ~$0.15 + Frank ~$0.16 + Axel ~$0.06 + CrypNuevo ~$0.04 (+ Wild_R ~$1.00 excl. pending split, 52kskew 3-mo ~$0.04) | SPEND | ~$0.45 core (or ~$1.45 all-in) |
| P1 | H7 | Bazaar test-buys ranked (n0brains → ottoai → cryptyx → news → Kalshi) | SPEND | ~$0.02 + Nansen free-credit test $0 |
| P1 | H8 | Paywall allowlist — RIPE NOW (A1–A4 results in hand) | JUDGMENT | Approve graduate list |
| P2 | H9 | Canonical dupe fix (10 event_ids) — review staged diff | PROD DATA | Agent stages, human approves |
| P2 | H10 | Strategy kill calls on real capital (S1–S6) | JUDGMENT | Agent computes, human pulls trigger |
| P2 | H11 | Stocks gold-set recon + pulls | SPEND (~$0.06) + new asset class | Panel directive says next |
| P3 | H12 | Freaktown hardening + CF P0 edge (pre-existing) | PRE-EXISTING | Approve staged changes |
| P3 | H13 | R2 source-object deletion re-verify (pre-existing) | PRE-EXISTING | Check then delete |
| P3 | H14 | Commit review: BEAR + mimichart trees | REVIEW | Walkthrough on request |

## Reference (no action until gated)

- S1 STRAT-004 VALIDATED (kill: equity < 1.0 × 30 forward trades) · S2–S5 HYPOTHESIS
  with kill conditions in `STRAT-*.json` · S6 half-falsified
- Serving chain fully specified in `~/mimichart/README.md`; blocked on H3/H4 (A2 done)
- Specs: `mimichartastro.md` (milestones 1–3 done) · `specs/originals/` are historical records

## Closed this session (log)

- C1 charts (3,683) · C2 v0 hurdle beats bases · C3 10-handle recon · C4 worker deploy+test
- C5 label recovery +25 · C6 mock-live matrix · C7 bridge verdict (flat) · C8 mimichart repo
- C9 infra paused (~$0.06) · C10 threads audit · C11 A-sprint (discriminator/brain/charts/validator)
- C12 org audit (README/AGENTS/RECIPES) · C13 beautify (17 files → stale/) · C14 July confirms
  ($0.059) · C15 categories/registry rank · C16 schemas v1.0 · C17 feeds + dream-shelf maps
- C18 arch-20 intake ($0.208: recon + Augusts) · C19 threads dedup audit (this rewrite)
- C20 A-loop run 2 (ONBOARD_SOURCE · 5m fields · +16 labels · twobots · AuthorMix pairs)
- C21 A-loop run 3: Bybit dailies (MNT/CAT/SPX, +7 labels → 508) · 5m-vs-1h entry audit
  (71.3% agree — 29% of labels entry-sensitive) · pair leakage 17%→0% (neutralize.py v1.2) ·
  brain 3/3 live · spend ledger $0.391+$0.015
- C22 env upgrade: venv+pip (pydantic/httpx/pandas) · OPENAI_API_KEY vaulted BUT 401-invalid
  (needs replacement) · Hermes 3 8B local via ollama :11434 ✓ · opencode wiring as example only
- C23 PIVOT voice→signals+charts: voice track SHELVED (LoRA/AuthorMix on hold) ·
  `mimic/post.py` template generator (fail-closed verified) · chart game-plan overlay
  (entry/target/stop zones + R:R) · live demo post+chart generated · PNG export needs chromium (H)
- C24 mermaid diagrams (`mimic/diagram.py`): game-plan flowchart + round-trip timeline from
  signal JSON, deterministic, zero-dep. For API/agent/GitHub surfaces; X still needs PNG.
- C25 full output chain CLOSED $0 (signal→post+SVG+mermaid→PNG via mermaid.ink, verified 24KB).
  Output machinery 100%; remaining gap is SIGNAL QUALITY (gate fails secret) + candle-PNG.
- C26 APIFY_TOKEN rotated in vault (user-supplied, verified live: tangta/FREE plan).
- C27 level-infill: 1,746 TIER1 levels; v0 beats spot, loses to swing; v1 grid FAILS;
  75.9% levels on $1k grid → $500-snap in post.py; which-grid-point needs vision (H/M).
- C28 prove-out FULL history ($0): 282 paper posts — astro 56% CI(46,66), Timeless 55%,
  XO 44%. Model matches man, OOS=in-sample (stable), no lower bound clears 50%.
- C29 Bheem multi-asset (BTC+ETH+HYPE): 60 trades 47/47; strict gap found (Bheem has
  zero strict rows — events-CALL fallback built); his 95/98 CALLs pre-date mock window.
