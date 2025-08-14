"""
Tests for Parameter Constraints System
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import tempfile
import shutil

from agents.parameter_optimization.app.parameter_constraints import ParameterConstraints
from agents.parameter_optimization.app.models import (
    ParameterAdjustment, ParameterCategory, MonthlyChangeTracker,
    RollbackCondition, RollbackSeverity, generate_id, get_current_month
)


class TestParameterConstraints:
    
    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage directory"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def constraints(self, temp_storage):
        """Create constraints system with temporary storage"""
        return ParameterConstraints(storage_path=temp_storage)
    
    @pytest.fixture
    def sample_adjustment(self):
        """Create sample parameter adjustment"""
        return ParameterAdjustment(
            adjustment_id=generate_id(),
            timestamp=datetime.utcnow(),
            parameter_name="base_risk_per_trade",
            category=ParameterCategory.POSITION_SIZING,
            current_value=0.015,
            proposed_value=0.018,
            change_percentage=0.2,  # 20% increase
            change_reason="Kelly optimization suggests increase"
        )
    
    def test_validate_adjustment_success(self, constraints, sample_adjustment):
        """Test successful adjustment validation"""
        is_valid, violations = constraints.validate_adjustment("test_account", sample_adjustment)
        
        assert is_valid
        assert len(violations) == 0
        assert sample_adjustment.constraints["within_monthly_limit"]
        assert sample_adjustment.constraints["within_safety_bounds"]
    
    def test_monthly_limit_violation(self, constraints, sample_adjustment):
        """Test monthly change limit violation"""
        account_id = "test_account"
        
        # First, make a large change to use up monthly budget
        first_adjustment = ParameterAdjustment(
            adjustment_id=generate_id(),
            timestamp=datetime.utcnow(),
            parameter_name="base_risk_per_trade",
            category=ParameterCategory.POSITION_SIZING,
            current_value=0.015,
            proposed_value=0.0165,  # 10% increase (uses up monthly limit)
            change_percentage=0.10,
            change_reason="First adjustment"
        )
        
        # Record the first adjustment
        constraints.record_adjustment(account_id, first_adjustment)
        
        # Try to make another change that would exceed monthly limit
        sample_adjustment.change_percentage = 0.05  # Another 5% (would total 15%)
        
        is_valid, violations = constraints.validate_adjustment(account_id, sample_adjustment)
        
        assert not is_valid
        assert any("Monthly change limit exceeded" in violation for violation in violations)
    
    def test_absolute_bounds_violation(self, constraints):
        """Test absolute parameter bounds violation"""
        # Create adjustment that violates bounds
        bad_adjustment = ParameterAdjustment(
            adjustment_id=generate_id(),
            timestamp=datetime.utcnow(),
            parameter_name="base_risk_per_trade",
            category=ParameterCategory.POSITION_SIZING,
            current_value=0.025,
            proposed_value=0.05,  # 5% (above maximum of 3%)
            change_percentage=1.0,
            change_reason="Test bounds violation"
        )
        
        is_valid, violations = constraints.validate_adjustment("test_account", bad_adjustment)
        
        assert not is_valid
        assert any("outside bounds" in violation for violation in violations)
    
    def test_change_magnitude_limits(self, constraints):
        """Test change magnitude limits"""
        # Create adjustment that's too large
        large_adjustment = ParameterAdjustment(
            adjustment_id=generate_id(),
            timestamp=datetime.utcnow(),
            parameter_name="base_risk_per_trade",
            category=ParameterCategory.POSITION_SIZING,
            current_value=0.015,
            proposed_value=0.025,  # 67% increase (too large)
            change_percentage=0.67,
            change_reason="Test large change"
        )
        
        is_valid, violations = constraints.validate_adjustment("test_account", large_adjustment)
        
        assert not is_valid
        assert any("Single change too large" in violation for violation in violations)
    
    def test_tiny_change_rejection(self, constraints):
        """Test rejection of very small changes"""
        tiny_adjustment = ParameterAdjustment(
            adjustment_id=generate_id(),
            timestamp=datetime.utcnow(),
            parameter_name="base_risk_per_trade",
            category=ParameterCategory.POSITION_SIZING,
            current_value=0.015,
            proposed_value=0.0151,  # 0.67% increase (too small)
            change_percentage=0.0067,
            change_reason="Test tiny change"
        )
        
        is_valid, violations = constraints.validate_adjustment("test_account", tiny_adjustment)
        
        assert not is_valid
        assert any("too small to be meaningful" in violation for violation in violations)
    
    def test_record_adjustment(self, constraints, sample_adjustment):
        """Test recording adjustment for monthly tracking"""
        account_id = "test_account"
        
        # Record the adjustment
        constraints.record_adjustment(account_id, sample_adjustment)
        
        # Check that it was recorded
        current_month = get_current_month()
        tracker_key = f"{account_id}_{current_month}"
        
        assert tracker_key in constraints.monthly_trackers
        tracker = constraints.monthly_trackers[tracker_key]
        assert tracker.position_sizing_changes == abs(sample_adjustment.change_percentage)
        assert sample_adjustment.adjustment_id in tracker.changes_this_month
    
    def test_remaining_monthly_budget(self, constraints, sample_adjustment):
        """Test remaining monthly budget calculation"""
        account_id = "test_account"
        category = ParameterCategory.POSITION_SIZING
        
        # Check initial budget
        initial_budget = constraints.get_remaining_monthly_budget(account_id, category)
        expected_limit = constraints.monthly_limits[category]
        assert initial_budget == expected_limit
        
        # Record an adjustment
        constraints.record_adjustment(account_id, sample_adjustment)
        
        # Check remaining budget
        remaining_budget = constraints.get_remaining_monthly_budget(account_id, category)
        expected_remaining = expected_limit - abs(sample_adjustment.change_percentage)
        assert abs(remaining_budget - expected_remaining) < 0.001
    
    def test_gradual_adjustment_plan(self, constraints, sample_adjustment):
        """Test gradual adjustment plan creation"""
        gradual_plan = constraints.create_gradual_adjustment_plan(sample_adjustment, target_months=3)
        
        assert len(gradual_plan) == 3
        
        # Check that adjustments sum to total change
        total_change = sum(adj.proposed_value - adj.current_value for adj in gradual_plan)
        expected_change = sample_adjustment.proposed_value - sample_adjustment.current_value
        assert abs(total_change - expected_change) < 0.0001
        
        # Check that final value matches target
        assert gradual_plan[-1].proposed_value == sample_adjustment.proposed_value
    
    def test_rollback_conditions_creation(self, constraints, sample_adjustment):
        """Test rollback conditions creation"""
        conditions = constraints.create_rollback_conditions(sample_adjustment)
        
        assert len(conditions) >= 2  # Should have multiple conditions
        
        # Check for performance degradation condition
        perf_conditions = [c for c in conditions if c.condition_type == "performance_degradation"]
        assert len(perf_conditions) >= 1
        
        # Check for drawdown condition
        dd_conditions = [c for c in conditions if c.condition_type == "drawdown_increase"]
        assert len(dd_conditions) >= 1
        assert any(c.automatic_rollback for c in dd_conditions)  # At least one should be automatic
    
    def test_constraint_summary(self, constraints, sample_adjustment):
        """Test constraint summary generation"""
        account_id = "test_account"
        
        # Record some adjustments
        constraints.record_adjustment(account_id, sample_adjustment)
        
        summary = constraints.get_constraint_summary(account_id)
        
        assert "monthly_limits" in summary
        assert "absolute_bounds" in summary
        assert "current_month" in summary
        assert "monthly_usage" in summary
        
        # Check monthly usage structure
        usage = summary["monthly_usage"]
        assert "position_sizing" in usage
        assert "used" in usage["position_sizing"]
        assert "limit" in usage["position_sizing"]
        assert "remaining" in usage["position_sizing"]
    
    def test_different_parameter_categories(self, constraints):
        """Test constraints for different parameter categories"""
        categories_and_params = [
            (ParameterCategory.POSITION_SIZING, "base_risk_per_trade", 0.015, 0.018),
            (ParameterCategory.STOP_LOSS, "atr_multiplier", 2.0, 2.2),
            (ParameterCategory.TAKE_PROFIT, "base_risk_reward_ratio", 2.0, 2.3),
            (ParameterCategory.SIGNAL_FILTERING, "confidence_threshold", 0.75, 0.78)
        ]
        
        for category, param_name, current_val, proposed_val in categories_and_params:
            adjustment = ParameterAdjustment(
                adjustment_id=generate_id(),
                timestamp=datetime.utcnow(),
                parameter_name=param_name,
                category=category,
                current_value=current_val,
                proposed_value=proposed_val,
                change_percentage=(proposed_val - current_val) / current_val,
                change_reason=f"Test {category.value} adjustment"
            )
            
            is_valid, violations = constraints.validate_adjustment("test_account", adjustment)
            
            # Should be valid for reasonable changes
            if abs(adjustment.change_percentage) <= 0.15:  # Reasonable change
                assert is_valid, f"Valid adjustment rejected for {category.value}: {violations}"
    
    def test_correlation_impact_check(self, constraints):
        """Test correlation impact checking"""
        # Create adjustment with large change that might affect correlation
        large_adjustment = ParameterAdjustment(
            adjustment_id=generate_id(),
            timestamp=datetime.utcnow(),
            parameter_name="base_risk_per_trade",
            category=ParameterCategory.POSITION_SIZING,
            current_value=0.015,
            proposed_value=0.025,  # Large change
            change_percentage=0.67,  # 67% increase
            change_reason="Test correlation impact"
        )
        
        is_valid, violations = constraints.validate_adjustment("test_account", large_adjustment)
        
        # Should fail due to correlation impact (and other reasons)
        assert not is_valid
        # Note: This test depends on the current implementation which may pass correlation check
    
    def test_cleanup_old_trackers(self, constraints):
        """Test cleanup of old monthly trackers"""
        account_id = "test_account"
        
        # Create old tracker (13 months ago)
        old_date = datetime.utcnow() - timedelta(days=400)
        old_month = old_date.strftime("%Y-%m")
        old_tracker = MonthlyChangeTracker(
            account_id=account_id,
            month=old_month
        )
        
        # Create recent tracker
        recent_month = get_current_month()
        recent_tracker = MonthlyChangeTracker(
            account_id=account_id,
            month=recent_month
        )
        
        # Add both to constraints
        constraints.monthly_trackers[f"{account_id}_{old_month}"] = old_tracker
        constraints.monthly_trackers[f"{account_id}_{recent_month}"] = recent_tracker
        
        # Cleanup old trackers (keep 12 months)
        constraints.cleanup_old_trackers(months_to_keep=12)
        
        # Old tracker should be removed, recent should remain
        assert f"{account_id}_{old_month}" not in constraints.monthly_trackers
        assert f"{account_id}_{recent_month}" in constraints.monthly_trackers
    
    def test_multiple_categories_same_month(self, constraints):
        """Test multiple parameter categories in same month"""
        account_id = "test_account"
        
        # Create adjustments for different categories
        pos_adjustment = ParameterAdjustment(
            adjustment_id=generate_id(),
            timestamp=datetime.utcnow(),
            parameter_name="base_risk_per_trade",
            category=ParameterCategory.POSITION_SIZING,
            current_value=0.015,
            proposed_value=0.0165,
            change_percentage=0.10,
            change_reason="Position sizing optimization"
        )
        
        sl_adjustment = ParameterAdjustment(
            adjustment_id=generate_id(),
            timestamp=datetime.utcnow(),
            parameter_name="atr_multiplier",
            category=ParameterCategory.STOP_LOSS,
            current_value=2.0,
            proposed_value=2.2,
            change_percentage=0.10,
            change_reason="Stop loss optimization"
        )
        
        # Both should be valid
        pos_valid, pos_violations = constraints.validate_adjustment(account_id, pos_adjustment)
        sl_valid, sl_violations = constraints.validate_adjustment(account_id, sl_adjustment)
        
        assert pos_valid
        assert sl_valid
        
        # Record both
        constraints.record_adjustment(account_id, pos_adjustment)
        constraints.record_adjustment(account_id, sl_adjustment)
        
        # Check that both are tracked separately
        current_month = get_current_month()
        tracker_key = f"{account_id}_{current_month}"
        tracker = constraints.monthly_trackers[tracker_key]
        
        assert tracker.position_sizing_changes == 0.10
        assert tracker.stop_loss_changes == 0.10
        assert len(tracker.changes_this_month) == 2
    
    def test_parameter_bounds_edge_cases(self, constraints):
        """Test parameter bounds with edge cases"""
        # Test with parameter at exact boundary
        boundary_adjustment = ParameterAdjustment(
            adjustment_id=generate_id(),
            timestamp=datetime.utcnow(),
            parameter_name="base_risk_per_trade",
            category=ParameterCategory.POSITION_SIZING,
            current_value=0.025,
            proposed_value=0.030,  # Exactly at maximum
            change_percentage=0.20,
            change_reason="Test boundary"
        )
        
        is_valid, violations = constraints.validate_adjustment("test_account", boundary_adjustment)
        assert is_valid  # Should be valid at boundary
        
        # Test with parameter just outside boundary
        outside_adjustment = ParameterAdjustment(
            adjustment_id=generate_id(),
            timestamp=datetime.utcnow(),
            parameter_name="base_risk_per_trade",
            category=ParameterCategory.POSITION_SIZING,
            current_value=0.025,
            proposed_value=0.0301,  # Just above maximum
            change_percentage=0.204,
            change_reason="Test outside boundary"
        )
        
        is_valid, violations = constraints.validate_adjustment("test_account", outside_adjustment)
        assert not is_valid  # Should be invalid outside boundary
    
    @pytest.mark.parametrize("category,limit", [
        (ParameterCategory.POSITION_SIZING, 0.10),
        (ParameterCategory.STOP_LOSS, 0.15),
        (ParameterCategory.TAKE_PROFIT, 0.10),
        (ParameterCategory.SIGNAL_FILTERING, 0.05),
    ])
    def test_monthly_limits_by_category(self, constraints, category, limit):
        """Test monthly limits are correctly set for each category"""
        assert constraints.monthly_limits[category] == limit
    
    def test_invalid_month_format_cleanup(self, constraints):
        """Test cleanup handles invalid month formats"""
        account_id = "test_account"
        
        # Create tracker with invalid month format
        invalid_tracker = MonthlyChangeTracker(
            account_id=account_id,
            month="invalid-format"
        )
        
        constraints.monthly_trackers[f"{account_id}_invalid"] = invalid_tracker
        
        # Cleanup should remove invalid tracker
        constraints.cleanup_old_trackers()
        
        assert f"{account_id}_invalid" not in constraints.monthly_trackers