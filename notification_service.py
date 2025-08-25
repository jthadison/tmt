#!/usr/bin/env python3
"""
Notification Service for Trading System
Supports Slack, Discord, and email notifications
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import aiohttp

logger = logging.getLogger(__name__)

class NotificationService:
    """Service for sending trading notifications"""
    
    def __init__(self):
        # Slack configuration
        self.slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        self.slack_channel = os.getenv("SLACK_CHANNEL", "#trading-alerts")
        
        # Discord configuration
        self.discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        
        # Email configuration (for future use)
        self.email_enabled = os.getenv("EMAIL_NOTIFICATIONS", "false").lower() == "true"
        
        # Notification settings
        self.notifications_enabled = os.getenv("NOTIFICATIONS_ENABLED", "true").lower() == "true"
        
        logger.info(f"Notification Service initialized - Enabled: {self.notifications_enabled}")
        if self.slack_webhook_url:
            logger.info("✅ Slack notifications configured")
        if self.discord_webhook_url:
            logger.info("✅ Discord notifications configured")
    
    async def send_trade_notification(self, trade_data: Dict[str, Any]):
        """Send notification about a trade"""
        if not self.notifications_enabled:
            return
        
        try:
            # Format trade message
            message = self._format_trade_message(trade_data)
            
            # Send to configured channels
            tasks = []
            
            if self.slack_webhook_url:
                tasks.append(self._send_slack_message(message, trade_data))
            
            if self.discord_webhook_url:
                tasks.append(self._send_discord_message(message, trade_data))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                
        except Exception as e:
            logger.error(f"Error sending trade notification: {e}")
    
    async def send_system_alert(self, alert_type: str, message: str, severity: str = "info"):
        """Send system alert notification"""
        if not self.notifications_enabled:
            return
        
        try:
            alert_message = self._format_system_alert(alert_type, message, severity)
            
            tasks = []
            
            if self.slack_webhook_url:
                tasks.append(self._send_slack_message(alert_message))
            
            if self.discord_webhook_url:
                tasks.append(self._send_discord_message(alert_message))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                
        except Exception as e:
            logger.error(f"Error sending system alert: {e}")
    
    def _format_trade_message(self, trade_data: Dict[str, Any]) -> str:
        """Format trade data into notification message"""
        success = trade_data.get("success", False)
        mode = trade_data.get("mode", "unknown")
        instrument = trade_data.get("instrument", "Unknown")
        fill_price = trade_data.get("fill_price", 0)
        units_filled = trade_data.get("units_filled", 0)
        stop_loss_set = trade_data.get("stop_loss_set", False)
        take_profit_set = trade_data.get("take_profit_set", False)
        
        if success:
            emoji = "✅" if units_filled > 0 else "📉"
            direction = "LONG" if units_filled > 0 else "SHORT"
            
            message = f"{emoji} **TRADE EXECUTED**\n"
            message += f"📊 **{instrument}** {direction}\n"
            message += f"💰 **Price**: {fill_price:.5f}\n"
            message += f"📏 **Size**: {abs(units_filled):,} units\n"
            message += f"🛡️ **Stop Loss**: {'✅' if stop_loss_set else '❌'}\n"
            message += f"🎯 **Take Profit**: {'✅' if take_profit_set else '❌'}\n"
            message += f"⚙️ **Mode**: {mode.upper()}\n"
            message += f"🕐 **Time**: {datetime.now().strftime('%H:%M:%S')}"
        else:
            message = f"❌ **TRADE FAILED**\n"
            message += f"📊 **{instrument}**\n"
            message += f"❗ **Error**: {trade_data.get('message', 'Unknown error')}\n"
            message += f"🕐 **Time**: {datetime.now().strftime('%H:%M:%S')}"
        
        return message
    
    def _format_system_alert(self, alert_type: str, message: str, severity: str) -> str:
        """Format system alert message"""
        emoji_map = {
            "info": "ℹ️",
            "warning": "⚠️", 
            "error": "❌",
            "critical": "🚨"
        }
        
        emoji = emoji_map.get(severity, "ℹ️")
        
        alert_message = f"{emoji} **SYSTEM ALERT**\n"
        alert_message += f"📋 **Type**: {alert_type}\n"
        alert_message += f"📝 **Message**: {message}\n"
        alert_message += f"⚡ **Severity**: {severity.upper()}\n"
        alert_message += f"🕐 **Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return alert_message
    
    async def _send_slack_message(self, message: str, trade_data: Dict = None):
        """Send message to Slack"""
        try:
            # Format for Slack
            payload = {
                "channel": self.slack_channel,
                "username": "TMT Trading Bot",
                "icon_emoji": ":robot_face:",
                "text": message
            }
            
            # Add rich formatting for trades
            if trade_data and trade_data.get("success"):
                payload["attachments"] = [{
                    "color": "good" if trade_data.get("success") else "danger",
                    "fields": [
                        {
                            "title": "Trade ID",
                            "value": trade_data.get("trade_id", "N/A"),
                            "short": True
                        },
                        {
                            "title": "Account",
                            "value": "OANDA Practice",
                            "short": True
                        }
                    ]
                }]
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.slack_webhook_url, json=payload) as response:
                    if response.status == 200:
                        logger.debug("Slack notification sent successfully")
                    else:
                        logger.error(f"Failed to send Slack notification: {response.status}")
                        
        except Exception as e:
            logger.error(f"Error sending Slack message: {e}")
    
    async def _send_discord_message(self, message: str, trade_data: Dict = None):
        """Send message to Discord"""
        try:
            # Format for Discord
            payload = {
                "username": "TMT Trading Bot",
                "avatar_url": "https://cdn.discordapp.com/emojis/robots.png",
                "content": message
            }
            
            # Add embed for trades
            if trade_data:
                success = trade_data.get("success", False)
                embed = {
                    "title": "Trade Execution" if success else "Trade Failed",
                    "color": 65280 if success else 16711680,  # Green or Red
                    "timestamp": datetime.now().isoformat(),
                    "fields": []
                }
                
                if success:
                    embed["fields"] = [
                        {"name": "Trade ID", "value": trade_data.get("trade_id", "N/A"), "inline": True},
                        {"name": "P&L", "value": f"${trade_data.get('pl', 0):.2f}", "inline": True}
                    ]
                
                payload["embeds"] = [embed]
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.discord_webhook_url, json=payload) as response:
                    if response.status == 204:  # Discord returns 204 for success
                        logger.debug("Discord notification sent successfully")
                    else:
                        logger.error(f"Failed to send Discord notification: {response.status}")
                        
        except Exception as e:
            logger.error(f"Error sending Discord message: {e}")

# Global instance
notification_service = NotificationService()

async def notify_trade(trade_data: Dict[str, Any]):
    """Convenience function to send trade notification"""
    await notification_service.send_trade_notification(trade_data)

async def notify_alert(alert_type: str, message: str, severity: str = "info"):
    """Convenience function to send system alert"""
    await notification_service.send_system_alert(alert_type, message, severity)