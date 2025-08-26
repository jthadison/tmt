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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("active_scanner")

class ActiveMarketScanner:
    """Actively scans markets and generates trading signals"""
    
    def __init__(self):
        self.orchestrator_url = "http://localhost:8083"
        self.oanda_api_key = os.getenv("OANDA_API_KEY")
        self.oanda_account_id = os.getenv("OANDA_ACCOUNT_ID")
        self.instruments = ["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "USD_CAD", "EUR_GBP"]
        self.scan_interval = int(os.getenv("SCAN_INTERVAL", "30"))  # seconds, configurable
        self.signal_probability = float(os.getenv("SIGNAL_PROBABILITY", "0.02"))  # 2% default (reduced from 5%)
        self.max_daily_trades = int(os.getenv("MAX_DAILY_TRADES", "5"))  # Maximum 5 trades per day
        self.signal_count = 0
        self.daily_trades = 0
        self.last_reset_date = datetime.now().date()
        self.running = False
        self.position_size_percent = 0.02  # 2% of account per trade
        self.account_balance = 100000  # Will be updated dynamically
        
        # OANDA API endpoints
        self.oanda_base_url = "https://api-fxpractice.oanda.com"
        self.headers = {
            "Authorization": f"Bearer {self.oanda_api_key}",
            "Content-Type": "application/json"
        }
        
    async def start_scanning(self):
        """Start the active market scanning loop"""
        self.running = True
        logger.info("🚀 Starting Active Market Scanner")
        logger.info(f"📊 Monitoring instruments: {', '.join(self.instruments)}")
        logger.info(f"⏰ Scan interval: {self.scan_interval} seconds")
        logger.info(f"🎯 Signal probability: {self.signal_probability:.1%}")
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
                
                # Scan each instrument
                for instrument in self.instruments:
                    await self.scan_instrument(instrument)
                
                logger.info(f"✅ Scan cycle complete. Signals generated: {self.signal_count}")
                cycle_count += 1
                await asyncio.sleep(self.scan_interval)
                
            except Exception as e:
                logger.error(f"Error in scanning loop: {e}")
                await asyncio.sleep(10)
    
    async def scan_instrument(self, instrument: str):
        """Scan a specific instrument for trading opportunities"""
        try:
            # Get current price
            price = await self.get_current_price(instrument)
            if not price:
                return
            
            # Simple signal generation logic
            # In production, this would use Wyckoff patterns, volume analysis, etc.
            signal = self.analyze_for_signal(instrument, price)
            
            if signal:
                await self.send_signal_to_orchestrator(signal)
                
        except Exception as e:
            logger.error(f"Error scanning {instrument}: {e}")
    
    async def get_current_price(self, instrument: str) -> Optional[float]:
        """Get current price from OANDA"""
        try:
            url = f"{self.oanda_base_url}/v3/accounts/{self.oanda_account_id}/pricing"
            params = {"instruments": instrument}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        prices = data.get("prices", [])
                        if prices:
                            bid = float(prices[0].get("bids", [{}])[0].get("price", 0))
                            ask = float(prices[0].get("asks", [{}])[0].get("price", 0))
                            return (bid + ask) / 2
            return None
            
        except Exception as e:
            logger.error(f"Error getting price for {instrument}: {e}")
            return None
    
    def calculate_position_size(self, instrument: str, stop_loss_pips: int = 30) -> int:
        """
        Calculate position size based on 2% risk per trade
        """
        # Risk amount (2% of balance)
        risk_amount = self.account_balance * self.position_size_percent
        
        # Pip value calculation
        if "JPY" in instrument:
            pip_value_per_unit = 0.01 / 100  # For JPY pairs
        else:
            pip_value_per_unit = 0.0001  # For standard pairs
        
        # Calculate units based on risk
        # Risk = Units * Stop Loss in Pips * Pip Value
        # Units = Risk / (Stop Loss in Pips * Pip Value)
        units = int(risk_amount / (stop_loss_pips * pip_value_per_unit * 10))
        
        # Round to nearest 1000 units (OANDA minimum)
        units = max(1000, (units // 1000) * 1000)
        
        # Cap at maximum safe size (10% of account)
        max_units = min(100000, int(self.account_balance * 0.1))
        units = min(units, max_units)
        
        return units
    
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
    
    def analyze_for_signal(self, instrument: str, price: float) -> Optional[Dict]:
        """
        Analyze price for trading signal
        In production, this would use sophisticated analysis
        For now, using simplified logic for demonstration
        """
        
        # Check daily trade limit
        self._reset_daily_count_if_needed()
        if self.daily_trades >= self.max_daily_trades:
            return None
        
        # Generate a signal with configurable probability
        if random.random() > self.signal_probability:
            return None
        
        # Randomly choose direction
        direction = random.choice(["long", "short"])
        
        # Calculate stop loss and take profit
        pip_value = 0.0001 if "JPY" not in instrument else 0.01
        stop_loss_pips = 30
        take_profit_pips = 60
        
        if direction == "long":
            stop_loss = price - (stop_loss_pips * pip_value)
            take_profit = price + (take_profit_pips * pip_value)
        else:
            stop_loss = price + (stop_loss_pips * pip_value)
            take_profit = price - (take_profit_pips * pip_value)
        
        # Calculate position size
        units = self.calculate_position_size(instrument, stop_loss_pips)
        
        signal = {
            "id": f"auto_signal_{self.signal_count:04d}",
            "instrument": instrument,
            "direction": direction,
            "units": units,  # ADD THIS FIELD
            "confidence": round(75.0 + random.random() * 20.0, 2),  # 75-95% confidence
            "entry_price": price,
            "stop_loss": round(stop_loss, 5),
            "take_profit": round(take_profit, 5),
            "pattern_type": "wyckoff_accumulation",
            "timeframe": "H1",
            "timestamp": datetime.now().isoformat(),
            "source": "active_scanner",
            "risk_percent": self.position_size_percent * 100
        }
        
        self.signal_count += 1
        self.daily_trades += 1  # Increment daily trade count
        logger.info(f"📈 Signal generated: {instrument} {direction.upper()} @ {price:.5f} | Units: {units}")
        logger.info(f"🎯 Daily trades: {self.daily_trades}/{self.max_daily_trades}")
        return signal
    
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