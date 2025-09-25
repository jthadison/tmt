"""
Alert Schedule Configuration

Provides configurable schedule times for performance alerts
with environment variable overrides and validation.
"""

import os
from datetime import time
from typing import Dict, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class AlertScheduleConfig:
    """Configuration for alert schedule times"""

    # Daily P&L check time (default: 17:00 UTC - NY market close)
    daily_pnl_hour: int = 17
    daily_pnl_minute: int = 0

    # Weekly stability check (default: Monday 08:00 UTC)
    weekly_stability_hour: int = 8
    weekly_stability_minute: int = 0
    weekly_stability_day: str = "monday"  # Day of week

    # Monthly forward test update (default: 1st of month 09:00 UTC)
    monthly_forward_hour: int = 9
    monthly_forward_minute: int = 0
    monthly_forward_day: int = 1  # Day of month

    # Performance threshold checks (default: 12:00 and 22:00 UTC)
    threshold_check_1_hour: int = 12
    threshold_check_1_minute: int = 0
    threshold_check_2_hour: int = 22
    threshold_check_2_minute: int = 0

    # Retry configuration
    max_retry_attempts: int = 3
    retry_delay_seconds: int = 60
    retry_backoff_multiplier: float = 2.0

    # Alert suppression configuration
    suppress_similar_alerts_minutes: int = 60
    escalation_delay_minutes: int = 15

    @classmethod
    def from_environment(cls) -> 'AlertScheduleConfig':
        """
        Load configuration from environment variables.

        Environment variables format:
        - ALERT_DAILY_PNL_TIME="17:00"
        - ALERT_WEEKLY_STABILITY_TIME="08:00"
        - ALERT_WEEKLY_STABILITY_DAY="monday"
        - ALERT_MONTHLY_FORWARD_TIME="09:00"
        - ALERT_MONTHLY_FORWARD_DAY="1"
        - ALERT_THRESHOLD_TIME_1="12:00"
        - ALERT_THRESHOLD_TIME_2="22:00"
        - ALERT_MAX_RETRY_ATTEMPTS="3"
        - ALERT_RETRY_DELAY_SECONDS="60"
        """
        config = cls()

        # Parse daily P&L time
        daily_pnl_time = os.getenv("ALERT_DAILY_PNL_TIME", "17:00")
        config.daily_pnl_hour, config.daily_pnl_minute = cls._parse_time(daily_pnl_time, "daily P&L")

        # Parse weekly stability time and day
        weekly_time = os.getenv("ALERT_WEEKLY_STABILITY_TIME", "08:00")
        config.weekly_stability_hour, config.weekly_stability_minute = cls._parse_time(weekly_time, "weekly stability")
        config.weekly_stability_day = os.getenv("ALERT_WEEKLY_STABILITY_DAY", "monday").lower()

        # Parse monthly forward test time and day
        monthly_time = os.getenv("ALERT_MONTHLY_FORWARD_TIME", "09:00")
        config.monthly_forward_hour, config.monthly_forward_minute = cls._parse_time(monthly_time, "monthly forward")
        config.monthly_forward_day = int(os.getenv("ALERT_MONTHLY_FORWARD_DAY", "1"))

        # Parse threshold check times
        threshold_1 = os.getenv("ALERT_THRESHOLD_TIME_1", "12:00")
        config.threshold_check_1_hour, config.threshold_check_1_minute = cls._parse_time(threshold_1, "threshold 1")

        threshold_2 = os.getenv("ALERT_THRESHOLD_TIME_2", "22:00")
        config.threshold_check_2_hour, config.threshold_check_2_minute = cls._parse_time(threshold_2, "threshold 2")

        # Parse retry configuration
        config.max_retry_attempts = int(os.getenv("ALERT_MAX_RETRY_ATTEMPTS", "3"))
        config.retry_delay_seconds = int(os.getenv("ALERT_RETRY_DELAY_SECONDS", "60"))
        config.retry_backoff_multiplier = float(os.getenv("ALERT_RETRY_BACKOFF_MULTIPLIER", "2.0"))

        # Parse suppression configuration
        config.suppress_similar_alerts_minutes = int(
            os.getenv("ALERT_SUPPRESS_SIMILAR_MINUTES", "60")
        )
        config.escalation_delay_minutes = int(
            os.getenv("ALERT_ESCALATION_DELAY_MINUTES", "15")
        )

        # Validate configuration
        config.validate()

        logger.info(f"Loaded alert schedule configuration from environment")
        return config

    @staticmethod
    def _parse_time(time_str: str, name: str) -> tuple[int, int]:
        """Parse time string in HH:MM format"""
        try:
            parts = time_str.strip().split(":")
            if len(parts) != 2:
                raise ValueError(f"Invalid time format for {name}: {time_str}")

            hour = int(parts[0])
            minute = int(parts[1])

            if not (0 <= hour <= 23):
                raise ValueError(f"Invalid hour for {name}: {hour}")
            if not (0 <= minute <= 59):
                raise ValueError(f"Invalid minute for {name}: {minute}")

            return hour, minute

        except Exception as e:
            logger.error(f"Error parsing time for {name}: {e}")
            raise ValueError(f"Invalid time format for {name}: {time_str}. Use HH:MM format.")

    def validate(self):
        """Validate configuration values"""
        # Validate day of week
        valid_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        if self.weekly_stability_day not in valid_days:
            raise ValueError(f"Invalid weekly day: {self.weekly_stability_day}")

        # Validate day of month
        if not (1 <= self.monthly_forward_day <= 31):
            raise ValueError(f"Invalid monthly day: {self.monthly_forward_day}")

        # Validate retry configuration
        if self.max_retry_attempts < 0:
            raise ValueError(f"Invalid max retry attempts: {self.max_retry_attempts}")
        if self.retry_delay_seconds < 0:
            raise ValueError(f"Invalid retry delay: {self.retry_delay_seconds}")
        if self.retry_backoff_multiplier < 1.0:
            raise ValueError(f"Invalid backoff multiplier: {self.retry_backoff_multiplier}")

    def get_daily_pnl_time(self) -> time:
        """Get daily P&L check time"""
        return time(self.daily_pnl_hour, self.daily_pnl_minute)

    def get_weekly_stability_time(self) -> time:
        """Get weekly stability check time"""
        return time(self.weekly_stability_hour, self.weekly_stability_minute)

    def get_monthly_forward_time(self) -> time:
        """Get monthly forward test time"""
        return time(self.monthly_forward_hour, self.monthly_forward_minute)

    def get_threshold_time_1(self) -> time:
        """Get first threshold check time"""
        return time(self.threshold_check_1_hour, self.threshold_check_1_minute)

    def get_threshold_time_2(self) -> time:
        """Get second threshold check time"""
        return time(self.threshold_check_2_hour, self.threshold_check_2_minute)

    def to_dict(self) -> Dict:
        """Convert configuration to dictionary"""
        return {
            "daily_pnl_time": f"{self.daily_pnl_hour:02d}:{self.daily_pnl_minute:02d}",
            "weekly_stability_time": f"{self.weekly_stability_hour:02d}:{self.weekly_stability_minute:02d}",
            "weekly_stability_day": self.weekly_stability_day,
            "monthly_forward_time": f"{self.monthly_forward_hour:02d}:{self.monthly_forward_minute:02d}",
            "monthly_forward_day": self.monthly_forward_day,
            "threshold_check_1_time": f"{self.threshold_check_1_hour:02d}:{self.threshold_check_1_minute:02d}",
            "threshold_check_2_time": f"{self.threshold_check_2_hour:02d}:{self.threshold_check_2_minute:02d}",
            "retry_config": {
                "max_attempts": self.max_retry_attempts,
                "delay_seconds": self.retry_delay_seconds,
                "backoff_multiplier": self.retry_backoff_multiplier
            },
            "suppression_config": {
                "suppress_similar_minutes": self.suppress_similar_alerts_minutes,
                "escalation_delay_minutes": self.escalation_delay_minutes
            }
        }

    def __repr__(self) -> str:
        return f"AlertScheduleConfig(daily={self.daily_pnl_hour:02d}:{self.daily_pnl_minute:02d}, " \
               f"weekly={self.weekly_stability_day} {self.weekly_stability_hour:02d}:{self.weekly_stability_minute:02d}, " \
               f"monthly={self.monthly_forward_day} {self.monthly_forward_hour:02d}:{self.monthly_forward_minute:02d})"


# Global configuration instance
_schedule_config: Optional[AlertScheduleConfig] = None


def get_schedule_config() -> AlertScheduleConfig:
    """Get global schedule configuration instance"""
    global _schedule_config
    if _schedule_config is None:
        _schedule_config = AlertScheduleConfig.from_environment()
    return _schedule_config


def reset_schedule_config():
    """Reset schedule configuration (useful for testing)"""
    global _schedule_config
    _schedule_config = None