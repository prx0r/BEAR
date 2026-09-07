# API Budget Rules

**Two GetXAPI keys. Track both.**

## Key Status

| Key | Balance | Status |
|-----|---------|--------|
| Primary | $0.01 | Almost empty |
| Backup | $0.15 | Active |

## Current Spend



## Rules

1. **Use backup key when primary is empty.** Already switched.
2. **Never fetch more than needed.** count=3 for sampling, count=10 for monitoring.
3. **Cache everything.** Never re-fetch the same tweet.
4. **Log every call.** Check balance before each run.
5. **Sample first, bulk later.** Test with 3 tweets before fetching 20.

## Cost Reference

| Task | Calls | Cost |
|------|-------|------|
| Sample 1 account × 3 tweets | 1 | $0.001 |
| Monitor 8 signal accounts | 8 | $0.008 |
| Full 30-account scan | 30 | $0.030 |
| Historical backfill (1 month) | 8 | $0.008 |
| Historical backfill (1 year) | 96 | $0.096 |

## API Usage Log

| Timestamp | Key | Calls | Cost | Notes |
|-----------|-----|-------|------|-------|
| 2026-09-06 21:49 | Primary | 100 | $0.10 | Initial setup, all accounts |
| 2026-09-07 00:24 | Backup | 4 | $0.004 | Sampled remaining accounts |
