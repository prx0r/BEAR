import requests
import json
import time
from datetime import datetime, timedelta, timezone
import gc

def fetch_top_protocols(limit=200):
    """Fetch top protocols by TVL from DeFiLlama."""
    print(f"Fetching top {limit} protocols from DeFiLlama...")
    r = requests.get("https://api.llama.fi/protocols", timeout=30)
    r.raise_for_status()
    protocols = r.json()
    protocols.sort(key=lambda p: p.get("tvl", 0) or 0, reverse=True)
    return protocols[:limit]

def fetch_and_analyze(slug):
    """Fetch protocol TVL, extract only last 100 days, compute decline."""
    try:
        r = requests.get(f"https://api.llama.fi/protocol/{slug}", timeout=20)
        if r.status_code != 200:
            return None
        
        data = r.json()
        tvl_history = data.get("tvl", [])
        del data  # Free memory immediately
        
        if not tvl_history or len(tvl_history) < 2:
            return None
        
        # Only keep last 120 days of entries (buffer for alignment)
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=120)
        cutoff_ts = cutoff.timestamp()
        
        recent = [e for e in tvl_history if e.get("date", 0) >= cutoff_ts]
        del tvl_history  # Free original
        
        if len(recent) < 2:
            return None
        
        # Current TVL
        current_entry = recent[-1]
        current_tvl = current_entry.get("totalLiquidityUSD", 0)
        current_date = current_entry.get("date", 0)
        
        # Find ~90d ago
        target_90d = (now - timedelta(days=90)).timestamp()
        best = None
        best_diff = float('inf')
        for e in recent:
            diff = abs(e.get("date", 0) - target_90d)
            if diff < best_diff:
                best_diff = diff
                best = e
        
        if best is None or best_diff > 7 * 86400:
            return None
        
        tvl_90d = best.get("totalLiquidityUSD", 0)
        if tvl_90d <= 0:
            return None
        
        pct = (current_tvl - tvl_90d) / tvl_90d
        
        return {
            "current_tvl": current_tvl,
            "tvl_90d_ago": tvl_90d,
            "pct_change": round(pct * 100, 2),
            "absolute_change": round(current_tvl - tvl_90d, 2),
            "current_date": datetime.fromtimestamp(current_date, tz=timezone.utc).strftime("%Y-%m-%d") if current_date else None,
            "days_of_data": len(recent),
        }
    except Exception:
        return None

def main():
    protocols = fetch_top_protocols(200)
    print(f"Fetched {len(protocols)} protocols. Starting sequential analysis...")
    
    results = []
    dying = []
    
    for i, proto in enumerate(protocols):
        slug = proto.get("slug", "")
        name = proto.get("name", slug)
        
        if not slug:
            continue
        
        decline = fetch_and_analyze(slug)
        gc.collect()  # Force GC between protocols
        
        if decline is None:
            continue
        
        entry = {
            "rank": i + 1,
            "name": name,
            "symbol": proto.get("symbol", ""),
            "slug": slug,
            "category": proto.get("category", ""),
            "chain": proto.get("chain", ""),
            **decline,
        }
        results.append(entry)
        
        if decline["pct_change"] < -30:
            dying.append(entry)
        
        if (i + 1) % 20 == 0:
            print(f"  Processed {i+1}/{len(protocols)} ({len(results)} analyzed, {len(dying)} dying)")
        
        time.sleep(0.15)
    
    dying.sort(key=lambda x: x["pct_change"])
    
    changes = [r["pct_change"] for r in results]
    avg_change = sum(changes) / len(changes) if changes else 0
    median_change = sorted(changes)[len(changes)//2] if changes else 0
    
    summary = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "total_protocols_scanned": len(protocols),
        "successful_analysis": len(results),
        "errors": len(protocols) - len(results),
        "avg_tvl_change_90d_pct": round(avg_change, 2),
        "median_tvl_change_90d_pct": round(median_change, 2),
        "protocols_declining_30pct_plus": len(dying),
        "threshold_pct": -30,
    }
    
    output = {
        "summary": summary,
        "dying_protocols": dying,
        "all_results": results,
    }
    
    with open("/root/BEAR/data/llama_tvl_decline.json", "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"\n{'='*70}")
    print(f"DeFiLlama TVL Decline Analysis")
    print(f"{'='*70}")
    print(f"Protocols scanned:  {len(protocols)}")
    print(f"Successfully analyzed: {len(results)}")
    print(f"Errors: {len(protocols) - len(results)}")
    print(f"\n90-Day TVL Changes:")
    print(f"  Average:  {avg_change:+.2f}%")
    print(f"  Median:   {median_change:+.2f}%")
    print(f"  Declining >30%: {len(dying)}")
    
    if dying:
        print(f"\n{'='*70}")
        print(f"DEATH SIGNALS: Protocols with >30% TVL decline (90d)")
        print(f"{'='*70}")
        print(f"{'Rank':<5} {'Name':<25} {'Symbol':<10} {'Category':<15} {'TVL Now':>12} {'TVL 90d Ago':>12} {'Change':>10}")
        print(f"{'-'*5} {'-'*25} {'-'*10} {'-'*15} {'-'*12} {'-'*12} {'-'*10}")
        for p in dying:
            print(f"{p['rank']:<5} {p['name'][:25]:<25} {p['symbol'][:10]:<10} {p['category'][:15]:<15} ${p['current_tvl']/1e6:>10.1f}M ${p['tvl_90d_ago']/1e6:>10.1f}M {p['pct_change']:>+9.1f}%")
    
    print(f"\nSaved to /root/BEAR/data/llama_tvl_decline.json")
    return output

if __name__ == "__main__":
    main()
