# RECIPES — copy-paste operations (all paths verified 2026-09-10)

Root: `/home/ubuntu/BEAR`. Python: system `python3` (stdlib only — no pip/torch/pandas
on this box). Secrets: NEVER in commands — vault-piped via
`unset AGENT_VAULT_TOKEN ...; KEY="$(agent-vault vault credential get KEY --vault oracle)"`.
Spend: every GetXAPI call $0.001 (log to `fetch_log.jsonl`); NOTHING else costs money.

## Mimic (offline, $0)

```bash
cd /home/ubuntu/BEAR/astronomer
./mimic/trial.sh astronomer_zero        # mock-live trial + JSON report to data/mimic_trials/
python3 -m mimic.replay                 # causal replay, activity + direction Brier
STRUCT_ONLY=1 python3 -m mimic.discriminator --json-out data/mimic_trials/d.json
python3 -m mimic.chart BTCUSDT /tmp/x.svg --levels=79000,77500
python3 -m mimic.validate               # schema selftest (or: validate FILE.jsonl)
python3 -m mimic.expand_labels          # asset recovery → all_outcomes_EXPANDED.json
python3 -m mimic.fetch_market           # 5m klines + futures histories (paced, resumable)
python3 -m mimic.brain &                # :8789 brain API (2-3 min warmup)
curl localhost:8789/signal/latest?handle=astronomer_zero
```

## Data pulls (SPEND — H/M approval first)

```bash
python3 /tmp/opencode/month_pull.py 2026-07 HANDLE [HANDLE...]   # $0.001/page, logged
# recon single: user_info $0.001; August pattern: 2-week chunks + cursor (see aug_pull.py)
```

## Quality scoring (offline, $0)

Same regex battery everywhere (CALL+levels+charts): see session reports.
Archetype classifier lives inline in analysis scripts; canonical labels in
`astronomer/mimic/categories/schemas.md` + `schema.json`.

## Infra (PAUSED — explicit resume order required)

- Worker: `cloudflare/astro-poll/` (`npx wrangler deploy`; secrets via
  `wrangler secret put`; schedules currently `[]`).
- VPS drain: `MIMIC_NS_ID=<id> python3 -m mimic.inbox_pull` (cron line in git history).
- x402 signal server: build doc `~/mimichart/README.md`; payer scripts `~/x402/x402fun/`.

## Entry map for new agents

`README.md` banner → `AGENTS.md` → `threads.md` → `mimichartastro.md` →
`AUDIT-2026-09-10.md` → this file. Live state = `threads.md`, always.
