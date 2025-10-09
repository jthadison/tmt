"""
Pytest configuration and fixtures for backtesting service tests
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import AsyncGenerator, List
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.models.market_data import Base, MarketCandleSchema
from app.database import Database


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_db() -> AsyncGenerator[Database, None]:
    """Create test database instance with SQLite"""
    db = Database()
    # Use file::memory:?cache=shared to allow multiple connections to share the same in-memory database
    db.settings.database_url = "sqlite+aiosqlite:///file::memory:?cache=shared&uri=true"

    await db.connect()
    await db.create_tables()

    yield db

    await db.disconnect()


@pytest.fixture
async def db_session(test_db: Database) -> AsyncGenerator[AsyncSession, None]:
    """Get database session for tests"""
    async with test_db.get_session() as session:
        yield session


@pytest.fixture
def sample_candles() -> List[MarketCandleSchema]:
    """Generate sample market candles for testing"""
    base_time = datetime(2024, 1, 1, 0, 0, 0)
    candles = []

    for i in range(100):
        timestamp = base_time + timedelta(hours=i)
        # Simple price movement
        base_price = 1.1000 + (i * 0.0001)

        candle = MarketCandleSchema(
            timestamp=timestamp,
            instrument="EUR_USD",
            timeframe="H1",
            open=base_price,
            high=base_price + 0.0010,
            low=base_price - 0.0010,
            close=base_price + 0.0005,
            volume=1000 + (i * 10),
            complete=True,
        )
        candles.append(candle)

    return candles


@pytest.fixture
def candles_with_gap() -> List[MarketCandleSchema]:
    """Generate candles with a data gap for testing"""
    base_time = datetime(2024, 1, 1, 0, 0, 0)
    candles = []

    for i in range(50):
        timestamp = base_time + timedelta(hours=i)
        base_price = 1.1000 + (i * 0.0001)

        candle = MarketCandleSchema(
            timestamp=timestamp,
            instrument="EUR_USD",
            timeframe="H1",
            open=base_price,
            high=base_price + 0.0010,
            low=base_price - 0.0010,
            close=base_price + 0.0005,
            volume=1000,
        )
        candles.append(candle)

    # Create gap (skip 10 hours)
    for i in range(60, 100):
        timestamp = base_time + timedelta(hours=i)
        base_price = 1.1000 + (i * 0.0001)

        candle = MarketCandleSchema(
            timestamp=timestamp,
            instrument="EUR_USD",
            timeframe="H1",
            open=base_price,
            high=base_price + 0.0010,
            low=base_price - 0.0010,
            close=base_price + 0.0005,
            volume=1000,
        )
        candles.append(candle)

    return candles


@pytest.fixture
def candles_with_outlier() -> List[MarketCandleSchema]:
    """Generate candles with a price outlier for testing"""
    base_time = datetime(2024, 1, 1, 0, 0, 0)
    candles = []

    for i in range(150):
        timestamp = base_time + timedelta(hours=i)
        base_price = 1.1000 + (i * 0.0001)

        # Insert outlier at position 100
        if i == 100:
            base_price = 1.5000  # Massive spike

        candle = MarketCandleSchema(
            timestamp=timestamp,
            instrument="EUR_USD",
            timeframe="H1",
            open=base_price,
            high=base_price + 0.0010,
            low=base_price - 0.0010,
            close=base_price + 0.0005,
            volume=1000,
        )
        candles.append(candle)

    return candles
