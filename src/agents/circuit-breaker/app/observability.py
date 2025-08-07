"""
Observability Implementation

Provides comprehensive monitoring, metrics, tracing, and logging
for the Circuit Breaker Agent with OpenTelemetry integration.
"""

import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from functools import wraps
import structlog

# OpenTelemetry imports
from opentelemetry import trace, metrics
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Prometheus imports
from prometheus_client import Counter, Histogram, Gauge, Info, start_http_server

from .config import config

logger = structlog.get_logger(__name__)


class CircuitBreakerMetrics:
    """
    Prometheus metrics for circuit breaker operations and system health.
    """
    
    def __init__(self):
        # Circuit breaker metrics
        self.breaker_triggers = Counter(
            'circuit_breaker_triggers_total',
            'Total number of circuit breaker triggers',
            ['level', 'reason', 'identifier']
        )
        
        self.breaker_resets = Counter(
            'circuit_breaker_resets_total',
            'Total number of circuit breaker resets',
            ['level', 'identifier']
        )
        
        self.breaker_state = Gauge(
            'circuit_breaker_state',
            'Current circuit breaker state (0=normal, 1=warning, 2=tripped)',
            ['level', 'identifier']
        )
        
        self.emergency_stop_duration = Histogram(
            'emergency_stop_duration_seconds',
            'Duration of emergency stop operations',
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
        )
        
        self.position_closure_count = Counter(
            'position_closures_total',
            'Total number of positions closed during emergency stops',
            ['success']
        )
        
        # System health metrics
        self.system_health_score = Gauge(
            'system_health_score',
            'Overall system health score (0-1)',
        )
        
        self.response_time = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint', 'status_code'],
            buckets=[0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0]
        )
        
        self.active_websocket_connections = Gauge(
            'websocket_connections_active',
            'Number of active WebSocket connections'
        )
        
        self.kafka_events = Counter(
            'kafka_events_total',
            'Total Kafka events processed',
            ['event_type', 'status']
        )
        
        self.health_check_failures = Counter(
            'health_check_failures_total',
            'Total health check failures',
            ['check_type']
        )
        
        # Service information
        self.service_info = Info(
            'circuit_breaker_service',
            'Circuit breaker service information'
        )
        
        # Set service information
        self.service_info.info({
            'version': config.version,
            'environment': config.environment,
            'service': config.service_name
        })
        
        logger.info("Circuit breaker metrics initialized")
    
    def record_breaker_trigger(self, level: str, reason: str, identifier: str):
        """Record circuit breaker trigger"""
        self.breaker_triggers.labels(
            level=level,
            reason=reason,
            identifier=identifier
        ).inc()
        
        # Update state metric (2 = tripped)
        self.breaker_state.labels(
            level=level,
            identifier=identifier
        ).set(2)
        
        logger.info(
            "Recorded breaker trigger metric",
            level=level,
            reason=reason,
            identifier=identifier
        )
    
    def record_breaker_reset(self, level: str, identifier: str):
        """Record circuit breaker reset"""
        self.breaker_resets.labels(
            level=level,
            identifier=identifier
        ).inc()
        
        # Update state metric (0 = normal)
        self.breaker_state.labels(
            level=level,
            identifier=identifier
        ).set(0)
        
        logger.info(
            "Recorded breaker reset metric",
            level=level,
            identifier=identifier
        )
    
    def record_emergency_stop_duration(self, duration_seconds: float):
        """Record emergency stop operation duration"""
        self.emergency_stop_duration.observe(duration_seconds)
    
    def record_position_closure(self, count: int, success: bool):
        """Record position closure results"""
        status = "success" if success else "failure"
        self.position_closure_count.labels(success=status).inc(count)
    
    def update_health_score(self, score: float):
        """Update overall system health score"""
        self.system_health_score.set(max(0.0, min(1.0, score)))
    
    def record_http_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record HTTP request metrics"""
        self.response_time.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code)
        ).observe(duration)
    
    def update_websocket_connections(self, count: int):
        """Update active WebSocket connection count"""
        self.active_websocket_connections.set(count)
    
    def record_kafka_event(self, event_type: str, success: bool):
        """Record Kafka event processing"""
        status = "success" if success else "failure"
        self.kafka_events.labels(
            event_type=event_type,
            status=status
        ).inc()
    
    def record_health_check_failure(self, check_type: str):
        """Record health check failure"""
        self.health_check_failures.labels(check_type=check_type).inc()


class OpenTelemetryTracer:
    """
    OpenTelemetry tracing setup for distributed tracing.
    """
    
    def __init__(self):
        # Create resource
        resource = Resource(attributes={
            SERVICE_NAME: config.service_name,
            SERVICE_VERSION: config.version,
            "environment": config.environment
        })
        
        # Configure tracing
        if config.enable_tracing:
            trace.set_tracer_provider(TracerProvider(resource=resource))
            self.tracer = trace.get_tracer(__name__)
        else:
            self.tracer = None
        
        logger.info(
            "OpenTelemetry tracer initialized",
            tracing_enabled=config.enable_tracing
        )
    
    def start_span(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Start a new span"""
        if not self.tracer:
            return trace.NoOpSpan()
        
        span = self.tracer.start_span(name)
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, str(value))
        
        return span
    
    def trace_function(self, name: Optional[str] = None):
        """Decorator to trace function execution"""
        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                span_name = name or f"{func.__module__}.{func.__name__}"
                
                with self.start_span(span_name) as span:
                    try:
                        span.set_attribute("function.name", func.__name__)
                        span.set_attribute("function.module", func.__module__)
                        
                        result = await func(*args, **kwargs)
                        span.set_attribute("function.success", True)
                        return result
                        
                    except Exception as e:
                        span.set_attribute("function.success", False)
                        span.set_attribute("function.error", str(e))
                        span.record_exception(e)
                        raise
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                span_name = name or f"{func.__module__}.{func.__name__}"
                
                with self.start_span(span_name) as span:
                    try:
                        span.set_attribute("function.name", func.__name__)
                        span.set_attribute("function.module", func.__module__)
                        
                        result = func(*args, **kwargs)
                        span.set_attribute("function.success", True)
                        return result
                        
                    except Exception as e:
                        span.set_attribute("function.success", False)
                        span.set_attribute("function.error", str(e))
                        span.record_exception(e)
                        raise
            
            # Return appropriate wrapper based on whether function is async
            import asyncio
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator


class StructuredLogger:
    """
    Structured logging setup with correlation ID support and JSON formatting.
    """
    
    def __init__(self):
        # Configure structlog
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.StackInfoRenderer(),
                structlog.dev.set_exc_info,
                structlog.processors.JSONRenderer()
            ],
            wrapper_class=structlog.make_filtering_bound_logger(
                level=getattr(structlog.stdlib, config.log_level.upper())
            ),
            logger_factory=structlog.WriteLoggerFactory(),
            cache_logger_on_first_use=True,
        )
        
        logger.info(
            "Structured logging configured",
            log_level=config.log_level,
            environment=config.environment
        )
    
    def get_logger(self, name: str = __name__):
        """Get a structured logger instance"""
        return structlog.get_logger(name)
    
    def bind_correlation_id(self, correlation_id: str):
        """Bind correlation ID to current context"""
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
    
    def clear_context(self):
        """Clear current context variables"""
        structlog.contextvars.clear_contextvars()


class ObservabilityManager:
    """
    Central manager for all observability components.
    """
    
    def __init__(self):
        self.metrics = CircuitBreakerMetrics()
        self.tracer = OpenTelemetryTracer()
        self.structured_logger = StructuredLogger()
        self._metrics_server_started = False
        
        logger.info("Observability manager initialized")
    
    async def start_metrics_server(self) -> bool:
        """Start Prometheus metrics server"""
        if self._metrics_server_started:
            logger.warning("Metrics server already started")
            return True
        
        try:
            start_http_server(config.metrics_port)
            self._metrics_server_started = True
            
            logger.info(
                "Prometheus metrics server started",
                port=config.metrics_port,
                endpoint=f"http://localhost:{config.metrics_port}/metrics"
            )
            return True
            
        except Exception as e:
            logger.exception("Failed to start metrics server", error=str(e))
            return False
    
    def instrument_fastapi(self, app):
        """Instrument FastAPI application with OpenTelemetry"""
        if config.enable_tracing:
            try:
                FastAPIInstrumentor.instrument_app(app)
                logger.info("FastAPI instrumentation enabled")
            except Exception as e:
                logger.exception("Failed to instrument FastAPI", error=str(e))
    
    def calculate_health_score(
        self,
        cpu_usage: float,
        memory_usage: float,
        error_rate: float,
        response_time: int
    ) -> float:
        """
        Calculate overall health score from system metrics.
        
        Args:
            cpu_usage: CPU usage percentage (0-100)
            memory_usage: Memory usage percentage (0-100)
            error_rate: Error rate (0-1)
            response_time: Average response time in milliseconds
            
        Returns:
            Health score between 0 and 1
        """
        try:
            # CPU score (100% = 0 score, 0% = 1 score)
            cpu_score = max(0, 1 - (cpu_usage / 100))
            
            # Memory score (100% = 0 score, 0% = 1 score)
            memory_score = max(0, 1 - (memory_usage / 100))
            
            # Error rate score (100% errors = 0 score, 0% errors = 1 score)
            error_score = max(0, 1 - error_rate)
            
            # Response time score (normalize against threshold)
            max_acceptable_response = config.response_time_threshold * 2  # 200ms for 100ms threshold
            response_score = max(0, 1 - (response_time / max_acceptable_response))
            
            # Weighted average (error rate and response time are most critical)
            health_score = (
                cpu_score * 0.2 +
                memory_score * 0.2 +
                error_score * 0.4 +
                response_score * 0.2
            )
            
            return max(0.0, min(1.0, health_score))
            
        except Exception as e:
            logger.exception("Error calculating health score", error=str(e))
            return 0.5  # Default to neutral score
    
    def get_observability_status(self) -> Dict[str, Any]:
        """Get status of all observability components"""
        return {
            "metrics_server_running": self._metrics_server_started,
            "metrics_port": config.metrics_port,
            "tracing_enabled": config.enable_tracing,
            "log_level": config.log_level,
            "service_name": config.service_name,
            "service_version": config.version,
            "environment": config.environment
        }


# Global observability manager instance
observability = ObservabilityManager()

# Convenience functions for common operations
def record_breaker_trigger(level: str, reason: str, identifier: str):
    """Record circuit breaker trigger"""
    observability.metrics.record_breaker_trigger(level, reason, identifier)

def record_breaker_reset(level: str, identifier: str):
    """Record circuit breaker reset"""
    observability.metrics.record_breaker_reset(level, identifier)

def record_emergency_stop_duration(duration_seconds: float):
    """Record emergency stop operation duration"""
    observability.metrics.record_emergency_stop_duration(duration_seconds)

def update_health_score(score: float):
    """Update overall system health score"""
    observability.metrics.update_health_score(score)

def trace_function(name: Optional[str] = None):
    """Decorator to trace function execution"""
    return observability.tracer.trace_function(name)

def get_logger(name: str = __name__):
    """Get structured logger"""
    return observability.structured_logger.get_logger(name)

def bind_correlation_id(correlation_id: str):
    """Bind correlation ID to logging context"""
    observability.structured_logger.bind_correlation_id(correlation_id)