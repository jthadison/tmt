"""
Trading System Configuration Management

Centralized configuration for separating simulation/mock from production components.
Prevents accidental use of random/mock components in live trading.
"""

import os
import logging
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class TradingMode(Enum):
    """Trading system operational modes"""
    SIMULATION = "simulation"      # Full simulation - no real trading
    PAPER = "paper"               # Paper trading - real data, simulated execution
    PRACTICE = "practice"         # OANDA practice account
    LIVE = "live"                # Live trading with real money


class ComponentMode(Enum):
    """Component operational modes"""
    MOCK = "mock"                # Mock/simulated components
    REAL = "real"                # Real API connections


@dataclass
class TradingConfig:
    """Centralized trading system configuration"""

    # Core trading mode
    trading_mode: TradingMode = TradingMode.SIMULATION

    # Component configurations
    use_mock_streaming: bool = True
    use_mock_pattern_detection: bool = False
    use_mock_execution: bool = True

    # OANDA configuration
    oanda_environment: str = "practice"  # "practice" or "live"
    oanda_api_key: Optional[str] = None
    oanda_account_id: Optional[str] = None

    # Safety settings
    max_daily_trades: int = 50
    max_position_size: float = 0.02  # 2% of account
    enable_emergency_stop: bool = True

    # Audit and compliance
    enable_audit_logging: bool = True
    prevent_random_in_production: bool = True

    def __post_init__(self):
        """Validate configuration after initialization"""
        # Load from environment if not provided
        if not self.oanda_api_key:
            self.oanda_api_key = os.getenv("OANDA_API_KEY")
        if not self.oanda_account_id:
            self.oanda_account_id = os.getenv("OANDA_ACCOUNT_ID")

        # Auto-configure based on trading mode
        self._auto_configure()

        # Validate configuration
        self._validate()

        logger.info(f"Trading system configured: {self.trading_mode.value}")

    def _auto_configure(self):
        """Auto-configure components based on trading mode"""
        if self.trading_mode == TradingMode.SIMULATION:
            self.use_mock_streaming = True
            self.use_mock_execution = True
            self.oanda_environment = "practice"

        elif self.trading_mode == TradingMode.PAPER:
            self.use_mock_streaming = False  # Real market data
            self.use_mock_execution = True   # Simulated execution
            self.oanda_environment = "practice"

        elif self.trading_mode == TradingMode.PRACTICE:
            self.use_mock_streaming = False  # Real market data
            self.use_mock_execution = False  # Real OANDA practice
            self.oanda_environment = "practice"

        elif self.trading_mode == TradingMode.LIVE:
            self.use_mock_streaming = False
            self.use_mock_execution = False
            self.oanda_environment = "live"
            self.prevent_random_in_production = True  # Enforce strict mode

    def _validate(self):
        """Validate configuration for safety"""
        if self.trading_mode in [TradingMode.PRACTICE, TradingMode.LIVE]:
            if not self.oanda_api_key:
                raise ValueError(f"OANDA API key required for {self.trading_mode.value} mode")
            if not self.oanda_account_id:
                raise ValueError(f"OANDA account ID required for {self.trading_mode.value} mode")

        if self.trading_mode == TradingMode.LIVE:
            if self.oanda_environment != "live":
                raise ValueError("Live trading mode requires OANDA live environment")

    def is_production_mode(self) -> bool:
        """Check if running in production mode"""
        return self.trading_mode in [TradingMode.PRACTICE, TradingMode.LIVE]

    def requires_real_data(self) -> bool:
        """Check if real market data is required"""
        return self.trading_mode in [TradingMode.PAPER, TradingMode.PRACTICE, TradingMode.LIVE]

    def allows_mock_components(self) -> bool:
        """Check if mock components are allowed"""
        return self.trading_mode in [TradingMode.SIMULATION, TradingMode.PAPER]

    def get_stream_manager_config(self) -> Dict[str, Any]:
        """Get stream manager configuration"""
        return {
            "use_mock": self.use_mock_streaming,
            "environment": self.oanda_environment,
            "api_key": self.oanda_api_key
        }

    def get_execution_config(self) -> Dict[str, Any]:
        """Get execution engine configuration"""
        return {
            "use_mock": self.use_mock_execution,
            "environment": self.oanda_environment,
            "api_key": self.oanda_api_key,
            "account_id": self.oanda_account_id,
            "max_position_size": self.max_position_size
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            "trading_mode": self.trading_mode.value,
            "use_mock_streaming": self.use_mock_streaming,
            "use_mock_pattern_detection": self.use_mock_pattern_detection,
            "use_mock_execution": self.use_mock_execution,
            "oanda_environment": self.oanda_environment,
            "max_daily_trades": self.max_daily_trades,
            "max_position_size": self.max_position_size,
            "enable_emergency_stop": self.enable_emergency_stop,
            "enable_audit_logging": self.enable_audit_logging,
            "prevent_random_in_production": self.prevent_random_in_production
        }


# Global configuration instance
_global_config: Optional[TradingConfig] = None


def get_trading_config() -> TradingConfig:
    """Get global trading configuration"""
    global _global_config

    if _global_config is None:
        # Load from environment
        trading_mode_str = os.getenv("TRADING_MODE", "simulation").lower()

        try:
            trading_mode = TradingMode(trading_mode_str)
        except ValueError:
            logger.warning(f"Invalid trading mode '{trading_mode_str}', defaulting to simulation")
            trading_mode = TradingMode.SIMULATION

        _global_config = TradingConfig(trading_mode=trading_mode)

    return _global_config


def set_trading_config(config: TradingConfig):
    """Set global trading configuration"""
    global _global_config
    _global_config = config
    logger.info(f"Trading configuration updated: {config.trading_mode.value}")


def is_production_environment() -> bool:
    """Quick check if running in production"""
    return get_trading_config().is_production_mode()


def validate_no_random_in_production():
    """Validate that random components are not used in production"""
    config = get_trading_config()

    if config.is_production_mode() and config.prevent_random_in_production:
        # This would be called by components to validate they're not using random
        import traceback
        stack = traceback.extract_stack()

        # Look for 'random' in the call stack
        for frame in stack:
            if 'random' in frame.filename.lower() or 'mock' in frame.filename.lower():
                error_msg = f"Random/mock component detected in production mode: {frame.filename}:{frame.lineno}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)


# Environment variable helpers
def set_env_for_testing():
    """Set environment variables for testing"""
    os.environ["TRADING_MODE"] = "simulation"
    os.environ["USE_MOCK_STREAMING"] = "true"


def set_env_for_production():
    """Set environment variables for production"""
    os.environ["TRADING_MODE"] = "practice"
    os.environ["USE_MOCK_STREAMING"] = "false"