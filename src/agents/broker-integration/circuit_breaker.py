"""
OANDA Circuit Breaker System
Story 8.9 - Task 2: Build circuit breaker system
"""
import asyncio
import logging
import time
import functools
from typing import Callable, Any, Optional, Dict, List
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"        # Normal operation
    OPEN = "open"           # Failing fast, not allowing requests
    HALF_OPEN = "half_open" # Testing if service has recovered


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open"""
    pass


@dataclass
class CircuitBreakerEvent:
    """Represents a circuit breaker state change event"""
    event_id: str
    timestamp: datetime
    old_state: CircuitBreakerState
    new_state: CircuitBreakerState
    failure_count: int
    error_message: Optional[str]
    triggered_by: str  # 'failure_threshold', 'recovery_timeout', 'manual_reset', 'half_open_success'
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            'event_id': self.event_id,
            'timestamp': self.timestamp.isoformat(),
            'old_state': self.old_state.value,
            'new_state': self.new_state.value,
            'failure_count': self.failure_count,
            'error_message': self.error_message,
            'triggered_by': self.triggered_by
        }


@dataclass
class CircuitBreakerMetrics:
    """Circuit breaker metrics for monitoring"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    rejected_requests: int  # Requests rejected due to open circuit
    state_changes: List[CircuitBreakerEvent]
    current_state: CircuitBreakerState
    current_failure_count: int
    last_failure_time: Optional[datetime]
    uptime_percentage: float
    mean_time_to_recovery: float  # Average time circuit stays open
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'rejected_requests': self.rejected_requests,
            'success_rate': (self.successful_requests / self.total_requests * 100) if self.total_requests > 0 else 0,
            'current_state': self.current_state.value,
            'current_failure_count': self.current_failure_count,
            'last_failure_time': self.last_failure_time.isoformat() if self.last_failure_time else None,
            'uptime_percentage': self.uptime_percentage,
            'mean_time_to_recovery': self.mean_time_to_recovery,
            'recent_state_changes': [event.to_dict() for event in self.state_changes[-10:]]  # Last 10 events
        }


class OandaCircuitBreaker:
    """Circuit breaker for OANDA API calls"""
    
    def __init__(self,
                 failure_threshold: int = 5,
                 recovery_timeout: int = 60,
                 name: str = "oanda_api"):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        
        # Circuit breaker state
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.last_success_time: Optional[datetime] = None
        self.opened_at: Optional[datetime] = None
        
        # Metrics and monitoring
        self.metrics = CircuitBreakerMetrics(
            total_requests=0,
            successful_requests=0,
            failed_requests=0,
            rejected_requests=0,
            state_changes=[],
            current_state=self.state,
            current_failure_count=0,
            last_failure_time=None,
            uptime_percentage=100.0,
            mean_time_to_recovery=0.0
        )
        
        # Callbacks for notifications
        self.on_state_change_callbacks: List[Callable] = []
        self.on_failure_callbacks: List[Callable] = []
        
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection
        
        Args:
            func: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerOpenError: When circuit breaker is open
        """
        # Check circuit breaker state
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                await self._transition_to_half_open()
            else:
                self.metrics.rejected_requests += 1
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is open. "
                    f"Recovery in {self._time_until_recovery():.1f}s"
                )
                
        # Execute the function
        self.metrics.total_requests += 1
        start_time = time.perf_counter()
        
        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
            
        except Exception as e:
            await self._on_failure(e)
            raise
            
    async def _on_success(self):
        """Handle successful call"""
        self.metrics.successful_requests += 1
        self.last_success_time = datetime.now(timezone.utc)
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            # Half-open test successful, close circuit
            await self._transition_to_closed()
        elif self.state == CircuitBreakerState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0
            self.metrics.current_failure_count = 0
            
        self._update_uptime_metrics()
        
    async def _on_failure(self, error: Exception):
        """Handle failed call"""
        self.metrics.failed_requests += 1
        self.failure_count += 1
        self.last_failure_time = datetime.now(timezone.utc)
        self.metrics.last_failure_time = self.last_failure_time
        self.metrics.current_failure_count = self.failure_count
        
        logger.warning(f"Circuit breaker '{self.name}' failure {self.failure_count}/{self.failure_threshold}: {error}")
        
        # Notify failure callbacks
        for callback in self.on_failure_callbacks:
            try:
                await callback(self, error)
            except Exception as cb_error:
                logger.error(f"Failure callback error: {cb_error}")
                
        # Check if we should open the circuit
        if self.failure_count >= self.failure_threshold:
            await self._transition_to_open()
            
        self._update_uptime_metrics()
        
    async def _transition_to_open(self):
        """Transition circuit breaker to OPEN state"""
        old_state = self.state
        self.state = CircuitBreakerState.OPEN
        self.opened_at = datetime.now(timezone.utc)
        self.metrics.current_state = self.state
        
        await self._record_state_change(
            old_state, self.state, 
            "failure_threshold", 
            f"Failure threshold reached: {self.failure_count}/{self.failure_threshold}"
        )
        
        logger.error(f"Circuit breaker '{self.name}' OPENED due to {self.failure_count} consecutive failures")
        
    async def _transition_to_half_open(self):
        """Transition circuit breaker to HALF_OPEN state"""
        old_state = self.state
        self.state = CircuitBreakerState.HALF_OPEN
        self.metrics.current_state = self.state
        
        await self._record_state_change(
            old_state, self.state,
            "recovery_timeout",
            f"Recovery timeout elapsed: {self.recovery_timeout}s"
        )
        
        logger.info(f"Circuit breaker '{self.name}' transitioned to HALF_OPEN for recovery test")
        
    async def _transition_to_closed(self):
        """Transition circuit breaker to CLOSED state"""
        old_state = self.state
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.metrics.current_failure_count = 0
        self.metrics.current_state = self.state
        
        # Calculate recovery time if we were open
        recovery_time = 0.0
        if self.opened_at:
            recovery_time = (datetime.now(timezone.utc) - self.opened_at).total_seconds()
            self._update_recovery_metrics(recovery_time)
            self.opened_at = None
            
        await self._record_state_change(
            old_state, self.state,
            "half_open_success",
            f"Half-open test successful, circuit closed (recovery time: {recovery_time:.1f}s)"
        )
        
        logger.info(f"Circuit breaker '{self.name}' CLOSED after successful recovery test")
        
    async def _record_state_change(self, 
                                 old_state: CircuitBreakerState,
                                 new_state: CircuitBreakerState,
                                 triggered_by: str,
                                 message: str):
        """Record state change event"""
        event = CircuitBreakerEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            old_state=old_state,
            new_state=new_state,
            failure_count=self.failure_count,
            error_message=message,
            triggered_by=triggered_by
        )
        
        self.metrics.state_changes.append(event)
        
        # Notify state change callbacks
        for callback in self.on_state_change_callbacks:
            try:
                await callback(self, event)
            except Exception as cb_error:
                logger.error(f"State change callback error: {cb_error}")
                
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if not self.last_failure_time:
            return True
            
        time_since_failure = (datetime.now(timezone.utc) - self.last_failure_time).total_seconds()
        return time_since_failure >= self.recovery_timeout
        
    def _time_until_recovery(self) -> float:
        """Calculate time until recovery attempt"""
        if not self.last_failure_time:
            return 0.0
            
        time_since_failure = (datetime.now(timezone.utc) - self.last_failure_time).total_seconds()
        return max(0, self.recovery_timeout - time_since_failure)
        
    def _update_uptime_metrics(self):
        """Update uptime percentage metrics"""
        total_events = len(self.metrics.state_changes)
        if total_events == 0:
            self.metrics.uptime_percentage = 100.0
            return
            
        # Calculate time spent in each state
        open_time = 0.0
        current_time = datetime.now(timezone.utc)
        
        for i, event in enumerate(self.metrics.state_changes):
            if event.new_state == CircuitBreakerState.OPEN:
                # Find when it closed or use current time
                close_time = current_time
                for j in range(i + 1, len(self.metrics.state_changes)):
                    if self.metrics.state_changes[j].old_state == CircuitBreakerState.OPEN:
                        close_time = self.metrics.state_changes[j].timestamp
                        break
                        
                open_time += (close_time - event.timestamp).total_seconds()
                
        # Calculate uptime percentage over last 24 hours
        if self.metrics.state_changes:
            total_time = (current_time - self.metrics.state_changes[0].timestamp).total_seconds()
            total_time = max(total_time, 86400)  # At least 24 hours
            self.metrics.uptime_percentage = max(0, (total_time - open_time) / total_time * 100)
            
    def _update_recovery_metrics(self, recovery_time: float):
        """Update mean time to recovery metrics"""
        # Count recovery events
        recovery_events = [
            event for event in self.metrics.state_changes
            if event.triggered_by == "half_open_success"
        ]
        
        if len(recovery_events) > 0:
            # Calculate rolling average
            total_recovery_time = self.metrics.mean_time_to_recovery * (len(recovery_events) - 1)
            total_recovery_time += recovery_time
            self.metrics.mean_time_to_recovery = total_recovery_time / len(recovery_events)
        else:
            self.metrics.mean_time_to_recovery = recovery_time
            
    async def manual_reset(self, reason: str = "Manual reset") -> bool:
        """
        Manually reset circuit breaker to CLOSED state
        
        Args:
            reason: Reason for manual reset
            
        Returns:
            True if reset was successful
        """
        if self.state == CircuitBreakerState.CLOSED:
            logger.info(f"Circuit breaker '{self.name}' is already closed")
            return True
            
        old_state = self.state
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.metrics.current_failure_count = 0
        self.metrics.current_state = self.state
        self.opened_at = None
        
        await self._record_state_change(
            old_state, self.state,
            "manual_reset",
            f"Manual reset: {reason}"
        )
        
        logger.info(f"Circuit breaker '{self.name}' manually reset to CLOSED")
        return True
        
    def get_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status"""
        return {
            'name': self.name,
            'state': self.state.value,
            'failure_count': self.failure_count,
            'failure_threshold': self.failure_threshold,
            'recovery_timeout': self.recovery_timeout,
            'last_failure_time': self.last_failure_time.isoformat() if self.last_failure_time else None,
            'last_success_time': self.last_success_time.isoformat() if self.last_success_time else None,
            'time_until_recovery': self._time_until_recovery(),
            'opened_at': self.opened_at.isoformat() if self.opened_at else None
        }
        
    def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics"""
        return self.metrics.to_dict()
        
    def add_state_change_callback(self, callback: Callable):
        """Add callback for state change events"""
        self.on_state_change_callbacks.append(callback)
        
    def add_failure_callback(self, callback: Callable):
        """Add callback for failure events"""
        self.on_failure_callbacks.append(callback)
        
    def is_available(self) -> bool:
        """Check if circuit breaker allows requests"""
        return self.state != CircuitBreakerState.OPEN
        
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on circuit breaker"""
        return {
            'healthy': self.state == CircuitBreakerState.CLOSED,
            'state': self.state.value,
            'failure_count': self.failure_count,
            'uptime_percentage': self.metrics.uptime_percentage,
            'last_failure': self.last_failure_time.isoformat() if self.last_failure_time else None,
            'recovery_time_remaining': self._time_until_recovery()
        }


class CircuitBreakerManager:
    """Manages multiple circuit breakers for different services/endpoints"""
    
    def __init__(self):
        self.circuit_breakers: Dict[str, OandaCircuitBreaker] = {}
        self.global_alerts_enabled = True
        
    def get_or_create_breaker(self,
                            name: str,
                            failure_threshold: int = 5,
                            recovery_timeout: int = 60) -> OandaCircuitBreaker:
        """Get existing circuit breaker or create new one"""
        if name not in self.circuit_breakers:
            breaker = OandaCircuitBreaker(
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                name=name
            )
            
            # Add global callbacks
            breaker.add_state_change_callback(self._global_state_change_handler)
            breaker.add_failure_callback(self._global_failure_handler)
            
            self.circuit_breakers[name] = breaker
            logger.info(f"Created circuit breaker: {name}")
            
        return self.circuit_breakers[name]
        
    async def execute_with_breaker(self,
                                 breaker_name: str,
                                 func: Callable,
                                 *args,
                                 **kwargs) -> Any:
        """
        Execute function with named circuit breaker protection
        
        Args:
            breaker_name: Name of circuit breaker to use
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
        """
        breaker = self.get_or_create_breaker(breaker_name)
        return await breaker.call(func, *args, **kwargs)
        
    async def manual_reset_all(self, reason: str = "Manual reset all") -> Dict[str, bool]:
        """Manually reset all circuit breakers"""
        results = {}
        
        for name, breaker in self.circuit_breakers.items():
            try:
                results[name] = await breaker.manual_reset(reason)
            except Exception as e:
                logger.error(f"Failed to reset circuit breaker {name}: {e}")
                results[name] = False
                
        return results
        
    async def manual_reset_breaker(self, name: str, reason: str = "Manual reset") -> bool:
        """Manually reset specific circuit breaker"""
        if name not in self.circuit_breakers:
            logger.warning(f"Circuit breaker '{name}' not found")
            return False
            
        return await self.circuit_breakers[name].manual_reset(reason)
        
    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all circuit breakers"""
        return {
            name: breaker.get_status()
            for name, breaker in self.circuit_breakers.items()
        }
        
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all circuit breakers"""
        return {
            name: breaker.get_metrics()
            for name, breaker in self.circuit_breakers.items()
        }
        
    async def global_health_check(self) -> Dict[str, Any]:
        """Perform health check on all circuit breakers"""
        health_data = {}
        overall_healthy = True
        
        for name, breaker in self.circuit_breakers.items():
            health = await breaker.health_check()
            health_data[name] = health
            
            if not health['healthy']:
                overall_healthy = False
                
        return {
            'overall_healthy': overall_healthy,
            'circuit_breakers': health_data,
            'total_breakers': len(self.circuit_breakers),
            'healthy_breakers': sum(1 for hc in health_data.values() if hc['healthy']),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
    async def _global_state_change_handler(self, breaker: OandaCircuitBreaker, event: CircuitBreakerEvent):
        """Handle state changes across all circuit breakers"""
        if self.global_alerts_enabled:
            logger.info(f"Circuit breaker state change: {breaker.name} {event.old_state.value} -> {event.new_state.value}")
            
            # Send alerts for critical state changes
            if event.new_state == CircuitBreakerState.OPEN:
                await self._send_critical_alert(breaker, event)
                
    async def _global_failure_handler(self, breaker: OandaCircuitBreaker, error: Exception):
        """Handle failures across all circuit breakers"""
        if self.global_alerts_enabled and breaker.failure_count >= breaker.failure_threshold - 1:
            # Send warning when approaching threshold
            await self._send_warning_alert(breaker, error)
            
    async def _send_critical_alert(self, breaker: OandaCircuitBreaker, event: CircuitBreakerEvent):
        """Send critical alert for circuit breaker opening"""
        logger.critical(f"CRITICAL: Circuit breaker '{breaker.name}' opened - immediate attention required")
        
    async def _send_warning_alert(self, breaker: OandaCircuitBreaker, error: Exception):
        """Send warning alert when approaching failure threshold"""
        logger.warning(f"WARNING: Circuit breaker '{breaker.name}' approaching failure threshold: {breaker.failure_count}/{breaker.failure_threshold}")


# Decorator for circuit breaker protection
def circuit_breaker_protected(breaker_name: str,
                            failure_threshold: int = 5,
                            recovery_timeout: int = 60):
    """
    Decorator for automatic circuit breaker protection
    
    Args:
        breaker_name: Name of circuit breaker
        failure_threshold: Number of failures before opening
        recovery_timeout: Seconds before attempting recovery
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Get or create circuit breaker manager from class instance
            if hasattr(args[0], '_circuit_breaker_manager'):
                manager = args[0]._circuit_breaker_manager
            else:
                # Create manager if it doesn't exist
                manager = CircuitBreakerManager()
                args[0]._circuit_breaker_manager = manager
                
            breaker = manager.get_or_create_breaker(
                breaker_name, failure_threshold, recovery_timeout
            )
            
            return await breaker.call(func, *args, **kwargs)
            
        return wrapper
    return decorator


# Global circuit breaker manager instance
_global_circuit_breaker_manager = CircuitBreakerManager()


def get_global_circuit_breaker_manager() -> CircuitBreakerManager:
    """Get global circuit breaker manager instance"""
    return _global_circuit_breaker_manager