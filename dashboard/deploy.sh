#!/bin/bash
set -euo pipefail

export CLOUDFLARE_API_TOKEN="YOUR_CLOUDFLARE_API_TOKEN"
export CLOUDFLARE_ACCOUNT_ID="954612afb5a97bb15dddcdc70176813d"

cd /root/BEAR

# 1. Generate fresh data.json
echo "[$(date)] Generating data..."
PYTHONPATH=src python3 dashboard/export_data.py 2>&1 | grep -v "^$"

# 2. Generate static HTML from data (server-side rendered)
echo "[$(date)] Building static dashboard..."
PYTHONPATH=src python3 /dev/stdin << 'PYEOF'
import json
from pathlib import Path
data = json.loads(Path("dashboard/data.json").read_text())
dw = data["leaderboards"].get("death_watch", [])[:20]
stats = data["stats"]
ts = data.get("timestamp", "")

lb_rows = ""
for i, s in enumerate(dw):
    sc = s.get("score", 0)
    cls = "hi" if sc >= 70 else ("md" if sc >= 50 else "lo")
    pct = min(sc, 100)
    vd = (s.get("vol_death_ratio", 0) or 0) * 100
    dd = s.get("drawdown", 0) or 0
    r90 = s.get("ret_90d", 0) or 0
    rc = "pos" if r90 > 0 else "neg"
    rs = f"+{r90:.0f}" if r90 > 0 else f"{r90:.0f}"
    m = "MEME" if s.get("is_meme") else "UTIL"
    lb_rows += f'<tr class="row"><td class="dim">{i+1}</td><td class="sym">{s["symbol"]}</td><td><div class="bar"><div class="bar-fill" style="width:{pct}%"></div></div></td><td class="num score {cls}">{sc}</td><td class="num">{vd:.1f}%</td><td class="num neg">{dd:.0f}%</td><td class="num {rc}">{rs}%</td><td class="dim">{m}</td></tr>\n'

mkts = sorted(data["markets"], key=lambda x: x.get("day_volume", 0), reverse=True)[:30]
mkt_rows = ""
for m in mkts:
    fc = "pos" if m.get("funding", 0) > 0 else "neg"
    mkt_rows += f'<tr><td style="font-weight:600">{m["symbol"]}</td><td class="num">${m.get("mark_px",0):,.2f}</td><td class="num">${m.get("day_volume",0)/1e6:,.0f}M</td><td class="num {fc}">{m.get("funding",0)*100:.4f}%</td></tr>\n'

html = f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>BEAR</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:monospace;background:#0d1117;color:#e6edf3;font-size:13px;padding:12px}}
h1{{font-size:16px;color:#f0f6fc}}h1 span{{color:#3fb950}}.dim{{color:#8b949e}}.pos{{color:#3fb950}}.neg{{color:#f85149}}
.row{{display:flex;align-items:center;gap:6px;padding:4px 0;border-bottom:1px solid #30363d}}
.sym{{font-weight:600;min-width:60px}}.num{{text-align:right}}
.bar{{height:5px;background:#30363d;border-radius:3px;flex:1;max-width:120px}}
.bar-fill{{height:100%;border-radius:3px;background:linear-gradient(90deg,#3fb950,#d29922,#f85149)}}
.score{{font-weight:700;min-width:30px;text-align:right}}.hi{{color:#f85149}}.md{{color:#d29922}}.lo{{color:#3fb950}}
.stats{{display:flex;gap:10px;margin-bottom:12px;flex-wrap:wrap}}
.stat{{background:#161b22;border:1px solid #30363d;border-radius:5px;padding:6px 12px}}
.stat .l{{font-size:9px;color:#8b949e;text-transform:uppercase}}.stat .v{{font-size:16px;font-weight:700}}
table{{width:100%;border-collapse:collapse;font-size:11px}}
th{{text-align:left;color:#8b949e;padding:4px;border-bottom:1px solid #30363d}}
td{{padding:4px;border-bottom:1px solid #30363d}}
</style></head><body>
<h1><span>BEAR</span> -- Short Opportunity Engine</h1>
<div class="dim" style="margin:4px 0">Updated: {ts} | <span class="pos">{stats["total_markets"]} markets</span> | Death Watch: Sharpe 0.45, win 66%</div>
<div class="stats">
<div class="stat"><div class="l">Markets</div><div class="v">{stats["total_markets"]}</div></div>
<div class="stat"><div class="l">24h Vol</div><div class="v">${stats["total_24h_volume"]/1e9:.1f}B</div></div>
<div class="stat"><div class="l">Avg Fund</div><div class="v">{stats["avg_funding"]*100:.4f}%</div></div>
<div class="stat"><div class="l">Pos/Neg</div><div class="v"><span class="pos">{stats["positive_funding_count"]}</span>/<span class="neg">{stats["negative_funding_count"]}</span></div></div>
</div>
<div style="margin-bottom:8px;font-size:11px"><b>Death Watch</b> -- tokens most likely to die</div>
<table><thead><tr><th>#</th><th>Symbol</th><th>Score</th><th>Vol Death</th><th>DD%</th><th>90d%</th><th>Type</th></tr></thead>
<tbody>{lb_rows}</tbody></table>
<h2 style="margin-top:16px;font-size:12px;color:#8b949e">Market Overview</h2>
<table><thead><tr><th>Symbol</th><th class="num">Price</th><th class="num">Volume</th><th class="num">Funding</th></tr></thead>
<tbody>{mkt_rows}</tbody></table>
</body></html>'''

Path("dashboard/index.html").write_text(html)
print(f"Static HTML: {len(html):,} bytes")
PYEOF

# 3. Deploy to Cloudflare Pages
echo "[$(date)] Deploying..."
mkdir -p /tmp/bear-deploy
cp dashboard/index.html /tmp/bear-deploy/
cd /tmp/bear-deploy
wrangler pages deploy . --project-name=bear-dashboard --branch=main --commit-dirty=true 2>&1

echo "[$(date)] Deploy complete!"
