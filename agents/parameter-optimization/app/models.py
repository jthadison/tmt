"""
Data models for parameter optimization system
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from enum import Enum
import uuid


class ParameterCategory(Enum):
    """Parameter category types"""
    POSITION_SIZING = "position_sizing"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    SIGNAL_FILTERING = "signal_filtering"


class OptimizationStatus(Enum):
    """Optimization process status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLBACK_REQUIRED = "rollback_required"


class MarketRegime(Enum):
    """Market regime types"""
    TRENDING = "trending"
    RANGING = "ranging"
    VOLATILE = "volatile"
    LOW_VOLATILITY = "low_volatility"
    UNKNOWN = "unknown"


class ImplementationMethod(Enum):
    """Parameter change implementation methods"""
    IMMEDIATE = "immediate"
    GRADUAL = "gradual"
    AB_TEST = "ab_test"


class RollbackSeverity(Enum):
    """Rollback condition severity levels"""
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class PerformanceMetrics:
    """Performance metrics for optimization analysis"""
    timestamp: datetime
    account_id: str
    
    # Core performance metrics
    sharpe_ratio: float
    calmar_ratio: float
    sortino_ratio: float
    profit_factor: float
    win_rate: float
    max_drawdown: float
    current_drawdown: float
    
    # Trade statistics
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    expectancy: float
    
    # Risk metrics
    volatility: float
    var_95: float  # Value at Risk 95%
    expected_shortfall: float
    
    # Period information
    period_start: datetime
    period_end: datetime
    market_regime: MarketRegime = MarketRegime.UNKNOWN


@dataclass
class RiskParameterSet:
    """Complete set of risk parameters for an account"""
    id: str
    version: str
    account_id: str
    effective_date: datetime
    
    # Position sizing parameters
    position_sizing: Dict[str, Union[float, bool]] = field(default_factory=lambda: {
        "base_risk_per_trade": 0.01,  # 1% default
        "kelly_multiplier": 0.25,     # Quarter Kelly
        "max_position_size": 0.03,    # 3% maximum
        "drawdown_reduction_factor": 0.5,  # Reduce size in drawdown
        "confidence_scaling": True,    # Scale by signal confidence
        "volatility_adjustment": True  # Adjust for market volatility
    })
    
    # Stop loss parameters
    stop_loss: Dict[str, Union[float, Dict[str, float]]] = field(default_factory=lambda: {
        "atr_multiplier": 2.0,        # 2x ATR default
        "min_stop_distance": 10.0,    # 10 pips minimum
        "max_stop_distance": 100.0,   # 100 pips maximum
        "volatility_floor": 0.0001,   # Minimum volatility
        "regime_adjustments": {       # Adjustments by market regime
            "trending": 1.2,
            "ranging": 0.8,
            "volatile": 1.5,
            "low_volatility": 0.7
        }
    })
    
    # Take profit parameters
    take_profit: Dict[str, Union[float, List[float], Dict[str, float]]] = field(default_factory=lambda: {
        "base_risk_reward_ratio": 2.0,  # 2:1 default
        "profit_target_multiplier": 1.0,
        "market_condition_adjustments": {
            "trending": 1.3,
            "ranging": 0.8,
            "volatile": 1.1,
            "low_volatility": 0.9
        },
        "partial_profit_levels": [0.5, 1.0, 1.5],  # R:R ratios
        "max_profit_target": 200.0  # 200 pips maximum
    })
    
    # Signal filtering parameters
    signal_filtering: Dict[str, Union[float, bool]] = field(default_factory=lambda: {
        "confidence_threshold": 0.75,     # 75% confidence minimum
        "strength_minimum": 0.6,          # 60% signal strength
        "cross_validation_required": True,
        "pattern_reliability_threshold": 0.65,
        "news_event_buffer": 60  # Minutes before/after news
    })
    
    # Optimization metadata
    optimization_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParameterAdjustment:
    """Individual parameter adjustment recommendation"""
    adjustment_id: str
    timestamp: datetime
    parameter_name: str
    category: ParameterCategory
    
    # Change details
    current_value: float
    proposed_value: float
    change_percentage: float
    change_reason: str
    
    # Supporting analysis
    analysis: Dict[str, float] = field(default_factory=lambda: {
        "performance_impact": 0.0,     # Expected Sharpe ratio change
        "risk_impact": 0.0,            # Expected drawdown change
        "confidence_level": 0.0,       # Statistical confidence
        "sample_size": 0,              # Trades used in analysis
        "p_value": 1.0                 # Statistical significance
    })
    
    # Constraints validation
    constraints: Dict[str, Union[bool, float]] = field(default_factory=lambda: {
        "within_monthly_limit": False,
        "within_safety_bounds": False,
        "correlation_impact": 0.0
    })
    
    # Implementation details
    implementation: Dict[str, Any] = field(default_factory=lambda: {
        "approved": False,
        "implemented_at": None,
        "rollback_conditions": [],
        "monitoring_metrics": []
    })


@dataclass
class RollbackCondition:
    """Condition that triggers parameter rollback"""
    condition_id: str
    condition_type: str  # performance_degradation, drawdown_increase, etc.
    threshold: float
    evaluation_period: int  # Days
    trigger_count: int
    severity: RollbackSeverity
    automatic_rollback: bool
    description: str


@dataclass
class OptimizationAnalysis:
    """Analysis period and results for optimization"""
    analysis_id: str
    timestamp: datetime
    account_id: str
    
    # Analysis period
    analysis_period: Dict[str, Any] = field(default_factory=lambda: {
        "start": None,
        "end": None,
        "trade_count": 0,
        "market_regimes": []
    })
    
    # Current performance baseline
    current_performance: Optional[PerformanceMetrics] = None
    
    # Optimization recommendations
    adjustments: List[ParameterAdjustment] = field(default_factory=list)
    
    # Validation results
    validation: Dict[str, Any] = field(default_factory=lambda: {
        "backtest_results": [],
        "monte_carlo_results": {},
        "sensitivity_analysis": {},
        "risk_analysis": {}
    })
    
    # Implementation plan
    implementation: Dict[str, Any] = field(default_factory=lambda: {
        "implementation_date": None,
        "gradual_rollout": False,
        "rollout_percentage": 100.0,
        "monitoring_period": 7  # Days
    })
    
    status: OptimizationStatus = OptimizationStatus.PENDING


@dataclass
class KellyCriterionAnalysis:
    """Kelly Criterion calculation results"""
    analysis_id: str
    timestamp: datetime
    account_id: str
    
    # Input data
    win_rate: float
    avg_win: float
    avg_loss: float
    sample_size: int
    analysis_period: timedelta
    
    # Kelly calculation
    kelly_percentage: float
    recommended_multiplier: float  # Conservative fraction
    confidence_interval: Tuple[float, float]
    
    # Recommendation
    recommended_position_size: float
    size_change_required: float
    implementation_confidence: float
    
    # Risk assessment
    risk_assessment: Dict[str, float] = field(default_factory=lambda: {
        "volatility": 0.0,
        "max_expected_drawdown": 0.0,
        "time_to_recovery": 0.0,
        "risk_of_ruin": 0.0
    })


@dataclass
class VolatilityAnalysis:
    """Market volatility analysis for stop loss optimization"""
    analysis_id: str
    timestamp: datetime
    symbol: str
    
    # ATR data
    current_atr: float
    atr_20_day_avg: float
    atr_trend: str  # "increasing", "stable", "decreasing"
    
    # Market regime classification
    current_regime: MarketRegime
    regime_confidence: float
    
    # Regime-based volatility
    regime_volatility: Dict[str, float] = field(default_factory=dict)
    time_of_day_volatility: Dict[str, float] = field(default_factory=dict)
    
    # Volatility percentiles
    volatility_percentiles: Dict[str, float] = field(default_factory=dict)


@dataclass
class StopLossEffectiveness:
    """Stop loss performance analysis"""
    analysis_id: str
    timestamp: datetime
    account_id: str
    symbol: str
    
    # Current configuration
    current_atr_multiplier: float
    current_avg_stop_distance: float
    
    # Effectiveness metrics
    stop_hit_rate: float           # Percentage of stops hit
    avg_stop_slippage: float       # Average slippage in pips
    premature_stop_rate: float     # Stops hit then price reverses
    
    # Optimization analysis
    optimal_atr_multiplier: float
    expected_improvement: float    # Expected performance improvement
    confidence_level: float
    
    # Alternative stop distances tested
    stop_distance_analysis: List[Dict[str, float]] = field(default_factory=list)


@dataclass
class TakeProfitAnalysis:
    """Take profit target effectiveness analysis"""
    analysis_id: str
    timestamp: datetime
    account_id: str
    
    # Achievement rates
    target_hit_rate: float         # How often TP is reached
    avg_profit_realized: float     # vs target
    premature_exit_rate: float     # Exits before TP
    
    # Recommendations
    recommended_rr_ratio: float
    expected_hit_rate: float
    expected_profit_improvement: float
    
    # Optimal exit analysis
    optimal_exit_points: List[float] = field(default_factory=list)  # Best historical exit levels
    market_condition_impact: Dict[str, Dict[str, float]] = field(default_factory=dict)


@dataclass
class SignalConfidenceCalibration:
    """Signal confidence threshold calibration analysis"""
    analysis_id: str
    timestamp: datetime
    account_id: str
    
    # Current threshold analysis
    current_threshold: float
    signals_above_threshold: int
    signals_below_threshold: int
    
    # Optimal threshold
    optimal_threshold: float
    expected_signal_count: int
    expected_performance_improvement: float
    
    # Performance by confidence level
    confidence_performance: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # Calibration curve
    calibration_data: List[Dict[str, float]] = field(default_factory=list)


@dataclass
class ParameterChangeLog:
    """Log entry for parameter changes"""
    change_id: str
    timestamp: datetime
    account_id: str
    
    # Change details
    parameter_changes: List[ParameterAdjustment]
    implementation_method: ImplementationMethod
    
    # Authorization
    authorized_by: str  # "system" or user_id
    approver: Optional[str] = None
    approval_reason: Optional[str] = None
    
    # Monitoring setup
    monitoring: Dict[str, Any] = field(default_factory=lambda: {
        "monitoring_period": 7,  # Days
        "monitoring_metrics": [],
        "alert_thresholds": {},
        "rollback_triggers": []
    })
    
    # Performance tracking
    performance_tracking: Dict[str, Any] = field(default_factory=lambda: {
        "pre_change_metrics": None,
        "post_change_metrics": None,
        "impact_assessment": None,
        "rollback_recommendation": None
    })


@dataclass
class ImpactAssessment:
    """Assessment of parameter change impact"""
    assessment_id: str
    timestamp: datetime
    change_id: str
    account_id: str
    
    # Statistical significance
    statistical_significance: float
    confidence_interval: Tuple[float, float]
    sample_size: int
    
    # Recommendation
    continue_change: bool
    rollback_recommended: bool
    adjustment_recommended: bool
    recommendation_reason: str
    
    # Performance comparison
    performance_delta: Dict[str, float] = field(default_factory=dict)
    attribution_analysis: Dict[str, float] = field(default_factory=dict)


@dataclass
class MonthlyChangeTracker:
    """Track monthly parameter changes to enforce limits"""
    account_id: str
    month: str  # "YYYY-MM" format
    
    # Change tracking by category
    position_sizing_changes: float = 0.0
    stop_loss_changes: float = 0.0
    take_profit_changes: float = 0.0
    signal_filtering_changes: float = 0.0
    
    # Change history
    changes_this_month: List[str] = field(default_factory=list)  # Change IDs
    
    # Limits
    monthly_limits: Dict[str, float] = field(default_factory=lambda: {
        "position_sizing": 0.10,    # 10% max change
        "stop_loss": 0.15,          # 15% max change
        "take_profit": 0.10,        # 10% max change
        "signal_filtering": 0.05    # 5% max change
    })


def generate_id() -> str:
    """Generate unique ID for records"""
    return str(uuid.uuid4())


def get_current_month() -> str:
    """Get current month in YYYY-MM format"""
    return datetime.utcnow().strftime("%Y-%m")