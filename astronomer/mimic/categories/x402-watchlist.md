# x402 watchlist — benchmark buys, watched endpoints, skip pile (2026-09-10)

Judgment: YES, ingest — but as *benchmarks first, data second*. $0.02 total to
benchmark against the only vendors with any proof is the cheapest validation in
the repo. Nothing integrates until it beats the free equivalent on mock-live
(n≥30). Re-check this list monthly: leaderboard volume is the demand truth.

## TIER 1 — buy on approval (~$0.02, one-off benchmark)

| # | Endpoint | $ | Why worth it |
|---|---|---|---|
| 1 | `api.n0brains.com/x402/signals` | 0.005 | Only forward record in market (61%, 12.9k/30d). Head-to-head vs ours, same horizons |
| 2 | `x402.ottoai.services/kol-sentiment` | 0.003 | Direct mimic overlap. Aggregation vs per-expert — loser learns |
| 3 | `cryptyx.ai/api/signals/top` | 0.01 | IC-ranked + health grades = gate design reference |
| 4 | `api.agentstools.dev/crypto/news` | 0.001 | Cheapest MACRO-wire test vs FirstSquawk+FRED (free) |
| 5 | Kalshi trades/books (CDP catalog) | 0.001+ | Only regime data we can't get free |

## TIER 2 — watch (re-query monthly, buy if proof/volume appears)

| Endpoint | $ | Trigger to buy |
|---|---|---|
| agent402 perp-funding | 0.002 | Free Binance funding ever insufficient |
| Hyperliquid fills/funding history ($0.001s) | 0.001 | HYPE-venue models need native fills |
| perpsignals funding scanner | 0.02 | Cross-venue arb becomes a voted strategy |
| Whale accumulation views / leaderboards | 0.30–0.45 | Offline signal proof OR price collapse |
| ottoai mega-report / token-alpha / base-season | 0.002–0.05 | Benchmark round 2, after Tier 1 absorbed |
| Polymarket vs Polygon latency-arb feed | 0.45 | Only with latency thesis + paper test |

## TIER 3 — track (no money, monitor)

- agent402 leaderboard (settled-$ demand truth) + `/api/find` for new signal sellers
- x402-list `/api/v1/best` + volume series per trading service
- Agentic.Market curated Trading tab; dchu3 x402-agent-mcp for agent self-serve
- n0brains proof board (their demotions are free intel on decayed edges)

## SKIP (documented, revisit only on evidence)

Funding-rate endpoints (Binance free covers) · $0.3+ whale views (no proof) ·
$0.05 mega-report (unproven) · x402bazaar.org search ($0.005 just to search).

## Standing rule

No paid feed enters models without beating free on mock-live Brier/return, n≥30.
Vendors' 402 metadata is free recon — re-pull quarterly. Full raw: `data/bazaar_recon.json`.
