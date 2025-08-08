"""Data models for performance tracking system."""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from uuid import UUID, uuid4
from enum import Enum

from pydantic import BaseModel, Field
from sqlalchemy import Column, String, DateTime, Numeric, Integer, Boolean, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID as SQLAlchemyUUID

Base = declarative_base()


class PeriodType(str, Enum):
    """Performance tracking periods."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class TradeStatus(str, Enum):
    """Trade status types."""
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"


# SQLAlchemy Models

class TradePerformance(Base):
    """Individual trade performance tracking."""
    __tablename__ = "trade_performance"
    
    trade_id = Column(SQLAlchemyUUID(as_uuid=True), primary_key=True, default=uuid4)
    account_id = Column(SQLAlchemyUUID(as_uuid=True), nullable=False, index=True)
    symbol = Column(String(20), nullable=False)
    entry_time = Column(DateTime(timezone=True), nullable=False)
    exit_time = Column(DateTime(timezone=True), nullable=True)
    entry_price = Column(Numeric(10, 5), nullable=False)
    exit_price = Column(Numeric(10, 5), nullable=True)
    position_size = Column(Numeric(10, 4), nullable=False)
    pnl = Column(Numeric(12, 2), nullable=True)
    pnl_percentage = Column(Numeric(8, 4), nullable=True)
    commission = Column(Numeric(8, 2), default=0)
    swap = Column(Numeric(8, 2), default=0)
    trade_duration_seconds = Column(Integer, nullable=True)
    status = Column(String(20), default=TradeStatus.OPEN.value)
    
    __table_args__ = (
        Index('idx_performance_account', 'account_id'),
        Index('idx_performance_time', 'entry_time'),
        Index('idx_performance_symbol', 'symbol'),
    )


class PerformanceMetrics(Base):
    """Aggregated performance metrics by period."""
    __tablename__ = "performance_metrics"
    
    metric_id = Column(SQLAlchemyUUID(as_uuid=True), primary_key=True, default=uuid4)
    account_id = Column(SQLAlchemyUUID(as_uuid=True), nullable=False, index=True)
    period_type = Column(String(20), nullable=False)
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    total_trades = Column(Integer, nullable=False, default=0)
    winning_trades = Column(Integer, nullable=False, default=0)
    losing_trades = Column(Integer, nullable=False, default=0)
    win_rate = Column(Numeric(5, 2), nullable=True)
    profit_factor = Column(Numeric(8, 2), nullable=True)
    sharpe_ratio = Column(Numeric(8, 4), nullable=True)
    sortino_ratio = Column(Numeric(8, 4), nullable=True)
    calmar_ratio = Column(Numeric(8, 4), nullable=True)
    max_drawdown = Column(Numeric(8, 4), nullable=True)
    total_pnl = Column(Numeric(12, 2), nullable=False, default=0)
    average_win = Column(Numeric(10, 2), nullable=True)
    average_loss = Column(Numeric(10, 2), nullable=True)
    largest_win = Column(Numeric(10, 2), nullable=True)
    largest_loss = Column(Numeric(10, 2), nullable=True)
    
    __table_args__ = (
        Index('idx_metrics_account_period', 'account_id', 'period_type', 'period_start'),
    )


class PerformanceSnapshot(Base):
    """Point-in-time performance snapshots."""
    __tablename__ = "performance_snapshots"
    
    snapshot_id = Column(SQLAlchemyUUID(as_uuid=True), primary_key=True, default=uuid4)
    account_id = Column(SQLAlchemyUUID(as_uuid=True), nullable=False, index=True)
    snapshot_time = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    balance = Column(Numeric(12, 2), nullable=False)
    equity = Column(Numeric(12, 2), nullable=False)
    margin_used = Column(Numeric(12, 2), default=0)
    free_margin = Column(Numeric(12, 2), nullable=True)
    open_positions = Column(Integer, default=0)
    realized_pnl = Column(Numeric(10, 2), default=0)
    unrealized_pnl = Column(Numeric(10, 2), default=0)
    daily_pnl = Column(Numeric(10, 2), default=0)
    weekly_pnl = Column(Numeric(10, 2), default=0)
    monthly_pnl = Column(Numeric(10, 2), default=0)
    
    __table_args__ = (
        Index('idx_snapshot_account_time', 'account_id', 'snapshot_time'),
    )


class AccountRanking(Base):
    """Account performance rankings."""
    __tablename__ = "account_rankings"
    
    ranking_id = Column(SQLAlchemyUUID(as_uuid=True), primary_key=True, default=uuid4)
    account_id = Column(SQLAlchemyUUID(as_uuid=True), nullable=False, index=True)
    period_type = Column(String(20), nullable=False)
    period_start = Column(DateTime(timezone=True), nullable=False)
    ranking_score = Column(Numeric(10, 4), nullable=False)
    performance_rank = Column(Integer, nullable=False)
    total_accounts = Column(Integer, nullable=False)
    percentile = Column(Numeric(5, 2), nullable=False)
    
    __table_args__ = (
        Index('idx_ranking_period', 'period_type', 'period_start'),
    )


# Pydantic Models for API

class TradeData(BaseModel):
    """Trade data for P&L calculation."""
    trade_id: UUID
    account_id: UUID
    symbol: str
    entry_time: datetime
    exit_time: Optional[datetime] = None
    entry_price: Decimal
    exit_price: Optional[Decimal] = None
    position_size: Decimal
    commission: Decimal = Decimal('0')
    swap: Decimal = Decimal('0')
    status: TradeStatus = TradeStatus.OPEN


class PnLSnapshot(BaseModel):
    """Real-time P&L snapshot."""
    account_id: UUID
    timestamp: datetime
    balance: Decimal
    equity: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    total_pnl: Decimal
    daily_change: Decimal
    daily_change_percentage: Decimal
    open_positions: int


class PerformanceMetricsData(BaseModel):
    """Performance metrics data."""
    account_id: UUID
    period_type: PeriodType
    period_start: datetime
    period_end: datetime
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: Decimal
    profit_factor: Decimal
    sharpe_ratio: Optional[Decimal] = None
    sortino_ratio: Optional[Decimal] = None
    calmar_ratio: Optional[Decimal] = None
    max_drawdown: Decimal
    total_pnl: Decimal
    average_win: Decimal
    average_loss: Decimal
    largest_win: Decimal
    largest_loss: Decimal


class AccountComparison(BaseModel):
    """Account performance comparison."""
    account_id: UUID
    account_name: Optional[str] = None
    performance_rank: int
    total_accounts: int
    percentile: Decimal
    ranking_score: Decimal
    total_pnl: Decimal
    win_rate: Decimal
    profit_factor: Decimal
    sharpe_ratio: Optional[Decimal] = None
    max_drawdown: Decimal


class PerformanceReport(BaseModel):
    """Performance report structure."""
    account_id: UUID
    period_type: PeriodType
    period_start: datetime
    period_end: datetime
    summary: PerformanceMetricsData
    trade_breakdown: List[TradeData]
    equity_curve: List[tuple[datetime, Decimal]]
    top_trades: List[TradeData]
    worst_trades: List[TradeData]


class ExportRequest(BaseModel):
    """Export request parameters."""
    account_ids: List[UUID]
    start_date: datetime
    end_date: datetime
    export_format: str = Field(..., pattern="^(csv|json|pdf|xlsx)$")
    report_type: str = Field(..., pattern="^(trades|metrics|tax|prop_firm)$")
    include_details: bool = True


class MarketTick(BaseModel):
    """Market data tick for P&L updates."""
    symbol: str
    bid_price: Decimal
    ask_price: Decimal
    timestamp: datetime
    volume: Optional[int] = None


class PositionData(BaseModel):
    """Open position data."""
    position_id: UUID
    account_id: UUID
    symbol: str
    position_size: Decimal
    entry_price: Decimal
    current_price: Decimal
    unrealized_pnl: Decimal
    commission: Decimal = Decimal('0')
    swap: Decimal = Decimal('0')
    margin_used: Decimal = Decimal('0')


class WebSocketMessage(BaseModel):
    """WebSocket message structure."""
    channel: str
    action: str
    data: dict
    timestamp: datetime = Field(default_factory=datetime.utcnow)