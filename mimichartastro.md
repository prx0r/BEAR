# mimichart-astro — Spec: a bot that posts like @astronomer_zero

*Status: SPEC (2026-09-10). No live polling — everything here runs on data on disk.
Related: `astronomer/mimic/` (v0 hurdle + replay), `STRAT-004` (ensemble gate).*

## 0. Data truth (do not assume 2 years)

| Item | Reality | File |
|---|---|---|
| Tweets | 766, 2026-04-08 → 2026-09-07 (151d, 5.1/day) | `astronomer/data/backtest/raw/astronomer_zero_2yr.json` |
| Strict calls | 461 (359 BULLISH / 102 BEARISH, 457 BTC) | `astronomer/data/core3/normalized/strict_calls.json` |
| With charts | 519/766 (67.8%), mostly 1200px landscape | `astronomer/data/media/astronomer_zero/` |
| With return labels | 96 BTC outcomes | `astronomer/data/core3/normalized/all_outcomes.json` |
| Text length | raw med 134ch / max 1740ch (events truncated at 500ch — train from raw) | raw vs `*_events.jsonl` |
| Active hours | 0–15 + 21–23 UTC; dead 16–20 UTC; weekdays 2× weekends | timing analysis 2026-09-10 |
| Corpus size | ~230k chars ≈ ~60k tokens — near StyleTunedLM's 70% band (viable, augment) | — |

Consequence: astro gets a **train 2026-04-08→06-30 / mock-live 07-01→09-07** split (84d/67d),
not 1yr/1yr. The 1yr+1yr protocol is developed on Timeless (true 2yr) and *applied* to astro.

## 1. Objective

`P(post?, direction, text, chart | market state)` that is indistinguishable from astro
in voice, then scored on divergence from his actual posts. Imitation objective —
fidelity first, profitability decided downstream by the STRAT-004 gate.

## 2. Architecture (hurdle — easy → hard, each stage gated)

```
market state (1h BTC/ETH + regime + time + memory)
  → A: P(post next hour)          [BUILT: Brier 0.1386 vs 0.1419 base]
  → D: P(BULLISH | post)          [BUILT: Brier 0.1555 vs 0.1723 base]
  → T: text in astro voice        [v0 retrieval; v1 StyleTuned LoRA]
  → C: 1200px chart, astro-styled [programmatic render, never diffusion]
```

A number that fails verification blocks the post (fail-closed). Charts are rendered
from real OHLCV — diffusion hallucinates candles/axes and is a liability.

## 3. Data prep

1. Join strict ↔ events on `(handle, published_at)` (940/940 proven) → raw full text,
   `post_id`, `media_files`. Strict texts are truncated at 200ch — never train on them.
2. Dedup (10 exact-prefix groups found; near-dup ~0) + shuffle field order for augmentation.
3. **Mask prices/levels/cashtags in the LM loss** (`labels=-100`, StyleTunedLM §3):
   the model must learn STYLE, not stale numbers. Numbers are slot-filled from live
   market state at serving time and regex-verified against it.
4. Splits by TIME only. Never shuffle.

## 4. Text model (two stages)

**v0 — retrieval (built, no training):** nearest train post by market-state vector,
adapted to current numbers. Baseline: 89% asset agreement, Jaccard scored vs random.
Ships first, generates the LoRA eval baseline.

**v1 — StyleTuned LoRA** (StyleTunedLM, INLG 2024 — beats 5/10-shot; 591-example
precedent trains in ~15 min):
- Base: `Qwen2.5-1.5B-Instruct` (ungated), chat template `market-state → post`,
  `max_seq 256–512`, no packing. Rented 4090, ~$0.50–3 total.
- `r=8–16, alpha=16–32, lr=1–2e-4, epochs=3–5`, early stop on held-out loss,
  attn-only targets, 10–15% held-out by time.
- Eval (in order): authorship-discriminator hit-rate (astro-vs-others DeBERTa),
  style-embedding cosine, blind human A/B. Ship bar: >90% condition adherence,
  style ≥ retrieval baseline. Modern-scenario test (topics astro never covered)
  to prove transfer, not memorization.

**Transfer astro → Timeless/XO/anyone (AuthorMix, 2026):** one LoRA adapter per
trader, then learned layer-wise mixing weights for a new target from a handful
of their posts. Per-trader adapters are also the ensemble's per-source simulators.

## 5. Chart renderer (astro-styled, programmatic)

- TradingView `lightweight-charts` (Apache 2.0) + drawing-tools lib
  (trend lines, fib, channels, text/callout annotations); dark theme matching
  astro's 1200px landscape screenshots; headless-chromium PNG export for X.
  Python side: `lwcharts` (offline, pandas-only) or `lightweight-charts-python`
  Toolbox (trendlines/rectangles/horizontal lines).
- Levels come from price structure (swings, S/R, ATR) — only 19% of astro texts
  state explicit levels, so text is not the source of levels.
- His 519 archived charts are the STYLE reference (annotation density, colors),
  not training pixels.

## 6. Mock-live protocol (`astronomer/mimic/mocklive.py`)

- Walk mock-live window hour by hour: predict → SHA256-commit → reveal → score → update.
- Two copies: **frozen** (true OOS) and **adaptive** (deployed performance).
- Metrics on mock-live only: Brier/log-loss/ECE vs train-window base rates,
  text Jaccard vs random-post baseline, transfer Brier (astro weights → target).
- Current baselines to beat: activity 0.1419, direction 0.1723 (astro).

## 7. Serving (when unpaused)

Build doc: `~/mimichart/README.md` (indexed in `AGENTS.md` → Serving).
Same skeleton as `~/x402/x402fun/server.ts` (Hono + ExactAvmScheme, Caddy →
localhost + systemd): `GET /v1/signal/latest` $0.05 (full JSON: asset, direction,
entry/invalidation/target, p_profitable, regime, evidence),
`GET /v1/evidence/{signal_id}` $0.01. Private T=0 → delayed public X card →
resolved outcome card (meta-science spec §4–5).

## 8. Milestones

1. [x] v0 hurdle beats baselines (replay, causal)
2. [x] Label expansion — canonical complete (450/450); +25 alt labels recovered
   (`all_outcomes_EXPANDED.json`, daily protocol). No further backtest expansion exists.
3. [x] Mock-live report: astro + Timeless + XO (`data/mimic_trials/` + session report
   `astronomer/reports/2026-09-10-mimic-trials-report.md`)
4. [ ] Authorship discriminator (style-divergence scorer)
5. [ ] Retrieval-text + rendered-chart end-to-end sample posts
6. [ ] StyleTuned LoRA (rented GPU) beating retrieval bar
7. [ ] AuthorMix adapters: astro → Timeless/XO transfer scores
8. [ ] x402 signal server on VPS + delayed-X proof loop (paused infra resumes here)

## 9. Open risks

- 151 days is thin; 78% bullish / 99% BTC base rates dominate — always beat base-rate.
- Measured: charted calls show NO return edge (51% vs 55%) — charts are packaging.
- Small-n edges (XO streak n=9, Timeless run-2 n=19) must not set gate weights alone;
  STRAT-004's 169 trades is the most trustworthy number in the repo.
- Compliance: retain every prediction + outcome; disclaimers required; no cherry-picked P&L.
