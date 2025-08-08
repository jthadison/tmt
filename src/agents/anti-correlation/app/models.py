"""Data models for anti-correlation engine."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, DateTime, Numeric, Integer, Text, JSON, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class AdjustmentType(str, Enum):
    POSITION_REDUCTION = "position_reduction"
    POSITION_HEDGING = "position_hedging"
    POSITION_ROTATION = "position_rotation"
    TIMING_DELAY = "timing_delay"
    SIZE_VARIANCE = "size_variance"


class CorrelationSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class CorrelationMetric(Base):
    """SQLAlchemy model for correlation metrics."""
    __tablename__ = 'correlation_metrics'
    
    metric_id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    account_1_id = Column(PGUUID(as_uuid=True), nullable=False)
    account_2_id = Column(PGUUID(as_uuid=True), nullable=False)
    correlation_coefficient = Column(Numeric(5, 4), nullable=False)
    p_value = Column(Numeric(5, 4))
    time_window = Column(Integer, nullable=False)  # seconds
    calculation_time = Column(DateTime(timezone=True), default=datetime.utcnow)
    position_correlation = Column(Numeric(5, 4))
    timing_correlation = Column(Numeric(5, 4))
    size_correlation = Column(Numeric(5, 4))
    pnl_correlation = Column(Numeric(5, 4))
    
    __table_args__ = (
        Index('idx_correlation_accounts', 'account_1_id', 'account_2_id'),
        Index('idx_correlation_time', 'calculation_time'),
        Index('idx_correlation_coefficient', 'correlation_coefficient'),
    )


class CorrelationAdjustment(Base):
    """SQLAlchemy model for correlation adjustments."""
    __tablename__ = 'correlation_adjustments'
    
    adjustment_id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    account_id = Column(PGUUID(as_uuid=True), nullable=False)
    adjustment_type = Column(String(50), nullable=False)
    adjustment_value = Column(JSON, nullable=False)
    reason = Column(Text)
    correlation_before = Column(Numeric(5, 4))
    correlation_after = Column(Numeric(5, 4))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class CorrelationAlert(Base):
    """SQLAlchemy model for correlation alerts."""
    __tablename__ = 'correlation_alerts'
    
    alert_id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    account_1_id = Column(PGUUID(as_uuid=True), nullable=False)
    account_2_id = Column(PGUUID(as_uuid=True), nullable=False)
    correlation_coefficient = Column(Numeric(5, 4), nullable=False)
    severity = Column(String(20), nullable=False)
    alert_time = Column(DateTime(timezone=True), default=datetime.utcnow)
    resolved_time = Column(DateTime(timezone=True))
    resolution_action = Column(String(100))
    
    __table_args__ = (
        Index('idx_alert_accounts', 'account_1_id', 'account_2_id'),
        Index('idx_alert_time', 'alert_time'),
        Index('idx_alert_severity', 'severity'),
    )


class ExecutionDelay(Base):
    """SQLAlchemy model for execution delays."""
    __tablename__ = 'execution_delays'
    
    delay_id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    account_id = Column(PGUUID(as_uuid=True), nullable=False)
    original_signal_time = Column(DateTime(timezone=True), nullable=False)
    delayed_execution_time = Column(DateTime(timezone=True), nullable=False)
    delay_seconds = Column(Numeric(6, 3), nullable=False)
    delay_factors = Column(JSON)
    trade_symbol = Column(String(10))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


# Pydantic models for API requests/responses

class CorrelationMetricResponse(BaseModel):
    """Response model for correlation metrics."""
    metric_id: UUID
    account_1_id: UUID
    account_2_id: UUID
    correlation_coefficient: float
    p_value: Optional[float]
    time_window: int
    calculation_time: datetime
    position_correlation: Optional[float]
    timing_correlation: Optional[float]
    size_correlation: Optional[float]
    pnl_correlation: Optional[float]
    
    class Config:
        from_attributes = True


class CorrelationRequest(BaseModel):
    """Request model for correlation calculation."""
    account_ids: List[UUID] = Field(..., min_items=2)
    time_window: int = Field(default=3600, ge=300, le=86400)  # 5min to 1day
    include_components: bool = Field(default=True)


class AdjustmentRequest(BaseModel):
    """Request model for correlation adjustment."""
    account_id: UUID
    adjustment_type: AdjustmentType
    target_correlation: float = Field(..., ge=0.0, le=1.0)
    adjustment_params: Dict[str, Any] = Field(default_factory=dict)


class CorrelationMatrixResponse(BaseModel):
    """Response model for correlation matrix."""
    accounts: List[UUID]
    correlation_matrix: List[List[float]]
    calculation_time: datetime
    time_window: int
    summary_stats: Dict[str, float]


class AlertResponse(BaseModel):
    """Response model for correlation alerts."""
    alert_id: UUID
    account_1_id: UUID
    account_2_id: UUID
    correlation_coefficient: float
    severity: CorrelationSeverity
    alert_time: datetime
    resolved_time: Optional[datetime]
    resolution_action: Optional[str]
    
    class Config:
        from_attributes = True


class DailyCorrelationReport(BaseModel):
    """Model for daily correlation report."""
    report_date: datetime
    summary: Dict[str, Any]
    correlation_matrix: List[List[float]]
    account_ids: List[UUID]
    warnings: List[Dict[str, Any]]
    adjustments: Dict[str, int]
    recommendations: List[str]


class DelayCalculationRequest(BaseModel):
    """Request model for execution delay calculation."""
    account_id: UUID
    base_signal_time: datetime
    trade_symbol: str
    market_conditions: Optional[Dict[str, Any]] = None
    priority_level: int = Field(default=1, ge=1, le=5)  # 1=normal, 5=critical


class DelayResponse(BaseModel):
    """Response model for execution delay."""
    account_id: UUID
    original_signal_time: datetime
    delayed_execution_time: datetime
    delay_seconds: float
    delay_factors: Dict[str, float]
    reasoning: str


class SizeVarianceRequest(BaseModel):
    """Request model for position size variance."""
    account_id: UUID
    base_size: float
    symbol: str
    variance_range: tuple[float, float] = Field(default=(0.05, 0.15))


class SizeVarianceResponse(BaseModel):
    """Response model for position size variance."""
    account_id: UUID
    original_size: float
    adjusted_size: float
    variance_applied: float
    variance_percentage: float
    personality_factor: str


class PositionData(BaseModel):
    """Model for position data."""
    account_id: UUID
    symbol: str
    position_size: float
    entry_time: datetime
    entry_price: float
    current_price: Optional[float]
    unrealized_pnl: Optional[float]


class AccountCorrelationProfile(BaseModel):
    """Model for account correlation profile."""
    account_id: UUID
    personality_type: str
    risk_tolerance: float
    typical_delay_range: tuple[float, float]
    size_variance_preference: float
    correlation_history: List[float]
    adjustment_frequency: int