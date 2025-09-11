"""
Centralized Trading Instruments Configuration

This module provides the official list of tradeable instruments for the entire
trading system. All services should import from this module to ensure consistency.
"""

from typing import Dict, List, Set
from enum import Enum


class InstrumentCategory(Enum):
    """Categories for organizing instruments"""
    MAJOR_PAIRS = "major_pairs"
    MINOR_PAIRS = "minor_pairs" 
    EXOTIC_PAIRS = "exotic_pairs"
    COMMODITIES = "commodities"
    INDICES = "indices"


class InstrumentInfo:
    """Information about a trading instrument"""
    def __init__(
        self,
        symbol: str,
        name: str,
        category: InstrumentCategory,
        pip_precision: int = 4,
        min_trade_size: float = 0.01,
        max_trade_size: float = 100.0,
        enabled: bool = True
    ):
        self.symbol = symbol
        self.name = name
        self.category = category
        self.pip_precision = pip_precision
        self.min_trade_size = min_trade_size
        self.max_trade_size = max_trade_size
        self.enabled = enabled


# Official list of supported trading instruments
INSTRUMENTS = {
    # Major Currency Pairs - Primary Focus
    "EUR_USD": InstrumentInfo(
        symbol="EUR_USD",
        name="Euro / US Dollar", 
        category=InstrumentCategory.MAJOR_PAIRS,
        pip_precision=4
    ),
    "GBP_USD": InstrumentInfo(
        symbol="GBP_USD",
        name="British Pound / US Dollar",
        category=InstrumentCategory.MAJOR_PAIRS,
        pip_precision=4
    ),
    "USD_CHF": InstrumentInfo(
        symbol="USD_CHF", 
        name="US Dollar / Swiss Franc",
        category=InstrumentCategory.MAJOR_PAIRS,
        pip_precision=4
    ),
    "AUD_USD": InstrumentInfo(
        symbol="AUD_USD",
        name="Australian Dollar / US Dollar",
        category=InstrumentCategory.MAJOR_PAIRS,
        pip_precision=4
    ),
    "USD_CAD": InstrumentInfo(
        symbol="USD_CAD",
        name="US Dollar / Canadian Dollar", 
        category=InstrumentCategory.MAJOR_PAIRS,
        pip_precision=4
    ),
    "NZD_USD": InstrumentInfo(
        symbol="NZD_USD",
        name="New Zealand Dollar / US Dollar",
        category=InstrumentCategory.MAJOR_PAIRS,
        pip_precision=4
    ),
    
    # USD_JPY - Special precision handling (2 decimal places)
    "USD_JPY": InstrumentInfo(
        symbol="USD_JPY",
        name="US Dollar / Japanese Yen",
        category=InstrumentCategory.MAJOR_PAIRS,
        pip_precision=2,  # JPY pairs use 2 decimal places
        enabled=True  # Re-enabled: precision handling is properly implemented
    ),
    
    # Cross Currency Pairs
    "EUR_GBP": InstrumentInfo(
        symbol="EUR_GBP",
        name="Euro / British Pound",
        category=InstrumentCategory.MINOR_PAIRS,
        pip_precision=4
    ),
}

# Convenience functions for accessing instrument data
def get_active_instruments() -> List[str]:
    """Get list of currently enabled instrument symbols"""
    return [symbol for symbol, info in INSTRUMENTS.items() if info.enabled]


def get_instruments_by_category(category: InstrumentCategory) -> List[str]:
    """Get instruments filtered by category"""
    return [
        symbol for symbol, info in INSTRUMENTS.items() 
        if info.category == category and info.enabled
    ]


def get_major_pairs() -> List[str]:
    """Get list of major currency pairs"""
    return get_instruments_by_category(InstrumentCategory.MAJOR_PAIRS)


def get_instrument_info(symbol: str) -> InstrumentInfo:
    """Get detailed information about an instrument"""
    if symbol not in INSTRUMENTS:
        raise ValueError(f"Unknown instrument: {symbol}")
    return INSTRUMENTS[symbol]


def is_instrument_enabled(symbol: str) -> bool:
    """Check if an instrument is enabled for trading"""
    return symbol in INSTRUMENTS and INSTRUMENTS[symbol].enabled


def get_instrument_precision(symbol: str) -> int:
    """Get pip precision for an instrument"""
    return get_instrument_info(symbol).pip_precision


# Constants for backward compatibility
DEFAULT_INSTRUMENTS = get_active_instruments()
MAJOR_PAIRS = get_major_pairs()

# Active monitoring instruments (for market analysis agents)
ACTIVE_MONITORING_INSTRUMENTS = [
    "EUR_USD", "GBP_USD", "USD_JPY", "USD_CHF", "AUD_USD", "NZD_USD", "EUR_GBP"
]

# Core trading instruments (most reliable for signal generation)
CORE_TRADING_INSTRUMENTS = [
    "EUR_USD", "GBP_USD", "USD_JPY", "USD_CHF", "AUD_USD"
]