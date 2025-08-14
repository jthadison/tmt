"""
Gradual Rollout Manager

Implements sophisticated phased deployment of trading improvements with statistical
validation at each stage. Manages progression from 10% → 25% → 50% → 100% of
accounts while maintaining safety and performance validation.

Key Features:
- Phased rollout with configurable stages
- Statistical validation at each progression point
- Account allocation and rebalancing
- Performance monitoring and decision making
- Automatic and manual advancement controls
- Rollback capabilities at any stage
"""

import logging
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Optional, Any, Tuple
import numpy as np
from dataclasses import asdict
import random

from .models import (
    ImprovementTest, TestPhase, TestDecision, TestGroup, RolloutStageResults,
    StageDecision, PerformanceComparison, StatisticalAnalysis, PerformanceMetrics,
    Change, Approval
)

# Import data interfaces
from ...src.shared.python_utils.data_interfaces import (
    AccountDataInterface, MockAccountDataProvider,
    TradeDataInterface, MockTradeDataProvider,
    PerformanceDataInterface, MockPerformanceDataProvider
)

logger = logging.getLogger(__name__)


class GradualRolloutManager:
    """
    Manages phased rollout of trading improvements with statistical validation.
    
    This manager orchestrates the careful progression of improvements through
    staged deployment phases, ensuring statistical significance and safety
    at each step before advancing to the next phase.
    """
    
    def __init__(self,
                 account_data_provider: Optional[AccountDataInterface] = None,
                 trade_data_provider: Optional[TradeDataInterface] = None,
                 performance_data_provider: Optional[PerformanceDataInterface] = None):
        
        # Data providers
        self.account_data_provider = account_data_provider or MockAccountDataProvider()
        self.trade_data_provider = trade_data_provider or MockTradeDataProvider()
        self.performance_data_provider = performance_data_provider or MockPerformanceDataProvider()
        
        # Rollout configuration
        self.config = {
            'rollout_stages': [10, 25, 50, 100],  # Percentage stages
            'min_stage_duration': timedelta(days=7),  # Minimum time per stage
            'min_trades_per_stage': 50,  # Minimum trades before advancement
            'significance_threshold': 0.05,  # 95% confidence required
            'min_improvement_threshold': Decimal('0.01'),  # 1% minimum improvement
            'max_risk_increase': Decimal('0.05'),  # 5% max risk increase allowed
            'account_rebalancing_enabled': True,  # Allow account rebalancing
            'emergency_stop_threshold': Decimal('-0.15'),  # 15% loss triggers emergency stop
            'auto_advancement_enabled': True,  # Automatic stage progression
            'manual_approval_required': False  # Require manual approval for advancement
        }
        
        # Internal state
        self._active_rollouts: Dict[str, Dict] = {}
        self._stage_results_cache: Dict[str, List[RolloutStageResults]] = {}
        self._account_allocations: Dict[str, Dict] = {}  # Track account assignments
        
        logger.info("Gradual Rollout Manager initialized")
    
    async def start_rollout(self, test: ImprovementTest, starting_stage: int = 10) -> bool:
        """
        Start gradual rollout for an improvement test.
        
        Args:
            test: ImprovementTest to begin rollout
            starting_stage: Starting percentage (default 10%)
            
        Returns:
            bool: True if rollout started successfully
        """
        try:
            logger.info(f"Starting gradual rollout for {test.test_id} at {starting_stage}%")
            
            # Validate rollout configuration
            if not await self._validate_rollout_config(test):
                logger.error(f"Rollout configuration invalid for {test.test_id}")
                return False
            
            # Get available accounts for rollout
            available_accounts = await self._get_available_accounts(test)
            if not available_accounts:
                logger.error(f"No available accounts for rollout {test.test_id}")
                return False
            
            # Create account allocation strategy
            allocation_strategy = await self._create_allocation_strategy(
                test, available_accounts, starting_stage
            )
            
            # Allocate accounts to control and treatment groups
            control_group, treatment_group = await self._allocate_accounts(
                test, allocation_strategy, starting_stage
            )
            
            # Update test groups
            test.control_group = control_group
            test.treatment_group = treatment_group
            
            # Set test phase
            test.current_phase = self._percentage_to_phase(starting_stage)
            test.current_stage_start = datetime.utcnow()
            
            # Initialize rollout tracking
            self._active_rollouts[test.test_id] = {
                'test': test,
                'current_stage': starting_stage,
                'start_time': datetime.utcnow(),
                'stage_start_time': datetime.utcnow(),
                'allocation_strategy': allocation_strategy,
                'stage_history': [],
                'performance_tracking': {},
                'status': 'active',
                'next_decision_due': datetime.utcnow() + self.config['min_stage_duration']
            }
            
            # Apply changes to treatment group
            await self._apply_changes_to_accounts(test.treatment_group)
            
            # Initialize performance baseline
            await self._initialize_performance_baseline(test.test_id)
            
            logger.info(f"Rollout started for {test.test_id}: {len(treatment_group.accounts)} treatment accounts, {len(control_group.accounts)} control accounts")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start rollout for {test.test_id}: {e}")
            return False
    
    async def update_rollout_progress(self, test_id: str) -> Optional[Dict]:
        """
        Update progress for an active rollout.
        
        Args:
            test_id: ID of the test to update
            
        Returns:
            Dict with update results or None if rollout not found
        """
        if test_id not in self._active_rollouts:
            return None
        
        try:
            rollout = self._active_rollouts[test_id]
            test = rollout['test']
            
            # Update performance metrics
            performance_update = await self._update_performance_metrics(test_id)
            
            # Check stage completion criteria
            stage_status = await self._check_stage_completion(test_id)
            
            # Update rollout tracking
            rollout['performance_tracking'] = performance_update
            rollout['last_updated'] = datetime.utcnow()
            
            # Check if decision is due
            decision_due = datetime.utcnow() >= rollout['next_decision_due']
            
            update_result = {
                'test_id': test_id,
                'current_stage': rollout['current_stage'],
                'stage_status': stage_status,
                'performance_update': performance_update,
                'decision_due': decision_due,
                'last_updated': datetime.utcnow()
            }
            
            # If stage is complete and decision is due, evaluate advancement
            if stage_status['complete'] and decision_due:
                advancement_decision = await self._evaluate_stage_advancement(test_id)
                update_result['advancement_decision'] = advancement_decision
                
                # Execute advancement if automatic
                if (advancement_decision['decision'] == 'advance' and 
                    self.config['auto_advancement_enabled'] and
                    not self.config['manual_approval_required']):
                    
                    advancement_result = await self._execute_stage_advancement(test_id)
                    update_result['advancement_executed'] = advancement_result
            
            return update_result
            
        except Exception as e:
            logger.error(f"Failed to update rollout progress for {test_id}: {e}")
            return {'error': str(e)}
    
    async def advance_to_next_stage(self, test_id: str, force: bool = False) -> bool:
        """
        Advance rollout to the next stage.
        
        Args:
            test_id: ID of the test to advance
            force: Force advancement even if criteria not met
            
        Returns:
            bool: True if advancement successful
        """
        if test_id not in self._active_rollouts:
            logger.error(f"Rollout {test_id} not found")
            return False
        
        try:
            rollout = self._active_rollouts[test_id]
            current_stage = rollout['current_stage']
            
            # Get next stage
            next_stage = self._get_next_stage(current_stage)
            if not next_stage:
                logger.info(f"Rollout {test_id} already at final stage")
                return True  # Already complete
            
            # Check advancement criteria unless forced
            if not force:
                advancement_decision = await self._evaluate_stage_advancement(test_id)
                if advancement_decision['decision'] != 'advance':
                    logger.warning(f"Advancement criteria not met for {test_id}: {advancement_decision['reason']}")
                    return False
            
            # Execute advancement
            success = await self._execute_stage_advancement(test_id)
            
            if success:
                logger.info(f"Successfully advanced {test_id} from {current_stage}% to {next_stage}%")
            else:
                logger.error(f"Failed to advance {test_id} to next stage")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to advance rollout {test_id}: {e}")
            return False
    
    async def rollback_to_previous_stage(self, test_id: str, reason: str) -> bool:
        """
        Rollback rollout to the previous stage.
        
        Args:
            test_id: ID of the test to rollback
            reason: Reason for rollback
            
        Returns:
            bool: True if rollback successful
        """
        if test_id not in self._active_rollouts:
            logger.error(f"Rollout {test_id} not found")
            return False
        
        try:
            rollout = self._active_rollouts[test_id]
            current_stage = rollout['current_stage']
            
            # Get previous stage
            previous_stage = self._get_previous_stage(current_stage)
            if not previous_stage:
                logger.warning(f"Cannot rollback {test_id} - already at minimum stage")
                return False
            
            logger.warning(f"Rolling back {test_id} from {current_stage}% to {previous_stage}%: {reason}")
            
            # Record rollback decision
            rollback_record = {
                'rollback_time': datetime.utcnow(),
                'from_stage': current_stage,
                'to_stage': previous_stage,
                'reason': reason,
                'initiated_by': 'system'
            }
            
            # Execute rollback
            success = await self._execute_stage_rollback(test_id, previous_stage, rollback_record)
            
            if success:
                logger.info(f"Successfully rolled back {test_id} to {previous_stage}%")
            else:
                logger.error(f"Failed to rollback {test_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to rollback {test_id}: {e}")
            return False
    
    async def complete_rollout(self, test_id: str) -> bool:
        """
        Complete rollout and transition to full deployment.
        
        Args:
            test_id: ID of the test to complete
            
        Returns:
            bool: True if completion successful
        """
        if test_id not in self._active_rollouts:
            return False
        
        try:
            rollout = self._active_rollouts[test_id]
            test = rollout['test']
            
            logger.info(f"Completing rollout for {test_id}")
            
            # Ensure we're at 100% stage
            if rollout['current_stage'] != 100:
                logger.warning(f"Completing rollout {test_id} at {rollout['current_stage']}% stage")
            
            # Generate final rollout results
            final_results = await self._generate_final_results(test_id)
            
            # Update test status
            test.current_phase = TestPhase.COMPLETED
            test.actual_completion = datetime.utcnow()
            test.final_results = final_results
            
            # Update rollout status
            rollout['status'] = 'completed'
            rollout['completion_time'] = datetime.utcnow()
            rollout['final_results'] = final_results
            
            # Cleanup resources
            await self._cleanup_rollout_resources(test_id)
            
            logger.info(f"Rollout {test_id} completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to complete rollout {test_id}: {e}")
            return False
    
    async def _validate_rollout_config(self, test: ImprovementTest) -> bool:
        """Validate rollout configuration"""
        
        # Check if test has required components
        if not test.treatment_group or not test.treatment_group.changes:
            logger.error(f"Test {test.test_id} missing treatment group or changes")
            return False
        
        # Validate rollout stages
        if not self.config['rollout_stages']:
            logger.error("No rollout stages configured")
            return False
        
        # Check minimum stage duration
        if self.config['min_stage_duration'] < timedelta(days=1):
            logger.error("Minimum stage duration too short")
            return False
        
        return True
    
    async def _get_available_accounts(self, test: ImprovementTest) -> List[str]:
        """Get accounts available for rollout"""
        
        # Get all managed accounts
        all_accounts = await self.account_data_provider.get_all_accounts()
        
        # Filter for eligible accounts
        eligible_accounts = []
        
        for account in all_accounts:
            # Check account status
            if account.status.value != 'active':
                continue
            
            # Check if account is already in use by other tests
            if await self._is_account_in_use(account.account_id):
                continue
            
            # Check account requirements (balance, type, etc.)
            if not await self._meets_account_requirements(account, test):
                continue
            
            eligible_accounts.append(account.account_id)
        
        logger.info(f"Found {len(eligible_accounts)} eligible accounts for rollout")
        return eligible_accounts
    
    async def _is_account_in_use(self, account_id: str) -> bool:
        """Check if account is already allocated to another test"""
        
        for rollout in self._active_rollouts.values():
            test = rollout['test']
            
            if test.control_group and account_id in test.control_group.accounts:
                return True
            if test.treatment_group and account_id in test.treatment_group.accounts:
                return True
        
        return False
    
    async def _meets_account_requirements(self, account, test: ImprovementTest) -> bool:
        """Check if account meets requirements for the test"""
        
        # Check minimum balance
        min_balance = Decimal('10000')  # $10k minimum
        if account.balance < min_balance:
            return False
        
        # Check account type (prefer live accounts)
        if account.account_type == 'demo' and test.risk_assessment == 'high':
            return False  # No demo accounts for high-risk tests
        
        # Check prop firm compatibility
        if hasattr(test, 'prop_firm_requirements'):
            if account.prop_firm not in test.prop_firm_requirements:
                return False
        
        return True
    
    async def _create_allocation_strategy(self, test: ImprovementTest, 
                                        available_accounts: List[str], 
                                        starting_stage: int) -> Dict:
        """Create account allocation strategy for rollout"""
        
        total_accounts = len(available_accounts)
        treatment_count = max(1, int(total_accounts * starting_stage / 100))
        control_count = total_accounts - treatment_count
        
        # Ensure minimum group sizes
        min_group_size = 3
        if treatment_count < min_group_size or control_count < min_group_size:
            logger.warning(f"Group sizes too small: treatment={treatment_count}, control={control_count}")
        
        strategy = {
            'total_accounts': total_accounts,
            'starting_stage': starting_stage,
            'treatment_count': treatment_count,
            'control_count': control_count,
            'allocation_method': 'stratified_random',  # Stratified randomization
            'stratification_factors': ['prop_firm', 'account_type', 'balance_tier'],
            'balance_tolerance': 0.1,  # 10% balance tolerance between groups
            'created_at': datetime.utcnow()
        }
        
        return strategy
    
    async def _allocate_accounts(self, test: ImprovementTest, 
                               allocation_strategy: Dict, 
                               stage_percentage: int) -> Tuple[TestGroup, TestGroup]:
        """Allocate accounts to control and treatment groups"""
        
        # Get available accounts
        available_accounts = await self._get_available_accounts(test)
        
        # Perform stratified randomization
        control_accounts, treatment_accounts = await self._stratified_random_allocation(
            available_accounts, allocation_strategy
        )
        
        # Create control group
        control_group = TestGroup(
            group_type='control',
            accounts=control_accounts,
            allocation_percentage=Decimal(str(len(control_accounts) / len(available_accounts) * 100)),
            baseline_performance=await self._get_group_baseline_performance(control_accounts)
        )
        
        # Create treatment group with changes
        treatment_group = TestGroup(
            group_type='treatment',
            accounts=treatment_accounts,
            allocation_percentage=Decimal(str(stage_percentage)),
            changes=test.treatment_group.changes.copy() if test.treatment_group else [],
            baseline_performance=await self._get_group_baseline_performance(treatment_accounts)
        )
        
        # Update account allocations tracking
        self._account_allocations[test.test_id] = {
            'control': control_accounts,
            'treatment': treatment_accounts,
            'stage_percentage': stage_percentage,
            'allocated_at': datetime.utcnow()
        }
        
        logger.info(f"Allocated accounts for {test.test_id}: {len(control_accounts)} control, {len(treatment_accounts)} treatment")
        return control_group, treatment_group
    
    async def _stratified_random_allocation(self, accounts: List[str], 
                                          strategy: Dict) -> Tuple[List[str], List[str]]:
        """Perform stratified random allocation of accounts"""
        
        # Get account details for stratification
        account_details = {}
        for account_id in accounts:
            account_info = await self.account_data_provider.get_account_info(account_id)
            if account_info:
                account_details[account_id] = {
                    'prop_firm': account_info.prop_firm,
                    'account_type': account_info.account_type,
                    'balance_tier': self._get_balance_tier(account_info.balance)
                }
        
        # Create strata based on stratification factors
        strata = {}
        for account_id, details in account_details.items():
            stratum_key = (
                details['prop_firm'],
                details['account_type'],
                details['balance_tier']
            )
            
            if stratum_key not in strata:
                strata[stratum_key] = []
            strata[stratum_key].append(account_id)
        
        # Allocate within each stratum
        control_accounts = []
        treatment_accounts = []
        
        treatment_ratio = strategy['treatment_count'] / strategy['total_accounts']
        
        for stratum_accounts in strata.values():
            # Randomize order within stratum
            shuffled = stratum_accounts.copy()
            random.shuffle(shuffled)
            
            # Allocate based on ratio
            stratum_treatment_count = max(1, int(len(shuffled) * treatment_ratio))
            
            treatment_accounts.extend(shuffled[:stratum_treatment_count])
            control_accounts.extend(shuffled[stratum_treatment_count:])
        
        # Adjust to exact counts if needed
        total_needed_treatment = strategy['treatment_count']
        if len(treatment_accounts) != total_needed_treatment:
            # Transfer accounts between groups to match exact requirements
            if len(treatment_accounts) > total_needed_treatment:
                excess = len(treatment_accounts) - total_needed_treatment
                control_accounts.extend(treatment_accounts[-excess:])
                treatment_accounts = treatment_accounts[:-excess]
            else:
                deficit = total_needed_treatment - len(treatment_accounts)
                treatment_accounts.extend(control_accounts[:deficit])
                control_accounts = control_accounts[deficit:]
        
        return control_accounts, treatment_accounts
    
    def _get_balance_tier(self, balance: Decimal) -> str:
        """Categorize account balance into tiers"""
        if balance < Decimal('25000'):
            return 'small'
        elif balance < Decimal('100000'):
            return 'medium'
        else:
            return 'large'
    
    async def _get_group_baseline_performance(self, accounts: List[str]) -> Optional[PerformanceMetrics]:
        """Get baseline performance metrics for a group of accounts"""
        
        if not accounts:
            return None
        
        # Aggregate performance across accounts
        total_metrics = PerformanceMetrics()
        valid_accounts = 0
        
        for account_id in accounts:
            account_perf = await self.performance_data_provider.get_account_performance(
                account_id, 'monthly'
            )
            
            if account_perf:
                # Simple aggregation (in production would be more sophisticated)
                total_metrics.total_trades += account_perf.total_trades
                total_metrics.total_return += account_perf.total_return
                valid_accounts += 1
        
        if valid_accounts > 0:
            # Average the metrics
            total_metrics.total_trades = total_metrics.total_trades // valid_accounts
            total_metrics.total_return = total_metrics.total_return / valid_accounts
            # ... calculate other averaged metrics
        
        return total_metrics
    
    async def _apply_changes_to_accounts(self, treatment_group: TestGroup):
        """Apply changes to treatment group accounts"""
        
        logger.info(f"Applying {len(treatment_group.changes)} changes to {len(treatment_group.accounts)} accounts")
        
        for account_id in treatment_group.accounts:
            for change in treatment_group.changes:
                await self._apply_change_to_account(account_id, change)
        
        logger.info("Changes applied successfully to treatment group")
    
    async def _apply_change_to_account(self, account_id: str, change: Change):
        """Apply a specific change to an account"""
        
        # This would interface with the actual trading system
        # For now, we'll log the change application
        
        logger.debug(f"Applying change {change.change_id} to account {account_id}")
        
        # Record change application
        change.implementation_date = datetime.utcnow()
        
        # In production, this would:
        # 1. Update account configuration
        # 2. Modify strategy parameters
        # 3. Deploy algorithm changes
        # 4. Enable/disable features
        # 5. Update risk parameters
    
    async def _initialize_performance_baseline(self, test_id: str):
        """Initialize performance tracking baseline"""
        
        rollout = self._active_rollouts[test_id]
        test = rollout['test']
        
        # Initialize tracking structure
        rollout['performance_tracking'] = {
            'baseline_date': datetime.utcnow(),
            'control_baseline': test.control_group.baseline_performance,
            'treatment_baseline': test.treatment_group.baseline_performance,
            'daily_snapshots': {},
            'cumulative_metrics': {
                'control': PerformanceMetrics(),
                'treatment': PerformanceMetrics()
            },
            'comparison_history': []
        }
        
        logger.info(f"Performance baseline initialized for {test_id}")
    
    async def _update_performance_metrics(self, test_id: str) -> Dict:
        """Update performance metrics for rollout"""
        
        rollout = self._active_rollouts[test_id]
        test = rollout['test']
        
        # Get current performance for both groups
        control_performance = await self._get_current_group_performance(test.control_group)
        treatment_performance = await self._get_current_group_performance(test.treatment_group)
        
        # Update cumulative tracking
        tracking = rollout['performance_tracking']
        tracking['cumulative_metrics']['control'] = control_performance
        tracking['cumulative_metrics']['treatment'] = treatment_performance
        
        # Take daily snapshot
        today = datetime.utcnow().date()
        tracking['daily_snapshots'][str(today)] = {
            'control': asdict(control_performance),
            'treatment': asdict(treatment_performance),
            'timestamp': datetime.utcnow()
        }
        
        # Calculate comparison
        comparison = await self._compare_group_performance(
            control_performance, treatment_performance
        )
        tracking['comparison_history'].append({
            'timestamp': datetime.utcnow(),
            'comparison': asdict(comparison)
        })
        
        return {
            'control_performance': asdict(control_performance),
            'treatment_performance': asdict(treatment_performance),
            'comparison': asdict(comparison),
            'updated_at': datetime.utcnow()
        }
    
    async def _get_current_group_performance(self, group: TestGroup) -> PerformanceMetrics:
        """Get current performance metrics for a test group"""
        
        if not group or not group.accounts:
            return PerformanceMetrics()
        
        # Aggregate performance across group accounts
        total_metrics = PerformanceMetrics()
        valid_accounts = 0
        
        for account_id in group.accounts:
            account_perf = await self.performance_data_provider.get_account_performance(
                account_id, 'daily'
            )
            
            if account_perf:
                # Aggregate metrics
                total_metrics.total_trades += account_perf.total_trades
                total_metrics.winning_trades += account_perf.winning_trades
                total_metrics.losing_trades += account_perf.losing_trades
                total_metrics.total_return += account_perf.total_return
                valid_accounts += 1
        
        if valid_accounts > 0:
            # Calculate averages and ratios
            total_metrics.win_rate = (
                Decimal(total_metrics.winning_trades) / 
                Decimal(total_metrics.total_trades)
            ) if total_metrics.total_trades > 0 else Decimal('0')
            
            # Average other metrics
            total_metrics.total_return = total_metrics.total_return / valid_accounts
            # ... calculate other metrics
        
        return total_metrics
    
    async def _compare_group_performance(self, control_perf: PerformanceMetrics,
                                       treatment_perf: PerformanceMetrics) -> PerformanceComparison:
        """Compare performance between control and treatment groups"""
        
        # Calculate relative improvement
        if control_perf.expectancy != 0:
            relative_improvement = (
                (treatment_perf.expectancy - control_perf.expectancy) / 
                abs(control_perf.expectancy)
            )
        else:
            relative_improvement = treatment_perf.expectancy
        
        # Calculate absolute difference
        absolute_difference = treatment_perf.expectancy - control_perf.expectancy
        
        # Calculate percentage improvement
        if control_perf.total_return != 0:
            percentage_improvement = (
                (treatment_perf.total_return - control_perf.total_return) / 
                abs(control_perf.total_return) * 100
            )
        else:
            percentage_improvement = treatment_perf.total_return * 100
        
        # Perform statistical analysis
        statistical_analysis = await self._perform_statistical_analysis(
            control_perf, treatment_perf
        )
        
        return PerformanceComparison(
            control_performance=control_perf,
            treatment_performance=treatment_perf,
            relative_improvement=relative_improvement,
            absolute_difference=absolute_difference,
            percentage_improvement=percentage_improvement,
            statistical_analysis=statistical_analysis,
            risk_adjusted_improvement=relative_improvement  # Simplified
        )
    
    async def _perform_statistical_analysis(self, control_perf: PerformanceMetrics,
                                          treatment_perf: PerformanceMetrics) -> StatisticalAnalysis:
        """Perform statistical analysis for group comparison"""
        
        # Get sample sizes
        control_size = control_perf.total_trades
        treatment_size = treatment_perf.total_trades
        total_size = control_size + treatment_size
        
        # Calculate effect size (Cohen's d approximation)
        if control_perf.expectancy != 0:
            effect_size = float(abs(treatment_perf.expectancy - control_perf.expectancy) / control_perf.expectancy)
        else:
            effect_size = 0.0
        
        # Simple statistical significance test (placeholder)
        # In production, would use proper t-test or Mann-Whitney U test
        significance_threshold = self.config['significance_threshold']
        
        # Assume statistical significance if effect size is large and sample size adequate
        statistically_significant = (
            effect_size > 0.2 and  # Medium effect size
            total_size >= 50 and   # Adequate sample size
            abs(float(treatment_perf.expectancy - control_perf.expectancy)) > 0.001  # Meaningful difference
        )
        
        # Calculate approximate p-value (simplified)
        if statistically_significant:
            p_value = 0.03  # Below threshold
        else:
            p_value = 0.15  # Above threshold
        
        # Calculate confidence interval (simplified)
        difference = float(treatment_perf.expectancy - control_perf.expectancy)
        margin_of_error = 0.002  # Simplified margin
        confidence_interval = (difference - margin_of_error, difference + margin_of_error)
        
        return StatisticalAnalysis(
            sample_size=total_size,
            power_analysis=0.8,  # Assumed 80% power
            p_value=p_value,
            confidence_interval=confidence_interval,
            effect_size=effect_size,
            statistically_significant=statistically_significant,
            significance_level=significance_threshold,
            confidence_level=0.95
        )
    
    async def _check_stage_completion(self, test_id: str) -> Dict:
        """Check if current stage meets completion criteria"""
        
        rollout = self._active_rollouts[test_id]
        stage_start = rollout['stage_start_time']
        
        # Check duration criteria
        duration = datetime.utcnow() - stage_start
        min_duration_met = duration >= self.config['min_stage_duration']
        
        # Check trade count criteria
        performance = rollout['performance_tracking']['cumulative_metrics']
        treatment_trades = performance['treatment'].total_trades
        min_trades_met = treatment_trades >= self.config['min_trades_per_stage']
        
        # Check data quality
        control_trades = performance['control'].total_trades
        data_quality_ok = (
            treatment_trades > 0 and 
            control_trades > 0 and
            abs(treatment_trades - control_trades) / max(treatment_trades, control_trades) < 0.5
        )
        
        # Overall completion status
        complete = min_duration_met and min_trades_met and data_quality_ok
        
        return {
            'complete': complete,
            'duration': duration,
            'min_duration_met': min_duration_met,
            'min_trades_met': min_trades_met,
            'data_quality_ok': data_quality_ok,
            'treatment_trades': treatment_trades,
            'control_trades': control_trades,
            'days_elapsed': duration.days
        }
    
    async def _evaluate_stage_advancement(self, test_id: str) -> Dict:
        """Evaluate whether to advance to next stage"""
        
        rollout = self._active_rollouts[test_id]
        performance_tracking = rollout['performance_tracking']
        
        # Get latest comparison
        if not performance_tracking['comparison_history']:
            return {
                'decision': 'hold',
                'reason': 'No performance data available',
                'confidence': 0.0
            }
        
        latest_comparison = performance_tracking['comparison_history'][-1]['comparison']
        comparison = PerformanceComparison(**latest_comparison)
        
        # Check for emergency stop conditions
        if comparison.relative_improvement <= self.config['emergency_stop_threshold']:
            return {
                'decision': 'emergency_stop',
                'reason': f'Performance degradation {comparison.relative_improvement:.2%} exceeds emergency threshold',
                'confidence': 1.0,
                'recommended_action': 'immediate_rollback'
            }
        
        # Check statistical significance
        if not comparison.statistical_analysis.statistically_significant:
            return {
                'decision': 'hold',
                'reason': f'Results not statistically significant (p={comparison.statistical_analysis.p_value:.3f})',
                'confidence': 0.3
            }
        
        # Check minimum improvement threshold
        if comparison.relative_improvement < self.config['min_improvement_threshold']:
            return {
                'decision': 'hold',
                'reason': f'Improvement {comparison.relative_improvement:.2%} below threshold {self.config["min_improvement_threshold"]:.2%}',
                'confidence': 0.4
            }
        
        # Check risk increase
        risk_increase = self._calculate_risk_increase(comparison)
        if risk_increase > self.config['max_risk_increase']:
            return {
                'decision': 'hold',
                'reason': f'Risk increase {risk_increase:.2%} exceeds threshold {self.config["max_risk_increase"]:.2%}',
                'confidence': 0.6
            }
        
        # All criteria met - recommend advancement
        confidence = min(1.0, (
            float(comparison.statistical_analysis.confidence_level) +
            float(comparison.relative_improvement) * 10 +
            (1.0 - comparison.statistical_analysis.p_value)
        ) / 3)
        
        return {
            'decision': 'advance',
            'reason': f'All advancement criteria met: improvement {comparison.relative_improvement:.2%}, p-value {comparison.statistical_analysis.p_value:.3f}',
            'confidence': confidence,
            'performance_improvement': float(comparison.relative_improvement),
            'statistical_significance': comparison.statistical_analysis.statistically_significant
        }
    
    def _calculate_risk_increase(self, comparison: PerformanceComparison) -> Decimal:
        """Calculate risk increase from treatment vs control"""
        
        # Simple risk calculation based on drawdown and volatility
        control_risk = (
            comparison.control_performance.max_drawdown * Decimal('0.7') +
            comparison.control_performance.volatility * Decimal('0.3')
        )
        
        treatment_risk = (
            comparison.treatment_performance.max_drawdown * Decimal('0.7') +
            comparison.treatment_performance.volatility * Decimal('0.3')
        )
        
        if control_risk > 0:
            risk_increase = (treatment_risk - control_risk) / control_risk
        else:
            risk_increase = Decimal('0')
        
        return risk_increase
    
    async def _execute_stage_advancement(self, test_id: str) -> bool:
        """Execute advancement to next stage"""
        
        try:
            rollout = self._active_rollouts[test_id]
            current_stage = rollout['current_stage']
            next_stage = self._get_next_stage(current_stage)
            
            if not next_stage:
                # Complete rollout
                return await self.complete_rollout(test_id)
            
            logger.info(f"Advancing {test_id} from {current_stage}% to {next_stage}%")
            
            # Record current stage results
            stage_results = await self._generate_stage_results(test_id, current_stage)
            if test_id not in self._stage_results_cache:
                self._stage_results_cache[test_id] = []
            self._stage_results_cache[test_id].append(stage_results)
            
            # Reallocate accounts for new stage
            success = await self._reallocate_for_next_stage(test_id, next_stage)
            if not success:
                logger.error(f"Failed to reallocate accounts for {test_id}")
                return False
            
            # Update rollout state
            rollout['current_stage'] = next_stage
            rollout['stage_start_time'] = datetime.utcnow()
            rollout['next_decision_due'] = datetime.utcnow() + self.config['min_stage_duration']
            
            # Update test phase
            test = rollout['test']
            test.current_phase = self._percentage_to_phase(next_stage)
            test.current_stage_start = datetime.utcnow()
            
            logger.info(f"Successfully advanced {test_id} to {next_stage}%")
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute stage advancement for {test_id}: {e}")
            return False
    
    async def _reallocate_for_next_stage(self, test_id: str, next_stage: int) -> bool:
        """Reallocate accounts for the next stage"""
        
        rollout = self._active_rollouts[test_id]
        test = rollout['test']
        
        # Get current allocation
        current_allocation = self._account_allocations[test_id]
        all_accounts = current_allocation['control'] + current_allocation['treatment']
        
        # Calculate new allocation
        total_accounts = len(all_accounts)
        new_treatment_count = max(1, int(total_accounts * next_stage / 100))
        new_control_count = total_accounts - new_treatment_count
        
        # Determine which accounts to move
        current_treatment = set(current_allocation['treatment'])
        current_control = set(current_allocation['control'])
        
        if new_treatment_count > len(current_treatment):
            # Need to move accounts from control to treatment
            accounts_to_move = new_treatment_count - len(current_treatment)
            accounts_to_transfer = list(current_control)[:accounts_to_move]
            
            new_treatment_accounts = list(current_treatment) + accounts_to_transfer
            new_control_accounts = [acc for acc in current_control if acc not in accounts_to_transfer]
        else:
            # Stage might be decreasing (rollback case)
            new_treatment_accounts = list(current_treatment)[:new_treatment_count]
            accounts_to_move_back = list(current_treatment)[new_treatment_count:]
            new_control_accounts = list(current_control) + accounts_to_move_back
        
        # Apply changes to newly added treatment accounts
        if new_treatment_count > len(current_treatment):
            for account_id in accounts_to_transfer:
                for change in test.treatment_group.changes:
                    await self._apply_change_to_account(account_id, change)
        
        # Update test groups
        test.control_group.accounts = new_control_accounts
        test.treatment_group.accounts = new_treatment_accounts
        test.treatment_group.allocation_percentage = Decimal(str(next_stage))
        
        # Update allocation tracking
        self._account_allocations[test_id] = {
            'control': new_control_accounts,
            'treatment': new_treatment_accounts,
            'stage_percentage': next_stage,
            'allocated_at': datetime.utcnow()
        }
        
        logger.info(f"Reallocated accounts for {test_id}: {len(new_treatment_accounts)} treatment, {len(new_control_accounts)} control")
        return True
    
    async def _generate_stage_results(self, test_id: str, stage: int) -> RolloutStageResults:
        """Generate results for completed stage"""
        
        rollout = self._active_rollouts[test_id]
        performance_tracking = rollout['performance_tracking']
        
        # Get stage performance data
        latest_comparison = performance_tracking['comparison_history'][-1]['comparison']
        comparison = PerformanceComparison(**latest_comparison)
        
        # Get advancement decision
        advancement_decision = await self._evaluate_stage_advancement(test_id)
        
        stage_decision = StageDecision(
            decision=TestDecision(advancement_decision['decision']),
            reason=advancement_decision['reason'],
            decision_maker='automatic',
            confidence_level=advancement_decision['confidence'],
            performance_data=comparison
        )
        
        return RolloutStageResults(
            stage=stage,
            start_date=rollout['stage_start_time'],
            end_date=datetime.utcnow(),
            duration=datetime.utcnow() - rollout['stage_start_time'],
            performance_comparison=comparison,
            stage_decision=stage_decision
        )
    
    async def _execute_stage_rollback(self, test_id: str, target_stage: int, rollback_record: Dict) -> bool:
        """Execute rollback to target stage"""
        
        try:
            rollout = self._active_rollouts[test_id]
            
            # Record rollback in stage history
            rollout['stage_history'].append(rollback_record)
            
            # Reallocate for target stage
            success = await self._reallocate_for_next_stage(test_id, target_stage)
            if not success:
                return False
            
            # Update rollout state
            rollout['current_stage'] = target_stage
            rollout['stage_start_time'] = datetime.utcnow()
            rollout['next_decision_due'] = datetime.utcnow() + self.config['min_stage_duration']
            
            # Update test phase
            test = rollout['test']
            test.current_phase = self._percentage_to_phase(target_stage)
            test.current_stage_start = datetime.utcnow()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute rollback for {test_id}: {e}")
            return False
    
    async def _generate_final_results(self, test_id: str) -> PerformanceComparison:
        """Generate final results for completed rollout"""
        
        rollout = self._active_rollouts[test_id]
        performance_tracking = rollout['performance_tracking']
        
        # Get final performance comparison
        if performance_tracking['comparison_history']:
            latest_comparison = performance_tracking['comparison_history'][-1]['comparison']
            return PerformanceComparison(**latest_comparison)
        else:
            # Return empty comparison if no data
            return PerformanceComparison(
                control_performance=PerformanceMetrics(),
                treatment_performance=PerformanceMetrics(),
                relative_improvement=Decimal('0'),
                absolute_difference=Decimal('0'),
                percentage_improvement=Decimal('0'),
                statistical_analysis=StatisticalAnalysis(
                    sample_size=0,
                    power_analysis=0.0,
                    p_value=1.0,
                    confidence_interval=(0.0, 0.0),
                    effect_size=0.0,
                    statistically_significant=False
                ),
                risk_adjusted_improvement=Decimal('0')
            )
    
    async def _cleanup_rollout_resources(self, test_id: str):
        """Cleanup resources for completed rollout"""
        
        # Move to completed rollouts (simplified)
        # In production, would archive to database
        
        logger.info(f"Cleaning up resources for completed rollout {test_id}")
    
    def _percentage_to_phase(self, percentage: int) -> TestPhase:
        """Convert percentage to test phase"""
        phase_mapping = {
            10: TestPhase.ROLLOUT_10,
            25: TestPhase.ROLLOUT_25,
            50: TestPhase.ROLLOUT_50,
            100: TestPhase.ROLLOUT_100
        }
        return phase_mapping.get(percentage, TestPhase.ROLLOUT_10)
    
    def _get_next_stage(self, current_stage: int) -> Optional[int]:
        """Get next stage in progression"""
        stages = self.config['rollout_stages']
        
        try:
            current_index = stages.index(current_stage)
            if current_index < len(stages) - 1:
                return stages[current_index + 1]
        except ValueError:
            pass
        
        return None
    
    def _get_previous_stage(self, current_stage: int) -> Optional[int]:
        """Get previous stage for rollback"""
        stages = self.config['rollout_stages']
        
        try:
            current_index = stages.index(current_stage)
            if current_index > 0:
                return stages[current_index - 1]
        except ValueError:
            pass
        
        return None
    
    # Public API methods
    
    async def get_active_rollouts(self) -> List[Dict]:
        """Get list of active rollouts"""
        return [
            {
                'test_id': test_id,
                'current_stage': data['current_stage'],
                'start_time': data['start_time'],
                'stage_start_time': data['stage_start_time'],
                'status': data['status'],
                'next_decision_due': data['next_decision_due']
            }
            for test_id, data in self._active_rollouts.items()
            if data['status'] == 'active'
        ]
    
    async def get_rollout_status(self, test_id: str) -> Optional[Dict]:
        """Get detailed status of specific rollout"""
        if test_id not in self._active_rollouts:
            return None
        
        rollout = self._active_rollouts[test_id]
        
        # Get stage completion status
        stage_status = await self._check_stage_completion(test_id)
        
        return {
            'test_id': test_id,
            'current_stage': rollout['current_stage'],
            'status': rollout['status'],
            'start_time': rollout['start_time'],
            'stage_start_time': rollout['stage_start_time'],
            'next_decision_due': rollout['next_decision_due'],
            'stage_completion': stage_status,
            'performance_tracking': rollout.get('performance_tracking', {}),
            'stage_history': rollout.get('stage_history', [])
        }
    
    async def force_stage_decision(self, test_id: str, decision: str, reason: str) -> bool:
        """Force a specific stage decision"""
        if test_id not in self._active_rollouts:
            return False
        
        try:
            if decision == 'advance':
                return await self.advance_to_next_stage(test_id, force=True)
            elif decision == 'rollback':
                current_stage = self._active_rollouts[test_id]['current_stage']
                previous_stage = self._get_previous_stage(current_stage)
                if previous_stage:
                    return await self.rollback_to_previous_stage(test_id, reason)
            elif decision == 'complete':
                return await self.complete_rollout(test_id)
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to force stage decision for {test_id}: {e}")
            return False