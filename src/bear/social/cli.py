"""XReader CLI — search X/Twitter from the command line."""

import os
import sys
import json
import click


@click.group()
def cli():
    """X/Twitter search tool."""
    pass


@cli.command()
@click.argument("query")
@click.option("--limit", "-n", default=10, help="Number of tweets")
@click.option("--provider", "-p", default=None, help="Force specific provider")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def search(query: str, limit: int, provider: str, as_json: bool):
    """Search tweets."""
    from bear.social.x_reader import XReader
    from bear.social.providers import TwitterAPI, GetXAPI, SocialData

    providers = _load_providers(provider)
    if not providers:
        click.echo("No API keys found. Set TWITTERAPI_KEY, GETXAPI_KEY, or SOCIALDATA_KEY.", err=True)
        sys.exit(1)

    reader = XReader(providers=providers)
    results = reader.search(query, limit=limit)

    if as_json:
        click.echo(json.dumps({
            "provider": results.provider,
            "cost_usd": results.cost_usd,
            "tweets": [
                {
                    "id": t.id,
                    "author": t.author,
                    "text": t.text[:200],
                    "likes": t.likes,
                    "retweets": t.retweets,
                    "url": t.url,
                }
                for t in results.tweets
            ],
        }, indent=2))
    else:
        click.echo(f"Provider: {results.provider} | Cost: ${results.cost_usd:.4f} | Tweets: {len(results.tweets)}")
        click.echo("-" * 80)
        for t in results.tweets:
            click.echo(f"@{t.author}: {t.text[:120]}")
            click.echo(f"  {t.url} | {t.likes} likes | {t.retweets} RT")
            click.echo()


@cli.command()
@click.argument("username")
@click.option("--limit", "-n", default=10, help="Number of tweets")
@click.option("--provider", "-p", default=None, help="Force specific provider")
def timeline(username: str, limit: int, provider: str):
    """Get user timeline."""
    from bear.social.x_reader import XReader

    providers = _load_providers(provider)
    if not providers:
        click.echo("No API keys found.", err=True)
        sys.exit(1)

    reader = XReader(providers=providers)
    results = reader.user_posts(username, limit=limit)

    click.echo(f"Provider: {results.provider} | Cost: ${results.cost_usd:.4f} | Tweets: {len(results.tweets)}")
    click.echo("-" * 80)
    for t in results.tweets:
        click.echo(f"@{t.author}: {t.text[:120]}")
        click.echo(f"  {t.url} | {t.likes} likes | {t.retweets} RT")
        click.echo()


@cli.command()
@click.argument("tweet_id")
@click.option("--provider", "-p", default=None, help="Force specific provider")
def thread(tweet_id: str, provider: str):
    """Get tweet thread."""
    from bear.social.x_reader import XReader

    providers = _load_providers(provider)
    if not providers:
        click.echo("No API keys found.", err=True)
        sys.exit(1)

    reader = XReader(providers=providers)
    tweets = reader.get_thread(tweet_id)

    click.echo(f"Thread ({len(tweets)} tweets):")
    click.echo("-" * 80)
    for t in tweets:
        click.echo(f"@{t.author}: {t.text[:120]}")
        click.echo(f"  {t.url}")
        click.echo()


@cli.command()
@click.option("--provider", "-p", default=None, help="Force specific provider")
def benchmark(provider: str):
    """Benchmark all providers with the same query."""
    from bear.social.x_reader import XReader

    providers = _load_providers(provider)
    if len(providers) < 2:
        click.echo("Need at least 2 providers to benchmark.", err=True)
        sys.exit(1)

    query = "BTC lang:en -filter:nativeretweets"
    click.echo(f"Benchmarking query: {query}")
    click.echo("=" * 80)

    for p in providers:
        reader = XReader(providers=[p])
        try:
            results = reader.search(query, limit=10)
            click.echo(f"\n{p.name}:")
            click.echo(f"  Tweets: {len(results.tweets)}")
            click.echo(f"  Cost: ${results.cost_usd:.4f}")
            if results.tweets:
                click.echo(f"  Sample: @{results.tweets[0].author}: {results.tweets[0].text[:80]}")
        except Exception as e:
            click.echo(f"\n{p.name}: FAILED — {e}")


def _load_providers(force: str = None) -> list:
    """Load available providers."""
    from bear.social.providers import TwitterAPI, GetXAPI, SocialData

    providers = []
    mapping = {
        "twitterapi": ("TWITTERAPI_KEY", TwitterAPI),
        "getxapi": ("GETXAPI_KEY", GetXAPI),
        "socialdata": ("SOCIALDATA_KEY", SocialData),
    }

    if force:
        key_name, cls = mapping.get(force, (None, None))
        if key_name and cls:
            key = os.environ.get(key_name)
            if key:
                providers.append(cls(api_key=key))
        return providers

    for name, (key_name, cls) in mapping.items():
        key = os.environ.get(key_name)
        if key:
            providers.append(cls(api_key=key))

    return providers


if __name__ == "__main__":
    cli()
