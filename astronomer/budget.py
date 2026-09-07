"""BEAR API Budget Controller — estimate before, track after, enforce limits.

Every API call MUST pass through this filter.

Usage:
    from budget import BudgetController
    
    bc = BudgetController()
    bc.estimate('advanced_search', pages=10)  # shows cost, asks if OK
    # ... make calls ...
    bc.record('advanced_search', pages=actual_pages)
    bc.status()  # shows remaining
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data" / "budgets"
LEDGER_PATH = DATA_DIR / "api_ledger.jsonl"
STATE_PATH = DATA_DIR / "budget_state.json"

# Known costs per endpoint (as of 2026-09-07)
COSTS = {
    "advanced_search": 0.001,       # per page (~20 tweets)
    "user_tweets": 0.001,          # per page (~20 tweets)
    "user_tweets_complete": 0.003, # per page (~20 tweets + replies)
    "tweet_detail": 0.001,         # per tweet
    "tweet_thread": 0.005,         # per thread
    "tweet_replies": 0.001,        # per page
    "user_info": 0.001,            # per call
    "user_search": 0.001,          # per page
}

# Rate limits (calls per minute)
RATE_LIMITS = {
    "advanced_search": 30,
    "user_tweets": 30,
    "user_tweets_complete": 10,
    "tweet_detail": 60,
    "tweet_thread": 20,
    "tweet_replies": 30,
    "user_info": 30,
    "user_search": 30,
}


def get_api_key() -> str:
    """Get API key from vault."""
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


def get_balance() -> float:
    """Get current balance from API."""
    import httpx
    key = get_api_key()
    if not key:
        return 0.0
    try:
        resp = httpx.get('https://api.getxapi.com/account/me',
            headers={'Authorization': f'Bearer {key}'}, timeout=10)
        d = resp.json()
        return d.get('balance_total', 0.0)
    except:
        return 0.0


class BudgetController:
    """Enforces budget discipline for all API calls."""
    
    def __init__(self, auto_approve_threshold: float = 0.10):
        """Initialize budget controller.
        
        Args:
            auto_approve_threshold: Auto-approve if estimated cost < this amount
        """
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.auto_approve_threshold = auto_approve_threshold
        self._load_state()
    
    def _load_state(self):
        """Load budget state from disk."""
        if STATE_PATH.exists():
            with open(STATE_PATH) as f:
                self.state = json.load(f)
        else:
            self.state = {
                "starting_balance": get_balance(),
                "estimated_total": 0.0,
                "actual_total": 0.0,
                "calls_today": 0,
                "tweets_today": 0,
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }
            self._save_state()
    
    def _save_state(self):
        """Save budget state."""
        self.state["last_updated"] = datetime.now(timezone.utc).isoformat()
        with open(STATE_PATH, "w") as f:
            json.dump(self.state, f, indent=2)
    
    def _log_call(self, endpoint: str, estimated: float, actual: float, 
                  details: dict):
        """Append to ledger."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "endpoint": endpoint,
            "estimated_usd": estimated,
            "actual_usd": actual,
            "difference": actual - estimated,
            **details,
        }
        with open(LEDGER_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")
    
    def estimate(self, endpoint: str, pages: int = 1, tweets: int = 0,
                 verbose: bool = True) -> float:
        """Estimate cost before making calls.
        
        Args:
            endpoint: API endpoint name
            pages: Number of pages to fetch
            tweets: Number of tweets (for logging)
            verbose: Print estimate
            
        Returns:
            Estimated cost in USD
        """
        cost_per_call = COSTS.get(endpoint, 0.001)
        estimated = cost_per_call * pages
        
        if verbose:
            print(f"\n{'='*50}")
            print(f"API COST ESTIMATE")
            print(f"{'='*50}")
            print(f"Endpoint: {endpoint}")
            print(f"Pages: {pages}")
            print(f"Est. tweets: {tweets or pages * 20}")
            print(f"Cost/page: ${cost_per_call:.4f}")
            print(f"ESTIMATED TOTAL: ${estimated:.4f}")
            print(f"Remaining budget: ${self.state['starting_balance'] - self.state['actual_total']:.2f}")
            print(f"{'='*50}")
        
        self.state["estimated_total"] += estimated
        self._save_state()
        
        return estimated
    
    def check_budget(self, estimated: float) -> bool:
        """Check if we can afford this. Returns True if OK to proceed."""
        remaining = self.state["starting_balance"] - self.state["actual_total"]
        
        if estimated > remaining:
            print(f"\n*** BUDGET EXCEEDED ***")
            print(f"Estimated: ${estimated:.4f}")
            print(f"Remaining: ${remaining:.2f}")
            print(f"Cannot proceed.")
            return False
        
        if estimated > self.auto_approve_threshold:
            print(f"\nCost ${estimated:.4f} exceeds auto-approve threshold ${self.auto_approve_threshold:.2f}")
            response = input("Approve? (y/n): ").strip().lower()
            return response == 'y'
        
        return True
    
    def record(self, endpoint: str, pages: int, tweets: int = 0,
               actual_cost: float = None):
        """Record actual API usage after calls complete.
        
        Args:
            endpoint: API endpoint used
            pages: Actual pages fetched
            tweets: Actual tweets received
            actual_cost: If known, the actual cost charged
        """
        cost_per_call = COSTS.get(endpoint, 0.001)
        actual = actual_cost if actual_cost is not None else cost_per_call * pages
        
        # Check balance
        current_balance = get_balance()
        
        self.state["actual_total"] += actual
        self.state["calls_today"] += pages
        self.state["tweets_today"] += tweets
        self._save_state()
        
        self._log_call(endpoint, cost_per_call * pages, actual, {
            "pages": pages,
            "tweets": tweets,
            "balance_after": current_balance,
        })
        
        # Warn if balance is low
        if current_balance < 5.0:
            print(f"\n*** LOW BALANCE WARNING: ${current_balance:.2f} ***")
    
    def status(self):
        """Print current budget status."""
        current_balance = get_balance()
        used = self.state["starting_balance"] - current_balance
        
        print(f"\n{'='*50}")
        print(f"BUDGET STATUS")
        print(f"{'='*50}")
        print(f"Starting balance:  ${self.state['starting_balance']:.2f}")
        print(f"Current balance:   ${current_balance:.2f}")
        print(f"Total spent:       ${used:.2f}")
        print(f"Calls today:       {self.state['calls_today']}")
        print(f"Tweets today:      {self.state['tweets_today']}")
        print(f"Estimated total:   ${self.state['estimated_total']:.4f}")
        print(f"Actual total:      ${self.state['actual_total']:.4f}")
        
        # Check accuracy
        if self.state["estimated_total"] > 0:
            accuracy = self.state["actual_total"] / self.state["estimated_total"]
            print(f"Estimate accuracy: {accuracy:.1%}")
        
        print(f"{'='*50}")
    
    def remaining(self) -> float:
        """Return remaining budget."""
        return get_balance()


def run_budget_check():
    """Quick budget status check."""
    bc = BudgetController()
    bc.status()


if __name__ == "__main__":
    run_budget_check()
