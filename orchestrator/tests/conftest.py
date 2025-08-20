"""
Test configuration and fixtures for Trading System Orchestrator
"""

import pytest
import asyncio
import tempfile
import os
from unittest.mock import Mock, AsyncMock
from datetime import datetime
from typing import Dict, Any

# Import all the modules we need to test
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.models import TradeSignal, AgentStatus, AgentInfo
from app.config import Settings, TestSettings


@pytest.fixture
def event_loop():
    """Create an event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings():
    """Provide test settings"""
    return TestSettings(
        oanda_api_key="test_key",
        oanda_account_ids="test_account_123",
        oanda_environment="practice",
        debug=True,
        log_level="DEBUG",
        risk_per_trade=0.001,
        max_daily_loss=0.01,
        max_concurrent_trades=1,
        message_broker_url="redis://localhost:6379/1",
        database_url="sqlite:///:memory:"
    )


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing"""
    mock_redis = AsyncMock()
    mock_redis.ping.return_value = True
    mock_redis.publish = AsyncMock()
    mock_redis.subscribe = AsyncMock()
    mock_redis.get_message = AsyncMock()
    mock_redis.setex = AsyncMock()
    mock_redis.zadd = AsyncMock()
    mock_redis.expire = AsyncMock()
    mock_redis.zrevrange = AsyncMock(return_value=[])
    mock_redis.get = AsyncMock(return_value=None)
    return mock_redis


@pytest.fixture
def sample_trade_signal():
    """Sample trade signal for testing"""
    return TradeSignal(
        id="test_signal_123",
        instrument="EUR_USD",
        direction="long",
        confidence=0.85,
        entry_price=1.0500,
        stop_loss=1.0450,
        take_profit=1.0600,
        risk_reward_ratio=2.0,
        timeframe="H1",
        pattern_type="wyckoff_accumulation",
        market_state="ranging",
        metadata={
            "volume_analysis": "high",
            "smart_money_flow": "bullish",
            "confluence_score": 8.5
        }
    )


@pytest.fixture
def sample_agent_info():
    """Sample agent info for testing"""
    return AgentInfo(
        agent_id="market-analysis",
        agent_type="market-analysis",
        endpoint="http://localhost:8001",
        status=AgentStatus.ACTIVE,
        last_seen=datetime.utcnow(),
        capabilities=["signal_generation", "market_analysis", "pattern_recognition"],
        version="1.0.0"
    )


@pytest.fixture
def mock_httpx_client():
    """Mock HTTPX client for testing"""
    mock_client = AsyncMock()
    
    # Mock health check responses
    health_response = Mock()
    health_response.status_code = 200
    health_response.json.return_value = {"status": "healthy", "capabilities": ["signal_generation"]}
    health_response.elapsed.total_seconds.return_value = 0.1
    mock_client.get.return_value = health_response
    
    # Mock trade execution responses
    trade_response = Mock()
    trade_response.status_code = 201
    trade_response.json.return_value = {
        "orderFillTransaction": {
            "id": "12345",
            "price": "1.0500",
            "units": "1000",
            "tradeOpened": {"tradeID": "67890"},
            "commission": "2.50",
            "financing": "0.25"
        }
    }
    mock_client.post.return_value = trade_response
    
    mock_client.aclose = AsyncMock()
    return mock_client


@pytest.fixture
def mock_oanda_account_data():
    """Mock OANDA account data for testing"""
    return {
        "account": {
            "id": "test_account_123",
            "balance": "99935.05",
            "unrealizedPL": "125.50",
            "marginUsed": "500.00",
            "marginAvailable": "99435.05",
            "openTradeCount": "2",
            "currency": "USD"
        }
    }


@pytest.fixture
def mock_oanda_positions_data():
    """Mock OANDA positions data for testing"""
    return {
        "positions": [
            {
                "instrument": "EUR_USD",
                "long": {
                    "units": "1000",
                    "averagePrice": "1.0500",
                    "unrealizedPL": "50.00"
                },
                "short": {
                    "units": "0",
                    "averagePrice": "0",
                    "unrealizedPL": "0"
                },
                "unrealizedPL": "50.00",
                "marginUsed": "250.00"
            }
        ]
    }


@pytest.fixture
def mock_oanda_trades_data():
    """Mock OANDA trades data for testing"""
    return {
        "trades": [
            {
                "id": "12345",
                "instrument": "EUR_USD",
                "currentUnits": "1000",
                "price": "1.0500",
                "unrealizedPL": "25.00",
                "openTime": "2024-01-01T12:00:00.000000Z"
            }
        ]
    }


@pytest.fixture
def trading_metrics_data():
    """Sample trading metrics for testing"""
    return {
        "account_id": "test_account_123",
        "current_balance": 100000.0,
        "starting_balance": 100000.0,
        "daily_pnl": 150.0,
        "unrealized_pnl": 75.0,
        "total_exposure": 5000.0,
        "position_count": 2,
        "largest_position": 2500.0,
        "correlation_score": 0.3,
        "volatility_score": 1.2,
        "drawdown_percentage": 2.5,
        "consecutive_losses": 1,
        "trades_today": 3,
        "risk_score": 25.0
    }


@pytest.fixture
def system_events_data():
    """Sample system events for testing"""
    return [
        {
            "type": "system.started",
            "timestamp": "2024-01-01T12:00:00Z",
            "data": {"message": "System started successfully"}
        },
        {
            "type": "signal.received",
            "timestamp": "2024-01-01T12:01:00Z",
            "data": {
                "signal_id": "test_signal_123",
                "instrument": "EUR_USD",
                "direction": "long",
                "confidence": 0.85
            }
        }
    ]


@pytest.fixture
def circuit_breaker_config():
    """Circuit breaker configuration for testing"""
    return {
        "account_loss_threshold": 0.05,
        "daily_loss_threshold": 0.03,
        "consecutive_losses": 5,
        "correlation_threshold": 0.8,
        "volatility_threshold": 2.0,
        "recovery_time_minutes": 30
    }


class MockAgent:
    """Mock trading agent for testing"""
    
    def __init__(self, agent_id: str, agent_type: str, healthy: bool = True):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.healthy = healthy
        self.endpoint = f"http://localhost:800{agent_id[-1]}"
        
    async def health_check(self):
        if self.healthy:
            return {"status": "healthy", "capabilities": ["trading"]}
        else:
            raise Exception("Agent unhealthy")
    
    async def process_signal(self, signal: Dict[str, Any]):
        if self.healthy:
            return {
                "success": True,
                "result": f"Processed by {self.agent_id}",
                "confidence": 0.8
            }
        else:
            raise Exception("Agent processing failed")


@pytest.fixture
def mock_agents():
    """Mock all 8 trading agents"""
    agents = {}
    agent_types = [
        "market-analysis",
        "strategy-analysis", 
        "parameter-optimization",
        "learning-safety",
        "disagreement-engine",
        "data-collection",
        "continuous-improvement",
        "pattern-detection"
    ]
    
    for i, agent_type in enumerate(agent_types, 1):
        agents[agent_type] = MockAgent(f"agent_{i}", agent_type)
    
    return agents


@pytest.fixture
async def temp_env_file():
    """Create temporary .env file for testing"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
        f.write("""
OANDA_API_KEY=test_key
OANDA_ACCOUNT_IDS=test_account_123
OANDA_ENVIRONMENT=practice
DEBUG=true
LOG_LEVEL=DEBUG
RISK_PER_TRADE=0.001
MAX_DAILY_LOSS=0.01
MAX_CONCURRENT_TRADES=1
MESSAGE_BROKER_URL=redis://localhost:6379/1
""")
        f.flush()
        yield f.name
        os.unlink(f.name)