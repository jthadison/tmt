"""
Integration tests for the complete Continuous Improvement Pipeline
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch

import sys
import os
from pathlib import Path

# Setup proper import paths
project_root = Path(__file__).parent.parent.parent.parent
app_dir = Path(__file__).parent.parent / "app"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(app_dir))

# Import test components that work without relative import issues
from test_components import (
    ContinuousImprovementOrchestrator,
    ShadowTestingEngine,
    GradualRolloutManager,
    PerformanceComparator,
    AutomaticRollbackManager,
    ImprovementSuggestionEngine,
    OptimizationReportGenerator
)

# Import models from local copy to avoid relative import issues
from models import (
    ImprovementTest, ImprovementSuggestion, TestPhase, ImprovementType,
    Priority, RiskLevel, ImplementationComplexity, SuggestionStatus,
    TestGroup, Change, PerformanceMetrics, PerformanceComparison,
    StatisticalAnalysis, ShadowTestResults, TestDecision
)


class TestContinuousImprovementIntegration:
    """Integration tests for the complete continuous improvement pipeline"""
    
    @pytest.fixture
    async def full_pipeline(self):
        """Create a fully configured pipeline with all components"""
        orchestrator = ContinuousImprovementOrchestrator()
        
        # Create all components
        shadow_tester = ShadowTestingEngine()
        rollout_manager = GradualRolloutManager()
        performance_comparator = PerformanceComparator()
        rollback_manager = AutomaticRollbackManager()
        suggestion_engine = ImprovementSuggestionEngine()
        report_generator = OptimizationReportGenerator()
        
        # Inject components
        orchestrator.set_components(
            shadow_tester=shadow_tester,
            rollout_manager=rollout_manager,
            performance_comparator=performance_comparator,
            rollback_manager=rollback_manager,
            suggestion_engine=suggestion_engine,
            report_generator=report_generator
        )
        
        await orchestrator.start_pipeline()
        return orchestrator
    
    @pytest.fixture
    def high_priority_suggestion(self):
        """Create a high-priority improvement suggestion"""
        return ImprovementSuggestion(
            title="Critical EURUSD Optimization",
            description="Optimize EURUSD entry criteria for better performance",
            rationale="Analysis shows 15% underperformance in EURUSD trades",
            suggestion_type=ImprovementType.PARAMETER_OPTIMIZATION,
            category="currency_optimization",
            expected_impact="significant",
            risk_level=RiskLevel.MEDIUM,
            implementation_effort=ImplementationComplexity.MEDIUM,
            priority=Priority.HIGH,
            priority_score=85.0,
            evidence_strength="strong"
        )
    
    @pytest.mark.asyncio
    async def test_end_to_end_improvement_workflow(self, full_pipeline, high_priority_suggestion):
        """Test complete end-to-end improvement workflow"""
        orchestrator = full_pipeline
        
        # Add high-priority suggestion to pipeline
        orchestrator.pipeline.pending_suggestions.append(high_priority_suggestion)
        
        # Execute improvement cycle
        cycle_results = await orchestrator.execute_improvement_cycle()
        
        # Verify cycle executed successfully
        assert len(cycle_results.new_tests_created) > 0
        assert cycle_results.suggestions_generated > 0
        
        # Verify suggestion was processed
        assert high_priority_suggestion.status == SuggestionStatus.TESTING
        assert high_priority_suggestion.implementation_date is not None
        
        # Verify test was created
        assert len(orchestrator.pipeline.active_improvements) > 0
        created_test = orchestrator.pipeline.active_improvements[0]
        assert created_test.name == high_priority_suggestion.title
        assert created_test.current_phase == TestPhase.SHADOW
        
        # Verify test has proper structure
        assert created_test.control_group is not None
        assert created_test.treatment_group is not None
        assert len(created_test.treatment_group.accounts) > 0
        assert len(created_test.treatment_group.changes) > 0
    
    @pytest.mark.asyncio
    async def test_shadow_to_rollout_progression(self, full_pipeline):
        """Test progression from shadow testing to rollout phases"""
        orchestrator = full_pipeline
        
        # Create a test manually and simulate shadow completion
        test = ImprovementTest(
            name="Shadow to Rollout Test",
            description="Test shadow to rollout progression",
            improvement_type=ImprovementType.PARAMETER_OPTIMIZATION,
            current_phase=TestPhase.SHADOW
        )
        
        # Add proper test groups
        test.control_group = TestGroup(
            group_type="control",
            accounts=["CTL001", "CTL002"],
            allocation_percentage=Decimal('50')
        )
        
        test.treatment_group = TestGroup(
            group_type="treatment",
            accounts=["TRT001", "TRT002"],
            allocation_percentage=Decimal('50'),
            changes=[Change(component="test_component", description="Test change")]
        )
        
        orchestrator.pipeline.active_improvements.append(test)
        
        # Mock shadow test completion with positive results
        with patch.object(orchestrator, '_is_shadow_test_complete', return_value=True):
            with patch.object(orchestrator.shadow_tester, 'evaluate_shadow_test') as mock_eval:
                from models import ShadowTestResults
                mock_eval.return_value = ShadowTestResults(
                    test_id=test.test_id,
                    start_date=datetime.utcnow() - timedelta(days=7),
                    end_date=datetime.utcnow(),
                    duration=timedelta(days=7),
                    validation_passed=True,
                    recommendation="proceed"
                )
                
                # Update the test
                update_result = await orchestrator._update_shadow_test(test)
                
                # Verify progression to rollout
                assert update_result.status == 'advanced_to_rollout'
                assert test.current_phase == TestPhase.ROLLOUT_10
                assert test.shadow_results is not None
                assert test.shadow_results.validation_passed is True
    
    @pytest.mark.asyncio
    async def test_rollback_trigger_and_execution(self, full_pipeline):
        """Test automatic rollback trigger and execution"""
        orchestrator = full_pipeline
        rollback_manager = orchestrator.rollback_manager
        
        # Create a test in rollout phase
        test = ImprovementTest(
            name="Rollback Test",
            description="Test automatic rollback functionality",
            improvement_type=ImprovementType.PARAMETER_OPTIMIZATION,
            current_phase=TestPhase.ROLLOUT_25,
            current_stage_start=datetime.utcnow() - timedelta(hours=3)  # Running for a while
        )
        
        # Add test groups with sufficient trades
        test.control_group = TestGroup(
            group_type="control",
            accounts=["CTL001"],
            trades_completed=50
        )
        
        test.treatment_group = TestGroup(
            group_type="treatment",
            accounts=["TRT001"],
            trades_completed=50
        )
        
        # Mock poor performance comparison
        with patch.object(orchestrator, '_get_current_performance') as mock_perf:
            from models import PerformanceComparison, StatisticalAnalysis
            mock_perf.return_value = PerformanceComparison(
                control_performance=PerformanceMetrics(expectancy=Decimal('0.01')),
                treatment_performance=PerformanceMetrics(expectancy=Decimal('-0.005')),
                relative_improvement=Decimal('-0.15'),  # 15% underperformance
                absolute_difference=Decimal('-0.015'),
                percentage_improvement=Decimal('-15'),
                statistical_analysis=StatisticalAnalysis(
                    sample_size=50,
                    power_analysis=0.8,
                    p_value=0.02,
                    confidence_interval=(-0.2, -0.1),
                    effect_size=0.8,
                    statistically_significant=True
                ),
                risk_adjusted_improvement=Decimal('-0.15')
            )
            
            # Check rollback conditions
            rollback_decision = await rollback_manager.check_rollback_conditions(test)
            
            # Verify rollback was triggered
            assert rollback_decision is not None
            assert rollback_decision.severity in ["automatic", "emergency"]
            assert "threshold" in rollback_decision.rollback_reason.lower()
            
            # Execute the rollback
            rollback_result = await rollback_manager.execute_rollback(rollback_decision)
            
            # Verify rollback execution
            assert rollback_result.rollback_successful is True
            assert rollback_result.test_id == test.test_id
    
    @pytest.mark.asyncio
    async def test_suggestion_generation_and_prioritization(self, full_pipeline):
        """Test improvement suggestion generation and prioritization"""
        orchestrator = full_pipeline
        suggestion_engine = orchestrator.suggestion_engine
        
        # Mock performance data indicating improvement opportunities
        with patch.object(suggestion_engine.performance_data_provider, 'get_system_performance') as mock_perf:
            mock_perf.return_value = PerformanceMetrics(
                total_trades=200,
                win_rate=Decimal('0.45'),  # Below benchmark
                profit_factor=Decimal('1.1'),  # Below benchmark
                sharpe_ratio=Decimal('0.6'),  # Below benchmark
                max_drawdown=Decimal('0.12'),  # Above threshold
                expectancy=Decimal('0.005')
            )
            
            # Generate suggestions
            suggestions = await suggestion_engine.generate_suggestions()
            
            # Verify suggestions were generated
            assert len(suggestions) > 0
            
            # Verify suggestions are properly prioritized
            for suggestion in suggestions:
                assert suggestion.priority_score > 0
                assert suggestion.suggestion_type in ImprovementType
                assert suggestion.risk_level in RiskLevel
                assert suggestion.implementation_effort in ImplementationComplexity
                
            # Verify highest priority suggestions come first
            sorted_suggestions = sorted(suggestions, key=lambda s: s.priority_score, reverse=True)
            assert suggestions == sorted_suggestions
    
    @pytest.mark.asyncio
    async def test_performance_comparison_statistical_validation(self, full_pipeline):
        """Test performance comparison with statistical validation"""
        orchestrator = full_pipeline
        comparator = orchestrator.performance_comparator
        
        # Create test groups
        control_group = TestGroup(
            group_type="control",
            accounts=["CTL001", "CTL002", "CTL003"]
        )
        
        treatment_group = TestGroup(
            group_type="treatment",
            accounts=["TRT001", "TRT002", "TRT003"]
        )
        
        # Mock performance data
        control_perf = PerformanceMetrics(
            total_trades=100,
            win_rate=Decimal('0.55'),
            expectancy=Decimal('0.01'),
            sharpe_ratio=Decimal('0.8'),
            max_drawdown=Decimal('0.08'),
            volatility=Decimal('0.015')
        )
        
        treatment_perf = PerformanceMetrics(
            total_trades=95,
            win_rate=Decimal('0.62'),
            expectancy=Decimal('0.018'),
            sharpe_ratio=Decimal('1.1'),
            max_drawdown=Decimal('0.06'),
            volatility=Decimal('0.012')
        )
        
        with patch.object(comparator, '_get_group_performance') as mock_get_perf:
            mock_get_perf.side_effect = [control_perf, treatment_perf]
            
            # Perform comparison
            comparison = await comparator.compare_groups(control_group, treatment_group)
            
            # Verify comprehensive comparison
            assert isinstance(comparison, PerformanceComparison)
            assert comparison.relative_improvement > Decimal('0.05')  # Significant improvement
            assert comparison.statistical_analysis.sample_size >= 95
            
            # Get recommendation
            summary = await comparator.get_comparison_summary(control_group, treatment_group)
            assert summary['recommendation'] in ['advance', 'caution']
            assert summary['relative_improvement'] > 0
    
    @pytest.mark.asyncio
    async def test_gradual_rollout_progression(self, full_pipeline):
        """Test gradual rollout progression through stages"""
        orchestrator = full_pipeline
        rollout_manager = orchestrator.rollout_manager
        
        # Create test for rollout
        test = ImprovementTest(
            name="Gradual Rollout Test",
            description="Test gradual rollout progression",
            improvement_type=ImprovementType.PARAMETER_OPTIMIZATION,
            current_phase=TestPhase.ROLLOUT_10
        )
        
        # Mock available accounts
        available_accounts = [f"ACC{i:03d}" for i in range(1, 101)]  # 100 accounts
        
        with patch.object(rollout_manager, '_get_available_accounts', return_value=available_accounts):
            # Start rollout at 10%
            rollout_result = await rollout_manager.start_rollout(test, 10)
            
            # Verify rollout started successfully
            assert rollout_result.stage == 10
            assert rollout_result.start_date is not None
            
            # Simulate positive performance to advance to next stage
            with patch.object(rollout_manager, '_evaluate_stage_performance') as mock_eval:
                mock_eval.return_value = {
                    'performance_threshold_met': True,
                    'statistical_significance': True,
                    'risk_acceptable': True,
                    'advance_recommended': True
                }
                
                # Advance to 25%
                advance_result = await rollout_manager.advance_to_next_stage(test)
                
                # Verify advancement decision
                assert advance_result.decision == TestDecision.ADVANCE
                assert advance_result.confidence_level > 0.5
    
    @pytest.mark.asyncio
    async def test_monthly_report_generation(self, full_pipeline):
        """Test monthly optimization report generation"""
        orchestrator = full_pipeline
        report_generator = orchestrator.report_generator
        
        # Mock some historical data
        with patch.object(report_generator.performance_data_provider, 'get_system_performance') as mock_perf:
            mock_perf.return_value = PerformanceMetrics(
                total_trades=300,
                win_rate=Decimal('0.58'),
                profit_factor=Decimal('1.35'),
                sharpe_ratio=Decimal('0.92'),
                max_drawdown=Decimal('0.075'),
                total_return=Decimal('0.12'),
                expectancy=Decimal('0.015')
            )
            
            # Generate monthly report
            report = await report_generator.generate_monthly_report()
            
            # Verify report structure
            assert 'report_metadata' in report
            assert 'executive_summary' in report
            assert 'performance_analysis' in report
            assert 'improvement_summary' in report
            assert 'roi_analysis' in report
            
            # Verify executive summary content
            exec_summary = report['executive_summary']
            assert 'key_highlights' in exec_summary
            assert 'performance_overview' in exec_summary
            assert 'optimization_metrics' in exec_summary
            
            # Verify performance analysis
            perf_analysis = report['performance_analysis']
            assert 'period_performance' in perf_analysis
            assert 'trend_analysis' in perf_analysis
            assert 'risk_metrics' in perf_analysis
    
    @pytest.mark.asyncio
    async def test_pipeline_safety_mechanisms(self, full_pipeline):
        """Test pipeline safety mechanisms and circuit breakers"""
        orchestrator = full_pipeline
        
        # Test maximum concurrent tests limit
        for i in range(10):  # Try to create more than max allowed
            suggestion = ImprovementSuggestion(
                title=f"Test Suggestion {i}",
                description=f"Test description {i}",
                rationale="Test rationale",
                suggestion_type=ImprovementType.PARAMETER_OPTIMIZATION,
                category="test",
                priority_score=80.0
            )
            orchestrator.pipeline.pending_suggestions.append(suggestion)
        
        # Execute cycle
        cycle_results = await orchestrator.execute_improvement_cycle()
        
        # Verify safety limits were respected
        max_concurrent = orchestrator.pipeline.configuration.max_concurrent_tests
        active_tests = len([
            t for t in orchestrator.pipeline.active_improvements
            if t.current_phase not in [TestPhase.COMPLETED, TestPhase.ROLLED_BACK]
        ])
        
        assert active_tests <= max_concurrent
        
        # Test emergency stop functionality
        if orchestrator.pipeline.active_improvements:
            test_to_stop = orchestrator.pipeline.active_improvements[0]
            
            stop_result = await orchestrator.emergency_stop_test(
                test_to_stop.test_id,
                "Safety test - emergency stop"
            )
            
            assert stop_result is True
            assert test_to_stop.current_phase == TestPhase.ROLLED_BACK
            assert "Emergency stop" in test_to_stop.rollback_reason
    
    @pytest.mark.asyncio
    async def test_pipeline_configuration_validation(self, full_pipeline):
        """Test pipeline configuration validation"""
        orchestrator = full_pipeline
        
        # Test valid configuration
        valid_result = await orchestrator._validate_configuration()
        assert valid_result is True
        
        # Test invalid rollback threshold
        original_threshold = orchestrator.pipeline.configuration.rollback_threshold
        orchestrator.pipeline.configuration.rollback_threshold = Decimal('0.10')  # Positive (invalid)
        
        invalid_result = await orchestrator._validate_configuration()
        assert invalid_result is False
        
        # Restore valid configuration
        orchestrator.pipeline.configuration.rollback_threshold = original_threshold
    
    @pytest.mark.asyncio
    async def test_component_dependency_injection(self, full_pipeline):
        """Test component dependency injection and integration"""
        orchestrator = full_pipeline
        
        # Verify all components were injected properly
        assert orchestrator.shadow_tester is not None
        assert orchestrator.rollout_manager is not None
        assert orchestrator.performance_comparator is not None
        assert orchestrator.rollback_manager is not None
        assert orchestrator.suggestion_engine is not None
        assert orchestrator.report_generator is not None
        
        # Test component replacement
        new_component = Mock()
        orchestrator.set_components(test_component=new_component)
        assert orchestrator.test_component == new_component


@pytest.mark.asyncio
async def test_complete_system_integration():
    """Complete system integration test simulating real-world usage"""
    
    # Initialize the complete system
    orchestrator = ContinuousImprovementOrchestrator()
    
    # Create and inject all components
    shadow_tester = ShadowTestingEngine()
    rollout_manager = GradualRolloutManager()
    performance_comparator = PerformanceComparator()
    rollback_manager = AutomaticRollbackManager()
    suggestion_engine = ImprovementSuggestionEngine()
    report_generator = OptimizationReportGenerator()
    
    orchestrator.set_components(
        shadow_tester=shadow_tester,
        rollout_manager=rollout_manager,
        performance_comparator=performance_comparator,
        rollback_manager=rollback_manager,
        suggestion_engine=suggestion_engine,
        report_generator=report_generator
    )
    
    # Start the pipeline
    start_result = await orchestrator.start_pipeline()
    assert start_result is True
    
    # Simulate multiple improvement cycles
    for cycle in range(3):
        # Add some suggestions
        suggestion = ImprovementSuggestion(
            title=f"Cycle {cycle} Optimization",
            description=f"Optimization suggestion for cycle {cycle}",
            rationale="Performance analysis indicates opportunity",
            suggestion_type=ImprovementType.PARAMETER_OPTIMIZATION,
            category=f"cycle_{cycle}",
            priority_score=70.0 + cycle * 5,  # Increasing priority
            risk_level=RiskLevel.MEDIUM,
            implementation_effort=ImplementationComplexity.MEDIUM
        )
        
        orchestrator.pipeline.pending_suggestions.append(suggestion)
        
        # Execute improvement cycle
        cycle_results = await orchestrator.execute_improvement_cycle()
        
        # Verify cycle executed successfully
        assert cycle_results.success is True
        
        # Check pipeline status
        status = await orchestrator.get_pipeline_status()
        assert status['running'] is True
        assert status['cycle_count'] == cycle + 1
    
    # Generate final report
    report = await report_generator.generate_monthly_report()
    assert 'executive_summary' in report
    assert 'improvement_summary' in report
    
    # Stop the pipeline
    stop_result = await orchestrator.stop_pipeline()
    assert stop_result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])