"""GetXAPI client — canonical interface for all X API interactions.

Every API call in BEAR MUST go through this class.
No direct httpx calls to api.getxapi.com allowed anywhere else.

Costs (as of 2026-09-07):
- advanced_search: $0.001/page (~20 tweets)
- user_tweets: $0.001/page
- user_tweets_complete: $0.003/page
- tweet_detail: $0.001/tweet
- tweet_thread: $0.005/thread
- tweet_replies: $0.001/page
- user_info: $0.001/call
"""

import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx


# Cost table — $0.001 per page/tweet for reads
COSTS = {
    "advanced_search": 0.001,
    "user_tweets": 0.001,
    "user_tweets_complete": 0.003,
    "tweet_detail": 0.001,
    "tweet_thread": 0.005,
    "tweet_replies": 0.001,
    "user_info": 0.001,
    "user_search": 0.001,
}

BASE_URL = "https://api.getxapi.com"


def _get_api_key() -> str:
    """Get API key from vault or environment."""
    try:
        result = subprocess.run(
            ["agent-vault", "vault", "credential", "get", "GETXAPI_KEY", "--vault", "oracle"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return os.environ.get("GETXAPI_KEY", "")


class GetXAPI:
    """Canonical X API client with built-in budget enforcement."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or _get_api_key()
        if not self.api_key:
            raise ValueError("No API key found. Set GETXAPI_KEY or configure vault.")
        
        self.client = httpx.Client(
            base_url=BASE_URL,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=30.0,
        )
        
        # Budget tracking
        self._calls = 0
        self._cost = 0.0
        self._tweets = 0
        self._start_balance = None
        self._last_request = 0.0
        
        # Ledger
        self._ledger_path = Path(__file__).parent.parent.parent / "data" / "budgets" / "api_ledger.jsonl"
        self._ledger_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _rate_limit(self):
        """Enforce rate limiting (30 req/min for advanced search)."""
        elapsed = time.time() - self._last_request
        if elapsed < 2.1:  # ~28 req/min
            time.sleep(2.1 - elapsed)
        self._last_request = time.time()
    
    def _request(self, endpoint: str, params: dict) -> dict:
        """Make an API request with rate limiting and logging."""
        self._rate_limit()
        
        start = time.time()
        resp = self.client.get(endpoint, params=params)
        elapsed = time.time() - start
        
        data = resp.json()
        
        # Track costs
        cost = COSTS.get(endpoint.split("/")[-1], 0.001)
        self._calls += 1
        self._cost += cost
        
        # Log
        self._log_call(endpoint, params, cost, elapsed)
        
        return data
    
    def _log_call(self, endpoint: str, params: dict, cost: float, elapsed: float):
        """Log API call to ledger."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "endpoint": endpoint,
            "cost_usd": cost,
            "elapsed_sec": round(elapsed, 3),
            "cumulative_calls": self._calls,
            "cumulative_cost": round(self._cost, 4),
        }
        with open(self._ledger_path, "a") as f:
            f.write(json.dumps(entry) + "\n")
    
    # === PUBLIC API ===
    
    def search(self, handle: str, since: str, until: str,
               max_pages: int = 50) -> list[dict]:
        """Fetch all tweets for a handle in a date range with full pagination.
        
        Args:
            handle: X username (without @)
            since: Start date YYYY-MM-DD
            until: End date YYYY-MM-DD
            max_pages: Safety limit on pages
            
        Returns:
            List of tweet dicts
        """
        query = f"from:{handle} since:{since} until:{until}"
        all_tweets = []
        cursor = None
        page = 0
        
        while page < max_pages:
            page += 1
            params = {"q": query, "product": "Latest"}
            if cursor:
                params["cursor"] = cursor
            
            data = self._request("/twitter/tweet/advanced_search", params)
            
            tweets = data.get("tweets", [])
            has_more = data.get("has_more")
            cursor = data.get("next_cursor")
            
            if not tweets:
                break
            
            all_tweets.extend(tweets)
            self._tweets += len(tweets)
            
            if not has_more or not cursor:
                break
        
        return all_tweets
    
    def user_tweets(self, handle: str, max_pages: int = 200) -> list[dict]:
        """Fetch all tweets for a handle using /user/tweets endpoint.
        
        Good for full history. Slower but more complete than search.
        """
        all_tweets = []
        cursor = None
        page = 0
        
        while page < max_pages:
            page += 1
            params = {"userName": handle}
            if cursor:
                params["cursor"] = cursor
            
            data = self._request("/twitter/user/tweets", params)
            
            tweets = data.get("tweets", [])
            has_more = data.get("has_more")
            cursor = data.get("next_cursor")
            
            if not tweets:
                break
            
            all_tweets.extend(tweets)
            self._tweets += len(tweets)
            
            if not has_more or not cursor:
                break
        
        return all_tweets
    
    def user_info(self, handle: str) -> dict:
        """Get user profile info."""
        data = self._request("/twitter/user/info", {"userName": handle})
        return data.get("data", {})
    
    def tweet_detail(self, tweet_id: str) -> dict:
        """Get full tweet detail including media."""
        data = self._request("/twitter/tweet/detail", {"id": tweet_id})
        return data.get("data", {})
    
    def tweet_thread(self, tweet_id: str) -> list[dict]:
        """Get full thread for a tweet."""
        data = self._request("/twitter/tweet/thread", {"id": tweet_id})
        return data.get("data", {}).get("tweets", [])
    
    def balance(self) -> float:
        """Get current API balance."""
        resp = self.client.get("/account/me")
        data = resp.json()
        return data.get("balance_total", 0.0)
    
    def status(self):
        """Print budget status."""
        bal = self.balance()
        print(f"\n{'='*50}")
        print(f"GetXAPI STATUS")
        print(f"{'='*50}")
        print(f"Balance:     ${bal:.2f}")
        print(f"Session:     {self._calls} calls, {self._tweets} tweets")
        print(f"Session cost: ${self._cost:.4f}")
        print(f"{'='*50}")
    
    def close(self):
        """Close the HTTP client."""
        self.client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()
