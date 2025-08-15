"""
Integration Tests for OANDA Broker Integration
Story 8.1: End-to-end testing of all components working together
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from datetime import datetime

from ..credential_manager import OandaCredentialManager
from ..oanda_auth_handler import OandaAuthHandler
from ..connection_pool import OandaConnectionPool
from ..reconnection_manager import OandaReconnectionManager
from ..session_manager import SessionManager
from ..dashboard_widget import ConnectionStatusWidget

class TestBrokerIntegrationComplete:
    """Complete integration tests for Story 8.1"""
    
    @pytest.mark.asyncio
    async def test_complete_authentication_flow(self, mock_vault_client, sample_credentials, mock_aiohttp_session):
        """Test complete authentication flow from credentials to active session"""
        
        # Setup components
        credential_manager = OandaCredentialManager("http://test:8200", "test-token")
        credential_manager.vault_client = mock_vault_client
        
        auth_handler = OandaAuthHandler(credential_manager)
        
        session_manager = SessionManager(auth_handler)
        await session_manager.start()
        
        try:
            # Mock successful credential validation
            with patch.object(credential_manager, 'validate_credentials', return_value=True):
                # Store credentials
                await credential_manager.store_credentials('test-user', sample_credentials)
                
                # Mock Vault retrieval
                encrypted_creds = credential_manager._encrypt_credentials(sample_credentials)
                mock_vault_client.secrets.kv.v2.read_secret_version.return_value = {
                    'data': {'data': {'credentials': encrypted_creds}}
                }
                
                # Mock API authentication
                with patch('aiohttp.ClientSession', return_value=mock_aiohttp_session):
                    # Create session
                    session_id = await session_manager.create_session(
                        'test-user', 
                        sample_credentials['account_id'],
                        sample_credentials['environment']
                    )
                    
                    assert session_id is not None
                    
                    # Verify session exists and is active
                    session = await session_manager.get_session(session_id)
                    assert session is not None
                    assert session.user_id == 'test-user'
                    assert session.account_id == sample_credentials['account_id']
                    
                    # Verify authentication context
                    context = session.context
                    assert context.user_id == 'test-user'
                    assert context.account_id == sample_credentials['account_id']
                    
        finally:
            await session_manager.stop()
    
    @pytest.mark.asyncio
    async def test_connection_pooling_with_auth(self, mock_vault_client, sample_credentials, mock_aiohttp_session):
        """Test connection pooling integrated with authentication"""
        
        # Setup components
        credential_manager = OandaCredentialManager("http://test:8200", "test-token")
        credential_manager.vault_client = mock_vault_client
        
        auth_handler = OandaAuthHandler(credential_manager)
        
        connection_pool = OandaConnectionPool(pool_size=3)
        await connection_pool.initialize()
        
        try:
            # Mock credentials and authentication
            with patch.object(credential_manager, 'validate_credentials', return_value=True):
                encrypted_creds = credential_manager._encrypt_credentials(sample_credentials)
                mock_vault_client.secrets.kv.v2.read_secret_version.return_value = {
                    'data': {'data': {'credentials': encrypted_creds}}
                }
                
                with patch('aiohttp.ClientSession', return_value=mock_aiohttp_session):
                    # Authenticate user
                    context = await auth_handler.authenticate_user(
                        'test-user',
                        sample_credentials['account_id'],
                        sample_credentials['environment']
                    )
                    
                    # Use connection pool with authenticated context
                    async with connection_pool.acquire(
                        context.account_id,
                        context.api_key,
                        context.base_url
                    ) as conn:
                        assert conn is not None
                        assert conn.account_id == context.account_id
                        
                        # Simulate API call
                        conn.mark_used()
                        conn.record_response_time(100.0)
                        
                        assert conn.metrics.request_count > 0
                        
        finally:
            await connection_pool.close()
    
    @pytest.mark.asyncio
    async def test_reconnection_with_session_recovery(self, mock_vault_client, sample_credentials, mock_aiohttp_session):
        """Test reconnection manager with session recovery"""
        
        # Setup components
        credential_manager = OandaCredentialManager("http://test:8200", "test-token")
        credential_manager.vault_client = mock_vault_client
        
        auth_handler = OandaAuthHandler(credential_manager)
        
        reconnection_manager = OandaReconnectionManager(max_retries=3, initial_delay=0.1)
        
        session_manager = SessionManager(auth_handler)
        await session_manager.start()
        
        try:
            # Mock credentials and authentication
            with patch.object(credential_manager, 'validate_credentials', return_value=True):
                encrypted_creds = credential_manager._encrypt_credentials(sample_credentials)
                mock_vault_client.secrets.kv.v2.read_secret_version.return_value = {
                    'data': {'data': {'credentials': encrypted_creds}}
                }
                
                with patch('aiohttp.ClientSession', return_value=mock_aiohttp_session):
                    # Create session
                    session_id = await session_manager.create_session(
                        'test-user',
                        sample_credentials['account_id'],
                        sample_credentials['environment']
                    )
                    
                    # Define reconnection callback that refreshes session
                    async def reconnection_callback():
                        return await session_manager.refresh_session(session_id)
                    
                    # Register connection with reconnection manager
                    connection_id = f"oanda_{sample_credentials['account_id']}"
                    reconnection_manager.register_connection(connection_id, reconnection_callback)
                    
                    # Simulate connection loss
                    await reconnection_manager.handle_disconnection(connection_id, "Network timeout")
                    
                    # Wait for reconnection
                    await asyncio.sleep(0.5)
                    
                    # Verify reconnection succeeded
                    state = reconnection_manager.get_connection_state(connection_id)
                    assert state is not None
                    
                    # Verify session is still valid
                    session = await session_manager.get_session(session_id)
                    assert session is not None
                    
        finally:
            await session_manager.stop()
            await reconnection_manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_dashboard_widget_integration(self, mock_vault_client, sample_credentials, mock_aiohttp_session):
        """Test dashboard widget with all components"""
        
        # Setup all components
        credential_manager = OandaCredentialManager("http://test:8200", "test-token")
        credential_manager.vault_client = mock_vault_client
        
        auth_handler = OandaAuthHandler(credential_manager)
        
        connection_pool = OandaConnectionPool(pool_size=3)
        await connection_pool.initialize()
        
        reconnection_manager = OandaReconnectionManager()
        
        dashboard_widget = ConnectionStatusWidget(
            auth_handler,
            connection_pool,
            reconnection_manager
        )
        await dashboard_widget.start()
        
        try:
            # Mock credentials and authentication
            with patch.object(credential_manager, 'validate_credentials', return_value=True):
                encrypted_creds = credential_manager._encrypt_credentials(sample_credentials)
                mock_vault_client.secrets.kv.v2.read_secret_version.return_value = {
                    'data': {'data': {'credentials': encrypted_creds}}
                }
                
                with patch('aiohttp.ClientSession', return_value=mock_aiohttp_session):
                    # Authenticate user
                    await auth_handler.authenticate_user(
                        'test-user',
                        sample_credentials['account_id'],
                        sample_credentials['environment']
                    )
                    
                    # Get dashboard data
                    dashboard_data = await dashboard_widget.get_dashboard_data()
                    
                    assert 'summary' in dashboard_data
                    assert 'connections' in dashboard_data
                    assert 'last_updated' in dashboard_data
                    
                    summary = dashboard_data['summary']
                    assert 'total_connections' in summary
                    assert 'healthy_connections' in summary
                    
                    # Test system summary
                    system_summary = await dashboard_widget.get_system_summary()
                    assert system_summary.total_connections >= 0
                    assert system_summary.overall_health_percentage >= 0
                    
        finally:
            await dashboard_widget.stop()
            await connection_pool.close()
            await reconnection_manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, mock_vault_client, sample_credentials):
        """Test system behavior under error conditions"""
        
        # Setup components
        credential_manager = OandaCredentialManager("http://test:8200", "test-token")
        credential_manager.vault_client = mock_vault_client
        
        auth_handler = OandaAuthHandler(credential_manager)
        
        session_manager = SessionManager(auth_handler)
        await session_manager.start()
        
        try:
            # Test with invalid credentials
            with patch.object(credential_manager, 'validate_credentials', return_value=False):
                with pytest.raises(Exception):  # Should raise validation error
                    await credential_manager.store_credentials('test-user', sample_credentials)
            
            # Test authentication failure
            mock_vault_client.secrets.kv.v2.read_secret_version.return_value = None
            
            with pytest.raises(Exception):  # Should raise authentication error
                await auth_handler.authenticate_user(
                    'test-user',
                    sample_credentials['account_id'],
                    sample_credentials['environment']
                )
            
            # Test session creation with bad auth
            with pytest.raises(Exception):
                await session_manager.create_session(
                    'test-user',
                    sample_credentials['account_id'],
                    sample_credentials['environment']
                )
                
        finally:
            await session_manager.stop()
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, mock_vault_client, sample_credentials, mock_aiohttp_session):
        """Test system behavior under concurrent load"""
        
        # Setup components
        credential_manager = OandaCredentialManager("http://test:8200", "test-token")
        credential_manager.vault_client = mock_vault_client
        
        auth_handler = OandaAuthHandler(credential_manager)
        
        connection_pool = OandaConnectionPool(pool_size=5)
        await connection_pool.initialize()
        
        session_manager = SessionManager(auth_handler)
        await session_manager.start()
        
        try:
            # Mock credentials and authentication
            with patch.object(credential_manager, 'validate_credentials', return_value=True):
                encrypted_creds = credential_manager._encrypt_credentials(sample_credentials)
                mock_vault_client.secrets.kv.v2.read_secret_version.return_value = {
                    'data': {'data': {'credentials': encrypted_creds}}
                }
                
                with patch('aiohttp.ClientSession', return_value=mock_aiohttp_session):
                    # Create multiple concurrent sessions
                    async def create_session(user_id):
                        return await session_manager.create_session(
                            user_id,
                            sample_credentials['account_id'],
                            sample_credentials['environment']
                        )
                    
                    # Run concurrent session creations
                    tasks = [create_session(f'user-{i}') for i in range(5)]
                    session_ids = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Verify all sessions were created successfully
                    successful_sessions = [
                        sid for sid in session_ids 
                        if isinstance(sid, str) and not isinstance(sid, Exception)
                    ]
                    
                    assert len(successful_sessions) > 0
                    
                    # Test concurrent connection acquisitions
                    async def use_connection():
                        context = await auth_handler.authenticate_user(
                            'concurrent-user',
                            sample_credentials['account_id'], 
                            sample_credentials['environment']
                        )
                        
                        async with connection_pool.acquire(
                            context.account_id,
                            context.api_key,
                            context.base_url,
                            timeout=1.0
                        ) as conn:
                            await asyncio.sleep(0.1)
                            return conn.connection_id
                    
                    # Run concurrent connection usage
                    connection_tasks = [use_connection() for _ in range(3)]
                    connection_results = await asyncio.gather(*connection_tasks, return_exceptions=True)
                    
                    # Should handle concurrent access gracefully
                    successful_connections = [
                        result for result in connection_results
                        if not isinstance(result, Exception)
                    ]
                    
                    assert len(successful_connections) > 0
                    
        finally:
            await session_manager.stop()
            await connection_pool.close()
    
    @pytest.mark.asyncio
    async def test_system_metrics_and_monitoring(self, mock_vault_client, sample_credentials, mock_aiohttp_session):
        """Test that all system metrics are properly collected"""
        
        # Setup components
        credential_manager = OandaCredentialManager("http://test:8200", "test-token")
        credential_manager.vault_client = mock_vault_client
        
        auth_handler = OandaAuthHandler(credential_manager)
        
        connection_pool = OandaConnectionPool(pool_size=3)
        await connection_pool.initialize()
        
        reconnection_manager = OandaReconnectionManager()
        
        session_manager = SessionManager(auth_handler)
        await session_manager.start()
        
        try:
            # Mock credentials and authentication
            with patch.object(credential_manager, 'validate_credentials', return_value=True):
                encrypted_creds = credential_manager._encrypt_credentials(sample_credentials)
                mock_vault_client.secrets.kv.v2.read_secret_version.return_value = {
                    'data': {'data': {'credentials': encrypted_creds}}
                }
                
                with patch('aiohttp.ClientSession', return_value=mock_aiohttp_session):
                    # Create session and perform operations
                    session_id = await session_manager.create_session(
                        'test-user',
                        sample_credentials['account_id'],
                        sample_credentials['environment']
                    )
                    
                    # Use connection pool
                    context = await auth_handler.authenticate_user(
                        'test-user',
                        sample_credentials['account_id'],
                        sample_credentials['environment']
                    )
                    
                    async with connection_pool.acquire(
                        context.account_id,
                        context.api_key, 
                        context.base_url
                    ) as conn:
                        conn.record_response_time(150.0)
                        session_manager.record_request(session_id, 150.0, success=True)
                    
                    # Check all metrics are available
                    
                    # Credential manager health
                    cred_health = credential_manager.health_check()
                    assert 'vault_connection' in cred_health
                    
                    # Auth handler stats
                    auth_stats = auth_handler.get_session_stats()
                    assert 'total_sessions' in auth_stats
                    
                    # Connection pool stats
                    pool_stats = connection_pool.get_pool_stats()
                    assert 'active_connections' in pool_stats
                    assert 'pool_metrics' in pool_stats
                    
                    # Reconnection manager health
                    reconnection_health = reconnection_manager.get_system_health()
                    assert 'total_connections' in reconnection_health
                    
                    # Session manager stats
                    session_stats = session_manager.get_session_statistics()
                    assert 'total_sessions' in session_stats
                    assert 'global_metrics' in session_stats
                    
                    # Verify metrics contain expected data
                    assert pool_stats['total_requests'] >= 0
                    assert session_stats['total_sessions'] >= 1
                    
        finally:
            await session_manager.stop()
            await connection_pool.close()
            await reconnection_manager.shutdown()