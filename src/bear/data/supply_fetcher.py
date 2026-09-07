"""Fetch supply/tokenomics data from CoinGecko free API.

CoinGecko /coins/list provides market_cap, total_supply, circulating_supply.
No API key needed for basic endpoints (rate limited ~30 req/min).
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import httpx

DATA_DIR = Path("/root/BEAR/data")
CACHE_PATH = DATA_DIR / "supply_cache.json"

# Map Binance symbols to CoinGecko IDs
SYMBOL_MAP = {
    "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana",
    "DOGE": "dogecoin", "SHIB": "shiba-inu", "PEPE": "pepe",
    "ADA": "cardano", "AVAX": "avalanche-2", "DOT": "polkadot",
    "LINK": "chainlink", "UNI": "uniswap", "AAVE": "aave",
    "MKR": "maker", "SNX": "havven", "CRV": "curve-dao-token",
    "LDO": "lido-dao", "PENDLE": "pendle", "INJ": "injective-protocol",
    "TIA": "celestia", "SEI": "sei-network", "NEAR": "near",
    "FIL": "filecoin", "AR": "arweave", "HBAR": "hedera-hashgraph",
    "XLM": "stellar", "ONDO": "ondo-finance", "TRX": "tron",
    "TON": "the-open-network", "ICP": "internet-computer",
    "ETC": "ethereum-classic", "BCH": "bitcoin-cash", "LTC": "litecoin",
    "DASH": "dash", "XMR": "monero", "ZEC": "zcash",
    "FET": "fetch-ai", "RENDER": "render-token", "AKT": "akash-network",
    "GRT": "the-graph", "OCEAN": "ocean-protocol",
    "ARB": "arbitrum", "OP": "optimism", "MATIC": "matic-network",
    "IMX": "immutable-x", "SAND": "the-sandbox", "MANA": "decentraland",
    "AXS": "axie-infinity", "GALA": "gala", "WIF": "dogwifcoin",
    "BONK": "bonk", "FLOKI": "floki", "ENA": "ethena",
    "WLD": "worldcoin-wld", "TNSR": "tensor", "JTO": "jito-governance-token",
    "SUSHI": "sushi", "DYDX": "dydx-chain", "ATOM": "cosmos",
    "APT": "aptos", "SUI": "sui", "STRK": "starknet",
    "W": "wormhole", "ZK": "zksync", "PYTH": "pyth-network",
    "IOTA": "iota", "XRP": "ripple",
}


def fetch_supply_data(symbols: list[str] | None = None, max_retries: int = 2) -> dict[str, dict]:
    """Fetch circulating/total supply from CoinGecko.

    Returns dict[symbol -> {circulating, total, max, market_cap, fdv, price}]
    """
    # Load cache
    cache = {}
    if CACHE_PATH.exists():
        try:
            cache = json.loads(CACHE_PATH.read_text())
        except Exception:
            cache = {}

    if symbols is None:
        symbols = list(SYMBOL_MAP.keys())

    results = {}
    client = httpx.Client(timeout=15, follow_redirects=True)

    for sym in symbols:
        cg_id = SYMBOL_MAP.get(sym)
        if not cg_id:
            continue

        # Use cache if < 24h old
        if cg_id in cache:
            cached_at = cache[cg_id].get("_cached_at", 0)
            if time.time() - cached_at < 86400:
                results[sym] = cache[cg_id]
                continue

        url = f"https://api.coingecko.com/api/v3/coins/{cg_id}"
        for attempt in range(max_retries):
            try:
                resp = client.get(url, params={
                    "localization": "false",
                    "tickers": "false",
                    "market_data": "true",
                    "community_data": "false",
                    "developer_data": "false",
                })
                if resp.status_code == 429:
                    time.sleep(10)
                    continue
                if resp.status_code != 200:
                    break

                data = resp.json()
                md = data.get("market_data", {})

                circ = md.get("circulating_supply")
                total = md.get("total_supply")
                max_s = md.get("max_supply")
                mcap = md.get("market_cap", {}).get("usd")
                fdv = md.get("fully_diluted_valuation", {}).get("usd")
                price = md.get("current_price", {}).get("usd")

                result = {
                    "circulating_supply": circ,
                    "total_supply": total,
                    "max_supply": max_s,
                    "market_cap": mcap,
                    "fdv": fdv,
                    "price": price,
                    "_cached_at": time.time(),
                }
                results[sym] = result
                cache[cg_id] = result
                break

            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(2)
                continue

        # Rate limit: ~30 req/min for free tier
        time.sleep(2.1)

    client.close()

    # Save cache
    CACHE_PATH.write_text(json.dumps(cache, indent=2, default=str))
    print(f"Fetched supply data for {len(results)} symbols (cached: {len(cache)})")
    return results


def compute_fdv_overhang(supply_data: dict[str, dict]) -> dict[str, float]:
    """Compute FDV/MCap overhang for each symbol.

    > 1.0 means FDV > MCap (dilution risk).
    """
    result = {}
    for sym, d in supply_data.items():
        mcap = d.get("market_cap")
        fdv = d.get("fdv")
        if mcap and fdv and mcap > 0:
            result[sym] = fdv / mcap
        elif d.get("circulating_supply") and d.get("total_supply"):
            circ = d["circulating_supply"]
            total = d["total_supply"]
            if circ > 0:
                result[sym] = total / circ
    return result


def compute_supply_pressure(supply_data: dict[str, dict]) -> dict[str, dict]:
    """Compute supply pressure metrics for each symbol.

    Returns dict[symbol -> {fdv_overhang, circ_pct, dilution_risk}]
    """
    result = {}
    for sym, d in supply_data.items():
        circ = d.get("circulating_supply")
        total = d.get("total_supply")
        max_s = d.get("max_supply")
        mcap = d.get("market_cap")
        fdv = d.get("fdv")

        denominator = max_s or total or circ
        circ_pct = (circ / denominator * 100) if circ and denominator and denominator > 0 else None
        fdv_overhang = (fdv / mcap) if fdv and mcap and mcap > 0 else None

        # Dilution risk: how much more supply can come
        remaining_pct = ((denominator - circ) / denominator * 100) if circ and denominator and denominator > circ else 0

        result[sym] = {
            "circulating_supply": circ,
            "total_supply": total,
            "max_supply": max_s,
            "market_cap": mcap,
            "fdv": fdv,
            "circ_pct": round(circ_pct, 1) if circ_pct else None,
            "fdv_overhang": round(fdv_overhang, 3) if fdv_overhang else None,
            "remaining_dilution_pct": round(remaining_pct, 1),
            "dilution_risk": "high" if remaining_pct > 50 else ("medium" if remaining_pct > 20 else "low"),
        }

    return result


if __name__ == "__main__":
    data = fetch_supply_data()
    pressure = compute_supply_pressure(data)
    overhang = compute_fdv_overhang(data)

    print("\nFDV Overhang (top 10 by dilution risk):")
    ranked = sorted(overhang.items(), key=lambda x: x[1], reverse=True)
    for sym, oh in ranked[:10]:
        p = pressure.get(sym, {})
        print(f"  {sym:>6s}: {oh:.2f}x  circ={p.get('circ_pct', '?')}%  risk={p.get('dilution_risk', '?')}")
