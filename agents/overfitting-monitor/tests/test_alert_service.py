"""
Unit tests for AlertService - Story 11.4, Task 3
"""

import pytest
from app.alert_service import AlertService
from app.models import AlertLevel


@pytest.mark.asyncio
class TestAlertService:
    """Test suite for AlertService class"""

    async def test_initialization(self):
        """Test alert service initialization"""
        service = AlertService(
            slack_webhook_url="https://hooks.slack.com/test",
            email_enabled=False
        )

        assert service.slack_webhook_url == "https://hooks.slack.com/test"
        assert not service.email_enabled
        assert len(service.active_alerts) == 0

    async def test_create_alert(self):
        """Test alert creation"""
        service = AlertService()
        await service.initialize()

        alert = await service.create_alert(
            severity=AlertLevel.WARNING,
            metric="overfitting_score",
            value=0.35,
            threshold=0.3,
            message="Test alert message",
            recommendation="Test recommendation"
        )

        assert alert.severity == AlertLevel.WARNING
        assert alert.metric == "overfitting_score"
        assert alert.value == 0.35
        assert alert.threshold == 0.3
        assert not alert.acknowledged
        assert alert.id in service.active_alerts

        await service.close()

    async def test_acknowledge_alert(self):
        """Test alert acknowledgment"""
        service = AlertService()
        await service.initialize()

        # Create alert
        alert = await service.create_alert(
            severity=AlertLevel.WARNING,
            metric="test_metric",
            value=0.5,
            threshold=0.3,
            message="Test"
        )

        # Acknowledge it
        ack_alert = await service.acknowledge_alert(alert.id)

        assert ack_alert is not None
        assert ack_alert.acknowledged
        assert ack_alert.acknowledged_at is not None

        await service.close()

    async def test_acknowledge_nonexistent_alert(self):
        """Test acknowledging non-existent alert"""
        service = AlertService()
        await service.initialize()

        result = await service.acknowledge_alert("nonexistent-id")

        assert result is None

        await service.close()

    async def test_get_active_alerts(self):
        """Test getting active alerts"""
        service = AlertService()
        await service.initialize()

        # Create multiple alerts
        await service.create_alert(
            severity=AlertLevel.WARNING,
            metric="metric1",
            value=0.35,
            threshold=0.3,
            message="Warning alert"
        )

        await service.create_alert(
            severity=AlertLevel.CRITICAL,
            metric="metric2",
            value=0.6,
            threshold=0.5,
            message="Critical alert"
        )

        # Get all active alerts
        alerts = await service.get_active_alerts()
        assert len(alerts) == 2

        # Filter by severity
        critical_alerts = await service.get_active_alerts(severity=AlertLevel.CRITICAL)
        assert len(critical_alerts) == 1
        assert critical_alerts[0].severity == AlertLevel.CRITICAL

        await service.close()

    async def test_get_active_alerts_excludes_acknowledged(self):
        """Test that acknowledged alerts are excluded"""
        service = AlertService()
        await service.initialize()

        # Create and acknowledge alert
        alert = await service.create_alert(
            severity=AlertLevel.WARNING,
            metric="test",
            value=0.35,
            threshold=0.3,
            message="Test"
        )
        await service.acknowledge_alert(alert.id)

        # Should return no active alerts
        active = await service.get_active_alerts()
        assert len(active) == 0

        await service.close()

    async def test_clear_acknowledged_alerts(self):
        """Test clearing acknowledged alerts"""
        service = AlertService()
        await service.initialize()

        # Create and acknowledge alert
        alert = await service.create_alert(
            severity=AlertLevel.WARNING,
            metric="test",
            value=0.35,
            threshold=0.3,
            message="Test"
        )
        await service.acknowledge_alert(alert.id)

        # Create unacknowledged alert
        await service.create_alert(
            severity=AlertLevel.CRITICAL,
            metric="test2",
            value=0.6,
            threshold=0.5,
            message="Test2"
        )

        assert len(service.active_alerts) == 2

        # Clear acknowledged
        await service.clear_acknowledged_alerts()

        assert len(service.active_alerts) == 1  # Only unacknowledged remains

        await service.close()

    async def test_check_overfitting_thresholds_normal(self):
        """Test overfitting threshold check with normal score"""
        service = AlertService()
        await service.initialize()

        alert = await service.check_overfitting_thresholds(
            overfitting_score=0.25,
            warning_threshold=0.3,
            critical_threshold=0.5
        )

        assert alert is None

        await service.close()

    async def test_check_overfitting_thresholds_warning(self):
        """Test overfitting threshold check with warning score"""
        service = AlertService()
        await service.initialize()

        alert = await service.check_overfitting_thresholds(
            overfitting_score=0.35,
            warning_threshold=0.3,
            critical_threshold=0.5
        )

        assert alert is not None
        assert alert.severity == AlertLevel.WARNING
        assert alert.metric == "overfitting_score"
        assert alert.recommendation is not None

        await service.close()

    async def test_check_overfitting_thresholds_critical(self):
        """Test overfitting threshold check with critical score"""
        service = AlertService()
        await service.initialize()

        alert = await service.check_overfitting_thresholds(
            overfitting_score=0.6,
            warning_threshold=0.3,
            critical_threshold=0.5
        )

        assert alert is not None
        assert alert.severity == AlertLevel.CRITICAL
        assert "CRITICAL" in alert.message

        await service.close()

    async def test_check_drift_threshold_normal(self):
        """Test drift threshold check with normal drift"""
        service = AlertService()
        await service.initialize()

        alert = await service.check_drift_threshold(
            parameter_name="confidence_threshold",
            drift_pct=10.0,
            max_drift_pct=15.0
        )

        assert alert is None

        await service.close()

    async def test_check_drift_threshold_exceeds(self):
        """Test drift threshold check with excessive drift"""
        service = AlertService()
        await service.initialize()

        alert = await service.check_drift_threshold(
            parameter_name="confidence_threshold",
            drift_pct=20.0,
            max_drift_pct=15.0
        )

        assert alert is not None
        assert alert.severity == AlertLevel.WARNING
        assert "confidence_threshold" in alert.message
        assert alert.value == 20.0

        await service.close()

    async def test_check_performance_degradation_normal(self):
        """Test performance degradation check with normal performance"""
        service = AlertService()
        await service.initialize()

        alert = await service.check_performance_degradation(
            live_sharpe=1.8,
            backtest_sharpe=2.0,
            threshold_ratio=0.7
        )

        assert alert is None  # 1.8/2.0 = 0.9 > 0.7 threshold

        await service.close()

    async def test_check_performance_degradation_warning(self):
        """Test performance degradation check with degraded performance"""
        service = AlertService()
        await service.initialize()

        alert = await service.check_performance_degradation(
            live_sharpe=1.2,
            backtest_sharpe=2.0,
            threshold_ratio=0.7
        )

        assert alert is not None  # 1.2/2.0 = 0.6 < 0.7 threshold
        assert alert.severity == AlertLevel.WARNING
        assert "degradation" in alert.message.lower()

        await service.close()

    async def test_check_performance_degradation_critical(self):
        """Test performance degradation check with critical degradation"""
        service = AlertService()
        await service.initialize()

        alert = await service.check_performance_degradation(
            live_sharpe=0.8,
            backtest_sharpe=2.0,
            threshold_ratio=0.7
        )

        assert alert is not None  # 0.8/2.0 = 0.4 < 0.5 (critical)
        assert alert.severity == AlertLevel.CRITICAL

        await service.close()

    async def test_multiple_alerts_different_severities(self):
        """Test creating multiple alerts with different severities"""
        service = AlertService()
        await service.initialize()

        # Create alerts of different severities
        await service.create_alert(
            severity=AlertLevel.WARNING,
            metric="metric1",
            value=0.35,
            threshold=0.3,
            message="Warning"
        )

        await service.create_alert(
            severity=AlertLevel.CRITICAL,
            metric="metric2",
            value=0.6,
            threshold=0.5,
            message="Critical"
        )

        await service.create_alert(
            severity=AlertLevel.WARNING,
            metric="metric3",
            value=0.4,
            threshold=0.3,
            message="Warning2"
        )

        # Check counts by severity
        all_alerts = await service.get_active_alerts()
        warnings = await service.get_active_alerts(severity=AlertLevel.WARNING)
        criticals = await service.get_active_alerts(severity=AlertLevel.CRITICAL)

        assert len(all_alerts) == 3
        assert len(warnings) == 2
        assert len(criticals) == 1

        await service.close()
