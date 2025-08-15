"""
OANDA Account Manager
Story 8.2 - Task 1: Build OANDA account data fetcher
"""
import asyncio
import logging
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
from decimal import Decimal
from dataclasses import dataclass, asdict
from enum import Enum
import aiohttp
import json

logger = logging.getLogger(__name__)

class AccountCurrency(Enum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    CAD = "CAD"
    AUD = "AUD"
    CHF = "CHF"
    NZD = "NZD"

@dataclass
class AccountSummary:
    """Complete account summary data"""
    account_id: str
    currency: AccountCurrency
    balance: Decimal
    unrealized_pl: Decimal
    realized_pl: Decimal
    margin_used: Decimal
    margin_available: Decimal
    margin_closeout_percent: Decimal
    margin_call_percent: Decimal
    open_position_count: int
    pending_order_count: int
    leverage: int
    financing: Decimal
    commission: Decimal
    dividend_adjustment: Decimal
    account_equity: Decimal  # balance + unrealized_pl
    nav: Decimal  # Net Asset Value
    margin_rate: Decimal
    position_value: Decimal
    last_transaction_id: str
    created_time: datetime
    
    def calculate_equity(self) -> Decimal:
        """Calculate account equity"""
        return self.balance + self.unrealized_pl
    
    def calculate_free_margin(self) -> Decimal:
        """Calculate free margin available for trading"""
        return self.margin_available
    
    def calculate_margin_level(self) -> Decimal:
        """Calculate margin level percentage"""
        if self.margin_used == 0:
            return Decimal('0')
        return (self.account_equity / self.margin_used) * 100
    
    def is_margin_call(self) -> bool:
        """Check if account is in margin call"""
        return self.calculate_margin_level() <= self.margin_call_percent
    
    def is_margin_closeout(self) -> bool:
        """Check if account is at margin closeout level"""
        return self.calculate_margin_level() <= self.margin_closeout_percent

@dataclass
class PositionSummary:
    """Summary of an open position"""
    instrument: str
    units: Decimal
    side: str  # 'buy' or 'sell'
    average_price: Decimal
    current_price: Decimal
    unrealized_pl: Decimal
    realized_pl: Decimal
    margin_used: Decimal
    financing: Decimal
    dividend_adjustment: Decimal
    trade_ids: List[str]
    
    def calculate_pips(self) -> Decimal:
        """Calculate P&L in pips"""
        pip_value = Decimal('0.0001') if 'JPY' not in self.instrument else Decimal('0.01')
        price_diff = self.current_price - self.average_price
        if self.side == 'sell':
            price_diff = -price_diff
        return price_diff / pip_value

@dataclass
class OrderSummary:
    """Summary of a pending order"""
    order_id: str
    instrument: str
    units: Decimal
    type: str  # 'LIMIT', 'STOP', 'MARKET_IF_TOUCHED'
    side: str  # 'buy' or 'sell'
    price: Decimal
    time_in_force: str
    expire_time: Optional[datetime]
    trigger_condition: str
    take_profit_price: Optional[Decimal]
    stop_loss_price: Optional[Decimal]

class AccountDataCache:
    """Cache for account data with TTL"""
    
    def __init__(self, ttl_seconds: int = 5):
        self.ttl = timedelta(seconds=ttl_seconds)
        self.cache: Dict[str, Any] = {}
        self.timestamps: Dict[str, datetime] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached data if not expired"""
        if key not in self.cache:
            return None
        
        if datetime.utcnow() - self.timestamps[key] > self.ttl:
            del self.cache[key]
            del self.timestamps[key]
            return None
        
        return self.cache[key]
    
    def set(self, key: str, value: Any):
        """Set cache data with current timestamp"""
        self.cache[key] = value
        self.timestamps[key] = datetime.utcnow()
    
    def clear(self):
        """Clear all cached data"""
        self.cache.clear()
        self.timestamps.clear()

class OandaAccountManager:
    """Manages OANDA account data fetching and caching"""
    
    def __init__(self, api_key: str, account_id: str, base_url: str):
        self.api_key = api_key
        self.account_id = account_id
        self.base_url = base_url
        self.cache = AccountDataCache(ttl_seconds=5)
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Headers for OANDA API
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'Accept-Datetime-Format': 'RFC3339'
        }
        
        # Metrics tracking
        self.metrics = {
            'api_calls': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'errors': 0,
            'last_update': None
        }
    
    async def initialize(self):
        """Initialize the account manager"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(
                headers=self.headers,
                timeout=timeout
            )
        logger.info(f"Account manager initialized for account: {self.account_id}")
    
    async def close(self):
        """Close the account manager"""
        if self.session and not self.session.closed:
            await self.session.close()
        self.cache.clear()
        logger.info("Account manager closed")
    
    async def get_account_summary(self, use_cache: bool = True) -> AccountSummary:
        """
        Fetch comprehensive account summary
        
        Args:
            use_cache: Whether to use cached data if available
            
        Returns:
            AccountSummary with all account metrics
        """
        cache_key = f"account_summary_{self.account_id}"
        
        if use_cache:
            cached = self.cache.get(cache_key)
            if cached:
                self.metrics['cache_hits'] += 1
                return cached
        
        self.metrics['cache_misses'] += 1
        self.metrics['api_calls'] += 1
        
        try:
            url = f"{self.base_url}/v3/accounts/{self.account_id}/summary"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"API error {response.status}: {error_text}")
                
                data = await response.json()
                account_data = data['account']
                
                # Parse account summary
                summary = AccountSummary(
                    account_id=account_data['id'],
                    currency=AccountCurrency(account_data['currency']),
                    balance=Decimal(account_data['balance']),
                    unrealized_pl=Decimal(account_data.get('unrealizedPL', '0')),
                    realized_pl=Decimal(account_data.get('pl', '0')),
                    margin_used=Decimal(account_data.get('marginUsed', '0')),
                    margin_available=Decimal(account_data.get('marginAvailable', '0')),
                    margin_closeout_percent=Decimal(account_data.get('marginCloseoutPercent', '50')),
                    margin_call_percent=Decimal(account_data.get('marginCallPercent', '100')),
                    open_position_count=int(account_data.get('openPositionCount', 0)),
                    pending_order_count=int(account_data.get('pendingOrderCount', 0)),
                    leverage=int(account_data.get('marginRate', '1').split(':')[0]) if ':' in str(account_data.get('marginRate', '1')) else int(1/Decimal(account_data.get('marginRate', '1'))),
                    financing=Decimal(account_data.get('financing', '0')),
                    commission=Decimal(account_data.get('commission', '0')),
                    dividend_adjustment=Decimal(account_data.get('dividendAdjustment', '0')),
                    account_equity=Decimal(account_data['balance']) + Decimal(account_data.get('unrealizedPL', '0')),
                    nav=Decimal(account_data.get('NAV', account_data['balance'])),
                    margin_rate=Decimal(account_data.get('marginRate', '0.02')),
                    position_value=Decimal(account_data.get('positionValue', '0')),
                    last_transaction_id=account_data.get('lastTransactionID', ''),
                    created_time=datetime.fromisoformat(account_data['createdTime'].replace('Z', '+00:00'))
                )
                
                # Cache the result
                self.cache.set(cache_key, summary)
                self.metrics['last_update'] = datetime.utcnow()
                
                return summary
                
        except Exception as e:
            self.metrics['errors'] += 1
            logger.error(f"Failed to fetch account summary: {e}")
            raise
    
    async def get_open_positions(self) -> List[PositionSummary]:
        """
        Fetch all open positions
        
        Returns:
            List of PositionSummary objects
        """
        cache_key = f"positions_{self.account_id}"
        cached = self.cache.get(cache_key)
        if cached:
            self.metrics['cache_hits'] += 1
            return cached
        
        self.metrics['cache_misses'] += 1
        self.metrics['api_calls'] += 1
        
        try:
            url = f"{self.base_url}/v3/accounts/{self.account_id}/positions"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"API error {response.status}: {error_text}")
                
                data = await response.json()
                positions = []
                
                for pos_data in data.get('positions', []):
                    # Handle both long and short positions
                    if pos_data.get('long', {}).get('units', '0') != '0':
                        side_data = pos_data['long']
                        side = 'buy'
                    elif pos_data.get('short', {}).get('units', '0') != '0':
                        side_data = pos_data['short']
                        side = 'sell'
                    else:
                        continue
                    
                    position = PositionSummary(
                        instrument=pos_data['instrument'],
                        units=abs(Decimal(side_data['units'])),
                        side=side,
                        average_price=Decimal(side_data.get('averagePrice', '0')),
                        current_price=Decimal(side_data.get('averagePrice', '0')),  # Will be updated with current price
                        unrealized_pl=Decimal(side_data.get('unrealizedPL', '0')),
                        realized_pl=Decimal(side_data.get('pl', '0')),
                        margin_used=Decimal(side_data.get('marginUsed', '0')),
                        financing=Decimal(side_data.get('financing', '0')),
                        dividend_adjustment=Decimal(side_data.get('dividendAdjustment', '0')),
                        trade_ids=side_data.get('tradeIDs', [])
                    )
                    positions.append(position)
                
                # Cache the result
                self.cache.set(cache_key, positions)
                
                return positions
                
        except Exception as e:
            self.metrics['errors'] += 1
            logger.error(f"Failed to fetch open positions: {e}")
            raise
    
    async def get_pending_orders(self) -> List[OrderSummary]:
        """
        Fetch all pending orders
        
        Returns:
            List of OrderSummary objects
        """
        cache_key = f"orders_{self.account_id}"
        cached = self.cache.get(cache_key)
        if cached:
            self.metrics['cache_hits'] += 1
            return cached
        
        self.metrics['cache_misses'] += 1
        self.metrics['api_calls'] += 1
        
        try:
            url = f"{self.base_url}/v3/accounts/{self.account_id}/pendingOrders"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"API error {response.status}: {error_text}")
                
                data = await response.json()
                orders = []
                
                for order_data in data.get('orders', []):
                    order = OrderSummary(
                        order_id=order_data['id'],
                        instrument=order_data['instrument'],
                        units=abs(Decimal(order_data['units'])),
                        type=order_data['type'],
                        side='buy' if Decimal(order_data['units']) > 0 else 'sell',
                        price=Decimal(order_data.get('price', '0')),
                        time_in_force=order_data.get('timeInForce', 'GTC'),
                        expire_time=datetime.fromisoformat(order_data['gtdTime'].replace('Z', '+00:00')) if 'gtdTime' in order_data else None,
                        trigger_condition=order_data.get('triggerCondition', 'DEFAULT'),
                        take_profit_price=Decimal(order_data['takeProfitOnFill']['price']) if 'takeProfitOnFill' in order_data else None,
                        stop_loss_price=Decimal(order_data['stopLossOnFill']['price']) if 'stopLossOnFill' in order_data else None
                    )
                    orders.append(order)
                
                # Cache the result
                self.cache.set(cache_key, orders)
                
                return orders
                
        except Exception as e:
            self.metrics['errors'] += 1
            logger.error(f"Failed to fetch pending orders: {e}")
            raise
    
    async def calculate_total_equity(self) -> Decimal:
        """
        Calculate total account equity (balance + unrealized P&L)
        
        Returns:
            Total equity as Decimal
        """
        summary = await self.get_account_summary()
        return summary.calculate_equity()
    
    async def get_margin_status(self) -> Dict[str, Any]:
        """
        Get detailed margin status
        
        Returns:
            Dict with margin metrics
        """
        summary = await self.get_account_summary()
        
        return {
            'margin_used': float(summary.margin_used),
            'margin_available': float(summary.margin_available),
            'margin_level': float(summary.calculate_margin_level()),
            'margin_call': summary.is_margin_call(),
            'margin_closeout': summary.is_margin_closeout(),
            'margin_call_percent': float(summary.margin_call_percent),
            'margin_closeout_percent': float(summary.margin_closeout_percent),
            'free_margin': float(summary.calculate_free_margin()),
            'leverage': summary.leverage
        }
    
    async def get_account_changes(self, since_transaction_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get account changes since a specific transaction
        
        Args:
            since_transaction_id: Transaction ID to get changes since
            
        Returns:
            Dict with account changes
        """
        try:
            url = f"{self.base_url}/v3/accounts/{self.account_id}/changes"
            
            params = {}
            if since_transaction_id:
                params['sinceTransactionID'] = since_transaction_id
            
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"API error {response.status}: {error_text}")
                
                data = await response.json()
                return data.get('changes', {})
                
        except Exception as e:
            logger.error(f"Failed to fetch account changes: {e}")
            raise
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get account manager metrics"""
        return self.metrics.copy()