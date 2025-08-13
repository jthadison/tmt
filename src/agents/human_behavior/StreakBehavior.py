"""
Streak Behavior Module - Implements winning/losing streak patterns for human-like trading behavior.

This module handles the psychological aspects of consecutive wins/losses and their impact
on position sizing and confidence levels, mimicking real trader behavior patterns.
"""

import logging
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class StreakType(Enum):
    """Types of trading streaks"""
    WIN = "win"
    LOSS = "loss"
    NONE = "none"


@dataclass
class StreakBehaviorConfig:
    """Configuration for streak-based behavior patterns"""
    win_streak_sensitivity: float = 0.3  # 0-1, how much wins affect size
    max_size_multiplier: float = 1.5     # Max position size increase
    streak_memory: int = 10               # How many trades to consider
    confidence_growth_rate: float = 0.15  # How fast confidence builds
    overconfidence_threshold: int = 7     # When to start reducing size
    min_size_multiplier: float = 0.5     # Minimum position size after losses


@dataclass
class StreakState:
    """Current streak state for a trading personality"""
    current_win_streak: int = 0
    current_loss_streak: int = 0
    streak_start_date: Optional[datetime] = None
    confidence_level: float = 0.5  # 0-1
    recent_trades: List[Dict] = None  # Recent trade results
    last_streak_update: Optional[datetime] = None
    
    def __post_init__(self):
        if self.recent_trades is None:
            self.recent_trades = []


class StreakBehavior:
    """
    Manages streak-based behavioral modifications for human-like trading patterns.
    
    Implements psychological responses to consecutive wins/losses including:
    - Gradual position size increases after winning streaks
    - Confidence-based adjustments
    - Overconfidence protection for very long streaks
    - Loss-based position size reductions
    """
    
    def __init__(self, config: StreakBehaviorConfig = None):
        self.config = config or StreakBehaviorConfig()
        self.streak_states: Dict[str, StreakState] = {}
        
    def update_streak(self, personality_id: str, trade_result: Dict) -> StreakState:
        """
        Update streak state based on trade result.
        
        Args:
            personality_id: Trading personality identifier
            trade_result: Dict with 'pnl', 'timestamp', 'trade_id' keys
            
        Returns:
            Updated streak state
        """
        if personality_id not in self.streak_states:
            self.streak_states[personality_id] = StreakState()
            
        state = self.streak_states[personality_id]
        pnl = trade_result.get('pnl', 0)
        timestamp = trade_result.get('timestamp', datetime.now())
        
        # Add trade to recent trades history
        state.recent_trades.append(trade_result)
        
        # Keep only recent trades within memory limit
        if len(state.recent_trades) > self.config.streak_memory:
            state.recent_trades = state.recent_trades[-self.config.streak_memory:]
            
        # Update streak based on trade result
        if pnl > 0:  # Winning trade
            state.current_loss_streak = 0
            state.current_win_streak += 1
            
            # Start new streak if this is the first win
            if state.current_win_streak == 1:
                state.streak_start_date = timestamp
                
        elif pnl < 0:  # Losing trade
            state.current_win_streak = 0
            state.current_loss_streak += 1
            
            # Start new loss streak
            if state.current_loss_streak == 1:
                state.streak_start_date = timestamp
                
        # Update confidence level
        state.confidence_level = self._calculate_confidence_level(state)
        state.last_streak_update = timestamp
        
        logger.info(f"Updated streak for {personality_id}: "
                   f"Win: {state.current_win_streak}, Loss: {state.current_loss_streak}, "
                   f"Confidence: {state.confidence_level:.3f}")
        
        return state
    
    def calculate_size_modifier(self, personality_id: str) -> float:
        """
        Calculate position size modifier based on current streak.
        
        Args:
            personality_id: Trading personality identifier
            
        Returns:
            Size multiplier (1.0 = no change, >1.0 = increase, <1.0 = decrease)
        """
        if personality_id not in self.streak_states:
            return 1.0
            
        state = self.streak_states[personality_id]
        
        # Handle winning streaks
        if state.current_win_streak > 0:
            return self._calculate_win_streak_modifier(state.current_win_streak)
            
        # Handle losing streaks
        elif state.current_loss_streak > 0:
            return self._calculate_loss_streak_modifier(state.current_loss_streak)
            
        # No active streak
        return 1.0
    
    def _calculate_win_streak_modifier(self, win_streak: int) -> float:
        """Calculate size modifier for winning streaks"""
        if win_streak <= 0:
            return 1.0
            
        # Logarithmic growth to prevent extreme position sizes
        base_multiplier = 1.0 + (math.log(1 + win_streak) * self.config.win_streak_sensitivity * 0.1)
        
        # Cap at maximum multiplier
        size_multiplier = min(base_multiplier, self.config.max_size_multiplier)
        
        # Apply overconfidence reduction for very long streaks
        if win_streak > self.config.overconfidence_threshold:
            overconfidence_penalty = 0.1 * (win_streak - self.config.overconfidence_threshold)
            reduction_factor = 1 - min(overconfidence_penalty, 0.5)  # Max 50% reduction
            size_multiplier *= reduction_factor
            
        return size_multiplier
    
    def _calculate_loss_streak_modifier(self, loss_streak: int) -> float:
        """Calculate size modifier for losing streaks"""
        if loss_streak <= 0:
            return 1.0
            
        # Exponential decay for loss streaks (more conservative)
        reduction_factor = math.exp(-0.2 * loss_streak)
        size_multiplier = max(reduction_factor, self.config.min_size_multiplier)
        
        return size_multiplier
    
    def _calculate_confidence_level(self, state: StreakState) -> float:
        """Calculate confidence level based on recent performance"""
        if not state.recent_trades:
            return 0.5  # Neutral confidence
            
        # Calculate win rate from recent trades
        wins = sum(1 for trade in state.recent_trades if trade.get('pnl', 0) > 0)
        total_trades = len(state.recent_trades)
        win_rate = wins / total_trades if total_trades > 0 else 0.5
        
        # Base confidence on win rate
        base_confidence = win_rate
        
        # Adjust for current streak
        if state.current_win_streak > 0:
            streak_boost = min(state.current_win_streak * self.config.confidence_growth_rate * 0.1, 0.3)
            base_confidence += streak_boost
        elif state.current_loss_streak > 0:
            streak_penalty = min(state.current_loss_streak * 0.1, 0.3)
            base_confidence -= streak_penalty
            
        # Clamp between 0 and 1
        return max(0.0, min(1.0, base_confidence))
    
    def get_streak_info(self, personality_id: str) -> Dict:
        """Get current streak information for a personality"""
        if personality_id not in self.streak_states:
            return {
                'current_win_streak': 0,
                'current_loss_streak': 0,
                'confidence_level': 0.5,
                'size_modifier': 1.0,
                'streak_type': StreakType.NONE.value
            }
            
        state = self.streak_states[personality_id]
        
        # Determine streak type
        if state.current_win_streak > 0:
            streak_type = StreakType.WIN.value
        elif state.current_loss_streak > 0:
            streak_type = StreakType.LOSS.value
        else:
            streak_type = StreakType.NONE.value
            
        return {
            'current_win_streak': state.current_win_streak,
            'current_loss_streak': state.current_loss_streak,
            'confidence_level': state.confidence_level,
            'size_modifier': self.calculate_size_modifier(personality_id),
            'streak_type': streak_type,
            'streak_start_date': state.streak_start_date,
            'recent_trades_count': len(state.recent_trades)
        }
    
    def reset_streak(self, personality_id: str) -> None:
        """Reset streak state for a personality"""
        if personality_id in self.streak_states:
            del self.streak_states[personality_id]
            logger.info(f"Reset streak state for personality {personality_id}")
    
    def get_behavioral_impact(self, personality_id: str) -> Dict:
        """
        Get the behavioral impact of current streak for decision making.
        
        Returns:
            Dict with behavioral modifications to apply
        """
        streak_info = self.get_streak_info(personality_id)
        
        impact = {
            'position_size_multiplier': streak_info['size_modifier'],
            'confidence_level': streak_info['confidence_level'],
            'risk_tolerance_adjustment': 0.0,
            'entry_aggressiveness': 0.0,
            'exit_patience': 0.0
        }
        
        # Adjust risk tolerance based on confidence
        confidence = streak_info['confidence_level']
        if confidence > 0.7:
            impact['risk_tolerance_adjustment'] = 0.2  # More risk tolerant
            impact['entry_aggressiveness'] = 0.3      # More aggressive entries
            impact['exit_patience'] = 0.2             # Hold positions longer
        elif confidence < 0.3:
            impact['risk_tolerance_adjustment'] = -0.2  # More risk averse
            impact['entry_aggressiveness'] = -0.3     # Less aggressive entries
            impact['exit_patience'] = -0.2            # Exit positions sooner
            
        return impact