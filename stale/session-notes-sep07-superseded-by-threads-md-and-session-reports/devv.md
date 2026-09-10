# BEAR Development Notes — Research-Backed System Architecture

## Core Thesis

The engine does not attempt to predict the direction of crypto as a whole. It attempts to identify assets with desirable idiosyncratic exposure, then hedge their common market exposures using behaviorally similar assets with inferior economics.

Key mental model: DON'T ASK "Will TAO go up?" ASK "Will TAO outperform the cheapest basket of bad assets that reproduces the risks I don't want?"

## Independent Short-Side Anomalies (Stackable)

1. **Dilution / issuance** — 8w supply growth predicts lower returns (Sharpe 1.39, ~35-45% spread)
2. **8-10 week reversal** — recent winners revert (Sharpe 1.19-1.38)
3. **Low-float/high-FDV + young-token effect** — first-year dilution strongest
4. **Scheduled insider unlock pressure** — -7% BTC-relative per event
5. **Weak fundamental value / activity** — market_cap/active_addresses as value badness
6. **CEX post-listing decay** — -37% at 6 months for 2024 Binance cohort
7. **Delisting/zombie risk** — XGBoost PR-AUC ~0.807
8. **Cointegration/factor matching** — for choosing what to short against TAO/UNI
9. **Funding/basis/crowding** — execution layer, ~7% excess carry on HL

## Key Finding: Dilution and Reversal are Independent (correlation ~-0.03)

## The Nasty Corner (Double Sort)
Recent winners + heavy issuance ≈ -33% annualized

## Factor Sleeves (test independently first)
- DILUTION
- REVERSAL
- UNLOCK
- LISTING
- VALUE
- DELIST
- FUNDING

## Composite (to test, not deploy)
structural_trash = 0.30*dilution_8w + 0.20*fdv_overhang + 0.20*insider_unlock_adv + 0.15*reversal_8w + 0.10*valuation_badness + 0.05*delist_risk

tradability = hedge_fit * liquidity_score * carry_score * (1 - squeeze_risk)

candidate_score = structural_trash * tradability

## Specific Names to Research
- ZRO: 35.3% circ, 76.9% insider+investor upcoming
- ZK: 49.4% circ, -15.1% median BTC-relative at unlocks
- W: 30.4% locked, -15.6% median, 93% negative events
- WLD: 33.9% circ, industrial dilution to 2038
- STRK: structurally ugly but currently expensive to short (negative funding)
- OP: same crowding issue
- ARB: weaker, DAO treasury unlocks less bearish

## False Positives (need net issuance)
- PUMP: buy-and-burn removes ~16.4% of supply
- ENA: bought out investors, collapsed schedule

## Architecture: Net Supply Pressure
Net Supply Pressure = Unlocks + Emissions - Buybacks - Burns

## Execution Layer
- 15m reversal for entry timing (1.3bp edge, use for execution not alpha)
- Funding carry as independent return stream
- Never predict funding with ML, use simple historical mean

## Implementation Order
1. Dilution factor (8w supply growth)
2. Reversal factor (8w return)
3. Unlock pressure (insider/ADV ratio)
4. Post-listing decay + delisting risk
5. Active-address value factor
6. Cointegration hedging
7. Factor sleeve composite
8. Dashboard + e2e tests
