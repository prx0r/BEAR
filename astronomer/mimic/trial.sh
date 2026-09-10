#!/bin/bash
# One-command agent-runnable mock-live trial. Offline, $0, stdlib only.
# Usage: ./trial.sh [HANDLE]   (default: astronomer_zero)
# Output: data/mimic_trials/<handle>_<date>.json  (+ stdout summary)
set -e
cd "$(dirname "$0")/.."
HANDLE="${1:-astronomer_zero}"
STAMP="$(date -u +%Y%m%d)"
SEED="$(python3 -c "import json; print(json.load(open('mimic/seed.json')).get('seed','seed1'))")"
OUT="data/mimic_trials/${HANDLE}_${SEED}_${STAMP}.json"
python3 -m mimic.mocklive --handle "$HANDLE" --json-out "$OUT" 2>&1 | tail -n 12
