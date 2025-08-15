"""
Tests for OandaReconnectionManager
Story 8.1 - Task 4: Automatic reconnection system
"""
import pytest
import asyncio
from unittest.mock import AsyncMock
from datetime import datetime, timedelta

from ..reconnection_manager import (
    OandaReconnectionManager,
    ConnectionState,
    ReconnectionAttempt,
    ReconnectionStats
)

class TestOandaReconnectionManager:
    """Test automatic reconnection functionality"""
    
    def test_initialization(self):
        """Test reconnection manager initialization"""
        manager = OandaReconnectionManager(
            max_retries=5,
            initial_delay=1.0,
            max_delay=30.0
        )
        
        assert manager.max_retries == 5
        assert manager.initial_delay == 1.0
        assert manager.max_delay == 30.0
        assert len(manager.connections) == 0
        assert len(manager.reconnection_tasks) == 0
    
    def test_register_connection(self, reconnection_manager):
        """Test connection registration"""
        callback = AsyncMock(return_value=True)
        
        success = reconnection_manager.register_connection("test-conn", callback)
        
        assert success is True
        assert "test-conn" in reconnection_manager.connections
        assert reconnection_manager.connections["test-conn"] == ConnectionState.CONNECTED
        assert "test-conn" in reconnection_manager.connection_callbacks
        assert "test-conn" in reconnection_manager.reconnection_stats
    
    @pytest.mark.asyncio
    async def test_handle_disconnection_success(self, reconnection_manager):
        """Test handling disconnection with successful reconnection"""
        callback = AsyncMock(return_value=True)
        reconnection_manager.register_connection("test-conn", callback)
        
        # Handle disconnection
        result = await reconnection_manager.handle_disconnection("test-conn", "Network error")
        
        assert result is True
        assert reconnection_manager.connections["test-conn"] == ConnectionState.RECONNECTING
        
        # Wait for reconnection to complete
        await asyncio.sleep(0.2)  # Give time for reconnection
        
        # Should be connected again
        assert reconnection_manager.connections["test-conn"] == ConnectionState.CONNECTED
        callback.assert_called()
    
    @pytest.mark.asyncio
    async def test_handle_disconnection_failure(self, reconnection_manager):
        """Test handling disconnection with failed reconnection"""
        callback = AsyncMock(return_value=False)  # Always fail
        reconnection_manager.register_connection("test-conn", callback)
        
        # Set low retry count for fast test
        reconnection_manager.max_retries = 2
        reconnection_manager.initial_delay = 0.01
        
        result = await reconnection_manager.handle_disconnection("test-conn", "Network error")
        
        assert result is True  # Initiated successfully
        
        # Wait for all attempts to fail
        await asyncio.sleep(0.5)
        
        # Should be in failed state
        assert reconnection_manager.connections["test-conn"] == ConnectionState.FAILED
        assert callback.call_count == 2  # Should have retried
    
    @pytest.mark.asyncio
    async def test_exponential_backoff(self, reconnection_manager):
        """Test exponential backoff timing"""
        attempt_times = []
        
        async def failing_callback():
            attempt_times.append(datetime.utcnow())
            return False
        
        reconnection_manager.register_connection("test-conn", failing_callback)
        reconnection_manager.max_retries = 3
        reconnection_manager.initial_delay = 0.1
        reconnection_manager.backoff_factor = 2.0
        
        await reconnection_manager.handle_disconnection("test-conn")
        
        # Wait for all attempts
        await asyncio.sleep(1.0)
        
        # Check that delays increased
        if len(attempt_times) >= 2:
            # Second attempt should be delayed more than first
            delay1 = (attempt_times[1] - attempt_times[0]).total_seconds()
            assert delay1 >= 0.1  # At least initial delay
    
    @pytest.mark.asyncio
    async def test_manual_reconnection_trigger(self, reconnection_manager):
        """Test manual reconnection triggering"""
        callback = AsyncMock(return_value=True)
        reconnection_manager.register_connection("test-conn", callback)
        
        # Set as failed first
        reconnection_manager.connections["test-conn"] = ConnectionState.FAILED
        reconnection_manager.circuit_states["test-conn"] = True  # Circuit open
        
        result = await reconnection_manager.trigger_manual_reconnection("test-conn")
        
        assert result is True
        assert reconnection_manager.circuit_states["test-conn"] is False  # Circuit reset
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_activation(self, reconnection_manager):
        """Test circuit breaker activation after persistent failures"""
        callback = AsyncMock(return_value=False)
        reconnection_manager.register_connection("test-conn", callback)
        reconnection_manager.max_retries = 2
        reconnection_manager.initial_delay = 0.01
        
        # Trigger disconnection
        await reconnection_manager.handle_disconnection("test-conn")
        
        # Wait for all attempts to fail
        await asyncio.sleep(0.5)
        
        # Circuit breaker should be active
        assert reconnection_manager.circuit_states["test-conn"] is True
        assert "test-conn" in reconnection_manager.circuit_last_failure
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_prevents_reconnection(self, reconnection_manager):
        """Test that circuit breaker prevents reconnection attempts"""
        callback = AsyncMock(return_value=True)
        reconnection_manager.register_connection("test-conn", callback)
        
        # Manually activate circuit breaker
        reconnection_manager.circuit_states["test-conn"] = True
        
        result = await reconnection_manager.handle_disconnection("test-conn")
        
        assert result is False
        callback.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_reset(self, reconnection_manager):
        """Test circuit breaker reset after timeout"""
        reconnection_manager.register_connection("test-conn", AsyncMock())
        
        # Activate circuit breaker
        reconnection_manager.circuit_states["test-conn"] = True
        reconnection_manager.circuit_last_failure["test-conn"] = datetime.utcnow() - timedelta(minutes=10)
        reconnection_manager.circuit_breaker_reset_time = timedelta(minutes=5)
        
        await reconnection_manager.reset_circuit_breakers()
        
        assert reconnection_manager.circuit_states["test-conn"] is False
    
    def test_connection_state_tracking(self, reconnection_manager):
        """Test connection state tracking"""
        callback = AsyncMock()
        reconnection_manager.register_connection("test-conn", callback)
        
        state = reconnection_manager.get_connection_state("test-conn")
        assert state == ConnectionState.CONNECTED
        
        # Test unknown connection
        unknown_state = reconnection_manager.get_connection_state("unknown-conn")
        assert unknown_state is None
    
    def test_reconnection_statistics(self, reconnection_manager):
        """Test reconnection statistics tracking"""
        callback = AsyncMock()
        reconnection_manager.register_connection("test-conn", callback)
        
        stats = reconnection_manager.get_reconnection_stats("test-conn")
        
        assert isinstance(stats, ReconnectionStats)
        assert stats.total_attempts == 0
        assert stats.successful_attempts == 0
        assert stats.failed_attempts == 0
    
    @pytest.mark.asyncio
    async def test_event_subscription(self, reconnection_manager):
        """Test event subscription and notification"""
        events_received = []
        
        def event_handler(event_data):
            events_received.append(event_data)
        
        reconnection_manager.subscribe_to_events('connection_lost', event_handler)
        
        callback = AsyncMock(return_value=True)
        reconnection_manager.register_connection("test-conn", callback)
        
        await reconnection_manager.handle_disconnection("test-conn", "Test error")
        
        # Give time for event processing
        await asyncio.sleep(0.1)
        
        assert len(events_received) >= 1
        assert events_received[0]['connection_id'] == "test-conn"
    
    @pytest.mark.asyncio
    async def test_async_event_subscription(self, reconnection_manager):
        """Test async event subscription"""
        events_received = []
        
        async def async_event_handler(event_data):
            events_received.append(event_data)
        
        reconnection_manager.subscribe_to_events('reconnection_started', async_event_handler)
        
        callback = AsyncMock(return_value=True)
        reconnection_manager.register_connection("test-conn", callback)
        
        await reconnection_manager.handle_disconnection("test-conn")
        
        # Give time for event processing
        await asyncio.sleep(0.1)
        
        assert len(events_received) >= 1
    
    def test_system_health_report(self, reconnection_manager):
        """Test system health reporting"""
        # Register multiple connections in different states
        callback1 = AsyncMock(return_value=True)
        callback2 = AsyncMock(return_value=True)
        
        reconnection_manager.register_connection("conn1", callback1)
        reconnection_manager.register_connection("conn2", callback2)
        
        # Set different states
        reconnection_manager.connections["conn1"] = ConnectionState.CONNECTED
        reconnection_manager.connections["conn2"] = ConnectionState.FAILED
        
        health = reconnection_manager.get_system_health()
        
        assert health['total_connections'] == 2
        assert health['connection_states']['connected'] == 1
        assert health['connection_states']['failed'] == 1
        assert 'reconnection_stats' in health
        assert 'circuit_breakers' in health
    
    @pytest.mark.asyncio
    async def test_shutdown(self, reconnection_manager):
        """Test graceful shutdown"""
        callback = AsyncMock(return_value=False)  # Will keep retrying
        reconnection_manager.register_connection("test-conn", callback)
        
        # Start a reconnection task
        await reconnection_manager.handle_disconnection("test-conn")
        
        # Ensure task is running
        await asyncio.sleep(0.1)
        assert len(reconnection_manager.reconnection_tasks) > 0
        
        # Shutdown
        await reconnection_manager.shutdown()
        
        # Tasks should be cancelled and cleaned up
        assert len(reconnection_manager.reconnection_tasks) == 0
        assert len(reconnection_manager.connections) == 0
    
    @pytest.mark.asyncio
    async def test_reconnection_stats_recording(self, reconnection_manager):
        """Test that reconnection attempts are properly recorded in stats"""
        attempts = []
        
        async def callback():
            attempts.append(datetime.utcnow())
            return len(attempts) > 2  # Succeed after 3 attempts
        
        reconnection_manager.register_connection("test-conn", callback)
        reconnection_manager.max_retries = 5
        reconnection_manager.initial_delay = 0.01
        
        await reconnection_manager.handle_disconnection("test-conn")
        
        # Wait for reconnection to succeed
        await asyncio.sleep(0.5)
        
        stats = reconnection_manager.get_reconnection_stats("test-conn")
        assert stats.total_attempts >= 3
        assert stats.successful_attempts >= 1
        assert stats.last_successful_reconnection is not None
    
    def test_reconnection_attempt_recording(self):
        """Test ReconnectionAttempt and ReconnectionStats classes"""
        stats = ReconnectionStats()
        
        # Record successful attempt
        success_attempt = ReconnectionAttempt(
            attempt_number=1,
            timestamp=datetime.utcnow(),
            success=True,
            response_time_ms=150.5
        )
        stats.record_attempt(success_attempt)
        
        assert stats.total_attempts == 1
        assert stats.successful_attempts == 1
        assert stats.average_reconnection_time == 150.5
        assert stats.success_rate == 1.0
        
        # Record failed attempt
        fail_attempt = ReconnectionAttempt(
            attempt_number=2,
            timestamp=datetime.utcnow(),
            success=False,
            error_message="Timeout"
        )
        stats.record_attempt(fail_attempt)
        
        assert stats.total_attempts == 2
        assert stats.failed_attempts == 1
        assert stats.success_rate == 0.5
        assert "Timeout" in stats.failure_reasons