"""
Data models for Strategy Performance Analysis.
"""
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Union
from dataclasses import dataclass
from pydantic import BaseModel, Field


class StrategyType(str, Enum):
    """Strategy classification types."""
    TREND_FOLLOWING = "trend_following"
    MEAN_REVERSION = "mean_reversion"
    BREAKOUT = "breakout"
    PATTERN_RECOGNITION = "pattern_recognition"
    ARBITRAGE = "arbitrage"


class StrategyComplexity(str, Enum):
    """Strategy complexity levels."""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


class StrategyStatus(str, Enum):
    """Strategy lifecycle status."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEPRECATED = "deprecated"
    TESTING = "testing"


class MarketRegime(str, Enum):
    """Market regime classifications."""
    STRONG_UPTREND = "strong_up"
    WEAK_UPTREND = "weak_up"
    SIDEWAYS = "sideways"
    WEAK_DOWNTREND = "weak_down"
    STRONG_DOWNTREND = "strong_down"


class VolatilityLevel(str, Enum):
    """Volatility classification levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class VolumeProfile(str, Enum):
    """Volume profile classifications."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class TrendDirection(str, Enum):
    """Performance trend directions."""
    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"


class SeverityLevel(str, Enum):
    """Issue severity levels."""
    MINOR = "minor"
    MODERATE = "moderate"
    SEVERE = "severe"
    CRITICAL = "critical"


class ImpactLevel(str, Enum):
    """Impact assessment levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PerformanceIssueType(str, Enum):
    """Types of performance issues."""
    LOW_WIN_RATE = "low_win_rate"
    HIGH_DRAWDOWN = "high_drawdown"
    POOR_RISK_REWARD = "poor_risk_reward"
    INCONSISTENT_PERFORMANCE = "inconsistent_performance"
    REGIME_MISMATCH = "regime_mismatch"


class RecommendedAction(str, Enum):
    """Recommended actions for underperformance."""
    MONITOR = "monitor"
    REDUCE_ALLOCATION = "reduce_allocation"
    SUSPEND = "suspend"
    DISABLE = "disable"


class RecoveryPhase(str, Enum):
    """Recovery phases for suspended strategies."""
    SUSPENDED = "suspended"
    MONITORING = "monitoring"
    GRADUAL_RETURN = "gradual_return"
    FULL_RETURN = "full_return"


@dataclass
class PerformanceMetrics:
    """Core performance metrics for strategies."""
    total_trades: int
    win_count: int
    loss_count: int
    win_rate: Decimal
    profit_factor: Decimal
    expectancy: Decimal
    sharpe_ratio: Decimal
    calmar_ratio: Decimal
    max_drawdown: Decimal
    average_win: Decimal
    average_loss: Decimal
    average_hold_time: timedelta
    total_return: Decimal
    annualized_return: Decimal


class StrategyClassification(BaseModel):
    """Strategy classification and metadata."""
    type: StrategyType
    subtype: str
    timeframe: List[str] = Field(description="Applicable timeframes like ['H1', 'H4', 'D1']")
    symbols: List[str] = Field(description="Applicable currency pairs")
    market_regimes: List[MarketRegime] = Field(description="Preferred market conditions")


class StrategyLogic(BaseModel):
    """Strategy logic definition."""
    entry_conditions: List[str]
    exit_conditions: List[str]
    risk_management: List[str]
    signal_generation: str
    complexity: StrategyComplexity


class StatisticalSignificance(BaseModel):
    """Statistical significance testing results."""
    sample_size: int
    confidence_level: Decimal
    p_value: Decimal
    confidence_interval: tuple[Decimal, Decimal]
    statistically_significant: bool
    required_sample_size: int
    current_significance_level: Decimal


class PerformanceTrend(BaseModel):
    """Performance trend analysis."""
    direction: TrendDirection
    trend_strength: Decimal = Field(ge=0, le=1, description="Strength from 0-1")
    trend_duration: int = Field(description="Duration in days")
    change_rate: Decimal = Field(description="Performance change per day")
    projected_performance: Decimal = Field(description="30-day projection")


class RegimeCharacteristics(BaseModel):
    """Market regime characteristics."""
    volatility: VolatilityLevel
    trend: MarketRegime
    volume_profile: VolumeProfile
    time_of_day: List[str] = Field(description="Sessions where this regime occurs")


class RegimeEffectiveness(BaseModel):
    """Strategy effectiveness in specific market regime."""
    preferred_regime: bool = Field(description="Is this a preferred regime for strategy?")
    relative_performance: Decimal = Field(description="vs overall performance")
    consistency: Decimal = Field(ge=0, le=1, description="Performance consistency in regime")
    adaptability: Decimal = Field(ge=0, le=1, description="How well strategy adapts to regime")


class RegimeStatistics(BaseModel):
    """Statistical data for market regime."""
    occurrences: int = Field(description="How often this regime occurs")
    total_trades: int
    average_trades_per_occurrence: Decimal
    regime_duration: timedelta = Field(description="Average regime duration")


class RegimePerformance(BaseModel):
    """Strategy performance in specific market regime."""
    regime: MarketRegime
    performance: PerformanceMetrics
    characteristics: RegimeCharacteristics
    effectiveness: RegimeEffectiveness
    statistics: RegimeStatistics


class DailyPerformance(BaseModel):
    """Daily performance metrics."""
    date: datetime
    trades: int
    pnl: Decimal
    win_rate: Decimal
    drawdown: Decimal


class WeeklyPerformance(BaseModel):
    """Weekly performance metrics."""
    week: str = Field(description="Week in YYYY-WW format")
    trades: int
    pnl: Decimal
    win_rate: Decimal
    sharpe_ratio: Decimal


class MonthlyPerformance(BaseModel):
    """Monthly performance metrics."""
    month: str = Field(description="Month in YYYY-MM format")
    trades: int
    pnl: Decimal
    win_rate: Decimal
    sharpe_ratio: Decimal
    max_drawdown: Decimal


class TimeBasedPerformance(BaseModel):
    """Time-based performance analysis."""
    daily: Dict[str, DailyPerformance] = Field(description="Performance by date (YYYY-MM-DD)")
    weekly: Dict[str, WeeklyPerformance] = Field(description="Performance by week (YYYY-WW)")
    monthly: Dict[str, MonthlyPerformance] = Field(description="Performance by month (YYYY-MM)")
    rolling_30_day: PerformanceMetrics
    rolling_90_day: PerformanceMetrics
    rolling_365_day: PerformanceMetrics


class StrategyLifecycle(BaseModel):
    """Strategy lifecycle information."""
    created_at: datetime
    activated_at: datetime
    last_modified: datetime
    status: StrategyStatus
    suspension_reason: Optional[str] = None
    suspended_at: Optional[datetime] = None


class StrategyConfiguration(BaseModel):
    """Strategy configuration settings."""
    enabled: bool
    weight: Decimal = Field(description="Portfolio allocation weight")
    max_allocation: Decimal = Field(description="Maximum portfolio percentage")
    min_trades_for_evaluation: int = Field(description="Minimum trades for statistical significance")
    evaluation_period: int = Field(description="Evaluation period in days")


class StrategyPerformance(BaseModel):
    """Complete strategy performance analysis."""
    strategy_id: str
    overall: PerformanceMetrics
    significance: StatisticalSignificance
    time_based: TimeBasedPerformance
    regime_performance: Dict[MarketRegime, RegimePerformance]
    trend: PerformanceTrend
    last_updated: datetime


class TradingStrategy(BaseModel):
    """Complete trading strategy definition and tracking."""
    strategy_id: str
    strategy_name: str
    version: str
    
    # Strategy Classification
    classification: StrategyClassification
    
    # Strategy Logic
    logic: StrategyLogic
    
    # Performance Tracking
    performance: StrategyPerformance
    
    # Lifecycle
    lifecycle: StrategyLifecycle
    
    # Configuration
    configuration: StrategyConfiguration


class PerformanceIssue(BaseModel):
    """Individual performance issue definition."""
    issue_type: PerformanceIssueType
    description: str
    severity: SeverityLevel
    
    # Metrics
    current_value: Decimal
    expected_value: Decimal
    threshold: Decimal
    deviation_magnitude: Decimal
    
    # Trend
    trend: TrendDirection
    trend_duration: int = Field(description="Duration in days")
    
    # Impact
    impact_on_portfolio: Decimal = Field(description="Portfolio performance impact")
    risk_contribution: Decimal = Field(description="Risk contribution")


class SeverityAssessment(BaseModel):
    """Severity assessment for performance issues."""
    level: SeverityLevel
    score: Decimal = Field(ge=0, le=100, description="Severity score 0-100")
    impact: ImpactLevel
    urgency: ImpactLevel


class RehabilitationPlan(BaseModel):
    """Rehabilitation plan for underperforming strategies."""
    plan_id: str
    strategy_id: str
    
    # Plan Details
    suspension_period: int = Field(description="Suspension period in days")
    monitoring_metrics: List[str]
    recovery_thresholds: Dict[str, Decimal]
    evaluation_schedule: List[int] = Field(description="Days for evaluation checkpoints")
    
    # Recovery Tracking
    current_phase: RecoveryPhase
    progress_score: Decimal = Field(ge=0, le=100, description="Progress score 0-100")
    metrics_improvement: Dict[str, Decimal]
    time_to_full_recovery: int = Field(description="Estimated days to full recovery")
    
    # Conditions for Return
    minimum_performance_period: int = Field(description="Days of good performance required")
    required_metrics: Dict[str, Decimal]
    manual_approval_required: bool
    gradual_return_steps: List[Decimal] = Field(description="Allocation percentages for gradual return")


class RecommendationSet(BaseModel):
    """Set of recommendations for strategy management."""
    immediate_action: RecommendedAction
    rehabilitation_plan: Optional[RehabilitationPlan] = None
    alternative_strategies: List[str]
    time_to_review: int = Field(description="Days until next review")


class AutomaticActions(BaseModel):
    """Automatic actions taken by the system."""
    suspension_triggered: bool
    allocation_reduced: bool
    alerts_sent: List[str]
    manual_review_required: bool


class UnderperformanceDetection(BaseModel):
    """Underperformance detection result."""
    detection_id: str
    strategy_id: str
    timestamp: datetime
    
    # Detection Criteria
    detection_type: str = Field(description="Type of detection algorithm used")
    threshold: Decimal
    evaluation_period: int = Field(description="Evaluation period in days")
    minimum_trades: int
    
    # Performance Issues
    issues: List[PerformanceIssue]
    
    # Severity Assessment
    severity: SeverityAssessment
    
    # Recommendations
    recommendations: RecommendationSet
    
    # Automatic Actions
    automatic_actions: AutomaticActions


class CorrelationCluster(BaseModel):
    """Cluster of correlated strategies."""
    cluster_id: str
    strategies: List[str]
    average_correlation: Decimal = Field(ge=-1, le=1)
    cluster_weight: Decimal = Field(description="Total portfolio weight of cluster")
    dominant_strategy: str = Field(description="Best performing strategy in cluster")
    redundant_strategies: List[str] = Field(description="Candidates for removal")


class PortfolioAnalysis(BaseModel):
    """Portfolio-level correlation analysis."""
    overall_correlation: Decimal = Field(ge=-1, le=1)
    diversification_ratio: Decimal
    portfolio_volatility: Decimal
    individual_volatilities: Dict[str, Decimal]
    correlation_clusters: List[CorrelationCluster]


class DiversificationAnalysis(BaseModel):
    """Analysis of diversification benefits."""
    current_diversification_benefit: Decimal
    potential_improvement: Decimal
    recommended_weight_changes: Dict[str, Decimal]
    risk_reduction: Decimal
    return_impact: Decimal


class RiskConcentration(BaseModel):
    """Risk concentration analysis."""
    concentration_risk: Decimal = Field(ge=0, le=1, description="0-1, higher = more concentrated")
    largest_cluster_weight: Decimal
    independent_strategies: int
    redundant_strategies: List[str] = Field(description="Highly correlated strategies")


class StrategyCorrelationAnalysis(BaseModel):
    """Strategy correlation analysis results."""
    analysis_id: str
    timestamp: datetime
    
    # Correlation Matrix
    correlation_matrix: Dict[str, Dict[str, Decimal]] = Field(description="strategy1 -> strategy2 -> correlation")
    
    # Portfolio Analysis
    portfolio_analysis: PortfolioAnalysis
    
    # Diversification Benefits
    diversification_analysis: DiversificationAnalysis
    
    # Risk Concentration
    risk_concentration: RiskConcentration


class StrategyRanking(BaseModel):
    """Strategy ranking result."""
    rank: int
    strategy_id: str
    strategy_name: str
    score: Decimal
    metric: str
    percentile: Decimal = Field(ge=0, le=100)
    trend: TrendDirection
    comments: str


class RegimeTransition(BaseModel):
    """Market regime transition information."""
    from_regime: MarketRegime
    to_regime: MarketRegime
    transition_time: datetime
    duration: timedelta
    impact_on_strategies: Dict[str, Decimal]


class RegimeForecast(BaseModel):
    """Market regime forecast."""
    predicted_regime: MarketRegime
    confidence: Decimal = Field(ge=0, le=1)
    estimated_time: datetime
    duration_estimate: timedelta
    recommended_strategies: List[str]


class RegimeAnalysis(BaseModel):
    """Market regime analysis."""
    current_regime: MarketRegime
    regime_strategies: Dict[MarketRegime, List[str]] = Field(description="regime -> preferred strategies")
    regime_transitions: List[RegimeTransition]
    upcoming_regime_changes: List[RegimeForecast]


class PortfolioOptimization(BaseModel):
    """Portfolio optimization recommendations."""
    target_allocation: Dict[str, Decimal]
    expected_return: Decimal
    expected_risk: Decimal
    diversification_score: Decimal
    implementation_timeline: List[str]


class ActionItem(BaseModel):
    """Action item for strategy management."""
    item_id: str
    category: str = Field(description="Category: strategy_management, allocation, risk_management, development")
    priority: str = Field(description="Priority: low, medium, high, critical")
    
    description: str
    expected_impact: str
    estimated_effort: str
    deadline: datetime
    assigned_to: str
    
    dependencies: List[str]
    success_criteria: List[str]
    risk_mitigation: List[str]


class ExecutiveSummary(BaseModel):
    """Executive summary of strategy effectiveness."""
    total_strategies: int
    active_strategies: int
    suspended_strategies: int
    top_performers: List[str] = Field(description="Strategy IDs")
    underperformers: List[str]
    portfolio_performance: PerformanceMetrics
    diversification_score: Decimal = Field(ge=0, le=100)
    overall_health_score: Decimal = Field(ge=0, le=100)


class StrategyRankings(BaseModel):
    """Strategy rankings by various metrics."""
    by_performance: List[StrategyRanking]
    by_risk_adjusted_return: List[StrategyRanking]
    by_consistency: List[StrategyRanking]
    by_diversification_benefit: List[StrategyRanking]


class ActionItems(BaseModel):
    """Action items categorized by timeline."""
    immediate: List[ActionItem] = Field(description="This week")
    short_term: List[ActionItem] = Field(description="Next month")
    long_term: List[ActionItem] = Field(description="Next quarter")


class StrategyRecommendations(BaseModel):
    """Strategy management recommendations."""
    strategies_to_activate: List[str]
    strategies_to_suspend: List[str]
    allocation_changes: Dict[str, Decimal]
    new_strategy_needs: List[str] = Field(description="Types of strategies needed")
    portfolio_optimization: PortfolioOptimization


class StrategyEffectivenessReport(BaseModel):
    """Weekly strategy effectiveness report."""
    report_id: str
    report_date: datetime
    report_period_start: datetime
    report_period_end: datetime
    
    # Executive Summary
    executive_summary: ExecutiveSummary
    
    # Strategy Rankings
    rankings: StrategyRankings
    
    # Market Regime Analysis
    regime_analysis: RegimeAnalysis
    
    # Recommendations
    recommendations: StrategyRecommendations
    
    # Action Items
    action_items: ActionItems