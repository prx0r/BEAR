# User Message — 2026-09-10 (Word-for-Word)

Yes. Re-running our old methodology against the architecture you pasted, there are several obvious omissions. The important principle from our earlier work was **source × latent variable**, not “who is the best trader?”: a source only gets weight for the specific thing it has demonstrated information about. CALL, REGIME, FLOW, DERIVATIVES, ONCHAIN and EVENT signals should remain separate.

I would **not yet assign two-year win rates** to the new accounts below without running the same historical extractor/backtest you used on Astronomer/XO/Timeless/etc. What I can validate now is that they produce the right kind of timestamped, falsifiable material. Several are strong enough that I would start their backfills immediately.

| Priority | Account                   | Put it in                     | Why it's additive                                                                                                                                                               | Initial verdict     |
| -------: | ------------------------- | ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------- |
|    **1** | **@52kskew**              | MICROSTRUCTURE / LEAN-TAC     | CVD, spot/perp delta, OI destruction, premiums, aggressive flow, exact structural levels. This is probably the biggest omission.                                                | **S+ ADD**          |
|    **2** | **@JA_Maartun**           | CALL + REGIME DATA            | Astonishingly good fit: exact BTC shorts, stops/TPs **and** CryptoQuant data. Literally a dual-use measurable source.                                                           | **S+ BACKFILL NOW** |
|    **3** | **@Husslin_**             | MM FLOW / REGIME              | Ex-TradFi MM/quant-fund perspective; discusses actual market-maker inventory and perp premium mechanics rather than charts.                                                     | **S+ FEATURE**      |
|    **4** | **@FrankAFetter**         | REGIME VERDICT                | Bitcoin quant; explicit thresholds, vol compression, STH cost basis, mean-reversion framework. Small enough to be especially interesting.                                       | **S+ BACKFILL**     |
|    **5** | **@jjcmoreno**            | REGIME VERDICT                | CryptoQuant head of research. Gives explicit regime states + thresholds + forward historical conditional returns.                                                               | **S+**              |
|    **6** | **@CavanXy**              | REGIME / FLOW                 | Realized profits, taker skew, holder cohorts, structural vs local market moves. Very aligned with your existing model.                                                          | **S+**              |
|    **7** | **@VetleLunde**           | DERIVATIVES / ETF / REGIME    | Institutional-quality perp OI, futures basis, CME, ETF positioning, correlations. Very little guru bullshit.                                                                    | **S+ DATA**         |
|    **8** | **@HyperTracker**         | SMART-MONEY FEATURE           | Hyperliquid wallets stratified by historical profitability; cohort positioning and ~10 months historical API. This directly solves your “profitable traders vs losers” feature. | **S+ MUST ADD**     |
|    **9** | **@CrypNuevo**            | CALL / LIQUIDITY              | Explicit liquidity targets and directional projections; recent BTC example projected $81k from wick/liquidity structure.                                                        | **S BACKFILL**      |
|   **10** | **@Wild_Randomness**      | CALL / CONDITIONAL            | Low-ish audience, publishes position size, entry, stop/invalidation, trend conditions. Exactly our preferred account shape.                                                     | **S BACKFILL**      |
|   **11** | **@RektProof**            | CALL / EXECUTION              | Explicit conditional BTC setups: “if supply/FVG → short; demand → long,” plus trade closes/results.                                                                             | **A+/S**            |
|   **12** | **@trader1sz / TraderSZ** | CALL / PLAN                   | Publishes structured BTC/SOL/HYPE/etc trade plans and regime-dependent trigger logic.                                                                                           | **A+/S**            |
|   **13** | **@CJ900X**               | CALL / CONDITIONAL            | Historical posts contain exact alternate trade plans with entries/invalidation/targets. Extremely extractor-friendly.                                                           | **A+**              |
|   **14** | **@liquiditygoblin**      | RV / CARRY / OPTIONS          | Prop/MM/HFT background; funding, basis, spread, borrow cost and actual carry-trade arithmetic. Not a directional voter.                                                         | **S+ SPECIALIST**   |
|   **15** | **@eyeonchains**          | WHALE / FORENSICS             | Traces whale identities, timing, wallet relationships and suspicious profitable positioning. Better than naïvely treating every whale as smart.                                 | **S EVENT**         |
|   **16** | **@that1618guy**          | TOKEN MECHANICS / FUNDAMENTAL | Builds quantitative token dashboards; fee/burn ratios, TWAP mechanics, token revenue/fair-value work. Excellent for alts, not BTC direction.                                    | **S SPECIALIST**    |
|   **17** | **@AxelAdlerJr**          | ONCHAIN REGIME                | Systematic holder/profitability/sell-side pressure framework and explicit accumulation/distribution states.                                                                     | **A+/S**              |
|   **18** | **@n3ocortex**            | ONCHAIN / FLOW                | Glassnode co-founder; interprets spot-volume delta, cycles, structural positioning.                                                                                             | **A+**              |
|   **19** | **@CryptoVizArt**         | ONCHAIN DATA                  | Glassnode lead research; holder distributions, funding interpretation, accumulation zones.                                                                                      | **A+**              |
|   **20** | **@NachoTrades**          | CATALYST                      | Event/listing/narrative trader with timestamped entries and catalyst theses. Gives an information class your current ensemble barely has.                                       | **A EXPERIMENT**    |

The strongest evidence for **@52kskew** is exactly the type we want. One archived analysis decomposes Binance/Bybit OI, the destruction of roughly 15K BTC of OI, aggregate CVD/delta, spot demand and then gives `$30.5K` as the pivotal structural level. That's much richer than `UP/DOWN`. ([Rattibha][1])

**@JA_Maartun may actually be the discovery of this pass.** A recent post explicitly says he is short BTC, gives a **$80,000 stop** and refers to predetermined take-profit levels. The preceding analysis identifies liquidity at `$77.5K–$78.5K` and downside clusters at `$76,600`, `$75,550`, `$72,400` and `$69,100`. Separately he posted that 24-hour net taker buying reached `$3.0B`. That's unusually clean `CALL + MICROSTRUCTURE FEATURE` training data from one source. ([TwStalker][2])

Full link:

**[https://x.com/JA_Maartun](https://x.com/JA_Maartun)**

### The biggest missing primitive: Skew

I would put **@52kskew above Kingfisher** for the actual model.

Kingfisher says approximately:

`where liquidation liquidity is`

Skew gives you:

`who is aggressively trading → where → spot vs perp → OI change → CVD → premium → whether move is covering/new positioning → structural price level`

Those are much closer to causal features.

**[https://x.com/52kskew](https://x.com/52kskew)**

Then combine:

`Skew interpretation + raw Binance data`

rather than making Skew's directional commentary a full-strength vote.

### Huss is even stranger — potentially extremely high value

This is one of those accounts that follower rankings wouldn't discover properly. @Husslin_ describes himself as a quant-fund founder and former TradFi market maker. More importantly, he has publicly described the positioning his perp market-making activity was producing. In one thread he explained that their operation had become net-long because customers were persistently shorting both rallies and declines, and explained how negative perp premium versus spot can be used as an approximate proxy for market-maker inventory. ([Thread Reader App][3])

That is a radically different information source from:

`Daan thinks BTC is going up.`

It potentially measures:

`customer flow → dealer inventory → eventual squeeze`

Even though Husslin_ probably doesn't post that often, that kind of carefully written, considered position piece is exactly the kind of thing we should retain.

**[https://x.com/Husslin](https://x.com/Husslin)_**

### FrankAFetter is almost purpose-built for your regime layer

This account only has around 16K followers and calls himself a Bitcoin quant. Recent output includes short-term-holder cost basis, implied-volatility extremes, mean-reversion and explicit price areas. For example, he flagged the lowest one-week Bitcoin implied volatility in his dataset and separately identified `$67K` STH cost basis with `$77K` as a potential magnet following reclamation. ([TwStalker][4])

**[https://x.com/FrankAFetter](https://x.com/FrankAFetter)**

This is exactly the sort of account we previously wanted: **small, falsifiable, quantitative, not primarily promotional**.

### Julio Moreno belongs beside Ki Young Ju

This is probably your biggest REGIME omission.

He currently publishes statements as explicit as:

`market regime = Bull`

but then supplies falsifiers/confirmation, such as BTC still needing to cross its 365-day MA, alongside exchange flows and unrealized-profit conditions. He also recently gave an empirical conditional: after apparent spot demand moved into expansion during a bear market, the historical median subsequent 60-day return was 23%. ([TwStalker][5])

That's *much* better training material than generic macro commentary.

**[https://x.com/jjcmoreno](https://x.com/jjcmoreno)**

I would therefore have:

`ki_young_ju + jjcmoreno + CavanXy + FrankAFetter + Checkmate`

and then learn weights independently.

### Cavan should come back into the system

We found him previously and I think dropping him was a mistake.

He is only around 12K followers and discusses things like short-term-holder realized profit, taker skew and whether an observed move represents a local positioning cascade versus a genuinely structural regime change. His current feed contains exactly this sort of disagreement with other analysts. ([TwStalker][6])

That's useful because **disagreement is data**.

**[https://x.com/CavanXy](https://x.com/CavanXy)**

Rather than ensemble-average five bullish analysts, preserve:

`Cavan disagrees with Checkmate because metric X`

as a structured observation.

### Vetle Lunde is substantially better than another influencer

He's Head of Research at K33. Recent work quantified Bitcoin's August squeeze: a record **$1.37B BTC short liquidation day**, another `$739M` two days later, perp OI reset to 284K BTC, funding normalization, CME basis and ETF flows. ([The Block][7])

His X feed is also unusually data-heavy — ETF exposure, crypto-vs-gold/Nasdaq correlations, perp volume and institutional positioning. ([TwStalker][8])

**[https://x.com/VetleLunde](https://x.com/VetleLunde)**

I would feed him into:

`REGIME_DATA`

and only occasionally:

`REGIME_VERDICT`.

### HyperTracker changes the architecture more than another trader

This deserves special emphasis.

They are now explicitly comparing:

`best historical wallets bullish/bearish`
versus
`worst historical wallets bullish/bearish`

and confirmed that historical positions are available in their API for roughly **10 months**, allowing you to freeze the cohort at `t0` and test it forward rather than accidentally introducing survivorship/lookahead bias. ([TwStalker][9])

**[https://x.com/HyperTracker](https://x.com/HyperTracker)**

This is much better than:

`whale opens $30M long → bullish`

because we've already discovered why that logic is garbage. Some giant whales repeatedly lose millions.

Your feature should become:

`wallet_position × ex_ante_wallet_skill × horizon_skill × asset_skill`

For example:

`+$30M BTC long from wallet with +$40M realized PnL / low drawdown / 2-year consistency`

is vastly more informative than:

`+$100M BTC long from anonymous whale with -$30M lifetime PnL`.

### Add Eye, not merely more wallet-alert bots

**[https://x.com/eyeonchains](https://x.com/eyeonchains)**

Eye currently has only about 19K followers and does actual forensic work. A recent investigation examined an SK Hynix liquidation event, quantified one trader's `$2.5M+` profit, investigated synchronized exits and explicitly distinguished what was proven from what remained speculation. ([TwStalker][10])

Historically, Eye also helped trace the enormous Hyperliquid whale associated with the October 2025 crash; reporting tied the investigation to wallet and ENS evidence rather than just screenshots. ([The Block][11])

That becomes:

`FORENSIC_EVENT`

not:

`directional vote`.

And keep **ZachXBT** in the same category. His investigation of a highly profitable Hyperliquid whale actually clustered counterparties and wallets after large, suspiciously timed BTC/ETH trades. ([Thread Reader App][12])

**[https://x.com/zachxbt](https://x.com/zachxbt)**

### CrypNuevo is worth a serious backfill

This one surprised me.

Recent BTC posts projected movement toward **$81K** based on an unfilled wick/liquidity imbalance, and subsequently documented the level being reached. ([TwStalker][13])

That's perfectly extractable:

`timestamp`
`asset`
`direction`
`target`
`basis = liquidity`
`horizon`
`result`

**[https://x.com/CrypNuevo](https://x.com/CrypNuevo)**

Do **not** credit retrospective “nailed it” tweets. Only evaluate the antecedent post.

### Wild_Randomness is exactly our hidden-gem archetype

This is another account around only ~10K followers. Historical posts show statements such as entering HYPE around `$28.40`, specifying **1/3 position size**, conditions for scaling up, and downside/invalidation logic. Other calls explicitly say the direction changes if the trend fails. ([TwitterScore][14])

That is gold for your parser.

**[https://x.com/Wild_Randomness](https://x.com/Wild_Randomness)**

Potential schema:

`ENTRY`
`SCALE`
`SIZE`
`INVALIDATION`
`TARGET`
`CONFIDENCE`

rather than reducing everything to BUY/SELL.

### RektProof / TraderSZ / CJ900X = backfill battle

I wouldn't just add all three as voters. Backfill them and make them fight.

**[https://x.com/RektProof](https://x.com/RektProof)**

Recent RektProof BTC posts contain conditional setup language — consolidate/push into supply + FVG → short; specified demand area → long — rather than hindsight-only charts. ([TwStalker][15])

**[https://x.com/trader1sz](https://x.com/trader1sz)**

TraderSZ's own site archives dated reviews with BTC/SOL/HYPE/etc trade plans and explicitly describes switching to short-term setups when the market is range-bound. ([Tradersz][16])

**[https://x.com/CJ900X](https://x.com/CJ900X)**

CJ has particularly parser-friendly historical plans. One archived BTC thread specifies a long scenario toward `$23K` and an alternative short scenario targeting roughly `$17.5K–$18.3K`, complete with the condition that switches between them. ([Thread Reader App][17])

I'd backfill all three and retain whichever demonstrates incremental PnL **after conditioning on Daan/XO/Astronomer**.

### LiquidityGoblin should not vote — but absolutely ingest him

**[https://x.com/liquiditygoblin](https://x.com/liquiditygoblin)**

This may be one of the highest-IQ sources in the entire set, just not for directional BTC calls.

His work explicitly decomposes:

`funding`
`basis`
`spread`
`borrow`
`fees`
`execution`
`holding-period breakeven`
`liquidity risk`

and then constructs actual relative-value/carry trades. One example calculated transaction costs around **1.86% round trip** and derived the approximately 3.5-day breakeven holding period from funding. ([Rattibha][18])

His profile now describes work across crypto prop trading, market making, HFT, MEV and stat arb. ([Substack][19])

That suggests an entirely new model head:

`P(RV opportunity profitable | funding,basis,spread,borrow,fees,liquidity)`

rather than only:

`P(BTC goes up)`.

## My revised architecture

I would make the ensemble:

```text
DIRECTIONAL CALL VOTERS
DrProfitCrypto
astronomer_zero
DaanCrypto
Timeless_Crypto
Trader_XO
CryptoBheem
Crypto_Chase
+ CrypNuevo             ← NEW
+ Wild_Randomness       ← NEW
+ RektProof             ← TEST
+ TraderSZ              ← TEST
+ CJ900X                ← TEST

MICROSTRUCTURE
52kskew                  ← HUGE ADD
Husslin_                 ← HUGE ADD
laevitas1
kingfisher_btc
PriorXBT                 ← research/feature only

REGIME VERDICT
0xaporia
ki_young_ju
DrProfit
Pentosh1
Checkmatey
+ FrankAFetter           ← HUGE ADD
+ jjcmoreno              ← HUGE ADD
+ CavanXy                ← RESTORE

REGIME / DERIVATIVE DATA
Laevitas
Hyblock
Farside
Tokenomist
+ VetleLunde             ← HUGE ADD
+ JA_Maartun             ← HUGE ADD
+ AxelAdlerJr
+ n3ocortex
+ CryptoVizArt

SMART MONEY
Hyperliquid raw API
OnchainLens
Lookonchain
+ HyperTracker           ← CRITICAL
+ HypurrScan             ← provenance
+ EyeOnChains            ← forensic interpretation

EVENT / SECURITY
PeckShield
CertiK
+ ZachXBT                ← MUST ADD
+ EyeOnChains

CATALYST / TOKEN MICROECONOMICS
+ that1618guy            ← UNIQUE
+ NachoTrades            ← EXPERIMENT

RELATIVE VALUE
+ liquiditygoblin        ← NEW MODEL HEAD
```

And the **five accounts I would backfill first tonight** are:

**@JA_Maartun → @52kskew → @FrankAFetter → @Wild_Randomness → @CrypNuevo.**

Those five give us five rather different sources of edge: `raw taker/liq + discretionary call`, `microstructure`, `quant regime`, `conditional discretionary positioning`, and `liquidity-target forecasting`.

The one architectural change I think is even more important than adding these X accounts is **Hyperliquid wallet discovery becoming recursive**. Don't decide beforehand who the “smart whales” are. Rank the entire available wallet universe based only on information known at `t`, freeze cohorts such as `top_1%_30d`, `top_1%_90d`, `consistent_low_DD`, `BTC_specialist`, `ETH_specialist`, then ask whether their **future aggregate position changes** predict returns. HyperTracker explicitly has historical positions suitable for freezing old cohorts, and public tools now expose tens of thousands of leaderboard wallets. ([TwStalker][20])

That could ultimately make the human trader accounts almost secondary: **X teaches the model what sophisticated traders are thinking; Hyperliquid lets us observe what demonstrably profitable traders are actually doing.**

[1]: https://en.rattibha.com/thread/1680076586597642240?utm_source=chatgpt.com "$BTC Binance / Bybit Open Interest Price back to range low & a lot of delta sold off from $31K A lot... - Skew Δ | Rattibha"
[2]: https://w.twstalker.com/JA_Maartun?utm_source=chatgpt.com "Maartunn @JA_Maartun - Twitter Profile | TwStalker"
[3]: https://threadreaderapp.com/user/Husslin_?utm_source=chatgpt.com "huss 🌊 🟦's Threads – Thread Reader App"
[4]: https://www6.twstalker.com/FrankAFetter?utm_source=chatgpt.com "Frank @FrankAFetter - Twitter Profile | TwStalker"
[5]: https://www6.twstalker.com/jjcmoreno?utm_source=chatgpt.com "Julio Moreno @jjcmoreno - Twitter Profile | TwStalker"
[6]: https://w.twstalker.com/CavanXy?utm_source=chatgpt.com "Cav @CavanXy - Twitter Profile | TwStalker"
[7]: https://www.theblock.co/news/markets/2026-08-26-altitude-sickness-can-wait-bitcoins-historic-short-squeeze-bessent-catalyst-may-signal-bull-market-reset-analysts-say-412785?utm_source=chatgpt.com "'Altitude sickness can wait': Bitcoin's historic short squeeze, Bessent catalyst may signal bull-market reset, analysts say | The Block"
[8]: https://www6.twstalker.com/VetleLunde?utm_source=chatgpt.com "Vetle Lunde @VetleLunde - Twitter Profile | TwStalker"
[9]: https://www6.twstalker.com/HyperTracker?utm_source=chatgpt.com "HyperTracker @HyperTracker - Twitter Profile | TwStalker"
[10]: https://ww.twstalker.com/eyeonchains?utm_source=chatgpt.com "Eye @eyeonchains - Twitter Profile | TwStalker"
[11]: https://www.theblock.co/news/markets/2025-10-12-hyperliquid-whale-who-made-150-million-with-short-bet-opens-new-160-million-short-374290?utm_source=chatgpt.com "Hyperliquid whale who made $150 million with short bet opens new $160 million short | The Block"
[12]: https://threadreaderapp.com/scrolly/1902713021937426495?utm_source=chatgpt.com "Thread by @zachxbt on Thread Reader App – Thread Reader App"
[13]: https://www6.twstalker.com/CrypNuevo?utm_source=chatgpt.com "CrypNuevo 🔨 @CrypNuevo - Twitter Profile | TwStalker"
[14]: https://twitterscore.io/twitter/Wild_Randomness/?utm_source=chatgpt.com "Mandelbrot (@Wild_Randomness) — Twitter Score 58.6/1000"
[15]: https://mobile.twstalker.com/RektProof?utm_source=chatgpt.com "RektProof @RektProof - Twitter Profile | TwStalker"
[16]: https://www.tradersz.com/category/crypto_videos/?utm_source=chatgpt.com "CRYPTO VIDEOS - TraderSZ"
[17]: https://threadreaderapp.com/thread/1544805599648616457?utm_source=chatgpt.com "Thread by @CJ900X on Thread Reader App – Thread Reader App"
[18]: https://en.rattibha.com/thread/1665924835955068930?utm_source=chatgpt.com "market stresses lead to interesting opportunities! a quick look at a carry trade opportunity I ident... - Liquidity Goblin | Rattibha"
[19]: https://substack.com/%40liquiditygoblin?utm_source=chatgpt.com "Liquidity Goblin | Substack"
[20]: https://twstalker.com/HyperTracker?utm_source=chatgpt.com "HyperTracker @HyperTracker - Twitter Profile | TwStalker"

*Saved word for word. No summarization. No condensation.*
