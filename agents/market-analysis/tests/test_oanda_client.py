"""Tests for OANDA API client."""

import asyncio
import json
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from app.market_data.oanda_client import OANDAClient, FOREX_PAIRS


@pytest.fixture
async def oanda_client():
    """Create OANDA client instance for testing."""
    client = OANDAClient(
        api_key="test_api_key",
        account_id="test_account",
        environment="practice"
    )
    await client.connect()
    yield client
    await client.disconnect()


@pytest.mark.asyncio
async def test_client_initialization():
    """Test OANDA client initialization with different environments."""
    # Test practice environment
    client = OANDAClient(
        api_key="test_key",
        account_id="test_account",
        environment="practice"
    )
    assert client.rest_url == "https://api-fxpractice.oanda.com"
    assert client.stream_url == "https://stream-fxpractice.oanda.com"
    
    # Test live environment
    client = OANDAClient(
        api_key="test_key",
        account_id="test_account",
        environment="live"
    )
    assert client.rest_url == "https://api-fxtrade.oanda.com"
    assert client.stream_url == "https://stream-fxtrade.oanda.com"


@pytest.mark.asyncio
async def test_context_manager(oanda_client):
    """Test async context manager functionality."""
    async with OANDAClient(
        api_key="test_key",
        account_id="test_account"
    ) as client:
        assert client.ws_session is not None
        
    # After exiting context, session should be closed
    assert client.ws_session is None


@pytest.mark.asyncio
async def test_get_instruments(oanda_client):
    """Test fetching tradeable instruments."""
    mock_response = {
        "instruments": [
            {"name": "EUR_USD", "type": "CURRENCY"},
            {"name": "GBP_USD", "type": "CURRENCY"}
        ]
    }
    
    with patch.object(oanda_client, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        
        instruments = await oanda_client.get_instruments()
        
        assert len(instruments) == 2
        assert instruments[0]["name"] == "EUR_USD"
        mock_request.assert_called_once_with(
            "GET",
            "/v3/accounts/test_account/instruments"
        )


@pytest.mark.asyncio
async def test_get_candles(oanda_client):
    """Test fetching historical candlestick data."""
    mock_response = {
        "candles": [
            {
                "time": "2024-01-01T00:00:00Z",
                "mid": {"o": "1.1000", "h": "1.1010", "l": "1.0990", "c": "1.1005"}
            }
        ]
    }
    
    with patch.object(oanda_client, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        
        candles = await oanda_client.get_candles(
            instrument="EUR_USD",
            granularity="M1",
            count=100
        )
        
        assert len(candles) == 1
        assert candles[0]["time"] == "2024-01-01T00:00:00Z"
        
        # Verify request parameters
        call_args = mock_request.call_args
        assert call_args[0][0] == "GET"
        assert "EUR_USD" in call_args[0][1]
        assert call_args[1]["params"]["granularity"] == "M1"
        assert call_args[1]["params"]["count"] == 100


@pytest.mark.asyncio
async def test_rate_limiting(oanda_client):
    """Test rate limiting enforcement."""
    with patch.object(oanda_client, "ws_session") as mock_session:
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={"data": "test"})
        mock_response.raise_for_status = MagicMock()
        
        mock_session.request.return_value.__aenter__.return_value = mock_response
        
        # Make multiple rapid requests
        start_time = datetime.now()
        tasks = [
            oanda_client._make_request("GET", "/test")
            for _ in range(3)
        ]
        await asyncio.gather(*tasks)
        elapsed = (datetime.now() - start_time).total_seconds()
        
        # Should take at least 1 second for 3 requests (rate limit: 2/sec)
        assert elapsed >= 1.0


@pytest.mark.asyncio
async def test_normalize_price_tick(oanda_client):
    """Test price tick normalization."""
    raw_tick = {
        "type": "PRICE",
        "instrument": "EUR_USD",
        "time": "2024-01-01T00:00:00Z",
        "bids": [{"price": "1.0999"}],
        "asks": [{"price": "1.1001"}]
    }
    
    normalized = oanda_client._normalize_price_tick(raw_tick)
    
    assert normalized["symbol"] == "EUR_USD"
    assert normalized["timestamp"] == "2024-01-01T00:00:00Z"
    assert normalized["bid"] == 1.0999
    assert normalized["ask"] == 1.1001
    assert normalized["mid"] == 1.1000
    assert normalized["source"] == "oanda"
    assert normalized["type"] == "tick"


@pytest.mark.asyncio
async def test_stream_prices_with_reconnection(oanda_client):
    """Test price streaming with automatic reconnection."""
    price_data = [
        b'{"type":"PRICE","instrument":"EUR_USD","time":"2024-01-01T00:00:00Z","bids":[{"price":"1.1000"}],"asks":[{"price":"1.1002"}]}\n',
        b'{"type":"HEARTBEAT","time":"2024-01-01T00:00:01Z"}\n'
    ]
    
    mock_response = AsyncMock()
    mock_response.content = AsyncMock()
    mock_response.content.__aiter__.return_value = iter(price_data)
    
    with patch.object(oanda_client.ws_session, "get") as mock_get:
        mock_get.return_value.__aenter__.return_value = mock_response
        
        prices = []
        async for price in oanda_client.stream_prices(["EUR_USD"]):
            prices.append(price)
            if len(prices) >= 1:  # Stop after first price
                break
                
        assert len(prices) == 1
        assert prices[0]["symbol"] == "EUR_USD"
        assert prices[0]["mid"] == 1.1001


@pytest.mark.asyncio
async def test_subscription_management(oanda_client):
    """Test instrument subscription management."""
    # Test adding instruments
    await oanda_client.subscribe_instruments(["EUR_USD", "GBP_USD"])
    assert "EUR_USD" in oanda_client.subscribed_instruments
    assert "GBP_USD" in oanda_client.subscribed_instruments
    
    # Test removing instruments
    await oanda_client.unsubscribe_instruments(["EUR_USD"])
    assert "EUR_USD" not in oanda_client.subscribed_instruments
    assert "GBP_USD" in oanda_client.subscribed_instruments


@pytest.mark.asyncio
async def test_connection_status(oanda_client):
    """Test connection status checking."""
    # Initially not connected
    assert not oanda_client.is_connected()
    
    # Mock connected state
    mock_connection = MagicMock()
    mock_connection.closed = False
    oanda_client.ws_connection = mock_connection
    assert oanda_client.is_connected()
    
    # Mock disconnected state
    mock_connection.closed = True
    assert not oanda_client.is_connected()


@pytest.mark.asyncio
async def test_forex_pairs_constant():
    """Test that all major forex pairs are defined."""
    expected_pairs = {
        "EUR_USD", "GBP_USD", "USD_JPY", "USD_CHF", "AUD_USD",
        "USD_CAD", "NZD_USD", "EUR_GBP", "EUR_JPY", "GBP_JPY"
    }
    assert FOREX_PAIRS == expected_pairs