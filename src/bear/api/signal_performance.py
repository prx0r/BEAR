"""Signal performance analytics — generates dashboard data from outcomes."""

import json
import numpy as np
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone


def load_outcomes() -> list[dict]:
    """Load all signal outcomes."""
    path = Path("/root/BEAR/astronomer/data/extracted/full_outcomes.json")
    if not path.exists():
        return []
    with open(path) as f:
        return json.load(f)


def load_author_stats() -> dict:
    """Load author reputation stats."""
    path = Path(__file__).parent.parent.parent / "data" / "reputation" / "author_stats.json"
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def compute_signal_stats(outcomes: list[dict]) -> dict:
    """Compute signal performance statistics."""
    if not outcomes:
        return {}

    # By author
    by_author = defaultdict(list)
    for o in outcomes:
        by_author[o['author']].append(o)

    author_stats = {}
    for author, author_outcomes in by_author.items():
        directional = [o for o in author_outcomes if o.get('signal_return_4h') is not None]
        if not directional:
            continue

        returns = [o['signal_return_4h'] for o in directional]
        wins = sum(1 for r in returns if r > 0)

        author_stats[author] = {
            'total_posts': len(author_outcomes),
            'directional_signals': len(directional),
            'win_rate': wins / len(directional) if directional else 0,
            'avg_return_4h': float(np.mean(returns)) if returns else 0,
            'median_return_4h': float(np.median(returns)) if returns else 0,
            'sharpe': float(np.mean(returns) / np.std(returns)) if returns and np.std(returns) > 0 else 0,
            'best_call': max(returns) if returns else 0,
            'worst_call': min(returns) if returns else 0,
        }

    # By regime (simplified — use hour-of-day as proxy)
    by_hour = defaultdict(list)
    for o in outcomes:
        if o.get('signal_return_4h') is not None:
            try:
                ts = datetime.strptime(o['timestamp'], '%a %b %d %H:%M:%S %z %Y')
                by_hour[ts.hour].append(o['signal_return_4h'])
            except:
                pass

    hour_stats = {}
    for hour, returns in by_hour.items():
        hour_stats[hour] = {
            'count': len(returns),
            'win_rate': sum(1 for r in returns if r > 0) / len(returns),
            'avg_return': float(np.mean(returns)),
        }

    # Overall
    all_returns = [o['signal_return_4h'] for o in outcomes if o.get('signal_return_4h') is not None]
    overall = {
        'total_signals': len(all_returns),
        'win_rate': sum(1 for r in all_returns if r > 0) / len(all_returns) if all_returns else 0,
        'avg_return': float(np.mean(all_returns)) if all_returns else 0,
        'sharpe': float(np.mean(all_returns) / np.std(all_returns)) if all_returns and np.std(all_returns) > 0 else 0,
    }

    return {
        'by_author': author_stats,
        'by_hour': hour_stats,
        'overall': overall,
    }


def generate_dashboard_data() -> dict:
    """Generate complete dashboard data."""
    outcomes = load_outcomes()
    stats = compute_signal_stats(outcomes)

    return {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'signal_performance': stats,
        'data_summary': {
            'total_outcomes': len(outcomes),
            'total_directional': len([o for o in outcomes if o.get('signal_return_4h') is not None]),
            'accounts_tracked': len(set(o['author'] for o in outcomes)),
        },
    }


if __name__ == "__main__":
    data = generate_dashboard_data()
    print(json.dumps(data, indent=2)[:2000])
