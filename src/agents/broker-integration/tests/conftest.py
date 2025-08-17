"""
Pytest configuration and fixtures for Error Handling tests
Story 8.9 - Task 6: Test configuration and shared fixtures
"""
import pytest
import asyncio
import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# Configure logging for tests
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Disable some noisy loggers during tests
logging.getLogger('asyncio').setLevel(logging.WARNING)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_oanda_api():
    """Mock OANDA API client for testing"""
    mock_client = MagicMock()
    
    # Mock async methods
    mock_client.get_account = AsyncMock(return_value={
        "account": {
            "id": "test_account",
            "balance": "10000.0",
            "currency": "USD"
        }
    })
    
    mock_client.get_instruments = AsyncMock(return_value={
        "instruments": [
            {"name": "EUR_USD", "type": "CURRENCY"},
            {"name": "GBP_USD", "type": "CURRENCY"}
        ]
    })
    
    mock_client.get_pricing = AsyncMock(return_value={
        "prices": [
            {
                "instrument": "EUR_USD",
                "bids": [{"price": "1.1000"}],
                "asks": [{"price": "1.1002"}],
                "timestamp": "2023-01-01T12:00:00Z"
            }
        ]
    })
    
    mock_client.create_order = AsyncMock(return_value={
        "orderCreateTransaction": {
            "id": "test_order_id",
            "type": "MARKET_ORDER",
            "state": "FILLED"
        }
    })
    
    return mock_client


@pytest.fixture
def mock_oanda_auth_handler():
    """Mock OANDA authentication handler for testing"""
    mock_auth = MagicMock()
    mock_auth.get_auth_headers = MagicMock(return_value={
        "Authorization": "Bearer test_token",
        "Content-Type": "application/json"
    })
    mock_auth.get_api_base_url = MagicMock(return_value="https://api-mock.oanda.com")
    mock_auth.validate_credentials = AsyncMock(return_value=True)
    return mock_auth


@pytest.fixture
def mock_connection_pool():
    """Mock connection pool for testing"""
    mock_pool = MagicMock()
    
    # Mock context manager
    mock_session = MagicMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    
    # Mock HTTP methods
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"success": True})
    mock_response.text = AsyncMock(return_value='{"success": true}')
    
    mock_session.get = AsyncMock(return_value=mock_response)
    mock_session.post = AsyncMock(return_value=mock_response)
    mock_session.put = AsyncMock(return_value=mock_response)
    mock_session.delete = AsyncMock(return_value=mock_response)
    
    mock_pool.get_session = MagicMock(return_value=mock_session)
    mock_pool.is_healthy = MagicMock(return_value=True)
    
    return mock_pool


@pytest.fixture
def sample_error_context():
    """Sample error context for testing"""
    from datetime import datetime, timezone
    from error_alerting import ErrorContext
    
    return ErrorContext(
        error_id="test_error_id",
        timestamp=datetime.now(timezone.utc),
        error_type="TestError",
        error_message="Test error message",
        service_name="test_service",
        operation="test_operation",
        account_id="test_account",
        request_id="test_request",
        correlation_id="test_correlation",
        stack_trace="Test stack trace",
        system_metrics={"memory": 100, "cpu": 50},
        user_context={"user": "test_user"},
        recovery_suggestions=["Try again", "Check connection"]
    )


@pytest.fixture
def sample_circuit_breaker_config():
    """Sample circuit breaker configuration for testing"""
    return {
        "failure_threshold": 3,
        "recovery_timeout": 60,
        "name": "test_breaker"
    }


@pytest.fixture
def sample_retry_config():
    """Sample retry configuration for testing"""
    from retry_handler import RetryConfiguration
    
    return RetryConfiguration(
        max_attempts=3,
        base_delay=0.1,  # Short delay for testing
        max_delay=1.0,
        jitter_factor=0.1,
        backoff_multiplier=2.0
    )


@pytest.fixture
def sample_rate_limit_config():
    """Sample rate limit configuration for testing"""
    return {
        "rate": 10.0,  # 10 requests per second
        "burst_capacity": 10,
        "name": "test_limiter"
    }


class MockException(Exception):
    """Mock exception for testing"""
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code
        self.status = status_code


@pytest.fixture
def mock_connection_error():
    """Mock connection error for testing"""
    return MockException("Connection failed", status_code=503)


@pytest.fixture
def mock_rate_limit_error():
    """Mock rate limit error for testing"""
    return MockException("Rate limit exceeded", status_code=429)


@pytest.fixture
def mock_auth_error():
    """Mock authentication error for testing"""
    return MockException("Authentication failed", status_code=401)


@pytest.fixture
def mock_server_error():
    """Mock server error for testing"""
    return MockException("Internal server error", status_code=500)


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their names"""
    for item in items:
        # Mark integration tests
        if "integration" in item.nodeid or "test_integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
            
        # Mark slow tests
        if "slow" in item.nodeid or any(keyword in item.name for keyword in ["timeout", "wait", "sleep"]):
            item.add_marker(pytest.mark.slow)
            
        # Mark unit tests (default)
        if not any(marker.name in ["integration", "slow"] for marker in item.iter_markers()):
            item.add_marker(pytest.mark.unit)


# Test utilities
def create_mock_async_context_manager(return_value=None, exception=None):
    """Create a mock async context manager"""
    mock_cm = MagicMock()
    
    if exception:
        mock_cm.__aenter__ = AsyncMock(side_effect=exception)
        mock_cm.__aexit__ = AsyncMock(return_value=None)
    else:
        mock_cm.__aenter__ = AsyncMock(return_value=return_value or mock_cm)
        mock_cm.__aexit__ = AsyncMock(return_value=None)
        
    return mock_cm


def assert_error_context_valid(error_context):
    """Assert that an error context is valid"""
    from error_alerting import ErrorContext
    
    assert isinstance(error_context, ErrorContext)
    assert error_context.error_id is not None
    assert error_context.timestamp is not None
    assert error_context.error_type is not None
    assert error_context.error_message is not None
    assert error_context.service_name is not None
    assert error_context.operation is not None


def assert_alert_valid(alert):
    """Assert that an alert is valid"""
    from error_alerting import Alert
    
    assert isinstance(alert, Alert)
    assert alert.alert_id is not None
    assert alert.timestamp is not None
    assert alert.severity is not None
    assert alert.title is not None
    assert alert.message is not None
    assert alert.service is not None


# Performance testing utilities
import time
from contextlib import contextmanager

@contextmanager
def assert_performance(max_time_seconds):
    """Context manager to assert performance requirements"""
    start_time = time.perf_counter()
    yield
    end_time = time.perf_counter()
    
    elapsed = end_time - start_time
    assert elapsed <= max_time_seconds, f"Operation took {elapsed:.3f}s, expected <= {max_time_seconds}s"


# Async testing utilities
async def wait_for_condition(condition_func, timeout=5.0, interval=0.1):
    """Wait for a condition to become true"""
    start_time = time.perf_counter()
    
    while time.perf_counter() - start_time < timeout:
        if condition_func():
            return True
        await asyncio.sleep(interval)
        
    return False


def create_multiple_mock_errors(count, error_type=Exception, base_message="Error"):
    """Create multiple mock errors for testing"""
    return [error_type(f"{base_message} {i}") for i in range(count)]