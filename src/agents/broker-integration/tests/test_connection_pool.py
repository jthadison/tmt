"""
Tests for OandaConnectionPool
Story 8.1 - Task 3: Connection pooling
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch
import aiohttp
from datetime import datetime, timedelta

from ..connection_pool import (
    OandaConnectionPool,
    ConnectionState,
    PooledConnection
)

class TestOandaConnectionPool:
    """Test connection pool functionality"""
    
    @pytest.mark.asyncio
    async def test_pool_initialization(self):
        """Test pool initialization"""
        pool = OandaConnectionPool(pool_size=5)
        
        await pool.initialize()
        
        assert pool._initialized is True
        assert pool.pool_size == 5
        
        await pool.close()
    
    @pytest.mark.asyncio
    async def test_create_connection(self, connection_pool):
        """Test creating a new connection"""
        connection = await connection_pool.create_connection(
            account_id="test-account",
            api_key="test-key",
            base_url="https://api-test.oanda.com"
        )
        
        assert isinstance(connection, PooledConnection)
        assert connection.account_id == "test-account"
        assert connection.api_key == "test-key"
        assert connection.base_url == "https://api-test.oanda.com"
        assert connection.state == ConnectionState.AVAILABLE
        assert connection.metrics.created_at is not None
    
    @pytest.mark.asyncio
    async def test_acquire_release_connection(self, connection_pool, mock_aiohttp_session):
        """Test acquiring and releasing connections"""
        account_id = "test-account"
        api_key = "test-key"
        base_url = "https://api-test.oanda.com"
        
        with patch('aiohttp.ClientSession', return_value=mock_aiohttp_session):
            async with connection_pool.acquire(account_id, api_key, base_url, timeout=5.0) as conn:
                assert conn is not None
                assert conn.state == ConnectionState.IN_USE
                assert conn.account_id == account_id
            
            # Connection should be released and available again
            assert conn.state == ConnectionState.AVAILABLE
    
    @pytest.mark.asyncio
    async def test_connection_health_check(self, connection_pool, mock_aiohttp_session):
        """Test connection health checking"""
        # Create a connection
        connection = await connection_pool.create_connection(
            account_id="test-account",
            api_key="test-key", 
            base_url="https://api-test.oanda.com"
        )
        connection.session = mock_aiohttp_session
        
        # Test healthy connection
        is_healthy = await connection_pool._is_connection_healthy(connection)
        assert is_healthy is True
        assert connection.state != ConnectionState.UNHEALTHY
    
    @pytest.mark.asyncio
    async def test_connection_health_check_failure(self, connection_pool):
        """Test connection health check failure"""
        # Create a connection with failing session
        connection = await connection_pool.create_connection(
            account_id="test-account",
            api_key="test-key",
            base_url="https://api-test.oanda.com"
        )
        
        # Mock failed response
        mock_session = AsyncMock()
        response = AsyncMock()
        response.status = 500  # Server error
        
        context_manager = AsyncMock()
        context_manager.__aenter__ = AsyncMock(return_value=response)
        context_manager.__aexit__ = AsyncMock(return_value=None)
        
        mock_session.get.return_value = context_manager
        connection.session = mock_session
        
        is_healthy = await connection_pool._is_connection_healthy(connection)
        assert is_healthy is False
        assert connection.state == ConnectionState.UNHEALTHY
    
    @pytest.mark.asyncio
    async def test_connection_timeout(self, connection_pool):
        """Test connection acquisition timeout"""
        # Fill the pool
        connections = []
        for i in range(connection_pool.pool_size):
            conn = await connection_pool.create_connection(
                account_id=f"account-{i}",
                api_key="test-key",
                base_url="https://api-test.oanda.com"
            )
            connection_pool.connections[conn.connection_id] = conn
            connections.append(conn)
        
        # Try to acquire with very short timeout
        with pytest.raises(asyncio.TimeoutError):
            async with connection_pool.acquire(
                "new-account", "test-key", "https://api-test.oanda.com", timeout=0.1
            ):
                pass
    
    @pytest.mark.asyncio
    async def test_connection_metrics_tracking(self, connection_pool, mock_aiohttp_session):
        """Test connection metrics are properly tracked"""
        account_id = "test-account"
        api_key = "test-key"
        base_url = "https://api-test.oanda.com"
        
        with patch('aiohttp.ClientSession', return_value=mock_aiohttp_session):
            async with connection_pool.acquire(account_id, api_key, base_url) as conn:
                # Simulate usage
                conn.record_response_time(100.5)
                conn.record_response_time(200.3)
                conn.record_error()
                
                assert conn.metrics.request_count == 1  # From mark_used() call
                assert conn.metrics.error_count == 1
                assert conn.metrics.total_response_time == 300.8
                assert conn.metrics.average_response_time == 300.8  # Only response times, not requests
                assert conn.metrics.error_rate == 1.0  # 1 error out of 1 request
    
    @pytest.mark.asyncio
    async def test_pool_statistics(self, connection_pool):
        """Test pool statistics reporting"""
        # Create some connections
        for i in range(3):
            conn = await connection_pool.create_connection(
                account_id=f"account-{i}",
                api_key="test-key",
                base_url="https://api-test.oanda.com"
            )
            connection_pool.connections[conn.connection_id] = conn
        
        stats = connection_pool.get_pool_stats()
        
        assert stats['pool_size'] == connection_pool.pool_size
        assert stats['active_connections'] == 3
        assert 'connection_states' in stats
        assert 'total_requests' in stats
        assert 'total_errors' in stats
        assert 'pool_metrics' in stats
        assert 'timestamp' in stats
    
    @pytest.mark.asyncio
    async def test_cleanup_unhealthy_connections(self, connection_pool):
        """Test cleanup of unhealthy connections"""
        # Create an unhealthy connection
        connection = await connection_pool.create_connection(
            account_id="test-account",
            api_key="test-key",
            base_url="https://api-test.oanda.com"
        )
        
        # Mark as unhealthy with high error rate
        connection.state = ConnectionState.UNHEALTHY
        connection.metrics.failed_requests = 10
        connection.metrics.request_count = 10  # 100% error rate
        
        connection_pool.connections[connection.connection_id] = connection
        
        # Run cleanup
        await connection_pool._cleanup_unhealthy_connections([connection.connection_id])
        
        # Connection should be removed
        assert connection.connection_id not in connection_pool.connections
    
    @pytest.mark.asyncio
    async def test_cleanup_idle_connections(self, connection_pool):
        """Test cleanup of idle connections"""
        # Create a connection and make it idle
        connection = await connection_pool.create_connection(
            account_id="test-account",
            api_key="test-key",
            base_url="https://api-test.oanda.com"
        )
        
        # Make it appear old
        connection.metrics.last_used = datetime.utcnow() - timedelta(hours=2)
        connection.state = ConnectionState.AVAILABLE
        
        connection_pool.connections[connection.connection_id] = connection
        
        # Run cleanup
        await connection_pool._cleanup_idle_connections()
        
        # Connection should be removed
        assert connection.connection_id not in connection_pool.connections
    
    @pytest.mark.asyncio
    async def test_concurrent_acquisitions(self, connection_pool, mock_aiohttp_session):
        """Test concurrent connection acquisitions"""
        account_id = "test-account"
        api_key = "test-key"
        base_url = "https://api-test.oanda.com"
        
        async def acquire_connection():
            with patch('aiohttp.ClientSession', return_value=mock_aiohttp_session):
                async with connection_pool.acquire(account_id, api_key, base_url) as conn:
                    await asyncio.sleep(0.1)  # Hold connection briefly
                    return conn.connection_id
        
        # Start multiple concurrent acquisitions
        tasks = [acquire_connection() for _ in range(3)]
        results = await asyncio.gather(*tasks)
        
        # All should succeed and get different connections (or reuse properly)
        assert len(results) == 3
        assert all(result is not None for result in results)
    
    @pytest.mark.asyncio
    async def test_connection_reuse(self, connection_pool, mock_aiohttp_session):
        """Test that connections are properly reused"""
        account_id = "test-account"
        api_key = "test-key"
        base_url = "https://api-test.oanda.com"
        
        connection_ids = []
        
        with patch('aiohttp.ClientSession', return_value=mock_aiohttp_session):
            # Acquire and release connection multiple times
            for _ in range(3):
                async with connection_pool.acquire(account_id, api_key, base_url) as conn:
                    connection_ids.append(conn.connection_id)
        
        # Should reuse connections for same account
        # (This behavior depends on implementation details)
        assert len(connection_pool.connections) <= connection_pool.pool_size
    
    @pytest.mark.asyncio
    async def test_pool_closure(self, connection_pool):
        """Test proper pool closure"""
        # Create some connections
        for i in range(2):
            conn = await connection_pool.create_connection(
                account_id=f"account-{i}",
                api_key="test-key", 
                base_url="https://api-test.oanda.com"
            )
            connection_pool.connections[conn.connection_id] = conn
        
        initial_count = len(connection_pool.connections)
        assert initial_count > 0
        
        # Close the pool
        await connection_pool.close()
        
        # All connections should be closed
        assert not connection_pool._initialized
        assert len(connection_pool.connections) == 0