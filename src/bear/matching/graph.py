"""Market graph construction for relative-value pair discovery.

Builds an asset graph where edges represent behavioral similarity,
weighted across multiple dimensions (correlation, beta, factor distance,
tail dependence, sector alignment).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import polars as pl
import numpy as np


@dataclass
class AssetNode:
    """Node in the market graph."""
    symbol: str
    sector: str = "unknown"
    adv_usd: float = 0.0
    structural_short_score: float = 50.0
    squeeze_score: float = 0.0
    metadata: dict = field(default_factory=dict)


@dataclass
class GraphEdge:
    """Edge in the market graph."""
    source: str
    target: str
    weight: float
    # Individual component weights
    corr_30d: float = 0.0
    corr_90d: float = 0.0
    downside_corr: float = 0.0
    beta_similarity: float = 0.0
    tail_dependence: float = 0.0
    vol_similarity: float = 0.0
    factor_similarity: float = 0.0
    sector_similarity: float = 0.0


@dataclass
class MarketGraph:
    """Graph representation of the asset universe."""
    nodes: dict[str, AssetNode] = field(default_factory=dict)
    edges: dict[tuple[str, str], GraphEdge] = field(default_factory=dict)
    adjacency: dict[str, list[str]] = field(default_factory=dict)

    def add_edge(self, edge: GraphEdge) -> None:
        """Add an edge to the graph."""
        key = tuple(sorted([edge.source, edge.target]))
        self.edges[key] = edge

        self.adjacency.setdefault(edge.source, [])
        self.adjacency.setdefault(edge.target, [])
        if edge.target not in self.adjacency[edge.source]:
            self.adjacency[edge.source].append(edge.target)
        if edge.source not in self.adjacency[edge.target]:
            self.adjacency[edge.target].append(edge.source)


def build_market_graph(
    all_returns: pl.DataFrame,
    asset_contexts: pl.DataFrame | None = None,
    taxonomy: dict[str, str] | None = None,
) -> MarketGraph:
    """Build a market graph with weighted edges.

    Edge weights combine:
        - 30-day correlation
        - 90-day correlation
        - Downside correlation (BTC-down periods)
        - Beta similarity
        - Tail dependence
        - Volatility similarity
        - Factor similarity (approximated via return correlation)
        - Sector similarity

    Args:
        all_returns: DataFrame with 'timestamp' and one return column per asset.
        asset_contexts: Optional DataFrame with 'symbol', 'adv_usd',
            'structural_short_score', 'squeeze_score'.
        taxonomy: Mapping of symbol -> sector name.

    Returns:
        MarketGraph with nodes and weighted edges.
    """
    if taxonomy is None:
        taxonomy = {}

    graph = MarketGraph()
    asset_cols = [c for c in all_returns.columns if c != "timestamp"]

    if len(asset_cols) < 2:
        return graph

    # Build nodes
    for sym in asset_cols:
        sector = taxonomy.get(sym, "unknown")
        node = AssetNode(symbol=sym, sector=sector)

        if asset_contexts is not None:
            ctx = asset_contexts.filter(pl.col("symbol") == sym)
            if ctx.height > 0:
                row = ctx.row(0, named=True)
                node.adv_usd = row.get("adv_usd", 0.0) or 0.0
                node.structural_short_score = row.get("structural_short_score", 50.0) or 50.0
                node.squeeze_score = row.get("squeeze_score", 0.0) or 0.0

        graph.nodes[sym] = node

    # Compute pairwise edge weights
    sorted_returns = all_returns.sort("timestamp")

    for i, sym_a in enumerate(asset_cols):
        for sym_b in asset_cols[i + 1:]:
            edge = _compute_edge(
                sym_a, sym_b, sorted_returns, taxonomy
            )
            if edge.weight > 0:
                graph.add_edge(edge)

    return graph


def _compute_edge(
    sym_a: str,
    sym_b: str,
    all_returns: pl.DataFrame,
    taxonomy: dict[str, str],
) -> GraphEdge:
    """Compute a single edge between two assets."""
    # Extract return series
    ts = all_returns["timestamp"].to_numpy()
    vals_a = all_returns[sym_a].to_numpy().astype(np.float64)
    vals_b = all_returns[sym_b].to_numpy().astype(np.float64)

    valid = np.isfinite(vals_a) & np.isfinite(vals_b)
    if valid.sum() < 20:
        return GraphEdge(source=sym_a, target=sym_b, weight=0.0)

    va = vals_a[valid]
    vb = vals_b[valid]

    # 30d correlation (last ~90 periods if 8h candles, or last 30 timestamps)
    window_30 = min(30, len(va))
    corr_30d = _safe_corr(va[-window_30:], vb[-window_30:])

    # 90d correlation
    window_90 = min(90, len(va))
    corr_90d = _safe_corr(va[-window_90:], vb[-window_90:])

    # Downside correlation (when both are in bottom decile)
    # Use joint negative returns as proxy
    both_neg = (va < 0) & (vb < 0)
    if both_neg.sum() >= 5:
        downside_corr = _safe_corr(va[both_neg], vb[both_neg])
    else:
        downside_corr = np.nan

    # Beta similarity (target: 1.0 = same risk profile)
    beta = _safe_beta(va, vb)
    beta_similarity = max(0, 1.0 - abs(beta - 1.0)) if np.isfinite(beta) else 0.5

    # Tail dependence
    lower_tail = _safe_tail_dependence(va, vb, 0.1)
    tail_dep = 1.0 - lower_tail if np.isfinite(lower_tail) else 0.5

    # Volatility similarity
    vol_a = np.std(va[-30:]) if len(va) >= 30 else np.std(va)
    vol_b = np.std(vb[-30:]) if len(vb) >= 30 else np.std(vb)
    if vol_a > 1e-15 and vol_b > 1e-15:
        vol_ratio = min(vol_a, vol_b) / max(vol_a, vol_b)
        vol_sim = vol_ratio
    else:
        vol_sim = 0.5

    # Sector similarity
    sec_a = taxonomy.get(sym_a, "unknown")
    sec_b = taxonomy.get(sym_b, "unknown")
    sector_sim = 1.0 if sec_a == sec_b and sec_a != "unknown" else 0.0

    # Factor similarity (approximated via full-sample correlation)
    factor_sim = abs(corr_90d) if np.isfinite(corr_90d) else 0.5

    # Weighted composite
    weights = {
        "corr_30d": 0.15,
        "corr_90d": 0.15,
        "downside_corr": 0.15,
        "beta_sim": 0.15,
        "tail_dep": 0.10,
        "vol_sim": 0.10,
        "factor_sim": 0.10,
        "sector_sim": 0.10,
    }

    values = {
        "corr_30d": abs(corr_30d) if np.isfinite(corr_30d) else 0.0,
        "corr_90d": abs(corr_90d) if np.isfinite(corr_90d) else 0.0,
        "downside_corr": abs(downside_corr) if np.isfinite(downside_corr) else 0.0,
        "beta_sim": beta_similarity,
        "tail_dep": tail_dep,
        "vol_sim": vol_sim,
        "factor_sim": factor_sim,
        "sector_sim": sector_sim,
    }

    weight = sum(weights[k] * values[k] for k in weights)

    return GraphEdge(
        source=sym_a,
        target=sym_b,
        weight=weight,
        corr_30d=abs(corr_30d) if np.isfinite(corr_30d) else 0.0,
        corr_90d=abs(corr_90d) if np.isfinite(corr_90d) else 0.0,
        downside_corr=abs(downside_corr) if np.isfinite(downside_corr) else 0.0,
        beta_similarity=beta_similarity,
        tail_dependence=tail_dep,
        vol_similarity=vol_sim,
        factor_similarity=factor_sim,
        sector_similarity=sector_sim,
    )


def get_neighbors(
    graph: MarketGraph,
    symbol: str,
    k: int = 10,
) -> list[tuple[str, float]]:
    """Get top-k neighbors by combined weight.

    Args:
        graph: MarketGraph to search.
        symbol: Target asset symbol.
        k: Number of top neighbors to return.

    Returns:
        List of (neighbor_symbol, combined_weight) sorted by weight descending.
    """
    if symbol not in graph.adjacency:
        return []

    neighbors_with_weights: list[tuple[str, float]] = []

    for neighbor_sym in graph.adjacency[symbol]:
        key = tuple(sorted([symbol, neighbor_sym]))
        if key in graph.edges:
            neighbors_with_weights.append((neighbor_sym, graph.edges[key].weight))

    neighbors_with_weights.sort(key=lambda x: x[1], reverse=True)
    return neighbors_with_weights[:k]


def _safe_corr(a: np.ndarray, b: np.ndarray) -> float:
    """Pearson correlation returning NaN on degenerate input."""
    if len(a) < 3 or np.std(a) < 1e-15 or np.std(b) < 1e-15:
        return np.nan
    return float(np.corrcoef(a, b)[0, 1])


def _safe_beta(x: np.ndarray, y: np.ndarray) -> float:
    """OLS beta of y on x."""
    if len(x) < 3 or np.std(x) < 1e-15:
        return np.nan
    cov_xy = np.mean((x - np.mean(x)) * (y - np.mean(y)))
    var_x = np.var(x)
    return float(cov_xy / var_x) if var_x > 1e-15 else np.nan


def _safe_tail_dependence(a: np.ndarray, b: np.ndarray, quantile: float = 0.1) -> float:
    """Lower tail dependence P(B < q | A < q)."""
    if len(a) < 10:
        return np.nan
    a_q = np.percentile(a, quantile * 100)
    mask = a <= a_q
    if mask.sum() == 0:
        return np.nan
    b_q = np.percentile(b, quantile * 100)
    return float((b[mask] <= b_q).mean())
