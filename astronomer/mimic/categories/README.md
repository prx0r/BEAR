# Mimic categories — data-derived account classification

Method: 7,374 posts (53 accounts, Jul+Aug 2026) archetype-classified by transparent
regex rules (see `clusters.json` for raw counts):
CALL (direction+number+level/chart) · EXIT (took profit/closed + number) ·
COND (if/waiting-for triggers) · VERDICT ("bull market because X") ·
MACRO (FOMC/CPI/DXY/yields…) · FLOW (ETF flows/OI/CVD/whale/alerts) ·
LEAN (directional lean, no levels) · CHATTER (rest).

Caveats: baseline August files are capped recon samples (n=20–100) vs complete
new pulls — small-n noise favors small files. Heuristic undercounts bespoke
formats (Chase). STATE-type value scores ~0 here by design.

Files: `trading-signals.md` (voters) · `regime-verdicts.md` (bull-market-because
voices) · `regime-data.md` (mechanical feeds) · `extra-categories.md` (emergent).
