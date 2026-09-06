#!/usr/bin/env python3
"""Binance Web3 Creator Wallet Forensics for BSC tokens.

For each token, uses GoPlus to get the creator address, then checks
Binance Web3 token info and GoPlus holder data to determine if the
creator still holds tokens.

Output: /root/BEAR/data/creator_forensics.json
"""

import json
import time
import urllib.request
import urllib.error
from pathlib import Path

GOPLUS_URL = "https://api.gopluslabs.io/api/v1/token_security/56"
BINANCE_TOKEN_URL = (
    "https://web3.binance.com/bapi/defi/v4/public/wallet-direct/"
    "buw/wallet/market/token/dynamic/info"
)
OUTPUT = Path(__file__).parent / "creator_forensics.json"

# Use same token list as goplus_scan or read from its output
GPLUS_OUTPUT = Path(__file__).parent / "goplus_security.json"

STABLECOINS = {
    "0x55d398326f99059ff775485246999027b3197955",
    "0xe9e7cea3dedca5984780bafc599bd69add087d56",
    "0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d",
    "0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c",
}

GEEKOTERMINAL_URL = (
    "https://api.geckoterminal.com/api/v2/networks/bsc/pools"
    "?sort=h24_volume_usd_desc&page=1"
)
HEADERS = {"User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36"}


def fetch_tokens():
    """Load token list from goplus_scan output, or fetch fresh from GeckoTerminal."""
    if GPLUS_OUTPUT.exists():
        print("  Loading token list from goplus_security.json...")
        prev = json.loads(GPLUS_OUTPUT.read_text())
        return {
            e["address"]: {
                "pool_name": e.get("pool", "?"),
                "volume_24h_usd": e.get("volume_24h_usd", 0),
                "token_name": e.get("token_name", "?"),
                "token_symbol": e.get("token_symbol", "?"),
            }
            for e in prev
            if e.get("contract_risk_score", -1) >= 0
        }

    print("  Fetching fresh token list from GeckoTerminal...")
    req = urllib.request.Request(GEEKOTERMINAL_URL, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())

    pools = data.get("data", [])[:20]
    tokens = {}
    for pool in pools:
        attrs = pool["attributes"]
        rels = pool["relationships"]
        vol = attrs.get("volume_usd", {})
        vol_24h = float(vol.get("h24", 0)) if isinstance(vol, dict) else 0
        pool_name = attrs.get("name", "?")
        for key in ("base_token", "quote_token"):
            raw_id = rels.get(key, {}).get("data", {}).get("id", "")
            addr = raw_id.replace("bsc_", "").lower()
            if addr and addr not in STABLECOINS and addr not in tokens:
                tokens[addr] = {"pool_name": pool_name, "volume_24h_usd": vol_24h}
    return tokens


def fetch_goplus(addr):
    """Query GoPlus for a single token."""
    url = f"{GOPLUS_URL}?contract_addresses={addr}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        return None, str(e)
    result = data.get("result") or {}
    return result.get(addr) or result.get(addr.lower()), None


def fetch_binance_token_info(addr):
    """Query Binance Web3 for token info."""
    url = f"{BINANCE_TOKEN_URL}?chainId=56&contractAddress={addr}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        return None, str(e)
    if data.get("code") != "000000":
        return None, data.get("message", "unknown error")
    return data.get("data"), None


def check_creator_holding(info, addr):
    """Check if creator still holds tokens using GoPlus holder data.

    Returns: (still_holds: bool, creator_balance: str, creator_percent: str, status: str)
    """
    creator = info.get("creator_address", "N/A")
    creator_balance = info.get("creator_balance", "0")
    creator_percent = info.get("creator_percent", "0.000000")

    if creator == "N/A" or not creator:
        return None, "N/A", "N/A", "UNKNOWN_NO_CREATOR"

    # Check creator balance from GoPlus
    try:
        bal = float(creator_balance)
    except (ValueError, TypeError):
        bal = 0.0

    try:
        pct = float(creator_percent)
    except (ValueError, TypeError):
        pct = 0.0

    if bal > 0 or pct > 0:
        return True, creator_balance, creator_percent, "TEAM_HOLDING"

    # Also check holders list for creator address
    holders = info.get("holders", [])
    creator_lower = creator.lower()
    for h in holders:
        if h.get("address", "").lower() == creator_lower:
            h_bal = float(h.get("balance", "0"))
            if h_bal > 0:
                return True, str(h_bal), h.get("percent", "0"), "TEAM_HOLDING"

    return False, "0", "0.000000", "TEAM_SOLD"


def main():
    print("=" * 60)
    print("Binance Web3 Creator Wallet Forensics — BSC Tokens")
    print("=" * 60)

    tokens = fetch_tokens()
    print(f"\n[1] Scanning {len(tokens)} tokens for creator forensics\n")

    results = []
    for i, (addr, meta) in enumerate(tokens.items()):
        symbol = meta.get("token_symbol", addr[:10])
        pool = meta.get("pool_name", "?")
        vol = meta.get("volume_24h_usd", 0)

        print(f"[{i+1}/{len(tokens)}] {symbol} ({pool}) vol=${vol:,.0f}")

        # Get GoPlus data
        info, err = fetch_goplus(addr)
        if err:
            print(f"  GoPlus error: {err}")
            results.append({
                "address": addr,
                "pool": pool,
                "volume_24h_usd": vol,
                "creator_address": "N/A",
                "status": "ERROR_Goplus",
                "error": err,
            })
            time.sleep(0.5)
            continue

        if not info:
            print(f"  No GoPlus data")
            results.append({
                "address": addr,
                "pool": pool,
                "volume_24h_usd": vol,
                "creator_address": "N/A",
                "status": "NO_DATA",
            })
            time.sleep(0.5)
            continue

        creator = info.get("creator_address", "N/A")
        still_holds, c_bal, c_pct, status = check_creator_holding(info, addr)

        # Get Binance token info for additional context
        binfo, berr = fetch_binance_token_info(addr)
        holders_count = "N/A"
        insider_pct = "N/A"
        if binfo:
            holders_count = binfo.get("holders", "N/A")
            insider_pct = binfo.get("insiderHoldingPercent", "N/A")

        entry = {
            "address": addr,
            "token_name": info.get("token_name", "?"),
            "token_symbol": info.get("token_symbol", "?"),
            "pool": pool,
            "volume_24h_usd": vol,
            "creator_address": creator,
            "creator_balance": c_bal,
            "creator_percent": c_pct,
            "creator_still_holds": still_holds,
            "status": status,
            "holders_count": holders_count,
            "insider_holding_percent": insider_pct,
        }

        status_icon = {
            "TEAM_SOLD": "SELL",
            "TEAM_HOLDING": "HOLD",
            "UNKNOWN_NO_CREATOR": "????",
        }.get(status, status)

        print(f"  Creator: {creator[:15]}... | Status: {status_icon} "
              f"bal={c_bal} pct={c_pct} holders={holders_count}")

        results.append(entry)
        time.sleep(0.5)

    # Sort: TEAM_SOLD first (most suspicious)
    status_order = {"TEAM_SOLD": 0, "UNKNOWN_NO_CREATOR": 1, "NO_DATA": 2, "ERROR_Goplus": 3, "TEAM_HOLDING": 4}
    results.sort(key=lambda x: status_order.get(x["status"], 99))

    OUTPUT.write_text(json.dumps(results, indent=2))
    print(f"\n[2] Saved {len(results)} results to {OUTPUT}")

    # Summary
    sold = [r for r in results if r["status"] == "TEAM_SOLD"]
    holding = [r for r in results if r["status"] == "TEAM_HOLDING"]
    unknown = [r for r in results if r["status"] in ("UNKNOWN_NO_CREATOR", "NO_DATA", "ERROR_Goplus")]

    print(f"\n{'=' * 60}")
    print(f"SUMMARY")
    print(f"  TEAM SOLD (creator dumped): {len(sold)}")
    print(f"  TEAM HOLDING:               {len(holding)}")
    print(f"  UNKNOWN/ERROR:              {len(unknown)}")

    if sold:
        print(f"\n  RED FLAG — Creator wallets that sold:")
        for r in sold:
            print(f"    {r.get('token_symbol','?'):>10s} pool={r['pool']} "
                  f"creator={r['creator_address'][:15]}... "
                  f"vol=${r['volume_24h_usd']:,.0f}")
    print("=" * 60)


if __name__ == "__main__":
    main()
