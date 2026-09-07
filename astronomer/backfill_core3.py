"""BEAR Core 3 backfill — fetch complete 2-year history for Astro, Timeless, XO.

Usage:
    python backfill_core3.py --handles Timeless_Crypto --since 2024-09-01 --until 2026-09-01
    python backfill_core3.py --handles astronomer_zero Timeless_Crypto Trader_XO --since 2024-09-01 --until 2026-09-01
    python backfill_core3.py --smoke --handle Timeless_Crypto  # 7-day smoke test
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import httpx

DATA_DIR = Path(__file__).parent / "data" / "core3"
LEDGER_PATH = DATA_DIR / "fetch_ledger.jsonl"

# Author IDs (canonical identity)
AUTHOR_IDS = {
    "astronomer_zero": "1691180785098072064",
    "Timeless_Crypto": "952109977157668864",
    "Trader_XO": "1388015866562760705",
}


def get_api_key() -> str:
    """Get GetXAPI key from vault."""
    try:
        result = subprocess.run(
            ['agent-vault', 'vault', 'credential', 'get', 'GETXAPI_KEY', '--vault', 'oracle'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except:
        pass
    return os.environ.get('GETXAPI_KEY', '')


def generate_partitions(since: str, until: str) -> list[tuple[str, str]]:
    """Generate 7-day contiguous windows."""
    start = datetime.strptime(since, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end = datetime.strptime(until, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    
    partitions = []
    current = start
    while current < end:
        partition_end = min(current + timedelta(days=7), end)
        partitions.append((
            current.strftime("%Y-%m-%d"),
            partition_end.strftime("%Y-%m-%d"),
        ))
        current = partition_end
    
    return partitions


def fetch_partition(handle: str, since: str, until: str, api_key: str) -> dict:
    """Fetch all tweets for one partition with full pagination.
    
    Returns manifest dict with tweets stored to disk.
    """
    headers = {'Authorization': f'Bearer {api_key}'}
    
    # Prepare storage
    month_str = since[:7]  # YYYY-MM
    partition_dir = DATA_DIR / handle / "raw" / month_str
    partition_dir.mkdir(parents=True, exist_ok=True)
    
    partition_file = partition_dir / f"{since}_{until}.json"
    if partition_file.exists():
        # Already fetched
        with open(partition_file) as f:
            existing = json.load(f)
        return {
            "handle": handle,
            "since": since,
            "until": until,
            "posts": len(existing.get("tweets", [])),
            "complete": True,
            "status": "already_fetched",
        }
    
    # Fetch with full pagination
    query = f"from:{handle} since:{since} until:{until}"
    all_tweets = []
    cursor = None
    page = 0
    api_calls = 0
    
    while True:
        page += 1
        params = {"q": query, "product": "Latest"}
        if cursor:
            params["cursor"] = cursor
        
        try:
            resp = httpx.get(
                "https://api.getxapi.com/twitter/tweet/advanced_search",
                params=params, headers=headers, timeout=30,
            )
            data = resp.json()
            api_calls += 1
        except Exception as e:
            print(f"  Error on page {page}: {e}")
            time.sleep(2)
            continue
        
        tweets = data.get("tweets", [])
        has_more = data.get("has_more")
        cursor = data.get("next_cursor")
        
        if not tweets:
            break
        
        all_tweets.extend(tweets)
        
        if not has_more or not cursor:
            break
        
        time.sleep(0.5)
    
    # Determine completeness
    complete = not has_more if 'has_more' in dir() else True
    
    # Build manifest
    first_at = all_tweets[0].get("createdAt", "") if all_tweets else ""
    last_at = all_tweets[-1].get("createdAt", "") if all_tweets else ""
    
    manifest = {
        "handle": handle,
        "author_id": AUTHOR_IDS.get(handle, ""),
        "since": since,
        "until": until,
        "pages": page,
        "posts": len(all_tweets),
        "first_post_at": first_at,
        "last_post_at": last_at,
        "has_more_final": has_more if 'has_more' in dir() else False,
        "complete": complete,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "api_calls": api_calls,
        "cost_usd": api_calls * 0.001,
    }
    
    # Store tweets
    with open(partition_file, "w") as f:
        json.dump({"tweets": all_tweets, "manifest": manifest}, f, indent=2)
    
    # Log to ledger
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LEDGER_PATH, "a") as f:
        f.write(json.dumps(manifest) + "\n")
    
    return manifest


def run_smoke_test(handle: str, api_key: str) -> bool:
    """Run 7-day smoke test."""
    print(f"=== SMOKE TEST: {handle} 2026-08-01 to 2026-08-08 ===")
    
    result = fetch_partition(handle, "2026-08-01", "2026-08-08", api_key)
    print(f"  Posts: {result['posts']}, Pages: {result['pages']}, Complete: {result['complete']}")
    
    if result["posts"] == 0:
        print("  FAIL: No posts fetched")
        return False
    
    # Validate author_id
    expected_id = AUTHOR_IDS.get(handle, "")
    if result.get("author_id") != expected_id:
        print(f"  FAIL: Author ID mismatch: {result.get('author_id')} != {expected_id}")
        return False
    
    # Check tweet IDs unique
    partition_file = DATA_DIR / handle / "raw" / "2026-08" / "2026-08-01_2026-08-08.json"
    if partition_file.exists():
        with open(partition_file) as f:
            data = json.load(f)
        tweets = data.get("tweets", [])
        ids = [t.get("id") for t in tweets]
        if len(ids) != len(set(ids)):
            print(f"  FAIL: Duplicate tweet IDs: {len(ids)} total, {len(set(ids))} unique")
            return False
        print(f"  Tweet IDs unique: {len(ids)}")
    
    # Check replies retained
    replies = [t for t in tweets if t.get("isReply")]
    print(f"  Replies retained: {len(replies)}")
    
    # Check photos
    photos = [t for t in tweets if t.get("media")]
    print(f"  Posts with media: {len(photos)}")
    
    print("  PASS")
    return True


def run_full_backfill(handles: list[str], since: str, until: str, api_key: str):
    """Run full backfill for all handles."""
    partitions = generate_partitions(since, until)
    print(f"Partitions: {len(partitions)} per handle")
    print(f"Total API calls needed: ~{len(partitions) * 5} per handle")
    print(f"Estimated cost: ~${len(partitions) * 5 * 0.001:.2f} per handle")
    print()
    
    for handle in handles:
        print(f"=== Backfilling {handle} ===")
        completed = 0
        total_posts = 0
        
        for i, (start, end) in enumerate(partitions):
            result = fetch_partition(handle, start, end, api_key)
            total_posts += result.get("posts", 0)
            completed += 1
            
            if result.get("status") != "already_fetched":
                print(f"  {start}: {result['posts']} posts, {result['pages']} pages")
            
            time.sleep(0.3)
        
        print(f"  DONE: {completed}/{len(partitions)} partitions, {total_posts} total posts")
        print()


def generate_completeness_report(handles: list[str]):
    """Generate completeness report."""
    report = ["# Core 3 Corpus Report\n"]
    report.append(f"Generated: {datetime.now(timezone.utc).isoformat()}\n")
    
    total_cost = 0.0
    
    for handle in handles:
        handle_dir = DATA_DIR / handle / "raw"
        if not handle_dir.exists():
            report.append(f"## {handle}\nNo data.\n")
            continue
        
        months = sorted([d.name for d in handle_dir.iterdir() if d.is_dir()])
        total_posts = 0
        total_pages = 0
        partitions = []
        
        for month in months:
            month_dir = handle_dir / month
            for pf in sorted(month_dir.glob("*.json")):
                with open(pf) as f:
                    data = json.load(f)
                manifest = data.get("manifest", {})
                posts = manifest.get("posts", 0)
                pages = manifest.get("pages", 0)
                complete = manifest.get("complete", False)
                cost = manifest.get("cost_usd", 0)
                
                total_posts += posts
                total_pages += pages
                total_cost += cost
                partitions.append({
                    "file": pf.name,
                    "posts": posts,
                    "complete": complete,
                })
        
        report.append(f"## {handle}")
        report.append(f"- Months: {len(months)}/{24}")
        report.append(f"- Total posts: {total_posts}")
        report.append(f"- Total API pages: {total_pages}")
        report.append(f"- Cost: ${total_cost:.3f}")
        
        incomplete = [p for p in partitions if not p["complete"]]
        if incomplete:
            report.append(f"- INCOMPLETE partitions: {len(incomplete)}")
            for p in incomplete[:5]:
                report.append(f"  - {p['file']}: {p['posts']} posts")
        else:
            report.append(f"- All {len(partitions)} partitions complete")
        report.append("")
    
    report_text = "\n".join(report)
    
    report_path = DATA_DIR.parent.parent / "reports" / "core3" / "CORPUS.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w") as f:
        f.write(report_text)
    
    print(report_text)
    return report_text


def main():
    parser = argparse.ArgumentParser(description="BEAR Core 3 backfill")
    parser.add_argument("--handles", nargs="+", default=["astronomer_zero", "Timeless_Crypto", "Trader_XO"])
    parser.add_argument("--since", default="2024-09-01")
    parser.add_argument("--until", default="2026-09-01")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--handle", type=str, help="Single handle for smoke test")
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args()
    
    api_key = get_api_key()
    if not api_key:
        print("No API key found")
        return
    
    if args.report:
        generate_completeness_report(args.handles)
    elif args.smoke:
        handle = args.handle or args.handles[0]
        run_smoke_test(handle, api_key)
    else:
        run_full_backfill(args.handles, args.since, args.until, api_key)
        generate_completeness_report(args.handles)


if __name__ == "__main__":
    main()
