"""Budget-aware fetcher — never waste a single API call."""

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
CACHE_FILE = DATA_DIR / "fetch_cache.json"
BUDGET_FILE = DATA_DIR / "budget_log.jsonl"


def load_cache() -> dict:
    """Load fetch cache — tracks what we've already fetched."""
    if CACHE_FILE.exists():
        with open(CACHE_FILE) as f:
            return json.load(f)
    return {}


def save_cache(cache: dict):
    """Save fetch cache."""
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def log_call(handle: str, query: str, tweets_returned: int):
    """Log an API call for budget tracking."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "handle": handle,
        "query": query,
        "tweets_returned": tweets_returned,
        "cost": 0.001,
    }
    with open(BUDGET_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def get_total_spend() -> float:
    """Calculate total API spend."""
    if not BUDGET_FILE.exists():
        return 0.0
    with open(BUDGET_FILE) as f:
        return sum(json.loads(line).get("cost", 0) for line in f if line.strip())


def should_fetch(handle: str, since: str, until: str, force: bool = False) -> bool:
    """Check if we need to fetch this account for this date range."""
    if force:
        return True

    cache = load_cache()
    key = f"{handle}:{since}:{until}"

    if key in cache:
        last_fetched = cache[key].get("fetched_at", "")
        # Don't re-fetch if fetched in last 24 hours
        if last_fetched:
            try:
                last = datetime.fromisoformat(last_fetched)
                if (datetime.now(timezone.utc) - last).total_seconds() < 86400:
                    return False
            except:
                pass

    return True


def mark_fetched(handle: str, since: str, until: str, tweets: int):
    """Mark a fetch as completed."""
    cache = load_cache()
    key = f"{handle}:{since}:{until}"
    cache[key] = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "tweets": tweets,
    }
    save_cache(cache)
    log_call(handle, f"from:{handle} since:{since} until:{until}", tweets)


def budget_check() -> dict:
    """Check current budget status."""
    total_spend = get_total_spend()
    budget = 10.00  # $10 top-up
    remaining = budget - total_spend

    cache = load_cache()
    unique_fetches = len(cache)

    return {
        "total_spend": total_spend,
        "budget": budget,
        "remaining": remaining,
        "calls_available": int(remaining / 0.001),
        "tweets_available": int(remaining / 0.001) * 20,
        "unique_fetches": unique_fetches,
    }


def smart_fetch(handle: str, since: str, until: str, client, count: int = 10) -> list:
    """Fetch only if needed, with budget check."""
    budget = budget_check()

    if budget["remaining"] < 0.001:
        print(f"  BUDGET EXHAUSTED. Stop.")
        return []

    if not should_fetch(handle, since, until):
        print(f"  @{handle}: Already fetched recently, skipping.")
        return []

    # Make the call
    resp = client.get(
        "https://api.getxapi.com/twitter/tweet/advanced_search",
        headers={"Authorization": f"Bearer {client.api_key}"},
        params={
            "q": f"from:{handle}+-filter:replies+-filter:nativeretweets+since:{since}+until:{until}",
            "product": "Latest",
            "count": min(count, 10),  # Cap at 10 to save credits
        },
        timeout=10.0,
    )
    data = resp.json()
    tweets = data.get("tweets", [])

    mark_fetched(handle, since, until, len(tweets))
    return tweets
