"""
Data models for the Decision Disagreement System.
"""
from datetime import datetime
from typing import Dict, List, Optional, Literal
from pydantic import BaseModel, Field
from enum import Enum


class DecisionType(str, Enum):
    TAKE = "take"
    SKIP = "skip"
    MODIFY = "modify"
    DELAY = "delay"


class SignalDirection(str, Enum):
    LONG = "long"
    SHORT = "short"


class AlertSeverity(str, Enum):
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class OriginalSignal(BaseModel):
    """Original trading signal before disagreement processing."""
    symbol: str
    direction: SignalDirection
    strength: float = Field(ge=0.0, le=1.0, description="Signal confidence 0-1")
    price: float = Field(gt=0, description="Entry price")
    stop_loss: float = Field(gt=0, description="Stop loss price")
    take_profit: float = Field(gt=0, description="Take profit price")


class SignalModifications(BaseModel):
    """Modifications applied to original signal."""
    direction: Optional[SignalDirection] = None
    size: Optional[float] = Field(None, gt=0)
    entry_price: Optional[float] = Field(None, gt=0)
    stop_loss: Optional[float] = Field(None, gt=0)
    take_profit: Optional[float] = Field(None, gt=0)
    timing: Optional[float] = Field(None, ge=0, description="Delay in seconds")


class RiskAssessment(BaseModel):
    """Risk assessment for an account decision."""
    personal_risk_level: float = Field(ge=0.0, le=1.0)
    market_risk_level: float = Field(ge=0.0, le=1.0)
    portfolio_risk_level: float = Field(ge=0.0, le=1.0)
    combined_risk_level: float = Field(ge=0.0, le=1.0)
    risk_threshold: float = Field(ge=0.0, le=1.0, description="Personal risk threshold")


class PersonalityFactors(BaseModel):
    """Personality factors affecting trading decisions."""
    greed_factor: float = Field(ge=0.0, le=1.0, description="Affects take profit")
    fear_factor: float = Field(ge=0.0, le=1.0, description="Affects stop loss")
    impatience_level: float = Field(ge=0.0, le=1.0, description="Affects timing")
    conformity_level: float = Field(ge=0.0, le=1.0, description="Likelihood to follow crowd")
    contrarian: bool = Field(description="Tendency to go against consensus")


class AccountDecision(BaseModel):
    """Individual account's decision on a signal."""
    account_id: str
    personality_id: str
    
    # Decision details
    decision: DecisionType
    reasoning: str = Field(description="Human-readable explanation")
    
    # Modifications if decision = 'modify'
    modifications: SignalModifications = Field(default_factory=SignalModifications)
    
    # Risk and personality analysis
    risk_assessment: RiskAssessment
    personality_factors: PersonalityFactors
    
    processed_at: datetime = Field(default_factory=datetime.utcnow)
    executed_at: Optional[datetime] = None


class DisagreementMetrics(BaseModel):
    """Metrics about signal disagreement."""
    participation_rate: float = Field(ge=0.0, le=1.0, description="% of accounts that took signal")
    direction_consensus: float = Field(ge=0.0, le=1.0, description="% agreement on direction")
    timing_spread: float = Field(ge=0.0, description="Seconds between first and last entry")
    sizing_variation: float = Field(ge=0.0, description="Coefficient of variation in sizes")
    profit_target_spread: float = Field(ge=0.0, description="Range of take profit levels")


class CorrelationAdjustment(BaseModel):
    """Correlation adjustment applied to reduce correlation."""
    account_pair: str
    before_correlation: float
    target_correlation: float
    adjustment_type: str
    adjustment_description: str


class CorrelationImpact(BaseModel):
    """Impact of signal on account correlations."""
    before_signal: Dict[str, float] = Field(description="Account pair correlations before signal")
    after_signal: Dict[str, float] = Field(description="Updated correlations after signal")
    target_adjustments: List[CorrelationAdjustment] = Field(default_factory=list)


class SignalDisagreement(BaseModel):
    """Complete disagreement analysis for a signal."""
    signal_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Original signal
    original_signal: OriginalSignal
    
    # Account decisions
    account_decisions: List[AccountDecision] = Field(default_factory=list)
    
    # Disagreement analysis
    disagreement_metrics: DisagreementMetrics
    
    # Correlation impact
    correlation_impact: CorrelationImpact


class DecisionBiases(BaseModel):
    """Decision biases for a trading personality."""
    risk_aversion: float = Field(ge=0.0, le=1.0, description="Higher = more likely to skip")
    signal_skepticism: float = Field(ge=0.0, le=1.0, description="Tendency to question signals")
    crowd_following: float = Field(ge=0.0, le=1.0, description="Follow vs oppose majority")
    profit_taking: float = Field(ge=0.0, le=1.0, description="Greedy vs conservative")
    loss_avoidance: float = Field(ge=0.0, le=1.0, description="Tight vs loose stops")


class SituationalModifiers(BaseModel):
    """Situational factors affecting disagreement."""
    market_volatility: float = Field(ge=0.0, description="How volatility affects disagreement")
    news_events: float = Field(ge=0.0, description="News impact on decisions")
    time_of_day: Dict[str, float] = Field(default_factory=dict, description="Hour-specific disagreement rates")
    day_of_week: Dict[str, float] = Field(default_factory=dict, description="Day-specific patterns")


class CorrelationAwareness(BaseModel):
    """Correlation awareness settings for a personality."""
    monitor_correlation: bool = Field(description="Whether this personality monitors correlation")
    correlation_sensitivity: float = Field(ge=0.0, le=1.0, description="How much correlation affects decisions")
    anti_correlation_bias: float = Field(ge=0.0, le=1.0, description="Tendency to deliberately disagree")


class DisagreementProfile(BaseModel):
    """Profile defining how a personality handles disagreements."""
    personality_id: str
    
    # Base disagreement rate
    base_disagreement_rate: float = Field(ge=0.15, le=0.20, description="Base 15-20% disagreement rate")
    
    # Decision biases
    biases: DecisionBiases
    
    # Situational modifiers
    situational_modifiers: SituationalModifiers
    
    # Correlation awareness
    correlation_awareness: CorrelationAwareness


class CorrelationThresholds(BaseModel):
    """Correlation monitoring thresholds."""
    warning: float = Field(default=0.6)
    critical: float = Field(default=0.7)
    emergency: float = Field(default=0.8)


class CorrelationAlert(BaseModel):
    """Correlation alert when thresholds are exceeded."""
    account_pair: str
    correlation: float
    severity: AlertSeverity
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    recommended_action: str


class CorrelationDataPoint(BaseModel):
    """Historical correlation data point."""
    timestamp: datetime
    account_pair: str
    correlation: float
    signal_count: int = Field(description="Number of signals in this period")
    agreement_rate: float = Field(ge=0.0, le=1.0, description="How often they agreed")


class AccountPair(BaseModel):
    """Account pair for correlation monitoring."""
    account1_id: str
    account2_id: str
    pair_id: str = Field(description="account1_account2 identifier")


class CorrelationAdjustmentStrategy(BaseModel):
    """Strategy for adjusting high correlations."""
    name: str
    description: str
    trigger_threshold: float
    adjustment_strength: float = Field(ge=0.0, le=1.0)
    
    
class CorrelationMonitor(BaseModel):
    """Real-time correlation monitoring system."""
    account_pairs: List[AccountPair] = Field(default_factory=list)
    
    # Real-time tracking
    current_correlations: Dict[str, float] = Field(default_factory=dict, description="accountId1_accountId2 -> correlation")
    correlation_history: List[CorrelationDataPoint] = Field(default_factory=list)
    
    # Alert system
    alerts: List[CorrelationAlert] = Field(default_factory=list)
    thresholds: CorrelationThresholds = Field(default_factory=CorrelationThresholds)
    
    # Adjustment mechanisms
    adjustment_strategies: List[CorrelationAdjustmentStrategy] = Field(default_factory=list)
    
    last_update: datetime = Field(default_factory=datetime.utcnow)