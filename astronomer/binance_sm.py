"""Binance Smart Money integration — tier-based signal weighting."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def load_accounts_by_tier() -> dict:
    """Load accounts grouped by tier."""
    accounts_path = Path(__file__).parent / "accounts.json"
    with open(accounts_path) as f:
        data = json.load(f)

    tiers = data.get("tiers", {})
    accounts = data.get("accounts", [])

    by_tier = {}
    for acct in accounts:
        tier = acct.get("tier", "ct_social")
        if tier not in by_tier:
            by_tier[tier] = {
                "info": tiers.get(tier, {}),
                "accounts": [],
            }
        by_tier[tier]["accounts"].append(acct)

    return by_tier


def get_effective_weight(account: dict) -> float:
    """Calculate effective weight including tier multiplier."""
    tiers_path = Path(__file__).parent / "accounts.json"
    with open(tiers_path) as f:
        data = json.load(f)

    tier = account.get("tier", "ct_social")
    multiplier = data.get("tiers", {}).get(tier, {}).get("weight_multiplier", 1.0)
    base_weight = account.get("weight", 1.0)

    return base_weight * multiplier


def generate_tier_report() -> str:
    """Generate report of accounts by tier."""
    by_tier = load_accounts_by_tier()

    lines = [
        "# Binance Smart Money Tier Report",
        "",
        "## Signal Quality Tiers",
        "",
        "| Tier | Description | Accounts | Weight Multiplier |",
        "|------|-------------|----------|-------------------|",
    ]

    for tier_name, tier_data in by_tier.items():
        info = tier_data["info"]
        count = len(tier_data["accounts"])
        mult = info.get("weight_multiplier", 1.0)
        desc = info.get("description", "")
        lines.append(f"| {tier_name} | {desc} | {count} | {mult}x |")

    lines.extend(["", "## Accounts by Tier", ""])

    for tier_name, tier_data in by_tier.items():
        info = tier_data["info"]
        lines.append(f"### {tier_name} ({info.get('description', '')})")
        lines.append("")

        for acct in tier_data["accounts"]:
            effective = get_effective_weight(acct)
            binance_info = ""
            if acct.get("binance_rank"):
                binance_info = f" | Binance: {acct['binance_rank']}"
            if acct.get("binance_stats"):
                binance_info += f" ({acct['binance_stats']})"

            lines.append(f"- **@{acct['handle']}** — {acct.get('name', '?')} ({acct.get('followers', '?')} followers){binance_info}")
            lines.append(f"  - Style: {acct.get('style', '?')}")
            lines.append(f"  - Effective weight: {effective:.1f}")
            lines.append(f"  - Tags: {', '.join(acct.get('tags', []))}")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    print(generate_tier_report())
