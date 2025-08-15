"""
Test configuration and fixtures for OANDA Broker Integration
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timedelta
import tempfile
import os

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from credential_manager import OandaCredentialManager
from oanda_auth_handler import OandaAuthHandler
from connection_pool import OandaConnectionPool
from reconnection_manager import OandaReconnectionManager
from session_manager import SessionManager
from dashboard_widget import ConnectionStatusWidget

@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_vault_client():
    """Mock HashiCorp Vault client"""
    vault = Mock()
    vault.is_authenticated.return_value = True
    vault.secrets.kv.v2.create_or_update_secret = Mock()
    vault.secrets.kv.v2.read_secret_version = Mock()
    vault.secrets.kv.v2.delete_metadata_and_all_versions = Mock()
    return vault

@pytest.fixture
def temp_persistence_file():
    """Create temporary file for session persistence tests"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pkl') as f:
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)

@pytest.fixture
async def credential_manager(mock_vault_client):
    """Create credential manager with mocked Vault"""
    manager = OandaCredentialManager(
        vault_url="http://test-vault:8200",
        vault_token="test-token"
    )
    manager.vault_client = mock_vault_client
    return manager

@pytest.fixture
async def auth_handler(credential_manager):
    """Create auth handler with mocked credential manager"""
    handler = OandaAuthHandler(credential_manager)
    return handler

@pytest.fixture
async def connection_pool():
    """Create connection pool for testing"""
    pool = OandaConnectionPool(pool_size=5)
    await pool.initialize()
    yield pool
    await pool.close()

@pytest.fixture
async def reconnection_manager():
    """Create reconnection manager for testing"""
    manager = OandaReconnectionManager(
        max_retries=3,
        initial_delay=0.1,  # Fast for tests
        max_delay=1.0
    )
    yield manager
    await manager.shutdown()

@pytest.fixture
async def session_manager(auth_handler, temp_persistence_file):
    """Create session manager for testing"""
    manager = SessionManager(
        auth_handler=auth_handler,
        session_timeout=timedelta(minutes=5),  # Short for tests
        idle_timeout=timedelta(minutes=1),
        persistence_file=temp_persistence_file
    )
    await manager.start()
    yield manager
    await manager.stop()

@pytest.fixture
async def dashboard_widget(auth_handler, connection_pool, reconnection_manager):
    """Create dashboard widget for testing"""
    widget = ConnectionStatusWidget(
        auth_handler=auth_handler,
        connection_pool=connection_pool,
        reconnection_manager=reconnection_manager
    )
    await widget.start()
    yield widget
    await widget.stop()

@pytest.fixture
def sample_credentials():
    """Sample OANDA credentials for testing"""
    return {
        'api_key': 'test-api-key-12345',
        'account_id': '101-001-12345678-001',
        'environment': 'practice'
    }

@pytest.fixture
def mock_oanda_response():
    """Mock successful OANDA API response"""
    return {
        'account': {
            'id': '101-001-12345678-001',
            'currency': 'USD',
            'balance': '10000.0000',
            'unrealizedPL': '0.0000',
            'pl': '0.0000',
            'marginUsed': '0.0000',
            'marginAvailable': '10000.0000',
            'openPositionCount': 0,
            'pendingOrderCount': 0
        }
    }

@pytest.fixture
def mock_aiohttp_session():
    """Mock aiohttp session for API calls"""
    session = AsyncMock()
    
    # Mock successful response
    response = AsyncMock()
    response.status = 200
    response.json = AsyncMock(return_value={'account': {'id': '101-001-12345678-001'}})
    
    context_manager = AsyncMock()
    context_manager.__aenter__ = AsyncMock(return_value=response)
    context_manager.__aexit__ = AsyncMock(return_value=None)
    
    session.get.return_value = context_manager
    session.closed = False
    session.close = AsyncMock()
    
    return session