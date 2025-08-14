"""
Data Interfaces Package

Provides abstract interfaces for data source integration across all agents.
These interfaces allow switching between mock data (for development/testing)
and real data sources (for production) without changing agent logic.
"""

from .market_data_interface import MarketDataInterface, MockMarketDataProvider
from .trade_data_interface import TradeDataInterface, MockTradeDataProvider
from .account_data_interface import AccountDataInterface, MockAccountDataProvider
from .performance_data_interface import PerformanceDataInterface, MockPerformanceDataProvider

__all__ = [
    'MarketDataInterface',
    'MockMarketDataProvider',
    'TradeDataInterface', 
    'MockTradeDataProvider',
    'AccountDataInterface',
    'MockAccountDataProvider',
    'PerformanceDataInterface',
    'MockPerformanceDataProvider'
]