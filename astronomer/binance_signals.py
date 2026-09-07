"""Binance Smart Money signal engine — positions as ground truth."""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx

sys.path.insert(0, str(Path(__file__).parent))

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# Apify config
APIFY_TOKEN = os.environ.get("APIFY_TOKEN", "")
ACTOR_ID = "muhammetakkurtt/binance-smart-money-scraper"


def run_actor(input_data: dict) -> list[dict]:
    """Run Apify actor and return results."""
    if not APIFY_TOKEN:
        print("WARNING: No APIFY_TOKEN set. Using mock data.")
        return []

    # Start actor run
    resp = httpx.post(
        f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs",
        headers={"Authorization": f"Bearer {APIFY_TOKEN}"},
        json=input_data,
        timeout=30.0,
    )
    resp.raise_for_status()
    run_id = resp.json()["data"]["id"]

    # Poll for completion
    for _ in range(60):
        import time
        time.sleep(5)
        status_resp = httpx.get(
            f"https://api.apify.com/v2/actor-runs/{run_id}",
            headers={"Authorization": f"Bearer {APIFY_TOKEN}"},
            timeout=10.0,
        )
        status = status_resp.json()["data"]["status"]
        if status == "SUCCEEDED":
            break
        elif status in ("FAILED", "ABORTED", "TIMED-OUT"):
            raise RuntimeError(f"Actor run failed: {status}")

    # Get dataset items
    dataset_id = status_resp.json()["data"]["defaultDatasetId"]
    items_resp = httpx.get(
        f"https://api.apify.com/v2/datasets/{dataset_id}/items",
        headers={"Authorization": f"Bearer {APIFY_TOKEN}"},
        timeout=30.0,
    )
    return items_resp.json()


def scrape_leaderboard(time_range: str = "30D", ranking_type: str = "PNL", limit: int = 50) -> list[dict]:
    """Scrape Binance Smart Money leaderboard."""
    print(f"Scraping leaderboard: {time_range} {ranking_type} (limit {limit})...")

    results = run_actor({
        "timeRange": time_range,
        "rankingType": ranking_type,
        "onlyShowSharingPosition": True,
        "limit": limit,
    })

    print(f"  Got {len(results)} traders")
    return results


def scrape_positions(trader_ids: list[str]) -> list[dict]:
    """Scrape positions for specific traders."""
    print(f"Scraping positions for {len(trader_ids)} traders...")

    results = run_actor({
        "topTraderIds": trader_ids,
        "fetchPerformance": True,
    })

    print(f"  Got {len(results)} position records")
    return results


def save_snapshot(traders: list[dict], label: str = "latest") -> Path:
    """Save point-in-time snapshot."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    out_path = DATA_DIR / "binance_snapshots" / f"snapshot_{label}_{timestamp}.json"
    out_path.parent.mkdir(exist_ok=True)

    snapshot = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "label": label,
        "trader_count": len(traders),
        "traders": traders,
    }

    with open(out_path, "w") as f:
        json.dump(snapshot, f, indent=2)

    # Also save as latest
    latest_path = DATA_DIR / "binance_latest.json"
    with open(latest_path, "w") as f:
        json.dump(snapshot, f, indent=2)

    print(f"Snapshot saved to {out_path}")
    return out_path


def load_latest_snapshot() -> Optional[dict]:
    """Load latest snapshot."""
    path = DATA_DIR / "binance_latest.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return None


def diff_snapshots(old: dict, new: dict) -> list[dict]:
    """Detect position changes between snapshots."""
    changes = []

    old_positions = {}
    for t in old.get("traders", []):
        uid = t.get("topTraderId", t.get("encryptedUid", ""))
        for pos in t.get("positions", {}).get("UM", []):
            key = f"{uid}:{pos['symbol']}"
            old_positions[key] = {
                "trader": uid,
                "symbol": pos["symbol"],
                "side": pos["side"],
                "size": pos.get("amount", 0),
                "entry": pos.get("entryPrice", 0),
                "pnl": pos.get("pnl", 0),
            }

    new_positions = {}
    for t in new.get("traders", []):
        uid = t.get("topTraderId", t.get("encryptedUid", ""))
        for pos in t.get("positions", {}).get("UM", []):
            key = f"{uid}:{pos['symbol']}"
            new_positions[key] = {
                "trader": uid,
                "symbol": pos["symbol"],
                "side": pos["side"],
                "size": pos.get("amount", 0),
                "entry": pos.get("entryPrice", 0),
                "pnl": pos.get("pnl", 0),
            }

    # Find changes
    all_keys = set(list(old_positions.keys()) + list(new_positions.keys()))
    for key in all_keys:
        old_pos = old_positions.get(key)
        new_pos = new_positions.get(key)

        if not old_pos and new_pos:
            changes.append({
                "type": "OPEN",
                "trader": new_pos["trader"],
                "symbol": new_pos["symbol"],
                "side": new_pos["side"],
                "size": new_pos["size"],
                "entry": new_pos["entry"],
            })
        elif old_pos and not new_pos:
            changes.append({
                "type": "CLOSE",
                "trader": old_pos["trader"],
                "symbol": old_pos["symbol"],
                "side": old_pos["side"],
                "pnl": old_pos["pnl"],
            })
        elif old_pos and new_pos:
            size_diff = new_pos["size"] - old_pos["size"]
            if abs(size_diff) > 0.001:  # threshold
                change_type = "ADD" if size_diff > 0 else "REDUCE"
                changes.append({
                    "type": change_type,
                    "trader": new_pos["trader"],
                    "symbol": new_pos["symbol"],
                    "side": new_pos["side"],
                    "old_size": old_pos["size"],
                    "new_size": new_pos["size"],
                    "size_change": size_diff,
                })

    return changes


def main():
    """Run full Binance Smart Money pipeline."""
    print("=== Binance Smart Money Pipeline ===\n")

    # 1. Scrape leaderboard
    traders = scrape_leaderboard("30D", "PNL", 50)

    if not traders:
        print("No data returned. Check APIFY_TOKEN.")
        return

    # 2. Save snapshot
    save_snapshot(traders, "leaderboard_30d")

    # 3. Check for position changes
    old_snapshot = load_latest_snapshot()
    new_snapshot = {
        "traders": traders,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if old_snapshot:
        changes = diff_snapshots(old_snapshot, new_snapshot)
        if changes:
            print(f"\n=== POSITION CHANGES DETECTED: {len(changes)} ===")
            for c in changes[:10]:
                print(f"  {c['type']} {c['symbol']} {c['side']} — trader {c['trader'][:10]}...")
        else:
            print("\nNo position changes detected.")

    print("\nDone.")


if __name__ == "__main__":
    main()
