"""
Unit tests for emergency stop implementation.

Tests emergency stop procedures, position closure integration,
and <100ms response time requirements.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timezone

from ..app.emergency_stop import EmergencyStopManager
from ..app.models import (
    EmergencyStopRequest, EmergencyStopResponse, BreakerLevel, 
    BreakerState, TriggerReason, PositionCloseResponse
)


@pytest.mark.unit
class TestEmergencyStopManager:
    """Test emergency stop manager functionality"""
    
    def test_initialization(self, emergency_stop_manager, breaker_manager):
        """Test emergency stop manager initialization"""
        assert emergency_stop_manager.breaker_manager is breaker_manager
        assert emergency_stop_manager.execution_client is not None
        assert isinstance(emergency_stop_manager._active_stops, dict)
        assert len(emergency_stop_manager._active_stops) == 0
    
    @pytest.mark.asyncio
    async def test_system_emergency_stop_execution(self, emergency_stop_manager, performance_timer):
        """Test system-level emergency stop execution meets <100ms requirement"""
        request = EmergencyStopRequest(
            level=BreakerLevel.SYSTEM,
            reason=TriggerReason.MANUAL_TRIGGER,
            correlation_id="test-system-stop",
            requested_by="test_user"
        )
        
        timer = performance_timer.start()
        response = await emergency_stop_manager.execute_emergency_stop(request)
        timer.stop()
        
        # Verify response structure
        assert isinstance(response, EmergencyStopResponse)
        assert response.success is True
        assert response.level == BreakerLevel.SYSTEM
        assert response.new_state == BreakerState.TRIPPED
        assert response.correlation_id == "test-system-stop"
        
        # Verify <100ms performance requirement
        assert timer.duration_ms < 100, f"Emergency stop took {timer.duration_ms}ms"
        assert response.response_time_ms < 100, f"Reported response time {response.response_time_ms}ms"
    
    @pytest.mark.asyncio
    async def test_account_emergency_stop_execution(self, emergency_stop_manager):
        """Test account-level emergency stop execution"""
        request = EmergencyStopRequest(
            level=BreakerLevel.ACCOUNT,
            reason=TriggerReason.DAILY_DRAWDOWN,
            details={"account_id": "test-account"},
            correlation_id="test-account-stop"
        )
        
        response = await emergency_stop_manager.execute_emergency_stop(request)
        
        assert response.success is True
        assert response.level == BreakerLevel.ACCOUNT
        assert response.correlation_id == "test-account-stop"
    
    @pytest.mark.asyncio
    async def test_agent_emergency_stop_execution(self, emergency_stop_manager):
        """Test agent-level emergency stop execution"""
        request = EmergencyStopRequest(
            level=BreakerLevel.AGENT,
            reason=TriggerReason.SYSTEM_FAILURE,
            correlation_id="test-agent-stop"
        )
        
        response = await emergency_stop_manager.execute_emergency_stop(request)
        
        assert response.success is True
        assert response.level == BreakerLevel.AGENT
        assert response.correlation_id == "test-agent-stop"
    
    @pytest.mark.asyncio
    async def test_already_tripped_breaker(self, emergency_stop_manager, breaker_manager):
        """Test emergency stop on already tripped breaker"""
        # Pre-trip the system breaker
        await breaker_manager.manual_trigger(BreakerLevel.SYSTEM)
        
        request = EmergencyStopRequest(
            level=BreakerLevel.SYSTEM,
            reason=TriggerReason.MANUAL_TRIGGER,
            correlation_id="test-already-tripped"
        )
        
        response = await emergency_stop_manager.execute_emergency_stop(request)
        
        assert response.success is True
        assert response.previous_state == BreakerState.TRIPPED
        assert response.new_state == BreakerState.TRIPPED
        assert "already tripped" in response.message.lower()
    
    @pytest.mark.asyncio
    async def test_force_emergency_stop_on_tripped_breaker(self, emergency_stop_manager, breaker_manager):
        """Test forced emergency stop on already tripped breaker"""
        # Pre-trip the system breaker
        await breaker_manager.manual_trigger(BreakerLevel.SYSTEM)
        
        request = EmergencyStopRequest(
            level=BreakerLevel.SYSTEM,
            reason=TriggerReason.MANUAL_TRIGGER,
            force=True,
            correlation_id="test-force-stop"
        )
        
        response = await emergency_stop_manager.execute_emergency_stop(request)
        
        assert response.success is True
        assert response.previous_state == BreakerState.TRIPPED
        assert response.new_state == BreakerState.TRIPPED
    
    @pytest.mark.asyncio
    async def test_close_all_positions_success(self, emergency_stop_manager, mock_execution_client):
        """Test successful closure of all positions"""
        correlation_id = "test-close-all"
        
        result = await emergency_stop_manager._close_all_positions(correlation_id)
        
        # Verify execution client was called correctly
        mock_execution_client.post.assert_called_once()
        call_args = mock_execution_client.post.call_args
        
        assert call_args[0][0] == "/api/v1/positions/close"
        assert call_args[1]["headers"]["X-Correlation-ID"] == correlation_id
        
        # Verify response
        assert isinstance(result, PositionCloseResponse)
        assert result.success is True
        assert result.positions_closed == 5
        assert result.correlation_id == correlation_id
    
    @pytest.mark.asyncio
    async def test_close_account_positions_success(self, emergency_stop_manager, mock_execution_client):
        """Test successful closure of account positions"""
        account_id = "test-account"
        correlation_id = "test-close-account"
        
        result = await emergency_stop_manager._close_account_positions(account_id, correlation_id)
        
        # Verify execution client was called correctly
        mock_execution_client.post.assert_called_once()
        call_args = mock_execution_client.post.call_args
        
        assert call_args[0][0] == f"/api/v1/accounts/{account_id}/positions/close"
        assert call_args[1]["headers"]["X-Correlation-ID"] == correlation_id
        
        # Verify response
        assert result.success is True
        assert result.correlation_id == correlation_id
    
    @pytest.mark.asyncio
    async def test_position_closure_timeout(self, emergency_stop_manager, mock_execution_client):
        """Test position closure with timeout"""
        import httpx
        
        # Mock timeout exception
        mock_execution_client.post.side_effect = httpx.TimeoutException("Request timeout")
        
        result = await emergency_stop_manager._close_all_positions("test-timeout")
        
        assert result.success is False
        assert "timed out" in result.errors[0].lower()
        assert result.response_time_ms > 0
    
    @pytest.mark.asyncio
    async def test_position_closure_http_error(self, emergency_stop_manager, mock_execution_client):
        """Test position closure with HTTP error"""
        # Mock HTTP error response
        error_response = Mock()
        error_response.status_code = 500
        error_response.text = "Internal server error"
        mock_execution_client.post.return_value = error_response
        
        result = await emergency_stop_manager._close_all_positions("test-error")
        
        assert result.success is False
        assert "500" in result.errors[0]
        assert result.positions_closed == 0
    
    @pytest.mark.asyncio
    async def test_get_active_stops(self, emergency_stop_manager):
        """Test getting list of active emergency stops"""
        # Initially should be empty
        active_stops = await emergency_stop_manager.get_active_stops()
        assert len(active_stops) == 0
        
        # Add a mock active stop
        mock_task = AsyncMock()
        mock_task.done.return_value = False
        emergency_stop_manager._active_stops["test-correlation"] = mock_task
        
        active_stops = await emergency_stop_manager.get_active_stops()
        assert len(active_stops) == 1
        assert active_stops[0]["correlation_id"] == "test-correlation"
        assert active_stops[0]["status"] == "running"
    
    @pytest.mark.asyncio
    async def test_verify_position_closure_success(self, emergency_stop_manager):
        """Test position closure verification with successful completion"""
        # Create a completed task that returns success
        mock_result = PositionCloseResponse(
            success=True,
            positions_closed=3,
            positions_failed=0,
            response_time_ms=150,
            correlation_id="test-verify"
        )
        
        completed_task = AsyncMock()
        completed_task.return_value = mock_result
        
        emergency_stop_manager._active_stops["test-verify"] = completed_task
        
        verification_result = await emergency_stop_manager.verify_position_closure("test-verify", 5)
        
        assert verification_result["success"] is True
        assert verification_result["positions_closed"] == 3
        assert verification_result["correlation_id"] == "test-verify"
    
    @pytest.mark.asyncio
    async def test_verify_position_closure_timeout(self, emergency_stop_manager):
        """Test position closure verification timeout"""
        # Create a task that never completes
        never_complete_task = AsyncMock()
        never_complete_task.side_effect = asyncio.TimeoutError()
        
        emergency_stop_manager._active_stops["test-timeout"] = never_complete_task
        
        verification_result = await emergency_stop_manager.verify_position_closure("test-timeout", 1)
        
        assert verification_result["success"] is False
        assert "timed out" in verification_result["error"].lower()
        assert verification_result["correlation_id"] == "test-timeout"
    
    @pytest.mark.asyncio
    async def test_verify_position_closure_not_found(self, emergency_stop_manager):
        """Test position closure verification for non-existent stop"""
        verification_result = await emergency_stop_manager.verify_position_closure("nonexistent", 5)
        
        assert verification_result["success"] is False
        assert "no active stop found" in verification_result["error"].lower()
        assert verification_result["correlation_id"] == "nonexistent"
    
    @pytest.mark.asyncio
    async def test_cleanup(self, emergency_stop_manager):
        """Test emergency stop manager cleanup"""
        # Add some mock active tasks
        mock_task1 = AsyncMock()
        mock_task1.done.return_value = False
        mock_task2 = AsyncMock()
        mock_task2.done.return_value = True
        
        emergency_stop_manager._active_stops["task1"] = mock_task1
        emergency_stop_manager._active_stops["task2"] = mock_task2
        
        await emergency_stop_manager.cleanup()
        
        # Verify tasks were cancelled
        mock_task1.cancel.assert_called_once()
        # Completed task should not be cancelled
        mock_task2.cancel.assert_not_called()
        
        # Verify client was closed
        emergency_stop_manager.execution_client.aclose.assert_called_once()


@pytest.mark.performance
class TestEmergencyStopPerformance:
    """Performance tests for emergency stop operations"""
    
    @pytest.mark.asyncio
    async def test_emergency_stop_response_time(self, emergency_stop_manager, performance_timer):
        """Test emergency stop meets <100ms response time requirement"""
        request = EmergencyStopRequest(
            level=BreakerLevel.SYSTEM,
            reason=TriggerReason.MANUAL_TRIGGER,
            correlation_id="perf-test"
        )
        
        # Run multiple tests to get consistent timing
        times = []
        for _ in range(10):
            timer = performance_timer.start()
            await emergency_stop_manager.execute_emergency_stop(request)
            timer.stop()
            times.append(timer.duration_ms)
            
            # Reset breaker for next test
            await emergency_stop_manager.breaker_manager.manual_reset(BreakerLevel.SYSTEM)
        
        avg_time = sum(times) / len(times)
        max_time = max(times)
        
        # All executions should be under 100ms
        assert max_time < 100, f"Maximum emergency stop time was {max_time}ms"
        assert avg_time < 50, f"Average emergency stop time was {avg_time}ms"
    
    @pytest.mark.asyncio
    async def test_concurrent_emergency_stops(self, emergency_stop_manager):
        """Test multiple concurrent emergency stop requests"""
        requests = [
            EmergencyStopRequest(
                level=BreakerLevel.SYSTEM,
                reason=TriggerReason.MANUAL_TRIGGER,
                correlation_id=f"concurrent-{i}"
            )
            for i in range(5)
        ]
        
        # Execute all requests concurrently
        start_time = datetime.now(timezone.utc)
        responses = await asyncio.gather(*[
            emergency_stop_manager.execute_emergency_stop(req)
            for req in requests
        ])
        end_time = datetime.now(timezone.utc)
        
        total_time_ms = (end_time - start_time).total_seconds() * 1000
        
        # Verify all responses
        for i, response in enumerate(responses):
            assert response.success is True
            assert response.correlation_id == f"concurrent-{i}"
            assert response.response_time_ms < 100
        
        # Total time should not be much more than individual request time
        assert total_time_ms < 200, f"Concurrent execution took {total_time_ms}ms"


@pytest.mark.integration
class TestEmergencyStopIntegration:
    """Integration tests for emergency stop with other components"""
    
    @pytest.mark.asyncio
    async def test_emergency_stop_with_position_tracking(self, emergency_stop_manager):
        """Test emergency stop with position closure tracking"""
        request = EmergencyStopRequest(
            level=BreakerLevel.SYSTEM,
            reason=TriggerReason.MAX_DRAWDOWN,
            correlation_id="integration-test"
        )
        
        response = await emergency_stop_manager.execute_emergency_stop(request)
        
        # Verify emergency stop succeeded
        assert response.success is True
        
        # Verify position closure task was started
        assert "integration-test" in emergency_stop_manager._active_stops
        
        # Verify active stops tracking
        active_stops = await emergency_stop_manager.get_active_stops()
        assert len(active_stops) == 1
        assert active_stops[0]["correlation_id"] == "integration-test"
    
    @pytest.mark.asyncio
    async def test_emergency_stop_breaker_state_integration(self, emergency_stop_manager, breaker_manager):
        """Test emergency stop properly updates circuit breaker state"""
        request = EmergencyStopRequest(
            level=BreakerLevel.SYSTEM,
            reason=TriggerReason.ERROR_RATE,
            correlation_id="breaker-integration-test"
        )
        
        # Verify initial state
        assert breaker_manager.system_breaker.state == BreakerState.NORMAL
        
        # Execute emergency stop
        response = await emergency_stop_manager.execute_emergency_stop(request)
        
        # Verify emergency stop succeeded
        assert response.success is True
        assert response.previous_state == BreakerState.NORMAL
        assert response.new_state == BreakerState.TRIPPED
        
        # Verify breaker manager state was updated
        assert breaker_manager.system_breaker.state == BreakerState.TRIPPED
        assert breaker_manager.system_breaker.trigger_reason == TriggerReason.ERROR_RATE
    
    @pytest.mark.asyncio
    async def test_position_closure_failure_handling(self, emergency_stop_manager, mock_execution_client):
        """Test emergency stop handles position closure failures gracefully"""
        # Mock execution client to fail
        mock_execution_client.post.side_effect = Exception("Connection failed")
        
        request = EmergencyStopRequest(
            level=BreakerLevel.SYSTEM,
            reason=TriggerReason.VOLATILITY_SPIKE,
            correlation_id="failure-test"
        )
        
        # Emergency stop should still succeed even if position closure fails
        response = await emergency_stop_manager.execute_emergency_stop(request)
        
        assert response.success is True
        assert response.new_state == BreakerState.TRIPPED
        
        # Breaker should be tripped regardless of position closure status
        assert emergency_stop_manager.breaker_manager.system_breaker.state == BreakerState.TRIPPED