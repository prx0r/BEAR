"""Setup script — get APIfy token and test Binance Smart Money scraper."""

import os
import sys
import httpx


def test_apify_connection():
    """Test if Apify token works."""
    token = os.environ.get("APIFY_TOKEN", "")
    if not token:
        print("ERROR: APIFY_TOKEN not set.")
        print("\nTo get your token:")
        print("1. Go to https://console.apify.com/account/integrations")
        print("2. Copy your API token")
        print("3. Run: export APIFY_TOKEN='your_token_here'")
        print("4. Or add to vault: agent-vault vault credential set APIFY_TOKEN='your_token' --vault oracle")
        return False

    try:
        resp = httpx.get(
            "https://api.apify.com/v2/users/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        print(f"✅ Connected to Apify as: {data.get('username', '?')}")
        print(f"   Plan: {data.get('plan', '?')}")
        print(f"   Usage this month: ${data.get('usageTotalUsd', 0):.2f}")
        return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


def test_binance_scraper():
    """Test the Binance Smart Money scraper."""
    token = os.environ.get("APIFY_TOKEN", "")
    if not token:
        print("Skipping scraper test — no token.")
        return

    print("\nTesting Binance Smart Money scraper...")

    # Start a small run
    resp = httpx.post(
        "https://api.apify.com/v2/acts/muhammetakkurtt/binance-smart-money-scraper/runs",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "timeRange": "30D",
            "rankingType": "PNL",
            "onlyShowSharingPosition": True,
            "limit": 5,  # Small test
        },
        timeout=30.0,
    )
    resp.raise_for_status()
    run_data = resp.json()["data"]
    run_id = run_data["id"]
    print(f"  Run started: {run_id}")

    # Poll for completion
    import time
    for i in range(30):
        time.sleep(3)
        status_resp = httpx.get(
            f"https://api.apify.com/v2/actor-runs/{run_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )
        status = status_resp.json()["data"]["status"]
        if status == "SUCCEEDED":
            break
        elif status in ("FAILED", "ABORTED", "TIMED-OUT"):
            print(f"  ❌ Run failed: {status}")
            return
        print(f"  Waiting... ({status})")

    # Get results
    dataset_id = status_resp.json()["data"]["defaultDatasetId"]
    items_resp = httpx.get(
        f"https://api.apify.com/v2/datasets/{dataset_id}/items",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30.0,
    )
    items = items_resp.json()

    print(f"  ✅ Got {len(items)} traders")
    for t in items[:3]:
        print(f"    #{t.get('rank', '?')} {t.get('traderName', '?')[:20]} — PnL: ${t.get('pnl', 0):,.0f} | ROI: {t.get('roi', 0):.1%}")

    # Save test data
    import json
    from pathlib import Path

    out_path = Path(__file__).parent / "data" / "binance_test.json"
    with open(out_path, "w") as f:
        json.dump(items, f, indent=2)
    print(f"\n  Test data saved to {out_path}")


def main():
    """Run setup and tests."""
    print("=== Binance Smart Money Setup ===\n")

    print("1. Testing Apify connection...")
    if not test_apify_connection():
        return

    print("\n2. Testing Binance Smart Money scraper...")
    test_binance_scraper()

    print("\n3. Next steps:")
    print("   - Set APIFY_TOKEN in your environment")
    print("   - Run: python3 astronomer/binance_signals.py")
    print("   - Run: python3 astronomer/signal_engine.py")


if __name__ == "__main__":
    main()
