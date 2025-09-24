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

# Conservative Emergency Parameters (response to September 2025 degradation)
EMERGENCY_CONSERVATIVE_PARAMETERS = {
    "confidence_threshold": 90.0,  # Ultra-high selectivity
    "min_risk_reward": 4.0,        # High risk-reward requirement
    "max_trades_per_day": 3,       # Limit frequency
    "max_risk_per_trade": 0.3,     # Reduced position size
    "session_specific": False,      # Disable session targeting
    "source": "emergency_conservative_v1",
    "description": "Ultra-conservative parameters for crisis situations"
}

# Stabilized Parameters V1 (regularized version of session-targeted)
STABILIZED_V1_PARAMETERS = {
    "tokyo": {
        "confidence_threshold": 80.0,  # Reduced from 85.0
        "min_risk_reward": 3.5,       # Reduced from 4.0
        "max_risk_reward": 5.0,       # Added upper limit
        "volatility_adjustment": 0.15,  # Position size adjustment
        "source": "stabilized_v1_tokyo"
    },
    "london": {
        "confidence_threshold": 75.0,  # Increased from 72.0
        "min_risk_reward": 3.0,       # Reduced from 3.2
        "max_risk_reward": 4.5,       # Added upper limit
        "volatility_adjustment": 0.10,  # Position size adjustment
        "source": "stabilized_v1_london"
    },
    "new_york": {
        "confidence_threshold": 72.0,  # Increased from 70.0
        "min_risk_reward": 2.8,       # Maintained
        "max_risk_reward": 4.0,       # Added upper limit
        "volatility_adjustment": 0.12,  # Position size adjustment
        "source": "stabilized_v1_new_york"
    },
    "sydney": {
        "confidence_threshold": 78.0,  # Maintained
        "min_risk_reward": 3.2,       # Reduced from 3.5
        "max_risk_reward": 4.5,       # Added upper limit
        "volatility_adjustment": 0.08,  # Position size adjustment
        "source": "stabilized_v1_sydney"
    },
    "overlap": {
        "confidence_threshold": 72.0,  # Increased from 70.0
        "min_risk_reward": 2.8,       # Maintained
        "max_risk_reward": 4.0,       # Added upper limit
        "volatility_adjustment": 0.15,  # Position size adjustment
        "source": "stabilized_v1_overlap"
    }
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

# Parameter mode control
class ParameterMode(Enum):
    """Parameter mode selections"""
    SESSION_TARGETED = "session_targeted"
    UNIVERSAL_CYCLE_4 = "universal_cycle_4"
    EMERGENCY_CONSERVATIVE = "emergency_conservative"
    STABILIZED_V1 = "stabilized_v1"

# Current parameter mode (can be changed via API or emergency override)
CURRENT_PARAMETER_MODE = ParameterMode.SESSION_TARGETED

def get_current_parameters():
    """Get trading parameters based on current configuration mode"""

    if CURRENT_PARAMETER_MODE == ParameterMode.EMERGENCY_CONSERVATIVE:
        params = EMERGENCY_CONSERVATIVE_PARAMETERS.copy()
        params['current_session'] = 'emergency'
        params['mode'] = 'emergency_conservative'
        return params

    elif CURRENT_PARAMETER_MODE == ParameterMode.STABILIZED_V1:
        if SESSION_TARGETING_ENABLED:
            session = get_current_session()
            session_key = session.value.lower()
            if session_key in STABILIZED_V1_PARAMETERS:
                params = STABILIZED_V1_PARAMETERS[session_key].copy()
                params['current_session'] = session.value
                params['mode'] = 'stabilized_v1'
                return params
        # Fallback to universal if session not found
        params = UNIVERSAL_PARAMETERS.copy()
        params['mode'] = 'universal_fallback'
        return params

    elif CURRENT_PARAMETER_MODE == ParameterMode.SESSION_TARGETED and SESSION_TARGETING_ENABLED:
        session = get_current_session()
        params = SESSION_PARAMETERS.get(session, UNIVERSAL_PARAMETERS).copy()
        params['current_session'] = session.value
        params['mode'] = 'session_targeted'
        return params

    else:  # Default to UNIVERSAL_CYCLE_4
        params = UNIVERSAL_PARAMETERS.copy()
        params['current_session'] = 'universal'
        params['mode'] = 'universal_cycle_4'
        return params

def set_parameter_mode(mode: ParameterMode, reason: str = "Manual override"):
    """Change parameter mode with logging"""
    global CURRENT_PARAMETER_MODE
    previous_mode = CURRENT_PARAMETER_MODE
    CURRENT_PARAMETER_MODE = mode

    # Log the change
    print(f"Parameter mode changed: {previous_mode.value} → {mode.value}")
    print(f"Reason: {reason}")
    print(f"Timestamp: {datetime.utcnow()}")

    return {
        "previous_mode": previous_mode.value,
        "new_mode": mode.value,
        "reason": reason,
        "timestamp": datetime.utcnow().isoformat()
    }

def emergency_rollback(reason: str = "Performance degradation detected"):
    """Emergency rollback to conservative parameters"""
    return set_parameter_mode(ParameterMode.EMERGENCY_CONSERVATIVE, f"EMERGENCY: {reason}")

def get_available_parameter_modes():
    """Get all available parameter modes with descriptions"""
    return {
        ParameterMode.SESSION_TARGETED.value: {
            "description": "Session-optimized parameters (original system)",
            "risk_level": "medium",
            "recommended_for": "stable market conditions"
        },
        ParameterMode.UNIVERSAL_CYCLE_4.value: {
            "description": "Universal parameters (Cycle 4 baseline)",
            "risk_level": "medium",
            "recommended_for": "general market conditions"
        },
        ParameterMode.STABILIZED_V1.value: {
            "description": "Regularized session parameters (September fix)",
            "risk_level": "low-medium",
            "recommended_for": "improved stability after September issues"
        },
        ParameterMode.EMERGENCY_CONSERVATIVE.value: {
            "description": "Ultra-conservative crisis parameters",
            "risk_level": "very low",
            "recommended_for": "crisis situations or performance degradation"
        }
    }

# Trading configuration with enhanced parameter management
TRADING_CONFIG = {
    "enable_trading": True,
    "session_targeting_enabled": SESSION_TARGETING_ENABLED,
    "current_parameter_mode": CURRENT_PARAMETER_MODE.value,
    "current_parameters": get_current_parameters(),
    "rollback_available": True,
    "emergency_rollback_available": True,
    "implementation_date": "2025-09-22",
    "september_fixes_date": "2025-09-23",
    "available_modes": list(ParameterMode),
    "stability_improvements": {
        "regularization": True,
        "regime_detection": True,
        "enhanced_validation": True,
        "conservative_backup": True,
        "performance_monitoring": True
    }
}