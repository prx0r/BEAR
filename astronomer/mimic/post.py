"""Deterministic signal-post generator — template + verified numbers, zero LLM.

Takes a signal dict {asset, direction, entry, target, invalidation, regime,
p_bullish, horizon_h} and renders post text. Every number echoed back from the
input (fail-closed: missing entry/target/invalidation -> refund/None, never invent).
Style: terse trader telegram — structure mimics call posts, no voice claims.
Usage: python3 -m mimic.post demo
"""
import json
import sys


def render(sig: dict) -> str | None:
    for k in ("asset", "direction", "entry", "target", "invalidation"):
        if sig.get(k) is None:
            return None
    d = "LONG" if str(sig["direction"]).upper().startswith(("LONG", "BULL", "BUY")) else "SHORT"
    arrow = "▲" if d == "LONG" else "▼"
    lines = [
        f"${sig['asset']} {d} {arrow}",
        f"Entry: {sig['entry']}",
        f"Target: {sig['target']}",
        f"Invalidation: {sig['invalidation']}",
    ]
    if sig.get("regime"):
        lines.append(f"Regime: {sig['regime']}")
    if sig.get("p_bullish") is not None:
        lines.append(f"Model P: {float(sig['p_bullish']):.2f}")
    if sig.get("horizon_h"):
        lines.append(f"Horizon: {sig['horizon_h']}h")
    lines.append("Not financial advice. Paper signal.")
    return "\n".join(lines)


def demo():
    sig = {"asset": "BTC", "direction": "LONG", "entry": 78250, "target": 81000,
           "invalidation": 76500, "regime": "RANGE", "p_bullish": 0.61, "horizon_h": 24}
    print(render(sig))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        demo()
    else:
        print(render(json.load(sys.stdin)) or "REFUSED: missing required number")
