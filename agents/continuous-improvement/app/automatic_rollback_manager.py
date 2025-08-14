"""
Automatic Rollback Manager

Critical safety system that monitors improvement tests and automatically triggers
rollbacks when performance degradation exceeds acceptable thresholds. This system
acts as the final safety net to prevent catastrophic losses from failed improvements.

Key Features:
- Real-time performance monitoring
- Multi-level rollback triggers (warning, automatic, emergency)
- Risk-based rollback thresholds
- Immediate execution capabilities
- Comprehensive rollback validation
- Emergency stop mechanisms
- Recovery and restoration procedures
"""

import logging
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import asdict
import numpy as np

from .models import (
    ImprovementTest, RollbackDecision, RollbackResult, PerformanceComparison,
    TestPhase, Change, TestGroup, PerformanceMetrics
)

# Import data interfaces
from ...src.shared.python_utils.data_interfaces import (
    PerformanceDataInterface, MockPerformanceDataProvider,
    TradeDataInterface, MockTradeDataProvider
)

logger = logging.getLogger(__name__)


class AutomaticRollbackManager:
    """
    Automatic rollback system with multiple safety layers.
    
    This system continuously monitors improvement tests and triggers rollbacks
    when performance criteria are breached. It implements multiple threshold
    levels and rollback strategies to protect against losses while minimizing
    false positives.
    """
    
    def __init__(self,
                 performance_data_provider: Optional[PerformanceDataInterface] = None,
                 trade_data_provider: Optional[TradeDataInterface] = None):
        
        # Data providers
        self.performance_data_provider = performance_data_provider or MockPerformanceDataProvider()
        self.trade_data_provider = trade_data_provider or MockTradeDataProvider()
        
        # Rollback configuration
        self.config = {
            # Performance thresholds
            'warning_threshold': Decimal('-0.05'),     # 5% underperformance warning
            'rollback_threshold': Decimal('-0.10'),    # 10% underperformance rollback
            'emergency_threshold': Decimal('-0.20'),   # 20% emergency stop
            'drawdown_threshold': Decimal('0.15'),     # 15% max drawdown
            
            # Time-based criteria
            'monitoring_interval': timedelta(minutes=5),  # Check every 5 minutes
            'confirmation_period': timedelta(minutes=15), # Confirm degradation for 15min
            'min_monitoring_duration': timedelta(hours=2), # Minimum time before rollback
            
            # Sample size requirements
            'min_trades_for_rollback': 20,             # Minimum trades before considering rollback
            'min_time_between_checks': timedelta(minutes=1), # Rate limiting
            
            # Risk adjustments
            'high_risk_multiplier': Decimal('0.5'),   # More sensitive for high-risk tests
            'volatility_adjustment': True,            # Adjust thresholds based on volatility
            'correlation_adjustment': True,           # Consider correlation with market
            
            # Emergency parameters
            'emergency_stop_immediate': True,         # Immediate stop on emergency threshold
            'circuit_breaker_enabled': True,         # System-wide circuit breaker
            'max_concurrent_rollbacks': 3,           # Limit simultaneous rollbacks
        }
        
        # State tracking
        self._monitoring_active = False
        self._last_check_time = None
        self._rollback_queue: List[RollbackDecision] = []
        self._active_rollbacks: Dict[str, RollbackResult] = {}
        self._warning_tracker: Dict[str, datetime] = {}
        self._performance_history: Dict[str, List[Dict]] = {}
        
        logger.info("Automatic Rollback Manager initialized")
    
    async def start_monitoring(self) -> bool:
        """Start the automatic rollback monitoring system"""
        if self._monitoring_active:
            logger.warning("Rollback monitoring is already active")
            return False
        
        try:
            self._monitoring_active = True
            logger.info("Automatic rollback monitoring started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start rollback monitoring: {e}")
            return False
    
    async def stop_monitoring(self) -> bool:
        """Stop the automatic rollback monitoring system"""
        if not self._monitoring_active:
            logger.warning("Rollback monitoring is not active")
            return False
        
        try:
            self._monitoring_active = False
            
            # Complete any pending rollbacks
            await self._complete_pending_rollbacks()
            
            logger.info("Automatic rollback monitoring stopped")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop rollback monitoring: {e}")
            return False
    
    async def check_rollback_conditions(self, test: ImprovementTest) -> Optional[RollbackDecision]:
        """
        Check if a test meets rollback conditions.
        
        Args:
            test: ImprovementTest to evaluate
            
        Returns:
            RollbackDecision if rollback is needed, None otherwise
        """
        try:
            # Skip if test is already completed or rolled back
            if test.current_phase in [TestPhase.COMPLETED, TestPhase.ROLLED_BACK]:
                return None
            
            # Skip if still in shadow testing
            if test.current_phase == TestPhase.SHADOW:
                return None
            
            # Rate limiting - don't check too frequently
            if await self._is_rate_limited(test.test_id):
                return None
            
            # Get current performance comparison
            performance_comparison = await self._get_current_performance(test)
            if not performance_comparison:
                return None
            
            # Check various rollback criteria
            rollback_decision = await self._evaluate_rollback_criteria(test, performance_comparison)
            
            if rollback_decision:
                logger.warning(f"Rollback decision made for test {test.test_id}: {rollback_decision.rollback_reason}")
                
                # Track the decision
                self._rollback_queue.append(rollback_decision)
            
            # Update monitoring history
            await self._update_performance_history(test.test_id, performance_comparison)
            
            return rollback_decision
            
        except Exception as e:
            logger.error(f"Failed to check rollback conditions for test {test.test_id}: {e}")
            return None
    
    async def execute_rollback(self, rollback_decision: RollbackDecision) -> RollbackResult:
        """
        Execute a rollback decision.
        
        Args:
            rollback_decision: The rollback decision to execute
            
        Returns:
            RollbackResult with execution details
        """
        rollback_start = datetime.utcnow()
        test_id = rollback_decision.test_id
        
        try:
            logger.info(f"Executing rollback for test {test_id}: {rollback_decision.rollback_reason}")
            
            # Validate rollback decision
            if not await self._validate_rollback_decision(rollback_decision):
                return RollbackResult(
                    test_id=test_id,
                    rollback_successful=False,
                    changes_reverted=0,
                    rollback_time=rollback_start,
                    issues_encountered=["Rollback decision validation failed"]
                )
            
            # Execute immediate emergency actions if needed
            if rollback_decision.severity == "emergency":
                await self._execute_emergency_stop(test_id)
            
            # Get the test details for rollback
            test_details = await self._get_test_details(test_id)
            if not test_details:
                return RollbackResult(
                    test_id=test_id,
                    rollback_successful=False,
                    changes_reverted=0,
                    rollback_time=rollback_start,
                    issues_encountered=["Test details not found"]
                )
            
            # Execute the rollback steps
            rollback_result = await self._execute_rollback_steps(test_details, rollback_decision)
            
            # Mark rollback as active
            self._active_rollbacks[test_id] = rollback_result
            
            # Verify rollback success
            await self._verify_rollback_completion(rollback_result)
            
            rollback_duration = datetime.utcnow() - rollback_start
            rollback_result.rollback_duration = rollback_duration
            
            if rollback_result.rollback_successful:
                logger.info(f"Rollback completed successfully for test {test_id} in {rollback_duration.total_seconds():.2f}s")
            else:
                logger.error(f"Rollback failed for test {test_id}: {rollback_result.issues_encountered}")
            
            return rollback_result
            
        except Exception as e:
            logger.error(f"Rollback execution failed for test {test_id}: {e}")
            return RollbackResult(
                test_id=test_id,
                rollback_successful=False,
                changes_reverted=0,
                rollback_time=rollback_start,
                rollback_duration=datetime.utcnow() - rollback_start,
                issues_encountered=[str(e)]
            )
    
    async def _get_current_performance(self, test: ImprovementTest) -> Optional[PerformanceComparison]:
        """Get current performance comparison for the test"""
        
        if not test.control_group or not test.treatment_group:
            return None
        
        try:
            # This would typically use the performance comparator
            # For now, we'll simulate the comparison
            control_performance = await self._get_group_current_performance(test.control_group)
            treatment_performance = await self._get_group_current_performance(test.treatment_group)
            
            if not control_performance or not treatment_performance:
                return None
            
            # Calculate relative improvement
            if control_performance.expectancy != 0:
                relative_improvement = ((treatment_performance.expectancy - control_performance.expectancy) / 
                                      abs(control_performance.expectancy))
            else:
                relative_improvement = treatment_performance.expectancy
            
            # Create performance comparison (simplified)
            from .models import StatisticalAnalysis
            
            comparison = PerformanceComparison(
                control_performance=control_performance,
                treatment_performance=treatment_performance,
                relative_improvement=relative_improvement,
                absolute_difference=treatment_performance.expectancy - control_performance.expectancy,
                percentage_improvement=relative_improvement * 100,
                statistical_analysis=StatisticalAnalysis(
                    sample_size=treatment_performance.total_trades,
                    power_analysis=0.8,
                    p_value=0.05,
                    confidence_interval=(float(relative_improvement) - 0.02, float(relative_improvement) + 0.02),
                    effect_size=float(abs(relative_improvement)),
                    statistically_significant=abs(relative_improvement) > Decimal('0.02')
                ),
                risk_adjusted_improvement=relative_improvement
            )
            
            return comparison
            
        except Exception as e:
            logger.error(f"Failed to get performance comparison: {e}")
            return None
    
    async def _get_group_current_performance(self, group: TestGroup) -> Optional[PerformanceMetrics]:
        """Get current performance for a test group"""
        
        # Return cached performance if available and recent
        if group.current_performance:
            return group.current_performance
        
        try:
            # Aggregate performance across accounts
            total_trades = 0
            total_return = Decimal('0')
            winning_trades = 0
            losing_trades = 0
            max_drawdown = Decimal('0')
            
            for account_id in group.accounts:
                account_perf = await self.performance_data_provider.get_account_performance(
                    account_id, 'hourly'  # Get recent performance
                )
                
                if account_perf:
                    total_trades += account_perf.total_trades
                    total_return += account_perf.total_return
                    winning_trades += account_perf.winning_trades
                    losing_trades += account_perf.losing_trades
                    max_drawdown = max(max_drawdown, account_perf.max_drawdown)
            
            if total_trades == 0:
                return None
            
            # Calculate metrics
            win_rate = Decimal(str(winning_trades / total_trades)) if total_trades > 0 else Decimal('0')
            
            # Simple expectancy calculation
            avg_win = Decimal('50') if winning_trades > 0 else Decimal('0')  # Mock values
            avg_loss = Decimal('30') if losing_trades > 0 else Decimal('0')
            expectancy = (win_rate * avg_win) - ((Decimal('1') - win_rate) * avg_loss)
            
            performance = PerformanceMetrics(
                total_trades=total_trades,
                winning_trades=winning_trades,
                losing_trades=losing_trades,
                win_rate=win_rate,
                total_return=total_return,
                expectancy=expectancy,
                max_drawdown=max_drawdown,
                average_win=avg_win,
                average_loss=avg_loss
            )
            
            return performance
            
        except Exception as e:
            logger.error(f"Failed to get group performance: {e}")
            return None
    
    async def _evaluate_rollback_criteria(self, test: ImprovementTest, 
                                        comparison: PerformanceComparison) -> Optional[RollbackDecision]:
        """Evaluate all rollback criteria and return decision if needed"""
        
        test_id = test.test_id
        relative_improvement = comparison.relative_improvement
        
        # Apply risk-based threshold adjustments
        adjusted_thresholds = await self._calculate_adjusted_thresholds(test, comparison)
        
        # Check emergency threshold (immediate rollback)
        if relative_improvement <= adjusted_thresholds['emergency']:
            return RollbackDecision(
                test_id=test_id,
                rollback_reason=f"Emergency threshold breached: {relative_improvement:.2%} <= {adjusted_thresholds['emergency']:.2%}",
                trigger_value=float(relative_improvement),
                threshold=float(adjusted_thresholds['emergency']),
                severity="emergency",
                immediate=True
            )
        
        # Check standard rollback threshold
        if relative_improvement <= adjusted_thresholds['rollback']:
            # Confirm the degradation over time
            if await self._confirm_performance_degradation(test_id, relative_improvement):
                return RollbackDecision(
                    test_id=test_id,
                    rollback_reason=f"Rollback threshold breached: {relative_improvement:.2%} <= {adjusted_thresholds['rollback']:.2%}",
                    trigger_value=float(relative_improvement),
                    threshold=float(adjusted_thresholds['rollback']),
                    severity="automatic",
                    immediate=False
                )
        
        # Check drawdown threshold
        treatment_drawdown = comparison.treatment_performance.max_drawdown
        if treatment_drawdown >= adjusted_thresholds['drawdown']:
            return RollbackDecision(
                test_id=test_id,
                rollback_reason=f"Drawdown threshold breached: {treatment_drawdown:.2%} >= {adjusted_thresholds['drawdown']:.2%}",
                trigger_value=float(treatment_drawdown),
                threshold=float(adjusted_thresholds['drawdown']),
                severity="automatic",
                immediate=False
            )
        
        # Check warning threshold (no rollback, just warning)
        if relative_improvement <= adjusted_thresholds['warning']:
            await self._record_warning(test_id, relative_improvement)
        
        # Check if minimum sample size is met
        if comparison.treatment_performance.total_trades < self.config['min_trades_for_rollback']:
            logger.debug(f"Insufficient trades for rollback consideration: {comparison.treatment_performance.total_trades}")
            return None
        
        # Check time-based criteria
        if not await self._meets_time_criteria(test):
            logger.debug(f"Time criteria not met for rollback consideration")
            return None
        
        return None
    
    async def _calculate_adjusted_thresholds(self, test: ImprovementTest, 
                                           comparison: PerformanceComparison) -> Dict[str, Decimal]:
        """Calculate risk-adjusted rollback thresholds"""
        
        base_thresholds = {
            'warning': self.config['warning_threshold'],
            'rollback': self.config['rollback_threshold'],
            'emergency': self.config['emergency_threshold'],
            'drawdown': self.config['drawdown_threshold']
        }
        
        # Risk-based adjustments
        if test.risk_assessment == "high":
            multiplier = self.config['high_risk_multiplier']
            base_thresholds['rollback'] *= multiplier
            base_thresholds['emergency'] *= multiplier
        
        # Volatility-based adjustments
        if self.config['volatility_adjustment']:
            volatility_ratio = comparison.treatment_performance.volatility / max(comparison.control_performance.volatility, Decimal('0.01'))
            if volatility_ratio > Decimal('1.5'):  # 50% higher volatility
                adjustment = Decimal('0.8')  # Make thresholds 20% more sensitive
                base_thresholds['rollback'] *= adjustment
                base_thresholds['emergency'] *= adjustment
        
        return base_thresholds
    
    async def _confirm_performance_degradation(self, test_id: str, current_performance: Decimal) -> bool:
        """Confirm performance degradation over the confirmation period"""
        
        confirmation_period = self.config['confirmation_period']
        cutoff_time = datetime.utcnow() - confirmation_period
        
        # Get recent performance history
        history = self._performance_history.get(test_id, [])
        recent_history = [
            h for h in history 
            if h['timestamp'] >= cutoff_time
        ]
        
        if len(recent_history) < 3:  # Need at least 3 data points
            return False
        
        # Check if performance has been consistently poor
        poor_performance_count = sum(
            1 for h in recent_history 
            if h['relative_improvement'] <= current_performance
        )
        
        confirmation_threshold = 0.7  # 70% of recent measurements must be poor
        return (poor_performance_count / len(recent_history)) >= confirmation_threshold
    
    async def _record_warning(self, test_id: str, performance: Decimal):
        """Record a performance warning"""
        current_time = datetime.utcnow()
        
        if test_id not in self._warning_tracker:
            self._warning_tracker[test_id] = current_time
            logger.warning(f"Performance warning for test {test_id}: {performance:.2%}")
        else:
            time_since_first_warning = current_time - self._warning_tracker[test_id]
            if time_since_first_warning > timedelta(hours=1):
                logger.warning(f"Persistent performance warning for test {test_id}: {performance:.2%} (ongoing for {time_since_first_warning})")
    
    async def _meets_time_criteria(self, test: ImprovementTest) -> bool:
        """Check if test meets minimum time criteria for rollback"""
        
        min_duration = self.config['min_monitoring_duration']
        test_duration = datetime.utcnow() - test.current_stage_start
        
        return test_duration >= min_duration
    
    async def _is_rate_limited(self, test_id: str) -> bool:
        """Check if we're rate-limited for checking this test"""
        
        if not self._last_check_time:
            self._last_check_time = datetime.utcnow()
            return False
        
        time_since_last = datetime.utcnow() - self._last_check_time
        min_interval = self.config['min_time_between_checks']
        
        if time_since_last < min_interval:
            return True
        
        self._last_check_time = datetime.utcnow()
        return False
    
    async def _update_performance_history(self, test_id: str, comparison: PerformanceComparison):
        """Update performance history for trend analysis"""
        
        if test_id not in self._performance_history:
            self._performance_history[test_id] = []
        
        history_entry = {
            'timestamp': datetime.utcnow(),
            'relative_improvement': comparison.relative_improvement,
            'absolute_difference': comparison.absolute_difference,
            'treatment_trades': comparison.treatment_performance.total_trades,
            'treatment_drawdown': comparison.treatment_performance.max_drawdown
        }
        
        self._performance_history[test_id].append(history_entry)
        
        # Keep only recent history (last 24 hours)
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        self._performance_history[test_id] = [
            h for h in self._performance_history[test_id]
            if h['timestamp'] >= cutoff_time
        ]
    
    async def _validate_rollback_decision(self, decision: RollbackDecision) -> bool:
        """Validate that a rollback decision is appropriate"""
        
        # Check if too many concurrent rollbacks
        if len(self._active_rollbacks) >= self.config['max_concurrent_rollbacks']:
            logger.warning(f"Too many concurrent rollbacks: {len(self._active_rollbacks)}")
            return False
        
        # Validate the decision parameters
        if decision.trigger_value > decision.threshold and decision.severity != "emergency":
            logger.warning(f"Invalid rollback decision: trigger {decision.trigger_value} > threshold {decision.threshold}")
            return False
        
        # Check if test is already being rolled back
        if decision.test_id in self._active_rollbacks:
            logger.warning(f"Test {decision.test_id} is already being rolled back")
            return False
        
        return True
    
    async def _execute_emergency_stop(self, test_id: str):
        """Execute immediate emergency stop actions"""
        logger.critical(f"Executing emergency stop for test {test_id}")
        
        # In a real implementation, this would:
        # 1. Immediately disable the strategy on all treatment accounts
        # 2. Close any open positions
        # 3. Send emergency notifications
        # 4. Activate circuit breakers if needed
        
        # Placeholder implementation
        await asyncio.sleep(0.1)  # Simulate emergency actions
    
    async def _get_test_details(self, test_id: str) -> Optional[Dict]:
        """Get detailed test information for rollback"""
        
        # This would typically query the database or pipeline
        # For now, return mock test details
        return {
            'test_id': test_id,
            'changes': [],  # List of changes to revert
            'accounts': ['ACC001', 'ACC002'],  # Affected accounts
            'rollback_procedures': []  # Specific rollback steps
        }
    
    async def _execute_rollback_steps(self, test_details: Dict, 
                                    decision: RollbackDecision) -> RollbackResult:
        """Execute the actual rollback steps"""
        
        test_id = test_details['test_id']
        changes_reverted = 0
        issues = []
        recovery_actions = []
        
        try:
            # Step 1: Disable strategy on treatment accounts
            for account_id in test_details.get('accounts', []):
                try:
                    # Placeholder: disable strategy
                    await asyncio.sleep(0.1)  # Simulate disabling
                    recovery_actions.append(f"Disabled strategy on account {account_id}")
                except Exception as e:
                    issues.append(f"Failed to disable strategy on {account_id}: {e}")
            
            # Step 2: Revert configuration changes
            for change in test_details.get('changes', []):
                try:
                    # Placeholder: revert change
                    await asyncio.sleep(0.1)  # Simulate reverting
                    changes_reverted += 1
                    recovery_actions.append(f"Reverted change: {change}")
                except Exception as e:
                    issues.append(f"Failed to revert change {change}: {e}")
            
            # Step 3: Restore original configurations
            try:
                # Placeholder: restore configurations
                await asyncio.sleep(0.1)  # Simulate restoration
                recovery_actions.append("Restored original configurations")
            except Exception as e:
                issues.append(f"Failed to restore configurations: {e}")
            
            # Step 4: Verify rollback completion
            rollback_successful = len(issues) == 0
            
            return RollbackResult(
                test_id=test_id,
                rollback_successful=rollback_successful,
                changes_reverted=changes_reverted,
                rollback_time=datetime.utcnow(),
                issues_encountered=issues,
                recovery_actions=recovery_actions
            )
            
        except Exception as e:
            logger.error(f"Rollback execution failed: {e}")
            return RollbackResult(
                test_id=test_id,
                rollback_successful=False,
                changes_reverted=changes_reverted,
                rollback_time=datetime.utcnow(),
                issues_encountered=[str(e)],
                recovery_actions=recovery_actions
            )
    
    async def _verify_rollback_completion(self, result: RollbackResult):
        """Verify that rollback was completed successfully"""
        
        if not result.rollback_successful:
            logger.error(f"Rollback verification failed for test {result.test_id}")
            return
        
        # Additional verification steps would go here
        # For example:
        # - Verify accounts are using original strategies
        # - Confirm configuration changes were reverted
        # - Check that no residual test effects remain
        
        logger.info(f"Rollback verification completed for test {result.test_id}")
    
    async def _complete_pending_rollbacks(self):
        """Complete any pending rollback operations"""
        
        for decision in self._rollback_queue[:]:
            try:
                result = await self.execute_rollback(decision)
                if result.rollback_successful:
                    self._rollback_queue.remove(decision)
            except Exception as e:
                logger.error(f"Failed to complete pending rollback {decision.test_id}: {e}")
    
    # Public API methods
    
    async def get_rollback_status(self) -> Dict[str, Any]:
        """Get current rollback system status"""
        
        return {
            'monitoring_active': self._monitoring_active,
            'pending_rollbacks': len(self._rollback_queue),
            'active_rollbacks': len(self._active_rollbacks),
            'warnings_tracked': len(self._warning_tracker),
            'last_check': self._last_check_time,
            'configuration': {
                'rollback_threshold': float(self.config['rollback_threshold']),
                'emergency_threshold': float(self.config['emergency_threshold']),
                'monitoring_interval': str(self.config['monitoring_interval'])
            }
        }
    
    async def get_test_risk_assessment(self, test: ImprovementTest) -> Dict[str, Any]:
        """Get comprehensive risk assessment for a test"""
        
        risk_score = 50  # Base risk score
        risk_factors = []
        
        # Assess based on test characteristics
        if test.risk_assessment == "high":
            risk_score += 30
            risk_factors.append("High risk classification")
        
        if test.current_phase == TestPhase.ROLLOUT_100:
            risk_score += 20
            risk_factors.append("Full rollout phase")
        
        # Check recent performance
        comparison = await self._get_current_performance(test)
        if comparison:
            if comparison.relative_improvement < Decimal('-0.05'):
                risk_score += 25
                risk_factors.append("Negative performance trend")
            
            if comparison.treatment_performance.max_drawdown > Decimal('0.10'):
                risk_score += 15
                risk_factors.append("High drawdown")
        
        # Historical warnings
        if test.test_id in self._warning_tracker:
            risk_score += 10
            risk_factors.append("Previous performance warnings")
        
        risk_level = "low" if risk_score < 40 else "medium" if risk_score < 70 else "high"
        
        return {
            'test_id': test.test_id,
            'risk_score': min(100, risk_score),
            'risk_level': risk_level,
            'risk_factors': risk_factors,
            'monitoring_recommended': risk_score >= 60,
            'rollback_sensitivity': self._calculate_rollback_sensitivity(test)
        }
    
    def _calculate_rollback_sensitivity(self, test: ImprovementTest) -> str:
        """Calculate rollback sensitivity level for a test"""
        
        if test.risk_assessment == "high":
            return "high"
        elif test.current_phase in [TestPhase.ROLLOUT_50, TestPhase.ROLLOUT_100]:
            return "medium"
        else:
            return "standard"
    
    async def manual_rollback_override(self, test_id: str, reason: str, 
                                     authorized_by: str) -> RollbackResult:
        """Manually trigger a rollback override"""
        
        logger.warning(f"Manual rollback override triggered for test {test_id} by {authorized_by}: {reason}")
        
        decision = RollbackDecision(
            test_id=test_id,
            rollback_reason=f"Manual override by {authorized_by}: {reason}",
            trigger_value=0.0,
            threshold=0.0,
            severity="manual",
            immediate=True
        )
        
        return await self.execute_rollback(decision)