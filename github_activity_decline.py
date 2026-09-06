import requests
import json
import time
from datetime import datetime

REPOS = [
    ("ethereum", "go-ethereum"),
    ("ethereum", " Ethereum"),
    ("solana-labs", "solana"),
    ("solana-labs", "solana-program-library"),
    ("Uniswap", "v4-core"),
    ("Uniswap", "v3-core"),
    ("aave", "aave-v3-core"),
    ("Aave", "aave-v3-core"),
    ("cosmos", "cosmos-sdk"),
    ("hyperliquid-dex", "node-indexer"),
    ("hyperliquid-labs", "hyperliquid"),
    ("bitcoin", "bitcoin"),
    ("lightningnetwork", "lnd"),
    ("lightning", "bolts"),
    ("polkadot", "polkadot-sdk"),
    ("near", "nearcore"),
    ("aptos-labs", "aptos-core"),
    ("Sui", "sui"),
    ("MystenLabs", "sui"),
    ("sei-protocol", "sei-chain"),
    ("sei-protocol", "sei-db"),
    ("CurveFi", "curve-contract"),
    ("curvefi", "curve-dao-contracts"),
    ("makerdao", "dss"),
    ("makerdao", "maker-core"),
    ("CompoundLabs", "compound-protocol"),
    ("compound-finance", "compound-iii"),
    ("Aragon", "dao-erc"),
    ("Aragon", "core"),
    ("Lido", "lido-dao"),
    ("rocket-pool", "rocketpool"),
    ("frax", "frax-core"),
    ("EthenaLabs", "ethena-contracts"),
    ("EigenLabs", "eigenlayer-contracts"),
    ("Pendle", "pendle-core-v2-public"),
    ("jito-labs", "jito-solana"),
    ("marinade", "native"),
    ("step-finance", "step-contracts"),
    ("orca-so", "whirlpools"),
    ("raydium-io", "raydium-core"),
    ("pancakeswap", "pancake-v3-contracts"),
    ("SushiSwap", "sushiswap-v3-core"),
    ("1inch", "1inch-v5-contracts"),
    ("dodoex", "DODO-core-v2"),
    ("stargate-protocol", "stargate-v2-contracts"),
    ("across-protocol", "across-contracts"),
    ("hop-protocol", "hop-contracts"),
    ("synapseprotocol", "bridge-v2"),
    ("omgnetwork", "bridge"),
    ("RenVM", "ren项目"),
    ("Thorchain", "thorchain"),
    ("chainflip-labs", "chainflip-backend"),
    ("defichain", "defichain"),
    ("hedera", "hedera-services"),
    ("algorand", "go-algorand"),
    ("avalanche", "avalanchego"),
    ("celo", "celo-blockchain"),
    ("arbitrum", "nitro"),
    ("optimism", "optimism"),
    ("starknet", "starknet"),
    ("zksync", "era-contracts"),
    ("scroll-tech", "scroll"),
    ("polygon", "zkevm-contracts"),
    ("berachain", "beacon"),
    ("sui", "sui"),
    ("movement", "movement"),
    ("monad", "monad"),
    ("linea", "linea-contracts"),
    ("zksync", "zksync-era"),
    ("blast", "blast-contracts"),
    ("mantle", "mantle"),
    ("manta", "manta-network"),
]

def fetch_commit_activity(owner, repo):
    """Fetch weekly commit activity for a repo."""
    url = f"https://api.github.com/repos/{owner}/{repo}/stats/commit_activity"
    r = requests.get(url, timeout=15, headers={"Accept": "application/vnd.github.v3+json"})
    
    if r.status_code == 202:
        # GitHub is computing stats, retry once
        time.sleep(2)
        r = requests.get(url, timeout=15, headers={"Accept": "application/vnd.github.v3+json"})
    
    if r.status_code == 200:
        return r.json()
    return None

def fetch_participation(owner, repo):
    """Fetch participation stats (all commits per week)."""
    url = f"https://api.github.com/repos/{owner}/{repo}/stats/participation"
    r = requests.get(url, timeout=15, headers={"Accept": "application/vnd.github.v3+json"})
    
    if r.status_code == 202:
        time.sleep(2)
        r = requests.get(url, timeout=15, headers={"Accept": "application/vnd.github.v3+json"})
    
    if r.status_code == 200:
        return r.json()
    return None

def fetch_repo_info(owner, repo):
    """Fetch basic repo info."""
    url = f"https://api.github.com/repos/{owner}/{repo}"
    r = requests.get(url, timeout=15, headers={"Accept": "application/vnd.github.v3+json"})
    if r.status_code == 200:
        return r.json()
    return None

def analyze_activity(commits_data, participation_data=None):
    """Analyze commit activity and determine trend."""
    result = {}
    
    if commits_data and isinstance(commits_data, list) and len(commits_data) >= 4:
        weeks = commits_data
        
        # Recent 4 weeks
        recent_4w = sum(w["total"] for w in weeks[-4:])
        # Recent 13 weeks
        recent_13w = sum(w["total"] for w in weeks[-13:]) if len(weeks) >= 13 else sum(w["total"] for w in weeks)
        
        # Previous 13 weeks (before recent 13)
        if len(weeks) >= 26:
            prev_13w = sum(w["total"] for w in weeks[-26:-13])
        else:
            prev_13w = recent_13w
        
        # Average weekly
        avg_recent_13w = recent_13w / min(13, len(weeks))
        avg_prev_13w = prev_13w / 13 if prev_13w > 0 else avg_recent_13w
        
        # Trend ratio (recent vs expected based on historical)
        if avg_prev_13w > 0:
            trend_ratio = avg_recent_13w / avg_prev_13w
        else:
            trend_ratio = 1.0 if avg_recent_13w > 0 else 0.0
        
        # 4-week vs 13-week normalized
        recent_4w_normalized = recent_4w / 4
        recent_13w_normalized = recent_13w / min(13, len(weeks))
        
        if recent_13w_normalized > 0:
            short_vs_long = recent_4w_normalized / recent_13w_normalized
        else:
            short_vs_long = 1.0 if recent_4w > 0 else 0.0
        
        # Combined score
        combined = (trend_ratio * 0.6 + short_vs_long * 0.4)
        
        if combined < 0.5:
            trend = "stalled"
        elif combined < 0.75:
            trend = "declining"
        elif combined < 0.9:
            trend = "slowing"
        else:
            trend = "stable"
        
        result = {
            "recent_4w_commits": recent_4w,
            "recent_13w_commits": recent_13w,
            "prev_13w_commits": prev_13w,
            "avg_weekly_recent_13w": round(avg_recent_13w, 1),
            "avg_weekly_prev_13w": round(avg_prev_13w, 1),
            "trend_ratio": round(trend_ratio, 3),
            "short_vs_long_ratio": round(short_vs_long, 3),
            "combined_score": round(combined, 3),
            "trend": trend,
            "weeks_of_data": len(weeks),
        }
    
    elif participation_data and "all" in participation_data:
        # Fallback to participation API
        all_commits = participation_data["all"]  # last 52 weeks
        recent_4w = sum(all_commits[-4:])
        recent_13w = sum(all_commits[-13:])
        prev_13w = sum(all_commits[-26:-13]) if len(all_commits) >= 26 else recent_13w
        
        avg_recent = recent_13w / 13
        avg_prev = prev_13w / 13 if prev_13w > 0 else avg_recent
        
        if avg_prev > 0:
            trend_ratio = avg_recent / avg_prev
        else:
            trend_ratio = 1.0 if avg_recent > 0 else 0.0
        
        recent_4w_norm = recent_4w / 4
        recent_13w_norm = recent_13w / 13
        
        short_vs_long = recent_4w_norm / recent_13w_norm if recent_13w_norm > 0 else 1.0
        combined = (trend_ratio * 0.6 + short_vs_long * 0.4)
        
        if combined < 0.5:
            trend = "stalled"
        elif combined < 0.75:
            trend = "declining"
        elif combined < 0.9:
            trend = "slowing"
        else:
            trend = "stable"
        
        result = {
            "recent_4w_commits": recent_4w,
            "recent_13w_commits": recent_13w,
            "prev_13w_commits": prev_13w,
            "avg_weekly_recent_13w": round(avg_recent, 1),
            "avg_weekly_prev_13w": round(avg_prev, 1),
            "trend_ratio": round(trend_ratio, 3),
            "short_vs_long_ratio": round(short_vs_long, 3),
            "combined_score": round(combined, 3),
            "trend": trend,
            "weeks_of_data": 52,
            "source": "participation_api",
        }
    
    return result if result else None

def main():
    print(f"Analyzing {len(REPOS)} repos...")
    
    results = []
    stalled = []
    declining = []
    errors = 0
    
    for i, (owner, repo) in enumerate(REPOS):
        full_name = f"{owner}/{repo}"
        
        try:
            # Fetch repo info
            info = fetch_repo_info(owner, repo)
            if info is None:
                errors += 1
                print(f"  [{i+1}/{len(REPOS)}] {full_name}: not found")
                continue
            
            stars = info.get("stargazers_count", 0)
            language = info.get("language", "")
            description = info.get("description", "")
            created = info.get("created_at", "")
            pushed = info.get("pushed_at", "")
            
            # Fetch commit activity
            commits = fetch_commit_activity(owner, repo)
            participation = fetch_participation(owner, repo)
            
            activity = analyze_activity(commits, participation)
            
            if activity is None:
                errors += 1
                print(f"  [{i+1}/{len(REPOS)}] {full_name}: no activity data")
                continue
            
            entry = {
                "rank": i + 1,
                "owner": owner,
                "repo": repo,
                "full_name": full_name,
                "stars": stars,
                "language": language,
                "description": (description or "")[:100],
                "created_at": created,
                "last_push": pushed,
                **activity,
            }
            
            results.append(entry)
            
            if activity["trend"] == "stalled":
                stalled.append(entry)
            elif activity["trend"] == "declining":
                declining.append(entry)
            
            print(f"  [{i+1}/{len(REPOS)}] {full_name}: {activity['trend']} ({activity['recent_4w_commits']} commits/4w)")
            
            time.sleep(1.0)  # GitHub rate limit: 60/hr
            
        except Exception as e:
            errors += 1
            print(f"  [{i+1}/{len(REPOS)}] {full_name}: ERROR {e}")
    
    # Summary
    all_scores = [r["combined_score"] for r in results]
    avg_score = sum(all_scores) / len(all_scores) if all_scores else 0
    
    summary = {
        "fetched_at": datetime.utcnow().isoformat() + "Z",
        "total_repos_scanned": len(REPOS),
        "successful_analysis": len(results),
        "errors": errors,
        "avg_combined_score": round(avg_score, 3),
        "stalled_count": len(stalled),
        "declining_count": len(declining),
        "stable_count": len([r for r in results if r["trend"] == "stable"]),
        "slowing_count": len([r for r in results if r["trend"] == "slowing"]),
    }
    
    output = {
        "summary": summary,
        "death_signals": stalled + declining,
        "all_results": results,
    }
    
    # Save
    with open("/root/BEAR/data/github_activity.json", "w") as f:
        json.dump(output, f, indent=2)
    
    # Print
    print(f"\n{'='*80}")
    print(f"GitHub Activity Decline Analysis")
    print(f"{'='*80}")
    print(f"Repos scanned:      {len(REPOS)}")
    print(f"Successfully analyzed: {len(results)}")
    print(f"Errors:             {errors}")
    print(f"")
    print(f"Trend Distribution:")
    print(f"  Stable:   {summary['stable_count']}")
    print(f"  Slowing:  {summary['slowing_count']}")
    print(f"  Declining: {summary['declining_count']}")
    print(f"  Stalled:  {summary['stalled_count']}")
    print(f"  Avg combined score: {avg_score:.3f}")
    
    if stalled or declining:
        print(f"\n{'='*80}")
        print(f"DEATH SIGNALS: Stalled or Declining Repos")
        print(f"{'='*80}")
        print(f"{'Repo':<40} {'Stars':>7} {'4w':>6} {'13w':>6} {'Score':>7} {'Trend':<12}")
        print(f"{'-'*40} {'-'*7} {'-'*6} {'-'*6} {'-'*7} {'-'*12}")
        for p in stalled + declining:
            print(f"{p['full_name']:<40} {p['stars']:>7} {p['recent_4w_commits']:>6} {p['recent_13w_commits']:>6} {p['combined_score']:>7.3f} {p['trend']:<12}")
    
    print(f"\nSaved to /root/BEAR/data/github_activity.json")
    return output

if __name__ == "__main__":
    main()
