"""
Continuous Improvement Pipeline Orchestrator

The central coordination engine that manages the entire continuous improvement
lifecycle - from suggestion generation through testing, rollout, and deployment.
This is the brain of the self-improving trading system.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Optional, Any
from dataclasses import asdict

from .models import (
    ContinuousImprovementPipeline, ImprovementTest, ImprovementSuggestion,
    TestPhase, TestDecision, ImprovementCycleResults, TestUpdate,
    RollbackDecision, RollbackResult, StageDecision, PerformanceComparison,
    PipelineStatus, PipelineMetrics, TestConfiguration, SuggestionStatus,
    Priority, RiskLevel
)

# Import data interfaces
from ...src.shared.python_utils.data_interfaces import (
    TradeDataInterface, MockTradeDataProvider,
    PerformanceDataInterface, MockPerformanceDataProvider
)

logger = logging.getLogger(__name__)


class ContinuousImprovementOrchestrator:
    """
    Main orchestrator for the continuous improvement pipeline.
    
    Coordinates all aspects of improvement testing including:
    - Suggestion evaluation and prioritization
    - Test creation and lifecycle management  
    - Shadow testing and gradual rollouts
    - Performance monitoring and decision making
    - Automatic rollbacks and safety mechanisms
    - Reporting and analytics
    """
    
    def __init__(self,
                 trade_data_provider: Optional[TradeDataInterface] = None,
                 performance_data_provider: Optional[PerformanceDataInterface] = None):
        self.trade_data_provider = trade_data_provider or MockTradeDataProvider()
        self.performance_data_provider = performance_data_provider or MockPerformanceDataProvider()
        
        # Initialize pipeline
        self.pipeline = ContinuousImprovementPipeline()
        
        # Component managers (will be injected)
        self.shadow_tester = None  # ShadowTestingEngine
        self.rollout_manager = None  # GradualRolloutManager
        self.performance_comparator = None  # PerformanceComparator
        self.rollback_manager = None  # AutomaticRollbackManager
        self.suggestion_engine = None  # ImprovementSuggestionEngine
        self.report_generator = None  # OptimizationReportGenerator
        
        # Internal state
        self._running = False
        self._cycle_count = 0
        self._last_cycle_time = None
        
        logger.info("Continuous Improvement Orchestrator initialized")
    
    def set_components(self, **components):
        """Inject component managers (dependency injection)"""
        for name, component in components.items():
            setattr(self, name, component)
            logger.info(f"Injected component: {name}")
    
    async def start_pipeline(self) -> bool:
        """Start the continuous improvement pipeline"""
        if self._running:
            logger.warning("Pipeline is already running")
            return False
        
        try:
            logger.info("Starting Continuous Improvement Pipeline")
            
            # Initialize components
            await self._initialize_components()
            
            # Validate configuration
            if not await self._validate_configuration():
                logger.error("Pipeline configuration validation failed")
                return False
            
            # Load existing state
            await self._load_pipeline_state()
            
            # Start main execution loop
            self._running = True
            
            logger.info("Continuous Improvement Pipeline started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start pipeline: {e}")
            self._running = False
            return False
    
    async def stop_pipeline(self) -> bool:
        """Stop the continuous improvement pipeline"""
        if not self._running:
            logger.warning("Pipeline is not running")
            return False
        
        try:
            logger.info("Stopping Continuous Improvement Pipeline")
            
            # Complete current cycle
            if self._last_cycle_time:
                await self._complete_current_cycle()
            
            # Save pipeline state
            await self._save_pipeline_state()
            
            # Stop components
            await self._shutdown_components()
            
            self._running = False
            
            logger.info("Continuous Improvement Pipeline stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop pipeline gracefully: {e}")
            self._running = False
            return False
    
    async def execute_improvement_cycle(self) -> ImprovementCycleResults:
        """
        Execute one complete improvement cycle.
        
        This is the main orchestration method that coordinates all pipeline activities:
        1. Process pending suggestions
        2. Update active tests
        3. Generate new suggestions
        4. Check rollback conditions
        5. Update pipeline metrics
        """
        cycle_start = datetime.utcnow()
        results = ImprovementCycleResults()
        
        try:
            logger.info(f"Starting improvement cycle #{self._cycle_count + 1}")
            
            # 1. Process pending suggestions
            await self._process_pending_suggestions(results)
            
            # 2. Update active tests
            await self._update_active_tests(results)
            
            # 3. Generate new suggestions
            if self.suggestion_engine:
                await self._generate_new_suggestions(results)
            
            # 4. Check rollback conditions
            await self._check_rollback_conditions(results)
            
            # 5. Update pipeline metrics
            await self._update_pipeline_metrics()
            
            # 6. Cleanup completed tests
            await self._cleanup_completed_tests()
            
            cycle_duration = datetime.utcnow() - cycle_start
            results.cycle_duration = cycle_duration
            results.success = True
            results.summary = f"Cycle completed successfully in {cycle_duration.total_seconds():.2f}s"
            
            self._cycle_count += 1
            self._last_cycle_time = datetime.utcnow()
            
            logger.info(f"Improvement cycle completed: {results.summary}")
            
        except Exception as e:
            logger.error(f"Improvement cycle failed: {e}")
            results.success = False
            results.errors_encountered.append(str(e))
            results.summary = f"Cycle failed: {e}"
        
        # Update pipeline status
        self.pipeline.status.last_run = datetime.utcnow()
        await self._save_pipeline_state()
        
        return results
    
    async def _process_pending_suggestions(self, results: ImprovementCycleResults):
        """Process and evaluate pending improvement suggestions"""
        logger.debug("Processing pending suggestions")
        
        pending_suggestions = [s for s in self.pipeline.pending_suggestions 
                             if s.status == SuggestionStatus.PENDING]
        
        for suggestion in pending_suggestions:
            try:
                if await self._should_test_suggestion(suggestion):
                    test = await self._create_improvement_test(suggestion)
                    if test:
                        self.pipeline.active_improvements.append(test)
                        results.new_tests_created.append(test.test_id)
                        
                        # Update suggestion status
                        suggestion.status = SuggestionStatus.TESTING
                        suggestion.implementation_date = datetime.utcnow()
                        
                        logger.info(f"Created test {test.test_id} for suggestion {suggestion.suggestion_id}")
                
            except Exception as e:
                logger.error(f"Failed to process suggestion {suggestion.suggestion_id}: {e}")
                results.errors_encountered.append(f"Suggestion {suggestion.suggestion_id}: {e}")
    
    async def _update_active_tests(self, results: ImprovementCycleResults):
        """Update progress for all active improvement tests"""
        logger.debug("Updating active tests")
        
        active_tests = [t for t in self.pipeline.active_improvements 
                       if t.current_phase not in [TestPhase.COMPLETED, TestPhase.ROLLED_BACK]]
        
        for test in active_tests:
            try:
                update = await self._update_test_progress(test)
                if update.status != 'no_update':
                    results.test_updates.append(update.test_id)
                    logger.info(f"Updated test {test.test_id}: {update.status}")
                
            except Exception as e:
                logger.error(f"Failed to update test {test.test_id}: {e}")
                results.errors_encountered.append(f"Test {test.test_id}: {e}")
    
    async def _update_test_progress(self, test: ImprovementTest) -> TestUpdate:
        """Update progress for a specific improvement test"""
        current_phase = test.current_phase
        
        if current_phase == TestPhase.SHADOW:
            return await self._update_shadow_test(test)
        elif current_phase.value.startswith('rollout_'):
            return await self._update_rollout_test(test)
        else:
            return TestUpdate(test_id=test.test_id, status='no_update')
    
    async def _update_shadow_test(self, test: ImprovementTest) -> TestUpdate:
        """Update a test in shadow testing phase"""
        if not self.shadow_tester:
            return TestUpdate(test_id=test.test_id, status='shadow_tester_unavailable')
        
        # Check if shadow test is complete
        shadow_complete = await self._is_shadow_test_complete(test)
        
        if shadow_complete:
            # Evaluate shadow test results
            shadow_results = await self.shadow_tester.evaluate_shadow_test(test)
            test.shadow_results = shadow_results
            
            if shadow_results.validation_passed:
                # Advance to first rollout stage
                test.current_phase = TestPhase.ROLLOUT_10
                test.current_stage_start = datetime.utcnow()
                
                logger.info(f"Test {test.test_id} advanced from shadow to rollout_10")
                return TestUpdate(
                    test_id=test.test_id,
                    status='advanced_to_rollout',
                    new_phase=TestPhase.ROLLOUT_10
                )
            else:
                # Shadow test failed - rollback
                await self._initiate_rollback(test, "Shadow test validation failed")
                return TestUpdate(
                    test_id=test.test_id,
                    status='rolled_back',
                    reason="Shadow test validation failed"
                )
        
        return TestUpdate(test_id=test.test_id, status='shadow_in_progress')
    
    async def _update_rollout_test(self, test: ImprovementTest) -> TestUpdate:
        """Update a test in rollout phase"""
        if not self.performance_comparator or not self.rollout_manager:
            return TestUpdate(test_id=test.test_id, status='components_unavailable')
        
        # Get current stage performance
        performance_comparison = await self.performance_comparator.compare_groups(
            test.control_group, test.treatment_group
        )
        
        # Check if stage is complete
        stage_complete = await self._is_stage_complete(test)
        
        if stage_complete:
            # Make stage decision
            decision = await self._make_stage_decision(performance_comparison, test)
            
            if decision.decision == TestDecision.ADVANCE:
                next_phase = await self._get_next_phase(test.current_phase)
                if next_phase:
                    test.current_phase = next_phase
                    test.current_stage_start = datetime.utcnow()
                    
                    logger.info(f"Test {test.test_id} advanced to {next_phase.value}")
                    return TestUpdate(
                        test_id=test.test_id,
                        status='advanced',
                        new_phase=next_phase,
                        performance=performance_comparison
                    )
                else:
                    # Test complete - full deployment
                    test.current_phase = TestPhase.COMPLETED
                    test.actual_completion = datetime.utcnow()
                    test.final_results = performance_comparison
                    
                    logger.info(f"Test {test.test_id} completed successfully")
                    return TestUpdate(
                        test_id=test.test_id,
                        status='completed',
                        performance=performance_comparison
                    )
            
            elif decision.decision == TestDecision.ROLLBACK:
                await self._initiate_rollback(test, decision.reason)
                return TestUpdate(
                    test_id=test.test_id,
                    status='rolled_back',
                    reason=decision.reason
                )
            
            elif decision.decision == TestDecision.MANUAL_REVIEW:
                test.human_review_required = True
                return TestUpdate(
                    test_id=test.test_id,
                    status='manual_review_required',
                    reason=decision.reason
                )
        
        return TestUpdate(
            test_id=test.test_id,
            status='rollout_in_progress',
            performance=performance_comparison
        )
    
    async def _make_stage_decision(self, performance: PerformanceComparison, 
                                 test: ImprovementTest) -> StageDecision:
        """Make decision for stage progression"""
        
        # Check for automatic rollback conditions
        if performance.relative_improvement < self.pipeline.configuration.rollback_threshold:
            return StageDecision(
                decision=TestDecision.ROLLBACK,
                reason=f"Treatment group underperforming by {performance.relative_improvement:.1%}",
                decision_maker='automatic',
                performance_data=performance
            )
        
        # Check statistical significance for advancement
        if performance.statistical_analysis.statistically_significant:
            min_improvement = Decimal('0.02')  # 2% minimum improvement
            if performance.relative_improvement > min_improvement:
                return StageDecision(
                    decision=TestDecision.ADVANCE,
                    reason=f"Statistically significant improvement of {performance.relative_improvement:.1%}",
                    decision_maker='automatic',
                    performance_data=performance,
                    confidence_level=performance.statistical_analysis.confidence_level
                )
        
        # Check if more time/data needed
        if not await self._sufficient_sample_size(test):
            return StageDecision(
                decision=TestDecision.HOLD,
                reason="Insufficient sample size for statistical significance",
                decision_maker='automatic'
            )
        
        # Default to manual review for edge cases
        return StageDecision(
            decision=TestDecision.MANUAL_REVIEW,
            reason="Manual review required for advancement decision",
            decision_maker='manual',
            performance_data=performance
        )
    
    async def _generate_new_suggestions(self, results: ImprovementCycleResults):
        """Generate new improvement suggestions"""
        if not self.suggestion_engine:
            return
        
        try:
            logger.debug("Generating new improvement suggestions")
            
            new_suggestions = await self.suggestion_engine.generate_suggestions()
            
            for suggestion in new_suggestions:
                # Add to pipeline
                self.pipeline.pending_suggestions.append(suggestion)
                results.new_suggestions.append(suggestion.suggestion_id)
            
            if new_suggestions:
                logger.info(f"Generated {len(new_suggestions)} new improvement suggestions")
            
        except Exception as e:
            logger.error(f"Failed to generate suggestions: {e}")
            results.errors_encountered.append(f"Suggestion generation: {e}")
    
    async def _check_rollback_conditions(self, results: ImprovementCycleResults):
        """Check for automatic rollback conditions across all tests"""
        if not self.rollback_manager:
            return
        
        active_tests = [t for t in self.pipeline.active_improvements 
                       if t.current_phase not in [TestPhase.COMPLETED, TestPhase.ROLLED_BACK]]
        
        for test in active_tests:
            try:
                rollback_decision = await self.rollback_manager.check_rollback_conditions(test)
                
                if rollback_decision:
                    await self._execute_rollback(rollback_decision)
                    results.rollback_actions.append(test.test_id)
                    logger.warning(f"Executed automatic rollback for test {test.test_id}")
                
            except Exception as e:
                logger.error(f"Failed to check rollback conditions for test {test.test_id}: {e}")
                results.errors_encountered.append(f"Rollback check {test.test_id}: {e}")
    
    async def _should_test_suggestion(self, suggestion: ImprovementSuggestion) -> bool:
        """Determine if a suggestion should be tested"""
        
        # Check priority threshold
        if suggestion.priority_score < 60.0:  # Below 60% priority
            return False
        
        # Check resource availability
        max_concurrent = self.pipeline.configuration.max_concurrent_tests
        current_active = len([t for t in self.pipeline.active_improvements 
                            if t.current_phase not in [TestPhase.COMPLETED, TestPhase.ROLLED_BACK]])
        
        if current_active >= max_concurrent:
            return False
        
        # Check risk level
        if suggestion.risk_level == RiskLevel.HIGH and suggestion.priority != Priority.CRITICAL:
            return False
        
        # Check for similar ongoing tests
        for test in self.pipeline.active_improvements:
            if (test.improvement_type == suggestion.suggestion_type and 
                test.current_phase not in [TestPhase.COMPLETED, TestPhase.ROLLED_BACK]):
                return False  # Don't test similar improvements simultaneously
        
        return True
    
    async def _create_improvement_test(self, suggestion: ImprovementSuggestion) -> Optional[ImprovementTest]:
        """Create a new improvement test from a suggestion"""
        try:
            test = ImprovementTest(
                improvement_type=suggestion.suggestion_type,
                name=suggestion.title,
                description=suggestion.description,
                hypothesis=suggestion.rationale,
                expected_impact=suggestion.description,
                risk_assessment=suggestion.risk_level.value,
                implementation_complexity=suggestion.implementation_effort
            )
            
            # Configure test parameters based on suggestion
            test.test_config = await self._create_test_configuration(suggestion)
            
            # Create test groups
            test.control_group, test.treatment_group = await self._create_test_groups(suggestion)
            
            # Set expected completion
            test.expected_completion = (datetime.utcnow() + 
                                      timedelta(days=test.test_config.test_duration))
            
            logger.info(f"Created improvement test {test.test_id} for suggestion {suggestion.suggestion_id}")
            return test
            
        except Exception as e:
            logger.error(f"Failed to create test for suggestion {suggestion.suggestion_id}: {e}")
            return None
    
    async def _create_test_configuration(self, suggestion: ImprovementSuggestion) -> TestConfiguration:
        """Create test configuration based on suggestion characteristics"""
        config = TestConfiguration()
        
        # Adjust parameters based on risk and complexity
        if suggestion.risk_level == RiskLevel.HIGH:
            config.test_duration = 45  # Longer testing for high risk
            config.minimum_sample_size = 200  # More data for validation
            config.significance_level = 0.01  # Higher confidence required
        elif suggestion.risk_level == RiskLevel.LOW:
            config.test_duration = 21  # Shorter testing for low risk
            config.minimum_sample_size = 75  # Less data required
        
        # Adjust for implementation complexity
        if suggestion.implementation_effort == suggestion.implementation_effort.HIGH:
            config.stage_validation_period = 10  # Longer validation periods
        
        return config
    
    async def _create_test_groups(self, suggestion: ImprovementSuggestion):
        """Create control and treatment groups for A/B testing"""
        # This is a placeholder - real implementation would:
        # 1. Get available accounts from account manager
        # 2. Ensure proper randomization and balance
        # 3. Apply stratification if needed
        # 4. Implement the actual changes for treatment group
        
        from .models import TestGroup, Change
        
        # Mock implementation
        control_group = TestGroup(
            group_type="control",
            accounts=["ACC001", "ACC002", "ACC003"],  # Mock accounts
            allocation_percentage=Decimal('50')
        )
        
        treatment_group = TestGroup(
            group_type="treatment", 
            accounts=["ACC004", "ACC005", "ACC006"],  # Mock accounts
            allocation_percentage=Decimal('50'),
            changes=[Change(
                component=suggestion.category,
                description=suggestion.description,
                expected_performance_change=suggestion.performance_gain_estimate
            )]
        )
        
        return control_group, treatment_group
    
    async def _initiate_rollback(self, test: ImprovementTest, reason: str):
        """Initiate rollback for a test"""
        logger.warning(f"Initiating rollback for test {test.test_id}: {reason}")
        
        test.current_phase = TestPhase.ROLLED_BACK
        test.rollback_reason = reason
        test.actual_completion = datetime.utcnow()
        
        # Execute actual rollback if rollback manager available
        if self.rollback_manager:
            rollback_decision = RollbackDecision(
                test_id=test.test_id,
                rollback_reason=reason,
                trigger_value=0.0,
                threshold=0.0,
                severity="automatic"
            )
            await self._execute_rollback(rollback_decision)
    
    async def _execute_rollback(self, rollback_decision: RollbackDecision):
        """Execute rollback using rollback manager"""
        if self.rollback_manager:
            result = await self.rollback_manager.execute_rollback(rollback_decision)
            logger.info(f"Rollback executed for {rollback_decision.test_id}: {result.rollback_successful}")
    
    async def _is_shadow_test_complete(self, test: ImprovementTest) -> bool:
        """Check if shadow test phase is complete"""
        if not test.shadow_results:
            return False
        
        # Check minimum duration
        min_duration = timedelta(days=7)  # Minimum 7 days of shadow testing
        if datetime.utcnow() - test.start_date < min_duration:
            return False
        
        # Check minimum sample size
        if test.shadow_results.trades_executed < test.test_config.minimum_sample_size:
            return False
        
        return True
    
    async def _is_stage_complete(self, test: ImprovementTest) -> bool:
        """Check if current rollout stage is complete"""
        # Check minimum duration
        min_duration = timedelta(days=test.test_config.stage_validation_period)
        if datetime.utcnow() - test.current_stage_start < min_duration:
            return False
        
        # Check minimum trades
        if (test.treatment_group and 
            test.treatment_group.trades_completed < test.test_config.min_trades_per_stage):
            return False
        
        return True
    
    async def _sufficient_sample_size(self, test: ImprovementTest) -> bool:
        """Check if sufficient sample size for statistical significance"""
        if not test.treatment_group:
            return False
        
        return test.treatment_group.trades_completed >= test.test_config.minimum_sample_size
    
    async def _get_next_phase(self, current_phase: TestPhase) -> Optional[TestPhase]:
        """Get the next phase in rollout progression"""
        phase_progression = {
            TestPhase.SHADOW: TestPhase.ROLLOUT_10,
            TestPhase.ROLLOUT_10: TestPhase.ROLLOUT_25,
            TestPhase.ROLLOUT_25: TestPhase.ROLLOUT_50,
            TestPhase.ROLLOUT_50: TestPhase.ROLLOUT_100,
            TestPhase.ROLLOUT_100: None  # Complete
        }
        return phase_progression.get(current_phase)
    
    async def _update_pipeline_metrics(self):
        """Update pipeline performance metrics"""
        # Calculate success rate
        completed_tests = [t for t in self.pipeline.active_improvements 
                          if t.current_phase == TestPhase.COMPLETED]
        rolled_back_tests = [t for t in self.pipeline.active_improvements 
                           if t.current_phase == TestPhase.ROLLED_BACK]
        
        total_finished = len(completed_tests) + len(rolled_back_tests)
        if total_finished > 0:
            self.pipeline.pipeline_metrics.improvement_success_rate = len(completed_tests) / total_finished
            self.pipeline.pipeline_metrics.rollback_rate = len(rolled_back_tests) / total_finished
        
        # Update status
        self.pipeline.status.improvements_in_testing = len([
            t for t in self.pipeline.active_improvements 
            if t.current_phase in [TestPhase.SHADOW, TestPhase.ROLLOUT_10, TestPhase.ROLLOUT_25, TestPhase.ROLLOUT_50]
        ])
        self.pipeline.status.successful_deployments = len(completed_tests)
        self.pipeline.status.rollbacks = len(rolled_back_tests)
        self.pipeline.status.pending_approvals = len([
            t for t in self.pipeline.active_improvements if t.human_review_required
        ])
    
    async def _cleanup_completed_tests(self):
        """Archive completed tests and clean up resources"""
        # Move old completed tests to archive (simplified)
        cutoff_date = datetime.utcnow() - timedelta(days=90)  # Archive after 90 days
        
        archived_count = 0
        for test in self.pipeline.active_improvements[:]:
            if (test.current_phase in [TestPhase.COMPLETED, TestPhase.ROLLED_BACK] and
                test.actual_completion and test.actual_completion < cutoff_date):
                # In real implementation, move to archive storage
                self.pipeline.active_improvements.remove(test)
                archived_count += 1
        
        if archived_count > 0:
            logger.info(f"Archived {archived_count} completed tests")
    
    async def _initialize_components(self):
        """Initialize pipeline components"""
        # Components will be injected via set_components()
        # This method can perform any component-specific initialization
        pass
    
    async def _validate_configuration(self) -> bool:
        """Validate pipeline configuration"""
        config = self.pipeline.configuration
        
        # Basic validation
        if config.rollback_threshold >= Decimal('0'):
            logger.error("Rollback threshold must be negative")
            return False
        
        if config.max_concurrent_tests <= 0:
            logger.error("Max concurrent tests must be positive")
            return False
        
        if not config.rollout_stages:
            logger.error("Rollout stages cannot be empty")
            return False
        
        return True
    
    async def _load_pipeline_state(self):
        """Load pipeline state from persistence"""
        # Placeholder - real implementation would load from database
        logger.info("Loading pipeline state")
    
    async def _save_pipeline_state(self):
        """Save pipeline state to persistence"""
        # Placeholder - real implementation would save to database
        self.pipeline.last_updated = datetime.utcnow()
        logger.debug("Pipeline state saved")
    
    async def _complete_current_cycle(self):
        """Complete any in-progress cycle"""
        logger.info("Completing current improvement cycle")
    
    async def _shutdown_components(self):
        """Shutdown pipeline components"""
        logger.info("Shutting down pipeline components")
    
    # Public API methods
    
    async def get_pipeline_status(self) -> Dict[str, Any]:
        """Get current pipeline status"""
        return {
            'pipeline_id': self.pipeline.pipeline_id,
            'running': self._running,
            'cycle_count': self._cycle_count,
            'last_cycle': self._last_cycle_time,
            'status': asdict(self.pipeline.status),
            'metrics': asdict(self.pipeline.pipeline_metrics),
            'active_tests': len(self.pipeline.active_improvements),
            'pending_suggestions': len(self.pipeline.pending_suggestions)
        }
    
    async def get_active_tests(self) -> List[Dict[str, Any]]:
        """Get list of active improvement tests"""
        return [
            {
                'test_id': test.test_id,
                'name': test.name,
                'phase': test.current_phase.value,
                'start_date': test.start_date,
                'expected_completion': test.expected_completion,
                'improvement_type': test.improvement_type.value
            }
            for test in self.pipeline.active_improvements
            if test.current_phase not in [TestPhase.COMPLETED, TestPhase.ROLLED_BACK]
        ]
    
    async def approve_test_advancement(self, test_id: str, approver: str, notes: str = "") -> bool:
        """Manually approve test advancement"""
        test = next((t for t in self.pipeline.active_improvements if t.test_id == test_id), None)
        if not test:
            return False
        
        from .models import Approval
        approval = Approval(
            approver=approver,
            approval_type="stage_advancement",
            approved=True,
            notes=notes
        )
        
        test.approvals.append(approval)
        test.human_review_required = False
        
        logger.info(f"Test {test_id} approved for advancement by {approver}")
        return True
    
    async def emergency_stop_test(self, test_id: str, reason: str) -> bool:
        """Emergency stop for a specific test"""
        test = next((t for t in self.pipeline.active_improvements if t.test_id == test_id), None)
        if not test:
            return False
        
        await self._initiate_rollback(test, f"Emergency stop: {reason}")
        logger.warning(f"Emergency stop executed for test {test_id}: {reason}")
        return True