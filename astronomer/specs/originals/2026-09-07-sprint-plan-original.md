# User Message — 2026-09-07 Sprint Plan (Word-for-Word)

*Saved strictly word for word. No summarization. No condensation.*

---

Yes. The repo is now at the point where **more architecture is lower ROI than more high-quality people + more real calls**.

The latest push fixed the major evaluator defects and added the reusable onboarding/background infrastructure.  The next move should be a deliberately crude but clean expansion:

**5 existing major/macro traders + ~6 meme traders → full August calls → outcomes → live monitoring.**

For the meme cohort, I would start with **@theunipcs, @SevaFTW, @kenjidgn, @loganlim_x, @0xAvast, @0xnobi**. These are substantially better research candidates than generic meme influencers because we have evidence of actual early calls/trading activity: Unipcs publicly documents large meme positions and detailed theses; Seva has publicly described early CASHCAT/ZCAT positioning; Kenji was specifically cited for an early CASHCAT thesis; Logan has public FOMO-linked trading history; Avast appears on current realized-PnL leaderboards; and 0xnobi has an unusually early documented PONS thesis/position. ([Twiscan][1])

The existing majors cohort should simply remain **@Timeless_Crypto, @Trader_XO, @astronomer_zero, @CryptoBheem, @0xaporia** for now. That is enough coverage to start observing BTC/major confluence while the meme engine fills the biggest gap.

Give the coding agent this:

# BEAR NEXT SPRINT

## Objective

STOP expanding architecture.

For this sprint BEAR has one job:

> Get the best existing major traders and the first high-signal memecoin traders into one clean August experiment and start recording them prospectively.

We want actual data:

```text
WHO said WHAT
WHEN
ABOUT WHICH TOKEN
AT WHAT PRICE / MARKET CAP
WHAT happened next
```

Then we can optimize weighting, primitives, RL, confluence, etc.

---

# 1. Cohort

## Existing majors — keep running

```text
Timeless_Crypto
Trader_XO
astronomer_zero
CryptoBheem
0xaporia
```

Do not expand this group yet.

They cover enough BTC / major directional and regime information for the current experiment.

---

# 2. Meme cohort — onboard now

Wave 1:

```text
theunipcs
SevaFTW
kenjidgn
loganlim_x
0xAvast
0xnobi
```

Wave 2 only after Wave 1 is running:

```text
yeon__
2442lll
Wolves_Techml
PhilOnChain
```

Do not spend another day finding accounts before Wave 1 is processed.

---

# 3. IMPORTANT: do not use the current extractor unchanged

Current `extractor_v2.py` only knows:

```text
BTC
ETH
SOL
HYPE
TAO
```

That makes it incapable of the meme experiment.

Fix this first.

---

# 4. Dynamic token extraction

Add a generic crypto asset reference object.

```python
class AssetRef:
    symbol: str | None
    contract_address: str | None
    chain: str | None
    name: str | None
    resolution_status: str
```

Extract:

### Cashtags

```regex
\$[A-Za-z0-9_]{2,20}
```

Examples:

```text
$PONS
$CASHCAT
$ZCAT
$BONK
$WIF
$FARTCOIN
```

Do NOT maintain a hard-coded meme symbol list.

---

# 5. Contract addresses are highest-confidence identity

Parse:

```text
Solana addresses
0x EVM addresses
explicit Dexscreener/GeckoTerminal links
explicit FOMO links
```

Identity priority:

```text
contract address
>
linked token/pair
>
unambiguous cashtag
>
plain token name
```

Never select among two `$ABC` tokens because one later pumped.

If identity cannot be determined uniquely:

```text
AMBIGUOUS_ASSET
```

and do not backtest it.

---

# 6. Meme calls need a much simpler classifier

Do not force them through BTC terminology.

Candidate post first requires:

```text
cashtag OR contract address
```

Then classify into:

```text
ENTRY
ADD
BULLISH_THESIS
HOLD
TARGET
REDUCE
EXIT
BEARISH
RETROSPECTIVE
MENTION
IGNORE
```

Examples:

```text
"bought $PONS"
→ ENTRY

"adding $PONS here"
→ ADD

"$PONS is my highest conviction play"
→ BULLISH_THESIS

"$PONS to 100m"
→ TARGET

"took half off"
→ REDUCE

"closed $PONS"
→ EXIT

"I bought PONS at 100k and now it's 50m"
→ RETROSPECTIVE
```

That final distinction is critical.

---

# 7. NEVER invent an entry from retrospective bragging

This will be common.

Post:

```text
"turned $2k into $1m on PONS"
```

is NOT:

```text
ENTRY PONS
```

Search their earlier August corpus.

Only an earlier timestamped public post such as:

```text
"I bought PONS"
"building a PONS position"
"PONS is my high conviction play"
```

creates a contemporaneous signal.

Later retrospective posts can verify attribution but cannot move the original timestamp backwards.

---

# 8. Collapse repeated shilling into a campaign

Meme traders may post the same coin 30 times.

Do not treat those as 30 independent trades.

Create:

```text
Campaign
```

Example:

```text
theunipcs:PONS:2026-08
```

Lifecycle:

```text
FIRST_ENTRY
     ↓
THESIS
     ↓
ADD
     ↓
CONVICTION_UPDATE
     ↓
TARGET_UPDATE
     ↓
REDUCE
     ↓
EXIT
```

This gives us one coherent trade/thesis rather than spam-weighted statistics.

---

# 9. Store every post anyway

Raw posts remain immutable.

Campaign collapsing happens in analysis.

Never filter raw ingestion.

---

# 10. Historical meme price adapter

Current BEAR only loads:

```text
BTCUSDT
ETHUSDT
SOLUSDT
TAOUSDT
```

Add:

```python
MarketDataProvider
```

Interface:

```python
resolve(asset_ref, timestamp)
get_ohlcv(asset_id, start, end, interval)
get_liquidity(asset_id, timestamp)
```

---

# 11. First provider: GeckoTerminal

Use GeckoTerminal public API for supported on-chain pools.

It exposes:

```text
token → pools
pool → OHLCV
```

and historical OHLCV.

Do not download an entire token history.

For each signal fetch only:

```text
signal - 24h
through
signal + 7d
```

Cache permanently:

```text
data/prices/onchain/{chain}/{contract}/{interval}.json
```

Official GeckoTerminal API supports historical pool OHLCV and tokens not listed on CoinGecko.

---

# 12. Resolution flow

For each meme asset:

```text
cashtag / contract
      ↓
resolve token
      ↓
find highest-liquidity valid pool
      ↓
record pool address
      ↓
download OHLCV
      ↓
freeze mapping
```

Store:

```json
{
  "symbol": "PONS",
  "chain": "...",
  "contract": "...",
  "pool": "...",
  "provider": "geckoterminal",
  "resolved_at": "...",
  "resolution_evidence": "..."
}
```

Never resolve the asset differently later without creating a new resolution version.

---

# 13. Unsupported chains

Do NOT build a huge market-data system right now.

If token historical data cannot be obtained:

```text
NO_PRICE_DATA
```

Move on.

Never substitute another token.

Never substitute BTC.

We can add another data adapter only when missing data materially blocks the experiment.

Birdeye is a sensible second adapter because it provides historical token/pair OHLCV across multiple chains, but do not integrate it unless GeckoTerminal coverage actually fails enough calls to matter.

---

# 14. Meme trade entry

For:

```text
"buying $XYZ"
"$XYZ looks like the one"
"highest conviction is $XYZ"
```

Primary standardized evaluation entry:

```text
first available candle strictly AFTER post
```

Keep separate classification:

```text
ENTRY
vs
BULLISH_THESIS
```

Do not pretend a thesis is an exact executed trade.

But both can have forward returns.

---

# 15. Meme horizons

Use:

```text
1h
4h
24h
3d
7d
```

Memes need the extra 3d horizon.

---

# 16. Meme-specific outcomes

For every first signal/campaign calculate:

```text
return_1h
return_4h
return_24h
return_3d
return_7d

MFE_24h
MFE_3d
MFE_7d

MAE_24h
MAE_3d
MAE_7d

time_to_2x
time_to_5x
time_to_10x

hit_2x
hit_5x
hit_10x

max_multiple
```

Also:

```text
entry_liquidity
entry_market_cap if available
```

This matters much more for meme traders than 51% versus 49% directional accuracy.

---

# 17. Use log returns for aggregation

A +9,900% meme winner should not destroy every average.

Store ordinary return, but aggregate using:

```python
log_return = log(exit / entry)
```

Report both.

---

# 18. Three meme scores

Do not make it complicated.

## A. CALL QUALITY

Did explicit trades/theses make money?

```text
median return
hit rate
MFE
MAE
```

---

## B. EARLYNESS

How early were they?

At first public call:

```text
market cap
liquidity
age of token
```

Example:

```text
calls at $150k MC
```

are much more interesting than:

```text
calls after token reaches $300m
```

---

## C. BIG-WINNER CAPTURE

The key meme metric:

```text
How often do they get exposure BEFORE 5x / 10x-type moves?
```

Report:

```text
2x hit rate
5x hit rate
10x hit rate
median max multiple
```

That's enough.

---

# 19. Compare to simple meme baseline

No elaborate factor models yet.

For every meme call compare against:

```text
BTC return
SOL/chain-native return
```

and when feasible:

```text
random liquid meme on same chain at same timestamp
```

The purpose is simply to make sure:

```text
everyone made money because all memes were ripping
```

is not mistaken for alpha.

---

# 20. Macro/major backtest remains simple

Do not change the major evaluator again.

For:

```text
Timeless
XO
Astronomer
CryptoBheem
```

continue:

```text
explicit CALL
asset
direction
next-candle entry

1h
4h
24h
7d
```

with:

```text
regime
MFE
MAE
net return
baseline comparison
```

Aporia can remain in the dataset, but do not trust the old CALL score without semantic inspection.

---

# 21. Major-vs-meme distinction

The two experiments answer different things.

Major trader:

```text
Did they correctly trade BTC/ETH/etc?
```

Meme trader:

```text
Did they identify the right token early enough to monetize the move?
```

That's it.

Don't unify the reward function yet.

---

# 22. Fix `run_background.py`

Current behavior:

```text
--handle newguy
→ fetch newguy
→ extract newguy
→ append
→ rerun EVERYONE
```

Change this.

Implement:

```bash
python run_background.py --handle theunipcs
```

as:

```text
FETCH entrant
EXTRACT entrant
RESOLVE entrant assets
FETCH only missing prices
BACKTEST entrant
WRITE entrant outcomes
WRITE entrant source card
MERGE immutable result index
DONE
```

No other source is recomputed.

---

# 23. Per-source files

Create:

```text
data/sources/{handle}/
    raw/
        2026-08.json

    events.jsonl
    campaigns.jsonl
    outcomes.jsonl
    source_card.json
    manifest.json
```

This makes onboarding massively easier.

---

# 24. `author_id` must actually be populated

Current `run_background.py` writes:

```python
'author_id': ''
```

Fix it.

Use immutable X author ID from the returned tweet/user object.

Handle is metadata.

Author ID is identity.

---

# 25. Fix pagination before onboarding high-volume people

Current fetcher only gets:

```text
first page
+
one additional page
```

That is not acceptable for very active meme traders.

For each two-week window:

```python
while has_more:
    fetch(next_cursor)
```

until:

```text
has_more == false
```

Log:

```text
pages
posts
first_timestamp
last_timestamp
complete=true/false
```

We need contiguous August coverage.

---

# 26. Do not send every post through expensive semantic extraction

Cheap pre-filter first.

Meme candidate if post contains:

```text
$CASHTAG
OR contract address
OR recognized token link
```

Then semantic classifier.

This cuts the workload massively.

---

# 27. Semantic classifier should be LLM-assisted

Current regex logic is too dumb for:

```text
"not selling $PONS here"
```

or:

```text
"people selling the breakout are insane"
```

Use the existing deterministic extraction for candidates, then one structured LLM pass for:

```json
{
  "action": "ENTRY|ADD|BULLISH_THESIS|HOLD|TARGET|REDUCE|EXIT|BEARISH|RETROSPECTIVE|MENTION",
  "asset_refs": [],
  "conviction": "LOW|MEDIUM|HIGH",
  "explicit_entry": false,
  "evidence_quotes": []
}
```

Hard requirement:

```text
evidence quote must occur verbatim in raw post
```

No quote → reject field.

---

# 28. Manual validation is tiny

We are no longer building a 300-item academic benchmark before doing anything.

For every new trader:

randomly inspect:

```text
10 extracted calls
```

plus:

```text
their 5 highest-return calls
```

If obvious semantic errors exist:

fix extractor and rerun that entrant.

That is enough for this sprint.

---

# 29. August onboarding command

Implement:

```bash
python -m bear.onboard \
    --handle theunipcs \
    --month 2026-08 \
    --mode meme
```

and:

```bash
python -m bear.onboard \
    --handle Timeless_Crypto \
    --month 2026-08 \
    --mode major
```

---

# 30. Launch all six meme backtests

After one works end-to-end:

```bash
for h in \
  theunipcs \
  SevaFTW \
  kenjidgn \
  loganlim_x \
  0xAvast \
  0xnobi
do
    nohup python -m bear.onboard \
        --handle "$h" \
        --month 2026-08 \
        --mode meme \
        > "logs/${h}_august.log" 2>&1 &
done
```

Do not launch them until ONE account completes correctly.

Start with:

```text
theunipcs
```

because his posting style gives lots of explicit token theses and positions.

---

# 31. Then start prospective monitoring immediately

Once each account has passed basic extraction QA:

```text
status = MONITORED
```

Monitor:

## Meme

```text
theunipcs
SevaFTW
kenjidgn
loganlim_x
0xAvast
0xnobi
```

## Majors

```text
Timeless_Crypto
Trader_XO
astronomer_zero
CryptoBheem
0xaporia
```

Every new post:

```text
raw store
→ candidate detection
→ semantic extraction
→ append event
→ never edit afterward
```

Outcomes fill automatically as horizons expire.

---

# 32. Live event feed

Generate:

```text
data/live/events.jsonl
```

Example:

```json
{
  "timestamp": "...",
  "source": "theunipcs",
  "type": "BULLISH_THESIS",
  "asset": "PONS",
  "chain": "...",
  "price": 0.123,
  "market_cap": 12000000,
  "text": "...",
  "evidence": "...",
  "status": "OPEN"
}
```

This immediately makes BEAR useful even before perfect reputation scores exist.

---

# 33. Simple live confluence

Do not build RL.

Within rolling windows:

```text
1h
6h
24h
```

calculate:

```text
how many monitored people are bullish
how many bearish
which tokens are mentioned
first mention time
number of independent sources
```

Output:

```text
BTC:
3 bullish
1 bearish

PONS:
3 bullish meme traders
first source: 0xnobi
latest source: theunipcs
```

That's immediately useful.

---

# 34. Daily output

Produce:

```text
reports/live/latest.md
```

with:

## Major consensus

```text
BTC
ETH
SOL
```

## Meme consensus

```text
token
first caller
number bullish
market cap at first call
current market cap
return since first call
```

## New explicit calls

chronological list.

## Historical source stats

small source card next to each caller.

No strategy recommendation yet.

Just information.

---

# 35. Meme leaderboard

Output something like:

| Trader | Campaigns | Median 24h | 2x | 5x | 10x | Median Entry MC | Best Call |
| ------ | --------: | ---------: | -: | -: | --: | --------------: | --------- |

This is far more useful than:

```text
4h win rate
```

for meme traders.

---

# 36. Major leaderboard

Keep:

| Trader | Calls | 4h EV | 24h EV | Win | MFE | MAE | UP | DOWN | RANGE |
| ------ | ----: | ----: | -----: | --: | --: | --: | -: | ---: | ----: |

Again, don't merge this with meme scoring.

---

# 37. Cross-layer confluence comes AFTER we have results

Later we can ask:

```text
Aporia says risk-on
+
BTC traders bullish
+
meme traders finding 5x winners
```

versus:

```text
BTC regime weak
+
major traders bearish
+
meme scouts stop producing winners
```

That will naturally become the meta layer.

But we do not need to implement it first.

Collect the evidence now.

---

# 38. Definition of done for this sprint

The sprint is complete when:

```text
[ ] current major cohort has August results

[ ] 6 meme traders have complete August raw corpora

[ ] dynamic cashtag extraction works

[ ] token resolution works

[ ] supported meme tokens have historical OHLCV

[ ] each meme trader has campaign-level outcomes

[ ] first-caller timestamps are stored

[ ] 2x/5x/10x metrics exist

[ ] entrant-only backtest works

[ ] all 11 sources are prospectively monitored

[ ] new posts append to immutable live ledger

[ ] live major consensus exists

[ ] live meme consensus exists

[ ] no automatic trading yet
```

Then STOP.

Look at the data.

Only then decide what deserves more sophistication.

One change I would make even more strongly than in our previous plans: **do not wait for a theoretically perfect backtest before putting these accounts online.** Start immutable prospective collection as soon as each extractor works. Historical August gives us immediate clues; prospective data protects us from fooling ourselves later.

For meme pricing, GeckoTerminal is a particularly good Occam's-razor first adapter: its public API exposes token pools and historical pool OHLCV, including tokens that are not CoinGecko-listed, with roughly a 10-call/minute public limit. ([GeckoTerminal][2]) Birdeye already exposes historical token/pair OHLCV and can be the fallback only if coverage actually becomes a problem. ([Birdeye Data][3])

So the immediate sequence is simply **fix dynamic meme assets → run @theunipcs end-to-end → inspect 15 calls → launch the other five entrant-only jobs → put all 11 accounts on prospective monitoring**. That gets us much closer to something potentially usable for actual trading than another week of ontology design.

[1]: https://twiscan.com/en/x/theunipcs?utm_source=chatgpt.com "Unipcs (aka 'Bonk Guy') 🎒 (@theunipcs) — X Web Viewer"
[2]: https://api.geckoterminal.com/docs/index.html?utm_source=chatgpt.com "GeckoTerminal API Docs"
[3]: https://docs.birdeye.so/reference/price-ohlcv?utm_source=chatgpt.com "Price & OHLCV"

---

*Timestamp: 2026-09-07*
*Source: User message to BEAR agent*
*Saved word for word. No summarization. No condensation.*
