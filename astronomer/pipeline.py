"""Pipeline automation — fetch, filter, store, monitor."""

import os
import json
import time
import httpx
from datetime import datetime, timezone
from pathlib import Path

API_KEY = os.environ.get("GETXAPI_KEY", "")
BASE_URL = "https://api.getxapi.com/twitter"


def get_headers():
    return {"Authorization": f"Bearer {API_KEY}"}


def get_balance() -> float:
    resp = httpx.get("https://api.getxapi.com/account/me", headers=get_headers(), timeout=5.0)
    return resp.json().get("balance_total", 0)


def fetch_search(handle: str, since: str, until: str, count: int = 20) -> dict:
    """Fetch tweets using Advanced Search with date chunks."""
    resp = httpx.get(
        f"{BASE_URL}/tweet/advanced_search",
        headers=get_headers(),
        params={
            "q": f"from:{handle} since:{since} until:{until}",
            "product": "Latest",
            "count": count,
        },
        timeout=15.0,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_complete(userId: str, count: int = 20, cursor: str = "") -> dict:
    """Fetch recent tweets + replies via user/tweets/complete."""
    params = {"userId": userId, "count": count}
    if cursor:
        params["cursor"] = cursor
    resp = httpx.get(f"{BASE_URL}/user/tweets/complete", headers=get_headers(), params=params, timeout=15.0)
    resp.raise_for_status()
    return resp.json()


def fetch_thread(tweet_id: str) -> dict:
    """Fetch full self-thread."""
    resp = httpx.get(f"{BASE_URL}/tweet/thread", headers=get_headers(), params={"id": tweet_id}, timeout=15.0)
    resp.raise_for_status()
    return resp.json()


def fetch_user_info(userName: str) -> dict:
    """Get user info with permanent userId."""
    resp = httpx.get(f"{BASE_URL}/user/info", headers=get_headers(), params={"userName": userName}, timeout=10.0)
    resp.raise_for_status()
    return resp.json()


def adaptive_backfill(handle: str, start_date: str, end_date: str, max_depth: int = 5) -> list:
    """Adaptive date-windowed backfill."""
    all_tweets = []
    cursor = None
    
    for _ in range(max_depth):
        data = fetch_search(handle, start_date, end_date)
        tweets = data.get("tweets", [])
        all_tweets.extend(tweets)
        
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
        time.sleep(0.3)
    
    return all_tweets


if __name__ == "__main__":
    print(f"Balance: ${get_balance():.2f}")
    print("Pipeline ready. Use functions directly.")
