#!/usr/bin/env python3
"""
Active Market Scanner - Simplified Signal Generator
This actively scans markets and generates trading signals
"""

import os
import sys
import asyncio
import logging
import random
from datetime import datetime
from typing import Dict, Any, Optional
import aiohttp
import json
from intelligent_signal_generator import IntelligentSignalGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("active_scanner")

class ActiveMarketScanner:
    """Actively scans markets and generates trading signals"""

    def __init__(self):
        self.orchestrator_url = os.getenv("ORCHESTRATOR_URL", "http://localhost:8089")
        self.oanda_api_key = os.getenv("OANDA_API_KEY")
        self.oanda_account_id = os.getenv("OANDA_ACCOUNT_ID")
        self.instruments = ["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "USD_CAD", "EUR_GBP"]
        self.scan_interval = int(os.getenv("SCAN_INTERVAL", "30"))  # seconds, configurable
        self.max_daily_trades = int(os.getenv("MAX_DAILY_TRADES", "5"))  # Maximum 5 trades per day
        self.signal_count = 0
        self.daily_trades = 0
        self.last_reset_date = datetime.now().date()
        self.running = False
        self.position_size_percent = 0.02  # 2% of account per trade
        self.account_balance = 100000  # Will be updated dynamically

        # Initialize intelligent signal generator
        self.intelligent_generator = IntelligentSignalGenerator()

        # OANDA API endpoints
        self.oanda_base_url = "https://api-fxpractice.oanda.com"
        self.headers = {
            "Authorization": f"Bearer {self.oanda_api_key}",
            "Content-Type": "application/json"
        }
        
    async def start_scanning(self):
        """Start the active market scanning loop"""
        self.running = True
        logger.info("🚀 Starting Intelligent Market Scanner")
        logger.info(f"📊 Monitoring instruments: {', '.join(self.instruments)}")
        logger.info(f"⏰ Scan interval: {self.scan_interval} seconds")
        logger.info(f"🧠 Analysis method: Wyckoff Patterns + VPA (Volume Price Analysis)")
        logger.info(f"📈 Max daily trades: {self.max_daily_trades}")
        logger.info(f"🗓️ Daily trades today: {self.daily_trades}")
        
        # Update account balance initially
        await self.update_account_balance()
        
        cycle_count = 0
        while self.running:
            try:
                # Update account balance every 10 cycles
                if cycle_count % 10 == 0:
                    await self.update_account_balance()

                # Check daily trade limit
                self._reset_daily_count_if_needed()
                if self.daily_trades >= self.max_daily_trades:
                    logger.info(f"📊 Daily trade limit reached ({self.daily_trades}/{self.max_daily_trades}). Waiting...")
                    await asyncio.sleep(self.scan_interval)
                    continue

                # Use intelligent signal generator
                signals = await self.intelligent_generator.analyze_market_and_generate_signals()

                # Process and send signals
                for signal in signals:
                    if self.daily_trades < self.max_daily_trades:
                        await self.send_signal_to_orchestrator(signal)
                        self.daily_trades += 1
                        logger.info(f"📈 Real signal sent: {signal['instrument']} {signal['direction'].upper()} | Confidence: {signal['confidence']}%")
                        logger.info(f"🎯 Daily trades: {self.daily_trades}/{self.max_daily_trades}")

                logger.info(f"✅ Intelligent scan complete. Real signals found: {len(signals)}")
                cycle_count += 1
                await asyncio.sleep(self.scan_interval)

            except Exception as e:
                logger.error(f"Error in scanning loop: {e}")
                await asyncio.sleep(10)
    
    
    async def update_account_balance(self):
        """Update account balance from OANDA"""
        try:
            url = f"{self.oanda_base_url}/v3/accounts/{self.oanda_account_id}/summary"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        account = data.get("account", {})
                        self.account_balance = float(account.get("balance", 100000))
                        logger.info(f"Updated account balance: ${self.account_balance:.2f}")
        except Exception as e:
            logger.error(f"Error updating account balance: {e}")
    
    
    def _reset_daily_count_if_needed(self):
        """Reset daily trade count if it's a new day"""
        current_date = datetime.now().date()
        if current_date != self.last_reset_date:
            self.daily_trades = 0
            self.last_reset_date = current_date
            logger.info(f"🗓️ New day! Daily trade count reset to 0")
    
    async def send_signal_to_orchestrator(self, signal: Dict):
        """Send trading signal to orchestrator"""
        try:
            url = f"{self.orchestrator_url}/api/signals/process"

            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=signal) as response:
                    if response.status == 200:
                        result = await response.json()
                        self.signal_count += 1
                        logger.info(f"✅ Signal sent to orchestrator: {result}")
                    else:
                        text = await response.text()
                        logger.warning(f"Signal rejected by orchestrator: {text}")

        except Exception as e:
            logger.error(f"Error sending signal to orchestrator: {e}")

async def main():
    """Main entry point"""
    scanner = ActiveMarketScanner()
    
    # Check if we have OANDA credentials
    if not scanner.oanda_api_key:
        logger.error("❌ OANDA_API_KEY not found in environment")
        return
    
    if not scanner.oanda_account_id:
        logger.error("❌ OANDA_ACCOUNT_ID not found in environment")
        return
    
    logger.info("=" * 60)
    logger.info("TMT ACTIVE MARKET SCANNER")
    logger.info("=" * 60)
    
    # Start scanning
    await scanner.start_scanning()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Market scanner stopped by user")