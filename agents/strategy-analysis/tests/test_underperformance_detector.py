"""
Tests for Underperformance Detector.
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from agents.strategy_analysis.app.underperformance_detector import UnderperformanceDetector
from agents.strategy_analysis.app.models import (
    TradingStrategy, StrategyType, StrategyStatus, StrategyConfiguration,
    StrategyClassification, StrategyLogic, StrategyLifecycle, StrategyComplexity,
    PerformanceMetrics, StrategyPerformance, StatisticalSignificance,
    TimeBasedPerformance, PerformanceTrend, TrendDirection,
    PerformanceIssueType, SeverityLevel, RecommendedAction
)


@pytest.fixture
def good_performance_metrics():
    """Create good performance metrics."""
    return PerformanceMetrics(
        total_trades=100,
        win_count=60,
        loss_count=40,
        win_rate=Decimal('0.6'),
        profit_factor=Decimal('1.8'),
        expectancy=Decimal('0.005'),
        sharpe_ratio=Decimal('1.2'),
        calmar_ratio=Decimal('2.0'),
        max_drawdown=Decimal('0.08'),  # 8%
        average_win=Decimal('150'),
        average_loss=Decimal('100'),
        average_hold_time=timedelta(hours=4),
        total_return=Decimal('0.12'),
        annualized_return=Decimal('0.25')
    )


@pytest.fixture
def poor_performance_metrics():
    """Create poor performance metrics."""
    return PerformanceMetrics(
        total_trades=50,
        win_count=15,
        loss_count=35,
        win_rate=Decimal('0.3'),  # Low win rate
        profit_factor=Decimal('0.8'),  # Poor profit factor
        expectancy=Decimal('-0.01'),  # Negative expectancy
        sharpe_ratio=Decimal('0.2'),  # Low Sharpe ratio
        calmar_ratio=Decimal('0.5'),
        max_drawdown=Decimal('0.25'),  # High drawdown (25%)
        average_win=Decimal('100'),
        average_loss=Decimal('150'),
        average_hold_time=timedelta(hours=6),
        total_return=Decimal('-0.05'),
        annualized_return=Decimal('-0.15')
    )


@pytest.fixture
def good_strategy(good_performance_metrics):
    """Create a well-performing strategy."""
    trend = PerformanceTrend(
        direction=TrendDirection.IMPROVING,
        trend_strength=Decimal('0.8'),
        trend_duration=30,
        change_rate=Decimal('0.001'),
        projected_performance=Decimal('0.01')
    )
    
    performance = StrategyPerformance(
        strategy_id="good_strategy",
        overall=good_performance_metrics,
        significance=StatisticalSignificance(
            sample_size=100,
            confidence_level=Decimal('0.95'),
            p_value=Decimal('0.01'),
            confidence_interval=(Decimal('0.002'), Decimal('0.008')),
            statistically_significant=True,
            required_sample_size=30,
            current_significance_level=Decimal('0.99')
        ),
        time_based=TimeBasedPerformance(
            daily={}, weekly={}, monthly={},
            rolling_30_day=good_performance_metrics,
            rolling_90_day=good_performance_metrics,
            rolling_365_day=good_performance_metrics
        ),
        regime_performance={},
        trend=trend,
        last_updated=datetime.utcnow()
    )
    
    return TradingStrategy(
        strategy_id="good_strategy",
        strategy_name="Good Strategy",
        version="1.0",
        classification=StrategyClassification(
            type=StrategyType.TREND_FOLLOWING,
            subtype="momentum",
            timeframe=["H4"],
            symbols=["EURUSD"],
            market_regimes=[]
        ),
        logic=StrategyLogic(
            entry_conditions=["signal"],
            exit_conditions=["stop"],
            risk_management=["stops"],
            signal_generation="pattern",
            complexity=StrategyComplexity.SIMPLE
        ),
        performance=performance,
        lifecycle=StrategyLifecycle(
            created_at=datetime.utcnow(),
            activated_at=datetime.utcnow(),
            last_modified=datetime.utcnow(),
            status=StrategyStatus.ACTIVE
        ),
        configuration=StrategyConfiguration(
            enabled=True,
            weight=Decimal('0.1'),
            max_allocation=Decimal('0.25'),
            min_trades_for_evaluation=30,
            evaluation_period=90
        )
    )


@pytest.fixture
def poor_strategy(poor_performance_metrics):
    """Create a poorly-performing strategy."""
    trend = PerformanceTrend(
        direction=TrendDirection.DECLINING,
        trend_strength=Decimal('0.6'),
        trend_duration=45,
        change_rate=Decimal('-0.002'),
        projected_performance=Decimal('-0.015')
    )
    
    performance = StrategyPerformance(
        strategy_id="poor_strategy",
        overall=poor_performance_metrics,
        significance=StatisticalSignificance(
            sample_size=50,
            confidence_level=Decimal('0.95'),
            p_value=Decimal('0.15'),
            confidence_interval=(Decimal('-0.015'), Decimal('-0.005')),
            statistically_significant=True,
            required_sample_size=30,
            current_significance_level=Decimal('0.85')
        ),
        time_based=TimeBasedPerformance(
            daily={}, weekly={}, monthly={},
            rolling_30_day=poor_performance_metrics,
            rolling_90_day=poor_performance_metrics,
            rolling_365_day=poor_performance_metrics
        ),
        regime_performance={},
        trend=trend,
        last_updated=datetime.utcnow()
    )
    
    return TradingStrategy(
        strategy_id="poor_strategy",
        strategy_name="Poor Strategy",
        version="1.0",
        classification=StrategyClassification(
            type=StrategyType.MEAN_REVERSION,
            subtype="oversold",
            timeframe=["H1"],
            symbols=["GBPUSD"],
            market_regimes=[]
        ),
        logic=StrategyLogic(
            entry_conditions=["oversold"],
            exit_conditions=["target"],
            risk_management=["stops"],
            signal_generation="indicator",
            complexity=StrategyComplexity.MODERATE
        ),
        performance=performance,
        lifecycle=StrategyLifecycle(
            created_at=datetime.utcnow(),
            activated_at=datetime.utcnow(),
            last_modified=datetime.utcnow(),
            status=StrategyStatus.ACTIVE
        ),
        configuration=StrategyConfiguration(
            enabled=True,
            weight=Decimal('0.15'),
            max_allocation=Decimal('0.3'),
            min_trades_for_evaluation=30,
            evaluation_period=90
        )
    )


class TestUnderperformanceDetector:
    """Test cases for UnderperformanceDetector."""
    
    def setup_method(self):
        """Setup test environment."""
        self.detector = UnderperformanceDetector()
    
    @pytest.mark.asyncio
    async def test_detect_no_underperformance_good_strategy(self, good_strategy):
        """Test that good strategy is not flagged for underperformance."""
        detection = await self.detector.detect_underperformance(good_strategy)
        
        assert detection is None
    
    @pytest.mark.asyncio
    async def test_detect_underperformance_poor_strategy(self, poor_strategy):
        """Test that poor strategy is flagged for underperformance."""
        detection = await self.detector.detect_underperformance(poor_strategy)
        
        assert detection is not None
        assert detection.strategy_id == "poor_strategy"
        assert len(detection.issues) > 0
        assert detection.severity.level in [SeverityLevel.SEVERE, SeverityLevel.CRITICAL]
    
    @pytest.mark.asyncio
    async def test_insufficient_trades_no_detection(self, good_strategy):
        """Test that strategies with insufficient trades are not analyzed."""
        # Modify strategy to have insufficient trades
        good_strategy.performance.overall.total_trades = 10
        
        detection = await self.detector.detect_underperformance(good_strategy)
        
        assert detection is None
    
    @pytest.mark.asyncio
    async def test_detect_specific_issues(self, poor_strategy):
        """Test detection of specific performance issues."""
        detection = await self.detector.detect_underperformance(poor_strategy)
        
        assert detection is not None
        
        # Check for expected issues
        issue_types = [issue.issue_type for issue in detection.issues]
        
        assert PerformanceIssueType.LOW_WIN_RATE in issue_types
        assert PerformanceIssueType.HIGH_DRAWDOWN in issue_types
        assert PerformanceIssueType.POOR_RISK_REWARD in issue_types
    
    def test_assess_severity_minor(self):
        """Test severity assessment for minor issues."""
        minor_issues = [
            self.detector._create_performance_issue(
                PerformanceIssueType.LOW_WIN_RATE,
                "Minor win rate issue",
                Decimal('0.44'),
                Decimal('0.45'),
                Decimal('0.45'),
                None  # Mock strategy
            )
        ]
        
        # Mock the strategy parameter
        with patch.object(self.detector, '_determine_performance_trend', return_value=TrendDirection.STABLE):
            severity = self.detector._assess_severity(minor_issues)
        
        assert severity.level in [SeverityLevel.MINOR, SeverityLevel.MODERATE]
    
    def test_assess_severity_critical(self):
        """Test severity assessment for critical issues."""
        critical_issues = [
            self.detector._create_performance_issue(
                PerformanceIssueType.HIGH_DRAWDOWN,
                "Critical drawdown",
                Decimal('0.35'),
                Decimal('0.15'),
                Decimal('0.15'),
                None  # Mock strategy
            ),
            self.detector._create_performance_issue(
                PerformanceIssueType.POOR_RISK_REWARD,
                "Terrible Sharpe ratio",
                Decimal('-0.5'),
                Decimal('0.5'),
                Decimal('0.5'),
                None  # Mock strategy
            )
        ]
        
        # Mock the strategy parameter and trend determination
        with patch.object(self.detector, '_determine_performance_trend', return_value=TrendDirection.DECLINING):
            severity = self.detector._assess_severity(critical_issues)
        
        assert severity.level in [SeverityLevel.SEVERE, SeverityLevel.CRITICAL]
        assert severity.impact == 'high'
        assert severity.urgency == 'high'
    
    @pytest.mark.asyncio
    async def test_generate_recommendations_suspend(self, poor_strategy):
        """Test recommendation generation for severe underperformance."""
        detection = await self.detector.detect_underperformance(poor_strategy)
        
        assert detection is not None
        
        # Should recommend suspension for severe issues
        if detection.severity.level in [SeverityLevel.SEVERE, SeverityLevel.CRITICAL]:
            assert detection.recommendations.immediate_action in [
                RecommendedAction.SUSPEND, 
                RecommendedAction.DISABLE,
                RecommendedAction.REDUCE_ALLOCATION
            ]
        
        # Should have alternative strategies
        assert len(detection.recommendations.alternative_strategies) > 0
        
        # Should have rehabilitation plan for suspension
        if detection.recommendations.immediate_action == RecommendedAction.SUSPEND:
            assert detection.recommendations.rehabilitation_plan is not None
    
    @pytest.mark.asyncio
    async def test_generate_recommendations_monitor(self, good_strategy):
        """Test recommendation for good strategy with minor issues."""
        # Artificially create a minor issue
        good_strategy.performance.overall.win_rate = Decimal('0.44')  # Slightly below threshold
        
        detection = await self.detector.detect_underperformance(good_strategy)
        
        if detection is not None:
            # Should recommend monitoring for minor issues
            assert detection.recommendations.immediate_action in [
                RecommendedAction.MONITOR,
                RecommendedAction.REDUCE_ALLOCATION
            ]
    
    @pytest.mark.asyncio
    async def test_automatic_actions_determination(self, poor_strategy):
        """Test determination of automatic actions."""
        detection = await self.detector.detect_underperformance(poor_strategy)
        
        assert detection is not None
        
        # Check automatic actions based on severity
        if detection.severity.level == SeverityLevel.CRITICAL:
            assert detection.automatic_actions.suspension_triggered
            assert detection.automatic_actions.manual_review_required
            assert len(detection.automatic_actions.alerts_sent) > 0
    
    @pytest.mark.asyncio
    async def test_create_rehabilitation_plan(self, poor_strategy):
        """Test creation of rehabilitation plan."""
        detection = await self.detector.detect_underperformance(poor_strategy)
        
        if detection and detection.recommendations.rehabilitation_plan:
            plan = detection.recommendations.rehabilitation_plan
            
            assert plan.strategy_id == poor_strategy.strategy_id
            assert plan.suspension_period > 0
            assert len(plan.monitoring_metrics) > 0
            assert len(plan.recovery_thresholds) > 0
            assert len(plan.evaluation_schedule) > 0
            assert len(plan.gradual_return_steps) > 0
    
    def test_create_performance_issue(self):
        """Test creation of performance issue objects."""
        # Mock strategy for trend determination
        with patch.object(self.detector, '_determine_performance_trend', return_value=TrendDirection.DECLINING):
            issue = self.detector._create_performance_issue(
                PerformanceIssueType.HIGH_DRAWDOWN,
                "Test drawdown issue",
                Decimal('0.25'),
                Decimal('0.15'),
                Decimal('0.15'),
                None  # Mock strategy
            )
        
        assert issue.issue_type == PerformanceIssueType.HIGH_DRAWDOWN
        assert issue.current_value == Decimal('0.25')
        assert issue.expected_value == Decimal('0.15')
        assert issue.threshold == Decimal('0.15')
        assert issue.deviation_magnitude > Decimal('0')
        assert issue.severity in [SeverityLevel.MINOR, SeverityLevel.MODERATE, SeverityLevel.SEVERE]
    
    @pytest.mark.asyncio
    async def test_update_rehabilitation_progress(self):
        """Test updating rehabilitation plan progress."""
        from agents.strategy_analysis.app.models import RehabilitationPlan, RecoveryPhase
        
        plan = RehabilitationPlan(
            plan_id="test_plan",
            strategy_id="test_strategy",
            suspension_period=30,
            monitoring_metrics=["sharpe_ratio", "max_drawdown"],
            recovery_thresholds={"sharpe_ratio": Decimal('0.8'), "max_drawdown": Decimal('0.12')},
            evaluation_schedule=[7, 14, 30],
            current_phase=RecoveryPhase.SUSPENDED,
            progress_score=Decimal('0'),
            metrics_improvement={},
            time_to_full_recovery=60,
            minimum_performance_period=30,
            required_metrics={"sharpe_ratio": Decimal('0.8'), "max_drawdown": Decimal('0.12')},
            manual_approval_required=False,
            gradual_return_steps=[Decimal('0.25'), Decimal('0.5'), Decimal('0.75'), Decimal('1.0')]
        )
        
        # Simulate improved performance
        current_performance = {
            "sharpe_ratio": Decimal('0.9'),  # Above threshold
            "max_drawdown": Decimal('0.10')  # Below threshold (good)
        }
        
        updated_plan = await self.detector.update_rehabilitation_progress(plan, current_performance)
        
        assert updated_plan.progress_score > Decimal('0')
        assert updated_plan.current_phase != RecoveryPhase.SUSPENDED  # Should advance
        assert len(updated_plan.metrics_improvement) > 0
    
    @pytest.mark.asyncio
    async def test_check_performance_consistency(self, poor_strategy):
        """Test performance consistency checking."""
        # Add mock time-based performance with high variability
        from agents.strategy_analysis.app.models import MonthlyPerformance
        
        # Create inconsistent monthly performance
        monthly_data = {}
        for i in range(6):
            month = f"2024-{i+1:02d}"
            # Alternate between very good and very bad months
            pnl = Decimal('1000') if i % 2 == 0 else Decimal('-800')
            monthly_data[month] = MonthlyPerformance(
                month=month,
                trades=20,
                pnl=pnl,
                win_rate=Decimal('0.6') if pnl > 0 else Decimal('0.3'),
                sharpe_ratio=Decimal('1.5') if pnl > 0 else Decimal('-0.5'),
                max_drawdown=Decimal('0.05') if pnl > 0 else Decimal('0.25')
            )
        
        poor_strategy.performance.time_based.monthly = monthly_data
        
        consistency_issue = await self.detector._check_performance_consistency(poor_strategy)
        
        if consistency_issue:
            assert consistency_issue.issue_type == PerformanceIssueType.INCONSISTENT_PERFORMANCE
            assert consistency_issue.current_value > Decimal('1.0')  # High CV