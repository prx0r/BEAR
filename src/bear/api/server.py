"""FastAPI REST API for BEAR — Signal intelligence dashboard.

⚠️  RESEARCH-ONLY SYSTEM — NO LIVE TRADING ⚠️
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI(title="BEAR API", version="0.1.0")

_start_time = time.time()


@app.get("/health")
async def health():
    return {"status": "ok", "uptime": time.time() - _start_time}


@app.get("/signals/stats")
async def signal_stats():
    """Get signal performance statistics."""
    try:
        from bear.api.signal_performance import generate_dashboard_data
        return generate_dashboard_data()
    except Exception as e:
        return {"error": str(e)}


@app.get("/signals/leaderboard")
async def signal_leaderboard():
    """Get author leaderboard."""
    try:
        from bear.api.signal_performance import load_outcomes, compute_signal_stats
        outcomes = load_outcomes()
        stats = compute_signal_stats(outcomes)
        leaderboard = []
        for author, s in stats.get('by_author', {}).items():
            leaderboard.append({
                "author": author,
                "signals": s["directional_signals"],
                "win_rate": round(s["win_rate"], 3),
                "avg_return_4h": round(s["avg_return_4h"], 4),
            })
        leaderboard.sort(key=lambda x: x.get("win_rate", 0), reverse=True)
        return leaderboard
    except Exception as e:
        return {"error": str(e)}


@app.get("/signals/budget")
async def signal_budget():
    """Get API spending status."""
    log_path = Path("/root/BEAR/astronomer/data/budgets/fetch_log.jsonl")
    total_cost = 0.0
    total_posts = 0
    if log_path.exists():
        with open(log_path) as f:
            for line in f:
                if line.strip():
                    entry = json.loads(line)
                    total_cost += entry.get("cost_usd", 0)
                    total_posts += entry.get("posts_returned", 0)
    
    try:
        resp = httpx.get("https://api.getxapi.com/account/me",
            headers={"Authorization": f"Bearer {os.environ.get('GETXAPI_KEY', '')}"}, timeout=5.0)
        balance = resp.json().get("balance_total", 0)
    except:
        balance = 0
    
    return {
        "balance": balance,
        "calls_remaining": int(balance / 0.001),
        "total_spent": round(total_cost, 4),
        "total_posts": total_posts,
    }


@app.post("/webhook/x")
async def x_webhook():
    """Receive real-time tweets from X monitoring."""
    return {"status": "received"}


@app.get("/mcp/summary")
async def mcp_summary():
    """MCP: System summary."""
    return {"status": "ok", "message": "BEAR Signal Intelligence"}


def create_app() -> FastAPI:
    return app
