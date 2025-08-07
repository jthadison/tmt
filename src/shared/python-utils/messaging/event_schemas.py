"""
Event Schema Definitions for Inter-Agent Communication

Defines standardized event schemas for all agent communication types with:
- Consistent message format with correlation IDs
- Type safety with Pydantic validation
- Financial-grade data integrity
- Distributed tracing support
"""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Dict, Any, Optional, List
from uuid import uuid4
from pydantic import BaseModel, Field, validator


class EventType(str, Enum):
    """Standardized event types for agent communication"""
    
    # Market Analysis Events
    TRADING_SIGNAL_GENERATED = "trading.signals.generated"
    MARKET_CONDITION_DETECTED = "trading.market.condition.detected"
    PATTERN_IDENTIFIED = "trading.patterns.identified"
    
    # Risk Management Events
    RISK_PARAMETERS_UPDATED = "risk.parameters.updated"
    POSITION_SIZING_CALCULATED = "risk.position.sizing.calculated"
    RISK_LIMIT_BREACHED = "risk.limits.breached"
    
    # Circuit Breaker Events
    BREAKER_AGENT_TRIGGERED = "breaker.agent.triggered"
    BREAKER_ACCOUNT_TRIGGERED = "breaker.account.triggered"
    BREAKER_SYSTEM_EMERGENCY = "breaker.system.emergency"
    HEALTH_CHECK_FAILED = "breaker.health.check.failed"
    
    # Personality Engine Events
    PERSONALITY_VARIANCE_APPLIED = "personality.variance.applied"
    CORRELATION_DETECTED = "personality.correlation.detected"
    PROFILE_SWITCHED = "personality.profile.switched"
    
    # Execution Engine Events
    ORDER_PLACED = "execution.order.placed"
    ORDER_FILLED = "execution.order.filled"
    ORDER_REJECTED = "execution.order.rejected"
    POSITION_CLOSED = "execution.position.closed"
    
    # Learning Agent Events
    LEARNING_MODEL_UPDATED = "learning.model.updated"
    PERFORMANCE_ANALYZED = "learning.performance.analyzed"
    ADAPTATION_APPLIED = "learning.adaptation.applied"


class Priority(str, Enum):
    """Message priority levels for processing order"""
    
    CRITICAL = "critical"    # Emergency stops, system failures
    HIGH = "high"           # Trading signals, risk breaches
    NORMAL = "normal"       # Regular updates, monitoring
    LOW = "low"            # Analytics, learning updates


class BaseEvent(BaseModel):
    """
    Base event schema for all agent communication.
    
    Provides standard fields required for distributed tracing,
    message deduplication, and system monitoring.
    """
    
    # Message identification and tracing
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    correlation_id: str = Field(...)
    causation_id: Optional[str] = Field(None)
    
    # Event metadata
    event_type: EventType = Field(...)
    source_agent: str = Field(...)
    target_agent: Optional[str] = Field(None)  # None for broadcast events
    
    # Timing information
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = Field(None)
    
    # Message handling
    priority: Priority = Field(default=Priority.NORMAL)
    retry_count: int = Field(default=0, ge=0)
    max_retries: int = Field(default=3, ge=0)
    
    # Event payload
    payload: Dict[str, Any] = Field(...)
    
    # System context
    environment: str = Field(default="development")
    version: str = Field(default="1.0")
    
    @validator('timestamp', pre=True, always=True)
    def ensure_utc_timestamp(cls, v):
        """Ensure all timestamps are UTC"""
        if isinstance(v, datetime):
            if v.tzinfo is None:
                return v.replace(tzinfo=timezone.utc)
            return v.astimezone(timezone.utc)
        return v
    
    @validator('correlation_id')
    def validate_correlation_id(cls, v):
        """Ensure correlation ID is not empty"""
        if not v or not v.strip():
            raise ValueError("correlation_id cannot be empty")
        return v.strip()
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: str(v)
        }


class TradingSignalEvent(BaseEvent):
    """
    Trading signal generation events from Market Analysis Agent.
    
    Contains Wyckoff pattern detection and volume price analysis results
    for risk assessment and position sizing.
    """
    
    event_type: EventType = Field(default=EventType.TRADING_SIGNAL_GENERATED, const=True)
    
    class PayloadSchema(BaseModel):
        symbol: str = Field(..., min_length=1, max_length=20)
        signal_type: str = Field(...)  # "BUY", "SELL", "HOLD"
        confidence: float = Field(..., ge=0.0, le=1.0)
        
        # Wyckoff analysis
        wyckoff_phase: str = Field(...)  # "Accumulation", "Distribution", etc.
        volume_confirmation: bool = Field(...)
        price_action_strength: float = Field(..., ge=0.0, le=1.0)
        
        # Market conditions
        market_structure: str = Field(...)  # "Bullish", "Bearish", "Sideways"
        volatility_level: str = Field(...)  # "Low", "Medium", "High"
        
        # Technical levels
        entry_price: Optional[Decimal] = Field(None)
        stop_loss: Optional[Decimal] = Field(None)
        take_profit: Optional[Decimal] = Field(None)
        
        # Metadata
        analysis_duration_ms: int = Field(..., ge=0)
        data_points_analyzed: int = Field(..., ge=0)
    
    def __init__(self, **data):
        if 'payload' in data:
            # Validate payload against schema
            TradingSignalEvent.PayloadSchema(**data['payload'])
        super().__init__(**data)


class RiskParameterEvent(BaseEvent):
    """
    Risk parameter updates from Adaptive Risk Intelligence Agent (ARIA).
    
    Contains dynamic position sizing and risk management parameter updates
    based on market conditions and performance analysis.
    """
    
    event_type: EventType = Field(default=EventType.RISK_PARAMETERS_UPDATED, const=True)
    
    class PayloadSchema(BaseModel):
        account_id: str = Field(..., min_length=1)
        
        # Position sizing parameters
        max_position_size: Decimal = Field(..., gt=0)
        risk_per_trade: Decimal = Field(..., gt=0, le=0.1)  # Max 10% risk per trade
        max_daily_loss: Decimal = Field(..., gt=0, le=0.05)  # Max 5% daily loss
        
        # Dynamic adjustments
        volatility_adjustment: float = Field(..., ge=0.1, le=2.0)
        correlation_adjustment: float = Field(..., ge=0.1, le=2.0)
        drawdown_adjustment: float = Field(..., ge=0.1, le=2.0)
        
        # Market condition adaptations
        market_regime: str = Field(...)  # "Trending", "Ranging", "Volatile"
        regime_confidence: float = Field(..., ge=0.0, le=1.0)
        
        # Performance metrics
        recent_win_rate: float = Field(..., ge=0.0, le=1.0)
        recent_profit_factor: float = Field(..., ge=0.0)
        current_drawdown: float = Field(..., ge=0.0)
        
        # Update metadata
        calculation_duration_ms: int = Field(..., ge=0)
        parameters_changed: List[str] = Field(...)
    
    def __init__(self, **data):
        if 'payload' in data:
            RiskParameterEvent.PayloadSchema(**data['payload'])
        super().__init__(**data)


class CircuitBreakerEvent(BaseEvent):
    """
    Circuit breaker activation events for emergency stops and health monitoring.
    
    Critical safety events that require immediate attention and may halt
    trading operations at agent, account, or system levels.
    """
    
    priority: Priority = Field(default=Priority.CRITICAL, const=True)
    
    class PayloadSchema(BaseModel):
        breaker_level: str = Field(...)  # "agent", "account", "system"
        breaker_state: str = Field(...)  # "triggered", "recovering", "reset"
        
        # Trigger information
        trigger_reason: str = Field(...)
        trigger_details: Dict[str, Any] = Field(...)
        affected_accounts: List[str] = Field(default_factory=list)
        
        # Health metrics
        current_health_score: float = Field(..., ge=0.0, le=1.0)
        health_trend: str = Field(...)  # "improving", "degrading", "stable"
        
        # Impact assessment
        positions_affected: int = Field(default=0, ge=0)
        estimated_impact: Optional[Decimal] = Field(None)
        recovery_eta: Optional[datetime] = Field(None)
        
        # Response actions
        actions_taken: List[str] = Field(...)
        manual_intervention_required: bool = Field(...)
        
        # Detection metadata
        detection_latency_ms: int = Field(..., ge=0)
        response_latency_ms: Optional[int] = Field(None)
    
    def __init__(self, **data):
        if 'payload' in data:
            CircuitBreakerEvent.PayloadSchema(**data['payload'])
        super().__init__(**data)


class PersonalityVarianceEvent(BaseEvent):
    """
    Personality engine variance application events.
    
    Documents execution variance and anti-correlation measures applied
    to trading behavior to avoid AI detection patterns.
    """
    
    event_type: EventType = Field(default=EventType.PERSONALITY_VARIANCE_APPLIED, const=True)
    
    class PayloadSchema(BaseModel):
        account_id: str = Field(..., min_length=1)
        personality_profile: str = Field(...)
        
        # Variance parameters applied
        timing_variance: float = Field(..., ge=0.0, le=1.0)
        size_variance: float = Field(..., ge=0.0, le=0.2)  # Max 20% size variance
        entry_variance: float = Field(..., ge=0.0, le=0.1)  # Max 10% entry variance
        
        # Anti-correlation measures
        correlation_score: float = Field(..., ge=0.0, le=1.0)
        diversification_applied: bool = Field(...)
        behavioral_randomization: Dict[str, Any] = Field(...)
        
        # Effectiveness tracking
        variance_effectiveness: Optional[float] = Field(None, ge=0.0, le=1.0)
        pattern_similarity: float = Field(..., ge=0.0, le=1.0)
        
        # Application metadata
        variance_calculation_ms: int = Field(..., ge=0)
        variance_history: List[Dict[str, Any]] = Field(default_factory=list)
    
    def __init__(self, **data):
        if 'payload' in data:
            PersonalityVarianceEvent.PayloadSchema(**data['payload'])
        super().__init__(**data)


class ExecutionEvent(BaseEvent):
    """
    Trade execution events from the high-performance execution engine.
    
    Documents order placement, fills, and position management with
    sub-100ms execution tracking for performance monitoring.
    """
    
    priority: Priority = Field(default=Priority.HIGH)
    
    class PayloadSchema(BaseModel):
        account_id: str = Field(..., min_length=1)
        order_id: str = Field(..., min_length=1)
        
        # Order details
        symbol: str = Field(..., min_length=1, max_length=20)
        order_type: str = Field(...)  # "MARKET", "LIMIT", "STOP"
        side: str = Field(...)  # "BUY", "SELL"
        quantity: Decimal = Field(..., gt=0)
        price: Optional[Decimal] = Field(None)
        
        # Execution details
        execution_status: str = Field(...)  # "PENDING", "FILLED", "REJECTED", "CANCELLED"
        fill_price: Optional[Decimal] = Field(None)
        fill_quantity: Optional[Decimal] = Field(None)
        remaining_quantity: Optional[Decimal] = Field(None)
        
        # Timing information
        order_received_at: datetime = Field(...)
        order_sent_at: Optional[datetime] = Field(None)
        fill_received_at: Optional[datetime] = Field(None)
        
        # Performance metrics
        signal_to_execution_ms: Optional[int] = Field(None)
        execution_latency_ms: Optional[int] = Field(None)
        slippage: Optional[Decimal] = Field(None)
        
        # MetaTrader integration
        mt_platform: str = Field(...)  # "MT4", "MT5"
        mt_account: str = Field(...)
        mt_order_id: Optional[str] = Field(None)
        
        # Error information
        rejection_reason: Optional[str] = Field(None)
        error_code: Optional[str] = Field(None)
        error_message: Optional[str] = Field(None)
    
    def __init__(self, **data):
        if 'payload' in data:
            ExecutionEvent.PayloadSchema(**data['payload'])
        super().__init__(**data)


# Topic mapping for event routing
EVENT_TOPIC_MAPPING = {
    EventType.TRADING_SIGNAL_GENERATED: "trading-signals",
    EventType.MARKET_CONDITION_DETECTED: "trading-signals", 
    EventType.PATTERN_IDENTIFIED: "trading-signals",
    
    EventType.RISK_PARAMETERS_UPDATED: "risk-management",
    EventType.POSITION_SIZING_CALCULATED: "risk-management",
    EventType.RISK_LIMIT_BREACHED: "risk-management",
    
    EventType.BREAKER_AGENT_TRIGGERED: "circuit-breaker",
    EventType.BREAKER_ACCOUNT_TRIGGERED: "circuit-breaker", 
    EventType.BREAKER_SYSTEM_EMERGENCY: "circuit-breaker",
    EventType.HEALTH_CHECK_FAILED: "circuit-breaker",
    
    EventType.PERSONALITY_VARIANCE_APPLIED: "personality-engine",
    EventType.CORRELATION_DETECTED: "personality-engine",
    EventType.PROFILE_SWITCHED: "personality-engine",
    
    EventType.ORDER_PLACED: "execution-engine",
    EventType.ORDER_FILLED: "execution-engine",
    EventType.ORDER_REJECTED: "execution-engine",
    EventType.POSITION_CLOSED: "execution-engine",
    
    EventType.LEARNING_MODEL_UPDATED: "learning-agent",
    EventType.PERFORMANCE_ANALYZED: "learning-agent",
    EventType.ADAPTATION_APPLIED: "learning-agent"
}

# Dead letter queue topic mapping
DLQ_TOPIC_MAPPING = {
    topic: f"{topic}-dlq" for topic in EVENT_TOPIC_MAPPING.values()
}


def get_topic_for_event(event_type: EventType) -> str:
    """Get Kafka topic name for an event type"""
    return EVENT_TOPIC_MAPPING.get(event_type, "unknown-events")


def get_dlq_topic_for_event(event_type: EventType) -> str:
    """Get dead letter queue topic name for an event type"""
    base_topic = get_topic_for_event(event_type)
    return DLQ_TOPIC_MAPPING.get(base_topic, f"{base_topic}-dlq")