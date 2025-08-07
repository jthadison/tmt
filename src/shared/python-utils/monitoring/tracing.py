"""
OpenTelemetry distributed tracing utilities for the Trading Management System.

This module provides comprehensive distributed tracing capabilities for all agents,
including correlation ID propagation, custom spans for critical trading operations,
and configurable sampling for performance optimization.
"""

import os
import uuid
from contextlib import contextmanager
from typing import Optional, Dict, Any, Iterator
from contextvars import ContextVar

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.kafka import KafkaInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.b3 import B3MultiFormat
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

# Trading system tracer name
TRADING_TRACER_NAME = "trading-management-system"

# Context variable for correlation ID
_correlation_id_context: ContextVar[Optional[str]] = ContextVar(
    'correlation_id', default=None
)

class TradingTracerProvider:
    """Custom tracer provider for the trading system."""
    
    def __init__(self):
        self._provider: Optional[TracerProvider] = None
        self._initialized = False
    
    def configure(
        self,
        service_name: str,
        service_version: str = "1.0.0",
        environment: str = "development",
        sampling_rate: float = 1.0,
        export_console: bool = False,
        jaeger_endpoint: Optional[str] = None,
        otlp_endpoint: Optional[str] = None
    ) -> None:
        """
        Configure OpenTelemetry tracing for the trading system.
        
        Args:
            service_name: Name of the service (e.g., "circuit-breaker-agent")
            service_version: Version of the service
            environment: Environment (development, staging, production)
            sampling_rate: Sampling rate (0.0 to 1.0) for performance optimization
            export_console: Whether to export traces to console for debugging
            jaeger_endpoint: Jaeger collector endpoint
            otlp_endpoint: OTLP collector endpoint
        """
        if self._initialized:
            return
        
        # Create resource with service identification
        resource = Resource.create({
            SERVICE_NAME: service_name,
            SERVICE_VERSION: service_version,
            "service.environment": environment,
            "service.namespace": "trading-system",
            "telemetry.sdk.language": "python",
            "telemetry.sdk.name": "opentelemetry",
        })
        
        # Configure sampling for performance optimization
        sampler = TraceIdRatioBased(sampling_rate)
        
        # Create tracer provider
        self._provider = TracerProvider(
            resource=resource,
            sampler=sampler
        )
        
        # Configure span processors and exporters
        processors = []
        
        # Console exporter for development debugging
        if export_console:
            console_processor = BatchSpanProcessor(ConsoleSpanExporter())
            processors.append(console_processor)
        
        # Jaeger exporter
        if jaeger_endpoint:
            jaeger_exporter = JaegerExporter(
                agent_host_name=jaeger_endpoint.split(':')[0] if ':' in jaeger_endpoint else jaeger_endpoint,
                agent_port=int(jaeger_endpoint.split(':')[1]) if ':' in jaeger_endpoint else 14268,
                collector_endpoint=f"http://{jaeger_endpoint}/api/traces"
            )
            jaeger_processor = BatchSpanProcessor(jaeger_exporter)
            processors.append(jaeger_processor)
        
        # OTLP exporter (preferred for production)
        if otlp_endpoint:
            otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
            otlp_processor = BatchSpanProcessor(otlp_exporter)
            processors.append(otlp_processor)
        
        # Add processors to provider
        for processor in processors:
            self._provider.add_span_processor(processor)
        
        # Set global tracer provider
        trace.set_tracer_provider(self._provider)
        
        # Configure B3 propagation for microservices communication
        set_global_textmap(B3MultiFormat())
        
        # Auto-instrument common libraries
        self._auto_instrument()
        
        self._initialized = True
    
    def _auto_instrument(self) -> None:
        """Automatically instrument common libraries used in trading system."""
        try:
            # FastAPI instrumentation for API endpoints
            FastAPIInstrumentor().instrument()
            
            # HTTP requests instrumentation
            RequestsInstrumentor().instrument()
            
            # PostgreSQL instrumentation
            Psycopg2Instrumentor().instrument()
            
            # Redis instrumentation
            RedisInstrumentor().instrument()
            
            # Kafka instrumentation for message processing
            KafkaInstrumentor().instrument()
            
        except Exception as e:
            # Log error but don't fail initialization
            print(f"Warning: Auto-instrumentation failed for some libraries: {e}")
    
    def get_tracer(self, name: str = TRADING_TRACER_NAME) -> trace.Tracer:
        """Get a tracer instance."""
        if not self._initialized:
            raise RuntimeError("Tracing not configured. Call configure() first.")
        return trace.get_tracer(name)
    
    def shutdown(self) -> None:
        """Shutdown the tracer provider and flush remaining spans."""
        if self._provider:
            self._provider.shutdown()

# Global tracer provider instance
_tracer_provider = TradingTracerProvider()

def configure_tracing(
    service_name: str,
    service_version: str = "1.0.0",
    environment: Optional[str] = None,
    sampling_rate: Optional[float] = None,
    export_console: Optional[bool] = None,
    jaeger_endpoint: Optional[str] = None,
    otlp_endpoint: Optional[str] = None
) -> None:
    """
    Configure OpenTelemetry tracing for the trading system.
    
    This function uses environment variables as defaults but allows overrides.
    
    Args:
        service_name: Name of the service
        service_version: Version of the service
        environment: Environment (defaults to TRADING_ENVIRONMENT)
        sampling_rate: Sampling rate (defaults to OTEL_TRACES_SAMPLER_ARG)
        export_console: Export to console (defaults to OTEL_EXPORTER_CONSOLE)
        jaeger_endpoint: Jaeger endpoint (defaults to OTEL_EXPORTER_JAEGER_ENDPOINT)
        otlp_endpoint: OTLP endpoint (defaults to OTEL_EXPORTER_OTLP_ENDPOINT)
    """
    # Use environment variables as defaults
    environment = environment or os.getenv("TRADING_ENVIRONMENT", "development")
    sampling_rate = sampling_rate or float(os.getenv("OTEL_TRACES_SAMPLER_ARG", "1.0"))
    export_console = export_console if export_console is not None else os.getenv("OTEL_EXPORTER_CONSOLE", "false").lower() == "true"
    jaeger_endpoint = jaeger_endpoint or os.getenv("OTEL_EXPORTER_JAEGER_ENDPOINT")
    otlp_endpoint = otlp_endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    
    _tracer_provider.configure(
        service_name=service_name,
        service_version=service_version,
        environment=environment,
        sampling_rate=sampling_rate,
        export_console=export_console,
        jaeger_endpoint=jaeger_endpoint,
        otlp_endpoint=otlp_endpoint
    )

def get_tracer(name: str = TRADING_TRACER_NAME) -> trace.Tracer:
    """Get a tracer instance."""
    return _tracer_provider.get_tracer(name)

@contextmanager
def create_span(
    name: str,
    kind: trace.SpanKind = trace.SpanKind.INTERNAL,
    attributes: Optional[Dict[str, Any]] = None,
    tracer_name: str = TRADING_TRACER_NAME
) -> Iterator[trace.Span]:
    """
    Create a span with automatic correlation ID injection.
    
    Args:
        name: Name of the span
        kind: Type of span (INTERNAL, CLIENT, SERVER, PRODUCER, CONSUMER)
        attributes: Additional attributes to add to the span
        tracer_name: Name of the tracer to use
        
    Yields:
        The created span
        
    Example:
        with create_span("calculate_position_size") as span:
            span.set_attribute("account_id", "ACC001")
            position_size = calculate_position_size(signal)
            span.set_attribute("position_size", str(position_size))
    """
    tracer = get_tracer(tracer_name)
    
    with tracer.start_as_current_span(name, kind=kind) as span:
        # Add correlation ID to span
        correlation_id = get_correlation_id()
        if correlation_id:
            span.set_attribute("correlation_id", correlation_id)
        
        # Add custom attributes
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, str(value))
        
        # Add trading system context
        span.set_attribute("system.component", "trading-management-system")
        
        yield span

def add_correlation_context(correlation_id: str) -> None:
    """
    Add correlation ID to the current context.
    
    Args:
        correlation_id: The correlation ID to add
    """
    _correlation_id_context.set(correlation_id)

def get_correlation_id() -> Optional[str]:
    """
    Get the current correlation ID from context.
    
    Returns:
        The correlation ID if available, None otherwise
    """
    return _correlation_id_context.get()

def generate_correlation_id() -> str:
    """
    Generate a new correlation ID.
    
    Returns:
        A new UUID-based correlation ID
    """
    return str(uuid.uuid4())

def ensure_correlation_id() -> str:
    """
    Ensure a correlation ID exists in the current context.
    
    If no correlation ID exists, generates a new one and sets it in context.
    
    Returns:
        The correlation ID (existing or newly generated)
    """
    correlation_id = get_correlation_id()
    if not correlation_id:
        correlation_id = generate_correlation_id()
        add_correlation_context(correlation_id)
    return correlation_id

# Critical trading operation span decorators
def trace_trading_operation(
    operation_name: str,
    operation_type: str = "trading"
):
    """
    Decorator to automatically trace trading operations with proper categorization.
    
    Args:
        operation_name: Name of the trading operation
        operation_type: Type of operation (trading, risk, analysis, execution)
    
    Example:
        @trace_trading_operation("signal_generation", "analysis")
        def generate_trading_signal(market_data):
            return analyze_wyckoff_pattern(market_data)
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            with create_span(
                f"{operation_type}.{operation_name}",
                attributes={
                    "operation.type": operation_type,
                    "operation.name": operation_name,
                    "function.name": func.__name__,
                    "function.module": func.__module__
                }
            ) as span:
                try:
                    result = func(*args, **kwargs)
                    span.set_status(trace.Status(trace.StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(
                        trace.Status(
                            trace.StatusCode.ERROR,
                            f"{type(e).__name__}: {str(e)}"
                        )
                    )
                    span.record_exception(e)
                    raise
        return wrapper
    return decorator

def shutdown_tracing() -> None:
    """Shutdown tracing and flush remaining spans."""
    _tracer_provider.shutdown()