# BEAR Signal Intelligence — Condensed Plan

*After 2 rounds of peer review. Simple, tested, cheap.*

---

## What We're Building

**Lossless X signal corpus + real-time capture for crypto trading.**

```
GetXAPI → raw store → normalize → extract → backtest → dashboard
```

## The Only Things That Matter

| # | Action | Cost | Worth It? |
|---|--------|------|-----------|
| 1 | Store everything (no filter) | $0 | ✅ |
| 2 | Keep replies (XO has 90%) | $0 | ✅ |
| 3 | Download media URLs | $0 | ✅ |
| 4 | Thread resolution | $0.005 | ✅ ($1-2 total) |
| 5 | Real-time monitoring | $0 (Pro) | ✅ |
| 6 | X Articles | $0.001 | ⚠️ Test first |

## What We're NOT Doing (And Why)

| Feature | Cost | Why Defer |
|---------|------|-----------|
| Chart OCR | $3+ | Text covers 80%, deferred |
| Graph analysis | $0 | Need 6+ months data first |
| User search | $0.001 | 20 accounts is enough |
| Complex ML | $0 | Start with descriptive stats |

## Budget

```
Historical backfill: ~$10
Thread resolution:   ~$2
Monitoring:          $0 (Pro plan)
────────────────────────────
Total:               ~$12
Remaining:           ~$28
```

## Key Rules (From Peer Review)

1. **Raw before filter** — Store everything, filter during analysis
2. **No selection bias** — Fetch ALL months for ALL accounts
3. **Engagement = snapshots** — Never use as historical features
4. **Use author_id** — Usernames change, IDs don't
5. **Check secrets** — Before every commit
6. **Adaptive date chunks** — Don't hardcode page limits

## Accounts (Frozen Universe)

| Tier | Accounts | Purpose |
|------|----------|---------|
| S (signal) | astronomer, Timeless, exitpump, 52kskew | Primary |
| A (context) | XO, Husslin, DeFiSquared, thiccyth0t | Secondary |
| B (archive) | 7 accounts | Discovery |

## Execution Order

```
1. Set up monitoring (TODAY) — free with Pro
2. Resolve all accounts to userId (TODAY) — 4 calls
3. Backfill 24 months (WEEK 1) — ~10,000 calls = $10
4. Extract everything (WEEK 2) — filter during analysis
5. Backtest (WEEK 3) — compare to BTC baseline
6. Dashboard (WEEK 4) — if results are good
```

## The One Rule

> **Capture first, model later. Every interpretation must be reproducible from raw data.**

---

*Not over-engineered. Just thorough.*
