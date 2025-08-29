#!/usr/bin/env python3
"""
Circuit Breaker Agent - Safety system for autonomous trading
Monitors trading activity and triggers safety measures when thresholds are exceeded
"""

import os
import sys
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field
import aiohttp
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("circuit_breaker")


class BreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Trading halted
    HALF_OPEN = "half_open"  # Testing recovery


class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = 1
    WARNING = 2
    CRITICAL = 3
    EMERGENCY = 4


@dataclass
class BreakerConfig:
    """Circuit breaker configuration"""
    # Loss thresholds
    max_daily_loss_percent: float = 5.0  # Max 5% daily loss
    max_consecutive_losses: int = 3       # Max 3 losses in a row
    max_position_size_percent: float = 10.0  # Max 10% per position
    
    # Trading frequency
    max_trades_per_hour: int = 10
    max_trades_per_day: int = 20
    
    # Account thresholds
    min_margin_level: float = 150.0  # Minimum 150% margin level
    max_drawdown_percent: float = 10.0  # Max 10% drawdown from peak
    
    # Recovery settings
    cooldown_minutes: int = 30  # Wait 30 mins before retry
    half_open_test_trades: int = 2  # Test with 2 trades in half-open
    
    # Risk concentration
    max_correlated_positions: int = 2  # Max 2 positions in correlated pairs
    max_total_exposure_percent: float = 30.0  # Max 30% total exposure


@dataclass
class TradingMetrics:
    """Current trading metrics"""
    daily_pnl: float = 0.0
    daily_trades: int = 0
    hourly_trades: int = 0
    consecutive_losses: int = 0
    consecutive_wins: int = 0
    largest_position_percent: float = 0.0
    total_exposure_percent: float = 0.0
    margin_level: float = 0.0
    drawdown_percent: float = 0.0
    peak_balance: float = 0.0
    current_balance: float = 0.0
    open_positions: int = 0
    last_trade_time: Optional[datetime] = None
    correlated_positions: int = 0


class CircuitBreakerAgent:
    """Circuit Breaker Agent for trading safety"""
    
    def __init__(self, config: Optional[BreakerConfig] = None):
        self.config = config or BreakerConfig()
        self.state = BreakerState.CLOSED
        self.metrics = TradingMetrics()
        self.state_history: List[Dict] = []
        self.alerts: List[Dict] = []
        self.last_state_change = datetime.now()
        self.test_trades_count = 0
        self.orchestrator_url = os.getenv("ORCHESTRATOR_URL", "http://localhost:8083")
        self.oanda_api_key = os.getenv("OANDA_API_KEY")
        self.oanda_account_id = os.getenv("OANDA_ACCOUNT_ID")
        self.oanda_base_url = "https://api-fxpractice.oanda.com"
        self.running = False
        
        # Correlated pairs mapping
        self.correlation_groups = {
            "USD": ["EUR_USD", "GBP_USD", "USD_JPY", "USD_CHF", "USD_CAD", "AUD_USD", "NZD_USD"],
            "EUR": ["EUR_USD", "EUR_GBP", "EUR_JPY", "EUR_CHF", "EUR_AUD"],
            "GBP": ["GBP_USD", "EUR_GBP", "GBP_JPY", "GBP_CHF"],
            "JPY": ["USD_JPY", "EUR_JPY", "GBP_JPY", "AUD_JPY"],
            "COMMODITY": ["AUD_USD", "NZD_USD", "USD_CAD"],
        }
    
    async def start(self):
        """Start the circuit breaker monitoring"""
        self.running = True
        logger.info("🛡️ Circuit Breaker Agent Starting...")
        logger.info(f"📊 Configuration: {self.config}")
        
        # Start monitoring tasks
        await asyncio.gather(
            self.monitor_loop(),
            self.metrics_update_loop(),
            self.state_management_loop()
        )
    
    async def monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                # Update metrics from OANDA
                await self.update_metrics()
                
                # Check all safety conditions
                breaches = self.check_safety_conditions()
                
                # Handle any breaches
                if breaches:
                    await self.handle_breaches(breaches)
                
                # Check if we can recover
                if self.state == BreakerState.OPEN:
                    await self.check_recovery()
                
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                await asyncio.sleep(10)
    
    async def metrics_update_loop(self):
        """Update metrics periodically"""
        while self.running:
            try:
                await self.fetch_account_metrics()
                await self.fetch_trading_metrics()
                await asyncio.sleep(30)  # Update every 30 seconds
            except Exception as e:
                logger.error(f"Error updating metrics: {e}")
                await asyncio.sleep(60)
    
    async def state_management_loop(self):
        """Manage circuit breaker state transitions"""
        while self.running:
            try:
                if self.state == BreakerState.HALF_OPEN:
                    await self.handle_half_open_state()
                
                await asyncio.sleep(10)
            except Exception as e:
                logger.error(f"Error in state management: {e}")
                await asyncio.sleep(30)
    
    def check_safety_conditions(self) -> List[Dict]:
        """Check all safety conditions and return breaches"""
        breaches = []
        
        # Check daily loss
        if abs(self.metrics.daily_pnl) > (self.metrics.current_balance * self.config.max_daily_loss_percent / 100):
            breaches.append({
                "type": "DAILY_LOSS_EXCEEDED",
                "level": AlertLevel.CRITICAL,
                "value": self.metrics.daily_pnl,
                "threshold": self.config.max_daily_loss_percent
            })
        
        # Check consecutive losses
        if self.metrics.consecutive_losses >= self.config.max_consecutive_losses:
            breaches.append({
                "type": "CONSECUTIVE_LOSSES",
                "level": AlertLevel.WARNING,
                "value": self.metrics.consecutive_losses,
                "threshold": self.config.max_consecutive_losses
            })
        
        # Check position size
        if self.metrics.largest_position_percent > self.config.max_position_size_percent:
            breaches.append({
                "type": "POSITION_SIZE_EXCEEDED",
                "level": AlertLevel.WARNING,
                "value": self.metrics.largest_position_percent,
                "threshold": self.config.max_position_size_percent
            })
        
        # Check trading frequency
        if self.metrics.hourly_trades > self.config.max_trades_per_hour:
            breaches.append({
                "type": "HOURLY_TRADE_LIMIT",
                "level": AlertLevel.WARNING,
                "value": self.metrics.hourly_trades,
                "threshold": self.config.max_trades_per_hour
            })
        
        if self.metrics.daily_trades > self.config.max_trades_per_day:
            breaches.append({
                "type": "DAILY_TRADE_LIMIT",
                "level": AlertLevel.CRITICAL,
                "value": self.metrics.daily_trades,
                "threshold": self.config.max_trades_per_day
            })
        
        # Check margin level
        if self.metrics.margin_level > 0 and self.metrics.margin_level < self.config.min_margin_level:
            breaches.append({
                "type": "LOW_MARGIN",
                "level": AlertLevel.EMERGENCY,
                "value": self.metrics.margin_level,
                "threshold": self.config.min_margin_level
            })
        
        # Check drawdown
        if self.metrics.drawdown_percent > self.config.max_drawdown_percent:
            breaches.append({
                "type": "MAX_DRAWDOWN",
                "level": AlertLevel.CRITICAL,
                "value": self.metrics.drawdown_percent,
                "threshold": self.config.max_drawdown_percent
            })
        
        # Check total exposure
        if self.metrics.total_exposure_percent > self.config.max_total_exposure_percent:
            breaches.append({
                "type": "TOTAL_EXPOSURE",
                "level": AlertLevel.WARNING,
                "value": self.metrics.total_exposure_percent,
                "threshold": self.config.max_total_exposure_percent
            })
        
        # Check correlated positions
        if self.metrics.correlated_positions > self.config.max_correlated_positions:
            breaches.append({
                "type": "CORRELATED_POSITIONS",
                "level": AlertLevel.WARNING,
                "value": self.metrics.correlated_positions,
                "threshold": self.config.max_correlated_positions
            })
        
        return breaches
    
    async def handle_breaches(self, breaches: List[Dict]):
        """Handle safety breaches"""
        # Log all breaches
        for breach in breaches:
            self.log_alert(breach)
            logger.warning(f"🚨 BREACH: {breach['type']} - {breach['value']} exceeds {breach['threshold']}")
        
        # Determine action based on severity
        max_level = max(breach["level"].value for breach in breaches)
        
        if max_level == AlertLevel.EMERGENCY.value:
            await self.trigger_emergency_stop()
        elif max_level == AlertLevel.CRITICAL.value:
            await self.open_circuit_breaker()
        elif max_level == AlertLevel.WARNING.value:
            # For warnings, just notify but don't stop
            await self.send_warning_notification(breaches)
    
    async def open_circuit_breaker(self):
        """Open the circuit breaker (halt trading)"""
        if self.state != BreakerState.OPEN:
            logger.critical("⛔ OPENING CIRCUIT BREAKER - Trading Halted")
            self.state = BreakerState.OPEN
            self.last_state_change = datetime.now()
            
            # Record state change
            self.state_history.append({
                "state": BreakerState.OPEN,
                "timestamp": datetime.now().isoformat(),
                "reason": "Safety threshold breach"
            })
            
            # Notify orchestrator to stop trading
            await self.notify_orchestrator_stop()
    
    async def trigger_emergency_stop(self):
        """Trigger emergency stop - close all positions"""
        logger.critical("🚨🚨🚨 EMERGENCY STOP TRIGGERED - Closing All Positions")
        self.state = BreakerState.OPEN
        
        # Close all positions immediately
        await self.close_all_positions()
        
        # Notify orchestrator
        await self.notify_orchestrator_emergency()
    
    async def check_recovery(self):
        """Check if we can move to half-open state"""
        if self.state != BreakerState.OPEN:
            return
        
        # Check if cooldown period has passed
        time_since_open = datetime.now() - self.last_state_change
        if time_since_open.total_seconds() >= self.config.cooldown_minutes * 60:
            # Move to half-open state
            logger.info("🔄 Moving to HALF-OPEN state for testing")
            self.state = BreakerState.HALF_OPEN
            self.test_trades_count = 0
            self.last_state_change = datetime.now()
    
    async def handle_half_open_state(self):
        """Handle half-open state logic"""
        if self.state != BreakerState.HALF_OPEN:
            return
        
        # Check test trades performance
        if self.test_trades_count >= self.config.half_open_test_trades:
            # Evaluate performance
            if self.metrics.consecutive_losses == 0:
                # Recovery successful
                logger.info("✅ Circuit Breaker CLOSED - Trading Resumed")
                self.state = BreakerState.CLOSED
                self.last_state_change = datetime.now()
            else:
                # Recovery failed, back to open
                logger.warning("❌ Recovery failed - Circuit Breaker remains OPEN")
                self.state = BreakerState.OPEN
                self.last_state_change = datetime.now()
    
    async def update_metrics(self):
        """Update current metrics from account data"""
        try:
            # This would normally fetch from OANDA API
            # For now, using placeholder logic
            pass
        except Exception as e:
            logger.error(f"Error updating metrics: {e}")
    
    async def fetch_account_metrics(self):
        """Fetch account metrics from OANDA"""
        if not self.oanda_api_key:
            return
        
        try:
            headers = {
                "Authorization": f"Bearer {self.oanda_api_key}",
                "Content-Type": "application/json"
            }
            
            url = f"{self.oanda_base_url}/v3/accounts/{self.oanda_account_id}/summary"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        account = data.get("account", {})
                        
                        self.metrics.current_balance = float(account.get("balance", 0))
                        self.metrics.margin_level = float(account.get("marginCloseoutPercent", 0)) * 100
                        self.metrics.open_positions = int(account.get("openPositionCount", 0))
                        
                        # Update peak balance
                        if self.metrics.current_balance > self.metrics.peak_balance:
                            self.metrics.peak_balance = self.metrics.current_balance
                        
                        # Calculate drawdown
                        if self.metrics.peak_balance > 0:
                            self.metrics.drawdown_percent = ((self.metrics.peak_balance - self.metrics.current_balance) 
                                                            / self.metrics.peak_balance) * 100
                        
        except Exception as e:
            logger.error(f"Error fetching account metrics: {e}")
    
    async def fetch_trading_metrics(self):
        """Fetch trading metrics from OANDA"""
        if not self.oanda_api_key:
            return
        
        try:
            # Get positions for exposure calculation
            headers = {
                "Authorization": f"Bearer {self.oanda_api_key}",
                "Content-Type": "application/json"
            }
            
            url = f"{self.oanda_base_url}/v3/accounts/{self.oanda_account_id}/positions"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        positions = data.get("positions", [])
                        
                        # Calculate exposure metrics
                        total_exposure = 0
                        largest_position = 0
                        position_instruments = []
                        
                        for pos in positions:
                            units = abs(float(pos.get("long", {}).get("units", 0)) + 
                                      float(pos.get("short", {}).get("units", 0)))
                            if units > 0:
                                exposure = units  # Simplified - would need proper calculation
                                total_exposure += exposure
                                largest_position = max(largest_position, exposure)
                                position_instruments.append(pos.get("instrument"))
                        
                        if self.metrics.current_balance > 0:
                            self.metrics.total_exposure_percent = (total_exposure / self.metrics.current_balance) * 100
                            self.metrics.largest_position_percent = (largest_position / self.metrics.current_balance) * 100
                        
                        # Count correlated positions
                        self.metrics.correlated_positions = self.count_correlated_positions(position_instruments)
                        
        except Exception as e:
            logger.error(f"Error fetching trading metrics: {e}")
    
    def count_correlated_positions(self, instruments: List[str]) -> int:
        """Count maximum correlated positions in any group"""
        max_correlated = 0
        
        for group_name, group_pairs in self.correlation_groups.items():
            count = sum(1 for inst in instruments if inst in group_pairs)
            max_correlated = max(max_correlated, count)
        
        return max_correlated
    
    async def close_all_positions(self):
        """Close all open positions"""
        logger.critical("🚨 Closing all positions via emergency script...")
        try:
            # Get current directory and construct path to scripts
            current_dir = os.path.dirname(os.path.abspath(__file__))
            script_path = os.path.join(current_dir, "..", "..", "scripts", "close_all_trades.py")
            script_path = os.path.abspath(script_path)
            
            if not os.path.exists(script_path):
                logger.error(f"❌ Close all trades script not found: {script_path}")
                return
            
            # Run script with proper environment variables
            env = os.environ.copy()
            env.update({
                "OANDA_API_KEY": self.oanda_api_key,
                "OANDA_ACCOUNT_ID": self.account_id
            })
            
            # Use asyncio subprocess for non-blocking execution
            process = await asyncio.create_subprocess_exec(
                "python", script_path,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.critical("✅ Emergency position closure completed successfully")
                if stdout:
                    logger.info(f"Script output: {stdout.decode()}")
            else:
                logger.error(f"❌ Emergency position closure failed: {stderr.decode()}")
                
        except Exception as e:
            logger.error(f"❌ Error executing emergency position closure: {e}")
    
    async def notify_orchestrator_stop(self):
        """Notify orchestrator to stop trading"""
        try:
            url = f"{self.orchestrator_url}/api/circuit-breaker/halt"
            data = {
                "state": self.state.value,
                "reason": "Circuit breaker triggered",
                "timestamp": datetime.now().isoformat()
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    if response.status == 200:
                        logger.info("Orchestrator notified of trading halt")
        except Exception as e:
            logger.error(f"Error notifying orchestrator: {e}")
    
    async def notify_orchestrator_emergency(self):
        """Notify orchestrator of emergency stop"""
        try:
            url = f"{self.orchestrator_url}/api/emergency-stop"
            data = {
                "reason": "Emergency circuit breaker trigger",
                "close_positions": True,
                "timestamp": datetime.now().isoformat()
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    if response.status == 200:
                        logger.info("Orchestrator notified of emergency stop")
        except Exception as e:
            logger.error(f"Error notifying orchestrator: {e}")
    
    async def send_warning_notification(self, breaches: List[Dict]):
        """Send warning notifications"""
        for breach in breaches:
            logger.warning(f"⚠️ {breach['type']}: {breach['value']} (threshold: {breach['threshold']})")
    
    def log_alert(self, alert: Dict):
        """Log an alert"""
        alert["timestamp"] = datetime.now().isoformat()
        self.alerts.append(alert)
        
        # Keep only last 100 alerts
        if len(self.alerts) > 100:
            self.alerts = self.alerts[-100:]
    
    def get_status(self) -> Dict:
        """Get current circuit breaker status"""
        return {
            "state": self.state.value,
            "metrics": {
                "daily_pnl": self.metrics.daily_pnl,
                "daily_trades": self.metrics.daily_trades,
                "consecutive_losses": self.metrics.consecutive_losses,
                "margin_level": self.metrics.margin_level,
                "drawdown_percent": self.metrics.drawdown_percent,
                "total_exposure_percent": self.metrics.total_exposure_percent,
                "open_positions": self.metrics.open_positions
            },
            "recent_alerts": self.alerts[-10:] if self.alerts else [],
            "last_state_change": self.last_state_change.isoformat(),
            "can_trade": self.state == BreakerState.CLOSED
        }


async def main():
    """Main entry point"""
    logger.info("=" * 60)
    logger.info("CIRCUIT BREAKER AGENT")
    logger.info("=" * 60)
    
    # Create circuit breaker with custom config
    config = BreakerConfig(
        max_daily_loss_percent=5.0,
        max_consecutive_losses=3,
        max_position_size_percent=10.0,
        max_trades_per_hour=10,
        max_trades_per_day=20,
        min_margin_level=150.0,
        max_drawdown_percent=10.0,
        cooldown_minutes=30
    )
    
    breaker = CircuitBreakerAgent(config)
    await breaker.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Circuit Breaker stopped by user")