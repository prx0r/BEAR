#!/bin/bash
set -euo pipefail

# BEAR Dashboard Auto-Deploy to Cloudflare Pages
# Runs every 5 minutes via cron

export CLOUDFLARE_API_TOKEN="YOUR_CLOUDFLARE_API_TOKEN"
export CLOUDFLARE_ACCOUNT_ID="954612afb5a97bb15dddcdc70176813d"

cd /root/BEAR

# 1. Sync fresh market data from Hyperliquid
echo "[$(date)] Syncing markets..."
PYTHONPATH=src python3 -c "
import asyncio
from bear.hyperliquid.client import HyperliquidClient
from bear.hyperliquid.universe import UniverseManager
from bear.data.store import DataStore
import polars as pl

async def sync():
    client = HyperliquidClient()
    store = DataStore()
    um = UniverseManager(client)
    snap = await um.refresh()
    rows = []
    for a in snap.assets:
        rows.append({
            'symbol': a.name, 'name': a.name,
            'dex': a.market_id.split(':')[0] if ':' in a.market_id else 'core',
            'sz_decimals': a.sz_decimals, 'max_leverage': a.max_leverage,
            'is_delisted': a.is_delisted, 'margin_table_id': a.margin_table_id,
            'category': a.category, 'mark_px': float(a.mark_px),
            'mid_px': float(a.mid_px), 'oracle_px': float(a.oracle_px),
            'funding': float(a.funding), 'open_interest': float(a.open_interest),
            'day_volume': float(a.day_ntl_vlm),
        })
    df = pl.DataFrame(rows)
    store.save_markets(df)
    print(f'Synced {len(df)} markets')
    await client.close()

asyncio.run(sync())
" 2>&1

# 2. Generate fresh dashboard with baked-in data
echo "[$(date)] Generating dashboard..."
PYTHONPATH=src python3 dashboard/export_data.py 2>&1

# 3. Deploy to Cloudflare Pages
echo "[$(date)] Deploying to Cloudflare Pages..."
mkdir -p /tmp/bear-deploy
cp dashboard/index.html /tmp/bear-deploy/
cp dashboard/data.json /tmp/bear-deploy/

cd /tmp/bear-deploy
wrangler pages deploy . --project-name=bear-dashboard --branch=main --commit-dirty=true 2>&1

echo "[$(date)] Deploy complete!"
