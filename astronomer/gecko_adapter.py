"""GeckoTerminal price adapter for on-chain meme tokens.

Fetches pool OHLCV data from GeckoTerminal public API.
Supports Solana, EVM chains.

Usage:
    adapter = GeckoTerminalAdapter()
    ohlcv = adapter.get_ohlcv("solana", "contract_address", "2026-08-01", "2026-08-31")
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx

BASE_URL = "https://api.geckoterminal.com/api/v2"
CACHE_DIR = Path(__file__).parent / "data" / "prices" / "onchain"


class GeckoTerminalAdapter:
    """Fetch on-chain OHLCV from GeckoTerminal."""

    def __init__(self, cache_dir: Path = CACHE_DIR):
        self.cache_dir = cache_dir
        self.client = httpx.Client(timeout=15.0, headers={
            "Accept": "application/json",
        })
        self._last_request = 0.0

    def _rate_limit(self):
        """Respect ~10 req/min public limit."""
        elapsed = time.time() - self._last_request
        if elapsed < 6.0:  # 6 seconds between requests
            time.sleep(6.0 - elapsed)
        self._last_request = time.time()

    def _cache_path(self, chain: str, contract: str, interval: str) -> Path:
        """Get cache file path."""
        return self.cache_dir / chain / contract / f"{interval}.json"

    def _load_cache(self, chain: str, contract: str, interval: str) -> Optional[list]:
        """Load cached OHLCV."""
        path = self._cache_path(chain, contract, interval)
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return None

    def _save_cache(self, chain: str, contract: str, interval: str, data: list):
        """Save OHLCV to cache."""
        path = self._cache_path(chain, contract, interval)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def find_pool(self, chain: str, contract: str) -> Optional[dict]:
        """Find the highest-liquidity pool for a token.

        Returns pool info or None.
        """
        self._rate_limit()

        try:
            resp = self.client.get(
                f"{BASE_URL}/networks/{chain}/tokens/{contract}/pools",
            )
            if resp.status_code != 200:
                print(f"  GeckoTerminal pool search failed: {resp.status_code}")
                return None

            data = resp.json()
            pools = data.get("data", [])

            if not pools:
                print(f"  No pools found for {contract} on {chain}")
                return None

            # Sort by liquidity (reserve_in_usd)
            best = None
            best_liquidity = 0
            for pool in pools:
                attrs = pool.get("attributes", {})
                liquidity = float(attrs.get("reserve_in_usd", 0))
                if liquidity > best_liquidity:
                    best_liquidity = liquidity
                    best = {
                        "pool_address": attrs.get("address", ""),
                        "dex_name": attrs.get("dex_id", ""),
                        "base_token": attrs.get("base_token_address", ""),
                        "quote_token": attrs.get("quote_token_address", ""),
                        "liquidity_usd": liquidity,
                        "url": attrs.get("url", ""),
                    }

            return best

        except Exception as e:
            print(f"  GeckoTerminal pool search error: {e}")
            return None

    def get_ohlcv(self, chain: str, pool_address: str, interval: str = "1h",
                  after: Optional[str] = None, before: Optional[str] = None) -> list[dict]:
        """Fetch OHLCV for a pool.

        Args:
            chain: Network (solana, ethereum, etc.)
            pool_address: Pool contract address
            interval: OHLCV interval (1h, 4h, 1d)
            after: ISO date string for start
            before: ISO date string for end

        Returns:
            List of {timestamp, open, high, low, close, volume}
        """
        # Check cache first
        cached = self._load_cache(chain, pool_address, interval)
        if cached:
            print(f"  Loaded {len(cached)} cached candles for {pool_address[:8]}...")
            return cached

        self._rate_limit()

        try:
            # GeckoTerminal OHLCV endpoint
            params = {"aggregate": "1"}  # 1 unit of the interval
            if after:
                dt = datetime.fromisoformat(after.replace("Z", "+00:00"))
                params["after"] = int(dt.timestamp())
            if before:
                dt = datetime.fromisoformat(before.replace("Z", "+00:00"))
                params["before"] = int(dt.timestamp())

            resp = self.client.get(
                f"{BASE_URL}/networks/{chain}/pools/{pool_address}/ohlcv/{interval}",
                params=params,
            )

            if resp.status_code != 200:
                print(f"  GeckoTerminal OHLCV failed: {resp.status_code}")
                return []

            data = resp.json()
            ohlcv_list = data.get("data", {}).get("attributes", {}).get("ohlcv_list", [])

            # Convert to standard format
            candles = []
            for item in ohlcv_list:
                # GeckoTerminal returns: [timestamp, open, high, low, close, volume]
                if len(item) >= 6:
                    candles.append({
                        "timestamp": item[0] * 1000,  # Convert to ms
                        "open": float(item[1]),
                        "high": float(item[2]),
                        "low": float(item[3]),
                        "close": float(item[4]),
                        "volume": float(item[5]),
                    })

            # Sort by timestamp
            candles.sort(key=lambda x: x["timestamp"])

            # Cache
            if candles:
                self._save_cache(chain, pool_address, interval, candles)

            print(f"  Fetched {len(candles)} candles for {pool_address[:8]}...")
            return candles

        except Exception as e:
            print(f"  GeckoTerminal OHLCV error: {e}")
            return []

    def resolve_and_fetch(self, chain: str, contract: str,
                          after: str, before: str) -> dict:
        """Full resolution: find pool, fetch OHLCV.

        Returns:
            {
                "pool": pool_info,
                "ohlcv": [...candles...],
                "status": "ok" | "no_pool" | "no_data" | "error"
            }
        """
        pool = self.find_pool(chain, contract)
        if not pool:
            return {"pool": None, "ohlcv": [], "status": "no_pool"}

        ohlcv = self.get_ohlcv(chain, pool["pool_address"], "1h", after, before)
        if not ohlcv:
            return {"pool": pool, "ohlcv": [], "status": "no_data"}

        return {"pool": pool, "ohlcv": ohlcv, "status": "ok"}

    def close(self):
        """Close the HTTP client."""
        self.client.close()


def parse_twitter_date(s: str) -> Optional[str]:
    """Parse Twitter date format to ISO."""
    if not s:
        return None
    try:
        dt = datetime.strptime(s, "%a %b %d %H:%M:%S %z %Y")
        return dt.isoformat()
    except:
        return None
