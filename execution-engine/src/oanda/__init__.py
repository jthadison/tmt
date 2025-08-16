"""
OANDA Integration Package

Provides comprehensive OANDA broker integration for the trading system.
"""

from .client import OandaClientInterface, MockOandaClient, OandaClient
from .stream_manager import StreamManagerInterface, MockStreamManager, OandaStreamManager
from .pending_order_manager import (
    OandaPendingOrderManager,
    OrderType,
    OrderSide,
    TimeInForce,
    OrderStatus,
    OrderInfo,
    OrderResult
)
from .order_expiry_manager import (
    OrderExpiryManager,
    ExpiryNotification,
    NotificationSeverity
)

__all__ = [
    # Core interfaces
    'OandaClientInterface',
    'StreamManagerInterface',
    
    # Mock implementations
    'MockOandaClient',
    'MockStreamManager',
    
    # Backwards compatibility
    'OandaClient',
    'OandaStreamManager',
    
    # Order management
    'OandaPendingOrderManager',
    'OrderExpiryManager',
    
    # Data structures
    'OrderType',
    'OrderSide',
    'TimeInForce',
    'OrderStatus',
    'OrderInfo',
    'OrderResult',
    'ExpiryNotification',
    'NotificationSeverity',
]