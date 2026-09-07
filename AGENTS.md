# AGENTS.md — BEAR Signal Intelligence Operating Manual

*How to manage this system as a business. Every procedure is agent-executable.*

---

## ⚠️ CRITICAL SECURITY RULES

### RULE 0: NEVER HARDCODE API KEYS OR SECRETS

**Incident: 2026-09-07**

An agent hardcoded API keys in 7 files and pushed to GitHub. GitHub secret scanning rejected the push. Keys are now in git history forever. User had to spend 30+ minutes cleaning up.

**The rules:**

1. **NEVER** put API keys, tokens, or secrets in `.py`, `.md`, or `.json` files
2. **ALWAYS** use `.env` for secrets
3. **ALWAYS** add `.env` to `.gitignore` BEFORE first commit
4. **Before ANY commit**, run: `grep -r "sk_live\|AKIA\|GOCSPX\|cfat_\|get-x-api-" --include="*.py" --include="*.md" --include="*.json" .`
5. **If you find a key**: STOP. Remove it. Put it in `.env`. Then commit.

**Correct pattern:**
```python
# WRONG - NEVER DO THIS
API_KEY = "get-x-api-0d101a57d43f429a69ff8dd821186eeb2f889406859be720"

# RIGHT
import os
API_KEY = os.environ.get("GETXAPI_KEY")
```

---

## Critical Architecture Rules

### RULE 1: Raw Before Filter

**Never filter during ingestion.** Store everything, filter during analysis.

```
GetXAPI response → raw JSON.zst → normalize → posts.parquet → derived views
```

Never throw away a tweet you've paid to acquire. A reply may contain a signal because the ticker was in its parent. A repost can mean endorsement. Filter for analysis, never filter the source corpus.

### RULE 2: No Selection Bias in Historical Coverage

For each target account: fetch full contiguous history. Don't skip months because "May looked promotional." Missing periods = NO_DATA, not excluded.

### RULE 3: Engagement is a Snapshot, Not a Feature

```
posts: tweet_id, author_id, text, created_at, ...
post_metric_snapshots: tweet_id, observed_at, likes, views, ...
```

Never use current likes/views as historical features. They leak future information.

### RULE 4: Use author_id, Not Username

Usernames change. IDs don't. Primary key everywhere = author_id.

### RULE 5: Check for Secrets Before EVERY Commit

```bash
grep -r "sk_live\|AKIA\|GOCSPX\|get-x-api-\|cfat_" --include="*.py" --include="*.md" --include="*.json" .
```

If found → STOP → remove → .env → commit.

### RULE 6: Check free -h before heavy jobs

---

## Vision

**BEAR is a signal intelligence business.**

We don't trade. We **research** which information sources have measurable predictive power, then build systems that exploit those sources.

The output is not "copy trade Astronomer." The output is:

> "Astronomer's BTC SHORT calls at 9am UTC have a 56% win rate at 4h with +0.15% avg return, but only when BTC is in DETERIORATION regime and funding is positive."

That conditional intelligence is the product.

## The Business Model

```
SCRAPE → EXTRACT → BACKTEST → RANK → ALLOCATE → TRACK → ADJUST
```

Each step has defined inputs, outputs, and quality gates.

### Revenue Model

1. **Internal alpha:** Use signals to trade on Hyperliquid (paper → live)
2. **Signal subscription:** Package ranked signals for other traders
3. **Research licensing:** Sell the backtest dataset to quant funds
4. **API access:** Let others query our reputation database

### Cost Structure

| Cost | Monthly | Annual |
|------|---------|--------|
| GetXAPI | $1-5 | $12-60 |
| Binance data | $0 | $0 |
| Hyperliquid data | $0 | $0 |
| Compute | ~$10 | ~$120 |
| **Total** | **~$15** | **~$180** |

At $0.05/1K tweets, we can scrape 20 accounts × 12 months for ~$5.

---

## Agent Procedures

### Procedure: ADD_NEW_INFLUENCER

```
INPUT: X handle to evaluate

STEPS:
1. SCOUT
   - Fetch 3 pages of tweets (3 API calls)
   - Store in data/raw/{handle}_scout.json
   
2. CLASSIFY
   - Count replies, retweets, standalone posts
   - Count directional calls (LONG/SHORT)
   - Count observations (flow, levels, regime)
   - Count off-topic posts
   - Compute signal_density = (directional + observations) / total
   
3. DECIDE
   IF signal_density > 0.3:
     → Add to Tier S (batch scrape)
   ELIF signal_density > 0.1:
     → Add to Tier A (selective scrape)
   ELSE:
     → Add to Tier B (archive only) or skip
   
4. DOCUMENT
   - Update accounts.json with classification
   - Add justification in notes field
   - Record scout results in scouting_log.jsonl
   
5. BATCH (if Tier S/A)
   - Fetch 1 month of data
   - Extract signals
   - Match to price outcomes
   - Compute initial win rate
   - Set initial weight = Bayesian shrinkage of win rate

OUTPUT: Updated accounts.json, new data in data/raw/
```

### Procedure: DAILY_SCRAPE

```
STEPS:
1. Check budget (getxapi balance)
2. For each Tier S account:
   - Fetch since last_fetch_date
   - Dedup against existing
   - Extract new signals
   - Match to outcomes
   - Update author_stats
3. For each Tier A account:
   - Fetch if experiment requires it
4. Log all calls to fetch_log.jsonl
5. Update latest_outcomes.json

QUALITY GATE:
- All new signals must have extraction_confidence > 0.8
- All outcomes must have price data available
- No future information leakage
```

### Procedure: WEEKLY_REVIEW

```
STEPS:
1. Compute 7-day rolling win rate per author
2. Compare to 30-day baseline
3. Flag any author with >10% win rate drop
4. Check if any author's posts became more/less frequent
5. Review regime classification accuracy
6. Update author weights based on recent performance
7. Generate weekly_report.md

OUTPUT: weekly_report.md, updated author_stats.parquet
```

### Procedure: MONTHLY_EXPERIMENT

```
STEPS:
1. Select 2-3 hypotheses to test
   (e.g., "Does XO outperform on FOMC weeks?")
2. Define experiment config (config.yaml)
3. Run backtest against held-out data
4. Compute metrics (Sharpe, win rate, expectancy)
5. Compare to control (no filter)
6. If statistically significant → add to strategy
7. Document results in experiments/{id}/

QUALITY GATE:
- Minimum 20 signals per condition
- Walk-forward validation (no random split)
- Report Deflated Sharpe (not just Sharpe)
```

### Procedure: PNL_REVIEW

```
STEPS:
1. Compute total PnL per author
2. Compute PnL per regime
3. Compute PnL per asset
4. Compute PnL per signal type
5. Identify:
   - Which authors contributed most to PnL?
   - Which regimes were most profitable?
   - Which assets were most profitable?
   - Were there missed opportunities?
6. For each missed opportunity:
   - Who called it before it happened?
   - Did we have their signal?
   - Was it weighted correctly?
   - What would the PnL have been?
7. Adjust weights based on findings

OUTPUT: monthly_pnl_report.md, updated weights
```

### Procedure: HINDSIGHT_ADJUSTMENT

```
TRIGGER: Major market move (>3% BTC in 24h)

STEPS:
1. Identify all signals before the move
2. Who called it correctly?
3. Who called it incorrectly?
4. Was the signal weighted appropriately?
5. For correct calls that were underweighted:
   - Increase weight by 10-20%
   - Document the adjustment
6. For incorrect calls that were overweighted:
   - Decrease weight by 10-20%
   - Document the adjustment
7. Check if regime detection caught the transition

OUTPUT: adjustment_log.jsonl, updated weights
```

---

## Data Architecture

```
astronomer/
├── config/
│   ├── accounts.json           # Account registry with weights
│   ├── strategies.yaml         # Strategy definitions
│   └── experiments/            # Experiment configs
│
├── data/
│   ├── raw/                    # Immutable API responses
│   ├── extracted/              # Classified posts + signals
│   ├── joined/                 # Signals + price outcomes
│   ├── reputation/             # Author stats
│   ├── experiments/            # Experiment results
│   └── budgets/                # API call logs
│
├── src/
│   ├── schemas.py              # Data models
│   ├── fetcher.py              # Budget-aware fetcher
│   ├── extractor.py            # Signal extraction
│   ├── backtest.py             # Price outcome matching
│   ├── signal_engine.py        # Regime detection
│   └── confluence.py           # Multi-author consensus
│
├── apistrategy.md              # How to scrape properly
├── strategy-combined.md        # AltCalls + Death + Macro
├── pipelineplan.md             # Full pipeline specification
└── data-architecture.md        # Schema definitions
```

---

## Key Metrics to Track

### Per Author
```
win_rate_4h
avg_return_4h
profit_factor
sharpe
signal_frequency
signal_density
half_life_hours
```

### Per Regime
```
altcalls_return
death_return
hedge_return
net_return
max_drawdown
```

### Per Strategy
```
sharpe
sortino
max_dd
win_rate
avg_holding_period
turnover
```

### Business Level
```
total_pnl
pnl_per_dollar_risked
cost_per_signal
information_ratio
calmar_ratio
```

---

## The Feedback Loop

```
SCRAPE → EXTRACT → BACKTEST → RANK
    ↑                          │
    │                          ▼
    │                    ALLOCATE
    │                          │
    │                          ▼
    │                    TRACK PNL
    │                          │
    │                          ▼
    └──────── ADJUST ←─── REVIEW
```

Every cycle:
1. We learn which signals are valuable
2. We adjust weights
3. We test new accounts
4. We retire bad accounts
5. The system improves

**The dataset is the moat.** Six months of timestamped signals + outcomes + regime context is extremely valuable.

---

## MCP Server Status

Endpoints implemented:
```
GET /signals/stats          — Signal performance statistics
GET /signals/author/{name}  — Per-author performance
GET /signals/leaderboard    — Author ranking
GET /signals/hour-performance — Performance by hour
GET /signals/outcomes       — Recent signal outcomes
GET /signals/budget         — API spending status
GET /mcp/summary           — Full system summary
```

Not yet implemented:
```
search_signals(query, author, asset, date_range)
get_regime(date)
backtest(strategy, date_range)
add_influencer(handle)
get_pnl(strategy, date_range)
```

## Reference Documents

| Document | Purpose |
|----------|---------|
| `GETXAPI.md` | Rate limits, balance tracking, spending rules |
| `astronomer/apistrategy.md` | How to scrape properly |
| `astronomer/pipelineplan.md` | Full pipeline specification |
| `astronomer/strategy-combined.md` | AltCalls + Death + Macro strategy |
| `astronomer/data-architecture.md` | Schema definitions |

---

*This is a business. Treat it like one.*
