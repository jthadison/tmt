"""
Backtesting Framework Foundation - Story 11.2

Comprehensive backtesting system with:
- Market replay with no look-ahead bias
- Signal generation replay
- Order execution simulation
- Performance metrics calculation
- Multi-parameter backtesting support
"""

from .models import (
    BacktestConfig,
    BacktestResult,
    Trade,
    EquityPoint,
    SessionMetrics,
    InstrumentMetrics,
    TradingSession,
)
from .engine import BacktestEngine
from .market_replay import MarketReplayIterator
from .signal_replay import SignalReplayEngine
from .order_simulator import OrderSimulator, SlippageModel
from .metrics_calculator import MetricsCalculator
from .session_detector import TradingSessionDetector
from .validators import LookAheadValidator

__all__ = [
    "BacktestConfig",
    "BacktestResult",
    "Trade",
    "EquityPoint",
    "SessionMetrics",
    "InstrumentMetrics",
    "TradingSession",
    "BacktestEngine",
    "MarketReplayIterator",
    "SignalReplayEngine",
    "OrderSimulator",
    "SlippageModel",
    "MetricsCalculator",
    "TradingSessionDetector",
    "LookAheadValidator",
]
