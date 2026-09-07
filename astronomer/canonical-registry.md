# Canonical X Account Registry

*Master list of all tracked accounts with data structures, filter rules, and scraping plans.*

---

## Account Schema

```json
{
  "handle": "string",
  "name": "string",
  "tier": "S|A|B|SKIP",
  "signal_type": "directional|levels|flow|structural|observation",
  "weight": float,
  "followers": int,
  "date_added": "ISO",
  "scrape_priority": int,
  
  "filter_rules": {
    "min_length": int,
    "exclude_keywords": [string],
    "require_asset": bool,
    "preferred_months": [string],
    "avoid_months": [string]
  },
  
  "performance": {
    "total_posts": int,
    "directional_signals": int,
    "win_rate_4h": float,
    "avg_return_4h": float,
    "sharpe": float,
    "last_updated": "ISO"
  },
  
  "scrape_plan": {
    "months_to_fetch": [string],
    "estimated_calls": int,
    "status": "pending|in_progress|complete"
  }
}
```

---

## Tier S — Primary Signal Sources

| Handle | Signal Type | Weight | Followers | Status |
|--------|-------------|--------|-----------|--------|
| @astronomer_zero | directional | 1.0 | 64,265 | ✅ Has data |
| @Timeless_Crypto | directional | 1.2 | 71,693 | ✅ SHORT validated |
| @exitpumpBTC | flow | 1.2 | 42,189 | ✅ Has data |
| @52kskew | flow | 1.2 | — | ✅ Has data |

## Tier A — Secondary Sources

| Handle | Signal Type | Weight | Followers | Status |
|--------|-------------|--------|-----------|--------|
| @Trader_XO | structural | 1.2 | 549,220 | ⚠️ Levels only |
| @Husslin_ | flow | 1.1 | — | ✅ Has data |
| @DeFiSquared | fundamental | 1.0 | — | ✅ Has data |
| @thiccyth0t | flow | 1.0 | — | ✅ Has data |
| @CryptoBheem | directional | 1.0 | 72,581 | ❌ Too sparse |
| @GreatMattsby | directional | 1.0 | 54,080 | ✅ Has data |
| @calvintsaikm | levels | 1.0 | — | ✅ Has data |
| @lBattleRhino | directional | 1.1 | 65,383 | ✅ Has data |

## Tier B — Context/Discovery

| Handle | Signal Type | Weight | Followers | Status |
|--------|-------------|--------|-----------|--------|
| @PriorXBT | microstructure | 0.3 | 1,148 | Context only |
| @0xLoris | MM intel | 0.3 | 14,792 | Context only |
| @macrocephalopod | systematic | 0.3 | 75,306 | Context only |
| @quant_arb | stat arb | 0.3 | 71,088 | Context only |
| @hftgod | HFT | 0.3 | 3,270 | Context only |
| @skyquake_1 | basis | 0.3 | — | Context only |
| @crypto_hades | HFT | 0.3 | — | Context only |

## Discovery Only — Binance Positions

| Handle | Weight | Why |
|--------|--------|-----|
| @0xPickleCati | 0.1 | #1 Binance all-time, X is Chinese commentary |
| @Shangus_Capital | 0.1 | Verified PnL, X is sparse |
| @BitcoinLiangGe | 0.1 | Lead portfolio, X is sparse |
| + 8 more | 0.1 | Similar pattern |

---

## Data Structures per Account

### Raw Data (immutable)
```
data/raw/{handle}_{month}.json
├── handle: string
├── tweets: array
│   ├── id: string
│   ├── text: string
│   ├── createdAt: string
│   ├── isReply: bool
│   ├── likeCount: int
│   ├── retweetCount: int
│   ├── viewCount: int
│   └── author: object
└── fetched_at: string
```

### Extracted Signals
```
data/extracted/{handle}_signals.json
├── signal_id: string (hash)
├── tweet_id: string
├── direction: LONG|SHORT
├── assets: [string]
├── levels: [float]
├── horizon: string
├── confidence: string
├── timestamp: string
└── source_text: string
```

### Outcomes
```
data/extracted/{handle}_outcomes.json
├── signal_id: string
├── entry_price: float
├── return_1h: float
├── return_4h: float
├── return_24h: float
├── direction_correct: bool
├── mfe: float
├── mae: float
└── regime: string
```

### Filter Rules
```
archive/filter_rules/{handle}.json
├── min_length: int
├── exclude_keywords: [string]
├── require_asset: bool
├── preferred_months: [string]
├── avoid_months: [string]
└── notes: string
```

---

## Scraping Plan

### Phase 1: Core (4 accounts × 24 months)
```
astronomer_zero:    Oct 2025 - Sep 2026 (need Oct-Apr)
Timeless_Crypto:    Oct 2025 - Sep 2026 (need Oct-May)
Trader_XO:          Oct 2025 - Sep 2026 (need Oct-Apr)
CryptoBheem:        Oct 2025 - Sep 2026 (need Oct-Apr)

Estimated: ~4,320 calls = $2.16
```

### Phase 2: Tier S (8 accounts × 12 months)
```
exitpumpBTC, 52kskew, PriorXBT, Husslin_,
DeFiSquared, thiccyth0t, 0xLoris, GreatMattsby

Estimated: ~4,320 calls = $2.16
```

### Phase 3: Tier A (remaining × 6 months)
```
calvintsaikm, lBattleRhino, CryptoBheem, etc.

Estimated: ~2,160 calls = $1.08
```

### Total
```
Phase 1 + 2 + 3 = ~10,800 calls = $5.40
Remaining after: ~29,215 calls for operations
```

---

## Automation Hooks

### Real-Time Monitoring (Pro plan feature)
```python
# Set up webhook for Tier S accounts
POST /twitter/monitor/webhook/create
  → url: https://our-server.com/webhook/x
  → signing_secret: auto-generated

POST /twitter/monitor/add
  → account: astronomer_zero
  → webhook_id: from above
  → tier: fast (2s latency)

# Receive tweets as webhooks (no polling needed)
POST https://our-server.com/webhook/x
  → tweet data
  → process signal
  → store to database
```

### Batch Backfill
```python
# Historical data acquisition
for account in core_accounts:
    for month in months_to_fetch:
        batch_scrape(account, month, max_calls=10)
        review_batch()
        log_results()
```

### Daily Monitoring
```python
# After backfill, switch to real-time
for account in tier_s_accounts:
    setup_monitor(account, webhook_url)
    # Tweets arrive automatically via webhook
```

---

*Registry version: 1.0 — 2026-09-07*
