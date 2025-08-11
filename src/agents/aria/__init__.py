"""
Adaptive Risk Intelligence Agent (ARIA)
======================================

The ARIA agent is responsible for intelligent position sizing and risk management
across multiple trading accounts and prop firms. It implements dynamic position
sizing based on volatility, drawdown, correlation, and prop firm limits while
maintaining anti-detection variance.

Core Components:
- Position Sizing Calculator: Core engine for calculating optimal position sizes
- Volatility Adjuster: ATR-based size adjustments for market volatility
- Drawdown Adjuster: Progressive size reduction based on account drawdown
- Correlation Adjuster: Portfolio heat and correlation-based size management
- Prop Firm Limits: Enforcement of prop firm specific limitations
- Variance Engine: Anti-detection size variance generation
"""

from .position_sizing.calculator import PositionSizeCalculator
from .position_sizing.models import (
    PositionSizeRequest,
    PositionSizeResponse,
    PositionSize,
    SizeAdjustments
)

__version__ = "1.0.0"
__all__ = [
    "PositionSizeCalculator",
    "PositionSizeRequest", 
    "PositionSizeResponse",
    "PositionSize",
    "SizeAdjustments"
]