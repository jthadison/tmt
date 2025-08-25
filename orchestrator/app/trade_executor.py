"""
Trade Execution Engine for OANDA
Converts trading signals into actual market orders with comprehensive risk management
"""

import asyncio
import logging
from typing import Dict, Optional, List, Any
from decimal import Decimal
from datetime import datetime
import aiohttp
import os
from enum import Enum

from .models import TradeSignal, OrderType, OrderStatus
from .config import get_settings
from .circuit_breaker import TradingCircuitBreaker
from .execution_client import ExecutionEngineClient

logger = logging.getLogger(__name__)


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class TradeExecutor:
    """Executes trades on OANDA based on signals"""
    
    def __init__(self):
        self.settings = get_settings()
        self.circuit_breaker = TradingCircuitBreaker()
        self.execution_client = ExecutionEngineClient()
        
        # Legacy OANDA configuration (for compatibility)
        self.api_key = os.getenv("OANDA_API_KEY")
        self.environment = os.getenv("OANDA_ENVIRONMENT", "practice")
        
        # Risk management
        self.max_position_size = float(os.getenv("MAX_POSITION_SIZE", "100000"))
        self.risk_per_trade = float(os.getenv("RISK_PER_TRADE", "0.02"))
        
        # Track active trades
        self.active_trades = {}
        self.daily_trades = 0
        self.daily_losses = Decimal("0")
        
        logger.info(f"Trade Executor initialized for {self.environment} environment")
    
    async def execute_signal(self, signal: TradeSignal, account_id: str) -> Dict:
        """
        Execute a trading signal on OANDA
        
        Args:
            signal: Trading signal to execute
            account_id: OANDA account ID
            
        Returns:
            Execution result with order details
        """
        try:
            # Pre-execution checks
            if not await self._pre_execution_checks(signal, account_id):
                return {
                    "success": False,
                    "reason": "Pre-execution checks failed",
                    "signal_id": signal.id
                }
            
            # Calculate position size based on risk management
            position_size = await self._calculate_position_size(
                signal, account_id
            )
            
            if position_size == 0:
                return {
                    "success": False,
                    "reason": "Position size too small",
                    "signal_id": signal.id
                }
            
            # Create and send order to OANDA
            order_result = await self._place_order(
                account_id=account_id,
                instrument=signal.instrument,
                units=position_size,
                side=signal.direction,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit,
                signal_id=signal.id
            )
            
            if order_result["success"]:
                # Track the trade
                self.active_trades[order_result["order_id"]] = {
                    "signal_id": signal.id,
                    "instrument": signal.instrument,
                    "units": position_size,
                    "entry_price": order_result["fill_price"],
                    "stop_loss": signal.stop_loss,
                    "take_profit": signal.take_profit,
                    "timestamp": datetime.now(),
                    "account_id": account_id
                }
                
                self.daily_trades += 1
                
                logger.info(f"Trade executed successfully: {order_result['order_id']}")
                
                # Send execution confirmation
                await self._send_execution_notification(signal, order_result)
            
            return order_result
            
        except Exception as e:
            logger.error(f"Error executing signal {signal.id}: {e}")
            return {
                "success": False,
                "reason": f"Execution error: {str(e)}",
                "signal_id": signal.id
            }
    
    async def _pre_execution_checks(self, signal: TradeSignal, account_id: str) -> bool:
        """Perform pre-execution safety checks"""
        
        # Check circuit breaker status
        if self.circuit_breaker.is_tripped(account_id):
            logger.warning(f"Circuit breaker tripped for account {account_id}")
            return False
        
        # Check daily trade limit
        max_trades_per_day = int(os.getenv("MAX_TRADES_PER_DAY", "10"))
        if self.daily_trades >= max_trades_per_day:
            logger.warning(f"Daily trade limit reached: {self.daily_trades}/{max_trades_per_day}")
            return False
        
        # Check signal confidence
        min_confidence = float(os.getenv("MIN_SIGNAL_CONFIDENCE", "70"))
        if signal.confidence < min_confidence:
            logger.warning(f"Signal confidence too low: {signal.confidence}% < {min_confidence}%")
            return False
        
        # Check market hours
        if not await self._is_market_open(signal.instrument):
            logger.warning(f"Market closed for {signal.instrument}")
            return False
        
        # Check account margin
        if not await self._check_margin_available(account_id, signal):
            logger.warning(f"Insufficient margin for account {account_id}")
            return False
        
        # Check for existing position in same instrument
        if await self._has_open_position(account_id, signal.instrument):
            logger.warning(f"Already have open position in {signal.instrument}")
            return False
        
        return True
    
    async def _calculate_position_size(self, signal: TradeSignal, account_id: str) -> int:
        """
        Calculate position size based on risk management rules
        
        Uses the formula: Position Size = (Account Balance * Risk%) / (Stop Loss Distance * Pip Value)
        """
        try:
            # Get account balance
            account_info = await self._get_account_info(account_id)
            if not account_info:
                return 0
            
            balance = float(account_info.get("balance", 0))
            
            # Calculate risk amount
            risk_amount = balance * self.risk_per_trade
            
            # Calculate stop loss distance in pips
            if signal.direction == "long":
                stop_distance = abs(signal.entry_price - signal.stop_loss)
            else:
                stop_distance = abs(signal.stop_loss - signal.entry_price)
            
            # Get pip value for the instrument
            pip_value = await self._get_pip_value(signal.instrument)
            
            # Calculate position size
            if stop_distance > 0 and pip_value > 0:
                position_size = int(risk_amount / (stop_distance * pip_value))
            else:
                position_size = 0
            
            # Apply position size limits
            position_size = min(position_size, int(self.max_position_size))
            
            # Ensure minimum position size (OANDA minimum is usually 1 unit)
            if position_size < 1:
                position_size = 0
            
            # Apply direction (negative for sell/short)
            if signal.direction in ["short", "sell"]:
                position_size = -position_size
            
            logger.info(f"Calculated position size: {position_size} units for signal {signal.id}")
            return position_size
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0
    
    async def _place_order(self, account_id: str, instrument: str, units: int,
                          side: str, stop_loss: float, take_profit: float,
                          signal_id: str) -> Dict:
        """Place order through execution engine"""
        try:
            logger.info(f"Placing order via execution engine: {instrument} {side} {units} units")
            
            # Use execution engine client instead of direct OANDA
            result = await self.execution_client.place_market_order(
                account_id=account_id,
                instrument=instrument,
                side=side,
                units=units,
                signal_id=signal_id
            )
            
            if result.get("success"):
                logger.info(f"Order placed successfully: {result}")
                return {
                    "success": True,
                    "order_id": result.get("order_id"),
                    "status": result.get("status", "filled"),
                    "fill_price": result.get("fill_price"),
                    "mode": result.get("mode", "unknown"),
                    "message": result.get("message", "Order placed"),
                    "execution_engine_result": result
                }
            else:
                logger.error(f"Order placement failed: {result}")
                return {
                    "success": False,
                    "reason": result.get("message", "Order placement failed"),
                    "error": result.get("error"),
                    "execution_engine_result": result
                }
                        
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return {
                "success": False,
                "reason": f"Order placement error: {str(e)}",
                "signal_id": signal_id
            }
    
    async def _get_account_info(self, account_id: str) -> Optional[Dict]:
        """Get account information from OANDA"""
        try:
            url = f"{self.base_url}/v3/accounts/{account_id}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("account", {})
                    else:
                        logger.error(f"Failed to get account info: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return None
    
    async def _get_pip_value(self, instrument: str) -> float:
        """Calculate pip value for an instrument"""
        # Simplified pip value calculation
        # In production, this should account for account currency and current exchange rates
        
        if "JPY" in instrument:
            return 0.01  # JPY pairs have different pip value
        else:
            return 0.0001  # Standard pip value for most pairs
    
    async def _is_market_open(self, instrument: str) -> bool:
        """Check if market is open for trading"""
        # Forex markets are open 24/5 (Sunday 5pm ET to Friday 5pm ET)
        # This is a simplified check - enhance for production
        
        from datetime import datetime
        now = datetime.utcnow()
        
        # Market closed on weekends (simplified)
        if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        
        # Friday after 9pm UTC (5pm ET)
        if now.weekday() == 4 and now.hour >= 21:
            return False
        
        # Sunday before 9pm UTC (5pm ET)
        if now.weekday() == 6 and now.hour < 21:
            return False
        
        return True
    
    async def _check_margin_available(self, account_id: str, signal: TradeSignal) -> bool:
        """Check if sufficient margin is available"""
        try:
            account_info = await self._get_account_info(account_id)
            if not account_info:
                return False
            
            margin_available = float(account_info.get("marginAvailable", 0))
            
            # Rough margin requirement estimate (3% of position value)
            estimated_margin = self.max_position_size * signal.entry_price * 0.03
            
            return margin_available > estimated_margin
            
        except Exception as e:
            logger.error(f"Error checking margin: {e}")
            return False
    
    async def _has_open_position(self, account_id: str, instrument: str) -> bool:
        """Check if there's already an open position in this instrument"""
        try:
            url = f"{self.base_url}/v3/accounts/{account_id}/positions/{instrument}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        position = data.get("position", {})
                        
                        # Check if position has units
                        long_units = int(position.get("long", {}).get("units", 0))
                        short_units = int(position.get("short", {}).get("units", 0))
                        
                        return (long_units != 0) or (short_units != 0)
                    else:
                        # No position found
                        return False
                        
        except Exception as e:
            logger.error(f"Error checking open positions: {e}")
            return True  # Err on the side of caution
    
    async def _send_execution_notification(self, signal: TradeSignal, order_result: Dict):
        """Send notification about trade execution"""
        logger.info(f"Trade executed for signal {signal.id}: Order {order_result['order_id']}")
        
        # In production, this could send email/SMS/webhook notifications
        # For now, just log the execution
        execution_summary = {
            "timestamp": datetime.now().isoformat(),
            "signal_id": signal.id,
            "order_id": order_result["order_id"],
            "instrument": signal.instrument,
            "direction": signal.direction,
            "units": order_result["units"],
            "fill_price": order_result["fill_price"],
            "stop_loss": signal.stop_loss,
            "take_profit": signal.take_profit,
            "confidence": signal.confidence
        }
        
        logger.info(f"Execution summary: {execution_summary}")
    
    async def close_position(self, account_id: str, instrument: str) -> Dict:
        """Close an open position"""
        try:
            url = f"{self.base_url}/v3/accounts/{account_id}/positions/{instrument}/close"
            
            # Close all units
            close_data = {
                "longUnits": "ALL",
                "shortUnits": "ALL"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.put(url, headers=self.headers, json=close_data) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"Position closed for {instrument}")
                        return {"success": True, "details": result}
                    else:
                        error = await response.text()
                        logger.error(f"Failed to close position: {error}")
                        return {"success": False, "error": error}
                        
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_open_trades(self, account_id: str) -> List[Dict]:
        """Get all open trades for an account"""
        try:
            url = f"{self.base_url}/v3/accounts/{account_id}/trades"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("trades", [])
                    else:
                        logger.error(f"Failed to get open trades: {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"Error getting open trades: {e}")
            return []
    
    async def monitor_trades(self):
        """Monitor open trades and update stop losses if needed"""
        while True:
            try:
                for account_id in self.settings.account_ids_list:
                    trades = await self.get_open_trades(account_id)
                    
                    for trade in trades:
                        trade_id = trade.get("id")
                        
                        # Check if we should adjust stop loss (trailing stop logic)
                        # This is where you'd implement trailing stop logic
                        
                        # Check if trade hit stop or target
                        if trade.get("state") == "CLOSED":
                            if trade_id in self.active_trades:
                                del self.active_trades[trade_id]
                                
                                # Update daily P&L
                                pl = float(trade.get("realizedPL", 0))
                                if pl < 0:
                                    self.daily_losses += Decimal(str(abs(pl)))
                
                # Check if we need to reset daily counters
                await self._check_daily_reset()
                
                # Wait before next check
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error monitoring trades: {e}")
                await asyncio.sleep(30)  # Wait longer on error
    
    async def _check_daily_reset(self):
        """Reset daily counters at market close"""
        from datetime import datetime
        now = datetime.utcnow()
        
        # Reset at 9pm UTC (5pm ET - market close)
        if now.hour == 21 and now.minute < 1:
            self.daily_trades = 0
            self.daily_losses = Decimal("0")
            logger.info("Daily trade counters reset")