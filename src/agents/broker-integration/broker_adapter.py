"""
Abstract Broker Adapter Interface
Story 8.10 - Task 1: Design abstract broker interface
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Set, AsyncIterator, Union, Callable
from decimal import Decimal
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class BrokerCapability(Enum):
    """Broker capability enumeration"""
    MARKET_ORDERS = "market_orders"
    LIMIT_ORDERS = "limit_orders"
    STOP_ORDERS = "stop_orders"
    STOP_LOSS_ORDERS = "stop_loss_orders"
    TAKE_PROFIT_ORDERS = "take_profit_orders"
    TRAILING_STOPS = "trailing_stops"
    GUARANTEED_STOPS = "guaranteed_stops"
    FRACTIONAL_UNITS = "fractional_units"
    HEDGING = "hedging"
    FIFO_ONLY = "fifo_only"
    NETTING = "netting"
    MARGIN_TRADING = "margin_trading"
    REAL_TIME_STREAMING = "real_time_streaming"
    HISTORICAL_DATA = "historical_data"
    MULTIPLE_ACCOUNTS = "multiple_accounts"
    PARTIAL_FILLS = "partial_fills"
    ORDER_MODIFICATION = "order_modification"
    POSITION_MODIFICATION = "position_modification"
    ACCOUNT_AGGREGATION = "account_aggregation"


class OrderType(Enum):
    """Unified order types"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    TRAILING_STOP = "trailing_stop"
    MARKET_IF_TOUCHED = "market_if_touched"
    LIMIT_IF_TOUCHED = "limit_if_touched"


class OrderSide(Enum):
    """Order side enumeration"""
    BUY = "buy"
    SELL = "sell"


class TimeInForce(Enum):
    """Time in force enumeration"""
    GTC = "gtc"  # Good Till Cancelled
    IOC = "ioc"  # Immediate Or Cancel
    FOK = "fok"  # Fill Or Kill
    DAY = "day"  # Day order
    GTD = "gtd"  # Good Till Date


class OrderState(Enum):
    """Order state enumeration"""
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    PARTIALLY_FILLED = "partially_filled"
    TRIGGERED = "triggered"


class PositionSide(Enum):
    """Position side enumeration"""
    LONG = "long"
    SHORT = "short"


@dataclass
class UnifiedOrder:
    """Broker-agnostic order representation"""
    order_id: str
    client_order_id: str
    instrument: str
    order_type: OrderType
    side: OrderSide
    units: Decimal
    price: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    trailing_amount: Optional[Decimal] = None
    time_in_force: TimeInForce = TimeInForce.GTC
    gtd_time: Optional[datetime] = None
    state: OrderState = OrderState.PENDING
    creation_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    fill_time: Optional[datetime] = None
    filled_units: Decimal = Decimal('0')
    remaining_units: Optional[Decimal] = None
    average_fill_price: Optional[Decimal] = None
    commission: Optional[Decimal] = None
    reason: Optional[str] = None
    broker_specific: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.remaining_units is None:
            self.remaining_units = self.units


@dataclass
class UnifiedPosition:
    """Broker-agnostic position representation"""
    position_id: str
    instrument: str
    side: PositionSide
    units: Decimal
    average_price: Decimal
    current_price: Optional[Decimal] = None
    unrealized_pl: Optional[Decimal] = None
    realized_pl: Optional[Decimal] = None
    margin_used: Optional[Decimal] = None
    creation_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_update: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    stop_loss_order_id: Optional[str] = None
    take_profit_order_id: Optional[str] = None
    broker_specific: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UnifiedAccountSummary:
    """Broker-agnostic account summary"""
    account_id: str
    account_name: str
    currency: str
    balance: Decimal
    available_margin: Decimal
    used_margin: Decimal
    margin_call_level: Optional[Decimal] = None
    unrealized_pl: Optional[Decimal] = None
    realized_pl: Optional[Decimal] = None
    nav: Optional[Decimal] = None  # Net Asset Value
    equity: Optional[Decimal] = None
    margin_rate: Optional[Decimal] = None
    last_update: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    position_count: int = 0
    open_order_count: int = 0
    broker_specific: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PriceTick:
    """Real-time price tick"""
    instrument: str
    bid: Decimal
    ask: Decimal
    timestamp: datetime
    spread: Optional[Decimal] = None
    volume: Optional[Decimal] = None
    broker_specific: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.spread is None:
            self.spread = self.ask - self.bid


@dataclass
class OrderResult:
    """Result of order placement"""
    success: bool
    order_id: Optional[str] = None
    client_order_id: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    order_state: Optional[OrderState] = None
    fill_price: Optional[Decimal] = None
    filled_units: Optional[Decimal] = None
    commission: Optional[Decimal] = None
    transaction_id: Optional[str] = None
    broker_specific: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BrokerInfo:
    """Broker information and metadata"""
    name: str
    display_name: str
    version: str
    capabilities: Set[BrokerCapability]
    supported_instruments: List[str]
    supported_order_types: List[OrderType]
    supported_time_in_force: List[TimeInForce]
    minimum_trade_size: Dict[str, Decimal]  # instrument -> min size
    maximum_trade_size: Dict[str, Decimal]  # instrument -> max size
    commission_structure: Dict[str, Any]
    margin_requirements: Dict[str, Decimal]
    trading_hours: Dict[str, Dict[str, str]]  # instrument -> {open, close}
    api_rate_limits: Dict[str, int]  # endpoint -> requests per second
    metadata: Dict[str, Any] = field(default_factory=dict)


class BrokerAdapter(ABC):
    """Abstract base class for all broker integrations"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.account_id = config.get('account_id')
        self.is_authenticated = False
        self.connection_status = 'disconnected'
        self.last_heartbeat = None
        self._capabilities: Optional[Set[BrokerCapability]] = None
        
        # Transaction recording hooks
        self._transaction_recorders: List[Callable] = []
        
    @property
    @abstractmethod
    def broker_name(self) -> str:
        """Return the broker name"""
        pass
        
    @property
    @abstractmethod
    def broker_display_name(self) -> str:
        """Return the broker display name"""
        pass
        
    @property
    @abstractmethod
    def api_version(self) -> str:
        """Return the API version"""
        pass
        
    @property
    @abstractmethod
    def capabilities(self) -> Set[BrokerCapability]:
        """Return set of supported capabilities"""
        pass
        
    @property
    @abstractmethod
    def supported_instruments(self) -> List[str]:
        """Return list of supported trading instruments"""
        pass
        
    @property
    @abstractmethod
    def supported_order_types(self) -> List[OrderType]:
        """Return list of supported order types"""
        pass
        
    @abstractmethod
    async def authenticate(self, credentials: Dict[str, str]) -> bool:
        """
        Authenticate with broker
        
        Args:
            credentials: Dictionary containing authentication credentials
            
        Returns:
            True if authentication successful, False otherwise
        """
        pass
        
    @abstractmethod
    async def disconnect(self) -> bool:
        """
        Disconnect from broker
        
        Returns:
            True if disconnection successful, False otherwise
        """
        pass
        
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check
        
        Returns:
            Dictionary containing health status information
        """
        pass
        
    @abstractmethod
    async def get_broker_info(self) -> BrokerInfo:
        """
        Get comprehensive broker information
        
        Returns:
            BrokerInfo object with metadata and capabilities
        """
        pass
        
    # Account Operations
    @abstractmethod
    async def get_account_summary(self, account_id: Optional[str] = None) -> UnifiedAccountSummary:
        """
        Get account information and summary
        
        Args:
            account_id: Optional account ID, uses default if not provided
            
        Returns:
            UnifiedAccountSummary object
        """
        pass
        
    @abstractmethod
    async def get_accounts(self) -> List[UnifiedAccountSummary]:
        """
        Get all accessible accounts
        
        Returns:
            List of UnifiedAccountSummary objects
        """
        pass
        
    # Order Operations
    @abstractmethod
    async def place_order(self, order: UnifiedOrder) -> OrderResult:
        """
        Place order with broker
        
        Args:
            order: UnifiedOrder object to place
            
        Returns:
            OrderResult with placement status
        """
        pass
        
    @abstractmethod
    async def modify_order(self, order_id: str, modifications: Dict[str, Any]) -> OrderResult:
        """
        Modify existing order
        
        Args:
            order_id: ID of order to modify
            modifications: Dictionary of field modifications
            
        Returns:
            OrderResult with modification status
        """
        pass
        
    @abstractmethod
    async def cancel_order(self, order_id: str, reason: Optional[str] = None) -> OrderResult:
        """
        Cancel existing order
        
        Args:
            order_id: ID of order to cancel
            reason: Optional cancellation reason
            
        Returns:
            OrderResult with cancellation status
        """
        pass
        
    @abstractmethod
    async def get_order(self, order_id: str) -> Optional[UnifiedOrder]:
        """
        Get order by ID
        
        Args:
            order_id: Order ID to retrieve
            
        Returns:
            UnifiedOrder object or None if not found
        """
        pass
        
    @abstractmethod
    async def get_orders(self, 
                        account_id: Optional[str] = None,
                        instrument: Optional[str] = None,
                        state: Optional[OrderState] = None,
                        count: Optional[int] = None) -> List[UnifiedOrder]:
        """
        Get orders with optional filtering
        
        Args:
            account_id: Optional account filter
            instrument: Optional instrument filter
            state: Optional order state filter
            count: Optional maximum number of orders
            
        Returns:
            List of UnifiedOrder objects
        """
        pass
        
    # Position Operations
    @abstractmethod
    async def get_position(self, instrument: str, account_id: Optional[str] = None) -> Optional[UnifiedPosition]:
        """
        Get position for specific instrument
        
        Args:
            instrument: Trading instrument
            account_id: Optional account ID
            
        Returns:
            UnifiedPosition object or None if no position
        """
        pass
        
    @abstractmethod
    async def get_positions(self, account_id: Optional[str] = None) -> List[UnifiedPosition]:
        """
        Get all open positions
        
        Args:
            account_id: Optional account ID filter
            
        Returns:
            List of UnifiedPosition objects
        """
        pass
        
    @abstractmethod
    async def close_position(self, 
                           instrument: str,
                           units: Optional[Decimal] = None,
                           account_id: Optional[str] = None) -> OrderResult:
        """
        Close position (fully or partially)
        
        Args:
            instrument: Trading instrument
            units: Optional units to close (None = close all)
            account_id: Optional account ID
            
        Returns:
            OrderResult with close status
        """
        pass
        
    # Market Data Operations
    @abstractmethod
    async def get_current_price(self, instrument: str) -> Optional[PriceTick]:
        """
        Get current price for instrument
        
        Args:
            instrument: Trading instrument
            
        Returns:
            PriceTick object or None if not available
            
        Raises:
            ValueError: If instrument is None or empty
        """
        if not instrument:
            raise ValueError("Instrument is required")
        pass
        
    @abstractmethod
    async def get_current_prices(self, instruments: List[str]) -> Dict[str, PriceTick]:
        """
        Get current prices for multiple instruments
        
        Args:
            instruments: List of trading instruments
            
        Returns:
            Dictionary mapping instrument to PriceTick
            
        Raises:
            ValueError: If instruments is None or empty
        """
        if not instruments:
            raise ValueError("Instruments list is required and cannot be empty")
        pass
        
    @abstractmethod
    async def stream_prices(self, instruments: List[str]) -> AsyncIterator[PriceTick]:
        """
        Stream real-time prices
        
        Args:
            instruments: List of instruments to stream
            
        Yields:
            PriceTick objects as they arrive
        """
        pass
        
    @abstractmethod
    async def get_historical_data(self,
                                instrument: str,
                                granularity: str,
                                count: Optional[int] = None,
                                from_time: Optional[datetime] = None,
                                to_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Get historical price data
        
        Args:
            instrument: Trading instrument
            granularity: Time granularity (e.g., 'M1', 'H1', 'D')
            count: Number of candles to retrieve
            from_time: Start time for data
            to_time: End time for data
            
        Returns:
            List of historical candle data
        """
        pass
        
    # Transaction Operations
    @abstractmethod
    async def get_transactions(self,
                             account_id: Optional[str] = None,
                             from_time: Optional[datetime] = None,
                             to_time: Optional[datetime] = None,
                             transaction_type: Optional[str] = None,
                             count: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get transaction history
        
        Args:
            account_id: Optional account ID filter
            from_time: Optional start time filter
            to_time: Optional end time filter
            transaction_type: Optional transaction type filter
            count: Optional maximum number of transactions
            
        Returns:
            List of transaction dictionaries
        """
        pass
        
    # Error Handling
    @abstractmethod
    def map_error(self, broker_error: Exception) -> 'StandardBrokerError':
        """
        Map broker-specific error to standard error
        
        Args:
            broker_error: Broker-specific exception
            
        Returns:
            StandardBrokerError with unified error code
        """
        pass
        
    # Utility Methods
    def generate_client_order_id(self) -> str:
        """Generate unique client order ID"""
        return f"{self.broker_name}_{uuid.uuid4().hex[:8]}"
        
    def is_capability_supported(self, capability: BrokerCapability) -> bool:
        """Check if broker supports specific capability"""
        return capability in self.capabilities
        
    def validate_order(self, order: UnifiedOrder) -> List[str]:
        """
        Validate order against broker capabilities
        
        Args:
            order: Order to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Check order type support
        if order.order_type not in self.supported_order_types:
            errors.append(f"Order type {order.order_type.value} not supported")
            
        # Check instrument support
        if order.instrument not in self.supported_instruments:
            errors.append(f"Instrument {order.instrument} not supported")
            
        # Check units
        if order.units <= 0:
            errors.append("Order units must be positive")
            
        # Check price for limit orders
        if order.order_type == OrderType.LIMIT and order.price is None:
            errors.append("Limit orders require price")
            
        # Check stop price for stop orders
        if order.order_type == OrderType.STOP and order.price is None:
            errors.append("Stop orders require price")
            
        return errors
        
    def add_transaction_recorder(self, recorder: Callable):
        """
        Add a transaction recorder callback
        
        Args:
            recorder: Callable that accepts transaction data
        """
        self._transaction_recorders.append(recorder)
        
    def remove_transaction_recorder(self, recorder: Callable):
        """
        Remove a transaction recorder callback
        
        Args:
            recorder: Callable to remove
        """
        if recorder in self._transaction_recorders:
            self._transaction_recorders.remove(recorder)
            
    async def _record_transaction(self, transaction_data: Dict[str, Any]):
        """
        Record transaction to all registered recorders
        
        Args:
            transaction_data: Transaction data to record
        """
        for recorder in self._transaction_recorders:
            try:
                if asyncio.iscoroutinefunction(recorder):
                    await recorder(transaction_data)
                else:
                    recorder(transaction_data)
            except Exception as e:
                logger.error(f"Error recording transaction with {recorder}: {e}")
                
    async def _record_order_transaction(self, order: UnifiedOrder, result: OrderResult, transaction_type: str = "ORDER_PLACE"):
        """
        Record order-related transaction
        
        Args:
            order: The order that was placed/modified/cancelled
            result: The result of the operation
            transaction_type: Type of transaction (ORDER_PLACE, ORDER_MODIFY, ORDER_CANCEL)
        """
        transaction_data = {
            'transaction_id': result.order_id or order.order_id,
            'transaction_type': transaction_type,
            'broker_name': self.broker_name,
            'account_id': self.account_id,
            'instrument': order.instrument,
            'order_type': order.order_type.value,
            'side': order.side.value,
            'units': float(order.units),
            'price': float(order.price) if order.price else None,
            'stop_loss': float(order.stop_loss) if order.stop_loss else None,
            'take_profit': float(order.take_profit) if order.take_profit else None,
            'time_in_force': order.time_in_force.value,
            'success': result.success,
            'error_message': result.error_message if not result.success else None,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'client_order_id': order.client_order_id,
            'fill_price': float(result.fill_price) if result.fill_price else None,
            'commission': float(result.commission) if result.commission else None
        }
        
        await self._record_transaction(transaction_data)
        
    async def get_trading_status(self, instrument: str) -> Dict[str, Any]:
        """
        Get trading status for instrument
        
        Args:
            instrument: Trading instrument
            
        Returns:
            Dictionary with trading status information
        """
        # Default implementation - brokers can override
        return {
            'instrument': instrument,
            'tradeable': instrument in self.supported_instruments,
            'market_open': True,  # Default assumption
            'halted': False
        }
        
    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.broker_name})"
        
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(broker_name='{self.broker_name}', account_id='{self.account_id}')"