"""Backtest engine — match historical calls to price outcomes."""

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from price_data import load_prices, get_price_at, get_price_range

DATA_DIR = Path(__file__).parent / "data"
CALLS_FILE = DATA_DIR / "calls.jsonl"
OUTCOMES_FILE = DATA_DIR / "outcomes.jsonl"
REPUTATION_FILE = DATA_DIR / "reputation.json"

# Time horizons to evaluate
HORIZONS = {
    "1h": 3600 * 1000,
    "4h": 4 * 3600 * 1000,
    "24h": 24 * 3600 * 1000,
    "7d": 7 * 24 * 3600 * 1000,
}

SYMBOL_MAP = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "SOL": "SOLUSDT",
    "TAO": "TAOUSDT",
    "HYPE": "BTCUSDT",  # fallback
}


def load_calls() -> list:
    """Load all historical calls."""
    calls = []
    if CALLS_FILE.exists():
        with open(CALLS_FILE) as f:
            for line in f:
                if line.strip():
                    try:
                        calls.append(json.loads(line))
                    except:
                        pass
    return calls


def evaluate_call(call: dict, prices: dict) -> dict:
    """Evaluate a single call against price data."""
    timestamp_ms = call.get("timestamp_ms", 0)
    if not timestamp_ms:
        return None

    direction = call.get("direction", "")
    assets = call.get("assets", ["BTC"])

    results = {}
    for asset in assets:
        symbol = SYMBOL_MAP.get(asset)
        if not symbol or symbol not in prices:
            continue

        price_list = prices[symbol]
        entry_candle = get_price_at(price_list, timestamp_ms)
        if not entry_candle:
            continue

        entry_price = entry_candle["close"]
        direction_mult = 1 if direction == "LONG" else -1

        for horizon_name, horizon_ms in HORIZONS.items():
            target_time = timestamp_ms + horizon_ms
            future_prices = get_price_range(price_list, timestamp_ms, target_time)

            if not future_prices:
                continue

            # Calculate returns
            returns = []
            for p in future_prices:
                ret = (p["close"] - entry_price) / entry_price * direction_mult
                returns.append(ret)

            if not returns:
                continue

            final_return = returns[-1]
            max_favorable = max(returns) if returns else 0
            max_adverse = min(returns) if returns else 0

            # Check targets/stops
            targets = call.get("levels", [])
            target_hit = False
            stop_hit = False

            if targets:
                for t in targets:
                    if direction == "LONG":
                        if any(p["high"] >= t for p in future_prices):
                            target_hit = True
                    else:
                        if any(p["low"] <= t for p in future_prices):
                            target_hit = True

            results[horizon_name] = {
                "entry_price": entry_price,
                "final_return": final_return,
                "mfe": max_favorable,
                "mae": max_adverse,
                "direction_correct": final_return > 0,
                "target_hit": target_hit,
            }

    return {
        "call_id": call.get("id", ""),
        "author": call.get("author", ""),
        "timestamp": call.get("timestamp", ""),
        "direction": direction,
        "assets": assets,
        "conviction": call.get("conviction", "medium"),
        "outcomes": results,
    }


def compute_reputation(outcomes: list) -> dict:
    """Compute reputation scores per author × asset × direction × horizon."""
    # Group by (author, asset, direction, horizon)
    groups = defaultdict(lambda: {"wins": 0, "total": 0, "returns": []})

    for o in outcomes:
        author = o["author"]
        direction = o["direction"]
        for asset in o["assets"]:
            for horizon, data in o.get("outcomes", {}).items():
                key = (author, asset, direction, horizon)
                groups[key]["total"] += 1
                if data["direction_correct"]:
                    groups[key]["wins"] += 1
                groups[key]["returns"].append(data["final_return"])

    # Calculate scores with Bayesian shrinkage
    reputation = {}
    alpha = 2  # prior wins
    beta = 2   # prior losses

    for (author, asset, direction, horizon), data in groups.items():
        n = data["total"]
        wins = data["wins"]
        returns = data["returns"]

        # Bayesian win rate
        win_rate = (wins + alpha) / (n + alpha + beta)

        # Median return
        sorted_returns = sorted(returns)
        median_return = sorted_returns[len(sorted_returns) // 2] if sorted_returns else 0

        # Profit factor
        gross_profit = sum(r for r in returns if r > 0)
        gross_loss = abs(sum(r for r in returns if r < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        reputation[f"{author}:{asset}:{direction}:{horizon}"] = {
            "author": author,
            "asset": asset,
            "direction": direction,
            "horizon": horizon,
            "n": n,
            "wins": wins,
            "win_rate": win_rate,
            "median_return": median_return,
            "profit_factor": profit_factor,
            "sample_size": "sufficient" if n >= 10 else "limited" if n >= 3 else "insufficient",
        }

    return reputation


def generate_report(reputation: dict) -> str:
    """Generate reputation report."""
    lines = [
        "# Trader Reputation Report",
        "",
        "## Per Author × Asset × Direction × Horizon",
        "",
        "| Author | Asset | Direction | Horizon | N | Win Rate | Median Return | PF | Sample |",
        "|--------|-------|-----------|---------|---|----------|---------------|-----|--------|",
    ]

    # Sort by win rate * sqrt(n) for significance
    sorted_rep = sorted(
        reputation.values(),
        key=lambda x: x["win_rate"] * (x["n"] ** 0.5),
        reverse=True,
    )

    for r in sorted_rep[:50]:
        lines.append(
            f"| @{r['author']} | {r['asset']} | {r['direction']} | {r['horizon']} | "
            f"{r['n']} | {r['win_rate']:.0%} | {r['median_return']:+.2%} | "
            f"{r['profit_factor']:.1f} | {r['sample_size']} |"
        )

    # Summary by author
    lines.extend(["", "## Author Summary", ""])

    by_author = defaultdict(lambda: {"total": 0, "weighted_wins": 0})
    for r in reputation.values():
        by_author[r["author"]]["total"] += r["n"]
        by_author[r["author"]]["weighted_wins"] += r["wins"]

    for author, data in sorted(by_author.items(), key=lambda x: -x[1]["weighted_wins"] / max(x[1]["total"], 1)):
        win_rate = data["weighted_wins"] / data["total"] if data["total"] > 0 else 0
        lines.append(f"- **@{author}**: {data['total']} calls, {win_rate:.0%} win rate")

    return "\n".join(lines)


def main():
    """Run backtest."""
    print("=== Backtest Engine ===\n")

    # Load calls
    calls = load_calls()
    print(f"Loaded {len(calls)} calls")

    if not calls:
        print("No calls found. Run collect_calls.py first.")
        return

    # Load prices
    prices = {}
    for symbol in ["BTCUSDT", "ETHUSDT", "SOLUSDT"]:
        price_data = load_prices(symbol, "1h")
        if price_data:
            prices[symbol] = price_data
            print(f"Loaded {len(price_data)} candles for {symbol}")

    if not prices:
        print("No price data. Run price_data.py first.")
        return

    # Evaluate calls
    print(f"\nEvaluating {len(calls)} calls...")
    outcomes = []
    for c in calls:
        result = evaluate_call(c, prices)
        if result:
            outcomes.append(result)

    print(f"Evaluated {len(outcomes)} calls with outcomes")

    # Save outcomes
    with open(OUTCOMES_FILE, "w") as f:
        for o in outcomes:
            f.write(json.dumps(o) + "\n")

    # Compute reputation
    reputation = compute_reputation(outcomes)
    print(f"Computed reputation for {len(reputation)} author×asset×direction×horizon combinations")

    # Save reputation
    with open(REPUTATION_FILE, "w") as f:
        json.dump(reputation, f, indent=2)

    # Generate report
    report = generate_report(reputation)
    report_path = DATA_DIR / "reputation_report.md"
    with open(report_path, "w") as f:
        f.write(report)

    print(f"\nReport saved to {report_path}")
    print(f"\n{'='*60}")
    print(report[:2000])


if __name__ == "__main__":
    main()
