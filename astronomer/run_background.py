#!/usr/bin/env python3
"""Background backtest runner — pipes all output to log files.

Usage:
    nohup python3 run_background.py > /root/BEAR/astronomer/logs/run_$(date +%Y%m%d_%H%M).log 2>&1 &

Or for a specific account:
    nohup python3 run_background.py --handle laevitas1 > /root/BEAR/astronomer/logs/laevitas1_$(date +%Y%m%d_%H%M).log 2>&1 &
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from extractor_v2 import classify_event
from backtest import load_all_prices, run_backtest, save_outcomes
from regime import load_regime_timeline
from metrics import compute_metrics, format_metrics_table
from baselines import evaluate_baselines, print_baselines
from schemas import MarketEvent, SemanticKind, CallState, SignalDirection


def parse_twitter_date(s):
    """Parse Twitter date format."""
    if not s:
        return ''
    try:
        dt = datetime.strptime(s, '%a %b %d %H:%M:%S %z %Y')
        return dt.isoformat()
    except:
        return ''


def fetch_account(handle, api_key):
    """Fetch August data for one account."""
    import httpx

    headers = {'Authorization': f'Bearer {api_key}'}
    chunks = [
        ('2026-08-01', '2026-08-15'),
        ('2026-08-15', '2026-09-01'),
    ]

    all_tweets = []
    for start, end in chunks:
        query = f'from:{handle} since:{start} until:{end}'
        resp = httpx.get('https://api.getxapi.com/twitter/tweet/advanced_search',
            params={'q': query, 'product': 'Latest'},
            headers=headers, timeout=15)
        data = resp.json()

        tweets = data.get('tweets', [])
        all_tweets.extend(tweets)

        if data.get('has_more') and data.get('next_cursor'):
            time.sleep(0.3)
            resp2 = httpx.get('https://api.getxapi.com/twitter/tweet/advanced_search',
                params={'q': query, 'product': 'Latest', 'cursor': data['next_cursor']},
                headers=headers, timeout=15)
            data2 = resp2.json()
            all_tweets.extend(data2.get('tweets', []))

        time.sleep(0.3)

    return all_tweets


def extract_events(tweets, handle):
    """Extract events from tweets."""
    events = []
    for t in tweets:
        text = t.get('text', '')
        tweet_id = t.get('id', '')
        created = t.get('createdAt', '')
        published_at = parse_twitter_date(created)

        evts = classify_event(text=text, post_id=tweet_id, handle=handle)
        for e in evts:
            d = e.direction
            if hasattr(d, 'value'):
                d = d.value
            events.append({
                'event_id': e.event_id,
                'post_id': e.post_id,
                'author_handle': handle,
                'author_id': '',
                'published_at': published_at,
                'semantic_kind': e.semantic_kind,
                'call_state': e.call_state,
                'asset': e.asset,
                'direction': d,
                'entry_type': e.entry_type,
                'entry_price': e.entry_price,
            })
    return events


def run_full_backtest():
    """Run backtest on all extracted events."""
    prices = load_all_prices()
    regime = load_regime_timeline()

    with open('data/backtest/extracted_august_v2.json') as f:
        raw_events = json.load(f)

    events = []
    for raw in raw_events:
        if raw['semantic_kind'] != 'CALL':
            continue
        if not raw['asset']:
            continue
        if not raw['published_at']:
            continue

        event = MarketEvent(
            event_id=raw['event_id'],
            post_id=raw['post_id'],
            author_id=raw.get('author_id', ''),
            author_handle=raw['author_handle'],
            published_at=raw['published_at'],
            semantic_kind=SemanticKind(raw['semantic_kind']),
            call_state=CallState(raw['call_state']),
            asset=raw['asset'],
            entry_type=raw.get('entry_type'),
            entry_price=raw.get('entry_price'),
        )
        d = raw.get('direction')
        if d:
            try:
                event.direction = SignalDirection(d)
            except:
                pass
        events.append(event)

    print(f"\nBacktesting {len(events)} CALL events with asset...")
    outcomes = run_backtest(events, prices, regime)
    print(f"Generated {len(outcomes)} outcomes")
    save_outcomes(outcomes)

    # Per-author breakdown
    event_to_author = {e['event_id']: e['author_handle'] for e in raw_events}
    by_author = {}
    for o in outcomes:
        author = event_to_author.get(o['event_id'], 'unknown')
        if author not in by_author:
            by_author[author] = {'4h': [], '24h': []}
        if o.return_4h is not None:
            by_author[author]['4h'].append(o.return_4h)
        if o.return_24h is not None:
            by_author[author]['24h'].append(o.return_24h)

    print(f"\n{'Author':<20} {'N':>3} {'Win4h':>6} {'Mean4h':>8} {'N':>3} {'Win24h':>6} {'Mean24h':>8}")
    print('-' * 65)
    for author in sorted(by_author.keys()):
        data = by_author[author]
        r4 = data['4h']
        r24 = data['24h']
        m4 = compute_metrics(r4) if r4 else None
        m24 = compute_metrics(r24) if r24 else None
        n4 = f'{m4.n}' if m4 else '-'
        w4 = f'{m4.hit_rate:.0%}' if m4 else '-'
        mean4 = f'{m4.mean_return*100:.2f}%' if m4 else '-'
        n24 = f'{m24.n}' if m24 else '-'
        w24 = f'{m24.hit_rate:.0%}' if m24 else '-'
        mean24 = f'{m24.mean_return*100:.2f}%' if m24 else '-'
        print(f'@{author:<19} {n4:>3} {w4:>6} {mean4:>8} {n24:>3} {w24:>6} {mean24:>8}')

    # Baselines
    outcome_dicts = []
    for o in outcomes:
        outcome_dicts.append({
            'event_id': o.event_id, 'asset': o.asset,
            'entry_time': o.entry_time, 'return_4h': o.return_4h,
            'return_24h': o.return_24h, 'btc_regime': o.btc_regime,
        })
    baselines = evaluate_baselines(outcome_dicts, horizon_hours=4)
    if baselines:
        print_baselines(baselines)

    return outcomes


def main():
    parser = argparse.ArgumentParser(description='BEAR background backtest runner')
    parser.add_argument('--handle', type=str, help='Specific account to fetch')
    parser.add_argument('--skip-fetch', action='store_true', help='Skip fetching, just run backtest')
    parser.add_argument('--api-key', type=str, help='GetXAPI key (or read from env)')
    args = parser.parse_args()

    print(f"{'='*60}")
    print(f"BEAR Background Run — {datetime.now(timezone.utc).isoformat()}")
    print(f"{'='*60}")

    api_key = args.api_key
    if not api_key:
        import os
        api_key = os.environ.get('GETXAPI_KEY', '')

    if not args.skip_fetch and args.handle:
        print(f"\nFetching @{args.handle}...")
        tweets = fetch_account(args.handle, api_key)
        print(f"Fetched {len(tweets)} tweets")

        if tweets:
            # Save raw
            raw_path = f'data/backtest/raw/{args.handle}_aug2026.json'
            with open(raw_path, 'w') as f:
                json.dump({'handle': args.handle, 'tweets': tweets, 'fetched_at': datetime.now(timezone.utc).isoformat()}, f, indent=2)
            print(f"Saved raw to {raw_path}")

            # Extract
            events = extract_events(tweets, args.handle)
            print(f"Extracted {len(events)} events")

            # Append to extracted
            extracted_path = 'data/backtest/extracted_august_v2.json'
            with open(extracted_path) as f:
                existing = json.load(f)
            existing = [e for e in existing if e.get('author_handle') != args.handle]
            existing.extend(events)
            with open(extracted_path, 'w') as f:
                json.dump(existing, f, indent=2)
            print(f"Total events now: {len(existing)}")

    print(f"\nRunning backtest...")
    run_full_backtest()

    print(f"\n{'='*60}")
    print(f"DONE — {datetime.now(timezone.utc).isoformat()}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
