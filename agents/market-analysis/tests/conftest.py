"""Pytest configuration and fixtures for market analysis tests."""

import asyncio
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.market_data.data_normalizer import MarketTick


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_oanda_candle():
    """Sample OANDA candle data for testing."""
    return {
        'time': '2024-01-01T12:00:00Z',
        'mid': {
            'o': '1.1000',
            'h': '1.1010',
            'l': '1.0990',
            'c': '1.1005'
        },
        'volume': 0
    }


@pytest.fixture
def sample_polygon_aggregate():
    """Sample Polygon aggregate data for testing."""
    return {
        't': 1704110400000,  # 2024-01-01T12:00:00Z in milliseconds
        'o': 100.0,
        'h': 101.0,
        'l': 99.0,
        'c': 100.5,
        'v': 1000000
    }


@pytest.fixture
def sample_market_tick():
    """Sample MarketTick for testing."""
    return MarketTick(
        symbol="EUR_USD",
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        timeframe="1m",
        open=Decimal("1.1000"),
        high=Decimal("1.1010"),
        low=Decimal("1.0990"),
        close=Decimal("1.1005"),
        volume=1000,
        source="oanda"
    )


@pytest.fixture
def mock_aiohttp_session():
    """Mock aiohttp ClientSession for testing."""
    session = MagicMock()
    session.request = AsyncMock()
    session.get = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def mock_websocket():
    """Mock WebSocket connection for testing."""
    ws = MagicMock()
    ws.send = AsyncMock()
    ws.recv = AsyncMock()
    ws.close = AsyncMock()
    ws.open = True
    ws.closed = False
    return ws


@pytest.fixture
def mock_database_connection():
    """Mock database connection for testing."""
    conn = MagicMock()
    conn.execute = AsyncMock()
    conn.executemany = AsyncMock()
    conn.fetch = AsyncMock()
    conn.fetchrow = AsyncMock()
    return conn