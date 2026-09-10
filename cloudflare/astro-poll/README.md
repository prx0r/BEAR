# astro-poll — 1-min X poll worker (PAUSED)

Polls 10 handles via GetXAPI → per-handle KV inbox. VPS drains it
(`mimic/inbox_pull.py`). Status 2026-09-10: DEPLOYED but schedules deleted —
zero spend. 1-min polling was 99.65% waste; resume plan is 15-min + dead-zone
skip (see `threads.md` P1–P3).

Ops (secrets NEVER in code — vault-piped only):
```bash
npm i
export CLOUDFLARE_API_TOKEN="$(agent-vault vault credential get CLOUDFLARE_API_TOKEN --vault oracle)"
export CLOUDFLARE_ACCOUNT_ID="$(agent-vault vault credential get CLOUDFLARE_ACCOUNT_ID --vault oracle)"
agent-vault vault credential get GETXAPI_KEY --vault oracle | npx wrangler secret put GETXAPI_KEY
npx wrangler deploy
curl https://astro-poll.tradesprior.workers.dev/tick   # manual tick ($0.001/handle)
```
KV: namespace `MIMIC_STATE` (`f4358b…9d12b`); keys `{handle}/last_seen_id`,
`{handle}/inbox`, `mimic/last_tick`. Writes only on new posts + hourly heartbeat.
PAUSED flag in `src/index.js` force-stops polling even if a schedule is restored.
