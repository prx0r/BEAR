# Scout criteria — hunt accounts that fit, from measured data (7,374 posts)

Replaces gut-feel scouting. Run on a 20-tweet recon sample (same cost as today).

## 0. Pipeline rule (binding): August validate → July confirm → backfill

New account: 1) recon ($0.001) → 2) August pull (~$0.01) → quality-gate it (§1–2).
Pass → July pull (~$0.01) to confirm format stability across months. Stable →
price the 2yr backfill for HUMAN approval. Never backfill blind. (Set 2026-09-10.)

## 1. Yield score (primary gate — validates ONBOARD_SOURCE's 0.3)

`yield = (CALL+EXIT+COND+VERDICT+FLOW+MACRO) / 20`
PROCEED ≥ 30% · CAUTION 10–30% · SKIP < 10%.
Measured: Tokenomist 77%, hyblock 57%, laevitas1 56%, Daan 51%, DrProfit 45%,
astro/Timeless ~26%, chatter sinks 0–3%.

## 2. Role signatures (all must clear yield first, except feeds)

- VOTER: CALL ≥ 2 posts + levels in ≥1. Fingerprint: `closed/pnl/opened/holds`,
  6.1 numbers/post, 94% charted.
- VERDICT voice: VERDICT+COND ≥ 2. Fingerprint: `breakout/bear/bull/ema/channel`,
  evenings UTC.
- FEED (whitelist, yield-blind): numbers ≥ 3/post + media, ~0 direction words.
  Fingerprint: `cvd/whale/unlock/funding/hack`. (FarsideUK scores yield=0 and is
  still a feed — never yield-gate pure data.)
- EXIT reporter: `closed` (143× lift) + number. Rarest, most valuable per post.
- EDUCATOR: high COND + threads, low CALL (Cred pattern) → reasoning corpus.

## 3. Instant filters (single-post rules)

- `numbers == 0` → CHATTER (measured 0.0 nums/post over 3,645 posts). Drop.
- Promo spam (`bitget/vip/cfd/bonus/deposit`) → exclude (167 posts, all LEAN).
- LEAN split: with-direction = LEAN-TAC (chart-pair it); number-only = LEAN-DATA
  (feed it); neither + no numbers = CHATTER.

## 4. Timing (poll scheduling, UTC)

CALLs 8–12 + 23 · VERDICTs 15–22 · FLOW 15–17 + 2–3 · MACRO 12–17 (US morning) ·
dead zone 16–20 for trader voices (astro measured). Poll dense at role peaks,
skip dead zones — this is the quantified version of the pause-lesson.

## 5. Account clusters (k=5 on archetype mix — look for more of these)

- C2 money cluster (CALL18/FLOW28/LEAN32): OnchainLens, Tokenomist, hyblock,
  laevitas1, lookonchain — highest yields. Hunt lookalikes.
- C0 alert-wire (number-dense, directionless): EmberCN, PeckShield, ai_9684xtpa.
- C4 macro-chatter (DonAlt, FlowHorse, FirstSquawk): HTF context, not voters.
- C1/C3 chatter主流 — skip unless 2yr record exists (XO exception: Aug sample
  lies, 2yr record rules).
