"""
Tests for WeeklyPatterns module
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from agents.human_behavior.WeeklyPatterns import (
    WeeklyPatterns, WeeklyPatternsConfig, WeeklyState, 
    DayOfWeek, FridayBehavior
)


class TestWeeklyPatterns:
    """Test suite for WeeklyPatterns class"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.config = WeeklyPatternsConfig(
            end_of_week_flattening=True,
            friday_reduction=0.3,
            monday_morning_caution=0.2,
            weekend_gap_aversion=0.4,
            friday_afternoon_start=14,
            monday_caution_hours=2,
            flattening_probability=0.6,
            position_size_reduction_friday=0.5
        )
        self.weekly_patterns = WeeklyPatterns(self.config)
        self.personality_id = "test_personality_1"
        
    def test_initial_state(self):
        """Test initial weekly state"""
        info = self.weekly_patterns.get_weekly_info(self.personality_id)
        
        assert info['weekly_pnl'] == 0.0
        assert info['friday_behavior'] == FridayBehavior.NORMAL.value
        assert info['monday_caution_active'] == False
        assert info['positions_to_flatten'] == []
        assert info['week_start_date'] is None
        assert info['activity_modifier'] == 1.0
        
    def test_weekly_pnl_tracking(self):
        """Test weekly P&L tracking"""
        base_time = datetime(2025, 1, 6, 10, 0, 0)  # Monday
        
        # First trade
        trade_result_1 = {'pnl': 200, 'timestamp': base_time, 'trade_id': '1'}
        state = self.weekly_patterns.update_weekly_state(self.personality_id, trade_result_1)
        assert state.weekly_pnl == 200
        
        # Second trade same week
        trade_result_2 = {'pnl': -100, 'timestamp': base_time + timedelta(days=2), 'trade_id': '2'}
        state = self.weekly_patterns.update_weekly_state(self.personality_id, trade_result_2)
        assert state.weekly_pnl == 100
        
    def test_new_week_reset(self):
        """Test weekly counters reset on new week"""
        # Week 1 - Monday
        week1_monday = datetime(2025, 1, 6, 10, 0, 0)
        trade_week1 = {'pnl': 300, 'timestamp': week1_monday, 'trade_id': '1'}
        self.weekly_patterns.update_weekly_state(self.personality_id, trade_week1)
        
        state = self.weekly_patterns.weekly_states[self.personality_id]
        assert state.weekly_pnl == 300
        
        # Week 2 - Monday (next week)
        week2_monday = datetime(2025, 1, 13, 10, 0, 0)
        trade_week2 = {'pnl': 150, 'timestamp': week2_monday, 'trade_id': '2'}
        self.weekly_patterns.update_weekly_state(self.personality_id, trade_week2)
        
        # Should reset to new week total
        state = self.weekly_patterns.weekly_states[self.personality_id]
        assert state.weekly_pnl == 150  # Reset and new trade
        
    def test_monday_morning_caution(self):
        """Test Monday morning caution behavior"""
        # Monday morning (within caution hours)
        monday_morning = datetime(2025, 1, 6, 1, 0, 0)  # 1 AM Monday
        
        should_reduce, reduction_factor, reason = self.weekly_patterns.should_reduce_activity(
            self.personality_id, monday_morning)
        
        assert should_reduce == True
        assert reduction_factor == (1.0 - self.config.monday_morning_caution)
        assert "Monday morning caution" in reason
        
        # Monday afternoon (after caution hours)
        monday_afternoon = datetime(2025, 1, 6, 10, 0, 0)  # 10 AM Monday
        
        should_reduce, reduction_factor, reason = self.weekly_patterns.should_reduce_activity(
            self.personality_id, monday_afternoon)
        
        assert should_reduce == False
        assert reduction_factor == 1.0
        
    def test_friday_afternoon_activity_reduction(self):
        """Test Friday afternoon activity reduction"""
        # Friday morning (before afternoon start)
        friday_morning = datetime(2025, 1, 10, 10, 0, 0)  # 10 AM Friday
        
        should_reduce, reduction_factor, reason = self.weekly_patterns.should_reduce_activity(
            self.personality_id, friday_morning)
        
        assert should_reduce == False
        assert reduction_factor == 1.0
        
        # Friday afternoon (after afternoon start)
        friday_afternoon = datetime(2025, 1, 10, 15, 0, 0)  # 3 PM Friday
        
        should_reduce, reduction_factor, reason = self.weekly_patterns.should_reduce_activity(
            self.personality_id, friday_afternoon)
        
        assert should_reduce == True
        assert reduction_factor == (1.0 - self.config.friday_reduction)
        assert "Friday afternoon" in reason
        
    def test_friday_behavior_progression(self):
        """Test Friday behavior progression throughout the day"""
        base_friday = datetime(2025, 1, 10, 0, 0, 0)  # Friday
        
        # Morning - should be normal
        morning = base_friday.replace(hour=10)
        trade_morning = {'pnl': 100, 'timestamp': morning, 'trade_id': '1'}
        state = self.weekly_patterns.update_weekly_state(self.personality_id, trade_morning)
        assert state.friday_behavior == FridayBehavior.NORMAL
        
        # Afternoon - should be reducing
        afternoon = base_friday.replace(hour=15)  # 3 PM
        trade_afternoon = {'pnl': 50, 'timestamp': afternoon, 'trade_id': '2'}
        state = self.weekly_patterns.update_weekly_state(self.personality_id, trade_afternoon)
        assert state.friday_behavior in [FridayBehavior.REDUCING, FridayBehavior.FLATTENING]
        
    @patch('random.random')
    def test_position_flattening_decision(self, mock_random):
        """Test position flattening decision logic"""
        current_positions = ['pos1', 'pos2', 'pos3', 'pos4']
        friday_afternoon = datetime(2025, 1, 10, 16, 0, 0)  # 4 PM Friday
        
        # Mock random to trigger flattening
        mock_random.return_value = 0.3  # Below flattening probability (0.6)
        
        should_flatten, positions_to_flatten, reason = self.weekly_patterns.should_flatten_positions(
            self.personality_id, current_positions, friday_afternoon)
        
        assert should_flatten == True
        assert len(positions_to_flatten) >= 2  # At least half
        assert "Friday afternoon" in reason
        
        # Mock random to avoid flattening
        mock_random.return_value = 0.8  # Above flattening probability
        
        should_flatten, positions_to_flatten, reason = self.weekly_patterns.should_flatten_positions(
            self.personality_id, current_positions, friday_afternoon)
        
        assert should_flatten == False
        assert positions_to_flatten == []
        
    def test_position_size_modifiers(self):
        """Test position size modifications for different days/times"""
        # Regular Tuesday - should be normal
        tuesday = datetime(2025, 1, 7, 14, 0, 0)
        modifier = self.weekly_patterns.calculate_position_size_modifier(self.personality_id, tuesday)
        assert modifier == 1.0
        
        # Friday afternoon - should be reduced
        friday_afternoon = datetime(2025, 1, 10, 16, 0, 0)
        modifier = self.weekly_patterns.calculate_position_size_modifier(self.personality_id, friday_afternoon)
        assert modifier < 1.0
        expected = 1.0 - self.config.position_size_reduction_friday
        assert abs(modifier - expected) < 0.01
        
        # Monday morning - should be reduced
        monday_morning = datetime(2025, 1, 6, 1, 0, 0)  # 1 AM Monday
        modifier = self.weekly_patterns.calculate_position_size_modifier(self.personality_id, monday_morning)
        assert modifier < 1.0
        expected = 1.0 - self.config.monday_morning_caution
        assert abs(modifier - expected) < 0.01
        
        # Sunday evening - should be reduced (weekend gap aversion)
        sunday_evening = datetime(2025, 1, 5, 19, 0, 0)  # 7 PM Sunday
        modifier = self.weekly_patterns.calculate_position_size_modifier(self.personality_id, sunday_evening)
        assert modifier < 1.0
        expected = 1.0 - self.config.weekend_gap_aversion
        assert abs(modifier - expected) < 0.01
        
    def test_early_exit_bias(self):
        """Test early exit bias calculations"""
        # Update state first
        friday_afternoon = datetime(2025, 1, 10, 16, 0, 0)
        trade = {'pnl': 100, 'timestamp': friday_afternoon, 'trade_id': '1'}
        self.weekly_patterns.update_weekly_state(self.personality_id, trade)
        
        # Friday afternoon should have exit bias
        bias = self.weekly_patterns.get_early_exit_bias(self.personality_id, friday_afternoon)
        assert bias > 0
        
        # Regular day should have no bias
        tuesday = datetime(2025, 1, 7, 14, 0, 0)
        bias = self.weekly_patterns.get_early_exit_bias(self.personality_id, tuesday)
        assert bias == 0.0
        
    def test_position_flattening_tracking(self):
        """Test position flattening tracking"""
        position_id = "test_position_1"
        
        # Mark position as flattened
        self.weekly_patterns.mark_position_flattened(self.personality_id, position_id)
        
        # Should be in flattened list
        state = self.weekly_patterns.weekly_states[self.personality_id]
        assert position_id in state.positions_flattened_friday
        
    def test_behavioral_impact_comprehensive(self):
        """Test comprehensive behavioral impact calculation"""
        current_positions = ['pos1', 'pos2', 'pos3']
        friday_afternoon = datetime(2025, 1, 10, 16, 0, 0)
        
        # Update state first
        trade = {'pnl': 100, 'timestamp': friday_afternoon, 'trade_id': '1'}
        self.weekly_patterns.update_weekly_state(self.personality_id, trade)
        
        with patch('random.random', return_value=0.3):  # Trigger flattening
            impact = self.weekly_patterns.get_behavioral_impact(
                self.personality_id, current_positions, friday_afternoon)
        
        # Should have multiple behavioral modifications
        assert impact['activity_multiplier'] < 1.0  # Friday afternoon reduction
        assert impact['position_size_multiplier'] < 1.0  # Size reduction
        assert impact['early_exit_bias'] > 0  # Exit bias
        assert impact['should_flatten_positions'] == True
        assert len(impact['positions_to_flatten']) > 0
        assert impact['skip_new_positions'] == True  # Friday afternoon
        assert impact['tighten_stops'] == True  # Friday
        
    def test_reset_weekly_state(self):
        """Test weekly state reset functionality"""
        # Build up some state
        trade_result = {'pnl': 200, 'timestamp': datetime.now(), 'trade_id': '1'}
        self.weekly_patterns.update_weekly_state(self.personality_id, trade_result)
        
        assert self.personality_id in self.weekly_patterns.weekly_states
        
        # Reset state
        self.weekly_patterns.reset_weekly_state(self.personality_id)
        
        assert self.personality_id not in self.weekly_patterns.weekly_states
        
        # Should return default values after reset
        info = self.weekly_patterns.get_weekly_info(self.personality_id)
        assert info['weekly_pnl'] == 0.0
        assert info['friday_behavior'] == FridayBehavior.NORMAL.value
        
    def test_multiple_personalities(self):
        """Test handling multiple personalities independently"""
        personality_2 = "test_personality_2"
        
        # Give different P&L to each personality
        trade_1 = {'pnl': 300, 'timestamp': datetime.now(), 'trade_id': '1'}
        self.weekly_patterns.update_weekly_state(self.personality_id, trade_1)
        
        trade_2 = {'pnl': -150, 'timestamp': datetime.now(), 'trade_id': '1'}
        self.weekly_patterns.update_weekly_state(personality_2, trade_2)
        
        # Check they maintain separate states
        info_1 = self.weekly_patterns.get_weekly_info(self.personality_id)
        info_2 = self.weekly_patterns.get_weekly_info(personality_2)
        
        assert info_1['weekly_pnl'] == 300
        assert info_2['weekly_pnl'] == -150
        
    def test_disabled_flattening(self):
        """Test behavior when end-of-week flattening is disabled"""
        config_no_flattening = WeeklyPatternsConfig(end_of_week_flattening=False)
        weekly_patterns = WeeklyPatterns(config_no_flattening)
        
        current_positions = ['pos1', 'pos2']
        friday_afternoon = datetime(2025, 1, 10, 16, 0, 0)
        
        should_flatten, positions_to_flatten, reason = weekly_patterns.should_flatten_positions(
            self.personality_id, current_positions, friday_afternoon)
        
        assert should_flatten == False
        assert positions_to_flatten == []
        assert "disabled" in reason


class TestWeeklyPatternsConfig:
    """Test suite for WeeklyPatternsConfig"""
    
    def test_default_config_values(self):
        """Test default configuration values are reasonable"""
        config = WeeklyPatternsConfig()
        
        assert isinstance(config.end_of_week_flattening, bool)
        assert 0 < config.friday_reduction <= 1
        assert 0 < config.monday_morning_caution <= 1
        assert 0 < config.weekend_gap_aversion <= 1
        assert 0 <= config.friday_afternoon_start <= 23
        assert config.monday_caution_hours > 0
        assert 0 < config.flattening_probability <= 1
        assert 0 < config.position_size_reduction_friday <= 1
        
    def test_custom_config_values(self):
        """Test custom configuration values"""
        config = WeeklyPatternsConfig(
            end_of_week_flattening=False,
            friday_reduction=0.5,
            monday_morning_caution=0.3,
            weekend_gap_aversion=0.6,
            friday_afternoon_start=13,
            monday_caution_hours=3,
            flattening_probability=0.8,
            position_size_reduction_friday=0.4
        )
        
        assert config.end_of_week_flattening == False
        assert config.friday_reduction == 0.5
        assert config.monday_morning_caution == 0.3
        assert config.weekend_gap_aversion == 0.6
        assert config.friday_afternoon_start == 13
        assert config.monday_caution_hours == 3
        assert config.flattening_probability == 0.8
        assert config.position_size_reduction_friday == 0.4


class TestDayOfWeekEnum:
    """Test suite for DayOfWeek enum"""
    
    def test_day_values(self):
        """Test day of week enum values match Python datetime weekday"""
        assert DayOfWeek.MONDAY.value == 0
        assert DayOfWeek.TUESDAY.value == 1
        assert DayOfWeek.WEDNESDAY.value == 2
        assert DayOfWeek.THURSDAY.value == 3
        assert DayOfWeek.FRIDAY.value == 4
        assert DayOfWeek.SATURDAY.value == 5
        assert DayOfWeek.SUNDAY.value == 6
        
    def test_weekday_compatibility(self):
        """Test compatibility with datetime.weekday()"""
        test_dates = [
            (datetime(2025, 1, 6), DayOfWeek.MONDAY),   # Monday
            (datetime(2025, 1, 7), DayOfWeek.TUESDAY),  # Tuesday
            (datetime(2025, 1, 8), DayOfWeek.WEDNESDAY), # Wednesday
            (datetime(2025, 1, 9), DayOfWeek.THURSDAY), # Thursday
            (datetime(2025, 1, 10), DayOfWeek.FRIDAY),  # Friday
            (datetime(2025, 1, 11), DayOfWeek.SATURDAY), # Saturday
            (datetime(2025, 1, 12), DayOfWeek.SUNDAY)   # Sunday
        ]
        
        for date, expected_day in test_dates:
            assert date.weekday() == expected_day.value


class TestFridayBehaviorEnum:
    """Test suite for FridayBehavior enum"""
    
    def test_friday_behavior_values(self):
        """Test Friday behavior enum values"""
        assert FridayBehavior.NORMAL.value == "normal"
        assert FridayBehavior.REDUCING.value == "reducing"
        assert FridayBehavior.FLATTENING.value == "flattening"
        
    def test_friday_behavior_from_string(self):
        """Test creating Friday behavior from string values"""
        assert FridayBehavior("normal") == FridayBehavior.NORMAL
        assert FridayBehavior("reducing") == FridayBehavior.REDUCING
        assert FridayBehavior("flattening") == FridayBehavior.FLATTENING