# API Budget Intelligence Engine

*Batch processing with review, logging, and filter learning.*

---

## Core Principle

**Never fetch blindly. Every batch must be reviewed before the next one runs.**

```
BATCH(10 calls) → REVIEW → LOG → LEARN → NEXT BATCH
```

## Batch Size Rules

| Rule | Value | Why |
|------|-------|-----|
| Max calls per batch | 10 | Forces review between batches |
| Max posts per batch | ~180 (10 calls × 18 posts/call) | Manageable for manual review |
| Review window | After each batch | Catch issues early |
| Budget floor | $5.00 remaining | Never drain completely |

## The Loop

```
1. PLAN: What do we need? Which accounts? What date range?
2. FETCH: 10 calls max
3. REVIEW: 
   - How many posts returned?
   - How many are replies/retweets (noise)?
   - How many have signal content?
   - Any API errors?
4. EXTRACT: Parse structured signals
5. MATCH: Connect to price outcomes
6. JUDGE: Was this batch useful?
7. LOG: Record everything
8. LEARN: Update filter rules
9. DECIDE: Fetch more or stop?
```

## Per-Influencer Filter Learning

After each batch, record:

```json
{
  "handle": "astronomer_zero",
  "batch_id": "batch_001",
  "date_range": ["2026-08-01", "2026-08-31"],
  "calls_used": 3,
  "posts_returned": 60,
  "posts_after_filter": 27,
  "filter_stats": {
    "replies_removed": 31,
    "retweets_removed": 0,
    "min_length_removed": 2
  },
  "signal_stats": {
    "directional_posts": 16,
    "observation_posts": 5,
    "off_topic_posts": 6
  },
  "signal_density": 0.35,
  "quality_judgment": "HIGH",
  "notes": "Posts are mostly standalone directional calls. Good for signal extraction."
}
```

## Global Filter Rules (learned from batches)

After N batches, we can compute:

```
最佳reply_filter: exclude if isReply=true → removes X% noise
最佳retweet_filter: exclude if starts with "RT @" → removes Y% noise  
最佳length_filter: exclude if len(text) < 20 → removes Z% noise
最佳time_filter: only keep posts between HH:MM and HH:MM → removes W% noise
```

## Archive Pile Structure

```
astronomer/archive/
├── batches/
│   ├── batch_001/
│   │   ├── fetch_log.json       # API calls made
│   │   ├── raw_posts.json       # Posts returned
│   │   ├── filtered_posts.json  # After noise removal
│   │   ├── signals.json         # Extracted signals
│   │   ├── outcomes.json        # Matched to prices
│   │   ├── review.md            # Manual review notes
│   │   └── learnings.json       # Filter rules learned
│   ├── batch_002/
│   │   └── ...
│   └── ...
├── filter_rules/
│   ├── global.json              # Global filter rules
│   └── {handle}.json            # Per-account filter rules
└── reviews/
    ├── batch_001_review.md
    └── ...
```

## The Review Checklist

After each batch:

```
□ Posts returned: ___ (expected ~18)
□ Replies removed: ___
□ Retweets removed: ___
□ Short posts removed: ___
□ Posts with signal content: ___
□ Posts with direction: ___
□ Posts with levels: ___
□ API errors: ___
□ Cost: $___
□ Signal density: ___%
□ Quality judgment: HIGH / MEDIUM / LOW
□ Notes: ___
```

## Judge Criteria

| Metric | HIGH | MEDIUM | LOW |
|--------|------|--------|-----|
| Signal density | >30% | 10-30% | <10% |
| Directional posts | >5 per batch | 2-5 per batch | <2 per batch |
| Level posts | >3 per batch | 1-3 per batch | <1 per batch |
| Reply ratio | <30% | 30-60% | >60% |

## Budget Intelligence

Track per batch:

```
calls_used
posts_returned
posts_per_call (efficiency)
cost_per_signal
signal_density
quality_score (1-5)
```

Over time, compute:

```
avg_posts_per_call by account
avg_signal_density by account
best_time_to_fetch by account
worst_time_to_fetch by account
```

This tells us:
- Which accounts are worth fetching
- When to fetch them
- How many calls to allocate
