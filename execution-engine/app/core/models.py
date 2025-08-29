"""
Core data models for the execution engine.

This module defines all the fundamental data structures used throughout
the execution engine for orders, positions, and execution results.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, validator


class OrderSide(str, Enum):
    """Order side enumeration."""
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """Order type enumeration."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"
    MARKET_IF_TOUCHED = "market_if_touched"


class TimeInForce(str, Enum):
    """Time in force enumeration."""
    FOK = "fill_or_kill"  # Fill completely or cancel
    IOC = "immediate_or_cancel"  # Fill what's available, cancel rest
    GTC = "good_till_cancelled"  # Good until explicitly cancelled
    GTD = "good_till_date"  # Good until specific date


class OrderStatus(str, Enum):
    """Order status enumeration."""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class PositionSide(str, Enum):
    """Position side enumeration."""
    LONG = "long"
    SHORT = "short"
    FLAT = "flat"


class ExecutionResult(str, Enum):
    """Execution result enumeration."""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    TIMEOUT = "timeout"
    REJECTED = "rejected"


class StopLoss(BaseModel):
    """Stop loss configuration."""
    price: Decimal = Field(..., description="Stop loss price level")
    guaranteed: bool = Field(default=False, description="Whether guaranteed stop loss")
    distance: Optional[Decimal] = Field(None, description="Distance in pips from entry")
    
    @validator('price')
    def validate_price(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Stop loss price must be positive")
        return v


class TakeProfit(BaseModel):
    """Take profit configuration."""
    price: Decimal = Field(..., description="Take profit price level")
    distance: Optional[Decimal] = Field(None, description="Distance in pips from entry")
    
    @validator('price')
    def validate_price(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Take profit price must be positive")
        return v


class ClientExtensions(BaseModel):
    """Client extensions for order tracking."""
    id: Optional[str] = Field(None, description="Client order ID")
    tag: Optional[str] = Field(None, description="Order tag for categorization")
    comment: Optional[str] = Field(None, description="Order comment")


class Order(BaseModel):
    """Order model representing a trading order."""
    id: UUID = Field(default_factory=uuid.uuid4, description="Unique order ID")
    client_order_id: Optional[str] = Field(None, description="Client-assigned order ID")
    oanda_order_id: Optional[str] = Field(None, description="OANDA order ID")
    account_id: str = Field(..., description="Trading account ID")
    instrument: str = Field(..., description="Trading instrument (e.g., EUR_USD)")
    units: Decimal = Field(..., description="Number of units to trade")
    side: OrderSide = Field(..., description="Order side (buy/sell)")
    type: OrderType = Field(..., description="Order type")
    status: OrderStatus = Field(default=OrderStatus.PENDING, description="Order status")
    
    # Price levels
    requested_price: Optional[Decimal] = Field(None, description="Requested execution price")
    fill_price: Optional[Decimal] = Field(None, description="Actual fill price")
    stop_price: Optional[Decimal] = Field(None, description="Stop trigger price")
    
    # Risk management
    stop_loss: Optional[StopLoss] = Field(None, description="Stop loss configuration")
    take_profit: Optional[TakeProfit] = Field(None, description="Take profit configuration")
    
    # Order parameters
    time_in_force: TimeInForce = Field(default=TimeInForce.GTC, description="Time in force")
    expiry_time: Optional[datetime] = Field(None, description="Order expiry time")
    
    # Execution details
    execution_time_ms: Optional[int] = Field(None, description="Execution time in milliseconds")
    slippage: Optional[Decimal] = Field(None, description="Execution slippage")
    commission: Optional[Decimal] = Field(None, description="Commission paid")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Order creation time")
    submitted_at: Optional[datetime] = Field(None, description="Order submission time")
    filled_at: Optional[datetime] = Field(None, description="Order fill time")
    cancelled_at: Optional[datetime] = Field(None, description="Order cancellation time")
    
    # Error handling
    rejection_reason: Optional[str] = Field(None, description="Rejection reason if applicable")
    retry_count: int = Field(default=0, description="Number of retry attempts")
    
    # Extensions
    client_extensions: Optional[ClientExtensions] = Field(None, description="Client extensions")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    @validator('units')
    def validate_units(cls, v: Decimal) -> Decimal:
        if v == 0:
            raise ValueError("Units cannot be zero")
        return v
    
    @validator('instrument')
    def validate_instrument(cls, v: str) -> str:
        if not v or '_' not in v:
            raise ValueError("Invalid instrument format")
        return v.upper()
    
    def is_buy(self) -> bool:
        """Check if this is a buy order."""
        return self.side == OrderSide.BUY
    
    def is_sell(self) -> bool:
        """Check if this is a sell order."""
        return self.side == OrderSide.SELL
    
    def is_market_order(self) -> bool:
        """Check if this is a market order."""
        return self.type == OrderType.MARKET
    
    def is_limit_order(self) -> bool:
        """Check if this is a limit order."""
        return self.type == OrderType.LIMIT
    
    def is_filled(self) -> bool:
        """Check if order is fully filled."""
        return self.status == OrderStatus.FILLED
    
    def is_active(self) -> bool:
        """Check if order is still active."""
        return self.status in {OrderStatus.PENDING, OrderStatus.SUBMITTED, OrderStatus.PARTIALLY_FILLED}


class Position(BaseModel):
    """Position model representing a trading position."""
    id: UUID = Field(default_factory=uuid.uuid4, description="Unique position ID")
    account_id: str = Field(..., description="Trading account ID")
    instrument: str = Field(..., description="Trading instrument")
    units: Decimal = Field(..., description="Position size")
    side: PositionSide = Field(..., description="Position side")
    
    # Price information
    average_price: Decimal = Field(..., description="Average entry price")
    current_price: Optional[Decimal] = Field(None, description="Current market price")
    
    # P&L information
    realized_pl: Decimal = Field(default=Decimal("0"), description="Realized P&L")
    unrealized_pl: Optional[Decimal] = Field(None, description="Unrealized P&L")
    
    # Risk information
    margin_used: Optional[Decimal] = Field(None, description="Margin used")
    margin_rate: Optional[Decimal] = Field(None, description="Margin rate")
    
    # Timestamps
    opened_at: datetime = Field(default_factory=datetime.utcnow, description="Position open time")
    closed_at: Optional[datetime] = Field(None, description="Position close time")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Last update time")
    
    # Associated orders
    opening_order_id: Optional[UUID] = Field(None, description="Opening order ID")
    stop_loss_order_id: Optional[UUID] = Field(None, description="Stop loss order ID")
    take_profit_order_id: Optional[UUID] = Field(None, description="Take profit order ID")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    @validator('units')
    def validate_units(cls, v: Decimal) -> Decimal:
        if v == 0:
            raise ValueError("Position units cannot be zero")
        return v
    
    def is_long(self) -> bool:
        """Check if position is long."""
        return self.side == PositionSide.LONG
    
    def is_short(self) -> bool:
        """Check if position is short."""
        return self.side == PositionSide.SHORT
    
    def is_open(self) -> bool:
        """Check if position is still open."""
        return self.closed_at is None
    
    def calculate_unrealized_pl(self, current_price: Decimal) -> Decimal:
        """Calculate unrealized P&L based on current price."""
        if self.is_long():
            return (current_price - self.average_price) * abs(self.units)
        else:
            return (self.average_price - current_price) * abs(self.units)


class OrderRequest(BaseModel):
    """Order request model for API endpoints."""
    account_id: str = Field(..., description="Trading account ID")
    instrument: str = Field(..., description="Trading instrument")
    units: Decimal = Field(..., description="Number of units to trade")
    side: OrderSide = Field(..., description="Order side")
    type: OrderType = Field(default=OrderType.MARKET, description="Order type")
    
    # Price levels
    price: Optional[Decimal] = Field(None, description="Order price (for limit orders)")
    stop_price: Optional[Decimal] = Field(None, description="Stop price (for stop orders)")
    
    # Risk management
    stop_loss: Optional[StopLoss] = Field(None, description="Stop loss configuration")
    take_profit: Optional[TakeProfit] = Field(None, description="Take profit configuration")
    
    # Order parameters
    time_in_force: TimeInForce = Field(default=TimeInForce.GTC, description="Time in force")
    expiry_time: Optional[datetime] = Field(None, description="Order expiry time")
    
    # Client extensions
    client_extensions: Optional[ClientExtensions] = Field(None, description="Client extensions")
    
    def to_order(self) -> Order:
        """Convert request to Order model."""
        return Order(
            account_id=self.account_id,
            instrument=self.instrument,
            units=self.units,
            side=self.side,
            type=self.type,
            requested_price=self.price,
            stop_price=self.stop_price,
            stop_loss=self.stop_loss,
            take_profit=self.take_profit,
            time_in_force=self.time_in_force,
            expiry_time=self.expiry_time,
            client_extensions=self.client_extensions,
        )


class OrderResult(BaseModel):
    """Order execution result."""
    order_id: UUID = Field(..., description="Order ID")
    client_order_id: Optional[str] = Field(None, description="Client order ID")
    oanda_order_id: Optional[str] = Field(None, description="OANDA order ID")
    result: ExecutionResult = Field(..., description="Execution result")
    status: OrderStatus = Field(..., description="Order status")
    
    # Execution details
    fill_price: Optional[Decimal] = Field(None, description="Fill price")
    fill_time: Optional[datetime] = Field(None, description="Fill time")
    execution_time_ms: Optional[int] = Field(None, description="Execution time in milliseconds")
    slippage: Optional[Decimal] = Field(None, description="Execution slippage")
    commission: Optional[Decimal] = Field(None, description="Commission paid")
    
    # Error information
    error_code: Optional[str] = Field(None, description="Error code if failed")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    
    # Additional information
    position_id: Optional[UUID] = Field(None, description="Associated position ID")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class PositionCloseRequest(BaseModel):
    """Position close request."""
    position_id: Optional[UUID] = Field(None, description="Position ID to close")
    instrument: Optional[str] = Field(None, description="Instrument to close (alternative to position_id)")
    units: Optional[Decimal] = Field(None, description="Units to close (None for all)")
    reason: Optional[str] = Field(None, description="Reason for closing")


class ExecutionMetrics(BaseModel):
    """Execution performance metrics."""
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Metric timestamp")
    metric_type: str = Field(..., description="Type of metric")
    instrument: Optional[str] = Field(None, description="Associated instrument")
    value: Decimal = Field(..., description="Metric value")
    unit: str = Field(..., description="Metric unit (ms, pips, etc.)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class RiskLevel(str, Enum):
    """Risk level enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskEventType(str, Enum):
    """Risk event type enumeration."""
    POSITION_SIZE_BREACH = "position_size_breach"
    LEVERAGE_LIMIT_EXCEEDED = "leverage_limit_exceeded"
    DAILY_LOSS_LIMIT = "daily_loss_limit"
    MARGIN_CALL_WARNING = "margin_call_warning"
    DRAWDOWN_LIMIT = "drawdown_limit"
    KILL_SWITCH_ACTIVATED = "kill_switch_activated"
    UNUSUAL_MARKET_CONDITIONS = "unusual_market_conditions"
    CORRELATION_RISK = "correlation_risk"
    CONCENTRATION_RISK = "concentration_risk"


class RiskAlert(BaseModel):
    """Risk alert model."""
    id: UUID = Field(default_factory=uuid.uuid4, description="Alert ID")
    account_id: str = Field(..., description="Account ID")
    event_type: RiskEventType = Field(..., description="Type of risk event")
    level: RiskLevel = Field(..., description="Risk level")
    message: str = Field(..., description="Alert message")
    current_value: Optional[Decimal] = Field(None, description="Current metric value")
    limit_value: Optional[Decimal] = Field(None, description="Risk limit value")
    percentage: Optional[float] = Field(None, description="Percentage of limit breached")
    instrument: Optional[str] = Field(None, description="Associated instrument")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Alert creation time")
    acknowledged: bool = Field(default=False, description="Whether alert was acknowledged")
    acknowledged_at: Optional[datetime] = Field(None, description="Acknowledgment time")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class RiskLimits(BaseModel):
    """Enhanced risk management limits."""
    # Position limits
    max_position_size: Optional[Decimal] = Field(None, description="Maximum position size")
    max_positions_per_instrument: Optional[int] = Field(None, description="Max positions per instrument")
    max_total_positions: Optional[int] = Field(None, description="Maximum total positions")
    
    # Leverage and margin limits
    max_leverage: Optional[Decimal] = Field(None, description="Maximum leverage")
    required_margin_ratio: Optional[Decimal] = Field(None, description="Required margin ratio")
    margin_call_threshold: Optional[Decimal] = Field(None, description="Margin call threshold")
    
    # Loss limits
    max_daily_loss: Optional[Decimal] = Field(None, description="Maximum daily loss")
    max_weekly_loss: Optional[Decimal] = Field(None, description="Maximum weekly loss")
    max_monthly_loss: Optional[Decimal] = Field(None, description="Maximum monthly loss")
    max_drawdown: Optional[Decimal] = Field(None, description="Maximum drawdown")
    
    # Risk exposure limits
    max_instrument_exposure: Optional[Decimal] = Field(None, description="Max exposure per instrument")
    max_currency_exposure: Optional[Decimal] = Field(None, description="Max exposure per currency")
    max_sector_exposure: Optional[Decimal] = Field(None, description="Max exposure per sector")
    
    # Time-based limits
    max_orders_per_minute: Optional[int] = Field(None, description="Max orders per minute")
    max_orders_per_hour: Optional[int] = Field(None, description="Max orders per hour")
    
    # Correlation limits
    max_correlation_exposure: Optional[Decimal] = Field(None, description="Max correlated position exposure")
    correlation_threshold: Optional[float] = Field(None, description="Correlation threshold for risk")
    
    # Warning thresholds (percentage of limit)
    warning_threshold: float = Field(default=0.8, description="Warning threshold as percentage")
    critical_threshold: float = Field(default=0.95, description="Critical threshold as percentage")
    
    # Emergency controls
    kill_switch_enabled: bool = Field(default=True, description="Whether kill switch is enabled")
    auto_close_on_limit: bool = Field(default=False, description="Auto-close positions on limit breach")
    
    @validator('warning_threshold', 'critical_threshold')
    def validate_thresholds(cls, v: float) -> float:
        if not 0 < v <= 1:
            raise ValueError("Thresholds must be between 0 and 1")
        return v


class AccountSummary(BaseModel):
    """Account summary information."""
    account_id: str = Field(..., description="Account ID")
    balance: Decimal = Field(..., description="Account balance")
    unrealized_pl: Decimal = Field(default=Decimal("0"), description="Total unrealized P&L")
    margin_used: Decimal = Field(default=Decimal("0"), description="Total margin used")
    margin_available: Decimal = Field(..., description="Available margin")
    open_positions: int = Field(default=0, description="Number of open positions")
    pending_orders: int = Field(default=0, description="Number of pending orders")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Last update time")


class RiskMetrics(BaseModel):
    """Comprehensive risk metrics."""
    account_id: str = Field(..., description="Account ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Metrics timestamp")
    
    # Leverage and margin metrics
    current_leverage: Decimal = Field(default=Decimal("0"), description="Current leverage ratio")
    margin_utilization: Decimal = Field(default=Decimal("0"), description="Margin utilization percentage")
    margin_available: Decimal = Field(default=Decimal("0"), description="Available margin")
    
    # Position metrics
    position_count: int = Field(default=0, description="Total open positions")
    total_exposure: Decimal = Field(default=Decimal("0"), description="Total notional exposure")
    largest_position: Decimal = Field(default=Decimal("0"), description="Largest position size")
    
    # P&L metrics
    daily_pl: Decimal = Field(default=Decimal("0"), description="Daily P&L")
    weekly_pl: Decimal = Field(default=Decimal("0"), description="Weekly P&L")
    monthly_pl: Decimal = Field(default=Decimal("0"), description="Monthly P&L")
    unrealized_pl: Decimal = Field(default=Decimal("0"), description="Unrealized P&L")
    max_drawdown: Decimal = Field(default=Decimal("0"), description="Current drawdown")
    
    # Risk scores
    overall_risk_score: float = Field(default=0.0, description="Overall risk score (0-100)")
    leverage_risk_score: float = Field(default=0.0, description="Leverage risk score")
    concentration_risk_score: float = Field(default=0.0, description="Concentration risk score")
    correlation_risk_score: float = Field(default=0.0, description="Correlation risk score")
    
    # Exposure by category
    currency_exposures: Dict[str, Decimal] = Field(default_factory=dict, description="Currency exposures")
    instrument_exposures: Dict[str, Decimal] = Field(default_factory=dict, description="Instrument exposures")
    
    # Trading activity
    orders_per_hour: int = Field(default=0, description="Orders per hour")
    orders_per_day: int = Field(default=0, description="Orders per day")
    
    # Market condition metrics
    volatility_exposure: Decimal = Field(default=Decimal("0"), description="Volatility-adjusted exposure")
    beta_weighted_exposure: Decimal = Field(default=Decimal("0"), description="Beta-weighted exposure")


class RiskConfiguration(BaseModel):
    """Risk management configuration."""
    account_id: str = Field(..., description="Account ID")
    name: str = Field(..., description="Configuration name")
    description: Optional[str] = Field(None, description="Configuration description")
    
    # Risk limits
    limits: RiskLimits = Field(..., description="Risk limits")
    
    # Monitoring settings
    monitoring_enabled: bool = Field(default=True, description="Enable risk monitoring")
    alert_frequency_minutes: int = Field(default=5, description="Alert check frequency in minutes")
    
    # Kill switch settings
    kill_switch_conditions: List[Dict[str, Any]] = Field(default_factory=list, description="Kill switch trigger conditions")
    auto_recovery_enabled: bool = Field(default=False, description="Enable automatic recovery")
    recovery_conditions: List[Dict[str, Any]] = Field(default_factory=list, description="Recovery conditions")
    
    # Notification settings
    notification_channels: List[str] = Field(default_factory=list, description="Notification channels")
    escalation_rules: List[Dict[str, Any]] = Field(default_factory=list, description="Alert escalation rules")
    
    # Time settings
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Configuration creation time")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update time")
    effective_from: datetime = Field(default_factory=datetime.utcnow, description="Effective from time")
    effective_until: Optional[datetime] = Field(None, description="Effective until time")
    
    # Status
    is_active: bool = Field(default=True, description="Whether configuration is active")
    version: int = Field(default=1, description="Configuration version")


class ValidationResult(BaseModel):
    """Enhanced order validation result."""
    is_valid: bool = Field(..., description="Whether validation passed")
    risk_score: float = Field(default=0.0, description="Risk score for this order (0-100)")
    confidence: float = Field(default=1.0, description="Validation confidence (0-1)")
    
    # Error details
    error_code: Optional[str] = Field(None, description="Error code if validation failed")
    error_message: Optional[str] = Field(None, description="Error message if validation failed")
    
    # Warnings
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    
    # Risk breakdown
    risk_factors: Dict[str, float] = Field(default_factory=dict, description="Individual risk factor scores")
    
    # Recommendations
    recommended_position_size: Optional[Decimal] = Field(None, description="Recommended position size")
    alternative_instruments: List[str] = Field(default_factory=list, description="Alternative instruments")
    
    # Timing
    validation_time_ms: Optional[float] = Field(None, description="Validation time in milliseconds")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Validation timestamp")


class RiskEvent(BaseModel):
    """Risk event for audit trail."""
    id: UUID = Field(default_factory=uuid.uuid4, description="Event ID")
    account_id: str = Field(..., description="Account ID")
    event_type: RiskEventType = Field(..., description="Event type")
    severity: RiskLevel = Field(..., description="Event severity")
    
    # Event details
    title: str = Field(..., description="Event title")
    description: str = Field(..., description="Event description")
    
    # Associated data
    order_id: Optional[UUID] = Field(None, description="Associated order ID")
    position_id: Optional[UUID] = Field(None, description="Associated position ID")
    instrument: Optional[str] = Field(None, description="Associated instrument")
    
    # Metrics at time of event
    trigger_value: Optional[Decimal] = Field(None, description="Value that triggered the event")
    limit_value: Optional[Decimal] = Field(None, description="Limit value")
    percentage_of_limit: Optional[float] = Field(None, description="Percentage of limit")
    
    # Actions taken
    actions_taken: List[str] = Field(default_factory=list, description="Actions taken in response")
    kill_switch_activated: bool = Field(default=False, description="Whether kill switch was activated")
    positions_closed: List[UUID] = Field(default_factory=list, description="Positions closed due to event")
    
    # Resolution
    resolved: bool = Field(default=False, description="Whether event is resolved")
    resolved_at: Optional[datetime] = Field(None, description="Resolution time")
    resolution_notes: Optional[str] = Field(None, description="Resolution notes")
    
    # Timing
    occurred_at: datetime = Field(default_factory=datetime.utcnow, description="Event occurrence time")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional event metadata")