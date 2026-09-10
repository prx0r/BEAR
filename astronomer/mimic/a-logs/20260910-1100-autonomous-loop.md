# A-log 2026-09-10 11:00 UTC — autonomous loop (all $0)

## Round-trips ×5 (after string-sort + maxhold + entry-guard fixes)
| Handle | Posts | Trips | Partials | Win | AvgRet | AvgHold |
|---|---|---|---|---|---|---|
| astro | 766 | 32 | 14 | 18/32 | -0.30% | 107h |
| Timeless | 2658 | 20 | 10 | 9/20 | -3.35% | 716h |
| XO | 776 | 11 | 0 | 7/11 | +6.86% | 640h |
| Bheem | 883 | 16 | 24 | 9/16 | +1.92% | 441h |
| eliz | 813 | 3 | 0 | 1/3 | -0.23% | 380h |
Total 82 trips. Bugs killed: lexicographic createdAt sort (caused negative holds);
no-maxhold absurdity (96d chains); loose entry fallback (philosophy posts as entries).
Caveat: per-handle close-language differs (XO/eliz partials=0) — needs calibration.

## Pairs ×5: 3,939 total (724 astro + 1718 + 514 + 513 + 470). Neutralizer v1.2 at 0% leak.

## Dead-code sweep: NO safe deletions. gecko_adapter dormant (needs httpx, meme track).
Everything else live/entry-point/scoped. Sweep method: import-graph + docs + __main__.

## Files: roundtrips_{5}.json, mimic_pairs_{5}.json, neutralize.py, twobots.md (prior run).
