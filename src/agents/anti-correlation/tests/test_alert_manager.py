"""Tests for alert management system."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from uuid import uuid4

from ..app.alert_manager import AlertManager
from ..app.models import CorrelationAlert, CorrelationSeverity


class TestAlertManager:
    """Test cases for AlertManager."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return Mock()
    
    @pytest.fixture
    def alert_manager(self, mock_db_session):
        """Create AlertManager instance."""
        return AlertManager(mock_db_session)
    
    @pytest.fixture
    def sample_account_ids(self):
        """Sample account IDs for testing."""
        return [uuid4(), uuid4()]
    
    @pytest.mark.asyncio
    async def test_check_correlation_threshold_normal(self, alert_manager, sample_account_ids):
        """Test correlation threshold check with normal levels."""
        account1_id, account2_id = sample_account_ids
        correlation = 0.5  # Below warning threshold
        
        with patch.object(alert_manager, 'trigger_alert') as mock_trigger:
            await alert_manager.check_correlation_threshold(
                account1_id, account2_id, correlation, 0.02
            )
            
            # No alert should be triggered
            mock_trigger.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_check_correlation_threshold_warning(self, alert_manager, sample_account_ids):
        """Test correlation threshold check with warning level."""
        account1_id, account2_id = sample_account_ids
        correlation = 0.75  # Above warning threshold
        
        with patch.object(alert_manager, 'trigger_alert') as mock_trigger:
            await alert_manager.check_correlation_threshold(
                account1_id, account2_id, correlation, 0.02
            )
            
            # Warning alert should be triggered
            mock_trigger.assert_called_once()
            args = mock_trigger.call_args[1]
            assert args['severity'] == CorrelationSeverity.WARNING
    
    @pytest.mark.asyncio
    async def test_check_correlation_threshold_critical(self, alert_manager, sample_account_ids):
        """Test correlation threshold check with critical level."""
        account1_id, account2_id = sample_account_ids
        correlation = 0.92  # Above critical threshold
        
        with patch.object(alert_manager, 'trigger_alert') as mock_trigger:
            await alert_manager.check_correlation_threshold(
                account1_id, account2_id, correlation, 0.01
            )
            
            # Critical alert should be triggered
            mock_trigger.assert_called_once()
            args = mock_trigger.call_args[1]
            assert args['severity'] == CorrelationSeverity.CRITICAL
    
    @pytest.mark.asyncio
    async def test_trigger_alert(self, alert_manager, mock_db_session, sample_account_ids):
        """Test alert triggering."""
        account1_id, account2_id = sample_account_ids
        
        with patch.object(alert_manager, '_send_notifications') as mock_notify:
            alert = await alert_manager.trigger_alert(
                account1_id=account1_id,
                account2_id=account2_id,
                correlation_coefficient=0.85,
                p_value=0.01,
                severity=CorrelationSeverity.WARNING,
                message="High correlation detected"
            )
            
            assert alert is not None
            assert alert.severity == CorrelationSeverity.WARNING
            assert alert.correlation_coefficient == 0.85
            
            # Verify database operations
            mock_db_session.add.assert_called_once()
            mock_db_session.commit.assert_called_once()
            
            # Verify notification sent
            mock_notify.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_resolve_alert(self, alert_manager, mock_db_session):
        """Test alert resolution."""
        alert_id = uuid4()
        
        # Mock existing alert
        mock_alert = Mock()
        mock_alert.resolved = False
        mock_alert.resolved_time = None
        
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_alert
        mock_db_session.query.return_value = mock_query
        
        result = await alert_manager.resolve_alert(
            alert_id, "Manual intervention", 0.4
        )
        
        assert result is True
        assert mock_alert.resolved is True
        assert mock_alert.resolution_action == "Manual intervention"
        assert mock_alert.correlation_after == 0.4
        assert mock_alert.resolved_time is not None
        
        mock_db_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_resolve_nonexistent_alert(self, alert_manager, mock_db_session):
        """Test resolving non-existent alert."""
        alert_id = uuid4()
        
        # Mock no alert found
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db_session.query.return_value = mock_query
        
        result = await alert_manager.resolve_alert(
            alert_id, "Manual intervention", 0.4
        )
        
        assert result is False
        mock_db_session.commit.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_active_alerts(self, alert_manager, mock_db_session):
        """Test getting active alerts."""
        # Mock active alerts
        mock_alerts = [
            Mock(
                alert_id=uuid4(),
                account_1_id=uuid4(),
                account_2_id=uuid4(),
                correlation_coefficient=0.8,
                severity=CorrelationSeverity.WARNING,
                alert_time=datetime.utcnow(),
                resolved=False,
                message="Test alert"
            )
        ]
        
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = mock_alerts
        mock_db_session.query.return_value = mock_query
        
        alerts = await alert_manager.get_active_alerts()
        
        assert len(alerts) == 1
        assert alerts[0].severity == "warning"
        assert alerts[0].correlation_coefficient == 0.8
    
    @pytest.mark.asyncio
    async def test_get_active_alerts_with_filters(self, alert_manager, mock_db_session):
        """Test getting active alerts with filters."""
        account_id = uuid4()
        severity = CorrelationSeverity.CRITICAL
        
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = []
        mock_db_session.query.return_value = mock_query
        
        alerts = await alert_manager.get_active_alerts(severity, account_id)
        
        # Verify filter was applied
        assert mock_query.filter.called
        assert len(alerts) == 0
    
    @pytest.mark.asyncio
    async def test_get_alert_history(self, alert_manager, mock_db_session):
        """Test getting alert history."""
        # Mock historical alerts
        mock_alerts = [
            Mock(
                alert_id=uuid4(),
                account_1_id=uuid4(),
                account_2_id=uuid4(),
                correlation_coefficient=0.75,
                severity=CorrelationSeverity.WARNING,
                alert_time=datetime.utcnow() - timedelta(hours=1),
                resolved=True,
                resolved_time=datetime.utcnow(),
                resolution_action="Automatic adjustment"
            )
        ]
        
        mock_query = Mock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = mock_alerts
        mock_db_session.query.return_value = mock_query
        
        history = await alert_manager.get_alert_history(24, True)
        
        assert len(history) == 1
        assert history[0].resolved is True
        assert history[0].resolution_action == "Automatic adjustment"
    
    @pytest.mark.asyncio
    async def test_get_alert_statistics(self, alert_manager, mock_db_session):
        """Test getting alert statistics."""
        # Mock statistics data
        mock_total = Mock()
        mock_total.scalar.return_value = 10
        
        mock_resolved = Mock()
        mock_resolved.scalar.return_value = 8
        
        mock_db_session.query.return_value.filter.return_value.scalar.side_effect = [10, 8, 2, 1]
        
        stats = await alert_manager.get_alert_statistics(30)
        
        assert stats['total_alerts'] == 10
        assert stats['resolved_alerts'] == 8
        assert stats['critical_alerts'] == 2
        assert stats['warning_alerts'] == 1
        assert stats['resolution_rate'] == 0.8
    
    @pytest.mark.asyncio
    async def test_generate_correlation_heatmap_data(self, alert_manager, mock_db_session):
        """Test correlation heatmap data generation."""
        account_ids = [uuid4(), uuid4(), uuid4()]
        
        # Mock correlation data
        mock_metrics = [
            Mock(
                account_1_id=account_ids[0],
                account_2_id=account_ids[1],
                correlation_coefficient=0.6,
                calculation_time=datetime.utcnow()
            ),
            Mock(
                account_1_id=account_ids[0],
                account_2_id=account_ids[2],
                correlation_coefficient=0.8,
                calculation_time=datetime.utcnow()
            ),
            Mock(
                account_1_id=account_ids[1],
                account_2_id=account_ids[2],
                correlation_coefficient=0.4,
                calculation_time=datetime.utcnow()
            )
        ]
        
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = mock_metrics
        mock_db_session.query.return_value = mock_query
        
        heatmap_data = await alert_manager.generate_correlation_heatmap_data(
            account_ids, 3600
        )
        
        assert 'matrix' in heatmap_data
        assert 'accounts' in heatmap_data
        assert len(heatmap_data['accounts']) == 3
        assert len(heatmap_data['matrix']) == 3
        assert len(heatmap_data['matrix'][0]) == 3
    
    @pytest.mark.asyncio
    async def test_auto_escalation_monitor(self, alert_manager, mock_db_session):
        """Test automatic alert escalation monitoring."""
        # Mock unescalated alerts
        old_alert = Mock()
        old_alert.alert_id = uuid4()
        old_alert.account_1_id = uuid4()
        old_alert.account_2_id = uuid4()
        old_alert.severity = CorrelationSeverity.INFO
        old_alert.alert_time = datetime.utcnow() - timedelta(minutes=35)
        old_alert.escalated = False
        
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = [old_alert]
        mock_db_session.query.return_value = mock_query
        
        with patch.object(alert_manager, '_escalate_alert') as mock_escalate:
            with patch('asyncio.sleep', new_callable=AsyncMock):
                # Run one iteration
                alert_manager.monitoring = True
                
                # This would normally run indefinitely, but we'll stop it
                await alert_manager._check_escalation_needed()
                alert_manager.monitoring = False
                
                # Verify escalation was called
                mock_escalate.assert_called_once_with(old_alert)
    
    @pytest.mark.asyncio
    async def test_escalate_alert(self, alert_manager, mock_db_session):
        """Test alert escalation."""
        alert = Mock()
        alert.alert_id = uuid4()
        alert.account_1_id = uuid4()
        alert.account_2_id = uuid4()
        alert.severity = CorrelationSeverity.INFO
        alert.correlation_coefficient = 0.6
        alert.escalated = False
        
        with patch.object(alert_manager, 'trigger_alert') as mock_trigger:
            await alert_manager._escalate_alert(alert)
            
            # Verify original alert marked as escalated
            assert alert.escalated is True
            
            # Verify new escalated alert triggered
            mock_trigger.assert_called_once()
            args = mock_trigger.call_args[1]
            assert args['severity'] == CorrelationSeverity.WARNING  # Escalated
    
    @pytest.mark.asyncio
    async def test_send_notifications(self, alert_manager):
        """Test notification sending."""
        alert = Mock()
        alert.alert_id = uuid4()
        alert.account_1_id = uuid4()
        alert.account_2_id = uuid4()
        alert.severity = CorrelationSeverity.CRITICAL
        alert.correlation_coefficient = 0.95
        alert.message = "Critical correlation detected"
        
        with patch.object(alert_manager, '_send_dashboard_notification') as mock_dashboard:
            with patch.object(alert_manager, '_send_webhook_notification') as mock_webhook:
                await alert_manager._send_notifications(alert)
                
                # Verify both notification methods called
                mock_dashboard.assert_called_once_with(alert)
                mock_webhook.assert_called_once_with(alert)
    
    @pytest.mark.asyncio
    async def test_duplicate_alert_suppression(self, alert_manager, mock_db_session):
        """Test duplicate alert suppression."""
        account1_id, account2_id = uuid4(), uuid4()
        
        # Mock existing recent alert
        existing_alert = Mock()
        existing_alert.alert_time = datetime.utcnow() - timedelta(minutes=5)
        
        mock_query = Mock()
        mock_query.filter.return_value.order_by.return_value.first.return_value = existing_alert
        mock_db_session.query.return_value = mock_query
        
        with patch.object(alert_manager, '_send_notifications') as mock_notify:
            alert = await alert_manager.trigger_alert(
                account1_id=account1_id,
                account2_id=account2_id,
                correlation_coefficient=0.75,
                p_value=0.02,
                severity=CorrelationSeverity.WARNING,
                message="Duplicate alert test"
            )
            
            # Should not create new alert due to suppression
            assert alert is None
            mock_notify.assert_not_called()
    
    def test_severity_level_determination(self, alert_manager):
        """Test automatic severity level determination."""
        assert alert_manager._determine_severity_level(0.95, 0.001) == CorrelationSeverity.CRITICAL
        assert alert_manager._determine_severity_level(0.75, 0.02) == CorrelationSeverity.WARNING
        assert alert_manager._determine_severity_level(0.55, 0.05) == CorrelationSeverity.INFO
        assert alert_manager._determine_severity_level(0.3, 0.1) == CorrelationSeverity.INFO
    
    @pytest.mark.asyncio
    async def test_notification_channel_selection(self, alert_manager):
        """Test notification channel selection based on severity."""
        critical_alert = Mock()
        critical_alert.severity = CorrelationSeverity.CRITICAL
        
        warning_alert = Mock()
        warning_alert.severity = CorrelationSeverity.WARNING
        
        info_alert = Mock()
        info_alert.severity = CorrelationSeverity.INFO
        
        # Critical should use all channels
        channels = alert_manager._select_notification_channels(critical_alert)
        assert 'dashboard' in channels
        assert 'webhook' in channels
        assert 'email' in channels
        
        # Warning should use dashboard and webhook
        channels = alert_manager._select_notification_channels(warning_alert)
        assert 'dashboard' in channels
        assert 'webhook' in channels
        
        # Info should use only dashboard
        channels = alert_manager._select_notification_channels(info_alert)
        assert 'dashboard' in channels