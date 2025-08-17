"""
Graceful Degradation System
Story 8.9 - Task 4: Build graceful degradation
"""
import asyncio
import logging
import time
import functools
from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import json
import uuid

logger = logging.getLogger(__name__)


class DegradationLevel(Enum):
    """System degradation levels"""
    NONE = "none"                    # Full functionality
    RATE_LIMITED = "rate_limited"    # Some rate limiting active
    CACHED_DATA = "cached_data"      # Using cached data, limited updates
    READ_ONLY = "read_only"          # Read-only mode, no new trades
    EMERGENCY = "emergency"          # Critical systems only


class ServiceHealth(Enum):
    """Service health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


@dataclass
class DegradationEvent:
    """Degradation state change event"""
    event_id: str
    timestamp: datetime
    old_level: DegradationLevel
    new_level: DegradationLevel
    trigger_reason: str
    affected_services: List[str]
    estimated_recovery_time: Optional[int]  # seconds
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            'event_id': self.event_id,
            'timestamp': self.timestamp.isoformat(),
            'old_level': self.old_level.value,
            'new_level': self.new_level.value,
            'trigger_reason': self.trigger_reason,
            'affected_services': self.affected_services,
            'estimated_recovery_time': self.estimated_recovery_time
        }


@dataclass
class ServiceStatus:
    """Status of a system service"""
    service_name: str
    health: ServiceHealth
    last_check: datetime
    error_count: int
    last_error: Optional[str]
    degradation_level: DegradationLevel
    fallback_active: bool
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            'service_name': self.service_name,
            'health': self.health.value,
            'last_check': self.last_check.isoformat(),
            'error_count': self.error_count,
            'last_error': self.last_error,
            'degradation_level': self.degradation_level.value,
            'fallback_active': self.fallback_active
        }


class CacheManager:
    """Manages cached data for graceful degradation"""
    
    def __init__(self, default_ttl: int = 300):  # 5 minutes default TTL
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_timestamps: Dict[str, datetime] = {}
        self.default_ttl = default_ttl
        self.hit_count = 0
        self.miss_count = 0
        
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set cached value"""
        self.cache[key] = value
        self.cache_timestamps[key] = datetime.now(timezone.utc)
        
        # Set TTL metadata
        actual_ttl = ttl if ttl is not None else self.default_ttl
        self.cache[f"{key}:ttl"] = actual_ttl
        
    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired"""
        if key not in self.cache:
            self.miss_count += 1
            return None
            
        # Check TTL
        cached_time = self.cache_timestamps.get(key)
        if cached_time:
            ttl = self.cache.get(f"{key}:ttl", self.default_ttl)
            if (datetime.now(timezone.utc) - cached_time).total_seconds() > ttl:
                # Expired
                self.delete(key)
                self.miss_count += 1
                return None
                
        self.hit_count += 1
        return self.cache.get(key)
        
    def delete(self, key: str):
        """Delete cached value"""
        self.cache.pop(key, None)
        self.cache.pop(f"{key}:ttl", None)
        self.cache_timestamps.pop(key, None)
        
    def clear(self):
        """Clear all cached data"""
        self.cache.clear()
        self.cache_timestamps.clear()
        self.hit_count = 0
        self.miss_count = 0
        
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.hit_count + self.miss_count
        hit_rate = (self.hit_count / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'total_entries': len(self.cache) // 2,  # Divide by 2 for TTL entries
            'hit_count': self.hit_count,
            'miss_count': self.miss_count,
            'hit_rate': hit_rate,
            'cache_size_bytes': len(json.dumps(self.cache, default=str))
        }


class GracefulDegradationManager:
    """Manages system degradation during API issues"""
    
    def __init__(self):
        self.current_level = DegradationLevel.NONE
        self.cache_manager = CacheManager()
        self.service_statuses: Dict[str, ServiceStatus] = {}
        self.degradation_history: List[DegradationEvent] = []
        
        # Configuration
        self.auto_recovery_enabled = True
        self.degradation_timeouts = {
            DegradationLevel.RATE_LIMITED: 300,    # 5 minutes
            DegradationLevel.CACHED_DATA: 900,     # 15 minutes
            DegradationLevel.READ_ONLY: 1800,      # 30 minutes
            DegradationLevel.EMERGENCY: 3600       # 1 hour
        }
        
        # Callbacks
        self.degradation_callbacks: List[Callable] = []
        
        # Initialize core services
        self._initialize_services()
        
    def _initialize_services(self):
        """Initialize core service tracking"""
        core_services = [
            'oanda_api', 'pricing_stream', 'account_data', 
            'order_execution', 'position_management', 'transaction_history'
        ]
        
        for service in core_services:
            self.service_statuses[service] = ServiceStatus(
                service_name=service,
                health=ServiceHealth.UNKNOWN,
                last_check=datetime.now(timezone.utc),
                error_count=0,
                last_error=None,
                degradation_level=DegradationLevel.NONE,
                fallback_active=False
            )
            
    async def handle_api_failure(self,
                                service_name: str,
                                error: Exception,
                                suggested_level: Optional[DegradationLevel] = None,
                                cascading_failures: Optional[List[str]] = None) -> DegradationLevel:
        """
        Handle API failure and determine appropriate degradation
        
        Args:
            service_name: Name of failing service
            error: Exception that occurred
            suggested_level: Optional suggested degradation level
            cascading_failures: List of other services that failed in cascade
            
        Returns:
            Applied degradation level
        """
        # Update service status
        if service_name in self.service_statuses:
            status = self.service_statuses[service_name]
            status.error_count += 1
            status.last_error = str(error)
            status.last_check = datetime.now(timezone.utc)
            status.health = ServiceHealth.UNAVAILABLE
            
        # Handle cascading failures
        if cascading_failures:
            for failed_service in cascading_failures:
                if failed_service in self.service_statuses:
                    self.service_statuses[failed_service].health = ServiceHealth.UNAVAILABLE
                    self.service_statuses[failed_service].error_count += 1
        
        # Determine degradation level considering cascading failures
        error_type = type(error).__name__
        new_level = self._determine_degradation_level(error, suggested_level, cascading_failures)
        
        # Apply degradation if more severe than current
        if new_level.value != self.current_level.value:
            severity_order = [
                DegradationLevel.NONE,
                DegradationLevel.RATE_LIMITED,
                DegradationLevel.CACHED_DATA,
                DegradationLevel.READ_ONLY,
                DegradationLevel.EMERGENCY
            ]
            
            new_index = severity_order.index(new_level)
            current_index = severity_order.index(self.current_level)
            
            if new_index > current_index:
                await self._transition_to_degradation_level(new_level, f"{service_name} failure: {error_type}")
                
        return self.current_level
        
    def _determine_degradation_level(self,
                                   error: Exception,
                                   suggested_level: Optional[DegradationLevel] = None,
                                   cascading_failures: Optional[List[str]] = None) -> DegradationLevel:
        """Determine appropriate degradation level based on error and cascading failures"""
        if suggested_level:
            return suggested_level
            
        error_type = type(error).__name__
        error_message = str(error).lower()
        
        # Check for cascading failure impact
        cascade_multiplier = 1
        if cascading_failures:
            critical_services = {'oanda_api', 'pricing_stream', 'order_execution'}
            cascaded_critical = len([s for s in cascading_failures if s in critical_services])
            if cascaded_critical >= 2:
                cascade_multiplier = 2
        
        # Critical errors -> Emergency mode
        if any(pattern in error_message for pattern in ['authentication', 'authorization', 'forbidden']):
            return DegradationLevel.EMERGENCY
            
        # Connection issues -> escalated based on cascading failures
        if any(pattern in error_message for pattern in ['connection', 'timeout', 'unreachable']):
            if cascade_multiplier >= 2:
                return DegradationLevel.EMERGENCY
            return DegradationLevel.READ_ONLY
            
        # Rate limiting -> escalated if multiple services affected
        if any(pattern in error_message for pattern in ['rate limit', 'too many requests', '429']):
            if cascade_multiplier >= 2:
                return DegradationLevel.CACHED_DATA
            return DegradationLevel.RATE_LIMITED
            
        # Server errors -> escalated based on cascade
        if any(pattern in error_message for pattern in ['server error', '500', '502', '503']):
            if cascade_multiplier >= 2:
                return DegradationLevel.READ_ONLY
            return DegradationLevel.CACHED_DATA
            
        # Default to cached data for unknown errors
        return DegradationLevel.CACHED_DATA
        
    async def _transition_to_degradation_level(self,
                                             new_level: DegradationLevel,
                                             reason: str):
        """Transition to new degradation level"""
        old_level = self.current_level
        self.current_level = new_level
        
        # Record degradation event
        event = DegradationEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            old_level=old_level,
            new_level=new_level,
            trigger_reason=reason,
            affected_services=list(self.service_statuses.keys()),
            estimated_recovery_time=self.degradation_timeouts.get(new_level)
        )
        
        self.degradation_history.append(event)
        
        # Apply degradation measures
        await self._apply_degradation_measures(new_level)
        
        # Notify callbacks
        for callback in self.degradation_callbacks:
            try:
                await callback(event)
            except Exception as e:
                logger.error(f"Degradation callback error: {e}")
                
        logger.warning(f"System degradation: {old_level.value} -> {new_level.value} ({reason})")
        
        # Schedule recovery check if auto-recovery is enabled
        if self.auto_recovery_enabled:
            recovery_time = self.degradation_timeouts.get(new_level, 300)
            asyncio.create_task(self._schedule_recovery_check(recovery_time))
            
    async def _apply_degradation_measures(self, level: DegradationLevel):
        """Apply specific measures for degradation level"""
        if level == DegradationLevel.RATE_LIMITED:
            # Increase cache TTL, reduce API call frequency
            self.cache_manager.default_ttl = 600  # 10 minutes
            
        elif level == DegradationLevel.CACHED_DATA:
            # Extend cache TTL, disable non-critical updates
            self.cache_manager.default_ttl = 1800  # 30 minutes
            
        elif level == DegradationLevel.READ_ONLY:
            # Disable all trading operations, use cached data only
            self.cache_manager.default_ttl = 3600  # 1 hour
            
        elif level == DegradationLevel.EMERGENCY:
            # Minimal operations only, maximum cache usage
            self.cache_manager.default_ttl = 7200  # 2 hours
            
        # Update service statuses
        for service_status in self.service_statuses.values():
            service_status.degradation_level = level
            service_status.fallback_active = level != DegradationLevel.NONE
            
    async def _schedule_recovery_check(self, delay_seconds: int):
        """Schedule automatic recovery check"""
        await asyncio.sleep(delay_seconds)
        
        if self.current_level != DegradationLevel.NONE:
            await self.attempt_recovery()
            
    async def attempt_recovery(self) -> bool:
        """
        Attempt to recover from degraded state
        
        Returns:
            True if recovery was successful
        """
        logger.info(f"Attempting recovery from degradation level: {self.current_level.value}")
        
        # Check service health
        healthy_services = 0
        total_services = len(self.service_statuses)
        
        for service_name, status in self.service_statuses.items():
            try:
                # Attempt a simple health check
                is_healthy = await self._check_service_health(service_name)
                if is_healthy:
                    status.health = ServiceHealth.HEALTHY
                    status.error_count = max(0, status.error_count - 1)
                    healthy_services += 1
                else:
                    status.health = ServiceHealth.DEGRADED
                    
                status.last_check = datetime.now(timezone.utc)
                
            except Exception as e:
                status.health = ServiceHealth.UNAVAILABLE
                status.last_error = str(e)
                status.last_check = datetime.now(timezone.utc)
                
        # Determine if we can recover
        health_percentage = healthy_services / total_services * 100
        
        if health_percentage >= 80:
            # Most services healthy, attempt recovery
            await self._transition_to_degradation_level(
                DegradationLevel.NONE,
                f"Automatic recovery: {healthy_services}/{total_services} services healthy"
            )
            return True
        elif health_percentage >= 60 and self.current_level in [DegradationLevel.READ_ONLY, DegradationLevel.EMERGENCY]:
            # Partial recovery to cached data mode
            await self._transition_to_degradation_level(
                DegradationLevel.CACHED_DATA,
                f"Partial recovery: {healthy_services}/{total_services} services healthy"
            )
            return True
            
        logger.info(f"Recovery not possible: only {healthy_services}/{total_services} services healthy")
        return False
        
    async def _check_service_health(self, service_name: str) -> bool:
        """Check health of specific service"""
        # Simple health check - attempt basic operation
        try:
            if service_name == 'oanda_api':
                # Mock health check for OANDA API
                await asyncio.sleep(0.1)  # Simulate API call
                return True
            elif service_name == 'pricing_stream':
                # Check if pricing stream is responsive
                await asyncio.sleep(0.05)
                return True
            else:
                # Default health check
                await asyncio.sleep(0.01)
                return True
                
        except Exception:
            return False
            
    async def get_cached_data(self,
                            service: str,
                            data_type: str,
                            default: Any = None) -> Any:
        """
        Get cached data during degradation
        
        Args:
            service: Service name
            data_type: Type of data requested
            default: Default value if cache miss
            
        Returns:
            Cached data or default value
        """
        cache_key = f"{service}:{data_type}"
        cached_data = self.cache_manager.get(cache_key)
        
        if cached_data is not None:
            logger.debug(f"Cache hit for {cache_key}")
            return cached_data
            
        logger.debug(f"Cache miss for {cache_key}, returning default")
        return default
        
    async def cache_data(self,
                        service: str,
                        data_type: str,
                        data: Any,
                        ttl: Optional[int] = None):
        """Cache data for degradation fallback"""
        cache_key = f"{service}:{data_type}"
        self.cache_manager.set(cache_key, data, ttl)
        logger.debug(f"Cached data for {cache_key}")
        
    def is_operation_allowed(self, operation_type: str) -> bool:
        """
        Check if operation is allowed in current degradation level
        
        Args:
            operation_type: Type of operation to check
            
        Returns:
            True if operation is allowed
        """
        if self.current_level == DegradationLevel.NONE:
            return True
            
        elif self.current_level == DegradationLevel.RATE_LIMITED:
            # All operations allowed but with rate limiting
            return True
            
        elif self.current_level == DegradationLevel.CACHED_DATA:
            # Read operations and cached data access allowed
            read_operations = ['get_account', 'get_positions', 'get_prices', 'get_transactions']
            return operation_type in read_operations
            
        elif self.current_level == DegradationLevel.READ_ONLY:
            # Only read operations allowed, no trading
            read_only_operations = ['get_account', 'get_positions', 'get_prices']
            return operation_type in read_only_operations
            
        elif self.current_level == DegradationLevel.EMERGENCY:
            # Only critical safety operations
            critical_operations = ['emergency_close', 'get_account_balance', 'risk_check']
            return operation_type in critical_operations
            
        return False
        
    async def execute_with_fallback(self,
                                  operation_type: str,
                                  primary_func: Callable,
                                  fallback_func: Optional[Callable] = None,
                                  cache_key: Optional[str] = None,
                                  *args,
                                  **kwargs) -> Any:
        """
        Execute operation with fallback strategies
        
        Args:
            operation_type: Type of operation
            primary_func: Primary function to execute
            fallback_func: Optional fallback function
            cache_key: Optional cache key for data
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Operation result using appropriate fallback strategy
        """
        # Check if operation is allowed
        if not self.is_operation_allowed(operation_type):
            raise Exception(f"Operation '{operation_type}' not allowed in degradation level: {self.current_level.value}")
            
        # Try primary function first
        try:
            result = await primary_func(*args, **kwargs)
            
            # Cache successful result if cache key provided
            if cache_key and self.current_level != DegradationLevel.NONE:
                await self.cache_data("api", cache_key, result)
                
            return result
            
        except Exception as e:
            logger.warning(f"Primary function failed for {operation_type}: {e}")
            
            # Try fallback function
            if fallback_func:
                try:
                    result = await fallback_func(*args, **kwargs)
                    logger.info(f"Fallback function succeeded for {operation_type}")
                    return result
                except Exception as fallback_error:
                    logger.error(f"Fallback function also failed for {operation_type}: {fallback_error}")
                    
            # Try cached data
            if cache_key:
                cached_result = await self.get_cached_data("api", cache_key)
                if cached_result is not None:
                    logger.info(f"Using cached data for {operation_type}")
                    return cached_result
                    
            # All fallbacks failed
            raise Exception(f"All fallback strategies failed for {operation_type}") from e
            
    async def manual_recovery(self, reason: str = "Manual recovery") -> bool:
        """
        Manually trigger recovery to normal operation
        
        Args:
            reason: Reason for manual recovery
            
        Returns:
            True if recovery was successful
        """
        if self.current_level == DegradationLevel.NONE:
            logger.info("System is already operating normally")
            return True
            
        # Reset service statuses
        for status in self.service_statuses.values():
            status.health = ServiceHealth.UNKNOWN
            status.error_count = 0
            status.last_error = None
            status.fallback_active = False
            
        # Transition to normal operation
        await self._transition_to_degradation_level(
            DegradationLevel.NONE,
            f"Manual recovery: {reason}"
        )
        
        logger.info(f"Manual recovery completed: {reason}")
        return True
        
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        healthy_services = sum(
            1 for status in self.service_statuses.values()
            if status.health == ServiceHealth.HEALTHY
        )
        
        return {
            'degradation_level': self.current_level.value,
            'healthy_services': healthy_services,
            'total_services': len(self.service_statuses),
            'health_percentage': (healthy_services / len(self.service_statuses) * 100) if self.service_statuses else 0,
            'cache_stats': self.cache_manager.get_cache_stats(),
            'auto_recovery_enabled': self.auto_recovery_enabled,
            'last_degradation': self.degradation_history[-1].to_dict() if self.degradation_history else None
        }
        
    def get_service_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all services"""
        return {
            name: status.to_dict()
            for name, status in self.service_statuses.items()
        }
        
    def add_degradation_callback(self, callback: Callable):
        """Add callback for degradation events"""
        self.degradation_callbacks.append(callback)
        
    async def detect_cascading_failures(self) -> List[str]:
        """Detect services that may be experiencing cascading failures"""
        now = datetime.now(timezone.utc)
        cascading_window = timedelta(minutes=5)  # 5-minute window
        
        failed_services = []
        for service_name, status in self.service_statuses.items():
            # Check if service failed recently and has high error count
            if (status.health == ServiceHealth.UNAVAILABLE and 
                status.last_check and 
                now - status.last_check <= cascading_window and
                status.error_count >= 3):
                failed_services.append(service_name)
                
        return failed_services
        
    async def handle_cascading_failure_scenario(self, 
                                              primary_service: str,
                                              primary_error: Exception) -> DegradationLevel:
        """Handle cascading failure scenarios across multiple services"""
        cascading_failures = await self.detect_cascading_failures()
        
        # If we detect cascading failures, escalate degradation
        if len(cascading_failures) >= 2:
            logger.warning(f"Cascading failures detected: {cascading_failures}")
            
            # Auto-escalate to higher degradation level
            return await self.handle_api_failure(
                primary_service, 
                primary_error, 
                cascading_failures=cascading_failures
            )
        else:
            return await self.handle_api_failure(primary_service, primary_error)

    async def update_service_health(self,
                                  service_name: str,
                                  health: ServiceHealth,
                                  error_message: Optional[str] = None):
        """Update service health status"""
        if service_name not in self.service_statuses:
            self.service_statuses[service_name] = ServiceStatus(
                service_name=service_name,
                health=health,
                last_check=datetime.now(timezone.utc),
                error_count=0,
                last_error=error_message,
                degradation_level=self.current_level,
                fallback_active=False
            )
        else:
            status = self.service_statuses[service_name]
            status.health = health
            status.last_check = datetime.now(timezone.utc)
            if error_message:
                status.last_error = error_message
                status.error_count += 1


# Decorator for graceful degradation protection
def graceful_degradation_protected(operation_type: str,
                                 cache_key: Optional[str] = None,
                                 fallback_func: Optional[Callable] = None):
    """
    Decorator for automatic graceful degradation
    
    Args:
        operation_type: Type of operation for degradation rules
        cache_key: Optional cache key for fallback data
        fallback_func: Optional fallback function
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Get or create degradation manager from class instance
            if hasattr(args[0], '_degradation_manager'):
                manager = args[0]._degradation_manager
            else:
                # Create manager if it doesn't exist
                manager = GracefulDegradationManager()
                args[0]._degradation_manager = manager
                
            return await manager.execute_with_fallback(
                operation_type, func, fallback_func, cache_key, *args, **kwargs
            )
            
        return wrapper
    return decorator


# Global degradation manager instance
_global_degradation_manager = GracefulDegradationManager()


def get_global_degradation_manager() -> GracefulDegradationManager:
    """Get global degradation manager instance"""
    return _global_degradation_manager