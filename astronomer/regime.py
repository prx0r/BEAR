"""BGeometrics integration — BTC regime detection from on-chain data."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx

# BGeometrics config
BASE_URL = "https://api.bgeometrics.com/v1"
DATA_DIR = Path(__file__).parent / "data" / "regime"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Key metrics for regime detection
METRICS = {
    "hash_rate": "mining/hash_rate_mean",
    "miner_revenue": "mining/revenue_sum",
    "exchange_inflow": "exchange/inflow_sum",
    "exchange_outflow": "exchange/outflow_sum",
    "exchange_netflow": "exchange/netflow_sum",
    "mvrv": "market/mvrv",
    "sopr": "market/sopr",
    "nvt": "market/nvt",
    "active_addresses": "network/active_addresses",
    "utxo_count": "supply/utxo_count",
    "lth_supply": "supply/lth_supply",
    "sth_supply": "supply/sth_supply",
}


def fetch_metric(metric: str, period: str = "24h") -> dict:
    """Fetch a single metric from BGeometrics."""
    try:
        resp = httpx.get(
            f"{BASE_URL}/metrics/{metric}",
            params={"period": period},
            timeout=10.0,
        )
        if resp.status_code == 429:
            return {"error": "rate_limited"}
        if resp.status_code == 200:
            return resp.json()
        return {"error": resp.status_code}
    except Exception as e:
        return {"error": str(e)}


def fetch_all_regime_metrics() -> dict:
    """Fetch all regime-relevant metrics."""
    metrics = {}
    for name, endpoint in METRICS.items():
        try:
            data = fetch_metric(endpoint)
            metrics[name] = data
        except Exception as e:
            metrics[name] = {"error": str(e)}
    return metrics


def detect_regime(metrics: dict) -> dict:
    """Detect BTC regime from on-chain metrics."""
    regime = {
        "hash_rate_trend": "unknown",
        "miner_behavior": "unknown",
        "exchange_flow": "unknown",
        "valuation": "unknown",
        "holder_distribution": "unknown",
        "overall": "UNKNOWN",
    }
    
    # Hash rate trend
    hr = metrics.get("hash_rate", {})
    if "v" in hr:
        regime["hash_rate_trend"] = "GROWING"  # simplified
    
    # Miner behavior
    miner_rev = metrics.get("miner_revenue", {})
    if "v" in miner_rev:
        regime["miner_behavior"] = "ACTIVE"
    
    # Exchange flow
    inflow = metrics.get("exchange_inflow", {})
    outflow = metrics.get("exchange_outflow", {})
    if "v" in inflow and "v" in outflow:
        if float(outflow.get("v", 0)) > float(inflow.get("v", 0)):
            regime["exchange_flow"] = "OUTFLOW_DOMINANT"
        else:
            regime["exchange_flow"] = "INFLOW_DOMINANT"
    
    # MVRV
    mvrv = metrics.get("mvrv", {})
    if "v" in mvrv:
        mvrv_val = float(mvrv["v"])
        if mvrv_val > 3.5:
            regime["valuation"] = "OVERVALUED"
        elif mvrv_val > 2.0:
            regime["valuation"] = "FAIR"
        elif mvrv_val > 1.0:
            regime["valuation"] = "UNDERVALUED"
        else:
            regime["valuation"] = "DEEPLY_UNDERVALUED"
    
    # Holder distribution
    lth = metrics.get("lth_supply", {})
    sth = metrics.get("sth_supply", {})
    if "v" in lth and "v" in sth:
        lth_val = float(lth["v"])
        sth_val = float(sth["v"])
        if lth_val > sth_val * 3:
            regime["holder_distribution"] = "LTH_DOMINANT"
        else:
            regime["holder_distribution"] = "BALANCED"
    
    # Overall regime
    scores = {
        "OVERVALUED": -1,
        "FAIR": 0,
        "UNDERVALUED": 1,
        "DEEPLY_UNDERVALUED": 2,
    }
    score = scores.get(regime.get("valuation", "FAIR"), 0)
    
    if regime["exchange_flow"] == "OUTFLOW_DOMINANT":
        score += 1
    if regime["hash_rate_trend"] == "GROWING":
        score += 1
    if regime["holder_distribution"] == "LTH_DOMINANT":
        score += 1
    
    if score >= 3:
        regime["overall"] = "RISK_ON"
    elif score >= 1:
        regime["overall"] = "NEUTRAL"
    else:
        regime["overall"] = "RISK_OFF"
    
    return regime


def main():
    """Fetch metrics and detect regime."""
    print("Fetching BGeometrics metrics...")
    metrics = fetch_all_regime_metrics()
    
    # Save raw metrics
    with open(DATA_DIR / "metrics.json", "w") as f:
        json.dump(metrics, f, indent=2, default=str)
    
    # Detect regime
    regime = detect_regime(metrics)
    
    # Save regime
    with open(DATA_DIR / "regime.json", "w") as f:
        json.dump(regime, f, indent=2)
    
    print(f"\nRegime: {regime['overall']}")
    print(f"  Hash rate: {regime['hash_rate_trend']}")
    print(f"  Exchange flow: {regime['exchange_flow']}")
    print(f"  Valuation: {regime['valuation']}")
    print(f"  Holders: {regime['holder_distribution']}")
    
    return regime


if __name__ == "__main__":
    main()
