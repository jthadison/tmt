"""
Tests for Circuit Breaker System
Story 8.9 - Task 6: Test circuit breaker system
"""
import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from circuit_breaker import (
    OandaCircuitBreaker, CircuitBreakerState, CircuitBreakerOpenError,
    CircuitBreakerManager, circuit_breaker_protected,
    get_global_circuit_breaker_manager
)


class TestOandaCircuitBreaker:
    """Test circuit breaker core functionality"""
    
    @pytest.fixture
    def circuit_breaker(self):
        """Create circuit breaker for testing"""
        return OandaCircuitBreaker(
            failure_threshold=3,
            recovery_timeout=0.1,  # Short timeout for testing
            name="test_breaker"
        )
        
    @pytest.mark.asyncio
    async def test_successful_call(self, circuit_breaker):
        """Test successful function call"""
        mock_func = AsyncMock(return_value="success")
        
        result = await circuit_breaker.call(mock_func, "arg1", kwarg1="value1")
        
        assert result == "success"
        assert circuit_breaker.state == CircuitBreakerState.CLOSED
        assert circuit_breaker.failure_count == 0
        mock_func.assert_called_with("arg1", kwarg1="value1")
        
    @pytest.mark.asyncio
    async def test_single_failure(self, circuit_breaker):
        """Test single failure doesn't open circuit"""
        mock_func = AsyncMock(side_effect=Exception("Test error"))
        
        with pytest.raises(Exception):
            await circuit_breaker.call(mock_func)
            
        assert circuit_breaker.state == CircuitBreakerState.CLOSED
        assert circuit_breaker.failure_count == 1
        
    @pytest.mark.asyncio
    async def test_failure_threshold_opens_circuit(self, circuit_breaker):
        """Test circuit opens after failure threshold"""
        mock_func = AsyncMock(side_effect=Exception("Test error"))
        
        # Fail enough times to open circuit
        for i in range(circuit_breaker.failure_threshold):
            with pytest.raises(Exception):
                await circuit_breaker.call(mock_func)
                
        assert circuit_breaker.state == CircuitBreakerState.OPEN
        assert circuit_breaker.failure_count == circuit_breaker.failure_threshold
        
    @pytest.mark.asyncio
    async def test_open_circuit_rejects_calls(self, circuit_breaker):
        """Test open circuit rejects calls immediately"""
        mock_func = AsyncMock(side_effect=Exception("Test error"))
        
        # Open the circuit
        for i in range(circuit_breaker.failure_threshold):
            with pytest.raises(Exception):
                await circuit_breaker.call(mock_func)
                
        # Reset mock to ensure it's not called
        mock_func.reset_mock()
        
        # Next call should be rejected without calling function
        with pytest.raises(CircuitBreakerOpenError):
            await circuit_breaker.call(mock_func)
            
        mock_func.assert_not_called()
        
    @pytest.mark.asyncio
    async def test_half_open_recovery_attempt(self, circuit_breaker):
        """Test half-open state after recovery timeout"""
        mock_func = AsyncMock(side_effect=Exception("Test error"))
        
        # Open the circuit
        for i in range(circuit_breaker.failure_threshold):
            with pytest.raises(Exception):
                await circuit_breaker.call(mock_func)
                
        assert circuit_breaker.state == CircuitBreakerState.OPEN
        
        # Wait for recovery timeout
        await asyncio.sleep(circuit_breaker.recovery_timeout + 0.01)
        
        # Configure mock to succeed for recovery test
        mock_func.side_effect = None
        mock_func.return_value = "recovery_success"
        
        # Next call should transition to half-open and succeed
        result = await circuit_breaker.call(mock_func)
        
        assert result == "recovery_success"
        assert circuit_breaker.state == CircuitBreakerState.CLOSED
        assert circuit_breaker.failure_count == 0
        
    @pytest.mark.asyncio
    async def test_half_open_failure_reopens_circuit(self, circuit_breaker):
        """Test failure in half-open state reopens circuit"""
        mock_func = AsyncMock(side_effect=Exception("Test error"))
        
        # Open the circuit
        for i in range(circuit_breaker.failure_threshold):
            with pytest.raises(Exception):
                await circuit_breaker.call(mock_func)
                
        # Wait for recovery timeout
        await asyncio.sleep(circuit_breaker.recovery_timeout + 0.01)
        
        # Keep mock failing for recovery test
        with pytest.raises(Exception):
            await circuit_breaker.call(mock_func)
            
        assert circuit_breaker.state == CircuitBreakerState.OPEN
        
    @pytest.mark.asyncio
    async def test_manual_reset(self, circuit_breaker):
        """Test manual circuit breaker reset"""
        mock_func = AsyncMock(side_effect=Exception("Test error"))
        
        # Open the circuit
        for i in range(circuit_breaker.failure_threshold):
            with pytest.raises(Exception):
                await circuit_breaker.call(mock_func)
                
        assert circuit_breaker.state == CircuitBreakerState.OPEN
        
        # Manual reset
        result = await circuit_breaker.manual_reset("Test reset")
        
        assert result is True
        assert circuit_breaker.state == CircuitBreakerState.CLOSED
        assert circuit_breaker.failure_count == 0
        
    def test_status_reporting(self, circuit_breaker):
        """Test circuit breaker status reporting"""
        status = circuit_breaker.get_status()
        
        assert status['name'] == "test_breaker"
        assert status['state'] == CircuitBreakerState.CLOSED.value
        assert status['failure_count'] == 0
        assert status['failure_threshold'] == 3
        assert status['recovery_timeout'] == 0.1
        
    def test_metrics_tracking(self, circuit_breaker):
        """Test metrics tracking"""
        metrics = circuit_breaker.get_metrics()
        
        assert metrics['total_requests'] == 0
        assert metrics['successful_requests'] == 0
        assert metrics['failed_requests'] == 0
        assert metrics['current_state'] == CircuitBreakerState.CLOSED.value
        
    @pytest.mark.asyncio
    async def test_callbacks(self, circuit_breaker):
        """Test state change and failure callbacks"""
        state_changes = []
        failures = []
        
        async def state_callback(breaker, event):
            state_changes.append((event.old_state, event.new_state))
            
        async def failure_callback(breaker, error):
            failures.append(str(error))
            
        circuit_breaker.add_state_change_callback(state_callback)
        circuit_breaker.add_failure_callback(failure_callback)
        
        mock_func = AsyncMock(side_effect=Exception("Test error"))
        
        # Generate failures to trigger callbacks
        for i in range(circuit_breaker.failure_threshold):
            with pytest.raises(Exception):
                await circuit_breaker.call(mock_func)
                
        # Check callbacks were called
        assert len(failures) == circuit_breaker.failure_threshold
        assert len(state_changes) == 1  # CLOSED -> OPEN
        assert state_changes[0] == (CircuitBreakerState.CLOSED, CircuitBreakerState.OPEN)
        
    @pytest.mark.asyncio
    async def test_health_check(self, circuit_breaker):
        """Test health check functionality"""
        health = await circuit_breaker.health_check()
        
        assert health['healthy'] is True
        assert health['state'] == CircuitBreakerState.CLOSED.value
        assert health['failure_count'] == 0
        
        # Open circuit and check health
        mock_func = AsyncMock(side_effect=Exception("Test error"))
        for i in range(circuit_breaker.failure_threshold):
            with pytest.raises(Exception):
                await circuit_breaker.call(mock_func)
                
        health = await circuit_breaker.health_check()
        assert health['healthy'] is False
        assert health['state'] == CircuitBreakerState.OPEN.value
        
    def test_is_available(self, circuit_breaker):
        """Test availability check"""
        assert circuit_breaker.is_available() is True
        
        # Manually set to open state
        circuit_breaker.state = CircuitBreakerState.OPEN
        assert circuit_breaker.is_available() is False
        
        circuit_breaker.state = CircuitBreakerState.HALF_OPEN
        assert circuit_breaker.is_available() is True


class TestCircuitBreakerManager:
    """Test circuit breaker manager functionality"""
    
    @pytest.fixture
    def manager(self):
        """Create circuit breaker manager for testing"""
        return CircuitBreakerManager()
        
    def test_get_or_create_breaker(self, manager):
        """Test getting or creating circuit breakers"""
        breaker1 = manager.get_or_create_breaker("test1")
        breaker2 = manager.get_or_create_breaker("test1")  # Same name
        breaker3 = manager.get_or_create_breaker("test2")  # Different name
        
        assert breaker1 is breaker2  # Same instance
        assert breaker1 is not breaker3  # Different instance
        assert breaker1.name == "test1"
        assert breaker3.name == "test2"
        
    @pytest.mark.asyncio
    async def test_execute_with_breaker(self, manager):
        """Test executing function with named breaker"""
        mock_func = AsyncMock(return_value="success")
        
        result = await manager.execute_with_breaker("test_breaker", mock_func, "arg1")
        
        assert result == "success"
        mock_func.assert_called_with("arg1")
        assert "test_breaker" in manager.circuit_breakers
        
    @pytest.mark.asyncio
    async def test_manual_reset_all(self, manager):
        """Test manually resetting all circuit breakers"""
        # Create some breakers
        manager.get_or_create_breaker("breaker1")
        manager.get_or_create_breaker("breaker2")
        
        results = await manager.manual_reset_all("Test reset all")
        
        assert results["breaker1"] is True
        assert results["breaker2"] is True
        
    @pytest.mark.asyncio
    async def test_manual_reset_specific_breaker(self, manager):
        """Test manually resetting specific breaker"""
        manager.get_or_create_breaker("test_breaker")
        
        result = await manager.manual_reset_breaker("test_breaker", "Test reset")
        assert result is True
        
        # Test non-existent breaker
        result = await manager.manual_reset_breaker("nonexistent", "Test reset")
        assert result is False
        
    def test_get_all_status(self, manager):
        """Test getting status of all breakers"""
        manager.get_or_create_breaker("breaker1")
        manager.get_or_create_breaker("breaker2")
        
        status = manager.get_all_status()
        
        assert "breaker1" in status
        assert "breaker2" in status
        assert status["breaker1"]["state"] == CircuitBreakerState.CLOSED.value
        
    def test_get_all_metrics(self, manager):
        """Test getting metrics for all breakers"""
        manager.get_or_create_breaker("breaker1")
        manager.get_or_create_breaker("breaker2")
        
        metrics = manager.get_all_metrics()
        
        assert "breaker1" in metrics
        assert "breaker2" in metrics
        assert metrics["breaker1"]["current_state"] == CircuitBreakerState.CLOSED.value
        
    @pytest.mark.asyncio
    async def test_global_health_check(self, manager):
        """Test global health check"""
        manager.get_or_create_breaker("healthy_breaker")
        manager.get_or_create_breaker("unhealthy_breaker")
        
        # Make one breaker unhealthy
        unhealthy = manager.circuit_breakers["unhealthy_breaker"]
        unhealthy.state = CircuitBreakerState.OPEN
        
        health = await manager.global_health_check()
        
        assert health["overall_healthy"] is False
        assert health["total_breakers"] == 2
        assert health["healthy_breakers"] == 1
        assert "healthy_breaker" in health["circuit_breakers"]
        assert "unhealthy_breaker" in health["circuit_breakers"]


class TestCircuitBreakerDecorator:
    """Test circuit breaker decorator"""
    
    @pytest.mark.asyncio
    async def test_decorator_success(self):
        """Test successful decorated function"""
        call_count = 0
        
        @circuit_breaker_protected("test_breaker", failure_threshold=2)
        async def test_func(self, value):
            nonlocal call_count
            call_count += 1
            return f"result: {value}"
            
        # Create mock self object
        mock_self = MagicMock()
        
        result = await test_func(mock_self, "test")
        assert result == "result: test"
        assert call_count == 1
        
    @pytest.mark.asyncio
    async def test_decorator_with_failures(self):
        """Test decorated function with failures"""
        call_count = 0
        
        @circuit_breaker_protected("failing_breaker", failure_threshold=2)
        async def test_func(self):
            nonlocal call_count
            call_count += 1
            raise Exception("Always fails")
            
        # Create mock self object
        mock_self = MagicMock()
        
        # First two failures should work
        with pytest.raises(Exception):
            await test_func(mock_self)
        with pytest.raises(Exception):
            await test_func(mock_self)
            
        # Third should be circuit breaker error
        with pytest.raises(CircuitBreakerOpenError):
            await test_func(mock_self)
            
        assert call_count == 2  # Only called twice due to circuit breaker


class TestGlobalCircuitBreakerManager:
    """Test global circuit breaker manager"""
    
    def test_get_global_manager(self):
        """Test getting global manager instance"""
        manager1 = get_global_circuit_breaker_manager()
        manager2 = get_global_circuit_breaker_manager()
        
        assert manager1 is manager2  # Same instance
        assert isinstance(manager1, CircuitBreakerManager)


class TestMetricsAndUptime:
    """Test metrics calculation and uptime tracking"""
    
    @pytest.mark.asyncio
    async def test_uptime_calculation(self):
        """Test uptime percentage calculation"""
        breaker = OandaCircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
        mock_func = AsyncMock(side_effect=Exception("Test error"))
        
        # Open circuit
        for i in range(breaker.failure_threshold):
            with pytest.raises(Exception):
                await breaker.call(mock_func)
                
        # Wait a bit while open
        await asyncio.sleep(0.05)
        
        # Close circuit manually
        await breaker.manual_reset("Test")
        
        metrics = breaker.get_metrics()
        assert metrics["uptime_percentage"] < 100.0
        
    @pytest.mark.asyncio
    async def test_recovery_time_tracking(self):
        """Test mean time to recovery tracking"""
        breaker = OandaCircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
        mock_func = AsyncMock()
        
        # Open circuit
        mock_func.side_effect = Exception("Test error")
        for i in range(breaker.failure_threshold):
            with pytest.raises(Exception):
                await breaker.call(mock_func)
                
        # Wait for recovery timeout
        await asyncio.sleep(breaker.recovery_timeout + 0.01)
        
        # Successful recovery
        mock_func.side_effect = None
        mock_func.return_value = "success"
        
        result = await breaker.call(mock_func)
        assert result == "success"
        
        metrics = breaker.get_metrics()
        assert metrics["mean_time_to_recovery"] > 0


class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_zero_failure_threshold(self):
        """Test circuit breaker with zero failure threshold (should work as 1)"""
        # Note: Real implementation might want to validate this
        breaker = OandaCircuitBreaker(failure_threshold=0)
        assert breaker.failure_threshold == 0
        
    def test_negative_recovery_timeout(self):
        """Test circuit breaker with negative recovery timeout"""
        breaker = OandaCircuitBreaker(recovery_timeout=-1)
        assert breaker.recovery_timeout == -1
        
        # Should always be ready for recovery
        assert breaker._should_attempt_reset() is True
        
    @pytest.mark.asyncio
    async def test_callback_exception_handling(self):
        """Test that callback exceptions don't break circuit breaker"""
        breaker = OandaCircuitBreaker(failure_threshold=2)
        
        async def failing_callback(breaker, event):
            raise Exception("Callback error")
            
        breaker.add_state_change_callback(failing_callback)
        
        mock_func = AsyncMock(side_effect=Exception("Test error"))
        
        # Should still work despite callback failure
        for i in range(breaker.failure_threshold):
            with pytest.raises(Exception):
                await breaker.call(mock_func)
                
        assert breaker.state == CircuitBreakerState.OPEN
        
    @pytest.mark.asyncio
    async def test_concurrent_calls(self):
        """Test concurrent calls to circuit breaker"""
        breaker = OandaCircuitBreaker(failure_threshold=3)
        
        async def slow_func():
            await asyncio.sleep(0.01)
            return "success"
            
        # Execute multiple concurrent calls
        tasks = [breaker.call(slow_func) for _ in range(5)]
        results = await asyncio.gather(*tasks)
        
        assert all(result == "success" for result in results)
        assert breaker.metrics.total_requests == 5
        assert breaker.metrics.successful_requests == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])