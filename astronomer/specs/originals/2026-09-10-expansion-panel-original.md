# User Message — 2026-09-10 (Word-for-Word)

ok great now get all the august data for these guys and compare in terms of quality to astronomer and xo and timeless .. see if they have the data we are looking for clear calls and charts Yes. Your five existing accounts are a much better seed than the normal “top crypto Twitter traders” lists. The key property is not popularity; it is falsifiability: they repeatedly expose what they think before the move, often with a level/chart, and leave enough history to score the misses too.

Crypto: I would expand from 5 → 10 first

I would not claim the five additions are already proven profitable under your exact two-year protocol. External scoring systems are useful for candidate discovery, but their objective differs substantially from yours. CallRank, for example, scores public forecasts against 15-minute market data on move/path/time and deliberately does not score stated price targets.

Rank	Trader	Add?	What I want from them	Why
1	@DaanCrypto	YES	BTC/ETH regime + breakout/failure levels	Extremely parser-friendly. Example: downside scenario toward $50Ks, alternatively reclaiming $72K explicitly invalidates the bearish pattern. His independent CoinVerdict sample is only 6 prospective calls, but 4/6 hit; much more importantly, there are another 41 historical calls available to test.
2
@Crypto_Chase
YES
Entries, failure levels, partial exits
Possibly the best training-data format. Example: HYPE around 28.5, explicit “otherwise back to new lows”; later publicly recorded taking 75% off around 36, +31.5%. CallRank has 321 completed calls.
3
@DrProfitCrypto
YES, test hard
BTC swing zones / bull-trap / liquidity setups
Much noisier stylistically than XO/Astro, but the statistical discovery evidence is unusually strong: CallRank currently has him #2/138, 353 completed calls, median favorable excursion +11.0% vs median adverse −6.1%. Recent calls state actual accumulation zones such as $54–64K.
4	@52kskew	YES, different role	Order flow / CVD / OI / perp-vs-spot state	I would not model him exactly like XO. Skew is valuable because he contributes market-state information orthogonal to price-only TA: spot/perp flows, CVD, liquidation structure, absorption. Make him an L1.5 state estimator.
5	@TheFlowHorse	YES	Short-duration flow/momentum/discretionary execution	Former prop-style approach, explicitly short-term, flow/trend oriented. Excellent source for learning when a setup gets acted upon rather than merely identifying levels.
Your resulting crypto panel

I would organize it like this rather than creating ten identical “trader simulators”:

Trader	Model role	Primary horizon
Astronomer	volume/timing specialist	12h
XO	momentum / DOWN-regime specialist	4h
Timeless	mean-reversion / RANGE specialist	24–168h
Bheem	stated limit-level specialist	4h
DonAlt	sparse HTF structure + invalidation	days/weeks
Daan	range/breakout/reclaim state	hours-days
Crypto Chase	explicit execution/entry/exit teacher	hours-days
DrProfit	liquidity/HTF directional	days-weeks
Skew	market-state features, not normal voter	intraday
FlowHorse	execution/flow voter	intraday-days

And I would keep @Bluntz_Capital, @Pentosh1, @SalsaTekila and @CryptoCred in the shadow evaluation set. DonAlt himself has publicly identified CryptoCred as one of the very small number of accounts he trusts, which is a good qualitative endorsement, but Cred is more useful as a TA/reasoning teacher than a high-frequency call generator.

Interesting sanity check: your methodology beats the public leaderboards

This is important.

CallRank's broad methodology has @Crypto_Chase only #36, while several very loud accounts score much higher. It also ranks many traders very differently from the edges you have measured locally.

That's not necessarily because either analysis is wrong. They're measuring different functions:

$$ \text{generic trader quality} \neq P(\text{profitable}\mid \text{trader, regime, asset, horizon, setup}) $$

Your discovery with XO is precisely the interesting thing:

XO overall can be mediocre while
XO × BTC-DOWN × 4h is valuable.

That is much closer to how a portfolio of specialist models should work.

I therefore would not train L2 on trader identity alone. Expand it to something like:

$$ P(\text{edge}) = f( trader, asset, direction, regime, volatility, trend, funding, OI, spot/perp\ flow, call\ type, streak, distance\ to\ level, horizon ) $$

And retain logistic models because interpretability here is genuinely useful.

Stocks are potentially much bigger

There is a fantastic source we weren't exploiting enough: actual brokerage-statement-backed trading competitions.

The United States Investing Championship requires participants to submit brokerage statements, and its rules explain how returns and external cash flows are calculated. That's dramatically better for candidate discovery than looking at follower counts.

For example:

J Law / @JLawStock: +353.9% in the $1M+ division in 2024 and another +252.3% in 2025.

Tito Adhikary / @GnT_Trades: +2,115.1% in 2025 and +1,626.6% through July 2026 in the enhanced-growth competition.

Omar / @OhMyOhMar: +2,313% through July 2026, and crucially his X output contains machine-readable trades. Just this week he posted a DRAM straddle around 4.97, then posted taking most off at +60%, plus recent NKE LEAP purchases.

Tom Doub / @tomdoub: +982.3% through July 2026.

Kohei Yamada / @khyymd2: +80.5% in 2024, +52.3% in 2025 and still positive in 2026. This is exactly the sort of multi-regime consistency I want.

Kinfo gives us another extremely valuable discovery layer because it connects directly to brokerage accounts. As of today it says 86 traders have verified $100K+ YTD, with ten over $1M; it also publicly highlights specific active traders and individual trades.

The current example of @Tradr_G is nearly perfect for your dataset: Kinfo says he made $302K last month, and his public AMD post says he entered off the open, took partials, exited, and then re-entered.

My first stock “gold set”

Before scraping 100 indiscriminately, these are the 15 I would backfill first:

Priority	Account	Why it belongs
1	@JLawStock	Best combination of multi-year verified returns + public reasoning
2	@GnT_Trades	Extreme verified performance + actual active setups
3	@OhMyOhMar	Extreme 2026 performance + fantastic machine-readable options calls
4	@HumbledTrader18	Kinfo says 6.5+ years verified and $3M... wait, Kinfo says 6.5+ years verified and $1.3M gains; publishes watchlists with levels/setups
5	@Tradr_G	Verified current P&L + timestamped public entries/exits
6	@khyymd2	Rare multi-year USIC consistency
7	@corkyinvestor	+71.1% 2024, +33.6% stock / +104.2% enhanced in 2026
8
@Sp3cul8r
+133.2% 2024; high-frequency veteran trader
9
@ForteCharts
+230.8% in 2025 and chart-native output
10	@therealtabgee	+85.2% 2025, positive 2026
11	@edu_trades	Kinfo currently describes $3M+ verified trading profit
12	@madaznfootballr	Kinfo-linked veteran/day trader; enormous public call history
13	@traderkylec	Current Kinfo leaderboard participant + public stock commentary
14	@MikeHuddie	Long-running small-cap/day-trading history; Kinfo ecosystem
15	@TheOneLanceB	Exceptional discretionary process teacher; former Trillium top trader

Notice @tomdoub isn't high despite +982%. He appears much more systematic and has relatively little public call data. That's exactly the distinction we need: phenomenal trader ≠ phenomenal imitation-training corpus.

The 100-account stock crawl universe

I would use these as candidates, not tell the model that all 100 are “good.” The outcome labels decide that. I've deliberately mixed independently verified competitors, Kinfo-verified traders, public setup traders, shorts and sector specialists so we don't create another permanently-long momentum echo chamber. The USIC portions are anchored by current and 2024–25 brokerage-statement competition standings.

#	Account / trader	Class
1	@JLawStock	verified swing
2	@GnT_Trades	verified options/momentum
3	@OhMyOhMar	verified options
4	@HumbledTrader18	verified day/swing
5	@Tradr_G	verified day
6	@khyymd2	verified swing
7	@corkyinvestor	verified
8	@Sp3cul8r	verified
9	@ForteCharts	verified/chart
10	@therealtabgee	verified
11	@edu_trades	Kinfo verified
12	@madaznfootballr	Kinfo/day
13	@traderkylec	Kinfo/day
14	@MikeHuddie	Kinfo/day
15	@TheOneLanceB	prop/discretionary
16	@tomdoub	systematic/USIC
17	@PriceGrip1	USIC
18	@LongTermWilliam	USIC
19	Layman_Stock	USIC
20	@itsjeromefong	USIC
21	@tronicjosh	USIC
22	@MarketMike	USIC
23	@GravityAnalyti1	USIC
24	@timgarner4F	USIC
25	@GripFangWolf	USIC
26	@artisanwill12	USIC
27	@ryustacey	USIC
28	@humblearning	USIC
29	@TMarketJournal	USIC
30	@Puerto_Rico___	USIC
31	@the_twigg_	USIC
32	@riskcog	USIC
33	@EvanEvansUSA	USIC
34	@lefortaments	USIC
35	@TarmanLT	USIC
36	@NoEdgeNoTrade	USIC / hybrid
37	@kharal_milan	USIC
38	@MikePSilva	USIC
39	@martinaustro	USIC
40	@idrsanthoshkoyadan	USIC
41	@mcpa_trader	USIC
42	@JWTFI	USIC
43	@InvestorsLive	Kinfo/day
44	@Jackaroo_Trades	Kinfo/momentum
45	@AT09_Trader	short seller
46	@TraderBryce	small cap
47	@KrisVerma88	day
48	@TheShortSniper	short/day
49	@Bthestory87	day
50	@OddStockTrader	options/equity
51	@thelaptoplegend	day
52	@daytradingzoo	systematic
53	@RickyAnalog	swing/fundamental
54	@BrianLeeTrades	day
55	@RolandWolf86	day
56	@Jin67171	short-biased
57	@Atem_Trader	small-cap systematic
58	@HKLManagement	systematic/Kinfo
59	@Bobdog1922	Kinfo
60	@matt415	Kinfo
61	Tim Grittani	Kinfo/small-cap
62	James “Stockwonk” Krieger	systematic/Kinfo
63	Michael Goode	short/small-cap
64	Steven Dux	small-cap/verified history
65	@markminervini	momentum/swing
66	@Qullamaggie	momentum
67	@OliverKell_	swing
68	@stockbee	momentum
69	@PradeepBonde	systematic momentum
70	@traderstewie	swing/chart
71	@alphatrends	technical
72	@PeterLBrandt	futures/chart
73	@TraderLion_	momentum ecosystem
74	@RichardMoglen	momentum ecosystem
75	@MikeBellafiore	prop/process
76	@FrankZorrilla	momentum
77	@Trader_Dante	macro/futures
78	@MRockRulez	day
79	@TradeVerity	verified candidate
80	@CrushingCharts	Kinfo candidate
81	@ScroogeCap	fundamental/catalyst
82	@TradexWhisperer	semis/AI
83	@BjerkeOy	semis/memory
84	@MartyChargin	sector momentum
85	@aleabitoreddit	photonics/memory
86	@wey_how12640	AI/semis momentum
87	@CitronResearch	short/catalyst
88	@muddywatersre	short/fundamental
89	@KerrisdaleCap	short/event
90	@BlueOrcaCapital	short/fundamental
91	@SprucePtCapital	short/fundamental
92	@ViceroyResearch	short/fundamental
93	@HindenburgRes	historical short corpus
94	@IcebergResearch	short
95	@WhiteDiamondRes	short
96	@AureliusValue	activist/short
97	@GrizzlyResearch	short
98	@jam_croissant	derivatives/regime
99	@Ksidiii	volatility/derivatives
100	@KrisAbdelmessih	options/volatility

I would also keep the semiconductor/photonics/AI specialist accounts we found recently in a separate research-alpha feed rather than falsely treating them as traders. Their value is identifying the trade before a chart trader notices it, whereas L1 is trying to imitate execution.

There is a very strong architecture hiding here

Your system becomes considerably more interesting if we stop asking:

“Who is the best trader?”

and instead learn:

$$ E[r\mid T,S,R,H,A] $$

where:

\(T\) = trader
\(S\) = setup/call archetype
\(R\) = measured market regime
\(H\) = holding horizon
\(A\) = asset

Then add the less obvious variables:

$$ +\, streak + volatility + volume + funding + OI + distance\_from\_entry + sector\_strength + market\_breadth $$

You can discover absurdly specific rules like:

Timeless × second consecutive bearish call × RANGE→DOWN deterioration × BTC × 7d

rather than ever concluding “Timeless is 55% accurate.”

That's the real alpha extraction.

I would change L1 slightly

Don't have one generic class of simulator. Give posts one of three semantic labels:

CALL — “Long BTC 68.4k, invalid below 66.8k.”
CONDITIONAL — “If 72k reclaims I'll turn bullish.”
STATE — “Spot bid absorbing perp selling; CVD divergence.”

Then:

CALL agents → L2 votes

CONDITIONAL agents → conditional votes once trigger activates

STATE agents → L2 features

That puts Skew where he belongs rather than forcing his order-flow observations into fake long/short labels.

And store the chart. Not because your previous E6 says charts directly predict returns—they apparently don't—but because the model should eventually learn what the trader saw. Text such as “this looks good here” is basically unusable without the attached chart.

The canonical event should therefore contain:

post timestamp
asset
direction
entry / entry range
trigger
invalidation
targets[]
stated horizon
inferred horizon
position_open / hypothetical
chart image
chart OCR/vision structure
thread context AS OF timestamp
regime
1m/5m market snapshot
MFE
MAE
15m / 1h / 4h / 12h / 24h / 48h / 7d return
benchmark return
strict / conditional / state

Most importantly: preserve all failures and deleted/revised theses wherever your archive allows it. Otherwise this turns into a sophisticated survivorship-bias machine.

The strongest immediate experiment is therefore not adding an LLM. It is:

10 crypto accounts × complete history × 1m/5m data → every parseable call → trader × regime × setup × horizon matrix.

Then automatically reject every discovered edge whose Wilson lower bound/sample size doesn't clear your chosen threshold.

For stocks I'd do the identical thing beginning with JLaw, Tito, Omar, HumbledTrader, Tradr_G, Kohei, Corky, Sp3cul8r, ForteCharts and Tabgee. That first ten alone should tell us whether the Astro/XO/Timeless phenomenon generalizes outside crypto.

*Saved word for word. No summarization. No condensation.*
