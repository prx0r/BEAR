# 1-Month Backtest Prep

## Account List (final, includes eliz883)

### Signal Accounts (16)
| Handle | Weight | Source |
|--------|--------|--------|
| @PriorXBT | 1.5 | microstructure, MM flow |
| @exitpumpBTC | 1.2 | order flow, BTC directional |
| @52kskew | 1.2 | order flow, levels, regime |
| @Trader_XO | 1.2 | levels, directional, macro |
| @Timeless_Crypto | 1.2 | conviction, levels, contrarian |
| @Husslin_ | 1.1 | dealer positioning, perp flow |
| @lBattleRhino | 1.1 | alt strength |
| @DeFiSquared | 1.0 | token unlocks, governance |
| @thiccyth0t | 1.0 | fund flow, positioning |
| @0xLoris | 1.0 | MM intel, onchain |
| @astronomer_zero | 1.0 | multi-TF, levels |
| @CryptoBheem | 1.0 | levels |
| @GreatMattsby | 1.0 | technical, levels |
| @calvintsaikm | 1.0 | levels, systematic |
| @eliz883 | 0.5 | high engagement, on the fence |
| @Oldman__Crypto | 0.5 | some calls, on the fence |

## Date Range

- **From:** 2026-08-01
- **To:** 2026-09-07
- **~5 weeks of data**

## Budget Estimate

- 16 accounts × 1 call each = **16 calls = $0.016**
- Plus pagination if needed: ~**$0.03-0.05 total**
- Remaining balance: **$0.13**

## What to Extract Per Tweet

From GetXAPI response, capture ALL fields:

```json
{
  "id": "tweet_id",
  "url": "https://x.com/...",
  "text": "full text",
  "source": "Twitter Web App",
  "createdAt": "timestamp",
  "likeCount": 0,
  "retweetCount": 0,
  "replyCount": 0,
  "quoteCount": 0,
  "viewCount": 0,
  "bookmarkCount": 0,
  "lang": "en",
  "isReply": false,
  "inReplyToId": null,
  "conversationId": "...",
  "media": [...],
  "entities": {
    "hashtags": [...],
    "symbols": [...],
    "urls": [...],
    "user_mentions": [...]
  },
  "author": {
    "userName": "...",
    "id": "...",
    "name": "...",
    "followers": 0,
    "following": 0
  },
  "quoted_tweet": null
}
```

## Signal Extraction (per tweet)

Extract:
1. **direction** — LONG/SHORT/NEUTRAL
2. **assets** — BTC, ETH, SOL, TAO, etc.
3. **levels** — price levels mentioned
4. **entry/target/stop** — if specified
5. **conviction** — high/medium/low
6. **conditional** — if/when statement
7. **is_reply** — whether it's a reply
8. **is_quote** — whether it's a quote tweet
9. **has_chart** — media attachment
10. **engagement** — likes, views, bookmarks

## Price Data

Already fetched:
- BTCUSDT: 23,520 hourly candles (2024-01-01 to now)
- ETHUSDT: 23,520 hourly candles
- SOLUSDT: 23,520 hourly candles
- TAOUSDT: 21,084 hourly candles

## File Structure

```
astronomer/data/
├── backtest/
│   ├── raw/                  # Raw API responses (per account per month)
│   │   ├── {handle}_{month}.json
│   ├── extracted/            # Extracted calls
│   │   └── calls.jsonl       # All calls with metadata
│   ├── matched/              # Calls matched to price outcomes
│   │   └── outcomes.jsonl    # Per-call outcomes at 1h/4h/24h/7d
│   └── reputation/           # Author reputation scores
│       └── reputation.json   # Per author × asset × direction × horizon
├── prices/                   # Already have this
│   ├── BTCUSDT_1h.json
│   ├── ETHUSDT_1h.json
│   ├── SOLUSDT_1h.json
│   └── TAOUSDT_1h.json
```

## Backtest Metrics Per Call

For each call at time T with entry price P:
- return_1h = (P_{T+1h} - P) / P × direction
- return_4h
- return_24h
- return_7d
- mfe_24h = max favorable excursion in 24h
- mae_24h = max adverse excursion in 24h
- direction_correct = return > 0

## Reputation Score Per Author × Asset × Direction × Horizon

- n = sample size
- win_rate = Bayesian (with shrinkage)
- median_return
- profit_factor = gross_profit / gross_loss
- confidence = sufficient (n>=10) / limited (n>=3) / insufficient (n<3)

## Ready to Run

Once credits are available:
```bash
cd /root/BEAR && python3 astronomer/backtest_1month.py
```
