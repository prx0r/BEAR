"""Budget enforcement for GetXAPI — estimate before, track after, enforce limits.

Every API call MUST check budget before executing.
"""

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path


STATE_PATH = Path(__file__).parent.parent.parent / "data" / "budgets" / "budget_state.json"


def get_balance() -> float:
    """Get current API balance."""
    try:
        import httpx
        key = os.environ.get("GETXAPI_KEY", "")
        if not key:
            result = subprocess.run(
                ["agent-vault", "vault", "credential", "get", "GETXAPI_KEY", "--vault", "oracle"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                key = result.stdout.strip()
        
        if not key:
            return 0.0
        
        resp = httpx.get("https://api.getxapi.com/account/me",
            headers={"Authorization": f"Bearer {key}"}, timeout=10)
        return resp.json().get("balance_total", 0.0)
    except Exception:
        return 0.0


def check_budget(estimated_cost: float, auto_approve_under: float = 0.10) -> bool:
    """Check if we can afford an operation. Returns True if OK.
    
    Args:
        estimated_cost: How much this will cost
        auto_approve_under: Auto-approve if under this threshold
    """
    balance = get_balance()
    
    if estimated_cost > balance:
        print(f"\n*** BUDGET EXCEEDED ***")
        print(f"Need: ${estimated_cost:.4f}")
        print(f"Have: ${balance:.2f}")
        return False
    
    if estimated_cost > auto_approve_under:
        print(f"\nCost ${estimated_cost:.4f} > auto-approve threshold")
        response = input("Approve? (y/n): ").strip().lower()
        return response == "y"
    
    return True


def record_usage(endpoint: str, calls: int, tweets: int = 0):
    """Record API usage after calls complete."""
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    if STATE_PATH.exists():
        with open(STATE_PATH) as f:
            state = json.load(f)
    else:
        state = {"total_calls": 0, "total_tweets": 0, "total_cost": 0.0}
    
    cost = calls * 0.001  # $0.001 per call
    state["total_calls"] += calls
    state["total_tweets"] += tweets
    state["total_cost"] += cost
    state["last_updated"] = datetime.now(timezone.utc).isoformat()
    
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


# Cost table
COST_TABLE = {
    "advanced_search": "$0.001/page (~20 tweets)",
    "user_tweets": "$0.001/page",
    "user_tweets_complete": "$0.003/page",
    "tweet_detail": "$0.001/tweet",
    "tweet_thread": "$0.005/thread",
    "tweet_replies": "$0.001/page",
    "user_info": "$0.001/call",
}
