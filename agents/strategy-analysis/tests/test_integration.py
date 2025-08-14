"""
Integration tests for Strategy Analysis system.
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from agents.strategy_analysis.app.strategy_performance_analyzer import StrategyPerformanceAnalyzer, Trade
from agents.strategy_analysis.app.correlation_analyzer import CorrelationAnalyzer
from agents.strategy_analysis.app.underperformance_detector import UnderperformanceDetector
from agents.strategy_analysis.app.report_generator import ReportGenerator
from agents.strategy_analysis.app.strategy_controller import StrategyController
from agents.strategy_analysis.app.strategy_lifecycle import StrategyLifecycleManager

from agents.strategy_analysis.app.models import (
    TradingStrategy, StrategyType, StrategyStatus, StrategyConfiguration,
    StrategyClassification, StrategyLogic, StrategyLifecycle, StrategyComplexity,
    PerformanceMetrics, StrategyPerformance, StatisticalSignificance,
    TimeBasedPerformance, PerformanceTrend, TrendDirection
)


@pytest.fixture
def sample_strategies():
    """Create sample strategies for integration testing."""
    strategies = []
    
    # Strategy 1: High-performing trend follower
    perf1 = PerformanceMetrics(
        total_trades=150,
        win_count=90,
        loss_count=60,
        win_rate=Decimal('0.6'),
        profit_factor=Decimal('2.1'),
        expectancy=Decimal('0.008'),
        sharpe_ratio=Decimal('1.5'),
        calmar_ratio=Decimal('2.5'),
        max_drawdown=Decimal('0.08'),
        average_win=Decimal('200'),
        average_loss=Decimal('120'),
        average_hold_time=timedelta(hours=6),
        total_return=Decimal('0.18'),
        annualized_return=Decimal('0.35')
    )
    
    strategy1 = TradingStrategy(
        strategy_id="trend_follower_1",
        strategy_name="Momentum Trend Follower",
        version="2.1",
        classification=StrategyClassification(
            type=StrategyType.TREND_FOLLOWING,
            subtype="momentum",
            timeframe=["H4", "D1"],
            symbols=["EURUSD", "GBPUSD", "USDCAD"],
            market_regimes=[]
        ),
        logic=StrategyLogic(
            entry_conditions=["momentum_breakout", "volume_confirmation"],
            exit_conditions=["trend_reversal", "profit_target"],
            risk_management=["trailing_stop", "position_sizing"],
            signal_generation="technical_indicators",
            complexity=StrategyComplexity.MODERATE
        ),
        performance=StrategyPerformance(
            strategy_id="trend_follower_1",
            overall=perf1,
            significance=StatisticalSignificance(
                sample_size=150,
                confidence_level=Decimal('0.95'),
                p_value=Decimal('0.001'),
                confidence_interval=(Decimal('0.005'), Decimal('0.011')),
                statistically_significant=True,
                required_sample_size=30,
                current_significance_level=Decimal('0.999')
            ),
            time_based=TimeBasedPerformance(
                daily={}, weekly={}, monthly={},
                rolling_30_day=perf1,
                rolling_90_day=perf1,
                rolling_365_day=perf1
            ),
            regime_performance={},
            trend=PerformanceTrend(
                direction=TrendDirection.IMPROVING,
                trend_strength=Decimal('0.7'),
                trend_duration=45,
                change_rate=Decimal('0.0002'),
                projected_performance=Decimal('0.01')
            ),
            last_updated=datetime.utcnow()
        ),
        lifecycle=StrategyLifecycle(
            created_at=datetime.utcnow() - timedelta(days=180),
            activated_at=datetime.utcnow() - timedelta(days=150),
            last_modified=datetime.utcnow(),
            status=StrategyStatus.ACTIVE
        ),
        configuration=StrategyConfiguration(
            enabled=True,
            weight=Decimal('0.25'),
            max_allocation=Decimal('0.35'),
            min_trades_for_evaluation=50,
            evaluation_period=90
        )
    )
    strategies.append(strategy1)
    
    # Strategy 2: Moderate mean reversion strategy
    perf2 = PerformanceMetrics(
        total_trades=80,
        win_count=56,
        loss_count=24,
        win_rate=Decimal('0.7'),
        profit_factor=Decimal('1.4'),
        expectancy=Decimal('0.003'),
        sharpe_ratio=Decimal('0.9'),
        calmar_ratio=Decimal('1.2'),
        max_drawdown=Decimal('0.12'),
        average_win=Decimal('100'),
        average_loss=Decimal('180'),
        average_hold_time=timedelta(hours=3),
        total_return=Decimal('0.08'),
        annualized_return=Decimal('0.18')
    )
    
    strategy2 = TradingStrategy(
        strategy_id="mean_reversion_1",
        strategy_name="Oversold Bounce Strategy",
        version="1.5",
        classification=StrategyClassification(
            type=StrategyType.MEAN_REVERSION,
            subtype="oversold_bounce",
            timeframe=["H1", "H4"],
            symbols=["EURJPY", "GBPJPY"],
            market_regimes=[]
        ),
        logic=StrategyLogic(
            entry_conditions=["oversold_rsi", "support_level"],
            exit_conditions=["overbought_rsi", "resistance_level"],
            risk_management=["fixed_stop", "position_sizing"],
            signal_generation="oscillator_based",
            complexity=StrategyComplexity.SIMPLE
        ),
        performance=StrategyPerformance(
            strategy_id="mean_reversion_1",
            overall=perf2,
            significance=StatisticalSignificance(
                sample_size=80,
                confidence_level=Decimal('0.95'),
                p_value=Decimal('0.05'),
                confidence_interval=(Decimal('0.001'), Decimal('0.005')),
                statistically_significant=True,
                required_sample_size=30,
                current_significance_level=Decimal('0.95')
            ),
            time_based=TimeBasedPerformance(
                daily={}, weekly={}, monthly={},
                rolling_30_day=perf2,
                rolling_90_day=perf2,
                rolling_365_day=perf2
            ),
            regime_performance={},
            trend=PerformanceTrend(
                direction=TrendDirection.STABLE,
                trend_strength=Decimal('0.3'),
                trend_duration=20,
                change_rate=Decimal('0.00005'),
                projected_performance=Decimal('0.004')
            ),
            last_updated=datetime.utcnow()
        ),
        lifecycle=StrategyLifecycle(
            created_at=datetime.utcnow() - timedelta(days=120),
            activated_at=datetime.utcnow() - timedelta(days=100),
            last_modified=datetime.utcnow(),
            status=StrategyStatus.ACTIVE
        ),
        configuration=StrategyConfiguration(
            enabled=True,
            weight=Decimal('0.15'),
            max_allocation=Decimal('0.25'),
            min_trades_for_evaluation=30,
            evaluation_period=60
        )
    )
    strategies.append(strategy2)
    
    # Strategy 3: Underperforming breakout strategy
    perf3 = PerformanceMetrics(
        total_trades=45,
        win_count=12,
        loss_count=33,
        win_rate=Decimal('0.27'),
        profit_factor=Decimal('0.6'),
        expectancy=Decimal('-0.015'),
        sharpe_ratio=Decimal('-0.3'),
        calmar_ratio=Decimal('-0.8'),
        max_drawdown=Decimal('0.28'),
        average_win=Decimal('150'),
        average_loss=Decimal('80'),
        average_hold_time=timedelta(hours=8),
        total_return=Decimal('-0.12'),
        annualized_return=Decimal('-0.25')
    )
    
    strategy3 = TradingStrategy(
        strategy_id="breakout_1",
        strategy_name="Failed Breakout Strategy",
        version="1.0",
        classification=StrategyClassification(
            type=StrategyType.BREAKOUT,
            subtype="range_breakout",
            timeframe=["H4"],
            symbols=["USDCHF"],
            market_regimes=[]
        ),
        logic=StrategyLogic(
            entry_conditions=["range_breakout", "volume_spike"],
            exit_conditions=["false_breakout", "stop_loss"],
            risk_management=["tight_stops", "small_positions"],
            signal_generation="price_action",
            complexity=StrategyComplexity.COMPLEX
        ),
        performance=StrategyPerformance(
            strategy_id="breakout_1",
            overall=perf3,
            significance=StatisticalSignificance(
                sample_size=45,
                confidence_level=Decimal('0.95'),
                p_value=Decimal('0.12'),
                confidence_interval=(Decimal('-0.02'), Decimal('-0.01')),
                statistically_significant=True,
                required_sample_size=30,
                current_significance_level=Decimal('0.88')
            ),
            time_based=TimeBasedPerformance(
                daily={}, weekly={}, monthly={},
                rolling_30_day=perf3,
                rolling_90_day=perf3,
                rolling_365_day=perf3
            ),
            regime_performance={},
            trend=PerformanceTrend(
                direction=TrendDirection.DECLINING,
                trend_strength=Decimal('0.8'),
                trend_duration=60,
                change_rate=Decimal('-0.0005'),
                projected_performance=Decimal('-0.02')
            ),
            last_updated=datetime.utcnow()
        ),
        lifecycle=StrategyLifecycle(
            created_at=datetime.utcnow() - timedelta(days=90),
            activated_at=datetime.utcnow() - timedelta(days=75),
            last_modified=datetime.utcnow(),
            status=StrategyStatus.ACTIVE
        ),
        configuration=StrategyConfiguration(
            enabled=True,
            weight=Decimal('0.08'),
            max_allocation=Decimal('0.15'),
            min_trades_for_evaluation=30,
            evaluation_period=45
        )
    )
    strategies.append(strategy3)
    
    return strategies


class TestStrategyAnalysisIntegration:
    """Integration tests for the complete strategy analysis system."""
    
    def setup_method(self):
        """Setup test environment."""
        self.performance_analyzer = StrategyPerformanceAnalyzer()
        self.correlation_analyzer = CorrelationAnalyzer()
        self.underperformance_detector = UnderperformanceDetector()
        self.report_generator = ReportGenerator()
        self.strategy_controller = StrategyController()
        self.lifecycle_manager = StrategyLifecycleManager()
    
    @pytest.mark.asyncio
    async def test_full_analysis_pipeline(self, sample_strategies):
        """Test the complete analysis pipeline from performance to recommendations."""
        
        # Step 1: Analyze performance for each strategy
        for strategy in sample_strategies:
            # Mock trade data retrieval
            with patch.object(self.performance_analyzer, '_get_strategy_trades', return_value=[]):
                performance = await self.performance_analyzer.analyze_strategy_performance(
                    strategy.strategy_id, timedelta(days=90)
                )
                assert performance is not None
        
        # Step 2: Check for underperformance
        underperformance_results = []
        for strategy in sample_strategies:
            detection = await self.underperformance_detector.detect_underperformance(strategy)
            if detection:
                underperformance_results.append(detection)
        
        # Should detect the failing breakout strategy
        assert len(underperformance_results) >= 1
        failing_strategy_detected = any(
            result.strategy_id == "breakout_1" for result in underperformance_results
        )
        assert failing_strategy_detected
        
        # Step 3: Analyze correlations
        correlation_analysis = await self.correlation_analyzer.analyze_strategy_correlations(
            sample_strategies, timedelta(days=90)
        )
        assert correlation_analysis is not None
        assert len(correlation_analysis.correlation_matrix) == len(sample_strategies)
        
        # Step 4: Generate comprehensive report
        report = await self.report_generator.generate_weekly_report(sample_strategies)
        
        assert report is not None
        assert report.executive_summary.total_strategies == len(sample_strategies)
        assert len(report.rankings.by_performance) == len(sample_strategies)
        assert len(report.action_items.immediate) > 0  # Should have immediate actions
    
    @pytest.mark.asyncio
    async def test_underperformance_to_suspension_workflow(self, sample_strategies):
        """Test workflow from underperformance detection to strategy suspension."""
        
        # Find the underperforming strategy
        failing_strategy = next(s for s in sample_strategies if s.strategy_id == "breakout_1")
        
        # Step 1: Detect underperformance
        detection = await self.underperformance_detector.detect_underperformance(failing_strategy)
        
        assert detection is not None
        assert detection.strategy_id == "breakout_1"
        
        # Step 2: Check if automatic suspension is triggered
        suspension_reason = await self.lifecycle_manager.check_auto_suspension_triggers(failing_strategy)
        
        if suspension_reason:
            # Step 3: Suspend the strategy
            success = await self.lifecycle_manager.suspend_strategy(failing_strategy, suspension_reason)
            assert success
            assert failing_strategy.lifecycle.status == StrategyStatus.SUSPENDED
            assert not failing_strategy.configuration.enabled
    
    @pytest.mark.asyncio
    async def test_strategy_ranking_consistency(self, sample_strategies):
        """Test that strategy rankings are consistent across different metrics."""
        
        report = await self.report_generator.generate_weekly_report(sample_strategies)
        
        # Get rankings
        performance_rankings = report.rankings.by_performance
        risk_adjusted_rankings = report.rankings.by_risk_adjusted_return
        consistency_rankings = report.rankings.by_consistency
        
        # The trend follower should rank highly in most categories
        trend_follower_perf_rank = next(
            r.rank for r in performance_rankings if r.strategy_id == "trend_follower_1"
        )
        trend_follower_risk_rank = next(
            r.rank for r in risk_adjusted_rankings if r.strategy_id == "trend_follower_1"
        )
        
        # Should be top performer
        assert trend_follower_perf_rank <= 2
        assert trend_follower_risk_rank <= 2
        
        # The failing strategy should rank poorly
        failing_perf_rank = next(
            r.rank for r in performance_rankings if r.strategy_id == "breakout_1"
        )
        
        assert failing_perf_rank == len(sample_strategies)  # Should be last
    
    @pytest.mark.asyncio
    async def test_correlation_analysis_integration(self, sample_strategies):
        """Test integration of correlation analysis with portfolio recommendations."""
        
        # Analyze correlations
        correlation_analysis = await self.correlation_analyzer.analyze_strategy_correlations(
            sample_strategies, timedelta(days=90)
        )
        
        # Check correlation matrix completeness
        assert len(correlation_analysis.correlation_matrix) == len(sample_strategies)
        
        for strategy1 in sample_strategies:
            assert strategy1.strategy_id in correlation_analysis.correlation_matrix
            for strategy2 in sample_strategies:
                assert strategy2.strategy_id in correlation_analysis.correlation_matrix[strategy1.strategy_id]
                
                # Self-correlation should be 1.0
                if strategy1.strategy_id == strategy2.strategy_id:
                    self_corr = correlation_analysis.correlation_matrix[strategy1.strategy_id][strategy2.strategy_id]
                    assert self_corr == Decimal('1.0')
        
        # Check diversification analysis
        assert correlation_analysis.diversification_analysis is not None
        assert correlation_analysis.risk_concentration is not None
        
        # Generate recommendations based on correlation
        if correlation_analysis.risk_concentration.concentration_risk > Decimal('0.7'):
            # High concentration - should recommend diversification
            assert len(correlation_analysis.risk_concentration.redundant_strategies) > 0
    
    @pytest.mark.asyncio
    async def test_manual_control_integration(self, sample_strategies):
        """Test manual strategy control integration with the analysis system."""
        
        strategy = sample_strategies[0]  # Use the trend follower
        user_id = "test_user"
        
        # Test enable/disable cycle
        disable_result = await self.strategy_controller.disable_strategy(
            strategy, user_id, "Testing disable functionality"
        )
        
        assert disable_result['success']
        assert not strategy.configuration.enabled
        assert strategy.configuration.weight == Decimal('0')
        
        # Test re-enable
        enable_result = await self.strategy_controller.enable_strategy(
            strategy, user_id, "Testing enable functionality"
        )
        
        assert enable_result['success']
        assert strategy.configuration.enabled
        assert strategy.configuration.weight > Decimal('0')
        
        # Test allocation update
        allocation_result = await self.strategy_controller.update_allocation(
            strategy, Decimal('0.2'), user_id, "Testing allocation update"
        )
        
        assert allocation_result['success']
        assert strategy.configuration.weight == Decimal('0.2')
        
        # Test audit log
        audit_log = await self.strategy_controller.get_control_audit_log(
            strategy_id=strategy.strategy_id
        )
        
        assert len(audit_log) >= 3  # Should have disable, enable, and allocation entries
    
    @pytest.mark.asyncio
    async def test_lifecycle_management_integration(self, sample_strategies):
        """Test strategy lifecycle management integration."""
        
        # Test activation of a new strategy (mock)
        new_strategy = sample_strategies[1]  # Use mean reversion strategy
        new_strategy.lifecycle.status = StrategyStatus.TESTING
        
        # Mock backtest results
        backtest_results = {
            'performance': {
                'total_trades': 120,
                'sharpe_ratio': 1.1,
                'max_drawdown': 0.09,
                'profit_factor': 1.6,
                'win_rate': 0.58
            }
        }
        
        success = await self.lifecycle_manager.activate_strategy(new_strategy, backtest_results)
        
        assert success
        assert new_strategy.lifecycle.status == StrategyStatus.ACTIVE
        assert new_strategy.configuration.enabled
        
        # Test lifecycle summary
        summary = await self.lifecycle_manager.get_strategy_lifecycle_summary(new_strategy)
        
        assert summary['strategy_id'] == new_strategy.strategy_id
        assert summary['current_status'] == 'active'
        assert 'performance_summary' in summary
    
    @pytest.mark.asyncio
    async def test_report_generation_with_recommendations(self, sample_strategies):
        """Test that report generation includes actionable recommendations."""
        
        report = await self.report_generator.generate_weekly_report(sample_strategies)
        
        # Check executive summary
        exec_summary = report.executive_summary
        assert exec_summary.total_strategies == len(sample_strategies)
        assert exec_summary.active_strategies > 0
        assert len(exec_summary.top_performers) > 0
        assert len(exec_summary.underperformers) > 0
        
        # Check recommendations
        recommendations = report.recommendations
        
        # Should recommend suspending the failing strategy
        assert "breakout_1" in recommendations.strategies_to_suspend
        
        # Should have allocation changes
        assert len(recommendations.allocation_changes) > 0
        
        # Should identify strategy needs
        if exec_summary.diversification_score < Decimal('60'):
            assert len(recommendations.new_strategy_needs) > 0
        
        # Check action items
        action_items = report.action_items
        
        # Should have immediate actions for underperforming strategies
        if recommendations.strategies_to_suspend:
            immediate_actions = [item.description for item in action_items.immediate]
            suspension_action = any("suspend" in action.lower() for action in immediate_actions)
            assert suspension_action
    
    @pytest.mark.asyncio
    async def test_end_to_end_monitoring_cycle(self, sample_strategies):
        """Test a complete monitoring cycle from analysis to action."""
        
        # Step 1: Run performance analysis
        for strategy in sample_strategies:
            with patch.object(self.performance_analyzer, '_get_strategy_trades', return_value=[]):
                performance = await self.performance_analyzer.analyze_strategy_performance(
                    strategy.strategy_id, timedelta(days=30)
                )
        
        # Step 2: Check for underperformance and auto-suspension triggers
        actions_taken = []
        
        for strategy in sample_strategies:
            # Check underperformance
            detection = await self.underperformance_detector.detect_underperformance(strategy)
            
            if detection and detection.automatic_actions.suspension_triggered:
                # Auto-suspend strategy
                success = await self.lifecycle_manager.suspend_strategy(
                    strategy, f"Auto-suspension: {detection.severity.level.value}"
                )
                if success:
                    actions_taken.append(f"Suspended {strategy.strategy_id}")
            
            # Check other auto-suspension triggers
            suspension_reason = await self.lifecycle_manager.check_auto_suspension_triggers(strategy)
            if suspension_reason and strategy.lifecycle.status == StrategyStatus.ACTIVE:
                success = await self.lifecycle_manager.suspend_strategy(strategy, suspension_reason)
                if success:
                    actions_taken.append(f"Auto-suspended {strategy.strategy_id}: {suspension_reason}")
        
        # Step 3: Generate report with current state
        report = await self.report_generator.generate_weekly_report(sample_strategies)
        
        # Step 4: Verify monitoring cycle completed successfully
        assert report is not None
        
        # Should have taken action on the failing strategy
        failing_strategy_actions = [action for action in actions_taken if "breakout_1" in action]
        assert len(failing_strategy_actions) > 0
        
        # Report should reflect the actions taken
        suspended_count = len([s for s in sample_strategies if s.lifecycle.status == StrategyStatus.SUSPENDED])
        assert report.executive_summary.suspended_strategies == suspended_count