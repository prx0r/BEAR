# User Message — 2026-09-07 Meme Data Lake (Word-for-Word)

*Saved strictly word for word. No summarization. No condensation.*

---

ok ensure u arent wasting api calls.. review current budget review how to manage api calls review the proces, how to review and do this properly Yes. The biggest simplification is: **stop thinking of GeckoTerminal/Birdeye/DexScreener as the database. Build our own Solana meme data lake from raw chain events.** Use hosted APIs as bootstraps/cross-checks only.

The best discovery from this research is that Pump.fun itself now maintains a fork of **Carbon**, the Solana indexing framework, and that fork already contains dedicated Pump bonding-curve, Pump Fees and Pump AMM decoder generation plus datasources for ordinary RPC, historical crawling, validator snapshots, Yellowstone gRPC and Jito Shredstream. This is almost exactly the skeleton BEAR needs. ([GitHub][1])

## The stack I would build

| Layer                             | Use                                                 | Dependency level                    |
| --------------------------------- | --------------------------------------------------- | ----------------------------------- |
| **Pump.fun Carbon**               | Core real-time + historical Solana indexer          | **OWN IT / CLONE**                  |
| **Pump official IDLs/docs**       | Decode Pump bonding curve/PumpSwap correctly        | **OWN IT / vendor source-of-truth** |
| **Raydium SDK + IDLs**            | Graduated liquidity + swaps                         | **OWN DECODERS**                    |
| **Meteora SDKs**                  | DLMM/DBC liquidity + swaps                          | **OWN DECODERS**                    |
| **Solana RPC / Yellowstone**      | Raw chain truth                                     | migrate toward self-host            |
| **Postgres/ClickHouse + Parquet** | Our permanent history                               | **OWN IT**                          |
| **Jupiter Tokens API**            | Token resolution, holders, liquidity, organic score | free convenience                    |
| **Jupiter Price/Swap**            | execution/quote cross-check                         | free convenience                    |
| **Helius**                        | cheap backfill, wallet history, metadata, debugging | free bootstrap                      |
| **DEX Screener**                  | discovery/cross-check                               | free fallback                       |
| **GoPlus**                        | token/address security                              | free fallback                       |
| **Dune**                          | one-off research and validation                     | free research                       |
| **X traders**                     | social alpha                                        | BEAR source layer                   |

Once Carbon has been running, **our own database becomes the API**.

### 1. Clone Pump.fun Carbon first

[pump-fun/carbon](https://github.com/pump-fun/carbon?utm_source=chatgpt.com)

This is the standout resource. Pump's fork has the whole architecture we were about to reinvent:

* `carbon-block-subscribe`: live blocks from ordinary Solana WS RPC.
* `carbon-program-subscribe`: account updates.
* `carbon-transaction-crawler`: historical transactions for an address/program.
* validator-snapshot ingestion.
* Yellowstone gRPC datasource.
* Jito Shredstream datasource.
* Postgres/GraphQL scaffolding.
* generated program decoders. ([GitHub][1])

Crucially, their repo explicitly ships build scripts for:

```text
carbon-gen:pump-bc
carbon-gen:pump-fees
carbon-gen:pump-amm
```

So rather than reverse-engineering Pump.fun from random GitHub bots, **fork this repository and make it the `meme-chain` backend for BEAR.** ([GitHub][1])

Carbon itself supports real-time streams, historical backfills, snapshots and Postgres sinks from the same processing model. ([GitHub][2])

## 2. Pump.fun source-of-truth

[pump-fun/pump-public-docs](https://github.com/pump-fun/pump-public-docs?utm_source=chatgpt.com)

This is official and current. It includes Pump program IDLs and the newest bonding-curve instructions rather than relying on an abandoned 2024 sniper bot. ([GitHub][3])

Also clone:

[pump-fun/pump-fun-skills](https://github.com/pump-fun/pump-fun-skills?utm_source=chatgpt.com)

Pump itself now maintains agent skills for token creation and swapping. Even if BEAR never launches tokens, the skills are excellent executable documentation of the current instruction/account layout. ([GitHub][4])

There is also a community Pump SDK with an MCP server and detailed bonding-curve/PumpSwap support:

[nirholas/pump-fun-sdk](https://github.com/nirholas/pump-fun-sdk?utm_source=chatgpt.com)

I would **read/steal patterns**, but make Pump's official IDLs + Carbon the authoritative implementation. ([GitHub][5])

## 3. Build our own price history — this eliminates GeckoTerminal dependence

For Pump.fun coins **before graduation**, price is encoded by bonding-curve state. Carbon can ingest and decode every relevant Pump account/transaction.

After graduation, derive price from actual swaps on:

**PumpSwap → Raydium → Meteora** as applicable.

For Raydium:

[Raydium SDK V2](https://github.com/raydium-io/raydium-sdk-V2?utm_source=chatgpt.com)

[Raydium runnable demos](https://github.com/raydium-io/raydium-sdk-V2-demo?utm_source=chatgpt.com)

[Raydium IDLs](https://github.com/raydium-io/raydium-idl?utm_source=chatgpt.com)

Raydium publishes SDKs, REST APIs and Anchor IDLs; the demo repo is deliberately runnable. ([Raydium Docs][6])

For Meteora:

[Meteora DLMM SDK](https://github.com/MeteoraAg/dlmm-sdk?utm_source=chatgpt.com)

Their GitHub org also publishes DAMM v2, Dynamic Bonding Curve, presale and other SDKs. ([GitHub][7])

Then every swap becomes something like:

```text
slot
block_time
signature

pool
base_mint
quote_mint

buyer
seller / authority

base_amount
quote_amount

price_sol
price_usd

liquidity_before
liquidity_after

venue
```

From that one table we locally materialize:

```text
1s / 5s / 1m / 5m / 1h OHLCV
volume
buy volume
sell volume
unique buyers
unique sellers
net flow
price impact
liquidity
market cap
```

**No GeckoTerminal call whatsoever.**

That is the real answer to "I don't want to be rate limited."

## 4. Build our own wallet intelligence

Once every swap is indexed, wallet analytics stops requiring Nansen/GMGN/Birdeye.

Create:

```text
wallet_trades
wallet_positions
wallet_token_pnl
wallet_daily_stats
wallet_reputation
```

You can derive:

```text
first buy time
entry market cap
average entry
total bought
total sold
realized PnL
unrealized PnL
max MFE
max MAE
hold time
2x/5x/10x captures
rug exposure
win rate
median winner
median loser
profit factor

token discovery lead time
repeat-cohort overlap
creator-wallet overlap
copy-trader graph
```

Then the really good stuff emerges:

```text
Which wallets repeatedly buy BEFORE X influencers?

Which influencers repeatedly post AFTER specific wallets accumulate?

Which 10 wallets co-buy eventual 20x tokens?

Which wallets sell before rug events?

Which wallets make money only during meme mania?

Which wallets are creators/dev-connected?

Which traders' public calls correspond to actual wallet purchases?
```

That becomes a much better dataset than paying for a "smart money" label.

## 5. Token identity / metadata: Jupiter is excellent

Jupiter's current Tokens API is surprisingly rich. It can search by symbol/name/mint and returns verification, **organic score, holder count, market cap, liquidity and trading statistics**. ([GitHub][8])

Their docs expose:

```text
/tokens/v2/search
/price/v3
/portfolio/v1/positions
```

and Jupiter provides keyless access at 0.5 RPS for prototyping, with a free API key for higher limits. ([GitHub][8])

So use Jupiter for:

```text
$PONS
    ↓
candidate mint(s)
    ↓
Jupiter metadata
    ↓
our chain data confirms mint/pool
```

Don't use Jupiter as your permanent historical database.

### Jupiter MCP is legitimately useful

[Jupiter Trading MCP docs](https://developers.jup.ag/docs/ai/trading-mcp?utm_source=chatgpt.com)

The hosted Trading MCP exposes **75 tools across 11 areas**, including Tokens, Price, Swap, Portfolio, triggers and execution. It even works without an API key at a lower limit. ([GitHub][8])

For coding agents this is worth installing immediately.

## 6. Helius: exploit the free tier, don't marry it

Helius currently gives the free plan **1M credits/month and 10 RPC requests/sec**. Standard RPC calls cost 1 credit; historical queries are also 1 credit, while DAS calls and enhanced parsing cost more. ([Helius][9])

Useful endpoints include raw Solana RPC, token metadata/DAS, transaction history, wallet transfers and streaming. Helius now recommends its newer transaction-address APIs over building new integrations around the older Enhanced Transactions API. ([Helius][10])

So BEAR should use Helius for:

```text
initial August wallet backfills
missing transactions
metadata
debugging decoder discrepancies
historical spot checks
```

Then cache permanently.

### Helius MCP

[helius-labs/core-ai](https://github.com/helius-labs/core-ai?utm_source=chatgpt.com)

This is official Helius AI tooling and includes `helius-mcp`, exposing wallet, assets, transactions and raw-chain functions to agents. ([GitHub][11])

Install this too.

## 7. DEX Screener is still fantastic — as a cache warmer

DEX Screener's public API currently allows **300 requests/minute** for pair/search/token-pool endpoints and 60/minute for profiles/boosts/orders. ([Dexscreener Documentation][12])

Use it to discover:

```text
new pairs
token → active pools
liquidity
FDV
boosts
paid orders
social links
pair creation time
```

Then write results locally.

Do not repeatedly query it for the same token.

Our cache policy should be:

```text
request external datum once
→ store raw response
→ normalize
→ never request historical copy again
```

That turns rate limits from a system constraint into a temporary ingestion-speed constraint.

## 8. Security/rug intelligence

GoPlus's security API is currently free at **30 calls/minute** and supports Solana token-security checks. ([GoPlus Security][13])

Official MCP:

[GoPlus MCP](https://github.com/GoPlusSecurity/goplus-mcp?utm_source=chatgpt.com)

It exposes Solana token security alongside malicious-address and other risk checks. ([GitHub][14])

But most Solana meme "rug" features should eventually be local:

```text
mint authority
freeze authority
Token-2022 extensions
metadata mutability

top-holder concentration
creator holdings
bundled wallets
LP ownership
LP burn/lock
creator sells

wallet funding ancestry
same-funder clusters
creator previous launches
sniper concentration
```

Those are directly derivable from chain state.

A nice open-source reference implementation is:

[degenfrends/solana-rugchecker](https://github.com/degenfrends/solana-rugchecker?utm_source=chatgpt.com)

It performs RPC-based SPL token/holder/liquidity checks locally. I wouldn't trust its final score blindly, but the primitives are useful to clone. ([GitHub][15])

---

# The genuinely unlimited architecture

There are three levels.

### Level A — now

```text
Carbon
    ↓
Helius free RPC / public RPC
    ↓
Pump/Raydium/Meteora decoders
    ↓
Postgres + Parquet
```

Cheap. Enough to start.

### Level B — serious

```text
multiple RPC providers
        ↓
Carbon
        ↓
local immutable event lake
        ↓
ClickHouse
        ↓
BEAR APIs
```

Now external RPC limits affect ingestion redundancy rather than your analytics queries.

### Level C — no provider rate limits

Run your own **Agave RPC/full node** and attach Yellowstone Geyser:

[anza-xyz/agave](https://github.com/anza-xyz/agave?utm_source=chatgpt.com)

[rpcpool/yellowstone-grpc](https://github.com/rpcpool/yellowstone-grpc?utm_source=chatgpt.com)

Yellowstone is open-source and streams slots, blocks, transactions and account changes through the Geyser plugin. ([GitHub][16])

Then:

```text
SOLANA
   ↓
OUR AGAVE NODE
   ↓
YELLOWSTONE
   ↓
CARBON
   ↓
OUR CLICKHOUSE
```

At that point there is **no third-party API rate limit between Solana and BEAR**.

But don't do this first. Solana itself explicitly warns public RPC is rate-limited and not intended for production; a private node is the path to independence, but running one is materially heavier than our current research needs. ([Solana][17])

## Jito if we eventually want speed

[jito-labs/shredstream-proxy](https://github.com/jito-labs/shredstream-proxy?utm_source=chatgpt.com)

ShredStream is the low-latency feed of Solana leader shreds; Carbon already has a Jito Shredstream datasource. ([GitHub][18])

That is what I'd investigate once BEAR evolves from:

```text
find good meme traders
```

to:

```text
react to wallet/pool activity before ordinary confirmed RPC users
```

Not necessary yet.

## Historical backfill without hammering RPC

SQD is worth testing.

[Solana SQD example](https://github.com/subsquid-labs/solana-example?utm_source=chatgpt.com)

[Squid SDK](https://github.com/subsquid/squid-sdk?utm_source=chatgpt.com)

Its architecture is a decentralized data lake/query engine where you request only the block fields you need instead of making millions of JSON-RPC calls; the Solana example indexes Orca swaps directly into Postgres. ([GitHub][19])

I would benchmark:

```text
Carbon transaction crawler + Helius
vs
SQD Solana
```

for August Pump history.

Whichever gives us full history cheapest/faster wins. Again, our normalized output schema stays identical.

## Dune is research, not infrastructure

Dune gives a free plan with 2,500 credits/month and has extensive Solana decoded tables. ([Dune Docs][20])

Use Dune for questions such as:

```text
Who were the most profitable Pump wallets in August?

Which wallets bought >10 eventual 10x coins?

How many Pump launches graduated?

What was the daily meme DEX volume?

Which creators repeatedly launched coins?
```

Then use the answer to discover targets that our own indexer subsequently follows.

Do **not** make BEAR production depend on Dune.

## MCP bundle I'd install

This is the one list I'd give the coding agent:

1. **Solana official MCP** — current ecosystem docs and source retrieval. [solana-foundation/solana-mcp-official](https://github.com/solana-foundation/solana-mcp-official?utm_source=chatgpt.com) ([GitHub][21])
2. **Jupiter Trading MCP** — token discovery, prices, portfolio, quotes/trading; 75 tools. ([GitHub][8])
3. **Helius MCP** — wallets, transactions, assets and chain queries. [helius-labs/core-ai](https://github.com/helius-labs/core-ai?utm_source=chatgpt.com) ([GitHub][11])
4. **GoPlus MCP** — token/address security. [GoPlusSecurity/goplus-mcp](https://github.com/GoPlusSecurity/goplus-mcp?utm_source=chatgpt.com) ([GitHub][14])
5. **Pump.fun read-only MCP** — there is an interesting zero-key community server with token discovery, bonding curves, holders, trades and KOL signals. Treat its backend as convenience rather than canonical data. [nirholas/pumpfun-mcp](https://github.com/nirholas/pumpfun-mcp?utm_source=chatgpt.com) ([GitHub][22])

### What I would literally tell the agent to build next

Don't integrate 20 APIs.

Create:

```text
src/bear/meme/
    indexer/
        carbon/

    decoders/
        pump/
        pumpswap/
        raydium/
        meteora/

    storage/
        raw_events
        swaps
        pools
        tokens
        wallets

    derived/
        candles
        holder_snapshots
        wallet_pnl
        wallet_reputation
        token_lifecycle

    social/
        influencer_calls
        campaigns

    joins/
        call_attribution
        wallet_attribution
```

Start with **Pump.fun Carbon + official Pump IDLs**.

The first target output should be one local query:

```sql
SELECT *
FROM token_swaps
WHERE mint = ?
ORDER BY block_time;
```

and one:

```sql
SELECT *
FROM wallet_stats
ORDER BY realized_pnl DESC;
```

and then the killer join:

```sql
SELECT
    influencer,
    token,
    call_time,
    call_market_cap,
    call_price,
    return_1h,
    return_24h,
    return_7d,
    max_multiple,
    smart_wallets_already_long
FROM influencer_calls;
```

Once those work, **BEAR no longer needs GeckoTerminal for backtesting at all**. DexScreener/Jupiter/Helius become cheap validators and discovery sources; our chain index is the permanent truth.

That is the route I'd take. **Clone Pump's Carbon fork before writing another custom indexer.** It potentially collapses a huge chunk of the meme-data project into work somebody else has already done properly.

[1]: https://github.com/pump-fun/carbon "GitHub - pump-fun/carbon: Carbon is an indexing framework on Solana. · GitHub"
[2]: https://github.com/sevenlabs-hq/carbon "https://github.com/sevenlabs-hq/carbon"
[3]: https://github.com/pump-fun/pump-public-docs "https://github.com/pump-fun/pump-public-docs"
[4]: https://github.com/pump-fun/pump-fun-skills "https://github.com/pump-fun/pump-fun-skills"
[5]: https://github.com/nirholas/pump-fun-sdk "https://github.com/nirholas/pump-fun-sdk"
[6]: https://docs.raydium.io/sdk-api "https://docs.raydium.io/sdk-api"
[7]: https://github.com/MeteoraAg/ "https://github.com/MeteoraAg/"
[8]: https://github.com/jup-ag/docs/blob/main/llms.txt "https://github.com/jup-ag/docs/blob/main/llms.txt"
[9]: https://www.helius.dev/pricing "https://www.helius.dev/pricing"
[10]: https://www.helius.dev/docs/enhanced-transactions/overview "https://www.helius.dev/docs/enhanced-transactions/overview"
[11]: https://github.com/helius-labs/core-ai "https://github.com/helius-labs/core-ai"
[12]: https://docs.dexscreener.com/api/reference "https://docs.dexscreener.com/api/reference"
[13]: https://docs.gopluslabs.io/reference/support "https://docs.gopluslabs.io/reference"
[14]: https://github.com/GoPlusSecurity/goplus-mcp "https://github.com/GoPlusSecurity/goplus-mcp"
[15]: https://github.com/degenfrends/solana-rugchecker "https://github.com/degenfrends/solana-rugchecker"
[16]: https://github.com/rpcpool/yellowstone-grpc "https://github.com/rpcpool/yellowstone-grpc"
[17]: https://solana.com/docs/references/clusters "https://solana.com/docs/references/clusters"
[18]: https://github.com/jito-labs/shredstream-proxy "https://github.com/jito-labs/shredstream-proxy"
[19]: https://github.com/subsquid-labs/solana-example "https://github.com/subsquid-labs/solana-example"
[20]: https://docs.dune.com/resources/credits-billing/how-credits-work "https://docs.dune.com/resources/credits-billing/how-credits-work"
[21]: https://github.com/solana-foundation/solana-mcp-official "https://github.com/solana-foundation/solana-mcp-official"
[22]: https://github.com/nirholas/pumpfun-mcp "https://github.com/nirholas/pumpfun-mcp"

---

*Timestamp: 2026-09-07*
*Source: User message to BEAR agent*
*Saved word for word. No summarization. No condensation.*
