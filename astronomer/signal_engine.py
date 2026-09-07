"""Combined signal engine — X opinions + Binance positions = conviction."""

import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))


# Evidence weights — positions > opinions
EVIDENCE_WEIGHTS = {
    # X/Twitter signals
    "tweet_bullish": 0.25,
    "tweet_bearish": 0.25,
    "tweet_explicit_entry": 0.50,
    "tweet_explicit_exit": 0.50,

    # Binance position signals
    "binance_open_long": 1.00,
    "binance_open_short": 1.00,
    "binance_add_position": 1.25,
    "binance_reduce_position": 0.75,
    "binance_close_position": 0.50,

    # Multi-source confirmation
    "tweet_plus_binance_align": 2.00,
    "tweet_plus_binance_conflict": 0.10,

    # On-chain (future)
    "onchain_wallet_buy": 1.00,
    "onchain_whale_accumulation": 1.50,
}


@dataclass
class SignalEvent:
    """A normalized signal event from any source."""
    id: str = ""
    timestamp: str = ""
    source: str = ""  # x, binance, onchain
    trader: str = ""
    symbol: str = ""
    direction: str = ""  # LONG, SHORT, FLAT
    action: str = ""  # OPEN, ADD, REDUCE, CLOSE, STATE
    size_usd: float = 0.0
    entry_price: float = 0.0
    current_price: float = 0.0
    evidence_weight: float = 0.0
    raw_data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TraderReputation:
    """Per-symbol reputation score for a trader."""
    trader: str
    symbol: str
    sample_size: int = 0
    directional_accuracy_24h: float = 0.0
    median_return_24h: float = 0.0
    profit_factor: float = 0.0
    reputation_score: float = 0.5  # 0-1

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SymbolConsensus:
    """Aggregate smart money positioning for a symbol."""
    symbol: str
    timestamp: str = ""
    long_count: int = 0
    short_count: int = 0
    flat_count: int = 0
    long_notional: float = 0.0
    short_notional: float = 0.0
    consensus_score: float = 0.0  # -1 to +1
    delta_1h: float = 0.0  # change in consensus
    high_reputation_long: int = 0
    high_reputation_short: int = 0
    weighted_consensus: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


def compute_symbol_consensus(positions: list[dict], reputations: dict) -> SymbolConsensus:
    """Compute aggregate positioning for a symbol."""
    symbol = positions[0]["symbol"] if positions else ""

    long_count = sum(1 for p in positions if p.get("side") == "LONG")
    short_count = sum(1 for p in positions if p.get("side") == "SHORT")
    flat_count = len(positions) - long_count - short_count

    long_notional = sum(
        p.get("size", 0) * p.get("mark", p.get("entryPrice", 0))
        for p in positions if p.get("side") == "LONG"
    )
    short_notional = sum(
        p.get("size", 0) * p.get("mark", p.get("entryPrice", 0))
        for p in positions if p.get("side") == "SHORT"
    )

    total = long_notional + short_notional
    consensus = (long_notional - short_notional) / total if total > 0 else 0

    # Weighted by reputation
    weighted_long = 0
    weighted_short = 0
    for p in positions:
        trader = p.get("trader", "")
        rep = reputations.get(f"{trader}:{symbol}", {}).get("reputation_score", 0.5)
        notion = p.get("size", 0) * p.get("mark", p.get("entryPrice", 0))
        if p.get("side") == "LONG":
            weighted_long += notion * rep
        elif p.get("side") == "SHORT":
            weighted_short += notion * rep

    weighted_total = weighted_long + weighted_short
    weighted_consensus = (weighted_long - weighted_short) / weighted_total if weighted_total > 0 else 0

    return SymbolConsensus(
        symbol=symbol,
        timestamp=datetime.now(timezone.utc).isoformat(),
        long_count=long_count,
        short_count=short_count,
        flat_count=flat_count,
        long_notional=long_notional,
        short_notional=short_notional,
        consensus_score=consensus,
        weighted_consensus=weighted_consensus,
    )


def cross_source_conviction(
    x_signals: list[dict],
    binance_changes: list[dict],
) -> list[dict]:
    """Compute conviction when X opinions align with Binance positions."""
    convictions = []

    for x in x_signals:
        symbol = x.get("asset", "BTC")
        direction = x.get("direction", "")
        trader = x.get("author", "")

        # Find matching Binance position changes
        matching_binance = [
            b for b in binance_changes
            if b.get("symbol", "").startswith(symbol)
            and b.get("trader", "")[:10] in trader
        ]

        if matching_binance:
            for b in matching_binance:
                binance_side = "LONG" if "LONG" in str(b.get("side", "")) else "SHORT"
                aligns = (direction == binance_side)

                convictions.append({
                    "source": "cross_source",
                    "trader": trader,
                    "symbol": symbol,
                    "x_direction": direction,
                    "binance_action": b.get("type", ""),
                    "binance_side": binance_side,
                    "aligns": aligns,
                    "weight": EVIDENCE_WEIGHTS["tweet_plus_binance_align" if aligns else "tweet_plus_binance_conflict"],
                    "x_text": x.get("thesis", "")[:100],
                })

    return convictions


def generate_report(
    consensus: list[SymbolConsensus],
    convictions: list[dict],
    changes: list[dict],
) -> str:
    """Generate human-readable report."""
    lines = [
        "# Smart Money Signal Report",
        f"**Time:** {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Symbol Consensus",
        "",
        "| Symbol | Longs | Shorts | Notional Long | Notional Short | Consensus | Weighted |",
        "|--------|-------|--------|---------------|----------------|-----------|----------|",
    ]

    for s in sorted(consensus, key=lambda x: abs(x.weighted_consensus), reverse=True):
        lines.append(
            f"| {s.symbol} | {s.long_count} | {s.short_count} | "
            f"${s.long_notional:,.0f} | ${s.short_notional:,.0f} | "
            f"{s.consensus_score:+.2f} | {s.weighted_consensus:+.2f} |"
        )

    if convictions:
        lines.extend(["", "## Cross-Source Convictions", ""])
        for c in convictions[:10]:
            emoji = "✅" if c["aligns"] else "❌"
            lines.append(
                f"- {emoji} **{c['trader']}** on {c['symbol']}: "
                f"X={c['x_direction']} vs Binance={c['binance_side']} "
                f"({c['binance_action']}) — weight {c['weight']:.2f}"
            )

    if changes:
        lines.extend(["", "## Position Changes", ""])
        for c in changes[:15]:
            lines.append(
                f"- {c['type']} {c['symbol']} {c.get('side', '?')} — "
                f"trader {c['trader'][:12]}..."
            )

    return "\n".join(lines)


def main():
    """Run combined signal analysis."""
    print("=== Combined Signal Engine ===\n")

    # Load latest Binance data
    binance_path = Path(__file__).parent / "data" / "binance_latest.json"
    if binance_path.exists():
        with open(binance_path) as f:
            binance_data = json.load(f)
        traders = binance_data.get("traders", [])
    else:
        traders = []

    # Load latest X signals
    signals_path = Path(__file__).parent / "data" / "signals.jsonl"
    x_signals = []
    if signals_path.exists():
        with open(signals_path) as f:
            for line in f:
                if line.strip():
                    try:
                        x_signals.append(json.loads(line))
                    except:
                        pass

    print(f"Binance traders: {len(traders)}")
    print(f"X signals: {len(x_signals)}")

    # Compute consensus per symbol
    symbol_positions = defaultdict(list)
    for t in traders:
        uid = t.get("topTraderId", t.get("encryptedUid", ""))
        for pos in t.get("positions", {}).get("UM", []):
            symbol_positions[pos["symbol"]].append({
                "trader": uid,
                "symbol": pos["symbol"],
                "side": pos["side"],
                "size": pos.get("amount", 0),
                "entry": pos.get("entryPrice", 0),
                "mark": pos.get("markPrice", 0),
                "pnl": pos.get("pnl", 0),
            })

    consensus = []
    for symbol, positions in symbol_positions.items():
        s = compute_symbol_consensus(positions, {})
        consensus.append(s)

    # Cross-source conviction
    convictions = cross_source_conviction(x_signals, [])

    # Generate report
    report = generate_report(consensus, convictions, [])

    # Save
    report_path = Path(__file__).parent / "data" / "signal_report.md"
    with open(report_path, "w") as f:
        f.write(report)

    consensus_path = Path(__file__).parent / "data" / "symbol_consensus.json"
    with open(consensus_path, "w") as f:
        json.dump([s.to_dict() for s in consensus], f, indent=2)

    print(f"\nReport saved to {report_path}")
    print(f"Consensus saved to {consensus_path}")
    print(f"\n{'='*60}")
    print(report)


if __name__ == "__main__":
    main()
