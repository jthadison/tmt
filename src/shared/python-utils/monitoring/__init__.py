"""
Shared monitoring utilities for the Trading Management System.

This module provides OpenTelemetry tracing and Prometheus metrics collection
utilities for all agents in the system.
"""

from .tracing import (
    configure_tracing,
    get_tracer,
    create_span,
    add_correlation_context,
    get_correlation_id,
    TRADING_TRACER_NAME
)
from .metrics import (
    configure_metrics,
    get_registry,
    create_counter,
    create_histogram,
    create_gauge,
    record_trading_metric,
    record_agent_metric
)

__all__ = [
    "configure_tracing",
    "get_tracer", 
    "create_span",
    "add_correlation_context",
    "get_correlation_id",
    "TRADING_TRACER_NAME",
    "configure_metrics",
    "get_registry",
    "create_counter",
    "create_histogram", 
    "create_gauge",
    "record_trading_metric",
    "record_agent_metric"
]