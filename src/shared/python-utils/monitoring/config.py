"""
Configuration for the Trading Management System observability stack.

This module provides configuration management for OpenTelemetry tracing,
Prometheus metrics, and structured logging with environment-specific
optimizations for development, staging, and production environments.
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

class Environment(Enum):
    DEVELOPMENT = "development"
    STAGING = "staging" 
    PRODUCTION = "production"

class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

@dataclass
class TracingConfig:
    """OpenTelemetry tracing configuration."""
    
    # Basic configuration
    enabled: bool = True
    service_name: str = "trading-agent"
    service_version: str = "1.0.0"
    environment: Environment = Environment.DEVELOPMENT
    
    # Sampling configuration for performance optimization
    sampling_rate: float = 1.0  # 100% sampling by default
    
    # Export configuration
    jaeger_endpoint: Optional[str] = None
    otlp_endpoint: Optional[str] = None
    export_console: bool = False
    
    # Performance tuning
    max_span_attributes: int = 128
    max_span_events: int = 128
    max_span_links: int = 128
    span_processor_batch_size: int = 512
    span_processor_export_timeout_ms: int = 30000
    
    @classmethod
    def from_environment(cls, service_name: str) -> 'TracingConfig':
        """Create tracing configuration from environment variables."""
        env_str = os.getenv("TRADING_ENVIRONMENT", "development").lower()
        try:
            environment = Environment(env_str)
        except ValueError:
            environment = Environment.DEVELOPMENT
        
        # Environment-specific sampling rates
        sampling_rates = {
            Environment.DEVELOPMENT: 1.0,      # 100% - full tracing for debugging
            Environment.STAGING: 0.5,         # 50% - balanced visibility and performance
            Environment.PRODUCTION: 0.1       # 10% - minimal overhead for production
        }
        
        # Critical trading operations always get 100% sampling in production
        if "circuit-breaker" in service_name.lower():
            base_sampling_rate = 1.0  # Always trace circuit breaker
        elif "risk" in service_name.lower():
            base_sampling_rate = sampling_rates.get(environment, 0.1) * 2  # Higher for risk systems
        elif "execution" in service_name.lower():
            base_sampling_rate = sampling_rates.get(environment, 0.1) * 3  # Highest for execution
        else:
            base_sampling_rate = sampling_rates.get(environment, 1.0)
        
        # Override with explicit environment variable
        sampling_rate = float(os.getenv("OTEL_TRACES_SAMPLER_ARG", str(base_sampling_rate)))
        
        return cls(
            enabled=os.getenv("OTEL_TRACING_ENABLED", "true").lower() == "true",
            service_name=service_name,
            service_version=os.getenv("SERVICE_VERSION", "1.0.0"),
            environment=environment,
            sampling_rate=max(0.0, min(1.0, sampling_rate)),  # Clamp between 0 and 1
            jaeger_endpoint=os.getenv("OTEL_EXPORTER_JAEGER_ENDPOINT", "jaeger:14268"),
            otlp_endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
            export_console=os.getenv("OTEL_EXPORTER_CONSOLE", "false").lower() == "true",
            max_span_attributes=int(os.getenv("OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT", "128")),
            max_span_events=int(os.getenv("OTEL_SPAN_EVENT_COUNT_LIMIT", "128")),
            max_span_links=int(os.getenv("OTEL_SPAN_LINK_COUNT_LIMIT", "128")),
            span_processor_batch_size=int(os.getenv("OTEL_BSP_MAX_EXPORT_BATCH_SIZE", "512")),
            span_processor_export_timeout_ms=int(os.getenv("OTEL_BSP_EXPORT_TIMEOUT", "30000"))
        )

@dataclass
class MetricsConfig:
    """Prometheus metrics configuration."""
    
    # Basic configuration
    enabled: bool = True
    service_name: str = "trading-agent"
    environment: Environment = Environment.DEVELOPMENT
    
    # HTTP server configuration
    metrics_port: int = 8000
    metrics_path: str = "/metrics"
    
    # Collection configuration
    enable_auto_metrics: bool = True
    collection_interval: int = 10  # seconds
    
    # Performance configuration
    enable_gc_metrics: bool = True
    enable_process_metrics: bool = True
    metric_retention_seconds: int = 300  # 5 minutes
    
    @classmethod
    def from_environment(cls, service_name: str) -> 'MetricsConfig':
        """Create metrics configuration from environment variables."""
        env_str = os.getenv("TRADING_ENVIRONMENT", "development").lower()
        try:
            environment = Environment(env_str)
        except ValueError:
            environment = Environment.DEVELOPMENT
        
        # Environment-specific collection intervals
        collection_intervals = {
            Environment.DEVELOPMENT: 5,    # More frequent for debugging
            Environment.STAGING: 10,      # Balanced
            Environment.PRODUCTION: 15    # Less frequent for performance
        }
        
        return cls(
            enabled=os.getenv("METRICS_ENABLED", "true").lower() == "true",
            service_name=service_name,
            environment=environment,
            metrics_port=int(os.getenv("METRICS_PORT", "8000")),
            metrics_path=os.getenv("METRICS_PATH", "/metrics"),
            enable_auto_metrics=os.getenv("METRICS_AUTO_COLLECT", "true").lower() == "true",
            collection_interval=int(os.getenv(
                "METRICS_COLLECTION_INTERVAL",
                str(collection_intervals.get(environment, 10))
            )),
            enable_gc_metrics=os.getenv("METRICS_GC_ENABLED", "true").lower() == "true",
            enable_process_metrics=os.getenv("METRICS_PROCESS_ENABLED", "true").lower() == "true",
            metric_retention_seconds=int(os.getenv("METRICS_RETENTION_SECONDS", "300"))
        )

@dataclass  
class LoggingConfig:
    """Structured logging configuration."""
    
    # Basic configuration
    enabled: bool = True
    service_name: str = "trading-agent"
    environment: Environment = Environment.DEVELOPMENT
    
    # Log levels
    level: LogLevel = LogLevel.INFO
    structured_format: bool = True
    
    # Output configuration
    output_console: bool = True
    output_file: Optional[str] = None
    
    # Correlation and context
    include_correlation_id: bool = True
    include_trace_id: bool = True
    include_span_id: bool = True
    
    # Performance
    async_logging: bool = True
    buffer_size: int = 1000
    
    @classmethod
    def from_environment(cls, service_name: str) -> 'LoggingConfig':
        """Create logging configuration from environment variables."""
        env_str = os.getenv("TRADING_ENVIRONMENT", "development").lower()
        try:
            environment = Environment(env_str)
        except ValueError:
            environment = Environment.DEVELOPMENT
        
        # Environment-specific log levels
        log_levels = {
            Environment.DEVELOPMENT: LogLevel.DEBUG,
            Environment.STAGING: LogLevel.INFO,
            Environment.PRODUCTION: LogLevel.WARNING
        }
        
        level_str = os.getenv("LOG_LEVEL", log_levels.get(environment, LogLevel.INFO).value)
        try:
            level = LogLevel(level_str.upper())
        except ValueError:
            level = LogLevel.INFO
        
        return cls(
            enabled=os.getenv("LOGGING_ENABLED", "true").lower() == "true",
            service_name=service_name,
            environment=environment,
            level=level,
            structured_format=os.getenv("LOG_STRUCTURED", "true").lower() == "true",
            output_console=os.getenv("LOG_OUTPUT_CONSOLE", "true").lower() == "true",
            output_file=os.getenv("LOG_OUTPUT_FILE"),
            include_correlation_id=os.getenv("LOG_INCLUDE_CORRELATION_ID", "true").lower() == "true",
            include_trace_id=os.getenv("LOG_INCLUDE_TRACE_ID", "true").lower() == "true",
            include_span_id=os.getenv("LOG_INCLUDE_SPAN_ID", "true").lower() == "true",
            async_logging=os.getenv("LOG_ASYNC", "true").lower() == "true",
            buffer_size=int(os.getenv("LOG_BUFFER_SIZE", "1000"))
        )

@dataclass
class ObservabilityConfig:
    """Complete observability configuration for a trading service."""
    
    tracing: TracingConfig = field(default_factory=lambda: TracingConfig())
    metrics: MetricsConfig = field(default_factory=lambda: MetricsConfig()) 
    logging: LoggingConfig = field(default_factory=lambda: LoggingConfig())
    
    @classmethod
    def for_service(cls, service_name: str) -> 'ObservabilityConfig':
        """Create complete observability configuration for a service."""
        return cls(
            tracing=TracingConfig.from_environment(service_name),
            metrics=MetricsConfig.from_environment(service_name),
            logging=LoggingConfig.from_environment(service_name)
        )

# Pre-defined configurations for different trading system components
class ServiceConfigs:
    """Pre-defined configurations for different trading system components."""
    
    @staticmethod
    def circuit_breaker_agent() -> ObservabilityConfig:
        """Configuration for Circuit Breaker Agent - maximum observability."""
        config = ObservabilityConfig.for_service("circuit-breaker-agent")
        # Always trace circuit breaker operations
        config.tracing.sampling_rate = 1.0
        # Frequent metrics collection for safety monitoring
        config.metrics.collection_interval = 5
        # Debug level logging for safety-critical operations
        config.logging.level = LogLevel.DEBUG if config.logging.environment == Environment.DEVELOPMENT else LogLevel.INFO
        return config
    
    @staticmethod
    def risk_management_agent() -> ObservabilityConfig:
        """Configuration for Risk Management Agent - high observability."""
        config = ObservabilityConfig.for_service("risk-management-agent")
        # High sampling rate for risk operations
        config.tracing.sampling_rate = max(0.5, config.tracing.sampling_rate)
        # Frequent metrics collection
        config.metrics.collection_interval = 10
        return config
    
    @staticmethod
    def execution_engine() -> ObservabilityConfig:
        """Configuration for Execution Engine - performance-optimized observability."""
        config = ObservabilityConfig.for_service("execution-engine")
        # High sampling for execution tracing
        config.tracing.sampling_rate = max(0.3, config.tracing.sampling_rate)
        # Fast metrics collection for latency monitoring
        config.metrics.collection_interval = 5
        # Smaller batch sizes for low latency
        config.tracing.span_processor_batch_size = 128
        config.tracing.span_processor_export_timeout_ms = 10000
        return config
    
    @staticmethod
    def market_analysis_agent() -> ObservabilityConfig:
        """Configuration for Market Analysis Agent - balanced observability."""
        config = ObservabilityConfig.for_service("market-analysis-agent")
        # Standard sampling rate
        config.metrics.collection_interval = 15
        return config
    
    @staticmethod
    def dashboard() -> ObservabilityConfig:
        """Configuration for Dashboard - user-facing observability."""
        config = ObservabilityConfig.for_service("dashboard")
        # Lower sampling rate for UI operations
        if config.tracing.environment == Environment.PRODUCTION:
            config.tracing.sampling_rate = 0.1
        # Less frequent metrics collection
        config.metrics.collection_interval = 30
        return config

def get_service_config(service_name: str) -> ObservabilityConfig:
    """
    Get observability configuration for a service.
    
    Args:
        service_name: Name of the service
        
    Returns:
        ObservabilityConfig: Configuration optimized for the service
    """
    service_configs = {
        "circuit-breaker-agent": ServiceConfigs.circuit_breaker_agent,
        "circuit-breaker": ServiceConfigs.circuit_breaker_agent,
        "risk-management-agent": ServiceConfigs.risk_management_agent,
        "risk-management": ServiceConfigs.risk_management_agent,
        "execution-engine": ServiceConfigs.execution_engine,
        "execution": ServiceConfigs.execution_engine,
        "market-analysis-agent": ServiceConfigs.market_analysis_agent,
        "market-analysis": ServiceConfigs.market_analysis_agent,
        "dashboard": ServiceConfigs.dashboard
    }
    
    # Find matching configuration
    for key, config_func in service_configs.items():
        if key in service_name.lower():
            return config_func()
    
    # Default configuration
    return ObservabilityConfig.for_service(service_name)