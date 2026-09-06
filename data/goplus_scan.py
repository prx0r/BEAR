#!/usr/bin/env python3
"""GoPlus Security Scanner for BSC death-watch tokens.

Fetches top 20 BSC pools by 24h volume from GeckoTerminal,
extracts unique token addresses, queries GoPlus for contract
red flags, and computes a risk score 0-100.

Output: /root/BEAR/data/goplus_security.json
"""

import json
import time
import urllib.request
import urllib.error
from pathlib import Path

GEEKOTERMINAL_URL = (
    "https://api.geckoterminal.com/api/v2/networks/bsc/pools"
    "?sort=h24_volume_usd_desc&page=1"
)
GOPLUS_URL = "https://api.gopluslabs.io/api/v1/token_security/56"
OUTPUT = Path(__file__).parent / "goplus_security.json"

# Known stablecoins to exclude
STABLECOINS = {
    "0x55d398326f99059ff775485246999027b3197955",  # USDT
    "0xe9e7cea3dedca5984780bafc599bd69add087d56",  # BUSD
    "0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d",  # USDC
    "0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c",  # WBNB
}

HEADERS = {"User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36"}


def fetch_geckoterminal_pools(n=20):
    """Fetch top BSC pools by 24h volume, return unique non-stablecoin token addresses."""
    req = urllib.request.Request(GEEKOTERMINAL_URL, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())

    pools = data.get("data", [])[:n]
    tokens = {}  # addr -> {pool_name, volume_24h, pool_id}
    for pool in pools:
        attrs = pool["attributes"]
        rels = pool["relationships"]
        vol = attrs.get("volume_usd", {})
        vol_24h = float(vol.get("h24", 0)) if isinstance(vol, dict) else 0
        pool_name = attrs.get("name", "?")
        pool_id = pool.get("id", "")

        for key in ("base_token", "quote_token"):
            token_data = rels.get(key, {}).get("data", {})
            raw_id = token_data.get("id", "")
            addr = raw_id.replace("bsc_", "").lower()
            if addr and addr not in STABLECOINS and addr not in tokens:
                tokens[addr] = {
                    "pool_name": pool_name,
                    "volume_24h_usd": vol_24h,
                    "pool_id": pool_id,
                    "token_side": key,
                }
    return tokens


def fetch_goplus_single(addr):
    """Query GoPlus for a single token address."""
    url = f"{GOPLUS_URL}?contract_addresses={addr}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        return None
    result = data.get("result") or {}
    return result.get(addr) or result.get(addr.lower())


def compute_risk_score(info):
    """Compute contract_risk_score 0-100. Higher = riskier.

    Scoring weights:
      - is_honeypot (1 or "1"): 30 pts
      - is_mintable (1): 15 pts
      - hidden_owner (1): 15 pts
      - selfdestruct (1): 10 pts
      - can_take_back_ownership (1): 10 pts
      - owner_change_balance (1): 5 pts
      - is_proxy (1): 5 pts
      - is_open_source (0): 5 pts (not open source = risky)
      - honeypot_with_same_creator (1): 5 pts
    """
    score = 0
    flags = {}

    def flag(name, weight):
        nonlocal score
        val = info.get(name, "N/A")
        is_bad = val == "1" or val == 1
        flags[name] = val
        if is_bad:
            score += weight
        return is_bad

    flag("is_honeypot", 30)
    flag("is_mintable", 15)
    flag("hidden_owner", 15)
    flag("selfdestruct", 10)
    flag("can_take_back_ownership", 10)
    flag("owner_change_balance", 5)
    flag("is_proxy", 5)
    flag("honeypot_with_same_creator", 5)

    # is_open_source: 0 = not open source = risky
    open_source = info.get("is_open_source", "N/A")
    flags["is_open_source"] = open_source
    if open_source == "0":
        score += 5

    return min(score, 100), flags


def main():
    print("=" * 60)
    print("GoPlus Security Scanner — BSC Death Watch Tokens")
    print("=" * 60)

    # Step 1: Get top pools
    print("\n[1] Fetching top 20 BSC pools by 24h volume from GeckoTerminal...")
    tokens = fetch_geckoterminal_pools(20)
    print(f"    Found {len(tokens)} unique non-stablecoin tokens")

    # Step 2: Query GoPlus one by one (batch queries are rate-limited)
    print("\n[2] Querying GoPlus for contract security data...")
    all_results = {}
    addr_list = list(tokens.keys())

    for i, addr in enumerate(addr_list):
        info = fetch_goplus_single(addr)
        if info:
            all_results[addr] = info
        if i < len(addr_list) - 1:
            time.sleep(0.4)  # rate limit

    print(f"    Got GoPlus data for {len(all_results)} tokens")

    # Step 3: Score each token
    print("\n[3] Computing risk scores...")
    output = []
    for addr in addr_list:
        info = all_results.get(addr, all_results.get(addr.lower(), {}))
        meta = tokens[addr]

        if not info:
            entry = {
                "address": addr,
                "pool": meta["pool_name"],
                "volume_24h_usd": meta["volume_24h_usd"],
                "contract_risk_score": -1,
                "error": "no_goplus_data",
                "flags": {},
            }
        else:
            score, flags = compute_risk_score(info)
            entry = {
                "address": addr,
                "token_name": info.get("token_name", "?"),
                "token_symbol": info.get("token_symbol", "?"),
                "pool": meta["pool_name"],
                "volume_24h_usd": meta["volume_24h_usd"],
                "contract_risk_score": score,
                "creator_address": info.get("creator_address", "N/A"),
                "creator_balance": info.get("creator_balance", "N/A"),
                "creator_percent": info.get("creator_percent", "N/A"),
                "holder_count": info.get("holder_count", "N/A"),
                "is_open_source": info.get("is_open_source", "N/A"),
                "dex": info.get("dex", []),
                "flags": flags,
            }
            risk_label = (
                "CRITICAL" if score >= 60
                else "HIGH" if score >= 40
                else "MEDIUM" if score >= 20
                else "LOW"
            )
            print(
                f"    {entry.get('token_symbol', addr[:10]):>10s} "
                f"risk={score:>3d} ({risk_label:>8s}) "
                f"honeypot={flags.get('is_honeypot','?')} "
                f"mintable={flags.get('is_mintable','?')} "
                f"proxy={flags.get('is_proxy','?')}"
            )

        output.append(entry)

    # Step 4: Save
    output.sort(key=lambda x: x["contract_risk_score"], reverse=True)
    OUTPUT.write_text(json.dumps(output, indent=2))
    print(f"\n[4] Saved {len(output)} results to {OUTPUT}")

    # Summary
    scores = [e["contract_risk_score"] for e in output if e["contract_risk_score"] >= 0]
    if scores:
        print(f"\n{'=' * 60}")
        print(f"SUMMARY: {len(scores)} tokens scanned")
        print(f"  Avg risk: {sum(scores)/len(scores):.1f}")
        print(f"  Max risk: {max(scores)}")
        critical = [e for e in output if e["contract_risk_score"] >= 60]
        high = [e for e in output if 40 <= e["contract_risk_score"] < 60]
        print(f"  CRITICAL (>=60): {len(critical)}")
        print(f"  HIGH (40-59): {len(high)}")
        for e in critical + high:
            print(f"    {e.get('token_symbol','?'):>10s} score={e['contract_risk_score']} "
                  f"pool={e['pool']} vol=${e['volume_24h_usd']:,.0f}")
    print("=" * 60)


if __name__ == "__main__":
    main()
