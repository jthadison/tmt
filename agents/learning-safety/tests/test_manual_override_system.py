"""
Tests for Manual Override System

Tests manual learning controls, authorization, impact assessment,
audit logging, and dashboard monitoring functionality.
"""

import pytest
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from manual_override_system import (
    ManualOverrideSystem,
    AuthorizationManager,
    ImpactAssessor,
    AuditLogger,
    OverrideType,
    OverrideStatus,
    AuthorizationLevel,
    ImpactLevel,
    OverrideAuthorization,
    OverrideRequest,
    AuditLogEntry
)


@pytest.fixture
def temp_storage_dir():
    """Create temporary storage directory for testing"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def auth_manager():
    """Create authorization manager for testing"""
    return AuthorizationManager()


@pytest.fixture
def impact_assessor():
    """Create impact assessor for testing"""
    return ImpactAssessor()


@pytest.fixture
def audit_logger(temp_storage_dir):
    """Create audit logger for testing"""
    return AuditLogger(str(Path(temp_storage_dir) / "audit"))


@pytest.fixture
def override_system(temp_storage_dir):
    """Create complete override system for testing"""
    return ManualOverrideSystem(temp_storage_dir)


class TestAuthorizationManager:
    """Test authorization and session management"""
    
    def test_authenticate_valid_user(self, auth_manager):
        """Test authentication with valid credentials"""
        authorization = auth_manager.authenticate_user("operator1", "password")
        
        assert authorization is not None
        assert authorization.user_id == "operator1"
        assert authorization.user_role == "operator"
        assert authorization.authorization_level == AuthorizationLevel.OPERATOR
        assert authorization.session_valid is True
        assert authorization.session_id in auth_manager.active_sessions
    
    def test_authenticate_invalid_user(self, auth_manager):
        """Test authentication with invalid credentials"""
        authorization = auth_manager.authenticate_user("invalid_user", "wrong_password")
        
        assert authorization is None
        assert len(auth_manager.active_sessions) == 0
    
    def test_user_permissions_by_role(self, auth_manager):
        """Test that permissions are correctly assigned by role"""
        # Test operator permissions
        operator_auth = auth_manager.authenticate_user("operator1", "password")
        operator_permissions = operator_auth.permissions
        
        assert OverrideType.FORCE_LEARNING_ON in operator_permissions
        assert OverrideType.FORCE_LEARNING_OFF in operator_permissions
        assert OverrideType.FORCE_QUARANTINE in operator_permissions
        assert OverrideType.BYPASS_CIRCUIT_BREAKER not in operator_permissions  # Requires supervisor
        
        # Test supervisor permissions
        supervisor_auth = auth_manager.authenticate_user("supervisor1", "password")
        supervisor_permissions = supervisor_auth.permissions
        
        assert OverrideType.FORCE_LEARNING_ON in supervisor_permissions
        assert OverrideType.BYPASS_CIRCUIT_BREAKER in supervisor_permissions
        assert OverrideType.FORCE_ROLLBACK in supervisor_permissions
        assert OverrideType.EMERGENCY_STOP not in supervisor_permissions  # Requires emergency
        
        # Test admin permissions
        admin_auth = auth_manager.authenticate_user("admin1", "password")
        admin_permissions = admin_auth.permissions
        
        assert OverrideType.PREVENT_ROLLBACK in admin_permissions
        assert OverrideType.RESET_SYSTEM in admin_permissions
        assert len(admin_permissions) > len(supervisor_permissions)
    
    def test_authorization_levels_and_durations(self, auth_manager):
        """Test maximum durations and approval requirements by authorization level"""
        operator_auth = auth_manager.authenticate_user("operator1", "password")
        supervisor_auth = auth_manager.authenticate_user("supervisor1", "password")
        admin_auth = auth_manager.authenticate_user("admin1", "password")
        
        # Check max durations
        assert operator_auth.max_duration_hours == 4.0
        assert supervisor_auth.max_duration_hours == 12.0
        assert admin_auth.max_duration_hours == 24.0
        
        # Check approval requirements
        assert operator_auth.requires_approval is False
        assert supervisor_auth.requires_approval is False
        assert admin_auth.requires_approval is True
    
    def test_check_authorization(self, auth_manager):
        """Test authorization checking for specific override types"""
        operator_auth = auth_manager.authenticate_user("operator1", "password")
        
        # Should be authorized for operator-level overrides
        assert auth_manager.check_authorization(operator_auth.session_id, OverrideType.FORCE_LEARNING_ON)
        assert auth_manager.check_authorization(operator_auth.session_id, OverrideType.FORCE_QUARANTINE)
        
        # Should not be authorized for higher-level overrides
        assert not auth_manager.check_authorization(operator_auth.session_id, OverrideType.BYPASS_CIRCUIT_BREAKER)
        assert not auth_manager.check_authorization(operator_auth.session_id, OverrideType.EMERGENCY_STOP)
        
        # Invalid session should fail
        assert not auth_manager.check_authorization("invalid_session", OverrideType.FORCE_LEARNING_ON)
    
    def test_session_management(self, auth_manager):
        """Test session creation, validation, and revocation"""
        authorization = auth_manager.authenticate_user("operator1", "password")
        session_id = authorization.session_id
        
        # Session should be valid initially
        assert auth_manager.check_authorization(session_id, OverrideType.FORCE_LEARNING_ON)
        
        # Update activity should work
        assert auth_manager.update_session_activity(session_id)
        
        # Revoke session
        assert auth_manager.revoke_session(session_id)
        
        # Should no longer be authorized
        assert not auth_manager.check_authorization(session_id, OverrideType.FORCE_LEARNING_ON)
        assert session_id not in auth_manager.active_sessions


class TestImpactAssessor:
    """Test impact assessment functionality"""
    
    def test_basic_impact_assessment(self, impact_assessor):
        """Test basic impact assessment for different override types"""
        # Low impact override
        low_impact = impact_assessor.assess_impact(
            OverrideType.FORCE_LEARNING_OFF, 
            ["learning_engine"], 
            2.0
        )
        
        assert low_impact.impact_level == ImpactLevel.LOW
        assert low_impact.override_type == OverrideType.FORCE_LEARNING_OFF
        assert low_impact.system_stability_risk < 0.5
        assert len(low_impact.recommended_safeguards) >= 2
        
        # High impact override
        high_impact = impact_assessor.assess_impact(
            OverrideType.BYPASS_CIRCUIT_BREAKER,
            ["circuit_breaker", "safety_system"],
            8.0
        )
        
        assert high_impact.impact_level == ImpactLevel.HIGH
        assert high_impact.system_stability_risk > 0.5
        assert high_impact.estimated_financial_risk > low_impact.estimated_financial_risk
        assert len(high_impact.recommended_safeguards) > len(low_impact.recommended_safeguards)
    
    def test_financial_risk_assessment(self, impact_assessor):
        """Test financial risk calculation"""
        # Test with context
        context = {
            "trading_volume": 5000000,  # $5M
            "affected_accounts": ["acc1", "acc2", "acc3", "acc4", "acc5"]
        }
        
        assessment = impact_assessor.assess_impact(
            OverrideType.BYPASS_CIRCUIT_BREAKER,
            ["circuit_breaker"],
            4.0,
            context
        )
        
        assert assessment.estimated_financial_risk > 0
        assert assessment.potential_loss_range[0] < assessment.potential_loss_range[1]
        assert assessment.affected_trading_volume == 5000000
        assert len(assessment.affected_accounts) == 5
    
    def test_urgency_determination(self, impact_assessor):
        """Test urgency level determination"""
        # Emergency override should be critical urgency
        emergency_assessment = impact_assessor.assess_impact(
            OverrideType.EMERGENCY_STOP,
            ["all_systems"],
            1.0
        )
        
        assert emergency_assessment.urgency_level == "critical"
        
        # Regular override should be lower urgency
        regular_assessment = impact_assessor.assess_impact(
            OverrideType.FORCE_LEARNING_OFF,
            ["learning_engine"],
            2.0
        )
        
        assert regular_assessment.urgency_level in ["low", "medium"]
    
    def test_safeguards_and_monitoring(self, impact_assessor):
        """Test safeguard and monitoring recommendations"""
        assessment = impact_assessor.assess_impact(
            OverrideType.FORCE_ROLLBACK,
            ["model_system", "data_system"],
            6.0
        )
        
        # Should have safeguards
        assert len(assessment.recommended_safeguards) > 0
        assert "monitoring" in assessment.recommended_safeguards[0].lower()
        
        # Should have monitoring requirements
        assert len(assessment.monitoring_requirements) > 0
        assert any("performance" in req.lower() for req in assessment.monitoring_requirements)
        
        # Should have rollback plan
        assert assessment.rollback_plan
        assert len(assessment.rollback_plan) > 10  # Non-trivial plan
    
    def test_max_safe_duration_calculation(self, impact_assessor):
        """Test maximum safe duration calculation"""
        # High impact should have shorter safe duration
        high_impact = impact_assessor.assess_impact(
            OverrideType.PREVENT_ROLLBACK,
            ["safety_system"],
            12.0
        )
        
        # Low impact should have longer safe duration
        low_impact = impact_assessor.assess_impact(
            OverrideType.FORCE_QUARANTINE,
            ["quarantine_system"],
            12.0
        )
        
        assert high_impact.max_safe_duration < low_impact.max_safe_duration
        assert high_impact.max_safe_duration <= timedelta(hours=4)  # Critical impact max


class TestAuditLogger:
    """Test audit logging functionality"""
    
    def test_log_event_creation(self, audit_logger):
        """Test basic audit event logging"""
        log_id = audit_logger.log_event(
            event_type="test_event",
            user_id="test_user",
            session_id="test_session",
            component_affected="test_component",
            action_taken="test_action",
            parameters={"param1": "value1"},
            success=True,
            system_state_before={"state": "before"},
            system_state_after={"state": "after"}
        )
        
        assert log_id is not None
        assert log_id.startswith("audit_")
        assert len(audit_logger.log_cache) == 1
        
        log_entry = audit_logger.log_cache[0]
        assert log_entry.log_id == log_id
        assert log_entry.event_type == "test_event"
        assert log_entry.user_id == "test_user"
        assert log_entry.success is True
    
    def test_log_filtering(self, audit_logger):
        """Test audit log filtering functionality"""
        # Create multiple log entries
        user1_logs = []
        user2_logs = []
        
        for i in range(5):
            log_id = audit_logger.log_event(
                event_type="user1_event",
                user_id="user1",
                session_id="session1",
                component_affected="component1",
                action_taken=f"action_{i}",
                parameters={},
                success=True,
                system_state_before={},
                system_state_after={}
            )
            user1_logs.append(log_id)
        
        for i in range(3):
            log_id = audit_logger.log_event(
                event_type="user2_event",
                user_id="user2",
                session_id="session2",
                component_affected="component2",
                action_taken=f"action_{i}",
                parameters={},
                success=True,
                system_state_before={},
                system_state_after={}
            )
            user2_logs.append(log_id)
        
        # Test user filtering
        user1_entries = audit_logger.get_audit_logs(user_id="user1")
        assert len(user1_entries) == 5
        assert all(entry.user_id == "user1" for entry in user1_entries)
        
        # Test event type filtering
        user1_events = audit_logger.get_audit_logs(event_type="user1_event")
        assert len(user1_events) == 5
        assert all(entry.event_type == "user1_event" for entry in user1_events)
        
        # Test limit
        limited_logs = audit_logger.get_audit_logs(limit=3)
        assert len(limited_logs) <= 3
    
    def test_user_activity_tracking(self, audit_logger):
        """Test user activity tracking"""
        # Log some user activity
        for i in range(3):
            audit_logger.log_event(
                event_type="user_action",
                user_id="active_user",
                session_id="session123",
                component_affected="system",
                action_taken=f"action_{i}",
                parameters={},
                success=True,
                system_state_before={},
                system_state_after={}
            )
        
        # Get user activity
        activity = audit_logger.get_user_activity("active_user", hours_back=24)
        
        assert len(activity) == 3
        assert all(entry.user_id == "active_user" for entry in activity)
    
    def test_system_events_tracking(self, audit_logger):
        """Test system component event tracking"""
        # Log events for different components
        audit_logger.log_event(
            event_type="component_event",
            user_id="user1",
            session_id="session1",
            component_affected="learning_engine",
            action_taken="start_learning",
            parameters={},
            success=True,
            system_state_before={},
            system_state_after={}
        )
        
        audit_logger.log_event(
            event_type="component_event",
            user_id="user2",
            session_id="session2",
            component_affected="circuit_breaker",
            action_taken="activate_breaker",
            parameters={},
            success=True,
            system_state_before={},
            system_state_after={}
        )
        
        # Get events for specific component
        learning_events = audit_logger.get_system_events("learning_engine", hours_back=24)
        assert len(learning_events) == 1
        assert learning_events[0].component_affected == "learning_engine"
        
        breaker_events = audit_logger.get_system_events("circuit_breaker", hours_back=24)
        assert len(breaker_events) == 1
        assert breaker_events[0].component_affected == "circuit_breaker"


class TestManualOverrideSystem:
    """Test integrated manual override system"""
    
    def test_user_authentication_flow(self, override_system):
        """Test complete user authentication flow"""
        # Valid authentication
        session_id = override_system.authenticate_user("operator1", "password", "192.168.1.1", "test-browser")
        
        assert session_id is not None
        assert session_id in override_system.authorization_manager.active_sessions
        
        # Check audit log
        recent_logs = override_system.audit_logger.get_audit_logs(limit=1)
        assert len(recent_logs) == 1
        assert recent_logs[0].event_type == "user_authentication"
        assert recent_logs[0].success is True
        
        # Invalid authentication
        invalid_session = override_system.authenticate_user("invalid", "wrong", "192.168.1.1", "test-browser")
        
        assert invalid_session is None
        
        # Check failed auth log
        recent_logs = override_system.audit_logger.get_audit_logs(limit=1)
        assert recent_logs[0].event_type == "authentication_failure"
        assert recent_logs[0].success is False
    
    def test_override_request_creation(self, override_system):
        """Test creating override requests"""
        # Authenticate user
        session_id = override_system.authenticate_user("operator1", "password")
        
        # Create override request
        request_id = override_system.request_override(
            session_id=session_id,
            override_type=OverrideType.FORCE_LEARNING_OFF,
            target_components=["learning_engine"],
            duration_hours=2.0,
            business_reason="Market volatility too high",
            technical_reason="Circuit breaker triggered multiple times",
            immediate_execution=False
        )
        
        assert request_id is not None
        
        # Should be in active overrides (auto-approved for operator)
        assert request_id in override_system.active_overrides
        
        override_request = override_system.active_overrides[request_id]
        assert override_request.override_type == OverrideType.FORCE_LEARNING_OFF
        assert override_request.status == OverrideStatus.APPROVED
        assert override_request.duration_hours == 2.0
        assert len(override_request.target_components) == 1
    
    def test_approval_workflow(self, override_system):
        """Test override approval workflow for high-privilege operations"""
        # Authenticate admin user (requires approval)
        session_id = override_system.authenticate_user("admin1", "password")
        
        # Create override request requiring approval
        request_id = override_system.request_override(
            session_id=session_id,
            override_type=OverrideType.RESET_SYSTEM,
            target_components=["all_systems"],
            duration_hours=1.0,
            business_reason="System corruption detected",
            technical_reason="Multiple component failures",
            immediate_execution=False
        )
        
        assert request_id is not None
        
        # Should be in pending requests (requires approval)
        assert request_id in override_system.pending_requests
        assert request_id not in override_system.active_overrides
        
        override_request = override_system.pending_requests[request_id]
        assert override_request.status == OverrideStatus.PENDING
        
        # Approve the request
        approval_success = override_system.approve_override(
            session_id, request_id, "Approved due to system corruption"
        )
        
        assert approval_success is True
        
        # Should now be in active overrides
        assert request_id not in override_system.pending_requests
        assert request_id in override_system.active_overrides
    
    def test_override_execution(self, override_system):
        """Test override execution and system state changes"""
        # Authenticate and create request
        session_id = override_system.authenticate_user("operator1", "password")
        
        # Initial system state
        initial_state = override_system.system_state.copy()
        assert initial_state["learning_enabled"] is True
        
        request_id = override_system.request_override(
            session_id=session_id,
            override_type=OverrideType.FORCE_LEARNING_OFF,
            target_components=["learning_engine"],
            duration_hours=1.0,
            business_reason="Manual testing",
            technical_reason="System validation required",
            immediate_execution=True
        )
        
        # Should be executed immediately
        override_request = override_system.active_overrides[request_id]
        assert override_request.status == OverrideStatus.ACTIVE
        assert override_request.execution_successful is True
        
        # System state should be changed
        assert override_system.system_state["learning_enabled"] is False
        
        # Should have expiry timestamp
        assert override_request.expiry_timestamp is not None
        assert override_request.expiry_timestamp > datetime.utcnow()
    
    def test_override_revocation(self, override_system):
        """Test revoking active overrides"""
        # Create and execute override
        session_id = override_system.authenticate_user("supervisor1", "password")
        
        request_id = override_system.request_override(
            session_id=session_id,
            override_type=OverrideType.BYPASS_CIRCUIT_BREAKER,
            target_components=["circuit_breaker"],
            duration_hours=4.0,
            business_reason="Critical trading opportunity",
            technical_reason="Circuit breaker false positive",
            immediate_execution=True
        )
        
        # Verify override is active
        assert request_id in override_system.active_overrides
        assert override_system.system_state["circuit_breaker_active"] is False
        
        # Revoke the override
        revoke_success = override_system.revoke_override(
            session_id, request_id, "Market conditions normalized"
        )
        
        assert revoke_success is True
        
        # Should be moved to completed
        assert request_id not in override_system.active_overrides
        assert request_id in override_system.completed_requests
        
        completed_request = override_system.completed_requests[request_id]
        assert completed_request.status == OverrideStatus.REVOKED
    
    def test_unauthorized_override_attempt(self, override_system):
        """Test handling of unauthorized override attempts"""
        # Authenticate operator (low privilege)
        session_id = override_system.authenticate_user("operator1", "password")
        
        # Try to perform high-privilege override
        request_id = override_system.request_override(
            session_id=session_id,
            override_type=OverrideType.EMERGENCY_STOP,  # Requires emergency level
            target_components=["all_systems"],
            duration_hours=1.0,
            business_reason="Emergency situation",
            technical_reason="System malfunction"
        )
        
        # Should be rejected
        assert request_id is None
        
        # Should be logged as unauthorized attempt
        recent_logs = override_system.audit_logger.get_audit_logs(limit=2)
        unauthorized_log = next((log for log in recent_logs 
                               if log.event_type == "unauthorized_override_attempt"), None)
        
        assert unauthorized_log is not None
        assert unauthorized_log.success is False
        assert "emergency_stop" in unauthorized_log.parameters["attempted_override"]
    
    def test_system_status_reporting(self, override_system):
        """Test system status and health reporting"""
        # Create some override activity
        session_id = override_system.authenticate_user("operator1", "password")
        
        request_id1 = override_system.request_override(
            session_id=session_id,
            override_type=OverrideType.FORCE_LEARNING_OFF,
            target_components=["learning_engine"],
            duration_hours=2.0,
            business_reason="Testing",
            technical_reason="System test",
            immediate_execution=True
        )
        
        # Get system status
        status = override_system.get_system_status()
        
        # Check status structure
        assert "system_state" in status
        assert "active_overrides" in status
        assert "pending_requests" in status
        assert "active_sessions" in status
        assert "override_summary" in status
        assert "system_health" in status
        
        # Check values
        assert status["active_overrides"] == 1
        assert status["active_sessions"] == 1
        
        # Check system health
        health = status["system_health"]
        assert "health_score" in health
        assert "warnings" in health
        assert 0.0 <= health["health_score"] <= 1.0
    
    def test_dashboard_data_generation(self, override_system):
        """Test dashboard data generation for monitoring"""
        # Authenticate user
        session_id = override_system.authenticate_user("supervisor1", "password")
        
        # Create some activity
        request_id = override_system.request_override(
            session_id=session_id,
            override_type=OverrideType.FORCE_ROLLBACK,
            target_components=["model_system"],
            duration_hours=3.0,
            business_reason="Model performance degraded",
            technical_reason="Rollback to stable version required"
        )
        
        # Get dashboard data
        dashboard_data = override_system.get_override_dashboard_data(session_id)
        
        # Check dashboard structure
        assert "user_info" in dashboard_data
        assert "active_overrides" in dashboard_data
        assert "pending_requests" in dashboard_data
        assert "recent_activity" in dashboard_data
        assert "system_alerts" in dashboard_data
        assert "quick_actions" in dashboard_data
        
        # Check user info
        user_info = dashboard_data["user_info"]
        assert user_info["user_id"] == "supervisor1"
        assert user_info["role"] == "supervisor"
        assert len(user_info["permissions"]) > 0
        
        # Check overrides formatting
        active_overrides = dashboard_data["active_overrides"]
        assert len(active_overrides) == 1
        assert active_overrides[0]["request_id"] == request_id
        assert active_overrides[0]["override_type"] == "force_rollback"
        
        # Check quick actions
        quick_actions = dashboard_data["quick_actions"]
        assert len(quick_actions) > 0
        assert all("override_type" in action for action in quick_actions)
    
    def test_emergency_override_flow(self, override_system):
        """Test emergency override scenario"""
        # Authenticate emergency user
        session_id = override_system.authenticate_user("emergency1", "password")
        
        # Create emergency override
        request_id = override_system.request_override(
            session_id=session_id,
            override_type=OverrideType.EMERGENCY_STOP,
            target_components=["all_systems"],
            duration_hours=0.5,
            business_reason="Critical system failure detected",
            technical_reason="Multiple safety violations",
            immediate_execution=True,
            context={"urgency": "critical", "system_failure": True}
        )
        
        assert request_id is not None
        
        # Should be executed immediately even though it requires approval
        # (emergency situations may have different approval rules)
        override_request = override_system.active_overrides[request_id]
        assert override_request.status == OverrideStatus.ACTIVE
        
        # System should be in emergency mode
        assert override_system.system_state["emergency_mode"] is True
        assert override_system.system_state["learning_enabled"] is False
        
        # Impact assessment should show critical impact
        assert override_request.impact_assessment.impact_level == ImpactLevel.CRITICAL
        assert override_request.impact_assessment.urgency_level == "critical"
    
    def test_override_expiration_handling(self, override_system):
        """Test handling of expired overrides"""
        # Create override with very short duration
        session_id = override_system.authenticate_user("operator1", "password")
        
        request_id = override_system.request_override(
            session_id=session_id,
            override_type=OverrideType.FORCE_LEARNING_OFF,
            target_components=["learning_engine"],
            duration_hours=0.001,  # Very short duration (3.6 seconds)
            business_reason="Short test",
            technical_reason="Expiration testing",
            immediate_execution=True
        )
        
        override_request = override_system.active_overrides[request_id]
        
        # Manually set expiry to past for testing
        override_request.expiry_timestamp = datetime.utcnow() - timedelta(minutes=1)
        
        # Check expiration detection
        assert override_request.is_expired() is True
        assert override_request.is_active() is False
        
        # Get system alerts should show expired override
        dashboard_data = override_system.get_override_dashboard_data(session_id)
        alerts = dashboard_data.get("system_alerts", [])
        
        expired_alert = next((alert for alert in alerts if alert["type"] == "expired_override"), None)
        assert expired_alert is not None
        assert "expired" in expired_alert["message"].lower()
    
    def test_audit_trail_completeness(self, override_system):
        """Test that all operations are properly audited"""
        # Perform various operations
        session_id = override_system.authenticate_user("supervisor1", "password")
        
        request_id = override_system.request_override(
            session_id=session_id,
            override_type=OverrideType.BYPASS_CIRCUIT_BREAKER,
            target_components=["circuit_breaker"],
            duration_hours=2.0,
            business_reason="Testing audit trail",
            technical_reason="Comprehensive logging test",
            immediate_execution=True
        )
        
        override_system.revoke_override(session_id, request_id, "Test completed")
        
        # Check audit logs
        all_logs = override_system.audit_logger.get_audit_logs(limit=10)
        
        # Should have logs for: authentication, request creation, execution, revocation
        event_types = [log.event_type for log in all_logs]
        
        assert "user_authentication" in event_types
        assert "override_request_created" in event_types
        assert "override_executed" in event_types
        assert "override_revoked" in event_types
        
        # Each log should have complete information
        for log in all_logs:
            assert log.log_id is not None
            assert log.timestamp is not None
            assert log.user_id is not None
            assert log.component_affected is not None
            assert log.action_taken is not None
            assert isinstance(log.success, bool)