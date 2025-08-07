"""
Structured logging utilities for the Trading Management System.

This module provides comprehensive structured logging capabilities with correlation ID
injection, security logging, and centralized log collection integration.
"""

import json
import logging
import logging.handlers
import os
import sys
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Union
from contextvars import ContextVar

import structlog
from opentelemetry import trace

from .tracing import get_correlation_id, ensure_correlation_id
from .config import LoggingConfig

# Context variable for additional logging context
_logging_context: ContextVar[Dict[str, Any]] = ContextVar('logging_context', default={})

class CorrelationIDProcessor:
    """Structlog processor that adds correlation ID to log entries."""
    
    def __call__(self, logger, method_name, event_dict):
        correlation_id = get_correlation_id()
        if not correlation_id:
            correlation_id = ensure_correlation_id()
        
        event_dict['correlation_id'] = correlation_id
        
        # Add OpenTelemetry trace context if available
        current_span = trace.get_current_span()
        if current_span and current_span.is_recording():
            span_context = current_span.get_span_context()
            event_dict['trace_id'] = format(span_context.trace_id, '032x')
            event_dict['span_id'] = format(span_context.span_id, '016x')
        
        return event_dict

class ServiceContextProcessor:
    """Structlog processor that adds service context information."""
    
    def __init__(self, service_name: str, service_version: str = "1.0.0", environment: str = "development"):
        self.service_name = service_name
        self.service_version = service_version
        self.environment = environment
    
    def __call__(self, logger, method_name, event_dict):
        event_dict['service'] = {
            'name': self.service_name,
            'version': self.service_version,
            'environment': self.environment
        }
        
        # Add additional context from context variable
        additional_context = _logging_context.get({})
        if additional_context:
            event_dict.update(additional_context)
        
        return event_dict

class SecurityLoggingProcessor:
    """Processor for security-related logging with PII redaction."""
    
    SENSITIVE_FIELDS = {
        'password', 'secret', 'token', 'key', 'auth', 'credential',
        'api_key', 'access_token', 'refresh_token', 'session_id',
        'ssn', 'social_security', 'credit_card', 'account_number'
    }
    
    def __call__(self, logger, method_name, event_dict):
        # Redact sensitive information
        self._redact_sensitive_data(event_dict)
        
        # Add security event classification
        if self._is_security_event(event_dict, method_name):
            event_dict['event_category'] = 'security'
            event_dict['requires_audit'] = True
        
        return event_dict
    
    def _redact_sensitive_data(self, data: Dict[str, Any], prefix: str = "") -> None:
        """Recursively redact sensitive data from log entries."""
        if isinstance(data, dict):
            for key, value in list(data.items()):
                full_key = f"{prefix}.{key}" if prefix else key
                
                if any(sensitive in key.lower() for sensitive in self.SENSITIVE_FIELDS):
                    data[key] = "[REDACTED]"
                elif isinstance(value, (dict, list)):
                    self._redact_sensitive_data(value, full_key)
                elif isinstance(value, str) and len(value) > 50:
                    # Potentially redact very long strings that might contain sensitive data
                    data[key] = f"{value[:20]}...[TRUNCATED]"
        
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, (dict, list)):
                    self._redact_sensitive_data(item, f"{prefix}[{i}]")
    
    def _is_security_event(self, event_dict: Dict[str, Any], method_name: str) -> bool:
        """Determine if this is a security-related event."""
        security_indicators = {
            'authentication', 'authorization', 'login', 'logout', 'access_denied',
            'permission', 'unauthorized', 'forbidden', 'security', 'breach',
            'intrusion', 'violation', 'suspicious', 'failed_login', 'brute_force'
        }
        
        # Check event message
        event = event_dict.get('event', '').lower()
        if any(indicator in event for indicator in security_indicators):
            return True
        
        # Check log level for security events
        if method_name in ['critical', 'error'] and any(
            indicator in str(value).lower() 
            for value in event_dict.values() 
            if isinstance(value, str)
            for indicator in security_indicators
        ):
            return True
        
        return False

def configure_structured_logging(config: LoggingConfig) -> None:
    """Configure structured logging for the application."""
    
    # Configure standard library logging
    logging.basicConfig(
        level=getattr(logging, config.level.value),
        format="%(message)s",
        stream=sys.stdout if config.output_console else None
    )
    
    # Configure structlog
    processors = [
        # Add correlation ID and trace context
        CorrelationIDProcessor(),
        
        # Add service context
        ServiceContextProcessor(
            service_name=config.service_name,
            environment=config.environment.value
        ),
        
        # Security logging and PII redaction
        SecurityLoggingProcessor(),
        
        # Add timestamp
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        
        # Add log level
        structlog.processors.add_log_level,
        
        # Add logger name
        structlog.processors.add_logger_name,
        
        # Stack trace for exceptions
        structlog.processors.format_exc_info,
    ]
    
    # Add JSON formatting for structured output
    if config.structured_format:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.processors.ConsoleRenderer())
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, config.level.value)
        ),
        logger_factory=structlog.WriteLoggerFactory(),
        cache_logger_on_first_use=True
    )

def get_logger(name: str) -> structlog.BoundLogger:
    """Get a configured structured logger."""
    return structlog.get_logger(name)

def set_logging_context(**context: Any) -> None:
    """Set additional context for logging."""
    current_context = _logging_context.get({})
    current_context.update(context)
    _logging_context.set(current_context)

def clear_logging_context() -> None:
    """Clear the logging context."""
    _logging_context.set({})

def log_security_event(
    logger: structlog.BoundLogger,
    event_type: str,
    description: str,
    severity: str = "WARNING",
    **additional_context: Any
) -> None:
    """Log a security-related event with proper categorization."""
    
    context = {
        'event_type': event_type,
        'event_category': 'security',
        'requires_audit': True,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        **additional_context
    }
    
    log_method = getattr(logger, severity.lower(), logger.warning)
    log_method(description, **context)

def log_trading_event(
    logger: structlog.BoundLogger,
    event_type: str,
    description: str,
    **additional_context: Any
) -> None:
    """Log a trading-related event with business context."""
    
    context = {
        'event_type': event_type,
        'event_category': 'trading',
        'business_impact': True,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        **additional_context
    }
    
    logger.info(description, **context)

def log_performance_event(
    logger: structlog.BoundLogger,
    operation: str,
    duration_ms: float,
    success: bool = True,
    **additional_context: Any
) -> None:
    """Log a performance-related event."""
    
    context = {
        'event_type': 'performance',
        'event_category': 'performance',
        'operation': operation,
        'duration_ms': duration_ms,
        'success': success,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        **additional_context
    }
    
    # Log level based on performance and success
    if not success:
        logger.error(f"Operation {operation} failed", **context)
    elif duration_ms > 1000:  # Slow operation
        logger.warning(f"Slow operation {operation}", **context)
    else:
        logger.info(f"Operation {operation} completed", **context)

# Pre-configured loggers for different system components
def get_agent_logger(agent_type: str) -> structlog.BoundLogger:
    """Get a logger configured for a specific agent type."""
    logger = get_logger(f"agent.{agent_type}")
    set_logging_context(agent_type=agent_type, component="agent")
    return logger

def get_infrastructure_logger(component: str) -> structlog.BoundLogger:
    """Get a logger configured for infrastructure components."""
    logger = get_logger(f"infrastructure.{component}")
    set_logging_context(component_type="infrastructure", component=component)
    return logger

def get_trading_logger() -> structlog.BoundLogger:
    """Get a logger configured for trading operations."""
    logger = get_logger("trading")
    set_logging_context(component_type="trading", business_critical=True)
    return logger

# Log aggregation helpers
class LogAggregator:
    """Helper for aggregating and analyzing log patterns."""
    
    def __init__(self, logger: structlog.BoundLogger):
        self.logger = logger
        self.error_counts = {}
        self.pattern_counts = {}
    
    def increment_error_count(self, error_type: str) -> None:
        """Track error frequency for monitoring."""
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        # Log high error frequency
        if self.error_counts[error_type] % 10 == 0:
            self.logger.warning(
                "High error frequency detected",
                error_type=error_type,
                count=self.error_counts[error_type],
                event_category="monitoring"
            )
    
    def track_pattern(self, pattern: str) -> None:
        """Track recurring patterns in logs."""
        self.pattern_counts[pattern] = self.pattern_counts.get(pattern, 0) + 1