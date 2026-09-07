"""NLP signal extraction from CT tweets."""

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from signal_schema import Signal, Direction, Timeframe, Confidence, SignalType, PriceLevel


# Keyword patterns
BULLISH_PATTERNS = [
    r'\blong\b', r'\blongs\b', r'\blonging\b', r'\blonged\b',
    r'\bbuy\b', r'\bbuying\b', r'\bbought\b',
    r'\bbull\b', r'\bbullish\b', r'\bmoon\b', r'\brip\b',
    r'\bbreakout\b', r'\bupside\b', r'\baccumulate\b',
]

BEARISH_PATTERNS = [
    r'\bshort\b', r'\bshorts\b', r'\bshorting\b', r'\bshorted\b',
    r'\bsell\b', r'\bselling\b', r'\bsold\b',
    r'\bbear\b', r'\bbearish\b', r'\bdump\b', r'\breject\b',
    r'\bdownside\b', r'\bcorrection\b',
]

TIMEFRAME_PATTERNS = {
    Timeframe.M15: [r'\bm15\b', r'\b15m\b', r'\b15 min\b'],
    Timeframe.M30: [r'\bm30\b', r'\b30m\b', r'\b30 min\b', r'\bscalp\b'],
    Timeframe.H1: [r'\bh1\b', r'\b1h\b', r'\bhourly\b'],
    Timeframe.H4: [r'\bh4\b', r'\b4h\b', r'\b4 hourly\b', r'\b4h timeframe\b'],
    Timeframe.D1: [r'\bdaily\b', r'\bday\b', r'\btoday\b'],
    Timeframe.W1: [r'\bweekly\b', r'\bweek\b', r'\b50wma\b', r'\b50w\b'],
    Timeframe.MN1: [r'\bmonthly\b', r'\bmonth\b', r'\bmacro\b'],
}

LEVEL_PATTERNS = [
    r'(\d{1,3}[,.]?\d{3,4})\s*(?:k|K)?\s*(?:support|res|resistance|level|entry|tp|sl|target|stop)',
    r'(?:support|res|resistance|level|entry|tp|sl|target|stop)\s*(?:at|@)?\s*(\d{1,3}[,.]?\d{3,4})\s*(?:k|K)?',
    r'(\d{1,3}[,.]?\d{3,4})\s*k\b',
]

ASSET_PATTERNS = {
    "BTC": [r'\$btc\b', r'\bbtc\b', r'\bbitcoin\b'],
    "ETH": [r'\$eth\b', r'\beth\b', r'\bethereum\b'],
    "SOL": [r'\$sol\b', r'\bsol\b', r'\bsolana\b'],
}


def extract_price(text: str) -> list[float]:
    """Extract price levels from text."""
    prices = []
    # Match patterns like 81k, 78,500, 81000
    for match in re.finditer(r'(\d{1,3}[,.]?\d{3,4})\s*(k|K)?', text):
        num_str = match.group(1).replace(',', '')
        try:
            num = float(num_str)
            if match.group(2):  # has 'k' suffix
                num *= 1000
            if 1000 < num < 500000:  # reasonable BTC price range
                prices.append(num)
        except ValueError:
            pass
    return prices


def extract_signal(text: str, author: str, tweet: dict) -> Signal:
    """Extract a structured signal from a tweet."""
    lower = text.lower()

    # Detect direction
    direction = Direction.NEUTRAL
    bull_score = sum(1 for p in BULLISH_PATTERNS if re.search(p, lower))
    bear_score = sum(1 for p in BEARISH_PATTERNS if re.search(p, lower))

    if bull_score > bear_score and bull_score >= 1:
        direction = Direction.LONG
    elif bear_score > bull_score and bear_score >= 1:
        direction = Direction.SHORT

    # Detect timeframe
    timeframe = Timeframe.D1
    for tf, patterns in TIMEFRAME_PATTERNS.items():
        if any(re.search(p, lower) for p in patterns):
            timeframe = tf
            break

    # Detect asset
    asset = "BTC"
    for a, patterns in ASSET_PATTERNS.items():
        if any(re.search(p, lower) for p in patterns):
            asset = a
            break

    # Extract price levels
    prices = extract_price(text)
    levels = []
    for p in prices:
        label = "level"
        if any(w in lower for w in ["support", "buy zone", "accumulate"]):
            label = "support"
        elif any(w in lower for w in ["resist", "sell zone", "tp", "target"]):
            label = "resistance"
        levels.append(PriceLevel(price=p, label=label, timeframe=timeframe.value))

    # Detect signal type
    signal_type = SignalType.OUTLOOK
    if any(w in lower for w in ["entry", "enter", "buying at", "longing at"]):
        signal_type = SignalType.ENTRY
    elif any(w in lower for w in ["exit", "tp", "take profit", "closing", "sold"]):
        signal_type = SignalType.EXIT
    elif any(w in lower for w in ["update", "still holding", "reminder"]):
        signal_type = SignalType.UPDATE

    # Confidence based on specificity
    confidence = Confidence.MEDIUM
    specificity = 0
    if prices:
        specificity += 1
    if signal_type == SignalType.ENTRY:
        specificity += 1
    if bull_score + bear_score >= 2:
        specificity += 1
    if specificity >= 2:
        confidence = Confidence.HIGH
    elif specificity == 0:
        confidence = Confidence.LOW

    # Generate thesis
    thesis = text[:200].replace('\n', ' ')

    return Signal(
        author=author,
        tweet_id=tweet.get("id", ""),
        tweet_url=tweet.get("url", ""),
        tweet_time=tweet.get("created_at", ""),
        extracted_at=datetime.now(timezone.utc).isoformat(),
        direction=direction,
        signal_type=signal_type,
        timeframe=timeframe,
        confidence=confidence,
        levels=levels,
        asset=asset,
        thesis=thesis,
        text_preview=text[:200],
        likes=tweet.get("likes", 0),
        retweets=tweet.get("retweets", 0),
        views=tweet.get("views", 0),
    )


def extract_signals_from_tweets(tweets: dict) -> list[Signal]:
    """Extract signals from all tweets across accounts."""
    all_signals = []

    for handle, account_data in tweets.items():
        for tweet in account_data.get("tweets", []):
            text = tweet.get("text", "")
            if not text or tweet.get("is_reply"):
                continue

            signal = extract_signal(text, handle, tweet)
            if signal.direction != Direction.NEUTRAL:
                all_signals.append(signal)

    return all_signals


def main():
    """Extract signals from current tweets."""
    import json

    current_path = Path(__file__).parent / "data" / "current_tweets.json"
    if not current_path.exists():
        print("No current_tweets.json found. Run fetcher.py first.")
        return

    with open(current_path) as f:
        tweets = json.load(f)

    signals = extract_signals_from_tweets(tweets)

    print(f"Extracted {len(signals)} signals from {len(tweets)} accounts\n")

    for s in signals:
        print(f"@{s.author}: {s.direction.value} {s.asset} ({s.timeframe.value})")
        print(f"  Confidence: {s.confidence.value}")
        print(f"  Levels: {[f'{l.price:.0f} ({l.label})' for l in s.levels]}")
        print(f"  Thesis: {s.thesis[:100]}...")
        print()

    # Save signals
    out_path = Path(__file__).parent / "data" / "signals.jsonl"
    with open(out_path, "a") as f:
        for s in signals:
            f.write(json.dumps(s.to_dict()) + "\n")
    print(f"Signals appended to {out_path}")


if __name__ == "__main__":
    main()
