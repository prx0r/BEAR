# Death Token X Intelligence Pipeline — Original Research

*Full message from user, 2026-09-07. Unedited.*

---

Yes. This strategy is **even better suited to an X intelligence layer than the influencer-call strategy**, because many accounts routinely publish snapshots from datasets that are otherwise paid, proprietary, difficult to reconstruct historically, or require significant labeling work.

I went through **100+ candidate accounts/data feeds/posts** around tokenomics, unlocks, on-chain sleuthing, exchange delistings, protocol fundamentals, dev activity, social decay, derivatives, liquidations, security incidents and low-float/FDV research. The goal was specifically: **could a post be transformed automatically into a timestamped numerical/event feature for DEATH_HAZARD, STRUCTURAL_DECAY, SETUP or TRADEABILITY?**

## The highest-value discovery: scrape data producers, not just traders

There are accounts effectively leaking little slices of expensive datasets into public X posts.

For example:

* `@CryptoRank_io` publishes upcoming unlocks with **ticker + dollar unlock amount**. ([X][1])
* `@santimentfeed` publishes ranked developer-activity snapshots and changes in rank; Santiment also has social-volume/social-dev datasets that combine X/Reddit/Telegram/etc. ([X][2])
* `@LunarCrush` publishes actual social-activity changes—for example a 56% drop in mentions in one observed case. ([X][3])
* `@Lookonchain` turns otherwise laborious wallet labeling into machine-readable facts such as exchange deposits, position sizes and liquidation prices. ([X][4])
* `@hyblockcapital` is especially insane for your **TRADEABILITY veto**: it publicly posts proprietary GBAR, aggregated spot/perp CVD, OI clusters, liquidation clusters, spread/slippage and historical-neighbor statistics—and explicitly says some of these metrics span 1,000+ tickers and 20+ exchanges. ([TwStalker][5])

That last account is very close to your request for **"things normally behind a paywall."**

## My death-token X universe

| Priority | Handle                       | Model | Turn posts into                                                  | Parseability |
| -------- | ---------------------------- | ----- | ---------------------------------------------------------------- | -----------: |
| **S+**   | **@Tokenomist_ai**           | B     | unlock date, allocation, cliff, linear unlock, supply event      |    **10/10** |
| **S+**   | **@CryptoRank_io**           | B     | unlock USD, ticker, next unlock, vesting                         |    **10/10** |
| **S+**   | **@hyblockcapital**          | D     | CVD, OI, liquidation clusters, bid/ask ratios, spread, liquidity |    **10/10** |
| **S+**   | **@santimentfeed**           | A     | dev rank, dev decline, social activity, sentiment                |     **9/10** |
| **S+**   | **@Lookonchain**             | B/D   | treasury/VC/MM transfers, exchange deposits, whale positioning   |    **10/10** |
| **S+**   | **@DelistingAlerts**         | A     | exchange, token, delisting event/time                            |    **10/10** |
| **S**    | **@BinanceFutures**          | A/D   | perp delisting, settlement time                                  |    **10/10** |
| **S**    | **@bwenews**                 | A     | Binance Monitoring Tag additions/removals, delist notices        |    **10/10** |
| **S**    | **@LunarCrush**              | A     | social mentions, creators, engagement, social momentum           |     **9/10** |
| **S**    | **@DefiLlama**               | A/B   | TVL, fees, revenue, users, incentive deterioration               |     **9/10** |
| **S**    | **@tokenterminal**           | A/B   | revenue, fees, token incentives, users, earnings                 |     **9/10** |
| **S**    | **@EmberCN**                 | B/D   | labeled whale/VC/team/MM flows to CEXs                           |    **10/10** |
| **S**    | **@ai_9684xtpa**             | B/D   | labeled on-chain whale/team flows                                |     **9/10** |
| **S**    | **@bubblemaps**              | B/R   | holder concentration, connected-wallet clusters, insider supply  |     **9/10** |
| **S**    | **@zachxbt**                 | B/R   | hidden supply, insiders, OTC structures, MM relationships        |     **8/10** |
| **S**    | **@CertiKAlert**             | A     | exploit, amount lost, illicit mint, bad debt                     |    **10/10** |
| **S**    | **@PeckShieldAlert**         | A     | exploit, outflow, stolen supply, attacker movements              |    **10/10** |
| **S**    | **@coinglass_com**           | D     | liquidations, OI, funding, liquidation maps                      |     **8/10** |
| **S**    | **@laevitas1**               | D     | derivatives OI, option positioning, perp volume                  |     **9/10** |
| **S**    | **@nansen_ai**               | B/D   | Smart Money flows, token flows, labeled wallets                  |     **8/10** |
| A+       | **@OnchainLens**             | B/D   | whale transfers, exchange flows                                  |         9/10 |
| A+       | **@arkham** / `@ArkhamIntel` | B     | entity-labelled treasury/VC/MM wallets                           |         8/10 |
| A+       | **@CoinMarketCal**           | B/C   | unlocks and scheduled token events                               |        10/10 |
| A+       | **@cmcal_bot**               | B/C   | automated event timestamps                                       |    **10/10** |
| A+       | **@artemis**                 | A     | active addresses, stablecoin activity, network adoption          |         8/10 |
| A+       | **@DappRadar**               | A     | active wallets, volume, TVL, usage                               |         9/10 |
| A        | **@coinalyzetool**           | D     | liquidations, OI/derivatives events                              |         8/10 |
| A        | **@TheCryptoData**           | D     | liquidation/OI crowding observations                             |         7/10 |
| A        | **@DefiIgnas**               | B     | FDV, launch valuation, supply design, unlock thesis              |         7/10 |
| A        | **@Defi_Warhol**             | A/B   | collapsing FDV, supply concentration, failing projects           |         8/10 |
| A        | **@Dannyhbrown**             | B     | dilution, buybacks, unlock pressure, revenue analysis            |     **9/10** |
| A        | **@HouseofChimera**          | A/B   | unlock + locked supply + fees/activity combined                  |     **9/10** |
| A        | **@Nazoku**                  | A     | explicit ecosystem deterioration timelines                       |         8/10 |
| A        | **@castle_labs**             | A/B   | protocol/tokenomics fundamental research                         |         6/10 |
| A        | **@Delphi_Digital**          | A/B   | institutional-quality protocol usage/fundamentals                |         7/10 |
| A        | **@aixbt_agent**             | A/B/C | token unlocks, OI decay, revenue, ecosystem stress               |     **8/10** |
| A        | **@fejau_inc**               | B     | VC overhang, low-float/high-FDV, emissions                       |         7/10 |
| B+       | **@WuBlockchain**            | A/B   | exchange announcements + proprietary-data reposts                |         8/10 |
| B+       | **@TreeNewsFeed**            | A/C   | fast catalyst/event aggregation                                  |         8/10 |
| B+       | **@binance**                 | A     | Monitoring Tags, listing/delisting ecosystem events              |         7/10 |

A couple deserve explanation.

### `@Tokenomist_ai` + `@CryptoRank_io` are basically STRUCTURAL_DECAY sensors

Tokenomist is explicitly the official X account for what used to be Token Unlocks, while CryptoRank exposes detailed allocation/unlock data including max supply, locked/unlocked amounts, allocation schedules and unlock frequency in its underlying product/API. ([Tokenomist][6])

Don't extract merely:

```
APT unlock = $8.6m
```

Derive:

```
unlock_usd
unlock_pct_mcap
unlock_pct_float
unlock_pct_ADV_7d
unlock_pct_ADV_30d
unlock_pct_OI
days_until_unlock

allocation_type:
  TEAM
  INVESTOR
  TREASURY
  ECOSYSTEM
  AIRDROP
  FOUNDATION

cliff_or_linear
next_7d_supply_growth
next_30d_supply_growth
next_90d_supply_growth
unlock_acceleration
```

Now X posts become point-in-time snapshots that can cross-check your canonical unlock database.

---

# `@hyblockcapital` is probably mandatory

This was the strongest new account I found specifically for **TRADEABILITY**.

Recent posts expose:

```
aggregated spot CVD
stablecoin-margined perp CVD
coin-margined perp CVD
OI changes
liquidation count
liquidation notional
liquidity clusters
OI clusters
front-book liquidity
slippage
bid/ask spread
GBAR
```

Their proprietary **GBAR** aggregates bids, asks, delta and imbalance over **1,000+ tickers and 20+ exchanges**. They also publish historical conditional comparisons—e.g. nearest historical days based on CVD/OI/price configurations. ([TwStalker][5])

That's almost exactly your model D:

```
TRADEABILITY

death candidate = TRUE
        │
        ▼
Hyblock:
  spot selling?
  perp shorting?
  OI expanding?
  liquidity disappearing?
  crowded short?
  liquidation wall above?
        │
        ▼
ENTER / WAIT / VETO
```

I would **scrape every single historical Hyblock post**.

You may find that its public X archive essentially gives you free historical samples of proprietary metrics.

---

# `@santimentfeed` gives DEATH_HAZARD something you're currently missing

Your A model has:

```
dev decline
social/search decline
```

Santiment is almost tailor-made for that.

It publishes ranked developer-activity data on X. Its Social-Dev methodology incorporates Twitter/X volume, Reddit activity, Telegram, 4chan and GitHub activity. One caveat: Santiment stated that its GitHub-derived developer-score component was broken as of August 3, 2026, so **mark the affected period rather than trusting the feed blindly**. ([Santiment Academy][7])

Extract longitudinal ranks:

```
dev_rank
dev_rank_change_30d

social_rank
social_rank_change_30d

dev_mentions
social_mentions
sentiment

social_volume_z
social_acceleration
```

The useful death signal might not be:

> Development low.

It might be:

> developer rank falling for 4 consecutive months while social volume also collapses.

---

# `@LunarCrush` gives you attention death

This is very promising.

They publish things like:

```
social mentions
unique creators
engagements
social activity
```

and historical percentage changes. ([X][8])

Build:

```
social_mentions_7d
social_mentions_30d

social_mentions / ATH_mentions
creator_count / ATH_creator_count

social_dd
social_velocity
social_acceleration

price_social_divergence
```

A really interesting DEATH signal:

```
price_down
AND
volume_down
AND
developers_down
AND
unique_social_creators_down
```

versus merely:

```
price_down
```

That may separate **temporarily hated** from **actually dying**.

---

# Protocol-fundamental death

`@DefiLlama`, `@tokenterminal`, `@artemis`, `@DappRadar` are another entire signal family.

Token Terminal standardizes fees/revenue/user data across large numbers of crypto projects, while DefiLlama exposes TVL, fees, revenue, active addresses and transaction counts. ([Token Terminal][9])

Extract every quantitative post into:

```
tvl_7d_change
tvl_30d_change
tvl_90d_change

fees_30d_change
revenue_30d_change

active_users_change
transactions_change

token_incentives / revenue
FDV / annualized_revenue
mcap / annualized_revenue

revenue_minus_emissions
```

That yields a killer variable:

```
ECONOMIC_SUFFOCATION
=
usage declining
+ revenue declining
+ TVL declining
+ emissions remaining high
```

That's conceptually much stronger than price decline alone.

---

# On-chain supply pressure: another huge model

This cluster:

```
@Lookonchain
@EmberCN
@ai_9684xtpa
@OnchainLens
@nansen_ai
@arkham
```

should become **one separate on-chain event feed**.

Lookonchain routinely publishes quantities, USD values, wallet identities, destination exchanges and sometimes positions/liquidation levels. ([X][4])

EmberCN does essentially the same at very high frequency—for example identifying token-team transfers through intermediaries into OKX and large holders transferring assets into Binance. ([TwStalker][10])

Parse:

```
entity_type:
  TEAM
  FOUNDATION
  VC
  MARKET_MAKER
  WHALE
  UNKNOWN

action:
  CEX_DEPOSIT
  CEX_WITHDRAWAL
  OTC
  TRANSFER
  UNLOCK
  SELL
  BUY

amount_tokens
amount_usd

amount / ADV
amount / float
amount / exchange_depth
```

Then construct:

```
TEAM_CEX_PRESSURE_7D
VC_CEX_PRESSURE_7D
MM_CEX_PRESSURE_7D

UNLOCK_TO_CEX_RATIO

DAYS_UNLOCK_TO_CEX
```

That last variable could be fucking excellent:

> Tokens unlocked ≠ tokens sold.

But:

> **investor allocation unlock → labeled investor wallet receives tokens → tokens reach Binance 18 hours later**

is much closer to observable sell pressure.

---

# Bubblemaps + ZachXBT are a resurrection-risk input too

This is subtle.

Your formula includes:

$$
TradableDeath=P_D \times P_L \times (1-P_R)
$$

Hidden supply concentration can increase **both death probability and resurrection/squeeze probability**.

Bubblemaps has publicly identified cases where large numbers of apparently separate addresses jointly controlled substantial supply. ([X][11])

And ZachXBT recently alleged that insiders controlled >95% of LAB's supply while explicitly warning that this **wasn't automatically a short**, because concentrated insiders might have enough supply/control to squeeze price higher. ([The Block][12])

That is almost a perfect empirical justification for keeping `P_R` independent.

Feature:

```
holder_concentration
connected_holder_concentration
insider_estimated_supply

top_cluster_pct_supply

MM_control_flag
OTC_discount_pct
OTC_unlock_days

MANIPULATION_CAPACITY
```

Then:

```
HIGH P_D
+
HIGH insider concentration
+
thin float

≠ immediate short

potentially HIGH P_R
```

Exactly your architecture.

---

# Exploit/security accounts belong in DEATH_HAZARD

Add:

```
@CertiKAlert
@PeckShieldAlert
```

CertiK currently publishes extremely structured alerts such as exploit amount, asset, attacker address, bad debt, abnormal mint quantities and timestamps. ([TwStalker][13])

These become:

```
exploit_event
exploit_usd
exploit_usd / TVL

bad_debt
bad_debt / TVL

unauthorized_mint
mint_pct_supply

fund_recovery_pct
protocol_paused
```

Potential hypothesis:

> already weak token + exploit > X% TVL + declining activity = dramatically increased P_D.

But:

> exploit + huge short buildup immediately afterwards = potential P_R spike → WAIT.

Again your separated models work beautifully.

---

# Delisting risk can become dramatically better

This is another unexpectedly strong X corpus.

`@DelistingAlerts` literally outputs:

```
exchange
ticker
delist
announcement
timestamp
```

in highly regular format. ([X][14])

`@bwenews` catches Binance's **Monitoring Tag** announcements; one April example listed five tagged assets and their market caps. ([X][15])

And `@BinanceFutures` publicly publishes forced settlement/delisting dates for perp contracts. ([X][16])

This lets you create a **delisting deterioration sequence**:

```
monitoring_tag
      ↓
liquidity decline
      ↓
spot delisting elsewhere
      ↓
perp delisting
      ↓
Binance spot delisting
```

Feature set:

```
exchange_count
exchange_count_change_30d
exchange_count_change_90d

monitoring_tag_binance
days_since_monitoring_tag

minor_cex_delist_count_30d
major_cex_delist_count_30d

perp_delisted
spot_delisted

exchange_survival_score
```

That could materially improve `P_D`.

---

# Accounts actually thinking like your strategy

The most interesting human-analysis cluster is:

```
@Dannyhbrown
@Defi_Warhol
@DefiIgnas
@HouseofChimera
@fejau_inc
@Nazoku
```

These aren't primarily call accounts. They're already looking at variants of **structural token deterioration**.

For example, Danny Brown Wolf recently decomposed JUP's buyback against its circulating-supply growth and scheduled unlock pressure, arguing that buybacks couldn't offset dilution. ([X][17])

`@HouseofChimera` explicitly combined upcoming unlocks, remaining locked supply and weak fee generation in a single project assessment. ([X][18])

`@Defi_Warhol` has been examining catastrophic launch-FDV deterioration and also holder concentration/market-maker issues. ([X][19])

`@fejau_inc` explicitly discusses VC overhang, emissions and low-float/high-FDV dynamics. ([X][20])

These should be treated differently:

```
DATA PRODUCERS
→ numerical features

STRUCTURAL ANALYSTS
→ candidate hypotheses
```

Don't blindly feed their opinions into the death probability.

**Mine them for experiments.**

---

# The resulting X augmentation is huge

Your existing four models become:

```
A. DEATH_HAZARD
━━━━━━━━━━━━━━━━━━━━━━━━━━

market:
 volume collapse
 OI collapse
 DD
 inactivity

protocol:
 TVL decline
 revenue decline
 fees decline
 active-user decline

development:
 developer decline
 repository decline

attention:
 social-volume decline
 creator-count decline
 mindshare decay

survival:
 monitoring tag
 CEX delisting count
 perp delisting
 security exploit
 bad debt

→ P_D


B. STRUCTURAL_DECAY
━━━━━━━━━━━━━━━━━━━━━━━━━━

canonical:
 FDV/MCap
 dilution
 unlocks
 issuance

X-derived:
 unlock announcements
 unlock changes/delays
 team CEX deposits
 VC CEX deposits
 MM transfers
 insider concentration
 hidden supply
 OTC discounts
 buyback announcements
 actual buyback vs dilution

→ structural expected return


C. SETUP
━━━━━━━━━━━━━━━━━━━━━━━━━━

cross-sectional returns
post-pump age
unlock distance
dispersion
relative momentum

X-derived:
 catalyst timing
 major deterioration announcement
 delisting progression
 smart-money distribution
 narrative/social decay

→ expected 7/30/60/90d return


D. TRADEABILITY
━━━━━━━━━━━━━━━━━━━━━━━━━━

HL funding
OI
spread
depth
flow
reversal

X-derived:
 Hyblock CVD
 Hyblock GBAR
 liquidation clusters
 OI clusters
 CoinGlass
 Coinalyze
 Laevitas
 whale positions
 squeeze-sensitive wallets

→ ENTER / WAIT / VETO
```

## And I'd add a fifth independent model

Your architecture is missing something that this sweep makes obvious:

### **E. MANIPULATION / RESURRECTION**

Not death.

Not tradeability.

Explicitly:

```
P_R = resurrection / squeeze probability
```

Features:

```
connected insider supply %
top holder concentration
estimated true float
float / OI

MM-associated wallets
MM inventory

short OI / true float
short liquidation concentration

negative funding percentile

social attention acceleration
creator acceleration

CEX net withdrawal

insider/treasury CEX withdrawal

recent catalyst

buyback announcement
burn announcement

recent exploit recovery

days since capitulation
```

This is exactly what protects you from doing:

> "fundamentally dead + horrible tokenomics = slam max short"

on a token whose insiders control 70% of the float and can vertically squeeze it 150%.

---

## The scraper architecture I would use

Don't throw all 40 accounts into one generic LLM extractor.

Give each source a **source-specific deterministic schema**:

```
Tokenomist/CryptoRank
→ UNLOCK_EVENT{}

Santiment/LunarCrush
→ ACTIVITY_SNAPSHOT{}

DefiLlama/TokenTerminal/Artemis
→ FUNDAMENTAL_SNAPSHOT{}

Lookonchain/Ember/Ai姨/OnchainLens
→ ENTITY_FLOW{}

Bubblemaps/ZachXBT
→ SUPPLY_STRUCTURE{}

Binance/DelistingAlerts/BWE
→ EXCHANGE_STATUS{}

CertiK/PeckShield
→ SECURITY_EVENT{}

Hyblock/CoinGlass/Coinalyze/Laevitas
→ DERIVATIVES_SNAPSHOT{}

Analyst accounts
→ HYPOTHESIS{}
```

And every record keeps your invariant:

```
event_at
published_at
available_at
ingested_at

source_account
source_post_id
source_post_url

raw_text
raw_media
extraction_version

assert available_at <= signal_time
```

For historical research, **X posts should never silently overwrite your canonical data**.

They are either:

```
PIT FEATURE
```

or:

```
PIT EVIDENCE
```

That's critical because accounts selectively post unusual observations. Absence of a LunarCrush tweet does **not** imply social activity was normal.

---

## My scrape order

If we're paying GetXAPI per historical result, I would start with this **20-account Death Core**:

```
Tokenomist_ai
CryptoRank_io
hyblockcapital
santimentfeed
LunarCrush

lookonchain
EmberCN
ai_9684xtpa
OnchainLens
nansen_ai

bubblemaps
zachxbt

DefiLlama
tokenterminal

DelistingAlerts
bwenews
BinanceFutures

CertiKAlert
PeckShieldAlert

Dannyhbrown
```

Then the second wave.

I would actually **do exactly the same one-month experiment as with the trader accounts before paying for two years**.

But the objective is different:

> For every Hyperliquid token that existed during August 2026, reconstruct every death-related X observation from these accounts, join it point-in-time to your existing BEAR features, and ask whether any X-derived feature improves out-of-sample ranking of subsequent losers, drawdowns and short-entry timing.

My strongest priors for incremental alpha are:

**`MonitoringTag/delisting progression`**, **`unlock → labeled-wallet → CEX transfer`**, **`social + developer simultaneous decay`**, **`revenue/TVL deterioration relative to continuing emissions`**, **`true insider concentration`**, and **`Hyblock crowding/liquidity state as the ENTER/WAIT veto`**.

Those are substantially more interesting than adding another RSI or EMA.

[1]: https://x.com/CryptoRank_io/status/2041173238026321953
[2]: https://x.com/santimentfeed/status/2043486871268081708
[3]: https://x.com/LunarCrush/status/2019245356102611212
[4]: https://x.com/lookonchain/status/2017619069164568579
[5]: https://twstalker.com/hyblockcapital
[6]: https://docs.tokenomist.ai/miscellaneous/official-links
[7]: https://academy.santiment.net/data-anomaly/social-dev-score/
[8]: https://x.com/LunarCrush/status/1864875012051865680
[9]: https://tokenterminal.com/?stream=business
[10]: https://twstalker.com/EmberCN
[11]: https://x.com/bubblemaps/status/1932906744893595948
[12]: https://www.theblock.co/news/ecosystems/2026-05-14-zachxbt-alleges-95-insider-control-of-lab-token-in-investigation-into-ai-terminals-6-billion-fdv-project-401290
[13]: https://twstalker.com/CertiKAlert
[14]: https://x.com/DelistingAlerts/status/2033619355502600422
[15]: https://x.com/bwenews/status/2049745605245988924
[16]: https://x.com/BinanceFutures/status/1992954152855773556
[17]: https://x.com/Dannyhbrown/status/2037364134627463183
[18]: https://x.com/HouseofChimera/status/2042256879620088046
[19]: https://x.com/Defi_Warhol/status/2041426763641983395
[20]: https://x.com/fejau_inc/status/2043163442274787722
