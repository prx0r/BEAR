# Death Token X Intelligence Pipeline

*X accounts that publish snapshots from proprietary datasets — better suited to X layer than influencer calls.*

---

## Core Thesis

Scrape data producers, not just traders. Many accounts leak expensive dataset slices into public X posts. Transform posts into timestamped numerical/event features for DEATH_HAZARD, STRUCTURAL_DECAY, SETUP, TRADEABILITY, and a new 5th model: MANIPULATION/RESURRECTION.

## The 20-Account Death Core

### S+ Tier — Highest Parseability

| Handle | Model | Features | Parseability |
|--------|-------|----------|--------------|
| @Tokenomist_ai | B | unlock date, allocation, cliff, linear, supply event | 10/10 |
| @CryptoRank_io | B | unlock USD, ticker, next unlock, vesting | 10/10 |
| @hyblockcapital | D | CVD, OI, liquidation clusters, bid/ask, spread, liquidity | 10/10 |
| @santimentfeed | A | dev rank, dev decline, social activity, sentiment | 9/10 |
| @Lookonchain | B/D | treasury/VC/MM transfers, exchange deposits, whale positioning | 10/10 |
| @DelistingAlerts | A | exchange, token, delisting event/time | 10/10 |

### S Tier — High Value

| Handle | Model | Features | Parseability |
|--------|-------|----------|--------------|
| @BinanceFutures | A/D | perp delisting, settlement time | 10/10 |
| @bwenews | A | Binance Monitoring Tag, delist notices | 10/10 |
| @LunarCrush | A | social mentions, creators, engagement, momentum | 9/10 |
| @DefiLlama | A/B | TVL, fees, revenue, users, incentive deterioration | 9/10 |
| @tokenterminal | A/B | revenue, fees, token incentives, users, earnings | 9/10 |
| @EmberCN | B/D | labeled whale/VC/team/MM flows to CEXs | 10/10 |
| @ai_9684xtpa | B/D | labeled on-chain whale/team flows | 9/10 |
| @bubblemaps | B/R | holder concentration, connected clusters, insider supply | 9/10 |
| @zachxbt | B/R | hidden supply, insiders, OTC, MM relationships | 8/10 |
| @CertiKAlert | A | exploit, amount lost, illicit mint, bad debt | 10/10 |
| @PeckShieldAlert | A | exploit, outflow, stolen supply, attacker movements | 10/10 |
| @coinglass_com | D | liquidations, OI, funding, liquidation maps | 8/10 |
| @laevitas1 | D | derivatives OI, option positioning, perp volume | 9/10 |
| @nansen_ai | B/D | Smart Money flows, token flows, labeled wallets | 8/10 |

### A+ Tier — Second Wave

| Handle | Model | Features |
|--------|-------|----------|
| @OnchainLens | B/D | whale transfers, exchange flows |
| @ArkhamIntel | B | entity-labelled treasury/VC/MM wallets |
| @CoinMarketCal | B/C | unlocks and scheduled token events |
| @cmcal_bot | C | automated event timestamps |
| @artemis | A | active addresses, stablecoin activity, adoption |
| @DappRadar | A | active wallets, volume, TVL, usage |

### Structural Analysts (mine for hypotheses, not features)

| Handle | What they examine |
|--------|-------------------|
| @Dannyhbrown | dilution, buybacks, unlock pressure, revenue |
| @Defi_Warhol | collapsing FDV, supply concentration, failing projects |
| @DefiIgnas | FDV, launch valuation, supply design, unlock thesis |
| @HouseofChimera | unlock + locked supply + fees/activity combined |
| @fejau_inc | VC overhang, low-float/high-FDV, emissions |

## The 5 Models

### A. DEATH_HAZARD — P(death within 30/90/180d)

**Market signals:**
- volume-floor collapse
- OI collapse
- drawdown from peak
- trading inactivity

**X-derived:**
- social-volume decline (LunarCrush)
- creator-count decline (LunarCrush)
- dev activity decline (Santiment)
- monitoring tag (bwenews)
- CEX delisting count (DelistingAlerts)
- perp delisting (BinanceFutures)
- security exploit (CertiK, PeckShield)
- bad debt

### B. STRUCTURAL_DECAY — expected underperformance

**Canonical:**
- FDV/MCap
- dilution
- unlocks
- issuance

**X-derived:**
- unlock announcements (Tokenomist, CryptoRank)
- unlock changes/delays
- team CEX deposits (Lookonchain, EmberCN)
- VC CEX deposits
- MM transfers
- insider concentration (Bubblemaps)
- hidden supply (ZachXBT)
- OTC discounts
- buyback vs dilution (Dannyhbrown)

### C. SETUP — expected 7/30/60/90d return

**Canonical:**
- cross-sectional returns
- post-pump age
- unlock distance
- dispersion
- relative momentum

**X-derived:**
- catalyst timing (CoinMarketCal, cmcal_bot)
- major deterioration announcement
- delisting progression
- smart-money distribution
- narrative/social decay

### D. TRADEABILITY — ENTER / WAIT / VETO

**Canonical:**
- HL funding
- OI
- spread
- depth
- flow
- reversal

**X-derived:**
- Hyblock CVD
- Hyblock GBAR
- liquidation clusters
- OI clusters (Hyblock)
- CoinGlass data
- Laevitas derivatives
- whale positions (Lookonchain)
- squeeze-sensitive wallets

### E. MANIPULATION / RESURRECTION — P_R

**Features:**
- connected insider supply %
- top holder concentration
- estimated true float
- float / OI
- MM-associated wallets
- MM inventory
- short OI / true float
- short liquidation concentration
- negative funding percentile
- social attention acceleration
- creator acceleration
- CEX net withdrawal
- insider/treasury CEX withdrawal
- recent catalyst
- buyback/burn announcement
- recent exploit recovery
- days since capitulation

## Source-Specific Schemas

```
Tokenomist/CryptoRank → UNLOCK_EVENT{}
Santiment/LunarCrush → ACTIVITY_SNAPSHOT{}
DefiLlama/TokenTerminal/Artemis → FUNDAMENTAL_SNAPSHOT{}
Lookonchain/Ember/Ai9684xtpa/OnchainLens → ENTITY_FLOW{}
Bubblemaps/ZachXBT → SUPPLY_STRUCTURE{}
Binance/DelistingAlerts/BWE → EXCHANGE_STATUS{}
CertiK/PeckShield → SECURITY_EVENT{}
Hyblock/CoinGlass/Coinalyze/Laevitas → DERIVATIVES_SNAPSHOT{}
Analyst accounts → HYPOTHESIS{}
```

## Every Record Must Keep

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

## Priority Scrape Order

**20-account Death Core:**
Tokenomist_ai, CryptoRank_io, hyblockcapital, santimentfeed, LunarCrush,
Lookonchain, EmberCN, ai_9684xtpa, OnchainLens, nansen_ai,
bubblemaps, zachxbt, DefiLlama, tokenterminal,
DelistingAlerts, bwenews, BinanceFutures,
CertiKAlert, PeckShieldAlert, Dannyhbrown

## Strongest Priors for Incremental Alpha

1. **MonitoringTag/delisting progression**
2. **unlock → labeled-wallet → CEX transfer**
3. **social + developer simultaneous decay**
4. **revenue/TVL deterioration relative to continuing emissions**
5. **true insider concentration**
6. **Hyblock crowding/liquidity state as ENTER/WAIT veto**

## The Experiment

For every Hyperliquid token that existed during August 2026:
1. Reconstruct every death-related X observation from these accounts
2. Join point-in-time to existing BEAR features
3. Ask whether any X-derived feature improves out-of-sample ranking of subsequent losers, drawdowns and short-entry timing

---

*Source: Comprehensive X data source research, 2026-09-07*
