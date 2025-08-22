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
from typing import Any, Dict, Optional, Union
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


class RiskLimits(BaseModel):
    """Risk management limits."""
    max_position_size: Optional[Decimal] = Field(None, description="Maximum position size")
    max_positions_per_instrument: Optional[int] = Field(None, description="Max positions per instrument")
    max_leverage: Optional[Decimal] = Field(None, description="Maximum leverage")
    max_daily_loss: Optional[Decimal] = Field(None, description="Maximum daily loss")
    max_drawdown: Optional[Decimal] = Field(None, description="Maximum drawdown")
    required_margin_ratio: Optional[Decimal] = Field(None, description="Required margin ratio")


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