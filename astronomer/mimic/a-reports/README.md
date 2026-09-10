# Peer-review pack — tournament loop seed1 → seed1.1

## How to verify (reproduce everything, $0)

```bash
cd /home/ubuntu/BEAR && git checkout seed1   # or seed1.1
cd astronomer
./mimic/trial.sh astronomer_zero   # compare vs data/mimic_trials/*_seed*_20260910.json
STRUCT_ONLY=1 python3 -m mimic.discriminator
python3 -m mimic.validate
```

## Reports (validation evidence inside each)

- `A-T2-tournament-seed1.md` — baseline numbers + determinism check
- `A-T4-tournament-seed1.1.md` — 3 changes, mixed/rejected verdicts with deltas

## Logs (raw evidence)

- `../a-logs/20260910-seed1-tournament.md` (numbers table)
- `../a-logs/20260910-seed1.1-tournament.md` (verdict: REJECT wholesale)

## Probe these (known weak spots, peer please attack)

1. Direction n is small (XO 55, astro 198) — are the seed1→1.1 deltas noise?
2. Transfer test uses astro weights on foreign regimes — fair, or strawman?
3. Rerank Jaccard differences are ±0.01 — distinguishable from sampling noise?
4. `commit()` writes predictions log on every mock-live bucket — 17k+ lines; intended?
5. seed1 branch has unreviewed bulk commit (b0e44f6) — review before any master merge.

## Stop-check

A-T1 northstar/seed/branch ✓ · A-T2 tournament+a-log+a-report ✓ ·
A-T3 justifications ✓ · A-T4 implement+compare+a-report ✓ · A-T5 this pack ✓.
Loop STOPS here per NORTHSTAR.md until peer verdict returns items.
