"""
Comprehensive Tests for Emergency Rollback System
Tests all components: rollback execution, monitoring, validation, and contact procedures
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone, timedelta
import json

# Import the modules we're testing
from orchestrator.app.emergency_rollback import (
    EmergencyRollbackSystem, RollbackTrigger, RollbackStatus,
    RollbackCondition, RollbackEvent
)
from orchestrator.app.rollback_monitor import RollbackMonitorService
from orchestrator.app.recovery_validator import (
    PerformanceRecoveryValidator, ValidationStatus, ValidationType
)
from orchestrator.app.emergency_contacts import (
    EmergencyContactSystem, ContactType, NotificationPriority, NotificationChannel
)


class TestEmergencyRollbackSystem:
    """Test suite for the emergency rollback system"""

    @pytest.fixture
    def mock_orchestrator(self):
        """Mock orchestrator for testing"""
        orchestrator = Mock()
        orchestrator.emergency_stop = AsyncMock()
        orchestrator.restart_agent = AsyncMock()
        orchestrator.get_system_status = AsyncMock()
        orchestrator.list_agents = AsyncMock(return_value=["market-analysis", "strategy-analysis"])
        return orchestrator

    @pytest.fixture
    def rollback_system(self, mock_orchestrator):
        """Create rollback system for testing"""
        return EmergencyRollbackSystem(mock_orchestrator)

    @pytest.mark.asyncio
    async def test_manual_emergency_rollback(self, rollback_system, mock_orchestrator):
        """Test manual emergency rollback execution"""

        # Mock the parameter switching by patching the config import
        with patch('orchestrator.app.emergency_rollback.sys.path'), \
             patch('importlib.import_module') as mock_import:

            # Mock the config module
            mock_config = Mock()
            mock_config.set_parameter_mode.return_value = {"previous_mode": "session_targeted", "new_mode": "universal_cycle_4"}
            mock_import.return_value = mock_config

            # Execute rollback
            rollback_event = await rollback_system.execute_emergency_rollback(
                trigger_type=RollbackTrigger.MANUAL,
                reason="Test rollback execution",
                notify_contacts=False
            )

            # Verify rollback event
            assert rollback_event.trigger_type == RollbackTrigger.MANUAL
            assert rollback_event.trigger_reason == "Test rollback execution"
            assert rollback_event.rollback_status == RollbackStatus.COMPLETED
            assert rollback_event.new_mode == "universal_cycle_4"

            # Verify orchestrator calls
            mock_orchestrator.emergency_stop.assert_called_once()
            mock_orchestrator.restart_agent.assert_called()

    @pytest.mark.asyncio
    async def test_automatic_trigger_detection(self, rollback_system):
        """Test automatic rollback trigger detection"""

        # Test data that should trigger rollback
        performance_data = {
            "walk_forward_stability": 30.0,  # Below threshold of 40.0
            "overfitting_score": 0.7,       # Above threshold of 0.5
            "consecutive_losses": 6,         # Above threshold of 5
            "max_drawdown_percent": 6.0,     # Above threshold of 5.0
        }

        trigger = await rollback_system.check_automatic_triggers(performance_data)

        # Should detect the first (highest priority) trigger
        assert trigger == RollbackTrigger.WALK_FORWARD_FAILURE

    @pytest.mark.asyncio
    async def test_no_trigger_when_conditions_not_met(self, rollback_system):
        """Test that no trigger is detected when conditions are not met"""

        # Test data that should NOT trigger rollback
        performance_data = {
            "walk_forward_stability": 60.0,  # Above threshold
            "overfitting_score": 0.2,       # Below threshold
            "consecutive_losses": 2,         # Below threshold
            "max_drawdown_percent": 2.0,     # Below threshold
        }

        trigger = await rollback_system.check_automatic_triggers(performance_data)

        assert trigger is None

    def test_rollback_status_tracking(self, rollback_system):
        """Test rollback system status tracking"""

        status = rollback_system.get_rollback_status()

        assert status["status"] == RollbackStatus.READY.value
        assert status["ready_for_rollback"] is True
        assert status["rollback_count"] == 0

    def test_rollback_condition_updates(self, rollback_system):
        """Test updating rollback conditions"""

        new_conditions = [
            {
                "trigger_type": "walk_forward_failure",
                "enabled": True,
                "threshold_value": 35.0,  # Changed from 40.0
                "threshold_unit": "stability_score",
                "consecutive_periods": 2,  # Changed from 1
                "description": "Updated walk-forward threshold",
                "priority": 1
            }
        ]

        rollback_system.update_rollback_conditions(new_conditions)

        # Find the updated condition
        updated_condition = None
        for condition in rollback_system.rollback_conditions:
            if condition.trigger_type == RollbackTrigger.WALK_FORWARD_FAILURE:
                updated_condition = condition
                break

        assert updated_condition is not None
        assert updated_condition.threshold_value == 35.0
        assert updated_condition.consecutive_periods == 2


class TestRollbackMonitorService:
    """Test suite for the rollback monitoring service"""

    @pytest.fixture
    def mock_orchestrator(self):
        orchestrator = Mock()
        orchestrator.get_system_metrics = AsyncMock()
        return orchestrator

    @pytest.fixture
    def monitor_service(self, mock_orchestrator):
        return RollbackMonitorService(mock_orchestrator, check_interval=1)  # 1 second for testing

    @pytest.mark.asyncio
    async def test_monitoring_start_stop(self, monitor_service):
        """Test starting and stopping the monitoring service"""

        assert monitor_service.monitoring_active is False

        # Start monitoring (run for short time)
        monitor_task = asyncio.create_task(monitor_service.start_monitoring())
        await asyncio.sleep(0.1)  # Let it start

        assert monitor_service.monitoring_active is True

        # Stop monitoring
        await monitor_service.stop_monitoring()
        await asyncio.sleep(0.1)  # Let it stop

        assert monitor_service.monitoring_active is False

        # Clean up task
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass

    def test_monitoring_status(self, monitor_service):
        """Test monitoring service status reporting"""

        status = monitor_service.get_monitoring_status()

        assert "monitoring_active" in status
        assert "check_interval_seconds" in status
        assert status["check_interval_seconds"] == 1

    @pytest.mark.asyncio
    async def test_performance_metrics_gathering(self, monitor_service):
        """Test gathering performance metrics for monitoring"""

        # Mock system metrics
        monitor_service.orchestrator.get_system_metrics.return_value = Mock(
            consecutive_losses=3,
            max_drawdown_percent=2.5,
            daily_pnl_percent=1.2
        )

        metrics = await monitor_service._gather_performance_metrics()

        assert "walk_forward_stability" in metrics
        assert "overfitting_score" in metrics
        assert "consecutive_losses" in metrics
        assert metrics["consecutive_losses"] == 3


class TestPerformanceRecoveryValidator:
    """Test suite for the performance recovery validator"""

    @pytest.fixture
    def mock_orchestrator(self):
        orchestrator = Mock()
        orchestrator.get_system_status = AsyncMock()
        orchestrator.list_agents = AsyncMock(return_value=[])
        return orchestrator

    @pytest.fixture
    def recovery_validator(self, mock_orchestrator):
        return PerformanceRecoveryValidator(mock_orchestrator)

    @pytest.mark.asyncio
    async def test_recovery_validation_execution(self, recovery_validator):
        """Test complete recovery validation execution"""

        rollback_event_id = "test_rollback_001"

        with patch('orchestrator.app.recovery_validator.get_current_parameters') as mock_params:
            mock_params.return_value = {
                "confidence_threshold": 55.0,
                "min_risk_reward": 1.8
            }

            validation_report = await recovery_validator.validate_recovery(rollback_event_id)

            # Verify validation report structure
            assert validation_report.rollback_event_id == rollback_event_id
            assert validation_report.overall_status in [ValidationStatus.PASSED, ValidationStatus.WARNING, ValidationStatus.FAILED]
            assert validation_report.overall_score >= 0.0
            assert len(validation_report.validations) > 0
            assert isinstance(validation_report.recommendations, list)

    @pytest.mark.asyncio
    async def test_parameter_configuration_validation(self, recovery_validator):
        """Test parameter configuration validation"""

        with patch('orchestrator.app.recovery_validator.get_current_parameters') as mock_params, \
             patch('orchestrator.app.recovery_validator.CURRENT_PARAMETER_MODE') as mock_mode:

            # Test successful validation
            mock_params.return_value = {
                "confidence_threshold": 55.0,  # Correct Cycle 4 value
                "min_risk_reward": 1.8         # Correct Cycle 4 value
            }
            from orchestrator.app.recovery_validator import ParameterMode
            mock_mode = ParameterMode.UNIVERSAL_CYCLE_4

            result = await recovery_validator._validate_parameter_configuration()

            assert result.validation_type == ValidationType.PARAMETER_CONFIRMATION
            assert result.score >= 95.0  # Should pass with correct parameters
            assert result.status == ValidationStatus.PASSED

    @pytest.mark.asyncio
    async def test_system_stability_validation(self, recovery_validator):
        """Test system stability validation"""

        # Mock healthy system status
        recovery_validator.orchestrator.get_system_status.return_value = Mock(
            status="healthy"
        )

        result = await recovery_validator._validate_system_stability()

        assert result.validation_type == ValidationType.SYSTEM_STABILITY
        assert result.score > 0.0

    def test_overall_score_calculation(self, recovery_validator):
        """Test overall validation score calculation"""

        from orchestrator.app.recovery_validator import ValidationResult, ValidationStatus, ValidationType

        # Create mock validation results
        validation_results = [
            ValidationResult(
                validation_type=ValidationType.PARAMETER_CONFIRMATION,
                status=ValidationStatus.PASSED,
                score=95.0,
                threshold=95.0,
                details={},
                timestamp=datetime.now(timezone.utc),
                message="Parameters validated"
            ),
            ValidationResult(
                validation_type=ValidationType.SYSTEM_STABILITY,
                status=ValidationStatus.PASSED,
                score=85.0,
                threshold=80.0,
                details={},
                timestamp=datetime.now(timezone.utc),
                message="System stable"
            )
        ]

        overall_score = recovery_validator._calculate_overall_score(validation_results)

        # Should be weighted average (parameter confirmation has highest weight)
        assert 85.0 <= overall_score <= 95.0

    def test_recovery_confirmation(self, recovery_validator):
        """Test recovery confirmation logic"""

        from orchestrator.app.recovery_validator import ValidationResult, ValidationStatus, ValidationType

        # Test with all critical validations passing
        passing_results = [
            ValidationResult(
                ValidationType.PARAMETER_CONFIRMATION, ValidationStatus.PASSED,
                95.0, 95.0, {}, datetime.now(timezone.utc), "Passed"
            ),
            ValidationResult(
                ValidationType.SYSTEM_STABILITY, ValidationStatus.PASSED,
                85.0, 80.0, {}, datetime.now(timezone.utc), "Passed"
            ),
            ValidationResult(
                ValidationType.RISK_METRICS, ValidationStatus.PASSED,
                90.0, 85.0, {}, datetime.now(timezone.utc), "Passed"
            )
        ]

        recovery_confirmed = recovery_validator._confirm_recovery(passing_results)
        assert recovery_confirmed is True

        # Test with critical validation failing
        failing_results = [
            ValidationResult(
                ValidationType.PARAMETER_CONFIRMATION, ValidationStatus.FAILED,
                60.0, 95.0, {}, datetime.now(timezone.utc), "Failed"
            )
        ]

        recovery_confirmed = recovery_validator._confirm_recovery(failing_results)
        assert recovery_confirmed is False


class TestEmergencyContactSystem:
    """Test suite for the emergency contact system"""

    @pytest.fixture
    def contact_system(self):
        return EmergencyContactSystem()

    def test_contact_initialization(self, contact_system):
        """Test that default contacts are properly initialized"""

        contacts = contact_system.get_contacts()

        assert len(contacts) > 0
        assert "admin-001" in contacts
        assert "risk-001" in contacts

        # Verify contact structure
        admin_contact = contacts["admin-001"]
        assert admin_contact["name"] == "System Administrator"
        assert admin_contact["contact_type"] == ContactType.PRIMARY.value
        assert admin_contact["email"] == "admin@trading-system.com"

    def test_template_initialization(self, contact_system):
        """Test that notification templates are properly initialized"""

        templates = contact_system.templates

        assert "emergency_rollback" in templates
        assert "automatic_trigger" in templates
        assert "validation_failure" in templates

        # Verify template structure
        rollback_template = templates["emergency_rollback"]
        assert rollback_template.priority == NotificationPriority.EMERGENCY
        assert NotificationChannel.EMAIL in rollback_template.channels

    @pytest.mark.asyncio
    async def test_emergency_notification_sending(self, contact_system):
        """Test sending emergency notifications"""

        # Test event data
        event_data = {
            "trigger_type": "TEST",
            "reason": "Test notification",
            "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
            "event_id": "test_001",
            "previous_mode": "session_targeted",
            "new_mode": "universal_cycle_4",
            "validation_status": "PASSED"
        }

        # Send notifications (will be mocked)
        results = await contact_system.notify_emergency_contacts(
            event_type="emergency_rollback",
            event_data=event_data,
            priority=NotificationPriority.EMERGENCY,
            contact_types=[ContactType.TECHNICAL]
        )

        # Verify results structure
        assert isinstance(results, list)
        if results:  # If any contacts were found
            assert all(hasattr(result, 'contact_id') for result in results)
            assert all(hasattr(result, 'success') for result in results)

    def test_notification_history_tracking(self, contact_system):
        """Test that notification history is properly tracked"""

        # Initially empty
        history = contact_system.get_notification_history()
        initial_count = len(history)

        # Add a mock notification to history
        contact_system.notification_history.append({
            "event_type": "test",
            "priority": "emergency",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "contacts_targeted": 1,
            "notifications_sent": 1,
            "successful_notifications": 1
        })

        # Verify history updated
        updated_history = contact_system.get_notification_history()
        assert len(updated_history) == initial_count + 1

    @pytest.mark.asyncio
    async def test_email_notification_formatting(self, contact_system):
        """Test email notification message formatting"""

        from orchestrator.app.emergency_contacts import EmergencyContact, NotificationTemplate

        # Create test contact
        test_contact = EmergencyContact(
            id="test-001",
            name="Test Contact",
            role="Test Role",
            contact_type=ContactType.TECHNICAL,
            email="test@example.com"
        )

        # Create test template
        test_template = NotificationTemplate(
            name="test_template",
            priority=NotificationPriority.HIGH,
            channels=[NotificationChannel.EMAIL],
            subject_template="Test Subject: {trigger_type}",
            body_template="Test Body: {reason}"
        )

        event_data = {
            "trigger_type": "TEST",
            "reason": "Test reason"
        }

        # Test email sending (mocked)
        result = await contact_system._send_email(test_contact, test_template, event_data)

        # Should succeed (mocked implementation)
        assert result.contact_id == "test-001"
        assert result.channel == NotificationChannel.EMAIL


class TestIntegrationScenarios:
    """Integration tests for complete rollback scenarios"""

    @pytest.fixture
    def mock_orchestrator(self):
        orchestrator = Mock()
        orchestrator.emergency_stop = AsyncMock()
        orchestrator.restart_agent = AsyncMock()
        orchestrator.get_system_status = AsyncMock()
        orchestrator.list_agents = AsyncMock(return_value=["market-analysis"])
        return orchestrator

    @pytest.fixture
    async def integrated_system(self, mock_orchestrator):
        """Create integrated rollback system with all components"""
        rollback_system = EmergencyRollbackSystem(mock_orchestrator)
        monitor_service = RollbackMonitorService(mock_orchestrator, check_interval=1)
        recovery_validator = PerformanceRecoveryValidator(mock_orchestrator)
        contact_system = EmergencyContactSystem()

        return {
            "rollback": rollback_system,
            "monitor": monitor_service,
            "validator": recovery_validator,
            "contacts": contact_system
        }

    @pytest.mark.asyncio
    async def test_complete_rollback_workflow(self, integrated_system):
        """Test complete rollback workflow: trigger -> rollback -> validate -> notify"""

        rollback_system = integrated_system["rollback"]
        recovery_validator = integrated_system["validator"]

        with patch('orchestrator.app.emergency_rollback.set_parameter_mode') as mock_params, \
             patch('orchestrator.app.recovery_validator.get_current_parameters') as mock_get_params:

            mock_params.return_value = {"previous_mode": "session_targeted", "new_mode": "universal_cycle_4"}
            mock_get_params.return_value = {"confidence_threshold": 55.0, "min_risk_reward": 1.8}

            # 1. Execute rollback
            rollback_event = await rollback_system.execute_emergency_rollback(
                trigger_type=RollbackTrigger.MANUAL,
                reason="Integration test rollback",
                notify_contacts=False  # Skip notifications for test
            )

            assert rollback_event.rollback_status == RollbackStatus.COMPLETED

            # 2. Validate recovery
            validation_report = await recovery_validator.validate_recovery(rollback_event.event_id)

            assert validation_report.rollback_event_id == rollback_event.event_id
            assert validation_report.overall_status in [ValidationStatus.PASSED, ValidationStatus.WARNING]

            # 3. Verify rollback history
            rollback_history = rollback_system.get_rollback_history(limit=5)
            assert len(rollback_history) >= 1
            assert rollback_history[0]["rollback_event_id"] == rollback_event.event_id

    @pytest.mark.asyncio
    async def test_automatic_rollback_scenario(self, integrated_system):
        """Test automatic rollback triggered by monitoring"""

        monitor_service = integrated_system["monitor"]
        rollback_system = integrated_system["rollback"]

        # Create conditions that should trigger automatic rollback
        with patch.object(monitor_service, '_gather_performance_metrics') as mock_metrics:
            mock_metrics.return_value = {
                "walk_forward_stability": 30.0,  # Critical failure
                "overfitting_score": 0.8,
                "consecutive_losses": 7,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            # Test trigger detection
            performance_data = await monitor_service._gather_performance_metrics()
            trigger = await rollback_system.check_automatic_triggers(performance_data)

            assert trigger == RollbackTrigger.WALK_FORWARD_FAILURE

    def test_error_handling_and_recovery(self, integrated_system):
        """Test error handling in rollback components"""

        rollback_system = integrated_system["rollback"]

        # Test rollback with orchestrator failure
        rollback_system.orchestrator.emergency_stop = AsyncMock(side_effect=Exception("Test error"))

        # Should handle gracefully and record failure
        with pytest.raises(Exception):
            asyncio.run(rollback_system.execute_emergency_rollback(
                trigger_type=RollbackTrigger.MANUAL,
                reason="Error handling test",
                notify_contacts=False
            ))

        # Should record the failed attempt
        assert rollback_system.current_status == RollbackStatus.FAILED


# Test fixtures and utilities
@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Test data generators
def generate_test_performance_data(scenario="normal"):
    """Generate test performance data for different scenarios"""

    scenarios = {
        "normal": {
            "walk_forward_stability": 65.0,
            "overfitting_score": 0.25,
            "consecutive_losses": 2,
            "max_drawdown_percent": 3.0,
        },
        "critical": {
            "walk_forward_stability": 25.0,  # Critical failure
            "overfitting_score": 0.75,      # High overfitting
            "consecutive_losses": 8,         # Excessive losses
            "max_drawdown_percent": 7.5,     # High drawdown
        },
        "warning": {
            "walk_forward_stability": 45.0,  # Below ideal but not critical
            "overfitting_score": 0.4,       # Moderate overfitting
            "consecutive_losses": 4,         # Moderate losses
            "max_drawdown_percent": 4.5,     # Moderate drawdown
        }
    }

    return scenarios.get(scenario, scenarios["normal"])


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])