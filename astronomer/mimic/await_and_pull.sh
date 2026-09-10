#!/bin/bash
# Wait for GetXAPI recovery (free account/me probe), then pull remainder:
#   XO 2025-05-11 window + astro Sep24-Apr26 gap. Resumable, idempotent.
# Usage: nohup ./await_and_pull.sh >> data/await_pull.log 2>&1 &
cd /home/ubuntu/BEAR/astronomer
unset AGENT_VAULT_TOKEN AGENT_VAULT_ADDR AGENT_VAULT_VAULT
export GETXAPI_KEY="$(agent-vault vault credential get GETXAPI_KEY --vault oracle 2>/dev/null)"
for i in $(seq 1 72); do
  if python3 -c "
import os, urllib.request
KEY=os.environ['GETXAPI_KEY']
urllib.request.urlopen(urllib.request.Request('https://api.getxapi.com/account/me', headers={'Authorization': f'Bearer {KEY}'}), timeout=25).read()
" 2>/dev/null; then
    echo "$(date -u +%FT%TZ) API UP after $((i*10))min — pulling remainder"
    python3 /home/ubuntu/BEAR/astronomer/mimic/range_pull.py Trader_XO 2025-05-11 2025-05-25
    python3 /home/ubuntu/BEAR/astronomer/mimic/range_pull.py astronomer_zero 2024-09-01 2026-04-08
    echo "$(date -u +%FT%TZ) pulls done"
    exit 0
  fi
  echo "$(date -u +%FT%TZ) still down (try $i/72)"
  sleep 600
done
echo "$(date -u +%FT%TZ) GAVE UP after 12h"
