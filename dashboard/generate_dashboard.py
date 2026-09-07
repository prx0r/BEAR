#!/usr/bin/env python3
"""Generate full BEAR dashboard HTML with charts, tabs, and TradableDeath."""

import json
from pathlib import Path

DATA = json.loads(Path("/root/BEAR/dashboard/data.json").read_text())
TS = DATA.get("timestamp", "")
STATS = DATA["stats"]
CHARTS_JS = Path("/root/BEAR/dashboard/lightweight-charts.js").read_text()

# ── Leaderboards ──
TD = DATA["leaderboards"].get("tradable_death", [])[:20]
DW = DATA["leaderboards"].get("death_watch", [])[:20]
PA = DATA["leaderboards"].get("price_action", [])[:20]
SQ = DATA["leaderboards"].get("squeeze_recovery", [])[:20]
SYN = DATA["leaderboards"].get("synthesis", [])[:20]

# ── Market data ──
MKTS = sorted(DATA["markets"], key=lambda x: x.get("day_volume", 0), reverse=True)[:30]
CANDLES = DATA.get("candles", {})

def td_rows():
    rows = ""
    for i, s in enumerate(TD):
        td_val = s.get("tradable_death", 0)
        death = s.get("death_hazard", 0)
        struct = s.get("structural_decay", 0)
        setup = s.get("setup_score", 0)
        trade = s.get("tradeability", "?")
        crowd = s.get("crowd_score", 0)
        rev8w = s.get("reversal_8w", 0)
        cls = "hi" if td_val >= 0.5 else ("md" if td_val >= 0.3 else "lo")
        trade_cls = "pos" if trade == "ENTER" else ("neg" if trade == "VETO" else "dim")
        veto = ", ".join(s.get("veto_reasons", [])[:2]) if s.get("veto_reasons") else ""
        rows += f'<tr class="row" onclick="selectSym(\'{s["symbol"]}\')"><td class="dim">{i+1}</td><td class="sym">{s["symbol"]}</td><td class="num score {cls}">{td_val:.3f}</td><td class="num">{death:.0f}</td><td class="num">{struct:.0f}</td><td class="num">{setup:.0f}</td><td class="num {trade_cls}">{trade}</td><td class="num">{crowd:.0f}</td><td class="num">{rev8w:+.0%}</td><td class="dim" style="font-size:9px;max-width:120px;overflow:hidden;text-overflow:ellipsis">{veto}</td><td class="dim">{s.get("sector","")}</td></tr>\n'
    return rows

def dw_rows():
    rows = ""
    for i, s in enumerate(DW):
        sc = s.get("score", 0)
        cls = "hi" if sc >= 70 else ("md" if sc >= 50 else "lo")
        pct = min(sc, 100)
        sigs = s.get("signals", {})
        firing = s.get("signals_firing", 0)
        checks = []
        for k, l in [("volume_death","V"),("deep_decline","D"),("reversal_8w","R"),("funding_pressure","F"),("momentum","M")]:
            if sigs.get(k, {}).get("fired"): checks.append(l)
        rows += f'<tr class="row" onclick="selectSym(\'{s["symbol"]}\')"><td class="dim">{i+1}</td><td class="sym">{s["symbol"]}</td><td><div class="bar"><div class="bar-fill" style="width:{pct}%"></div></div></td><td class="num score {cls}">{sc}</td><td class="dim">{"".join(checks)}</td><td class="dim">{s.get("sector","")}</td></tr>\n'
    return rows

def pa_rows():
    rows = ""
    for i, s in enumerate(PA):
        sc = s.get("score", 0)
        cls = "hi" if sc >= 70 else ("md" if sc >= 50 else "lo")
        rows += f'<tr class="row" onclick="selectSym(\'{s["symbol"]}\')"><td class="dim">{i+1}</td><td class="sym">{s["symbol"]}</td><td class="num score {cls}">{sc:.0f}</td><td class="num">{s.get("reversal",0):.0f}</td><td class="num">{s.get("carry",0):.0f}</td><td class="num">{s.get("momentum",0):.0f}</td><td class="dim">{s.get("sector","")}</td></tr>\n'
    return rows

def sq_rows():
    rows = ""
    for i, s in enumerate(SQ):
        sc = s.get("score", 0)
        cls = "hi" if sc >= 70 else ("md" if sc >= 50 else "lo")
        rows += f'<tr class="row" onclick="selectSym(\'{s["symbol"]}\')"><td class="dim">{i+1}</td><td class="sym">{s["symbol"]}</td><td class="num score {cls}">{sc:.0f}</td><td class="num">{s.get("drawdown_30d",0):.0f}%</td><td class="num">{s.get("pump_from_low",0):+.0f}%</td><td class="num">{s.get("volume_spike",0):.1f}x</td></tr>\n'
    return rows

def syn_rows():
    rows = ""
    for i, s in enumerate(SYN):
        sc = s.get("score", 0)
        cls = "hi" if sc >= 70 else ("md" if sc >= 50 else "lo")
        boards = s.get("in_boards", 0)
        ev = " | ".join(s.get("evidence", [])[:2])
        rows += f'<tr class="row" onclick="selectSym(\'{s["symbol"]}\')"><td class="dim">{i+1}</td><td class="sym">{s["symbol"]}</td><td class="num score {cls}">{sc:.0f}</td><td class="num">{boards}/3</td><td class="dim" style="font-size:9px">{ev}</td></tr>\n'
    return rows

def mkt_rows():
    rows = ""
    for m in MKTS:
        fc = "pos" if m.get("funding", 0) > 0 else "neg"
        rows += f'<tr onclick="selectSym(\'{m["symbol"]}\')"><td style="font-weight:600">{m["symbol"]}</td><td class="num">${m.get("mark_px",0):,.2f}</td><td class="num">${m.get("day_volume",0)/1e6:,.0f}M</td><td class="num {fc}">{m.get("funding",0)*100:.4f}%</td></tr>\n'
    return rows

# Build candle JSON for JS (only top symbols)
chart_syms = [s["symbol"] for s in TD[:10]] + ["BTC", "ETH"]
chart_data = {}
for sym in chart_syms:
    if sym in CANDLES:
        chart_data[sym] = CANDLES[sym]

html = f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>BEAR</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
:root{{--bg:#0d1117;--surface:#161b22;--border:#30363d;--text:#e6edf3;--dim:#8b949e;--bright:#f0f6fc;--green:#3fb950;--red:#f85149;--yellow:#d29922;--blue:#58a6ff}}
body{{font-family:monospace;background:var(--bg);color:var(--text);font-size:13px;padding:12px;max-width:1400px;margin:0 auto}}
h1{{font-size:18px;color:var(--bright)}} h1 span{{color:var(--red)}}
h2{{font-size:12px;color:var(--dim);margin:16px 0 6px;border-bottom:1px solid var(--border);padding-bottom:4px}}
.dim{{color:var(--dim)}} .pos{{color:var(--green)}} .neg{{color:var(--red)}}
.sym{{font-weight:600;min-width:60px}} .num{{text-align:right;font-size:11px}}
.bar{{height:5px;background:var(--border);border-radius:3px;flex:1;max-width:80px}}
.bar-fill{{height:100%;border-radius:3px;background:linear-gradient(90deg,var(--green),var(--yellow),var(--red))}}
.score{{font-weight:700;min-width:28px;text-align:right;font-size:11px}}
.hi{{color:var(--red)}} .md{{color:var(--yellow)}} .lo{{color:var(--green)}}
.stats{{display:flex;gap:10px;margin-bottom:12px;flex-wrap:wrap}}
.stat{{background:var(--surface);border:1px solid var(--border);border-radius:5px;padding:6px 12px}}
.stat .l{{font-size:9px;color:var(--dim);text-transform:uppercase}} .stat .v{{font-size:16px;font-weight:700}}
table{{width:100%;border-collapse:collapse;font-size:11px}}
th{{text-align:left;color:var(--dim);padding:4px;border-bottom:1px solid var(--border);font-size:10px;cursor:pointer}}
td{{padding:4px;border-bottom:1px solid var(--border)}}
.row{{cursor:pointer}} .row:hover{{background:var(--surface)}}
.tabs{{display:flex;gap:2px;margin-bottom:8px;flex-wrap:wrap}}
.tab{{padding:5px 10px;background:var(--bg);border:1px solid var(--border);border-radius:4px 4px 0 0;cursor:pointer;font-size:11px;color:var(--dim);transition:all .15s}}
.tab:hover{{color:var(--text)}} .tab.active{{background:var(--surface);color:var(--bright);border-bottom-color:var(--surface)}}
.ml{{display:inline-block;background:var(--surface);border:1px solid var(--border);border-radius:3px;padding:1px 5px;font-size:9px;color:var(--dim);margin:0 2px}}
#chart-container{{height:300px;border:1px solid var(--border);border-radius:6px;overflow:hidden;margin-bottom:8px}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}
@media(max-width:900px){{.grid{{grid-template-columns:1fr}}}}
</style></head><body>
<h1><span>BEAR</span> -- TradableDeath Engine</h1>
<div class="dim" style="margin:4px 0">Updated: {TS} | <span class="pos">{STATS["total_markets"]} markets</span> | 4-model: Death Hazard + Structural Decay + Setup + Tradeability</div>
<div class="stats">
<div class="stat"><div class="l">Markets</div><div class="v">{STATS["total_markets"]}</div></div>
<div class="stat"><div class="l">24h Vol</div><div class="v">${STATS["total_24h_volume"]/1e9:.1f}B</div></div>
<div class="stat"><div class="l">Avg Fund</div><div class="v">{STATS["avg_funding"]*100:.4f}%</div></div>
<div class="stat"><div class="l">Pos/Neg</div><div class="v"><span class="pos">{STATS["positive_funding_count"]}</span>/<span class="neg">{STATS["negative_funding_count"]}</span></div></div>
<div class="stat"><div class="l">Weights</div><div class="v" style="font-size:10px">D35 S25 U25 V15</div></div>
</div>
<div id="chart-container"></div>
<div class="tabs">
<div class="tab active" onclick="switchTab('td')">&#127919; TradableDeath</div>
<div class="tab" onclick="switchTab('dw')">&#128148; Death Watch</div>
<div class="tab" onclick="switchTab('pa')">&#128200; Price Action</div>
<div class="tab" onclick="switchTab('sq')">&#9889; Squeeze</div>
<div class="tab" onclick="switchTab('syn')">&#128200; Synthesis</div>
</div>
<div id="board-td" class="board"><table><thead><tr><th>#</th><th>Symbol</th><th>TD</th><th>Death</th><th>Struct</th><th>Setup</th><th>Trade</th><th>Crowd</th><th>Rev8w</th><th>Veto</th><th>Sector</th></tr></thead><tbody>{td_rows()}</tbody></table></div>
<div id="board-dw" class="board" style="display:none"><h2>Death Watch <span class="ml">LEGACY</span> -- multi-signal death score</h2><table><thead><tr><th>#</th><th>Symbol</th><th>Score</th><th>Signals</th><th>Checks</th><th>Type</th></tr></thead><tbody>{dw_rows()}</tbody></table></div>
<div id="board-pa" class="board" style="display:none"><h2>Price Action -- momentum + crowding</h2><table><thead><tr><th>#</th><th>Symbol</th><th>Score</th><th>Rev</th><th>Carry</th><th>Mom</th><th>Sector</th></tr></thead><tbody>{pa_rows()}</tbody></table></div>
<div id="board-sq" class="board" style="display:none"><h2>Squeeze Recovery -- post-blowout shorts</h2><table><thead><tr><th>#</th><th>Symbol</th><th>Score</th><th>DD 30d</th><th>Pump</th><th>Vol Spike</th></tr></thead><tbody>{sq_rows()}</tbody></table></div>
<div id="board-syn" class="board" style="display:none"><h2>Synthesis -- multi-board confluence</h2><table><thead><tr><th>#</th><th>Symbol</th><th>Score</th><th>Boards</th><th>Evidence</th></tr></thead><tbody>{syn_rows()}</tbody></table></div>
<div class="grid">
<div><h2>Markets</h2><table><thead><tr><th>Symbol</th><th class="num">Price</th><th class="num">Volume</th><th class="num">Funding</th></tr></thead><tbody>{mkt_rows()}</tbody></table></div>
<div><h2>Signals</h2><div style="font-size:11px;line-height:1.8">
<div><b>TradableDeath</b> = P(zombie) x liquidity x (1-squeeze_risk)</div>
<div class="dim">D=Death 35% | S=Struct 25% | U=Setup 25% | V=Vol 15%</div>
<div class="dim">Trade: ENTER=crowd OK, VETO=BTC rallying/crowded</div>
<div style="margin-top:8px"><b>Key finding:</b> 8-10w winners revert at 90d (-9.27% for Q5 vs +9.85% for Q1)</div>
<div class="dim">Reversal spread = 19.12% (Kiefer/Nowotny 2026 validated)</div>
</div></div>
</div>
<script>
var DATA={json.dumps({"candles": chart_data})};
var currentTab='td';
function switchTab(t){{currentTab=t;document.querySelectorAll('.tab').forEach((e,i)=>{{e.classList.toggle('active',['td','dw','pa','sq','syn'][i]===t)}});document.querySelectorAll('.board').forEach(e=>e.style.display='none');document.getElementById('board-'+t).style.display='block';}}
function selectSym(sym){{renderChart(sym);}}
function renderChart(sym){{var el=document.getElementById('chart-container');var candles=DATA.candles[sym];if(!candles||!candles.length){{el.innerHTML='<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--dim);font-size:12px">No chart data for '+sym+'</div>';return;}}el.innerHTML='';if(typeof LightweightCharts==='undefined'){{el.innerHTML='<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--red)">Chart library failed to load</div>';return;}}var chart=LightweightCharts.createChart(el,{{width:el.clientWidth,height:300,layout:{{background:{{color:'#0d1117'}},textStyle:{{color:'#8b949e'}}}},grid:{{vertLines:{{color:'#21262d'}},horzLines:{{color:'#21262d'}}}},crosshair:{{mode:0}},timeScale:{{timeVisible:false}}}});var s=chart.addCandlestickSeries({{upColor:'#3fb950',downColor:'#f85149',borderUpColor:'#3fb950',borderDownColor:'#f85149',wickUpColor:'#3fb950',wickDownColor:'#f85149'}});s.setData(candles.map(c=>({{time:c.time,open:c.open,high:c.high,low:c.low,close:c.close}})));chart.timeScale().fitContent();window.addEventListener('resize',()=>{{chart.applyOptions({{width:el.clientWidth}})}});}}
renderChart('BTC');
</script>
</body></html>'''

Path("/root/BEAR/dashboard/index.html").write_text(html)
print(f"Dashboard: {len(html):,} bytes")
