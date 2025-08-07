"""
Pydantic Models for Circuit Breaker Agent

Defines all data models, request/response schemas, and validation logic
for the Circuit Breaker Agent.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator


class BreakerLevel(str, Enum):
    """Circuit breaker levels"""
    AGENT = "agent"
    ACCOUNT = "account" 
    SYSTEM = "system"


class BreakerState(str, Enum):
    """Circuit breaker states"""
    NORMAL = "normal"
    WARNING = "warning"
    TRIPPED = "tripped"
    HALF_OPEN = "half_open"


class TriggerReason(str, Enum):
    """Reasons for circuit breaker activation"""
    DAILY_DRAWDOWN = "daily_drawdown"
    MAX_DRAWDOWN = "max_drawdown"
    ERROR_RATE = "error_rate"
    RESPONSE_TIME = "response_time"
    VOLATILITY_SPIKE = "volatility_spike"
    GAP_DETECTION = "gap_detection"
    MANUAL_TRIGGER = "manual_trigger"
    SYSTEM_FAILURE = "system_failure"
    CONSECUTIVE_FAILURES = "consecutive_failures"


class BreakerStatus(BaseModel):
    """Circuit breaker status model"""
    
    level: BreakerLevel
    state: BreakerState
    triggered_at: Optional[datetime] = None
    reset_at: Optional[datetime] = None
    trigger_reason: Optional[TriggerReason] = None
    trigger_details: Dict[str, Any] = Field(default_factory=dict)
    failure_count: int = Field(default=0)
    success_count: int = Field(default=0)
    last_failure_at: Optional[datetime] = None
    recovery_timeout: Optional[datetime] = None
    
    class Config:
        use_enum_values = True


class SystemHealth(BaseModel):
    """System health metrics model"""
    
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    cpu_usage: float = Field(..., ge=0, le=100)
    memory_usage: float = Field(..., ge=0, le=100)
    disk_usage: float = Field(..., ge=0, le=100)
    error_rate: float = Field(..., ge=0, le=1)
    response_time: int = Field(..., ge=0, description="Response time in milliseconds")
    active_connections: int = Field(default=0, ge=0)
    
    @validator("response_time")
    def validate_response_time(cls, v):
        if v > 10000:  # 10 seconds
            raise ValueError("Response time seems unreasonably high")
        return v


class MarketConditions(BaseModel):
    """Market conditions assessment model"""
    
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    volatility: float = Field(..., ge=0)
    gap_detected: bool = Field(default=False)
    gap_size: Optional[float] = None
    correlation_breakdown: bool = Field(default=False)
    unusual_volume: bool = Field(default=False)
    circuit_breaker_triggered: bool = Field(default=False)


class AccountMetrics(BaseModel):
    """Account-specific metrics model"""
    
    account_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    daily_pnl: float = Field(default=0.0)
    daily_drawdown: float = Field(default=0.0, ge=0, le=1)
    max_drawdown: float = Field(default=0.0, ge=0, le=1)
    position_count: int = Field(default=0, ge=0)
    total_exposure: float = Field(default=0.0, ge=0)
    last_trade_time: Optional[datetime] = None


class EmergencyStopRequest(BaseModel):
    """Emergency stop request model"""
    
    level: BreakerLevel
    reason: TriggerReason
    details: Dict[str, Any] = Field(default_factory=dict)
    force: bool = Field(default=False, description="Force stop even if already tripped")
    correlation_id: str = Field(default_factory=lambda: str(uuid4()))
    requested_by: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EmergencyStopResponse(BaseModel):
    """Emergency stop response model"""
    
    success: bool
    level: BreakerLevel
    previous_state: BreakerState
    new_state: BreakerState
    positions_closed: int = Field(default=0)
    response_time_ms: int = Field(..., ge=0)
    correlation_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    message: str = Field(default="")
    errors: List[str] = Field(default_factory=list)


class BreakerStatusResponse(BaseModel):
    """Circuit breaker status response model"""
    
    agent_breakers: Dict[str, BreakerStatus] = Field(default_factory=dict)
    account_breakers: Dict[str, BreakerStatus] = Field(default_factory=dict) 
    system_breaker: BreakerStatus
    overall_status: str = Field(..., description="Overall system status")
    health_metrics: SystemHealth
    market_conditions: Optional[MarketConditions] = None
    correlation_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PositionCloseRequest(BaseModel):
    """Position closure request model"""
    
    account_id: Optional[str] = None
    position_ids: Optional[List[str]] = None
    close_all: bool = Field(default=False)
    emergency: bool = Field(default=True)
    timeout_seconds: int = Field(default=5, ge=1, le=60)
    correlation_id: str = Field(default_factory=lambda: str(uuid4()))


class PositionCloseResponse(BaseModel):
    """Position closure response model"""
    
    success: bool
    positions_closed: int = Field(default=0)
    positions_failed: int = Field(default=0)
    failed_position_ids: List[str] = Field(default_factory=list)
    response_time_ms: int = Field(..., ge=0)
    correlation_id: str
    errors: List[str] = Field(default_factory=list)


class WebSocketMessage(BaseModel):
    """WebSocket message model"""
    
    type: str = Field(..., description="Message type")
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: str = Field(default_factory=lambda: str(uuid4()))


class KafkaEvent(BaseModel):
    """Kafka event model"""
    
    event_type: str
    event_data: Dict[str, Any]
    correlation_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_service: str = Field(default="circuit-breaker-agent")
    event_version: str = Field(default="1.0")


class StandardAPIResponse(BaseModel):
    """Standard API response wrapper"""
    
    data: Optional[Any] = None
    error: Optional[str] = None
    correlation_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        arbitrary_types_allowed = True