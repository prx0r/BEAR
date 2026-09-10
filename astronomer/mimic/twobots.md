# Two-bot wiring spec v1.0 — SIGNALS voters + REGIME estimators

SIGNALS bot: per-handle CALL voters (direction + levels). Each voter = hurdle
model (`features.py` + `online.py`) trained on that handle's CALLs; emits
`{asset, direction, entry_basis, p_bullish, model, handle}` per post.
Gate: STRAT-004 rules consume votes only in their regime (XO→DOWN-4h,
Timeless→RANGE-24h, UP→nothing).

REGIME bot: estimators that never vote direction. Inputs, in priority:
1. Deterministic engine (`regime.py`: EMA20/50, 24h return, 7d vol) — base layer.
2. VERDICT voters (aporia, jjcmoreno, FrankAFetter, CavanXy, AxelAdlerJr…):
   per-account `P(regime | post)` micro-models, disagreement preserved as
   `{a disagrees with b because metric X}` observations (never averaged away).
3. FLOW/DATA features (hyblock, laevitas1, FarsideUK, Tokenomist): numeric vector
   concatenated into MarketState (pattern: `features.py` futures fields).
4. MICROSTRUCTURE (52kskew, Husslin_): `Skew interpretation + raw Binance data`
   as causal features, directional commentary down-weighted to ~0 vote.

Wiring: `brain.py` `/gate` returns `{regime, rule, voters_live[], estimators{}}`;
`/signal/latest?handle=` attaches gate state to every signal. Regime estimators
refresh hourly (cron, free); voters score per post. Horizon discipline: voter
outputs carry their proven horizon (astro 12h, XO 4h, Timeless 24–168h);
gate rejects votes outside it.
