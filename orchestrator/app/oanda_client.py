"""
OANDA Client for Trading System Orchestrator

Handles all OANDA API interactions for trade execution and account management.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from decimal import Decimal
import httpx
from pydantic import BaseModel

from .config import get_settings
from .exceptions import OandaException, TimeoutException
from .models import TradeSignal, TradeResult

logger = logging.getLogger(__name__)


class OandaAccount(BaseModel):
    """OANDA account information"""
    account_id: str
    balance: float
    unrealized_pnl: float
    margin_used: float
    margin_available: float
    open_trade_count: int
    currency: str


class OandaPosition(BaseModel):
    """OANDA position information"""
    instrument: str
    units: float
    average_price: float
    unrealized_pnl: float
    margin_used: float


class OandaTrade(BaseModel):
    """OANDA trade information"""
    trade_id: str
    instrument: str
    units: float
    price: float
    unrealized_pnl: float
    open_time: datetime


class OandaOrder(BaseModel):
    """OANDA order information"""
    order_id: str
    type: str
    instrument: str
    units: float
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    time_in_force: str = "FOK"


class OandaClient:
    """OANDA API client for trading operations"""
    
    def __init__(self):
        self.settings = get_settings()
        self.client = httpx.AsyncClient(
            timeout=10.0,
            headers={
                "Authorization": f"Bearer {self.settings.oanda_api_key}",
                "Content-Type": "application/json",
                "Accept-Datetime-Format": "RFC3339"
            }
        )
        self.base_url = self.settings.oanda_api_url
        
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    async def get_account_info(self, account_id: str) -> OandaAccount:
        """Get account information"""
        try:
            response = await self.client.get(f"{self.base_url}/v3/accounts/{account_id}")
            
            if response.status_code == 200:
                account_data = response.json()["account"]
                
                return OandaAccount(
                    account_id=account_data["id"],
                    balance=float(account_data["balance"]),
                    unrealized_pnl=float(account_data.get("unrealizedPL", 0)),
                    margin_used=float(account_data.get("marginUsed", 0)),
                    margin_available=float(account_data.get("marginAvailable", 0)),
                    open_trade_count=int(account_data.get("openTradeCount", 0)),
                    currency=account_data.get("currency", "USD")
                )
            else:
                raise OandaException(f"Failed to get account info: {response.status_code}")
                
        except httpx.TimeoutException:
            raise TimeoutException("get_account_info", 10.0)
        except Exception as e:
            raise OandaException(f"Account info request failed: {e}")
    
    async def get_all_accounts_info(self) -> Dict[str, OandaAccount]:
        """Get information for all configured accounts"""
        accounts = {}
        
        for account_id in self.settings.account_ids_list:
            try:
                account_info = await self.get_account_info(account_id)
                accounts[account_id] = account_info
            except Exception as e:
                logger.error(f"Failed to get info for account {account_id}: {e}")
        
        return accounts
    
    async def get_positions(self, account_id: str) -> List[OandaPosition]:
        """Get open positions for an account"""
        try:
            response = await self.client.get(f"{self.base_url}/v3/accounts/{account_id}/positions")
            
            if response.status_code == 200:
                positions_data = response.json()["positions"]
                positions = []
                
                for pos_data in positions_data:
                    long_units = float(pos_data.get("long", {}).get("units", 0))
                    short_units = float(pos_data.get("short", {}).get("units", 0))
                    
                    # Only include positions with actual units
                    if long_units != 0 or short_units != 0:
                        net_units = long_units + short_units
                        
                        # Calculate average price
                        long_avg = float(pos_data.get("long", {}).get("averagePrice", 0))
                        short_avg = float(pos_data.get("short", {}).get("averagePrice", 0))
                        
                        if long_units != 0 and short_units != 0:
                            avg_price = (long_avg * long_units + short_avg * short_units) / net_units
                        elif long_units != 0:
                            avg_price = long_avg
                        else:
                            avg_price = short_avg
                        
                        positions.append(OandaPosition(
                            instrument=pos_data["instrument"],
                            units=net_units,
                            average_price=avg_price,
                            unrealized_pnl=float(pos_data.get("unrealizedPL", 0)),
                            margin_used=float(pos_data.get("marginUsed", 0))
                        ))
                
                return positions
            else:
                raise OandaException(f"Failed to get positions: {response.status_code}")
                
        except httpx.TimeoutException:
            raise TimeoutException("get_positions", 10.0)
        except Exception as e:
            raise OandaException(f"Positions request failed: {e}")
    
    async def get_trades(self, account_id: str) -> List[OandaTrade]:
        """Get open trades for an account"""
        try:
            response = await self.client.get(f"{self.base_url}/v3/accounts/{account_id}/trades")
            
            if response.status_code == 200:
                trades_data = response.json()["trades"]
                trades = []
                
                for trade_data in trades_data:
                    trades.append(OandaTrade(
                        trade_id=trade_data["id"],
                        instrument=trade_data["instrument"],
                        units=float(trade_data["currentUnits"]),
                        price=float(trade_data["price"]),
                        unrealized_pnl=float(trade_data.get("unrealizedPL", 0)),
                        open_time=datetime.fromisoformat(trade_data["openTime"].replace("Z", "+00:00"))
                    ))
                
                return trades
            else:
                raise OandaException(f"Failed to get trades: {response.status_code}")
                
        except httpx.TimeoutException:
            raise TimeoutException("get_trades", 10.0)
        except Exception as e:
            raise OandaException(f"Trades request failed: {e}")
    
    async def place_market_order(self, account_id: str, instrument: str, units: float, 
                               stop_loss: Optional[float] = None, 
                               take_profit: Optional[float] = None) -> Dict[str, Any]:
        """Place a market order"""
        try:
            order_data = {
                "order": {
                    "type": "MARKET",
                    "instrument": instrument,
                    "units": str(int(units)),
                    "timeInForce": "FOK",
                    "positionFill": "DEFAULT"
                }
            }
            
            # Add stop loss if specified
            if stop_loss:
                order_data["order"]["stopLossOnFill"] = {
                    "price": str(stop_loss)
                }
            
            # Add take profit if specified
            if take_profit:
                order_data["order"]["takeProfitOnFill"] = {
                    "price": str(take_profit)
                }
            
            response = await self.client.post(
                f"{self.base_url}/v3/accounts/{account_id}/orders",
                json=order_data
            )
            
            if response.status_code == 201:
                result = response.json()
                return result
            else:
                error_data = response.json()
                error_msg = error_data.get("errorMessage", f"HTTP {response.status_code}")
                raise OandaException(f"Order placement failed: {error_msg}")
                
        except httpx.TimeoutException:
            raise TimeoutException("place_market_order", 10.0)
        except Exception as e:
            raise OandaException(f"Order placement failed: {e}")
    
    async def close_trade(self, account_id: str, trade_id: str, units: Optional[float] = None) -> Dict[str, Any]:
        """Close a trade (partially or completely)"""
        try:
            close_data = {}
            if units:
                close_data["units"] = str(int(units))
            else:
                close_data["units"] = "ALL"
            
            response = await self.client.put(
                f"{self.base_url}/v3/accounts/{account_id}/trades/{trade_id}/close",
                json=close_data
            )
            
            if response.status_code == 200:
                result = response.json()
                return result
            else:
                error_data = response.json()
                error_msg = error_data.get("errorMessage", f"HTTP {response.status_code}")
                raise OandaException(f"Trade close failed: {error_msg}")
                
        except httpx.TimeoutException:
            raise TimeoutException("close_trade", 10.0)
        except Exception as e:
            raise OandaException(f"Trade close failed: {e}")
    
    async def close_all_positions(self, account_id: str) -> List[Dict[str, Any]]:
        """Close all open positions for an account"""
        try:
            positions = await self.get_positions(account_id)
            results = []
            
            for position in positions:
                if position.units != 0:
                    # Close the position by placing opposite order
                    close_units = -position.units
                    
                    result = await self.place_market_order(
                        account_id, 
                        position.instrument, 
                        close_units
                    )
                    results.append(result)
            
            return results
            
        except Exception as e:
            raise OandaException(f"Close all positions failed: {e}")
    
    async def get_current_price(self, instrument: str) -> Dict[str, float]:
        """Get current bid/ask prices for an instrument"""
        try:
            response = await self.client.get(
                f"{self.base_url}/v3/instruments/{instrument}/candles",
                params={"count": 1, "granularity": "M1"}
            )
            
            if response.status_code == 200:
                candles = response.json()["candles"]
                if candles:
                    candle = candles[0]
                    return {
                        "bid": float(candle["bid"]["c"]),
                        "ask": float(candle["ask"]["c"]),
                        "mid": (float(candle["bid"]["c"]) + float(candle["ask"]["c"])) / 2
                    }
                else:
                    raise OandaException("No price data available")
            else:
                raise OandaException(f"Price request failed: {response.status_code}")
                
        except httpx.TimeoutException:
            raise TimeoutException("get_current_price", 10.0)
        except Exception as e:
            raise OandaException(f"Price request failed: {e}")
    
    async def execute_trade_signal(self, account_id: str, signal: TradeSignal) -> TradeResult:
        """Execute a trade signal"""
        try:
            # Calculate position size based on risk management
            account_info = await self.get_account_info(account_id)
            
            # Calculate units based on risk per trade
            risk_amount = account_info.balance * self.settings.risk_per_trade
            
            # Get current price for calculation
            price_data = await self.get_current_price(signal.instrument)
            current_price = price_data["ask" if signal.direction == "BUY" else "bid"]
            
            # Calculate stop loss distance in pips (simplified)
            if signal.stop_loss:
                stop_distance = abs(current_price - signal.stop_loss)
                pip_value = 0.0001  # Simplified - would need proper pip value calculation
                units = risk_amount / (stop_distance / pip_value * 10)  # Simplified calculation
            else:
                units = risk_amount / (current_price * 0.01)  # 1% risk default
            
            # Apply direction
            if signal.direction == "SELL":
                units = -units
            
            # Place the order
            order_result = await self.place_market_order(
                account_id=account_id,
                instrument=signal.instrument,
                units=units,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit
            )
            
            # Parse result
            if "orderFillTransaction" in order_result:
                fill = order_result["orderFillTransaction"]
                
                return TradeResult(
                    success=True,
                    trade_id=fill.get("tradeOpened", {}).get("tradeID"),
                    executed_price=float(fill["price"]),
                    executed_units=float(fill["units"]),
                    pnl=0.0,  # Will be calculated later
                    commission=float(fill.get("commission", 0)),
                    financing=float(fill.get("financing", 0)),
                    execution_time=datetime.utcnow(),
                    message="Trade executed successfully"
                )
            else:
                return TradeResult(
                    success=False,
                    message="Order was not filled",
                    execution_time=datetime.utcnow()
                )
                
        except Exception as e:
            logger.error(f"Trade execution failed: {e}")
            return TradeResult(
                success=False,
                message=f"Execution failed: {e}",
                execution_time=datetime.utcnow()
            )
    
    async def health_check(self) -> bool:
        """Perform health check on OANDA connection"""
        try:
            # Try to get accounts
            response = await self.client.get(f"{self.base_url}/v3/accounts")
            return response.status_code == 200
        except Exception:
            return False