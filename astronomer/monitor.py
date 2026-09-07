"""Multi-account signal monitor — runs full pipeline."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fetcher import fetch_all_accounts, save_snapshot
from extractor import extract_signals_from_tweets
from confluence import compute_confluence, generate_confluence_report

DATA_DIR = Path(__file__).parent / "data"


def run_pipeline():
    """Run full fetch → extract → confluence pipeline."""
    print("=== CT Signal Monitor ===\n")

    # 1. Fetch all accounts
    print("--- Fetching tweets ---")
    tweets = fetch_all_accounts()
    save_snapshot(tweets)

    # 2. Extract signals
    print("\n--- Extracting signals ---")
    signals = extract_signals_from_tweets(tweets)
    print(f"Extracted {len(signals)} signals")

    # Save signals
    signals_path = DATA_DIR / "signals.jsonl"
    with open(signals_path, "a") as f:
        for s in signals:
            f.write(json.dumps(s.to_dict()) + "\n")

    # 3. Compute confluence
    print("\n--- Computing confluence ---")
    scores = compute_confluence(signals)

    # Save confluence
    confluence_path = DATA_DIR / "confluence.json"
    with open(confluence_path, "w") as f:
        json.dump([s.to_dict() for s in scores], f, indent=2)

    # 4. Generate reports
    report = generate_confluence_report(scores)
    report_path = DATA_DIR / "confluence_report.md"
    with open(report_path, "w") as f:
        f.write(report)

    # 5. Print summary
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Accounts fetched: {len(tweets)}")
    print(f"Total tweets: {sum(d['count'] for d in tweets.values())}")
    print(f"Signals extracted: {len(signals)}")
    print(f"Confluence scores: {len(scores)}")

    strong = [s for s in scores if s.strength == "strong"]
    moderate = [s for s in scores if s.strength == "moderate"]
    if strong:
        print(f"\n🟢 STRONG CONFLUENCE:")
        for s in strong:
            print(f"  {s.direction.value} {s.asset} ({s.timeframe}) — {len(s.accounts_aligned)} accounts")
    if moderate:
        print(f"\n🟡 MODERATE CONFLUENCE:")
        for s in moderate:
            print(f"  {s.direction.value} {s.asset} ({s.timeframe}) — {len(s.accounts_aligned)} accounts")

    print(f"\n{report}")

    return {
        "tweets": tweets,
        "signals": [s.to_dict() for s in signals],
        "confluence": [s.to_dict() for s in scores],
    }


if __name__ == "__main__":
    run_pipeline()
