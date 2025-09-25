"""
Tests for Performance Alert Scheduler

Tests the daily/weekly/monthly performance alert scheduling system
including all scheduled alert types and configuration management.
"""

import pytest
import asyncio
from datetime import datetime, time, timedelta
from unittest.mock import Mock, AsyncMock, patch
import json
import tempfile
from pathlib import Path

# Import the components to test
from app.performance_alert_scheduler import (
    PerformanceAlertScheduler,
    ScheduledAlert,
    ScheduleFrequency,
    get_alert_scheduler
)
from app.performance_tracking import AlertSeverity


class TestPerformanceAlertScheduler:
    """Test suite for PerformanceAlertScheduler"""

    @pytest.fixture
    def scheduler(self):
        """Create a scheduler instance for testing"""
        scheduler = PerformanceAlertScheduler()
        # Override alerts directory to use temp directory for tests
        scheduler.alerts_history_path = Path(tempfile.mkdtemp()) / "test_alerts"
        scheduler.alerts_history_path.mkdir(parents=True, exist_ok=True)
        return scheduler

    @pytest.fixture
    def mock_performance_tracker(self):
        """Mock performance tracker"""
        tracker = Mock()
        tracker.get_current_metrics = AsyncMock(return_value={
            "actual_pnl": 12450.0,
            "projected_pnl": 12000.0,
            "pnl_deviation_pct": 3.75,
            "rolling_sharpe_ratio": 1.67,
            "drawdown_current": 0.02,
            "drawdown_max": 0.05,
            "timestamp": datetime.utcnow()
        })
        tracker.calculate_stability_score = AsyncMock(return_value={
            "walk_forward_stability": 45.2,
            "out_of_sample_validation": 65.8,
            "overfitting_score": 0.412
        })
        return tracker

    @pytest.fixture
    def mock_monte_carlo(self):
        """Mock Monte Carlo engine"""
        engine = Mock()
        engine.get_daily_projections = AsyncMock(return_value={
            "confidence_intervals": {
                "95%": (400.0, 500.0),
                "99%": (350.0, 550.0)
            }
        })
        engine.run_monthly_forward_test_update = AsyncMock(return_value={
            "expected_monthly_pnl": 13250.0,
            "walk_forward_stability": 42.1,
            "out_of_sample_validation": 62.3
        })
        engine.get_previous_month_projections = AsyncMock(return_value={
            "expected_monthly_pnl": 12800.0,
            "walk_forward_stability": 45.2,
            "out_of_sample_validation": 65.8
        })
        return engine

    @pytest.mark.asyncio
    async def test_scheduler_initialization(self, scheduler):
        """Test scheduler initializes correctly"""
        assert scheduler.running is False
        assert len(scheduler.scheduled_alerts) == 5  # Default alerts
        assert scheduler.alerts_history_path.exists()

        # Check default alerts are configured correctly
        alert_names = [alert.name for alert in scheduler.scheduled_alerts]
        expected_alerts = [
            "daily_pnl_check",
            "weekly_stability_check",
            "monthly_forward_test_update",
            "performance_threshold_check",
            "evening_performance_check"
        ]

        for expected in expected_alerts:
            assert expected in alert_names

    @pytest.mark.asyncio
    async def test_daily_pnl_vs_projection_check(self, scheduler, mock_performance_tracker, mock_monte_carlo):
        """Test daily P&L vs projection alert generation"""
        # Setup mocks
        with patch.object(scheduler, 'performance_tracker', mock_performance_tracker), \
             patch.object(scheduler, 'monte_carlo', mock_monte_carlo), \
             patch.object(scheduler.alert_system, 'evaluate_performance_alerts') as mock_evaluate, \
             patch.object(scheduler.alert_system, 'save_alerts') as mock_save, \
             patch.object(scheduler, '_save_scheduled_alert_summary') as mock_summary:

            # Configure mock alert system response
            mock_alerts = [
                Mock(severity=AlertSeverity.WARNING, alert_id="test_alert_1"),
                Mock(severity=AlertSeverity.CRITICAL, alert_id="test_alert_2")
            ]
            mock_evaluate.return_value = mock_alerts

            # Execute daily P&L check
            await scheduler._check_daily_pnl_vs_projection()

            # Verify calls
            mock_performance_tracker.get_current_metrics.assert_called_once()
            mock_monte_carlo.get_daily_projections.assert_called_once()
            mock_evaluate.assert_called_once()
            mock_save.assert_called_once_with(mock_alerts)
            mock_summary.assert_called_once_with("daily_pnl_check", mock_alerts)

    @pytest.mark.asyncio
    async def test_weekly_stability_score_monitoring(self, scheduler, mock_performance_tracker):
        """Test weekly stability score monitoring"""
        with patch.object(scheduler, 'performance_tracker', mock_performance_tracker), \
             patch.object(scheduler.alert_system, 'save_alerts') as mock_save, \
             patch.object(scheduler, '_save_scheduled_alert_summary') as mock_summary, \
             patch.object(scheduler, '_create_stability_alert') as mock_create_alert:

            # Configure low stability scores that should trigger alerts
            mock_performance_tracker.calculate_stability_score.return_value = {
                "walk_forward_stability": 35.0,  # Below 60 target
                "out_of_sample_validation": 45.0  # Below 70 target
            }

            mock_alert = Mock()
            mock_create_alert.return_value = mock_alert

            # Execute weekly stability check
            await scheduler._check_weekly_stability_score()

            # Verify stability calculation was called
            mock_performance_tracker.calculate_stability_score.assert_called_once()

            # Should create two alerts (one for each metric below threshold)
            assert mock_create_alert.call_count == 2
            mock_save.assert_called_once()
            mock_summary.assert_called_once()

    @pytest.mark.asyncio
    async def test_monthly_forward_test_update(self, scheduler, mock_monte_carlo):
        """Test monthly forward test update process"""
        with patch.object(scheduler, 'monte_carlo', mock_monte_carlo), \
             patch.object(scheduler.alert_system, 'save_alerts') as mock_save, \
             patch.object(scheduler, '_save_scheduled_alert_summary') as mock_summary, \
             patch.object(scheduler, '_create_forward_test_alert') as mock_create_alert:

            # Configure Monte Carlo to return significantly different projections
            mock_monte_carlo.run_monthly_forward_test_update.return_value = {
                "expected_monthly_pnl": 16000.0,  # 25% increase from 12800
                "walk_forward_stability": 42.1,
                "out_of_sample_validation": 62.3
            }

            mock_alert = Mock()
            mock_create_alert.return_value = mock_alert

            # Execute monthly forward test update
            await scheduler._update_monthly_forward_test()

            # Verify Monte Carlo calls
            mock_monte_carlo.run_monthly_forward_test_update.assert_called_once()
            mock_monte_carlo.get_previous_month_projections.assert_called_once()

            # Should create alert for significant projection change
            mock_create_alert.assert_called()
            mock_save.assert_called_once()
            mock_summary.assert_called_once()

    @pytest.mark.asyncio
    async def test_performance_threshold_check(self, scheduler, mock_performance_tracker):
        """Test performance threshold notifications"""
        with patch.object(scheduler, 'performance_tracker', mock_performance_tracker), \
             patch.object(scheduler.alert_system, 'evaluate_performance_alerts') as mock_evaluate, \
             patch.object(scheduler.alert_system, 'save_alerts') as mock_save, \
             patch.object(scheduler, '_save_scheduled_alert_summary') as mock_summary:

            # Configure critical alerts
            critical_alerts = [
                Mock(severity=AlertSeverity.CRITICAL, alert_id="critical_1"),
                Mock(severity=AlertSeverity.EMERGENCY, alert_id="emergency_1")
            ]
            warning_alerts = [Mock(severity=AlertSeverity.WARNING, alert_id="warning_1")]

            all_alerts = critical_alerts + warning_alerts
            mock_evaluate.return_value = all_alerts

            # Execute threshold check
            await scheduler._check_performance_thresholds()

            # Verify only critical alerts are saved during threshold checks
            mock_save.assert_called_once_with(critical_alerts)
            mock_summary.assert_called_once_with("performance_threshold_check", critical_alerts)

    def test_schedule_status(self, scheduler):
        """Test getting schedule status"""
        status = scheduler.get_schedule_status()

        assert "scheduler_running" in status
        assert "scheduled_alerts" in status
        assert len(status["scheduled_alerts"]) == 5

        # Check alert status structure
        alert_status = status["scheduled_alerts"][0]
        required_fields = ["name", "frequency", "enabled", "last_run", "time_of_day"]

        for field in required_fields:
            assert field in alert_status

    def test_calculate_next_run_time_daily(self, scheduler):
        """Test next run time calculation for daily alerts"""
        # Create a daily alert for 14:00 UTC
        daily_alert = ScheduledAlert(
            name="test_daily",
            frequency=ScheduleFrequency.DAILY,
            time_of_day=time(14, 0)
        )

        next_run = scheduler._calculate_next_run_time(daily_alert)

        assert next_run is not None
        assert next_run.time() == time(14, 0)

        # Should be today if current time is before 14:00, otherwise tomorrow
        now = datetime.utcnow()
        if now.time() < time(14, 0):
            assert next_run.date() == now.date()
        else:
            assert next_run.date() == now.date() + timedelta(days=1)

    def test_calculate_next_run_time_weekly(self, scheduler):
        """Test next run time calculation for weekly alerts"""
        # Create a weekly alert for Monday 08:00 UTC
        weekly_alert = ScheduledAlert(
            name="test_weekly",
            frequency=ScheduleFrequency.WEEKLY,
            time_of_day=time(8, 0)
        )

        next_run = scheduler._calculate_next_run_time(weekly_alert)

        assert next_run is not None
        assert next_run.time() == time(8, 0)
        assert next_run.weekday() == 0  # Monday

    def test_calculate_next_run_time_monthly(self, scheduler):
        """Test next run time calculation for monthly alerts"""
        # Create a monthly alert for 1st at 09:00 UTC
        monthly_alert = ScheduledAlert(
            name="test_monthly",
            frequency=ScheduleFrequency.MONTHLY,
            time_of_day=time(9, 0)
        )

        next_run = scheduler._calculate_next_run_time(monthly_alert)

        assert next_run is not None
        assert next_run.time() == time(9, 0)
        assert next_run.day == 1

    @pytest.mark.asyncio
    async def test_save_scheduled_alert_summary(self, scheduler):
        """Test saving alert summary to file"""
        # Create mock alerts
        alerts = [
            Mock(
                alert_id="test_alert_1",
                severity=AlertSeverity.WARNING,
                message="Test warning"
            ),
            Mock(
                alert_id="test_alert_2",
                severity=AlertSeverity.CRITICAL,
                message="Test critical alert"
            )
        ]

        # Save summary
        await scheduler._save_scheduled_alert_summary("test_check", alerts)

        # Verify file was created
        summary_files = list(scheduler.alerts_history_path.glob("scheduled_summary_test_check_*.json"))
        assert len(summary_files) == 1

        # Verify file contents
        with open(summary_files[0], 'r') as f:
            summary_data = json.load(f)

        assert summary_data["check_name"] == "test_check"
        assert summary_data["alerts_generated"] == 2
        assert summary_data["critical_count"] == 1
        assert summary_data["warning_count"] == 1
        assert len(summary_data["alert_details"]) == 2

    @pytest.mark.asyncio
    async def test_create_stability_alert(self, scheduler):
        """Test creating stability-related alerts"""
        alert = await scheduler._create_stability_alert(
            AlertSeverity.WARNING,
            "Test stability message",
            45.0,
            60.0,
            "walk_forward_stability"
        )

        assert alert.severity == AlertSeverity.WARNING
        assert alert.message == "Test stability message"
        assert alert.current_value == 45.0
        assert alert.expected_value == 60.0
        assert alert.alert_type == "Weekly Stability Monitoring"
        assert "walk_forward_stability" in alert.details["metric_type"]
        assert alert.details["scheduled_check"] is True

    @pytest.mark.asyncio
    async def test_create_forward_test_alert(self, scheduler):
        """Test creating forward test related alerts"""
        alert = await scheduler._create_forward_test_alert(
            AlertSeverity.CRITICAL,
            "Test forward test message",
            16000.0,
            12800.0,
            "expected_pnl_change"
        )

        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.message == "Test forward test message"
        assert alert.current_value == 16000.0
        assert alert.expected_value == 12800.0
        assert alert.alert_type == "Monthly Forward Test Update"
        assert alert.details["alert_type"] == "expected_pnl_change"
        assert alert.details["scheduled_check"] is True

    @pytest.mark.asyncio
    async def test_scheduler_start_stop(self, scheduler):
        """Test scheduler start and stop operations"""
        with patch('orchestrator.app.performance_tracking.get_performance_tracker') as mock_get_tracker:
            mock_get_tracker.return_value = Mock()

            # Test start
            await scheduler.start()
            assert scheduler.running is True
            assert scheduler.scheduler_thread is not None
            assert scheduler.performance_tracker is not None

            # Test stop
            await scheduler.stop()
            assert scheduler.running is False

    def test_global_scheduler_instance(self):
        """Test global scheduler instance creation"""
        # Clear any existing global instance
        import app.performance_alert_scheduler
        app.performance_alert_scheduler._alert_scheduler = None

        # Get instance
        scheduler1 = get_alert_scheduler()
        scheduler2 = get_alert_scheduler()

        # Should be same instance (singleton pattern)
        assert scheduler1 is scheduler2
        assert isinstance(scheduler1, PerformanceAlertScheduler)


class TestScheduledAlertConfiguration:
    """Test suite for ScheduledAlert configuration"""

    def test_scheduled_alert_creation(self):
        """Test creating scheduled alert configurations"""
        alert = ScheduledAlert(
            name="test_alert",
            frequency=ScheduleFrequency.DAILY,
            time_of_day=time(12, 0),
            enabled=True,
            alert_function="test_function"
        )

        assert alert.name == "test_alert"
        assert alert.frequency == ScheduleFrequency.DAILY
        assert alert.time_of_day == time(12, 0)
        assert alert.enabled is True
        assert alert.alert_function == "test_function"
        assert alert.last_run is None
        assert alert.next_run is None

    def test_schedule_frequency_enum(self):
        """Test ScheduleFrequency enum values"""
        assert ScheduleFrequency.DAILY.value == "daily"
        assert ScheduleFrequency.WEEKLY.value == "weekly"
        assert ScheduleFrequency.MONTHLY.value == "monthly"


class TestAlertSchedulerIntegration:
    """Integration tests for alert scheduler"""

    @pytest.mark.asyncio
    async def test_end_to_end_alert_processing(self):
        """Test complete alert processing flow"""
        scheduler = PerformanceAlertScheduler()
        scheduler.alerts_history_path = Path(tempfile.mkdtemp()) / "integration_test"
        scheduler.alerts_history_path.mkdir(parents=True, exist_ok=True)

        # Mock all dependencies
        with patch.object(scheduler, 'performance_tracker') as mock_tracker, \
             patch.object(scheduler, 'monte_carlo') as mock_monte_carlo, \
             patch.object(scheduler.alert_system, 'evaluate_performance_alerts') as mock_evaluate, \
             patch.object(scheduler.alert_system, 'save_alerts') as mock_save:

            # Configure mocks
            mock_tracker.get_current_metrics = AsyncMock(return_value={
                "actual_pnl": 15000.0,
                "projected_pnl": 12000.0,
                "rolling_sharpe_ratio": 1.2,
                "timestamp": datetime.utcnow()
            })

            mock_monte_carlo.get_daily_projections = AsyncMock(return_value={
                "confidence_intervals": {"95%": (400.0, 500.0)}
            })

            mock_alerts = [Mock(severity=AlertSeverity.WARNING, alert_id="integration_test")]
            mock_evaluate.return_value = mock_alerts

            # Execute scheduled alert
            await scheduler._check_daily_pnl_vs_projection()

            # Verify complete flow
            mock_tracker.get_current_metrics.assert_called_once()
            mock_monte_carlo.get_daily_projections.assert_called_once()
            mock_evaluate.assert_called_once()
            mock_save.assert_called_once_with(mock_alerts)

            # Verify summary file was created
            summary_files = list(scheduler.alerts_history_path.glob("scheduled_summary_daily_pnl_check_*.json"))
            assert len(summary_files) == 1

    @pytest.mark.asyncio
    async def test_error_handling(self, scheduler):
        """Test error handling in scheduler operations"""
        # Test with missing performance tracker
        scheduler.performance_tracker = None

        # Should not raise exception, just log warning
        await scheduler._check_daily_pnl_vs_projection()

        # Test with failing Monte Carlo
        with patch.object(scheduler, 'performance_tracker') as mock_tracker, \
             patch.object(scheduler, 'monte_carlo') as mock_monte_carlo:

            mock_tracker.get_current_metrics = AsyncMock(return_value={})
            mock_monte_carlo.get_daily_projections = AsyncMock(side_effect=Exception("Monte Carlo failed"))

            # Should not raise exception
            await scheduler._check_daily_pnl_vs_projection()

if __name__ == "__main__":
    pytest.main([__file__])