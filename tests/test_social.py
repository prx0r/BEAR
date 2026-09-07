"""Tests for XReader social module."""

import os
import pytest
from unittest.mock import patch, MagicMock

from bear.social.x_reader import XReader, Tweet, SearchResponse, XProvider
from bear.social.providers.twitter_api import TwitterAPI
from bear.social.providers.getxapi import GetXAPI
from bear.social.providers.social_data import SocialData


def test_tweet_from_dict():
    """Test Tweet normalization."""
    t = Tweet.from_dict({
        "id": "123456",
        "text": "Hello world",
        "author": "testuser",
        "favorite_count": 42,
        "retweet_count": 10,
    })
    assert t.id == "123456"
    assert t.text == "Hello world"
    assert t.author == "testuser"
    assert t.likes == 42
    assert t.retweets == 10


def test_search_response():
    """Test SearchResponse dataclass."""
    resp = SearchResponse(
        tweets=[Tweet(id="1", text="test", author="user")],
        has_next=True,
        provider="test",
        cost_usd=0.001,
    )
    assert len(resp.tweets) == 1
    assert resp.has_next is True
    assert resp.cost_usd == 0.001


def test_xreader_empty_providers():
    """Test XReader with no providers raises on search."""
    reader = XReader(providers=[])
    with pytest.raises(RuntimeError, match="All providers failed"):
        reader.search("test")


def test_xreader_failover():
    """Test XReader falls through to next provider on failure."""
    class FailProvider(XProvider):
        name = "fail"
        def search(self, *a, **kw):
            raise Exception("API error")
        def user_posts(self, *a, **kw):
            raise Exception("API error")
        def get_post(self, *a):
            raise Exception("API error")

    class OKProvider(XProvider):
        name = "ok"
        def search(self, query, limit=20, cursor="", since=None, until=None):
            return SearchResponse(
                tweets=[Tweet(id="1", text="ok", author="test")],
                provider="ok",
            )
        def user_posts(self, username, limit=20, cursor=""):
            return SearchResponse(tweets=[], provider="ok")
        def get_post(self, tweet_id):
            return Tweet(id=tweet_id, text="ok", author="test")

    reader = XReader(providers=[FailProvider(), OKProvider()])
    result = reader.search("test")
    assert result.provider == "ok"
    assert reader.active_provider == "ok"


def test_twitterapi_client():
    """Test TwitterAPI client instantiation."""
    client = TwitterAPI(api_key="test-key")
    assert client.name == "twitterapi"
    assert client.COST_PER_TWEET == 0.00015
    client._client.close()


def test_getxapi_client():
    """Test GetXAPI client instantiation."""
    client = GetXAPI(api_key="test-key")
    assert client.name == "getxapi"
    assert client.COST_PER_TWEET == 0.00005
    client._client.close()


def test_socialdata_client():
    """Test SocialData client instantiation."""
    client = SocialData(api_key="test-key")
    assert client.name == "socialdata"
    assert client.COST_PER_TWEET == 0.0002
    client._client.close()
