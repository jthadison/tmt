"""
OANDA API Client Interface

Defines the interface for OANDA API interactions used across the trading system.
This provides a consistent interface for all OANDA operations.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import asyncio
import logging

logger = logging.getLogger(__name__)


class OandaClientInterface(ABC):
    """Interface for OANDA API client"""
    
    @property
    @abstractmethod
    def account_id(self) -> str:
        """Get account ID"""
        pass
    
    @abstractmethod
    async def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make GET request to OANDA API"""
        pass
    
    @abstractmethod
    async def post(self, path: str, json: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make POST request to OANDA API"""
        pass
    
    @abstractmethod
    async def put(self, path: str, json: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make PUT request to OANDA API"""
        pass
    
    @abstractmethod
    async def delete(self, path: str) -> Dict[str, Any]:
        """Make DELETE request to OANDA API"""
        pass


class MockOandaClient(OandaClientInterface):
    """
    Mock OANDA client for testing and development.
    
    Provides realistic responses for testing without requiring actual OANDA API access.
    """
    
    def __init__(self, account_id: str = "test_account"):
        self._account_id = account_id
        self.call_count = 0
        
        # Track created orders
        self.created_orders = {}
        
        # Mock data for responses
        self.mock_positions = {
            'positions': [
                {
                    'instrument': 'EUR_USD',
                    'long': {
                        'units': '10000',
                        'averagePrice': '1.0500',
                        'unrealizedPL': '75.00',
                        'openTime': '2024-01-15T10:30:00.000000Z'
                    },
                    'short': {'units': '0', 'averagePrice': '0', 'unrealizedPL': '0'},
                    'financing': '1.25',
                    'commission': '0.50',
                    'marginUsed': '350.00'
                }
            ]
        }
        
        self.mock_orders = {
            'orders': [
                {
                    'id': 'order_12345',
                    'createTime': '2024-01-15T11:00:00.000000Z',
                    'state': 'PENDING',
                    'type': 'LIMIT',
                    'instrument': 'EUR_USD',
                    'units': '5000',
                    'price': '1.0450'
                }
            ]
        }
        
        self.mock_pricing = {
            'prices': [
                {
                    'instrument': 'EUR_USD',
                    'closeoutBid': '1.0575',
                    'closeoutAsk': '1.0577',
                    'time': '2024-01-15T12:00:00.000000Z'
                }
            ]
        }
    
    @property
    def account_id(self) -> str:
        return self._account_id
    
    async def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Mock GET request"""
        self.call_count += 1
        
        # Simulate network delay
        await asyncio.sleep(0.01)
        
        # Route based on path
        if 'openPositions' in path:
            return self.mock_positions
        elif 'orders' in path:
            # Return tracked orders
            orders_list = list(self.created_orders.values())
            return {'orders': orders_list}
        elif 'pricing' in path:
            return self.mock_pricing
        elif 'account' in path and 'summary' in path:
            return {
                'account': {
                    'id': self.account_id,
                    'balance': '10000.00',
                    'unrealizedPL': '75.00',
                    'marginUsed': '350.00',
                    'marginAvailable': '9650.00'
                }
            }
        else:
            logger.warning(f"Mock client: Unknown GET path {path}")
            return {}
    
    async def post(self, path: str, json: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Mock POST request (order creation)"""
        self.call_count += 1
        await asyncio.sleep(0.01)
        
        if 'orders' in path:
            order_id = f"order_{self.call_count}"
            
            # Extract order details from the request
            order_data = json.get('order', {}) if json else {}
            
            # Store the order for tracking
            self.created_orders[order_id] = {
                'id': order_id,
                'createTime': '2024-01-15T12:00:00.000000Z',
                'state': 'PENDING',
                'type': order_data.get('type', 'LIMIT'),
                'instrument': order_data.get('instrument', 'EUR_USD'),
                'units': order_data.get('units', '10000'),
                'price': order_data.get('price', '1.0550'),
                'timeInForce': order_data.get('timeInForce', 'GTC')
            }
            
            return {
                'orderCreateTransaction': {
                    'id': order_id,
                    'time': '2024-01-15T12:00:00.000000Z',
                    'type': 'ORDER_CREATE',
                    'accountID': self.account_id,
                    'batchID': f"batch_{self.call_count}",
                    'requestID': f"req_{self.call_count}"
                },
                'relatedTransactionIDs': [order_id]
            }
        elif 'positions' in path and 'close' in path:
            # Position close
            return {
                'closeTransaction': {
                    'id': f"close_{self.call_count}",
                    'time': '2024-01-15T12:00:00.000000Z',
                    'type': 'MARKET_ORDER_CLOSE',
                    'accountID': self.account_id
                }
            }
        else:
            logger.warning(f"Mock client: Unknown POST path {path}")
            return {}
    
    async def put(self, path: str, json: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Mock PUT request (order modification/cancellation)"""
        self.call_count += 1
        await asyncio.sleep(0.01)
        
        if 'cancel' in path:
            # Order cancellation
            order_id = path.split('/')[-2]  # Extract order ID from path
            
            # Remove from tracking
            if order_id in self.created_orders:
                del self.created_orders[order_id]
            
            return {
                'orderCancelTransaction': {
                    'id': f"cancel_{self.call_count}",
                    'time': '2024-01-15T12:00:00.000000Z',
                    'type': 'ORDER_CANCEL',
                    'accountID': self.account_id,
                    'orderID': order_id
                }
            }
        elif 'orders' in path:
            # Order modification
            new_order_id = f"order_{self.call_count}"
            return {
                'orderCancelTransaction': {
                    'id': f"cancel_{self.call_count}",
                    'type': 'ORDER_CANCEL'
                },
                'orderCreateTransaction': {
                    'id': new_order_id,
                    'time': '2024-01-15T12:00:00.000000Z',
                    'type': 'ORDER_CREATE',
                    'accountID': self.account_id
                }
            }
        elif 'trades' in path:
            # Trade modification (stop loss, take profit)
            return {
                'tradeModifyTransaction': {
                    'id': f"modify_{self.call_count}",
                    'time': '2024-01-15T12:00:00.000000Z',
                    'type': 'TRADE_MODIFY',
                    'accountID': self.account_id
                }
            }
        else:
            logger.warning(f"Mock client: Unknown PUT path {path}")
            return {}
    
    async def delete(self, path: str) -> Dict[str, Any]:
        """Mock DELETE request"""
        self.call_count += 1
        await asyncio.sleep(0.01)
        
        return {
            'deleteTransaction': {
                'id': f"delete_{self.call_count}",
                'time': '2024-01-15T12:00:00.000000Z',
                'type': 'DELETE',
                'accountID': self.account_id
            }
        }


# For backwards compatibility, provide the original class name
OandaClient = MockOandaClient