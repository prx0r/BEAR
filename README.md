# ⛔ NEW AGENTS START HERE, NOT BELOW ⛔
> This README describes the ORIGINAL rel-value engine (archived direction).
> The live project is **signal intelligence + per-expert mimics → x402 endpoints**.
> Read in order: `AGENTS.md` (control plane) → `threads.md` (live status + task
> taxonomy) → `mimichartastro.md` (mimic spec) → `RECIPES.md` (copy-paste commands).
> Repo lives at `/home/ubuntu/BEAR` (not `/root/BEAR` — old docs lie, see RECIPES).

# BEAR — Hyperliquid Relative-Value Trading Engine

## Thesis (Section 76)

The most profitable long-short equity strategies have always been built on a simple insight:
**when you're long the best and short the worst, you can profit from both sides of the market**.
BEAR applies this to crypto perpetuals on Hyperliquid.

Crypto perps are uniquely suited to relative-value trading because:

1. **Funding rates create a structural edge.** Perpetual markets systematically overpay
   shorts during euphoria and overpay longs during panic. By being long quality and
   short garbage, we collect funding from the retail leverage on both sides.

2. **Dispersion is extreme.** A 10x move in a small-cap is common while BTC does 2x.
   This dispersion is harvestable — the cross-section of perp returns has far more
   variance than equity indices.

3. **Lending markets are thin.** Unlike equities where borrow costs are well-known and
   priced in, crypto borrow is fragmented and opaque. Tokens with high retail demand
   (meme coins, leveraged plays) carry hidden borrow costs that create short alpha.

4. **Survivorship bias works in our favor.** Most altcoins trend to zero. Being short
   the ones with poor tokenomics, declining usage, and high emission is a negative-carry
   bet with positive expected value.

BEAR implements a systematic relative-value strategy:

- **Long basket:** Top-tier crypto assets (BTC, ETH, high-quality L1s/DeFi)
- **Short basket:** Worst-tier assets ranked by tokenomics, funding, correlation, and momentum
- **Hedge ratio:** Optimized to minimize residual risk while maximizing funding capture
- **Dynamic rebalancing:** Walk-forward optimization with no lookahead bias

## Architecture

```
bear/
├── portfolio/          # Portfolio optimization
│   ├── optimizer.py    # Basket optimizer (scipy SLSQP)
│   ├── constraints.py  # Portfolio constraints dataclass
│   └── attribution.py  # PnL attribution decomposition
├── backtest/           # Backtesting engine
│   ├── engine.py       # Walk-forward backtester
│   ├── costs.py        # Execution cost model
│   ├── metrics.py      # Performance metrics
│   └── funding.py      # Funding-aware PnL
├── tokenomics/         # Tokenomics data
│   ├── base.py         # Provider abstraction
│   ├── manual.py       # CSV/JSON import
│   └── merge.py        # Point-in-time merge
├── api/                # REST API
│   └── server.py       # FastAPI endpoints
└── cli.py              # Click CLI
```

## Quick Start

```bash
# Install
pip install -e .

# CLI
bear sync universe
bear markets
bear rank-shorts
bear recommend --long BTC --mode balanced
bear backtest --long BTC --start 2024-01-01

# API
uvicorn bear.api.server:app --host 0.0.0.0 --port 8800
```

## Configuration

All parameters in `config/default.yaml`. Long portfolio in `config/longs.yaml`.
Sector taxonomy in `config/taxonomy.yaml`.

## Key Design Decisions

- **Point-in-time everything.** No lookahead bias in backtests. Tokenomics data
  uses `known_at` timestamps.
- **Funding at actual timestamps.** Not a fixed APR approximation.
- **Stress-weighted optimization.** BTC drawdown regimes weight errors 2-6x.
- **Walk-forward only.** Train/validate/test splits with no information leakage.
- **Squeeze-aware.** Names with high short squeeze risk are excluded or penalized.
