"""
Manual Override System

Provides manual controls for learning circuit breaker operations, including
authorization, impact assessment, audit logging, and dashboard monitoring.
"""

import json
import hashlib
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Set, Any, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class OverrideType(Enum):
    """Types of manual overrides"""
    FORCE_LEARNING_ON = "force_learning_on"
    FORCE_LEARNING_OFF = "force_learning_off"
    BYPASS_CIRCUIT_BREAKER = "bypass_circuit_breaker"
    FORCE_QUARANTINE = "force_quarantine"
    RELEASE_QUARANTINE = "release_quarantine"
    FORCE_ROLLBACK = "force_rollback"
    PREVENT_ROLLBACK = "prevent_rollback"
    EMERGENCY_STOP = "emergency_stop"
    RESET_SYSTEM = "reset_system"


class OverrideStatus(Enum):
    """Status of override requests"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


class AuthorizationLevel(Enum):
    """Authorization levels for different override types"""
    OPERATOR = "operator"          # Basic operations
    SUPERVISOR = "supervisor"      # Advanced operations  
    ADMIN = "admin"               # Critical operations
    EMERGENCY = "emergency"       # Emergency-only operations


class ImpactLevel(Enum):
    """Impact assessment levels"""
    LOW = "low"           # Minimal risk
    MEDIUM = "medium"     # Moderate risk
    HIGH = "high"         # Significant risk
    CRITICAL = "critical" # Severe risk


@dataclass
class OverrideAuthorization:
    """Authorization details for override operations"""
    user_id: str
    user_role: str
    authorization_level: AuthorizationLevel
    permissions: List[OverrideType]
    
    # Authorization constraints
    max_duration_hours: float
    requires_approval: bool
    requires_justification: bool
    approval_required_from: List[str]  # List of required approver roles
    
    # Session info
    session_id: str
    login_timestamp: datetime
    last_activity: datetime
    session_valid: bool = True


@dataclass
class ImpactAssessment:
    """Assessment of override impact"""
    assessment_id: str
    override_type: OverrideType
    impact_level: ImpactLevel
    
    # Financial impact
    estimated_financial_risk: float
    potential_loss_range: Tuple[float, float]  # (min, max)
    affected_accounts: List[str]
    affected_trading_volume: float
    
    # System impact
    affected_components: List[str]
    system_stability_risk: float  # 0-1
    data_integrity_risk: float    # 0-1
    operational_continuity_risk: float  # 0-1
    
    # Time sensitivity
    urgency_level: str  # low, medium, high, critical
    max_safe_duration: timedelta
    rollback_complexity: str  # simple, moderate, complex
    
    # Mitigation measures
    recommended_safeguards: List[str]
    monitoring_requirements: List[str]
    rollback_plan: str
    
    # Assessment metadata
    assessed_by: str
    assessment_timestamp: datetime
    confidence_level: float  # 0-1


@dataclass
class OverrideJustification:
    """Justification for manual override"""
    justification_id: str
    override_type: OverrideType
    business_reason: str
    technical_reason: str
    
    # Context
    market_conditions: str
    system_conditions: str
    alternative_options_considered: List[str]
    why_alternatives_insufficient: str
    
    # Risk acceptance
    risks_acknowledged: List[str]
    mitigation_measures: List[str]
    monitoring_plan: str
    success_criteria: str
    
    # Approval chain
    submitted_by: str
    submission_timestamp: datetime
    required_approvals: List[str]
    received_approvals: List[Dict[str, Any]]
    approval_complete: bool


@dataclass
class OverrideRequest:
    """Complete override request"""
    request_id: str
    override_type: OverrideType
    status: OverrideStatus
    
    # Request details
    requested_by: str
    request_timestamp: datetime
    target_components: List[str]
    duration_hours: float
    immediate_execution: bool
    
    # Authorization and approval
    authorization: OverrideAuthorization
    justification: OverrideJustification
    impact_assessment: ImpactAssessment
    
    # Execution details
    approved_by: Optional[str] = None
    approval_timestamp: Optional[datetime] = None
    executed_by: Optional[str] = None
    execution_timestamp: Optional[datetime] = None
    expiry_timestamp: Optional[datetime] = None
    
    # Results
    execution_successful: bool = False
    actual_impact: Optional[Dict[str, Any]] = None
    side_effects: List[str] = None
    
    # Monitoring
    monitoring_data: List[Dict[str, Any]] = None
    warnings_triggered: List[str] = None
    
    def __post_init__(self):
        if self.side_effects is None:
            self.side_effects = []
        if self.monitoring_data is None:
            self.monitoring_data = []
        if self.warnings_triggered is None:
            self.warnings_triggered = []
    
    def is_expired(self) -> bool:
        """Check if override has expired"""
        if not self.expiry_timestamp:
            return False
        return datetime.utcnow() > self.expiry_timestamp
    
    def is_active(self) -> bool:
        """Check if override is currently active"""
        return (self.status == OverrideStatus.ACTIVE and 
                not self.is_expired())


@dataclass
class AuditLogEntry:
    """Audit log entry for override operations"""
    log_id: str
    timestamp: datetime
    event_type: str
    user_id: str
    session_id: str
    
    # Event details
    override_request_id: Optional[str]
    component_affected: str
    action_taken: str
    parameters: Dict[str, Any]
    
    # Results
    success: bool
    error_message: Optional[str]
    system_state_before: Dict[str, Any]
    system_state_after: Dict[str, Any]
    
    # Security
    ip_address: str
    user_agent: str
    authentication_method: str
    authorization_checks: List[str]


class AuthorizationManager:
    """Manages user authorization and permissions"""
    
    def __init__(self):
        # Authorization rules mapping
        self.authorization_rules = {
            OverrideType.FORCE_LEARNING_ON: AuthorizationLevel.OPERATOR,
            OverrideType.FORCE_LEARNING_OFF: AuthorizationLevel.OPERATOR,
            OverrideType.BYPASS_CIRCUIT_BREAKER: AuthorizationLevel.SUPERVISOR,
            OverrideType.FORCE_QUARANTINE: AuthorizationLevel.OPERATOR,
            OverrideType.RELEASE_QUARANTINE: AuthorizationLevel.SUPERVISOR,
            OverrideType.FORCE_ROLLBACK: AuthorizationLevel.SUPERVISOR,
            OverrideType.PREVENT_ROLLBACK: AuthorizationLevel.ADMIN,
            OverrideType.EMERGENCY_STOP: AuthorizationLevel.EMERGENCY,
            OverrideType.RESET_SYSTEM: AuthorizationLevel.ADMIN
        }
        
        # Role hierarchy
        self.role_hierarchy = {
            "operator": AuthorizationLevel.OPERATOR,
            "supervisor": AuthorizationLevel.SUPERVISOR,
            "senior_supervisor": AuthorizationLevel.SUPERVISOR,
            "admin": AuthorizationLevel.ADMIN,
            "system_admin": AuthorizationLevel.ADMIN,
            "emergency_responder": AuthorizationLevel.EMERGENCY
        }
        
        # Active sessions
        self.active_sessions: Dict[str, OverrideAuthorization] = {}
    
    def authenticate_user(self, user_id: str, password: str, 
                         authentication_method: str = "password") -> Optional[OverrideAuthorization]:
        """Authenticate user and create authorization session"""
        # Mock authentication - in production, integrate with real auth system
        if self._verify_credentials(user_id, password):
            user_role = self._get_user_role(user_id)
            authorization_level = self.role_hierarchy.get(user_role, AuthorizationLevel.OPERATOR)
            
            # Create session
            session_id = f"session_{uuid.uuid4().hex[:16]}"
            
            authorization = OverrideAuthorization(
                user_id=user_id,
                user_role=user_role,
                authorization_level=authorization_level,
                permissions=self._get_user_permissions(authorization_level),
                max_duration_hours=self._get_max_duration(authorization_level),
                requires_approval=self._requires_approval(authorization_level),
                requires_justification=True,
                approval_required_from=self._get_required_approvers(authorization_level),
                session_id=session_id,
                login_timestamp=datetime.utcnow(),
                last_activity=datetime.utcnow()
            )
            
            self.active_sessions[session_id] = authorization
            return authorization
        
        return None
    
    def check_authorization(self, session_id: str, override_type: OverrideType) -> bool:
        """Check if user is authorized for specific override type"""
        if session_id not in self.active_sessions:
            return False
        
        authorization = self.active_sessions[session_id]
        
        # Check session validity
        if not self._is_session_valid(authorization):
            return False
        
        # Check permissions
        return override_type in authorization.permissions
    
    def update_session_activity(self, session_id: str) -> bool:
        """Update last activity timestamp for session"""
        if session_id in self.active_sessions:
            self.active_sessions[session_id].last_activity = datetime.utcnow()
            return True
        return False
    
    def revoke_session(self, session_id: str) -> bool:
        """Revoke authorization session"""
        if session_id in self.active_sessions:
            self.active_sessions[session_id].session_valid = False
            del self.active_sessions[session_id]
            return True
        return False
    
    def _verify_credentials(self, user_id: str, password: str) -> bool:
        """Verify user credentials (mock implementation)"""
        # Mock verification - in production, use real authentication
        return user_id in ["operator1", "supervisor1", "admin1", "emergency1", "senior_supervisor1", "system_admin1"]
    
    def _get_user_role(self, user_id: str) -> str:
        """Get user role (mock implementation)"""
        role_mapping = {
            "operator1": "operator",
            "supervisor1": "supervisor", 
            "admin1": "admin",
            "emergency1": "emergency_responder",
            "senior_supervisor1": "senior_supervisor",
            "system_admin1": "system_admin"
        }
        return role_mapping.get(user_id, "operator")
    
    def _get_user_permissions(self, auth_level: AuthorizationLevel) -> List[OverrideType]:
        """Get permissions based on authorization level"""
        permissions = []
        
        for override_type, required_level in self.authorization_rules.items():
            if auth_level.value in ["emergency", "admin"] or auth_level == required_level:
                permissions.append(override_type)
            elif auth_level == AuthorizationLevel.SUPERVISOR and required_level == AuthorizationLevel.OPERATOR:
                permissions.append(override_type)
            elif auth_level == AuthorizationLevel.ADMIN and required_level in [AuthorizationLevel.OPERATOR, AuthorizationLevel.SUPERVISOR]:
                permissions.append(override_type)
        
        return permissions
    
    def _get_max_duration(self, auth_level: AuthorizationLevel) -> float:
        """Get maximum override duration based on authorization level"""
        duration_mapping = {
            AuthorizationLevel.OPERATOR: 4.0,      # 4 hours
            AuthorizationLevel.SUPERVISOR: 12.0,   # 12 hours
            AuthorizationLevel.ADMIN: 24.0,        # 24 hours
            AuthorizationLevel.EMERGENCY: 72.0     # 72 hours
        }
        return duration_mapping.get(auth_level, 4.0)
    
    def _requires_approval(self, auth_level: AuthorizationLevel) -> bool:
        """Check if authorization level requires additional approval"""
        return auth_level in [AuthorizationLevel.ADMIN, AuthorizationLevel.EMERGENCY]
    
    def _get_required_approvers(self, auth_level: AuthorizationLevel) -> List[str]:
        """Get required approver roles"""
        if auth_level == AuthorizationLevel.ADMIN:
            return ["admin", "senior_supervisor", "system_admin"]  # Allow admin self-approval for testing
        elif auth_level == AuthorizationLevel.EMERGENCY:
            return ["admin", "system_admin"]
        return []
    
    def _is_session_valid(self, authorization: OverrideAuthorization) -> bool:
        """Check if authorization session is still valid"""
        if not authorization.session_valid:
            return False
        
        # Check for session timeout (4 hours)
        session_age = datetime.utcnow() - authorization.last_activity
        if session_age > timedelta(hours=4):
            return False
        
        return True


class ImpactAssessor:
    """Assesses impact of manual overrides"""
    
    def __init__(self):
        # Impact assessment rules
        self.impact_rules = {
            OverrideType.FORCE_LEARNING_ON: ImpactLevel.MEDIUM,
            OverrideType.FORCE_LEARNING_OFF: ImpactLevel.LOW,
            OverrideType.BYPASS_CIRCUIT_BREAKER: ImpactLevel.HIGH,
            OverrideType.FORCE_QUARANTINE: ImpactLevel.LOW,
            OverrideType.RELEASE_QUARANTINE: ImpactLevel.MEDIUM,
            OverrideType.FORCE_ROLLBACK: ImpactLevel.HIGH,
            OverrideType.PREVENT_ROLLBACK: ImpactLevel.CRITICAL,
            OverrideType.EMERGENCY_STOP: ImpactLevel.CRITICAL,
            OverrideType.RESET_SYSTEM: ImpactLevel.CRITICAL
        }
    
    def assess_impact(self, override_type: OverrideType, 
                     target_components: List[str],
                     duration_hours: float,
                     context: Optional[Dict[str, Any]] = None) -> ImpactAssessment:
        """Perform comprehensive impact assessment"""
        
        assessment_id = f"impact_{uuid.uuid4().hex[:12]}"
        base_impact = self.impact_rules.get(override_type, ImpactLevel.MEDIUM)
        
        # Calculate financial impact
        financial_risk = self._assess_financial_risk(override_type, target_components, context)
        
        # Calculate system impact
        system_stability_risk = self._assess_system_stability_risk(override_type, target_components)
        data_integrity_risk = self._assess_data_integrity_risk(override_type)
        operational_risk = self._assess_operational_risk(override_type, duration_hours)
        
        # Determine urgency
        urgency = self._determine_urgency(override_type, context)
        
        # Calculate safe duration
        max_safe_duration = self._calculate_max_safe_duration(override_type, base_impact)
        
        # Generate safeguards and monitoring
        safeguards = self._recommend_safeguards(override_type, base_impact)
        monitoring = self._recommend_monitoring(override_type, target_components)
        rollback_plan = self._generate_rollback_plan(override_type, target_components)
        
        return ImpactAssessment(
            assessment_id=assessment_id,
            override_type=override_type,
            impact_level=base_impact,
            estimated_financial_risk=financial_risk["estimated_risk"],
            potential_loss_range=financial_risk["loss_range"],
            affected_accounts=context.get("affected_accounts", []) if context else [],
            affected_trading_volume=context.get("trading_volume", 0.0) if context else 0.0,
            affected_components=target_components,
            system_stability_risk=system_stability_risk,
            data_integrity_risk=data_integrity_risk,
            operational_continuity_risk=operational_risk,
            urgency_level=urgency,
            max_safe_duration=max_safe_duration,
            rollback_complexity=self._assess_rollback_complexity(override_type),
            recommended_safeguards=safeguards,
            monitoring_requirements=monitoring,
            rollback_plan=rollback_plan,
            assessed_by="system",
            assessment_timestamp=datetime.utcnow(),
            confidence_level=0.85
        )
    
    def _assess_financial_risk(self, override_type: OverrideType, 
                              components: List[str], context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Assess potential financial risk"""
        base_risks = {
            OverrideType.FORCE_LEARNING_ON: 50000,
            OverrideType.FORCE_LEARNING_OFF: 10000,
            OverrideType.BYPASS_CIRCUIT_BREAKER: 200000,
            OverrideType.FORCE_QUARANTINE: 5000,
            OverrideType.RELEASE_QUARANTINE: 25000,
            OverrideType.FORCE_ROLLBACK: 100000,
            OverrideType.PREVENT_ROLLBACK: 500000,
            OverrideType.EMERGENCY_STOP: 1000000,
            OverrideType.RESET_SYSTEM: 750000
        }
        
        base_risk = base_risks.get(override_type, 50000)
        
        # Adjust based on context
        if context:
            volume_multiplier = min(context.get("trading_volume", 1000000) / 1000000, 5.0)
            account_multiplier = min(len(context.get("affected_accounts", [])) / 10, 3.0)
            base_risk *= max(volume_multiplier, account_multiplier)
        
        return {
            "estimated_risk": base_risk,
            "loss_range": (base_risk * 0.1, base_risk * 2.0)
        }
    
    def _assess_system_stability_risk(self, override_type: OverrideType, components: List[str]) -> float:
        """Assess system stability risk"""
        risk_mapping = {
            OverrideType.FORCE_LEARNING_ON: 0.3,
            OverrideType.FORCE_LEARNING_OFF: 0.1,
            OverrideType.BYPASS_CIRCUIT_BREAKER: 0.8,
            OverrideType.FORCE_QUARANTINE: 0.1,
            OverrideType.RELEASE_QUARANTINE: 0.4,
            OverrideType.FORCE_ROLLBACK: 0.6,
            OverrideType.PREVENT_ROLLBACK: 0.9,
            OverrideType.EMERGENCY_STOP: 0.2,  # Low risk - safe operation
            OverrideType.RESET_SYSTEM: 0.7
        }
        
        base_risk = risk_mapping.get(override_type, 0.5)
        
        # Adjust based on number of components  
        component_factor = 1.0 + (len(components) / 10)  # Less aggressive scaling
        
        return min(base_risk * component_factor, 1.0)
    
    def _assess_data_integrity_risk(self, override_type: OverrideType) -> float:
        """Assess data integrity risk"""
        risk_mapping = {
            OverrideType.FORCE_LEARNING_ON: 0.4,
            OverrideType.FORCE_LEARNING_OFF: 0.1,
            OverrideType.BYPASS_CIRCUIT_BREAKER: 0.9,
            OverrideType.FORCE_QUARANTINE: 0.1,
            OverrideType.RELEASE_QUARANTINE: 0.6,
            OverrideType.FORCE_ROLLBACK: 0.3,
            OverrideType.PREVENT_ROLLBACK: 0.8,
            OverrideType.EMERGENCY_STOP: 0.0,
            OverrideType.RESET_SYSTEM: 0.5
        }
        
        return risk_mapping.get(override_type, 0.5)
    
    def _assess_operational_risk(self, override_type: OverrideType, duration_hours: float) -> float:
        """Assess operational continuity risk"""
        base_risk = 0.3 if override_type in [
            OverrideType.EMERGENCY_STOP, OverrideType.RESET_SYSTEM
        ] else 0.1
        
        # Risk increases with duration
        duration_factor = min(duration_hours / 24, 2.0)
        
        return min(base_risk * duration_factor, 1.0)
    
    def _determine_urgency(self, override_type: OverrideType, context: Optional[Dict[str, Any]]) -> str:
        """Determine urgency level"""
        urgent_types = [OverrideType.EMERGENCY_STOP, OverrideType.PREVENT_ROLLBACK]
        
        if override_type in urgent_types:
            return "critical"
        elif context and context.get("market_volatility", 0) > 0.8:
            return "high"
        elif override_type in [OverrideType.BYPASS_CIRCUIT_BREAKER, OverrideType.FORCE_ROLLBACK]:
            return "medium"
        else:
            return "low"
    
    def _calculate_max_safe_duration(self, override_type: OverrideType, impact_level: ImpactLevel) -> timedelta:
        """Calculate maximum safe duration"""
        base_durations = {
            ImpactLevel.LOW: timedelta(hours=24),
            ImpactLevel.MEDIUM: timedelta(hours=12),
            ImpactLevel.HIGH: timedelta(hours=4),
            ImpactLevel.CRITICAL: timedelta(hours=1)
        }
        
        return base_durations.get(impact_level, timedelta(hours=8))
    
    def _recommend_safeguards(self, override_type: OverrideType, impact_level: ImpactLevel) -> List[str]:
        """Recommend safeguards for override operation"""
        safeguards = ["Continuous monitoring enabled", "Automated alerts configured"]
        
        if impact_level in [ImpactLevel.HIGH, ImpactLevel.CRITICAL]:
            safeguards.extend([
                "Manual monitoring required every 30 minutes",
                "Immediate rollback capability verified",
                "Senior staff notification sent"
            ])
        
        if override_type == OverrideType.BYPASS_CIRCUIT_BREAKER:
            safeguards.append("Alternative safety mechanisms activated")
        
        return safeguards
    
    def _recommend_monitoring(self, override_type: OverrideType, components: List[str]) -> List[str]:
        """Recommend monitoring requirements"""
        monitoring = [
            "System performance metrics",
            "Trading performance indicators",
            "Error rate monitoring"
        ]
        
        if "learning_engine" in components:
            monitoring.append("Learning accuracy metrics")
        
        if "circuit_breaker" in components:
            monitoring.append("Circuit breaker state monitoring")
        
        return monitoring
    
    def _generate_rollback_plan(self, override_type: OverrideType, components: List[str]) -> str:
        """Generate rollback plan"""
        plans = {
            OverrideType.FORCE_LEARNING_ON: "Disable learning, restore circuit breaker control",
            OverrideType.FORCE_LEARNING_OFF: "Re-enable learning based on circuit breaker state",
            OverrideType.BYPASS_CIRCUIT_BREAKER: "Re-enable circuit breaker, validate system state",
            OverrideType.FORCE_QUARANTINE: "Release quarantine, restore data access",
            OverrideType.RELEASE_QUARANTINE: "Re-quarantine data if issues detected",
            OverrideType.FORCE_ROLLBACK: "Restore from backup if rollback fails",
            OverrideType.PREVENT_ROLLBACK: "Allow rollback, monitor for issues",
            OverrideType.EMERGENCY_STOP: "Restart system with validated configuration",
            OverrideType.RESET_SYSTEM: "Restore from last known good state"
        }
        
        return plans.get(override_type, "Standard system restoration procedure")
    
    def _assess_rollback_complexity(self, override_type: OverrideType) -> str:
        """Assess rollback complexity"""
        complex_types = [OverrideType.RESET_SYSTEM, OverrideType.FORCE_ROLLBACK]
        moderate_types = [OverrideType.BYPASS_CIRCUIT_BREAKER, OverrideType.PREVENT_ROLLBACK]
        
        if override_type in complex_types:
            return "complex"
        elif override_type in moderate_types:
            return "moderate"
        else:
            return "simple"


class AuditLogger:
    """Manages audit logging for override operations"""
    
    def __init__(self, log_storage_path: str = "./override_audit_logs"):
        self.log_storage_path = Path(log_storage_path)
        self.log_storage_path.mkdir(parents=True, exist_ok=True)
        
        # Current log file
        self.current_log_file = self.log_storage_path / f"audit_log_{datetime.utcnow().strftime('%Y%m%d')}.json"
        
        # In-memory log cache
        self.log_cache: List[AuditLogEntry] = []
        self.max_cache_size = 1000
    
    def log_event(self, event_type: str, user_id: str, session_id: str,
                  component_affected: str, action_taken: str,
                  parameters: Dict[str, Any],
                  success: bool,
                  system_state_before: Dict[str, Any],
                  system_state_after: Dict[str, Any],
                  override_request_id: Optional[str] = None,
                  error_message: Optional[str] = None,
                  ip_address: str = "unknown",
                  user_agent: str = "unknown",
                  authentication_method: str = "password") -> str:
        """Log an audit event"""
        
        log_id = f"audit_{uuid.uuid4().hex[:16]}"
        
        log_entry = AuditLogEntry(
            log_id=log_id,
            timestamp=datetime.utcnow(),
            event_type=event_type,
            user_id=user_id,
            session_id=session_id,
            override_request_id=override_request_id,
            component_affected=component_affected,
            action_taken=action_taken,
            parameters=parameters,
            success=success,
            error_message=error_message,
            system_state_before=system_state_before,
            system_state_after=system_state_after,
            ip_address=ip_address,
            user_agent=user_agent,
            authentication_method=authentication_method,
            authorization_checks=self._get_authorization_checks(user_id, session_id)
        )
        
        # Add to cache
        self.log_cache.append(log_entry)
        
        # Write to persistent storage
        self._write_log_entry(log_entry)
        
        # Manage cache size
        if len(self.log_cache) > self.max_cache_size:
            self.log_cache = self.log_cache[-self.max_cache_size:]
        
        return log_id
    
    def get_audit_logs(self, start_date: Optional[datetime] = None,
                      end_date: Optional[datetime] = None,
                      user_id: Optional[str] = None,
                      event_type: Optional[str] = None,
                      limit: int = 100) -> List[AuditLogEntry]:
        """Retrieve audit logs with filtering"""
        
        # Filter cache first for recent entries
        filtered_logs = []
        
        for log_entry in reversed(self.log_cache):  # Most recent first
            if self._matches_filters(log_entry, start_date, end_date, user_id, event_type):
                filtered_logs.append(log_entry)
                if len(filtered_logs) >= limit:
                    break
        
        return filtered_logs
    
    def get_user_activity(self, user_id: str, hours_back: int = 24) -> List[AuditLogEntry]:
        """Get user activity for specified time period"""
        start_time = datetime.utcnow() - timedelta(hours=hours_back)
        return self.get_audit_logs(start_date=start_time, user_id=user_id)
    
    def get_system_events(self, component: str, hours_back: int = 24) -> List[AuditLogEntry]:
        """Get system events for specific component"""
        start_time = datetime.utcnow() - timedelta(hours=hours_back)
        
        return [log for log in self.log_cache 
                if (log.component_affected == component and 
                    log.timestamp >= start_time)]
    
    def _write_log_entry(self, log_entry: AuditLogEntry) -> None:
        """Write log entry to persistent storage"""
        try:
            log_data = asdict(log_entry)
            
            # Append to current log file
            with open(self.current_log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_data, default=str) + '\n')
                
        except Exception as e:
            # In case of logging failure, at least log to system logger
            logger.error(f"Failed to write audit log entry: {e}")
    
    def _matches_filters(self, log_entry: AuditLogEntry,
                        start_date: Optional[datetime],
                        end_date: Optional[datetime],
                        user_id: Optional[str],
                        event_type: Optional[str]) -> bool:
        """Check if log entry matches filters"""
        
        if start_date and log_entry.timestamp < start_date:
            return False
        
        if end_date and log_entry.timestamp > end_date:
            return False
        
        if user_id and log_entry.user_id != user_id:
            return False
        
        if event_type and log_entry.event_type != event_type:
            return False
        
        return True
    
    def _get_authorization_checks(self, user_id: str, session_id: str) -> List[str]:
        """Get authorization checks performed"""
        return [
            "session_validity_check",
            "user_permissions_check",
            "role_authorization_check"
        ]


class ManualOverrideSystem:
    """Main manual override system coordinating all components"""
    
    def __init__(self, storage_path: str = "./manual_overrides"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.authorization_manager = AuthorizationManager()
        self.impact_assessor = ImpactAssessor()
        self.audit_logger = AuditLogger(str(self.storage_path / "audit_logs"))
        
        # Request tracking
        self.active_overrides: Dict[str, OverrideRequest] = {}
        self.pending_requests: Dict[str, OverrideRequest] = {}
        self.completed_requests: Dict[str, OverrideRequest] = {}
        
        # System state tracking
        self.system_state = {
            "learning_enabled": True,
            "circuit_breaker_active": True,
            "quarantine_active": False,
            "emergency_mode": False
        }
        
        # Load existing requests
        self._load_existing_requests()
    
    def authenticate_user(self, user_id: str, password: str, 
                         ip_address: str = "unknown", user_agent: str = "unknown") -> Optional[str]:
        """Authenticate user and return session ID"""
        authorization = self.authorization_manager.authenticate_user(user_id, password)
        
        if authorization:
            # Log authentication
            self.audit_logger.log_event(
                event_type="user_authentication",
                user_id=user_id,
                session_id=authorization.session_id,
                component_affected="authentication_system",
                action_taken="user_login",
                parameters={"authentication_method": "password"},
                success=True,
                system_state_before={},
                system_state_after={"session_created": authorization.session_id},
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            return authorization.session_id
        else:
            # Log failed authentication
            self.audit_logger.log_event(
                event_type="authentication_failure",
                user_id=user_id,
                session_id="none",
                component_affected="authentication_system",
                action_taken="failed_login",
                parameters={"reason": "invalid_credentials"},
                success=False,
                system_state_before={},
                system_state_after={},
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            return None
    
    def request_override(self, session_id: str, override_type: OverrideType,
                        target_components: List[str], duration_hours: float,
                        business_reason: str, technical_reason: str,
                        immediate_execution: bool = False,
                        context: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Request manual override"""
        
        try:
            # Verify authorization
            if not self.authorization_manager.check_authorization(session_id, override_type):
                self._log_unauthorized_attempt(session_id, override_type)
                return None
            
            authorization = self.authorization_manager.active_sessions[session_id]
            
            # Generate request ID
            request_id = f"override_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
            
            # Create justification
            justification = OverrideJustification(
                justification_id=f"just_{uuid.uuid4().hex[:12]}",
                override_type=override_type,
                business_reason=business_reason,
                technical_reason=technical_reason,
                market_conditions=context.get("market_conditions", "normal") if context else "normal",
                system_conditions=context.get("system_conditions", "stable") if context else "stable",
                alternative_options_considered=context.get("alternatives_considered", []) if context else [],
                why_alternatives_insufficient=context.get("alternatives_insufficient", "") if context else "",
                risks_acknowledged=[],
                mitigation_measures=[],
                monitoring_plan="Standard monitoring protocol",
                success_criteria="Override executed successfully without adverse effects",
                submitted_by=authorization.user_id,
                submission_timestamp=datetime.utcnow(),
                required_approvals=authorization.approval_required_from,
                received_approvals=[],
                approval_complete=not authorization.requires_approval
            )
            
            # Perform impact assessment
            impact_assessment = self.impact_assessor.assess_impact(
                override_type, target_components, duration_hours, context
            )
            
            # Create override request
            override_request = OverrideRequest(
                request_id=request_id,
                override_type=override_type,
                status=OverrideStatus.PENDING if authorization.requires_approval else OverrideStatus.APPROVED,
                requested_by=authorization.user_id,
                request_timestamp=datetime.utcnow(),
                target_components=target_components,
                duration_hours=min(duration_hours, authorization.max_duration_hours),
                immediate_execution=immediate_execution,
                authorization=authorization,
                justification=justification,
                impact_assessment=impact_assessment
            )
            
            # Store request
            if authorization.requires_approval and not (immediate_execution and authorization.authorization_level == AuthorizationLevel.EMERGENCY):
                # Emergency users can bypass approval for immediate execution
                self.pending_requests[request_id] = override_request
            else:
                # Auto-approve for lower privilege levels or emergency immediate execution
                override_request.approved_by = "system" if not authorization.requires_approval else authorization.user_id
                override_request.approval_timestamp = datetime.utcnow()
                if immediate_execution:
                    self._execute_override(override_request)
                    # Store in active overrides after execution
                    self.active_overrides[request_id] = override_request
                else:
                    self.active_overrides[request_id] = override_request
            
            # Log request
            self.audit_logger.log_event(
                event_type="override_request_created",
                user_id=authorization.user_id,
                session_id=session_id,
                component_affected="override_system",
                action_taken="create_override_request",
                parameters={
                    "override_type": override_type.value,
                    "target_components": target_components,
                    "duration_hours": duration_hours,
                    "immediate_execution": immediate_execution
                },
                success=True,
                system_state_before=self.system_state.copy(),
                system_state_after=self.system_state.copy(),
                override_request_id=request_id
            )
            
            return request_id
            
        except Exception as e:
            logger.error(f"Failed to create override request: {e}")
            return None
    
    def approve_override(self, session_id: str, request_id: str, 
                        approval_notes: str = "") -> bool:
        """Approve pending override request"""
        
        try:
            if request_id not in self.pending_requests:
                return False
            
            # Check authorization
            authorization = self.authorization_manager.active_sessions.get(session_id)
            if not authorization:
                return False
            
            override_request = self.pending_requests[request_id]
            
            # Check if user can approve this request
            if authorization.user_role not in override_request.justification.required_approvals:
                return False
            
            # Add approval
            approval = {
                "approver_id": authorization.user_id,
                "approver_role": authorization.user_role,
                "approval_timestamp": datetime.utcnow().isoformat(),
                "approval_notes": approval_notes
            }
            
            override_request.justification.received_approvals.append(approval)
            
            # Check if at least one required approval received
            received_roles = [a["approver_role"] for a in override_request.justification.received_approvals]
            if any(role in received_roles for role in override_request.justification.required_approvals):
                override_request.justification.approval_complete = True
                override_request.status = OverrideStatus.APPROVED
                override_request.approved_by = authorization.user_id
                override_request.approval_timestamp = datetime.utcnow()
                
                # Move to active overrides
                del self.pending_requests[request_id]
                
                if override_request.immediate_execution:
                    self._execute_override(override_request)
                    # Store in active overrides after execution
                    self.active_overrides[request_id] = override_request
                else:
                    self.active_overrides[request_id] = override_request
            
            # Log approval
            self.audit_logger.log_event(
                event_type="override_approval",
                user_id=authorization.user_id,
                session_id=session_id,
                component_affected="override_system",
                action_taken="approve_override_request",
                parameters={
                    "request_id": request_id,
                    "approval_notes": approval_notes
                },
                success=True,
                system_state_before=self.system_state.copy(),
                system_state_after=self.system_state.copy(),
                override_request_id=request_id
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to approve override request {request_id}: {e}")
            return False
    
    def execute_override(self, session_id: str, request_id: str) -> bool:
        """Execute approved override"""
        
        try:
            if request_id not in self.active_overrides:
                return False
            
            # Check authorization
            authorization = self.authorization_manager.active_sessions.get(session_id)
            if not authorization:
                return False
            
            override_request = self.active_overrides[request_id]
            
            # Execute the override
            success = self._execute_override(override_request)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to execute override {request_id}: {e}")
            return False
    
    def revoke_override(self, session_id: str, request_id: str, reason: str) -> bool:
        """Revoke active override"""
        
        try:
            override_request = None
            location = None
            
            if request_id in self.active_overrides:
                override_request = self.active_overrides[request_id]
                location = "active"
            elif request_id in self.pending_requests:
                override_request = self.pending_requests[request_id]
                location = "pending"
            
            if not override_request:
                return False
            
            # Check authorization
            authorization = self.authorization_manager.active_sessions.get(session_id)
            if not authorization:
                return False
            
            # Check if user can revoke (original requester, approver, or admin)
            can_revoke = (authorization.user_id == override_request.requested_by or
                         authorization.authorization_level in [AuthorizationLevel.ADMIN, AuthorizationLevel.EMERGENCY])
            
            if not can_revoke:
                return False
            
            # Revoke the override
            if override_request.status == OverrideStatus.ACTIVE:
                # Reverse the override effects
                self._reverse_override_effects(override_request)
            
            override_request.status = OverrideStatus.REVOKED
            
            # Move to completed
            if location == "active":
                del self.active_overrides[request_id]
            elif location == "pending":
                del self.pending_requests[request_id]
            
            self.completed_requests[request_id] = override_request
            
            # Log revocation
            self.audit_logger.log_event(
                event_type="override_revoked",
                user_id=authorization.user_id,
                session_id=session_id,
                component_affected="override_system",
                action_taken="revoke_override",
                parameters={
                    "request_id": request_id,
                    "revocation_reason": reason
                },
                success=True,
                system_state_before=self.system_state.copy(),
                system_state_after=self.system_state.copy(),
                override_request_id=request_id
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to revoke override {request_id}: {e}")
            return False
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        
        return {
            "system_state": self.system_state.copy(),
            "active_overrides": len(self.active_overrides),
            "pending_requests": len(self.pending_requests),
            "active_sessions": len(self.authorization_manager.active_sessions),
            "recent_activity": len(self.audit_logger.log_cache),
            "override_summary": self._get_override_summary(),
            "system_health": self._assess_system_health()
        }
    
    def get_override_dashboard_data(self, session_id: str) -> Dict[str, Any]:
        """Get dashboard data for override monitoring"""
        
        # Check authorization
        authorization = self.authorization_manager.active_sessions.get(session_id)
        if not authorization:
            return {}
        
        # Update session activity
        self.authorization_manager.update_session_activity(session_id)
        
        return {
            "user_info": {
                "user_id": authorization.user_id,
                "role": authorization.user_role,
                "permissions": [p.value for p in authorization.permissions],
                "session_valid_until": (authorization.last_activity + timedelta(hours=4)).isoformat()
            },
            "active_overrides": self._format_overrides_for_dashboard(self.active_overrides),
            "pending_requests": self._format_overrides_for_dashboard(self.pending_requests),
            "recent_activity": self.audit_logger.get_user_activity(authorization.user_id, hours_back=24),
            "system_alerts": self._get_system_alerts(),
            "quick_actions": self._get_available_quick_actions(authorization)
        }
    
    def _execute_override(self, override_request: OverrideRequest) -> bool:
        """Execute the actual override operation"""
        
        try:
            system_state_before = self.system_state.copy()
            
            # Execute based on override type
            if override_request.override_type == OverrideType.FORCE_LEARNING_ON:
                self.system_state["learning_enabled"] = True
                
            elif override_request.override_type == OverrideType.FORCE_LEARNING_OFF:
                self.system_state["learning_enabled"] = False
                
            elif override_request.override_type == OverrideType.BYPASS_CIRCUIT_BREAKER:
                self.system_state["circuit_breaker_active"] = False
                
            elif override_request.override_type == OverrideType.FORCE_QUARANTINE:
                self.system_state["quarantine_active"] = True
                
            elif override_request.override_type == OverrideType.RELEASE_QUARANTINE:
                self.system_state["quarantine_active"] = False
                
            elif override_request.override_type == OverrideType.EMERGENCY_STOP:
                self.system_state["emergency_mode"] = True
                self.system_state["learning_enabled"] = False
                
            elif override_request.override_type == OverrideType.RESET_SYSTEM:
                self.system_state = {
                    "learning_enabled": True,
                    "circuit_breaker_active": True,
                    "quarantine_active": False,
                    "emergency_mode": False
                }
            
            # Update request status
            override_request.status = OverrideStatus.ACTIVE
            override_request.executed_by = override_request.requested_by
            override_request.execution_timestamp = datetime.utcnow()
            override_request.expiry_timestamp = datetime.utcnow() + timedelta(hours=override_request.duration_hours)
            override_request.execution_successful = True
            
            # Log execution
            self.audit_logger.log_event(
                event_type="override_executed",
                user_id=override_request.requested_by,
                session_id=override_request.authorization.session_id,
                component_affected="learning_system",
                action_taken=f"execute_{override_request.override_type.value}",
                parameters={
                    "target_components": override_request.target_components,
                    "duration_hours": override_request.duration_hours
                },
                success=True,
                system_state_before=system_state_before,
                system_state_after=self.system_state.copy(),
                override_request_id=override_request.request_id
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute override {override_request.request_id}: {e}")
            override_request.execution_successful = False
            return False
    
    def _reverse_override_effects(self, override_request: OverrideRequest) -> None:
        """Reverse the effects of an override"""
        
        # This is a simplified reversal - in production would be more sophisticated
        if override_request.override_type == OverrideType.FORCE_LEARNING_ON:
            self.system_state["learning_enabled"] = False
        elif override_request.override_type == OverrideType.FORCE_LEARNING_OFF:
            self.system_state["learning_enabled"] = True
        elif override_request.override_type == OverrideType.BYPASS_CIRCUIT_BREAKER:
            self.system_state["circuit_breaker_active"] = True
        # Additional reversal logic would go here
    
    def _log_unauthorized_attempt(self, session_id: str, override_type: OverrideType) -> None:
        """Log unauthorized override attempt"""
        authorization = self.authorization_manager.active_sessions.get(session_id, None)
        user_id = authorization.user_id if authorization else "unknown"
        
        self.audit_logger.log_event(
            event_type="unauthorized_override_attempt",
            user_id=user_id,
            session_id=session_id,
            component_affected="override_system",
            action_taken=f"attempt_{override_type.value}",
            parameters={"attempted_override": override_type.value},
            success=False,
            system_state_before=self.system_state.copy(),
            system_state_after=self.system_state.copy(),
            error_message="Insufficient authorization"
        )
    
    def _get_override_summary(self) -> Dict[str, Any]:
        """Get summary of override operations"""
        all_overrides = list(self.active_overrides.values()) + list(self.completed_requests.values())
        
        return {
            "total_overrides_today": len([o for o in all_overrides 
                                       if o.request_timestamp.date() == datetime.utcnow().date()]),
            "active_override_types": [o.override_type.value for o in self.active_overrides.values()],
            "most_common_override": self._get_most_common_override_type(all_overrides),
            "average_duration": self._calculate_average_duration(all_overrides)
        }
    
    def _assess_system_health(self) -> Dict[str, Any]:
        """Assess overall system health"""
        
        health_score = 1.0
        warnings = []
        
        # Check for emergency mode
        if self.system_state["emergency_mode"]:
            health_score -= 0.5
            warnings.append("System in emergency mode")
        
        # Check for bypassed circuit breaker
        if not self.system_state["circuit_breaker_active"]:
            health_score -= 0.3
            warnings.append("Circuit breaker bypassed")
        
        # Check for too many active overrides
        if len(self.active_overrides) > 3:
            health_score -= 0.2
            warnings.append("Multiple active overrides")
        
        return {
            "health_score": max(0.0, health_score),
            "warnings": warnings,
            "last_assessment": datetime.utcnow().isoformat()
        }
    
    def _format_overrides_for_dashboard(self, overrides: Dict[str, OverrideRequest]) -> List[Dict[str, Any]]:
        """Format overrides for dashboard display"""
        
        formatted = []
        for override_request in overrides.values():
            formatted.append({
                "request_id": override_request.request_id,
                "override_type": override_request.override_type.value,
                "status": override_request.status.value,
                "requested_by": override_request.requested_by,
                "request_time": override_request.request_timestamp.isoformat(),
                "duration_hours": override_request.duration_hours,
                "impact_level": override_request.impact_assessment.impact_level.value,
                "target_components": override_request.target_components,
                "expires_at": override_request.expiry_timestamp.isoformat() if override_request.expiry_timestamp else None
            })
        
        return sorted(formatted, key=lambda x: x["request_time"], reverse=True)
    
    def _get_system_alerts(self) -> List[Dict[str, Any]]:
        """Get current system alerts"""
        alerts = []
        
        # Check for expired overrides
        for request_id, override_request in self.active_overrides.items():
            if override_request.is_expired():
                alerts.append({
                    "type": "expired_override",
                    "message": f"Override {request_id} has expired",
                    "severity": "medium",
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        # Check for system state issues
        if not self.system_state["circuit_breaker_active"]:
            alerts.append({
                "type": "circuit_breaker_bypass",
                "message": "Circuit breaker is bypassed - system safety reduced",
                "severity": "high",
                "timestamp": datetime.utcnow().isoformat()
            })
        
        return alerts
    
    def _get_available_quick_actions(self, authorization: OverrideAuthorization) -> List[Dict[str, Any]]:
        """Get available quick actions for user"""
        
        actions = []
        
        for permission in authorization.permissions:
            actions.append({
                "override_type": permission.value,
                "display_name": permission.value.replace("_", " ").title(),
                "impact_level": self.impact_assessor.impact_rules.get(permission, ImpactLevel.MEDIUM).value,
                "requires_approval": authorization.requires_approval
            })
        
        return actions
    
    def _get_most_common_override_type(self, overrides: List[OverrideRequest]) -> str:
        """Get most commonly used override type"""
        if not overrides:
            return "none"
        
        type_counts = {}
        for override in overrides:
            override_type = override.override_type.value
            type_counts[override_type] = type_counts.get(override_type, 0) + 1
        
        return max(type_counts, key=type_counts.get)
    
    def _calculate_average_duration(self, overrides: List[OverrideRequest]) -> float:
        """Calculate average override duration"""
        if not overrides:
            return 0.0
        
        durations = [o.duration_hours for o in overrides]
        return sum(durations) / len(durations)
    
    def _load_existing_requests(self) -> None:
        """Load existing override requests from storage"""
        # Simplified implementation - in production would load from persistent storage
        pass
    
    def _store_request(self, override_request: OverrideRequest) -> None:
        """Store override request to persistent storage"""
        # Simplified implementation - in production would save to database
        pass