"""
Execution Engine Client
Connects the orchestrator to the execution engine for paper trading
"""

import asyncio
import logging
from typing import Dict, Optional, Any
import aiohttp
import os

logger = logging.getLogger(__name__)


class ExecutionEngineClient:
    """Client to communicate with the execution engine"""
    
    def __init__(self):
        self.execution_engine_url = os.getenv("EXECUTION_ENGINE_URL", "http://localhost:8082")
        self.timeout = aiohttp.ClientTimeout(total=10.0)
        
        logger.info(f"Execution Engine Client initialized: {self.execution_engine_url}")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get execution engine status"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(f"{self.execution_engine_url}/status") as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"Execution engine status check failed: {response.status}")
                        return {"status": "error", "message": f"HTTP {response.status}"}
        except Exception as e:
            logger.error(f"Failed to get execution engine status: {e}")
            return {"status": "error", "message": str(e)}
    
    async def place_market_order(
        self, 
        account_id: str, 
        instrument: str, 
        side: str, 
        units: int,
        signal_id: Optional[str] = None,
        price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Place a market order through the execution engine
        
        Args:
            account_id: Account to place order for
            instrument: Trading instrument (e.g., EUR_USD)
            side: Order side ("buy" or "sell")
            units: Number of units to trade
            signal_id: Associated signal ID for tracking
            price: Expected price for validation
            stop_loss: Stop loss price level
            take_profit: Take profit price level
            
        Returns:
            Order execution result
        """
        try:
            order_data = {
                "account_id": account_id,
                "instrument": instrument,
                "side": side,
                "units": units,
                "type": "market"
            }
            
            if signal_id:
                order_data["signal_id"] = signal_id
            if price:
                order_data["price"] = price
            if stop_loss:
                order_data["stop_loss_price"] = stop_loss
            if take_profit:
                order_data["take_profit_price"] = take_profit
            
            logger.info(f"Placing market order: {order_data}")
            
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    f"{self.execution_engine_url}/orders/market",
                    json=order_data
                ) as response:
                    result = await response.json()
                    
                    if response.status == 200:
                        logger.info(f"Order placed successfully: {result}")
                        return result
                    else:
                        logger.error(f"Order placement failed: {result}")
                        return {
                            "success": False,
                            "error": result,
                            "message": f"HTTP {response.status}"
                        }
        except Exception as e:
            logger.error(f"Failed to place market order: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to communicate with execution engine"
            }
    
    async def get_positions(self, account_id: str) -> Dict[str, Any]:
        """Get current positions"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(f"{self.execution_engine_url}/positions") as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"Failed to get positions: {response.status}")
                        return {"positions": [], "error": f"HTTP {response.status}"}
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return {"positions": [], "error": str(e)}
    
    async def health_check(self) -> bool:
        """Check if execution engine is healthy"""
        try:
            status = await self.get_status()
            return status.get("status") == "running"
        except Exception:
            return False