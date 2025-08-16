"""
OANDA Pending Order Manager

Handles limit and stop order placement, modification, and cancellation
for OANDA broker integration. Supports GTC/GTD time-in-force options.
"""

import asyncio
import logging
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass
from enum import Enum

from .client import OandaClientInterface
from .stream_manager import StreamManagerInterface


class OrderType(Enum):
    """Order type enumeration"""
    LIMIT = "LIMIT"
    STOP = "STOP"
    MARKET_IF_TOUCHED = "MARKET_IF_TOUCHED"


class OrderSide(Enum):
    """Order side enumeration"""
    BUY = "BUY"
    SELL = "SELL"


class TimeInForce(Enum):
    """Time in force enumeration"""
    GTC = "GTC"  # Good Till Cancelled
    GTD = "GTD"  # Good Till Date


class OrderStatus(Enum):
    """Order status enumeration"""
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


@dataclass
class OrderInfo:
    """Comprehensive order information"""
    order_id: str
    instrument: str
    order_type: OrderType
    side: OrderSide
    units: Decimal
    price: Decimal
    time_in_force: TimeInForce
    status: OrderStatus
    current_distance: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    expiry_time: Optional[datetime] = None
    created_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    fill_price: Optional[Decimal] = None


@dataclass
class OrderResult:
    """Order placement/modification result"""
    success: bool
    order_id: Optional[str] = None
    message: str = ""
    order_info: Optional[OrderInfo] = None


class OandaPendingOrderManager:
    """
    Manages pending orders (limit, stop, market-if-touched) for OANDA.
    
    Features:
    - Limit and stop order placement with validation
    - GTC/GTD time-in-force support
    - Order modification and cancellation
    - Real-time order monitoring
    - Distance tracking from current price
    """
    
    def __init__(
        self, 
        client: OandaClientInterface, 
        price_stream: StreamManagerInterface,
        refresh_interval: float = 5.0
    ):
        self.client = client
        self.price_stream = price_stream
        self.refresh_interval = refresh_interval
        
        # Order tracking
        self.pending_orders: Dict[str, OrderInfo] = {}
        
        # Monitoring
        self.is_monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        
        # Logger
        self.logger = logging.getLogger(__name__)
        
    async def place_limit_order(
        self,
        instrument: str,
        units: Union[Decimal, str],
        price: Union[Decimal, str],
        time_in_force: TimeInForce = TimeInForce.GTC,
        expiry_time: Optional[datetime] = None,
        stop_loss: Optional[Union[Decimal, str]] = None,
        take_profit: Optional[Union[Decimal, str]] = None
    ) -> OrderResult:
        """
        Place a limit order.
        
        Args:
            instrument: Trading instrument (e.g., "EUR_USD")
            units: Order size (positive for buy, negative for sell)
            price: Limit price
            time_in_force: GTC or GTD
            expiry_time: Expiry time for GTD orders
            stop_loss: Optional stop loss price
            take_profit: Optional take profit price
            
        Returns:
            OrderResult with success status and order details
        """
        try:
            # Convert to Decimal
            units_decimal = Decimal(str(units))
            price_decimal = Decimal(str(price))
            
            # Determine order side
            side = OrderSide.BUY if units_decimal > 0 else OrderSide.SELL
            
            # Validate limit order price
            current_price = await self._get_current_price(instrument)
            if not self._validate_limit_order_price(units_decimal, price_decimal, current_price):
                return OrderResult(
                    success=False,
                    message=f"Invalid limit order price {price_decimal} for {side.value}"
                )
            
            # Build order request
            order_request = {
                "order": {
                    "type": "LIMIT",
                    "instrument": instrument,
                    "units": str(int(units_decimal)),
                    "price": str(price_decimal),
                    "timeInForce": time_in_force.value
                }
            }
            
            # Add expiry time for GTD orders
            if time_in_force == TimeInForce.GTD:
                if not expiry_time:
                    expiry_time = datetime.now(timezone.utc) + timedelta(days=1)
                order_request["order"]["gtdTime"] = expiry_time.strftime('%Y-%m-%dT%H:%M:%S.000000000Z')
            
            # Add stop loss if specified
            if stop_loss:
                stop_loss_decimal = Decimal(str(stop_loss))
                order_request["order"]["stopLossOnFill"] = {"price": str(stop_loss_decimal)}
            
            # Add take profit if specified
            if take_profit:
                take_profit_decimal = Decimal(str(take_profit))
                order_request["order"]["takeProfitOnFill"] = {"price": str(take_profit_decimal)}
            
            # Place order
            response = await self.client.post(
                f"/v3/accounts/{self.client.account_id}/orders",
                json=order_request
            )
            
            if response and "orderCreateTransaction" in response:
                order_id = response["orderCreateTransaction"]["id"]
                
                # Create order info
                order_info = OrderInfo(
                    order_id=order_id,
                    instrument=instrument,
                    order_type=OrderType.LIMIT,
                    side=side,
                    units=abs(units_decimal),
                    price=price_decimal,
                    time_in_force=time_in_force,
                    status=OrderStatus.PENDING,
                    stop_loss=Decimal(str(stop_loss)) if stop_loss else None,
                    take_profit=Decimal(str(take_profit)) if take_profit else None,
                    expiry_time=expiry_time,
                    created_at=datetime.now(timezone.utc)
                )
                
                # Calculate distance from current price
                order_info.current_distance = self._calculate_price_distance(
                    price_decimal, current_price, instrument
                )
                
                # Store order
                self.pending_orders[order_id] = order_info
                
                # Start monitoring if not already active
                await self._ensure_monitoring()
                
                self.logger.info(f"Limit order placed: {order_id} for {instrument}")
                
                return OrderResult(
                    success=True,
                    order_id=order_id,
                    message=f"Limit order placed successfully",
                    order_info=order_info
                )
            else:
                return OrderResult(
                    success=False,
                    message="Failed to place limit order"
                )
                
        except Exception as e:
            self.logger.error(f"Error placing limit order: {e}")
            return OrderResult(
                success=False,
                message=f"Error placing limit order: {str(e)}"
            )
    
    async def place_stop_order(
        self,
        instrument: str,
        units: Union[Decimal, str],
        price: Union[Decimal, str],
        time_in_force: TimeInForce = TimeInForce.GTC,
        expiry_time: Optional[datetime] = None,
        stop_loss: Optional[Union[Decimal, str]] = None,
        take_profit: Optional[Union[Decimal, str]] = None
    ) -> OrderResult:
        """
        Place a stop order.
        
        Args:
            instrument: Trading instrument (e.g., "EUR_USD")
            units: Order size (positive for buy, negative for sell)
            price: Stop price
            time_in_force: GTC or GTD
            expiry_time: Expiry time for GTD orders
            stop_loss: Optional stop loss price
            take_profit: Optional take profit price
            
        Returns:
            OrderResult with success status and order details
        """
        try:
            # Convert to Decimal
            units_decimal = Decimal(str(units))
            price_decimal = Decimal(str(price))
            
            # Determine order side
            side = OrderSide.BUY if units_decimal > 0 else OrderSide.SELL
            
            # Validate stop order price
            current_price = await self._get_current_price(instrument)
            if not self._validate_stop_order_price(units_decimal, price_decimal, current_price):
                return OrderResult(
                    success=False,
                    message=f"Invalid stop order price {price_decimal} for {side.value}"
                )
            
            # Build order request
            order_request = {
                "order": {
                    "type": "STOP",
                    "instrument": instrument,
                    "units": str(int(units_decimal)),
                    "price": str(price_decimal),
                    "timeInForce": time_in_force.value
                }
            }
            
            # Add expiry time for GTD orders
            if time_in_force == TimeInForce.GTD:
                if not expiry_time:
                    expiry_time = datetime.now(timezone.utc) + timedelta(days=1)
                order_request["order"]["gtdTime"] = expiry_time.strftime('%Y-%m-%dT%H:%M:%S.000000000Z')
            
            # Add stop loss if specified
            if stop_loss:
                stop_loss_decimal = Decimal(str(stop_loss))
                order_request["order"]["stopLossOnFill"] = {"price": str(stop_loss_decimal)}
            
            # Add take profit if specified
            if take_profit:
                take_profit_decimal = Decimal(str(take_profit))
                order_request["order"]["takeProfitOnFill"] = {"price": str(take_profit_decimal)}
            
            # Place order
            response = await self.client.post(
                f"/v3/accounts/{self.client.account_id}/orders",
                json=order_request
            )
            
            if response and "orderCreateTransaction" in response:
                order_id = response["orderCreateTransaction"]["id"]
                
                # Create order info
                order_info = OrderInfo(
                    order_id=order_id,
                    instrument=instrument,
                    order_type=OrderType.STOP,
                    side=side,
                    units=abs(units_decimal),
                    price=price_decimal,
                    time_in_force=time_in_force,
                    status=OrderStatus.PENDING,
                    stop_loss=Decimal(str(stop_loss)) if stop_loss else None,
                    take_profit=Decimal(str(take_profit)) if take_profit else None,
                    expiry_time=expiry_time,
                    created_at=datetime.now(timezone.utc)
                )
                
                # Calculate distance from current price
                order_info.current_distance = self._calculate_price_distance(
                    price_decimal, current_price, instrument
                )
                
                # Store order
                self.pending_orders[order_id] = order_info
                
                # Start monitoring if not already active
                await self._ensure_monitoring()
                
                self.logger.info(f"Stop order placed: {order_id} for {instrument}")
                
                return OrderResult(
                    success=True,
                    order_id=order_id,
                    message=f"Stop order placed successfully",
                    order_info=order_info
                )
            else:
                return OrderResult(
                    success=False,
                    message="Failed to place stop order"
                )
                
        except Exception as e:
            self.logger.error(f"Error placing stop order: {e}")
            return OrderResult(
                success=False,
                message=f"Error placing stop order: {str(e)}"
            )
    
    async def place_market_if_touched_order(
        self,
        instrument: str,
        units: Union[Decimal, str],
        price: Union[Decimal, str],
        time_in_force: TimeInForce = TimeInForce.GTC,
        expiry_time: Optional[datetime] = None,
        stop_loss: Optional[Union[Decimal, str]] = None,
        take_profit: Optional[Union[Decimal, str]] = None
    ) -> OrderResult:
        """
        Place a market-if-touched order.
        
        Args:
            instrument: Trading instrument (e.g., "EUR_USD")
            units: Order size (positive for buy, negative for sell)
            price: Touch price
            time_in_force: GTC or GTD
            expiry_time: Expiry time for GTD orders
            stop_loss: Optional stop loss price
            take_profit: Optional take profit price
            
        Returns:
            OrderResult with success status and order details
        """
        try:
            # Convert to Decimal
            units_decimal = Decimal(str(units))
            price_decimal = Decimal(str(price))
            
            # Determine order side
            side = OrderSide.BUY if units_decimal > 0 else OrderSide.SELL
            
            # Build order request
            order_request = {
                "order": {
                    "type": "MARKET_IF_TOUCHED",
                    "instrument": instrument,
                    "units": str(int(units_decimal)),
                    "price": str(price_decimal),
                    "timeInForce": time_in_force.value
                }
            }
            
            # Add expiry time for GTD orders
            if time_in_force == TimeInForce.GTD:
                if not expiry_time:
                    expiry_time = datetime.now(timezone.utc) + timedelta(days=1)
                order_request["order"]["gtdTime"] = expiry_time.strftime('%Y-%m-%dT%H:%M:%S.000000000Z')
            
            # Add stop loss if specified
            if stop_loss:
                stop_loss_decimal = Decimal(str(stop_loss))
                order_request["order"]["stopLossOnFill"] = {"price": str(stop_loss_decimal)}
            
            # Add take profit if specified
            if take_profit:
                take_profit_decimal = Decimal(str(take_profit))
                order_request["order"]["takeProfitOnFill"] = {"price": str(take_profit_decimal)}
            
            # Place order
            response = await self.client.post(
                f"/v3/accounts/{self.client.account_id}/orders",
                json=order_request
            )
            
            if response and "orderCreateTransaction" in response:
                order_id = response["orderCreateTransaction"]["id"]
                
                # Get current price for distance calculation
                current_price = await self._get_current_price(instrument)
                
                # Create order info
                order_info = OrderInfo(
                    order_id=order_id,
                    instrument=instrument,
                    order_type=OrderType.MARKET_IF_TOUCHED,
                    side=side,
                    units=abs(units_decimal),
                    price=price_decimal,
                    time_in_force=time_in_force,
                    status=OrderStatus.PENDING,
                    stop_loss=Decimal(str(stop_loss)) if stop_loss else None,
                    take_profit=Decimal(str(take_profit)) if take_profit else None,
                    expiry_time=expiry_time,
                    created_at=datetime.now(timezone.utc)
                )
                
                # Calculate distance from current price
                order_info.current_distance = self._calculate_price_distance(
                    price_decimal, current_price, instrument
                )
                
                # Store order
                self.pending_orders[order_id] = order_info
                
                # Start monitoring if not already active
                await self._ensure_monitoring()
                
                self.logger.info(f"Market-if-touched order placed: {order_id} for {instrument}")
                
                return OrderResult(
                    success=True,
                    order_id=order_id,
                    message=f"Market-if-touched order placed successfully",
                    order_info=order_info
                )
            else:
                return OrderResult(
                    success=False,
                    message="Failed to place market-if-touched order"
                )
                
        except Exception as e:
            self.logger.error(f"Error placing market-if-touched order: {e}")
            return OrderResult(
                success=False,
                message=f"Error placing market-if-touched order: {str(e)}"
            )
    
    async def get_pending_orders(
        self, 
        instrument: Optional[str] = None,
        order_type: Optional[OrderType] = None
    ) -> List[OrderInfo]:
        """
        Get all pending orders with current distance from market price.
        
        Args:
            instrument: Filter by instrument (optional)
            order_type: Filter by order type (optional)
            
        Returns:
            List of OrderInfo objects with updated distances
        """
        try:
            # Refresh from OANDA
            await self._refresh_pending_orders()
            
            # Filter orders
            orders = list(self.pending_orders.values())
            
            if instrument:
                orders = [order for order in orders if order.instrument == instrument]
            
            if order_type:
                orders = [order for order in orders if order.order_type == order_type]
            
            # Update distances for each order
            for order in orders:
                try:
                    current_price = await self._get_current_price(order.instrument)
                    order.current_distance = self._calculate_price_distance(
                        order.price, current_price, order.instrument
                    )
                except Exception as e:
                    self.logger.warning(f"Failed to update distance for order {order.order_id}: {e}")
            
            # Sort by distance (closest first)
            orders.sort(key=lambda x: abs(x.current_distance) if x.current_distance else Decimal('999999'))
            
            return orders
            
        except Exception as e:
            self.logger.error(f"Error getting pending orders: {e}")
            return []
    
    def _validate_limit_order_price(
        self, 
        units: Decimal, 
        limit_price: Decimal, 
        current_price: Decimal
    ) -> bool:
        """Validate limit order price is correct relative to market"""
        if units > 0:  # Buy limit
            return limit_price < current_price  # Must be below market
        else:  # Sell limit
            return limit_price > current_price  # Must be above market
    
    def _validate_stop_order_price(
        self, 
        units: Decimal, 
        stop_price: Decimal, 
        current_price: Decimal
    ) -> bool:
        """Validate stop order price is correct relative to market"""
        if units > 0:  # Buy stop
            return stop_price > current_price  # Must be above market
        else:  # Sell stop
            return stop_price < current_price  # Must be below market
    
    async def _get_current_price(self, instrument: str) -> Decimal:
        """Get current market price for instrument"""
        try:
            response = await self.client.get(
                f"/v3/accounts/{self.client.account_id}/pricing",
                params={"instruments": instrument}
            )
            
            if response and "prices" in response and response["prices"]:
                price_data = response["prices"][0]
                bid = Decimal(price_data["closeoutBid"])
                ask = Decimal(price_data["closeoutAsk"])
                return (bid + ask) / 2
            
            return Decimal('0')
            
        except Exception as e:
            self.logger.error(f"Error getting current price for {instrument}: {e}")
            return Decimal('0')
    
    def _calculate_price_distance(
        self, 
        target_price: Decimal, 
        current_price: Decimal, 
        instrument: str
    ) -> Decimal:
        """Calculate distance in pips between target and current price"""
        try:
            pip_value = self._get_pip_value(instrument)
            distance_pips = (target_price - current_price) / pip_value
            return distance_pips
            
        except Exception:
            return Decimal('0')
    
    def _get_pip_value(self, instrument: str) -> Decimal:
        """Get pip value for instrument"""
        if 'JPY' in instrument:
            return Decimal('0.01')
        else:
            return Decimal('0.0001')
    
    async def _refresh_pending_orders(self):
        """Refresh pending orders from OANDA"""
        try:
            response = await self.client.get(
                f"/v3/accounts/{self.client.account_id}/orders"
            )
            
            if response and "orders" in response:
                # Update order statuses
                server_orders = {order["id"]: order for order in response["orders"]}
                
                # Check for filled or cancelled orders
                for order_id in list(self.pending_orders.keys()):
                    if order_id not in server_orders:
                        # Order no longer pending - mark as filled/cancelled
                        if order_id in self.pending_orders:
                            del self.pending_orders[order_id]
                            self.logger.info(f"Order {order_id} no longer pending")
                
        except Exception as e:
            self.logger.error(f"Error refreshing pending orders: {e}")
    
    async def _ensure_monitoring(self):
        """Ensure monitoring is active"""
        if not self.is_monitoring and self.pending_orders:
            self.is_monitoring = True
            self._monitor_task = asyncio.create_task(self._monitor_orders())
    
    async def _monitor_orders(self):
        """Monitor pending orders for expiry and updates"""
        try:
            while self.pending_orders and self.is_monitoring:
                await self._refresh_pending_orders()
                await self._check_order_expiry()
                await asyncio.sleep(self.refresh_interval)
                
        except Exception as e:
            self.logger.error(f"Error in order monitoring: {e}")
        finally:
            self.is_monitoring = False
    
    async def _check_order_expiry(self):
        """Check for expired orders"""
        current_time = datetime.now(timezone.utc)
        
        for order_id, order in list(self.pending_orders.items()):
            if (order.expiry_time and 
                current_time >= order.expiry_time and 
                order.status == OrderStatus.PENDING):
                
                # Cancel expired order
                await self.cancel_pending_order(order_id)
                self.logger.info(f"Cancelled expired order: {order_id}")
    
    async def modify_pending_order(
        self,
        order_id: str,
        new_price: Optional[Union[Decimal, str]] = None,
        new_stop_loss: Optional[Union[Decimal, str]] = None,
        new_take_profit: Optional[Union[Decimal, str]] = None,
        new_expiry: Optional[datetime] = None
    ) -> OrderResult:
        """
        Modify a pending order.
        
        Args:
            order_id: Order ID to modify
            new_price: New order price (optional)
            new_stop_loss: New stop loss price (optional)
            new_take_profit: New take profit price (optional)
            new_expiry: New expiry time (optional)
            
        Returns:
            OrderResult with success status
        """
        try:
            if order_id not in self.pending_orders:
                return OrderResult(
                    success=False,
                    message=f"Order {order_id} not found"
                )
            
            order = self.pending_orders[order_id]
            
            # Build modification request
            replace_order = {
                "type": order.order_type.value,
                "instrument": order.instrument,
                "units": str(int(order.units if order.side == OrderSide.BUY else -order.units)),
                "timeInForce": order.time_in_force.value
            }
            
            # Update price if provided
            if new_price is not None:
                new_price_decimal = Decimal(str(new_price))
                
                # Validate new price
                current_price = await self._get_current_price(order.instrument)
                units_for_validation = order.units if order.side == OrderSide.BUY else -order.units
                
                if order.order_type == OrderType.LIMIT:
                    if not self._validate_limit_order_price(units_for_validation, new_price_decimal, current_price):
                        return OrderResult(
                            success=False,
                            message=f"Invalid limit order price {new_price_decimal}"
                        )
                elif order.order_type == OrderType.STOP:
                    if not self._validate_stop_order_price(units_for_validation, new_price_decimal, current_price):
                        return OrderResult(
                            success=False,
                            message=f"Invalid stop order price {new_price_decimal}"
                        )
                
                replace_order["price"] = str(new_price_decimal)
            else:
                replace_order["price"] = str(order.price)
            
            # Update stop loss if provided
            if new_stop_loss is not None:
                replace_order["stopLossOnFill"] = {"price": str(new_stop_loss)}
            elif order.stop_loss:
                replace_order["stopLossOnFill"] = {"price": str(order.stop_loss)}
            
            # Update take profit if provided
            if new_take_profit is not None:
                replace_order["takeProfitOnFill"] = {"price": str(new_take_profit)}
            elif order.take_profit:
                replace_order["takeProfitOnFill"] = {"price": str(order.take_profit)}
            
            # Update expiry if provided
            if new_expiry is not None:
                if order.time_in_force == TimeInForce.GTD:
                    replace_order["gtdTime"] = new_expiry.strftime('%Y-%m-%dT%H:%M:%S.000000000Z')
            elif order.expiry_time and order.time_in_force == TimeInForce.GTD:
                replace_order["gtdTime"] = order.expiry_time.strftime('%Y-%m-%dT%H:%M:%S.000000000Z')
            
            # Replace order
            replace_request = {"order": replace_order}
            
            response = await self.client.put(
                f"/v3/accounts/{self.client.account_id}/orders/{order_id}",
                json=replace_request
            )
            
            if response and "orderCreateTransaction" in response:
                new_order_id = response["orderCreateTransaction"]["id"]
                
                # Update order info
                if new_price is not None:
                    order.price = Decimal(str(new_price))
                if new_stop_loss is not None:
                    order.stop_loss = Decimal(str(new_stop_loss))
                if new_take_profit is not None:
                    order.take_profit = Decimal(str(new_take_profit))
                if new_expiry is not None:
                    order.expiry_time = new_expiry
                
                # Update order ID if changed
                if new_order_id != order_id:
                    del self.pending_orders[order_id]
                    order.order_id = new_order_id
                    self.pending_orders[new_order_id] = order
                
                # Update distance
                current_price = await self._get_current_price(order.instrument)
                order.current_distance = self._calculate_price_distance(
                    order.price, current_price, order.instrument
                )
                
                self.logger.info(f"Order {order_id} modified successfully")
                
                return OrderResult(
                    success=True,
                    order_id=new_order_id,
                    message="Order modified successfully",
                    order_info=order
                )
            else:
                return OrderResult(
                    success=False,
                    message="Failed to modify order"
                )
                
        except Exception as e:
            self.logger.error(f"Error modifying order {order_id}: {e}")
            return OrderResult(
                success=False,
                message=f"Error modifying order: {str(e)}"
            )
    
    async def cancel_pending_order(self, order_id: str) -> OrderResult:
        """
        Cancel a pending order.
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            OrderResult with success status
        """
        try:
            # Cancel order on OANDA
            response = await self.client.put(
                f"/v3/accounts/{self.client.account_id}/orders/{order_id}/cancel"
            )
            
            if response and "orderCancelTransaction" in response:
                # Remove from local tracking
                if order_id in self.pending_orders:
                    order = self.pending_orders[order_id]
                    order.status = OrderStatus.CANCELLED
                    order.cancelled_at = datetime.now(timezone.utc)
                    del self.pending_orders[order_id]
                
                self.logger.info(f"Order {order_id} cancelled successfully")
                
                return OrderResult(
                    success=True,
                    order_id=order_id,
                    message="Order cancelled successfully"
                )
            else:
                return OrderResult(
                    success=False,
                    message="Failed to cancel order"
                )
                
        except Exception as e:
            self.logger.error(f"Error cancelling order {order_id}: {e}")
            return OrderResult(
                success=False,
                message=f"Error cancelling order: {str(e)}"
            )
    
    async def cancel_all_orders(
        self, 
        instrument: Optional[str] = None,
        order_type: Optional[OrderType] = None
    ) -> Dict[str, OrderResult]:
        """
        Cancel all pending orders, optionally filtered by instrument or type.
        
        Args:
            instrument: Cancel only orders for this instrument (optional)
            order_type: Cancel only orders of this type (optional)
            
        Returns:
            Dictionary mapping order_id to OrderResult
        """
        results = {}
        
        # Get orders to cancel
        orders_to_cancel = []
        for order_id, order in self.pending_orders.items():
            if instrument and order.instrument != instrument:
                continue
            if order_type and order.order_type != order_type:
                continue
            orders_to_cancel.append(order_id)
        
        # Cancel each order
        for order_id in orders_to_cancel:
            result = await self.cancel_pending_order(order_id)
            results[order_id] = result
        
        self.logger.info(f"Cancelled {len(orders_to_cancel)} orders")
        
        return results
    
    async def get_order_status(self, order_id: str) -> Optional[OrderInfo]:
        """
        Get detailed status of a specific order.
        
        Args:
            order_id: Order ID to check
            
        Returns:
            OrderInfo if found, None otherwise
        """
        try:
            if order_id in self.pending_orders:
                order = self.pending_orders[order_id]
                
                # Update distance
                current_price = await self._get_current_price(order.instrument)
                order.current_distance = self._calculate_price_distance(
                    order.price, current_price, order.instrument
                )
                
                return order
            
            # Check if order exists on server but not in local cache
            response = await self.client.get(
                f"/v3/accounts/{self.client.account_id}/orders/{order_id}"
            )
            
            if response and "order" in response:
                # Order exists but not in cache - refresh cache
                await self._refresh_pending_orders()
                return self.pending_orders.get(order_id)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting order status for {order_id}: {e}")
            return None
    
    async def get_order_performance_metrics(self, order_id: str) -> Dict[str, Any]:
        """
        Get performance metrics for an order.
        
        Args:
            order_id: Order ID
            
        Returns:
            Dictionary with performance metrics
        """
        try:
            order = await self.get_order_status(order_id)
            if not order:
                return {}
            
            current_price = await self._get_current_price(order.instrument)
            
            metrics = {
                "order_id": order_id,
                "instrument": order.instrument,
                "order_type": order.order_type.value,
                "side": order.side.value,
                "target_price": float(order.price),
                "current_price": float(current_price),
                "distance_pips": float(order.current_distance) if order.current_distance else 0,
                "distance_percentage": float((order.price - current_price) / current_price * 100),
                "age_hours": (datetime.now(timezone.utc) - order.created_at).total_seconds() / 3600 if order.created_at else 0,
                "time_to_expiry_hours": (order.expiry_time - datetime.now(timezone.utc)).total_seconds() / 3600 if order.expiry_time else None
            }
            
            # Add stop loss and take profit distances
            if order.stop_loss:
                sl_distance = self._calculate_price_distance(order.stop_loss, current_price, order.instrument)
                metrics["stop_loss_distance_pips"] = float(sl_distance)
            
            if order.take_profit:
                tp_distance = self._calculate_price_distance(order.take_profit, current_price, order.instrument)
                metrics["take_profit_distance_pips"] = float(tp_distance)
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error getting performance metrics for {order_id}: {e}")
            return {}
    
    async def cleanup_expired_orders(self) -> int:
        """
        Clean up expired orders that weren't automatically cancelled.
        
        Returns:
            Number of orders cleaned up
        """
        cleaned_count = 0
        current_time = datetime.now(timezone.utc)
        
        for order_id in list(self.pending_orders.keys()):
            order = self.pending_orders[order_id]
            if (order.expiry_time and 
                current_time >= order.expiry_time and 
                order.status == OrderStatus.PENDING):
                
                result = await self.cancel_pending_order(order_id)
                if result.success:
                    cleaned_count += 1
        
        if cleaned_count > 0:
            self.logger.info(f"Cleaned up {cleaned_count} expired orders")
        
        return cleaned_count
    
    async def stop_monitoring(self):
        """Stop order monitoring"""
        self.is_monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None