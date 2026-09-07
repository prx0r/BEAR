"""BEAR Trading Agent — LLM reads signals, decides when to activate strategies.

One job: WHEN to turn each strategy ON or OFF.

Input: raw tweets + regime + strategy states
Output: ON/OFF decisions with reasoning

Uses Hermes via Anthropic API with Pydantic structured output.
"""

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx


def get_hermes_key() -> str:
    """Get Hermes API key from vault."""
    try:
        result = subprocess.run(
            ["agent-vault", "vault", "credential", "get", "HERMES_API_KEY", "--vault", "oracle"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return os.environ.get("HERMES_API_KEY", "")


# Strategy definitions
STRATEGIES = {
    "DEATH_TOKEN": {
        "description": "Short tokens with structural decay (volume death, deep decline, funding pressure)",
        "activation": "When market regime is DOWN or RANGE AND death score > 75",
        "deactivation": "When regime flips UP OR death score < 50",
    },
    "RANGE_TRADE": {
        "description": "Follow Timeless's calls in RANGE regime at 24h horizon",
        "activation": "When BTC is ranging AND Timeless posts BTC call",
        "deactivation": "When regime leaves RANGE OR 24h passes",
    },
    "DOWNTREND_SHORT": {
        "description": "Follow XO's calls in DOWN regime at 4h horizon",
        "activation": "When BTC is in downtrend AND XO posts BTC short",
        "deactivation": "When regime leaves DOWN OR 4h passes",
    },
    "ETH_BHEEM": {
        "description": "Follow CryptoBheem's ETH level trades",
        "activation": "When Bheem posts ETH with specific levels",
        "deactivation": "When target hit OR invalidation hit",
    },
}


def build_prompt(tweets: list[dict], regime: str, strategy_states: dict) -> str:
    """Build the prompt for the trading agent."""
    
    # Format recent tweets
    tweet_text = ""
    for t in tweets[-20:]:  # Last 20 tweets
        handle = t.get("handle", "?")
        text = t.get("text", "")[:200]
        created = t.get("createdAt", "")[:16]
        asset = t.get("asset", "")
        direction = t.get("direction", "")
        tweet_text += f"[{created}] @{handle}: {text}\n"
    
    # Format strategy states
    strategy_text = ""
    for name, state in strategy_states.items():
        status = "ON" if state.get("active") else "OFF"
        strategy_text += f"  {name}: {status}"
        if state.get("reason"):
            strategy_text += f" (since {state['reason']})"
        strategy_text += "\n"
    
    prompt = f"""You are BEAR, a crypto trading agent. Your ONE job: decide when to turn strategies ON or OFF.

CURRENT REGIME: {regime}

ACTIVE STRATEGIES:
{strategy_text}

RECENT SIGNALS (from monitored traders):
{tweet_text}

YOUR TASK:
For each strategy, decide: should it be ON or OFF right now?

Consider:
1. What are the traders actually saying? (not just keywords — read the meaning)
2. Does the regime support this strategy?
3. Are there conflicting signals?
4. Is this a new entry or an exit?

For each strategy, output:
- DECISION: ON or OFF
- REASON: one sentence explaining why
- CONFIDENCE: HIGH/MEDIUM/LOW

Be decisive. Don't hedge. If the signal is clear, act on it."""

    return prompt


def call_hermes(prompt: str) -> str:
    """Call OpenCode Zen MiMo V2.5 API."""
    key = get_hermes_key()
    
    resp = httpx.post(
        "https://opencode.ai/zen/go/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "x-opencode-session": "bear-agent-001",
        },
        json={
            "model": "mimo-v2.5",
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=60.0,
    )
    
    data = resp.json()
    return data.get("choices", [{}])[0].get("message", {}).get("content", "")


def parse_decisions(response: str) -> dict:
    """Parse LLM response into strategy decisions."""
    decisions = {}
    current_strategy = None
    
    for line in response.split("\n"):
        line = line.strip()
        if not line:
            continue
        
        # Detect strategy name
        for strat in STRATEGIES:
            if strat.lower() in line.lower():
                current_strategy = strat
                if current_strategy not in decisions:
                    decisions[current_strategy] = {}
        
        # Detect ON/OFF
        if current_strategy:
            if "ON" in line.upper() and "OFF" not in line.upper():
                decisions[current_strategy]["active"] = True
            elif "OFF" in line.upper():
                decisions[current_strategy]["active"] = False
        
        # Detect confidence
        if current_strategy:
            if "HIGH" in line.upper():
                decisions[current_strategy]["confidence"] = "HIGH"
            elif "MEDIUM" in line.upper():
                decisions[current_strategy]["confidence"] = "MEDIUM"
            elif "LOW" in line.upper():
                decisions[current_strategy]["confidence"] = "LOW"
        
        # Detect reason
        if current_strategy and ("reason:" in line.lower() or "because" in line.lower()):
            decisions[current_strategy]["reason"] = line
    
    return decisions


class BearAgent:
    """The trading agent. One job: when to turn strategies on/off."""
    
    def __init__(self):
        self.strategy_states = {name: {"active": False, "reason": ""} 
                                for name in STRATEGIES}
        self.decision_log = []
    
    def decide(self, tweets: list[dict], regime: str) -> dict:
        """Main decision loop. Read signals, decide strategy states."""
        
        # Build prompt
        prompt = build_prompt(tweets, regime, self.strategy_states)
        
        # Call LLM
        response = call_hermes(prompt)
        
        # Parse decisions
        new_decisions = parse_decisions(response)
        
        # Update states
        for strat, decision in new_decisions.items():
            old_state = self.strategy_states.get(strat, {})
            new_active = decision.get("active", old_state.get("active", False))
            
            if new_active != old_state.get("active", False):
                # State changed
                self.strategy_states[strat] = {
                    "active": new_active,
                    "reason": decision.get("reason", ""),
                    "confidence": decision.get("confidence", "MEDIUM"),
                    "changed_at": datetime.now(timezone.utc).isoformat(),
                }
                
                # Log the change
                self.decision_log.append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "strategy": strat,
                    "old_state": old_state.get("active", False),
                    "new_state": new_active,
                    "reason": decision.get("reason", ""),
                    "regime": regime,
                })
        
        return {
            "decisions": self.strategy_states,
            "raw_response": response,
            "changes": [d for d in self.decision_log if d["timestamp"] > 
                       (datetime.now(timezone.utc).isoformat()[:10])],
        }


def run_agent_scan():
    """Scan latest tweets and make decisions."""
    # Load latest tweets from all monitored accounts
    from pathlib import Path
    
    live_dir = Path(__file__).parent / "data" / "live"
    events_file = live_dir / "events.jsonl"
    
    if not events_file.exists():
        print("No live events found. Run monitor.py first.")
        return
    
    # Load recent events
    events = []
    with open(events_file) as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))
    
    # Get latest regime
    regime_file = Path(__file__).parent / "data" / "regime" / "timeline.json"
    if regime_file.exists():
        with open(regime_file) as f:
            timeline = json.load(f)
        regime = timeline[-1]["btc_regime"] if timeline else "UNKNOWN"
    else:
        regime = "UNKNOWN"
    
    # Run agent
    agent = BearAgent()
    result = agent.decide(events, regime)
    
    print(f"\n{'='*50}")
    print(f"BEAR AGENT DECISIONS")
    print(f"{'='*50}")
    print(f"Regime: {regime}")
    print()
    
    for strat, state in result["decisions"].items():
        status = "ON" if state.get("active") else "OFF"
        reason = state.get("reason", "no reason given")
        confidence = state.get("confidence", "?")
        print(f"  {strat}: {status} [{confidence}]")
        print(f"    {reason}")
    
    print(f"\n{'='*50}")
    
    return result


if __name__ == "__main__":
    run_agent_scan()
