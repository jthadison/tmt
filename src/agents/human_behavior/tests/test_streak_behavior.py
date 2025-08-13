"""
Tests for StreakBehavior module
"""

import pytest
import math
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from agents.human_behavior.StreakBehavior import StreakBehavior, StreakBehaviorConfig, StreakState, StreakType


class TestStreakBehavior:
    """Test suite for StreakBehavior class"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.config = StreakBehaviorConfig(
            win_streak_sensitivity=0.3,
            max_size_multiplier=1.5,
            streak_memory=10,
            confidence_growth_rate=0.15,
            overconfidence_threshold=7,
            min_size_multiplier=0.5
        )
        self.streak_behavior = StreakBehavior(self.config)
        self.personality_id = "test_personality_1"
        
    def test_initial_state(self):
        """Test initial streak state"""
        streak_info = self.streak_behavior.get_streak_info(self.personality_id)
        
        assert streak_info['current_win_streak'] == 0
        assert streak_info['current_loss_streak'] == 0
        assert streak_info['confidence_level'] == 0.5
        assert streak_info['size_modifier'] == 1.0
        assert streak_info['streak_type'] == StreakType.NONE.value
        
    def test_winning_streak_update(self):
        """Test updating with winning trades"""
        # First winning trade
        trade_result = {'pnl': 100, 'timestamp': datetime.now(), 'trade_id': '1'}
        state = self.streak_behavior.update_streak(self.personality_id, trade_result)
        
        assert state.current_win_streak == 1
        assert state.current_loss_streak == 0
        assert state.streak_start_date is not None
        
        # Second winning trade
        trade_result = {'pnl': 150, 'timestamp': datetime.now(), 'trade_id': '2'}
        state = self.streak_behavior.update_streak(self.personality_id, trade_result)
        
        assert state.current_win_streak == 2
        assert state.current_loss_streak == 0
        
    def test_losing_streak_update(self):
        """Test updating with losing trades"""
        # First losing trade
        trade_result = {'pnl': -100, 'timestamp': datetime.now(), 'trade_id': '1'}
        state = self.streak_behavior.update_streak(self.personality_id, trade_result)
        
        assert state.current_win_streak == 0
        assert state.current_loss_streak == 1
        assert state.streak_start_date is not None
        
        # Second losing trade
        trade_result = {'pnl': -80, 'timestamp': datetime.now(), 'trade_id': '2'}
        state = self.streak_behavior.update_streak(self.personality_id, trade_result)
        
        assert state.current_win_streak == 0
        assert state.current_loss_streak == 2
        
    def test_streak_reset_on_opposite_result(self):
        """Test streak resets when result changes from win to loss or vice versa"""
        # Build up winning streak
        for i in range(3):
            trade_result = {'pnl': 100, 'timestamp': datetime.now(), 'trade_id': str(i)}
            self.streak_behavior.update_streak(self.personality_id, trade_result)
            
        state = self.streak_behavior.streak_states[self.personality_id]
        assert state.current_win_streak == 3
        
        # Losing trade should reset winning streak
        trade_result = {'pnl': -100, 'timestamp': datetime.now(), 'trade_id': '4'}
        state = self.streak_behavior.update_streak(self.personality_id, trade_result)
        
        assert state.current_win_streak == 0
        assert state.current_loss_streak == 1
        
    def test_win_streak_size_modifier(self):
        """Test position size modification for winning streaks"""
        # Build up winning streak
        for i in range(5):
            trade_result = {'pnl': 100, 'timestamp': datetime.now(), 'trade_id': str(i)}
            self.streak_behavior.update_streak(self.personality_id, trade_result)
            
        modifier = self.streak_behavior.calculate_size_modifier(self.personality_id)
        
        # Should be greater than 1.0 for winning streak
        assert modifier > 1.0
        # Should not exceed max multiplier
        assert modifier <= self.config.max_size_multiplier
        
    def test_loss_streak_size_modifier(self):
        """Test position size modification for losing streaks"""
        # Build up losing streak
        for i in range(5):
            trade_result = {'pnl': -100, 'timestamp': datetime.now(), 'trade_id': str(i)}
            self.streak_behavior.update_streak(self.personality_id, trade_result)
            
        modifier = self.streak_behavior.calculate_size_modifier(self.personality_id)
        
        # Should be less than 1.0 for losing streak
        assert modifier < 1.0
        # Should not go below minimum multiplier
        assert modifier >= self.config.min_size_multiplier
        
    def test_overconfidence_protection(self):
        """Test overconfidence protection for very long winning streaks"""
        # Build up very long winning streak
        for i in range(10):  # Above overconfidence threshold
            trade_result = {'pnl': 100, 'timestamp': datetime.now(), 'trade_id': str(i)}
            self.streak_behavior.update_streak(self.personality_id, trade_result)
            
        modifier = self.streak_behavior.calculate_size_modifier(self.personality_id)
        
        # Should be reduced due to overconfidence protection
        # Calculate what it would be without overconfidence protection
        win_streak = 10
        base_multiplier = 1.0 + (math.log(1 + win_streak) * self.config.win_streak_sensitivity * 0.1)
        base_multiplier = min(base_multiplier, self.config.max_size_multiplier)
        
        # With overconfidence protection, it should be less
        assert modifier < base_multiplier
        
    def test_confidence_level_calculation(self):
        """Test confidence level calculation based on performance"""
        # Mixed results: 3 wins, 2 losses
        results = [
            {'pnl': 100, 'timestamp': datetime.now(), 'trade_id': '1'},
            {'pnl': -50, 'timestamp': datetime.now(), 'trade_id': '2'},
            {'pnl': 75, 'timestamp': datetime.now(), 'trade_id': '3'},
            {'pnl': -80, 'timestamp': datetime.now(), 'trade_id': '4'},
            {'pnl': 120, 'timestamp': datetime.now(), 'trade_id': '5'}
        ]
        
        for result in results:
            self.streak_behavior.update_streak(self.personality_id, result)
            
        streak_info = self.streak_behavior.get_streak_info(self.personality_id)
        confidence = streak_info['confidence_level']
        
        # Should reflect 60% win rate (3/5 wins)
        assert 0.4 < confidence < 0.8  # Should be above neutral due to win rate and current win
        
    def test_recent_trades_memory_limit(self):
        """Test that recent trades are limited by memory setting"""
        # Add more trades than memory limit
        for i in range(15):  # More than streak_memory (10)
            trade_result = {'pnl': 100, 'timestamp': datetime.now(), 'trade_id': str(i)}
            self.streak_behavior.update_streak(self.personality_id, trade_result)
            
        state = self.streak_behavior.streak_states[self.personality_id]
        
        # Should only keep the most recent trades
        assert len(state.recent_trades) == self.config.streak_memory
        
        # Should have the most recent trade IDs
        trade_ids = [trade['trade_id'] for trade in state.recent_trades]
        expected_ids = [str(i) for i in range(5, 15)]  # Last 10 trades
        assert trade_ids == expected_ids
        
    def test_behavioral_impact_high_confidence(self):
        """Test behavioral impact calculations for high confidence scenarios"""
        # Build up winning streak for high confidence
        for i in range(6):
            trade_result = {'pnl': 100, 'timestamp': datetime.now(), 'trade_id': str(i)}
            self.streak_behavior.update_streak(self.personality_id, trade_result)
            
        impact = self.streak_behavior.get_behavioral_impact(self.personality_id)
        
        # High confidence should increase risk tolerance and aggressiveness
        assert impact['position_size_multiplier'] > 1.0
        assert impact['risk_tolerance_adjustment'] > 0
        assert impact['entry_aggressiveness'] > 0
        assert impact['exit_patience'] > 0
        
    def test_behavioral_impact_low_confidence(self):
        """Test behavioral impact calculations for low confidence scenarios"""
        # Build up losing streak for low confidence
        for i in range(6):
            trade_result = {'pnl': -100, 'timestamp': datetime.now(), 'trade_id': str(i)}
            self.streak_behavior.update_streak(self.personality_id, trade_result)
            
        impact = self.streak_behavior.get_behavioral_impact(self.personality_id)
        
        # Low confidence should decrease risk tolerance and aggressiveness
        assert impact['position_size_multiplier'] < 1.0
        assert impact['risk_tolerance_adjustment'] < 0
        assert impact['entry_aggressiveness'] < 0
        assert impact['exit_patience'] < 0
        
    def test_reset_streak(self):
        """Test streak state reset functionality"""
        # Build up some state
        trade_result = {'pnl': 100, 'timestamp': datetime.now(), 'trade_id': '1'}
        self.streak_behavior.update_streak(self.personality_id, trade_result)
        
        assert self.personality_id in self.streak_behavior.streak_states
        
        # Reset streak
        self.streak_behavior.reset_streak(self.personality_id)
        
        assert self.personality_id not in self.streak_behavior.streak_states
        
        # Should return default values after reset
        streak_info = self.streak_behavior.get_streak_info(self.personality_id)
        assert streak_info['current_win_streak'] == 0
        assert streak_info['current_loss_streak'] == 0
        assert streak_info['confidence_level'] == 0.5
        
    def test_multiple_personalities(self):
        """Test handling multiple personalities independently"""
        personality_2 = "test_personality_2"
        
        # Give personality 1 a winning streak
        trade_result_1 = {'pnl': 100, 'timestamp': datetime.now(), 'trade_id': '1'}
        self.streak_behavior.update_streak(self.personality_id, trade_result_1)
        
        # Give personality 2 a losing streak
        trade_result_2 = {'pnl': -100, 'timestamp': datetime.now(), 'trade_id': '1'}
        self.streak_behavior.update_streak(personality_2, trade_result_2)
        
        # Check they maintain separate states
        info_1 = self.streak_behavior.get_streak_info(self.personality_id)
        info_2 = self.streak_behavior.get_streak_info(personality_2)
        
        assert info_1['current_win_streak'] == 1
        assert info_1['current_loss_streak'] == 0
        assert info_2['current_win_streak'] == 0
        assert info_2['current_loss_streak'] == 1
        
    def test_zero_pnl_trade(self):
        """Test handling of breakeven trades (zero P&L)"""
        trade_result = {'pnl': 0, 'timestamp': datetime.now(), 'trade_id': '1'}
        state = self.streak_behavior.update_streak(self.personality_id, trade_result)
        
        # Zero P&L should not affect streaks
        assert state.current_win_streak == 0
        assert state.current_loss_streak == 0
        
        # But should be recorded in recent trades
        assert len(state.recent_trades) == 1
        assert state.recent_trades[0]['pnl'] == 0


class TestStreakBehaviorConfig:
    """Test suite for StreakBehaviorConfig"""
    
    def test_default_config_values(self):
        """Test default configuration values are reasonable"""
        config = StreakBehaviorConfig()
        
        assert 0 < config.win_streak_sensitivity <= 1
        assert config.max_size_multiplier > 1.0
        assert config.streak_memory > 0
        assert 0 < config.confidence_growth_rate <= 1
        assert config.overconfidence_threshold > 0
        assert 0 < config.min_size_multiplier < 1
        
    def test_custom_config_values(self):
        """Test custom configuration values"""
        config = StreakBehaviorConfig(
            win_streak_sensitivity=0.5,
            max_size_multiplier=2.0,
            streak_memory=20,
            confidence_growth_rate=0.2,
            overconfidence_threshold=5,
            min_size_multiplier=0.3
        )
        
        assert config.win_streak_sensitivity == 0.5
        assert config.max_size_multiplier == 2.0
        assert config.streak_memory == 20
        assert config.confidence_growth_rate == 0.2
        assert config.overconfidence_threshold == 5
        assert config.min_size_multiplier == 0.3


class TestStreakState:
    """Test suite for StreakState dataclass"""
    
    def test_initial_state_values(self):
        """Test initial state values"""
        state = StreakState()
        
        assert state.current_win_streak == 0
        assert state.current_loss_streak == 0
        assert state.streak_start_date is None
        assert state.confidence_level == 0.5
        assert state.recent_trades == []
        assert state.last_streak_update is None
        
    def test_state_with_custom_values(self):
        """Test state with custom initial values"""
        start_date = datetime.now()
        trades = [{'pnl': 100, 'trade_id': '1'}]
        
        state = StreakState(
            current_win_streak=3,
            current_loss_streak=0,
            streak_start_date=start_date,
            confidence_level=0.7,
            recent_trades=trades
        )
        
        assert state.current_win_streak == 3
        assert state.current_loss_streak == 0
        assert state.streak_start_date == start_date
        assert state.confidence_level == 0.7
        assert state.recent_trades == trades