"""
Global pytest configuration and fixtures for TMT Trading System
"""
import asyncio
import os
import sys
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from faker import Faker

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# Initialize Faker for test data
fake = Faker()


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_kafka_producer():
    """Mock Kafka producer for testing"""
    producer = MagicMock()
    producer.send = AsyncMock(return_value=MagicMock())
    producer.flush = AsyncMock()
    return producer


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing"""
    client = AsyncMock()
    client.get = AsyncMock(return_value=None)
    client.set = AsyncMock(return_value=True)
    client.delete = AsyncMock(return_value=1)
    client.exists = AsyncMock(return_value=0)
    client.expire = AsyncMock(return_value=True)
    return client


@pytest.fixture
def sample_trade_signal():
    """Generate sample trade signal for testing"""
    return {
        "id": fake.uuid4(),
        "timestamp": fake.date_time().isoformat(),
        "symbol": fake.random_element(["EURUSD", "GBPUSD", "USDJPY"]),
        "action": fake.random_element(["BUY", "SELL"]),
        "confidence": fake.random.uniform(0.7, 0.95),
        "entry_price": fake.pyfloat(min_value=1.0, max_value=2.0, right_digits=5),
        "stop_loss": fake.pyfloat(min_value=1.0, max_value=2.0, right_digits=5),
        "take_profit": fake.pyfloat(min_value=1.0, max_value=2.0, right_digits=5),
        "position_size": fake.pyfloat(min_value=0.01, max_value=1.0, right_digits=2),
        "risk_percentage": fake.pyfloat(min_value=0.5, max_value=2.0, right_digits=2),
        "agent_id": fake.random_element(["wyckoff", "aria", "market_state", "smc"]),
        "account_id": f"ACC{fake.random_number(digits=6)}"
    }


@pytest.fixture
def sample_market_data():
    """Generate sample market data for testing"""
    return {
        "symbol": fake.random_element(["EURUSD", "GBPUSD", "USDJPY"]),
        "timestamp": fake.date_time().isoformat(),
        "bid": fake.pyfloat(min_value=1.0, max_value=2.0, right_digits=5),
        "ask": fake.pyfloat(min_value=1.0, max_value=2.0, right_digits=5),
        "volume": fake.random_int(min=1000, max=100000),
        "spread": fake.pyfloat(min_value=0.0001, max_value=0.001, right_digits=5)
    }


@pytest.fixture
def sample_account_config():
    """Generate sample account configuration"""
    return {
        "account_id": f"ACC{fake.random_number(digits=6)}",
        "broker": fake.random_element(["FTMO", "MyForexFunds", "FundedNext"]),
        "platform": fake.random_element(["MT4", "MT5", "TradingView"]),
        "balance": fake.pyfloat(min_value=10000, max_value=100000, right_digits=2),
        "max_drawdown": fake.pyfloat(min_value=5.0, max_value=10.0, right_digits=2),
        "daily_loss_limit": fake.pyfloat(min_value=2.0, max_value=5.0, right_digits=2),
        "max_position_size": fake.pyfloat(min_value=1.0, max_value=5.0, right_digits=2),
        "allowed_symbols": ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"],
        "trading_personality": {
            "risk_appetite": fake.random_element(["conservative", "moderate", "aggressive"]),
            "timing_preference": fake.random_element(["london", "newyork", "asian"]),
            "hold_duration": fake.random_element(["scalp", "intraday", "swing"])
        }
    }


@pytest.fixture
def performance_timer():
    """Timer fixture for performance testing"""
    import time
    
    class Timer:
        def __init__(self):
            self.start_time = None
            self.elapsed = None
            
        def __enter__(self):
            self.start_time = time.perf_counter()
            return self
            
        def __exit__(self, *args):
            self.elapsed = (time.perf_counter() - self.start_time) * 1000  # Convert to ms
            
        def assert_under(self, milliseconds):
            assert self.elapsed < milliseconds, f"Operation took {self.elapsed:.2f}ms, expected under {milliseconds}ms"
    
    return Timer


@pytest.fixture
def mock_database():
    """Mock database connection for testing"""
    db = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock())
    db.fetch_one = AsyncMock(return_value=None)
    db.fetch_all = AsyncMock(return_value=[])
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.fixture
def circuit_breaker_config():
    """Circuit breaker configuration for testing"""
    return {
        "agent_level": {
            "max_consecutive_losses": 3,
            "max_daily_loss_percentage": 2.0,
            "cooldown_minutes": 30
        },
        "account_level": {
            "max_drawdown_percentage": 5.0,
            "max_daily_trades": 10,
            "emergency_stop_loss": 10.0
        },
        "system_level": {
            "max_correlation": 0.7,
            "min_agents_online": 6,
            "heartbeat_timeout_seconds": 60
        }
    }


# Environment setup for tests
os.environ.setdefault("TESTING", "true")
os.environ.setdefault("LOG_LEVEL", "DEBUG")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test_db")