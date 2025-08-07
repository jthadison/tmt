"""
Pytest configuration and fixtures for circuit breaker agent tests.
"""

import asyncio
import sys
import os
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, MagicMock
import httpx

# Add the src directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

# Import test dependencies using absolute imports
try:
    # Try importing as a package first
    from agents.circuit_breaker.app.config import CircuitBreakerConfig
    from agents.circuit_breaker.app.models import SystemHealth, BreakerLevel, BreakerState, TriggerReason
    from agents.circuit_breaker.app.breaker_logic import CircuitBreakerManager
    from agents.circuit_breaker.app.emergency_stop import EmergencyStopManager
    from agents.circuit_breaker.app.health_monitor import HealthMonitor
    from agents.circuit_breaker.app.kafka_events import KafkaEventManager
except ImportError:
    # Fallback to relative imports for local testing
    import importlib.util
    import os
    
    # Import modules directly
    spec = importlib.util.spec_from_file_location(
        "config", 
        os.path.join(os.path.dirname(__file__), "..", "app", "config.py")
    )
    config_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_module)
    CircuitBreakerConfig = config_module.CircuitBreakerConfig
    
    # Import models
    spec = importlib.util.spec_from_file_location(
        "models", 
        os.path.join(os.path.dirname(__file__), "..", "app", "models.py")
    )
    models_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(models_module)
    SystemHealth = models_module.SystemHealth
    BreakerLevel = models_module.BreakerLevel
    BreakerState = models_module.BreakerState
    TriggerReason = models_module.TriggerReason
    
    # Import other modules
    spec = importlib.util.spec_from_file_location(
        "breaker_logic", 
        os.path.join(os.path.dirname(__file__), "..", "app", "breaker_logic.py")
    )
    breaker_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(breaker_module)
    CircuitBreakerManager = breaker_module.CircuitBreakerManager
    
    spec = importlib.util.spec_from_file_location(
        "emergency_stop", 
        os.path.join(os.path.dirname(__file__), "..", "app", "emergency_stop.py")
    )
    emergency_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(emergency_module)
    EmergencyStopManager = emergency_module.EmergencyStopManager
    
    spec = importlib.util.spec_from_file_location(
        "health_monitor", 
        os.path.join(os.path.dirname(__file__), "..", "app", "health_monitor.py")
    )
    health_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(health_module)
    HealthMonitor = health_module.HealthMonitor
    
    spec = importlib.util.spec_from_file_location(
        "kafka_events", 
        os.path.join(os.path.dirname(__file__), "..", "app", "kafka_events.py")
    )
    kafka_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(kafka_module)
    KafkaEventManager = kafka_module.KafkaEventManager


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_config():
    """Test configuration with safe defaults"""
    config = CircuitBreakerConfig(
        environment="test",
        database_url="sqlite:///:memory:",
        redis_url="redis://localhost:6379/15",  # Use test DB
        kafka_bootstrap_servers=["localhost:9092"],
        daily_drawdown_threshold=0.05,
        max_drawdown_threshold=0.08,
        response_time_threshold=100,
        enable_tracing=False,
        enable_metrics=False
    )
    return config


@pytest.fixture
def sample_health_metrics():
    """Sample health metrics for testing"""
    return SystemHealth(
        cpu_usage=45.5,
        memory_usage=62.3,
        disk_usage=78.1,
        error_rate=0.02,
        response_time=75,
        active_connections=25
    )


@pytest.fixture
def critical_health_metrics():
    """Critical health metrics for testing breaker triggers"""
    return SystemHealth(
        cpu_usage=95.0,
        memory_usage=88.5,
        disk_usage=92.0,
        error_rate=0.25,  # 25% error rate
        response_time=500,  # High response time
        active_connections=150
    )


@pytest.fixture
def breaker_manager():
    """Circuit breaker manager instance"""
    return CircuitBreakerManager()


@pytest.fixture
def mock_execution_client():
    """Mock HTTP client for execution engine communication"""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    
    # Mock successful position closure response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "success": True,
        "positions_closed": 5,
        "positions_failed": 0,
        "failed_position_ids": [],
        "response_time_ms": 150,
        "correlation_id": "test-correlation-id",
        "errors": []
    }
    
    mock_client.post.return_value = mock_response
    return mock_client


@pytest.fixture
def emergency_stop_manager(breaker_manager, mock_execution_client):
    """Emergency stop manager with mocked dependencies"""
    manager = EmergencyStopManager(breaker_manager)
    manager.execution_client = mock_execution_client
    return manager


@pytest.fixture
def health_monitor(breaker_manager, emergency_stop_manager):
    """Health monitor instance"""
    return HealthMonitor(breaker_manager, emergency_stop_manager)


@pytest.fixture
def mock_kafka_producer():
    """Mock Kafka producer"""
    producer = Mock()
    future = Mock()
    future.get.return_value = Mock(topic="test", partition=0, offset=123)
    future.add_callback.return_value = future
    future.add_errback.return_value = future
    producer.send.return_value = future
    return producer


@pytest.fixture
def mock_kafka_consumer():
    """Mock Kafka consumer"""
    consumer = Mock()
    consumer.poll.return_value = {}
    consumer.commit_async.return_value = None
    consumer.close.return_value = None
    return consumer


@pytest.fixture
def kafka_manager(mock_kafka_producer):
    """Kafka event manager with mocked producer"""
    manager = KafkaEventManager()
    manager.producer = mock_kafka_producer
    manager.is_connected = True
    return manager


@pytest.fixture
async def running_health_monitor(health_monitor):
    """Health monitor that's actively running"""
    await health_monitor.start_monitoring()
    yield health_monitor
    await health_monitor.stop_monitoring()


@pytest.fixture
def sample_account_metrics():
    """Sample account metrics for testing"""
    from ..app.models import AccountMetrics
    
    return {
        "account_1": AccountMetrics(
            account_id="account_1",
            daily_pnl=150.0,
            daily_drawdown=0.02,
            max_drawdown=0.03,
            position_count=3,
            total_exposure=15000.0
        ),
        "account_2": AccountMetrics(
            account_id="account_2", 
            daily_pnl=-300.0,
            daily_drawdown=0.06,  # High drawdown
            max_drawdown=0.09,    # Very high max drawdown
            position_count=5,
            total_exposure=25000.0
        )
    }


@pytest.fixture
def sample_market_conditions():
    """Sample market conditions for testing"""
    from ..app.models import MarketConditions
    
    return MarketConditions(
        volatility=0.25,
        gap_detected=False,
        gap_size=None,
        correlation_breakdown=False,
        unusual_volume=False,
        circuit_breaker_triggered=False
    )


@pytest.fixture
def extreme_market_conditions():
    """Extreme market conditions for testing"""
    from ..app.models import MarketConditions
    
    return MarketConditions(
        volatility=4.5,  # Extreme volatility
        gap_detected=True,
        gap_size=0.08,   # 8% gap
        correlation_breakdown=True,
        unusual_volume=True,
        circuit_breaker_triggered=False
    )


# Test data generators
def create_emergency_stop_request(
    level: BreakerLevel = BreakerLevel.SYSTEM,
    reason: TriggerReason = TriggerReason.MANUAL_TRIGGER,
    correlation_id: str = "test-correlation-id"
):
    """Create test emergency stop request"""
    from ..app.models import EmergencyStopRequest
    
    return EmergencyStopRequest(
        level=level,
        reason=reason,
        details={"test": "data"},
        correlation_id=correlation_id,
        requested_by="test_user"
    )


def create_websocket_mock():
    """Create mock WebSocket connection"""
    websocket = AsyncMock()
    websocket.accept = AsyncMock()
    websocket.send_text = AsyncMock()
    websocket.receive_text = AsyncMock()
    websocket.close = AsyncMock()
    return websocket


@pytest.fixture
def mock_websocket():
    """Mock WebSocket connection"""
    return create_websocket_mock()


# Performance test utilities
@pytest.fixture
def performance_timer():
    """Utility for measuring execution time"""
    class PerformanceTimer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def start(self):
            self.start_time = datetime.now(timezone.utc)
            return self
        
        def stop(self):
            self.end_time = datetime.now(timezone.utc)
            return self
        
        @property
        def duration_ms(self):
            if self.start_time and self.end_time:
                return (self.end_time - self.start_time).total_seconds() * 1000
            return None
        
        @property
        def duration_seconds(self):
            if self.start_time and self.end_time:
                return (self.end_time - self.start_time).total_seconds()
            return None
    
    return PerformanceTimer()


# Test markers for different test categories
def pytest_configure(config):
    """Configure custom pytest markers"""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")  
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "slow: Slow-running tests")
    config.addinivalue_line("markers", "kafka: Tests requiring Kafka")
    config.addinivalue_line("markers", "database: Tests requiring database")


# Async test helpers
class AsyncContextManager:
    """Helper for testing async context managers"""
    
    def __init__(self, obj):
        self.obj = obj
        
    async def __aenter__(self):
        return self.obj
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


def async_mock_context(obj):
    """Wrap object in async context manager for testing"""
    return AsyncContextManager(obj)