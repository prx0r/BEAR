"""GetXAPI provider — $0.05/1k, cheapest, $0.10 free credit."""

from __future__ import annotations

import time
from typing import Optional
from datetime import datetime

import httpx

from bear.social.x_reader import XProvider, Tweet, SearchResponse


class GetXAPI(XProvider):
    """GetXAPI — https://www.getxapi.com"""

    name = "getxapi"
    BASE_URL = "https://api.getxapi.com/twitter"
    COST_PER_TWEET = 0.00005  # $0.05 / 1k

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
        """Advanced search."""
        params = {
            "q": query,
            "product": "Latest",
            "count": min(limit, 20),
        }
        if since:
            params["since_time"] = since.strftime("%Y-%m-%d_%H:%M:%S_UTC")
        if until:
            params["until_time"] = until.strftime("%Y-%m-%d_%H:%M:%S_UTC")
        if cursor:
            params["cursor"] = cursor

        resp = self._client.get("/tweet/advanced_search", params=params)
        resp.raise_for_status()
        data = resp.json()

        tweets = [Tweet.from_dict(t) for t in data.get("tweets", data.get("data", []))]
        next_cursor = data.get("next_cursor", data.get("cursor", ""))
        has_next = data.get("has_next_page", bool(next_cursor))

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
        params = {
            "q": f"from:{username}",
            "product": "Latest",
            "count": min(limit, 20),
        }
        if cursor:
            params["cursor"] = cursor

        resp = self._client.get("/tweet/advanced_search", params=params)
        resp.raise_for_status()
        data = resp.json()

        tweets = [Tweet.from_dict(t) for t in data.get("tweets", data.get("data", []))]
        next_cursor = data.get("next_cursor", data.get("cursor", ""))
        has_next = data.get("has_next_page", bool(next_cursor))

        return SearchResponse(
            tweets=tweets[:limit],
            next_cursor=next_cursor,
            has_next=has_next,
            provider=self.name,
            cost_usd=len(tweets) * self.COST_PER_TWEET,
        )

    def get_post(self, tweet_id: str) -> Optional[Tweet]:
        """Get single tweet by ID."""
        resp = self._client.get("/tweet/get", params={"tweet_id": tweet_id})
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json().get("tweet", resp.json())
        return Tweet.from_dict(data)

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
        """Get replies via conversation search."""
        query = f"conversation_id:{tweet_id}"
        return self.search(query, limit=limit, cursor=cursor)
