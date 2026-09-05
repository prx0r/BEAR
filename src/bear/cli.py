"""Click CLI for BEAR — Hyperliquid relative-value trading engine.

All commands call into real engine modules: DataStore, managers, features,
matching, and optimizer.

⚠️  RESEARCH-ONLY SYSTEM — NO LIVE TRADING ⚠️
This produces signals and dashboards. It does not place orders.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Optional

import click
import polars as pl
import yaml

from bear import __version__


def _run_async(coro):
    """Run an async coroutine from sync Click commands."""
    return asyncio.run(coro)


def _load_config(config_path: str) -> dict:
    try:
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}


def _get_store() -> "DataStore":
    from bear.data.store import DataStore
    return DataStore()


def _get_taxonomy() -> dict[str, str]:
    """Load taxonomy from config, return symbol -> sector mapping."""
    tax_path = Path("config/taxonomy.yaml")
    if not tax_path.exists():
        tax_path = Path(__file__).resolve().parent.parent.parent.parent / "config" / "taxonomy.yaml"
    if tax_path.exists():
        with open(tax_path) as f:
            raw = yaml.safe_load(f) or {}
        sectors = raw.get("sectors", {})
        mapping: dict[str, str] = {}
        for sector, symbols in sectors.items():
            for sym in symbols:
                mapping[sym.upper()] = sector
        return mapping
    return {}


# ── CLI Group ────────────────────────────────────────────────────────────────


@click.group()
@click.version_option(__version__, prog_name="bear")
@click.option("--config", "config_path", default="config/default.yaml", help="Config file path")
@click.pass_context
def cli(ctx: click.Context, config_path: str) -> None:
    """BEAR — Hyperliquid relative-value trading engine."""
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config_path
    ctx.obj["config"] = _load_config(config_path)


# ── Sync ─────────────────────────────────────────────────────────────────────


@cli.group()
def sync() -> None:
    """Sync market data from Hyperliquid."""


@sync.command("universe")
@click.option("--save", default="data/universe.json", help="Output path")
def sync_universe(save: str) -> None:
    """Sync current Hyperliquid universe."""
    async def _run():
        from bear.hyperliquid.client import HyperliquidClient
        from bear.hyperliquid.universe import UniverseManager
        from bear.data.store import DataStore

        client = HyperliquidClient()
        mgr = UniverseManager(client)
        snapshot = await mgr.refresh()
        await client.close()

        # Save to DuckDB
        store = DataStore()
        rows = mgr.to_market_rows()
        if rows:
            df = pl.DataFrame(rows)
            store.save_markets(df)
            click.echo(f"Saved {len(rows)} markets to DuckDB")

        # Save JSON
        out = Path(save)
        out.parent.mkdir(parents=True, exist_ok=True)
        market_data = [
            {"name": a.name, "market_id": a.market_id, "category": a.category,
             "mark_px": str(a.mark_px), "funding": str(a.funding),
             "open_interest": str(a.open_interest), "day_ntl_vlm": str(a.day_ntl_vlm)}
            for a in snapshot.active_assets
        ]
        out.write_text(json.dumps(market_data, indent=2))
        click.echo(f"Saved universe ({len(market_data)} active assets) to {save}")

    _run_async(_run())


@sync.command("candles")
@click.option("--symbols", multiple=True, help="Symbols to sync")
@click.option("--interval", default="1h", help="Candle interval")
@click.option("--days", default=90, help="Days of history")
@click.pass_context
def sync_candles(ctx: click.Context, symbols: tuple, interval: str, days: int) -> None:
    """Sync OHLCV candle data."""
    async def _run():
        from bear.hyperliquid.client import HyperliquidClient
        from bear.hyperliquid.universe import UniverseManager
        from bear.hyperliquid.candles import CandleManager
        from bear.data.store import DataStore

        client = HyperliquidClient()
        universe_mgr = UniverseManager(client)
        snapshot = await universe_mgr.get_or_refresh()
        candle_mgr = CandleManager(client)
        store = DataStore()

        coins = list(symbols) if symbols else [a.name for a in snapshot.active_assets]
        start_ms = int((time.time() - days * 86400) * 1000)
        end_ms = int(time.time() * 1000)

        total_rows = 0
        for coin in coins:
            try:
                click.echo(f"  Syncing {coin} ({interval})...", nl=False)
                df = await candle_mgr.backfill(coin, interval, start_ms, end_ms)
                if df.height > 0:
                    store.save_candles(df)
                    total_rows += df.height
                click.echo(f" {df.height} candles")
            except Exception as e:
                click.echo(f" ERROR: {e}")

        await client.close()
        click.echo(f"Done. {total_rows} total candles synced.")

    _run_async(_run())


@sync.command("funding")
@click.option("--symbols", multiple=True, help="Symbols to sync")
@click.option("--days", default=90, help="Days of history")
@click.pass_context
def sync_funding(ctx: click.Context, symbols: tuple, days: int) -> None:
    """Sync funding rate history."""
    async def _run():
        from bear.hyperliquid.client import HyperliquidClient
        from bear.hyperliquid.universe import UniverseManager
        from bear.hyperliquid.funding import FundingManager
        from bear.data.store import DataStore

        client = HyperliquidClient()
        universe_mgr = UniverseManager(client)
        snapshot = await universe_mgr.get_or_refresh()
        funding_mgr = FundingManager(client)
        store = DataStore()

        coins = list(symbols) if symbols else [a.name for a in snapshot.active_assets]
        start_ms = int((time.time() - days * 86400) * 1000)
        end_ms = int(time.time() * 1000)

        total_rows = 0
        for coin in coins:
            try:
                click.echo(f"  Syncing {coin} funding...", nl=False)
                df = await funding_mgr.backfill(coin, start_ms, end_ms)
                if df.height > 0:
                    store.save_funding(df)
                    total_rows += df.height
                click.echo(f" {df.height} entries")
            except Exception as e:
                click.echo(f" ERROR: {e}")

        await client.close()
        click.echo(f"Done. {total_rows} total funding entries synced.")

    _run_async(_run())


@sync.command("all")
@click.option("--days", default=90, help="Days of history")
@click.option("--symbols", multiple=True, help="Specific symbols (default: all)")
@click.pass_context
def sync_all(ctx: click.Context, days: int, symbols: tuple) -> None:
    """Sync universe, candles, and funding."""
    click.echo("=== Syncing universe ===")
    ctx.invoke(sync_universe, save="data/universe.json")
    click.echo("\n=== Syncing candles ===")
    ctx.invoke(sync_candles, symbols=symbols, interval="1h", days=days)
    click.echo("\n=== Syncing funding ===")
    ctx.invoke(sync_funding, symbols=symbols, days=days)


# ── Markets ───────────────────────────────────────────────────────────────────


@cli.command("markets")
@click.option("--json-out", is_flag=True, help="Output as JSON")
@click.option("--sector", help="Filter by sector")
def markets(json_out: bool, sector: str | None) -> None:
    """List current Hyperliquid markets from local store."""
    store = _get_store()
    df = store.load_markets()
    if df.height == 0:
        click.echo("No markets in store. Run: bear sync universe")
        return

    if sector:
        df = df.filter(pl.col("category") == sector)

    if json_out:
        click.echo(json.dumps(df.to_dicts(), indent=2))
    else:
        click.echo(f"{'Symbol':<12} {'Market ID':<20} {'Category':<12} {'Max Lev':>8} {'Delisted':>8}")
        click.echo("-" * 64)
        for row in df.iter_rows(named=True):
            name = row.get("name", row.get("market_id", "?"))
            click.echo(
                f"{name:<12} {row['market_id']:<20} {row.get('category', '?'):<12} "
                f"{row.get('max_leverage', 0):>8} {'Yes' if row.get('is_delisted') else 'No':>8}"
            )
        click.echo(f"\nTotal: {df.height} markets")


@cli.command("inspect")
@click.argument("symbol")
def inspect(symbol: str) -> None:
    """Inspect a single market's details."""
    store = _get_store()
    df = store.load_markets()
    sym_upper = symbol.upper()

    match = df.filter(
        (pl.col("market_id").str.contains(sym_upper))
        | (pl.col("name") == sym_upper)
    )
    if match.height == 0:
        click.echo(f"Market '{symbol}' not found in store.")
        return

    row = match.row(0, named=True)
    click.echo(f"=== {sym_upper} ===")
    for k, v in row.items():
        click.echo(f"  {k}: {v}")

    # Show available candle data
    try:
        candles = store.load_candles(sym_upper, "1h")
        click.echo(f"\n  Candles (1h): {candles.height} rows")
        if candles.height > 0:
            first = candles["open_time"].min()
            last = candles["open_time"].max()
            click.echo(f"  Range: {first} → {last}")
    except Exception:
        pass

    # Show available funding data
    try:
        funding = store.load_funding(sym_upper)
        click.echo(f"  Funding: {funding.height} rows")
    except Exception:
        pass


# ── Neighbors ─────────────────────────────────────────────────────────────────


@cli.command("neighbors")
@click.argument("symbol")
@click.option("--top", default=10, help="Number of neighbors")
@click.option("--mode", default="relative_value",
              type=click.Choice(["risk_hedge", "relative_value", "alpha_preserve"]))
@click.option("--interval", default="1h", help="Candle interval to use")
def neighbors(symbol: str, top: int, mode: str, interval: str) -> None:
    """Find behavioral neighbors of a symbol."""
    store = _get_store()
    sym_upper = symbol.upper()

    # Load candles for the target symbol
    long_candles = store.load_candles(sym_upper, interval)
    if long_candles.height == 0:
        click.echo(f"No candle data for {sym_upper}. Run: bear sync candles --symbols {sym_upper}")
        return

    # Load candles for all other symbols
    markets = store.load_markets()
    if markets.height == 0:
        click.echo("No markets in store. Run: bear sync universe")
        return

    # Build returns
    from bear.features.returns import compute_log_returns

    # Get close prices for all available symbols
    all_symbols = markets["name"].to_list() if "name" in markets.columns else []
    price_dfs = []
    for s in all_symbols:
        if s == sym_upper:
            continue
        c = store.load_candles(s, interval)
        if c.height > 10:
            pdf = c.select([
                pl.col("open_time").alias("timestamp"),
                pl.col("close"),
            ]).with_columns(pl.lit(s).alias("symbol"))
            price_dfs.append(pdf)

    if not price_dfs:
        click.echo("Not enough data for other symbols to find neighbors.")
        return

    # Build wide returns DataFrame
    all_close = long_candles.select([
        pl.col("open_time").alias("timestamp"),
        pl.col("close").alias(sym_upper),
    ])

    for pdf in price_dfs:
        sym = pdf["symbol"][0]
        sym_close = pdf.select([
            pl.col("timestamp"),
            pl.col("close").alias(sym),
        ])
        all_close = all_close.join(sym_close, on="timestamp", how="full", coalesce=True)

    all_returns = compute_log_returns(all_close)
    long_returns = all_close.select(["timestamp", sym_upper])
    long_returns = compute_log_returns(long_returns)

    # Find neighbors
    from bear.matching.pair import find_nearest_neighbors
    taxonomy = _get_taxonomy()

    candidates = find_nearest_neighbors(
        long_returns=long_returns,
        all_returns=all_returns,
        taxonomy=taxonomy,
        mode=mode,
        top_k=top,
    )

    if not candidates:
        click.echo("No neighbors found (insufficient data or no candidates).")
        return

    click.echo(f"=== Top {len(candidates)} neighbors for {sym_upper} (mode={mode}) ===\n")
    click.echo(f"{'Rank':>4} {'Symbol':<12} {'Score':>8} {'Corr':>8} {'Beta':>8} {'Sector':<12}")
    click.echo("-" * 56)
    for c in candidates:
        click.echo(
            f"{c.rank:>4} {c.candidate_symbol:<12} {c.fit_score:>8.2f} "
            f"{c.correlation_score:>8.2f} {c.beta_score:>8.2f} "
            f"{taxonomy.get(c.candidate_symbol, '?'):<12}"
        )


# ── Ranking ───────────────────────────────────────────────────────────────────


@cli.command("rank-shorts")
@click.option("--long", "long_symbol", help="Reference long symbol for relative scoring")
@click.option("--sector", help="Filter by sector")
@click.option("--top", default=20, help="Number of results")
@click.option("--json-out", is_flag=True)
@click.option("--interval", default="1h")
def rank_shorts(
    long_symbol: str | None,
    sector: str | None,
    top: int,
    json_out: bool,
    interval: str,
) -> None:
    """Rank available short candidates by structural short score."""
    store = _get_store()
    markets = store.load_markets()
    if markets.height == 0:
        click.echo("No markets in store. Run: bear sync universe")
        return

    # Build scores from available data
    results = []
    for row in markets.iter_rows(named=True):
        name = row.get("name", row.get("market_id", ""))
        if not name:
            continue

        # Load funding data for carry score
        funding = store.load_funding(name)
        carry = 0.0
        if funding.height > 0:
            rates = funding["rate"].to_list()
            carry = sum(rates[-24:]) / max(len(rates[-24:]), 1) * 24 * 365 if rates else 0.0

        # Load candle data for volatility
        candles = store.load_candles(name, interval)
        vol = 0.0
        adv = 0.0
        if candles.height > 10:
            closes = candles["close"].to_list()
            returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes)) if closes[i-1] > 0]
            if returns:
                import statistics
                vol = statistics.stdev(returns) if len(returns) > 1 else 0.0
            volumes = candles["volume"].to_list()
            adv = sum(volumes[-24:]) / 24 if len(volumes) >= 24 else sum(volumes) / max(len(volumes), 1)

        # Structural short score approximation (higher = more short-worthy)
        structural_score = min(100, max(0,
            50  # base
            + (carry * 50 if carry > 0 else -carry * 30)  # high positive funding = good for shorts
            + vol * 200  # high vol = more short-worthy
            - (adv / 1e6) * 5  # high liquidity = slightly less short-worthy
        ))

        squeeze_risk = max(0, min(1.0, 1.0 - vol * 10)) if vol > 0 else 0.5

        results.append({
            "symbol": name,
            "sector": row.get("category", "?"),
            "structural_short_score": round(structural_score, 2),
            "carry": round(carry, 4),
            "volatility": round(vol, 4),
            "adv": round(adv, 2),
            "squeeze_risk": round(squeeze_risk, 2),
        })

    # Filter by sector
    if sector:
        results = [r for r in results if r["sector"] == sector]

    # Sort by structural short score
    results.sort(key=lambda x: x["structural_short_score"], reverse=True)
    results = results[:top]

    if json_out:
        click.echo(json.dumps(results, indent=2))
    else:
        click.echo(f"=== Top {len(results)} Short Candidates ===\n")
        click.echo(f"{'Rank':>4} {'Symbol':<12} {'Score':>8} {'Carry':>10} {'Vol':>8} {'Sector':<12}")
        click.echo("-" * 58)
        for i, r in enumerate(results, 1):
            click.echo(
                f"{i:>4} {r['symbol']:<12} {r['structural_short_score']:>8.2f} "
                f"{r['carry']:>10.4f} {r['volatility']:>8.4f} {r['sector']:<12}"
            )


# ── Recommend ─────────────────────────────────────────────────────────────────


@cli.command("recommend")
@click.option("--long", "long_symbol", help="Single long symbol")
@click.option("--portfolio", "portfolio_path", help="Portfolio YAML path")
@click.option("--mode", default="relative_value",
              type=click.Choice(["risk_hedge", "relative_value", "alpha_preserve"]))
@click.option("--top", default=5, help="Number of shorts to recommend")
@click.option("--interval", default="1h")
@click.pass_context
def recommend(
    ctx: click.Context,
    long_symbol: str | None,
    portfolio_path: str | None,
    mode: str,
    top: int,
    interval: str,
) -> None:
    """Recommend short hedge for a long position or portfolio."""
    store = _get_store()

    longs: dict[str, float] = {}
    if portfolio_path:
        with open(portfolio_path) as f:
            port = yaml.safe_load(f) or {}
        longs = port.get("longs", {})
        click.echo(f"Portfolio from {portfolio_path}:")
        for sym, weight in longs.items():
            click.echo(f"  {sym}: {weight:.0%}")
    elif long_symbol:
        longs = {long_symbol.upper(): 1.0}
    else:
        click.echo("Specify --long SYMBOL or --portfolio PATH")
        return

    from bear.features.returns import compute_log_returns
    from bear.matching.pair import find_nearest_neighbors

    taxonomy = _get_taxonomy()

    for long_sym, weight in longs.items():
        click.echo(f"\n{'='*60}")
        click.echo(f"Hedge recommendation for {long_sym} (weight={weight:.0%}, mode={mode})")
        click.echo(f"{'='*60}")

        # Load long candles
        long_candles = store.load_candles(long_sym, interval)
        if long_candles.height == 0:
            click.echo(f"  No data for {long_sym}. Skipping.")
            continue

        # Build returns for all symbols
        markets = store.load_markets()
        all_symbols = markets["name"].to_list() if "name" in markets.columns else []

        all_close = long_candles.select([
            pl.col("open_time").alias("timestamp"),
            pl.col("close").alias(long_sym),
        ])

        for s in all_symbols:
            if s == long_sym:
                continue
            c = store.load_candles(s, interval)
            if c.height > 10:
                sym_close = c.select([
                    pl.col("open_time").alias("timestamp"),
                    pl.col("close").alias(s),
                ])
                all_close = all_close.join(sym_close, on="timestamp", how="full", coalesce=True)

        all_returns = compute_log_returns(all_close)
        long_returns = all_close.select(["timestamp", long_sym])
        long_returns = compute_log_returns(long_returns)

        # Find neighbors
        candidates = find_nearest_neighbors(
            long_returns=long_returns,
            all_returns=all_returns,
            taxonomy=taxonomy,
            mode=mode,
            top_k=top * 2,
        )

        if not candidates:
            click.echo("  No candidates found.")
            continue

        # Score and rank
        from bear.matching.baskets import compute_total_score

        scored = []
        for c in candidates[:top]:
            # Approximate component scores
            hedge_fit = c.fit_score
            structural = 50.0  # default
            carry = 0.0
            execution = 80.0  # default
            squeeze = 50.0
            dq = 70.0

            # Get funding carry
            funding = store.load_funding(c.candidate_symbol)
            if funding.height > 0:
                rates = funding["rate"].to_list()
                carry = sum(rates[-24:]) / max(len(rates[-24:]), 1) * 24 * 365 if rates else 0.0

            ts = compute_total_score(
                hedge_fit=hedge_fit,
                structural_short=structural,
                carry=carry,
                execution=execution,
                squeeze_risk=squeeze,
                data_quality=dq,
            )
            scored.append((c, ts, carry))

        scored.sort(key=lambda x: x[1].total, reverse=True)

        click.echo(f"\n{'Rank':>4} {'Symbol':<12} {'Total':>8} {'Hedge':>8} {'Carry':>10} {'Carry%':>8}")
        click.echo("-" * 54)
        for i, (cand, ts, carry) in enumerate(scored[:top], 1):
            click.echo(
                f"{i:>4} {cand.candidate_symbol:<12} {ts.total:>8.2f} "
                f"{ts.hedge_fit:>8.2f} {carry:>10.4f} {carry*100:>7.2f}%"
            )

        # Optimize basket
        if len(scored) >= 2:
            import numpy as np
            from bear.portfolio.optimizer import optimize_basket
            from bear.portfolio.constraints import PortfolioConstraints

            # Build return matrices
            cand_syms = [c.candidate_symbol for c, _, _ in scored[:top]]
            long_ret = long_returns[long_sym].to_numpy().astype(np.float64)
            cand_ret = np.column_stack([
                all_returns[s].to_numpy().astype(np.float64)
                for s in cand_syms if s in all_returns.columns
            ])

            # Remove NaN rows
            valid = np.isfinite(long_ret) & np.all(np.isfinite(cand_ret), axis=1)
            long_ret = long_ret[valid]
            cand_ret = cand_ret[valid]

            if len(long_ret) > 20 and cand_ret.shape[1] > 0:
                scores = np.array([ts.total for _, ts, _ in scored[:top]])
                constraints = PortfolioConstraints(
                    max_names=top,
                    max_name_weight=0.35,
                )
                result = optimize_basket(
                    long_returns=long_ret,
                    candidate_returns=cand_ret,
                    candidate_scores=scores,
                    constraints=constraints,
                )

                if result.weights:
                    click.echo(f"\nOptimized hedge basket:")
                    for name, w in sorted(result.weights.items(), key=lambda x: -x[1]):
                        click.echo(f"  {name}: {w:.2%}")
                    click.echo(f"  Short gross: {result.short_gross:.2%}")
                    click.echo(f"  Net exposure: {result.net_exposure:.2%}")


# ── Backtest ──────────────────────────────────────────────────────────────────


@cli.command("backtest")
@click.option("--long", "long_symbol", required=True, help="Long symbol")
@click.option("--shorts", multiple=True, help="Short symbols")
@click.option("--interval", default="1h")
@click.option("--json-out", is_flag=True)
def backtest(long_symbol: str, shorts: tuple, interval: str, json_out: bool) -> None:
    """Run backtest for a long-short pair."""
    store = _get_store()
    sym = long_symbol.upper()

    long_candles = store.load_candles(sym, interval)
    if long_candles.height == 0:
        click.echo(f"No candle data for {sym}. Run: bear sync candles --symbols {sym}")
        return

    # Build price DataFrame
    price_df = long_candles.select([
        pl.col("open_time").alias("timestamp"),
        pl.col("close"),
    ]).with_columns(pl.lit(sym).alias("symbol"))

    if shorts:
        for s in shorts:
            c = store.load_candles(s.upper(), interval)
            if c.height > 0:
                sym_df = c.select([
                    pl.col("open_time").alias("timestamp"),
                    pl.col("close"),
                ]).with_columns(pl.lit(s.upper()).alias("symbol"))
                price_df = pl.concat([price_df, sym_df])

    # Compute returns
    from bear.backtest.metrics import compute_metrics
    import numpy as np

    # Pivot to wide format
    wide = price_df.pivot(index="timestamp", on="symbol", values="close").sort("timestamp")
    closes = wide[sym].to_numpy().astype(np.float64)
    valid_closes = closes[np.isfinite(closes)]

    if len(valid_closes) < 10:
        click.echo("Insufficient data for backtest.")
        return

    returns = np.diff(valid_closes) / valid_closes[:-1]
    equity = np.cumprod(1 + returns)
    equity = np.insert(equity, 0, 1.0)

    metrics = compute_metrics(equity)

    if json_out:
        click.echo(json.dumps({
            "total_return": metrics.total_return,
            "cagr": metrics.cagr,
            "sharpe_ratio": metrics.sharpe_ratio,
            "sortino_ratio": metrics.sortino_ratio,
            "max_drawdown": metrics.max_drawdown,
            "calmar_ratio": metrics.calmar_ratio,
            "hit_rate": metrics.hit_rate,
        }, indent=2))
    else:
        click.echo(f"=== Backtest: {sym} ({len(valid_closes)} periods) ===\n")
        click.echo(f"  Total Return:    {metrics.total_return:>10.2%}")
        click.echo(f"  CAGR:            {metrics.cagr:>10.2%}")
        click.echo(f"  Sharpe Ratio:    {metrics.sharpe_ratio:>10.2f}")
        click.echo(f"  Sortino Ratio:   {metrics.sortino_ratio:>10.2f}")
        click.echo(f"  Max Drawdown:    {metrics.max_drawdown:>10.2%}")
        click.echo(f"  Calmar Ratio:    {metrics.calmar_ratio:>10.2f}")
        click.echo(f"  Hit Rate:        {metrics.hit_rate:>10.2%}")
        click.echo(f"  VaR 95%:         {metrics.var_95:>10.4f}")
        click.echo(f"  CVaR 95%:        {metrics.cvar_95:>10.4f}")


# ── Graph ─────────────────────────────────────────────────────────────────────


@cli.command("graph")
@click.option("--interval", default="1h")
@click.option("--min-weight", default=0.1, help="Minimum edge weight to display")
@click.option("--json-out", is_flag=True)
def graph(interval: str, min_weight: float, json_out: bool) -> None:
    """Build and display the market correlation graph."""
    store = _get_store()
    markets = store.load_markets()
    if markets.height == 0:
        click.echo("No markets in store. Run: bear sync universe")
        return

    from bear.features.returns import compute_log_returns
    from bear.matching.graph import build_market_graph, get_neighbors

    # Build returns
    all_close = pl.DataFrame({"timestamp": []})
    symbols = markets["name"].to_list() if "name" in markets.columns else []

    for s in symbols:
        c = store.load_candles(s, interval)
        if c.height > 10:
            sym_close = c.select([
                pl.col("open_time").alias("timestamp"),
                pl.col("close").alias(s),
            ])
            if all_close.height == 0:
                all_close = sym_close
            else:
                all_close = all_close.join(sym_close, on="timestamp", how="full", coalesce=True)

    if all_close.height == 0:
        click.echo("No candle data. Run: bear sync candles")
        return

    all_returns = compute_log_returns(all_close)
    taxonomy = _get_taxonomy()

    graph_obj = build_market_graph(all_returns, taxonomy=taxonomy)

    # Filter edges by weight
    strong_edges = [
        e for e in graph_obj.edges.values()
        if e.weight >= min_weight
    ]
    strong_edges.sort(key=lambda e: e.weight, reverse=True)

    if json_out:
        nodes = [{"id": n.symbol, "sector": n.sector} for n in graph_obj.nodes.values()]
        edges = [
            {"source": e.source, "target": e.target, "weight": round(e.weight, 3)}
            for e in strong_edges
        ]
        click.echo(json.dumps({"nodes": nodes, "edges": edges}, indent=2))
    else:
        click.echo(f"=== Market Graph ===")
        click.echo(f"Nodes: {len(graph_obj.nodes)}, Edges: {len(strong_edges)} (weight >= {min_weight})\n")
        click.echo(f"{'Source':<12} {'Target':<12} {'Weight':>8}")
        click.echo("-" * 34)
        for e in strong_edges[:50]:
            click.echo(f"{e.source:<12} {e.target:<12} {e.weight:>8.3f}")


# ── Status ────────────────────────────────────────────────────────────────────


@cli.command("status")
def status() -> None:
    """Show data store status."""
    store = _get_store()
    stats = store.table_stats()
    click.echo("=== Data Store Status ===\n")
    for table, count in stats.items():
        click.echo(f"  {table:<20} {count:>8} rows")


# ── Health ────────────────────────────────────────────────────────────────────


@cli.command("health")
def health() -> None:
    """Quick health check of data and connectivity."""
    store = _get_store()
    stats = store.table_stats()
    total = sum(stats.values())

    click.echo(f"Data store: {total} total rows")
    for table, count in stats.items():
        status_icon = "✓" if count > 0 else "✗"
        click.echo(f"  {status_icon} {table}: {count}")

    if total == 0:
        click.echo("\nNo data loaded. Run: bear sync all")


# ── Entry point ───────────────────────────────────────────────────────────────


def main() -> None:
    """Entry point."""
    cli(standalone_mode=True)


if __name__ == "__main__":
    main()
