# API Strategy — How to Scrape Properly

*Every API call must be justified. Never fetch 100 posts without understanding the account first.*

---

## The Problem

Raw API calls return noise. Most posts from any account are:
- Replies to other people
- Retweets
- Off-topic commentary
- Engagement bait

The signal is in the **10-20% of posts that contain actual market observations or trade calls.**

## The Process: Scout → Validate → Batch → Analyze

### Step 1: SCOUT (3 calls max)

Before committing to scraping an account, do a **3-call scout**:

```
CALL 1: from:{handle} (Latest, count=10)
CALL 2: from:{handle} (Top, count=10)
CALL 3: from:{handle} since:2026-01-01 (oldest available)
```

**Purpose:** Understand the account's post style.

### Step 2: VALIDATE (manual review of 10 posts)

From the 30 posts returned by the scout, manually review:

| Question | What to look for |
|----------|------------------|
| What % are replies? | >50% replies = low standalone signal |
| What % are retweets? | >20% retweets = low original content |
| Do they post trade calls? | Explicit LONG/SHORT with levels |
| Do they post observations? | CVD, OI, flow data without explicit call |
| Do they post charts? | Visual analysis (need vision extraction) |
| What language? | Non-English = needs translation/exclusion |
| What assets? | BTC only? Alts? Specific tokens? |
| What timeframes? | Scalps (1-4h)? Swing (1-7d)? Positional? |
| Engagement pattern? | High engagement = crowd-following, not alpha |

### Step 3: SCORING (rate the account)

```
SIGNAL_DENSITY = (directional_posts + observation_posts) / total_posts

if SIGNAL_DENSITY > 0.3:  → HIGH SIGNAL → batch scrape
if SIGNAL_DENSITY 0.1-0.3: → MEDIUM → selective scrape
if SIGNAL_DENSITY < 0.1:  → LOW → skip or archive only
```

### Step 4: BATCH (only if validated)

```
FOR high-signal accounts:
  - Fetch 1 month at a time
  - Use since:/until: date chunks (not cursor chains)
  - Max 3 pages per chunk (60 posts)
  - Dedup against existing data
  - Log every call to fetch_log.jsonl

FOR medium-signal accounts:
  - Fetch 1 week at a time
  - Max 1 page per chunk (20 posts)
  - Only if we need more data for a specific experiment
```

### Step 5: EXTRACT (structured parsing)

Never store raw text as "the signal." Extract structured data:

```
EXTRACT per post:
  - direction (LONG/SHORT/NEUTRAL)
  - assets (BTC, ETH, SOL...)
  - levels (entry, target, stop)
  - horizon (1h, 4h, 24h, swing)
  - confidence (high/medium/low)
  - is_conditional (if/when statement)
  - is_reply (context from thread)
```

### Step 6: MATCH (to price outcomes)

```
FOR each extracted signal:
  - Get price at signal_time + latency (1-5 min)
  - Compute returns at 1h, 4h, 24h
  - Compute MFE, MAE
  - Determine if direction was correct
  - Store in signal_outcomes.parquet
```

---

## Account Classification

### Tier S (scrape everything)

| Account | Signal Density | Why |
|---------|---------------|-----|
| @astronomer_zero | High | Regular directional calls, levels, transparent |
| @Timeless_Crypto | High | Conviction calls, specific levels |
| @exitpumpBTC | High | Real-time flow observations |
| @52kskew | High | Order flow, machine-extractable |

### Tier A (selective scrape)

| Account | Signal Density | Why |
|---------|---------------|-----|
| @Trader_XO | Medium | Structural posts, not keyword-extractable |
| @CryptoBheem | Low | Barely posts, BTC only |
| @Husslin_ | Medium | Position info, but sparse |
| @DeFiSquared | Medium | Token fundamentals, sparse |

### Tier B (archive only)

| Account | Signal Density | Why |
|---------|---------------|-----|
| @PriorXBT | Low | Replies only, microstructure context |
| @macrocephalopod | Low | Institutional discussion |
| @quant_arb | Low | Theory, not calls |

### Skip

| Account | Why |
|---------|-----|
| @eliz883 | Charts+emojis, no text to extract |
| @Oldman__Crypto | Mixed commentary |
| Any account with <10% signal density | Not worth the API cost |

---

## The Audit Loop

After every batch scrape:

```
1. COUNT: How many posts fetched?
2. FILTER: How many after reply/retweet removal?
3. EXTRACT: How many have direction/levels?
4. MATCH: How many matched to price outcomes?
5. SCORE: What's the win rate?
6. ADJUST: Update account weight based on results
```

If an account consistently produces low signal density OR poor win rates:
- Move to Tier B (archive only)
- Stop wasting API calls
- Document why in accounts.json

---

## Budget Rules

| Rule | Implementation |
|------|----------------|
| Scout first | 3 calls before committing to batch |
| Max 3 pages per chunk | Prevents over-fetching |
| Dedup before fetch | Check cache, skip if already have |
| Log every call | fetch_log.jsonl |
| Budget guard | Check balance before each batch |
| Hard stop | Stop when balance < $0.01 |

---

## Adding New Influencers

```
1. Scout (3 calls)
2. Review 10 posts manually
3. Score signal density
4. If HIGH: batch 1 month
5. Extract signals
6. Match to outcomes
7. Compute win rate
8. Update accounts.json
9. Add to backtest universe
```

**Never skip the scout.** The cost of 3 calls ($0.003) is nothing compared to wasting 30 calls on a low-signal account.
