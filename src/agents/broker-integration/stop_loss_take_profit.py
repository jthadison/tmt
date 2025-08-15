"""
Stop Loss and Take Profit Management
Story 8.3 - Task 2: Implement stop loss and take profit

Advanced SL/TP management with guaranteed stops, trailing stops, and dynamic adjustments.
"""
import asyncio
import logging
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from dataclasses import dataclass
import aiohttp

try:
    from .oanda_auth_handler import OandaAuthHandler, AccountContext
    from .order_executor import OrderSide
except ImportError:
    from oanda_auth_handler import OandaAuthHandler, AccountContext
    from order_executor import OrderSide

logger = logging.getLogger(__name__)

class StopType(Enum):
    FIXED = "fixed"
    TRAILING = "trailing"
    GUARANTEED = "guaranteed"

class StopLossStatus(Enum):
    ACTIVE = "active"
    TRIGGERED = "triggered"
    CANCELLED = "cancelled"
    MODIFIED = "modified"

@dataclass
class StopLossConfig:
    """Stop loss configuration"""
    price: Decimal
    distance_pips: Optional[int] = None
    stop_type: StopType = StopType.FIXED
    guaranteed: bool = False
    trailing_distance: Optional[Decimal] = None
    time_restriction: Optional[str] = None  # GTC, IOC, FOK

@dataclass
class TakeProfitConfig:
    """Take profit configuration"""
    price: Decimal
    distance_pips: Optional[int] = None
    time_restriction: Optional[str] = None

@dataclass
class StopLossOrder:
    """Active stop loss order tracking"""
    order_id: str
    parent_trade_id: str
    instrument: str
    units: int
    stop_price: Decimal
    stop_type: StopType
    guaranteed: bool
    trailing_distance: Optional[Decimal]
    created_at: datetime
    last_modified: datetime
    status: StopLossStatus
    trigger_price: Optional[Decimal] = None
    triggered_at: Optional[datetime] = None

class StopLossTakeProfitManager:
    """Advanced stop loss and take profit management system"""
    
    def __init__(self, auth_handler: OandaAuthHandler):
        self.auth_handler = auth_handler
        self.active_stops: Dict[str, StopLossOrder] = {}
        self.active_take_profits: Dict[str, Dict] = {}
        
        # Default pip values for distance calculations
        self.pip_values = {
            'EUR_USD': Decimal('0.0001'),
            'GBP_USD': Decimal('0.0001'),
            'USD_JPY': Decimal('0.01'),
            'USD_CHF': Decimal('0.0001'),
            'AUD_USD': Decimal('0.0001'),
            'USD_CAD': Decimal('0.0001'),
            'NZD_USD': Decimal('0.0001'),
            'EUR_GBP': Decimal('0.0001'),
            'EUR_JPY': Decimal('0.01'),
            'GBP_JPY': Decimal('0.01'),
        }
        self.default_pip_value = Decimal('0.0001')
        
        # Guaranteed stop loss fees (example rates)
        self.guaranteed_stop_fees = {
            'EUR_USD': Decimal('0.5'),  # 0.5 pips
            'GBP_USD': Decimal('0.5'),
            'USD_JPY': Decimal('0.5'),
            'default': Decimal('1.0')   # 1 pip for other pairs
        }
        
        # Session pool for API calls
        self.session_pool = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10),
            connector=aiohttp.TCPConnector(limit=50, keepalive_timeout=30)
        )
    
    def calculate_stop_loss_price(
        self, 
        entry_price: Decimal,
        side: OrderSide,
        stop_distance_pips: int,
        instrument: str
    ) -> Decimal:
        """
        Calculate stop loss price based on entry price and pip distance
        
        Args:
            entry_price: Entry price of the position
            side: Order side (BUY/SELL)
            stop_distance_pips: Stop distance in pips
            instrument: Trading instrument
            
        Returns:
            Calculated stop loss price
        """
        pip_value = self._get_pip_value(instrument)
        stop_distance = Decimal(str(stop_distance_pips)) * pip_value
        
        if side == OrderSide.BUY:
            # For buy orders, stop loss is below entry price
            stop_price = entry_price - stop_distance
        else:
            # For sell orders, stop loss is above entry price
            stop_price = entry_price + stop_distance
        
        # Round to appropriate decimal places
        return self._round_to_pip(stop_price, instrument)
    
    def calculate_take_profit_price(
        self,
        entry_price: Decimal,
        side: OrderSide, 
        profit_distance_pips: int,
        instrument: str
    ) -> Decimal:
        """Calculate take profit price based on entry price and pip distance"""
        pip_value = self._get_pip_value(instrument)
        profit_distance = Decimal(str(profit_distance_pips)) * pip_value
        
        if side == OrderSide.BUY:
            # For buy orders, take profit is above entry price
            tp_price = entry_price + profit_distance
        else:
            # For sell orders, take profit is below entry price
            tp_price = entry_price - profit_distance
        
        return self._round_to_pip(tp_price, instrument)
    
    async def create_stop_loss_order(
        self,
        user_id: str,
        account_id: str,
        trade_id: str,
        instrument: str,
        units: int,
        stop_config: StopLossConfig
    ) -> str:
        """
        Create stop loss order for existing position
        
        Args:
            user_id: User identifier
            account_id: OANDA account ID
            trade_id: Parent trade ID
            instrument: Trading instrument
            units: Position units (negative for closing long positions)
            stop_config: Stop loss configuration
            
        Returns:
            Stop loss order ID
        """
        logger.info(f"Creating stop loss order for trade {trade_id}: {stop_config.price}")
        
        try:
            # Get authenticated context
            context = await self.auth_handler.get_session_context(user_id, account_id)
            if not context or not context.session_valid:
                context = await self.auth_handler.authenticate_user(user_id, account_id, "practice")
            
            # Build stop loss order request
            order_request = self._build_stop_loss_request(
                trade_id, instrument, units, stop_config
            )
            
            # Send request
            response = await self._send_order_request(context, order_request)
            
            # Extract order ID
            order_id = self._extract_order_id(response)
            
            # Track stop loss order
            stop_order = StopLossOrder(
                order_id=order_id,
                parent_trade_id=trade_id,
                instrument=instrument,
                units=units,
                stop_price=stop_config.price,
                stop_type=stop_config.stop_type,
                guaranteed=stop_config.guaranteed,
                trailing_distance=stop_config.trailing_distance,
                created_at=datetime.utcnow(),
                last_modified=datetime.utcnow(),
                status=StopLossStatus.ACTIVE
            )
            
            self.active_stops[order_id] = stop_order
            
            logger.info(f"Created stop loss order {order_id} for trade {trade_id}")
            return order_id
            
        except Exception as e:
            logger.error(f"Failed to create stop loss order for trade {trade_id}: {e}")
            raise
    
    async def create_take_profit_order(
        self,
        user_id: str,
        account_id: str,
        trade_id: str,
        instrument: str,
        units: int,
        tp_config: TakeProfitConfig
    ) -> str:
        """Create take profit order for existing position"""
        logger.info(f"Creating take profit order for trade {trade_id}: {tp_config.price}")
        
        try:
            context = await self.auth_handler.get_session_context(user_id, account_id)
            if not context or not context.session_valid:
                context = await self.auth_handler.authenticate_user(user_id, account_id, "practice")
            
            order_request = self._build_take_profit_request(
                trade_id, instrument, units, tp_config
            )
            
            response = await self._send_order_request(context, order_request)
            order_id = self._extract_order_id(response)
            
            # Track take profit order
            self.active_take_profits[order_id] = {
                'parent_trade_id': trade_id,
                'instrument': instrument,
                'units': units,
                'price': tp_config.price,
                'created_at': datetime.utcnow(),
                'status': 'active'
            }
            
            logger.info(f"Created take profit order {order_id} for trade {trade_id}")
            return order_id
            
        except Exception as e:
            logger.error(f"Failed to create take profit order for trade {trade_id}: {e}")
            raise
    
    def _build_stop_loss_request(
        self, 
        trade_id: str,
        instrument: str,
        units: int,
        stop_config: StopLossConfig
    ) -> Dict:
        """Build OANDA stop loss order request"""
        order_type = "STOP_LOSS"
        if stop_config.stop_type == StopType.TRAILING:
            order_type = "TRAILING_STOP_LOSS"
        
        order_request = {
            "order": {
                "type": order_type,
                "tradeID": trade_id,
                "price": str(stop_config.price),
                "timeInForce": stop_config.time_restriction or "GTC"
            }
        }
        
        # Add guaranteed stop loss (if supported and requested)
        if stop_config.guaranteed:
            order_request["order"]["guaranteed"] = True
            # Note: Guaranteed stops typically have a premium cost
        
        # Add trailing distance for trailing stops
        if stop_config.stop_type == StopType.TRAILING and stop_config.trailing_distance:
            order_request["order"]["distance"] = str(stop_config.trailing_distance)
        
        return order_request
    
    def _build_take_profit_request(
        self,
        trade_id: str,
        instrument: str, 
        units: int,
        tp_config: TakeProfitConfig
    ) -> Dict:
        """Build OANDA take profit order request"""
        return {
            "order": {
                "type": "TAKE_PROFIT",
                "tradeID": trade_id,
                "price": str(tp_config.price),
                "timeInForce": tp_config.time_restriction or "GTC"
            }
        }
    
    async def _send_order_request(self, context: AccountContext, order_request: Dict) -> Dict:
        """Send order request to OANDA API"""
        headers = {
            'Authorization': f'Bearer {context.api_key}',
            'Content-Type': 'application/json'
        }
        
        url = f"{context.base_url}/v3/accounts/{context.account_id}/orders"
        
        async with self.session_pool.post(url, json=order_request, headers=headers) as response:
            response_data = await response.json()
            
            if response.status != 201:
                error_msg = response_data.get('errorMessage', 'Unknown error')
                error_code = response_data.get('errorCode', 'UNKNOWN')
                raise Exception(f"Order request failed ({response.status}): {error_code} - {error_msg}")
            
            return response_data
    
    def _extract_order_id(self, response: Dict) -> str:
        """Extract order ID from OANDA response"""
        if 'orderCreateTransaction' in response:
            return response['orderCreateTransaction']['id']
        elif 'lastTransactionID' in response:
            return response['lastTransactionID']
        else:
            raise Exception("Cannot extract order ID from response")
    
    async def modify_stop_loss(
        self,
        user_id: str,
        account_id: str,
        order_id: str,
        new_price: Decimal,
        new_trailing_distance: Optional[Decimal] = None
    ) -> bool:
        """
        Modify existing stop loss order
        
        Args:
            user_id: User identifier
            account_id: OANDA account ID
            order_id: Stop loss order ID to modify
            new_price: New stop loss price
            new_trailing_distance: New trailing distance (for trailing stops)
            
        Returns:
            True if modification successful
        """
        if order_id not in self.active_stops:
            logger.warning(f"Cannot modify unknown stop loss order: {order_id}")
            return False
        
        try:
            context = await self.auth_handler.get_session_context(user_id, account_id)
            if not context:
                return False
            
            headers = {
                'Authorization': f'Bearer {context.api_key}',
                'Content-Type': 'application/json'
            }
            
            modify_request = {
                "order": {
                    "price": str(new_price)
                }
            }
            
            if new_trailing_distance:
                modify_request["order"]["distance"] = str(new_trailing_distance)
            
            url = f"{context.base_url}/v3/accounts/{context.account_id}/orders/{order_id}"
            
            async with self.session_pool.put(url, json=modify_request, headers=headers) as response:
                if response.status == 200:
                    # Update tracking
                    stop_order = self.active_stops[order_id]
                    stop_order.stop_price = new_price
                    stop_order.last_modified = datetime.utcnow()
                    stop_order.status = StopLossStatus.MODIFIED
                    if new_trailing_distance:
                        stop_order.trailing_distance = new_trailing_distance
                    
                    logger.info(f"Modified stop loss order {order_id}: new price {new_price}")
                    return True
                else:
                    logger.error(f"Failed to modify stop loss order {order_id}: {response.status}")
                    return False
        
        except Exception as e:
            logger.error(f"Error modifying stop loss order {order_id}: {e}")
            return False
    
    async def cancel_stop_loss(self, user_id: str, account_id: str, order_id: str) -> bool:
        """Cancel stop loss order"""
        if order_id not in self.active_stops:
            logger.warning(f"Cannot cancel unknown stop loss order: {order_id}")
            return False
        
        try:
            context = await self.auth_handler.get_session_context(user_id, account_id)
            if not context:
                return False
            
            headers = {
                'Authorization': f'Bearer {context.api_key}',
                'Content-Type': 'application/json'
            }
            
            url = f"{context.base_url}/v3/accounts/{context.account_id}/orders/{order_id}/cancel"
            
            async with self.session_pool.put(url, headers=headers) as response:
                if response.status == 200:
                    # Update tracking
                    stop_order = self.active_stops[order_id]
                    stop_order.status = StopLossStatus.CANCELLED
                    stop_order.last_modified = datetime.utcnow()
                    
                    logger.info(f"Cancelled stop loss order {order_id}")
                    return True
                else:
                    logger.error(f"Failed to cancel stop loss order {order_id}: {response.status}")
                    return False
        
        except Exception as e:
            logger.error(f"Error cancelling stop loss order {order_id}: {e}")
            return False
    
    async def update_trailing_stop_loss(
        self, 
        order_id: str, 
        current_market_price: Decimal
    ) -> bool:
        """Update trailing stop loss based on current market price"""
        if order_id not in self.active_stops:
            return False
        
        stop_order = self.active_stops[order_id]
        
        if stop_order.stop_type != StopType.TRAILING or not stop_order.trailing_distance:
            return False
        
        # Calculate new trailing stop price
        # (This logic would be more complex in a real implementation)
        new_stop_price = current_market_price - stop_order.trailing_distance
        
        # Only update if the new stop is more favorable
        if new_stop_price > stop_order.stop_price:
            # Update would be done via modify_stop_loss in practice
            stop_order.stop_price = new_stop_price
            stop_order.last_modified = datetime.utcnow()
            logger.debug(f"Updated trailing stop {order_id} to {new_stop_price}")
            return True
        
        return False
    
    def _get_pip_value(self, instrument: str) -> Decimal:
        """Get pip value for instrument"""
        return self.pip_values.get(instrument, self.default_pip_value)
    
    def _round_to_pip(self, price: Decimal, instrument: str) -> Decimal:
        """Round price to appropriate pip precision"""
        pip_value = self._get_pip_value(instrument)
        
        if pip_value == Decimal('0.01'):  # JPY pairs
            return price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        else:  # Most other pairs
            return price.quantize(Decimal('0.00001'), rounding=ROUND_HALF_UP)
    
    def get_stop_loss_orders(self, trade_id: Optional[str] = None) -> List[StopLossOrder]:
        """Get stop loss orders, optionally filtered by trade ID"""
        if trade_id:
            return [
                stop for stop in self.active_stops.values()
                if stop.parent_trade_id == trade_id
            ]
        return list(self.active_stops.values())
    
    def get_guaranteed_stop_fee(self, instrument: str, units: int) -> Decimal:
        """Calculate guaranteed stop loss fee"""
        fee_per_pip = self.guaranteed_stop_fees.get(
            instrument, 
            self.guaranteed_stop_fees['default']
        )
        
        # Convert units to lots (assuming 100,000 units = 1 lot)
        lots = Decimal(abs(units)) / Decimal('100000')
        
        return fee_per_pip * lots
    
    def get_active_stops_summary(self) -> Dict[str, Any]:
        """Get summary of active stop loss orders"""
        active_count = len([s for s in self.active_stops.values() if s.status == StopLossStatus.ACTIVE])
        trailing_count = len([s for s in self.active_stops.values() if s.stop_type == StopType.TRAILING])
        guaranteed_count = len([s for s in self.active_stops.values() if s.guaranteed])
        
        return {
            'total_stops': len(self.active_stops),
            'active_stops': active_count,
            'trailing_stops': trailing_count,
            'guaranteed_stops': guaranteed_count,
            'cancelled_stops': len([s for s in self.active_stops.values() if s.status == StopLossStatus.CANCELLED]),
            'triggered_stops': len([s for s in self.active_stops.values() if s.status == StopLossStatus.TRIGGERED])
        }
    
    async def close(self):
        """Clean up resources"""
        if self.session_pool and not self.session_pool.closed:
            await self.session_pool.close()