# Crypto Tool Registry

*Free/granular data APIs + MCP servers for BEAR.*

---

## Bitcoin On-Chain Data (Free/Cheap)

| Source | Data | Cost | Best For |
|--------|------|------|----------|
| **BGeometrics** | 350+ on-chain metrics, miner data, UTXO, HODL waves, MVRV, SOPR | Free tier (8 req/hr), paid plans | **Miner profit, hash rate, on-chain analytics** |
| **mempool.space** | Mempool, fees, UTXO, block data | Free | Fee estimation, mempool visibility |
| **Blockchair** | UTXO, addresses, transactions, dataset dumps | Free tier | Flexible lookups, light analysis |
| **Blockchain.com** | Addresses, transactions, balances | Free | Basic lookups |
| **Glassnode** | 350+ metrics, miner data, hash rate, exchange flows | Free tier (limited), paid for full | **Deep on-chain analytics** |
| **BitcoinDatabase** | Full indexed blockchain, REST + SQL | Paid | Genesis-to-now, SQL queries |
| **CryptoAPIs** | Transactions, addresses, UTXOs, webhooks | Free tier | Basic Bitcoin data |

### BGeometrics (Best Free Option)

```
Free tier: 8 requests/hour, 15/day
Paid: Unlimited

Metrics:
- Price, MVRV, SOPR, Realized Price, Halving cycles, HODL Waves
- Open Interest, Funding Rate, Basis, Liquidations
- M2 Supply, BTC ETFs, Stablecoin Supply, DXY, VIX
- Exchange Inflow/Outflow/Netflow, Miner Inflow/Outflow
- Coin Days Destroyed, LTH/STH Position

MCP Server: bitcoin-data.com/api/mcp.html
```

### Glassnode (Best Paid Option)

```
Free tier: Limited metrics
Professional: Full access

Key metrics:
- Hash Rate Mean (latest: 914 EH/s)
- Miner Revenue
- UTXO Age Distribution
- Exchange Reserves
- SOPR, MVRV, NVT
- Funding Rates, OI

MCP Server: Available
```

---

## Crypto MCP Servers (Awesome Lists)

### Top Tier — Production Ready

| MCP Server | Use Case | Cost |
|------------|----------|------|
| **Hive Intelligence** | Broad crypto intelligence | Free |
| **Dune Analytics** | SQL queries on blockchain | Free tier |
| **Token Terminal** | Financial metrics, fees, revenue | Free tier |
| **CryptoQuant** | On-chain analytics, derivatives | Free tier |
| **Glassnode** | BTC/ETH on-chain metrics | Free tier (limited) |
| **Nansen** | Smart money labels, wallet activity | Paid |
| **Alchemy** | RPC, nodes, infrastructure | Free tier |

### Trading & Execution

| MCP Server | Use Case | Cost |
|------------|----------|------|
| **CCXT MCP** | Multi-exchange trading, 100+ exchanges | Free |
| **Kraken MCP** | Market data, trading, paper trading | Free (public data) |
| **Bybit MCP** | Market data, positions, orders | Free (public data) |
| **Hyperliquid** | Perps, funding, positions | Free |

### On-Chain Analytics

| MCP Server | Use Case | Cost |
|------------|----------|------|
| **DexPaprika** | DEX analytics, 20+ chains | Free |
| **CoinCap** | Real-time crypto market data | Free (no API key) |
| **Moralis Cortex** | Wallet activity, token metrics | Free tier |
| **Nansen** | Smart money, wallet labels | Paid |
| **Chainbase** | Token balances, holders, NFTs | Free tier |

### Bitcoin-Specific

| MCP Server | Use Case | Cost |
|------------|----------|------|
| **BGeometrics MCP** | 350+ BTC metrics, miner data | Free tier |
| **Glassnode MCP** | BTC/ETH on-chain metrics | Free tier |
| **BitcoinDatabase** | Full indexed blockchain, SQL | Paid |
| **mempool.space** | Mempool, fees, UTXO | Free |

---

## What to Add to BEAR

### Priority 1: Free BTC Data (no API key)

```python
# BGeometrics — free tier
GET https://api.bgeometrics.com/v1/metrics/{metric}
# 8 req/hr, 15/day

# mempool.space — completely free
GET https://mempool.space/api/v1/fees/recommended
GET https://mempool.space/api/mempool

# CoinCap — no API key needed
GET https://api.coincap.io/v2/assets/bitcoin
```

### Priority 2: MCP Servers (for Claude/Cursor)

```json
{
  "mcpServers": {
    "bgeometrics": {
      "url": "https://bitcoin-data.com/api/mcp.html"
    },
    "coincap": {
      "command": "npx",
      "args": ["-y", "coincap-mcp"]
    }
  }
}
```

### Priority 3: Free Crypto Data (no key)

| Source | Endpoint | What |
|--------|----------|------|
| CoinCap | `api.coincap.io/v2/assets` | Prices, market cap |
| CoinGecko | `api.coingecko.com/api/v3/simple/price` | Prices |
| Binance | `api.binance.com/api/v3/ticker/24hr` | 24h volume |
| Hyperliquid | `api.hyperliquid.xyz/info` | Funding, OI |

---

## Integration with BEAR

### For Regime Detection

```python
# BTC regime signals from BGeometrics
hash_rate = GET bgeometrics/v1/metrics/mining/hash_rate_mean
exchange_flows = GET bgeometrics/v1/metrics/exchange/netflow
miner_revenue = GET bgeometrics/v1/metrics/mining/revenue

# Market regime from Glassnode
mvrv = GET glassnode/v1/metrics/market/mvrv
sopr = GET glassnode/v1/metrics/market/sopr
```

### For Death Token Signals

```python
# On-chain data for death candidates
exchange_inflow = GET bgeometrics/v1/metrics/exchange/inflow
miner_selling = GET bgeometrics/v1/metrics/mining/outflow
utxo_age = GET bgeometrics/v1/metrics/utxo/age_distribution
```

### For Meme/Meta Detection

```python
# From Binance (free)
funding = GET api.hyperliquid.xyz/info  # Hyperliquid funding
oi = GET api.hyperliquid.xyz/info       # Open interest

# From CoinCap (free)
btc_dominance = GET api.coincap.io/v2/assets
```

---

## Key Insight

**You don't need expensive APIs for Bitcoin on-chain data.** BGeometrics free tier + mempool.space + CoinCap covers most needs. Glassnode is nice but not required for the core regime detection.

The expensive part is **X data** (GetXAPI) and **Binance Smart Money** (Apify). Everything else is free or near-free.

---

*Registry version: 1.0 — 2026-09-07*
