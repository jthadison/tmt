"""
Health Aggregator
Aggregates health data from all system services
"""

import asyncio
import aiohttp
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ServiceDefinition:
    """Definition of a service to monitor"""
    name: str
    port: int
    service_type: str  # 'agent', 'core', or 'external'


class HealthAggregator:
    """Aggregates health data from all services"""

    # Service registry - all 11 services
    SERVICES = [
        # AI Agents (8)
        ServiceDefinition("Market Analysis", 8001, "agent"),
        ServiceDefinition("Strategy Analysis", 8002, "agent"),
        ServiceDefinition("Parameter Optimization", 8003, "agent"),
        ServiceDefinition("Learning Safety", 8004, "agent"),
        ServiceDefinition("Disagreement Engine", 8005, "agent"),
        ServiceDefinition("Data Collection", 8006, "agent"),
        ServiceDefinition("Continuous Improvement", 8007, "agent"),
        ServiceDefinition("Pattern Detection", 8008, "agent"),

        # Core Services (3)
        ServiceDefinition("Execution Engine", 8082, "core"),
        ServiceDefinition("Circuit Breaker", 8084, "core"),
        ServiceDefinition("Orchestrator", 8089, "core"),
    ]

    def __init__(
        self,
        timeout: float = 2.0,
        cache_ttl: int = 5,
        localhost: str = "localhost"
    ):
        """
        Initialize health aggregator

        Args:
            timeout: HTTP request timeout in seconds
            cache_ttl: Cache time-to-live in seconds
            localhost: Base host for service URLs
        """
        self.timeout = timeout
        self.cache_ttl = cache_ttl
        self.localhost = localhost
        self._cache: Optional[Dict[str, Any]] = None
        self._cache_timestamp: Optional[datetime] = None

    async def get_detailed_health(
        self,
        circuit_breaker_agent: Any = None,
        oanda_client: Any = None
    ) -> Dict[str, Any]:
        """
        Get detailed health status from all services

        Args:
            circuit_breaker_agent: Circuit breaker agent instance for threshold data
            oanda_client: OANDA client instance for external service status

        Returns:
            Detailed health data dictionary
        """
        # Check cache
        if self._is_cache_valid():
            logger.debug("Returning cached health data")
            return self._cache

        # Fetch all service health data concurrently
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
            tasks = [
                self._check_service_health(session, service)
                for service in self.SERVICES
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        # Categorize results
        agents = []
        services = []

        for service_def, result in zip(self.SERVICES, results):
            if isinstance(result, Exception):
                # Service check failed
                health_data = {
                    "name": service_def.name,
                    "port": service_def.port,
                    "status": "unknown",
                    "latency_ms": None,
                    "last_check": datetime.now(timezone.utc).isoformat()
                }
            else:
                health_data = result

            if service_def.service_type == "agent":
                agents.append(health_data)
            else:
                services.append(health_data)

        # Get circuit breaker status
        circuit_breaker_status = await self._get_circuit_breaker_status(circuit_breaker_agent)

        # Get external services status (OANDA)
        external_services = await self._get_external_services_status(oanda_client)

        # Calculate system metrics
        system_metrics = self._calculate_system_metrics(agents, services)

        # Build response
        response = {
            "agents": agents,
            "services": services,
            "external_services": external_services,
            "circuit_breaker": circuit_breaker_status,
            "system_metrics": system_metrics,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Cache the response
        self._cache = response
        self._cache_timestamp = datetime.now(timezone.utc)

        return response

    async def _check_service_health(
        self,
        session: aiohttp.ClientSession,
        service: ServiceDefinition
    ) -> Dict[str, Any]:
        """
        Check health of a single service

        Args:
            session: aiohttp session
            service: Service definition

        Returns:
            Service health data
        """
        url = f"http://{self.localhost}:{service.port}/health"

        try:
            start_time = datetime.now(timezone.utc)
            async with session.get(url) as response:
                end_time = datetime.now(timezone.utc)
                latency_ms = int((end_time - start_time).total_seconds() * 1000)

                if response.status == 200:
                    data = await response.json()
                    status = data.get("status", "unknown")

                    # Map status to our standard values
                    if status in ["ok", "healthy"]:
                        status = "healthy"
                    elif status in ["degraded", "warning"]:
                        status = "degraded"
                    elif status in ["error", "critical"]:
                        status = "critical"

                    return {
                        "name": service.name,
                        "port": service.port,
                        "status": status,
                        "latency_ms": latency_ms,
                        "last_check": end_time.isoformat()
                    }
                else:
                    return {
                        "name": service.name,
                        "port": service.port,
                        "status": "critical",
                        "latency_ms": latency_ms,
                        "last_check": end_time.isoformat()
                    }

        except asyncio.TimeoutError:
            logger.warning(f"Timeout checking health of {service.name} on port {service.port}")
            return {
                "name": service.name,
                "port": service.port,
                "status": "unknown",
                "latency_ms": None,
                "last_check": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Error checking health of {service.name}: {e}")
            return {
                "name": service.name,
                "port": service.port,
                "status": "unknown",
                "latency_ms": None,
                "last_check": datetime.now(timezone.utc).isoformat()
            }

    async def _get_circuit_breaker_status(
        self,
        circuit_breaker_agent: Any
    ) -> Dict[str, Any]:
        """Get circuit breaker threshold status"""

        # Default values if circuit breaker not available
        default_status = {
            "max_drawdown": {
                "current": 0.0,
                "threshold": 5.0,
                "limit": 10.0
            },
            "daily_loss": {
                "current": 0.0,
                "threshold": 500.0,
                "limit": 1000.0
            },
            "consecutive_losses": {
                "current": 0,
                "threshold": 5,
                "limit": 10
            }
        }

        if not circuit_breaker_agent:
            return default_status

        try:
            # Try to get actual circuit breaker data
            # This will depend on the circuit breaker agent's API
            # For now, return default values
            # TODO: Integrate with actual circuit breaker agent API
            return default_status
        except Exception as e:
            logger.error(f"Error getting circuit breaker status: {e}")
            return default_status

    async def _get_external_services_status(
        self,
        oanda_client: Any
    ) -> List[Dict[str, Any]]:
        """Get external services (OANDA) status"""

        external_services = []

        if oanda_client:
            try:
                # Check OANDA connection
                start_time = datetime.now(timezone.utc)
                # Attempt a lightweight API call to check connectivity
                # This is a placeholder - actual implementation depends on oanda_client API
                connected = True  # TODO: Implement actual check
                end_time = datetime.now(timezone.utc)
                latency_ms = int((end_time - start_time).total_seconds() * 1000)

                external_services.append({
                    "name": "OANDA API",
                    "status": "connected" if connected else "critical",
                    "latency_ms": latency_ms,
                    "last_check": end_time.isoformat()
                })
            except Exception as e:
                logger.error(f"Error checking OANDA status: {e}")
                external_services.append({
                    "name": "OANDA API",
                    "status": "unknown",
                    "latency_ms": None,
                    "last_check": datetime.now(timezone.utc).isoformat()
                })
        else:
            external_services.append({
                "name": "OANDA API",
                "status": "unknown",
                "latency_ms": None,
                "last_check": datetime.now(timezone.utc).isoformat()
            })

        return external_services

    def _calculate_system_metrics(
        self,
        agents: List[Dict[str, Any]],
        services: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate overall system metrics"""

        # Calculate average latency (excluding None values)
        all_latencies = []
        for item in agents + services:
            if item.get("latency_ms") is not None:
                all_latencies.append(item["latency_ms"])

        avg_latency = int(sum(all_latencies) / len(all_latencies)) if all_latencies else 0

        # These would be fetched from actual trading system in production
        # For now, return placeholder values
        return {
            "avg_latency_ms": avg_latency,
            "active_positions": 0,  # TODO: Get from execution engine
            "daily_pnl": 0.0  # TODO: Get from OANDA account summary
        }

    def _is_cache_valid(self) -> bool:
        """Check if cached data is still valid"""
        if not self._cache or not self._cache_timestamp:
            return False

        age = (datetime.now(timezone.utc) - self._cache_timestamp).total_seconds()
        return age < self.cache_ttl

    def clear_cache(self):
        """Clear the cache"""
        self._cache = None
        self._cache_timestamp = None
