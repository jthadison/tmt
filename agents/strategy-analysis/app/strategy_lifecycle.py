"""
Strategy lifecycle management system.
"""
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
import asyncio
from dataclasses import asdict

from .models import (
    TradingStrategy, StrategyStatus, StrategyLifecycle, StrategyConfiguration,
    UnderperformanceDetection, RehabilitationPlan, RecoveryPhase
)

logger = logging.getLogger(__name__)


class StrategyLifecycleManager:
    """
    Manages the complete lifecycle of trading strategies including activation,
    suspension, rehabilitation, and deprecation.
    """
    
    def __init__(self):
        # Lifecycle thresholds
        self.activation_thresholds = {
            'min_backtest_trades': 100,
            'min_sharpe_ratio': Decimal('0.8'),
            'max_drawdown': Decimal('0.12'),  # 12%
            'min_profit_factor': Decimal('1.3'),
            'min_win_rate': Decimal('0.48')   # 48%
        }
        
        self.deprecation_thresholds = {
            'max_suspension_period': 180,  # 6 months
            'min_trades_per_month': 5,
            'max_consecutive_suspensions': 3
        }
        
        # Auto-suspension triggers
        self.suspension_triggers = {
            'critical_underperformance': True,
            'high_drawdown_breach': True,
            'negative_expectancy_period': 30,  # Days
            'manual_override': True
        }
    
    async def activate_strategy(self, strategy: TradingStrategy,
                              backtest_results: Optional[Dict] = None) -> bool:
        """
        Activate a new strategy after validation.
        
        Args:
            strategy: Strategy to activate
            backtest_results: Historical backtest performance data
            
        Returns:
            True if successfully activated, False otherwise
        """
        logger.info(f"Activating strategy {strategy.strategy_id}")
        
        # Validate strategy meets activation criteria
        validation_result = await self._validate_strategy_for_activation(strategy, backtest_results)
        
        if not validation_result['eligible']:
            logger.warning(f"Strategy {strategy.strategy_id} failed activation validation: {validation_result['reasons']}")
            return False
        
        # Update strategy lifecycle
        strategy.lifecycle.status = StrategyStatus.ACTIVE
        strategy.lifecycle.activated_at = datetime.utcnow()
        strategy.lifecycle.last_modified = datetime.utcnow()
        
        # Set initial configuration
        if not hasattr(strategy, 'configuration') or strategy.configuration is None:
            strategy.configuration = StrategyConfiguration(
                enabled=True,
                weight=Decimal('0.1'),  # Start with 10% allocation
                max_allocation=Decimal('0.25'),  # Max 25% allocation
                min_trades_for_evaluation=30,
                evaluation_period=90  # 90 days
            )
        else:
            strategy.configuration.enabled = True
        
        # Log activation
        await self._log_lifecycle_event(
            strategy.strategy_id,
            'activated',
            f"Strategy activated with {validation_result['score']:.1f}% validation score"
        )
        
        logger.info(f"Strategy {strategy.strategy_id} successfully activated")
        return True
    
    async def suspend_strategy(self, strategy: TradingStrategy,
                             reason: str,
                             underperformance_detection: Optional[UnderperformanceDetection] = None) -> bool:
        """
        Suspend a strategy due to performance issues or other reasons.
        
        Args:
            strategy: Strategy to suspend
            reason: Reason for suspension
            underperformance_detection: Detection results that triggered suspension
            
        Returns:
            True if successfully suspended, False otherwise
        """
        logger.warning(f"Suspending strategy {strategy.strategy_id}: {reason}")
        
        # Update strategy lifecycle
        strategy.lifecycle.status = StrategyStatus.SUSPENDED
        strategy.lifecycle.suspension_reason = reason
        strategy.lifecycle.suspended_at = datetime.utcnow()
        strategy.lifecycle.last_modified = datetime.utcnow()
        
        # Disable strategy
        strategy.configuration.enabled = False
        
        # Create or update rehabilitation plan
        if underperformance_detection and underperformance_detection.recommendations.rehabilitation_plan:
            await self._initiate_rehabilitation(strategy, underperformance_detection.recommendations.rehabilitation_plan)
        
        # Log suspension
        await self._log_lifecycle_event(
            strategy.strategy_id,
            'suspended',
            f"Strategy suspended: {reason}"
        )
        
        # Notify stakeholders
        await self._notify_suspension(strategy, reason)
        
        logger.info(f"Strategy {strategy.strategy_id} successfully suspended")
        return True
    
    async def deprecate_strategy(self, strategy: TradingStrategy, reason: str) -> bool:
        """
        Deprecate a strategy permanently.
        
        Args:
            strategy: Strategy to deprecate
            reason: Reason for deprecation
            
        Returns:
            True if successfully deprecated, False otherwise
        """
        logger.info(f"Deprecating strategy {strategy.strategy_id}: {reason}")
        
        # Check if strategy can be deprecated
        if strategy.lifecycle.status == StrategyStatus.ACTIVE:
            # Must suspend first before deprecating
            await self.suspend_strategy(strategy, f"Pre-deprecation suspension: {reason}")
        
        # Update strategy lifecycle
        strategy.lifecycle.status = StrategyStatus.DEPRECATED
        strategy.lifecycle.suspension_reason = reason
        strategy.lifecycle.last_modified = datetime.utcnow()
        
        # Disable strategy completely
        strategy.configuration.enabled = False
        strategy.configuration.weight = Decimal('0')
        
        # Log deprecation
        await self._log_lifecycle_event(
            strategy.strategy_id,
            'deprecated',
            f"Strategy deprecated: {reason}"
        )
        
        # Archive strategy data
        await self._archive_strategy_data(strategy)
        
        logger.info(f"Strategy {strategy.strategy_id} successfully deprecated")
        return True
    
    async def rehabilitate_strategy(self, strategy: TradingStrategy,
                                  rehabilitation_plan: RehabilitationPlan) -> bool:
        """
        Attempt to rehabilitate a suspended strategy.
        
        Args:
            strategy: Strategy to rehabilitate
            rehabilitation_plan: Plan for rehabilitation
            
        Returns:
            True if rehabilitation successful, False otherwise
        """
        logger.info(f"Starting rehabilitation for strategy {strategy.strategy_id}")
        
        if strategy.lifecycle.status != StrategyStatus.SUSPENDED:
            logger.warning(f"Strategy {strategy.strategy_id} not in suspended state, cannot rehabilitate")
            return False
        
        # Update rehabilitation plan
        current_performance = await self._get_current_performance_metrics(strategy)
        updated_plan = await self._update_rehabilitation_progress(rehabilitation_plan, current_performance)
        
        # Check if ready for return
        if updated_plan.current_phase == RecoveryPhase.FULL_RETURN:
            return await self._complete_rehabilitation(strategy, updated_plan)
        elif updated_plan.current_phase == RecoveryPhase.GRADUAL_RETURN:
            return await self._begin_gradual_return(strategy, updated_plan)
        else:
            # Continue monitoring
            await self._log_lifecycle_event(
                strategy.strategy_id,
                'rehabilitation_progress',
                f"Rehabilitation progress: {updated_plan.progress_score:.1f}%, Phase: {updated_plan.current_phase}"
            )
            return True
    
    async def check_auto_suspension_triggers(self, strategy: TradingStrategy) -> Optional[str]:
        """
        Check if strategy should be auto-suspended based on triggers.
        
        Args:
            strategy: Strategy to check
            
        Returns:
            Suspension reason if triggered, None otherwise
        """
        if strategy.lifecycle.status != StrategyStatus.ACTIVE:
            return None
        
        performance = strategy.performance.overall
        
        # Check critical underperformance
        if self.suspension_triggers['critical_underperformance']:
            if (performance.expectancy < Decimal('-0.01') and  # Negative expectancy
                performance.total_trades >= 50):  # Sufficient sample size
                return "Critical underperformance: Negative expectancy with sufficient trades"
        
        # Check high drawdown breach
        if self.suspension_triggers['high_drawdown_breach']:
            if performance.max_drawdown > Decimal('0.20'):  # 20% drawdown
                return "High drawdown breach: Maximum drawdown exceeds 20%"
        
        # Check negative expectancy period
        if hasattr(strategy.performance, 'trend'):
            trend = strategy.performance.trend
            if (trend.direction == 'declining' and
                trend.trend_duration >= self.suspension_triggers['negative_expectancy_period']):
                return f"Prolonged decline: {trend.trend_duration} days of declining performance"
        
        return None
    
    async def _validate_strategy_for_activation(self, strategy: TradingStrategy,
                                              backtest_results: Optional[Dict] = None) -> Dict:
        """Validate strategy meets activation criteria."""
        
        validation_result = {
            'eligible': True,
            'score': Decimal('0'),
            'reasons': [],
            'warnings': []
        }
        
        score_components = []
        
        if backtest_results:
            # Validate backtest results
            backtest_performance = backtest_results.get('performance', {})
            
            # Check minimum trades
            trades = backtest_performance.get('total_trades', 0)
            if trades < self.activation_thresholds['min_backtest_trades']:
                validation_result['eligible'] = False
                validation_result['reasons'].append(f"Insufficient backtest trades: {trades} < {self.activation_thresholds['min_backtest_trades']}")
            else:
                score_components.append(min(Decimal('25'), Decimal(str(trades)) / Decimal('200') * Decimal('25')))
            
            # Check Sharpe ratio
            sharpe = Decimal(str(backtest_performance.get('sharpe_ratio', 0)))
            if sharpe < self.activation_thresholds['min_sharpe_ratio']:
                validation_result['eligible'] = False
                validation_result['reasons'].append(f"Low Sharpe ratio: {sharpe} < {self.activation_thresholds['min_sharpe_ratio']}")
            else:
                score_components.append(min(Decimal('25'), sharpe / Decimal('2') * Decimal('25')))
            
            # Check max drawdown
            drawdown = Decimal(str(backtest_performance.get('max_drawdown', 0.5)))
            if drawdown > self.activation_thresholds['max_drawdown']:
                validation_result['eligible'] = False
                validation_result['reasons'].append(f"High drawdown: {drawdown:.1%} > {self.activation_thresholds['max_drawdown']:.1%}")
            else:
                score_components.append(Decimal('25') * (Decimal('1') - drawdown / Decimal('0.3')))
            
            # Check profit factor
            profit_factor = Decimal(str(backtest_performance.get('profit_factor', 1)))
            if profit_factor < self.activation_thresholds['min_profit_factor']:
                validation_result['eligible'] = False
                validation_result['reasons'].append(f"Low profit factor: {profit_factor} < {self.activation_thresholds['min_profit_factor']}")
            else:
                score_components.append(min(Decimal('25'), (profit_factor - Decimal('1')) / Decimal('1') * Decimal('25')))
        
        else:
            validation_result['warnings'].append("No backtest results provided")
            score_components = [Decimal('15')] * 4  # Default moderate scores
        
        # Calculate overall score
        if score_components:
            validation_result['score'] = sum(score_components)
        
        return validation_result
    
    async def _initiate_rehabilitation(self, strategy: TradingStrategy,
                                     rehabilitation_plan: RehabilitationPlan) -> None:
        """Initiate rehabilitation process for suspended strategy."""
        
        logger.info(f"Initiating rehabilitation for strategy {strategy.strategy_id}")
        
        # Store rehabilitation plan (in production, would save to database)
        await self._save_rehabilitation_plan(strategy.strategy_id, rehabilitation_plan)
        
        # Schedule rehabilitation checkpoints
        await self._schedule_rehabilitation_checkpoints(strategy, rehabilitation_plan)
        
        await self._log_lifecycle_event(
            strategy.strategy_id,
            'rehabilitation_initiated',
            f"Rehabilitation plan created with {len(rehabilitation_plan.monitoring_metrics)} monitoring metrics"
        )
    
    async def _complete_rehabilitation(self, strategy: TradingStrategy,
                                     rehabilitation_plan: RehabilitationPlan) -> bool:
        """Complete rehabilitation and reactivate strategy."""
        
        logger.info(f"Completing rehabilitation for strategy {strategy.strategy_id}")
        
        # Reactivate strategy
        strategy.lifecycle.status = StrategyStatus.ACTIVE
        strategy.lifecycle.suspension_reason = None
        strategy.lifecycle.suspended_at = None
        strategy.lifecycle.last_modified = datetime.utcnow()
        
        # Re-enable with reduced allocation initially
        strategy.configuration.enabled = True
        strategy.configuration.weight = min(
            strategy.configuration.weight,
            Decimal('0.05')  # Start with 5% allocation
        )
        
        await self._log_lifecycle_event(
            strategy.strategy_id,
            'rehabilitation_completed',
            f"Strategy reactivated with {strategy.configuration.weight:.1%} allocation"
        )
        
        return True
    
    async def _begin_gradual_return(self, strategy: TradingStrategy,
                                  rehabilitation_plan: RehabilitationPlan) -> bool:
        """Begin gradual return of strategy allocation."""
        
        logger.info(f"Beginning gradual return for strategy {strategy.strategy_id}")
        
        # Enable strategy with minimal allocation
        strategy.configuration.enabled = True
        
        # Set allocation based on gradual return steps
        if rehabilitation_plan.gradual_return_steps:
            initial_allocation = rehabilitation_plan.gradual_return_steps[0]
            strategy.configuration.weight = initial_allocation * strategy.configuration.max_allocation
        else:
            strategy.configuration.weight = Decimal('0.01')  # 1% default
        
        await self._log_lifecycle_event(
            strategy.strategy_id,
            'gradual_return_started',
            f"Gradual return initiated with {strategy.configuration.weight:.1%} allocation"
        )
        
        return True
    
    async def _get_current_performance_metrics(self, strategy: TradingStrategy) -> Dict[str, Decimal]:
        """Get current performance metrics for rehabilitation assessment."""
        
        # In production, would query recent performance data
        performance = strategy.performance.overall
        
        return {
            'expectancy': performance.expectancy,
            'sharpe_ratio': performance.sharpe_ratio,
            'max_drawdown': performance.max_drawdown,
            'win_rate': performance.win_rate,
            'profit_factor': performance.profit_factor
        }
    
    async def _update_rehabilitation_progress(self, rehabilitation_plan: RehabilitationPlan,
                                            current_performance: Dict[str, Decimal]) -> RehabilitationPlan:
        """Update rehabilitation plan progress."""
        
        # Calculate progress for each monitored metric
        progress_scores = []
        
        for metric in rehabilitation_plan.monitoring_metrics:
            if metric in current_performance and metric in rehabilitation_plan.recovery_thresholds:
                current_value = current_performance[metric]
                threshold = rehabilitation_plan.recovery_thresholds[metric]
                
                # Calculate progress (simplified)
                if metric in ['max_drawdown']:  # Lower is better
                    progress = max(Decimal('0'), Decimal('1') - (current_value / threshold))
                else:  # Higher is better
                    progress = min(Decimal('1'), current_value / threshold)
                
                progress_scores.append(progress)
        
        # Calculate overall progress
        if progress_scores:
            overall_progress = sum(progress_scores) / len(progress_scores)
            rehabilitation_plan.progress_score = overall_progress * Decimal('100')
        
        # Update recovery phase
        if rehabilitation_plan.progress_score >= Decimal('90'):
            rehabilitation_plan.current_phase = RecoveryPhase.FULL_RETURN
        elif rehabilitation_plan.progress_score >= Decimal('70'):
            rehabilitation_plan.current_phase = RecoveryPhase.GRADUAL_RETURN
        elif rehabilitation_plan.progress_score >= Decimal('40'):
            rehabilitation_plan.current_phase = RecoveryPhase.MONITORING
        else:
            rehabilitation_plan.current_phase = RecoveryPhase.SUSPENDED
        
        return rehabilitation_plan
    
    async def _log_lifecycle_event(self, strategy_id: str, event_type: str, description: str) -> None:
        """Log strategy lifecycle event."""
        
        event = {
            'timestamp': datetime.utcnow(),
            'strategy_id': strategy_id,
            'event_type': event_type,
            'description': description
        }
        
        # In production, would save to audit log database
        logger.info(f"Lifecycle event - {strategy_id}: {event_type} - {description}")
    
    async def _notify_suspension(self, strategy: TradingStrategy, reason: str) -> None:
        """Notify stakeholders of strategy suspension."""
        
        # In production, would send notifications via email, Slack, etc.
        logger.warning(f"NOTIFICATION: Strategy {strategy.strategy_name} ({strategy.strategy_id}) suspended: {reason}")
    
    async def _archive_strategy_data(self, strategy: TradingStrategy) -> None:
        """Archive deprecated strategy data."""
        
        # In production, would move strategy data to archive storage
        logger.info(f"Archiving data for deprecated strategy {strategy.strategy_id}")
    
    async def _save_rehabilitation_plan(self, strategy_id: str, plan: RehabilitationPlan) -> None:
        """Save rehabilitation plan to storage."""
        
        # In production, would save to database
        logger.info(f"Saving rehabilitation plan for strategy {strategy_id}")
    
    async def _schedule_rehabilitation_checkpoints(self, strategy: TradingStrategy,
                                                 rehabilitation_plan: RehabilitationPlan) -> None:
        """Schedule rehabilitation progress checkpoints."""
        
        # In production, would schedule automated checks
        logger.info(f"Scheduling {len(rehabilitation_plan.evaluation_schedule)} rehabilitation checkpoints for strategy {strategy.strategy_id}")
    
    async def get_strategy_lifecycle_summary(self, strategy: TradingStrategy) -> Dict:
        """Get comprehensive lifecycle summary for a strategy."""
        
        summary = {
            'strategy_id': strategy.strategy_id,
            'strategy_name': strategy.strategy_name,
            'current_status': strategy.lifecycle.status.value,
            'created_at': strategy.lifecycle.created_at,
            'activated_at': strategy.lifecycle.activated_at,
            'last_modified': strategy.lifecycle.last_modified,
            'suspension_info': None,
            'configuration': {
                'enabled': strategy.configuration.enabled,
                'current_weight': strategy.configuration.weight,
                'max_allocation': strategy.configuration.max_allocation
            },
            'performance_summary': {
                'total_trades': strategy.performance.overall.total_trades,
                'expectancy': strategy.performance.overall.expectancy,
                'sharpe_ratio': strategy.performance.overall.sharpe_ratio,
                'max_drawdown': strategy.performance.overall.max_drawdown
            }
        }
        
        # Add suspension info if applicable
        if strategy.lifecycle.status == StrategyStatus.SUSPENDED:
            summary['suspension_info'] = {
                'suspended_at': strategy.lifecycle.suspended_at,
                'reason': strategy.lifecycle.suspension_reason,
                'duration_days': (datetime.utcnow() - strategy.lifecycle.suspended_at).days if strategy.lifecycle.suspended_at else 0
            }
        
        return summary