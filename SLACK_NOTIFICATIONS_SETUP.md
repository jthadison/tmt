# Slack Notifications Setup Guide

## Overview

Your trading system now supports Slack notifications for trade events! You'll receive real-time notifications when:

- 🔄 **Signals are executed** (before trade opens)
- 🚀 **Trades are opened** (with entry details)
- 📊 **Trades are updated** (P&L changes)
- 🏁 **Trades are closed** (with final P&L)
- ⚠️ **System errors** occur
- 🚀 **System starts/stops**

## Setup Instructions

### 1. Create a Slack Webhook

1. Go to https://api.slack.com/apps
2. Click "Create New App" → "From scratch"
3. Name it "TMT Trading System" and select your workspace
4. Go to "Incoming Webhooks" → Enable webhooks
5. Click "Add New Webhook to Workspace"
6. Select the channel where you want notifications
7. Copy the webhook URL (looks like: `https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX`)

### 2. Configure the Trading System

Set the webhook URL as an environment variable:

**Windows (Command Prompt):**
```cmd
set SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

**Windows (PowerShell):**
```powershell
$env:SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
```

**Linux/Mac:**
```bash
export SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### 3. Optional: Disable Notifications

If you want to temporarily disable notifications without removing the webhook URL:

```cmd
set NOTIFICATIONS_ENABLED=false
```

## Test the Setup

Run the test script to verify everything works:

```bash
cd E:\projects\claude_code\prop-ai\tmt
python test_slack_notifications.py
```

## What You'll See

### Signal Executed Notification
```
⚡ Signal Executed
Instrument: EUR/USD
Direction: BUY
Units: 10,000
Status: 🔄 Signal executed, waiting for trade confirmation...
```

### Trade Opened Notification
```
🚀 Trade Opened
Instrument: EUR/USD
Direction: BUY
Units: 10,000
Entry Price: 1.09500
Stop Loss: 1.09000
Take Profit: 1.10000
```

### Trade Closed Notification (Profit)
```
🏁 Trade Closed
Instrument: EUR/USD
Direction: BUY
Entry Price: 1.09500
Close Price: 1.10000
💰 Realized P&L: $50.00
Close Reason: TAKE_PROFIT
```

### Trade Closed Notification (Loss)
```
🏁 Trade Closed
Instrument: GBP/USD
Direction: SELL
Entry Price: 1.25000
Close Price: 1.25200
💸 Realized P&L: -$10.00
Close Reason: STOP_LOSS
```

## Integration Points

The notifications are automatically sent from these components:

1. **Trade Sync Service** (`orchestrator/app/trade_sync/sync_service.py`)
   - Line 143: New trade opened
   - Line 154: Trade closed
   - Line 415: Signal executed

2. **Notification Service** (`orchestrator/app/notifications/slack_service.py`)
   - Formats and sends all notifications
   - Handles different event types
   - Manages HTTP client lifecycle

## Configuration Options

All settings are in `orchestrator/app/config.py`:

- `slack_webhook_url`: Your Slack webhook URL
- `notifications_enabled`: Enable/disable notifications (default: True)

## Troubleshooting

### No notifications appearing
1. Check the webhook URL is correct
2. Verify `SLACK_WEBHOOK_URL` environment variable is set
3. Ensure `NOTIFICATIONS_ENABLED` is not set to `false`
4. Check orchestrator logs for error messages

### Testing connectivity
Run the simple test:
```bash
python simple_slack_test.py
```

### Manual notification test
```python
import asyncio
import os
from orchestrator.app.notifications import send_system_notification

os.environ['SLACK_WEBHOOK_URL'] = 'your_webhook_url_here'

async def test():
    await send_system_notification("Test", "This is a test notification")

asyncio.run(test())
```

## Security Notes

- Keep your webhook URL secret
- Don't commit webhook URLs to version control
- Use environment variables or secure configuration management
- Consider IP restrictions in Slack app settings for production

## Next Steps

Your trading system will now automatically send notifications for all trade events. The notifications include:

- Real-time trade execution updates
- Profit/loss tracking
- System status messages
- Error alerts

No additional code changes are needed - notifications are fully integrated into your existing trading pipeline!