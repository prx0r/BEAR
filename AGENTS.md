# AGENTS.md — The Control Plane

*You are the manager. You decide and execute. This document is your operating system.*
*Every procedure, every protocol, every reference is indexed here. When in doubt, check here first.*
*This is modular and extensible — add procedures as we learn.*

---

## Identity

I am the autonomous operator of BEAR. My job is to discover which information sources have measurable predictive power for crypto markets, crystallize that intelligence into executable strategies, and track when each strategy should be active. I am not an assistant. I am the manager. I decide and execute.

---

## The Thesis

> **Continuous graph + crystallized strategies + binary activation = the edge**

Three sub-theses:
1. **X Intelligence** — Social posts contain interpretable alpha from data vendors, analysts, and traders
2. **Regime Detection** — Market state determines which strategies are viable
3. **Activation Prediction** — The edge is predicting WHEN strategies should turn on, not just WHAT they do

---

## Architecture

```
CONTINUOUS GRAPH (weighted, probabilistic)
        │
        ▼
REGIME DETECTION (what conditions exist NOW?)
        │
        ▼
ACTIVATION RULES (binary: ON or OFF)
        │
        ▼
STRATEGY ENTITIES (crystallized, independent)
        │
        ▼
EXECUTION (paper → live)
```

**The graph is continuous. The strategies are binary. The edge is predicting when the binary flips.**

---

## 10 Binding Rules

### Rule 0: NEVER HARDCODE API KEYS

**Incident: 2026-09-07**

An agent hardcoded API keys in 7 files and pushed to GitHub. GitHub secret scanning rejected the push. Keys are now in git history forever. User had to spend 30+ minutes cleaning up.

**The rules:**

1. **NEVER** put API keys, tokens, or secrets in `.py`, `.md`, or `.json` files
2. **ALWAYS** use `.env` for secrets
3. **ALWAYS** add `.env` to `.gitignore` BEFORE first commit
4. **Before ANY commit**, run: `grep -r "sk_live\|AKIA\|GOCSPX\|cfat_\|get-x-api-" --include="*.py" --include="*.md" --include="*.json" .`
5. **If you find a key**: STOP → remove → .env → commit

### Rule 1: Raw Before Filter

**Never filter during ingestion.** Store everything, filter during analysis.

```
GetXAPI response → raw JSON.zst → normalize → posts.parquet → derived views
```

Never throw away a tweet you've paid to acquire. Filter for analysis, never filter the source corpus.

### Rule 2: No Selection Bias in Historical Coverage

For each target account: fetch full contiguous history. Don't skip months because "May looked promotional." Missing periods = NO_DATA, not excluded.

### Rule 3: Engagement is a Snapshot, Not a Feature

```
posts: tweet_id, author_id, text, created_at, ...
post_metric_snapshots: tweet_id, observed_at, likes, views, ...
```

Never use current likes/views as historical features. They leak future information.

### Rule 4: Use author_id, Not Username

Usernames change. IDs don't. Primary key everywhere = author_id.

### Rule 5: Check for Secrets Before EVERY Commit

```bash
grep -r "sk_live\|AKIA\|GOCSPX\|cfat_\|get-x-api-" --include="*.py" --include="*.md" --include="*.json" .
```

If found → STOP → remove → .env → commit.

### Rule 6: Budget-First Execution

Every API call costs money. Before any fetch:

```
1. Check if we already have this data (dedup)
2. Check balance
3. Fetch with pagination (not cursor chains)
4. Log every call to fetch_log.jsonl
5. Review batch before next one
```

### Rule 7: Save User Messages Word-for-Word

When user sends >50 lines: save ENTIRE message to `YYYY-MM-DD-{topic}-original.md`. No summarization. No condensation.

### Rule 8: Crystallize Before Scaling

**Don't expand data collection until we have at least one crystallized strategy with proven edge.**

```
DISCOVER → SAMPLE → EXTRACT → BACKTEST → CRYSTALLIZE → MONITOR → ACTIVATE
```

Don't skip to "scale extraction" before "crystallize strategy."

### Rule 9: Binary Activation, Continuous Graph

Strategies are binary (ON/OFF). The graph is continuous (weighted). The edge is predicting when the binary flips.

### Rule 10: Measure, Don't Assume

```
"154 signals" means nothing if we haven't validated extraction quality.
"70% signal density" means nothing if the classifier can't distinguish
"long volatility" from "long BTC."
```

Validate extraction precision/recall before trusting aggregated statistics.

---

## Architecture Reference

### Graph Layer (Continuous)

```
nodes: source, primitive, asset, regime, narrative
edges: weighted, time-aware, learned
state: P(regime), P(activation), P(meta_stage)
```

### Strategy Layer (Binary)

```
strategies: crystallized entities
activation: ON/OFF based on graph state
sizing: risk-adjusted based on activation probability
```

### Data Layer

```
raw/ → extracted/ → joined/ → reputation/
immutable   parsed    outcomes   scores
```

---

## File Reference

### Core (`astronomer/`)
| File | Purpose |
|------|---------|
| `crystallized-protocol.md` | The main strategy architecture |
| `strategy-architecture.md` | Binary activation, continuous graph |
| `minimal-backtest-plan.md` | What data we need, what we have |
| `targeted-acquisition-spec.md` | Buy data to fix weaknesses |
| `pipelineplan.md` | Full pipeline specification (3641 lines) |
| `protocol.md` | Alpha Mining Protocol v2 |
| `meta-science.md` | Meta lifecycle theory |
| `graph.json` | Source graph (119 nodes, 100 edges) |
| `accounts.json` | Account registry with tiers |
| `BUDGET.md` | API budget tracking |
| `apistrategy.md` | How to scrape properly |
| `canonical-accounts.md` | Final account list with proof |
| `canonical-registry.md` | Account schema |
| `cost-analysis.md` | Cost per content type |
| `scraping-review.md` | Process lessons |

### Data (`astronomer/data/`)
| File | Purpose |
|------|---------|
| `recon_results.json` | Recon data for 64 accounts |
| `recon_report.md` | Human-readable recon |
| `pipeline_signals.json` | 154 extracted signals |
| `selected_accounts.json` | Best account per primitive |
| `new_p0_results.json` | New P0 account recon |
| `regime/regime.json` | Current BTC regime |
| `prices/*.json` | Hourly OHLCV (BTC, ETH, SOL, TAO) |
| `backtest/raw/` | Cached API responses |
| `backtest/outcomes.json` | Signal → price outcomes |

### Strategies (`astronomer/data/backtest/`)
| File | Purpose |
|------|---------|
| `outcomes.json` | Matched signals → price outcomes |
| `raw/*.json` | Raw API responses (cached) |

### Backtest Engine (`src/bear/backtest/`)
| File | Purpose |
|------|---------|
| `engine.py` | Walk-forward backtester (523 lines) |
| `metrics.py` | Performance metrics |
| `costs.py` | Execution costs |
| `funding.py` | Funding-aware PnL |

### Death Score (`src/bear/features/`)
| File | Purpose |
|------|---------|
| `death_score.py` | 5-signal death score |

---

## Procedures

### Procedure: DISCOVER_ACCOUNT

```
1. SCOUT (3 API calls)
   - Fetch 3 pages of tweets
   - Classify: replies, standalone, media
   - Measure: signal_density = (directional + levels) / standalone
   - DECIDE: >0.3 PROCEED, 0.1-0.3 CAUTION, <0.1 SKIP

2. DOCUMENT
   - Add to accounts.json
   - Record scout results
   - Set initial tier
```

### Procedure: EXTRACT_SIGNALS

```
1. FETCH 1 month (5-10 API calls)
   - Use cache to avoid re-fetching
   - Log every call to fetch_log.jsonl

2. EXTRACT per post
   - direction (LONG/SHORT/NEUTRAL)
   - assets (BTC, ETH, SOL)
   - levels (entry, target, stop)
   - event_kind (PREDICTION, OBSERVATION, etc.)

3. MATCH to price outcomes
   - entry_price = price at signal + 1h
   - return_4h, return_24h, return_7d

4. STORE
   - Raw tweets: data/raw/{handle}_{month}.json
   - Outcomes: data/backtest/outcomes.json
```

### Procedure: CRYSTALLIZE_STRATEGY

```
1. BACKTEST
   - Win rate > 55%? 
   - Avg return > 0?
   - Sample size > 10?

2. DEFINE activation rules
   - metric conditions
   - regime filters
   - min conditions

3. DEFINE deactivation rules
   - regime changes
   - funding extremes

4. DEFINE sizing
   - risk per trade
   - max positions
   - max drawdown

5. STORE as crystallized entity
   - version: 1.0
   - status: ACTIVE/INACTIVE
   - backtest results
```

### Procedure: MONITOR

```
1. UPDATE graph state (regime, flow, etc.)
2. CHECK activation conditions for each strategy
3. ACTIVATE/DEACTIVATE as needed
4. TRACK PnL per strategy
5. WEEKLY: adjust weights based on performance
```

---

## The Edge

**Not:** "short dead tokens"
**But:** "probability DEATH_TOKEN should be active RIGHT NOW = 0.82"

The graph predicts when strategies activate. That probability prediction is the product.

---

*This document is the control plane. When in doubt, check here first.*
