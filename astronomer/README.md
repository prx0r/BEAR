# BEAR Astronomer — X Signal Intelligence Module

*Crystallized strategies, continuous graph, binary activation.*

---

## Structure

```
astronomer/
├── config/                    # Account registry, budget, filters
│   ├── accounts.json          # 119 nodes, tier/weight
│   ├── accounts-reference.md  # Account details
│   ├── canonical-registry.md  # Schema
│   └── BUDGET.md              # API tracking
│
├── specs/                     # Architecture documents
│   ├── crystallized-protocol.md  # Main strategy architecture
│   ├── strategy-architecture.md  # Binary activation
│   ├── protocol.md               # Alpha Mining v2
│   ├── meta-science.md           # Meta lifecycle theory
│   ├── graph-architecture.md     # Graph spec
│   ├── data-architecture.md      # Schema spec
│   ├── minimal-backtest-plan.md  # What data we need
│   ├── targeted-acquisition-spec.md  # Buy data to fix weaknesses
│   ├── pipelineplan.md           # Full pipeline (3641 lines)
│   ├── apistrategy.md            # How to scrape
│   ├── cost-analysis.md          # Cost per content type
│   └── originals/                # User messages (word-for-word)
│
├── data/                      # Raw data + backtest results
│   ├── backtest/              # Cached API responses + outcomes
│   ├── prices/                # BTC/ETH/SOL/TAO hourly OHLCV
│   ├── regime/                # BTC regime detection
│   └── recon_report.md        # 64-account recon results
│
├── src/                       # Code
│   ├── backtest.py            # Signal → price outcomes
│   ├── pipeline.py            # Fetch pipeline
│   ├── regime.py              # BGeometrics regime detection
│   ├── schemas.py             # Data models
│   └── ...
│
├── specs/originals/           # User messages (word-for-word)
│   ├── 2026-09-07-meta-science-original.md
│   ├── 2026-09-07-architecture-expansion-original.md
│   ├── 2026-09-07-canonical-sources-original.md
│   ├── 2026-09-07-new-research-accounts-original.md
│   └── death-token-x-intelligence-original.md
│
├── archive/                   # Batch processing archives
│   ├── batches/               # Raw API responses
│   ├── filter_rules/          # Learned filter rules
│   └── reviews/               # Batch review notes
│
└── docs/getxapi/              # GetXAPI documentation
```

## Current State

| Metric | Value |
|--------|-------|
| Accounts | 119 nodes |
| Edges | 100 |
| August backtest | 10 accounts, 383 tweets, 68 signals |
| Top performer | @0xaporia (86% win 4h) |
| Balance | $39.61 |

## Quick Start

```python
# Fetch data
python3 astronomer/pipeline.py

# Run backtest
python3 astronomer/backtest.py

# Check regime
python3 astronomer/regime.py
```

## The Edge

**Not:** "short dead tokens"
**But:** "probability DEATH_TOKEN should be active RIGHT NOW = 0.82"

The graph predicts when strategies activate. That probability prediction is the product.
