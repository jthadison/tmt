"""
Unit tests for circuit breaker logic implementation.

Tests the three-tier circuit breaker system, trigger conditions,
recovery logic, and state management.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock

from ..app.breaker_logic import CircuitBreakerManager
from ..app.models import (
    BreakerLevel, BreakerState, TriggerReason, SystemHealth, 
    MarketConditions, AccountMetrics
)


@pytest.mark.unit
class TestCircuitBreakerManager:
    """Test circuit breaker manager functionality"""
    
    def test_initialization(self, breaker_manager):
        """Test circuit breaker manager initialization"""
        assert isinstance(breaker_manager.agent_breakers, dict)
        assert isinstance(breaker_manager.account_breakers, dict)
        assert breaker_manager.system_breaker.level == BreakerLevel.SYSTEM
        assert breaker_manager.system_breaker.state == BreakerState.NORMAL
        assert len(breaker_manager.agent_breakers) == 0
        assert len(breaker_manager.account_breakers) == 0
    
    @pytest.mark.asyncio
    async def test_system_breaker_max_drawdown_trigger(self, breaker_manager, sample_health_metrics):
        """Test system breaker triggers on max drawdown threshold"""
        # Create account metrics with high max drawdown
        account_metrics = {
            "account_1": AccountMetrics(
                account_id="account_1",
                daily_pnl=-500.0,
                daily_drawdown=0.04,
                max_drawdown=0.12,  # Above 8% threshold
                position_count=2,
                total_exposure=10000.0
            )
        }
        
        result = await breaker_manager.check_and_update_breakers(
            health_metrics=sample_health_metrics,
            account_metrics=account_metrics
        )
        
        # Verify system breaker was triggered
        assert len(result['triggered_breakers']) > 0
        assert result['triggered_breakers'][0]['level'] == 'system'
        assert result['triggered_breakers'][0]['reason'] == 'max_drawdown'
        assert breaker_manager.system_breaker.state == BreakerState.TRIPPED
        assert breaker_manager.system_breaker.trigger_reason == TriggerReason.MAX_DRAWDOWN
    
    @pytest.mark.asyncio
    async def test_account_breaker_daily_drawdown_trigger(self, breaker_manager, sample_health_metrics):
        """Test account breaker triggers on daily drawdown threshold"""
        # Create account metrics with high daily drawdown
        account_metrics = {
            "account_1": AccountMetrics(
                account_id="account_1",
                daily_pnl=-800.0,
                daily_drawdown=0.07,  # Above 5% threshold
                max_drawdown=0.04,    # Below system threshold
                position_count=3,
                total_exposure=15000.0
            )
        }
        
        result = await breaker_manager.check_and_update_breakers(
            health_metrics=sample_health_metrics,
            account_metrics=account_metrics
        )
        
        # Verify account breaker was triggered
        assert len(result['triggered_breakers']) > 0
        assert result['triggered_breakers'][0]['level'] == 'account'
        assert result['triggered_breakers'][0]['reason'] == 'daily_drawdown'
        assert 'account_1' in breaker_manager.account_breakers
        assert breaker_manager.account_breakers['account_1'].state == BreakerState.TRIPPED
    
    @pytest.mark.asyncio
    async def test_system_breaker_error_rate_trigger(self, breaker_manager):
        """Test system breaker triggers on high error rate"""
        high_error_health = SystemHealth(
            cpu_usage=45.0,
            memory_usage=60.0,
            disk_usage=70.0,
            error_rate=0.25,  # Above 20% threshold
            response_time=80,
            active_connections=20
        )
        
        result = await breaker_manager.check_and_update_breakers(
            health_metrics=high_error_health
        )
        
        # Verify system breaker was triggered
        assert len(result['triggered_breakers']) > 0
        assert result['triggered_breakers'][0]['level'] == 'system'
        assert result['triggered_breakers'][0]['reason'] == 'error_rate'
        assert breaker_manager.system_breaker.state == BreakerState.TRIPPED
    
    @pytest.mark.asyncio
    async def test_system_breaker_response_time_trigger(self, breaker_manager):
        """Test system breaker triggers on slow response time"""
        slow_response_health = SystemHealth(
            cpu_usage=40.0,
            memory_usage=55.0,
            disk_usage=65.0,
            error_rate=0.05,
            response_time=150,  # Above 100ms threshold
            active_connections=15
        )
        
        result = await breaker_manager.check_and_update_breakers(
            health_metrics=slow_response_health
        )
        
        # Verify system breaker was triggered
        assert len(result['triggered_breakers']) > 0
        assert result['triggered_breakers'][0]['level'] == 'system'
        assert result['triggered_breakers'][0]['reason'] == 'response_time'
        assert breaker_manager.system_breaker.state == BreakerState.TRIPPED
    
    @pytest.mark.asyncio
    async def test_volatility_spike_trigger(self, breaker_manager, sample_health_metrics):
        """Test system breaker triggers on market volatility spike"""
        extreme_market = MarketConditions(
            volatility=4.5,  # Above 3.0 threshold
            gap_detected=False,
            correlation_breakdown=False,
            unusual_volume=False
        )
        
        result = await breaker_manager.check_and_update_breakers(
            health_metrics=sample_health_metrics,
            market_conditions=extreme_market
        )
        
        # Verify system breaker was triggered
        assert len(result['triggered_breakers']) > 0
        assert result['triggered_breakers'][0]['level'] == 'system'
        assert result['triggered_breakers'][0]['reason'] == 'volatility_spike'
        assert breaker_manager.system_breaker.state == BreakerState.TRIPPED
    
    @pytest.mark.asyncio
    async def test_gap_detection_trigger(self, breaker_manager, sample_health_metrics):
        """Test system breaker triggers on market gap detection"""
        gap_market = MarketConditions(
            volatility=1.5,
            gap_detected=True,
            gap_size=0.08,  # 8% gap
            correlation_breakdown=False,
            unusual_volume=False
        )
        
        result = await breaker_manager.check_and_update_breakers(
            health_metrics=sample_health_metrics,
            market_conditions=gap_market
        )
        
        # Verify system breaker was triggered
        assert len(result['triggered_breakers']) > 0
        assert result['triggered_breakers'][0]['level'] == 'system'
        assert result['triggered_breakers'][0]['reason'] == 'gap_detection'
        assert breaker_manager.system_breaker.state == BreakerState.TRIPPED
    
    @pytest.mark.asyncio
    async def test_agent_breaker_high_cpu_trigger(self, breaker_manager):
        """Test agent breaker triggers on high CPU usage"""
        high_cpu_health = SystemHealth(
            cpu_usage=95.0,  # Above 90% threshold
            memory_usage=60.0,
            disk_usage=70.0,
            error_rate=0.05,
            response_time=80,
            active_connections=20
        )
        
        result = await breaker_manager.check_and_update_breakers(
            health_metrics=high_cpu_health
        )
        
        # Verify agent breaker was triggered
        assert len(result['triggered_breakers']) > 0
        assert result['triggered_breakers'][0]['level'] == 'agent'
        assert result['triggered_breakers'][0]['reason'] == 'high_cpu'
        assert 'system-agent' in breaker_manager.agent_breakers
        assert breaker_manager.agent_breakers['system-agent'].state == BreakerState.TRIPPED
    
    @pytest.mark.asyncio
    async def test_manual_trigger(self, breaker_manager):
        """Test manual circuit breaker triggering"""
        success = await breaker_manager.manual_trigger(
            BreakerLevel.SYSTEM,
            "manual-test",
            "Testing manual trigger"
        )
        
        assert success is True
        assert breaker_manager.system_breaker.state == BreakerState.TRIPPED
        assert breaker_manager.system_breaker.trigger_reason == TriggerReason.MANUAL_TRIGGER
    
    @pytest.mark.asyncio
    async def test_manual_reset(self, breaker_manager):
        """Test manual circuit breaker reset"""
        # First trigger a breaker
        await breaker_manager.manual_trigger(BreakerLevel.SYSTEM)
        assert breaker_manager.system_breaker.state == BreakerState.TRIPPED
        
        # Then reset it
        success = await breaker_manager.manual_reset(BreakerLevel.SYSTEM)
        
        assert success is True
        assert breaker_manager.system_breaker.state == BreakerState.NORMAL
        assert breaker_manager.system_breaker.failure_count == 0
        assert breaker_manager.system_breaker.success_count == 0
    
    @pytest.mark.asyncio
    async def test_recovery_scheduling(self, breaker_manager):
        """Test automatic recovery scheduling"""
        # Trigger a breaker
        await breaker_manager._trigger_breaker(
            BreakerLevel.AGENT,
            "test-agent",
            TriggerReason.SYSTEM_FAILURE,
            {"test": "data"}
        )
        
        assert 'test-agent' in breaker_manager.agent_breakers
        assert breaker_manager.agent_breakers['test-agent'].state == BreakerState.TRIPPED
        
        # Verify recovery task was scheduled
        task_key = "agent-test-agent"
        assert task_key in breaker_manager._recovery_tasks
        assert not breaker_manager._recovery_tasks[task_key].done()
    
    @pytest.mark.asyncio
    async def test_half_open_state_transition(self, breaker_manager):
        """Test transition to half-open state during recovery"""
        # Trigger a breaker
        await breaker_manager._trigger_breaker(
            BreakerLevel.AGENT,
            "test-agent",
            TriggerReason.SYSTEM_FAILURE,
            {"test": "data"}
        )
        
        # Manually trigger recovery
        await breaker_manager._attempt_recovery(BreakerLevel.AGENT, "test-agent")
        
        assert breaker_manager.agent_breakers['test-agent'].state == BreakerState.HALF_OPEN
        assert breaker_manager.agent_breakers['test-agent'].success_count == 0
    
    @pytest.mark.asyncio 
    async def test_full_recovery_after_successes(self, breaker_manager):
        """Test full recovery after consecutive successes in half-open state"""
        # Create breaker in half-open state
        await breaker_manager._trigger_breaker(
            BreakerLevel.AGENT,
            "test-agent", 
            TriggerReason.SYSTEM_FAILURE,
            {"test": "data"}
        )
        await breaker_manager._attempt_recovery(BreakerLevel.AGENT, "test-agent")
        
        # Record 3 consecutive successes
        for _ in range(3):
            breaker_manager.record_success(BreakerLevel.AGENT, "test-agent")
        
        # Trigger recovery update
        await breaker_manager._update_recovery_states()
        
        assert breaker_manager.agent_breakers['test-agent'].state == BreakerState.NORMAL
        assert breaker_manager.agent_breakers['test-agent'].success_count == 0
        assert breaker_manager.agent_breakers['test-agent'].failure_count == 0
    
    @pytest.mark.asyncio
    async def test_failure_in_half_open_state(self, breaker_manager):
        """Test that failure in half-open state returns to tripped"""
        # Create breaker in half-open state
        await breaker_manager._trigger_breaker(
            BreakerLevel.AGENT,
            "test-agent",
            TriggerReason.SYSTEM_FAILURE,
            {"test": "data"}
        )
        await breaker_manager._attempt_recovery(BreakerLevel.AGENT, "test-agent")
        
        # Record a failure
        breaker_manager.record_failure(BreakerLevel.AGENT, "test-agent")
        
        assert breaker_manager.agent_breakers['test-agent'].state == BreakerState.TRIPPED
        assert breaker_manager.agent_breakers['test-agent'].success_count == 0
    
    def test_get_all_breaker_status(self, breaker_manager):
        """Test getting status of all circuit breakers"""
        status = breaker_manager.get_all_breaker_status()
        
        assert 'agent_breakers' in status
        assert 'account_breakers' in status
        assert 'system_breaker' in status
        assert 'overall_healthy' in status
        
        assert isinstance(status['agent_breakers'], dict)
        assert isinstance(status['account_breakers'], dict)
        assert isinstance(status['system_breaker'], dict)
        assert isinstance(status['overall_healthy'], bool)
        
        # Should be healthy initially
        assert status['overall_healthy'] is True
    
    @pytest.mark.asyncio
    async def test_response_time_measurement(self, breaker_manager, sample_health_metrics):
        """Test that breaker checks measure response time"""
        result = await breaker_manager.check_and_update_breakers(
            health_metrics=sample_health_metrics
        )
        
        assert 'response_time_ms' in result
        assert isinstance(result['response_time_ms'], int)
        assert result['response_time_ms'] >= 0
    
    @pytest.mark.asyncio
    async def test_no_triggers_on_normal_conditions(self, breaker_manager, sample_health_metrics, sample_account_metrics):
        """Test that no breakers trigger under normal conditions"""
        result = await breaker_manager.check_and_update_breakers(
            health_metrics=sample_health_metrics,
            account_metrics=sample_account_metrics
        )
        
        assert len(result['triggered_breakers']) == 0
        assert result['system_state'] == 'normal'
        assert result['total_breakers_tripped'] == 0
        assert breaker_manager.system_breaker.state == BreakerState.NORMAL


@pytest.mark.performance
class TestCircuitBreakerPerformance:
    """Performance tests for circuit breaker operations"""
    
    @pytest.mark.asyncio
    async def test_breaker_check_performance(self, breaker_manager, sample_health_metrics, performance_timer):
        """Test that breaker checks complete within performance requirements"""
        timer = performance_timer.start()
        
        # Run multiple checks to get average performance
        for _ in range(10):
            await breaker_manager.check_and_update_breakers(
                health_metrics=sample_health_metrics
            )
        
        timer.stop()
        avg_duration_ms = timer.duration_ms / 10
        
        # Should complete well within 100ms requirement
        assert avg_duration_ms < 50, f"Average breaker check took {avg_duration_ms}ms"
    
    @pytest.mark.asyncio
    async def test_emergency_trigger_performance(self, breaker_manager, performance_timer):
        """Test that emergency triggers are fast"""
        timer = performance_timer.start()
        
        await breaker_manager.manual_trigger(
            BreakerLevel.SYSTEM,
            "performance-test",
            "Performance testing"
        )
        
        timer.stop()
        
        # Should complete very quickly for emergency scenarios
        assert timer.duration_ms < 10, f"Emergency trigger took {timer.duration_ms}ms"


@pytest.mark.integration
class TestCircuitBreakerIntegration:
    """Integration tests for circuit breaker with other components"""
    
    @pytest.mark.asyncio
    async def test_multiple_breaker_levels_coordination(self, breaker_manager):
        """Test coordination between different breaker levels"""
        # Trigger agent-level breaker first
        await breaker_manager.manual_trigger(BreakerLevel.AGENT, "agent-1", "Test")
        
        # Trigger system-level breaker
        await breaker_manager.manual_trigger(BreakerLevel.SYSTEM, "system", "Test")
        
        # Verify both are triggered
        status = breaker_manager.get_all_breaker_status()
        assert not status['overall_healthy']
        assert breaker_manager.system_breaker.state == BreakerState.TRIPPED
        assert 'agent-1' in breaker_manager.agent_breakers
        assert breaker_manager.agent_breakers['agent-1'].state == BreakerState.TRIPPED
    
    @pytest.mark.asyncio
    async def test_breaker_state_persistence_across_checks(self, breaker_manager, sample_health_metrics):
        """Test that breaker states persist across multiple health checks"""
        # Trigger a breaker
        await breaker_manager.manual_trigger(BreakerLevel.SYSTEM)
        
        # Run multiple health checks
        for _ in range(5):
            await breaker_manager.check_and_update_breakers(
                health_metrics=sample_health_metrics
            )
        
        # Breaker should still be tripped
        assert breaker_manager.system_breaker.state == BreakerState.TRIPPED