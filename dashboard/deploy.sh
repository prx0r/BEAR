#!/bin/bash
set -euo pipefail

source /root/BEAR/.env.cloudflare 2>/dev/null || true
export CLOUDFLARE_API_TOKEN="${CLOUDFLARE_API_TOKEN:-}"
export CLOUDFLARE_ACCOUNT_ID="954612afb5a97bb15dddcdc70176813d"

cd /root/BEAR

echo "[$(date)] Generating data..."
PYTHONPATH=src python3 dashboard/export_data.py 2>&1 | grep -v "^$"

echo "[$(date)] Building dashboard with charts..."
PYTHONPATH=src python3 dashboard/generate_dashboard.py

echo "[$(date)] Deploying..."
mkdir -p /tmp/bear-deploy
cp dashboard/index.html dashboard/data.json dashboard/lightweight-charts.js /tmp/bear-deploy/
cd /tmp/bear-deploy
wrangler pages deploy . --project-name=bear-dashboard --branch=main --commit-dirty=true 2>&1

echo "[$(date)] Done!"
