"""Multi-account confluence scoring."""

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from signal_schema import Signal, Direction, ConfluenceScore


def load_accounts() -> dict:
    """Load account weights with tier multipliers."""
    accounts_path = Path(__file__).parent / "accounts.json"
    with open(accounts_path) as f:
        data = json.load(f)

    weights = {}
    tiers = data.get("tiers", {})
    for a in data["accounts"]:
        tier = a.get("tier", "ct_social")
        multiplier = tiers.get(tier, {}).get("weight_multiplier", 1.0)
        base = a.get("weight", 1.0)
        weights[a["handle"]] = base * multiplier

    return weights


def compute_confluence(signals: list[Signal]) -> list[ConfluenceScore]:
    """Compute confluence scores across accounts."""
    weights = load_accounts()

    # Group signals by (direction, asset, timeframe)
    groups = defaultdict(lambda: {"accounts": set(), "weights": [], "signals": []})

    for s in signals:
        if s.direction == Direction.NEUTRAL:
            continue

        key = (s.direction, s.asset, s.timeframe.value)
        groups[key]["accounts"].add(s.author)
        groups[key]["weights"].append(weights.get(s.author, 1.0))
        groups[key]["signals"].append(s)

    # Compute scores
    scores = []
    for (direction, asset, tf), data in groups.items():
        total_weight = sum(data["weights"])
        signal_count = len(data["signals"])
        avg_confidence = sum(
            {"high": 1.0, "medium": 0.6, "low": 0.3}.get(s.confidence.value, 0.5)
            for s in data["signals"]
        ) / signal_count

        # Determine strength
        if total_weight >= 4.0 or len(data["accounts"]) >= 4:
            strength = "strong"
        elif total_weight >= 2.5 or len(data["accounts"]) >= 3:
            strength = "moderate"
        elif len(data["accounts"]) >= 2:
            strength = "weak"
        else:
            strength = "none"

        scores.append(ConfluenceScore(
            direction=direction,
            asset=asset,
            timeframe=tf,
            accounts_aligned=sorted(data["accounts"]),
            total_weight=total_weight,
            signal_count=signal_count,
            avg_confidence=avg_confidence,
            strength=strength,
        ))

    # Sort by strength then weight
    strength_order = {"strong": 0, "moderate": 1, "weak": 2, "none": 3}
    scores.sort(key=lambda s: (strength_order.get(s.strength, 3), -s.total_weight))

    return scores


def generate_confluence_report(scores: list[ConfluenceScore]) -> str:
    """Generate human-readable confluence report."""
    lines = [
        "# Confluence Report",
        "",
    ]

    for score in scores:
        if score.strength == "none":
            continue

        emoji = {"strong": "🟢", "moderate": "🟡", "weak": "🟠"}.get(score.strength, "⚪")
        lines.extend([
            f"## {emoji} {score.direction.value} {score.asset} ({score.timeframe}) — {score.strength.upper()}",
            f"- **Accounts aligned:** {', '.join(f'@{a}' for a in score.accounts_aligned)}",
            f"- **Weight:** {score.total_weight:.1f}",
            f"- **Signals:** {score.signal_count}",
            f"- **Avg confidence:** {score.avg_confidence:.0%}",
            "",
        ])

    if not any(s.strength != "none" for s in scores):
        lines.append("*No significant confluence detected.*")

    return "\n".join(lines)


def main():
    """Compute confluence from latest signals."""
    signals_path = Path(__file__).parent / "data" / "signals.jsonl"
    if not signals_path.exists():
        print("No signals.jsonl found. Run extractor.py first.")
        return

    # Load recent signals (last 24h worth)
    signals = []
    with open(signals_path) as f:
        for line in f:
            if line.strip():
                try:
                    signals.append(Signal.from_dict(json.loads(line)))
                except:
                    pass

    print(f"Loaded {len(signals)} signals")

    scores = compute_confluence(signals)
    report = generate_confluence_report(scores)

    # Save
    out_path = Path(__file__).parent / "data" / "confluence.json"
    with open(out_path, "w") as f:
        json.dump([s.to_dict() for s in scores], f, indent=2)

    report_path = Path(__file__).parent / "data" / "confluence_report.md"
    with open(report_path, "w") as f:
        f.write(report)

    print(f"\nConfluence saved to {out_path}")
    print(f"Report saved to {report_path}")
    print(f"\n{'='*60}")
    print(report)


if __name__ == "__main__":
    main()
