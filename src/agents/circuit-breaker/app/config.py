"""
Configuration Management for Circuit Breaker Agent

Handles all configuration settings using Pydantic Settings with environment
variable support and validation.
"""

import os
from typing import List, Optional, Dict, Any
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class CircuitBreakerConfig(BaseSettings):
    """Circuit Breaker Agent Configuration"""
    
    # Service Information
    service_name: str = Field(default="circuit-breaker-agent")
    version: str = Field(default="0.1.0")
    environment: str = Field(default="development")
    
    # Server Configuration
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8001)
    workers: int = Field(default=1)
    
    # Database Configuration
    database_url: str = Field(default="postgresql://postgres:password@localhost:5432/trading_system")
    database_pool_size: int = Field(default=10)
    database_max_overflow: int = Field(default=20)
    
    # Redis Configuration
    redis_url: str = Field(default="redis://localhost:6379/0")
    redis_max_connections: int = Field(default=10)
    
    # Kafka Configuration
    kafka_bootstrap_servers: List[str] = Field(default=["localhost:9092"])
    kafka_group_id: str = Field(default="circuit-breaker-agent")
    kafka_auto_offset_reset: str = Field(default="latest")
    
    # Circuit Breaker Settings
    daily_drawdown_threshold: float = Field(default=0.05, description="5% daily drawdown threshold")
    max_drawdown_threshold: float = Field(default=0.08, description="8% max drawdown threshold")
    volatility_spike_threshold: float = Field(default=3.0, description="3 standard deviations")
    response_time_threshold: int = Field(default=100, description="Response time threshold in ms")
    
    # Breaker Timeout Settings (in seconds)
    agent_breaker_timeout: int = Field(default=30)
    account_breaker_timeout: int = Field(default=60)
    system_breaker_timeout: int = Field(default=300)
    
    # Error Rate Thresholds
    error_rate_threshold: float = Field(default=0.2, description="20% error rate threshold")
    consecutive_failures_limit: int = Field(default=5)
    
    # Monitoring Settings
    health_check_interval: int = Field(default=5, description="Health check interval in seconds")
    metrics_port: int = Field(default=8002)
    
    # Security Settings
    jwt_secret_key: str = Field(default="circuit-breaker-secret-key-change-in-production")
    jwt_algorithm: str = Field(default="HS256")
    jwt_expiration_hours: int = Field(default=24)
    
    # External Service URLs
    execution_engine_url: str = Field(default="http://localhost:8080")
    dashboard_url: str = Field(default="http://localhost:3000")
    
    # Observability
    enable_tracing: bool = Field(default=True)
    enable_metrics: bool = Field(default=True)
    log_level: str = Field(default="INFO")
    
    # WebSocket Settings
    websocket_heartbeat_interval: int = Field(default=30)
    websocket_max_connections: int = Field(default=100)
    
    class Config:
        env_prefix = "CIRCUIT_BREAKER_"
        case_sensitive = False
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    @validator("daily_drawdown_threshold", "max_drawdown_threshold")
    def validate_drawdown_thresholds(cls, v):
        if not 0 < v < 1:
            raise ValueError("Drawdown thresholds must be between 0 and 1")
        return v
    
    @validator("error_rate_threshold")
    def validate_error_rate(cls, v):
        if not 0 < v < 1:
            raise ValueError("Error rate threshold must be between 0 and 1")
        return v
    
    @validator("log_level")
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment.lower() == "production"
    
    @property
    def kafka_config(self) -> Dict[str, Any]:
        """Get Kafka configuration dictionary"""
        return {
            "bootstrap_servers": self.kafka_bootstrap_servers,
            "group_id": self.kafka_group_id,
            "auto_offset_reset": self.kafka_auto_offset_reset,
            "enable_auto_commit": True,
            "auto_commit_interval_ms": 1000,
            "session_timeout_ms": 30000,
            "heartbeat_interval_ms": 3000,
        }


# Global configuration instance
config = CircuitBreakerConfig()