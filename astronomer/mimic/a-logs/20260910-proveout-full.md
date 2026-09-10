# A-log full-history prove-out ($0, frozen seed1.4 weights)

| Handle | n | MODEL | 95% CI | ACTUAL | Verdict |
|---|---|---|---|---|---|
| astro | 89 | 50/89 56% | (46,66) | 48/89 54% | matches man; OOS 56% = INS 56% (stable) |
| Timeless | 173 | 96/173 55% | (48,63) | 101/173 58% | close; lower bound 48% |
| XO | 25 | 11/25 44% | (27,63) | 13/25 52% | worse, tiny n |

282 paper posts (txt+mmd) in data/proveout_posts_*/. No lower bound clears 50% —
no edge claim. But: zero degradation OOS vs in-sample anywhere = the pipeline
generalizes; the missing ingredient is n + selection (gate-conditioning), not modeling.
