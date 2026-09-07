# Signal Trading Dev Plan

*Miniature research/trading desk. Every signal evaluated in paper mode first, then tiny isolated capital.*

---

## The Architecture

```
SIGNALS (X + Binance + TradingView)
        │
        ▼
SIGNAL EXTRACTOR (normalized Signal{})
        │
        ▼
SIGNAL ENGINE
        │
   ┌────┴────┐
   ▼         ▼
RECORD    PAPER-MAINNET    →    EXECUTOR
           simulator              │
                                ├── testnet (test machinery)
                                └── mainnet-micro ($10 live)
```

## Four Execution Modes

| Mode | Capital | Purpose |
|------|---------|---------|
| **RECORD** | $0 | Permanent corpus, no trading |
| **PAPER-MAINNET** | $1 normalized | Real book, simulated fills |
| **TESTNET** | 1000 mock USDC | Test machinery, not alpha |
| **MAINNET-MICRO** | $50-100 USDC | Verify simulator, tiny real trades |

## Hyperliquid Constraints

- Min perp order: $10 notional
- Subaccounts: $100K volume required
- API wallet: can trade, can't withdraw (ideal for bot)
- Isolated margin: one bad position doesn't contaminate
- Testnet: 1000 mock USDC after mainnet deposit

## Four Strategies (run simultaneously)

| Strategy | What it does |
|----------|--------------|
| **P0 RAW_CALLS** | Every directional call → $1 paper |
| **P1 AUTHOR_EDGE** | Trade only historically proven edges |
| **P2 CONSENSUS_ONLY** | Weighted multi-author consensus |
| **P3 CONSENSUS + MARKET** | Signal + CVD/OI/book confirmation |

## The Minimum Viable System

**Universe:** BTC, ETH, SOL, HYPE
**Accounts:** ~27 high-signal sources
**Paper capital:** $1 per signal
**Horizons:** 15m, 1h, 4h, 24h

**First question:** Does information from these people contain forward return information at all?

## Build Order

### Week 1: Data Infrastructure
1. X → normalized signal database (GetXAPI + parser)
2. Hyperliquid WebSocket recorder (L2 book, trades, candles)
3. $1 mainnet-orderbook paper executor

### Week 2: Signal Processing
4. Author reputation model (Bayesian, per-domain)
5. Consensus engine with independence weighting
6. Alpha decay measurement per author/signal type
7. Regime classifier (trend, vol, funding, OI)

### Week 3: Strategies
8. P0: Raw follower strategy
9. P1: Historical edge strategy
10. P2: Weighted consensus
11. P3: Signal + market confirmation

### Week 4: Execution
12. Hyperliquid testnet executor
13. Hyperliquid mainnet-micro executor
14. Risk management (stops, sizing, kill switch)
15. Dashboard + analytics

## Key Design Decisions

### Simulate real book, not midpoint
- Use L2 orderbook at time of signal + latency
- Model actual slippage, fees, funding
- Track paper vs live execution difference

### Track MAE and MFE
- MAE median + MFE median per author
- Where stops should live
- Which authors are right but awful to trade

### Chase filter
- Don't trade if price already moved >X% since post
- Measure alpha decay per author:
  - PriorXBT: best edge 0-2m
  - Trader_XO: edge remains 1-12h
  - exitpump: signal half-life ~10m

### Consensus independence
- Don't double-count reply chains
- Timestamp + quote/reply + language similarity
- 3 independent > 3 people repeating one trader

### Exit priority
1. Author's explicit invalidation
2. Author's explicit target
3. Opposite high-confidence signal
4. Thesis expiration
5. Volatility-adjusted stop (k × ATR)
6. Maximum time stop

## Go-Live Criteria

Before any real money:
- >= 300 independent trades
- Multiple market regimes
- Positive net expectancy AFTER costs
- Paper/live execution difference understood
- Positive out-of-sample result
- No single author responsible for all PnL
- Strategy survives: fee worsening, 2x latency, 2x slippage, best trader removed

## Database Schema

```sql
authors (handle, name, tier, domains, first_seen)
posts (id, author, timestamp, text, asset, direction, levels, conviction)
signals (id, post_id, domain, confidence, market_snapshot)
paper_orders (id, signal_id, strategy, side, size, entry, stop, targets)
paper_fills (id, order_id, fill_price, fees, funding, slippage)
signal_outcomes (signal_id, return_1m...return_3d, mfe, mae, regime)
author_stats (author, domain, asset, horizon, win_rate, expectancy, n)
regime_stats (regime, strategy, win_rate, expectancy, n)
```

## Architecture

```
signalbot/
├── ingest/
│   ├── x_stream.py
│   ├── parser.py
│   └── deduper.py
├── intelligence/
│   ├── classifier.py
│   ├── author_model.py
│   ├── consensus.py
│   ├── independence.py
│   ├── regime.py
│   └── alpha_decay.py
├── market/
│   ├── hyperliquid_ws.py
│   ├── orderbook.py
│   ├── candles.py
│   ├── funding.py
│   └── oi.py
├── strategies/
│   ├── raw_calls.py
│   ├── author_edge.py
│   ├── weighted_consensus.py
│   └── confirmed_consensus.py
├── execution/
│   ├── base.py
│   ├── paper_mainnet.py
│   ├── hyperliquid_testnet.py
│   └── hyperliquid_mainnet.py
├── risk/
│   ├── sizing.py
│   ├── stops.py
│   ├── exposure.py
│   └── kill_switch.py
└── analytics/
    ├── pnl.py
    ├── attribution.py
    ├── author_stats.py
    ├── strategy_compare.py
    └── dashboard.py
```

## The End State

```
SPECIALIST HUMAN INTELLIGENCE
        +
LIVE MARKET MICROSTRUCTURE
        +
HISTORICAL MEMORY
        ↓
PROBABILITY ENGINE
        ↓
TRADE / PASS
```

Example output:
```
SOL LONG                              0.79

exitpump orderflow                   +0.17
PriorXBT MM-flow                     +0.14
XO technical reclaim                 +0.09
52kskew positioning                  +0.08
independent confirmation             +0.12
spot CVD                             +0.11
book imbalance                       +0.07

funding elevated                     -0.04
move already +0.7% since first post  -0.05

EXPECTED MOVE                        +1.32%
EXPECTED COST                         0.11%
EXPECTED NET                          1.21%

ACTION: LONG | confidence 79% | horizon 4h
```

---

*Sources: Hyperliquid docs, SSRN research on social signals*
