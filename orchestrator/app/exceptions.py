"""
Custom exceptions for the Trading System Orchestrator
"""

from typing import Optional, Dict, Any


class OrchestratorException(Exception):
    """Base exception for orchestrator errors"""
    
    def __init__(
        self, 
        message: str, 
        status_code: int = 500, 
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class AgentException(OrchestratorException):
    """Exception related to agent operations"""
    
    def __init__(self, agent_id: str, message: str, status_code: int = 500):
        self.agent_id = agent_id
        super().__init__(
            message=f"Agent {agent_id}: {message}",
            status_code=status_code,
            details={"agent_id": agent_id}
        )


class CircuitBreakerException(OrchestratorException):
    """Exception when circuit breaker is triggered"""
    
    def __init__(self, breaker_type: str, message: str):
        self.breaker_type = breaker_type
        super().__init__(
            message=f"Circuit breaker '{breaker_type}': {message}",
            status_code=423,  # Locked
            details={"breaker_type": breaker_type}
        )


class OandaException(OrchestratorException):
    """Exception related to OANDA operations"""
    
    def __init__(self, message: str, error_code: Optional[str] = None):
        self.error_code = error_code
        details = {"error_code": error_code} if error_code else {}
        super().__init__(
            message=f"OANDA: {message}",
            status_code=502,  # Bad Gateway
            details=details
        )


class SafetyException(OrchestratorException):
    """Exception when safety checks fail"""
    
    def __init__(self, safety_check: str, message: str):
        self.safety_check = safety_check
        super().__init__(
            message=f"Safety check '{safety_check}': {message}",
            status_code=403,  # Forbidden
            details={"safety_check": safety_check}
        )


class ConfigurationException(OrchestratorException):
    """Exception related to configuration errors"""
    
    def __init__(self, config_key: str, message: str):
        self.config_key = config_key
        super().__init__(
            message=f"Configuration '{config_key}': {message}",
            status_code=500,
            details={"config_key": config_key}
        )


class ValidationException(OrchestratorException):
    """Exception for validation errors"""
    
    def __init__(self, field: str, message: str, value: Any = None):
        self.field = field
        self.value = value
        details = {"field": field}
        if value is not None:
            details["value"] = str(value)
        
        super().__init__(
            message=f"Validation error for '{field}': {message}",
            status_code=400,  # Bad Request
            details=details
        )


class TimeoutException(OrchestratorException):
    """Exception for timeout errors"""
    
    def __init__(self, operation: str, timeout_seconds: float):
        self.operation = operation
        self.timeout_seconds = timeout_seconds
        super().__init__(
            message=f"Operation '{operation}' timed out after {timeout_seconds}s",
            status_code=408,  # Request Timeout
            details={"operation": operation, "timeout_seconds": timeout_seconds}
        )


class RateLimitException(OrchestratorException):
    """Exception for rate limiting"""
    
    def __init__(self, resource: str, retry_after: Optional[int] = None):
        self.resource = resource
        self.retry_after = retry_after
        details = {"resource": resource}
        if retry_after:
            details["retry_after"] = retry_after
        
        super().__init__(
            message=f"Rate limit exceeded for '{resource}'",
            status_code=429,  # Too Many Requests
            details=details
        )


class AuthenticationException(OrchestratorException):
    """Exception for authentication errors"""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            status_code=401  # Unauthorized
        )


class AuthorizationException(OrchestratorException):
    """Exception for authorization errors"""
    
    def __init__(self, resource: str, action: str):
        self.resource = resource
        self.action = action
        super().__init__(
            message=f"Not authorized to {action} {resource}",
            status_code=403,  # Forbidden
            details={"resource": resource, "action": action}
        )


class MaintenanceException(OrchestratorException):
    """Exception when system is in maintenance mode"""
    
    def __init__(self, estimated_duration: Optional[int] = None):
        self.estimated_duration = estimated_duration
        message = "System is currently in maintenance mode"
        if estimated_duration:
            message += f" (estimated duration: {estimated_duration} minutes)"
        
        super().__init__(
            message=message,
            status_code=503,  # Service Unavailable
            details={"estimated_duration": estimated_duration}
        )