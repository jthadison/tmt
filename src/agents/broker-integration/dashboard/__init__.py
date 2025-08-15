"""
Dashboard Package for Story 8.2: Account Information & Balance Tracking
Provides comprehensive real-time dashboard for OANDA account monitoring
"""

from .account_dashboard import (
    AccountDashboard,
    DashboardWidget,
    AccountSummaryWidget,
    MarginStatusWidget,
    PositionCounterWidget,
    InstrumentSpreadWidget,
    BalanceHistoryWidget,
    EquityCurveWidget,
    WidgetStatus
)
from .websocket_handler import (
    DashboardWebSocketHandler,
    WebSocketMessage
)
from .server import (
    DashboardServer,
    create_dashboard_server,
    main
)

__all__ = [
    # Core dashboard
    'AccountDashboard',
    'DashboardWidget',
    'WidgetStatus',
    
    # Widget types
    'AccountSummaryWidget',
    'MarginStatusWidget', 
    'PositionCounterWidget',
    'InstrumentSpreadWidget',
    'BalanceHistoryWidget',
    'EquityCurveWidget',
    
    # WebSocket handling
    'DashboardWebSocketHandler',
    'WebSocketMessage',
    
    # Server
    'DashboardServer',
    'create_dashboard_server',
    'main'
]

# Package metadata
__version__ = "1.0.0"
__author__ = "TMT Development Team"
__description__ = "Real-time OANDA account dashboard for Story 8.2"