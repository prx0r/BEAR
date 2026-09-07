"""Provider-agnostic X/Twitter reader interface."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional
from datetime import datetime


@dataclass
class Tweet:
    """Normalized tweet representation."""
    id: str
    text: str
    author: str
    author_name: str = ""
    created_at: Optional[datetime] = None
    likes: int = 0
    retweets: int = 0
    replies: int = 0
    views: int = 0
    url: str = ""
    raw: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict) -> "Tweet":
        """Parse from provider-specific dict. Override per provider."""
        # Handle nested author object (GetXAPI style)
        author = d.get("author", {})
        if isinstance(author, dict):
            author_name = author.get("userName", author.get("screen_name", ""))
            display_name = author.get("name", "")
        else:
            author_name = str(author) if author else d.get("user", {}).get("screen_name", d.get("username", ""))
            display_name = d.get("author_name", d.get("user", {}).get("name", ""))

        return cls(
            id=str(d.get("id", d.get("tweet_id", ""))),
            text=d.get("text", d.get("full_text", "")),
            author=author_name,
            author_name=display_name,
            likes=d.get("likes", d.get("favorite_count", d.get("likeCount", 0))),
            retweets=d.get("retweets", d.get("retweet_count", d.get("retweetCount", 0))),
            replies=d.get("replies", d.get("reply_count", d.get("replyCount", 0))),
            views=d.get("views", d.get("view_count", d.get("viewCount", 0))),
            url=d.get("url", ""),
            raw=d,
        )


@dataclass
class SearchResponse:
    """Normalized search result."""
    tweets: list[Tweet]
    next_cursor: str = ""
    has_next: bool = False
    provider: str = ""
    cost_usd: float = 0.0


class XProvider(ABC):
    """Abstract X data provider."""

    name: str = "abstract"

    @abstractmethod
    def search(
        self,
        query: str,
        limit: int = 20,
        cursor: str = "",
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> SearchResponse:
        """Search tweets."""
        ...

    @abstractmethod
    def user_posts(
        self,
        username: str,
        limit: int = 20,
        cursor: str = "",
    ) -> SearchResponse:
        """Get posts from a user."""
        ...

    @abstractmethod
    def get_post(self, tweet_id: str) -> Optional[Tweet]:
        """Get a single tweet by ID."""
        ...

    def get_thread(self, tweet_id: str, limit: int = 20) -> list[Tweet]:
        """Get thread starting at tweet_id. Default: just the tweet."""
        post = self.get_post(tweet_id)
        return [post] if post else []

    def get_replies(self, tweet_id: str, limit: int = 20, cursor: str = "") -> SearchResponse:
        """Get replies to a tweet. Default: empty."""
        return SearchResponse(tweets=[], provider=self.name)


class XReader:
    """
    Provider-agnostic X reader with automatic failover.

    Usage:
        reader = XReader()
        results = reader.search("AI agents lang:en", limit=10)
        for tweet in results.tweets:
            print(f"{tweet.author}: {tweet.text[:100]}")
    """

    def __init__(
        self,
        providers: Optional[list[XProvider]] = None,
        rate_limit_pause: float = 1.0,
    ):
        if providers:
            self.providers = providers
        else:
            self.providers = self._load_default_providers()
        self.rate_limit_pause = rate_limit_pause
        self._last_provider = None

    def _load_default_providers(self) -> list[XProvider]:
        """Load providers from environment variables."""
        providers = []

        # Primary: TwitterAPI.io
        if os.environ.get("TWITTERAPI_KEY"):
            from bear.social.providers import TwitterAPI
            providers.append(TwitterAPI(api_key=os.environ["TWITTERAPI_KEY"]))

        # Secondary: GetXAPI
        if os.environ.get("GETXAPI_KEY"):
            from bear.social.providers import GetXAPI
            providers.append(GetXAPI(api_key=os.environ["GETXAPI_KEY"]))

        # Fallback: SocialData
        if os.environ.get("SOCIALDATA_KEY"):
            from bear.social.providers import SocialData
            providers.append(SocialData(api_key=os.environ["SOCIALDATA_KEY"]))

        return providers

    def search(
        self,
        query: str,
        limit: int = 20,
        cursor: str = "",
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> SearchResponse:
        """Search with automatic failover."""
        last_error = None
        for provider in self.providers:
            try:
                result = provider.search(query, limit, cursor, since, until)
                self._last_provider = provider.name
                return result
            except Exception as e:
                last_error = e
                continue
        raise RuntimeError(f"All providers failed. Last error: {last_error}")

    def user_posts(
        self,
        username: str,
        limit: int = 20,
        cursor: str = "",
    ) -> SearchResponse:
        """Get user posts with automatic failover."""
        last_error = None
        for provider in self.providers:
            try:
                result = provider.user_posts(username, limit, cursor)
                self._last_provider = provider.name
                return result
            except Exception as e:
                last_error = e
                continue
        raise RuntimeError(f"All providers failed. Last error: {last_error}")

    def get_post(self, tweet_id: str) -> Optional[Tweet]:
        """Get single tweet with automatic failover."""
        for provider in self.providers:
            try:
                result = provider.get_post(tweet_id)
                if result:
                    self._last_provider = provider.name
                    return result
            except Exception:
                continue
        return None

    def get_thread(self, tweet_id: str, limit: int = 20) -> list[Tweet]:
        """Get thread with automatic failover."""
        for provider in self.providers:
            try:
                result = provider.get_thread(tweet_id, limit)
                if result:
                    self._last_provider = provider.name
                    return result
            except Exception:
                continue
        return []

    def get_replies(self, tweet_id: str, limit: int = 20, cursor: str = "") -> SearchResponse:
        """Get replies with automatic failover."""
        for provider in self.providers:
            try:
                result = provider.get_replies(tweet_id, limit, cursor)
                if result.tweets:
                    self._last_provider = provider.name
                    return result
            except Exception:
                continue
        return SearchResponse(tweets=[], provider="none")

    @property
    def active_provider(self) -> str:
        """Name of the last successful provider."""
        return self._last_provider or "none"
