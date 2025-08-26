"""
Data Models for Continuous Improvement Pipeline

Comprehensive data structures for managing improvement tests, rollouts,
performance tracking, and optimization reporting.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import uuid


class ImprovementType(Enum):
    """Types of improvements that can be tested"""
    STRATEGY_NEW = "strategy_new"
    STRATEGY_MODIFICATION = "strategy_modification" 
    PARAMETER_OPTIMIZATION = "parameter_optimization"
    ALGORITHM_ENHANCEMENT = "algorithm_enhancement"
    RISK_ADJUSTMENT = "risk_adjustment"
    FEATURE_ADDITION = "feature_addition"


class ImprovementPhase(Enum):
    """Phases of improvement testing"""
    SHADOW = "shadow"
    ROLLOUT_10 = "rollout_10"
    ROLLOUT_25 = "rollout_25" 
    ROLLOUT_50 = "rollout_50"
    ROLLOUT_100 = "rollout_100"
    COMPLETED = "completed"
    ROLLED_BACK = "rolled_back"
    PAUSED = "paused"


class PhaseDecision(Enum):
    """Decisions for test progression"""
    ADVANCE = "advance"
    HOLD = "hold"
    ROLLBACK = "rollback"
    MANUAL_REVIEW = "manual_review"


class SuggestionStatus(Enum):
    """Status of improvement suggestions"""
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    IMPLEMENTED = "implemented"
    TESTING = "testing"


class Priority(Enum):
    """Priority levels for improvements"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskLevel(Enum):
    """Risk assessment levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ImplementationComplexity(Enum):
    """Implementation complexity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class PerformanceMetrics:
    """Core performance metrics for comparisons"""
    total_trades: int = 0
    win_rate: Decimal = Decimal('0')
    profit_factor: Decimal = Decimal('0')
    sharpe_ratio: Decimal = Decimal('0')
    max_drawdown: Decimal = Decimal('0')
    total_return: Decimal = Decimal('0')
    expectancy: Decimal = Decimal('0')
    volatility: Decimal = Decimal('0')
    calmar_ratio: Decimal = Decimal('0')
    
    # Time-based metrics
    average_trade_duration: Optional[timedelta] = None
    best_trade: Optional[Decimal] = None
    worst_trade: Optional[Decimal] = None
    
    # Additional metrics
    winning_trades: int = 0
    losing_trades: int = 0
    average_win: Decimal = Decimal('0')
    average_loss: Decimal = Decimal('0')


@dataclass
class StatisticalAnalysis:
    """Statistical analysis results for A/B testing"""
    sample_size: int
    power_analysis: float
    p_value: float
    confidence_interval: tuple[float, float]
    effect_size: float
    statistically_significant: bool
    significance_level: float = 0.05
    
    # Additional statistics
    t_statistic: Optional[float] = None
    degrees_of_freedom: Optional[int] = None
    confidence_level: float = 0.95


@dataclass 
class PerformanceComparison:
    """Comparison between control and treatment groups"""
    control_performance: PerformanceMetrics
    treatment_performance: PerformanceMetrics
    
    # Relative performance
    relative_improvement: Decimal  # Treatment vs Control (positive = better)
    absolute_difference: Decimal
    percentage_improvement: Decimal
    
    # Statistical validation
    statistical_analysis: StatisticalAnalysis
    
    # Risk metrics
    risk_adjusted_improvement: Decimal
    correlation_impact: Optional[Decimal] = None
    volatility_impact: Optional[Decimal] = None


@dataclass
class Change:
    """Represents a specific change being tested"""
    change_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    change_type: str = "parameter"  # parameter, algorithm, strategy, feature
    
    # Change details
    component: str = ""
    description: str = ""
    implementation_date: datetime = field(default_factory=datetime.utcnow)
    
    # Change specifications
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    configuration_changes: Dict[str, Any] = field(default_factory=dict)
    code_changes: List[str] = field(default_factory=list)
    
    # Impact tracking
    expected_performance_change: Decimal = Decimal('0')
    actual_performance_change: Optional[Decimal] = None
    risk_impact: str = ""
    system_impact: str = ""
    
    # Rollback information
    can_rollback: bool = True
    rollback_procedure: str = ""
    rollback_data: Any = None
    rollback_complexity: ImplementationComplexity = ImplementationComplexity.LOW


@dataclass
class ImprovementGroup:
    """Represents a control or treatment group in A/B testing"""
    group_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    group_type: str = "control"  # control or treatment
    
    # Group configuration
    accounts: List[str] = field(default_factory=list)
    allocation_percentage: Decimal = Decimal('0')
    
    # Changes applied (for treatment group)
    changes: List[Change] = field(default_factory=list)
    
    # Performance tracking
    baseline_performance: Optional[PerformanceMetrics] = None
    current_performance: Optional[PerformanceMetrics] = None
    daily_performance: Dict[str, PerformanceMetrics] = field(default_factory=dict)
    
    # Sample statistics
    sample_size: int = 0
    trades_completed: int = 0
    average_trades_per_account: Decimal = Decimal('0')
    account_variance: Decimal = Decimal('0')


@dataclass
class StageDecision:
    """Decision for test stage progression"""
    decision: PhaseDecision
    reason: str
    decision_maker: str  # automatic or manual
    decision_date: datetime = field(default_factory=datetime.utcnow)
    next_stage_date: Optional[datetime] = None
    confidence_level: float = 0.0
    
    # Supporting data
    performance_data: Optional[PerformanceComparison] = None
    risk_assessment: Optional[str] = None
    stakeholder_input: Optional[str] = None


@dataclass
class RolloutStageResults:
    """Results from a specific rollout stage"""
    stage_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    stage: int = 10  # 10, 25, 50, 100
    
    # Stage period
    start_date: datetime = field(default_factory=datetime.utcnow)
    end_date: Optional[datetime] = None
    duration: Optional[timedelta] = None
    
    # Performance comparison
    performance_comparison: Optional[PerformanceComparison] = None
    
    # Stage decision
    stage_decision: Optional[StageDecision] = None
    
    # Observations and issues
    performance_issues: List[str] = field(default_factory=list)
    unexpected_behaviors: List[str] = field(default_factory=list)
    risk_concerns: List[str] = field(default_factory=list)
    positive_findings: List[str] = field(default_factory=list)


@dataclass
class ShadowTestResults:
    """Results from shadow testing phase"""
    test_id: str
    
    # Shadow period
    start_date: datetime
    end_date: datetime
    duration: timedelta
    
    # Shadow performance
    total_signals: int = 0
    trades_executed: int = 0  # In shadow mode
    simulated_performance: Optional[PerformanceMetrics] = None
    comparison_to_live: Optional[PerformanceComparison] = None
    
    # Risk analysis
    max_simulated_drawdown: Decimal = Decimal('0')
    volatility_increase: Decimal = Decimal('0')
    correlation_impact: Decimal = Decimal('0')
    risk_score: int = 50  # 0-100
    
    # Validation results
    validation_passed: bool = False
    validation_issues: List[str] = field(default_factory=list)
    performance_gain: Decimal = Decimal('0')
    significance_level: float = 0.05
    recommendation: str = "proceed"  # proceed, modify, reject


@dataclass
class ImprovementConfiguration:
    """Configuration parameters for improvement tests"""
    test_duration: int = 30  # Days
    minimum_sample_size: int = 100  # Trades required
    significance_level: float = 0.05  # 95% confidence
    power_level: float = 0.8  # 80% power
    rollout_stages: List[int] = field(default_factory=lambda: [10, 25, 50, 100])
    
    # Safety parameters
    max_rollback_threshold: Decimal = Decimal('-0.10')  # 10% underperformance
    min_advancement_threshold: Decimal = Decimal('0.02')  # 2% improvement
    
    # Stage validation
    stage_validation_period: int = 7  # Days per stage minimum
    min_trades_per_stage: int = 50  # Minimum trades before advancement


@dataclass
class Approval:
    """Approval record for manual oversight"""
    approver: str
    approval_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    approval_date: datetime = field(default_factory=datetime.utcnow)
    approval_type: str = "stage_advancement"  # stage_advancement, test_initiation, rollback
    approved: bool = False
    notes: str = ""
    conditions: List[str] = field(default_factory=list)


@dataclass
class ImprovementTest:
    """Main improvement test entity"""
    test_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    improvement_type: ImprovementType = ImprovementType.PARAMETER_OPTIMIZATION
    
    # Test details
    name: str = ""
    description: str = ""
    hypothesis: str = ""
    expected_impact: str = ""
    risk_assessment: str = ""
    implementation_complexity: ImplementationComplexity = ImplementationComplexity.MEDIUM
    
    # Test configuration
    test_config: ImprovementConfiguration = field(default_factory=ImprovementConfiguration)
    
    # Test groups
    control_group: Optional[ImprovementGroup] = None
    treatment_group: Optional[ImprovementGroup] = None
    
    # Current status
    current_phase: ImprovementPhase = ImprovementPhase.SHADOW
    start_date: datetime = field(default_factory=datetime.utcnow)
    current_stage_start: datetime = field(default_factory=datetime.utcnow)
    expected_completion: Optional[datetime] = None
    actual_completion: Optional[datetime] = None
    
    # Results tracking
    shadow_results: Optional[ShadowTestResults] = None
    rollout_results: List[RolloutStageResults] = field(default_factory=list)
    final_results: Optional[PerformanceComparison] = None
    rollback_reason: Optional[str] = None
    
    # Approval and oversight
    required_approvals: List[str] = field(default_factory=list)
    approvals: List[Approval] = field(default_factory=list)
    human_review_required: bool = False
    auto_advance_enabled: bool = True
    
    # Metadata
    created_by: str = "system"
    created_date: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ImprovementSuggestion:
    """AI-generated improvement suggestion"""
    suggestion_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Suggestion details
    suggestion_type: ImprovementType = ImprovementType.PARAMETER_OPTIMIZATION
    category: str = ""
    title: str = ""
    description: str = ""
    rationale: str = ""
    
    # Source and evidence
    source_type: str = "automated_analysis"  # automated_analysis, performance_review, etc.
    evidence_strength: str = "moderate"  # weak, moderate, strong
    supporting_data: List[Any] = field(default_factory=list)
    analysis_method: str = ""
    
    # Impact assessment
    expected_impact: str = "moderate"  # minor, moderate, significant, major
    impact_areas: List[str] = field(default_factory=list)
    performance_gain_estimate: Decimal = Decimal('0')
    risk_level: RiskLevel = RiskLevel.MEDIUM
    implementation_effort: ImplementationComplexity = ImplementationComplexity.MEDIUM
    
    # Prioritization
    priority: Priority = Priority.MEDIUM
    priority_score: float = 50.0  # 0-100
    priority_factors: List[str] = field(default_factory=list)
    urgency: Priority = Priority.MEDIUM
    
    # Review status
    status: SuggestionStatus = SuggestionStatus.PENDING
    reviewer: Optional[str] = None
    review_date: Optional[datetime] = None
    review_notes: Optional[str] = None
    implementation_date: Optional[datetime] = None
    
    # Outcome tracking
    implemented: bool = False
    actual_impact: Optional[Decimal] = None
    impact_assessment_accuracy: Optional[float] = None
    lessons_learned: List[str] = field(default_factory=list)


@dataclass
class PipelineConfiguration:
    """Configuration for the continuous improvement pipeline"""
    shadow_testing_enabled: bool = True
    gradual_rollout_enabled: bool = True
    automatic_rollback_enabled: bool = True
    
    # Thresholds
    rollback_threshold: Decimal = Decimal('-0.10')  # 10% performance degradation
    rollout_stages: List[int] = field(default_factory=lambda: [10, 25, 50, 100])
    stage_validation_period: int = 7  # Days per stage
    
    # Safety parameters
    max_concurrent_tests: int = 5
    max_accounts_in_testing: Decimal = Decimal('0.30')  # 30% max
    emergency_stop_threshold: Decimal = Decimal('-0.20')  # 20% loss triggers emergency stop
    
    # Automation settings
    auto_advance_enabled: bool = True
    require_manual_approval: bool = True
    notification_enabled: bool = True


@dataclass
class PipelineStatus:
    """Current status of the improvement pipeline"""
    last_run: datetime = field(default_factory=datetime.utcnow)
    improvements_in_testing: int = 0
    improvements_in_rollout: int = 0
    successful_deployments: int = 0
    rollbacks: int = 0
    pending_approvals: int = 0
    
    # Performance tracking
    pipeline_health: float = 100.0  # 0-100
    average_test_duration: Optional[timedelta] = None
    success_rate: float = 0.0
    current_performance_impact: Decimal = Decimal('0')


@dataclass
class PipelineMetrics:
    """Key performance indicators for the pipeline"""
    improvement_success_rate: float = 0.0
    average_improvement_gain: Decimal = Decimal('0')
    average_test_duration: timedelta = timedelta(days=30)
    rollback_rate: float = 0.0
    time_to_full_deployment: timedelta = timedelta(days=45)
    
    # Efficiency metrics
    suggestion_to_test_conversion: float = 0.0
    test_to_deployment_conversion: float = 0.0
    false_positive_rate: float = 0.0
    
    # Quality metrics
    impact_prediction_accuracy: float = 0.0
    risk_assessment_accuracy: float = 0.0


@dataclass
class ContinuousImprovementPipeline:
    """Main pipeline entity"""
    pipeline_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    version: str = "1.0.0"
    
    # Pipeline configuration
    configuration: PipelineConfiguration = field(default_factory=PipelineConfiguration)
    
    # Active improvements
    active_improvements: List[ImprovementTest] = field(default_factory=list)
    pending_suggestions: List[ImprovementSuggestion] = field(default_factory=list)
    
    # Pipeline status
    status: PipelineStatus = field(default_factory=PipelineStatus)
    
    # Performance tracking
    pipeline_metrics: PipelineMetrics = field(default_factory=PipelineMetrics)
    
    # Metadata
    created_date: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ImprovementCycleResults:
    """Results from a single improvement cycle execution"""
    cycle_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    execution_time: datetime = field(default_factory=datetime.utcnow)
    
    # Cycle results
    new_tests_created: List[str] = field(default_factory=list)  # Test IDs
    test_updates: List[str] = field(default_factory=list)  # Test IDs updated
    new_suggestions: List[str] = field(default_factory=list)  # Suggestion IDs
    rollback_actions: List[str] = field(default_factory=list)  # Test IDs rolled back
    
    # Performance metrics
    cycle_duration: Optional[timedelta] = None
    tests_processed: int = 0
    suggestions_generated: int = 0
    decisions_made: int = 0
    
    # Issues and errors
    errors_encountered: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Summary
    success: bool = True
    summary: str = ""


@dataclass
class PhaseUpdate:
    """Update information for a test"""
    test_id: str
    status: str
    new_phase: Optional[ImprovementPhase] = None
    performance: Optional[PerformanceComparison] = None
    reason: Optional[str] = None
    next_action: Optional[str] = None
    update_timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RollbackDecision:
    """Decision to rollback a test"""
    test_id: str
    rollback_reason: str
    trigger_value: float
    threshold: float
    severity: str = "automatic"  # automatic, manual, emergency
    immediate: bool = True
    decision_timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RollbackResult:
    """Result of rollback execution"""
    test_id: str
    rollback_successful: bool
    changes_reverted: int
    rollback_time: datetime
    rollback_duration: Optional[timedelta] = None
    issues_encountered: List[str] = field(default_factory=list)
    recovery_actions: List[str] = field(default_factory=list)


# Aliases for backward compatibility
TestPhase = ImprovementPhase  # Alias for legacy code
TestDecision = PhaseDecision  # Alias for legacy code