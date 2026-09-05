# BEAR Audit — Flaws, Hypotheses, Resolution Plan

## Critical Bugs (Must Fix)

### BUG-1: Column name mismatches across entire pipeline
- candles.py writes `market_id`, backtest/features expect `symbol`
- funding.py writes `rate`, features expect `funding_rate`
- **Hypothesis:** Standardize on `symbol` everywhere. Add alias in store layer.
- **Fix:** Rename all `market_id` → `symbol` in output DataFrames, add `funding_rate` column alias.

### BUG-2: DuckDB `INSTALL polars` doesn't exist
- store.py line 52 runs `INSTALL polars; LOAD polars;` on every property access
- **Hypothesis:** DuckDB ingests Polars natively via Arrow. No extension needed.
- **Fix:** Remove the INSTALL/LOAD. Use `conn.register()` for DataFrame ingestion.

### BUG-3: Beta formula computes wrong ratio
- `_safe_beta(x, y)` computes Cov(x,y)/Var(x) but spec requires Cov(long,candidate)/Var(candidate)
- **Hypothesis:** Called as `_safe_beta(long, candidate)` → wrong denominator
- **Fix:** Flip argument order or rename to clarify: hedge_ratio = Cov(L,S)/Var(S)

### BUG-4: CLONE_GAP uses abs() instead of max(..., 0)
- baskets.py line 203: `abs(structural_short_candidate - structural_short_long)`
- Spec: `max(STRUCTURAL_SHORT(candidate) - STRUCTURAL_SHORT(long), 0)`
- **Fix:** Replace abs() with max(candidate - long, 0)

### BUG-5: Funding annualization off by 8x
- features/funding.py uses `* 3 * 365` (8h assumption)
- Hyperliquid is hourly: should be `* 24 * 365`
- **Fix:** Change to 24x for HL hourly funding

### BUG-6: Backtest never calls optimizer
- `current_weights` initialized as zeros, never updated
- **Hypothesis:** Backtest runs long-only, not hedged
- **Fix:** Wire optimizer into rebalance loop

### BUG-7: Skewness/kurtosis don't demean
- metrics.py computes E[X³]/σ³ instead of E[(X-μ)³]/σ³
- **Fix:** Subtract mean before power computation

## Structural Gaps (Must Build)

### GAP-1: No WebSocket module (SPEC §6)
- Need real-time allMids, activeAssetCtx, bbo, candle streams
- **Fix:** Build async WebSocket manager with auto-reconnect

### GAP-2: No regime detection (SPEC §17)
- Need BULL/BEAR/HIGH_VOL/LOW_VOL/CRASH classification
- **Fix:** BTC 30d EMA + realized vol percentile

### GAP-3: No squeeze risk score (SPEC §24)
- Need SQUEEZE_RISK 0-100 combining funding, OI, momentum, books
- **Fix:** Build squeeze_scorer.py

### GAP-4: No spread monitor / cointegration (SPEC §36)
- Need Engle-Granger, ADF, half-life for pairs
- **Fix:** Build matching/cointegration.py

### GAP-5: No paper execution engine (SPEC §59)
- **Fix:** Build execution/paper.py

### GAP-6: CLI and API are all stubs
- **Fix:** Wire all commands to real engines

### GAP-7: No tests (SPEC §63-64)
- **Fix:** Build comprehensive test suite

## New Research-Backed Factors to Implement

### NEW-1: Dilution/issuance factor (8w supply growth)
- From Guo 2026 + Kiefer & Nowotny
- `dilution_8w = log(circ_t / circ_t_minus_56d)`
- percentile_rank → short candidates

### NEW-2: 8-10 week reversal factor
- Recent winners revert in crypto
- `reversal_8w = log(price_t / price_t_minus_56d)`
- High = recent winner = short candidate

### NEW-3: Unlock pressure with recipient weighting
- insider_unlock_usd / ADV_30d with recipient-specific weights
- team * 1.0, investor * 0.8, foundation * 0.4, community * 0.25, ecosystem * 0.1

### NEW-4: Post-listing decay + delisting risk
- age_days, listing_return, cohort analysis
- XGBoost delisting probability

### NEW-5: Active-address value factor
- market_cap / active_addresses_30d within sectors
- High = overvalued = short candidate

### NEW-6: Net supply pressure
- Unlocks + Emissions - Buybacks - Burns
- Critical for false positive avoidance (PUMP, ENA)

### NEW-7: Factor sleeve architecture
- Test each factor independently first
- Then double sorts: DILUTION × REVERSAL, DILUTION × AGE
- composite = weighted sum of percentile-ranked sleeves
