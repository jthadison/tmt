"""Pytest configuration and shared fixtures."""

import pytest
import asyncio
from unittest.mock import Mock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'app'))
from models import Base


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_db_engine():
    """Create in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def test_db_session(test_db_engine):
    """Create database session for testing."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def mock_position_data():
    """Mock position data for testing."""
    return [
        {
            "account_id": "acc1",
            "symbol": "EURUSD",
            "position_size": 1.0,
            "timestamp": "2024-01-01T12:00:00Z"
        },
        {
            "account_id": "acc2", 
            "symbol": "EURUSD",
            "position_size": 0.8,
            "timestamp": "2024-01-01T12:01:00Z"
        }
    ]


@pytest.fixture
def mock_market_data():
    """Mock market data for testing."""
    return {
        "EURUSD": {"price": 1.0850, "volatility": 0.12, "session": "london"},
        "GBPUSD": {"price": 1.2650, "volatility": 0.15, "session": "london"},
        "USDJPY": {"price": 149.50, "volatility": 0.10, "session": "tokyo"}
    }


@pytest.fixture
def sample_correlation_data():
    """Sample correlation data for testing."""
    return {
        "account_pairs": [
            {"account1": "acc1", "account2": "acc2", "correlation": 0.75, "p_value": 0.02},
            {"account1": "acc1", "account2": "acc3", "correlation": 0.45, "p_value": 0.15},
            {"account1": "acc2", "account2": "acc3", "correlation": 0.85, "p_value": 0.001}
        ]
    }


@pytest.fixture(autouse=True)
def mock_external_services():
    """Mock external services to avoid real API calls during testing."""
    with pytest.MonkeyPatch().context() as m:
        # Mock webhook notifications
        m.setattr("requests.post", Mock(return_value=Mock(status_code=200)))
        
        # Mock email notifications
        m.setattr("smtplib.SMTP", Mock())
        
        # Mock Slack notifications
        m.setattr("slack_sdk.WebClient.chat_postMessage", Mock())
        
        yield


class AsyncMock(Mock):
    """Mock class for async functions."""
    
    def __call__(self, *args, **kwargs):
        sup = super(AsyncMock, self)
        
        async def coro():
            return sup.__call__(*args, **kwargs)
        return coro()
    
    def __await__(self):
        return iter([])


@pytest.fixture
def mock_async():
    """Fixture providing AsyncMock class."""
    return AsyncMock