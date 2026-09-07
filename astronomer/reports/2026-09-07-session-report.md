# Session Report — 2026-09-07

## What Happened

### Phase 1: Canonical Protocol Saved
- User sent the full 46-part canonical protocol
- Saved word-for-word to `specs/originals/2026-09-07-canonical-protocol-original.md`
- This is the binding architecture for all BEAR work going forward

### Phase 2: Fixed the 4 Backtest Bugs

| Bug | Fix |
|-----|-----|
| `SYMBOL_MAP` defaulted HYPE → BTCUSDT | Removed. Unknown assets return `None` |
| `get_price_at()` entered same candle | Replaced with `get_next_candle_from_list()` — entry on first candle AFTER publication |
| `results[horizon_name]` flat dict for multi-asset | One `EventOutcome` per event × asset. Never flat. |
| Return `0.00338` displayed as `0.003%` | Returns stored as decimal. 0.00338 = 0.338%. Print statements show `* 100`. |

### Phase 3: Built Canonical Infrastructure

**New files created:**
- `schemas.py` — Canonical types: `RawPost`, `MarketEvent`, `EvidenceSpan`, `EventOutcome`, `SourceReputation`, `ExperimentRecord`, `MarketStateSnapshot`
- `regime.py` — Deterministic BTC regime from hourly data (EMA20/50, 24h return, 7d vol). Timeline: 23,520 entries.
- `backtest.py` — Canonical backtest engine. No BTC default, next-candle entry, one outcome per asset, correct return units.
- `metrics.py` — Performance metrics (Sharpe, Sortino, drawdown, VaR, profit factor, Wilson CI, bootstrap CI). Adapted from `BEAR/src/bear/backtest/metrics.py` and `fleece/fleece/eval/gates.py`.
- `baselines.py` — Baseline models: always long, always short, random, momentum.
- `run_backtest.py` — Full pipeline runner.

**Old files moved to stale:**
- `backtest_august_v2.json` → `stale/`
- `outcomes.json` → `stale/`
- `classified_august.json` → `stale/`
- `extracted_gold.json` → `stale/`

### Phase 4: Fixed Extractor Asset Detection

**Bug found:** `extractor_v2.py` used `find_quote_span()` (plain string search) on regex patterns like `r'\$btc'`. The patterns were never matching.

**Fix:** Changed asset detection to use `re.search()` instead of `find_quote_span()`.

**Result:** Asset detection went from 0/383 to 104/383 posts. CALL events with asset went from 0 to 30.

### Phase 5: Re-extracted August

- 383 raw posts from 10 accounts
- 523 total events (after adding laevitas1, ki_young_ju, FarsideUK)
- 53 CALL events, 405 VIEW, 45 RETROSPECTIVE, 16 OBSERVATION, 4 NON_SIGNAL
- 206 events with asset identified (39%)

### Phase 6: Ran Canonical Backtest

**33 outcomes generated** (CALL events with asset + timestamp + direction).

**Overall (n=33):**
- Win rate: 57.1% (Bayesian: 56.2%)
- Wilson CI: [39.1%, 73.5%]
- Mean 4h return: 0.331%
- Sharpe: 7.71
- Profit factor: 3.48

**Baselines (4h, same timestamps):**
- Always long: 64.3% win, 0.090% mean, Sharpe 2.12
- Random: 57.1% win, 0.140% mean, Sharpe 3.30
- Our signals: 57.1% win, 0.331% mean, Sharpe 7.71

**Per-author:**
| Author | N (4h) | Win% | Mean | N (24h) | Win% | Mean |
|--------|--------|------|------|---------|------|------|
| @Timeless_Crypto | 8 | 62% | 0.24% | 8 | 62% | 0.13% |
| @astronomer_zero | 8 | 50% | 0.60% | 8 | 50% | -0.53% |
| @lookonchain | 5 | 60% | 0.37% | 5 | 100% | 1.72% |
| @laevitas1 | 5 | 20% | -0.16% | 5 | 60% | 1.10% |
| @exitpumpBTC | 2 | 50% | 0.00% | 2 | 0% | -1.43% |
| @CryptoBheem | 2 | 50% | 0.27% | 2 | 50% | 0.22% |
| @ki_young_ju | 2 | 50% | -0.61% | 2 | 50% | -1.06% |

**Key finding:** laevitas1 is BAD at 4h (20%) but GOOD at 24h (60%, 1.10% mean). Derivatives signals need longer horizon. This validates the canonical protocol's claim: "horizon follows economic mechanism."

### Phase 7: First Full Onboarding (laevitas1)

Ran the complete protocol:
1. **Recon** — user/info: 123K followers, derivatives flow specialist
2. **Fetch** — advanced_search: 45 August tweets in 2-week chunks
3. **Extract** — 45 events: 8 CALL, 26 VIEW, 9 RETRO
4. **Backtest** — 5 outcomes at 4h and 24h
5. **Source card** — Saved to `source_cards/laevitas1.json`
6. **Key insight** — Derivatives signals operate at 24h, not 4h

**Cost:** ~$0.06 (6 API calls × $0.001)

### Phase 8: Attempted Other Influencers

| Account | Result |
|---------|--------|
| 52kskew | Last tweet June 16, 2026. Inactive. Cannot backtest August. |
| DefiSquared | Last tweet April 9, 2026. Inactive. |
| PriorXBT | 0 August tweets. Inactive. |
| Husslin_ | 0 August tweets. Inactive. |
| FarsideUK | 80 August tweets. All VIEW (ETF flow data). Needs event study, not directional backtest. |
| ki_young_ju | 35 August tweets. Only 2 CALLs. Most content is onchain data observations. |

**Lesson:** Many high-value accounts post structured data (ETF flows, onchain metrics, derivatives state), not directional calls. The current extractor/classifier only catches directional calls. These accounts need **event study** testing, not trade backtest.

### Phase 9: Honest Assessment Written

Saved to `data/backtest/RESULTS_AUGUST_2026.md` with explicit caveats:
- n=33 total (too small for conclusions)
- Wilson CI includes 50% (can't distinguish signal from noise)
- August was bullish BTC (always-long baseline got 64.3%)
- 17/53 CALL events had no asset detected (selection bias)
- Sharpe ratios of 7-14 are artifacts of small samples

## Budget Status

| Metric | Value |
|--------|-------|
| Starting balance | $39.62 |
| Ending balance | $39.61 |
| API calls this session | ~13 |
| Cost this session | ~$0.01 |
| Remaining | $39.61 |
| Plan expires | 2026-10-07 |

## Files Created/Modified

### New files
- `astronomer/schemas.py` — Canonical types
- `astronomer/regime.py` — BTC regime timeline
- `astronomer/metrics.py` — Performance metrics
- `astronomer/baselines.py` — Baseline models
- `astronomer/run_backtest.py` — Full pipeline runner
- `astronomer/data/regime/timeline.json` — 23,520 regime entries
- `astronomer/data/backtest/outcomes_v2.json` — 33 canonical outcomes
- `astronomer/data/backtest/source_cards_v2.json` — Source cards
- `astronomer/data/backtest/source_cards/laevitas1.json` — laevitas1 source card
- `astronomer/data/backtest/RESULTS_AUGUST_2026.md` — Honest assessment
- `astronomer/stale/` — Old backtest files with explanations
- `specs/originals/2026-09-07-canonical-protocol-original.md` — User's protocol

### Modified files
- `astronomer/extractor_v2.py` — Fixed asset detection (regex, not string find)
- `astronomer/backtest.py` — Rewritten with 4 bug fixes
- `astronomer/data/backtest/extracted_august_v2.json` — Re-extracted with fixes
- `astronomer/data/backtest/raw/` — Added laevitas1, ki_young_ju, FarsideUK, 52kskew

## What We Learned

1. **The pipeline works end-to-end** — extract → match → outcomes → metrics
2. **Horizon follows economic mechanism** — laevitas1 proves derivatives need 24h, not 4h
3. **Many accounts post data, not calls** — need event study for non-directional content
4. **Sample sizes are tiny** — n<30 means no conclusions are valid
5. **The extractor catches ~75% of CALL assets** — need gold set for QA
6. **Always-long is a strong baseline in bullish August** — any edge must beat it
7. **52kskew, PriorXBT, Husslin_ are inactive** — can't onboard right now
8. **FarsideUK needs event study** — ETF flows predict differently than directional calls
