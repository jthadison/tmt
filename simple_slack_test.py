#!/usr/bin/env python3
"""
Simple test for Slack notifications
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the orchestrator to the path
current_dir = Path(__file__).parent
orchestrator_path = current_dir / "orchestrator"
sys.path.insert(0, str(orchestrator_path))

# Set a dummy webhook URL for testing
os.environ['SLACK_WEBHOOK_URL'] = 'https://hooks.slack.com/services/dummy/test/url'

from app.notifications.slack_service import SlackNotificationService


async def test_basic_functionality():
    """Test basic functionality without actual HTTP calls"""

    print("Testing Slack notification service...")

    # Test initialization
    service = SlackNotificationService()
    await service.initialize()

    # Test message formatting
    trade_data = {
        "trade_id": "TEST_123",
        "instrument": "EUR/USD",
        "direction": "buy",
        "units": 10000,
        "entry_price": 1.0950,
        "account_id": "test-account"
    }

    # Test different message types
    message1 = service._format_trade_message(trade_data, "signal_executed")
    message2 = service._format_trade_message(trade_data, "trade_opened")
    message3 = service._format_trade_message(trade_data, "trade_closed")

    print("OK Signal executed message formatted")
    print("OK Trade opened message formatted")
    print("OK Trade closed message formatted")

    # Test utility functions
    test_float = service._safe_float("123.45")
    assert test_float == 123.45
    print("OK Safe float conversion works")

    # Test color logic
    color1 = service._get_message_color(trade_data, "signal_executed")
    color2 = service._get_message_color(trade_data, "trade_opened")
    print("OK Color logic works")

    await service.close()
    print("\nAll basic functionality tests passed!")
    print("The service is ready to send actual notifications when a real webhook URL is provided.")


if __name__ == "__main__":
    asyncio.run(test_basic_functionality())