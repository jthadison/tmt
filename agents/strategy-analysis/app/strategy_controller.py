"""
Manual strategy control system for enable/disable operations.
"""
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any
import asyncio
from dataclasses import asdict

from .models import (
    TradingStrategy, StrategyStatus, StrategyConfiguration
)

logger = logging.getLogger(__name__)


class StrategyController:
    """
    Manual control system for strategy operations including enable/disable,
    allocation changes, and configuration management.
    """
    
    def __init__(self):
        # Control permissions and limits
        self.control_limits = {
            'max_allocation_change': Decimal('0.10'),  # 10% max change per operation
            'min_allocation': Decimal('0.01'),         # 1% minimum allocation
            'max_allocation': Decimal('0.30'),         # 30% maximum allocation
            'cooldown_period_hours': 4,                # 4 hours between major changes
        }
        
        # Audit trail for all control actions
        self.audit_trail = []
        
    async def enable_strategy(self, strategy: TradingStrategy, 
                            user_id: str,
                            reason: str,
                            override_checks: bool = False) -> Dict[str, Any]:
        """
        Enable a strategy with validation and audit logging.
        
        Args:
            strategy: Strategy to enable
            user_id: User performing the action
            reason: Reason for enabling
            override_checks: Whether to override safety checks
            
        Returns:
            Operation result with success status and details
        """
        logger.info(f"Enabling strategy {strategy.strategy_id} by user {user_id}")
        
        operation_id = f"enable_{strategy.strategy_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            # Pre-enable validation
            validation_result = await self._validate_enable_operation(strategy, override_checks)
            
            if not validation_result['allowed'] and not override_checks:
                return self._create_operation_result(
                    operation_id=operation_id,
                    success=False,
                    action='enable',
                    strategy_id=strategy.strategy_id,
                    user_id=user_id,
                    reason=reason,
                    error=f"Enable validation failed: {validation_result['reason']}"
                )
            
            # Store previous state for rollback
            previous_state = {
                'enabled': strategy.configuration.enabled,
                'weight': strategy.configuration.weight,
                'status': strategy.lifecycle.status
            }
            
            # Enable the strategy
            strategy.configuration.enabled = True
            
            # If strategy was suspended, reactivate it
            if strategy.lifecycle.status == StrategyStatus.SUSPENDED:
                strategy.lifecycle.status = StrategyStatus.ACTIVE
                strategy.lifecycle.suspension_reason = None
                strategy.lifecycle.suspended_at = None
            
            # Set minimum allocation if currently zero
            if strategy.configuration.weight == Decimal('0'):
                strategy.configuration.weight = self.control_limits['min_allocation']
            
            # Update timestamp
            strategy.lifecycle.last_modified = datetime.utcnow()
            
            # Log the operation
            await self._log_control_action(
                operation_id=operation_id,
                action='enable',
                strategy_id=strategy.strategy_id,
                user_id=user_id,
                reason=reason,
                previous_state=previous_state,
                new_state={
                    'enabled': strategy.configuration.enabled,
                    'weight': strategy.configuration.weight,
                    'status': strategy.lifecycle.status.value
                },
                validation_warnings=validation_result.get('warnings', [])
            )
            
            return self._create_operation_result(
                operation_id=operation_id,
                success=True,
                action='enable',
                strategy_id=strategy.strategy_id,
                user_id=user_id,
                reason=reason,
                changes={
                    'enabled': True,
                    'allocation': strategy.configuration.weight,
                    'status': strategy.lifecycle.status.value
                }
            )
        
        except Exception as e:
            logger.error(f"Error enabling strategy {strategy.strategy_id}: {str(e)}")
            return self._create_operation_result(
                operation_id=operation_id,
                success=False,
                action='enable',
                strategy_id=strategy.strategy_id,
                user_id=user_id,
                reason=reason,
                error=f"Enable operation failed: {str(e)}"
            )
    
    async def disable_strategy(self, strategy: TradingStrategy,
                             user_id: str,
                             reason: str,
                             immediate: bool = False) -> Dict[str, Any]:
        """
        Disable a strategy with proper position management.
        
        Args:
            strategy: Strategy to disable
            user_id: User performing the action
            reason: Reason for disabling
            immediate: Whether to immediately close positions
            
        Returns:
            Operation result with success status and details
        """
        logger.info(f"Disabling strategy {strategy.strategy_id} by user {user_id}")
        
        operation_id = f"disable_{strategy.strategy_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            # Store previous state
            previous_state = {
                'enabled': strategy.configuration.enabled,
                'weight': strategy.configuration.weight,
                'status': strategy.lifecycle.status.value
            }
            
            # Disable the strategy
            strategy.configuration.enabled = False
            
            # Set allocation to zero
            strategy.configuration.weight = Decimal('0')
            
            # Update timestamp
            strategy.lifecycle.last_modified = datetime.utcnow()
            
            # Handle existing positions
            position_closure_plan = await self._plan_position_closure(strategy, immediate)
            
            # Log the operation
            await self._log_control_action(
                operation_id=operation_id,
                action='disable',
                strategy_id=strategy.strategy_id,
                user_id=user_id,
                reason=reason,
                previous_state=previous_state,
                new_state={
                    'enabled': strategy.configuration.enabled,
                    'weight': strategy.configuration.weight,
                    'status': strategy.lifecycle.status.value
                },
                additional_data={'position_closure_plan': position_closure_plan}
            )
            
            return self._create_operation_result(
                operation_id=operation_id,
                success=True,
                action='disable',
                strategy_id=strategy.strategy_id,
                user_id=user_id,
                reason=reason,
                changes={
                    'enabled': False,
                    'allocation': Decimal('0'),
                    'position_closure': position_closure_plan
                }
            )
        
        except Exception as e:
            logger.error(f"Error disabling strategy {strategy.strategy_id}: {str(e)}")
            return self._create_operation_result(
                operation_id=operation_id,
                success=False,
                action='disable',
                strategy_id=strategy.strategy_id,
                user_id=user_id,
                reason=reason,
                error=f"Disable operation failed: {str(e)}"
            )
    
    async def update_allocation(self, strategy: TradingStrategy,
                              new_allocation: Decimal,
                              user_id: str,
                              reason: str) -> Dict[str, Any]:
        """
        Update strategy allocation with validation.
        
        Args:
            strategy: Strategy to update
            new_allocation: New allocation percentage (0-1)
            user_id: User performing the action
            reason: Reason for change
            
        Returns:
            Operation result with success status and details
        """
        logger.info(f"Updating allocation for strategy {strategy.strategy_id} to {new_allocation:.1%}")
        
        operation_id = f"allocate_{strategy.strategy_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            # Validate allocation change
            validation_result = await self._validate_allocation_change(strategy, new_allocation)
            
            if not validation_result['allowed']:
                return self._create_operation_result(
                    operation_id=operation_id,
                    success=False,
                    action='allocation_change',
                    strategy_id=strategy.strategy_id,
                    user_id=user_id,
                    reason=reason,
                    error=f"Allocation validation failed: {validation_result['reason']}"
                )
            
            # Store previous allocation
            previous_allocation = strategy.configuration.weight
            allocation_change = new_allocation - previous_allocation
            
            # Update allocation
            strategy.configuration.weight = new_allocation
            strategy.lifecycle.last_modified = datetime.utcnow()
            
            # If allocation is set to zero, disable the strategy
            if new_allocation == Decimal('0'):
                strategy.configuration.enabled = False
            elif not strategy.configuration.enabled and new_allocation > Decimal('0'):
                # Enable strategy if allocation is increased from zero
                strategy.configuration.enabled = True
            
            # Log the operation
            await self._log_control_action(
                operation_id=operation_id,
                action='allocation_change',
                strategy_id=strategy.strategy_id,
                user_id=user_id,
                reason=reason,
                previous_state={'weight': previous_allocation},
                new_state={'weight': new_allocation},
                additional_data={
                    'allocation_change': allocation_change,
                    'change_percentage': (allocation_change / previous_allocation * Decimal('100')) if previous_allocation > 0 else Decimal('0')
                }
            )
            
            return self._create_operation_result(
                operation_id=operation_id,
                success=True,
                action='allocation_change',
                strategy_id=strategy.strategy_id,
                user_id=user_id,
                reason=reason,
                changes={
                    'previous_allocation': previous_allocation,
                    'new_allocation': new_allocation,
                    'allocation_change': allocation_change,
                    'enabled': strategy.configuration.enabled
                }
            )
        
        except Exception as e:
            logger.error(f"Error updating allocation for strategy {strategy.strategy_id}: {str(e)}")
            return self._create_operation_result(
                operation_id=operation_id,
                success=False,
                action='allocation_change',
                strategy_id=strategy.strategy_id,
                user_id=user_id,
                reason=reason,
                error=f"Allocation update failed: {str(e)}"
            )
    
    async def update_configuration(self, strategy: TradingStrategy,
                                 configuration_updates: Dict[str, Any],
                                 user_id: str,
                                 reason: str) -> Dict[str, Any]:
        """
        Update strategy configuration parameters.
        
        Args:
            strategy: Strategy to update
            configuration_updates: Dictionary of configuration changes
            user_id: User performing the action
            reason: Reason for changes
            
        Returns:
            Operation result with success status and details
        """
        logger.info(f"Updating configuration for strategy {strategy.strategy_id}")
        
        operation_id = f"config_{strategy.strategy_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            # Validate configuration changes
            validation_result = await self._validate_configuration_changes(strategy, configuration_updates)
            
            if not validation_result['allowed']:
                return self._create_operation_result(
                    operation_id=operation_id,
                    success=False,
                    action='configuration_update',
                    strategy_id=strategy.strategy_id,
                    user_id=user_id,
                    reason=reason,
                    error=f"Configuration validation failed: {validation_result['reason']}"
                )
            
            # Store previous configuration
            previous_config = {
                'max_allocation': strategy.configuration.max_allocation,
                'min_trades_for_evaluation': strategy.configuration.min_trades_for_evaluation,
                'evaluation_period': strategy.configuration.evaluation_period
            }
            
            # Apply configuration updates
            changes_applied = {}
            
            if 'max_allocation' in configuration_updates:
                old_value = strategy.configuration.max_allocation
                strategy.configuration.max_allocation = Decimal(str(configuration_updates['max_allocation']))
                changes_applied['max_allocation'] = {
                    'old': old_value,
                    'new': strategy.configuration.max_allocation
                }
            
            if 'min_trades_for_evaluation' in configuration_updates:
                old_value = strategy.configuration.min_trades_for_evaluation
                strategy.configuration.min_trades_for_evaluation = int(configuration_updates['min_trades_for_evaluation'])
                changes_applied['min_trades_for_evaluation'] = {
                    'old': old_value,
                    'new': strategy.configuration.min_trades_for_evaluation
                }
            
            if 'evaluation_period' in configuration_updates:
                old_value = strategy.configuration.evaluation_period
                strategy.configuration.evaluation_period = int(configuration_updates['evaluation_period'])
                changes_applied['evaluation_period'] = {
                    'old': old_value,
                    'new': strategy.configuration.evaluation_period
                }
            
            # Update timestamp
            strategy.lifecycle.last_modified = datetime.utcnow()
            
            # Log the operation
            await self._log_control_action(
                operation_id=operation_id,
                action='configuration_update',
                strategy_id=strategy.strategy_id,
                user_id=user_id,
                reason=reason,
                previous_state=previous_config,
                new_state={
                    'max_allocation': strategy.configuration.max_allocation,
                    'min_trades_for_evaluation': strategy.configuration.min_trades_for_evaluation,
                    'evaluation_period': strategy.configuration.evaluation_period
                },
                additional_data={'changes_applied': changes_applied}
            )
            
            return self._create_operation_result(
                operation_id=operation_id,
                success=True,
                action='configuration_update',
                strategy_id=strategy.strategy_id,
                user_id=user_id,
                reason=reason,
                changes=changes_applied
            )
        
        except Exception as e:
            logger.error(f"Error updating configuration for strategy {strategy.strategy_id}: {str(e)}")
            return self._create_operation_result(
                operation_id=operation_id,
                success=False,
                action='configuration_update',
                strategy_id=strategy.strategy_id,
                user_id=user_id,
                reason=reason,
                error=f"Configuration update failed: {str(e)}"
            )
    
    async def emergency_stop_strategy(self, strategy: TradingStrategy,
                                    user_id: str,
                                    reason: str) -> Dict[str, Any]:
        """
        Emergency stop for a strategy - immediate disable with position closure.
        
        Args:
            strategy: Strategy to stop
            user_id: User performing the action
            reason: Emergency reason
            
        Returns:
            Operation result with success status and details
        """
        logger.critical(f"EMERGENCY STOP for strategy {strategy.strategy_id} by user {user_id}: {reason}")
        
        operation_id = f"emergency_{strategy.strategy_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            # Store previous state
            previous_state = {
                'enabled': strategy.configuration.enabled,
                'weight': strategy.configuration.weight,
                'status': strategy.lifecycle.status.value
            }
            
            # Immediate disable
            strategy.configuration.enabled = False
            strategy.configuration.weight = Decimal('0')
            strategy.lifecycle.status = StrategyStatus.SUSPENDED
            strategy.lifecycle.suspension_reason = f"EMERGENCY STOP: {reason}"
            strategy.lifecycle.suspended_at = datetime.utcnow()
            strategy.lifecycle.last_modified = datetime.utcnow()
            
            # Immediate position closure
            emergency_closure_plan = await self._execute_emergency_closure(strategy)
            
            # Log the emergency operation
            await self._log_control_action(
                operation_id=operation_id,
                action='emergency_stop',
                strategy_id=strategy.strategy_id,
                user_id=user_id,
                reason=reason,
                previous_state=previous_state,
                new_state={
                    'enabled': False,
                    'weight': Decimal('0'),
                    'status': StrategyStatus.SUSPENDED.value
                },
                additional_data={
                    'emergency_closure': emergency_closure_plan,
                    'severity': 'CRITICAL'
                }
            )
            
            # Send emergency notifications
            await self._send_emergency_notifications(strategy, user_id, reason)
            
            return self._create_operation_result(
                operation_id=operation_id,
                success=True,
                action='emergency_stop',
                strategy_id=strategy.strategy_id,
                user_id=user_id,
                reason=reason,
                changes={
                    'emergency_stopped': True,
                    'positions_closed': emergency_closure_plan,
                    'status': StrategyStatus.SUSPENDED.value
                }
            )
        
        except Exception as e:
            logger.critical(f"EMERGENCY STOP FAILED for strategy {strategy.strategy_id}: {str(e)}")
            return self._create_operation_result(
                operation_id=operation_id,
                success=False,
                action='emergency_stop',
                strategy_id=strategy.strategy_id,
                user_id=user_id,
                reason=reason,
                error=f"Emergency stop failed: {str(e)}"
            )
    
    async def get_control_audit_log(self, strategy_id: Optional[str] = None,
                                  user_id: Optional[str] = None,
                                  start_date: Optional[datetime] = None,
                                  end_date: Optional[datetime] = None) -> List[Dict]:
        """
        Retrieve control action audit log with filtering.
        
        Args:
            strategy_id: Filter by strategy ID
            user_id: Filter by user ID
            start_date: Filter by start date
            end_date: Filter by end date
            
        Returns:
            List of audit log entries
        """
        filtered_log = self.audit_trail.copy()
        
        # Apply filters
        if strategy_id:
            filtered_log = [entry for entry in filtered_log if entry['strategy_id'] == strategy_id]
        
        if user_id:
            filtered_log = [entry for entry in filtered_log if entry['user_id'] == user_id]
        
        if start_date:
            filtered_log = [entry for entry in filtered_log if entry['timestamp'] >= start_date]
        
        if end_date:
            filtered_log = [entry for entry in filtered_log if entry['timestamp'] <= end_date]
        
        # Sort by timestamp (newest first)
        filtered_log.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return filtered_log
    
    # Private helper methods
    
    async def _validate_enable_operation(self, strategy: TradingStrategy, override_checks: bool) -> Dict:
        """Validate if strategy can be enabled."""
        
        if override_checks:
            return {'allowed': True, 'warnings': ['Override checks enabled']}
        
        # Check if strategy is deprecated
        if strategy.lifecycle.status == StrategyStatus.DEPRECATED:
            return {'allowed': False, 'reason': 'Cannot enable deprecated strategy'}
        
        # Check recent control actions (cooldown)
        recent_actions = await self._get_recent_control_actions(strategy.strategy_id, hours=self.control_limits['cooldown_period_hours'])
        if recent_actions:
            return {'allowed': False, 'reason': f'Cooldown period active - last action {recent_actions[0]["timestamp"]}'}
        
        # Check performance criteria
        performance = strategy.performance.overall
        warnings = []
        
        if performance.total_trades < 30:
            warnings.append('Low sample size - fewer than 30 trades')
        
        if performance.sharpe_ratio < Decimal('0.5'):
            warnings.append(f'Low Sharpe ratio: {performance.sharpe_ratio:.2f}')
        
        if performance.max_drawdown > Decimal('0.15'):
            warnings.append(f'High maximum drawdown: {performance.max_drawdown:.1%}')
        
        return {'allowed': True, 'warnings': warnings}
    
    async def _validate_allocation_change(self, strategy: TradingStrategy, new_allocation: Decimal) -> Dict:
        """Validate allocation change."""
        
        current_allocation = strategy.configuration.weight
        allocation_change = abs(new_allocation - current_allocation)
        
        # Check allocation limits
        if new_allocation < Decimal('0') or new_allocation > Decimal('1'):
            return {'allowed': False, 'reason': 'Allocation must be between 0% and 100%'}
        
        if new_allocation > self.control_limits['max_allocation']:
            return {'allowed': False, 'reason': f'Allocation exceeds maximum of {self.control_limits["max_allocation"]:.1%}'}
        
        if allocation_change > self.control_limits['max_allocation_change']:
            return {'allowed': False, 'reason': f'Allocation change exceeds maximum of {self.control_limits["max_allocation_change"]:.1%}'}
        
        # Check strategy maximum allocation
        if new_allocation > strategy.configuration.max_allocation:
            return {'allowed': False, 'reason': f'Allocation exceeds strategy maximum of {strategy.configuration.max_allocation:.1%}'}
        
        return {'allowed': True}
    
    async def _validate_configuration_changes(self, strategy: TradingStrategy, changes: Dict) -> Dict:
        """Validate configuration changes."""
        
        # Validate max_allocation
        if 'max_allocation' in changes:
            max_alloc = Decimal(str(changes['max_allocation']))
            if max_alloc <= Decimal('0') or max_alloc > Decimal('1'):
                return {'allowed': False, 'reason': 'Max allocation must be between 0% and 100%'}
            
            if max_alloc > self.control_limits['max_allocation']:
                return {'allowed': False, 'reason': f'Max allocation exceeds system limit of {self.control_limits["max_allocation"]:.1%}'}
        
        # Validate min_trades_for_evaluation
        if 'min_trades_for_evaluation' in changes:
            min_trades = int(changes['min_trades_for_evaluation'])
            if min_trades < 10 or min_trades > 1000:
                return {'allowed': False, 'reason': 'Min trades for evaluation must be between 10 and 1000'}
        
        # Validate evaluation_period
        if 'evaluation_period' in changes:
            eval_period = int(changes['evaluation_period'])
            if eval_period < 7 or eval_period > 365:
                return {'allowed': False, 'reason': 'Evaluation period must be between 7 and 365 days'}
        
        return {'allowed': True}
    
    async def _plan_position_closure(self, strategy: TradingStrategy, immediate: bool) -> Dict:
        """Plan position closure for disabled strategy."""
        
        # In production, would query actual positions and create closure plan
        return {
            'method': 'immediate' if immediate else 'gradual',
            'estimated_time': '5 minutes' if immediate else '1 hour',
            'open_positions': 0,  # Would query actual positions
            'closure_plan': 'Market orders' if immediate else 'Limit orders at favorable prices'
        }
    
    async def _execute_emergency_closure(self, strategy: TradingStrategy) -> Dict:
        """Execute emergency position closure."""
        
        # In production, would immediately close all positions
        return {
            'method': 'emergency_market_orders',
            'execution_time': datetime.utcnow(),
            'positions_closed': 0,  # Would track actual closures
            'estimated_slippage': '0.1%'  # Estimated cost of emergency closure
        }
    
    async def _send_emergency_notifications(self, strategy: TradingStrategy, user_id: str, reason: str):
        """Send emergency notifications to stakeholders."""
        
        # In production, would send actual notifications
        logger.critical(f"EMERGENCY NOTIFICATION: Strategy {strategy.strategy_name} ({strategy.strategy_id}) stopped by {user_id}: {reason}")
    
    async def _get_recent_control_actions(self, strategy_id: str, hours: int) -> List[Dict]:
        """Get recent control actions for cooldown checking."""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        recent_actions = [
            entry for entry in self.audit_trail
            if entry['strategy_id'] == strategy_id and entry['timestamp'] >= cutoff_time
        ]
        
        return sorted(recent_actions, key=lambda x: x['timestamp'], reverse=True)
    
    async def _log_control_action(self, operation_id: str, action: str, strategy_id: str,
                                user_id: str, reason: str, previous_state: Dict,
                                new_state: Dict, validation_warnings: List[str] = None,
                                additional_data: Dict = None):
        """Log control action to audit trail."""
        
        audit_entry = {
            'operation_id': operation_id,
            'timestamp': datetime.utcnow(),
            'action': action,
            'strategy_id': strategy_id,
            'user_id': user_id,
            'reason': reason,
            'previous_state': previous_state,
            'new_state': new_state,
            'validation_warnings': validation_warnings or [],
            'additional_data': additional_data or {}
        }
        
        self.audit_trail.append(audit_entry)
        
        # Keep only last 1000 entries (in production, would persist to database)
        if len(self.audit_trail) > 1000:
            self.audit_trail = self.audit_trail[-1000:]
        
        logger.info(f"Control action logged: {action} for strategy {strategy_id} by {user_id}")
    
    def _create_operation_result(self, operation_id: str, success: bool, action: str,
                               strategy_id: str, user_id: str, reason: str,
                               changes: Dict = None, error: str = None) -> Dict[str, Any]:
        """Create standardized operation result."""
        
        result = {
            'operation_id': operation_id,
            'timestamp': datetime.utcnow(),
            'success': success,
            'action': action,
            'strategy_id': strategy_id,
            'user_id': user_id,
            'reason': reason
        }
        
        if success:
            result['changes'] = changes or {}
        else:
            result['error'] = error
        
        return result