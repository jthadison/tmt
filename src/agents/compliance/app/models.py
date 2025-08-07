"""
Data models for compliance system
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel, Field
from .prop_firm_configs import PropFirm, AccountPhase, TradingPlatform


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class ViolationType(str, Enum):
    DAILY_LOSS_EXCEEDED = "daily_loss_exceeded"
    MAX_DRAWDOWN_EXCEEDED = "max_drawdown_exceeded"
    NEWS_BLACKOUT_VIOLATION = "news_blackout_violation"
    MIN_HOLD_TIME_VIOLATION = "min_hold_time_violation"
    POSITION_SIZE_VIOLATION = "position_size_violation"
    MAX_POSITIONS_EXCEEDED = "max_positions_exceeded"
    WEEKEND_HOLDING_VIOLATION = "weekend_holding_violation"
    MISSING_STOP_LOSS = "missing_stop_loss"
    PROHIBITED_STRATEGY = "prohibited_strategy"
    CONSISTENCY_VIOLATION = "consistency_violation"


class ComplianceStatus(str, Enum):
    COMPLIANT = "compliant"
    WARNING = "warning"
    VIOLATION = "violation"
    SUSPENDED = "suspended"


class TradingAccount(BaseModel):
    """Trading account configuration and state"""
    account_id: str
    prop_firm: PropFirm
    account_phase: AccountPhase
    initial_balance: Decimal
    current_balance: Decimal
    platform: TradingPlatform
    status: ComplianceStatus
    created_at: datetime
    
    # Compliance tracking
    daily_pnl: Decimal = Field(default=Decimal("0.0"))
    total_drawdown: Decimal = Field(default=Decimal("0.0"))
    max_drawdown_reached: Decimal = Field(default=Decimal("0.0"))
    trading_days_completed: int = Field(default=0)
    last_reset_date: Optional[datetime] = None
    
    # Position tracking
    open_positions: int = Field(default=0)
    total_positions_today: int = Field(default=0)


class TradeOrder(BaseModel):
    """Trade order for validation"""
    order_id: Optional[str] = None
    account_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal  # Lot size
    price: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Position(BaseModel):
    """Open position tracking"""
    position_id: str
    account_id: str
    symbol: str
    side: OrderSide
    quantity: Decimal
    entry_price: Decimal
    current_price: Decimal
    unrealized_pnl: Decimal
    opened_at: datetime
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None


class NewsEvent(BaseModel):
    """Economic news event"""
    event_id: str
    title: str
    currency: str
    impact: str  # high, medium, low
    actual: Optional[str] = None
    forecast: Optional[str] = None
    previous: Optional[str] = None
    timestamp: datetime
    
    def is_high_impact(self) -> bool:
        return self.impact.lower() == "high"


class ValidationRequest(BaseModel):
    """Trade validation request"""
    account_id: str
    trade_order: TradeOrder
    current_positions: List[Position] = Field(default_factory=list)
    upcoming_news: List[NewsEvent] = Field(default_factory=list)


class ValidationResult(BaseModel):
    """Trade validation result"""
    is_valid: bool
    compliance_status: ComplianceStatus
    violations: List[ViolationType] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    reason: str
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ComplianceViolation(BaseModel):
    """Compliance violation record"""
    violation_id: str
    account_id: str
    violation_type: ViolationType
    severity: str  # warning, error, critical
    description: str
    rule_violated: str
    current_value: Decimal
    limit_value: Decimal
    trade_order: Optional[TradeOrder] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    resolved: bool = Field(default=False)
    resolution_notes: Optional[str] = None


class AccountStatus(BaseModel):
    """Current account compliance status"""
    account_id: str
    compliance_status: ComplianceStatus
    daily_pnl: Decimal
    daily_loss_limit: Decimal
    daily_loss_remaining: Decimal
    total_drawdown: Decimal
    max_drawdown_limit: Decimal
    drawdown_remaining: Decimal
    open_positions: int
    max_positions_allowed: int
    trading_days_completed: int
    min_trading_days_required: int
    recent_violations: List[ComplianceViolation] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class PnLUpdate(BaseModel):
    """Real-time P&L update"""
    account_id: str
    position_id: Optional[str] = None
    realized_pnl: Decimal = Field(default=Decimal("0.0"))
    unrealized_pnl: Decimal = Field(default=Decimal("0.0"))
    total_pnl: Decimal
    daily_pnl: Decimal
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ComplianceMetrics(BaseModel):
    """Compliance monitoring metrics"""
    account_id: str
    total_trades: int
    successful_validations: int
    violations_count: int
    warnings_count: int
    compliance_rate: float
    avg_validation_time_ms: float
    last_violation: Optional[datetime] = None
    uptime_minutes: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)