# BEAR Signal Intelligence — Revised Plan

*After peer review. Key change: capture first, model later. Lossless corpus, then query.*

---

## The Core Insight

> **Do not filter during ingestion. Build a lossless X corpus first, then make every later interpretation reproducible from it.**

Our previous approach was wrong:
- We filtered for "long/short" during extraction → lost 76% of posts
- We used keyword matching → missed structural observations
- We didn't preserve threads, quotes, media, or Articles
- We stored engagement as historical features (leakage!)

The correct approach:
- **Ingest everything.** Every reply, every quote, every thread continuation.
- **Store engagement as snapshots.** Never use current likes/views as historical features.
- **Enrich only what can't be reconstructed.** Threads, quote sources, Articles, media.
- **Filter during analysis, not ingestion.**

---

## Revised Architecture

### Stage 1: Identity Resolution

```python
# For each target account
GET /twitter/user/info?userName=Trader_XO
GET /twitter/user/user_about?userName=Trader_XO

# Store:
{
  "author_id": "123456789",          # PERMANENT - use this everywhere
  "current_username": "Trader_XO",    # Can change
  "display_name": "Trader XO",
  "followers": 549220,
  "following": 892,
  "created_at": "2021-...",
  "bio": "...",
  "profile_image_url": "...",
  "resolved_at": "2026-09-07T..."
}
```

**Key:** Use `author_id` as primary key everywhere. Usernames change. IDs don't.

### Stage 2: Recent Truth Set

```python
# High-quality recent corpus (last 30 days)
GET /twitter/user/tweets/complete?userId=123456789&count=20

# This returns:
# - Original tweets
# - Replies
# - Self-thread expansions
# - Up to ~3,200 items (X's timeline window)
```

**Why:** This is the most complete recent dataset. Use it as ground truth to validate Advanced Search coverage.

### Stage 3: Historical Archive (Adaptive Date Chunks)

```python
# NOT this (unreliable deep pagination):
GET /twitter/user/tweets?userName=Trader_XO&cursor=...

# THIS (date-chunked Advanced Search):
GET /twitter/tweet/advanced_search?q=from:Trader_XO since:2024-01-01 until:2024-02-01

# Adaptive splitting:
# if pages > 4: split window in half
# if pages <= 1: merge with adjacent window
# always dedupe by tweet_id
```

**Key:** Advanced Search + date chunks is more reliable than cursor pagination for historical data.

### Stage 4: Context Enrichment

```python
# Self-threads (when isReply && author_id == parent_author_id)
GET /twitter/tweet/thread?id=<tweet_id>  # $0.005/call

# Quote context
# Already in tweet object as quoted_tweet

# Reply parents
# Already in tweet object as inReplyToId

# X Articles
GET /twitter/article/get?id=<wrapper_tweet_id>  # $0.001/call

# Media preservation
# Download images, compute SHA256, store to object storage
```

### Stage 5: Forward Capture (Monitoring)

```python
# Set up NOW — creates pristine point-in-time dataset
POST /twitter/monitor/webhook/create → webhook_id
POST /twitter/monitor/add → account=Trader_XO, tier=fast

# Every future tweet arrives at our webhook within 2-15 seconds
# Even if trader deletes it 2 hours later, we have it
```

---

## Critical Design Decisions

### 1. Engagement is a SNAPSHOT, not a feature

```python
# WRONG (leakage!)
tweet.likes = 9500  # This is TODAY's count, not when posted

# RIGHT (two separate records)
tweet:
  tweet_id, created_at, text, author_id, ...

tweet_metrics_snapshot:
  tweet_id, observed_at, likes, views, quotes, bookmarks
```

**Why:** If a tweet from Jan 2024 has 9,500 likes today, those likes accumulated over 20 months. Using them as a feature leaks future information.

### 2. Raw archive is immutable

```
raw/getxapi/
  <job_id>/
    <request_id>.json.gz
    
Manifest:
  endpoint, params, cursor, window_start, window_end,
  requested_at, received_at, http_status, response_sha256,
  item_count, has_more, next_cursor
```

**Why:** Raw data is the ground truth. If we normalize wrong, we can always re-normalize from raw.

### 3. Dual-endpoint completeness check

```python
# For each account, compare:
A = IDs from /user/tweets/complete (recent 30 days)
B = IDs from date-chunked advanced_search (recent 30 days)

# Calculate:
# A ∩ B = both found
# A - B = only in complete
# B - A = only in advanced_search

# If disagreement > 5%, flag for review
```

**Why:** Two independent extraction paths should agree. If they don't, one is broken.

### 4. Threads are first-class

```python
# When we see:
isReply = true AND author_id == in_reply_to_user_id

# Fetch full thread:
GET /twitter/tweet/thread?id=<tweet_id>

# Store as:
thread:
  conversation_id, author_id, root_tweet_id,
  tweets: [{id, text, created_at, ...}],
  thread_length, complete
```

**Why:** A trader's thesis often spans 5-10 posts. The full thread is the signal, not individual posts.

### 5. X Articles are mandatory to capture

```python
# Detect article wrapper:
if "tweet.type" == "article" or "tweet.article" exists:
    GET /twitter/article/get?id=<tweet_id>
    # Store full article content
```

**Why:** Traders put real theses in Articles. The wrapper tweet is just "My thoughts on $TAO 👇" — the actual signal is in the Article.

---

## What Changes From Previous Plan

| Old Approach | New Approach |
|--------------|--------------|
| Filter for "long/short" during extraction | Ingest everything, filter later |
| Use /user/tweets for history | Use /tweet/advanced_search with date chunks |
| Store likes as historical features | Store as timestamped snapshots |
| Ignore replies | Store replies with conversation context |
| Ignore threads | First-class thread resolution |
| Ignore media | Archive images with SHA256 |
| Ignore Articles | Detect and fetch full Articles |
| No completeness check | Dual-endpoint overlap verification |
| No raw archive | Immutable raw + normalized tables |

---

## Implementation Order

### Step 1: Set up monitoring (TODAY)
- Create webhook for Tier S accounts
- Start capturing forward tweets
- This creates a pristine dataset from today onward

### Step 2: Resolve all target accounts (TODAY)
- Get permanent userId for each account
- Snapshot current profile
- Store in x_accounts table

### Step 3: Pull recent truth set (TODAY)
- /user/tweets/complete for each account
- This gives us ground truth for validation

### Step 4: Historical archive (WEEK 1)
- Date-chunked Advanced Search for 24 months
- Adaptive window splitting
- Dedupe by tweet_id
- Verify with completeness check

### Step 5: Enrich (WEEK 2)
- Self-threads via /tweet/thread
- Quote context from tweet objects
- X Articles via /article/get
- Media download + SHA256

### Step 6: Store (WEEK 2)
- Raw archive (immutable)
- Normalized tables (x_posts, x_post_entities, x_post_edges, etc.)
- Engagement snapshots (not features)
- Completeness report

### Step 7: THEN extract and backtest (WEEK 3+)
- Only after corpus is frozen
- Reproducible from raw data
- Every interpretation versioned

---

## Budget Impact

| Item | Old Cost | New Cost | Why |
|------|----------|----------|-----|
| Historical backfill | $5.40 | ~$10 | More calls for completeness |
| Monitoring | $0 | $19/mo | Pro plan includes basic |
| Thread enrichment | $0 | ~$2 | For high-value signals |
| Article capture | $0 | ~$0.50 | For article wrappers |
| **Total first month** | **$5.40** | **~$31.50** | |

**Still well within $40 budget.** And we get a much better dataset.

---

## The One-Page Summary (Revised)

```
WHAT: Lossless X signal corpus + real-time capture
HOW: Capture first → Normalize later → Extract → Backtest
WHY: Every interpretation must be reproducible from raw data

ARCHITECTURE:
  raw/     → immutable API responses
  normalized/ → analytical tables
  extracted/  → signals + outcomes
  reputation/ → author scores

KEY DECISIONS:
  - author_id (not username) as primary key
  - Engagement as snapshots, not features
  - Threads/quotes/Articles as first-class records
  - Dual-endpoint completeness verification
  - Adaptive date-window historical extraction

BUDGET:
  Historical: ~$10
  Monitoring: $19/mo (Pro plan)
  Total first month: ~$31.50
  Remaining: ~$8.50
```

---

*This is the revised plan. The key change: lossless capture first, modeling later.*
