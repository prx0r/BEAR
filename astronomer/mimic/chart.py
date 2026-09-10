"""A4: SVG chart renderer v0 — dark 1200px candles + levels, stdlib only.

Renders the last N 5m candles with swing-high/low levels and an optional
call overlay (entry/target/invalidation lines + labels). SVG keeps text
crisp; convert to PNG later (headless chromium) for X posting.
Usage: cd astronomer && python3 -m mimic.chart BTCUSDT /tmp/x.svg [--levels 67200,66500]
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
W, H, PAD = 1200, 630, 54
UP, DOWN, BG, GRID, TXT = "#26a69a", "#ef5350", "#0b0e11", "#1c2128", "#c9d1d9"


def load(symbol, n=120):
    d = json.load(open(os.path.join(ROOT, "astronomer", "data", "prices", f"{symbol}_5m.json")))
    return d[-n:]


def swings(rows, k=3):
    hi = [r["high"] for r in rows]
    lo = [r["low"] for r in rows]
    return max(hi[-60:]), min(lo[-60:])


def render(symbol, out, extra_levels=(), title=None, plan=None):
    """plan: {direction, entry, target, invalidation} -> shaded game-plan overlay.
    PNG export needs chromium/rsvg (not on box) — SVG now, convert later."""
    rows = load(symbol)
    hi, lo = swings(rows)
    for lv in list(extra_levels) + [v for k, v in (plan or {}).items()
                                    if k in ("entry", "target", "invalidation") and v]:
        hi, lo = max(hi, lv), min(lo, lv)
    span = max(hi - lo, 1e-9)
    cw = (W - 2 * PAD) / len(rows)

    def X(i):
        return PAD + i * cw + cw * 0.5

    def Y(p):
        return PAD + (1 - (p - lo) / span) * (H - 2 * PAD)

    el = [f'<rect width="{W}" height="{H}" fill="{BG}"/>']
    for f in (0.0, 0.25, 0.5, 0.75, 1.0):
        y = PAD + f * (H - 2 * PAD)
        el.append(f'<line x1="{PAD}" y1="{y:.0f}" x2="{W-PAD}" y2="{y:.0f}" stroke="{GRID}"/>')
        el.append(f'<text x="{W-PAD+6}" y="{y+4:.0f}" fill="{TXT}" font-size="13" font-family="monospace">{hi-f*span:,.0f}</text>')
    for i, r in enumerate(rows):
        c = UP if r["close"] >= r["open"] else DOWN
        bw = max(cw * 0.6, 1.5)
        el.append(f'<line x1="{X(i):.1f}" y1="{Y(r["high"]):.1f}" x2="{X(i):.1f}" y2="{Y(r["low"]):.1f}" stroke="{c}" stroke-width="1.5"/>')
        el.append(f'<rect x="{X(i)-bw/2:.1f}" y="{min(Y(r["open"]),Y(r["close"])):.1f}" width="{bw:.1f}" height="{max(abs(Y(r["close"])-Y(r["open"])),1.5):.1f}" fill="{c}"/>')
    colors = ["#f0b429", "#e040fb", "#58a6ff"]
    for j, lv in enumerate(extra_levels):
        el.append(f'<line x1="{PAD}" y1="{Y(lv):.0f}" x2="{W-PAD}" y2="{Y(lv):.0f}" stroke="{colors[j%3]}" stroke-width="1.5" stroke-dasharray="7,4"/>')
        el.append(f'<text x="{PAD+4}" y="{Y(lv)-6:.0f}" fill="{colors[j%3]}" font-size="14" font-family="monospace">L{j+1} {lv:,.0f}</text>')
    el.append(f'<text x="{PAD}" y="30" fill="{TXT}" font-size="17" font-family="monospace">{title or symbol + " 5m"} · mimichart v0</text>')
    if plan and all(plan.get(k) for k in ("entry", "target", "invalidation")):
        e, t, s = float(plan["entry"]), float(plan["target"]), float(plan["invalidation"])
        long = t > e
        rtop, rbot = (t, s) if long else (s, t)
        el.append(f'<rect x="{PAD}" y="{Y(rtop):.0f}" width="{W-2*PAD}" height="{abs(Y(rbot)-Y(rtop)):.0f}" fill="{"#26a69a" if long else "#ef5350"}" opacity="0.10"/>')
        for lv, lbl, col in ((e, f"ENTRY {e:,.0f}", "#f0b429"), (t, f"TARGET {t:,.0f}", "#26a69a"), (s, f"STOP {s:,.0f}", "#ef5350")):
            el.append(f'<line x1="{PAD}" y1="{Y(lv):.0f}" x2="{W-PAD}" y2="{Y(lv):.0f}" stroke="{col}" stroke-width="2"/>')
            el.append(f'<text x="{W-PAD-6}" y="{Y(lv)-7:.0f}" text-anchor="end" fill="{col}" font-size="14" font-family="monospace" font-weight="bold">{lbl}</text>')
        d = str(plan.get("direction", "")).upper()
        el.append(f'<text x="{PAD}" y="52" fill="{TXT}" font-size="15" font-family="monospace">{d} plan · R:R 1:{abs(t-e)/max(abs(e-s),1e-9):.1f}</text>')
    open(out, "w").write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}">' + "".join(el) + "</svg>")
    print(f"chart -> {out} ({len(rows)} candles)")


if __name__ == "__main__":
    import json as _j
    sym = sys.argv[1] if len(sys.argv) > 1 else "BTCUSDT"
    out = sys.argv[2] if len(sys.argv) > 2 else "/tmp/mimichart.svg"
    lvls, plan = [], None
    for a in sys.argv[3:]:
        if a.startswith("--levels"):
            lvls = [float(x) for x in a.split("=", 1)[1].split(",")]
        if a.startswith("--plan"):
            plan = _j.loads(a.split("=", 1)[1])
    render(sym, out, lvls, plan=plan)
