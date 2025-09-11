"""
Shared configuration module for the trading system.
"""

from .instruments import (
    InstrumentCategory,
    InstrumentInfo,
    INSTRUMENTS,
    get_active_instruments,
    get_instruments_by_category,
    get_major_pairs,
    get_instrument_info,
    is_instrument_enabled,
    get_instrument_precision,
    DEFAULT_INSTRUMENTS,
    MAJOR_PAIRS,
    ACTIVE_MONITORING_INSTRUMENTS,
    CORE_TRADING_INSTRUMENTS,
)

__all__ = [
    "InstrumentCategory",
    "InstrumentInfo", 
    "INSTRUMENTS",
    "get_active_instruments",
    "get_instruments_by_category",
    "get_major_pairs",
    "get_instrument_info",
    "is_instrument_enabled",
    "get_instrument_precision",
    "DEFAULT_INSTRUMENTS",
    "MAJOR_PAIRS",
    "ACTIVE_MONITORING_INSTRUMENTS",
    "CORE_TRADING_INSTRUMENTS",
]