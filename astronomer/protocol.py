"""Dynamic extraction protocol — run for any influencer.

Usage:
    python3 -m astronomer.protocol extract --handle timeless_crypto
    python3 -m astronomer.protocol report --handle astronomer_zero
    python3 -m astronomer.protocol recon --handle new_account
"""

import json
import os
import sys
import time
import re
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx

# Config
API_KEY = os.environ.get("GETXAPI_KEY", "")
BASE_URL = "https://api.getxapi.com/twitter"
DATA_DIR = Path(__file__).parent / "data"
PROTOCOL_DIR = Path(__file__).parent / "protocols"


def get_headers():
    return {"Authorization": f"Bearer {API_KEY}"}


# ── Signal Extraction ─────────────────────────────────────────────────────────

LONG_KW = ['long', 'longing', 'longed', 'buy', 'buying', 'bullish', 'accumulate']
SHORT_KW = ['short', 'shorting', 'shorted', 'sell', 'selling', 'bearish']
LEVEL_KW = ['support', 'resist', 'resistance', 'level', 'target', 'tp', 'sl', 'stop', 'zone', 'area', 'vwap']
FLOW_KW = ['cvd', 'oi', 'funding', 'volume', 'order', 'bid', 'ask', 'flow', 'depth']
REGIME_KW = ['regime', 'trend', 'range', 'consolidation', 'breakout', 'reversal']


def classify_post(text: str) -> dict:
    """Classify a single post into signal categories."""
    lower = text.lower()
    
    has_long = any(re.search(r'\b' + kw + r'\b', lower) for kw in LONG_KW)
    has_short = any(re.search(r'\b' + kw + r'\b', lower) for kw in SHORT_KW)
    has_level = any(re.search(r'\b' + kw + r'\b', lower) for kw in LEVEL_KW)
    has_flow = any(re.search(r'\b' + kw + r'\b', lower) for kw in FLOW_KW)
    has_regime = any(re.search(r'\b' + kw + r'\b', lower) for kw in REGIME_KW)
    
    # Detect assets
    assets = []
    for asset in ['btc', 'eth', 'sol', 'hype', 'tao', 'doge', 'xrp']:
        if re.search(r'\$' + asset + r'\b|\b' + asset + r'\b', lower):
            assets.append(asset.upper())
    
    # Detect price levels
    levels = []
    for match in re.finditer(r'(\d{1,3}[,.]?\d{3,4})\s*(k|K)?', text):
        num_str = match.group(1).replace(',', '')
        try:
            num = float(num_str)
            if match.group(2):
                num *= 1000
            if 1000 < num < 500000:
                levels.append(num)
        except:
            pass
    
    # Determine signal type
    if has_long or has_short:
        direction = "LONG" if has_long else "SHORT"
        signal_type = "DIRECTIONAL"
    elif has_level:
        signal_type = "LEVELS"
    elif has_flow:
        signal_type = "FLOW"
    elif has_regime:
        signal_type = "REGIME"
    else:
        signal_type = "COMMENTARY"
    
    return {
        "signal_type": signal_type,
        "direction": direction if has_long or has_short else None,
        "assets": assets,
        "levels": levels[:5],
        "has_media": False,  # filled in by caller
        "is_reply": False,   # filled in by caller
    }


# ── Fetching ──────────────────────────────────────────────────────────────────

def fetch_tweets(handle: str, since: str, until: str, max_pages: int = 10) -> list:
    """Fetch tweets with pagination."""
    tweets = []
    cursor = None
    
    for _ in range(max_pages):
        params = {
            "q": f"from:{handle} since:{since} until:{until}",
            "product": "Latest",
            "count": 20,
        }
        if cursor:
            params["cursor"] = cursor
        
        resp = httpx.get(
            f"{BASE_URL}/tweet/advanced_search",
            headers=get_headers(),
            params=params,
            timeout=15.0,
        )
        data = resp.json()
        tweets.extend(data.get("tweets", []))
        
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
        time.sleep(0.3)
    
    return tweets


def dedup_tweets(tweets: list) -> list:
    """Remove duplicate tweets by ID."""
    seen = set()
    unique = []
    for t in tweets:
        if t["id"] not in seen:
            seen.add(t["id"])
            unique.append(t)
    return unique


# ── Analysis ──────────────────────────────────────────────────────────────────

def analyze_tweets(tweets: list) -> dict:
    """Analyze a set of tweets and return metrics."""
    total = len(tweets)
    if total == 0:
        return {}
    
    replies = sum(1 for t in tweets if t.get("isReply"))
    standalone = total - replies
    media = sum(1 for t in tweets if t.get("media"))
    
    # Classify standalone posts
    signal_counts = {"DIRECTIONAL": 0, "LEVELS": 0, "FLOW": 0, "REGIME": 0, "COMMENTARY": 0}
    direction_counts = {"LONG": 0, "SHORT": 0}
    asset_counts = {}
    
    for t in tweets:
        if t.get("isReply"):
            continue
        classification = classify_post(t.get("text", ""))
        signal_counts[classification["signal_type"]] += 1
        if classification["direction"]:
            direction_counts[classification["direction"]] += 1
        for asset in classification["assets"]:
            asset_counts[asset] = asset_counts.get(asset, 0) + 1
    
    signal_posts = signal_counts["DIRECTIONAL"] + signal_counts["LEVELS"] + signal_counts["FLOW"] + signal_counts["REGIME"]
    signal_density = signal_posts / max(standalone, 1)
    
    return {
        "total": total,
        "replies": replies,
        "standalone": standalone,
        "media": media,
        "reply_ratio": replies / total,
        "media_ratio": media / total,
        "signal_density": signal_density,
        "signal_counts": signal_counts,
        "direction_counts": direction_counts,
        "asset_counts": asset_counts,
    }


# ── Recon ─────────────────────────────────────────────────────────────────────

def run_recon(handle: str) -> dict:
    """Day 1: Quick recon of an account."""
    print(f"\n{'='*60}")
    print(f"RECON: @{handle}")
    print(f"{'='*60}")
    
    # Fetch 3 pages
    tweets = fetch_tweets(handle, 
        since=(datetime.now() - __import__('datetime').timedelta(days=7)).strftime("%Y-%m-%d"),
        until=datetime.now().strftime("%Y-%m-%d"),
        max_pages=3)
    tweets = dedup_tweets(tweets)
    
    # Analyze
    analysis = analyze_tweets(tweets)
    
    # Decision
    verdict = "PROCEED" if (
        analysis["signal_density"] > 0.15 and
        analysis["standalone"] > 3 and
        analysis["reply_ratio"] < 0.90
    ) else "SKIP"
    
    report = {
        "handle": handle,
        "phase": "recon",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tweets_sampled": len(tweets),
        "analysis": analysis,
        "verdict": verdict,
        "next_step": "validation" if verdict == "PROCEED" else None,
    }
    
    # Print summary
    print(f"\n  Tweets: {len(tweets)}")
    print(f"  Standalone: {analysis['standalone']} ({analysis['standalone']/max(len(tweets),1)*100:.0f}%)")
    print(f"  Replies: {analysis['replies']} ({analysis['reply_ratio']:.0%})")
    print(f"  Media: {analysis['media']} ({analysis['media_ratio']:.0%})")
    print(f"  Signal density: {analysis['signal_density']:.0%}")
    print(f"  Verdict: {verdict}")
    
    return report


# ── Validation ────────────────────────────────────────────────────────────────

def run_validation(handle: str) -> dict:
    """Week 1: Validate signal quality."""
    print(f"\n{'='*60}")
    print(f"VALIDATION: @{handle}")
    print(f"{'='*60}")
    
    # Fetch 1 week
    since = (datetime.now() - __import__('datetime').timedelta(days=7)).strftime("%Y-%m-%d")
    until = datetime.now().strftime("%Y-%m-%d")
    tweets = fetch_tweets(handle, since, until, max_pages=5)
    tweets = dedup_tweets(tweets)
    
    # Extract signals
    signals = []
    for t in tweets:
        if t.get("isReply"):
            continue
        classification = classify_post(t.get("text", ""))
        if classification["signal_type"] in ["DIRECTIONAL", "LEVELS"]:
            try:
                ts = datetime.strptime(t["createdAt"], "%a %b %d %H:%M:%S %z %Y")
                ts_ms = int(ts.timestamp() * 1000)
            except:
                ts_ms = 0
            
            signals.append({
                "tweet_id": t["id"],
                "author": handle,
                "timestamp_ms": ts_ms,
                "direction": classification["direction"],
                "assets": classification["assets"],
                "levels": classification["levels"],
                "likes": t.get("likeCount", 0),
            })
    
    # Analysis
    analysis = analyze_tweets(tweets)
    
    verdict = "CONFIRM" if (
        len(signals) >= 5 and
        analysis["signal_density"] > 0.10
    ) else "SKIP"
    
    report = {
        "handle": handle,
        "phase": "validation",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tweets": len(tweets),
        "signals": len(signals),
        "analysis": analysis,
        "verdict": verdict,
        "next_step": "confirmation" if verdict == "CONFIRM" else None,
    }
    
    print(f"\n  Tweets: {len(tweets)}")
    print(f"  Signals: {len(signals)}")
    print(f"  Signal density: {analysis['signal_density']:.0%}")
    print(f"  Verdict: {verdict}")
    
    return report


# ── Confirmation ──────────────────────────────────────────────────────────────

def run_confirmation(handle: str) -> dict:
    """Month 1: Confirm consistency."""
    print(f"\n{'='*60}")
    print(f"CONFIRMATION: @{handle}")
    print(f"{'='*60}")
    
    # Fetch 1 month
    since = (datetime.now() - __import__('datetime').timedelta(days=30)).strftime("%Y-%m-%d")
    until = datetime.now().strftime("%Y-%m-%d")
    tweets = fetch_tweets(handle, since, until, max_pages=20)
    tweets = dedup_tweets(tweets)
    
    # Full analysis
    analysis = analyze_tweets(tweets)
    
    # Extract signals
    signals = []
    for t in tweets:
        if t.get("isReply"):
            continue
        classification = classify_post(t.get("text", ""))
        if classification["signal_type"] in ["DIRECTIONAL", "LEVELS"]:
            try:
                ts = datetime.strptime(t["createdAt"], "%a %b %d %H:%M:%S %z %Y")
                ts_ms = int(ts.timestamp() * 1000)
            except:
                ts_ms = 0
            
            signals.append({
                "tweet_id": t["id"],
                "author": handle,
                "timestamp_ms": ts_ms,
                "direction": classification["direction"],
                "assets": classification["assets"],
                "levels": classification["levels"],
            })
    
    verdict = "FULL_EXTRACTION" if (
        len(signals) > 15 and
        analysis["signal_density"] > 0.10
    ) else "SKIP"
    
    report = {
        "handle": handle,
        "phase": "confirmation",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tweets": len(tweets),
        "signals": len(signals),
        "analysis": analysis,
        "verdict": verdict,
        "next_step": "extraction" if verdict == "FULL_EXTRACTION" else None,
    }
    
    print(f"\n  Tweets: {len(tweets)}")
    print(f"  Signals: {len(signals)}")
    print(f"  Signal density: {analysis['signal_density']:.0%}")
    print(f"  Verdict: {verdict}")
    
    return report


# ── Full Extraction ───────────────────────────────────────────────────────────

def run_extraction(handle: str, start_year: int = 2024) -> dict:
    """Full extraction: all available history."""
    print(f"\n{'='*60}")
    print(f"EXTRACTION: @{handle}")
    print(f"{'='*60}")
    
    all_tweets = []
    total_cost = 0
    
    # Fetch month by month
    for year in range(start_year, datetime.now().year + 1):
        for month in range(1, 13):
            since = f"{year}-{month:02d}-01"
            if month == 12:
                until = f"{year+1}-01-01"
            else:
                until = f"{year}-{month+1:02d}-01"
            
            # Skip future months
            if since > datetime.now().strftime("%Y-%m-%d"):
                break
            
            tweets = fetch_tweets(handle, since, until, max_pages=10)
            all_tweets.extend(tweets)
            total_cost += len(tweets) / 20 * 0.001  # estimate
            
            print(f"  {since[:7]}: {len(tweets)} tweets")
            time.sleep(0.2)
    
    # Dedup
    unique = dedup_tweets(all_tweets)
    
    # Save
    out_path = DATA_DIR / "raw" / f"{handle}_full.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump({
            "handle": handle,
            "tweets": unique,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "total_cost": total_cost,
        }, f, indent=2)
    
    # Analysis
    analysis = analyze_tweets(unique)
    
    report = {
        "handle": handle,
        "phase": "extraction",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_tweets": len(unique),
        "analysis": analysis,
        "cost": total_cost,
        "file": str(out_path),
    }
    
    print(f"\n  Total: {len(unique)} tweets")
    print(f"  Cost: ${total_cost:.3f}")
    print(f"  Saved to: {out_path}")
    
    return report


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Dynamic extraction protocol")
    parser.add_argument("action", choices=["recon", "validation", "confirmation", "extraction", "full"])
    parser.add_argument("--handle", required=True, help="Twitter handle")
    parser.add_argument("--start-year", type=int, default=2024, help="Start year for full extraction")
    
    args = parser.parse_args()
    
    if args.action == "recon":
        report = run_recon(args.handle)
    elif args.action == "validation":
        report = run_validation(args.handle)
    elif args.action == "confirmation":
        report = run_confirmation(args.handle)
    elif args.action == "extraction":
        report = run_extraction(args.handle, args.start_year)
    elif args.action == "full":
        # Run all phases
        recon = run_recon(args.handle)
        if recon["verdict"] == "SKIP":
            print("\nRecon says SKIP. Stopping.")
            return
        
        validation = run_validation(args.handle)
        if validation["verdict"] == "SKIP":
            print("\nValidation says SKIP. Stopping.")
            return
        
        confirmation = run_confirmation(args.handle)
        if confirmation["verdict"] == "SKIP":
            print("\nConfirmation says SKIP. Stopping.")
            return
        
        extraction = run_extraction(args.handle, args.start_year)
        print("\nFull pipeline complete.")
    
    # Save report
    report_path = DATA_DIR / "reports" / f"{args.handle}_{args.action}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nReport saved to: {report_path}")


if __name__ == "__main__":
    main()
