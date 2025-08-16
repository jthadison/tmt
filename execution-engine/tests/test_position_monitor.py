"""
Comprehensive tests for Position Monitor functionality.

Tests position monitoring, alerts, risk assessment, performance tracking,
and optimization suggestions.
"""

import pytest
import asyncio
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch

from src.oanda.position_monitor import (
    PositionMonitor,
    AlertType,
    AlertSeverity,
    AlertConfig,
    PositionAlert,
    RiskMetrics,
    PerformanceMetrics
)
from src.oanda.position_manager import (
    OandaPositionManager,
    PositionInfo,
    PositionSide
)


@pytest.fixture
def mock_position_manager():
    """Mock position manager"""
    manager = Mock(spec=OandaPositionManager)
    manager.position_cache = {}
    manager.get_open_positions = AsyncMock()
    return manager


@pytest.fixture
def mock_alert_callback():
    """Mock alert callback function"""
    return AsyncMock()


@pytest.fixture
def position_monitor(mock_position_manager, mock_alert_callback):
    """Position monitor instance for testing"""
    return PositionMonitor(
        mock_position_manager,
        mock_alert_callback,
        monitoring_interval=1  # Short interval for testing
    )


@pytest.fixture
def sample_profitable_position():
    """Sample profitable position for testing"""
    return PositionInfo(
        position_id="EUR_USD_long",
        instrument="EUR_USD",
        side=PositionSide.LONG,
        units=Decimal('10000'),
        entry_price=Decimal('1.0500'),
        current_price=Decimal('1.0575'),
        unrealized_pl=Decimal('75.00'),
        swap_charges=Decimal('1.25'),
        commission=Decimal('0.50'),
        margin_used=Decimal('350'),
        opened_at=datetime.now(timezone.utc) - timedelta(hours=5),
        age_hours=5.0
    )


@pytest.fixture
def sample_losing_position():
    """Sample losing position for testing"""
    return PositionInfo(
        position_id="GBP_USD_short",
        instrument="GBP_USD",
        side=PositionSide.SHORT,
        units=Decimal('5000'),
        entry_price=Decimal('1.2500'),
        current_price=Decimal('1.2550'),
        unrealized_pl=Decimal('-25.00'),
        swap_charges=Decimal('0.50'),
        commission=Decimal('0.25'),
        margin_used=Decimal('200'),
        opened_at=datetime.now(timezone.utc) - timedelta(hours=1),
        age_hours=1.0
    )


@pytest.fixture
def sample_old_position():
    """Sample old position for testing"""
    return PositionInfo(
        position_id="USD_JPY_long",
        instrument="USD_JPY",
        side=PositionSide.LONG,
        units=Decimal('100000'),
        entry_price=Decimal('150.00'),
        current_price=Decimal('150.25'),
        unrealized_pl=Decimal('25.00'),
        swap_charges=Decimal('2.00'),
        commission=Decimal('1.00'),
        margin_used=Decimal('500'),
        opened_at=datetime.now(timezone.utc) - timedelta(hours=30),
        age_hours=30.0
    )


class TestAlertConfiguration:
    """Test suite for alert configuration and management"""
    
    @pytest.mark.asyncio
    async def test_configure_alert(self, position_monitor):
        """Test configuring an alert"""
        await position_monitor.configure_alert(
            AlertType.PROFIT_TARGET,
            Decimal('150'),
            enabled=True,
            severity=AlertSeverity.INFO,
            cooldown_minutes=15
        )
        
        # Verify configuration
        config = position_monitor.alert_configs[AlertType.PROFIT_TARGET]
        assert config.threshold == Decimal('150')
        assert config.enabled is True
        assert config.severity == AlertSeverity.INFO
        assert config.cooldown_minutes == 15
        
    def test_default_alert_configurations(self, position_monitor):
        """Test default alert configurations are set"""
        configs = position_monitor.alert_configs
        
        assert AlertType.PROFIT_TARGET in configs
        assert AlertType.LOSS_THRESHOLD in configs
        assert AlertType.AGE_WARNING in configs
        assert AlertType.MARGIN_WARNING in configs
        assert AlertType.RISK_LEVEL in configs
        
        # Check default values
        assert configs[AlertType.PROFIT_TARGET].threshold == Decimal('100')
        assert configs[AlertType.LOSS_THRESHOLD].threshold == Decimal('-50')
        assert configs[AlertType.AGE_WARNING].threshold == Decimal('24')


class TestPerformanceMetrics:
    """Test suite for performance metrics tracking"""
    
    @pytest.mark.asyncio
    async def test_update_performance_metrics_new_position(
        self,
        position_monitor,
        sample_profitable_position
    ):
        """Test updating performance metrics for new position"""
        await position_monitor._update_performance_metrics(sample_profitable_position)
        
        # Verify metrics were created
        history = position_monitor._performance_history[sample_profitable_position.position_id]
        assert len(history) == 1
        
        metrics = history[0]
        assert metrics.position_id == sample_profitable_position.position_id
        assert metrics.unrealized_pl == sample_profitable_position.unrealized_pl
        assert metrics.duration_hours == sample_profitable_position.age_hours
        assert metrics.max_favorable_excursion == sample_profitable_position.unrealized_pl
        assert metrics.max_adverse_excursion == sample_profitable_position.unrealized_pl
        
    @pytest.mark.asyncio
    async def test_update_performance_metrics_existing_position(
        self,
        position_monitor,
        sample_profitable_position
    ):
        """Test updating performance metrics for existing position"""
        # Create initial history
        initial_metrics = PerformanceMetrics(
            position_id=sample_profitable_position.position_id,
            unrealized_pl=Decimal('50.00'),
            unrealized_pl_percentage=Decimal('2.0'),
            duration_hours=3.0,
            max_favorable_excursion=Decimal('60.00'),
            max_adverse_excursion=Decimal('-10.00'),
            efficiency_ratio=Decimal('6.0')
        )
        position_monitor._performance_history[sample_profitable_position.position_id] = [initial_metrics]
        
        # Update with current position data
        await position_monitor._update_performance_metrics(sample_profitable_position)
        
        # Verify updated metrics
        history = position_monitor._performance_history[sample_profitable_position.position_id]
        assert len(history) == 2
        
        latest_metrics = history[-1]
        assert latest_metrics.unrealized_pl == Decimal('75.00')
        assert latest_metrics.max_favorable_excursion == Decimal('75.00')  # Updated
        assert latest_metrics.max_adverse_excursion == Decimal('-10.00')  # Preserved
        
    @pytest.mark.asyncio
    async def test_get_position_performance(
        self,
        position_monitor,
        sample_profitable_position
    ):
        """Test getting position performance metrics"""
        # Update performance first
        await position_monitor._update_performance_metrics(sample_profitable_position)
        
        # Get performance
        performance = await position_monitor.get_position_performance(sample_profitable_position.position_id)
        
        assert performance is not None
        assert performance.position_id == sample_profitable_position.position_id
        assert performance.unrealized_pl == sample_profitable_position.unrealized_pl
        
    @pytest.mark.asyncio
    async def test_get_position_performance_not_found(self, position_monitor):
        """Test getting performance for non-existent position"""
        performance = await position_monitor.get_position_performance("nonexistent_position")
        
        assert performance is None


class TestAlertChecking:
    """Test suite for alert checking logic"""
    
    @pytest.mark.asyncio
    async def test_check_profit_target_alert(
        self,
        position_monitor,
        mock_alert_callback,
        sample_profitable_position
    ):
        """Test profit target alert triggering"""
        # Configure alert with lower threshold
        await position_monitor.configure_alert(
            AlertType.PROFIT_TARGET,
            Decimal('50'),  # Below current profit of 75
            enabled=True
        )
        
        # Check alerts
        await position_monitor._check_position_alerts(sample_profitable_position)
        
        # Verify alert was triggered
        mock_alert_callback.assert_called_once()
        alert = mock_alert_callback.call_args[0][0]
        assert isinstance(alert, PositionAlert)
        assert alert.alert_type == AlertType.PROFIT_TARGET
        assert alert.position_id == sample_profitable_position.position_id
        assert alert.current_value == Decimal('75.00')
        
    @pytest.mark.asyncio
    async def test_check_loss_threshold_alert(
        self,
        position_monitor,
        mock_alert_callback,
        sample_losing_position
    ):
        """Test loss threshold alert triggering"""
        # Configure alert with higher threshold
        await position_monitor.configure_alert(
            AlertType.LOSS_THRESHOLD,
            Decimal('-20'),  # Above current loss of -25
            enabled=True
        )
        
        # Check alerts
        await position_monitor._check_position_alerts(sample_losing_position)
        
        # Verify alert was triggered
        mock_alert_callback.assert_called_once()
        alert = mock_alert_callback.call_args[0][0]
        assert alert.alert_type == AlertType.LOSS_THRESHOLD
        assert alert.current_value == Decimal('-25.00')
        
    @pytest.mark.asyncio
    async def test_check_age_warning_alert(
        self,
        position_monitor,
        mock_alert_callback,
        sample_old_position
    ):
        """Test age warning alert triggering"""
        # Configure alert with lower threshold
        await position_monitor.configure_alert(
            AlertType.AGE_WARNING,
            Decimal('25'),  # Below current age of 30 hours
            enabled=True
        )
        
        # Check alerts
        await position_monitor._check_position_alerts(sample_old_position)
        
        # Verify alert was triggered
        mock_alert_callback.assert_called_once()
        alert = mock_alert_callback.call_args[0][0]
        assert alert.alert_type == AlertType.AGE_WARNING
        assert alert.current_value == Decimal('30.0')
        
    @pytest.mark.asyncio
    async def test_alert_cooldown_prevention(
        self,
        position_monitor,
        mock_alert_callback,
        sample_profitable_position
    ):
        """Test that alert cooldown prevents duplicate alerts"""
        # Configure alert with short cooldown
        await position_monitor.configure_alert(
            AlertType.PROFIT_TARGET,
            Decimal('50'),
            enabled=True,
            cooldown_minutes=5
        )
        
        # Trigger alert first time
        await position_monitor._check_position_alerts(sample_profitable_position)
        assert mock_alert_callback.call_count == 1
        
        # Trigger alert again immediately
        await position_monitor._check_position_alerts(sample_profitable_position)
        assert mock_alert_callback.call_count == 1  # Should not increase
        
    @pytest.mark.asyncio
    async def test_disabled_alert_not_triggered(
        self,
        position_monitor,
        mock_alert_callback,
        sample_profitable_position
    ):
        """Test that disabled alerts are not triggered"""
        # Configure disabled alert
        await position_monitor.configure_alert(
            AlertType.PROFIT_TARGET,
            Decimal('50'),
            enabled=False
        )
        
        # Check alerts
        await position_monitor._check_position_alerts(sample_profitable_position)
        
        # Verify no alert was triggered
        mock_alert_callback.assert_not_called()


class TestRiskAssessment:
    """Test suite for risk assessment functionality"""
    
    @pytest.mark.asyncio
    async def test_assess_position_risk(
        self,
        position_monitor,
        sample_profitable_position
    ):
        """Test position risk assessment"""
        risk_metrics = await position_monitor._assess_position_risk(sample_profitable_position)
        
        assert isinstance(risk_metrics, RiskMetrics)
        assert risk_metrics.position_id == sample_profitable_position.position_id
        assert 0 <= risk_metrics.risk_score <= 100
        assert risk_metrics.overall_assessment in [
            "HIGH RISK", "MODERATE RISK", "LOW RISK", "MINIMAL RISK"
        ]
        
    @pytest.mark.asyncio
    async def test_get_position_risk_assessment(
        self,
        position_monitor,
        mock_position_manager,
        sample_profitable_position
    ):
        """Test getting risk assessment for a position"""
        # Setup position in cache
        mock_position_manager.position_cache = {
            sample_profitable_position.position_id: sample_profitable_position
        }
        
        risk_metrics = await position_monitor.get_position_risk_assessment(
            sample_profitable_position.position_id
        )
        
        assert risk_metrics is not None
        assert risk_metrics.position_id == sample_profitable_position.position_id
        
    @pytest.mark.asyncio
    async def test_get_position_risk_assessment_not_found(self, position_monitor, mock_position_manager):
        """Test getting risk assessment for non-existent position"""
        mock_position_manager.position_cache = {}
        
        risk_metrics = await position_monitor.get_position_risk_assessment("nonexistent_position")
        
        assert risk_metrics is None
        
    def test_calculate_margin_utilization(self, position_monitor, sample_profitable_position):
        """Test margin utilization calculation"""
        margin_util = position_monitor._calculate_margin_utilization(sample_profitable_position)
        
        assert isinstance(margin_util, Decimal)
        assert 0 <= margin_util <= 100
        
    @pytest.mark.asyncio
    async def test_calculate_correlation_risk(
        self,
        position_monitor,
        mock_position_manager,
        sample_profitable_position
    ):
        """Test correlation risk calculation"""
        # Setup multiple correlated positions
        correlated_position = PositionInfo(
            position_id="EUR_GBP_long",
            instrument="EUR_GBP",  # Shares EUR with EUR_USD
            side=PositionSide.LONG,
            units=Decimal('5000'),
            entry_price=Decimal('0.8500'),
            current_price=Decimal('0.8525'),
            unrealized_pl=Decimal('12.50'),
            swap_charges=Decimal('0'),
            commission=Decimal('0'),
            margin_used=Decimal('200'),
            opened_at=datetime.now(timezone.utc),
            age_hours=1.0
        )
        
        mock_position_manager.get_open_positions.return_value = [
            sample_profitable_position,
            correlated_position
        ]
        
        correlation_risk = await position_monitor._calculate_correlation_risk(sample_profitable_position)
        
        assert isinstance(correlation_risk, Decimal)
        assert correlation_risk > 0  # Should detect correlation
        
    def test_instruments_correlated(self, position_monitor):
        """Test instrument correlation detection"""
        # Test correlated pairs (share common currency)
        assert position_monitor._instruments_correlated("EUR_USD", "EUR_GBP") is True
        assert position_monitor._instruments_correlated("GBP_USD", "EUR_GBP") is True
        assert position_monitor._instruments_correlated("USD_JPY", "EUR_USD") is True
        
        # Test uncorrelated pairs
        assert position_monitor._instruments_correlated("EUR_USD", "AUD_CAD") is False
        
    def test_calculate_time_risk(self, position_monitor):
        """Test time-based risk calculation"""
        # Test different age scenarios
        young_position = PositionInfo(
            position_id="test",
            instrument="EUR_USD",
            side=PositionSide.LONG,
            units=Decimal('10000'),
            entry_price=Decimal('1.0500'),
            current_price=Decimal('1.0525'),
            unrealized_pl=Decimal('25.00'),
            swap_charges=Decimal('0'),
            commission=Decimal('0'),
            margin_used=Decimal('350'),
            opened_at=datetime.now(timezone.utc),
            age_hours=0.5  # 30 minutes
        )
        
        old_position = PositionInfo(
            position_id="test",
            instrument="EUR_USD",
            side=PositionSide.LONG,
            units=Decimal('10000'),
            entry_price=Decimal('1.0500'),
            current_price=Decimal('1.0525'),
            unrealized_pl=Decimal('25.00'),
            swap_charges=Decimal('0'),
            commission=Decimal('0'),
            margin_used=Decimal('350'),
            opened_at=datetime.now(timezone.utc) - timedelta(days=2),
            age_hours=48.0  # 2 days
        )
        
        young_risk = position_monitor._calculate_time_risk(young_position)
        old_risk = position_monitor._calculate_time_risk(old_position)
        
        assert young_risk < old_risk  # Older positions should have higher time risk


class TestOptimizationSuggestions:
    """Test suite for optimization suggestions"""
    
    @pytest.mark.asyncio
    async def test_generate_optimization_suggestions_profitable(
        self,
        position_monitor,
        mock_position_manager,
        sample_profitable_position
    ):
        """Test optimization suggestions for profitable position"""
        # Setup position in cache
        mock_position_manager.position_cache = {
            sample_profitable_position.position_id: sample_profitable_position
        }
        
        # Add performance history
        performance = PerformanceMetrics(
            position_id=sample_profitable_position.position_id,
            unrealized_pl=sample_profitable_position.unrealized_pl,
            unrealized_pl_percentage=Decimal('7.14'),
            duration_hours=5.0,
            max_favorable_excursion=Decimal('80.00'),
            max_adverse_excursion=Decimal('-5.00'),
            efficiency_ratio=Decimal('16.0')  # Strong momentum
        )
        position_monitor._performance_history[sample_profitable_position.position_id] = [performance]
        
        suggestions = await position_monitor.generate_optimization_suggestions(
            sample_profitable_position.position_id
        )
        
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        
        # Should suggest take profit or trailing stop for profitable position
        suggestion_text = " ".join(suggestions).lower()
        assert any(term in suggestion_text for term in ["take profit", "trailing stop", "lock in gains"])
        
    @pytest.mark.asyncio
    async def test_generate_optimization_suggestions_losing(
        self,
        position_monitor,
        mock_position_manager,
        sample_losing_position
    ):
        """Test optimization suggestions for losing position"""
        # Setup position in cache
        mock_position_manager.position_cache = {
            sample_losing_position.position_id: sample_losing_position
        }
        
        suggestions = await position_monitor.generate_optimization_suggestions(
            sample_losing_position.position_id
        )
        
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        
        # Should suggest stop loss for losing position
        suggestion_text = " ".join(suggestions).lower()
        assert "stop loss" in suggestion_text
        
    @pytest.mark.asyncio
    async def test_generate_optimization_suggestions_old_position(
        self,
        position_monitor,
        mock_position_manager,
        sample_old_position
    ):
        """Test optimization suggestions for old position"""
        # Setup position in cache
        mock_position_manager.position_cache = {
            sample_old_position.position_id: sample_old_position
        }
        
        suggestions = await position_monitor.generate_optimization_suggestions(
            sample_old_position.position_id
        )
        
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        
        # Should suggest review for old position
        suggestion_text = " ".join(suggestions).lower()
        assert any(term in suggestion_text for term in ["review", "long-held", "fundamental"])
        
    @pytest.mark.asyncio
    async def test_generate_optimization_suggestions_position_not_found(
        self,
        position_monitor,
        mock_position_manager
    ):
        """Test optimization suggestions for non-existent position"""
        mock_position_manager.position_cache = {}
        
        suggestions = await position_monitor.generate_optimization_suggestions("nonexistent_position")
        
        assert suggestions == ["Position not found"]


class TestMonitoringLoop:
    """Test suite for monitoring loop functionality"""
    
    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self, position_monitor):
        """Test starting and stopping monitoring"""
        # Initially not monitoring
        assert position_monitor.is_monitoring is False
        
        # Start monitoring
        await position_monitor.start_monitoring()
        assert position_monitor.is_monitoring is True
        assert position_monitor._monitor_task is not None
        
        # Stop monitoring
        await position_monitor.stop_monitoring()
        assert position_monitor.is_monitoring is False
        assert position_monitor._monitor_task is None
        
    @pytest.mark.asyncio
    async def test_monitoring_loop_processes_positions(
        self,
        position_monitor,
        mock_position_manager,
        sample_profitable_position
    ):
        """Test that monitoring loop processes positions"""
        # Setup position
        mock_position_manager.get_open_positions.return_value = [sample_profitable_position]
        
        # Configure alert that should trigger
        await position_monitor.configure_alert(
            AlertType.PROFIT_TARGET,
            Decimal('50'),  # Below current profit
            enabled=True
        )
        
        # Start monitoring briefly
        await position_monitor.start_monitoring()
        
        # Give monitoring loop time to run
        await asyncio.sleep(0.1)
        
        # Stop monitoring
        await position_monitor.stop_monitoring()
        
        # Verify position was processed
        mock_position_manager.get_open_positions.assert_called()
        
        # Verify performance history was updated
        assert sample_profitable_position.position_id in position_monitor._performance_history


class TestEdgeCases:
    """Test suite for edge cases and error conditions"""
    
    @pytest.mark.asyncio
    async def test_alert_callback_exception(
        self,
        position_monitor,
        sample_profitable_position
    ):
        """Test handling of alert callback exceptions"""
        # Setup callback that raises exception
        async def failing_callback(alert):
            raise Exception("Callback failed")
            
        position_monitor.alert_callback = failing_callback
        
        # Configure alert
        await position_monitor.configure_alert(
            AlertType.PROFIT_TARGET,
            Decimal('50'),
            enabled=True
        )
        
        # Should not raise exception even if callback fails
        await position_monitor._check_position_alerts(sample_profitable_position)
        
    @pytest.mark.asyncio
    async def test_performance_history_size_limit(
        self,
        position_monitor,
        sample_profitable_position
    ):
        """Test that performance history is limited in size"""
        # Add many entries to history
        for i in range(150):  # More than the 100 limit
            metrics = PerformanceMetrics(
                position_id=sample_profitable_position.position_id,
                unrealized_pl=Decimal(str(i)),
                unrealized_pl_percentage=Decimal('1.0'),
                duration_hours=float(i),
                max_favorable_excursion=Decimal(str(i)),
                max_adverse_excursion=Decimal('0'),
                efficiency_ratio=Decimal('1.0')
            )
            
            if sample_profitable_position.position_id not in position_monitor._performance_history:
                position_monitor._performance_history[sample_profitable_position.position_id] = []
            position_monitor._performance_history[sample_profitable_position.position_id].append(metrics)
            
        # Update performance one more time
        await position_monitor._update_performance_metrics(sample_profitable_position)
        
        # Verify history size is limited
        history = position_monitor._performance_history[sample_profitable_position.position_id]
        assert len(history) <= 100


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])