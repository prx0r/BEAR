# GetXAPI Protocol

## The Rule

**Every API call in BEAR MUST go through `src.getxapi.GetXAPI`.**

No direct `httpx.get("https://api.getxapi.com/...")` anywhere else.

## Why

1. **Budget enforcement** — can't accidentally spend money
2. **Rate limiting** — prevents 429 errors
3. **Logging** — every call tracked in ledger
4. **Single source of truth** — costs, limits, auth in one place
5. **Reproducibility** — same code, same results

## How to Use

### Basic Search (most common)

```python
from src.getxapi import GetXAPI

with GetXAPI() as api:
    tweets = api.search(
        handle="Timeless_Crypto",
        since="2024-09-01",
        until="2024-09-08"
    )
    print(f"Got {len(tweets)} tweets")
```

### Full History

```python
with GetXAPI() as api:
    tweets = api.user_tweets(handle="Trader_XO", max_pages=200)
```

### Check Budget

```python
with GetXAPI() as api:
    print(f"Balance: ${api.balance():.2f}")
    api.status()
```

## Cost Reference

| Endpoint | Cost | What You Get |
|----------|------|--------------|
| advanced_search | $0.001/page | ~20 tweets matching query |
| user_tweets | $0.001/page | ~20 of user's tweets |
| user_tweets_complete | $0.003/page | tweets + replies + threads |
| tweet_detail | $0.001/tweet | full tweet with media |
| tweet_thread | $0.005/thread | complete thread |
| tweet_replies | $0.001/page | replies to a tweet |
| user_info | $0.001/call | profile info |

**Budget math:**
- 2yr history per account: ~100-200 pages = $0.10-0.20
- 5 accounts × 2yr: ~$0.50-1.00 total
- August snapshot per account: ~5 pages = $0.005
- 36 accounts × August: ~$0.18

## Rate Limits

- advanced_search: ~30 req/min (enforced by client)
- user_tweets: ~30 req/min
- General: don't exceed 100 req/min total

The client auto-enforces 2.1s between requests (~28 req/min).

## Pagination

Always paginate until `has_more == false`:

```python
cursor = None
while True:
    params = {"q": query, "product": "Latest"}
    if cursor:
        params["cursor"] = cursor
    
    data = api._request("/twitter/tweet/advanced_search", params)
    tweets = data.get("tweets", [])
    has_more = data.get("has_more")
    cursor = data.get("next_cursor")
    
    all_tweets.extend(tweets)
    
    if not has_more or not cursor:
        break
```

**Never stop after 2 pages.** Always complete pagination.

## Logging

Every call is logged to `data/budgets/api_ledger.jsonl`:

```json
{
  "timestamp": "2026-09-07T...",
  "endpoint": "/twitter/tweet/advanced_search",
  "cost_usd": 0.001,
  "elapsed_sec": 0.342,
  "cumulative_calls": 15,
  "cumulative_cost": 0.015
}
```

## Prohibited

These will be caught in code review:

```python
# WRONG — direct API call
import httpx
resp = httpx.get("https://api.getxapi.com/twitter/user/tweets", ...)

# RIGHT — use the module
from src.getxapi import GetXAPI
with GetXAPI() as api:
    tweets = api.user_tweets(handle="...")
```

```python
# WRONG — hardcoded API key
API_KEY = "get-x-api-..."

# RIGHT — vault or env
from src.getxapi import GetXAPI
api = GetXAPI()  # reads from vault automatically
```
