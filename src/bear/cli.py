"""Click CLI for BEAR (Section 51)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import click
import yaml

from bear import __version__


@click.group()
@click.version_option(__version__, prog_name="bear")
@click.option("--config", "config_path", default="config/default.yaml", help="Config file path")
@click.pass_context
def cli(ctx: click.Context, config_path: str) -> None:
    """BEAR — Hyperliquid relative-value trading engine."""
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config_path
    try:
        with open(config_path) as f:
            ctx.obj["config"] = yaml.safe_load(f)
    except FileNotFoundError:
        ctx.obj["config"] = {}


# ── Sync ─────────────────────────────────────────────────────────────────────


@cli.group()
def sync() -> None:
    """Sync market data from Hyperliquid."""


@sync.command("universe")
@click.option("--save", default="data/universe.json", help="Output path")
def sync_universe(save: str) -> None:
    """Sync current Hyperliquid universe."""
    click.echo(f"Syncing universe to {save}...")
    # Placeholder — real impl calls hyperliquid API
    click.echo("Done. (Implement Hyperliquid API client)")


@sync.command("candles")
@click.option("--symbols", multiple=True, help="Symbols to sync")
@click.option("--start", help="Start date YYYY-MM-DD")
@click.option("--end", help="End date YYYY-MM-DD")
def sync_candles(symbols: tuple, start: str, end: str) -> None:
    """Sync OHLCV candle data."""
    click.echo(f"Syncing candles for {len(symbols)} symbols...")
    for sym in symbols:
        click.echo(f"  {sym}: {start} → {end}")
    click.echo("Done.")


@sync.command("funding")
@click.option("--symbols", multiple=True, help="Symbols to sync")
def sync_funding(symbols: tuple) -> None:
    """Sync funding rate history."""
    click.echo(f"Syncing funding for {len(symbols)} symbols...")
    click.echo("Done.")


@sync.command("all")
@click.pass_context
def sync_all(ctx: click.Context) -> None:
    """Sync universe, candles, and funding."""
    ctx.invoke(sync_universe, save="data/universe.json")
    ctx.invoke(sync_candles, symbols=(), start="", end="")
    ctx.invoke(sync_funding, symbols=())


# ── Markets ───────────────────────────────────────────────────────────────────


@cli.command("markets")
@click.option("--json-out", is_flag=True, help="Output as JSON")
def markets(json_out: bool) -> None:
    """List current Hyperliquid markets."""
    click.echo("Fetching markets...")
    # Placeholder
    click.echo("Markets: (implement Hyperliquid API)")


@cli.command("inspect")
@click.argument("symbol")
def inspect(symbol: str) -> None:
    """Inspect a single market's details."""
    click.echo(f"Inspecting {symbol}...")
    click.echo(f"  Symbol: {symbol}")
    click.echo("  (Implement detailed market data)")


# ── Neighbors ─────────────────────────────────────────────────────────────────


@cli.command("neighbors")
@click.argument("symbol")
@click.option("--top", default=10, help="Number of neighbors")
def neighbors(symbol: str, top: int) -> None:
    """Find correlated neighboring assets."""
    click.echo(f"Finding {top} neighbors for {symbol}...")
    click.echo("  (Implement correlation analysis)")


# ── Ranking ───────────────────────────────────────────────────────────────────


@cli.command("rank-shorts")
@click.option("--sector", help="Filter by sector")
@click.option("--top", default=20, help="Number of results")
@click.option("--json-out", is_flag=True)
def rank_shorts(sector: Optional[str], top: int, json_out: bool) -> None:
    """Rank available short candidates."""
    click.echo(f"Ranking shorts (sector={sector}, top={top})...")
    click.echo("  (Implement short ranking)")


# ── Recommend ─────────────────────────────────────────────────────────────────


@cli.command("recommend")
@click.option("--long", "long_symbol", help="Single long symbol")
@click.option("--portfolio", "portfolio_path", help="Portfolio YAML path")
@click.option("--mode", default="balanced", type=click.Choice(["aggressive", "balanced", "conservative"]))
@click.pass_context
def recommend(ctx: click.Context, long_symbol: Optional[str], portfolio_path: Optional[str], mode: str) -> None:
    """Recommend hedge portfolio for longs."""
    if portfolio_path:
        with open(portfolio_path) as f:
            port = yaml.safe_load(f)
        click.echo(f"Portfolio from {portfolio_path}:")
        for sym, weight in port.get("longs", {}).items():
            click.echo(f"  {sym}: {weight:.0%}")
    elif long_symbol:
        click.echo(f"Recommending hedge for {long_symbol} (mode={mode})...")
    else:
        click.echo("Specify --long SYMBOL or --portfolio PATH")
        return

    click.echo("  (Implement hedge recommendation)")


# ── Backtest ──────────────────────────────────────────────────────────────────


@cli.command("backtest")
@click.option("--long", "long_symbol", required=True, help="Long symbol")
@click.option("--start", help="Start date YYYY-MM-DD")
@click.option("--end", help="End date YYYY-MM-DD")
@click.option("--mode", default="balanced", type=click.Choice(["aggressive", "balanced", "conservative"]))
@click.option("--json-out", is_flag=True)
def backtest(long_symbol: str, start: Optional[str], end: Optional[str], mode: str, json_out: bool) -> None:
    """Run backtest for a long-short pair."""
    click.echo(f"Backtesting {long_symbol} ({start} → {end}, mode={mode})...")
    click.echo("  (Implement backtest engine)")


# ── Dispersion ────────────────────────────────────────────────────────────────


@cli.command("dispersion")
@click.option("--sector", required=True, help="Sector to analyze")
@click.option("--lookback", default=30, help="Lookback days")
def dispersion(sector: str, lookback: int) -> None:
    """Analyze sector dispersion for relative-value opportunities."""
    click.echo(f"Dispersion analysis for {sector} (lookback={lookback}d)...")
    click.echo("  (Implement dispersion analysis)")


# ── Report ────────────────────────────────────────────────────────────────────


@cli.command("report")
@click.option("--output", default="report.md", help="Report output path")
def report(output: str) -> None:
    """Generate performance and risk report."""
    click.echo(f"Generating report to {output}...")
    click.echo("  (Implement report generation)")


def main() -> None:
    """Entry point."""
    cli(standalone_mode=True)


if __name__ == "__main__":
    main()
