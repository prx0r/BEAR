"""Canonical backtest runner — wires extraction, outcomes, baselines, and source cards.

Run: cd /home/ubuntu/BEAR/astronomer && python3 run_backtest.py

This is the ONLY backtest entry point.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from schemas import MarketEvent, SemanticKind, CallState, SignalDirection
from backtest import (
    load_all_prices, run_backtest, save_outcomes,
    compute_source_cards, load_regime_timeline_cached
)
from metrics import compute_metrics, PerformanceMetrics, format_metrics_table, SourceReportCard
from baselines import evaluate_baselines, print_baselines


DATA_DIR = Path(__file__).parent / "data"
BACKTEST_DIR = DATA_DIR / "backtest"


def load_extracted_events() -> list[dict]:
    """Load extracted events from v2 extraction."""
    path = BACKTEST_DIR / "extracted_august_v2.json"
    if not path.exists():
        print(f"No events file: {path}")
        return []
    with open(path) as f:
        return json.load(f)


def raw_to_market_event(raw: dict) -> MarketEvent:
    """Convert raw extracted dict to canonical MarketEvent."""
    event = MarketEvent(
        event_id=raw.get("event_id", ""),
        post_id=raw.get("post_id", ""),
        author_id=raw.get("author_id", ""),
        author_handle=raw.get("author_handle", ""),
        published_at=raw.get("published_at", ""),
        semantic_kind=SemanticKind(raw.get("semantic_kind", "VIEW")),
        call_state=CallState(raw.get("call_state", "NONE")),
        asset=raw.get("asset"),
        entry_type=raw.get("entry_type"),
        entry_price=raw.get("entry_price"),
    )
    d = raw.get("direction")
    if d:
        try:
            event.direction = SignalDirection(d)
        except ValueError:
            pass
    return event


def load_existing_outcomes() -> list[dict]:
    """Load v2 outcomes if they exist."""
    path = BACKTEST_DIR / "outcomes_v2.json"
    if not path.exists():
        return []
    with open(path) as f:
        return json.load(f)


def group_by_author(outcomes: list[dict], events_raw: list[dict]) -> dict[str, list[dict]]:
    """Group outcomes by author handle."""
    # Build post_id → author mapping from raw events
    post_to_author = {}
    for raw in events_raw:
        post_id = raw.get("post_id", "")
        handle = raw.get("author_handle", "")
        if post_id and handle:
            post_to_author[post_id] = handle

    # Map event_id → author
    event_to_author = {}
    for raw in events_raw:
        event_id = raw.get("event_id", "")
        handle = raw.get("author_handle", "")
        if event_id and handle:
            event_to_author[event_id] = handle

    by_author = {}
    for o in outcomes:
        event_id = o.get("event_id", "")
        author = event_to_author.get(event_id, "unknown")
        if author not in by_author:
            by_author[author] = []
        by_author[author].append(o)

    return by_author


def compute_author_source_cards(by_author: dict[str, list[dict]],
                                 events_raw: list[dict]) -> dict[str, SourceReportCard]:
    """Compute source report cards per author."""
    # Count events per author from raw
    author_event_counts = {}
    for raw in events_raw:
        handle = raw.get("author_handle", "unknown")
        kind = raw.get("semantic_kind", "VIEW")
        if handle not in author_event_counts:
            author_event_counts[handle] = {"total": 0, "CALL": 0, "VIEW": 0,
                                            "OBSERVATION": 0, "INTERPRETATION": 0,
                                            "RETROSPECTIVE": 0}
        author_event_counts[handle]["total"] += 1
        if kind in author_event_counts[handle]:
            author_event_counts[handle][kind] += 1

    cards = {}
    for author, outcomes in by_author.items():
        # Separate CALL outcomes (tradeable) from VIEW outcomes (event study)
        call_outcomes = [o for o in outcomes
                         if o.get("trigger_status") != "NOT_TRIGGERED"]
        call_returns_4h = [o.get("return_4h") for o in call_outcomes
                           if o.get("return_4h") is not None]
        call_returns_24h = [o.get("return_24h") for o in call_outcomes
                            if o.get("return_24h") is not None]

        card = SourceReportCard(
            source_handle=author,
            total_posts=author_event_counts.get(author, {}).get("total", 0),
            calls=author_event_counts.get(author, {}).get("CALL", 0),
            views=author_event_counts.get(author, {}).get("VIEW", 0),
            observations=author_event_counts.get(author, {}).get("OBSERVATION", 0),
            interpretations=author_event_counts.get(author, {}).get("INTERPRETATION", 0),
            retrospectives=author_event_counts.get(author, {}).get("RETROSPECTIVE", 0),
            trade_call_n=len(call_returns_4h),
            view_n=len([o for o in outcomes if o.get("return_4h") is not None]),
            unresolved_asset_fraction=sum(1 for o in outcomes if not o.get("asset")) / max(len(outcomes), 1),
        )

        if call_returns_4h:
            card.trade_call_metrics = compute_metrics(call_returns_4h)

        # View signed returns (all outcomes including VIEW)
        all_returns_4h = [o.get("return_4h") for o in outcomes
                          if o.get("return_4h") is not None]
        all_returns_24h = [o.get("return_24h") for o in outcomes
                           if o.get("return_24h") is not None]
        if all_returns_4h:
            card.view_signed_return_4h = sum(all_returns_4h) / len(all_returns_4h)
        if all_returns_24h:
            card.view_signed_return_24h = sum(all_returns_24h) / len(all_returns_24h)

        # Regime distribution
        for o in outcomes:
            regime = o.get("btc_regime", "")
            if regime == "UP":
                card.regime_up_n += 1
            elif regime == "DOWN":
                card.regime_down_n += 1
            elif regime == "RANGE":
                card.regime_range_n += 1

        cards[author] = card

    return cards


def print_source_cards(cards: dict[str, SourceReportCard]):
    """Print source report cards."""
    print("\n" + "=" * 80)
    print("SOURCE REPORT CARDS")
    print("=" * 80)

    for author, card in sorted(cards.items()):
        print(f"\n--- @{author} ---")
        print(f"  Posts: {card.total_posts} | Events: {card.calls + card.views + card.observations + card.interpretations + card.retrospectives}")
        print(f"  Mix: {card.calls} CALL, {card.views} VIEW, {card.observations} OBS, "
              f"{card.interpretations} INTERP, {card.retrospectives} RETRO")

        if card.trade_call_metrics and card.trade_call_n > 0:
            m = card.trade_call_metrics
            print(f"  Trade calls: n={card.trade_call_n}")
            print(f"    Hit rate:  {m.hit_rate:.1%} (Bayesian: {m.bayesian_win_rate:.1%})")
            if m.wilson_ci_lo is not None:
                print(f"    Wilson CI: [{m.wilson_ci_lo:.1%}, {m.wilson_ci_hi:.1%}]")
            print(f"    Mean ret:  {m.mean_return * 100:.3f}% (4h)")
            print(f"    Sharpe:    {m.sharpe_ratio:.2f}")
            print(f"    EV/trade:  {m.expected_value * 100:.3f}%")
            print(f"    PF:        {m.profit_factor:.2f}")
        else:
            print(f"  Trade calls: n={card.trade_call_n} (insufficient)")

        print(f"  Views: n={card.view_n}, "
              f"avg 4h={card.view_signed_return_4h * 100:.3f}%, "
              f"avg 24h={card.view_signed_return_24h * 100:.3f}%")
        print(f"  Regime: UP={card.regime_up_n} DOWN={card.regime_down_n} RANGE={card.regime_range_n}")
        print(f"  Unresolved assets: {card.unresolved_asset_fraction:.1%}")


def main():
    """Run the full canonical backtest."""
    print("=" * 80)
    print("BEAR CANONICAL BACKTEST")
    print("=" * 80)

    # 1. Load raw extracted events
    raw_events = load_extracted_events()
    if not raw_events:
        print("No extracted events found. Run extractor first.")
        return

    print(f"\nLoaded {len(raw_events)} extracted events")

    # 2. Convert to MarketEvent objects
    events = [raw_to_market_event(r) for r in raw_events]

    # Stats
    by_kind = {}
    for e in events:
        k = e.semantic_kind.value
        by_kind[k] = by_kind.get(k, 0) + 1
    print(f"Events by kind: {by_kind}")

    with_asset = sum(1 for e in events if e.asset)
    without_asset = sum(1 for e in events if not e.asset)
    print(f"With asset: {with_asset} | Without (UNKNOWN): {without_asset}")

    # 3. Load prices and regime
    prices = load_all_prices()
    regime_timeline = load_regime_timeline_cached()
    print(f"Regime timeline: {len(regime_timeline)} entries")

    # 4. Run backtest
    print("\nRunning canonical backtest...")
    outcomes = run_backtest(events, prices, regime_timeline)
    print(f"Generated {len(outcomes)} outcomes (one per event × asset)")

    # Save outcomes
    save_outcomes(outcomes)

    # 5. Convert outcomes to dicts for analysis
    outcome_dicts = []
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
            "btc_regime": o.btc_regime,
            "btc_vol_state": o.btc_vol_state,
            "trigger_status": o.trigger_status,
        }
        outcome_dicts.append(d)

    # 6. Overall metrics
    all_returns_4h = [o.get("return_4h") for o in outcome_dicts
                      if o.get("return_4h") is not None]
    all_returns_24h = [o.get("return_24h") for o in outcome_dicts
                       if o.get("return_24h") is not None]

    if all_returns_4h:
        m4 = compute_metrics(all_returns_4h)
        print("\n" + format_metrics_table(m4, "ALL EVENTS — 4h returns (decimal: 0.00338 = 0.338%)"))
    if all_returns_24h:
        m24 = compute_metrics(all_returns_24h)
        print("\n" + format_metrics_table(m24, "ALL EVENTS — 24h returns"))

    # 7. By semantic kind
    for kind in ["CALL", "VIEW", "OBSERVATION", "INTERPRETATION"]:
        kind_returns = [o.get("return_4h") for o in outcome_dicts
                        if o.get("return_4h") is not None
                        and any(r.get("semantic_kind") == kind
                                for r in raw_events if r.get("event_id") == o.get("event_id"))]
        if kind_returns and len(kind_returns) >= 3:
            mk = compute_metrics(kind_returns)
            print(f"\n{format_metrics_table(mk, f'{kind} events — 4h')}")

    # 8. By regime
    for regime in ["UP", "DOWN", "RANGE"]:
        regime_returns = [o.get("return_4h") for o in outcome_dicts
                          if o.get("return_4h") is not None
                          and o.get("btc_regime") == regime]
        if regime_returns and len(regime_returns) >= 3:
            mr = compute_metrics(regime_returns)
            print(f"\n{format_metrics_table(mr, f'Regime={regime} — 4h')}")

    # 9. Baselines
    baselines = evaluate_baselines(outcome_dicts, horizon_hours=4)
    if baselines:
        print_baselines(baselines)

    # 10. Source report cards
    by_author = group_by_author(outcome_dicts, raw_events)
    cards = compute_author_source_cards(by_author, raw_events)
    print_source_cards(cards)

    # 11. Save source cards
    cards_data = {}
    for author, card in cards.items():
        cards_data[author] = {
            "source_handle": card.source_handle,
            "total_posts": card.total_posts,
            "calls": card.calls,
            "views": card.views,
            "observations": card.observations,
            "interpretations": card.interpretations,
            "retrospectives": card.retrospectives,
            "trade_call_n": card.trade_call_n,
            "unresolved_asset_fraction": round(card.unresolved_asset_fraction, 4),
            "regime_up_n": card.regime_up_n,
            "regime_down_n": card.regime_down_n,
            "regime_range_n": card.regime_range_n,
        }
        if card.trade_call_metrics:
            m = card.trade_call_metrics
            cards_data[author]["trade_call_4h"] = {
                "n": m.n,
                "hit_rate": round(m.hit_rate, 4),
                "bayesian_win_rate": round(m.bayesian_win_rate, 4),
                "mean_return": round(m.mean_return, 6),
                "median_return": round(m.median_return, 6),
                "sharpe": round(m.sharpe_ratio, 2),
                "profit_factor": round(m.profit_factor, 2),
                "expected_value": round(m.expected_value, 6),
            }

    cards_path = BACKTEST_DIR / "source_cards_v2.json"
    with open(cards_path, "w") as f:
        json.dump(cards_data, f, indent=2)
    print(f"\nSaved source cards to {cards_path}")

    print("\n" + "=" * 80)
    print("BACKTEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
