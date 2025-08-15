"""
OANDA Order Execution System
Story 8.3 - Market Order Execution

Handles market order execution with sub-100ms latency targets,
stop loss/take profit placement, and comprehensive order tracking.
"""
import asyncio
import logging
import time
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from dataclasses import dataclass, asdict
import aiohttp
import uuid

try:
    from .oanda_auth_handler import OandaAuthHandler, AccountContext
except ImportError:
    from oanda_auth_handler import OandaAuthHandler, AccountContext

logger = logging.getLogger(__name__)

class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"

class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled" 
    PARTIALLY_FILLED = "partially_filled"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"

@dataclass
class OrderResult:
    """Result of order execution"""
    client_order_id: str
    oanda_order_id: Optional[str]
    transaction_id: Optional[str]
    status: OrderStatus
    instrument: str
    units: int
    side: OrderSide
    requested_price: Optional[Decimal]
    fill_price: Optional[Decimal]
    slippage: Optional[Decimal]
    execution_time_ms: float
    timestamp: datetime
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    filled_units: int = 0
    remaining_units: int = 0
    rejection_reason: Optional[str] = None
    error_code: Optional[str] = None

@dataclass
class SlippageRecord:
    """Record for slippage tracking"""
    instrument: str
    timestamp: datetime
    expected_price: Decimal
    actual_price: Decimal
    slippage: Decimal
    units: int
    side: OrderSide

class OandaOrderExecutor:
    """High-performance OANDA order execution system"""
    
    def __init__(self, auth_handler: OandaAuthHandler, metrics_collector=None):
        self.auth_handler = auth_handler
        self.metrics = metrics_collector
        self.order_cache: Dict[str, OrderResult] = {}
        self.slippage_history: Dict[str, List[SlippageRecord]] = {}
        self.slippage_alert_threshold = Decimal('0.0005')  # 0.5 pips
        
        # Performance optimization
        self.session_pool = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10),
            connector=aiohttp.TCPConnector(
                limit=100,
                limit_per_host=20,
                keepalive_timeout=30,
                enable_cleanup_closed=True
            )
        )
    
    async def execute_market_order(
        self,
        user_id: str,
        account_id: str,
        instrument: str,
        units: int,
        side: OrderSide,
        stop_loss: Optional[Decimal] = None,
        take_profit: Optional[Decimal] = None,
        client_extensions: Optional[Dict] = None,
        tmt_signal_id: Optional[str] = None
    ) -> OrderResult:
        """
        Execute market order with sub-100ms target latency
        
        Args:
            user_id: User identifier
            account_id: OANDA account ID
            instrument: Trading instrument (e.g., EUR_USD)
            units: Position size in units (positive for buy, negative for sell)
            side: Order side (BUY/SELL)
            stop_loss: Optional stop loss price
            take_profit: Optional take profit price
            client_extensions: Optional client extensions
            tmt_signal_id: TMT signal ID for correlation
            
        Returns:
            OrderResult: Execution result with timing and fill details
        """
        start_time = time.perf_counter()
        
        # Generate unique client order ID
        client_order_id = self._generate_client_order_id(tmt_signal_id)
        
        logger.info(f"Executing market order {client_order_id}: {instrument} {units} units ({side.value})")
        
        try:
            # Get authenticated session
            context = await self.auth_handler.get_session_context(user_id, account_id)
            if not context or not context.session_valid:
                context = await self.auth_handler.authenticate_user(user_id, account_id, "practice")
            
            # Build order request
            order_request = self._build_market_order_request(
                instrument, units, side, stop_loss, take_profit, 
                client_order_id, client_extensions, tmt_signal_id
            )
            
            # Execute order
            response = await self._send_order_request(context, order_request)
            
            # Calculate execution time
            execution_time_ms = (time.perf_counter() - start_time) * 1000
            
            # Process response
            result = await self._process_order_response(
                response, client_order_id, instrument, units, side, 
                execution_time_ms, stop_loss, take_profit
            )
            
            # Store in cache
            self.order_cache[client_order_id] = result
            
            # Record slippage if filled
            if result.status == OrderStatus.FILLED and result.fill_price:
                await self._record_slippage(result)
            
            # Record metrics
            if self.metrics:
                await self.metrics.record_execution_time(execution_time_ms)
                await self.metrics.record_order_execution(result)
            
            logger.info(f"Order {client_order_id} executed in {execution_time_ms:.2f}ms: {result.status.value}")
            
            return result
            
        except Exception as e:
            execution_time_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Order execution failed for {client_order_id}: {e}")
            
            result = OrderResult(
                client_order_id=client_order_id,
                oanda_order_id=None,
                transaction_id=None,
                status=OrderStatus.REJECTED,
                instrument=instrument,
                units=units,
                side=side,
                requested_price=None,
                fill_price=None,
                slippage=None,
                execution_time_ms=execution_time_ms,
                timestamp=datetime.utcnow(),
                rejection_reason=str(e),
                error_code="EXECUTION_ERROR"
            )
            
            self.order_cache[client_order_id] = result
            return result
    
    def _generate_client_order_id(self, tmt_signal_id: Optional[str] = None) -> str:
        """Generate unique client order ID"""
        timestamp = int(datetime.utcnow().timestamp() * 1000)
        unique_id = str(uuid.uuid4())[:8]
        
        if tmt_signal_id:
            return f"TMT_{tmt_signal_id}_{timestamp}_{unique_id}"
        return f"TMT_{timestamp}_{unique_id}"
    
    def _build_market_order_request(
        self,
        instrument: str,
        units: int,
        side: OrderSide,
        stop_loss: Optional[Decimal],
        take_profit: Optional[Decimal],
        client_order_id: str,
        client_extensions: Optional[Dict],
        tmt_signal_id: Optional[str]
    ) -> Dict:
        """Build OANDA market order request"""
        
        # Convert units to string with proper sign
        units_str = str(abs(units) if side == OrderSide.BUY else -abs(units))
        
        order_request = {
            "order": {
                "type": "MARKET",
                "instrument": instrument,
                "units": units_str,
                "clientExtensions": {
                    "id": client_order_id,
                    "tag": client_extensions.get('tag', 'TMT') if client_extensions else 'TMT',
                    "comment": client_extensions.get('comment', f'TMT Signal: {tmt_signal_id}') if tmt_signal_id else 'TMT Market Order'
                }
            }
        }
        
        # Add stop loss if specified
        if stop_loss:
            order_request["order"]["stopLossOnFill"] = {
                "price": str(stop_loss)
            }
        
        # Add take profit if specified
        if take_profit:
            order_request["order"]["takeProfitOnFill"] = {
                "price": str(take_profit)
            }
        
        return order_request
    
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
    
    async def _process_order_response(
        self,
        response: Dict,
        client_order_id: str,
        instrument: str,
        units: int,
        side: OrderSide,
        execution_time_ms: float,
        stop_loss: Optional[Decimal],
        take_profit: Optional[Decimal]
    ) -> OrderResult:
        """Process OANDA order response"""
        
        # Extract order fill transaction
        order_fill_transaction = None
        order_transaction = None
        
        for transaction in response.get('orderFillTransaction', []) + response.get('relatedTransactionIDs', []):
            if isinstance(transaction, dict):
                if transaction.get('type') == 'ORDER_FILL':
                    order_fill_transaction = transaction
                elif transaction.get('type') == 'MARKET_ORDER':
                    order_transaction = transaction
        
        # Handle direct response structure
        if 'orderFillTransaction' in response:
            order_fill_transaction = response['orderFillTransaction']
        if 'orderCreateTransaction' in response:
            order_transaction = response['orderCreateTransaction']
        
        # Determine status and fill details
        if order_fill_transaction:
            status = OrderStatus.FILLED
            fill_price = Decimal(str(order_fill_transaction.get('price', '0')))
            filled_units = int(order_fill_transaction.get('units', '0'))
            transaction_id = order_fill_transaction.get('id')
            oanda_order_id = order_fill_transaction.get('orderID')
        elif order_transaction:
            status = OrderStatus.PENDING
            fill_price = None
            filled_units = 0
            transaction_id = order_transaction.get('id')
            oanda_order_id = order_transaction.get('id')
        else:
            status = OrderStatus.REJECTED
            fill_price = None
            filled_units = 0
            transaction_id = None
            oanda_order_id = None
        
        # Calculate slippage (will be calculated later with market price)
        slippage = None
        
        return OrderResult(
            client_order_id=client_order_id,
            oanda_order_id=oanda_order_id,
            transaction_id=transaction_id,
            status=status,
            instrument=instrument,
            units=units,
            side=side,
            requested_price=None,  # Market orders don't have requested price
            fill_price=fill_price,
            slippage=slippage,
            execution_time_ms=execution_time_ms,
            timestamp=datetime.utcnow(),
            stop_loss=stop_loss,
            take_profit=take_profit,
            filled_units=filled_units,
            remaining_units=abs(units) - abs(filled_units)
        )
    
    async def _record_slippage(self, order_result: OrderResult):
        """Record slippage for analysis"""
        if not order_result.fill_price:
            return
        
        # For market orders, we need to compare against current market price
        # This would typically require a separate price feed
        # For now, we'll record the execution for future slippage calculation
        
        slippage_record = SlippageRecord(
            instrument=order_result.instrument,
            timestamp=order_result.timestamp,
            expected_price=order_result.fill_price,  # Placeholder - would use market price
            actual_price=order_result.fill_price,
            slippage=Decimal('0'),  # Placeholder
            units=order_result.units,
            side=order_result.side
        )
        
        if order_result.instrument not in self.slippage_history:
            self.slippage_history[order_result.instrument] = []
        
        self.slippage_history[order_result.instrument].append(slippage_record)
        
        # Keep only last 1000 records per instrument
        if len(self.slippage_history[order_result.instrument]) > 1000:
            self.slippage_history[order_result.instrument] = \
                self.slippage_history[order_result.instrument][-1000:]
    
    def get_order_status(self, client_order_id: str) -> Optional[OrderResult]:
        """Get order status by client order ID"""
        return self.order_cache.get(client_order_id)
    
    def get_orders_by_tmt_signal(self, tmt_signal_id: str) -> List[OrderResult]:
        """Get all orders correlated to a TMT signal"""
        matching_orders = []
        for order_result in self.order_cache.values():
            if tmt_signal_id in order_result.client_order_id:
                matching_orders.append(order_result)
        return matching_orders
    
    def get_slippage_stats(self, instrument: str, hours: int = 24) -> Dict[str, Any]:
        """Get slippage statistics for instrument"""
        if instrument not in self.slippage_history:
            return {}
        
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        recent_records = [
            record for record in self.slippage_history[instrument]
            if record.timestamp >= cutoff
        ]
        
        if not recent_records:
            return {}
        
        slippages = [record.slippage for record in recent_records]
        
        return {
            'instrument': instrument,
            'period_hours': hours,
            'total_trades': len(recent_records),
            'average_slippage': float(sum(slippages) / len(slippages)),
            'max_slippage': float(max(slippages)),
            'min_slippage': float(min(slippages)),
            'slippage_threshold': float(self.slippage_alert_threshold)
        }
    
    def get_execution_metrics(self) -> Dict[str, Any]:
        """Get execution performance metrics"""
        if not self.order_cache:
            return {}
        
        orders = list(self.order_cache.values())
        execution_times = [order.execution_time_ms for order in orders]
        
        filled_orders = [order for order in orders if order.status == OrderStatus.FILLED]
        rejected_orders = [order for order in orders if order.status == OrderStatus.REJECTED]
        
        return {
            'total_orders': len(orders),
            'filled_orders': len(filled_orders),
            'rejected_orders': len(rejected_orders),
            'fill_rate': len(filled_orders) / len(orders) * 100 if orders else 0,
            'average_execution_time_ms': sum(execution_times) / len(execution_times) if execution_times else 0,
            'max_execution_time_ms': max(execution_times) if execution_times else 0,
            'min_execution_time_ms': min(execution_times) if execution_times else 0,
            'sub_100ms_orders': sum(1 for t in execution_times if t < 100),
            'sub_100ms_rate': sum(1 for t in execution_times if t < 100) / len(execution_times) * 100 if execution_times else 0
        }
    
    async def close(self):
        """Clean up resources"""
        if self.session_pool and not self.session_pool.closed:
            await self.session_pool.close()