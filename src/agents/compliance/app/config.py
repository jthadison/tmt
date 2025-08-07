"""
Configuration for Compliance Agent
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""
    
    # Service configuration
    service_name: str = "compliance-agent"
    service_port: int = 8003
    debug: bool = False
    
    # Database configuration
    database_url: str = "postgresql://postgres:password@localhost:5432/trading_system"
    
    # Kafka configuration
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_consumer_group: str = "compliance-agent"
    
    # Redis configuration (for caching)
    redis_url: str = "redis://localhost:6379"
    
    # External APIs
    economic_calendar_api_key: Optional[str] = None
    economic_calendar_url: str = "https://api.tradingeconomics.com"
    
    # Compliance settings
    validation_timeout_ms: int = 50  # Max time for validation
    warning_threshold_pct: float = 0.8  # Warning at 80% of limit
    critical_threshold_pct: float = 0.95  # Critical at 95% of limit
    
    # Monitoring
    prometheus_port: int = 9003
    enable_metrics: bool = True
    
    class Config:
        env_file = ".env"
        env_prefix = "COMPLIANCE_"


def get_settings() -> Settings:
    """Get application settings"""
    return Settings()