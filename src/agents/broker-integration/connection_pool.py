"""
OANDA Connection Pool Implementation
Story 8.1 - Task 3: Implement connection pooling
"""
import asyncio
import logging
from typing import Dict, Optional, List, Any, AsyncContextManager
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from dataclasses import dataclass
import aiohttp
import time
from enum import Enum

logger = logging.getLogger(__name__)

class ConnectionState(Enum):
    AVAILABLE = "available"
    IN_USE = "in_use"
    UNHEALTHY = "unhealthy"
    CLOSED = "closed"

@dataclass
class ConnectionMetrics:
    """Track connection performance metrics"""
    created_at: datetime
    last_used: datetime
    request_count: int = 0
    error_count: int = 0
    total_response_time: float = 0.0
    
    @property
    def average_response_time(self) -> float:
        return self.total_response_time / max(self.request_count, 1)
    
    @property
    def error_rate(self) -> float:
        return self.error_count / max(self.request_count, 1)

@dataclass
class PooledConnection:
    """Wrapper for pooled HTTP session with metadata"""
    session: aiohttp.ClientSession
    connection_id: str
    state: ConnectionState
    metrics: ConnectionMetrics
    account_id: str
    api_key: str
    base_url: str
    last_health_check: datetime
    
    def mark_used(self):
        """Mark connection as recently used"""
        self.metrics.last_used = datetime.utcnow()
        self.metrics.request_count += 1
    
    def record_error(self):
        """Record an error for this connection"""
        self.metrics.error_count += 1
    
    def record_response_time(self, response_time: float):
        """Record response time for metrics"""
        self.metrics.total_response_time += response_time

class OandaConnectionPool:
    """High-performance connection pool for OANDA API with health monitoring"""
    
    def __init__(self, pool_size: int = 10, max_idle_time: timedelta = timedelta(minutes=30)):
        self.pool_size = pool_size
        self.max_idle_time = max_idle_time
        self.connections: Dict[str, PooledConnection] = {}
        self._available_queue = asyncio.Queue(maxsize=pool_size)
        self._lock = asyncio.Lock()
        self._initialized = False
        self._health_check_interval = 60  # seconds
        self._health_check_task: Optional[asyncio.Task] = None
        
        # Pool metrics
        self.pool_metrics = {
            'connections_created': 0,
            'connections_destroyed': 0,
            'health_checks_performed': 0,
            'health_check_failures': 0,
            'acquire_requests': 0,
            'acquire_timeouts': 0
        }
    
    async def initialize(self):
        """Initialize the connection pool"""
        if self._initialized:
            return
        
        logger.info(f"Initializing OANDA connection pool with size: {self.pool_size}")
        
        # Start health check background task
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        self._initialized = True
        
        logger.info("Connection pool initialized successfully")
    
    async def create_connection(self, account_id: str, api_key: str, base_url: str) -> PooledConnection:
        """
        Create a new pooled connection for specific account
        
        Args:
            account_id: OANDA account ID
            api_key: API authentication key
            base_url: OANDA API base URL
            
        Returns:
            PooledConnection: New connection instance
        """
        connection_id = f"{account_id}_{int(time.time()*1000)}"
        
        # Configure session with optimized settings
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        connector = aiohttp.TCPConnector(
            limit=100,  # Total connection pool size
            limit_per_host=10,  # Per-host connection limit
            ttl_dns_cache=300,  # DNS cache TTL
            use_dns_cache=True,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )
        
        session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
                'User-Agent': 'TMT-BrokerIntegration/1.0'
            }
        )
        
        metrics = ConnectionMetrics(
            created_at=datetime.utcnow(),
            last_used=datetime.utcnow()
        )
        
        connection = PooledConnection(
            session=session,
            connection_id=connection_id,
            state=ConnectionState.AVAILABLE,
            metrics=metrics,
            account_id=account_id,
            api_key=api_key,
            base_url=base_url,
            last_health_check=datetime.utcnow()
        )
        
        self.pool_metrics['connections_created'] += 1
        logger.debug(f"Created new connection: {connection_id}")
        
        return connection
    
    @asynccontextmanager
    async def acquire(self, account_id: str, api_key: str, base_url: str, timeout: float = 30.0) -> AsyncContextManager[PooledConnection]:
        """
        Acquire a connection from the pool
        
        Args:
            account_id: OANDA account ID
            api_key: API key for authentication
            base_url: OANDA API base URL
            timeout: Acquisition timeout in seconds
            
        Yields:
            PooledConnection: Available connection
            
        Raises:
            asyncio.TimeoutError: If acquisition times out
        """
        if not self._initialized:
            await self.initialize()
        
        self.pool_metrics['acquire_requests'] += 1
        connection = None
        
        try:
            # Try to get available connection or create new one
            connection = await asyncio.wait_for(
                self._get_or_create_connection(account_id, api_key, base_url),
                timeout=timeout
            )
            
            # Mark as in use
            connection.state = ConnectionState.IN_USE
            connection.mark_used()
            
            yield connection
            
        except asyncio.TimeoutError:
            self.pool_metrics['acquire_timeouts'] += 1
            logger.error(f"Connection acquisition timeout after {timeout}s")
            raise
        except Exception as e:
            logger.error(f"Error acquiring connection: {e}")
            if connection:
                connection.record_error()
            raise
        finally:
            # Return connection to pool
            if connection:
                await self._release_connection(connection)
    
    async def _get_or_create_connection(self, account_id: str, api_key: str, base_url: str) -> PooledConnection:
        """Get existing connection or create new one"""
        async with self._lock:
            # Look for available connection for this account
            for conn in self.connections.values():
                if (conn.account_id == account_id and 
                    conn.state == ConnectionState.AVAILABLE and
                    await self._is_connection_healthy(conn)):
                    return conn
            
            # Create new connection if pool not full
            if len(self.connections) < self.pool_size:
                connection = await self.create_connection(account_id, api_key, base_url)
                self.connections[connection.connection_id] = connection
                return connection
            
            # If pool is full, wait for available connection
            # This is a simplified approach; production would have more sophisticated logic
            await asyncio.sleep(0.1)
            return await self._get_or_create_connection(account_id, api_key, base_url)
    
    async def _release_connection(self, connection: PooledConnection):
        """Release connection back to pool"""
        if connection.state != ConnectionState.CLOSED:
            connection.state = ConnectionState.AVAILABLE
            logger.debug(f"Released connection: {connection.connection_id}")
    
    async def _is_connection_healthy(self, connection: PooledConnection) -> bool:
        """
        Check if connection is healthy
        
        Args:
            connection: Connection to check
            
        Returns:
            bool: True if healthy
        """
        # Skip health check if recently checked
        if datetime.utcnow() - connection.last_health_check < timedelta(seconds=30):
            return connection.state != ConnectionState.UNHEALTHY
        
        try:
            # Simple health check - test account endpoint
            start_time = time.time()
            url = f"{connection.base_url}/v3/accounts/{connection.account_id}"
            
            async with connection.session.get(url, timeout=5) as response:
                response_time = time.time() - start_time
                connection.record_response_time(response_time)
                
                if response.status == 200:
                    connection.last_health_check = datetime.utcnow()
                    if connection.state == ConnectionState.UNHEALTHY:
                        connection.state = ConnectionState.AVAILABLE
                        logger.info(f"Connection {connection.connection_id} recovered")
                    return True
                else:
                    logger.warning(f"Health check failed for {connection.connection_id}: {response.status}")
                    connection.state = ConnectionState.UNHEALTHY
                    connection.record_error()
                    return False
                    
        except Exception as e:
            logger.warning(f"Health check error for {connection.connection_id}: {e}")
            connection.state = ConnectionState.UNHEALTHY
            connection.record_error()
            return False
    
    async def _health_check_loop(self):
        """Background task for periodic health checks"""
        while self._initialized:
            try:
                await asyncio.sleep(self._health_check_interval)
                
                if not self.connections:
                    continue
                
                logger.debug(f"Running health checks on {len(self.connections)} connections")
                self.pool_metrics['health_checks_performed'] += 1
                
                # Check all connections
                unhealthy_connections = []
                for connection in self.connections.values():
                    if connection.state == ConnectionState.IN_USE:
                        continue  # Skip connections in use
                    
                    if not await self._is_connection_healthy(connection):
                        unhealthy_connections.append(connection.connection_id)
                        self.pool_metrics['health_check_failures'] += 1
                
                # Clean up persistently unhealthy connections
                await self._cleanup_unhealthy_connections(unhealthy_connections)
                
                # Clean up idle connections
                await self._cleanup_idle_connections()
                
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
    
    async def _cleanup_unhealthy_connections(self, unhealthy_connection_ids: List[str]):
        """Remove unhealthy connections from pool"""
        async with self._lock:
            for conn_id in unhealthy_connection_ids:
                if conn_id in self.connections:
                    connection = self.connections[conn_id]
                    if connection.metrics.error_rate > 0.5:  # More than 50% error rate
                        await self._destroy_connection(connection)
                        del self.connections[conn_id]
                        logger.info(f"Removed unhealthy connection: {conn_id}")
    
    async def _cleanup_idle_connections(self):
        """Remove connections that have been idle too long"""
        now = datetime.utcnow()
        async with self._lock:
            idle_connections = [
                conn_id for conn_id, conn in self.connections.items()
                if (now - conn.metrics.last_used > self.max_idle_time and 
                    conn.state == ConnectionState.AVAILABLE)
            ]
            
            for conn_id in idle_connections:
                connection = self.connections[conn_id]
                await self._destroy_connection(connection)
                del self.connections[conn_id]
                logger.debug(f"Removed idle connection: {conn_id}")
    
    async def _destroy_connection(self, connection: PooledConnection):
        """Properly close and destroy a connection"""
        try:
            connection.state = ConnectionState.CLOSED
            if not connection.session.closed:
                await connection.session.close()
            self.pool_metrics['connections_destroyed'] += 1
            logger.debug(f"Destroyed connection: {connection.connection_id}")
        except Exception as e:
            logger.error(f"Error destroying connection {connection.connection_id}: {e}")
    
    async def close(self):
        """Close the connection pool and all connections"""
        logger.info("Closing connection pool")
        self._initialized = False
        
        # Cancel health check task
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Close all connections
        async with self._lock:
            for connection in self.connections.values():
                await self._destroy_connection(connection)
            self.connections.clear()
        
        logger.info("Connection pool closed")
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        now = datetime.utcnow()
        connection_states = {}
        total_requests = 0
        total_errors = 0
        
        for state in ConnectionState:
            connection_states[state.value] = 0
        
        for conn in self.connections.values():
            connection_states[conn.state.value] += 1
            total_requests += conn.metrics.request_count
            total_errors += conn.metrics.error_count
        
        return {
            'pool_size': self.pool_size,
            'active_connections': len(self.connections),
            'connection_states': connection_states,
            'total_requests': total_requests,
            'total_errors': total_errors,
            'overall_error_rate': total_errors / max(total_requests, 1),
            'pool_metrics': self.pool_metrics.copy(),
            'timestamp': now.isoformat()
        }