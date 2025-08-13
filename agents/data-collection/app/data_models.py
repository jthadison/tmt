"""
Data models for comprehensive trade data collection.

This module implements the 50+ feature comprehensive trade record and related
data structures for pattern tracking, execution quality analysis, and data validation.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union, Any
from datetime import datetime
from decimal import Decimal
from enum import Enum


class TradeDirection(str, Enum):
    LONG = "long"
    SHORT = "short"


class TradeStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class MarketSession(str, Enum):
    ASIAN = "asian"
    LONDON = "london"
    NEWYORK = "newyork"
    OVERLAP = "overlap"


class MarketRegime(str, Enum):
    TRENDING = "trending"
    RANGING = "ranging"
    VOLATILE = "volatile"
    QUIET = "quiet"


class RejectionSource(str, Enum):
    RISK_MANAGEMENT = "risk_management"
    PERSONALITY = "personality"
    CORRELATION = "correlation"
    MANUAL = "manual"


class ValidationCategory(str, Enum):
    MISSING_DATA = "missing_data"
    INCONSISTENT_DATA = "inconsistent_data"
    ANOMALOUS_VALUES = "anomalous_values"
    TIMING_ISSUES = "timing_issues"


class ValidationSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class TradeDetails:
    """Core trade information."""
    symbol: str
    direction: TradeDirection
    size: Decimal
    entry_price: Decimal
    exit_price: Optional[Decimal] = None
    stop_loss: Decimal = field(default_factory=Decimal)
    take_profit: Decimal = field(default_factory=Decimal)
    status: TradeStatus = TradeStatus.OPEN
    duration: Optional[int] = None  # minutes
    pnl: Optional[Decimal] = None
    pnl_percentage: Optional[Decimal] = None


@dataclass
class SignalContext:
    """Signal generation context with 15+ features."""
    signal_id: str
    confidence: Decimal
    strength: Decimal
    pattern_type: str
    pattern_subtype: str
    signal_source: str
    previous_signals: int
    signal_cluster_size: int
    cross_confirmation: bool
    divergence_present: bool
    volume_confirmation: bool
    news_event_proximity: int  # minutes to next news
    technical_score: Decimal
    fundamental_score: Decimal
    sentiment_score: Decimal


@dataclass
class MarketConditions:
    """Market conditions with 20+ features."""
    atr14: Decimal
    volatility: Decimal
    volume: Decimal
    spread: Decimal
    liquidity: Decimal
    session: MarketSession
    day_of_week: int
    hour_of_day: int
    market_regime: MarketRegime
    vix_level: Optional[Decimal] = None
    correlation_environment: Decimal = field(default_factory=Decimal)  # 0-1
    seasonality: Decimal = field(default_factory=Decimal)
    economic_calendar_risk: Decimal = field(default_factory=Decimal)
    support_resistance_proximity: Decimal = field(default_factory=Decimal)
    fibonacci_level: Decimal = field(default_factory=Decimal)
    moving_average_alignment: Decimal = field(default_factory=Decimal)
    rsi_level: Decimal = field(default_factory=Decimal)
    macd_signal: Decimal = field(default_factory=Decimal)
    bollinger_position: Decimal = field(default_factory=Decimal)
    ichimoku_signal: Decimal = field(default_factory=Decimal)


@dataclass
class ExecutionQuality:
    """Execution quality metrics with 10+ features."""
    order_placement_time: datetime
    fill_time: Optional[datetime] = None
    execution_latency: int = 0  # milliseconds
    slippage: Decimal = field(default_factory=Decimal)  # pips
    slippage_percentage: Decimal = field(default_factory=Decimal)
    partial_fill_count: int = 0
    rejection_count: int = 0
    requote_count: int = 0
    market_impact: Decimal = field(default_factory=Decimal)
    liquidity_at_execution: Decimal = field(default_factory=Decimal)
    spread_at_execution: Decimal = field(default_factory=Decimal)
    price_improvement_opportunity: Decimal = field(default_factory=Decimal)


@dataclass
class PersonalityImpact:
    """Personality and variance impact tracking."""
    personality_id: str
    variance_applied: bool
    timing_variance: Decimal
    sizing_variance: Decimal
    level_variance: Decimal
    disagreement_factor: Decimal
    human_behavior_modifiers: List[str] = field(default_factory=list)


@dataclass
class Performance:
    """Performance tracking metrics."""
    expected_pnl: Decimal
    actual_pnl: Decimal
    performance_ratio: Decimal
    risk_adjusted_return: Decimal
    sharpe_contribution: Decimal
    max_drawdown_contribution: Decimal
    win_probability: Decimal
    actual_outcome: str  # 'win' or 'loss'
    exit_reason: str
    holding_period_return: Decimal


@dataclass
class LearningMetadata:
    """Learning-related metadata and validation."""
    data_quality: Decimal  # 0-1
    learning_eligible: bool
    anomaly_score: Decimal
    feature_completeness: Decimal
    validation_errors: List[str] = field(default_factory=list)
    learning_weight: Decimal = field(default=Decimal("1.0"))


@dataclass
class ComprehensiveTradeRecord:
    """Complete trade record with 50+ features."""
    # Core identification
    id: str
    account_id: str
    timestamp: datetime
    
    # Main data sections
    trade_details: TradeDetails
    signal_context: SignalContext
    market_conditions: MarketConditions
    execution_quality: ExecutionQuality
    personality_impact: PersonalityImpact
    performance: Performance
    learning_metadata: LearningMetadata
    
    # Audit trail
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class SuccessMetrics:
    """Statistical success metrics for patterns."""
    total_trades: int
    win_count: int
    loss_count: int
    win_rate: Decimal
    average_win: Decimal
    average_loss: Decimal
    profit_factor: Decimal
    expectancy: Decimal
    max_drawdown: Decimal
    sharpe_ratio: Decimal
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class PatternEvolution:
    """Pattern evolution tracking."""
    first_seen: datetime
    last_seen: datetime
    total_occurrences: int
    recent_trend: str  # 'improving', 'stable', 'declining'
    adaptation_required: bool


@dataclass
class PatternStatistics:
    """Statistical significance metrics."""
    sample_size: int
    confidence_interval: Decimal
    p_value: Decimal
    statistically_significant: bool
    minimum_sample_size: int


@dataclass
class PatternPerformance:
    """Pattern performance tracking with context breakdown."""
    pattern_id: str
    pattern_name: str
    
    # Success rates by various contexts
    success_rates: Dict[str, SuccessMetrics]  # overall, byTimeframe, etc.
    
    # Pattern evolution
    evolution: PatternEvolution
    
    # Statistical significance
    statistics: PatternStatistics


@dataclass
class SlippageAnalysis:
    """Detailed slippage analysis."""
    average_slippage: Decimal
    slippage_standard_deviation: Decimal
    slippage_distribution: Dict[str, int]  # histogram buckets
    positive_slippage: Decimal  # percentage
    negative_slippage: Decimal
    slippage_by_symbol: Dict[str, Decimal]
    slippage_by_session: Dict[str, Decimal]


@dataclass
class ExecutionTiming:
    """Execution timing metrics."""
    average_latency: Decimal
    latency_standard_deviation: Decimal
    latency_percentiles: Dict[str, Decimal]  # 50th, 90th, 99th
    timeout_rate: Decimal
    rejection_rate: Decimal
    requote_rate: Decimal


@dataclass
class FillQuality:
    """Fill quality metrics."""
    full_fill_rate: Decimal
    partial_fill_rate: Decimal
    average_fill_ratio: Decimal
    fill_time_distribution: Dict[str, int]


@dataclass
class MarketImpact:
    """Market impact analysis."""
    average_impact: Decimal
    impact_by_size: Dict[str, Decimal]
    impact_by_liquidity: Dict[str, Decimal]
    impact_recovery_time: Decimal


@dataclass
class ExecutionQualityMetrics:
    """Comprehensive execution quality metrics."""
    timeframe: Dict[str, datetime]  # start, end
    slippage: SlippageAnalysis
    timing: ExecutionTiming
    fill_quality: FillQuality
    market_impact: MarketImpact


@dataclass
class RejectionInfo:
    """Signal rejection information."""
    rejection_reason: str
    rejection_source: RejectionSource
    rejection_score: Decimal  # strength of rejection
    alternative_action: str


@dataclass
class SignalQuality:
    """Quality metrics for signals."""
    original_confidence: Decimal
    strength_score: Decimal
    pattern_clarity: Decimal
    market_support_score: Decimal
    cross_validation_score: Decimal


@dataclass
class CounterfactualAnalysis:
    """Counterfactual analysis of rejected signals."""
    simulated_outcome: str  # 'win', 'loss', 'unknown'
    simulated_pnl: Decimal
    rejection_correctness: str  # 'correct_rejection', 'false_positive', 'uncertain'
    learning_value: Decimal  # how much this teaches us


@dataclass
class PatternImpact:
    """Impact on pattern recognition."""
    pattern_type: str
    pattern_reliability: Decimal
    suggested_adjustment: str
    pattern_frequency: Decimal


@dataclass
class FalseSignalAnalysis:
    """Analysis of rejected/false signals."""
    rejected_signal_id: str
    timestamp: datetime
    rejection_info: RejectionInfo
    signal_quality: SignalQuality
    counterfactual: CounterfactualAnalysis
    pattern_impact: PatternImpact


@dataclass
class ValidationIssue:
    """Individual validation issue."""
    category: ValidationCategory
    severity: ValidationSeverity
    description: str
    affected_fields: List[str]
    suggested_fix: str


@dataclass
class ValidationResults:
    """Validation scoring results."""
    passed: bool
    quality_score: Decimal  # 0-1
    completeness_score: Decimal
    consistency_score: Decimal
    anomaly_score: Decimal


@dataclass
class ValidationRecommendations:
    """Recommendations based on validation."""
    use_for_learning: bool
    quarantine: bool
    requires_review: bool
    confidence_reduction: Decimal


@dataclass
class DataValidationResult:
    """Complete data validation results."""
    record_id: str
    timestamp: datetime
    validation: ValidationResults
    issues: List[ValidationIssue] = field(default_factory=list)
    recommendations: Optional[ValidationRecommendations] = None


@dataclass
class TradeEvent:
    """Event data structure for pipeline processing."""
    trade_id: str
    account_id: str
    event_type: str
    timestamp: datetime
    event_data: Dict[str, Any]
    market_data: Dict[str, Any] = field(default_factory=dict)
    signal_data: Dict[str, Any] = field(default_factory=dict)
    execution_data: Dict[str, Any] = field(default_factory=dict)