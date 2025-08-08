"""Tests for Polygon.io API client."""

import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
import websockets

from app.market_data.polygon_client import (
    PolygonClient,
    MAJOR_INDICES
)


@pytest.fixture
async def polygon_client():
    """Create Polygon client instance for testing."""
    client = PolygonClient(
        api_key="test_api_key",
        plan_tier="starter"
    )
    await client.connect()
    yield client
    await client.disconnect()


@pytest.mark.asyncio
async def test_client_initialization():
    """Test Polygon client initialization with different plan tiers."""
    # Test starter tier
    client = PolygonClient(api_key="test_key", plan_tier="starter")
    assert client.requests_per_second == 5/60
    
    # Test developer tier
    client = PolygonClient(api_key="test_key", plan_tier="developer")
    assert client.requests_per_second == 100/60
    
    # Test advanced tier
    client = PolygonClient(api_key="test_key", plan_tier="advanced")
    assert client.requests_per_second == 1000/60


@pytest.mark.asyncio
async def test_context_manager(polygon_client):
    """Test async context manager functionality."""
    async with PolygonClient(api_key="test_key") as client:
        assert client.session is not None
        
    # After exiting context, session should be closed
    assert client.session is None


@pytest.mark.asyncio
async def test_get_aggregates(polygon_client):
    """Test fetching aggregate bar data."""
    mock_response = {
        "results": [
            {
                "t": 1609459200000,
                "o": 100.0,
                "h": 101.0,
                "l": 99.0,
                "c": 100.5,
                "v": 1000000
            }
        ]
    }
    
    with patch.object(polygon_client, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        
        aggregates = await polygon_client.get_aggregates(
            ticker="AAPL",
            multiplier=1,
            timespan="minute",
            from_date="2024-01-01",
            to_date="2024-01-02"
        )
        
        assert len(aggregates) == 1
        assert aggregates[0]["o"] == 100.0
        
        # Verify request parameters
        call_args = mock_request.call_args
        assert call_args[0][0] == "GET"
        assert "AAPL" in call_args[0][1]
        assert call_args[1]["params"]["limit"] == 5000


@pytest.mark.asyncio
async def test_get_ticker_details(polygon_client):
    """Test fetching ticker details."""
    mock_response = {
        "results": {
            "ticker": "AAPL",
            "name": "Apple Inc.",
            "market": "stocks"
        }
    }
    
    with patch.object(polygon_client, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        
        details = await polygon_client.get_ticker_details("AAPL")
        
        assert details["ticker"] == "AAPL"
        assert details["name"] == "Apple Inc."
        mock_request.assert_called_once_with(
            "GET",
            "/v3/reference/tickers/AAPL"
        )


@pytest.mark.asyncio
async def test_get_snapshot(polygon_client):
    """Test fetching market snapshot."""
    mock_response = {
        "ticker": {
            "day": {
                "o": 100.0,
                "h": 101.0,
                "l": 99.0,
                "c": 100.5
            },
            "lastTrade": {
                "p": 100.5,
                "s": 100
            }
        }
    }
    
    with patch.object(polygon_client, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        
        snapshot = await polygon_client.get_snapshot("AAPL")
        
        assert snapshot["day"]["c"] == 100.5
        assert snapshot["lastTrade"]["p"] == 100.5


@pytest.mark.asyncio
async def test_rate_limiting(polygon_client):
    """Test rate limiting enforcement."""
    with patch.object(polygon_client, "session") as mock_session:
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={"data": "test"})
        mock_response.raise_for_status = MagicMock()
        
        mock_session.request.return_value.__aenter__.return_value = mock_response
        
        # Make multiple rapid requests
        start_time = datetime.now()
        tasks = [
            polygon_client._make_request("GET", "/test")
            for _ in range(2)
        ]
        await asyncio.gather(*tasks)
        elapsed = (datetime.now() - start_time).total_seconds()
        
        # For starter tier (5 req/min), should enforce minimum interval
        expected_interval = 60 / 5  # 12 seconds between requests
        assert elapsed >= (expected_interval - 1)  # Allow 1 second tolerance


@pytest.mark.asyncio
async def test_normalize_trade_data(polygon_client):
    """Test trade data normalization."""
    raw_trade = {
        "ev": "T",
        "sym": "AAPL",
        "t": 1609459200000,
        "p": 100.5,
        "s": 100
    }
    
    normalized = polygon_client._normalize_trade_data(raw_trade)
    
    assert normalized["symbol"] == "AAPL"
    assert normalized["price"] == 100.5
    assert normalized["volume"] == 100
    assert normalized["source"] == "polygon"
    assert normalized["type"] == "trade"


@pytest.mark.asyncio
async def test_normalize_quote_data(polygon_client):
    """Test quote data normalization."""
    raw_quote = {
        "ev": "Q",
        "sym": "AAPL",
        "t": 1609459200000,
        "bp": 100.4,
        "ap": 100.6,
        "bs": 100,
        "as": 200
    }
    
    normalized = polygon_client._normalize_quote_data(raw_quote)
    
    assert normalized["symbol"] == "AAPL"
    assert normalized["bid"] == 100.4
    assert normalized["ask"] == 100.6
    assert normalized["mid"] == 100.5
    assert normalized["bid_size"] == 100
    assert normalized["ask_size"] == 200
    assert normalized["source"] == "polygon"
    assert normalized["type"] == "quote"


@pytest.mark.asyncio
async def test_subscription_management(polygon_client):
    """Test symbol subscription management."""
    # Test adding symbols
    await polygon_client.subscribe_symbols(["AAPL", "GOOGL"])
    assert "AAPL" in polygon_client.subscribed_symbols
    assert "GOOGL" in polygon_client.subscribed_symbols
    
    # Test removing symbols
    await polygon_client.unsubscribe_symbols(["AAPL"])
    assert "AAPL" not in polygon_client.subscribed_symbols
    assert "GOOGL" in polygon_client.subscribed_symbols


@pytest.mark.asyncio
async def test_connection_status(polygon_client):
    """Test connection status checking."""
    # Initially not connected
    assert not polygon_client.is_connected()
    
    # Mock connected state
    mock_connection = MagicMock()
    mock_connection.open = True
    polygon_client.ws_connection = mock_connection
    assert polygon_client.is_connected()
    
    # Mock disconnected state
    mock_connection.open = False
    assert not polygon_client.is_connected()


@pytest.mark.asyncio
async def test_map_index_symbol():
    """Test index symbol mapping."""
    client = PolygonClient(api_key="test_key")
    
    # Test known index mappings
    assert client.map_index_symbol("US30") == "I:DJI"
    assert client.map_index_symbol("NAS100") == "I:NDX"
    assert client.map_index_symbol("SPX500") == "I:SPX"
    
    # Test unknown symbol (should return as-is)
    assert client.map_index_symbol("UNKNOWN") == "UNKNOWN"


@pytest.mark.asyncio
async def test_major_indices_constant():
    """Test that all major indices are defined."""
    expected_indices = {
        "US30": "I:DJI",
        "NAS100": "I:NDX",
        "SPX500": "I:SPX",
        "RUT2000": "I:RUT",
        "VIX": "I:VIX"
    }
    assert MAJOR_INDICES == expected_indices