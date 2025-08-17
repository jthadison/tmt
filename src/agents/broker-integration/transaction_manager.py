"""
OANDA Transaction Manager
Story 8.8 - Task 1: Build transaction data fetcher
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from dataclasses import dataclass, asdict
from enum import Enum
import aiohttp
import json

try:
    from .oanda_auth_handler import OandaAuthHandler, AccountContext
    from .connection_pool import OandaConnectionPool
except ImportError:
    try:
        from oanda_auth_handler import OandaAuthHandler, AccountContext
        from connection_pool import OandaConnectionPool
    except ImportError:
        # Use mock implementations for testing
        from mock_oanda_auth_handler import OandaAuthHandler, AccountContext
        from mock_connection_pool import OandaConnectionPool

logger = logging.getLogger(__name__)


class TransactionType(Enum):
    """OANDA transaction types"""
    ORDER_FILL = "ORDER_FILL"
    TRADE_CLOSE = "TRADE_CLOSE"
    DAILY_FINANCING = "DAILY_FINANCING"
    STOP_LOSS_ORDER = "STOP_LOSS_ORDER"
    TAKE_PROFIT_ORDER = "TAKE_PROFIT_ORDER"
    CLIENT_CONFIGURE = "CLIENT_CONFIGURE"
    MARGIN_CALL = "MARGIN_CALL"
    TRANSFER_FUNDS = "TRANSFER_FUNDS"
    LIMIT_ORDER = "LIMIT_ORDER"
    STOP_ORDER = "STOP_ORDER"


@dataclass
class TransactionRecord:
    """Represents a single transaction from OANDA"""
    transaction_id: str
    transaction_type: str
    instrument: Optional[str]
    units: Decimal
    price: Decimal
    pl: Decimal
    commission: Decimal
    financing: Decimal
    timestamp: datetime
    account_balance: Decimal
    reason: str
    order_id: Optional[str] = None
    trade_id: Optional[str] = None
    time_in_force: Optional[str] = None
    position_fill: Optional[str] = None
    request_id: Optional[str] = None
    correlation_id: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        result = asdict(self)
        # Convert Decimal to string for JSON serialization
        for key, value in result.items():
            if isinstance(value, Decimal):
                result[key] = str(value)
            elif isinstance(value, datetime):
                result[key] = value.isoformat()
        return result


class OandaTransactionManager:
    """Manages OANDA transaction history and audit trail"""
    
    def __init__(self, auth_handler: OandaAuthHandler, connection_pool: OandaConnectionPool):
        self.auth_handler = auth_handler
        self.connection_pool = connection_pool
        self.retention_years = 7
        self.max_transactions_per_request = 1000
        self.transaction_cache: Dict[str, List[TransactionRecord]] = {}
        self.cache_ttl = timedelta(minutes=15)
        self.last_cache_update: Dict[str, datetime] = {}
        
    async def get_transaction_history(self, 
                                     account_id: str,
                                     start_date: datetime, 
                                     end_date: datetime,
                                     transaction_types: Optional[List[TransactionType]] = None,
                                     instrument: Optional[str] = None,
                                     page_token: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch transaction history with filtering and pagination
        
        Args:
            account_id: OANDA account ID
            start_date: Start of date range
            end_date: End of date range
            transaction_types: Optional list of transaction types to filter
            instrument: Optional instrument to filter by
            page_token: Optional pagination token
            
        Returns:
            Dict containing transactions and pagination info
        """
        try:
            # Get account context
            context = await self._get_account_context(account_id)
            
            # Build query parameters
            params = {
                'from': start_date.isoformat() + 'Z',
                'to': end_date.isoformat() + 'Z',
                'pageSize': self.max_transactions_per_request
            }
            
            if transaction_types:
                params['type'] = ','.join([t.value for t in transaction_types])
                
            if page_token:
                params['from'] = page_token
                
            # Make API request
            async with self.connection_pool.get_session() as session:
                url = f"{context.base_url}/v3/accounts/{account_id}/transactions"
                headers = {
                    'Authorization': f'Bearer {context.api_key}',
                    'Accept-Datetime-Format': 'RFC3339'
                }
                
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Failed to fetch transactions: {response.status} - {error_text}")
                        raise Exception(f"API Error: {response.status}")
                        
                    data = await response.json()
                    
            # Parse transactions
            transactions = []
            for tx_data in data.get('transactions', []):
                transaction = await self._parse_transaction(tx_data)
                
                # Apply additional filtering
                if instrument and transaction.instrument != instrument:
                    continue
                    
                transactions.append(transaction)
                
            # Store in cache
            cache_key = f"{account_id}:{start_date.isoformat()}:{end_date.isoformat()}"
            self.transaction_cache[cache_key] = transactions
            self.last_cache_update[cache_key] = datetime.now(timezone.utc)
            
            return {
                'transactions': transactions,
                'count': len(transactions),
                'lastTransactionID': data.get('lastTransactionID'),
                'pageToken': data.get('pages', [{}])[0].get('from') if data.get('pages') else None,
                'hasMore': len(data.get('pages', [])) > 0
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch transaction history: {e}")
            raise
            
    async def _parse_transaction(self, tx_data: Dict) -> TransactionRecord:
        """Parse OANDA transaction data into TransactionRecord"""
        return TransactionRecord(
            transaction_id=tx_data.get('id', ''),
            transaction_type=tx_data.get('type', ''),
            instrument=tx_data.get('instrument'),
            units=Decimal(str(tx_data.get('units', '0'))),
            price=Decimal(str(tx_data.get('price', '0'))),
            pl=Decimal(str(tx_data.get('pl', '0'))),
            commission=Decimal(str(tx_data.get('commission', '0'))),
            financing=Decimal(str(tx_data.get('financing', '0'))),
            timestamp=datetime.fromisoformat(tx_data.get('time', '').replace('Z', '+00:00')),
            account_balance=Decimal(str(tx_data.get('accountBalance', '0'))),
            reason=tx_data.get('reason', ''),
            order_id=tx_data.get('orderID'),
            trade_id=tx_data.get('tradeID'),
            time_in_force=tx_data.get('timeInForce'),
            position_fill=tx_data.get('positionFill'),
            request_id=tx_data.get('requestID')
        )
        
    async def get_transaction_by_id(self, account_id: str, transaction_id: str) -> Optional[TransactionRecord]:
        """Get a specific transaction by ID"""
        try:
            context = await self._get_account_context(account_id)
            
            async with self.connection_pool.get_session() as session:
                url = f"{context.base_url}/v3/accounts/{account_id}/transactions/{transaction_id}"
                headers = {
                    'Authorization': f'Bearer {context.api_key}',
                    'Accept-Datetime-Format': 'RFC3339'
                }
                
                async with session.get(url, headers=headers) as response:
                    if response.status == 404:
                        return None
                    elif response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Failed to fetch transaction {transaction_id}: {error_text}")
                        raise Exception(f"API Error: {response.status}")
                        
                    data = await response.json()
                    
            return await self._parse_transaction(data.get('transaction', {}))
            
        except Exception as e:
            logger.error(f"Failed to fetch transaction {transaction_id}: {e}")
            raise
            
    async def get_transactions_since_id(self, account_id: str, since_id: str) -> List[TransactionRecord]:
        """Get all transactions since a specific transaction ID"""
        try:
            context = await self._get_account_context(account_id)
            
            async with self.connection_pool.get_session() as session:
                url = f"{context.base_url}/v3/accounts/{account_id}/transactions/sinceid"
                headers = {
                    'Authorization': f'Bearer {context.api_key}',
                    'Accept-Datetime-Format': 'RFC3339'
                }
                params = {'id': since_id}
                
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Failed to fetch transactions since {since_id}: {error_text}")
                        raise Exception(f"API Error: {response.status}")
                        
                    data = await response.json()
                    
            transactions = []
            for tx_data in data.get('transactions', []):
                transaction = await self._parse_transaction(tx_data)
                transactions.append(transaction)
                
            return transactions
            
        except Exception as e:
            logger.error(f"Failed to fetch transactions since {since_id}: {e}")
            raise
            
    async def _get_account_context(self, account_id: str) -> AccountContext:
        """Get authenticated account context"""
        context = self.auth_handler.active_sessions.get(account_id)
        if not context:
            raise Exception(f"No active session for account {account_id}")
        return context
        
    def clear_cache(self, account_id: Optional[str] = None):
        """Clear transaction cache"""
        if account_id:
            keys_to_remove = [k for k in self.transaction_cache.keys() if k.startswith(f"{account_id}:")]
            for key in keys_to_remove:
                del self.transaction_cache[key]
                if key in self.last_cache_update:
                    del self.last_cache_update[key]
        else:
            self.transaction_cache.clear()
            self.last_cache_update.clear()