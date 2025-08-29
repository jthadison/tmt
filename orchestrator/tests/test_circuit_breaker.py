"""
Tests for Circuit Breaker System
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from app.circuit_breaker import (
    CircuitBreakerManager, BreakerType, BreakerState, 
    BreakerStatus, TradingMetrics
)
from app.exceptions import CircuitBreakerException, SafetyException


class TestBreakerTypes:
    """Test BreakerType and BreakerState enums"""
    
    def test_breaker_type_values(self):
        """Test BreakerType enum values"""
        assert BreakerType.ACCOUNT_LOSS == "account_loss"
        assert BreakerType.DAILY_LOSS == "daily_loss"
        assert BreakerType.CONSECUTIVE_LOSSES == "consecutive_losses"
        assert BreakerType.CORRELATION == "correlation"
        assert BreakerType.VOLATILITY == "volatility"
        assert BreakerType.POSITION_SIZE == "position_size"
        assert BreakerType.RATE_LIMIT == "rate_limit"
        assert BreakerType.SYSTEM_HEALTH == "system_health"
    
    def test_breaker_state_values(self):
        """Test BreakerState enum values"""
        assert BreakerState.CLOSED == "closed"
        assert BreakerState.OPEN == "open"
        assert BreakerState.HALF_OPEN == "half_open"


class TestTradingMetrics:
    """Test TradingMetrics model"""
    
    def test_trading_metrics_creation(self):
        """Test creating TradingMetrics"""
        metrics = TradingMetrics(
            account_id="test_account",
            current_balance=100000.0,
            starting_balance=100000.0,
            daily_pnl=-500.0,
            consecutive_losses=2,
            position_size=5000.0,
            trades_this_hour=3,
            correlation_with_others=0.45,
            market_volatility=1.5
        )
        
        assert metrics.account_id == "test_account"
        assert metrics.current_balance == 100000.0
        assert metrics.daily_pnl == -500.0
        assert metrics.consecutive_losses == 2
        assert metrics.correlation_with_others == 0.45


class TestCircuitBreakerManager:
    """Test CircuitBreakerManager functionality"""
    
    @pytest.fixture
    async def breaker_manager(self, test_settings):
        """Create CircuitBreakerManager instance for testing"""
        with patch('app.circuit_breaker.get_settings', return_value=test_settings):
            manager = CircuitBreakerManager()
            yield manager
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_initialization(self, breaker_manager):
        """Test CircuitBreakerManager initialization"""
        # Should have all breaker types initialized
        expected_breakers = [
            BreakerType.ACCOUNT_LOSS,
            BreakerType.DAILY_LOSS,
            BreakerType.CONSECUTIVE_LOSSES,
            BreakerType.CORRELATION,
            BreakerType.VOLATILITY,
            BreakerType.POSITION_SIZE,
            BreakerType.RATE_LIMIT,
            BreakerType.SYSTEM_HEALTH
        ]
        
        for breaker_type in expected_breakers:
            assert breaker_type in breaker_manager.breakers
            breaker = breaker_manager.breakers[breaker_type]
            assert breaker.state == BreakerState.CLOSED
            assert breaker.failure_count == 0
    
    @pytest.mark.asyncio
    async def test_account_loss_breaker_triggered(self, breaker_manager):
        """Test account loss circuit breaker triggering"""
        metrics = TradingMetrics(
            account_id="test_account",
            current_balance=94000.0,  # 6% loss
            starting_balance=100000.0,
            daily_pnl=0.0,
            consecutive_losses=0,
            position_size=0.0,
            trades_this_hour=0,
            correlation_with_others=0.0,
            market_volatility=1.0
        )
        
        # Should trigger (6% > 5% threshold)
        result = await breaker_manager._check_account_loss_breaker(metrics)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_account_loss_breaker_not_triggered(self, breaker_manager):
        """Test account loss circuit breaker not triggering"""
        metrics = TradingMetrics(
            account_id="test_account",
            current_balance=96000.0,  # 4% loss
            starting_balance=100000.0,
            daily_pnl=0.0,
            consecutive_losses=0,
            position_size=0.0,
            trades_this_hour=0,
            correlation_with_others=0.0,
            market_volatility=1.0
        )
        
        # Should not trigger (4% < 5% threshold)
        result = await breaker_manager._check_account_loss_breaker(metrics)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_daily_loss_breaker_triggered(self, breaker_manager):
        """Test daily loss circuit breaker triggering"""
        metrics = TradingMetrics(
            account_id="test_account",
            current_balance=100000.0,
            starting_balance=100000.0,
            daily_pnl=-3500.0,  # 3.5% daily loss
            consecutive_losses=0,
            position_size=0.0,
            trades_this_hour=0,
            correlation_with_others=0.0,
            market_volatility=1.0
        )
        
        # Should trigger (3.5% > 3% threshold)
        result = await breaker_manager._check_daily_loss_breaker(metrics)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_consecutive_losses_breaker_triggered(self, breaker_manager):
        """Test consecutive losses circuit breaker triggering"""
        metrics = TradingMetrics(
            account_id="test_account",
            current_balance=100000.0,
            starting_balance=100000.0,
            daily_pnl=0.0,
            consecutive_losses=5,  # 5 consecutive losses
            position_size=0.0,
            trades_this_hour=0,
            correlation_with_others=0.0,
            market_volatility=1.0
        )
        
        # Should trigger (5 >= 5 threshold)
        result = await breaker_manager._check_consecutive_losses_breaker(metrics)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_correlation_breaker_triggered(self, breaker_manager):
        """Test correlation circuit breaker triggering"""
        metrics = TradingMetrics(
            account_id="test_account",
            current_balance=100000.0,
            starting_balance=100000.0,
            daily_pnl=0.0,
            consecutive_losses=0,
            position_size=0.0,
            trades_this_hour=0,
            correlation_with_others=0.85,  # 85% correlation
            market_volatility=1.0
        )
        
        # Should trigger (0.85 >= 0.8 threshold)
        result = await breaker_manager._check_correlation_breaker(metrics)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_volatility_breaker_triggered(self, breaker_manager):
        """Test volatility circuit breaker triggering"""
        metrics = TradingMetrics(
            account_id="test_account",
            current_balance=100000.0,
            starting_balance=100000.0,
            daily_pnl=0.0,
            consecutive_losses=0,
            position_size=0.0,
            trades_this_hour=0,
            correlation_with_others=0.0,
            market_volatility=2.5  # 2.5x normal volatility
        )
        
        # Should trigger (2.5 >= 2.0 threshold)
        result = await breaker_manager._check_volatility_breaker(metrics)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_position_size_breaker_triggered(self, breaker_manager):
        """Test position size circuit breaker triggering"""
        metrics = TradingMetrics(
            account_id="test_account",
            current_balance=100000.0,
            starting_balance=100000.0,
            daily_pnl=0.0,
            consecutive_losses=0,
            position_size=1500.0,  # Above max position size
            trades_this_hour=0,
            correlation_with_others=0.0,
            market_volatility=1.0
        )
        
        # Should trigger (1500 >= 1000 threshold)
        result = await breaker_manager._check_position_size_breaker(metrics)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_rate_limit_breaker_triggered(self, breaker_manager):
        """Test rate limit circuit breaker triggering"""
        metrics = TradingMetrics(
            account_id="test_account",
            current_balance=100000.0,
            starting_balance=100000.0,
            daily_pnl=0.0,
            consecutive_losses=0,
            position_size=0.0,
            trades_this_hour=3,  # Above max trades per hour
            correlation_with_others=0.0,
            market_volatility=1.0
        )
        
        # Should trigger (3 >= 2 threshold in test settings)
        result = await breaker_manager._check_rate_limit_breaker(metrics)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_check_all_breakers_pass(self, breaker_manager):
        """Test all breakers passing"""
        # Mock good metrics
        with patch.object(breaker_manager, '_get_trading_metrics') as mock_get_metrics:
            mock_get_metrics.return_value = TradingMetrics(
                account_id="test_account",
                current_balance=100000.0,
                starting_balance=100000.0,
                daily_pnl=100.0,  # Positive P&L
                consecutive_losses=0,
                position_size=500.0,
                trades_this_hour=1,
                correlation_with_others=0.3,
                market_volatility=1.0
            )
            
            result = await breaker_manager.check_all_breakers("test_account", "trade")
            assert result is True
    
    @pytest.mark.asyncio
    async def test_check_all_breakers_fail(self, breaker_manager):
        """Test breaker failing check"""
        # Mock bad metrics
        with patch.object(breaker_manager, '_get_trading_metrics') as mock_get_metrics:
            mock_get_metrics.return_value = TradingMetrics(
                account_id="test_account",
                current_balance=94000.0,  # 6% loss - should trigger
                starting_balance=100000.0,
                daily_pnl=0.0,
                consecutive_losses=0,
                position_size=0.0,
                trades_this_hour=0,
                correlation_with_others=0.0,
                market_volatility=1.0
            )
            
            # Mock event bus to avoid actual event emission
            mock_event_bus = AsyncMock()
            breaker_manager.event_bus = mock_event_bus
            
            result = await breaker_manager.check_all_breakers("test_account", "trade")
            assert result is False
            
            # Should have triggered account loss breaker
            breaker = breaker_manager.breakers[BreakerType.ACCOUNT_LOSS]
            assert breaker.state == BreakerState.OPEN
    
    @pytest.mark.asyncio
    async def test_trigger_breaker(self, breaker_manager):
        """Test triggering a circuit breaker"""
        mock_event_bus = AsyncMock()
        breaker_manager.event_bus = mock_event_bus
        
        await breaker_manager._trigger_breaker(
            BreakerType.ACCOUNT_LOSS,
            "test_account",
            "Test trigger"
        )
        
        breaker = breaker_manager.breakers[BreakerType.ACCOUNT_LOSS]
        assert breaker.state == BreakerState.OPEN
        assert breaker.reason == "Test trigger"
        assert breaker.opened_at is not None
        assert breaker.recovery_time is not None
        assert breaker.failure_count == 1
        
        # Should emit event
        if mock_event_bus:
            mock_event_bus.emit_circuit_breaker_triggered.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_attempt_recovery_successful(self, breaker_manager):
        """Test successful recovery from circuit breaker state"""
        breaker = breaker_manager.breakers[BreakerType.DAILY_LOSS]
        breaker.state = BreakerState.OPEN
        breaker.opened_at = datetime.utcnow() - timedelta(minutes=35)
        breaker.recovery_time = datetime.utcnow() - timedelta(minutes=5)
        breaker.failure_count = 3
        
        await breaker_manager._attempt_recovery(BreakerType.DAILY_LOSS)
        
        # Should recover to closed state
        assert breaker.state == BreakerState.CLOSED
        assert breaker.failure_count == 0
        assert breaker.opened_at is None
        assert breaker.recovery_time is None
    
    @pytest.mark.asyncio
    async def test_force_open_breaker(self, breaker_manager):
        """Test manually opening a circuit breaker"""
        mock_event_bus = AsyncMock()
        breaker_manager.event_bus = mock_event_bus
        
        await breaker_manager.force_open_breaker(
            BreakerType.VOLATILITY,
            "Manual intervention required"
        )
        
        breaker = breaker_manager.breakers[BreakerType.VOLATILITY]
        assert breaker.state == BreakerState.OPEN
        assert breaker.reason == "Manual intervention required"
    
    @pytest.mark.asyncio
    async def test_force_close_breaker(self, breaker_manager):
        """Test manually closing a circuit breaker"""
        # First open the breaker
        breaker = breaker_manager.breakers[BreakerType.RATE_LIMIT]
        breaker.state = BreakerState.OPEN
        breaker.failure_count = 5
        breaker.reason = "Test reason"
        
        await breaker_manager.force_close_breaker(BreakerType.RATE_LIMIT)
        
        # Should be closed and reset
        assert breaker.state == BreakerState.CLOSED
        assert breaker.failure_count == 0
        assert breaker.reason is None
    
    @pytest.mark.asyncio
    async def test_reset_all_breakers(self, breaker_manager):
        """Test resetting all circuit breakers"""
        # Open some breakers
        breaker_manager.breakers[BreakerType.ACCOUNT_LOSS].state = BreakerState.OPEN
        breaker_manager.breakers[BreakerType.DAILY_LOSS].state = BreakerState.HALF_OPEN
        breaker_manager.breakers[BreakerType.VOLATILITY].state = BreakerState.OPEN
        
        await breaker_manager.reset_all_breakers()
        
        # All breakers should be closed
        for breaker in breaker_manager.breakers.values():
            assert breaker.state == BreakerState.CLOSED
            assert breaker.failure_count == 0
    
    def test_get_breaker_status(self, breaker_manager):
        """Test getting breaker status"""
        breaker = breaker_manager.breakers[BreakerType.CORRELATION]
        breaker.state = BreakerState.OPEN
        breaker.failure_count = 2
        
        status = breaker_manager.get_breaker_status(BreakerType.CORRELATION)
        
        assert status.breaker_type == BreakerType.CORRELATION
        assert status.state == BreakerState.OPEN
        assert status.failure_count == 2
    
    def test_get_all_breaker_status(self, breaker_manager):
        """Test getting all breaker statuses"""
        statuses = breaker_manager.get_all_breaker_status()
        
        assert len(statuses) == len(BreakerType)
        for breaker_type in BreakerType:
            assert breaker_type.value in statuses
    
    def test_is_system_healthy_all_closed(self, breaker_manager):
        """Test system health when all breakers are closed"""
        # All breakers start closed
        assert breaker_manager.is_system_healthy() is True
    
    def test_is_system_healthy_some_open(self, breaker_manager):
        """Test system health when some breakers are open"""
        breaker_manager.breakers[BreakerType.ACCOUNT_LOSS].state = BreakerState.OPEN
        
        assert breaker_manager.is_system_healthy() is False
    
    @pytest.mark.asyncio
    async def test_emergency_close_positions(self, breaker_manager):
        """Test emergency position closure"""
        # This is a placeholder test since actual implementation would need OANDA client
        mock_event_bus = AsyncMock()
        breaker_manager.event_bus = mock_event_bus
        
        await breaker_manager._trigger_breaker(
            BreakerType.ACCOUNT_LOSS,
            "test_account",
            "Emergency test"
        )
        
        # In real implementation, this would close positions
        # For now, just verify the breaker was triggered
        breaker = breaker_manager.breakers[BreakerType.ACCOUNT_LOSS]
        assert breaker.state == BreakerState.OPEN


class TestBreakerIntegration:
    """Integration tests for circuit breaker system"""
    
    @pytest.mark.asyncio
    async def test_cascading_breaker_failure(self, test_settings):
        """Test cascading breaker failures"""
        with patch('app.circuit_breaker.get_settings', return_value=test_settings):
            manager = CircuitBreakerManager()
            
            # Mock metrics that trigger multiple breakers
            with patch.object(manager, '_get_trading_metrics') as mock_get_metrics:
                mock_get_metrics.return_value = TradingMetrics(
                    account_id="test_account",
                    current_balance=93000.0,  # 7% loss
                    starting_balance=100000.0,
                    daily_pnl=-4000.0,  # 4% daily loss
                    consecutive_losses=6,  # Above threshold
                    position_size=0.0,
                    trades_this_hour=0,
                    correlation_with_others=0.0,
                    market_volatility=1.0
                )
                
                # Mock event bus
                manager.event_bus = AsyncMock()
                
                result = await manager.check_all_breakers("test_account", "trade")
                assert result is False
                
                # Multiple breakers should be triggered
                assert manager.breakers[BreakerType.ACCOUNT_LOSS].state == BreakerState.OPEN
    
    @pytest.mark.asyncio
    async def test_breaker_recovery_cycle(self, test_settings):
        """Test full breaker lifecycle: closed -> open -> recovery -> closed"""
        with patch('app.circuit_breaker.get_settings', return_value=test_settings):
            manager = CircuitBreakerManager()
            manager.event_bus = AsyncMock()
            
            breaker = manager.breakers[BreakerType.VOLATILITY]
            
            # Initial state
            assert breaker.state == BreakerState.CLOSED
            
            # Trigger breaker
            await manager._trigger_breaker(
                BreakerType.VOLATILITY,
                "test_account",
                "High volatility"
            )
            assert breaker.state == BreakerState.OPEN
            
            # Set recovery time in the past
            breaker.recovery_time = datetime.utcnow() - timedelta(minutes=1)
            
            # Attempt recovery
            await manager._attempt_recovery(BreakerType.VOLATILITY)
            
            # Should be closed again
            assert breaker.state == BreakerState.CLOSED
            assert breaker.failure_count == 0