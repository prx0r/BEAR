# X/Twitter API Research — September 2026 (Updated)

**Date:** 2026-09-07
**Context:** Evaluating X/Twitter API options for agent-based social data ingestion
**Update:** Minimum spend requirements change ranking materially

---

## TL;DR

Build a provider-agnostic `XReader` interface. Start with TwitterAPI.io ($0 minimum), benchmark GetXAPI (free 2k tweets), use SocialData as fallback ($1 deposit works), Apify/Xquik as zero-cost sandbox. Skip Xquik direct ($20/mo minimum kills tiny usage).

## Provider Comparison (With Minimums)

| Provider | Cost/1k | Min to Test | Recurring? | Credits Expire | Best For |
|----------|---------|-------------|------------|----------------|----------|
| **TwitterAPI.io** | **$0.15** | **None** | **No** | **Never** | Production default |
| **GetXAPI** | **$0.05** | $0 free, then $10 | No | Never | Benchmark/cheap volume |
| **SocialData.tools** | **$0.20** | Any deposit | No | Never | Fallback/backup |
| **Apify/Xquik** | **$0.15 + platform** | $0 ($5/mo free) | No (Apify resets) | Apify resets monthly | Zero-cost sandbox |
| **Xquik direct** | **$0.12-0.15** | **$20/month** | **Yes** | Monthly reset | Skip for tiny usage |
| Official X | **~$5/1k** | — | — | — | Never |

## Provider Details

### 1. TwitterAPI.io (Recommended Primary)

```bash
curl --get 'https://api.twitterapi.io/twitter/tweet/advanced_search' \
  -H 'X-API-Key: YOUR_KEY' \
  --data-urlencode 'query=AI agents lang:en' \
  --data-urlencode 'queryType=Latest'
```

- **No minimum spend, pay-as-you-go**
- Credits never expire
- Manual top-ups can be "any USD amount"
- WARNING: X pagination is problematic, use `since_time`/`until_time`, keep ≤20 tweets per request
- Status: 99.9% uptime

**Cost at volume:**
- 100 tweets = $0.015
- 1,000 = $0.15
- 10,000 = $1.50
- 100,000 = $15

### 2. GetXAPI (Best Free Benchmark)

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "https://api.getxapi.com/twitter/tweet/advanced_search?q=from:elonmusk&product=Latest"
```

- **$0.10 free credit** (no card required) → ~2,000 tweets
- Then $10 minimum top-up
- Credits never expire
- $0.05/1k after free credit
- At $10 deposit: ~200,000 tweets
- Newer but docs updated Jul/Aug 2026

**Verdict:** Test immediately with free credit. If search quality is good, price is insane.

### 3. SocialData.tools (Best Fallback)

```bash
curl "https://api.socialdata.tools/twitter/search?query=from%3AOpenAI&type=Latest" \
  -H "Authorization: Bearer $SOCIALDATA_API_KEY"
```

- **Deposit any amount, no minimum**
- Credits never expire
- $0.20/1k tweets
- No subscription, no plans, no seats
- Read-only, no X account connection
- Supports: search, posts, timelines, threads, replies, communities, lists, Spaces, followers

**Verdict:** Throw $1-2 into it and leave dormant as backup.

### 4. Apify/Xquik (Zero-Cost Sandbox)

```json
{
  "searchTerms": ["(AI agent OR coding agent) lang:en -filter:nativeretweets"],
  "maxItems": 1000,
  "queryType": "Latest"
}
```

- Apify Free: **$5/month platform usage for $0**
- Xquik actor: $0.15/1k results + platform usage
- Can do surprising amount of scraping on $0/month
- Extra indirection: code → start Actor → Actor runs → dataset → fetch results

**Verdict:** Great for experiments, bad for direct code integration.

### 5. Xquik Direct (Skip)

- **$20/month minimum** for Starter tier (140k credits)
- Unused monthly credits don't carry over
- $10 minimum for additional top-ups
- At meaningful volume it's competitive, but silly at $0.50-5/month usage

**Exception:** 31 read-only endpoints support Machine Payments Protocol (USDC), no subscription. Interesting for autonomous economic agents but not worth $20/mo just to save.

### 6. Avoid Twikit/Twscrape

- Technically $0 but: accounts, cookies, proxies, bans, Cloudflare, endpoint changes, constant maintenance
- 2026 GitHub issues: login failures, Cloudflare IP blocking, missing fields
- Not worth saving $0.15/1k

## Recommended Architecture

```
XReader
 ├── search(query, limit, cursor)
 ├── userPosts(username, limit, cursor)
 ├── getPost(id)
 ├── getThread(id)
 └── getReplies(id)
```

Routing:
```
PRIMARY       TwitterAPI.io      ($0 min, $0.15/1k)
FREE_TEST     GetXAPI            ($0 free = 2k tweets, then $10)
FALLBACK      SocialData.tools   ($1 deposit works, $0.20/1k)
SANDBOX       Apify/Xquik        ($0/mo via free tier)
SKIP          Xquik direct       ($20/mo minimum)
```

## Implementation Plan

1. Register TwitterAPI.io (no card required)
2. Test GetXAPI with free $0.10 credit (~2k tweets)
3. Register SocialData with $1 deposit as backup
4. Build `XReader` interface with provider abstraction
5. Run same 100 queries against all three
6. Measure recall/latency/result overlap
7. Choose primary based on API quality, not price

## Key Insight

At these prices, **choosing based on API quality (recall, latency, search depth) is more important than headline $/1k**. The cost difference between providers is negligible vs. the value of reliable data.

---

*Sources: TwitterAPI.io, Xquik, Apify, SocialData, GetXAPI, Reddit dev discussions, GitHub issues*
