"""
Tests for LossAversion module
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from agents.human_behavior.LossAversion import (
    LossAversion, LossAversionConfig, LossAversionState, EmotionalState
)


class TestLossAversion:
    """Test suite for LossAversion class"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.config = LossAversionConfig(
            loss_aversion=0.7,
            recovery_time_hours=24.0,
            max_activity_reduction=0.6,
            max_risk_reduction=0.5,
            emotional_volatility=0.3,
            daily_loss_threshold=500.0,
            emotional_memory_days=3
        )
        self.loss_aversion = LossAversion(self.config)
        self.personality_id = "test_personality_1"
        
    def test_initial_state(self):
        """Test initial loss aversion state"""
        info = self.loss_aversion.get_loss_aversion_info(self.personality_id)
        
        assert info['recent_losses'] == 0.0
        assert info['daily_pnl'] == 0.0
        assert info['emotional_state'] == EmotionalState.NEUTRAL.value
        assert info['recovery_progress'] == 1.0
        assert info['activity_modifier'] == 1.0
        assert info['risk_modifier'] == 1.0
        assert info['consecutive_losing_days'] == 0
        
    def test_single_loss_update(self):
        """Test updating with a single losing trade"""
        trade_result = {'pnl': -200, 'timestamp': datetime.now(), 'trade_id': '1'}
        state = self.loss_aversion.update_loss_state(self.personality_id, trade_result)
        
        assert state.daily_pnl == -200
        assert state.recent_losses == 200
        assert state.daily_loss_count == 1
        assert state.last_loss_date is not None
        
    def test_multiple_losses_same_day(self):
        """Test multiple losing trades in the same day"""
        base_time = datetime.now()
        
        # First loss
        trade_result_1 = {'pnl': -200, 'timestamp': base_time, 'trade_id': '1'}
        self.loss_aversion.update_loss_state(self.personality_id, trade_result_1)
        
        # Second loss same day (within 1 hour to avoid decay)
        trade_result_2 = {'pnl': -150, 'timestamp': base_time + timedelta(minutes=30), 'trade_id': '2'}
        state = self.loss_aversion.update_loss_state(self.personality_id, trade_result_2)
        
        assert state.daily_pnl == -350
        assert state.recent_losses == 350
        assert state.daily_loss_count == 2
        
    def test_winning_trade_impact(self):
        """Test that winning trades don't increase recent losses"""
        trade_result = {'pnl': 300, 'timestamp': datetime.now(), 'trade_id': '1'}
        state = self.loss_aversion.update_loss_state(self.personality_id, trade_result)
        
        assert state.daily_pnl == 300
        assert state.recent_losses == 0.0
        assert state.daily_loss_count == 0
        
    def test_emotional_state_transitions(self):
        """Test emotional state transitions based on losses"""
        base_time = datetime.now()
        
        # Start with neutral state
        info = self.loss_aversion.get_loss_aversion_info(self.personality_id)
        assert info['emotional_state'] == EmotionalState.NEUTRAL.value
        
        # Large loss should trigger fearful state
        large_loss = {'pnl': -800, 'timestamp': base_time, 'trade_id': '1'}
        self.loss_aversion.update_loss_state(self.personality_id, large_loss)
        
        info = self.loss_aversion.get_loss_aversion_info(self.personality_id)
        emotional_state = EmotionalState(info['emotional_state'])
        
        # Should be cautious or fearful after large loss
        assert emotional_state in [EmotionalState.CAUTIOUS, EmotionalState.FEARFUL]
        
    def test_activity_modifier_reduction(self):
        """Test activity reduction after losses"""
        # Initial activity should be normal
        activity_before = self.loss_aversion.calculate_activity_modifier(self.personality_id)
        assert activity_before == 1.0
        
        # Add significant losses
        base_time = datetime.now()
        for i in range(3):
            loss = {'pnl': -300, 'timestamp': base_time + timedelta(hours=i), 'trade_id': str(i)}
            self.loss_aversion.update_loss_state(self.personality_id, loss)
            
        # Activity should be reduced
        activity_after = self.loss_aversion.calculate_activity_modifier(self.personality_id)
        assert activity_after < 1.0
        assert activity_after >= 0.2  # Minimum threshold
        
    def test_risk_modifier_reduction(self):
        """Test risk reduction after losses"""
        # Initial risk should be normal
        risk_before = self.loss_aversion.calculate_risk_modifier(self.personality_id)
        assert risk_before == 1.0
        
        # Add significant losses
        base_time = datetime.now()
        for i in range(3):
            loss = {'pnl': -400, 'timestamp': base_time + timedelta(hours=i), 'trade_id': str(i)}
            self.loss_aversion.update_loss_state(self.personality_id, loss)
            
        # Risk should be reduced
        risk_after = self.loss_aversion.calculate_risk_modifier(self.personality_id)
        assert risk_after < 1.0
        assert risk_after >= 0.3  # Minimum threshold
        
    def test_recovery_over_time(self):
        """Test recovery progress over time"""
        base_time = datetime.now()
        
        # Add a loss
        loss = {'pnl': -500, 'timestamp': base_time, 'trade_id': '1'}
        self.loss_aversion.update_loss_state(self.personality_id, loss)
        
        # Recovery should be low immediately after loss
        info = self.loss_aversion.get_loss_aversion_info(self.personality_id)
        assert info['recovery_progress'] < 0.1
        
        # Simulate time passing (12 hours)
        future_time = base_time + timedelta(hours=12)
        trade_result = {'pnl': 0, 'timestamp': future_time, 'trade_id': '2'}  # Neutral trade
        self.loss_aversion.update_loss_state(self.personality_id, trade_result)
        
        # Recovery should be approximately 50%
        info = self.loss_aversion.get_loss_aversion_info(self.personality_id)
        assert 0.4 < info['recovery_progress'] < 0.6
        
        # Simulate full recovery time (24+ hours)
        future_time = base_time + timedelta(hours=25)
        trade_result = {'pnl': 0, 'timestamp': future_time, 'trade_id': '3'}
        self.loss_aversion.update_loss_state(self.personality_id, trade_result)
        
        # Should be fully recovered
        info = self.loss_aversion.get_loss_aversion_info(self.personality_id)
        assert info['recovery_progress'] >= 1.0
        
    @patch('random.random')
    def test_should_skip_trade_logic(self, mock_random):
        """Test trade skipping logic based on loss aversion"""
        # Setup losing scenario
        base_time = datetime.now()
        for i in range(4):
            loss = {'pnl': -200, 'timestamp': base_time + timedelta(hours=i), 'trade_id': str(i)}
            self.loss_aversion.update_loss_state(self.personality_id, loss)
            
        # Mock random to force skip scenario
        mock_random.return_value = 0.9  # High random value
        
        should_skip, reason = self.loss_aversion.should_skip_trade(self.personality_id)
        assert should_skip
        assert reason != ""
        
        # Mock random to force trade scenario
        mock_random.return_value = 0.1  # Low random value
        
        should_skip, reason = self.loss_aversion.should_skip_trade(self.personality_id)
        assert not should_skip
        
    def test_consecutive_losing_days(self):
        """Test consecutive losing days tracking"""
        base_date = datetime(2025, 1, 1, 10, 0, 0)
        
        # Day 1: Losing day
        loss_day_1 = {'pnl': -600, 'timestamp': base_date, 'trade_id': '1'}
        self.loss_aversion.update_loss_state(self.personality_id, loss_day_1)
        
        # Day 2: Another losing day (simulate new day)
        day_2 = base_date + timedelta(days=1)
        self.loss_aversion.reset_daily_state(self.personality_id)  # Simulate day rollover
        loss_day_2 = {'pnl': -700, 'timestamp': day_2, 'trade_id': '2'}
        self.loss_aversion.update_loss_state(self.personality_id, loss_day_2)
        
        info = self.loss_aversion.get_loss_aversion_info(self.personality_id)
        # Should have at least 1 consecutive losing day from the reset
        assert info['consecutive_losing_days'] >= 1
        
    def test_daily_state_reset(self):
        """Test daily state reset functionality"""
        # Add some daily activity
        base_time = datetime.now()
        trade_result = {'pnl': -300, 'timestamp': base_time, 'trade_id': '1'}
        self.loss_aversion.update_loss_state(self.personality_id, trade_result)
        
        state = self.loss_aversion.loss_states[self.personality_id]
        assert state.daily_pnl == -300
        assert state.daily_loss_count == 1
        
        # Reset daily state
        self.loss_aversion.reset_daily_state(self.personality_id)
        
        # Daily counters should be reset
        assert state.daily_pnl == 0
        assert state.daily_loss_count == 0
        # But recent_losses should persist
        assert state.recent_losses > 0
        
    def test_loss_decay_over_time(self):
        """Test that recent losses decay over time"""
        base_time = datetime.now()
        
        # Add initial loss
        loss = {'pnl': -500, 'timestamp': base_time, 'trade_id': '1'}
        self.loss_aversion.update_loss_state(self.personality_id, loss)
        
        initial_losses = self.loss_aversion.loss_states[self.personality_id].recent_losses
        assert initial_losses == 500.0
        
        # Simulate significant time passing
        future_time = base_time + timedelta(hours=48)  # 48 hours later
        neutral_trade = {'pnl': 0, 'timestamp': future_time, 'trade_id': '2'}
        self.loss_aversion.update_loss_state(self.personality_id, neutral_trade)
        
        # Recent losses should have decayed
        decayed_losses = self.loss_aversion.loss_states[self.personality_id].recent_losses
        assert decayed_losses < initial_losses
        
    def test_behavioral_impact_fearful_state(self):
        """Test behavioral impact in fearful emotional state"""
        # Create scenario leading to fearful state
        base_time = datetime.now()
        for i in range(3):
            large_loss = {'pnl': -600, 'timestamp': base_time + timedelta(hours=i), 'trade_id': str(i)}
            self.loss_aversion.update_loss_state(self.personality_id, large_loss)
            
        impact = self.loss_aversion.get_behavioral_impact(self.personality_id)
        
        # Should have significant behavioral modifications
        assert impact['activity_multiplier'] < 1.0
        assert impact['position_size_multiplier'] < 1.0
        assert impact['exit_bias'] > 0  # More likely to exit early
        assert impact['entry_hesitation'] > 0  # More hesitation on entries
        assert impact['stop_loss_tightening'] > 0  # Tighter stops
        
    def test_behavioral_impact_confident_state(self):
        """Test behavioral impact in confident emotional state"""
        # Create winning scenario
        base_time = datetime.now()
        for i in range(3):
            win = {'pnl': 400, 'timestamp': base_time + timedelta(hours=i), 'trade_id': str(i)}
            self.loss_aversion.update_loss_state(self.personality_id, win)
            
        impact = self.loss_aversion.get_behavioral_impact(self.personality_id)
        
        # Should have normal or positive modifications
        assert impact['activity_multiplier'] == 1.0  # Normal activity
        assert impact['position_size_multiplier'] >= 0.8  # Normal or slightly reduced risk
        assert impact['exit_bias'] <= 0  # Less likely to exit early
        assert impact['entry_hesitation'] <= 0  # Less hesitation
        
    def test_reset_loss_state(self):
        """Test complete loss state reset functionality"""
        # Build up some state
        trade_result = {'pnl': -300, 'timestamp': datetime.now(), 'trade_id': '1'}
        self.loss_aversion.update_loss_state(self.personality_id, trade_result)
        
        assert self.personality_id in self.loss_aversion.loss_states
        
        # Reset complete state
        self.loss_aversion.reset_loss_state(self.personality_id)
        
        assert self.personality_id not in self.loss_aversion.loss_states
        
        # Should return default values after reset
        info = self.loss_aversion.get_loss_aversion_info(self.personality_id)
        assert info['recent_losses'] == 0.0
        assert info['emotional_state'] == EmotionalState.NEUTRAL.value
        
    def test_multiple_personalities(self):
        """Test handling multiple personalities independently"""
        personality_2 = "test_personality_2"
        
        # Give personality 1 losses
        loss_1 = {'pnl': -400, 'timestamp': datetime.now(), 'trade_id': '1'}
        self.loss_aversion.update_loss_state(self.personality_id, loss_1)
        
        # Give personality 2 wins
        win_2 = {'pnl': 500, 'timestamp': datetime.now(), 'trade_id': '1'}
        self.loss_aversion.update_loss_state(personality_2, win_2)
        
        # Check they maintain separate states
        info_1 = self.loss_aversion.get_loss_aversion_info(self.personality_id)
        info_2 = self.loss_aversion.get_loss_aversion_info(personality_2)
        
        assert info_1['daily_pnl'] < 0
        assert info_1['recent_losses'] > 0
        assert info_2['daily_pnl'] > 0
        assert info_2['recent_losses'] == 0


class TestLossAversionConfig:
    """Test suite for LossAversionConfig"""
    
    def test_default_config_values(self):
        """Test default configuration values are reasonable"""
        config = LossAversionConfig()
        
        assert 0 < config.loss_aversion <= 1
        assert config.recovery_time_hours > 0
        assert 0 < config.max_activity_reduction <= 1
        assert 0 < config.max_risk_reduction <= 1
        assert 0 < config.emotional_volatility <= 1
        assert config.daily_loss_threshold > 0
        assert config.emotional_memory_days > 0
        
    def test_custom_config_values(self):
        """Test custom configuration values"""
        config = LossAversionConfig(
            loss_aversion=0.8,
            recovery_time_hours=48.0,
            max_activity_reduction=0.8,
            max_risk_reduction=0.6,
            emotional_volatility=0.5,
            daily_loss_threshold=1000.0,
            emotional_memory_days=5
        )
        
        assert config.loss_aversion == 0.8
        assert config.recovery_time_hours == 48.0
        assert config.max_activity_reduction == 0.8
        assert config.max_risk_reduction == 0.6
        assert config.emotional_volatility == 0.5
        assert config.daily_loss_threshold == 1000.0
        assert config.emotional_memory_days == 5


class TestEmotionalState:
    """Test suite for EmotionalState enum"""
    
    def test_emotional_state_values(self):
        """Test emotional state enum values"""
        assert EmotionalState.CONFIDENT.value == "confident"
        assert EmotionalState.NEUTRAL.value == "neutral"
        assert EmotionalState.CAUTIOUS.value == "cautious"
        assert EmotionalState.FEARFUL.value == "fearful"
        
    def test_emotional_state_from_string(self):
        """Test creating emotional state from string values"""
        assert EmotionalState("confident") == EmotionalState.CONFIDENT
        assert EmotionalState("neutral") == EmotionalState.NEUTRAL
        assert EmotionalState("cautious") == EmotionalState.CAUTIOUS
        assert EmotionalState("fearful") == EmotionalState.FEARFUL