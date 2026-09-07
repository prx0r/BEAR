# BEAR Dev Plan — Literature-Informed Strategy Overhaul

> Canonical resource. All work stems from this document.

## Core Thesis

**Predict terminal deterioration first; separately predict when it is safe/profitable to short it.**

The sweet spot is the **terminal-but-still-liquid phase** — not already dead tokens.

## The TradableDeath Formula

$$
\text{TradableDeath} = P_D \times P_L \times (1 - P_R)
$$

Where:
- $P_D$ = P(death within 30/90/180d)
- $P_L$ = P(still liquid enough to exit over horizon)
- $P_R$ = P(resurrection/squeeze within 30d)

## Implementation Priority (from literature)

### Phase 1: Fix Foundations
1. **Fix canonical calendar/PIT backtest** — freeze untouched OOS set
2. **Rebuild point-in-time everything** — event_at, published_at, available_at, ingested_at per arXiv audit paper

### Phase 2: Core Models (4 independent models — do NOT combine during training)

#### A. DEATH_HAZARD — slow
Inputs: volume-floor collapse, OI collapse, mcap decline, trading inactivity, dev decline, social/search decline, TVL/revenue decline, delisting-risk, token age, cohort
Output: P(zombie 30d), P(zombie 90d), P(zombie 180d)
Method: Random forest/XGBoost (per zombie paper — 84% balanced accuracy)

#### B. STRUCTURAL_DECAY — slow
Inputs: FDV/MCap, 2/4/8/12w issuance, issuance acceleration, discretionary issuance %, upcoming unlock/ADV, upcoming unlock/OI, active-address valuation, voluntary lock ratio, net buybacks/burns
Output: expected structural underperformance

#### C. SETUP — medium horizon
Inputs: 8–10w cross-sectional return, volatility, post-listing age, post-pump age, days to unlock, residual momentum, dispersion regime
Output: expected 7/30/60/90d residual return

#### D. TRADEABILITY — fast
Inputs: HL funding, funding z-score, OI change, OI/ADV, spread, depth, taker flow, recent squeeze, 15m/1h reversal, BTC/alt regime
Output: ENTER / WAIT / VETO

### Phase 3: Experiments (in order)
1. Replicate zombie paper → P(zombie_28d)
2. Replicate Guo → FDV/MC + 12w dilution
3. Replicate Kiefer/Nowotny → 8–10w cross-sectional reversal
4. 2D dilution × return sorts (recent winner / high dilution)
5. Token age interaction (<1y independently)
6. Unlock event-study curves T−30…T+30
7. Pump-event curves (when does post-pump alpha turn negative?)
8. Conditional: does high death forecast 30/60/90d BTC-beta-adjusted underperformance?
9. Last Pump strategy (high death + high dilution + recent winner + rollover + veto)
10. TAO/UNI long vs matched terminal-token shorts

### Phase 4: Two Short Archetypes

#### LAST PUMP
- High volatility / catalyst / issuance
- Entry: rally exhaustion via microstructure

#### SLOW SUFFOCATION
- Liquidity/activity collapse
- Entry: failed recoveries

## Key Literature Findings to Steal

| Finding | Source | BEAR Implementation |
|---------|--------|-------------------|
| Volume floor collapse = strongest zombie predictor | Zombie crypto 2026 | min_volume_28d, min_volume_182d, volume_floor_slope |
| FDV overhang + 12w dilution → 25-32% LS spread | Guo 2026 | FDVOverhang, Dilution_12w, DilutionAcceleration |
| 8w heavy issuance → 1.39 Sharpe | Kiefer/Nowotny 2026 | DiscretionaryDilution classification |
| Recent winner + heavy issuer → -33% annualized | Kiefer/Nowotny 5×5 sort | 2D sort: return × issuance |
| 8-10w cross-sectional reversal | Kiefer/Nowotny reversal | Multiple lookback windows |
| 46/52 unlocks negative within 72h | 72-Hour Shock 2026 | Unlock event study |
| 90% of 183 pairs show 15m reversal | arXiv 2026 | Entry timing for structural shorts |
| Age-specific models needed | Fantazzini 2022 | NEW/YOUNG/ESTABLISHED/OLD splits |
| Ghost valuation = MC/ActiveAddresses | Management Science 2026 | GhostValuation feature |
| Most composite screens are garbage | SSRN 2026 | Specific mechanisms only, no feature soup |

## Mandatory Reporting

Every experiment must report:
- Sharpe AND Deflated Sharpe
- Block-bootstrap confidence intervals
- Turnover/costs/funding
- Parameter surfaces
- Calendar-year results
- Regime results
- Dynamic-universe results
- One untouched holdout

## Repo Invariant

Every data field gets:
```
event_at
published_at
available_at
ingested_at
```

And:
```python
assert available_at <= signal_time
```

No exceptions.

---

## Research References

1. Zombie crypto prediction, 2026 — ScienceDirect
2. Token Mortality, 2026 — Lim (SSRN)
3. Crypto Probability of Death, 2022 — Fantazzini (MDPI)
4. Token Dilution, 2026 — Guo (SSRN)
5. Issuance factor, 2026 — Kiefer/Nowotny (Substack)
6. Crypto Reversal, 2026 — Kiefer/Nowotny (SSRN)
7. Token unlocks 72-Hour Shock, 2026 — Kim (SSRN)
8. Pump aftermath, arXiv — Clough/Edwards
9. 15-min crypto reversal, arXiv 2026
10. Binance delisting prediction, 2026 — Yang (Wiley)
11. Crypto value, Management Science 2026
12. Voluntary locked supply, 2026 — Khoja (SSRN)
13. RPHunter rug pulls, arXiv 2026
14. TON rug pull detection, arXiv 2026
15. Cross-sectional dispersion, 2026 — Zhang/Makgolo (SSRN)
16. AdaptiveTrend, arXiv 2026
17. Hidden crypto factors, arXiv 2026
18. Liquidation cascade heterogeneity, arXiv 2026
19. Crypto Carry, Management Science 2026
20. Perpetual swaps OI, arXiv 2026
21. Failure of cross-sectional alpha screening, SSRN 2026
22. Point-in-Time Audit Before Alpha, arXiv 2026
