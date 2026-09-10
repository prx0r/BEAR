"""Mermaid game-plan diagrams from signal JSON — deterministic, zero deps.

Why mermaid: text-based (agent-readable, versionable, diffable), renders on
GitHub/VSCode/Notion/chat UIs, zero production cost. Limits: NO candlesticks
(xychart does line/bar only) and X itself doesn't render it — so: mermaid for
game-plan + API/agent surfaces, SVG candles for pixels, PNG later for X.
Rules to avoid silent render failure: simple labels, no backticks/quotes in
nodes, <20 nodes.
Usage: python3 -m mimic.diagram --plan '{"direction":"LONG",...}' | python3 -m mimic.post
"""
import json
import sys


def _sid(s):
    return "".join(c if c.isalnum() else "_" for c in str(s))[:24]


def gameplan(sig: dict) -> str | None:
    for k in ("asset", "direction", "entry", "target", "invalidation"):
        if sig.get(k) is None:
            return None
    d = "LONG" if str(sig["direction"]).upper().startswith(("LONG", "BULL", "BUY")) else "SHORT"
    e, t, s = sig["entry"], sig["target"], sig["invalidation"]
    a = _sid(sig["asset"])
    L = [f"flowchart LR",
         f'    sig[["${a} {d} @ {e}"]]',
         f'    sig -->|"hold above {s}"| tgt[["TARGET {t}"]]',
         f'    sig -->|"lose {s}"| stp[["STOPPED · max loss {abs(float(e)-float(s)):.0f}"]]',
         f'    tgt -->|"partial 50%"| t2[["runner to measured move"]]',
         f'    style sig fill:#f0b429,stroke:#333',
         f'    style tgt fill:#26a69a,stroke:#333',
         f'    style stp fill:#ef5350,stroke:#333']
    if sig.get("regime"):
        L.append(f'    sub["regime {sig["regime"]}" ]')
    return "\n".join(L)


def roundtrip(trip: dict) -> str | None:
    if not trip.get("entry_price") or not trip.get("exit_price"):
        return None
    d = trip.get("dir", "?")
    L = ["flowchart LR",
         f'    e[["ENTRY {trip["entry_price"]} {d}"]]',
         f'    e -->|"hold {trip.get("hold_h","?")}h · MFE {trip.get("mfe","?")}"| x[["EXIT {trip["exit_price"]}"]]']
    for i, p in enumerate(trip.get("partials", [])[:3]):
        f = p.get("frac")
        L.append(f'    e -.->|"partial {f if f is not None else "? "}"| p{i}[["TP{i+1}"]]')
        L.append(f'    p{i} -.-> x')
    return "\n".join(L)


if __name__ == "__main__":
    if "--plan" in sys.argv:
        print(gameplan(json.loads(sys.argv[sys.argv.index("--plan") + 1])) or "REFUSED")
    elif "--trip" in sys.argv:
        print(roundtrip(json.load(open(sys.argv[sys.argv.index("--trip") + 1]))) or "REFUSED")
    else:
        print(gameplan({"asset": "BTC", "direction": "LONG", "entry": 78250,
                        "target": 81000, "invalidation": 76500, "regime": "RANGE"})
              or "REFUSED")
