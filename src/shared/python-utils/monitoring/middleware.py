"""
Observability middleware for the Trading Management System.

This module provides middleware components that integrate OpenTelemetry tracing
and Prometheus metrics with existing infrastructure components like Kafka,
FastAPI, and database connections.
"""

import time
from typing import Dict, Any, Optional, Callable
from functools import wraps
from contextvars import ContextVar

from opentelemetry import trace, propagate
from opentelemetry.trace import Status, StatusCode
from fastapi import Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
import structlog

from .tracing import (
    get_tracer,
    create_span,
    add_correlation_context,
    get_correlation_id,
    ensure_correlation_id,
    TRADING_TRACER_NAME
)
from .metrics import time_operation, record_agent_metric

logger = structlog.get_logger(__name__)

class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware to handle correlation ID propagation across HTTP requests.
    
    This middleware:
    1. Extracts correlation ID from headers
    2. Sets it in the request context
    3. Propagates it to downstream services
    4. Adds it to response headers
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract correlation ID from headers
        correlation_id = (
            request.headers.get("x-correlation-id") or
            request.headers.get("correlation-id") or
            ensure_correlation_id()
        )
        
        # Set correlation ID in context
        add_correlation_context(correlation_id)
        
        # Add to request for downstream use
        request.state.correlation_id = correlation_id
        
        # Process request with tracing
        with create_span(
            f"http.{request.method.lower()}.{request.url.path}",
            kind=trace.SpanKind.SERVER,
            attributes={
                "http.method": request.method,
                "http.url": str(request.url),
                "http.route": request.url.path,
                "http.user_agent": request.headers.get("user-agent", ""),
                "correlation_id": correlation_id
            }
        ) as span:
            try:
                start_time = time.time()
                response = await call_next(request)
                duration = time.time() - start_time
                
                # Add response attributes to span
                span.set_attribute("http.status_code", response.status_code)
                span.set_attribute("http.response_time_ms", duration * 1000)
                
                # Record metrics
                record_agent_metric(
                    "http_request_duration",
                    duration,
                    labels={
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": str(response.status_code)
                    }
                )
                
                # Set span status based on HTTP status code
                if response.status_code >= 400:
                    span.set_status(Status(StatusCode.ERROR, f"HTTP {response.status_code}"))
                else:
                    span.set_status(Status(StatusCode.OK))
                
                # Add correlation ID to response headers
                response.headers["x-correlation-id"] = correlation_id
                
                return response
                
            except Exception as e:
                # Record exception in span
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                
                logger.error(
                    "HTTP request failed",
                    correlation_id=correlation_id,
                    method=request.method,
                    path=request.url.path,
                    error=str(e)
                )
                raise

class KafkaTracingMiddleware:
    """
    Middleware for Kafka message tracing and correlation ID propagation.
    
    This middleware wraps Kafka producer/consumer operations to:
    1. Create spans for message production/consumption
    2. Propagate trace context via message headers
    3. Extract correlation IDs from messages
    4. Record messaging metrics
    """
    
    @staticmethod
    def wrap_producer_send(original_send_method):
        """Wrap Kafka producer send method with tracing."""
        
        @wraps(original_send_method)
        async def traced_send(self, event, topic=None, key=None, headers=None):
            correlation_id = get_correlation_id() or event.correlation_id
            add_correlation_context(correlation_id)
            
            with create_span(
                f"kafka.producer.send",
                kind=trace.SpanKind.PRODUCER,
                attributes={
                    "messaging.system": "kafka",
                    "messaging.destination": topic or "auto",
                    "messaging.operation": "send",
                    "messaging.message_id": event.event_id,
                    "event.type": event.event_type.value if hasattr(event, 'event_type') else "unknown",
                    "correlation_id": correlation_id
                }
            ) as span:
                try:
                    # Add trace context to message headers
                    trace_headers = {}
                    propagate.inject(trace_headers)
                    
                    # Merge with existing headers
                    if headers is None:
                        headers = {}
                    headers.update(trace_headers)
                    headers["correlation_id"] = correlation_id
                    
                    # Record message production metric
                    with time_operation(
                        "kafka_message_send",
                        labels={
                            "topic": topic or "auto",
                            "event_type": getattr(event, 'event_type', {}).get('value', 'unknown')
                        }
                    ):
                        result = await original_send_method(event, topic, key, headers)
                    
                    span.set_status(Status(StatusCode.OK))
                    span.set_attribute("messaging.kafka.partition", -1)  # Will be set by actual implementation
                    
                    return result
                    
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    
                    logger.error(
                        "Kafka message send failed",
                        correlation_id=correlation_id,
                        topic=topic,
                        event_id=getattr(event, 'event_id', 'unknown'),
                        error=str(e)
                    )
                    raise
        
        return traced_send
    
    @staticmethod
    def wrap_consumer_process(original_process_method):
        """Wrap Kafka consumer message processing with tracing."""
        
        @wraps(original_process_method)
        async def traced_process(self, message):
            # Extract correlation ID and trace context from message headers
            headers = dict(message.headers or [])
            correlation_id = headers.get("correlation_id", b"").decode("utf-8")
            
            if correlation_id:
                add_correlation_context(correlation_id)
            else:
                correlation_id = ensure_correlation_id()
            
            # Extract trace context
            trace_context = {}
            for key, value in headers.items():
                if isinstance(value, bytes):
                    trace_context[key] = value.decode("utf-8")
                else:
                    trace_context[key] = str(value)
            
            # Create consumer span with extracted context
            with trace.set_span_in_context(
                propagate.extract(trace_context) or trace.get_current_span()
            ):
                with create_span(
                    f"kafka.consumer.process",
                    kind=trace.SpanKind.CONSUMER,
                    attributes={
                        "messaging.system": "kafka",
                        "messaging.source": message.topic,
                        "messaging.operation": "receive",
                        "messaging.kafka.partition": message.partition,
                        "messaging.kafka.offset": message.offset,
                        "correlation_id": correlation_id
                    }
                ) as span:
                    try:
                        # Record message consumption metric
                        with time_operation(
                            "kafka_message_process",
                            labels={
                                "topic": message.topic,
                                "partition": str(message.partition)
                            }
                        ):
                            result = await original_process_method(message)
                        
                        span.set_status(Status(StatusCode.OK))
                        return result
                        
                    except Exception as e:
                        span.record_exception(e)
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        
                        logger.error(
                            "Kafka message processing failed",
                            correlation_id=correlation_id,
                            topic=message.topic,
                            partition=message.partition,
                            offset=message.offset,
                            error=str(e)
                        )
                        raise
        
        return traced_process

class DatabaseTracingMiddleware:
    """
    Middleware for database operation tracing and metrics.
    
    This middleware wraps database operations to:
    1. Create spans for database queries
    2. Record query performance metrics
    3. Propagate correlation IDs in database context
    """
    
    @staticmethod
    def wrap_database_operation(operation_name: str, database_name: str = "postgres"):
        """Decorator for database operations."""
        
        def decorator(func):
            @wraps(func)
            async def traced_operation(*args, **kwargs):
                correlation_id = get_correlation_id() or ensure_correlation_id()
                
                with create_span(
                    f"db.{operation_name}",
                    kind=trace.SpanKind.CLIENT,
                    attributes={
                        "db.system": "postgresql",
                        "db.name": database_name,
                        "db.operation": operation_name,
                        "correlation_id": correlation_id
                    }
                ) as span:
                    try:
                        # Record database operation metric
                        with time_operation(
                            f"database_{operation_name}",
                            labels={
                                "database": database_name,
                                "operation": operation_name
                            }
                        ):
                            result = await func(*args, **kwargs)
                        
                        span.set_status(Status(StatusCode.OK))
                        return result
                        
                    except Exception as e:
                        span.record_exception(e)
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        
                        logger.error(
                            "Database operation failed",
                            correlation_id=correlation_id,
                            operation=operation_name,
                            database=database_name,
                            error=str(e)
                        )
                        raise
            
            return traced_operation
        return decorator

def trace_circuit_breaker_operation(tier: str, reason: str = ""):
    """
    Decorator for circuit breaker operations with enhanced tracing.
    
    Args:
        tier: Circuit breaker tier (agent, account, system)
        reason: Reason for activation (optional)
    """
    def decorator(func):
        @wraps(func)
        async def traced_breaker_operation(*args, **kwargs):
            correlation_id = get_correlation_id() or ensure_correlation_id()
            
            with create_span(
                f"circuit_breaker.{func.__name__}",
                attributes={
                    "circuit_breaker.tier": tier,
                    "circuit_breaker.reason": reason,
                    "circuit_breaker.operation": func.__name__,
                    "correlation_id": correlation_id
                }
            ) as span:
                try:
                    result = await func(*args, **kwargs)
                    
                    # Record circuit breaker metrics
                    if "activate" in func.__name__ or "open" in func.__name__:
                        record_agent_metric(
                            "circuit_breaker_activations",
                            1,
                            labels={
                                "tier": tier,
                                "reason": reason or "unknown",
                                "operation": func.__name__
                            }
                        )
                        
                        # Mark as critical event in span
                        span.add_event(
                            "circuit_breaker_activated",
                            attributes={
                                "tier": tier,
                                "reason": reason,
                                "timestamp": time.time()
                            }
                        )
                    
                    span.set_status(Status(StatusCode.OK))
                    return result
                    
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    
                    logger.critical(
                        "Circuit breaker operation failed",
                        correlation_id=correlation_id,
                        tier=tier,
                        operation=func.__name__,
                        reason=reason,
                        error=str(e)
                    )
                    raise
        
        return traced_breaker_operation
    return decorator

def trace_trading_operation(operation_type: str):
    """
    Enhanced decorator for trading operations with business metrics.
    
    Args:
        operation_type: Type of trading operation (signal, risk, execution, analysis)
    """
    def decorator(func):
        @wraps(func)
        async def traced_trading_operation(*args, **kwargs):
            correlation_id = get_correlation_id() or ensure_correlation_id()
            
            with create_span(
                f"trading.{operation_type}.{func.__name__}",
                attributes={
                    "trading.operation_type": operation_type,
                    "trading.operation": func.__name__,
                    "correlation_id": correlation_id
                }
            ) as span:
                try:
                    start_time = time.time()
                    result = await func(*args, **kwargs)
                    duration = time.time() - start_time
                    
                    # Record trading operation metrics
                    record_agent_metric(
                        f"trading_{operation_type}_duration",
                        duration,
                        labels={
                            "operation": func.__name__,
                            "operation_type": operation_type
                        }
                    )
                    
                    # Add business context to span
                    if hasattr(result, 'confidence') and result.confidence:
                        span.set_attribute("trading.confidence_score", result.confidence)
                    
                    if hasattr(result, 'position_size') and result.position_size:
                        span.set_attribute("trading.position_size", str(result.position_size))
                    
                    span.set_attribute("trading.duration_ms", duration * 1000)
                    span.set_status(Status(StatusCode.OK))
                    
                    return result
                    
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    
                    logger.error(
                        "Trading operation failed",
                        correlation_id=correlation_id,
                        operation_type=operation_type,
                        operation=func.__name__,
                        error=str(e)
                    )
                    raise
        
        return traced_trading_operation
    return decorator