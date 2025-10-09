"""
Market Data Models for Historical Data Storage
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    DateTime,
    Index,
    Boolean,
    Text,
    BigInteger,
)
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel, Field

Base = declarative_base()


class MarketCandle(Base):
    """
    Historical OHLCV market data stored in TimescaleDB

    This table uses TimescaleDB's time-series optimization for efficient
    storage and querying of historical market data.
    """

    __tablename__ = "market_candles"

    # Primary key and partitioning
    # Use Integer for SQLite compatibility with autoincrement (maps to BigInteger in Postgres)
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    instrument = Column(String(20), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False, default="H1")

    # OHLCV data
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False, default=0)

    # Metadata
    complete = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Composite indexes for efficient queries
    __table_args__ = (
        Index("idx_candles_instrument_time", "instrument", "timestamp"),
        Index("idx_candles_timeframe_time", "timeframe", "timestamp"),
    )


class TradeExecution(Base):
    """
    Historical trade execution records from production system

    Stores all executed trades with full execution details for backtesting
    validation and slippage modeling.
    """

    __tablename__ = "trade_executions"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_id = Column(String(50), nullable=False, unique=True, index=True)

    # Trade details
    instrument = Column(String(20), nullable=False, index=True)
    side = Column(String(10), nullable=False)  # "long" or "short"
    entry_time = Column(DateTime(timezone=True), nullable=False, index=True)
    exit_time = Column(DateTime(timezone=True), nullable=True, index=True)

    # Prices and sizing
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    units = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)

    # Execution quality
    entry_slippage = Column(Float, nullable=True)  # Pips
    exit_slippage = Column(Float, nullable=True)  # Pips

    # Performance
    pnl = Column(Float, nullable=True)
    pnl_pips = Column(Float, nullable=True)

    # Signal reference
    signal_id = Column(String(50), nullable=True, index=True)
    signal_confidence = Column(Float, nullable=True)

    # Account reference
    account_id = Column(String(50), nullable=False, index=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_executions_instrument_time", "instrument", "entry_time"),
        Index("idx_executions_account_time", "account_id", "entry_time"),
    )


class TradingSignal(Base):
    """
    Historical trading signals (both executed and rejected)

    Stores all generated signals to analyze signal quality and
    rejection reasons for backtesting improvement.
    """

    __tablename__ = "trading_signals"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    signal_id = Column(String(50), nullable=False, unique=True, index=True)

    # Signal details
    instrument = Column(String(20), nullable=False, index=True)
    side = Column(String(10), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)

    # Signal parameters
    entry_price = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False)
    take_profit = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    risk_reward_ratio = Column(Float, nullable=False)

    # Execution status
    executed = Column(Boolean, nullable=False, default=False, index=True)
    rejection_reason = Column(String(200), nullable=True)

    # Pattern detection details
    pattern_type = Column(String(50), nullable=True)
    vpa_score = Column(Float, nullable=True)
    wyckoff_phase = Column(String(50), nullable=True)

    # Session info
    trading_session = Column(String(20), nullable=True)  # Tokyo, London, NY, etc.

    # Metadata
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_signals_instrument_time", "instrument", "timestamp"),
        Index("idx_signals_executed_time", "executed", "timestamp"),
    )


# Pydantic schemas for API requests/responses

class MarketCandleSchema(BaseModel):
    """Market candle data schema"""

    timestamp: datetime
    instrument: str
    timeframe: str = "H1"
    open: float
    high: float
    low: float
    close: float
    volume: int = 0
    complete: bool = True

    class Config:
        from_attributes = True


class TradeExecutionSchema(BaseModel):
    """Trade execution data schema"""

    trade_id: str
    instrument: str
    side: str
    entry_time: datetime
    exit_time: Optional[datetime] = None
    entry_price: float
    exit_price: Optional[float] = None
    units: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    entry_slippage: Optional[float] = None
    exit_slippage: Optional[float] = None
    pnl: Optional[float] = None
    pnl_pips: Optional[float] = None
    signal_id: Optional[str] = None
    signal_confidence: Optional[float] = None
    account_id: str

    class Config:
        from_attributes = True


class TradingSignalSchema(BaseModel):
    """Trading signal data schema"""

    signal_id: str
    instrument: str
    side: str
    timestamp: datetime
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float
    risk_reward_ratio: float
    executed: bool = False
    rejection_reason: Optional[str] = None
    pattern_type: Optional[str] = None
    vpa_score: Optional[float] = None
    wyckoff_phase: Optional[str] = None
    trading_session: Optional[str] = None

    class Config:
        from_attributes = True


class DataQualityReport(BaseModel):
    """Data quality validation report"""

    instrument: str
    start_date: datetime
    end_date: datetime
    total_candles: int
    expected_candles: int
    missing_candles: int
    gaps_detected: int
    outliers_detected: int
    completeness_score: float = Field(ge=0.0)  # Can exceed 1.0 if more data than expected
    quality_score: float = Field(ge=0.0, le=1.0)
    issues: list[str] = []

    class Config:
        from_attributes = True
