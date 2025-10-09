"""
Configuration for Backtesting Service
"""

import os
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8090
    api_reload: bool = False

    # Database Configuration
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/trading_system"
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # OANDA API Configuration
    oanda_api_key: str = os.getenv("OANDA_API_KEY", "")
    oanda_account_ids: str = os.getenv("OANDA_ACCOUNT_IDS", "")
    oanda_api_url: str = "https://api-fxpractice.oanda.com"
    oanda_stream_url: str = "https://stream-fxpractice.oanda.com"

    # Data Collection Configuration
    instruments: list[str] = ["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "USD_CHF"]
    default_timeframe: str = "H1"  # 1-hour candles
    historical_data_years: int = 2  # Default 2 years of historical data
    tick_data_months: int = 6  # 6 months of tick data for slippage modeling

    # Data Quality Configuration
    max_gap_hours: int = 1  # Maximum acceptable gap in data
    outlier_std_threshold: float = 10.0  # Standard deviations for outlier detection
    data_refresh_interval_hours: int = 24  # Daily refresh

    # Performance Configuration
    query_timeout_seconds: int = 30
    max_candles_per_request: int = 5000  # OANDA limit

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
