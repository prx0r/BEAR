"""Historical price data fetcher — Binance public API (free)."""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

DATA_DIR = Path(__file__).parent / "data" / "prices"
DATA_DIR.mkdir(exist_ok=True)

BINANCE_BASE = "https://api.binance.com/api/v3"


def get_klines(symbol: str, interval: str = "1h", limit: int = 1000, start_time: int = None, end_time: int = None) -> list:
    """Fetch klines from Binance."""
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    if start_time:
        params["startTime"] = start_time
    if end_time:
        params["endTime"] = end_time

    resp = httpx.get(f"{BINANCE_BASE}/klines", params=params, timeout=15.0)
    resp.raise_for_status()
    return resp.json()


def fetch_full_history(symbol: str, interval: str = "1h", start_date: str = "2024-01-01") -> list:
    """Fetch full history from start_date to now."""
    start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)
    end_ts = int(datetime.now(timezone.utc).timestamp() * 1000)

    all_klines = []
    current_start = start_ts

    while current_start < end_ts:
        klines = get_klines(symbol, interval, 1000, current_start, end_ts)
        if not klines:
            break
        all_klines.extend(klines)
        current_start = klines[-1][0] + 1  # next ms after last kline
        time.sleep(0.1)  # rate limit courtesy

    return all_klines


def parse_klines(raw: list) -> list:
    """Parse raw klines into clean format."""
    parsed = []
    for k in raw:
        parsed.append({
            "timestamp": k[0],
            "open": float(k[1]),
            "high": float(k[2]),
            "low": float(k[3]),
            "close": float(k[4]),
            "volume": float(k[5]),
            "close_time": k[6],
        })
    return parsed


def save_prices(symbol: str, interval: str, data: list):
    """Save price data."""
    out_path = DATA_DIR / f"{symbol}_{interval}.json"
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Saved {len(data)} candles to {out_path}")


def load_prices(symbol: str, interval: str = "1h") -> list:
    """Load price data."""
    path = DATA_DIR / f"{symbol}_{interval}.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return []


def get_price_at(prices: list, timestamp_ms: int) -> dict:
    """Get the candle at or just after a timestamp."""
    for p in prices:
        if p["timestamp"] >= timestamp_ms:
            return p
    return None


def get_price_range(prices: list, start_ms: int, end_ms: int) -> list:
    """Get all candles in a time range."""
    return [p for p in prices if start_ms <= p["timestamp"] <= end_ms]


def main():
    """Fetch price data for major assets."""
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "TAOUSDT"]
    interval = "1h"
    start_date = "2024-01-01"

    for symbol in symbols:
        print(f"Fetching {symbol}...")
        raw = fetch_full_history(symbol, interval, start_date)
        parsed = parse_klines(raw)
        save_prices(symbol, interval, parsed)
        print(f"  Got {len(parsed)} candles from {start_date}")

    print("\nDone.")


if __name__ == "__main__":
    main()
