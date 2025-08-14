"""
Parameter Constraints System

Implements safety constraints and limits for parameter changes including
monthly change limits, safety bounds, and gradual adjustment mechanisms.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import logging

from .models import (
    ParameterAdjustment, ParameterCategory, MonthlyChangeTracker,
    RollbackCondition, RollbackSeverity, generate_id, get_current_month
)

logger = logging.getLogger(__name__)


class ParameterConstraints:
    """
    Enforces safety constraints on parameter changes
    """
    
    def __init__(self, storage_path: str = "./parameter_constraints"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Monthly change limits by category
        self.monthly_limits = {
            ParameterCategory.POSITION_SIZING: 0.10,    # 10% max change
            ParameterCategory.STOP_LOSS: 0.15,          # 15% max change
            ParameterCategory.TAKE_PROFIT: 0.10,        # 10% max change
            ParameterCategory.SIGNAL_FILTERING: 0.05    # 5% max change
        }
        
        # Absolute parameter bounds
        self.absolute_bounds = {
            "base_risk_per_trade": (0.005, 0.030),       # 0.5% to 3%
            "atr_multiplier": (1.0, 4.0),               # 1x to 4x ATR
            "base_risk_reward_ratio": (1.0, 5.0),       # 1:1 to 5:1
            "confidence_threshold": (0.60, 0.90),       # 60% to 90%
            "kelly_multiplier": (0.1, 0.5),             # 10% to 50% of Kelly
            "max_position_size": (0.01, 0.05),          # 1% to 5%
            "min_stop_distance": (5.0, 50.0),           # 5 to 50 pips
            "max_stop_distance": (50.0, 200.0),         # 50 to 200 pips
            "profit_target_multiplier": (0.5, 3.0),     # 0.5x to 3x base target
            "strength_minimum": (0.5, 0.9),             # 50% to 90%
            "pattern_reliability_threshold": (0.5, 0.9), # 50% to 90%
            "news_event_buffer": (30.0, 120.0)          # 30 to 120 minutes
        }
        
        # Change tracking
        self.monthly_trackers: Dict[str, MonthlyChangeTracker] = {}
        self.load_monthly_trackers()
        
    def validate_adjustment(self, account_id: str, adjustment: ParameterAdjustment) -> Tuple[bool, List[str]]:
        """
        Validate a parameter adjustment against all constraints
        
        Args:
            account_id: Account identifier
            adjustment: Parameter adjustment to validate
            
        Returns:
            Tuple of (is_valid, list_of_violations)
        """
        try:
            violations = []
            
            # Check monthly change limits
            monthly_valid, monthly_violations = self._check_monthly_limits(account_id, adjustment)
            if not monthly_valid:
                violations.extend(monthly_violations)
            
            # Check absolute bounds
            bounds_valid, bounds_violations = self._check_absolute_bounds(adjustment)
            if not bounds_valid:
                violations.extend(bounds_violations)
            
            # Check change magnitude
            magnitude_valid, magnitude_violations = self._check_change_magnitude(adjustment)
            if not magnitude_valid:
                violations.extend(magnitude_violations)
            
            # Check correlation impact
            correlation_valid, correlation_violations = self._check_correlation_impact(account_id, adjustment)
            if not correlation_valid:
                violations.extend(correlation_violations)
            
            # Update constraint status in adjustment
            adjustment.constraints = {
                "within_monthly_limit": monthly_valid,
                "within_safety_bounds": bounds_valid,
                "correlation_impact": 0.0  # Simplified for now
            }
            
            is_valid = len(violations) == 0
            
            logger.info(f"Parameter validation for {account_id}: {'PASSED' if is_valid else 'FAILED'}")
            if violations:
                logger.warning(f"Constraint violations: {violations}")
            
            return is_valid, violations
            
        except Exception as e:
            logger.error(f"Parameter validation failed for {account_id}: {e}")
            return False, [f"Validation error: {str(e)}"]
    
    def _check_monthly_limits(self, account_id: str, adjustment: ParameterAdjustment) -> Tuple[bool, List[str]]:
        """Check monthly change limits"""
        try:
            current_month = get_current_month()
            tracker_key = f"{account_id}_{current_month}"
            
            # Get or create monthly tracker
            if tracker_key not in self.monthly_trackers:
                self.monthly_trackers[tracker_key] = MonthlyChangeTracker(
                    account_id=account_id,
                    month=current_month
                )
            
            tracker = self.monthly_trackers[tracker_key]
            category = adjustment.category
            
            # Get current month's changes for this category
            current_changes = getattr(tracker, f"{category.value}_changes", 0.0)
            
            # Get monthly limit for this category
            monthly_limit = self.monthly_limits.get(category, 0.10)
            
            # Calculate new total change
            new_change = abs(adjustment.change_percentage)
            total_change = current_changes + new_change
            
            violations = []
            
            if total_change > monthly_limit:
                violations.append(
                    f"Monthly change limit exceeded for {category.value}: "
                    f"{total_change:.1%} > {monthly_limit:.1%}"
                )
                return False, violations
            
            return True, []
            
        except Exception as e:
            logger.warning(f"Monthly limit check failed: {e}")
            return False, [f"Monthly limit check error: {str(e)}"]
    
    def _check_absolute_bounds(self, adjustment: ParameterAdjustment) -> Tuple[bool, List[str]]:
        """Check absolute parameter bounds"""
        try:
            parameter_name = adjustment.parameter_name
            proposed_value = adjustment.proposed_value
            
            if parameter_name in self.absolute_bounds:
                min_val, max_val = self.absolute_bounds[parameter_name]
                
                if not (min_val <= proposed_value <= max_val):
                    violation = (
                        f"Parameter {parameter_name} value {proposed_value:.4f} "
                        f"outside bounds [{min_val:.4f}, {max_val:.4f}]"
                    )
                    return False, [violation]
            
            return True, []
            
        except Exception as e:
            logger.warning(f"Absolute bounds check failed: {e}")
            return False, [f"Bounds check error: {str(e)}"]
    
    def _check_change_magnitude(self, adjustment: ParameterAdjustment) -> Tuple[bool, List[str]]:
        """Check if change magnitude is reasonable"""
        try:
            change_pct = abs(adjustment.change_percentage)
            violations = []
            
            # Category-specific change limits per adjustment
            max_single_changes = {
                ParameterCategory.POSITION_SIZING: 0.25,    # Max 25% change at once
                ParameterCategory.STOP_LOSS: 0.30,          # Max 30% change at once
                ParameterCategory.TAKE_PROFIT: 0.25,        # Max 25% change at once
                ParameterCategory.SIGNAL_FILTERING: 0.15    # Max 15% change at once
            }
            
            max_change = max_single_changes.get(adjustment.category, 0.25)
            
            if change_pct > max_change:
                violations.append(
                    f"Single change too large for {adjustment.category.value}: "
                    f"{change_pct:.1%} > {max_change:.1%}"
                )
                return False, violations
            
            # Check for extremely small changes (might be noise)
            if change_pct < 0.02:  # Less than 2% change
                violations.append(
                    f"Change too small to be meaningful: {change_pct:.1%} < 2%"
                )
                return False, violations
            
            return True, []
            
        except Exception as e:
            logger.warning(f"Change magnitude check failed: {e}")
            return False, [f"Magnitude check error: {str(e)}"]
    
    def _check_correlation_impact(self, account_id: str, adjustment: ParameterAdjustment) -> Tuple[bool, List[str]]:
        """Check impact on strategy correlation (simplified)"""
        try:
            # Simplified correlation check
            # In practice, this would analyze how the change affects correlation with other accounts
            
            # For now, just check if the change is extreme
            change_pct = abs(adjustment.change_percentage)
            
            if change_pct > 0.5:  # More than 50% change might affect correlation
                violation = f"Large parameter change may impact strategy correlation: {change_pct:.1%}"
                return False, [violation]
            
            return True, []
            
        except Exception as e:
            logger.warning(f"Correlation impact check failed: {e}")
            return True, []  # Don't fail validation on correlation check errors
    
    def record_adjustment(self, account_id: str, adjustment: ParameterAdjustment):
        """Record an approved adjustment for monthly tracking"""
        try:
            current_month = get_current_month()
            tracker_key = f"{account_id}_{current_month}"
            
            # Get or create monthly tracker
            if tracker_key not in self.monthly_trackers:
                self.monthly_trackers[tracker_key] = MonthlyChangeTracker(
                    account_id=account_id,
                    month=current_month
                )
            
            tracker = self.monthly_trackers[tracker_key]
            category = adjustment.category
            change_amount = abs(adjustment.change_percentage)
            
            # Update the appropriate category change total
            if category == ParameterCategory.POSITION_SIZING:
                tracker.position_sizing_changes += change_amount
            elif category == ParameterCategory.STOP_LOSS:
                tracker.stop_loss_changes += change_amount
            elif category == ParameterCategory.TAKE_PROFIT:
                tracker.take_profit_changes += change_amount
            elif category == ParameterCategory.SIGNAL_FILTERING:
                tracker.signal_filtering_changes += change_amount
            
            # Add to change history
            tracker.changes_this_month.append(adjustment.adjustment_id)
            
            # Save updated tracker
            self._save_monthly_tracker(tracker_key, tracker)
            
            logger.info(f"Recorded parameter change for {account_id}: {category.value} +{change_amount:.1%}")
            
        except Exception as e:
            logger.error(f"Failed to record adjustment for {account_id}: {e}")
    
    def get_remaining_monthly_budget(self, account_id: str, category: ParameterCategory) -> float:
        """Get remaining monthly change budget for a category"""
        try:
            current_month = get_current_month()
            tracker_key = f"{account_id}_{current_month}"
            
            if tracker_key not in self.monthly_trackers:
                # No changes this month yet
                return self.monthly_limits.get(category, 0.10)
            
            tracker = self.monthly_trackers[tracker_key]
            monthly_limit = self.monthly_limits.get(category, 0.10)
            
            # Get current usage
            if category == ParameterCategory.POSITION_SIZING:
                current_usage = tracker.position_sizing_changes
            elif category == ParameterCategory.STOP_LOSS:
                current_usage = tracker.stop_loss_changes
            elif category == ParameterCategory.TAKE_PROFIT:
                current_usage = tracker.take_profit_changes
            elif category == ParameterCategory.SIGNAL_FILTERING:
                current_usage = tracker.signal_filtering_changes
            else:
                current_usage = 0.0
            
            remaining = monthly_limit - current_usage
            return max(0.0, remaining)
            
        except Exception as e:
            logger.warning(f"Failed to get monthly budget for {account_id}: {e}")
            return 0.0
    
    def create_gradual_adjustment_plan(self, adjustment: ParameterAdjustment,
                                     target_months: int = 3) -> List[ParameterAdjustment]:
        """Create a plan for gradual parameter adjustment over multiple months"""
        try:
            if target_months <= 1:
                return [adjustment]
            
            # Calculate monthly increments
            total_change = adjustment.proposed_value - adjustment.current_value
            monthly_increment = total_change / target_months
            
            # Create monthly adjustments
            gradual_adjustments = []
            current_value = adjustment.current_value
            
            for month in range(target_months):
                if month == target_months - 1:
                    # Last adjustment gets to final value
                    new_value = adjustment.proposed_value
                else:
                    new_value = current_value + monthly_increment
                
                # Create adjustment for this month
                monthly_adjustment = ParameterAdjustment(
                    adjustment_id=generate_id(),
                    timestamp=adjustment.timestamp + timedelta(days=30 * month),
                    parameter_name=adjustment.parameter_name,
                    category=adjustment.category,
                    current_value=current_value,
                    proposed_value=new_value,
                    change_percentage=(new_value - current_value) / current_value,
                    change_reason=f"Gradual adjustment month {month + 1}/{target_months}: {adjustment.change_reason}",
                    analysis=adjustment.analysis.copy(),
                    constraints=adjustment.constraints.copy()
                )
                
                gradual_adjustments.append(monthly_adjustment)
                current_value = new_value
            
            logger.info(f"Created gradual adjustment plan: {len(gradual_adjustments)} monthly steps")
            return gradual_adjustments
            
        except Exception as e:
            logger.error(f"Failed to create gradual adjustment plan: {e}")
            return [adjustment]
    
    def create_rollback_conditions(self, adjustment: ParameterAdjustment) -> List[RollbackCondition]:
        """Create rollback conditions for a parameter change"""
        try:
            conditions = []
            
            # Performance degradation condition
            conditions.append(RollbackCondition(
                condition_id=generate_id(),
                condition_type="performance_degradation",
                threshold=0.2,  # 20% performance drop
                evaluation_period=7,  # 7 days
                trigger_count=3,  # Must happen 3 times
                severity=RollbackSeverity.WARNING,
                automatic_rollback=False,
                description="Rollback if performance degrades by 20% for 3 consecutive evaluations"
            ))
            
            # Drawdown increase condition
            conditions.append(RollbackCondition(
                condition_id=generate_id(),
                condition_type="drawdown_increase",
                threshold=0.05,  # 5% additional drawdown
                evaluation_period=5,  # 5 days
                trigger_count=2,  # Must happen 2 times
                severity=RollbackSeverity.CRITICAL,
                automatic_rollback=True,
                description="Automatic rollback if drawdown increases by 5% for 2 evaluations"
            ))
            
            # Volatility spike condition (for position sizing changes)
            if adjustment.category == ParameterCategory.POSITION_SIZING:
                conditions.append(RollbackCondition(
                    condition_id=generate_id(),
                    condition_type="volatility_spike",
                    threshold=2.0,  # 2x normal volatility
                    evaluation_period=3,  # 3 days
                    trigger_count=1,  # Immediate trigger
                    severity=RollbackSeverity.WARNING,
                    automatic_rollback=False,
                    description="Warning if portfolio volatility spikes to 2x normal levels"
                ))
            
            return conditions
            
        except Exception as e:
            logger.error(f"Failed to create rollback conditions: {e}")
            return []
    
    def load_monthly_trackers(self):
        """Load monthly change trackers from storage"""
        try:
            tracker_file = self.storage_path / "monthly_trackers.json"
            
            if tracker_file.exists():
                with open(tracker_file, 'r') as f:
                    data = json.load(f)
                
                for key, tracker_data in data.items():
                    tracker = MonthlyChangeTracker(
                        account_id=tracker_data["account_id"],
                        month=tracker_data["month"],
                        position_sizing_changes=tracker_data.get("position_sizing_changes", 0.0),
                        stop_loss_changes=tracker_data.get("stop_loss_changes", 0.0),
                        take_profit_changes=tracker_data.get("take_profit_changes", 0.0),
                        signal_filtering_changes=tracker_data.get("signal_filtering_changes", 0.0),
                        changes_this_month=tracker_data.get("changes_this_month", [])
                    )
                    self.monthly_trackers[key] = tracker
                
                logger.info(f"Loaded {len(self.monthly_trackers)} monthly change trackers")
            
        except Exception as e:
            logger.warning(f"Failed to load monthly trackers: {e}")
    
    def _save_monthly_tracker(self, tracker_key: str, tracker: MonthlyChangeTracker):
        """Save a specific monthly tracker"""
        try:
            # Load all trackers
            all_trackers = {}
            tracker_file = self.storage_path / "monthly_trackers.json"
            
            if tracker_file.exists():
                with open(tracker_file, 'r') as f:
                    all_trackers = json.load(f)
            
            # Update the specific tracker
            all_trackers[tracker_key] = {
                "account_id": tracker.account_id,
                "month": tracker.month,
                "position_sizing_changes": tracker.position_sizing_changes,
                "stop_loss_changes": tracker.stop_loss_changes,
                "take_profit_changes": tracker.take_profit_changes,
                "signal_filtering_changes": tracker.signal_filtering_changes,
                "changes_this_month": tracker.changes_this_month
            }
            
            # Save all trackers
            with open(tracker_file, 'w') as f:
                json.dump(all_trackers, f, indent=2)
            
        except Exception as e:
            logger.error(f"Failed to save monthly tracker: {e}")
    
    def cleanup_old_trackers(self, months_to_keep: int = 12):
        """Clean up old monthly trackers"""
        try:
            current_date = datetime.utcnow()
            cutoff_date = current_date - timedelta(days=30 * months_to_keep)
            
            keys_to_remove = []
            for key, tracker in self.monthly_trackers.items():
                try:
                    tracker_date = datetime.strptime(tracker.month, "%Y-%m")
                    if tracker_date < cutoff_date:
                        keys_to_remove.append(key)
                except ValueError:
                    # Invalid date format, remove it
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self.monthly_trackers[key]
            
            logger.info(f"Cleaned up {len(keys_to_remove)} old monthly trackers")
            
            # Save updated trackers
            if keys_to_remove:
                tracker_file = self.storage_path / "monthly_trackers.json"
                all_trackers = {
                    key: {
                        "account_id": tracker.account_id,
                        "month": tracker.month,
                        "position_sizing_changes": tracker.position_sizing_changes,
                        "stop_loss_changes": tracker.stop_loss_changes,
                        "take_profit_changes": tracker.take_profit_changes,
                        "signal_filtering_changes": tracker.signal_filtering_changes,
                        "changes_this_month": tracker.changes_this_month
                    }
                    for key, tracker in self.monthly_trackers.items()
                }
                
                with open(tracker_file, 'w') as f:
                    json.dump(all_trackers, f, indent=2)
            
        except Exception as e:
            logger.error(f"Failed to cleanup old trackers: {e}")
    
    def get_constraint_summary(self, account_id: str) -> Dict[str, any]:
        """Get summary of current constraints and usage"""
        try:
            current_month = get_current_month()
            tracker_key = f"{account_id}_{current_month}"
            
            summary = {
                "monthly_limits": dict(self.monthly_limits),
                "absolute_bounds": dict(self.absolute_bounds),
                "current_month": current_month,
                "monthly_usage": {}
            }
            
            if tracker_key in self.monthly_trackers:
                tracker = self.monthly_trackers[tracker_key]
                summary["monthly_usage"] = {
                    "position_sizing": {
                        "used": tracker.position_sizing_changes,
                        "limit": self.monthly_limits[ParameterCategory.POSITION_SIZING],
                        "remaining": self.get_remaining_monthly_budget(account_id, ParameterCategory.POSITION_SIZING)
                    },
                    "stop_loss": {
                        "used": tracker.stop_loss_changes,
                        "limit": self.monthly_limits[ParameterCategory.STOP_LOSS],
                        "remaining": self.get_remaining_monthly_budget(account_id, ParameterCategory.STOP_LOSS)
                    },
                    "take_profit": {
                        "used": tracker.take_profit_changes,
                        "limit": self.monthly_limits[ParameterCategory.TAKE_PROFIT],
                        "remaining": self.get_remaining_monthly_budget(account_id, ParameterCategory.TAKE_PROFIT)
                    },
                    "signal_filtering": {
                        "used": tracker.signal_filtering_changes,
                        "limit": self.monthly_limits[ParameterCategory.SIGNAL_FILTERING],
                        "remaining": self.get_remaining_monthly_budget(account_id, ParameterCategory.SIGNAL_FILTERING)
                    }
                }
            else:
                # No usage this month
                for category in ParameterCategory:
                    summary["monthly_usage"][category.value] = {
                        "used": 0.0,
                        "limit": self.monthly_limits[category],
                        "remaining": self.monthly_limits[category]
                    }
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get constraint summary for {account_id}: {e}")
            return {}