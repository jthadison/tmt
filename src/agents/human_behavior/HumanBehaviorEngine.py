"""
Human Behavior Engine - Main orchestration module for human-like trading behavior.

This module integrates all behavioral components to create comprehensive
human-like trading patterns that appear as genuine human traders.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .StreakBehavior import StreakBehavior, StreakBehaviorConfig
from .LossAversion import LossAversion, LossAversionConfig  
from .WeeklyPatterns import WeeklyPatterns, WeeklyPatternsConfig
from .DailyRoutines import DailyRoutines, DailyRoutineConfig, TradingSession
from .ManualAdjustments import ManualAdjustments, ManualAdjustmentConfig
from .SessionPreferences import SessionPreferences, SessionPreferencesConfig, TraderLocation

logger = logging.getLogger(__name__)


@dataclass
class HumanBehaviorProfile:
    """Complete human behavior profile for a trading personality"""
    personality_id: str
    trader_type: str = 'day_trader'  # 'scalper', 'day_trader', 'swing_trader'
    location: TraderLocation = TraderLocation.LONDON
    timezone: str = "UTC"
    
    # Behavioral component configs
    streak_config: StreakBehaviorConfig = None
    loss_aversion_config: LossAversionConfig = None  
    weekly_config: WeeklyPatternsConfig = None
    daily_config: DailyRoutineConfig = None
    adjustment_config: ManualAdjustmentConfig = None
    session_config: SessionPreferencesConfig = None
    
    def __post_init__(self):
        if self.streak_config is None:
            self.streak_config = StreakBehaviorConfig()
        if self.loss_aversion_config is None:
            self.loss_aversion_config = LossAversionConfig()
        if self.weekly_config is None:
            self.weekly_config = WeeklyPatternsConfig()
        if self.daily_config is None:
            self.daily_config = DailyRoutineConfig(timezone=self.timezone)
        if self.adjustment_config is None:
            self.adjustment_config = ManualAdjustmentConfig()
        if self.session_config is None:
            self.session_config = SessionPreferencesConfig(trader_location=self.location)


@dataclass
class SignalModification:
    """Modifications to apply to a trading signal based on behavioral patterns"""
    skip_signal: bool = False
    skip_reason: str = ""
    
    position_size_multiplier: float = 1.0
    activity_multiplier: float = 1.0
    
    stop_loss_adjustment: float = 0.0  # Additive adjustment
    take_profit_adjustment: float = 0.0  # Additive adjustment
    
    early_exit_bias: float = 0.0  # 0-1, likelihood to exit early
    entry_hesitation: float = 0.0  # 0-1, hesitation on entry
    
    manual_adjustments: List[Dict] = None
    behavioral_notes: List[str] = None
    
    def __post_init__(self):
        if self.manual_adjustments is None:
            self.manual_adjustments = []
        if self.behavioral_notes is None:
            self.behavioral_notes = []


class HumanBehaviorEngine:
    """
    Main engine for applying human-like behavioral modifications to trading signals.
    
    Integrates all behavioral components:
    - Streak-based position sizing and confidence
    - Loss aversion and emotional responses
    - Weekly patterns and end-of-week behavior
    - Daily routines and session preferences
    - Manual adjustments and human-like modifications
    """
    
    def __init__(self):
        self.profiles: Dict[str, HumanBehaviorProfile] = {}
        
        # Initialize behavioral components
        self.streak_behavior: Optional[StreakBehavior] = None
        self.loss_aversion: Optional[LossAversion] = None
        self.weekly_patterns: Optional[WeeklyPatterns] = None
        self.daily_routines: Optional[DailyRoutines] = None
        self.manual_adjustments: Optional[ManualAdjustments] = None
        self.session_preferences: Optional[SessionPreferences] = None
        
    def add_personality(self, profile: HumanBehaviorProfile) -> None:
        """
        Add a trading personality with specific behavioral profile.
        
        Args:
            profile: Complete behavioral profile for the personality
        """
        self.profiles[profile.personality_id] = profile
        
        # Initialize behavioral components if not already done
        self._initialize_components()
        
        # Initialize personality in session preferences
        self.session_preferences.initialize_preferences(
            profile.personality_id, profile.location)
        
        logger.info(f"Added personality {profile.personality_id} with profile: "
                   f"Type: {profile.trader_type}, Location: {profile.location.value}")
    
    def apply_behavioral_modifications(self, signal: Dict, personality_id: str,
                                     current_positions: List[Dict] = None) -> SignalModification:
        """
        Apply comprehensive behavioral modifications to a trading signal.
        
        Args:
            signal: Trading signal dict with 'entry_price', 'stop_loss', 'take_profit', 'size', etc.
            personality_id: Trading personality identifier
            current_positions: List of current positions
            
        Returns:
            SignalModification object with all behavioral adjustments
        """
        if personality_id not in self.profiles:
            logger.warning(f"Unknown personality {personality_id}, using default behavior")
            return SignalModification()
            
        if current_positions is None:
            current_positions = []
            
        self._initialize_components()
        
        modifications = SignalModification()
        timestamp = datetime.now()
        
        # 1. Check daily routines first (may skip entirely)
        daily_impact = self.daily_routines.get_behavioral_impact(personality_id, timestamp)
        if daily_impact['skip_trade']:
            modifications.skip_signal = True
            modifications.skip_reason = daily_impact['skip_reason']
            modifications.behavioral_notes.append(f"Daily routine: {daily_impact['skip_reason']}")
            return modifications
            
        # 2. Apply loss aversion patterns
        loss_impact = self.loss_aversion.get_behavioral_impact(personality_id)
        if loss_impact['skip_trade']:
            modifications.skip_signal = True
            modifications.skip_reason = loss_impact['skip_reason']
            modifications.behavioral_notes.append(f"Loss aversion: {loss_impact['skip_reason']}")
            return modifications
            
        # 3. Apply weekly patterns
        weekly_impact = self.weekly_patterns.get_behavioral_impact(
            personality_id, [p.get('position_id', str(i)) for i, p in enumerate(current_positions)], timestamp)
        
        if weekly_impact['should_flatten_positions']:
            modifications.behavioral_notes.append(f"Weekly: {weekly_impact['flatten_reason']}")
            
        # 4. Calculate position size modifications
        streak_impact = self.streak_behavior.get_behavioral_impact(personality_id)
        
        # Combine all size multipliers
        size_multipliers = [
            streak_impact['position_size_multiplier'],
            loss_impact['position_size_multiplier'], 
            weekly_impact['position_size_multiplier']
        ]
        modifications.position_size_multiplier = self._combine_multipliers(size_multipliers)
        
        # 5. Calculate activity modifications
        activity_multipliers = [
            daily_impact['activity_multiplier'],
            loss_impact['activity_multiplier'],
            weekly_impact['activity_multiplier']
        ]
        modifications.activity_multiplier = self._combine_multipliers(activity_multipliers)
        
        # 6. Apply session preferences
        current_session = daily_impact.get('session_focus', TradingSession.OFF_HOURS)
        if isinstance(current_session, str):
            current_session = TradingSession(current_session)
            
        session_impact = self.session_preferences.get_behavioral_impact(
            personality_id, current_session, signal.get('currency_pair'), timestamp)
        
        # Adjust activity by session preference
        modifications.activity_multiplier *= session_impact['session_activity_multiplier']
        
        # 7. Calculate exit and entry biases
        modifications.early_exit_bias = max(
            weekly_impact['early_exit_bias'],
            loss_impact.get('exit_bias', 0.0)
        )
        
        modifications.entry_hesitation = loss_impact.get('entry_hesitation', 0.0)
        
        # 8. Generate manual adjustments
        manual_impact = self.manual_adjustments.get_behavioral_impact(personality_id, signal)
        modifications.manual_adjustments = manual_impact['suggested_adjustments']
        
        # 9. Apply stop loss and take profit adjustments
        if loss_impact.get('stop_loss_tightening', 0) > 0:
            tighten_pct = loss_impact['stop_loss_tightening']
            if signal.get('stop_loss'):
                sl_adjustment = abs(signal['stop_loss'] - signal.get('entry_price', signal['stop_loss'])) * tighten_pct
                modifications.stop_loss_adjustment = -sl_adjustment  # Tighter stop
                modifications.behavioral_notes.append(f"Tightened stop loss by {tighten_pct*100:.1f}%")
                
        # 10. Check final activity level for skip decision
        if modifications.activity_multiplier < 0.3:
            modifications.skip_signal = True
            modifications.skip_reason = "Combined behavioral factors indicate low activity"
            
        # Add comprehensive behavioral notes
        self._add_behavioral_notes(modifications, {
            'streak': streak_impact,
            'loss': loss_impact,
            'weekly': weekly_impact,
            'daily': daily_impact,
            'session': session_impact,
            'manual': manual_impact
        })
        
        logger.debug(f"Applied behavioral modifications for {personality_id}: "
                    f"Size: {modifications.position_size_multiplier:.3f}, "
                    f"Activity: {modifications.activity_multiplier:.3f}, "
                    f"Skip: {modifications.skip_signal}")
        
        return modifications
    
    def update_performance(self, personality_id: str, trade_result: Dict) -> None:
        """
        Update behavioral state based on trade performance.
        
        Args:
            personality_id: Trading personality identifier
            trade_result: Trade result with 'pnl', 'timestamp', 'trade_id', etc.
        """
        if personality_id not in self.profiles:
            return
            
        self._initialize_components()
        
        # Update all behavioral components
        self.streak_behavior.update_streak(personality_id, trade_result)
        self.loss_aversion.update_loss_state(personality_id, trade_result)
        self.weekly_patterns.update_weekly_state(personality_id, trade_result)
        self.daily_routines.update_daily_state(personality_id, trade_result.get('timestamp'))
        
        # Update session performance if session info available
        if 'session' in trade_result:
            session = TradingSession(trade_result['session'])
            pnl = trade_result.get('pnl', 0)
            performance_score = 1.0 if pnl > 0 else -1.0 if pnl < 0 else 0.0
            self.session_preferences.update_session_performance(
                personality_id, session, performance_score)
        
        # Increment daily trade count
        self.daily_routines.increment_trade_count(personality_id)
        
        logger.debug(f"Updated performance for {personality_id}: P&L ${trade_result.get('pnl', 0):.2f}")
    
    def get_personality_status(self, personality_id: str) -> Dict:
        """Get comprehensive status of a personality's behavioral state"""
        if personality_id not in self.profiles:
            return {}
            
        self._initialize_components()
        
        return {
            'personality_id': personality_id,
            'profile': {
                'trader_type': self.profiles[personality_id].trader_type,
                'location': self.profiles[personality_id].location.value,
                'timezone': self.profiles[personality_id].timezone
            },
            'streak_info': self.streak_behavior.get_streak_info(personality_id),
            'loss_aversion_info': self.loss_aversion.get_loss_aversion_info(personality_id),
            'weekly_info': self.weekly_patterns.get_weekly_info(personality_id),
            'daily_info': self.daily_routines.get_daily_info(personality_id),
            'adjustment_info': self.manual_adjustments.get_adjustment_info(personality_id),
            'session_info': self.session_preferences.get_session_info(personality_id)
        }
    
    def _initialize_components(self) -> None:
        """Initialize behavioral components with default configs if not already done"""
        if self.streak_behavior is None:
            self.streak_behavior = StreakBehavior()
        if self.loss_aversion is None:
            self.loss_aversion = LossAversion()
        if self.weekly_patterns is None:
            self.weekly_patterns = WeeklyPatterns()
        if self.daily_routines is None:
            self.daily_routines = DailyRoutines()
        if self.manual_adjustments is None:
            self.manual_adjustments = ManualAdjustments()
        if self.session_preferences is None:
            self.session_preferences = SessionPreferences()
    
    def _combine_multipliers(self, multipliers: List[float]) -> float:
        """Combine multiple multipliers in a balanced way"""
        if not multipliers:
            return 1.0
            
        # Use geometric mean for balanced combination
        product = 1.0
        for mult in multipliers:
            product *= mult
            
        return product ** (1.0 / len(multipliers))
    
    def _add_behavioral_notes(self, modifications: SignalModification, impacts: Dict[str, Dict]) -> None:
        """Add detailed behavioral notes for transparency"""
        
        # Streak behavior notes
        streak_info = impacts['streak']
        if streak_info['confidence_level'] > 0.7:
            modifications.behavioral_notes.append("High confidence from winning streak")
        elif streak_info['confidence_level'] < 0.3:
            modifications.behavioral_notes.append("Low confidence from recent losses")
            
        # Loss aversion notes
        loss_info = impacts['loss']
        if loss_info['emotional_state'] in ['cautious', 'fearful']:
            modifications.behavioral_notes.append(f"Emotional state: {loss_info['emotional_state']}")
            
        # Weekly pattern notes
        weekly_info = impacts['weekly']
        if weekly_info['friday_behavior'] == 'flattening':
            modifications.behavioral_notes.append("Friday position flattening mode")
        elif weekly_info['monday_caution_active']:
            modifications.behavioral_notes.append("Monday morning caution active")
            
        # Session preference notes
        session_info = impacts['session']
        if session_info['should_focus_session']:
            modifications.behavioral_notes.append(f"Focused on {session_info['session_specialization']} session")
            
        # Manual adjustment notes
        manual_info = impacts['manual']
        if manual_info['suggested_adjustments']:
            adj_count = len(manual_info['suggested_adjustments'])
            modifications.behavioral_notes.append(f"{adj_count} manual adjustments suggested")
    
    def reset_personality(self, personality_id: str) -> None:
        """Reset all behavioral state for a personality"""
        if personality_id not in self.profiles:
            return
            
        self._initialize_components()
        
        # Reset all behavioral components
        self.streak_behavior.reset_streak(personality_id)
        self.loss_aversion.reset_loss_state(personality_id)
        self.weekly_patterns.reset_weekly_state(personality_id)
        self.daily_routines.reset_daily_state(personality_id)
        self.manual_adjustments.reset_adjustment_state(personality_id)
        self.session_preferences.reset_session_preferences(personality_id)
        
        logger.info(f"Reset all behavioral state for personality {personality_id}")
    
    def remove_personality(self, personality_id: str) -> None:
        """Remove a personality and all its behavioral state"""
        if personality_id in self.profiles:
            self.reset_personality(personality_id)
            del self.profiles[personality_id]
            logger.info(f"Removed personality {personality_id}")
    
    def get_all_personalities(self) -> List[str]:
        """Get list of all registered personality IDs"""
        return list(self.profiles.keys())