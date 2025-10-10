"""
Database package for trading system persistence.

Provides SQLite database infrastructure with SQLAlchemy ORM for
persisting trades, signals, performance snapshots, and parameter history.
"""

from .connection import DatabaseEngine, get_database_engine, initialize_database
from .models import Trade, Signal, PerformanceSnapshot, ParameterHistory
from .trade_repository import TradeRepository
from .signal_repository import SignalRepository

__all__ = [
    "DatabaseEngine",
    "get_database_engine",
    "initialize_database",
    "Trade",
    "Signal",
    "PerformanceSnapshot",
    "ParameterHistory",
    "TradeRepository",
    "SignalRepository",
]
