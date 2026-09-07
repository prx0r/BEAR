"""GetXAPI client — canonical interface for ALL X API interactions.

EVERY API call in BEAR MUST go through this class.
No direct httpx calls to api.getxapi.com allowed anywhere else.

Budget is checked BEFORE every call. No exceptions.

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
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx


# Cost table
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
BUDGET_FILE = Path(__file__).parent.parent.parent / "data" / "budgets" / "budget_state.json"
LEDGER_FILE = Path(__file__).parent.parent.parent / "data" / "budgets" / "api_ledger.jsonl"


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


class BudgetBlocker:
    """Enforces budget checks before every API call."""
    
    def __init__(self):
        BUDGET_FILE.parent.mkdir(parents=True, exist_ok=True)
        LEDGER_FILE.parent.mkdir(parents=True, exist_ok=True)
        self._state = self._load_state()
    
    def _load_state(self) -> dict:
        if BUDGET_FILE.exists():
            with open(BUDGET_FILE) as f:
                return json.load(f)
        return {
            "session_calls": 0,
            "session_tweets": 0,
            "session_cost": 0.0,
            "last_balance_check": 0.0,
            "last_balance": 0.0,
            "auto_approve_under": 0.05,
            "require_approval_over": 0.05,
        }
    
    def _save_state(self):
        with open(BUDGET_FILE, "w") as f:
            json.dump(self._state, f, indent=2)
    
    def get_balance(self, force: bool = False) -> float:
        """Get current balance. Caches for 60 seconds."""
        now = time.time()
        if not force and (now - self._state["last_balance_check"]) < 60:
            return self._state["last_balance"]
        
        try:
            key = _get_api_key()
            resp = httpx.get(f"{BASE_URL}/account/me",
                headers={"Authorization": f"Bearer {key}"}, timeout=10)
            balance = resp.json().get("balance_total", 0.0)
            self._state["last_balance"] = balance
            self._state["last_balance_check"] = now
            self._save_state()
            return balance
        except Exception:
            return self._state.get("last_balance", 0.0)
    
    def check_budget(self, estimated_cost: float) -> bool:
        """BLOCK if can't afford. Returns True if OK to proceed."""
        balance = self.get_balance()
        
        if estimated_cost > balance:
            print(f"\n{'='*50}")
            print(f"BUDGET BLOCKED")
            print(f"{'='*50}")
            print(f"Need:  ${estimated_cost:.4f}")
            print(f"Have:  ${balance:.2f}")
            print(f"Cannot proceed. Top up or reduce scope.")
            print(f"{'='*50}")
            return False
        
        if estimated_cost > self._state["require_approval_over"]:
            print(f"\nCost ${estimated_cost:.4f} > auto-approve threshold ${self._state['require_approval_over']:.2f}")
            response = input("Approve? (y/n): ").strip().lower()
            if response != "y":
                print("Blocked by user.")
                return False
        
        return True
    
    def record(self, endpoint: str, calls: int, tweets: int = 0):
        """Record actual usage."""
        cost = calls * COSTS.get(endpoint.split("/")[-1], 0.001)
        self._state["session_calls"] += calls
        self._state["session_tweets"] += tweets
        self._state["session_cost"] += cost
        self._save_state()
        
        # Log
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "endpoint": endpoint,
            "calls": calls,
            "tweets": tweets,
            "cost_usd": cost,
            "session_total_calls": self._state["session_calls"],
            "session_total_cost": round(self._state["session_cost"], 4),
        }
        with open(LEDGER_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")
    
    def status(self):
        """Print budget status."""
        balance = self.get_balance()
        print(f"\n{'='*50}")
        print(f"BUDGET STATUS")
        print(f"{'='*50}")
        print(f"Balance:       ${balance:.2f}")
        print(f"Session calls: {self._state['session_calls']}")
        print(f"Session tweets:{self._state['session_tweets']}")
        print(f"Session cost:  ${self._state['session_cost']:.4f}")
        print(f"{'='*50}")


# Global budget blocker instance
_budget = BudgetBlocker()


class GetXAPI:
    """Canonical X API client with ENFORCED budget checks.
    
    Every method that makes API calls checks budget FIRST.
    No call happens without budget approval.
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or _get_api_key()
        if not self.api_key:
            raise ValueError("No API key found.")
        
        self.client = httpx.Client(
            base_url=BASE_URL,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=30.0,
        )
        self._last_request = 0.0
        self._calls = 0
        self._cost = 0.0
    
    def _rate_limit(self):
        """Enforce rate limiting."""
        elapsed = time.time() - self._last_request
        if elapsed < 2.1:
            time.sleep(2.1 - elapsed)
        self._last_request = time.time()
    
    def _request(self, endpoint: str, params: dict) -> dict:
        """Make an API request. Budget is already checked by caller."""
        self._rate_limit()
        
        start = time.time()
        resp = self.client.get(endpoint, params=params)
        elapsed = time.time() - start
        
        data = resp.json()
        
        cost = COSTS.get(endpoint.split("/")[-1], 0.001)
        self._calls += 1
        self._cost += cost
        
        _budget.record(endpoint, 1)
        
        return data
    
    def search(self, handle: str, since: str, until: str,
               max_pages: int = 50) -> list[dict]:
        """Fetch tweets with BUDGET CHECK before each page."""
        query = f"from:{handle} since:{since} until:{until}"
        all_tweets = []
        cursor = None
        page = 0
        cost_per_page = COSTS["advanced_search"]
        
        # Estimate total cost
        estimated_total = cost_per_page * max_pages
        if not _budget.check_budget(estimated_total):
            return []
        
        while page < max_pages:
            page += 1
            
            # Check budget BEFORE each page
            if not _budget.check_budget(cost_per_page):
                print(f"  Budget exhausted after {page-1} pages")
                break
            
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
            
            if not has_more or not cursor:
                break
        
        return all_tweets
    
    def user_tweets(self, handle: str, max_pages: int = 200) -> list[dict]:
        """Fetch user tweets with BUDGET CHECK."""
        cost_per_page = COSTS["user_tweets"]
        estimated_total = cost_per_page * max_pages
        if not _budget.check_budget(estimated_total):
            return []
        
        all_tweets = []
        cursor = None
        page = 0
        
        while page < max_pages:
            page += 1
            if not _budget.check_budget(cost_per_page):
                break
            
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
            
            if not has_more or not cursor:
                break
        
        return all_tweets
    
    def user_info(self, handle: str) -> dict:
        """Get user info with BUDGET CHECK."""
        if not _budget.check_budget(COSTS["user_info"]):
            return {}
        data = self._request("/twitter/user/info", {"userName": handle})
        return data.get("data", {})
    
    def balance(self) -> float:
        """Get current balance (cached)."""
        return _budget.get_balance()
    
    def status(self):
        """Print budget status."""
        _budget.status()
    
    def close(self):
        self.client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()
