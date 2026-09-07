# Astronomer — X Signal Intelligence Module

*Part of BEAR. Scrape X accounts, extract signals, backtest against price data.*

## Quick Start

```python
# 1. Scout an account (3 calls)
from astronomer.fetcher import scout_account
result = scout_account("new_trader_handle")
print(f"Signal density: {result['signal_density']:.0%}")

# 2. Batch scrape if signal density > 0.3
from astronomer.fetcher import batch_scrape
batch_scrape("new_trader_handle", "2026-08-01", "2026-08-31")

# 3. Extract signals
from astronomer.extractor import extract_signals
signals = extract_signals(handle="new_trader_handle")

# 4. Backtest
from astronomer.backtest import match_outcomes
outcomes = match_outcomes(signals)

# 5. Analyze
from astronomer.signal_engine import compute_author_stats
stats = compute_author_stats(outcomes)
```

## Key Files

| File | Purpose |
|------|---------|
| `apistrategy.md` | How to scrape properly |
| `pipelineplan.md` | Full pipeline specification |
| `strategy-combined.md` | AltCalls + Death + Macro strategy |
| `strategy-flaws-addressed.md` | Guardrails for each flaw |
| `death-pipeline.md` | Death token X intelligence |
| `data-architecture.md` | Schema definitions |
| `schemas.py` | Pydantic data models |
| `scraping-review.md` | Process review and lessons |

## Data

| Path | Content |
|------|---------|
| `data/raw/` | 16 JSON files, 591 tweets |
| `data/extracted/` | 128 directional signals |
| `data/prices/` | BTC/ETH/SOL/TAO hourly klines |
| `data/budgets/` | API call log |

## Budget

| Metric | Value |
|--------|-------|
| GetXAPI balance | $0.08 (83 calls) |
| Total spent: $0.31 (468 calls) |
| Posts collected | 591 |
| Cost per post | $0.00004 |
| Cost per signal | $0.0002 |

## Accounts

| Tier | Count | Purpose |
|------|-------|---------|
| S (scrape) | 8 | Direct signal |
| A (selective) | 8 | Context + some signal |
| B (archive) | 11 | Discovery only |

See `accounts.json` and `canonical-accounts.md` for full list.

## See Also

- `../AGENTS.md` — Agent operating manual
- `../src/bear/social/` — XReader adapter
- `../DEV_PLAN.md` — Death token strategy
