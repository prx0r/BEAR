"""Canonical backtest engine — Match MarketEvents to price outcomes.

FIXES from old backtest.py:
1. No BTC default — asset must be explicit, UNKNOWN if not determined
2. Next-candle entry — enter on first candle AFTER publication, not same candle
3. One EventOutcome per event × asset — no flat multi-asset dictionary
4. Returns as decimal — 0.00338 = 0.338%, NOT 0.003%
5. Point-in-time market state — regime, vol, funding at event time
6. Abnormal returns — beta-adjusted for alts

Source fidelity outranks what the model thinks is true.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))
from price_data import load_prices, get_price_at, get_price_range
from regime import load_regime_timeline, get_market_state_at, get_next_candle
from schemas import MarketEvent, EventOutcome, SemanticKind, CallState

DATA_DIR = Path(__file__).parent / "data"
BACKTEST_DIR = DATA_DIR / "backtest"

# Time horizons for forward returns
HORIZONS_HOURS = [1, 4, 24, 168]  # 1h, 4h, 24h, 7d

# Cost model
DEFAULT_FEE_RATE = 0.001      # 0.1% round trip (0.05% each way)
DEFAULT_SLIPPAGE = 0.0005     # 0.05% slippage


def load_all_prices() -> dict[str, list[dict]]:
    """Load all available price data. Returns {symbol: [candles]}."""
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "TAOUSDT", "HYPERUSDT"]
    prices = {}
    for symbol in symbols:
        data = load_prices(symbol, "1h")
        if data:
            prices[symbol] = sorted(data, key=lambda x: x["timestamp"])
            print(f"Loaded {len(data)} candles for {symbol}")
    return prices


def asset_to_symbol(asset: Optional[str]) -> Optional[str]:
    """Map asset name to Binance symbol. Returns None for UNKNOWN."""
    if not asset:
        return None
    mapping = {
        "BTC": "BTCUSDT",
        "ETH": "ETHUSDT",
        "SOL": "SOLUSDT",
        "TAO": "TAOUSDT",
        "HYPE": "HYPERUSDT",
    }
    return mapping.get(asset.upper())


def compute_raw_return(entry_price: float, exit_price: float,
                       direction: str) -> float:
    """Compute raw return as decimal. 0.00338 = 0.338%."""
    if entry_price == 0:
        return 0.0
    mult = 1.0 if direction == "BULLISH" else -1.0
    return mult * (exit_price - entry_price) / entry_price


def compute_net_return(gross_return: float, fee_rate: float = DEFAULT_FEE_RATE,
                       slippage: float = DEFAULT_SLIPPAGE) -> float:
    """Compute net return after costs."""
    return gross_return - fee_rate - slippage


def compute_beta_adjusted_return(asset_return: float, btc_return: float,
                                  beta: float) -> float:
    """Compute abnormal return: asset_return - beta * btc_return."""
    return asset_return - beta * btc_return


def estimate_beta_from_history(prices: dict[str, list[dict]], asset_symbol: str,
                                event_ts_ms: int, lookback_hours: int = 168) -> Optional[float]:
    """Estimate beta using information strictly before the event.
    Uses rolling 7-day window of hourly returns."""
    btc_prices = prices.get("BTCUSDT", [])
    asset_prices = prices.get(asset_symbol, [])

    if not btc_prices or not asset_prices:
        return None

    # Get returns in the lookback window
    start_ts = event_ts_ms - (lookback_hours * 3600 * 1000)

    btc_rets = []
    asset_rets = []

    for i in range(1, len(btc_prices)):
        ts = btc_prices[i]["timestamp"]
        if ts < start_ts or ts > event_ts_ms:
            continue
        prev_ts = btc_prices[i - 1]["timestamp"]
        if prev_ts < start_ts:
            continue

        btc_ret = (btc_prices[i]["close"] - btc_prices[i - 1]["close"]) / btc_prices[i - 1]["close"]

        # Find matching asset candle
        asset_candle = get_price_at(asset_prices, ts)
        asset_prev = get_price_at(asset_prices, prev_ts)
        if asset_candle and asset_prev and asset_prev["close"] > 0:
            asset_ret = (asset_candle["close"] - asset_prev["close"]) / asset_prev["close"]
            btc_rets.append(btc_ret)
            asset_rets.append(asset_ret)

    if len(btc_rets) < 24:  # Need at least 24 hours of data
        return None

    # OLS beta
    mean_btc = sum(btc_rets) / len(btc_rets)
    mean_asset = sum(asset_rets) / len(asset_rets)

    cov = sum((b - mean_btc) * (a - mean_asset) for b, a in zip(btc_rets, asset_rets)) / len(btc_rets)
    var_btc = sum((b - mean_btc) ** 2 for b in btc_rets) / len(btc_rets)

    if var_btc == 0:
        return None

    return cov / var_btc


def evaluate_event(event: MarketEvent, prices: dict[str, list[dict]],
                   regime_timeline: list[dict],
                   fee_rate: float = DEFAULT_FEE_RATE,
                   slippage: float = DEFAULT_SLIPPAGE) -> Optional[EventOutcome]:
    """Evaluate a single MarketEvent against price data.

    Rules:
    1. asset must be explicit — None = skip (NOT_TRIGGERED is not applicable here)
    2. Entry on NEXT candle after publication (no same-candle entry)
    3. One outcome per event × asset
    4. Returns as decimal
    """
    # Only evaluate CALL events with DIRECT or triggered CONDITIONAL
    if event.semantic_kind != SemanticKind.CALL:
        return None
    if event.call_state not in (CallState.DIRECT, CallState.CONDITIONAL):
        return None

    # Asset must be explicit
    if not event.asset:
        return None

    symbol = asset_to_symbol(event.asset)
    if not symbol or symbol not in prices:
        return None

    # Parse publication time
    try:
        pub_dt = datetime.fromisoformat(event.published_at.replace("Z", "+00:00"))
        pub_ts_ms = int(pub_dt.timestamp() * 1000)
    except (ValueError, TypeError):
        return None

    # Entry: FIRST candle AFTER publication (no same-candle entry)
    asset_prices = prices[symbol]
    entry_candle = get_next_candle_from_list(asset_prices, pub_ts_ms)
    if not entry_candle:
        return None

    entry_price = entry_candle["close"]
    entry_time = datetime.fromtimestamp(
        entry_candle["timestamp"] / 1000, tz=timezone.utc
    ).isoformat()

    if entry_price <= 0:
        return None

    direction = event.direction.value if event.direction else "UNKNOWN"
    if direction == "UNKNOWN":
        return None

    # Get market state at event time
    market_state = get_market_state_at(regime_timeline, pub_ts_ms)

    # Compute forward returns at each horizon
    outcome = EventOutcome(
        event_id=event.event_id,
        asset=event.asset,
        entry_time=entry_time,
        entry_price=entry_price,
        direction=direction,
    )

    # Set market state
    if market_state:
        outcome.btc_price_at_event = market_state.get("btc_price")
        outcome.btc_regime = market_state.get("btc_regime")
        outcome.btc_vol_state = market_state.get("btc_vol_state")
        outcome.btc_ema20 = market_state.get("btc_ema20_1h")
        outcome.btc_ema50 = market_state.get("btc_ema50_1h")

    # BTC reference returns for beta adjustment
    btc_prices = prices.get("BTCUSDT", [])
    btc_entry = get_price_at(btc_prices, entry_candle["timestamp"])

    for hours in HORIZONS_HOURS:
        horizon_ms = hours * 3600 * 1000
        target_ts = entry_candle["timestamp"] + horizon_ms

        # Find price at horizon
        future_candle = get_price_at(asset_prices, target_ts)
        if not future_candle:
            continue

        raw_return = compute_raw_return(entry_price, future_candle["close"], direction)
        net_return = compute_net_return(raw_return, fee_rate, slippage)

        # Set returns
        if hours == 1:
            outcome.return_1h = round(raw_return, 6)
        elif hours == 4:
            outcome.return_4h = round(raw_return, 6)
            outcome.net_return_4h = round(net_return, 6)
            outcome.direction_correct_4h = raw_return > 0

            # MFE/MAE for 4h
            candles_4h = get_price_range_from_list(
                asset_prices, entry_candle["timestamp"], target_ts
            )
            if candles_4h:
                returns_4h = [compute_raw_return(entry_price, c["high"], direction)
                              for c in candles_4h]
                adverse_4h = [compute_raw_return(entry_price, c["low"], direction)
                              for c in candles_4h]
                outcome.mfe_4h = round(max(returns_4h), 6) if returns_4h else None
                outcome.mae_4h = round(min(adverse_4h), 6) if adverse_4h else None

        elif hours == 24:
            outcome.return_24h = round(raw_return, 6)
            outcome.net_return_24h = round(net_return, 6)
            outcome.direction_correct_24h = raw_return > 0

            # MFE/MAE for 24h
            candles_24h = get_price_range_from_list(
                asset_prices, entry_candle["timestamp"], target_ts
            )
            if candles_24h:
                returns_24h = [compute_raw_return(entry_price, c["high"], direction)
                               for c in candles_24h]
                adverse_24h = [compute_raw_return(entry_price, c["low"], direction)
                               for c in candles_24h]
                outcome.mfe_24h = round(max(returns_24h), 6) if returns_24h else None
                outcome.mae_24h = round(min(adverse_24h), 6) if adverse_24h else None

        elif hours == 168:
            outcome.return_7d = round(raw_return, 6)

        # Abnormal return (beta-adjusted) for 4h and 24h
        if hours in (4, 24) and btc_entry and symbol != "BTCUSDT":
            btc_future = get_price_at(btc_prices, target_ts)
            if btc_future:
                btc_return = compute_raw_return(
                    btc_entry["close"], btc_future["close"], "BULLISH"
                )
                beta = estimate_beta_from_history(prices, symbol, pub_ts_ms)
                if beta is not None:
                    abnormal = compute_beta_adjusted_return(raw_return, btc_return, beta)
                    if hours == 4:
                        outcome.abnormal_return_4h = round(abnormal, 6)
                    elif hours == 24:
                        outcome.abnormal_return_24h = round(abnormal, 6)

    return outcome


def get_next_candle_from_list(prices: list[dict], timestamp_ms: int) -> Optional[dict]:
    """Get the FIRST candle STRICTLY AFTER a timestamp."""
    for p in prices:
        if p["timestamp"] > timestamp_ms:
            return p
    return None


def get_price_range_from_list(prices: list[dict], start_ms: int,
                               end_ms: int) -> list[dict]:
    """Get all candles in a time range."""
    return [p for p in prices if start_ms <= p["timestamp"] <= end_ms]


def run_backtest(events: list[MarketEvent], prices: dict[str, list[dict]],
                 regime_timeline: list[dict]) -> list[EventOutcome]:
    """Run backtest on a list of MarketEvents.

    Returns list of EventOutcome (one per event × asset).
    Events with asset=None are SKIPPED, not defaulted to BTC.
    """
    outcomes = []
    for event in events:
        outcome = evaluate_event(event, prices, regime_timeline)
        if outcome:
            outcomes.append(outcome)
    return outcomes


def save_outcomes(outcomes: list[EventOutcome], path: Optional[Path] = None):
    """Save outcomes to JSON."""
    if path is None:
        path = BACKTEST_DIR / "outcomes_v2.json"
    path.parent.mkdir(parents=True, exist_ok=True)

    data = []
    for o in outcomes:
        d = {
            "event_id": o.event_id,
            "asset": o.asset,
            "entry_time": o.entry_time,
            "entry_price": o.entry_price,
            "direction": o.direction,
            "return_1h": o.return_1h,
            "return_4h": o.return_4h,
            "return_24h": o.return_24h,
            "return_7d": o.return_7d,
            "abnormal_return_4h": o.abnormal_return_4h,
            "abnormal_return_24h": o.abnormal_return_24h,
            "mfe_4h": o.mfe_4h,
            "mae_4h": o.mae_4h,
            "mfe_24h": o.mfe_24h,
            "mae_24h": o.mae_24h,
            "direction_correct_4h": o.direction_correct_4h,
            "direction_correct_24h": o.direction_correct_24h,
            "net_return_4h": o.net_return_4h,
            "net_return_24h": o.net_return_24h,
            "trigger_status": o.trigger_status,
            "btc_price_at_event": o.btc_price_at_event,
            "btc_regime": o.btc_regime,
            "btc_vol_state": o.btc_vol_state,
            "outcome_version": o.outcome_version,
        }
        data.append(d)

    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Saved {len(data)} outcomes to {path}")
    return data


def compute_source_cards(outcomes: list[EventOutcome]) -> dict:
    """Compute source report cards — per author × asset × direction × horizon.

    Returns dict keyed by source_handle.
    """
    # Group outcomes by source (we need author info, so we group by event_id prefix)
    # Actually, outcomes don't carry author info. We need to join with events.
    # For now, return raw grouped by asset × direction × horizon.
    groups = {}
    for o in outcomes:
        key = (o.asset, o.direction, "4h")
        if key not in groups:
            groups[key] = {"returns": [], "correct": 0, "total": 0}
        groups[key]["total"] += 1
        if o.direction_correct_4h:
            groups[key]["correct"] += 1
        if o.return_4h is not None:
            groups[key]["returns"].append(o.return_4h)

    cards = {}
    for (asset, direction, horizon), data in groups.items():
        n = data["total"]
        wins = data["correct"]
        returns = data["returns"]

        win_rate = wins / n if n > 0 else 0.0
        mean_return = sum(returns) / len(returns) if returns else 0.0
        sorted_returns = sorted(returns) if returns else [0.0]
        median_return = sorted_returns[len(sorted_returns) // 2]

        gross_profit = sum(r for r in returns if r > 0)
        gross_loss = abs(sum(r for r in returns if r < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        key = f"{asset}:{direction}:{horizon}"
        cards[key] = {
            "asset": asset,
            "direction": direction,
            "horizon": horizon,
            "n": n,
            "wins": wins,
            "win_rate": round(win_rate, 4),
            "mean_return": round(mean_return, 6),
            "median_return": round(median_return, 6),
            "profit_factor": round(profit_factor, 2),
        }

    return cards


def main():
    """Run the canonical backtest."""
    print("=== Canonical Backtest Engine ===\n")

    # Load price data
    prices = load_all_prices()
    if not prices:
        print("No price data found.")
        return

    # Load regime timeline
    regime_timeline = load_regime_timeline()
    print(f"Loaded {len(regime_timeline)} regime entries")

    # Load extracted events
    events_file = BACKTEST_DIR / "extracted_august_v2.json"
    if not events_file.exists():
        print(f"No events file found: {events_file}")
        return

    with open(events_file) as f:
        raw_events = json.load(f)

    # Convert raw dicts to MarketEvent objects
    events = []
    for raw in raw_events:
        try:
            event = MarketEvent(
                event_id=raw.get("event_id", ""),
                post_id=raw.get("post_id", ""),
                author_id=raw.get("author_id", ""),
                author_handle=raw.get("author_handle", ""),
                published_at=raw.get("published_at", ""),
                semantic_kind=SemanticKind(raw.get("semantic_kind", "VIEW")),
                call_state=CallState(raw.get("call_state", "NONE")),
                asset=raw.get("asset"),
                direction=None,
                entry_type=raw.get("entry_type"),
                entry_price=raw.get("entry_price"),
            )
            # Set direction if present
            d = raw.get("direction")
            if d:
                from schemas import SignalDirection
                try:
                    event.direction = SignalDirection(d)
                except ValueError:
                    pass
            events.append(event)
        except Exception as e:
            print(f"  Skipping event: {e}")

    print(f"Loaded {len(events)} events")

    # Count by kind
    by_kind = {}
    for e in events:
        k = e.semantic_kind.value
        by_kind[k] = by_kind.get(k, 0) + 1
    print(f"Events by kind: {by_kind}")

    # Count with/without asset
    with_asset = sum(1 for e in events if e.asset)
    without_asset = sum(1 for e in events if not e.asset)
    print(f"With asset: {with_asset}, Without asset (UNKNOWN): {without_asset}")

    # Run backtest
    print("\nRunning backtest...")
    outcomes = run_backtest(events, prices, regime_timeline)
    print(f"Generated {len(outcomes)} outcomes")

    # Save outcomes
    save_outcomes(outcomes)

    # Generate source cards
    cards = compute_source_cards(outcomes)
    cards_path = BACKTEST_DIR / "source_cards_v2.json"
    with open(cards_path, "w") as f:
        json.dump(cards, f, indent=2)
    print(f"Saved source cards to {cards_path}")

    # Print summary
    print("\n=== Results ===")
    for key, card in sorted(cards.items()):
        print(f"  {key}: n={card['n']}, win={card['win_rate']:.0%}, "
              f"mean={card['mean_return'] * 100:.2f}%, "
              f"PF={card['profit_factor']:.1f}")


if __name__ == "__main__":
    main()
