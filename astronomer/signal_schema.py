"""Structured signal format for CT signal processing."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional
from enum import Enum


class Direction(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"


class Timeframe(Enum):
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "daily"
    W1 = "weekly"
    MN1 = "monthly"


class Confidence(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SignalType(Enum):
    ENTRY = "entry"
    EXIT = "exit"
    UPDATE = "update"
    OUTLOOK = "outlook"
    LEVEL = "level"


@dataclass
class PriceLevel:
    """A specific price level."""
    price: float
    label: str = ""  # support, resistance, entry, tp, sl
    timeframe: str = ""


@dataclass
class Signal:
    """A structured trading signal from a CT account."""
    # Identity
    id: str = ""
    author: str = ""
    tweet_id: str = ""
    tweet_url: str = ""

    # Timestamps
    tweet_time: str = ""
    extracted_at: str = ""

    # Signal content
    direction: Direction = Direction.NEUTRAL
    signal_type: SignalType = SignalType.OUTLOOK
    timeframe: Timeframe = Timeframe.D1
    confidence: Confidence = Confidence.MEDIUM

    # Price levels
    levels: list[PriceLevel] = field(default_factory=list)
    entry: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

    # Context
    asset: str = "BTC"
    thesis: str = ""
    text_preview: str = ""

    # Engagement (signal quality proxy)
    likes: int = 0
    retweets: int = 0
    views: int = 0

    def to_dict(self) -> dict:
        """Convert to dict for JSON serialization."""
        d = asdict(self)
        d["direction"] = self.direction.value
        d["signal_type"] = self.signal_type.value
        d["timeframe"] = self.timeframe.value
        d["confidence"] = self.confidence.value
        return d

    @classmethod
    def from_dict(cls, d: dict) -> Signal:
        """Parse from dict."""
        return cls(
            id=d.get("id", ""),
            author=d.get("author", ""),
            tweet_id=d.get("tweet_id", ""),
            tweet_url=d.get("tweet_url", ""),
            tweet_time=d.get("tweet_time", ""),
            extracted_at=d.get("extracted_at", ""),
            direction=Direction(d.get("direction", "neutral")),
            signal_type=SignalType(d.get("signal_type", "outlook")),
            timeframe=Timeframe(d.get("timeframe", "daily")),
            confidence=Confidence(d.get("confidence", "medium")),
            levels=[PriceLevel(**l) for l in d.get("levels", [])],
            entry=d.get("entry"),
            stop_loss=d.get("stop_loss"),
            take_profit=d.get("take_profit"),
            asset=d.get("asset", "BTC"),
            thesis=d.get("thesis", ""),
            text_preview=d.get("text_preview", ""),
            likes=d.get("likes", 0),
            retweets=d.get("retweets", 0),
            views=d.get("views", 0),
        )


@dataclass
class ConfluenceScore:
    """Multi-account agreement on a signal."""
    direction: Direction
    asset: str
    timeframe: str
    accounts_aligned: list[str] = field(default_factory=list)
    total_weight: float = 0.0
    signal_count: int = 0
    avg_confidence: float = 0.0
    strength: str = "none"  # none, weak, moderate, strong

    def to_dict(self) -> dict:
        d = asdict(self)
        d["direction"] = self.direction.value
        return d
