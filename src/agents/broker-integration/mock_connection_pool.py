"""
Mock Connection Pool for testing
Provides stub implementation when actual connection pool is not available
"""
import asyncio
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Dict, Optional
from unittest.mock import AsyncMock, MagicMock
import aiohttp


@dataclass
class ConnectionMetrics:
    """Connection metrics"""
    created_at: datetime
    last_used: datetime
    request_count: int = 0
    error_count: int = 0


class MockSession:
    """Mock aiohttp session"""
    
    def __init__(self):
        self.metrics = ConnectionMetrics(
            created_at=datetime.now(timezone.utc),
            last_used=datetime.now(timezone.utc)
        )
        
    def get(self, url, **kwargs):
        """Mock GET request - returns async context manager"""
        response = MagicMock()
        response.status = 200
        response.json = AsyncMock(return_value={
            'transactions': [],
            'lastTransactionID': '1'
        })
        
        class ResponseContext:
            async def __aenter__(self):
                return response
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
                
        return ResponseContext()
        
    async def post(self, url, **kwargs):
        """Mock POST request"""
        response = MagicMock()
        response.status = 200
        response.json = AsyncMock(return_value={'success': True})
        return response
        
    async def close(self):
        """Mock close"""
        pass


class OandaConnectionPool:
    """Mock connection pool for testing"""
    
    def __init__(self, max_connections: int = 10):
        self.max_connections = max_connections
        self.connections: Dict[str, MockSession] = {}
        self.metrics = {
            'total_requests': 0,
            'active_connections': 0,
            'pool_hits': 0,
            'pool_misses': 0
        }
        
    def get_session(self):
        """Get mock session context manager"""
        session = MockSession()
        
        class SessionContext:
            def __init__(self, session):
                self.session = session
                
            async def __aenter__(self):
                return self.session
                
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
                
        return SessionContext(session)
        
    async def health_check(self) -> Dict:
        """Mock health check"""
        return {
            'status': 'healthy',
            'active_connections': len(self.connections),
            'metrics': self.metrics
        }
        
    async def close_all(self):
        """Close all connections"""
        for session in self.connections.values():
            await session.close()
        self.connections.clear()