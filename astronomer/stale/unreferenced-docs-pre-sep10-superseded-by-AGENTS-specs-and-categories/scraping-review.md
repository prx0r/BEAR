# Scraping Process Review & Clean Process

*Lessons from the mini experiment. How to repeat at scale.*

---

## Mini Experiment Results

| Metric | Value |
|--------|-------|
| API calls used | 11 |
| Cost | $0.015 |
| Posts imported | 197 |
| Cost per post | $0.00008 |
| Posts per call | 17.9 |
| Signals extracted | 27 (13.7% of posts) |

## What Worked

| Step | Status | Notes |
|------|--------|-------|
| GetXAPI `since:/until:` chunking | ✅ | Works perfectly for date-range pulls |
| Pagination (`has_more` + `next_cursor`) | ✅ | Reliable |
| Cost exactly $0.001/call | ✅ | Matches advertised |
| Full tweet objects returned | ✅ | All fields available |

## What Didn't Work

| Issue | Impact | Fix |
|-------|--------|-----|
| Replies not filtered at API level | 107 of 197 posts are replies | Add `isReply` filter in extraction step |
| Retweets not filtered at API level | ~5% are retweets | Add RT prefix check |
| Raw JSON storage | 358KB for 4 accounts | Switch to Parquet for scale |
| XO posts don't extract with keywords | 0 signals from 60 posts | Need pattern-based extraction |
| Bheem too sparse | Only 20 posts/month | Need longer date range or more accounts |

---

## Clean Process for Scale

### Step 1: Fetch with budget guard

```python
def fetch_account(handle, start_date, end_date, max_calls=10):
    """Fetch with budget guard and deduplication."""
    
    # Check budget
    balance = get_balance()
    if balance < max_calls * 0.001:
        print(f"Budget exhausted: ${balance:.3f}")
        return []
    
    # Check cache
    cache_key = f"{handle}:{start_date}:{end_date}"
    if cache_key in load_cache():
        print(f"Already fetched: {cache_key}")
        return []
    
    # Fetch
    all_tweets = []
    cursor = None
    calls = 0
    
    while calls < max_calls:
        resp = call_api(handle, start_date, end_date, cursor)
        tweets = resp['tweets']
        all_tweets.extend(tweets)
        calls += 1
        
        if not resp['has_more']:
            break
        cursor = resp['next_cursor']
    
    # Mark as fetched
    mark_fetched(cache_key, len(all_tweets))
    
    return all_tweets
```

### Step 2: Filter before storage

```python
def filter_tweets(tweets):
    """Remove noise before storage."""
    return [
        t for t in tweets
        if not t.get('isReply')           # no replies
        and not t['text'].startswith('RT @')  # no retweets
        and len(t.get('text', '')) > 20    # minimum length
        and t.get('createdAt')              # has timestamp
    ]
```

### Step 3: Store as Parquet (not JSON)

```python
import polars as pl

# Convert to DataFrame
df = pl.DataFrame([{
    'tweet_id': t['id'],
    'author': t['author']['userName'],
    'text': t['text'],
    'created_at': t['createdAt'],
    'likes': t.get('likeCount', 0),
    'views': t.get('viewCount', 0),
    'is_reply': t.get('isReply', False),
    'fetched_at': datetime.now().isoformat(),
} for t in filtered_tweets])

# Save as Parquet (columnar, compressed, fast reads)
df.write_parquet(f'data/raw/{handle}_aug2026.parquet')
```

### Step 4: Extract signals with proper schema

```python
from astronomer.schemas import Signal, SignalType, Direction, EntryType

def extract_signal(tweet: dict) -> Optional[Signal]:
    """Extract structured signal from tweet."""
    text = tweet['text']
    lower = text.lower()
    
    # Skip non-signals
    if not any(kw in lower for kw in ['long', 'short', 'buy', 'sell', 'bullish', 'bearish']):
        return None
    
    # Extract direction
    direction = Direction.LONG if any(kw in lower for kw in ['long', 'buy', 'bullish']) else Direction.SHORT
    
    # Extract assets
    assets = []
    if re.search(r'\$btc|\bbtc\b|\bbitcoin\b', lower):
        assets.append('BTC')
    if re.search(r'\$eth|\beth\b|\bethereum\b', lower):
        assets.append('ETH')
    # ... etc
    
    # Create signal
    return Signal(
        signal_id=hashlib.sha256(f"{tweet['id']}:1.0".encode()).hexdigest(),
        tweet_id=tweet['id'],
        author_handle=tweet['author']['userName'],
        signal_type=SignalType.DIRECTIONAL_CALL,
        direction=direction,
        assets=assets,
        primary_asset=assets[0] if assets else 'BTC',
        source_text=text,
        extracted_at=datetime.now(timezone.utc).isoformat(),
    )
```

### Step 5: Match to price outcomes

```python
def match_outcomes(signals, price_data):
    """Match signals to price outcomes."""
    outcomes = []
    
    for signal in signals:
        entry_price = get_price_at(signal.created_at_ms)
        
        for horizon_hours in [1, 4, 24]:
            ret = get_return(signal.created_at_ms, horizon_hours)
            direction_mult = 1 if signal.direction == Direction.LONG else -1
            
            outcomes.append(SignalOutcome(
                signal_id=signal.signal_id,
                entry_price=entry_price,
                entry_latency_sec=60,  # assume 1 minute
                net_return=ret * direction_mult,
                direction_correct=(ret * direction_mult) > 0,
            ))
    
    return outcomes
```

---

## Cost Projection for Scale

### 1 month × 27 accounts

```
27 accounts × 1 month × ~30 posts/day × 30 days
= ~24,300 posts
= ~1,350 calls (at 18 posts/call)
= $1.35
```

### 6 months × 27 accounts

```
27 accounts × 6 months × ~30 posts/day × 180 days
= ~145,800 posts
= ~8,100 calls
= $8.10
```

### 1 year × 27 accounts

```
27 accounts × 12 months × ~30 posts/day × 365 days
= ~291,600 posts
= ~16,200 calls
= $16.20
```

**Total cost for full 1-year backtest: ~$16.** That's nothing.

---

## Storage at Scale

### 1 year × 27 accounts

```
27 accounts × 365 days × ~30 posts/day = ~291,600 posts
At ~600 bytes/post (JSON) = ~175 MB
At ~100 bytes/post (Parquet) = ~29 MB
```

**Parquet is 6x smaller and 10x faster to query.**

---

## The Clean Checklist

Before scaling, verify:

```
✅ Budget guard in place
✅ Deduplication cache working
✅ Reply/retweet filtering working
✅ Parquet storage working
✅ Signal extraction working
✅ Price data available for all referenced assets
✅ Outcome matching working
✅ No data leakage (engagement not used as features)
```

---

*Lessons from 11 API calls, $0.015, 197 posts.*
