#!/usr/bin/env python3
"""
Circuit Breaker Agent Client
Connects to the external Circuit Breaker Agent service
"""

import os
import asyncio
import logging
import aiohttp
from typing import Dict, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class CircuitBreakerClient:
    """Client for the external Circuit Breaker Agent"""
    
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or os.getenv("CIRCUIT_BREAKER_URL", "http://localhost:8084")
        self.timeout = aiohttp.ClientTimeout(total=5.0)  # 5 second timeout
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        if not self.session:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def _get(self, endpoint: str) -> Dict:
        """Make GET request to circuit breaker service"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession(timeout=self.timeout)
            
            url = f"{self.base_url}{endpoint}"
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Circuit breaker GET {endpoint} failed: {response.status}")
                    return {"error": f"HTTP {response.status}"}
        except asyncio.TimeoutError:
            logger.warning(f"Circuit breaker timeout on GET {endpoint}")
            return {"error": "timeout"}
        except Exception as e:
            logger.error(f"Circuit breaker GET {endpoint} error: {e}")
            return {"error": str(e)}
    
    async def _post(self, endpoint: str, data: Dict) -> Dict:
        """Make POST request to circuit breaker service"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession(timeout=self.timeout)
            
            url = f"{self.base_url}{endpoint}"
            async with self.session.post(url, json=data) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Circuit breaker POST {endpoint} failed: {response.status}")
                    return {"error": f"HTTP {response.status}"}
        except asyncio.TimeoutError:
            logger.warning(f"Circuit breaker timeout on POST {endpoint}")
            return {"error": "timeout"}
        except Exception as e:
            logger.error(f"Circuit breaker POST {endpoint} error: {e}")
            return {"error": str(e)}
    
    async def get_status(self) -> Dict:
        """Get circuit breaker status"""
        return await self._get("/api/status")
    
    async def get_metrics(self) -> Dict:
        """Get current trading metrics"""
        return await self._get("/api/metrics")
    
    async def evaluate_trade(self, instrument: str, direction: str, units: float, account_id: str) -> Dict:
        """Evaluate if a trade should be allowed"""
        data = {
            "instrument": instrument,
            "direction": direction,
            "units": units,
            "account_id": account_id
        }
        return await self._post("/api/evaluate-trade", data)
    
    async def report_trade(self, trade_result: Dict) -> Dict:
        """Report trade result to update metrics"""
        return await self._post("/api/report-trade", trade_result)
    
    async def is_healthy(self) -> bool:
        """Check if circuit breaker service is healthy"""
        try:
            result = await self._get("/health")
            return result.get("status") == "healthy"
        except:
            return False
    
    async def can_trade(self, account_id: str = None) -> bool:
        """Check if trading is allowed"""
        try:
            status = await self.get_status()
            if "error" in status:
                # If circuit breaker is unavailable, allow trading (fail open)
                logger.warning("Circuit breaker unavailable, allowing trading")
                return True
            
            return status.get("can_trade", True)
        except:
            # Fail open - allow trading if circuit breaker is unreachable
            return True
    
    async def manual_override(self, action: str, reason: str, force: bool = False) -> Dict:
        """Manually override circuit breaker state"""
        data = {
            "action": action,  # "open", "close", "reset"
            "reason": reason,
            "force": force
        }
        return await self._post("/api/override", data)
    
    async def get_alerts(self, limit: int = 10) -> Dict:
        """Get recent alerts"""
        return await self._get(f"/api/alerts?limit={limit}")
    
    async def close(self):
        """Close the client session"""
        if self.session:
            await self.session.close()
            self.session = None


# Global circuit breaker client instance
_client_instance: Optional[CircuitBreakerClient] = None


def get_circuit_breaker_client() -> CircuitBreakerClient:
    """Get global circuit breaker client instance"""
    global _client_instance
    if _client_instance is None:
        _client_instance = CircuitBreakerClient()
    return _client_instance


async def close_circuit_breaker_client():
    """Close the global client instance"""
    global _client_instance
    if _client_instance:
        await _client_instance.close()
        _client_instance = None