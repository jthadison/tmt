"""
Market Analysis Agent Configuration
With session-targeted trading enabled
"""

import os
from datetime import datetime
from enum import Enum

class TradingSession(Enum):
    """Trading session definitions with GMT/UTC timings"""
    SYDNEY = "Sydney"       # 21:00 - 06:00 GMT
    TOKYO = "Tokyo"         # 00:00 - 09:00 GMT
    LONDON = "London"       # 08:00 - 17:00 GMT
    NEW_YORK = "New_York"   # 13:00 - 22:00 GMT
    OVERLAP = "Overlap"     # 13:00 - 17:00 GMT (London-NY)

# Session-targeted trading configuration
SESSION_TARGETING_ENABLED = True  # Toggle for session-specific parameters

# Core trading instruments (maintained from original config)
CORE_TRADING_INSTRUMENTS = [
    "EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "USD_CHF"
]

# Session-specific optimized parameters
SESSION_PARAMETERS = {
    TradingSession.TOKYO: {
        "confidence_threshold": 85.0,
        "min_risk_reward": 4.0,
        "source": "session_targeted_cycle_5"
    },
    TradingSession.LONDON: {
        "confidence_threshold": 72.0,
        "min_risk_reward": 3.2,
        "source": "session_targeted_cycle_5"
    },
    TradingSession.NEW_YORK: {
        "confidence_threshold": 70.0,
        "min_risk_reward": 2.8,
        "source": "session_targeted_cycle_5"
    },
    TradingSession.SYDNEY: {
        "confidence_threshold": 78.0,
        "min_risk_reward": 3.5,
        "source": "session_targeted_cycle_5"
    },
    TradingSession.OVERLAP: {
        "confidence_threshold": 70.0,
        "min_risk_reward": 2.8,
        "source": "session_targeted_cycle_5"
    }
}

# Universal Cycle 4 parameters (fallback when session targeting disabled)
UNIVERSAL_PARAMETERS = {
    "confidence_threshold": 55.0,
    "min_risk_reward": 1.8,
    "source": "cycle_4_balanced_aggressive"
}

def get_current_session():
    """Determine current trading session based on GMT time"""
    current_hour = datetime.utcnow().hour

    if 21 <= current_hour or current_hour < 6:
        return TradingSession.SYDNEY
    elif 0 <= current_hour < 9:
        return TradingSession.TOKYO
    elif 8 <= current_hour < 13:
        return TradingSession.LONDON
    elif 13 <= current_hour < 17:
        return TradingSession.OVERLAP  # London-NY overlap
    elif 17 <= current_hour < 22:
        return TradingSession.NEW_YORK
    else:
        return TradingSession.LONDON  # Default

def get_current_parameters():
    """Get trading parameters based on current configuration"""
    if SESSION_TARGETING_ENABLED:
        session = get_current_session()
        params = SESSION_PARAMETERS.get(session, UNIVERSAL_PARAMETERS).copy()
        params['current_session'] = session.value
        params['mode'] = 'session_targeted'
        return params
    else:
        params = UNIVERSAL_PARAMETERS.copy()
        params['current_session'] = 'universal'
        params['mode'] = 'universal_cycle_4'
        return params

# Trading configuration with session targeting enabled
TRADING_CONFIG = {
    "enable_trading": True,
    "session_targeting_enabled": SESSION_TARGETING_ENABLED,
    "current_parameters": get_current_parameters(),
    "rollback_available": True,
    "implementation_date": "2025-09-22"
}