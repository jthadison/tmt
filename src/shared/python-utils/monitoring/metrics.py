"""
Prometheus metrics collection utilities for the Trading Management System.

This module provides comprehensive metrics collection for all agents, including
business metrics, infrastructure metrics, and custom metrics for circuit breaker
activations and message latency.
"""

import os
import time
import threading
from typing import Dict, Optional, List, Any
from contextlib import contextmanager
from decimal import Decimal

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Histogram,
    Gauge,
    Info,
    Enum,
    Summary,
    generate_latest,
    CONTENT_TYPE_LATEST,
    start_http_server
)
import psutil

class TradingMetricsRegistry:
    """Central registry for all trading system metrics (thread-safe singleton)."""
    
    _instance: Optional['TradingMetricsRegistry'] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> 'TradingMetricsRegistry':
        """Thread-safe singleton implementation."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        # Prevent re-initialization of singleton
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        self.registry = CollectorRegistry()
        self._metrics: Dict[str, Any] = {}
        self._initialized = False
        self._http_server_port: Optional[int] = None
        
        # Thread safety locks
        self._metrics_lock = threading.RLock()  # Reentrant lock for nested calls
        self._config_lock = threading.Lock()   # Configuration lock
        
        # Core business metrics
        self._trading_metrics: Dict[str, Any] = {}
        self._agent_metrics: Dict[str, Any] = {}
        self._infrastructure_metrics: Dict[str, Any] = {}
        
        # Background metrics collection
        self._metrics_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        self._singleton_initialized = True
    
    def __del__(self):
        """Cleanup resources when object is garbage collected."""
        try:
            self.shutdown()
        except Exception:
            # Ignore exceptions during cleanup to prevent issues during garbage collection
            pass
    
    def configure(
        self,
        service_name: str,
        service_version: str = "1.0.0",
        environment: str = "development",
        metrics_port: int = 8000,
        enable_auto_metrics: bool = True,
        collection_interval: int = 10
    ) -> None:
        """
        Configure Prometheus metrics collection for the trading system.
        
        Args:
            service_name: Name of the service
            service_version: Version of the service  
            environment: Environment (development, staging, production)
            metrics_port: Port for metrics HTTP server
            enable_auto_metrics: Enable automatic infrastructure metrics collection
            collection_interval: Metrics collection interval in seconds
        """
        with self._config_lock:
            if self._initialized:
                return
            
            self._service_name = service_name
            self._service_version = service_version
            self._environment = environment
            
            # Initialize core metrics
            self._init_trading_metrics()
            self._init_agent_metrics()
            self._init_infrastructure_metrics()
            
            # Start HTTP server for metrics endpoint
            try:
                start_http_server(metrics_port, registry=self.registry)
                self._http_server_port = metrics_port
            except Exception as e:
                print(f"Warning: Failed to start metrics HTTP server on port {metrics_port}: {e}")
            
            # Start automatic infrastructure metrics collection
            if enable_auto_metrics:
                self._start_auto_metrics_collection(collection_interval)
            
            self._initialized = True
    
    def _init_trading_metrics(self) -> None:
        """Initialize core trading business metrics."""
        with self._metrics_lock:
            # Trade execution metrics
        self._trading_metrics["trades_total"] = Counter(
            "trading_trades_total",
            "Total number of trades executed",
            ["agent_type", "account_id", "pair", "direction", "status"],
            registry=self.registry
        )
        
        self._trading_metrics["trade_success_rate"] = Gauge(
            "trading_success_rate",
            "Success rate of trades (percentage)",
            ["agent_type", "account_id", "timeframe"],
            registry=self.registry
        )
        
        self._trading_metrics["position_size_usd"] = Histogram(
            "trading_position_size_usd",
            "Position size in USD",
            ["agent_type", "account_id", "pair"],
            buckets=[10, 50, 100, 500, 1000, 5000, 10000, 50000, 100000, float("inf")],
            registry=self.registry
        )
        
        # Signal generation metrics
        self._trading_metrics["signals_generated"] = Counter(
            "trading_signals_generated_total",
            "Total signals generated",
            ["agent_type", "signal_type", "confidence_level"],
            registry=self.registry
        )
        
        self._trading_metrics["signal_confidence"] = Histogram(
            "trading_signal_confidence_score",
            "Signal confidence scores",
            ["agent_type", "signal_type"],
            buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            registry=self.registry
        )
        
        # Risk management metrics
        self._trading_metrics["risk_calculation_duration"] = Histogram(
            "trading_risk_calculation_duration_seconds",
            "Time taken for risk calculations",
            ["agent_type", "calculation_type"],
            registry=self.registry
        )
        
        self._trading_metrics["drawdown_current"] = Gauge(
            "trading_drawdown_current_percent",
            "Current drawdown percentage",
            ["account_id"],
            registry=self.registry
        )
        
        # P&L metrics
        self._trading_metrics["pnl_unrealized"] = Gauge(
            "trading_pnl_unrealized_usd",
            "Unrealized P&L in USD",
            ["account_id", "pair"],
            registry=self.registry
        )
        
        self._trading_metrics["pnl_realized"] = Counter(
            "trading_pnl_realized_usd_total",
            "Realized P&L in USD",
            ["account_id", "pair", "result"],
            registry=self.registry
        )
    
    def _init_agent_metrics(self) -> None:
        """Initialize agent-specific metrics."""
        
        # Agent health and status
        self._agent_metrics["agent_status"] = Enum(
            "agent_status",
            "Current status of the agent",
            ["agent_type", "agent_id"],
            states=["healthy", "degraded", "stopped", "error"],
            registry=self.registry
        )
        
        # Message processing metrics
        self._agent_metrics["messages_processed"] = Counter(
            "agent_messages_processed_total",
            "Total messages processed by agent",
            ["agent_type", "message_type", "status"],
            registry=self.registry
        )
        
        self._agent_metrics["message_processing_duration"] = Histogram(
            "agent_message_processing_duration_seconds",
            "Message processing duration",
            ["agent_type", "message_type"],
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
            registry=self.registry
        )
        
        # Circuit breaker metrics
        self._agent_metrics["circuit_breaker_activations"] = Counter(
            "agent_circuit_breaker_activations_total",
            "Circuit breaker activation count",
            ["agent_type", "breaker_tier", "reason"],
            registry=self.registry
        )
        
        self._agent_metrics["circuit_breaker_state"] = Enum(
            "agent_circuit_breaker_state",
            "Current circuit breaker state",
            ["agent_type", "breaker_tier"],
            states=["closed", "open", "half_open"],
            registry=self.registry
        )
        
        # Agent communication latency
        self._agent_metrics["inter_agent_latency"] = Histogram(
            "agent_inter_agent_latency_seconds",
            "Latency between agent communications",
            ["source_agent", "destination_agent", "message_type"],
            buckets=[0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0],
            registry=self.registry
        )
    
    def _init_infrastructure_metrics(self) -> None:
        """Initialize infrastructure monitoring metrics."""
        
        # System resource metrics
        self._infrastructure_metrics["cpu_usage_percent"] = Gauge(
            "system_cpu_usage_percent",
            "CPU usage percentage",
            ["service", "cpu_type"],
            registry=self.registry
        )
        
        self._infrastructure_metrics["memory_usage_bytes"] = Gauge(
            "system_memory_usage_bytes",
            "Memory usage in bytes",
            ["service", "memory_type"],
            registry=self.registry
        )
        
        self._infrastructure_metrics["disk_usage_bytes"] = Gauge(
            "system_disk_usage_bytes",
            "Disk usage in bytes",
            ["service", "disk_type", "mountpoint"],
            registry=self.registry
        )
        
        # Network metrics
        self._infrastructure_metrics["network_bytes"] = Counter(
            "system_network_bytes_total",
            "Network bytes sent/received",
            ["service", "direction", "interface"],
            registry=self.registry
        )
        
        # Database metrics
        self._infrastructure_metrics["db_connections"] = Gauge(
            "database_connections_active",
            "Active database connections",
            ["service", "database"],
            registry=self.registry
        )
        
        self._infrastructure_metrics["db_query_duration"] = Histogram(
            "database_query_duration_seconds",
            "Database query duration",
            ["service", "database", "operation"],
            registry=self.registry
        )
        
        # Service health
        self._infrastructure_metrics["service_up"] = Gauge(
            "service_up",
            "Service health status (1=up, 0=down)",
            ["service", "instance"],
            registry=self.registry
        )
        
        # Kafka metrics
        self._infrastructure_metrics["kafka_messages"] = Counter(
            "kafka_messages_total",
            "Kafka messages produced/consumed",
            ["service", "topic", "operation"],
            registry=self.registry
        )
        
        self._infrastructure_metrics["kafka_lag"] = Gauge(
            "kafka_consumer_lag_messages",
            "Consumer lag in messages",
            ["service", "topic", "partition"],
            registry=self.registry
        )
    
    def _start_auto_metrics_collection(self, interval: int) -> None:
        """Start automatic collection of infrastructure metrics."""
        def collect_metrics():
            while not self._shutdown_event.wait(interval):
                try:
                    self._collect_system_metrics()
                except Exception as e:
                    print(f"Error collecting system metrics: {e}")
        
        self._metrics_thread = threading.Thread(target=collect_metrics, daemon=True)
        self._metrics_thread.start()
    
    def _collect_system_metrics(self) -> None:
        """Collect system-level metrics."""
        service_name = self._service_name
        
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        self._infrastructure_metrics["cpu_usage_percent"].labels(
            service=service_name, cpu_type="total"
        ).set(cpu_percent)
        
        # Memory metrics
        memory = psutil.virtual_memory()
        self._infrastructure_metrics["memory_usage_bytes"].labels(
            service=service_name, memory_type="used"
        ).set(memory.used)
        self._infrastructure_metrics["memory_usage_bytes"].labels(
            service=service_name, memory_type="available"
        ).set(memory.available)
        
        # Disk metrics
        disk = psutil.disk_usage('/')
        self._infrastructure_metrics["disk_usage_bytes"].labels(
            service=service_name, disk_type="used", mountpoint="/"
        ).set(disk.used)
        self._infrastructure_metrics["disk_usage_bytes"].labels(
            service=service_name, disk_type="free", mountpoint="/"
        ).set(disk.free)
        
        # Set service up status
        self._infrastructure_metrics["service_up"].labels(
            service=service_name, instance="primary"
        ).set(1)
    
    def get_registry(self) -> CollectorRegistry:
        """Get the metrics registry."""
        return self.registry
    
    def shutdown(self) -> None:
        """Shutdown metrics collection."""
        with self._config_lock:
            if self._metrics_thread and self._metrics_thread.is_alive():
                self._shutdown_event.set()
                # Use timeout to prevent hanging during shutdown
                self._metrics_thread.join(timeout=5.0)
                if self._metrics_thread.is_alive():
                    print("Warning: Metrics collection thread did not shutdown gracefully")
                self._metrics_thread = None
            self._shutdown_event.clear()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.shutdown()
        return False

# Global metrics registry with thread safety
_global_registry_lock = threading.Lock()
_metrics_registry: Optional[TradingMetricsRegistry] = None

def get_metrics_registry() -> TradingMetricsRegistry:
    """Get the global metrics registry (thread-safe)."""
    global _metrics_registry
    if _metrics_registry is None:
        with _global_registry_lock:
            if _metrics_registry is None:
                _metrics_registry = TradingMetricsRegistry()
    return _metrics_registry

def configure_metrics(
    service_name: str,
    service_version: str = "1.0.0",
    environment: Optional[str] = None,
    metrics_port: Optional[int] = None,
    enable_auto_metrics: bool = True,
    collection_interval: int = 10
) -> None:
    """
    Configure Prometheus metrics collection for the trading system.
    
    Args:
        service_name: Name of the service
        service_version: Version of the service
        environment: Environment (defaults to TRADING_ENVIRONMENT)
        metrics_port: Port for metrics server (defaults to METRICS_PORT)
        enable_auto_metrics: Enable automatic infrastructure metrics
        collection_interval: Metrics collection interval in seconds
    """
    environment = environment or os.getenv("TRADING_ENVIRONMENT", "development")
    metrics_port = metrics_port or int(os.getenv("METRICS_PORT", "8000"))
    
    registry = get_metrics_registry()
    registry.configure(
        service_name=service_name,
        service_version=service_version,
        environment=environment,
        metrics_port=metrics_port,
        enable_auto_metrics=enable_auto_metrics,
        collection_interval=collection_interval
    )

def get_registry() -> CollectorRegistry:
    """Get the global metrics registry."""
    registry = get_metrics_registry()
    return registry.get_registry()

# Convenience functions for creating metrics
def create_counter(name: str, description: str, labels: List[str] = None) -> Counter:
    """Create a counter metric."""
    return Counter(name, description, labels or [], registry=get_registry())

def create_histogram(name: str, description: str, labels: List[str] = None, buckets=None) -> Histogram:
    """Create a histogram metric."""
    return Histogram(name, description, labels or [], buckets=buckets, registry=get_registry())

def create_gauge(name: str, description: str, labels: List[str] = None) -> Gauge:
    """Create a gauge metric."""
    return Gauge(name, description, labels or [], registry=get_registry())

# Trading-specific metric recording functions
def record_trading_metric(
    metric_type: str,
    metric_name: str,
    value: float,
    labels: Dict[str, str] = None,
    agent_type: str = "unknown"
) -> None:
    """
    Record a trading business metric.
    
    Args:
        metric_type: Type of metric (trade, signal, risk, pnl)
        metric_name: Name of the specific metric
        value: Value to record
        labels: Additional labels
        agent_type: Type of agent recording the metric
    """
    labels = labels or {}
    labels["agent_type"] = agent_type
    
    full_metric_name = f"trading_{metric_type}_{metric_name}"
    
    if hasattr(_metrics_registry, "_trading_metrics"):
        if full_metric_name in _metrics_registry._trading_metrics:
            metric = _metrics_registry._trading_metrics[full_metric_name]
            if isinstance(metric, Counter):
                metric.labels(**labels).inc(value)
            elif isinstance(metric, Gauge):
                metric.labels(**labels).set(value)
            elif isinstance(metric, Histogram):
                metric.labels(**labels).observe(value)

def record_agent_metric(
    metric_name: str,
    value: float,
    labels: Dict[str, str] = None,
    agent_type: str = "unknown"
) -> None:
    """
    Record an agent-specific metric.
    
    Args:
        metric_name: Name of the metric
        value: Value to record
        labels: Additional labels
        agent_type: Type of agent
    """
    labels = labels or {}
    labels["agent_type"] = agent_type
    
    if hasattr(_metrics_registry, "_agent_metrics"):
        if metric_name in _metrics_registry._agent_metrics:
            metric = _metrics_registry._agent_metrics[metric_name]
            if isinstance(metric, Counter):
                metric.labels(**labels).inc(value)
            elif isinstance(metric, Gauge):
                metric.labels(**labels).set(value)
            elif isinstance(metric, Histogram):
                metric.labels(**labels).observe(value)

@contextmanager
def time_operation(operation_name: str, agent_type: str = "unknown", labels: Dict[str, str] = None):
    """
    Context manager to time operations and record as histogram.
    
    Args:
        operation_name: Name of the operation
        agent_type: Type of agent
        labels: Additional labels
        
    Example:
        with time_operation("risk_calculation", "risk-agent"):
            result = calculate_risk(position)
    """
    start_time = time.time()
    labels = labels or {}
    labels.update({"agent_type": agent_type, "operation": operation_name})
    
    try:
        yield
    finally:
        duration = time.time() - start_time
        
        # Record to appropriate histogram
        if hasattr(_metrics_registry, "_agent_metrics"):
            if "message_processing_duration" in _metrics_registry._agent_metrics:
                _metrics_registry._agent_metrics["message_processing_duration"].labels(**labels).observe(duration)

def shutdown_metrics() -> None:
    """Shutdown metrics collection."""
    _metrics_registry.shutdown()