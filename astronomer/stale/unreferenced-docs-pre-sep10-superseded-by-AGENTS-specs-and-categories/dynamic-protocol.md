# Dynamic Influencer Protocol

*One-day recon → one-week validation → one-month confirmation → full extraction.*

---

## The Process

```
DAY 1: RECON
  Fetch 1 day of posts
  Classify post types
  Measure signal density
  Decision: PROCEED or SKIP

WEEK 1: VALIDATION
  Fetch 1 week of posts
  Extract signals
  Match to price outcomes
  Decision: CONFIRM or SKIP

MONTH 1: CONFIRMATION
  Fetch 1 month of posts
  Full backtest
  Decision: FULL EXTRACTION or SKIP

FULL: EXTRACTION
  Fetch all available history
  Complete dataset
  Ongoing monitoring
```

## Step 1: Recon (Day 1)

**Cost:** 3 API calls = $0.003
**Time:** 5 minutes

### What to do:

```python
# Fetch 3 pages of recent tweets
tweets = fetch(handle, count=20, max_pages=3)

# Classify
replies = [t for t in tweets if t.get('isReply')]
standalone = [t for t in tweets if not t.get('isReply')]
media = [t for t in tweets if t.get('media')]

# Count signals
directional = count_directional(standalone)
structural = count_structural(standalone)

# Calculate density
signal_density = (directional + structural) / max(len(standalone), 1)
reply_ratio = len(replies) / max(len(tweets), 1)
media_ratio = len(media) / max(len(tweets), 1)
```

### Decision criteria:

| Metric | PROCEED | SKIP |
|--------|---------|------|
| Signal density | >20% | <10% |
| Standalone posts | >5 | <3 |
| Reply ratio | <80% | >90% |
| Language | English | Non-English |

### Output:

```json
{
  "handle": "new_account",
  "recon_date": "2026-09-07",
  "tweets_sampled": 60,
  "signal_density": 0.35,
  "reply_ratio": 0.45,
  "media_ratio": 0.30,
  "verdict": "PROCEED",
  "notes": "High signal density, good media ratio"
}
```

---

## Step 2: Validation (Week 1)

**Cost:** ~10 API calls = $0.01
**Time:** 30 minutes

### What to do:

```python
# Fetch 1 week of posts
tweets = fetch(handle, since=week_ago, until=today, max_pages=5)

# Full extraction
signals = extract_signals(tweets)
outcomes = match_to_prices(signals)

# Calculate metrics
win_rate = calculate_win_rate(outcomes)
avg_return = calculate_avg_return(outcomes)
signal_count = len(signals)
```

### Decision criteria:

| Metric | CONFIRM | SKIP |
|--------|---------|------|
| Signal count | >10 | <5 |
| Win rate (4h) | >50% | <45% |
| Avg return (4h) | >0% | <-0.1% |
| Media posts | >20% | <10% |

### Output:

```json
{
  "handle": "new_account",
  "validation_date": "2026-09-07",
  "week_tweets": 150,
  "signals": 25,
  "win_rate_4h": 0.58,
  "avg_return_4h": 0.0012,
  "verdict": "CONFIRM",
  "notes": "58% win rate, positive avg return"
}
```

---

## Step 3: Confirmation (Month 1)

**Cost:** ~30 API calls = $0.03
**Time:** 1 hour

### What to do:

```python
# Fetch 1 month of posts
tweets = fetch(handle, since=month_ago, until=today, max_pages=20)

# Full extraction + backtest
signals = extract_signals(tweets)
outcomes = match_to_prices(signals)

# Reputation scores
reputation = compute_reputation(outcomes)

# Regime analysis
regime_perf = analyze_by_regime(outcomes)
```

### Decision criteria:

| Metric | FULL EXTRACTION | SKIP |
|--------|-----------------|------|
| Signal count | >30 | <15 |
| Win rate (4h) | >52% | <48% |
| Avg return (4h) | >0.05% | <0% |
| Sharpe | >0.3 | <0 |
| Regime consistency | Works in 2+ regimes | Only 1 regime |

### Output:

```json
{
  "handle": "new_account",
  "confirmation_date": "2026-09-07",
  "month_tweets": 600,
  "signals": 75,
  "win_rate_4h": 0.56,
  "avg_return_4h": 0.0008,
  "sharpe": 0.45,
  "regime_perf": {
    "uptrend": 0.52,
    "range": 0.61,
    "downtrend": 0.48
  },
  "verdict": "FULL_EXTRACTION",
  "notes": "Consistent across regimes, positive Sharpe"
}
```

---

## Step 4: Full Extraction

**Cost:** ~72 API calls = $0.07 (per 12 months)
**Time:** 2 hours

### What to do:

```python
# Fetch all available history
for month in all_months:
    tweets = fetch(handle, since=month_start, until=month_end, max_pages=10)
    save_raw(tweets)
    dedup()

# Complete dataset
total = count_all_tweets(handle)
media = count_media(handle)
replies = count_replies(handle)

# Generate report
report = generate_extraction_report(handle)
```

### Output:

```json
{
  "handle": "new_account",
  "extraction_date": "2026-09-07",
  "total_tweets": 2264,
  "months": 12,
  "media_posts": 472,
  "replies": 1685,
  "signal_posts": 386,
  "cost": 0.11,
  "status": "COMPLETE"
}
```

---

## Training Runs (What We Learned)

### Run 1: Astronomer

| Metric | Value |
|--------|-------|
| Total tweets | 2,264 |
| Standalone | 26% |
| Replies | 74% |
| Media | 21% |
| Signal density | 67% (standalone) |
| Reply signal rate | 14% |

**Key insight:** 74% replies, but 14% of replies contain signals. Filter replies by signal content, not blindly.

### Run 2: Timeless

| Metric | Value |
|--------|-------|
| Total tweets | 214 |
| Standalone | 74% |
| Replies | 26% |
| Media | 62% |
| Signal density | 42% (standalone) |
| SHORT win rate | 55% at 4h |

**Key insight:** High media ratio (62%). Charts contain levels. SHORT signals are strongest.

### Run 3: XO

| Metric | Value |
|--------|-------|
| Total tweets | 81 |
| Standalone | 7% |
| Replies | 93% |
| Media | 17% |
| Signal density | N/A (almost all replies) |

**Key insight:** 93% replies. His alpha is ENTIRELY in replies. Cannot filter replies for this account.

---

## The Dynamic Protocol

### For ANY new influencer:

```python
def dynamic_protocol(handle):
    """Run the full protocol for a new influencer."""
    
    # Step 1: Recon
    recon = run_recon(handle)
    if recon['verdict'] == 'SKIP':
        return {'status': 'skipped', 'reason': 'low signal density'}
    
    # Step 2: Validation
    validation = run_validation(handle)
    if validation['verdict'] == 'SKIP':
        return {'status': 'skipped', 'reason': 'poor performance'}
    
    # Step 3: Confirmation
    confirmation = run_confirmation(handle)
    if confirmation['verdict'] == 'SKIP':
        return {'status': 'skipped', 'reason': 'not consistent'}
    
    # Step 4: Full extraction
    extraction = run_full_extraction(handle)
    
    return {
        'status': 'complete',
        'handle': handle,
        'recon': recon,
        'validation': validation,
        'confirmation': confirmation,
        'extraction': extraction,
    }
```

### Filter rules per account type:

| Account Type | Filter Strategy |
|--------------|-----------------|
| High standalone (Astronomer) | Keep standalone, filter replies by signal |
| High media (Timeless) | Keep all, extract chart levels |
| High replies (XO) | Keep replies with signal keywords |
| Low volume (Bheem) | Keep everything, small sample |

---

## Cost Summary

| Phase | Calls | Cost | Time |
|-------|-------|------|------|
| Recon | 3 | $0.003 | 5 min |
| Validation | 10 | $0.010 | 30 min |
| Confirmation | 30 | $0.030 | 1 hour |
| Full extraction | 72 | $0.072 | 2 hours |
| **TOTAL** | **115** | **$0.115** | **~4 hours** |

**Per influencer: $0.115 for complete 12-month dataset.**

---

*Protocol version: 1.0 — Validated on astronomer, timeless, xo*
