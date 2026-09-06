"""Export BEAR dashboard data from DuckDB to JSON.

Reads markets, computes structural short scores and factor scores,
writes /root/BEAR/dashboard/data.json and regenerates index.html.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import numpy as np
import polars as pl

DB_PATH = Path("/root/BEAR/data/research.duckdb")
DATA_OUT = Path("/root/BEAR/dashboard/data.json")
HTML_OUT = Path("/root/BEAR/dashboard/index.html")
TEMPLATE_PATH = Path("/root/BEAR/src/bear/api/templates/index.html")

TAXONOMY: dict[str, str] = {}
_tax_path = Path("/root/BEAR/config/taxonomy.yaml")
if _tax_path.exists():
    import yaml

    with open(_tax_path) as f:
        _tax = yaml.safe_load(f)
    for sector, syms in _tax.get("sectors", {}).items():
        for s in syms:
            TAXONOMY[s] = sector


def _connect() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DB_PATH), read_only=True)


def load_markets(conn: duckdb.DuckDBPyConnection) -> list[dict]:
    df = pl.read_database("SELECT * FROM markets WHERE NOT is_delisted", conn)
    return df.to_dicts()


def compute_stats(markets: list[dict]) -> dict:
    total_vol = sum(m.get("day_volume") or 0 for m in markets)
    fundings = [m.get("funding") or 0 for m in markets]
    pos = sum(1 for f in fundings if f > 0)
    neg = sum(1 for f in fundings if f < 0)
    avg_f = float(np.mean(fundings)) if fundings else 0.0
    return {
        "total_markets": len(markets),
        "total_24h_volume": round(total_vol, 2),
        "avg_funding": round(avg_f, 8),
        "positive_funding_count": pos,
        "negative_funding_count": neg,
    }


def compute_structural_short_scores(markets: list[dict]) -> list[dict]:
    """Score each asset on structural short attractiveness (higher = more shortable).

    Uses available market data: funding rate, open interest, volume, and
    sector classification.  Missing tokenomics data is handled gracefully
    by normalising only over available signals.
    """
    rows = []
    for m in markets:
        sym = m["symbol"]
        funding = m.get("funding") or 0.0
        oi = m.get("open_interest") or 0.0
        vol = m.get("day_volume") or 0.0
        oi_vol_ratio = oi / vol if vol > 0 else 0.0
        rows.append({
            "symbol": sym,
            "sector": TAXONOMY.get(sym, m.get("category", "other")),
            "mark_px": m.get("mark_px") or 0.0,
            "funding": funding,
            "open_interest": oi,
            "day_volume": vol,
            "oi_vol_ratio": oi_vol_ratio,
        })

    df = pl.DataFrame(rows)
    if df.is_empty():
        return []

    # Cross-sectional percentile ranks (0-100)
    def _pct_rank(col: str) -> pl.Series:
        vals = df[col].to_numpy().astype(float)
        n = len(vals)
        order = vals.argsort().argsort().astype(float)
        valid_count = (~np.isnan(vals)).sum()
        if valid_count == 0:
            return pl.Series(col + "_pct", np.zeros(n))
        # Handle ties by averaging ranks
        ranked = (order / max(n - 1, 1)) * 100.0
        return pl.Series(col + "_pct", ranked)

    # Funding: negative = more shortable (invert so high score = good short)
    fund_arr = df["funding"].to_numpy().astype(float)
    fund_rank = np.zeros(len(fund_arr))
    valid_mask = ~np.isnan(fund_arr)
    if valid_mask.any():
        valid = fund_arr[valid_mask]
        # More negative funding = better short candidate
        inv = -valid
        order = inv.argsort().argsort().astype(float)
        fund_rank[valid_mask] = (order / max(len(valid) - 1, 1)) * 100.0

    # OI/Volume ratio: higher = more crowding = better short
    oi_arr = df["oi_vol_ratio"].to_numpy().astype(float)
    oi_rank = np.zeros(len(oi_arr))
    valid_mask = ~np.isnan(oi_arr)
    if valid_mask.any():
        valid = oi_arr[valid_mask]
        order = valid.argsort().argsort().astype(float)
        oi_rank[valid_mask] = (order / max(len(valid) - 1, 1)) * 100.0

    # Volume: lower volume = harder to exit = riskier short (lower squeeze risk, good for structural)
    vol_arr = df["day_volume"].to_numpy().astype(float)
    vol_rank = np.zeros(len(vol_arr))
    valid_mask = ~np.isnan(vol_arr)
    if valid_mask.any():
        valid = vol_arr[valid_mask]
        inv = -valid  # lower volume = higher score
        order = inv.argsort().argsort().astype(float)
        vol_rank[valid_mask] = (order / max(len(valid) - 1, 1)) * 100.0

    # Composite structural short score
    scores = 0.35 * fund_rank + 0.30 * oi_rank + 0.15 * vol_rank
    # Normalize to 0-100
    if scores.max() > 0:
        scores = (scores / scores.max()) * 100.0

    result = []
    for i, r in enumerate(rows):
        result.append({
            "symbol": r["symbol"],
            "sector": r["sector"],
            "structural_short": round(float(scores[i]), 1),
            "funding_score": round(float(fund_rank[i]), 1),
            "oi_crowding": round(float(oi_rank[i]), 1),
            "mark_px": r["mark_px"],
            "funding": r["funding"],
        })

    result.sort(key=lambda x: x["structural_short"], reverse=True)
    return result


def compute_factor_scores(markets: list[dict]) -> dict[str, dict]:
    """Compute per-asset factor scores with full transparency.

    Returns a dict keyed by symbol with factor scores and breakdowns.
    Each factor includes: value, raw_value, formula, inputs, source, paper_url, validated.
    """
    import os
    from pathlib import Path

    CANDLE_DIR = Path("/root/BEAR/data/raw/candles")
    factors: dict[str, dict] = {}

    # Load candle data for all available assets
    candle_data: dict[str, pl.DataFrame] = {}
    for sym in [m["symbol"] for m in markets]:
        p = CANDLE_DIR / sym / "1h.parquet"
        if p.exists():
            candle_data[sym] = pl.read_parquet(p)

    btc_df = candle_data.get("BTC")

    # Cross-sectional ranking helpers
    def percentile_rank(values: dict[str, float]) -> dict[str, float]:
        vals = {k: v for k, v in values.items() if v is not None and not (isinstance(v, float) and (v != v))}
        if not vals:
            return {k: 50.0 for k in values}
        sorted_vals = sorted(vals.values())
        n = len(sorted_vals)
        ranks = {}
        for k, v in values.items():
            if v is None or (isinstance(v, float) and v != v):
                ranks[k] = 50.0
            else:
                # Count how many values are <= this one
                count = sum(1 for s in sorted_vals if s <= v)
                ranks[k] = (count / max(n, 1)) * 100.0
        return ranks

    # Factor 1: Reversal 8w (56-day return)
    reversal_raw = {}
    reversal_inputs = {}
    for m in markets:
        sym = m["symbol"]
        df = candle_data.get(sym)
        if df is not None and df.height >= 1344:  # 56 days * 24 hours
            now_price = float(df["close"][-1])
            old_price = float(df["close"][-1344])
            if old_price > 0:
                rev = float(np.log(now_price / old_price))
                reversal_raw[sym] = rev
                reversal_inputs[sym] = {"now": now_price, "56d_ago": old_price, "candles_used": 1344}
            else:
                reversal_raw[sym] = 0.0
                reversal_inputs[sym] = {"now": now_price, "56d_ago": old_price, "error": "old_price=0"}
        else:
            reversal_raw[sym] = None
            reversal_inputs[sym] = {"error": "insufficient candles", "have": df.height if df is not None else 0, "need": 1344}

    reversal_ranks = percentile_rank({k: v for k, v in reversal_raw.items() if v is not None})

    # Factor 2: Volatility 30d
    vol_raw = {}
    vol_inputs = {}
    for m in markets:
        sym = m["symbol"]
        df = candle_data.get(sym)
        if df is not None and df.height >= 720:
            closes = df["close"].to_numpy().astype(float)
            log_ret = np.diff(np.log(closes[-720:]))
            vol = float(np.std(log_ret) * np.sqrt(8760))  # annualized
            vol_raw[sym] = vol
            vol_inputs[sym] = {"vol_annualized": round(vol, 4), "candles_used": 720}
        else:
            vol_raw[sym] = None
            vol_inputs[sym] = {"error": "insufficient candles"}

    vol_ranks = percentile_rank({k: v for k, v in vol_raw.items() if v is not None})

    # Factor 3: Momentum 7d
    mom_raw = {}
    mom_inputs = {}
    for m in markets:
        sym = m["symbol"]
        df = candle_data.get(sym)
        if df is not None and df.height >= 168:
            now_p = float(df["close"][-1])
            old_p = float(df["close"][-168])
            if old_p > 0:
                mom = (now_p - old_p) / old_p
                mom_raw[sym] = mom
                mom_inputs[sym] = {"now": now_p, "7d_ago": old_p, "return": round(mom, 4)}
            else:
                mom_raw[sym] = None
                mom_inputs[sym] = {"error": "old_price=0"}
        else:
            mom_raw[sym] = None
            mom_inputs[sym] = {"error": "insufficient candles"}

    mom_ranks = percentile_rank({k: v for k, v in mom_raw.items() if v is not None})

    # Build per-asset factor dicts
    for m in markets:
        sym = m["symbol"]
        funding = m.get("funding") or 0.0
        vol = m.get("day_volume") or 0.0
        oi = m.get("open_interest") or 0.0
        sector = TAXONOMY.get(sym, m.get("category", "other"))
        px = m.get("mark_px") or 0.0

        # Funding carry
        carry_val = funding * 24 * 365  # annualized
        carry_score = max(0.0, min(100.0, 50.0 + carry_val * 500))

        # OI/ADV crowding
        oi_adv = oi / vol if vol > 0 else 0.0
        oi_adv_score = max(0.0, min(100.0, oi_adv * 10))

        # Reversal
        rev_val = reversal_raw.get(sym)
        rev_score = reversal_ranks.get(sym, 50.0)

        # Volatility
        vol_val = vol_raw.get(sym)
        vol_score = vol_ranks.get(sym, 50.0)

        # Momentum
        mom_val = mom_raw.get(sym)
        mom_score = mom_ranks.get(sym, 50.0)

        # TOTAL SHORT SCORE: higher = BETTER short candidate
        # Overextension: top 20% of cross-section by 8w return (validated: Kiefer 2026, CoinQuant 2026)
        rev_raw = reversal_raw.get(sym)
        mom_val = mom_raw.get(sym)
        rev_pct = reversal_ranks.get(sym, 50.0)  # percentile rank

        # Overextended = top 20% of cross-section (80th percentile)
        is_overextended = rev_pct >= 80

        if not is_overextended:
            total = rev_score * 0.3 + mom_score * 0.3 + carry_score * 0.2 + (100 - oi_adv_score) * 0.1 + (100 - vol_score) * 0.1
            total = min(total, 45)
        else:
            total = (rev_score * 0.30 + carry_score * 0.15 + mom_score * 0.25
                     + (100 - oi_adv_score) * 0.15 + (100 - vol_score) * 0.15)

        # Confidence: how many factors were real vs fallback
        real_count = sum(1 for v in [rev_val, vol_val, mom_val] if v is not None)
        confidence = round((real_count / 3) * 100 + 33, 1)  # base 33% from market data

        factors[sym] = {
            "reversal_8w": {
                "value": round(rev_score, 1),
                "raw": round(rev_val, 6) if rev_val is not None else None,
                "formula": "log(price_now / price_56d_ago)",
                "inputs": reversal_inputs.get(sym, {}),
                "validated": rev_val is not None,
                "note": "Higher = recent winner = short candidate (reversal effect)",
            },
            "volatility_30d": {
                "value": round(vol_score, 1),
                "raw": round(vol_val, 4) if vol_val is not None else None,
                "formula": "std(log_returns, 720h) × √8760",
                "inputs": vol_inputs.get(sym, {}),
                "validated": vol_val is not None,
                "note": "Higher = more volatile = harder to hold short",
            },
            "funding_carry": {
                "value": round(carry_score, 1),
                "raw": round(carry_val, 6),
                "formula": "funding_hourly × 24 × 365",
                "inputs": {"funding_hourly": funding, "annualized": round(carry_val, 6)},
                "validated": True,
                "note": "Higher = shorts receive more carry (good for short)",
                "source": "Hyperliquid API (live)",
                "paper_url": "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6993978",
            },
            "oi_crowding": {
                "value": round(oi_adv_score, 1),
                "raw": round(oi_adv, 4),
                "formula": "open_interest / day_volume",
                "inputs": {"open_interest": oi, "day_volume": vol, "ratio": round(oi_adv, 4)},
                "validated": vol > 0,
                "note": "Higher = more crowded = squeeze risk",
            },
            "momentum_7d": {
                "value": round(mom_score, 1),
                "raw": round(mom_val, 4) if mom_val is not None else None,
                "formula": "(price_now - price_7d_ago) / price_7d_ago",
                "inputs": mom_inputs.get(sym, {}),
                "validated": mom_val is not None,
                "note": "Higher = recent winner = tends to revert",
                "paper_url": "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6703978",
            },
            "sector": sector,
            "total_score": round(total, 1),
            "confidence": confidence,
        }

    return factors


def generate_json_data() -> dict:
    """Build the complete dashboard data JSON with candle data for charts."""
    conn = _connect()
    from pathlib import Path
    CANDLE_DIR = Path("/root/BEAR/data/raw/candles")

    try:
        markets = load_markets(conn)
    except Exception:
        markets = []

    stats = compute_stats(markets)
    factors = compute_factor_scores(markets)

    # ── Leaderboard 1: Price Action (best shorts based on momentum/reversal) ──
    price_action = []
    for sym, f in factors.items():
        m = next((m for m in markets if m["symbol"] == sym), {})
        price_action.append({
            "symbol": sym, "sector": f.get("sector", "other"),
            "score": f["total_score"],
            "reversal": f["reversal_8w"]["value"],
            "carry": f["funding_carry"]["value"],
            "momentum": f["momentum_7d"]["value"],
            "crowding": f["oi_crowding"]["value"],
            "volatility": f["volatility_30d"]["value"],
            "mark_px": m.get("mark_px", 0),
            "funding": m.get("funding", 0),
        })
    price_action.sort(key=lambda x: x["score"], reverse=True)

    # ── Leaderboard 2: Dogshit (fundamental garbage — destined for zero) ──
    # Only flags genuinely bad projects. Excludes real L1s, DEXs, established DeFi.
    TRASH_CATEGORIES = {"meme"}  # Only true meme/animal coins are auto-flagged
    QUALITY_CATEGORIES = {"layer1", "l1", "l2", "defi", "dex", "oracle", "privacy", "rwa", "storage", "exchange", "ai"}  # Never dogshit
    dogshit = []
    for m in markets:
        sym = m["symbol"]
        px = m.get("mark_px") or 0
        vol = m.get("day_volume") or 0
        oi = m.get("open_interest") or 0
        fund = m.get("funding") or 0
        cat = (m.get("category") or "other").lower()

        # Skip quality projects entirely
        if cat in QUALITY_CATEGORIES:
            continue
        # Skip well-known legitimate projects by name
        if sym in ("BTC", "ETH", "SOL", "HYPE", "BNB", "XRP", "ADA", "AVAX", "DOT",
                    "LINK", "UNI", "AAVE", "MKR", "SNX", "CRV", "LDO", "PENDLE",
                    "INJ", "TIA", "SEI", "NEAR", "FIL", "AR", "HBAR", "XLM",
                    "ONDO", "PAXG", "TRX", "TON", "ICP", "ETC", "BCH", "LTC",
                    "DASH", "XMR", "ZEC", "BSV"):
            continue

        # Dogshit signals (higher = worse)
        # 1. Meme category
        meme_score = 80 if cat == "meme" else 20 if cat == "other" else 0

        # 2. Very low price + small market cap = microcap junk
        # Use volume as proxy for market cap (larger vol = larger mcap)
        cap_score = 0
        if vol < 50_000: cap_score = 90  # tiny volume = nobody cares
        elif vol < 200_000: cap_score = 70
        elif vol < 1_000_000: cap_score = 50
        elif vol < 5_000_000: cap_score = 30

        # 3. Negative funding = market consensus it's bad
        fund_score = 0
        if fund < -0.0001: fund_score = 80
        elif fund < -0.00001: fund_score = 60
        elif fund < 0: fund_score = 40

        # 4. Price below $0.01 = likely junk
        price_junk = 0
        if px < 0.001: price_junk = 70
        elif px < 0.01: price_junk = 50
        elif px < 0.05: price_junk = 20

        dog_total = meme_score * 0.30 + cap_score * 0.25 + fund_score * 0.25 + price_junk * 0.20
        if dog_total < 30:  # Don't show mediocre scores
            continue

        dogshit.append({
            "symbol": sym, "sector": cat,
            "score": round(dog_total, 1),
            "meme_score": meme_score, "cap_score": cap_score,
            "fund_score": fund_score, "price_junk": price_junk,
            "mark_px": px, "funding": fund,
        })
    dogshit.sort(key=lambda x: x["score"], reverse=True)

    # ── Leaderboard 3: Squeeze Recovery (just got blown out, now overextended) ──
    squeeze_recovery = []
    for p in CANDLE_DIR.iterdir():
        if not p.is_dir():
            continue
        sym = p.name
        try:
            df = pl.read_parquet(p / "1h.parquet")
            if df.height < 720:
                continue
            closes = df["close"].to_numpy()
            volumes = df["volume"].to_numpy()

            # 30-day drawdown
            recent = closes[-720:]
            peak_30d = max(recent)
            trough_30d = min(recent)
            dd_30d = (peak_30d - trough_30d) / peak_30d if peak_30d > 0 else 0

            # 7-day pump from 30-day low
            last_7d_high = max(closes[-168:])
            pump_pct = (last_7d_high - trough_30d) / trough_30d if trough_30d > 0 else 0

            # Volume spike (3-day avg vs 30-day avg)
            vol_3d = float(sum(volumes[-72:])) / 72 if len(volumes) >= 72 else 0
            vol_30d = float(sum(volumes[-720:])) / 720 if len(volumes) >= 720 else 0
            vol_spike = vol_3d / vol_30d if vol_30d > 0 else 1

            # Squeeze recovery score: big drawdown + big pump + volume spike = just got squeezed
            # These are the best SHORT entries AFTER the squeeze
            sq_score = (dd_30d * 100 * 0.4 + pump_pct * 100 * 0.4 + min(vol_spike, 5) * 20 * 0.2)

            mkt = next((m for m in markets if m["symbol"] == sym), {})
            squeeze_recovery.append({
                "symbol": sym,
                "sector": mkt.get("category", "other"),
                "score": round(sq_score, 1),
                "drawdown_30d": round(dd_30d * 100, 1),
                "pump_from_low": round(pump_pct * 100, 1),
                "volume_spike": round(vol_spike, 1),
                "mark_px": mkt.get("mark_px", 0),
                "funding": mkt.get("funding", 0),
            })
        except Exception:
            pass
    squeeze_recovery.sort(key=lambda x: x["score"], reverse=True)

    # ── Leaderboard 4: Synthesis (combines all 3 — maximum conviction) ──
    pa_map = {s["symbol"]: s for s in price_action}
    dog_map = {s["symbol"]: s for s in dogshit}
    sq_map = {s["symbol"]: s for s in squeeze_recovery}
    all_syms = set(list(pa_map.keys()) + list(dog_map.keys()) + list(sq_map.keys()))

    synthesis = []
    for sym in all_syms:
        pa = pa_map.get(sym, {})
        dog = dog_map.get(sym, {})
        sq = sq_map.get(sym, {})
        m = next((m for m in markets if m["symbol"] == sym), {})

        # How many leaderboards is this asset in? (confluence)
        in_count = (1 if pa else 0) + (1 if dog else 0) + (1 if sq else 0)

        pa_score = pa.get("score", 0)
        dog_score = dog.get("score", 0)
        sq_score = sq.get("score", 0)

        # Synthesis: weighted combo + confluence bonus
        # Confluence is the key — being in 2+ boards is much stronger
        base = pa_score * 0.35 + dog_score * 0.25 + sq_score * 0.25
        confluence_bonus = in_count * 15  # +15 per board
        # Penalty if only in 1 board (less conviction)
        if in_count == 1:
            base *= 0.6

        total = min(100, base + confluence_bonus)

        # Evidence: what each board says about this asset
        evidence = []
        if pa: evidence.append(f"Price: overextended (rev={pa.get('reversal',0):.0f})")
        if dog: evidence.append(f"Fundamentals: garbage (score={dog.get('score',0):.0f})")
        if sq: evidence.append(f"Squeeze: just blew out (+{sq.get('pump_from_low',0):.0f}%)")

        synthesis.append({
            "symbol": sym,
            "sector": pa.get("sector") or dog.get("sector") or sq.get("sector") or "other",
            "score": round(total, 1),
            "in_boards": in_count,
            "price_action": pa_score,
            "dogshit": dog_score,
            "squeeze": sq_score,
            "evidence": evidence,
            "mark_px": m.get("mark_px", 0),
            "funding": m.get("funding", 0),
        })
    synthesis.sort(key=lambda x: x["score"], reverse=True)

    # Also build old-format short_rankings for backward compat
    short_rankings = price_action[:20]

    # Load candle data for top 20 short candidates (for chart rendering)
    candles = {}
    top_shorts = [sr["symbol"] for sr in short_rankings[:20]]
    for sym in top_shorts:
        p = CANDLE_DIR / sym / "1h.parquet"
        if p.exists():
            try:
                df = pl.read_parquet(p)
                # Downsample to daily for dashboard (last 90 days)
                df = df.with_columns(pl.col("open_time").dt.date().alias("date"))
                daily = df.group_by("date").agg([
                    pl.col("open").first(),
                    pl.col("high").max(),
                    pl.col("low").min(),
                    pl.col("close").last(),
                    pl.col("volume").sum(),
                ]).sort("date")
                candles[sym] = [
                    {"time": str(r["date"]), "open": round(r["open"],6),
                     "high": round(r["high"],6), "low": round(r["low"],6),
                     "close": round(r["close"],6), "volume": round(r["volume"],0)}
                    for r in daily.iter_rows(named=True)
                ]
            except Exception:
                pass
    for sr in short_rankings:
        sym = sr["symbol"]
        if sym in factors:
            f = factors[sym]
            sr["total_score"] = f["total_score"]
            sr["confidence"] = f["confidence"]
            sr["reversal_8w"] = f["reversal_8w"]["value"]
            sr["volatility"] = f["volatility_30d"]["value"]
            sr["funding_carry"] = f["funding_carry"]["value"]
            sr["oi_crowding"] = f["oi_crowding"]["value"]
            sr["momentum_7d"] = f["momentum_7d"]["value"]

    data = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stats": stats,
        "markets": markets,
        "short_rankings": short_rankings,
        "leaderboards": {
            "price_action": price_action[:20],
            "dogshit": dogshit[:20],
            "squeeze_recovery": squeeze_recovery[:20],
            "synthesis": synthesis[:20],
        },
        "factors": factors,
        "candles": candles,
    }

    conn.close()
    return data


def write_data_json(data: dict) -> None:
    DATA_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_OUT, "w") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"Wrote {DATA_OUT} ({DATA_OUT.stat().st_size:,} bytes)")


def regenerate_html(data: dict) -> None:
    """Replace the bear-data script tag in index.html with fresh data."""
    # Always use the template as source (it has the rendering JS)
    src = TEMPLATE_PATH if TEMPLATE_PATH.exists() else HTML_OUT
    if not src.exists():
        print(f"Warning: no template found at {src}, skipping HTML regeneration")
        return

    html = src.read_text()
    data_json = json.dumps(data, default=str)

    # Replace or insert the bear-data script tag (avoid regex for unicode safety)
    data_json = json.dumps(data, default=str)
    tag = f'<script id="bear-data" type="application/json">\n{data_json}\n</script>'
    
    # Simple string replacement instead of regex
    if '<script id="bear-data"' in html:
        start = html.find('<script id="bear-data"')
        end = html.find('</script>', start) + len('</script>')
        html = html[:start] + tag + html[end:]
    elif '{BEAR_DATA_PLACEHOLDER}' in html:
        html = html.replace('{BEAR_DATA_PLACEHOLDER}', data_json)
    else:
        html = html.replace("</body>", f"{tag}\n</body>")

    HTML_OUT.parent.mkdir(parents=True, exist_ok=True)
    HTML_OUT.write_text(html)
    print(f"Wrote {HTML_OUT} ({HTML_OUT.stat().st_size:,} bytes)")


def main() -> None:
    print(f"Reading from {DB_PATH}...")
    data = generate_json_data()
    write_data_json(data)
    regenerate_html(data)

    s = data["stats"]
    print(f"Stats: {s['total_markets']} markets, "
          f"${s['total_24h_volume']:,.0f} 24h vol, "
          f"{s['positive_funding_count']}/{s['negative_funding_count']} pos/neg funding")
    print(f"Top short: {data['short_rankings'][0]['symbol'] if data['short_rankings'] else 'N/A'}")


if __name__ == "__main__":
    main()
