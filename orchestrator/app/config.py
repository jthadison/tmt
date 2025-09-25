"""
Configuration management for the Trading System Orchestrator
"""

import os
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application settings
    app_name: str = "TMT Trading System Orchestrator"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    
    # OANDA configuration
    oanda_api_key: str = Field(..., env="OANDA_API_KEY")
    oanda_account_ids: str = Field(..., env="OANDA_ACCOUNT_IDS")
    oanda_environment: str = Field("practice", env="OANDA_ENVIRONMENT")
    oanda_base_url: str = Field("https://api-fxpractice.oanda.com", env="OANDA_BASE_URL")
    oanda_stream_url: str = Field("https://stream-fxpractice.oanda.com", env="OANDA_STREAM_URL")
    
    # Agent discovery and management
    agent_discovery_port: int = Field(8000, env="AGENT_DISCOVERY_PORT")
    agent_health_check_interval: int = Field(30, env="AGENT_HEALTH_CHECK_INTERVAL")
    agent_startup_timeout: int = Field(60, env="AGENT_STARTUP_TIMEOUT")
    agent_request_timeout: int = Field(10, env="AGENT_REQUEST_TIMEOUT")

    # Trade synchronization settings
    trade_sync_interval: int = Field(30, env="TRADE_SYNC_INTERVAL")
    trade_reconciliation_interval_hours: int = Field(1, env="TRADE_RECONCILIATION_INTERVAL_HOURS")
    trade_sync_auto_fix: bool = Field(True, env="TRADE_SYNC_AUTO_FIX")
    trade_sync_fast_on_trade: bool = Field(True, env="TRADE_SYNC_FAST_ON_TRADE")
    trade_sync_max_retries: int = Field(3, env="TRADE_SYNC_MAX_RETRIES")
    trade_sync_base_backoff: float = Field(1.0, env="TRADE_SYNC_BASE_BACKOFF")
    
    # Trading risk management
    max_concurrent_trades: int = Field(3, env="MAX_CONCURRENT_TRADES")
    risk_per_trade: float = Field(0.02, env="RISK_PER_TRADE")
    max_daily_loss: float = Field(0.06, env="MAX_DAILY_LOSS")
    circuit_breaker_threshold: float = Field(0.10, env="CIRCUIT_BREAKER_THRESHOLD")
    
    # Advanced position sizing
    max_position_concentration: float = Field(0.30, env="MAX_POSITION_CONCENTRATION")
    emergency_concentration_threshold: float = Field(0.50, env="EMERGENCY_CONCENTRATION_THRESHOLD")
    portfolio_heat_threshold: float = Field(0.15, env="PORTFOLIO_HEAT_THRESHOLD")
    min_margin_buffer: float = Field(5000.0, env="MIN_MARGIN_BUFFER")
    
    # Safety settings
    emergency_close_positions: bool = Field(True, env="EMERGENCY_CLOSE_POSITIONS")
    max_position_size: float = Field(100000.0, env="MAX_POSITION_SIZE")
    max_trades_per_hour: int = Field(10, env="MAX_TRADES_PER_HOUR")
    
    # Trading control
    enable_trading: bool = Field(True, env="ENABLE_TRADING")
    
    # Message broker configuration
    message_broker_url: str = Field("redis://localhost:6379", env="MESSAGE_BROKER_URL")
    event_retention_hours: int = Field(24, env="EVENT_RETENTION_HOURS")
    
    # Database configuration
    database_url: str = Field("postgresql://user:pass@localhost/trading_system", env="DATABASE_URL")
    timescale_url: str = Field("postgresql://user:pass@localhost/market_data", env="TIMESCALE_URL")
    
    # Monitoring and metrics
    metrics_enabled: bool = Field(True, env="METRICS_ENABLED")
    health_check_interval: int = Field(30, env="HEALTH_CHECK_INTERVAL")
    prometheus_port: int = Field(9090, env="PROMETHEUS_PORT")
    
    # Security settings
    jwt_secret_key: str = Field("your-secret-key", env="JWT_SECRET_KEY")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Agent endpoints (auto-discovered or configured)
    agent_endpoints: Dict[str, str] = Field(default_factory=lambda: {
        "market-analysis": "http://localhost:8001",
        "strategy-analysis": "http://localhost:8002",
        "parameter-optimization": "http://localhost:8003",
        "learning-safety": "http://localhost:8004",
        "disagreement-engine": "http://localhost:8005",
        "data-collection": "http://localhost:8006",
        "continuous-improvement": "http://localhost:8007",
        "pattern-detection": "http://localhost:8008"
    })
    
    # Trading hours (UTC)
    trading_hours: Dict[str, Any] = Field(default_factory=lambda: {
        "enabled": True,
        "start_hour": 0,  # Sunday 22:00 UTC (Monday open)
        "end_hour": 22,   # Friday 22:00 UTC (Friday close)
        "break_hours": [21, 22, 23],  # Daily break hours
        "holiday_calendar": "forex"
    })
    
    # Circuit breaker configuration
    circuit_breaker_config: Dict[str, Any] = Field(default_factory=lambda: {
        "account_loss_threshold": 0.05,  # 5% account loss
        "daily_loss_threshold": 0.03,    # 3% daily loss
        "consecutive_losses": 5,          # 5 consecutive losses
        "correlation_threshold": 0.8,     # 80% correlation between accounts
        "volatility_threshold": 2.0,      # 2x normal volatility
        "recovery_time_minutes": 30       # 30 minutes before retry
    })
    
    # Performance thresholds
    performance_thresholds: Dict[str, float] = Field(default_factory=lambda: {
        "max_latency_ms": 100.0,
        "min_win_rate": 0.5,
        "max_drawdown": 0.1,
        "min_profit_factor": 1.2,
        "max_correlation": 0.7
    })
    
    @validator("oanda_account_ids")
    def parse_account_ids(cls, v):
        """Parse comma-separated account IDs"""
        if isinstance(v, str):
            return [aid.strip() for aid in v.split(",") if aid.strip()]
        return v
    
    @validator("oanda_environment")
    def validate_environment(cls, v):
        """Validate OANDA environment"""
        if v not in ["practice", "live"]:
            raise ValueError("OANDA environment must be 'practice' or 'live'")
        return v
    
    @validator("risk_per_trade")
    def validate_risk_per_trade(cls, v):
        """Validate risk per trade is reasonable"""
        if not 0.001 <= v <= 0.1:
            raise ValueError("Risk per trade must be between 0.1% and 10%")
        return v
    
    @validator("max_daily_loss")
    def validate_max_daily_loss(cls, v):
        """Validate maximum daily loss is reasonable"""
        if not 0.01 <= v <= 0.5:
            raise ValueError("Max daily loss must be between 1% and 50%")
        return v
    
    @property
    def account_ids_list(self) -> List[str]:
        """Get OANDA account IDs as a list"""
        if isinstance(self.oanda_account_ids, list):
            return self.oanda_account_ids
        return [aid.strip() for aid in self.oanda_account_ids.split(",") if aid.strip()]
    
    @property
    def is_live_trading(self) -> bool:
        """Check if this is live trading environment"""
        return self.oanda_environment == "live"
    
    @property
    def oanda_api_url(self) -> str:
        """Get the appropriate OANDA API URL"""
        if self.oanda_environment == "live":
            return "https://api-fxtrade.oanda.com"
        return "https://api-fxpractice.oanda.com"
    
    @property
    def oanda_streaming_url(self) -> str:
        """Get the appropriate OANDA streaming URL"""
        if self.oanda_environment == "live":
            return "https://stream-fxtrade.oanda.com"
        return "https://stream-fxpractice.oanda.com"
    
    def get_agent_endpoint(self, agent_type: str) -> Optional[str]:
        """Get endpoint for specific agent type"""
        return self.agent_endpoints.get(agent_type)
    
    def get_circuit_breaker_threshold(self, breaker_type: str) -> float:
        """Get circuit breaker threshold for specific type"""
        return self.circuit_breaker_config.get(f"{breaker_type}_threshold", 0.05)
    
    def get_performance_threshold(self, metric: str) -> float:
        """Get performance threshold for specific metric"""
        return self.performance_thresholds.get(metric, 0.0)
    
    def is_trading_hours(self) -> bool:
        """Check if current time is within trading hours"""
        if not self.trading_hours.get("enabled", True):
            return False
        
        # TODO: Implement actual trading hours check
        # This is a simplified version
        from datetime import datetime
        now = datetime.utcnow()
        current_hour = now.hour
        
        # Simple check - avoid break hours
        break_hours = self.trading_hours.get("break_hours", [])
        return current_hour not in break_hours
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get application settings singleton"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """Reload settings from environment"""
    global _settings
    _settings = Settings()
    return _settings


# Development/testing configuration
class TestSettings(Settings):
    """Settings for testing environment"""
    
    debug: bool = True
    log_level: str = "DEBUG"
    
    # Use in-memory databases for testing
    database_url: str = "sqlite:///:memory:"
    message_broker_url: str = "redis://localhost:6379/1"  # Different Redis DB
    
    # Faster timeouts for testing
    agent_health_check_interval: int = 5
    agent_request_timeout: int = 2
    health_check_interval: int = 5
    
    # Lower risk limits for testing
    risk_per_trade: float = 0.001
    max_daily_loss: float = 0.01
    max_concurrent_trades: int = 1
    
    # Mock agent endpoints
    agent_endpoints: Dict[str, str] = Field(default_factory=lambda: {
        "market-analysis": "http://localhost:18001",
        "strategy-analysis": "http://localhost:18002",
        "parameter-optimization": "http://localhost:18003",
        "learning-safety": "http://localhost:18004",
        "disagreement-engine": "http://localhost:18005",
        "data-collection": "http://localhost:18006",
        "continuous-improvement": "http://localhost:18007",
        "pattern-detection": "http://localhost:18008"
    })


# Production configuration
class ProductionSettings(Settings):
    """Settings for production environment"""
    
    debug: bool = False
    log_level: str = "INFO"
    workers: int = 4
    
    # Production security
    jwt_secret_key: str = Field(..., env="JWT_SECRET_KEY")
    
    # Production performance
    agent_health_check_interval: int = 60
    health_check_interval: int = 60
    
    # Production safety
    emergency_close_positions: bool = True
    max_trades_per_hour: int = 5  # More conservative


def get_settings_for_environment(env: str = None) -> Settings:
    """Get settings for specific environment"""
    env = env or os.getenv("ENVIRONMENT", "development")
    
    if env == "test":
        return TestSettings()
    elif env == "production":
        return ProductionSettings()
    else:
        return Settings()