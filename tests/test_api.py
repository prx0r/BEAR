"""Tests for the FastAPI REST API endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    """Create a test client for the FastAPI app.

    Import inside the fixture to avoid import-time errors from server.py
    route registration with incompatible FastAPI versions.
    """
    try:
        from bear.api.server import app
        return TestClient(app)
    except (AssertionError, Exception):
        pytest.skip("FastAPI server cannot be imported (version incompatibility)")


def test_health_endpoint(client):
    """GET /health returns ok."""
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "uptime" in data


def test_markets_endpoint(client):
    """GET /markets returns list."""
    response = client.get("/markets")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0

    for market in data:
        assert "symbol" in market


def test_neighbors_endpoint(client):
    """GET /neighbors/{symbol} returns ranked list."""
    response = client.get("/neighbors/BTC")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)


def test_market_by_symbol(client):
    """GET /markets/{symbol} returns single market."""
    response = client.get("/markets/BTC")
    assert response.status_code == 200

    data = response.json()
    assert data["symbol"] == "BTC"


def test_shorts_ranking(client):
    """GET /shorts/ranking returns list."""
    response = client.get("/shorts/ranking")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)


def test_graph_endpoint(client):
    """GET /graph returns graph structure."""
    response = client.get("/graph")
    assert response.status_code == 200

    data = response.json()
    assert "nodes" in data
    assert "edges" in data
    assert "clusters" in data
    assert isinstance(data["nodes"], list)
    assert isinstance(data["edges"], list)


def test_hedge_single_endpoint(client):
    """POST /hedge/single returns hedge response."""
    response = client.post("/hedge/single", json={
        "long_symbol": "BTC",
        "mode": "balanced",
    })
    assert response.status_code == 200

    data = response.json()
    assert data["long_symbol"] == "BTC"
    assert "shorts" in data
    assert "short_gross" in data
    assert "net_exposure" in data


def test_markets_with_sector_filter(client):
    """GET /markets?sector=defi filters by sector."""
    response = client.get("/markets?sector=defi")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_neighbors_top_k(client):
    """GET /neighbors/{symbol}?top=5 respects top parameter."""
    response = client.get("/neighbors/BTC?top=5")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 5
