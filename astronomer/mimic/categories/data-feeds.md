# Quant feeds per category — free/unlimited first, paid only after signal proof

Verified live from this box 2026-09-10 unless noted.

## FREE, keyless, effectively unlimited (use now)

| Category | Feed | Endpoint (no key) | Use |
|---|---|---|---|
| CALL (entries/targets) | Binance klines 1m→1M | `api.binance.com/api/v3/klines` | Candle truth for charts, levels, MFE/MAE |
| CALL / VERDICT | Binance orderbook L2 | `api/v3/depth?symbol=&limit=` | Bid/ask walls for S/R ("purple boxes") |
| FLOW (STATE) | Binance funding rate | `fapi/.../fapi/v1/fundingRate` | Crowded-long/short gauge |
| FLOW (STATE) | Binance open interest | `fapi/v1/openInterest` | Positioning size |
| FLOW (STATE) | Binance long/short accounts | `futures/data/globalLongShortAccountRatio` | Retail crowd sensor |
| MACRO | FRED (free key, generous) | `api.stlouisfed.org` — DGS10, CPI, unemployment | Regime base layer — needs HUMAN: mint free key |
| MACRO sentiment | Fear & Greed (free, keyless) | `api.alternative.me/fng/` — verified live | Contrarian regime feature |
| DEFI/ALTS | DeFiLlama TVL + Yields (free, full history) | `api.llama.fi`, `yields.llama.fi/pools` (11.8MB dump) — verified live | TVL regime + alt rotation + carry inputs |
| STOCKS | Stooq daily CSV | `stooq.com/q/d/l/` — BLOCKED from datacenter (JS wall) | Unreliable from VPS; revisit via browser-side pull |

Limits: Binance ~6,000 weight/min/IP — we use <50. FRED key is free but keyed.

## NOT free (verdicts — do not build on these)

- **Apify actors**: pay-per-event ($0.95–3.00/1k rows; only ~$5/mo free credit).
  Orderbook/funding actors just resell the Binance endpoints above. SKIP except
  one-off scrapes. (Cute: foxlabs funding actor accepts x402 agent payments.)
- **Dune/Flipside**: free tiers are execution-capped — verify quota before depending.
- **CoinGecko free**: 5–15 req/min — backup only.
- **Glassnode: NO free tier.** Advanced $49–99/mo (API Light: 14d history, daily, 50 calls/day);
  full API = Professional + unpublished per-credit meter. GATED — human $$ call.
- **CryptoQuant: API needs paid plan** (~$39–109/mo). GATED — human $$ call.
- **CoinMetrics community**: unverified from VPS (400s) — treat as gated until proven.
- **Etherscan V2**: free key, generous — needs HUMAN: mint free key (like FRED).

## x402 WATCHLIST (browse free, buy only after signal experiments)

Live catalog: Circle keyless `api.circle.com/v2/x402/discovery/resources`
(CDP Bazaar search equivalent). Candidates found 2026-09-10:

| Endpoint | Price | Would test |
|---|---|---|
| Derivatives intel: funding + OI + L/S + whale positions | $0.001 | Cheapest FLOW upgrade; A/B vs free Binance same fields |
| Hyperliquid perps market data + fills/funding history | $0.001 ×2 | HYPE is our traded venue; native flows |
| Perp funding cross-exchange / Surf funding history | $0.007–0.008 | Only if free Binance funding proves insufficient |
| Whale accumulation views / wallet leaderboards | $0.30–0.45 | Expensive — needs offline signal proof first |
| Weekly insight reports | — | NONE FOUND in catalog (gap = our product opportunity) |

Rule: no paid feed enters the model until it beats the free equivalent on
mock-live Brier/return with n≥30. The missing weekly-report category is
exactly what OUR delayed-X cards become.
