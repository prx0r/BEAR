"""SocialData.tools provider — $0.20/1k, deposit any amount, best fallback."""

from __future__ import annotations

import time
from typing import Optional
from datetime import datetime

import httpx

from bear.social.x_reader import XProvider, Tweet, SearchResponse


class SocialData(XProvider):
    """SocialData.tools — https://socialdata.tools"""

    name = "socialdata"
    BASE_URL = "https://api.socialdata.tools/twitter"
    COST_PER_TWEET = 0.0002  # $0.20 / 1k

    def __init__(self, api_key: str, timeout: float = 10.0):
        self.api_key = api_key
        self.timeout = timeout
        self._client = httpx.Client(
            base_url=self.BASE_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )

    def search(
        self,
        query: str,
        limit: int = 20,
        cursor: str = "",
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> SearchResponse:
        """Search tweets."""
        params = {"query": query, "type": "Latest"}
        if since:
            params["start_time"] = since.isoformat()
        if until:
            params["end_time"] = until.isoformat()
        if cursor:
            params["cursor"] = cursor

        resp = self._client.get("/search", params=params)
        resp.raise_for_status()
        data = resp.json()

        tweets_data = data.get("tweets", data.get("statuses", []))
        tweets = [self._normalize_tweet(t) for t in tweets_data]

        next_cursor = data.get("next_cursor", data.get("cursor", ""))
        has_next = bool(next_cursor) or len(tweets) >= limit

        return SearchResponse(
            tweets=tweets[:limit],
            next_cursor=next_cursor,
            has_next=has_next,
            provider=self.name,
            cost_usd=len(tweets) * self.COST_PER_TWEET,
        )

    def user_posts(
        self,
        username: str,
        limit: int = 20,
        cursor: str = "",
    ) -> SearchResponse:
        """Get user timeline."""
        # SocialData uses search for user timelines
        query = f"from:{username}"
        return self.search(query, limit=limit, cursor=cursor)

    def get_post(self, tweet_id: str) -> Optional[Tweet]:
        """Get single tweet by ID."""
        resp = self._client.get(f"/tweet/{tweet_id}")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()
        return self._normalize_tweet(data)

    def get_thread(self, tweet_id: str, limit: int = 20) -> list[Tweet]:
        """Get thread by navigating parent tweets."""
        post = self.get_post(tweet_id)
        if not post:
            return []

        thread = [post]
        current = post.raw
        for _ in range(limit - 1):
            parent_id = current.get("in_reply_to_status_id_str") or current.get("in_reply_to_tweet_id")
            if not parent_id:
                break
            parent = self.get_post(parent_id)
            if not parent:
                break
            thread.insert(0, parent)
            current = parent.raw
            time.sleep(0.1)

        return thread[:limit]

    def get_replies(self, tweet_id: str, limit: int = 20, cursor: str = "") -> SearchResponse:
        """Get replies via search."""
        query = f"conversation_id:{tweet_id}"
        return self.search(query, limit=limit, cursor=cursor)

    def _normalize_tweet(self, d: dict) -> Tweet:
        """SocialData uses slightly different field names."""
        user = d.get("user", d.get("author", {}))
        return Tweet(
            id=str(d.get("id_str", d.get("id", ""))),
            text=d.get("full_text", d.get("text", "")),
            author=user.get("screen_name", user.get("username", "")),
            author_name=user.get("name", ""),
            likes=d.get("favorite_count", d.get("likes", 0)),
            retweets=d.get("retweet_count", d.get("retweets", 0)),
            replies=d.get("reply_count", d.get("replies", 0)),
            views=d.get("views", d.get("view_count", 0)),
            url=f"https://x.com/{user.get('screen_name', '_')}/status/{d.get('id_str', d.get('id', ''))}",
            raw=d,
        )
