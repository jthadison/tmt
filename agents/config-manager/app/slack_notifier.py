"""
Slack Notification Service

Sends configuration change notifications to Slack channels.
"""

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime

try:
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError
    SLACK_AVAILABLE = True
except ImportError:
    SLACK_AVAILABLE = False
    logging.warning("slack_sdk not available - Slack notifications will be disabled")

from .models import TradingConfig, ValidationMetrics

logger = logging.getLogger(__name__)


class SlackNotifier:
    """
    Sends configuration change notifications to Slack

    Features:
    - Configuration change notifications
    - Rollback alerts
    - Validation metrics summary
    - Emergency notifications (high priority)
    """

    def __init__(
        self,
        webhook_url: Optional[str] = None,
        channel: Optional[str] = None
    ):
        """
        Initialize Slack notifier

        Args:
            webhook_url: Slack webhook URL (default: from SLACK_WEBHOOK_URL env)
            channel: Slack channel to post to (default: from SLACK_CHANNEL env)
        """
        self.webhook_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL")
        self.channel = channel or os.getenv("SLACK_CHANNEL", "#trading-config")
        self.enabled = bool(self.webhook_url) and SLACK_AVAILABLE

        if not self.enabled:
            logger.warning(
                "Slack notifications disabled (no webhook URL or slack_sdk not available)"
            )
        else:
            logger.info(f"Slack notifications enabled: channel={self.channel}")

    def send_config_change_notification(
        self,
        config: TradingConfig,
        activated: bool = False
    ):
        """
        Send configuration change notification

        Args:
            config: New configuration
            activated: Whether config was activated (vs. just proposed)
        """
        if not self.enabled:
            logger.debug("Slack notification skipped (disabled)")
            return

        try:
            # Build notification message
            action = "Activated" if activated else "Proposed"
            title = f":gear: Configuration {action}: v{config.version}"

            message = self._build_config_change_message(config, action)

            # Send to Slack
            self._send_message(title, message, color="#36a64f" if activated else "#439FE0")

            logger.info(f"Sent Slack notification: {action} v{config.version}")

        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")

    def send_rollback_notification(
        self,
        from_version: Optional[str],
        to_version: str,
        reason: str,
        emergency: bool = False
    ):
        """
        Send rollback notification

        Args:
            from_version: Version being rolled back from
            to_version: Version being rolled back to
            reason: Rollback reason
            emergency: Emergency rollback flag
        """
        if not self.enabled:
            return

        try:
            # Build notification message
            emoji = ":rotating_light:" if emergency else ":leftwards_arrow_with_hook:"
            title = f"{emoji} {'EMERGENCY ' if emergency else ''}Configuration Rollback"

            message = f"*From:* v{from_version or 'current'}\n"
            message += f"*To:* v{to_version}\n"
            message += f"*Reason:* {reason}\n"
            message += f"*Timestamp:* {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n"

            if emergency:
                message += "\n:warning: *This was an EMERGENCY rollback* :warning:"

            # Send to Slack with appropriate color
            color = "#ff0000" if emergency else "#ff9900"
            self._send_message(title, message, color=color)

            logger.info(f"Sent rollback notification: {to_version}")

        except Exception as e:
            logger.error(f"Failed to send rollback notification: {e}")

    def send_validation_failure_notification(
        self,
        version: str,
        errors: list[str]
    ):
        """
        Send validation failure notification

        Args:
            version: Version that failed validation
            errors: List of validation errors
        """
        if not self.enabled:
            return

        try:
            title = f":x: Configuration Validation Failed: v{version}"

            message = "*Validation Errors:*\n"
            for error in errors[:5]:  # Limit to first 5 errors
                message += f"• {error}\n"

            if len(errors) > 5:
                message += f"... and {len(errors) - 5} more errors"

            self._send_message(title, message, color="#ff0000")

            logger.info(f"Sent validation failure notification: v{version}")

        except Exception as e:
            logger.error(f"Failed to send validation failure notification: {e}")

    def send_constraint_violation_notification(
        self,
        version: str,
        violations: list[str]
    ):
        """
        Send constraint violation notification

        Args:
            version: Version with constraint violations
            violations: List of violations
        """
        if not self.enabled:
            return

        try:
            title = f":warning: Configuration Constraint Violations: v{version}"

            message = "*Violations:*\n"
            for violation in violations:
                message += f"• {violation}\n"

            self._send_message(title, message, color="#ff9900")

            logger.info(f"Sent constraint violation notification: v{version}")

        except Exception as e:
            logger.error(f"Failed to send constraint violation notification: {e}")

    def _build_config_change_message(
        self,
        config: TradingConfig,
        action: str
    ) -> str:
        """Build configuration change message"""

        message = f"*Version:* {config.version}\n"
        message += f"*Author:* {config.author}\n"
        message += f"*Effective:* {config.effective_date}\n"
        message += f"*Reason:* {config.reason}\n"

        # Validation metrics
        if config.validation:
            message += "\n*Validation Metrics:*\n"

            if config.validation.backtest_sharpe:
                message += f"• Backtest Sharpe: {config.validation.backtest_sharpe:.2f}\n"

            if config.validation.out_of_sample_sharpe:
                message += f"• Out-of-Sample Sharpe: {config.validation.out_of_sample_sharpe:.2f}\n"

            if config.validation.overfitting_score is not None:
                score = config.validation.overfitting_score
                emoji = ":white_check_mark:" if score < 0.25 else ":warning:"
                message += f"• Overfitting Score: {emoji} {score:.3f}\n"

            if config.validation.max_drawdown:
                message += f"• Max Drawdown: {config.validation.max_drawdown:.1%}\n"

            if config.validation.approved_by:
                message += f"\n*Approved by:* {config.validation.approved_by}\n"

        # Session parameter highlights
        message += "\n*Session Parameters:*\n"
        for session_name, session in list(config.session_parameters.items())[:3]:
            confidence_dev = session.confidence_threshold - config.baseline.confidence_threshold
            message += f"• *{session_name.title()}:* "
            message += f"Confidence {session.confidence_threshold:.0f}% "
            message += f"({confidence_dev:+.0f}%), "
            message += f"R:R {session.min_risk_reward:.1f}\n"

        if len(config.session_parameters) > 3:
            message += f"... and {len(config.session_parameters) - 3} more sessions\n"

        return message

    def _send_message(
        self,
        title: str,
        message: str,
        color: str = "#36a64f"
    ):
        """
        Send message to Slack

        Args:
            title: Message title
            message: Message body
            color: Sidebar color (#hex)
        """
        if not self.enabled:
            return

        try:
            import requests

            # Build Slack webhook payload
            payload = {
                "channel": self.channel,
                "username": "Config Manager",
                "icon_emoji": ":gear:",
                "attachments": [
                    {
                        "color": color,
                        "title": title,
                        "text": message,
                        "footer": "Trading System Configuration Manager",
                        "footer_icon": "https://platform.slack-edge.com/img/default_application_icon.png",
                        "ts": int(datetime.utcnow().timestamp())
                    }
                ]
            }

            # Send POST request to webhook
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )

            response.raise_for_status()

            logger.debug(f"Slack message sent: {title}")

        except Exception as e:
            logger.error(f"Failed to send Slack message: {e}")
            raise


def send_notification(
    message: str,
    level: str = "info",
    webhook_url: Optional[str] = None
):
    """
    Standalone function to send a simple notification

    Args:
        message: Message to send
        level: Notification level (info, warning, error)
        webhook_url: Slack webhook URL
    """
    notifier = SlackNotifier(webhook_url=webhook_url)

    color_map = {
        "info": "#36a64f",
        "warning": "#ff9900",
        "error": "#ff0000"
    }

    emoji_map = {
        "info": ":information_source:",
        "warning": ":warning:",
        "error": ":x:"
    }

    title = f"{emoji_map.get(level, ':gear:')} Configuration Alert"
    color = color_map.get(level, "#36a64f")

    notifier._send_message(title, message, color=color)
