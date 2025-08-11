"""
Position Sizing Data Models
===========================

This module defines the data models and types used throughout the position
sizing system.
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID
import datetime


class RiskModel(Enum):
    """Risk percentage calculation models."""
    FIXED = "fixed"
    ADAPTIVE = "adaptive"
    KELLY_CRITERION = "kelly_criterion"


class VolatilityRegime(Enum):
    """Market volatility classification."""
    LOW = "low"
    BELOW_NORMAL = "below_normal"
    NORMAL = "normal"
    ABOVE_NORMAL = "above_normal"
    HIGH = "high"
    EXTREME = "extreme"


class DrawdownLevel(Enum):
    """Account drawdown classification levels."""
    MINIMAL = "minimal"
    SMALL = "small"
    MODERATE = "moderate"
    LARGE = "large"
    EXTREME = "extreme"


class PropFirm(Enum):
    """Supported prop firms."""
    FTMO = "ftmo"
    MY_FOREX_FUNDS = "my_forex_funds"
    THE5ERS = "the5ers"
    FUNDED_NEXT = "funded_next"
    TRUE_FOREX_FUNDS = "true_forex_funds"


@dataclass
class PositionSizeRequest:
    """Request parameters for position size calculation."""
    signal_id: UUID
    account_id: UUID
    symbol: str
    account_balance: Decimal
    stop_distance_pips: Decimal
    risk_model: RiskModel = RiskModel.FIXED
    base_risk_percentage: Optional[Decimal] = None
    entry_price: Optional[Decimal] = None
    direction: str = "long"  # "long" or "short"
    
    def __post_init__(self):
        """Validate request parameters."""
        if self.base_risk_percentage is None:
            self.base_risk_percentage = Decimal("1.0")  # Default 1%
        
        if self.account_balance <= 0:
            raise ValueError("Account balance must be positive")
        
        if self.stop_distance_pips <= 0:
            raise ValueError("Stop distance must be positive")


@dataclass
class SizeAdjustments:
    """Adjustment factors applied to base position size."""
    volatility_factor: Decimal
    drawdown_factor: Decimal
    correlation_factor: Decimal
    limit_factor: Decimal
    variance_factor: Decimal
    
    @property
    def total_adjustment(self) -> Decimal:
        """Calculate total adjustment factor."""
        return (self.volatility_factor * 
                self.drawdown_factor * 
                self.correlation_factor * 
                self.limit_factor * 
                self.variance_factor)


@dataclass
class PositionSize:
    """Final position size calculation result."""
    signal_id: UUID
    account_id: UUID
    symbol: str
    base_size: Decimal
    adjusted_size: Decimal
    adjustments: SizeAdjustments
    risk_amount: Decimal
    pip_value: Decimal
    reasoning: str
    calculated_at: datetime.datetime
    
    @property
    def size_reduction_pct(self) -> Decimal:
        """Calculate percentage reduction from base size."""
        if self.base_size == 0:
            return Decimal("0")
        
        reduction = (self.base_size - self.adjusted_size) / self.base_size
        return reduction * Decimal("100")


@dataclass
class PositionSizeResponse:
    """API response for position size calculation."""
    position_size: PositionSize
    validation_errors: List[str]
    warnings: List[str]
    calculation_time_ms: int
    
    @property
    def is_valid(self) -> bool:
        """Check if calculation is valid for trading."""
        return len(self.validation_errors) == 0 and self.position_size.adjusted_size > 0


@dataclass
class PropFirmLimits:
    """Prop firm specific position limits."""
    max_lot_size: Decimal
    max_positions_per_symbol: int
    max_total_exposure: Decimal
    max_daily_loss: Decimal
    max_total_drawdown: Decimal
    margin_requirement: Decimal
    minimum_trade_size: Decimal
    
    
@dataclass 
class MarketContext:
    """Market context for position sizing."""
    symbol: str
    current_atr: Decimal
    volatility_percentile: Decimal
    volatility_regime: VolatilityRegime
    pip_value: Decimal
    contract_value: Decimal
    margin_requirement: Decimal
    

@dataclass
class AccountContext:
    """Account context for position sizing."""
    account_id: UUID
    current_balance: Decimal
    equity: Decimal
    drawdown_pct: Decimal
    drawdown_level: DrawdownLevel
    open_positions_count: int
    total_exposure: Decimal
    available_margin: Decimal
    prop_firm: PropFirm
    

@dataclass
class PositionCorrelation:
    """Correlation data between positions."""
    symbol1: str
    symbol2: str
    correlation_coefficient: Decimal
    lookback_days: int
    confidence_level: Decimal
    

@dataclass
class VarianceProfile:
    """Account-specific variance profile for anti-detection."""
    account_id: UUID
    aggressive: bool
    variance_range_min: Decimal  # Minimum variance percentage
    variance_range_max: Decimal  # Maximum variance percentage
    seed: int  # Randomization seed for consistency
    pattern_detected: bool
    last_updated: datetime.datetime