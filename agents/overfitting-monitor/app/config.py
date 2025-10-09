"""
Configuration for Overfitting Monitor Agent
"""

import os
from typing import Optional, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings"""

    # Service configuration
    service_name: str = "overfitting-monitor"
    port: int = Field(default=8010, env="PORT")
    host: str = Field(default="0.0.0.0", env="HOST")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    # Database
    database_url: str = Field(
        default="postgresql://postgres:password@localhost:5432/trading_system",
        env="DATABASE_URL"
    )

    # Baseline parameters
    baseline_confidence_threshold: float = Field(default=55.0)
    baseline_min_risk_reward: float = Field(default=1.8)
    baseline_vpa_threshold: float = Field(default=0.6)

    # Overfitting thresholds
    overfitting_warning_threshold: float = Field(default=0.3)
    overfitting_critical_threshold: float = Field(default=0.5)
    max_parameter_drift_pct: float = Field(default=15.0)

    # Performance degradation
    performance_degradation_threshold: float = Field(default=0.7)  # 70%
    rolling_performance_window_days: int = Field(default=7)

    # Expected backtest metrics
    expected_backtest_sharpe: float = Field(default=1.8)
    expected_backtest_win_rate: float = Field(default=60.0)
    expected_backtest_profit_factor: float = Field(default=2.0)

    # Alerts
    notifications_enabled: bool = Field(default=True, env="NOTIFICATIONS_ENABLED")
    slack_webhook_url: Optional[str] = Field(default=None, env="SLACK_WEBHOOK_URL")
    email_enabled: bool = Field(default=False, env="EMAIL_NOTIFICATIONS")
    sendgrid_api_key: Optional[str] = Field(default=None, env="SENDGRID_API_KEY")
    alert_recipients: str = Field(default="", env="ALERT_RECIPIENTS")  # Comma-separated

    # Monitoring schedule
    enable_scheduler: bool = Field(default=True)
    calculation_interval_minutes: int = Field(default=60)  # Hourly

    # API settings
    api_title: str = "Overfitting Monitor API"
    api_version: str = "1.0.0"
    api_description: str = "Real-time overfitting monitoring and alerting"

    # CORS
    cors_origins: str = Field(default="*", env="CORS_ORIGINS")

    class Config:
        env_file = ".env"
        case_sensitive = False

    def get_baseline_parameters(self) -> Dict[str, Any]:
        """
        Get baseline parameters as dictionary

        @returns: Baseline parameters
        """
        return {
            "confidence_threshold": self.baseline_confidence_threshold,
            "min_risk_reward": self.baseline_min_risk_reward,
            "vpa_threshold": self.baseline_vpa_threshold
        }

    def get_alert_recipients_list(self) -> list:
        """
        Get alert recipients as list

        @returns: List of email addresses
        """
        if not self.alert_recipients:
            return []
        return [email.strip() for email in self.alert_recipients.split(",")]


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get application settings (singleton)

    @returns: Settings instance
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
