"""
Error Alerting and Logging System
Story 8.9 - Task 5: Create alerting and logging
"""
import asyncio
import logging
import json
import time
import functools
from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict, field
from enum import Enum
import uuid
import traceback
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertChannel(Enum):
    """Alert delivery channels"""
    LOG = "log"
    SLACK = "slack"
    PAGERDUTY = "pagerduty"
    EMAIL = "email"
    WEBHOOK = "webhook"


@dataclass
class ErrorContext:
    """Comprehensive error context"""
    error_id: str
    timestamp: datetime
    error_type: str
    error_message: str
    service_name: str
    operation: str
    account_id: Optional[str] = None
    request_id: Optional[str] = None
    correlation_id: Optional[str] = None
    stack_trace: Optional[str] = None
    system_metrics: Dict[str, Any] = field(default_factory=dict)
    user_context: Dict[str, Any] = field(default_factory=dict)
    recovery_suggestions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            'error_id': self.error_id,
            'timestamp': self.timestamp.isoformat(),
            'error_type': self.error_type,
            'error_message': self.error_message,
            'service_name': self.service_name,
            'operation': self.operation,
            'account_id': self.account_id,
            'request_id': self.request_id,
            'correlation_id': self.correlation_id,
            'stack_trace': self.stack_trace,
            'system_metrics': self.system_metrics,
            'user_context': self.user_context,
            'recovery_suggestions': self.recovery_suggestions
        }


@dataclass
class Alert:
    """Alert message"""
    alert_id: str
    timestamp: datetime
    severity: AlertSeverity
    title: str
    message: str
    service: str
    error_context: Optional[ErrorContext] = None
    channels: List[AlertChannel] = field(default_factory=list)
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            'alert_id': self.alert_id,
            'timestamp': self.timestamp.isoformat(),
            'severity': self.severity.value,
            'title': self.title,
            'message': self.message,
            'service': self.service,
            'error_context': self.error_context.to_dict() if self.error_context else None,
            'channels': [c.value for c in self.channels],
            'acknowledged': self.acknowledged,
            'acknowledged_by': self.acknowledged_by,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            'resolved': self.resolved,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None
        }


class StructuredLogger:
    """Enhanced structured logging for OANDA operations"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.error_aggregation: Dict[str, List[ErrorContext]] = {}
        self.log_entries: List[Dict[str, Any]] = []
        self.max_log_entries = 10000
        
    def log_with_context(self,
                        level: int,
                        message: str,
                        operation: str,
                        service_name: str = "oanda",
                        **context) -> str:
        """
        Log message with structured context
        
        Args:
            level: Logging level
            message: Log message
            operation: Operation being performed
            service_name: Name of service
            **context: Additional context data
            
        Returns:
            Log entry ID
        """
        entry_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc)
        
        # Create structured log entry
        log_entry = {
            'entry_id': entry_id,
            'timestamp': timestamp.isoformat(),
            'level': logging.getLevelName(level),
            'message': message,
            'service': service_name,
            'operation': operation,
            'context': context
        }
        
        # Store log entry
        self.log_entries.append(log_entry)
        
        # Maintain size limit
        if len(self.log_entries) > self.max_log_entries:
            self.log_entries = self.log_entries[-self.max_log_entries:]
            
        # Log to standard logger
        self.logger.log(level, f"[{operation}] {message}", extra={
            'entry_id': entry_id,
            'service': service_name,
            'context': context
        })
        
        return entry_id
        
    def log_error_with_context(self,
                              error: Exception,
                              operation: str,
                              service_name: str = "oanda",
                              **context) -> ErrorContext:
        """
        Log error with comprehensive context
        
        Args:
            error: Exception that occurred
            operation: Operation that failed
            service_name: Service name
            **context: Additional context
            
        Returns:
            ErrorContext object
        """
        error_id = str(uuid.uuid4())
        
        # Create error context
        error_context = ErrorContext(
            error_id=error_id,
            timestamp=datetime.now(timezone.utc),
            error_type=type(error).__name__,
            error_message=str(error),
            service_name=service_name,
            operation=operation,
            account_id=context.get('account_id'),
            request_id=context.get('request_id'),
            correlation_id=context.get('correlation_id'),
            stack_trace=traceback.format_exc(),
            system_metrics=self._collect_system_metrics(),
            user_context=context,
            recovery_suggestions=self._generate_recovery_suggestions(error)
        )
        
        # Aggregate similar errors
        error_key = f"{error_context.error_type}:{error_context.operation}"
        if error_key not in self.error_aggregation:
            self.error_aggregation[error_key] = []
        self.error_aggregation[error_key].append(error_context)
        
        # Log error
        self.log_with_context(
            logging.ERROR,
            f"Error in {operation}: {error}",
            operation,
            service_name,
            error_id=error_id,
            error_type=type(error).__name__,
            **context
        )
        
        return error_context
        
    def _collect_system_metrics(self) -> Dict[str, Any]:
        """Collect system metrics for error context"""
        return {
            'memory_usage_mb': self._get_memory_usage(),
            'cpu_count': self._get_cpu_count(),
            'python_version': sys.version,
            'process_uptime': time.perf_counter()
        }
        
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0.0
            
    def _get_cpu_count(self) -> int:
        """Get CPU count"""
        try:
            import psutil
            return psutil.cpu_count()
        except ImportError:
            import os
            return os.cpu_count() or 1
            
    def _generate_recovery_suggestions(self, error: Exception) -> List[str]:
        """Generate recovery suggestions based on error type"""
        error_type = type(error).__name__
        error_message = str(error).lower()
        
        suggestions = []
        
        if 'connection' in error_message or 'timeout' in error_message:
            suggestions.extend([
                "Check network connectivity",
                "Verify OANDA API endpoints are accessible",
                "Consider increasing timeout values",
                "Check firewall and proxy settings"
            ])
            
        elif 'authentication' in error_message or 'unauthorized' in error_message:
            suggestions.extend([
                "Verify API credentials are valid",
                "Check if API key has expired",
                "Ensure account has proper permissions",
                "Refresh authentication tokens"
            ])
            
        elif 'rate limit' in error_message or '429' in error_message:
            suggestions.extend([
                "Reduce request frequency",
                "Implement longer delays between requests",
                "Use cached data where possible",
                "Consider upgrading API tier if available"
            ])
            
        elif 'server error' in error_message or '5' in error_type:
            suggestions.extend([
                "Wait and retry the operation",
                "Check OANDA system status",
                "Use cached data if available",
                "Consider graceful degradation"
            ])
            
        if not suggestions:
            suggestions.append("Review error details and consult documentation")
            
        return suggestions
        
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get error summary for specified time period"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        recent_errors = []
        for error_list in self.error_aggregation.values():
            recent_errors.extend([
                e for e in error_list if e.timestamp >= cutoff_time
            ])
            
        # Group by error type
        error_types = {}
        for error in recent_errors:
            error_type = error.error_type
            if error_type not in error_types:
                error_types[error_type] = 0
            error_types[error_type] += 1
            
        return {
            'period_hours': hours,
            'total_errors': len(recent_errors),
            'unique_error_types': len(error_types),
            'error_breakdown': error_types,
            'recent_errors': [e.to_dict() for e in recent_errors[-20:]]  # Last 20 errors
        }


class AlertManager:
    """Manages alerts and notifications"""
    
    def __init__(self):
        self.alerts: Dict[str, Alert] = {}
        self.alert_channels: Dict[AlertChannel, Callable] = {}
        self.alert_rules: List[Dict[str, Any]] = []
        self.alert_history: List[Alert] = []
        self.suppression_rules: Dict[str, datetime] = {}
        
        # Default alert rules
        self._setup_default_alert_rules()
        
    def _setup_default_alert_rules(self):
        """Setup default alerting rules"""
        self.alert_rules = [
            {
                'name': 'circuit_breaker_open',
                'condition': lambda ctx: 'circuit' in ctx.get('operation', '').lower() and 'open' in ctx.get('error_message', '').lower(),
                'severity': AlertSeverity.CRITICAL,
                'channels': [AlertChannel.LOG, AlertChannel.PAGERDUTY],
                'suppress_minutes': 10
            },
            {
                'name': 'authentication_failure',
                'condition': lambda ctx: 'auth' in ctx.get('error_type', '').lower(),
                'severity': AlertSeverity.CRITICAL,
                'channels': [AlertChannel.LOG, AlertChannel.SLACK],
                'suppress_minutes': 30
            },
            {
                'name': 'rate_limit_exceeded',
                'condition': lambda ctx: 'rate limit' in ctx.get('error_message', '').lower(),
                'severity': AlertSeverity.WARNING,
                'channels': [AlertChannel.LOG],
                'suppress_minutes': 5
            },
            {
                'name': 'high_error_rate',
                'condition': lambda ctx: ctx.get('error_count', 0) > 10,
                'severity': AlertSeverity.ERROR,
                'channels': [AlertChannel.LOG, AlertChannel.SLACK],
                'suppress_minutes': 15
            }
        ]
        
    async def send_alert(self,
                        severity: AlertSeverity,
                        title: str,
                        message: str,
                        service: str,
                        error_context: Optional[ErrorContext] = None,
                        channels: Optional[List[AlertChannel]] = None) -> str:
        """
        Send alert through specified channels
        
        Args:
            severity: Alert severity
            title: Alert title
            message: Alert message
            service: Service name
            error_context: Optional error context
            channels: Optional list of channels (uses default if None)
            
        Returns:
            Alert ID
        """
        alert_id = str(uuid.uuid4())
        
        # Check suppression rules
        suppression_key = f"{service}:{title}"
        if suppression_key in self.suppression_rules:
            if datetime.now(timezone.utc) < self.suppression_rules[suppression_key]:
                logger.debug(f"Alert suppressed: {title}")
                return alert_id
                
        # Create alert
        alert = Alert(
            alert_id=alert_id,
            timestamp=datetime.now(timezone.utc),
            severity=severity,
            title=title,
            message=message,
            service=service,
            error_context=error_context,
            channels=channels or [AlertChannel.LOG]
        )
        
        self.alerts[alert_id] = alert
        self.alert_history.append(alert)
        
        # Send through each channel
        for channel in alert.channels:
            try:
                await self._send_to_channel(alert, channel)
            except Exception as e:
                logger.error(f"Failed to send alert to {channel.value}: {e}")
                
        # Apply suppression if rule exists
        matching_rule = self._find_matching_rule(error_context.to_dict() if error_context else {})
        if matching_rule:
            suppress_until = datetime.now(timezone.utc) + timedelta(minutes=matching_rule['suppress_minutes'])
            self.suppression_rules[suppression_key] = suppress_until
            
        logger.info(f"Alert sent: {title} [{severity.value}]")
        return alert_id
        
    async def _send_to_channel(self, alert: Alert, channel: AlertChannel):
        """Send alert to specific channel"""
        if channel == AlertChannel.LOG:
            await self._send_to_log(alert)
        elif channel == AlertChannel.SLACK:
            await self._send_to_slack(alert)
        elif channel == AlertChannel.PAGERDUTY:
            await self._send_to_pagerduty(alert)
        elif channel == AlertChannel.EMAIL:
            await self._send_to_email(alert)
        elif channel == AlertChannel.WEBHOOK:
            await self._send_to_webhook(alert)
            
    async def _send_to_log(self, alert: Alert):
        """Send alert to log"""
        log_level = {
            AlertSeverity.INFO: logging.INFO,
            AlertSeverity.WARNING: logging.WARNING,
            AlertSeverity.ERROR: logging.ERROR,
            AlertSeverity.CRITICAL: logging.CRITICAL
        }[alert.severity]
        
        logger.log(log_level, f"ALERT [{alert.severity.value.upper()}] {alert.title}: {alert.message}")
        
    async def _send_to_slack(self, alert: Alert):
        """Send alert to Slack (mock implementation)"""
        logger.info(f"[SLACK] Would send alert: {alert.title}")
        
        # Mock Slack webhook
        slack_payload = {
            'text': f"🚨 {alert.title}",
            'attachments': [{
                'color': self._get_slack_color(alert.severity),
                'fields': [
                    {'title': 'Service', 'value': alert.service, 'short': True},
                    {'title': 'Severity', 'value': alert.severity.value.upper(), 'short': True},
                    {'title': 'Message', 'value': alert.message, 'short': False}
                ],
                'timestamp': int(alert.timestamp.timestamp())
            }]
        }
        
        logger.debug(f"Slack payload: {json.dumps(slack_payload, indent=2)}")
        
    async def _send_to_pagerduty(self, alert: Alert):
        """Send alert to PagerDuty (mock implementation)"""
        logger.info(f"[PAGERDUTY] Would send alert: {alert.title}")
        
        # Mock PagerDuty event
        pd_payload = {
            'routing_key': 'mock_routing_key',
            'event_action': 'trigger',
            'dedup_key': f"{alert.service}:{alert.title}",
            'payload': {
                'summary': alert.title,
                'source': alert.service,
                'severity': alert.severity.value,
                'component': 'oanda_integration',
                'group': 'trading_system',
                'custom_details': alert.error_context.to_dict() if alert.error_context else {}
            }
        }
        
        logger.debug(f"PagerDuty payload: {json.dumps(pd_payload, indent=2)}")
        
    async def _send_to_email(self, alert: Alert):
        """Send alert to email (mock implementation)"""
        logger.info(f"[EMAIL] Would send alert: {alert.title}")
        
    async def _send_to_webhook(self, alert: Alert):
        """Send alert to webhook (mock implementation)"""
        logger.info(f"[WEBHOOK] Would send alert: {alert.title}")
        
    def _get_slack_color(self, severity: AlertSeverity) -> str:
        """Get Slack color for severity"""
        colors = {
            AlertSeverity.INFO: 'good',
            AlertSeverity.WARNING: 'warning',
            AlertSeverity.ERROR: 'danger',
            AlertSeverity.CRITICAL: 'danger'
        }
        return colors.get(severity, 'good')
        
    def _find_matching_rule(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find matching alert rule for context"""
        for rule in self.alert_rules:
            try:
                if rule['condition'](context):
                    return rule
            except Exception as e:
                logger.error(f"Error evaluating alert rule {rule['name']}: {e}")
                
        return None
        
    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an alert"""
        if alert_id in self.alerts:
            alert = self.alerts[alert_id]
            alert.acknowledged = True
            alert.acknowledged_by = acknowledged_by
            alert.acknowledged_at = datetime.now(timezone.utc)
            
            logger.info(f"Alert acknowledged: {alert_id} by {acknowledged_by}")
            return True
            
        return False
        
    async def resolve_alert(self, alert_id: str) -> bool:
        """Mark alert as resolved"""
        if alert_id in self.alerts:
            alert = self.alerts[alert_id]
            alert.resolved = True
            alert.resolved_at = datetime.now(timezone.utc)
            
            logger.info(f"Alert resolved: {alert_id}")
            return True
            
        return False
        
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active (unresolved) alerts"""
        return [
            alert.to_dict() for alert in self.alerts.values()
            if not alert.resolved
        ]
        
    def get_alert_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get alert summary for time period"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        recent_alerts = [
            alert for alert in self.alert_history
            if alert.timestamp >= cutoff_time
        ]
        
        # Count by severity
        severity_counts = {}
        for alert in recent_alerts:
            severity = alert.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
        return {
            'period_hours': hours,
            'total_alerts': len(recent_alerts),
            'active_alerts': len(self.get_active_alerts()),
            'severity_breakdown': severity_counts,
            'recent_alerts': [a.to_dict() for a in recent_alerts[-10:]]
        }


class OandaErrorHandler:
    """Comprehensive error handling for OANDA operations"""
    
    def __init__(self):
        self.structured_logger = StructuredLogger("oanda_error_handler")
        self.alert_manager = AlertManager()
        self.error_stats = {
            'total_errors': 0,
            'errors_by_type': {},
            'errors_by_service': {},
            'recovery_attempts': 0,
            'successful_recoveries': 0
        }
        
    async def handle_error(self,
                          error: Exception,
                          operation: str,
                          service_name: str = "oanda_api",
                          account_id: Optional[str] = None,
                          request_id: Optional[str] = None,
                          correlation_id: Optional[str] = None,
                          auto_alert: bool = True) -> ErrorContext:
        """
        Comprehensive error handling
        
        Args:
            error: Exception that occurred
            operation: Operation that failed
            service_name: Service name
            account_id: Optional account ID
            request_id: Optional request ID
            correlation_id: Optional correlation ID
            auto_alert: Whether to automatically send alerts
            
        Returns:
            ErrorContext with full error details
        """
        # Update error statistics
        self.error_stats['total_errors'] += 1
        
        error_type = type(error).__name__
        self.error_stats['errors_by_type'][error_type] = self.error_stats['errors_by_type'].get(error_type, 0) + 1
        self.error_stats['errors_by_service'][service_name] = self.error_stats['errors_by_service'].get(service_name, 0) + 1
        
        # Create error context
        error_context = self.structured_logger.log_error_with_context(
            error, operation, service_name,
            account_id=account_id,
            request_id=request_id,
            correlation_id=correlation_id
        )
        
        # Send alert if enabled
        if auto_alert:
            await self._send_error_alert(error_context)
            
        return error_context
        
    async def _send_error_alert(self, error_context: ErrorContext):
        """Send appropriate alert based on error context"""
        severity = self._determine_alert_severity(error_context)
        
        title = f"{error_context.service_name.upper()} Error: {error_context.operation}"
        message = f"{error_context.error_type}: {error_context.error_message}"
        
        channels = self._determine_alert_channels(severity)
        
        await self.alert_manager.send_alert(
            severity=severity,
            title=title,
            message=message,
            service=error_context.service_name,
            error_context=error_context,
            channels=channels
        )
        
    def _determine_alert_severity(self, error_context: ErrorContext) -> AlertSeverity:
        """Determine alert severity based on error context"""
        error_type = error_context.error_type.lower()
        error_message = error_context.error_message.lower()
        
        # Critical errors
        if any(pattern in error_type for pattern in ['authentication', 'authorization']):
            return AlertSeverity.CRITICAL
            
        if any(pattern in error_message for pattern in ['circuit breaker open', 'emergency stop']):
            return AlertSeverity.CRITICAL
            
        # Error level
        if any(pattern in error_type for pattern in ['connection', 'timeout']):
            return AlertSeverity.ERROR
            
        if any(pattern in error_message for pattern in ['server error', '500', '502', '503']):
            return AlertSeverity.ERROR
            
        # Warning level
        if any(pattern in error_message for pattern in ['rate limit', '429']):
            return AlertSeverity.WARNING
            
        # Default to warning
        return AlertSeverity.WARNING
        
    def _determine_alert_channels(self, severity: AlertSeverity) -> List[AlertChannel]:
        """Determine alert channels based on severity"""
        if severity == AlertSeverity.CRITICAL:
            return [AlertChannel.LOG, AlertChannel.PAGERDUTY, AlertChannel.SLACK]
        elif severity == AlertSeverity.ERROR:
            return [AlertChannel.LOG, AlertChannel.SLACK]
        elif severity == AlertSeverity.WARNING:
            return [AlertChannel.LOG]
        else:
            return [AlertChannel.LOG]
            
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get comprehensive error statistics"""
        return {
            **self.error_stats,
            'alert_summary': self.alert_manager.get_alert_summary(),
            'error_summary': self.structured_logger.get_error_summary()
        }
        
    async def test_alerting_system(self) -> Dict[str, Any]:
        """Test the alerting system"""
        test_results = {}
        
        # Test each alert channel
        for channel in AlertChannel:
            try:
                test_alert = Alert(
                    alert_id=str(uuid.uuid4()),
                    timestamp=datetime.now(timezone.utc),
                    severity=AlertSeverity.INFO,
                    title="Alerting System Test",
                    message=f"Test alert for {channel.value} channel",
                    service="test_service",
                    channels=[channel]
                )
                
                await self.alert_manager._send_to_channel(test_alert, channel)
                test_results[channel.value] = "SUCCESS"
                
            except Exception as e:
                test_results[channel.value] = f"FAILED: {e}"
                
        return test_results


# Global error handler instance
_global_error_handler = OandaErrorHandler()


def get_global_error_handler() -> OandaErrorHandler:
    """Get global error handler instance"""
    return _global_error_handler


def error_handled(operation: str,
                 service_name: str = "oanda_api",
                 auto_alert: bool = True):
    """
    Decorator for automatic error handling
    
    Args:
        operation: Operation name
        service_name: Service name
        auto_alert: Whether to auto-send alerts
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Get error handler from class instance or use global
                if hasattr(args[0], '_error_handler'):
                    error_handler = args[0]._error_handler
                else:
                    error_handler = get_global_error_handler()
                    
                # Extract context from kwargs
                account_id = kwargs.get('account_id')
                request_id = kwargs.get('request_id')
                correlation_id = kwargs.get('correlation_id')
                
                # Handle error
                await error_handler.handle_error(
                    error, operation, service_name,
                    account_id=account_id,
                    request_id=request_id,
                    correlation_id=correlation_id,
                    auto_alert=auto_alert
                )
                
                # Re-raise the error
                raise
                
        return wrapper
    return decorator