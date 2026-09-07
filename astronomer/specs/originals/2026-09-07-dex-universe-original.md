# User Message — 2026-09-07 DEX Universe (Word-for-Word)

*Saved strictly word for word. No summarization. No condensation.*

---

Yes. For your exact strategy — **lots of ~$100 shorts across structurally decaying / high-FDV / unlock-heavy / abandoned tokens** — the key metric is not headline DEX volume. It is **long-tail perp coverage**.

The big finding is that you are missing **Aster**. I would add that before GMX.

| Venue                 | Value for your strategy |                   Long-tail coverage | Add?           |
| --------------------- | ----------------------: | -----------------------------------: | -------------- |
| **Aster**             |               **10/10** |                             **Huge** | **YES — #1**   |
| **Hyperliquid**       |                   10/10 |                                 Huge | Already have   |
| **dYdX**              |                    8/10 |      Large + permissionless listings | **YES**        |
| **Lighter**           |                    8/10 |                   Increasingly large | **YES**        |
| **edgeX**             |                    7/10 |             Large, some weird assets | YES            |
| **Paradex**           |                    7/10 |                                 Good | YES            |
| **Pacifica**          |                    7/10 |                                 Good | Already have   |
| **Orderly ecosystem** |                    7/10 |                140+ + permissionless | YES            |
| **SynFutures**        |                    6/10 |                       Permissionless | Maybe          |
| **ApeX**              |                    6/10 |                               Medium | Maybe          |
| **Aevo**              |                    6/10 |               Historically long-tail | Maybe          |
| **MYX**               |                    5/10 |                              Growing | Maybe          |
| **GMX**               |                    4/10 |                              Curated | Not priority   |
| **Jupiter Perps**     |                    3/10 |                              Curated | Not for this   |
| **Avantis**           |                    3/10 |                    Mostly majors/RWA | Not for this   |
| **Gains/gTrade**      |                    3/10 | Broad asset classes, not tail crypto | Not priority   |
| **Ostium**            |                    2/10 |                            RWA-heavy | Wrong use case |

A current cross-DEX market snapshot dated **September 2, 2026** tracks **649 distinct perp assets across Hyperliquid, dYdX, Aster, Lighter, edgeX, Paradex and Pacifica**. That's an excellent initial universe for what you're building. ([PerpDEX Guide][1])

### Aster is basically made for this

Its market list is absurdly long-tail. Current/recent listings include things such as:

**XAI, BOME, PEOPLE, PIXEL, PHA, COS, DEGO, MELANIA, GRIFFAIN, HMSTR, SAGA, LUNC, YGG, MANTA, GALA, TURBO, NEIRO, PNUT, REZ, TNSR, ANIME, POLYX**, and a gigantic number of even more obscure contracts. Aster's own documentation shows hundreds of supported perp contracts, including BOME and XAI. ([AsterDex Docs][2])

Even better for your strategy, Aster currently caps some of these tail assets relatively conservatively. For example, its July 2026 risk update lists **BOME at 5x max leverage** and a 10% maintenance-margin rate. ([Asterdex][3])

Your specific examples currently look like this:

| Token      | Hyperliquid | Aster | dYdX | Lighter | edgeX | Paradex | Pacifica |
| ---------- | ----------: | ----: | ---: | ------: | ----: | ------: | -------: |
| **XAI**    |           ✅ |     ✅ |    — |       — |     — |       — |        — |
| **BOME**   |           ✅ |     ✅ |    — |       — |     — |       — |        — |
| **PEOPLE** |           ✅ |     ✅ |    — |       — |     — |       — |        — |
| **ZETA**   |           ✅ |     — |    — |       — |     — |       — |        — |

That means your intuition about Hyperliquid is right: **it retains some genuinely dead/legacy perps that other modern DEXs don't bother with.** ZETA is a particularly good example — among those seven large DEX market sets, the current dataset shows it only on Hyperliquid. ([PerpDEX Guide][4])

XAI, BOME and PEOPLE all have Aster alternatives. ([perpdexguide.com][5])

## The next four accounts I'd actually open

**1. Aster — mandatory.** This substantially expands your short universe. It looks particularly strong for Binance-era GameFi, launchpad coins, memes and miscellaneous VC tokens.

**2. dYdX — worth having.** There is an interesting structural reason: dYdX now supports **instant market listings**. A user can launch a launchable perp by supplying $10,000 into MegaVault, with the process taking roughly one minute. That means its obscure-asset universe can expand without the conventional exchange-listing process. ([help.dydx.trade][6])

**3. Lighter — worth having.** It overlaps the liquid universe but also has some contracts the others don't. The September snapshot shows examples like POPCAT, MNT, GMX, APEX and a growing bunch of unique markets. ([PerpDEX Guide][1])

**4. edgeX — worth having as another tail source.** It has quite a few Aster/edgeX-only obscure markets in the current universe, so it genuinely expands coverage rather than merely duplicating BTC/ETH/SOL. ([PerpDEX Guide][1])

After those I'd add **Paradex**, then stop unless the data shows missing candidates.

### Orderly is also interesting

Orderly isn't one DEX frontend: it's a shared perp liquidity/orderbook layer underlying hundreds of interfaces. It says its existing ecosystem provides **140+ assets**, and in April 2026 it launched permissionless market listings using oracle prices from sources including Binance, OKX, Bybit, Gate, KuCoin, MEXC, Bitget, Hyperliquid and others. ([Orderly Network][7])

Its August 2026 **Perp Anything** system pushes this even further: essentially any asset with a usable price feed can become a perp, although whoever creates a community market needs to supply the required liquidity/insurance infrastructure. ([Orderly Network][8])

So I'd definitely ingest **Orderly's market universe into the scanner**, even if you don't necessarily keep substantial collateral there.

## GMX: yes, but not for the reason you want

GMX is absolutely still active. V2 currently operates on **Arbitrum, Avalanche and MegaETH**, has proper short positions, API/SDK support, market liquidity/OI/funding data, etc. ([GMX Docs][9])

But markets need liquidity pools and risk configuration. That's inherently less conducive to keeping around **random 2023 GameFi token #472 whose FDV is slowly bleeding to zero**.

So:

> **GMX = good exchange.
> GMX ≠ particularly useful expansion of the Death Token universe.**

For $100 shorts, I'd prioritize **market count over TVL**.

### Also: Bitunix isn't a DEX

Your current portfolio is really:

**DEX / onchain-ish:** Hyperliquid, Variational, Pacifica
**CEX:** Bitunix

If you're willing to use CEXs too, the universe becomes substantially larger. **Gate, MEXC and Bitget** are particularly interesting to research because long-tail centralized futures listings can extend much further down the garbage-token curve than most perp DEXs.

But I wouldn't even bother yet. **Hyperliquid + Aster + dYdX + Lighter + edgeX + Pacifica + Variational** should already give you an enormous research universe.

## More importantly: this should become part of the Death pipeline

Rather than manually looking for exchanges, I'd make the canonical universe:

> **Every currently shortable perp × every venue → deduplicate underlying token → attach tokenomics/death features → choose best execution venue.**

So one row becomes roughly:

```text
XAI
├── Hyperliquid
│   ├── shortable: yes
│   ├── OI
│   ├── 24h volume
│   ├── spread
│   ├── funding
│   └── max leverage
├── Aster
│   ├── shortable: yes
│   ├── OI
│   ├── volume
│   ├── spread
│   └── funding
│
├── circulating / FDV
├── unlock_30d
├── unlock_90d
├── insider allocation
├── emissions
├── revenue
├── active users
├── developer activity
├── ATH drawdown
├── volume decay
├── OI decay
└── DEATH_SCORE
```

Then execution isn't **"I want to short XAI on Hyperliquid."**

It's:

> **"I want $100 short exposure to XAI. Route it to whichever approved venue currently has the best combination of spread + depth + funding + liquidation characteristics."**

And for a $100 notional position, **raw liquidity requirements are tiny**, which is exactly why this strategy can exploit the horrible tail that institutions can't practically trade.

One critical addition to the score: **expected funding cost**. A fundamentally awful token can still be an awful short when everyone has already discovered it and shorts are paying brutal negative funding. Also track **delisting risk** because the most successful "death" candidates can eventually have their perps wound down/force-settled.

So my immediate signup/integration order would be:

**Aster → dYdX → Lighter → edgeX → Paradex → Orderly markets.**

I would **not prioritize GMX/Jupiter** for this specific strategy. Aster is the big one you were missing.

[1]: https://perpdexguide.com/markets/?utm_source=chatgpt.com "All 649 Perp Markets Across 7 DEXs: Coverage & Specs"
[2]: https://docs.asterdex.com/product/aster-perpetual-pro/market-maker-program?utm_source=chatgpt.com "Market Maker Program | Aster"
[3]: https://www.asterdex.com/zh-CN/announcement/384?category=ALL&utm_source=chatgpt.com "公告"
[4]: https://www.perpdexguide.com/markets/zeta/?utm_source=chatgpt.com "ZETA Perpetual on Hyperliquid: Live Price, Funding, Specs"
[5]: https://perpdexguide.com/markets/bome/?utm_source=chatgpt.com "BOME Perpetual on Hyperliquid: Live Price, Funding, Specs"
[6]: https://help.dydx.trade/en/articles/240150-instant-market-listings-faq?utm_source=chatgpt.com "Instant Market Listings FAQ | dYdX Help Center"
[7]: https://orderly.network/faq?utm_source=chatgpt.com "FAQ | Orderly"
[8]: https://orderly.network/blog/create-a-perp-market?utm_source=chatgpt.com "Perp Anything: List Any Market, Own the Order Flow | Orderly"
[9]: https://docs.gmx.io/docs/api/rest-api/markets/?utm_source=chatgpt.com "Markets | GMX Docs"

---

*Timestamp: 2026-09-07*
*Source: User message to BEAR agent*
*Saved word for word. No summarization. No condensation.*
