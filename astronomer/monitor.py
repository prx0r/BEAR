"""Prospective monitoring — fetch latest posts, append to live ledger.

Usage:
    python monitor.py                    # fetch latest for all monitored accounts
    python monitor.py --handle theunipcs # fetch latest for one account
    python monitor.py --report           # generate daily report without fetching

Every new post is appended to data/live/events.jsonl (immutable).
Outcomes fill automatically as horizons expire.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent))

from extractor_v2 import classify_event
from meme_extractor import extract_meme_events

DATA_DIR = Path(__file__).parent / "data"
LIVE_DIR = DATA_DIR / "live"
RAW_DIR = DATA_DIR / "backtest" / "raw"

# All monitored accounts
MONITORED = {
    'major': ['Timeless_Crypto', 'Trader_XO', 'astronomer_zero', 'CryptoBheem', '0xaporia'],
    'meme': ['theunipcs', 'SevaFTW', 'kenjidgn', 'loganlim_x', '0xAvast', '0xnobi'],
    'derivative': ['exitpumpBTC', 'laevitas1', 'kingfisher_btc', 'hyblockcapital'],
    'onchain': ['lookonchain', 'ki_young_ju', 'EmberCN', 'OnchainLens'],
    'flow': ['FarsideUK'],
    'news': ['DeItaone', 'FirstSquawk', 'EleanorTerrett'],
    'macro': ['crossbordercap', 'josephwang'],
    'hl': ['HyperliquidR'],
    'security': ['zachxbt', 'PeckShieldAlert', 'CertiKAlert'],
    'fundamental': ['Tokenomist_ai'],
    'tao': ['SubnetStats', 'TAOTemplar'],
}


def get_api_key():
    """Get GetXAPI key from vault or env."""
    try:
        import subprocess
        result = subprocess.run(
            ['agent-vault', 'vault', 'credential', 'get', 'GETXAPI_KEY', '--vault', 'oracle'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except:
        pass
    return os.environ.get('GETXAPI_KEY', '')


def fetch_latest(handle: str, api_key: str, days: int = 3) -> list[dict]:
    """Fetch most recent posts for an account."""
    headers = {'Authorization': f'Bearer {api_key}'}
    
    # Search last N days
    from datetime import timedelta
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    
    query = f'from:{handle} since:{start.strftime("%Y-%m-%d")} until:{end.strftime("%Y-%m-%d")}'
    
    all_tweets = []
    cursor = None
    page = 0
    
    while page < 5:
        page += 1
        params = {'q': query, 'product': 'Latest'}
        if cursor:
            params['cursor'] = cursor
        
        try:
            resp = httpx.get('https://api.getxapi.com/twitter/tweet/advanced_search',
                params=params, headers=headers, timeout=15)
            data = resp.json()
        except Exception as e:
            print(f'  Error fetching {handle}: {e}')
            break
        
        tweets = data.get('tweets', [])
        has_more = data.get('has_more')
        cursor = data.get('next_cursor')
        
        if not tweets:
            break
        
        all_tweets.extend(tweets)
        
        if not has_more or not cursor:
            break
        time.sleep(0.5)
    
    return all_tweets


def classify_post(post: dict, handle: str, category: str) -> list[dict]:
    """Classify a post into events."""
    events = []
    
    if category == 'meme':
        meme_events = extract_meme_events([post])
        for e in meme_events:
            events.append({
                'timestamp': e.published_at,
                'source': handle,
                'category': category,
                'type': e.action,
                'asset': e.asset_refs[0].get('symbol', '') if e.asset_refs else '',
                'contract': e.asset_refs[0].get('contract_address', '') if e.asset_refs else '',
                'conviction': e.conviction,
                'text': e.text[:200],
                'evidence': e.evidence_quotes[:3],
                'status': 'OPEN',
            })
    else:
        evts = classify_event(
            text=post.get('text', ''),
            post_id=post.get('id', ''),
            handle=handle,
        )
        for e in evts:
            kind = e.semantic_kind if hasattr(e, 'semantic_kind') else 'VIEW'
            asset = e.asset if hasattr(e, 'asset') else None
            direction = e.direction if hasattr(e, 'direction') else None
            if hasattr(direction, 'value'):
                direction = direction.value
            
            events.append({
                'timestamp': post.get('createdAt', ''),
                'source': handle,
                'category': category,
                'type': kind,
                'asset': asset or '',
                'direction': direction or '',
                'text': post.get('text', '')[:200],
                'status': 'OPEN',
            })
    
    return events


def append_to_ledger(events: list[dict]):
    """Append events to live ledger (immutable)."""
    LIVE_DIR.mkdir(parents=True, exist_ok=True)
    ledger_path = LIVE_DIR / "events.jsonl"
    
    with open(ledger_path, "a") as f:
        for e in events:
            e['ingested_at'] = datetime.now(timezone.utc).isoformat()
            f.write(json.dumps(e) + "\n")


def load_seen_post_ids(handle: str) -> set:
    """Load post IDs we've already processed for an account."""
    path = LIVE_DIR / f"seen_{handle}.json"
    if path.exists():
        with open(path) as f:
            return set(json.load(f))
    return set()


def save_seen_post_ids(handle: str, ids: set):
    """Save seen post IDs."""
    LIVE_DIR.mkdir(parents=True, exist_ok=True)
    path = LIVE_DIR / f"seen_{handle}.json"
    with open(path, "w") as f:
        json.dump(sorted(ids), f)


def run_monitor(handles: list[str] = None, days: int = 3):
    """Run monitoring for specified or all accounts."""
    api_key = get_api_key()
    if not api_key:
        print("No API key found")
        return
    
    # Determine which accounts to monitor
    if handles:
        target_handles = handles
    else:
        target_handles = []
        for cat_handles in MONITORED.values():
            target_handles.extend(cat_handles)
    
    # Build category lookup
    handle_to_cat = {}
    for cat, cat_handles in MONITORED.items():
        for h in cat_handles:
            handle_to_cat[h] = cat
    
    total_new = 0
    total_events = 0
    
    for handle in target_handles:
        cat = handle_to_cat.get(handle, 'unknown')
        seen_ids = load_seen_post_ids(handle)
        
        print(f'@{handle} ({cat}): ', end='', flush=True)
        
        tweets = fetch_latest(handle, api_key, days)
        
        if not tweets:
            print('no new tweets')
            continue
        
        # Filter to new posts
        new_tweets = [t for t in tweets if t.get('id', '') not in seen_ids]
        
        if not new_tweets:
            print(f'{len(tweets)} tweets, all seen')
            continue
        
        # Classify and append
        new_events = []
        for t in new_tweets:
            events = classify_post(t, handle, cat)
            new_events.extend(events)
        
        append_to_ledger(new_events)
        
        # Update seen IDs
        new_ids = {t.get('id', '') for t in new_tweets}
        save_seen_post_ids(handle, seen_ids | new_ids)
        
        print(f'+{len(new_tweets)} new tweets, +{len(new_events)} events')
        total_new += len(new_tweets)
        total_events += len(new_events)
        
        time.sleep(0.3)
    
    print(f'\nTotal: +{total_new} new tweets, +{total_events} events')
    return total_new, total_events


def generate_daily_report():
    """Generate daily report from live ledger."""
    ledger_path = LIVE_DIR / "events.jsonl"
    if not ledger_path.exists():
        print("No live ledger found")
        return
    
    events = []
    with open(ledger_path) as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))
    
    # Group by source
    by_source = {}
    for e in events:
        src = e.get('source', '?')
        if src not in by_source:
            by_source[src] = []
        by_source[src].append(e)
    
    # Generate report
    report = []
    report.append(f"# BEAR Live Feed — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    report.append(f"\nTotal events: {len(events)}")
    report.append(f"Sources monitored: {len(by_source)}")
    
    # Major consensus
    major_events = [e for e in events if e.get('category') == 'major']
    if major_events:
        bullish = sum(1 for e in major_events if e.get('direction') == 'BULLISH')
        bearish = sum(1 for e in major_events if e.get('direction') == 'BEARISH')
        report.append(f"\n## Major Consensus")
        report.append(f"BTC: {bullish} bullish, {bearish} bearish")
    
    # New calls
    report.append(f"\n## Recent Events (last 24h)")
    recent = [e for e in events if e.get('ingested_at', '') >= datetime.now(timezone.utc).isoformat()[:10]]
    for e in recent[:20]:
        report.append(f"- {e.get('source', '?')}: {e.get('type', '?')} {e.get('asset', '')} {e.get('direction', '')} | {e.get('text', '')[:60]}")
    
    # Source summary
    report.append(f"\n## Source Summary")
    for src in sorted(by_source.keys()):
        src_events = by_source[src]
        report.append(f"- @{src}: {len(src_events)} events")
    
    report_text = "\n".join(report)
    
    # Save
    report_path = LIVE_DIR / "latest.md"
    with open(report_path, "w") as f:
        f.write(report_text)
    
    print(report_text)
    return report_text


def main():
    parser = argparse.ArgumentParser(description='BEAR prospective monitoring')
    parser.add_argument('--handle', type=str, help='Specific account to monitor')
    parser.add_argument('--days', type=int, default=3, help='Days to look back')
    parser.add_argument('--report', action='store_true', help='Generate daily report only')
    args = parser.parse_args()
    
    if args.report:
        generate_daily_report()
    else:
        handles = [args.handle] if args.handle else None
        run_monitor(handles, args.days)


if __name__ == "__main__":
    main()
