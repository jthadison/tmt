"""
Loss Aversion Module - Implements loss aversion patterns for human-like trading behavior.

This module handles the psychological impact of losses on trading behavior, including
reduced activity after losing days, risk reduction, and emotional recovery simulation.
"""

import logging
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class EmotionalState(Enum):
    """Emotional states based on recent performance"""
    CONFIDENT = "confident"
    NEUTRAL = "neutral"
    CAUTIOUS = "cautious"
    FEARFUL = "fearful"


@dataclass
class LossAversionConfig:
    """Configuration for loss aversion behavior patterns"""
    loss_aversion: float = 0.7               # 0-1, sensitivity to losses
    recovery_time_hours: float = 24.0        # Hours to recover from losses
    max_activity_reduction: float = 0.6      # Max % reduction in trading activity
    max_risk_reduction: float = 0.5          # Max % reduction in position size
    emotional_volatility: float = 0.3        # How much emotions fluctuate
    daily_loss_threshold: float = 500.0      # $ threshold for "losing day"
    emotional_memory_days: int = 3           # Days to consider for emotional state


@dataclass
class LossAversionState:
    """Current loss aversion state for a trading personality"""
    recent_losses: float = 0.0               # Recent losses in $
    last_loss_date: Optional[datetime] = None
    recovery_progress: float = 1.0           # 0-1, how much recovered
    emotional_state: EmotionalState = EmotionalState.NEUTRAL
    daily_pnl: float = 0.0                  # Today's P&L
    daily_loss_count: int = 0               # Number of losing trades today
    consecutive_losing_days: int = 0        # Consecutive losing days
    emotional_volatility_today: float = 0.0 # Today's emotional impact
    last_emotional_update: Optional[datetime] = None


class LossAversion:
    """
    Manages loss aversion behavioral modifications for human-like trading patterns.
    
    Implements psychological responses to losses including:
    - Reduced activity after losing days
    - Risk reduction after losses
    - Emotional recovery simulation over time
    - Daily loss impact tracking
    """
    
    def __init__(self, config: LossAversionConfig = None):
        self.config = config or LossAversionConfig()
        self.loss_states: Dict[str, LossAversionState] = {}
        
    def update_loss_state(self, personality_id: str, trade_result: Dict) -> LossAversionState:
        """
        Update loss aversion state based on trade result.
        
        Args:
            personality_id: Trading personality identifier
            trade_result: Dict with 'pnl', 'timestamp', 'trade_id' keys
            
        Returns:
            Updated loss aversion state
        """
        if personality_id not in self.loss_states:
            self.loss_states[personality_id] = LossAversionState()
            
        state = self.loss_states[personality_id]
        pnl = trade_result.get('pnl', 0)
        timestamp = trade_result.get('timestamp', datetime.now())
        
        # Update daily P&L
        if self._is_new_day(state.last_emotional_update, timestamp):
            # New day - check if yesterday was a losing day
            if state.daily_pnl < -self.config.daily_loss_threshold:
                state.consecutive_losing_days += 1
            elif state.daily_pnl > 0:
                state.consecutive_losing_days = 0
                
            # Reset daily counters
            state.daily_pnl = 0
            state.daily_loss_count = 0
            
        # Update daily P&L and loss tracking
        state.daily_pnl += pnl
        
        if pnl < 0:
            state.daily_loss_count += 1
            state.recent_losses += abs(pnl)
            state.last_loss_date = timestamp
            
            # Calculate emotional volatility impact
            loss_impact = abs(pnl) / 100.0  # Scale by $100
            state.emotional_volatility_today += loss_impact * self.config.emotional_volatility
            
        # Update recovery progress based on time since last loss
        if state.last_loss_date:
            hours_since_loss = (timestamp - state.last_loss_date).total_seconds() / 3600
            state.recovery_progress = min(1.0, hours_since_loss / self.config.recovery_time_hours)
        else:
            state.recovery_progress = 1.0
            
        # Decay recent losses over time (only if significant time has passed)
        if state.last_emotional_update:
            hours_elapsed = (timestamp - state.last_emotional_update).total_seconds() / 3600
            # Only apply decay if more than 1 hour has passed
            if hours_elapsed > 1.0:
                decay_factor = math.exp(-hours_elapsed / (self.config.recovery_time_hours / 2))
                state.recent_losses *= decay_factor
            
        # Update emotional state
        state.emotional_state = self._calculate_emotional_state(state)
        state.last_emotional_update = timestamp
        
        logger.info(f"Updated loss aversion for {personality_id}: "
                   f"Daily P&L: ${state.daily_pnl:.2f}, Recent losses: ${state.recent_losses:.2f}, "
                   f"Emotional state: {state.emotional_state.value}, Recovery: {state.recovery_progress:.3f}")
        
        return state
    
    def calculate_activity_modifier(self, personality_id: str) -> float:
        """
        Calculate activity reduction modifier based on recent losses.
        
        Args:
            personality_id: Trading personality identifier
            
        Returns:
            Activity multiplier (1.0 = normal, <1.0 = reduced activity)
        """
        if personality_id not in self.loss_states:
            return 1.0
            
        state = self.loss_states[personality_id]
        
        # Base activity reduction from recent losses
        loss_impact = min(state.recent_losses / 1000.0, 1.0)  # Normalize to $1000
        base_reduction = self.config.max_activity_reduction * loss_impact * self.config.loss_aversion
        
        # Adjust for consecutive losing days
        consecutive_day_penalty = min(state.consecutive_losing_days * 0.1, 0.3)  # Max 30% additional reduction
        
        # Adjust for recovery progress
        recovery_factor = state.recovery_progress
        
        # Calculate final activity level
        total_reduction = base_reduction + consecutive_day_penalty
        activity_level = (1.0 - total_reduction) + (recovery_factor * total_reduction)
        
        # Apply minimum activity threshold
        return max(0.2, activity_level)  # Minimum 20% activity
    
    def calculate_risk_modifier(self, personality_id: str) -> float:
        """
        Calculate risk/position size modifier based on recent losses.
        
        Args:
            personality_id: Trading personality identifier
            
        Returns:
            Risk multiplier (1.0 = normal, <1.0 = reduced risk)
        """
        if personality_id not in self.loss_states:
            return 1.0
            
        state = self.loss_states[personality_id]
        
        # Base risk reduction from emotional state
        emotional_impact = {
            EmotionalState.CONFIDENT: 0.0,
            EmotionalState.NEUTRAL: 0.1,
            EmotionalState.CAUTIOUS: 0.3,
            EmotionalState.FEARFUL: 0.5
        }
        
        base_reduction = emotional_impact.get(state.emotional_state, 0.1)
        
        # Additional reduction for consecutive losing days
        consecutive_penalty = min(state.consecutive_losing_days * 0.05, 0.2)  # Max 20% additional
        
        # Recovery factor
        recovery_boost = state.recovery_progress * 0.3  # Up to 30% recovery
        
        # Calculate final risk level
        total_reduction = (base_reduction + consecutive_penalty) * self.config.loss_aversion
        risk_level = (1.0 - total_reduction) + recovery_boost
        
        # Apply bounds
        return max(0.3, min(1.0, risk_level))  # 30% to 100% risk
    
    def should_skip_trade(self, personality_id: str) -> Tuple[bool, str]:
        """
        Determine if a trade should be skipped due to loss aversion.
        
        Args:
            personality_id: Trading personality identifier
            
        Returns:
            Tuple of (should_skip, reason)
        """
        activity_modifier = self.calculate_activity_modifier(personality_id)
        
        # Use random threshold based on activity level
        import random
        threshold = activity_modifier
        
        if random.random() > threshold:
            state = self.loss_states.get(personality_id)
            if state:
                if state.emotional_state == EmotionalState.FEARFUL:
                    return True, "Fearful emotional state - avoiding trades"
                elif state.consecutive_losing_days >= 2:
                    return True, "Multiple consecutive losing days - reducing activity"
                elif state.daily_loss_count >= 3:
                    return True, "Too many losses today - taking a break"
                else:
                    return True, "Loss aversion - reduced trading activity"
            return True, "General loss aversion"
            
        return False, ""
    
    def _calculate_emotional_state(self, state: LossAversionState) -> EmotionalState:
        """Calculate emotional state based on recent performance and losses"""
        # Consider daily P&L impact
        daily_impact = 0.0
        if state.daily_pnl < -self.config.daily_loss_threshold:
            daily_impact = -0.4  # Strong negative impact
        elif state.daily_pnl < 0:
            daily_impact = -0.2  # Moderate negative impact
        elif state.daily_pnl > self.config.daily_loss_threshold:
            daily_impact = 0.3   # Positive impact
            
        # Consider recent losses impact
        loss_impact = -min(state.recent_losses / 1000.0, 0.5)  # Up to -0.5 impact
        
        # Consider consecutive losing days
        consecutive_impact = -min(state.consecutive_losing_days * 0.15, 0.3)  # Up to -0.3 impact
        
        # Consider recovery progress (positive impact)
        recovery_impact = state.recovery_progress * 0.2  # Up to +0.2 impact
        
        # Calculate overall emotional score
        emotional_score = daily_impact + loss_impact + consecutive_impact + recovery_impact
        
        # Map to emotional states
        if emotional_score > 0.2:
            return EmotionalState.CONFIDENT
        elif emotional_score > -0.1:
            return EmotionalState.NEUTRAL
        elif emotional_score > -0.3:
            return EmotionalState.CAUTIOUS
        else:
            return EmotionalState.FEARFUL
    
    def _is_new_day(self, last_update: Optional[datetime], current_time: datetime) -> bool:
        """Check if we've moved to a new trading day"""
        if last_update is None:
            return True
            
        return last_update.date() != current_time.date()
    
    def get_loss_aversion_info(self, personality_id: str) -> Dict:
        """Get current loss aversion information for a personality"""
        if personality_id not in self.loss_states:
            return {
                'recent_losses': 0.0,
                'daily_pnl': 0.0,
                'emotional_state': EmotionalState.NEUTRAL.value,
                'recovery_progress': 1.0,
                'activity_modifier': 1.0,
                'risk_modifier': 1.0,
                'consecutive_losing_days': 0
            }
            
        state = self.loss_states[personality_id]
        
        return {
            'recent_losses': state.recent_losses,
            'daily_pnl': state.daily_pnl,
            'emotional_state': state.emotional_state.value,
            'recovery_progress': state.recovery_progress,
            'activity_modifier': self.calculate_activity_modifier(personality_id),
            'risk_modifier': self.calculate_risk_modifier(personality_id),
            'consecutive_losing_days': state.consecutive_losing_days,
            'daily_loss_count': state.daily_loss_count,
            'last_loss_date': state.last_loss_date
        }
    
    def reset_daily_state(self, personality_id: str) -> None:
        """Reset daily state (typically called at start of new trading day)"""
        if personality_id in self.loss_states:
            state = self.loss_states[personality_id]
            
            # Check if yesterday was losing day before reset
            if state.daily_pnl < -self.config.daily_loss_threshold:
                state.consecutive_losing_days += 1
            elif state.daily_pnl > 0:
                state.consecutive_losing_days = 0
                
            # Reset daily counters
            state.daily_pnl = 0
            state.daily_loss_count = 0
            state.emotional_volatility_today = 0.0
            
            logger.info(f"Reset daily state for {personality_id}, "
                       f"consecutive losing days: {state.consecutive_losing_days}")
    
    def reset_loss_state(self, personality_id: str) -> None:
        """Reset complete loss aversion state for a personality"""
        if personality_id in self.loss_states:
            del self.loss_states[personality_id]
            logger.info(f"Reset loss aversion state for personality {personality_id}")
    
    def get_behavioral_impact(self, personality_id: str) -> Dict:
        """
        Get the behavioral impact of loss aversion for decision making.
        
        Returns:
            Dict with behavioral modifications to apply
        """
        info = self.get_loss_aversion_info(personality_id)
        should_skip, skip_reason = self.should_skip_trade(personality_id)
        
        impact = {
            'activity_multiplier': info['activity_modifier'],
            'position_size_multiplier': info['risk_modifier'],
            'emotional_state': info['emotional_state'],
            'skip_trade': should_skip,
            'skip_reason': skip_reason,
            'exit_bias': 0.0,
            'entry_hesitation': 0.0,
            'stop_loss_tightening': 0.0
        }
        
        # Adjust behavior based on emotional state
        emotional_state = EmotionalState(info['emotional_state'])
        
        if emotional_state == EmotionalState.FEARFUL:
            impact['exit_bias'] = 0.4        # 40% more likely to exit early
            impact['entry_hesitation'] = 0.5  # 50% more hesitation on entries
            impact['stop_loss_tightening'] = 0.3  # Tighten stops by 30%
        elif emotional_state == EmotionalState.CAUTIOUS:
            impact['exit_bias'] = 0.2        # 20% more likely to exit early
            impact['entry_hesitation'] = 0.3  # 30% more hesitation on entries
            impact['stop_loss_tightening'] = 0.15 # Tighten stops by 15%
        elif emotional_state == EmotionalState.CONFIDENT:
            impact['exit_bias'] = -0.1       # 10% less likely to exit early
            impact['entry_hesitation'] = -0.1 # 10% less hesitation on entries
            
        return impact