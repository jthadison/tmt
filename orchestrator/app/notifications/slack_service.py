"""
Slack Notification Service

Handles sending trade execution notifications to Slack via webhooks.
"""

import asyncio
import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime
from decimal import Decimal
import httpx

from ..config import get_settings

logger = logging.getLogger(__name__)


class SlackNotificationService:
    """Service for sending trade notifications to Slack"""

    def __init__(self, webhook_url: Optional[str] = None):
        self.settings = get_settings()
        self.webhook_url = webhook_url or self.settings.slack_webhook_url
        self.client: Optional[httpx.AsyncClient] = None
        self.notifications_enabled = self.settings.notifications_enabled

    async def initialize(self):
        """Initialize the Slack service"""
        if self.webhook_url and self.notifications_enabled:
            self.client = httpx.AsyncClient(timeout=10.0)
            logger.info("Slack notification service initialized")
        else:
            logger.info("Slack notifications disabled (no webhook URL or notifications disabled)")

    async def close(self):
        """Close the HTTP client"""
        if self.client:
            await self.client.aclose()
            self.client = None

    async def send_trade_notification(self, trade_data: Dict[str, Any], event_type: str):
        """Send a trade notification to Slack"""
        if not self._should_send_notification():
            return

        try:
            message = self._format_trade_message(trade_data, event_type)
            await self._send_slack_message(message)
            logger.info(f"Sent Slack notification for {event_type}: {trade_data.get('trade_id', 'unknown')}")
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")

    async def send_system_notification(self, title: str, message: str, color: str = "good"):
        """Send a general system notification to Slack"""
        if not self._should_send_notification():
            return

        try:
            slack_message = {
                "attachments": [
                    {
                        "color": color,
                        "title": title,
                        "text": message,
                        "ts": int(datetime.now().timestamp())
                    }
                ]
            }
            await self._send_slack_message(slack_message)
            logger.info(f"Sent system notification: {title}")
        except Exception as e:
            logger.error(f"Failed to send system notification: {e}")

    def _should_send_notification(self) -> bool:
        """Check if notifications should be sent"""
        return (
            self.notifications_enabled
            and self.webhook_url is not None
            and self.client is not None
        )

    def _format_trade_message(self, trade_data: Dict[str, Any], event_type: str) -> Dict[str, Any]:
        """Format trade data into a Slack message"""

        # Determine color based on event type and PnL
        color = self._get_message_color(trade_data, event_type)

        # Create main message
        if event_type == "trade_opened":
            title = "🚀 Trade Opened"
            fields = self._get_open_trade_fields(trade_data)
        elif event_type == "trade_closed":
            title = "🏁 Trade Closed"
            fields = self._get_closed_trade_fields(trade_data)
        elif event_type == "trade_updated":
            title = "📊 Trade Updated"
            fields = self._get_update_trade_fields(trade_data)
        elif event_type == "signal_executed":
            title = "⚡ Signal Executed"
            fields = self._get_signal_executed_fields(trade_data)
        else:
            title = f"📈 Trade Event: {event_type.title()}"
            fields = self._get_basic_trade_fields(trade_data)

        # Format timestamp
        timestamp = int(datetime.now().timestamp())

        return {
            "attachments": [
                {
                    "color": color,
                    "title": title,
                    "fields": fields,
                    "footer": "TMT Trading System",
                    "ts": timestamp
                }
            ]
        }

    def _get_message_color(self, trade_data: Dict[str, Any], event_type: str) -> str:
        """Determine message color based on trade data and event type"""
        if event_type == "trade_opened":
            return "#36a64f"  # Green
        elif event_type == "signal_executed":
            return "#ffaa00"  # Orange for signal execution
        elif event_type == "trade_closed":
            pnl = self._safe_float(trade_data.get("pnl_realized", 0))
            if pnl > 0:
                return "#36a64f"  # Green for profit
            elif pnl < 0:
                return "#ff0000"  # Red for loss
            else:
                return "#ffa500"  # Orange for breakeven
        else:
            return "#439fe0"  # Blue for updates/other

    def _get_open_trade_fields(self, trade_data: Dict[str, Any]) -> list:
        """Get fields for trade opened notification"""
        return [
            {
                "title": "Instrument",
                "value": trade_data.get("instrument", "N/A"),
                "short": True
            },
            {
                "title": "Direction",
                "value": trade_data.get("direction", "N/A").upper(),
                "short": True
            },
            {
                "title": "Units",
                "value": f"{trade_data.get('units', 0):,}",
                "short": True
            },
            {
                "title": "Entry Price",
                "value": f"{self._safe_float(trade_data.get('entry_price', 0)):.5f}",
                "short": True
            },
            {
                "title": "Stop Loss",
                "value": f"{self._safe_float(trade_data.get('stop_loss', 0)):.5f}" if trade_data.get('stop_loss') else "None",
                "short": True
            },
            {
                "title": "Take Profit",
                "value": f"{self._safe_float(trade_data.get('take_profit', 0)):.5f}" if trade_data.get('take_profit') else "None",
                "short": True
            },
            {
                "title": "Account",
                "value": trade_data.get("account_id", "N/A"),
                "short": False
            }
        ]

    def _get_closed_trade_fields(self, trade_data: Dict[str, Any]) -> list:
        """Get fields for trade closed notification"""
        pnl = self._safe_float(trade_data.get("pnl_realized", 0))
        pnl_emoji = "💰" if pnl > 0 else "💸" if pnl < 0 else "💸"

        return [
            {
                "title": "Instrument",
                "value": trade_data.get("instrument", "N/A"),
                "short": True
            },
            {
                "title": "Direction",
                "value": trade_data.get("direction", "N/A").upper(),
                "short": True
            },
            {
                "title": "Units",
                "value": f"{trade_data.get('units', 0):,}",
                "short": True
            },
            {
                "title": "Entry Price",
                "value": f"{self._safe_float(trade_data.get('entry_price', 0)):.5f}",
                "short": True
            },
            {
                "title": "Close Price",
                "value": f"{self._safe_float(trade_data.get('close_price', 0)):.5f}",
                "short": True
            },
            {
                "title": f"{pnl_emoji} Realized P&L",
                "value": f"${pnl:.2f}",
                "short": True
            },
            {
                "title": "Close Reason",
                "value": trade_data.get("close_reason", "Unknown"),
                "short": False
            }
        ]

    def _get_update_trade_fields(self, trade_data: Dict[str, Any]) -> list:
        """Get fields for trade updated notification"""
        unrealized_pnl = self._safe_float(trade_data.get("pnl_unrealized", 0))
        pnl_emoji = "📈" if unrealized_pnl > 0 else "📉" if unrealized_pnl < 0 else "📊"

        return [
            {
                "title": "Instrument",
                "value": trade_data.get("instrument", "N/A"),
                "short": True
            },
            {
                "title": "Direction",
                "value": trade_data.get("direction", "N/A").upper(),
                "short": True
            },
            {
                "title": f"{pnl_emoji} Unrealized P&L",
                "value": f"${unrealized_pnl:.2f}",
                "short": True
            },
            {
                "title": "Current Price",
                "value": f"{self._safe_float(trade_data.get('current_price', 0)):.5f}",
                "short": True
            }
        ]

    def _get_signal_executed_fields(self, trade_data: Dict[str, Any]) -> list:
        """Get fields for signal executed notification"""
        return [
            {
                "title": "Instrument",
                "value": trade_data.get("instrument", "N/A"),
                "short": True
            },
            {
                "title": "Direction",
                "value": trade_data.get("direction", "N/A").upper(),
                "short": True
            },
            {
                "title": "Units",
                "value": f"{trade_data.get('units', 0):,}",
                "short": True
            },
            {
                "title": "Signal ID",
                "value": trade_data.get("signal_id", "N/A"),
                "short": True
            },
            {
                "title": "Account",
                "value": trade_data.get("account_id", "N/A"),
                "short": False
            },
            {
                "title": "Status",
                "value": "🔄 Signal executed, waiting for trade confirmation...",
                "short": False
            }
        ]

    def _get_basic_trade_fields(self, trade_data: Dict[str, Any]) -> list:
        """Get basic fields for any trade event"""
        return [
            {
                "title": "Trade ID",
                "value": trade_data.get("trade_id", "N/A"),
                "short": True
            },
            {
                "title": "Instrument",
                "value": trade_data.get("instrument", "N/A"),
                "short": True
            },
            {
                "title": "Account",
                "value": trade_data.get("account_id", "N/A"),
                "short": False
            }
        ]

    def _safe_float(self, value: Any) -> float:
        """Safely convert value to float"""
        if value is None:
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except (ValueError, TypeError):
                return 0.0
        return 0.0

    async def _send_slack_message(self, message: Dict[str, Any]):
        """Send message to Slack webhook"""
        if not self.client or not self.webhook_url:
            return

        try:
            response = await self.client.post(
                self.webhook_url,
                json=message,
                headers={"Content-Type": "application/json"}
            )
            if response.status_code != 200:
                logger.error(f"Slack webhook error {response.status_code}: {response.text}")
            else:
                logger.debug("Slack message sent successfully")
        except httpx.TimeoutException:
            logger.error("Slack webhook request timed out")
        except Exception as e:
            logger.error(f"Error sending Slack message: {e}")

    async def send_startup_notification(self):
        """Send a notification when the trading system starts"""
        await self.send_system_notification(
            title="🚀 Trading System Started",
            message="TMT Trading System Orchestrator has started successfully and is monitoring for trade opportunities.",
            color="good"
        )

    async def send_shutdown_notification(self):
        """Send a notification when the trading system shuts down"""
        await self.send_system_notification(
            title="🛑 Trading System Stopped",
            message="TMT Trading System Orchestrator has been shut down.",
            color="warning"
        )

    async def send_error_notification(self, error_message: str, details: str = ""):
        """Send an error notification"""
        message = f"Error: {error_message}"
        if details:
            message += f"\n\nDetails: {details}"

        await self.send_system_notification(
            title="⚠️ System Error",
            message=message,
            color="danger"
        )


# Global instance
_slack_service: Optional[SlackNotificationService] = None


async def get_slack_service() -> SlackNotificationService:
    """Get the global Slack service instance"""
    global _slack_service
    if _slack_service is None:
        _slack_service = SlackNotificationService()
        await _slack_service.initialize()
    return _slack_service


async def send_trade_notification(trade_data: Dict[str, Any], event_type: str):
    """Convenience function to send trade notification"""
    service = await get_slack_service()
    await service.send_trade_notification(trade_data, event_type)


async def send_system_notification(title: str, message: str, color: str = "good"):
    """Convenience function to send system notification"""
    service = await get_slack_service()
    await service.send_system_notification(title, message, color)