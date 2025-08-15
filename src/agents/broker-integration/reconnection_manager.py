"""
OANDA Automatic Reconnection System
Story 8.1 - Task 4: Build automatic reconnection system
"""
import asyncio
import logging
from typing import Dict, Optional, List, Callable, Any
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import time

logger = logging.getLogger(__name__)

class ConnectionState(Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected" 
    RECONNECTING = "reconnecting"
    FAILED = "failed"

@dataclass
class ReconnectionAttempt:
    """Track individual reconnection attempt"""
    attempt_number: int
    timestamp: datetime
    success: bool
    error_message: Optional[str] = None
    response_time_ms: Optional[float] = None

@dataclass
class ReconnectionStats:
    """Track reconnection statistics"""
    total_attempts: int = 0
    successful_attempts: int = 0
    failed_attempts: int = 0
    average_reconnection_time: float = 0.0
    last_successful_reconnection: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    failure_reasons: Dict[str, int] = field(default_factory=dict)
    
    @property
    def success_rate(self) -> float:
        return self.successful_attempts / max(self.total_attempts, 1)
    
    def record_attempt(self, attempt: ReconnectionAttempt):
        """Record a reconnection attempt"""
        self.total_attempts += 1
        if attempt.success:
            self.successful_attempts += 1
            self.last_successful_reconnection = attempt.timestamp
            if attempt.response_time_ms:
                # Update average reconnection time
                current_avg = self.average_reconnection_time
                self.average_reconnection_time = (
                    (current_avg * (self.successful_attempts - 1) + attempt.response_time_ms) / 
                    self.successful_attempts
                )
        else:
            self.failed_attempts += 1
            self.last_failure = attempt.timestamp
            if attempt.error_message:
                self.failure_reasons[attempt.error_message] = (
                    self.failure_reasons.get(attempt.error_message, 0) + 1
                )

class OandaReconnectionManager:
    """Manages automatic reconnection with exponential backoff and state machine"""
    
    def __init__(self, 
                 max_retries: int = 10,
                 initial_delay: float = 1.0,
                 max_delay: float = 30.0,
                 backoff_factor: float = 2.0,
                 target_reconnection_time: float = 5.0):
        
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.target_reconnection_time = target_reconnection_time
        
        # Connection state tracking
        self.connections: Dict[str, ConnectionState] = {}
        self.reconnection_tasks: Dict[str, asyncio.Task] = {}
        self.reconnection_stats: Dict[str, ReconnectionStats] = {}
        self.connection_callbacks: Dict[str, Callable] = {}
        
        # Event subscribers
        self.event_subscribers: Dict[str, List[Callable]] = {
            'connection_lost': [],
            'reconnection_started': [],
            'reconnection_success': [],
            'reconnection_failed': [],
            'manual_reconnection_triggered': []
        }
        
        # Circuit breaker for persistent failures
        self.circuit_breaker_threshold = 5  # failures before circuit opens
        self.circuit_breaker_reset_time = timedelta(minutes=5)
        self.circuit_states: Dict[str, bool] = {}  # True = open (blocked)
        self.circuit_last_failure: Dict[str, datetime] = {}
    
    def register_connection(self, connection_id: str, reconnection_callback: Callable) -> bool:
        """
        Register a connection for monitoring and reconnection
        
        Args:
            connection_id: Unique connection identifier
            reconnection_callback: Async function to call for reconnection
            
        Returns:
            bool: True if registered successfully
        """
        logger.info(f"Registering connection for monitoring: {connection_id}")
        
        self.connections[connection_id] = ConnectionState.CONNECTED
        self.connection_callbacks[connection_id] = reconnection_callback
        self.reconnection_stats[connection_id] = ReconnectionStats()
        self.circuit_states[connection_id] = False  # Circuit closed (allow reconnections)
        
        return True
    
    async def handle_disconnection(self, connection_id: str, error_details: Optional[str] = None) -> bool:
        """
        Handle connection loss and trigger reconnection
        
        Args:
            connection_id: Connection that was lost
            error_details: Optional error information
            
        Returns:
            bool: True if reconnection was initiated
        """
        if connection_id not in self.connections:
            logger.warning(f"Unknown connection disconnected: {connection_id}")
            return False
        
        logger.warning(f"Connection lost: {connection_id} - {error_details}")
        self.connections[connection_id] = ConnectionState.DISCONNECTED
        
        # Notify subscribers
        await self._notify_subscribers('connection_lost', {
            'connection_id': connection_id,
            'timestamp': datetime.utcnow(),
            'error_details': error_details
        })
        
        # Check circuit breaker
        if self.circuit_states.get(connection_id, False):
            logger.warning(f"Circuit breaker open for {connection_id}, skipping reconnection")
            return False
        
        # Cancel any existing reconnection task
        if connection_id in self.reconnection_tasks:
            self.reconnection_tasks[connection_id].cancel()
        
        # Start reconnection task
        self.reconnection_tasks[connection_id] = asyncio.create_task(
            self._reconnection_loop(connection_id)
        )
        
        return True
    
    async def trigger_manual_reconnection(self, connection_id: str) -> bool:
        """
        Manually trigger reconnection for a connection
        
        Args:
            connection_id: Connection to reconnect
            
        Returns:
            bool: True if reconnection was initiated
        """
        logger.info(f"Manual reconnection triggered for: {connection_id}")
        
        # Reset circuit breaker
        self.circuit_states[connection_id] = False
        
        # Notify subscribers
        await self._notify_subscribers('manual_reconnection_triggered', {
            'connection_id': connection_id,
            'timestamp': datetime.utcnow()
        })
        
        return await self.handle_disconnection(connection_id, "manual_trigger")
    
    async def _reconnection_loop(self, connection_id: str):
        """
        Main reconnection loop with exponential backoff
        
        Args:
            connection_id: Connection to reconnect
        """
        logger.info(f"Starting reconnection loop for: {connection_id}")
        self.connections[connection_id] = ConnectionState.RECONNECTING
        
        await self._notify_subscribers('reconnection_started', {
            'connection_id': connection_id,
            'timestamp': datetime.utcnow()
        })
        
        current_delay = self.initial_delay
        callback = self.connection_callbacks[connection_id]
        
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"Reconnection attempt {attempt}/{self.max_retries} for {connection_id}")
                
                # Wait before attempting (except first attempt)
                if attempt > 1:
                    await asyncio.sleep(current_delay)
                
                # Record attempt start time
                start_time = time.time()
                
                # Attempt reconnection
                success = await callback()
                
                # Calculate reconnection time
                reconnection_time = (time.time() - start_time) * 1000  # ms
                
                # Create attempt record
                attempt_record = ReconnectionAttempt(
                    attempt_number=attempt,
                    timestamp=datetime.utcnow(),
                    success=success,
                    response_time_ms=reconnection_time
                )
                
                if success:
                    self.connections[connection_id] = ConnectionState.CONNECTED
                    self.reconnection_stats[connection_id].record_attempt(attempt_record)
                    
                    logger.info(f"Reconnection successful for {connection_id} in {reconnection_time:.1f}ms")
                    
                    await self._notify_subscribers('reconnection_success', {
                        'connection_id': connection_id,
                        'attempt_number': attempt,
                        'reconnection_time_ms': reconnection_time,
                        'timestamp': datetime.utcnow()
                    })
                    
                    # Clean up task reference
                    if connection_id in self.reconnection_tasks:
                        del self.reconnection_tasks[connection_id]
                    
                    return True
                else:
                    # Record failed attempt
                    attempt_record.error_message = "reconnection_callback_returned_false"
                    self.reconnection_stats[connection_id].record_attempt(attempt_record)
                    
                    logger.warning(f"Reconnection attempt {attempt} failed for {connection_id}")
                    
                    # Increase delay for next attempt (exponential backoff)
                    current_delay = min(current_delay * self.backoff_factor, self.max_delay)
                    
            except asyncio.CancelledError:
                logger.info(f"Reconnection cancelled for {connection_id}")
                return False
            except Exception as e:
                # Record failed attempt with error
                attempt_record = ReconnectionAttempt(
                    attempt_number=attempt,
                    timestamp=datetime.utcnow(),
                    success=False,
                    error_message=str(e)
                )
                self.reconnection_stats[connection_id].record_attempt(attempt_record)
                
                logger.error(f"Reconnection attempt {attempt} error for {connection_id}: {e}")
                
                # Increase delay for next attempt
                current_delay = min(current_delay * self.backoff_factor, self.max_delay)
        
        # All attempts failed
        logger.error(f"All reconnection attempts failed for {connection_id}")
        self.connections[connection_id] = ConnectionState.FAILED
        
        # Activate circuit breaker
        self._activate_circuit_breaker(connection_id)
        
        await self._notify_subscribers('reconnection_failed', {
            'connection_id': connection_id,
            'total_attempts': self.max_retries,
            'timestamp': datetime.utcnow()
        })
        
        # Clean up task reference
        if connection_id in self.reconnection_tasks:
            del self.reconnection_tasks[connection_id]
        
        return False
    
    def _activate_circuit_breaker(self, connection_id: str):
        """Activate circuit breaker for persistent failures"""
        self.circuit_states[connection_id] = True
        self.circuit_last_failure[connection_id] = datetime.utcnow()
        logger.warning(f"Circuit breaker activated for {connection_id}")
    
    def get_connection_state(self, connection_id: str) -> Optional[ConnectionState]:
        """Get current state of a connection"""
        return self.connections.get(connection_id)
    
    def get_reconnection_stats(self, connection_id: str) -> Optional[ReconnectionStats]:
        """Get reconnection statistics for a connection"""
        return self.reconnection_stats.get(connection_id)
    
    def get_all_connection_states(self) -> Dict[str, ConnectionState]:
        """Get states of all registered connections"""
        return self.connections.copy()
    
    def subscribe_to_events(self, event_type: str, callback: Callable):
        """
        Subscribe to reconnection events
        
        Args:
            event_type: Type of event to subscribe to
            callback: Function to call when event occurs
        """
        if event_type in self.event_subscribers:
            self.event_subscribers[event_type].append(callback)
            logger.debug(f"Subscribed to {event_type} events")
    
    async def _notify_subscribers(self, event_type: str, event_data: Dict[str, Any]):
        """Notify all subscribers of an event"""
        subscribers = self.event_subscribers.get(event_type, [])
        for callback in subscribers:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event_data)
                else:
                    callback(event_data)
            except Exception as e:
                logger.error(f"Error notifying subscriber for {event_type}: {e}")
    
    async def reset_circuit_breakers(self):
        """Reset circuit breakers that have been open long enough"""
        now = datetime.utcnow()
        
        for connection_id, is_open in self.circuit_states.items():
            if is_open and connection_id in self.circuit_last_failure:
                time_since_failure = now - self.circuit_last_failure[connection_id]
                if time_since_failure >= self.circuit_breaker_reset_time:
                    self.circuit_states[connection_id] = False
                    logger.info(f"Circuit breaker reset for {connection_id}")
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health summary"""
        total_connections = len(self.connections)
        connected_count = sum(1 for state in self.connections.values() if state == ConnectionState.CONNECTED)
        reconnecting_count = sum(1 for state in self.connections.values() if state == ConnectionState.RECONNECTING)
        failed_count = sum(1 for state in self.connections.values() if state == ConnectionState.FAILED)
        
        # Calculate aggregate statistics
        total_attempts = sum(stats.total_attempts for stats in self.reconnection_stats.values())
        total_successful = sum(stats.successful_attempts for stats in self.reconnection_stats.values())
        
        # Circuit breaker info
        open_circuits = sum(1 for is_open in self.circuit_states.values() if is_open)
        
        return {
            'total_connections': total_connections,
            'connection_states': {
                'connected': connected_count,
                'disconnected': total_connections - connected_count - reconnecting_count - failed_count,
                'reconnecting': reconnecting_count,
                'failed': failed_count
            },
            'reconnection_stats': {
                'total_attempts': total_attempts,
                'total_successful': total_successful,
                'overall_success_rate': total_successful / max(total_attempts, 1)
            },
            'circuit_breakers': {
                'total': len(self.circuit_states),
                'open': open_circuits,
                'closed': len(self.circuit_states) - open_circuits
            },
            'active_reconnection_tasks': len(self.reconnection_tasks),
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def shutdown(self):
        """Gracefully shutdown the reconnection manager"""
        logger.info("Shutting down reconnection manager")
        
        # Cancel all active reconnection tasks
        for connection_id, task in self.reconnection_tasks.items():
            logger.info(f"Cancelling reconnection task for {connection_id}")
            task.cancel()
            
        # Wait for tasks to complete
        if self.reconnection_tasks:
            await asyncio.gather(*self.reconnection_tasks.values(), return_exceptions=True)
        
        # Clear state
        self.connections.clear()
        self.reconnection_tasks.clear()
        self.connection_callbacks.clear()
        
        logger.info("Reconnection manager shutdown complete")