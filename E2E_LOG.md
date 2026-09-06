# BEAR E2E Test Log — 2026-09-06 05:19:17 UTC

## 1. Health Check
✅ PASS: Health endpoint returns ok

## 2. Market Data
✅ PASS: Markets endpoint returns 5 entries
✅ PASS: BTC market lookup (price>0)

## 3. Leaderboards
✅ PASS: Leaderboard 'death_watch' has 5 entries
✅ PASS: Leaderboard 'price_action' has 5 entries
✅ PASS: Leaderboard 'squeeze_recovery' has 5 entries
✅ PASS: Leaderboard 'synthesis' has 5 entries
✅ PASS: Invalid leaderboard returns error

## 4. Factor Breakdown
✅ PASS: BTC factors: has reversal_8w, funding_carry, validated, formulas, paper URLs
✅ PASS: MOVE factors: has all required fields

## 5. Candle Data
✅ PASS: BTC candles: 5 daily OHLCV bars
✅ PASS: Non-existent symbol returns error

## 6. Summary Endpoint
✅ PASS: Summary: all 4 leaderboards, 177 markets, death_watch top>=60

## 7. Chat Endpoint
✅ PASS: Chat: responds with market analysis mentioning death watch

## 8. Dashboard Page
✅ PASS: Dashboard HTML: small, has loadData, fetches data.json
✅ PASS: Cloudflare data.json: 177 markets, 20 death watch, 50+ candle assets

## 9. Data Consistency
✅ PASS: Local and Cloudflare timestamps match: 2026-09-06T05:19:00Z

## 10. Validation Status
✅ PASS: BTC factors validation: 3+/5 validated

## Results

| Metric | Value |
|--------|-------|
| Total Tests | 18 |
| Passed | 18 |
| Failed | 0 |
| Pass Rate | 100% |

---
Test completed at 2026-09-06 05:19:20 UTC
