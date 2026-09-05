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
    """Compute per-asset factor scores for the dashboard.

    Returns a dict keyed by symbol with factor scores:
      dilution, reversal, unlock, value, squeeze, carry
    All values are 0-100 percentile ranks where applicable.
    """
    factors: dict[str, dict] = {}

    for m in markets:
        sym = m["symbol"]
        funding = m.get("funding") or 0.0
        vol = m.get("day_volume") or 0.0
        oi = m.get("open_interest") or 0.0
        sector = TAXONOMY.get(sym, m.get("category", "other"))

        # Carry: higher funding = more carry for shorts (good)
        # Map funding to 0-100 scale
        carry_raw = funding
        carry_score = max(0.0, min(100.0, 50.0 + carry_raw * 5000))

        # Squeeze risk: low volume + high OI relative to volume = higher squeeze risk (bad for shorts)
        if vol > 0:
            squeeze_raw = oi / vol
            squeeze_score = max(0.0, min(100.0, squeeze_raw * 50))
        else:
            squeeze_score = 50.0

        # Value badness: higher funding + lower volume = worse value
        value_score = max(0.0, min(100.0, (carry_score + squeeze_score) / 2))

        factors[sym] = {
            "dilution": 50.0,  # Placeholder - needs historical supply data
            "reversal": 50.0,  # Placeholder - needs price history
            "unlock": 50.0,    # Placeholder - needs unlock schedule
            "value": round(value_score, 1),
            "squeeze": round(squeeze_score, 1),
            "carry": round(carry_score, 1),
            "sector": sector,
        }

    return factors


def generate_json_data() -> dict:
    """Build the complete dashboard data JSON."""
    conn = _connect()

    try:
        markets = load_markets(conn)
    except Exception:
        markets = []

    stats = compute_stats(markets)
    short_rankings = compute_structural_short_scores(markets)
    factors = compute_factor_scores(markets)

    # Build short rankings with factor details
    for sr in short_rankings:
        sym = sr["symbol"]
        if sym in factors:
            f = factors[sym]
            sr["dilution_8w"] = f["dilution"]
            sr["reversal_8w"] = f["reversal"]
            sr["unlock_pressure"] = f["unlock"]
            sr["squeeze_risk"] = f["squeeze"]
            sr["total_score"] = sr["structural_short"]

    data = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stats": stats,
        "markets": markets,
        "short_rankings": short_rankings,
        "factors": factors,
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

    # Replace or insert the bear-data script tag
    tag = f'<script id="bear-data" type="application/json">\n{data_json}\n</script>'
    pattern = r'<script id="bear-data"[^>]*>.*?</script>'

    if re.search(pattern, html, re.DOTALL):
        html = re.sub(pattern, tag, html, flags=re.DOTALL)
    elif '{BEAR_DATA_PLACEHOLDER}' in html:
        html = html.replace('{BEAR_DATA_PLACEHOLDER}', data_json)
    else:
        # Insert before </body>
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
