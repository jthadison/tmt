"""
Session Preferences Module - Implements trading session consistency patterns.

This module manages trader location-based preferences, session focus algorithms,
and consistent session behavior patterns that reflect real trader preferences
based on their geographic location and trading style.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import pytz

from .DailyRoutines import TradingSession

logger = logging.getLogger(__name__)


class TraderLocation(Enum):
    """Trader geographic locations"""
    LONDON = "london"
    NEW_YORK = "new_york"  
    TOKYO = "tokyo"
    SYDNEY = "sydney"
    FRANKFURT = "frankfurt"
    ZURICH = "zurich"
    SINGAPORE = "singapore"
    HONG_KONG = "hong_kong"


@dataclass
class CurrencyPairPreference:
    """Preference for trading specific currency pairs during sessions"""
    pair: str
    preference: float = 0.5      # 0-1, how much this trader likes this pair
    session_multiplier: float = 1.0  # Multiplier during preferred session


@dataclass  
class SessionPreferencesConfig:
    """Configuration for session preference patterns"""
    trader_location: TraderLocation = TraderLocation.LONDON
    home_session_bias: float = 1.5              # Preference multiplier for home session
    overlap_session_bonus: float = 1.3          # Bonus for overlap sessions
    off_hours_penalty: float = 0.2              # Activity reduction during off hours  
    session_consistency: float = 0.8            # How consistent session preferences are (0-1)
    pair_specialization: bool = True            # Focus on location-specific pairs
    news_session_awareness: bool = True         # Increased activity during news sessions
    

@dataclass
class SessionState:
    """Current session preference state for a trading personality"""
    preferred_sessions: List[TradingSession] = None
    current_session_activity: float = 1.0
    session_performance_history: Dict[str, float] = None  # Session -> avg performance
    preferred_pairs: List[CurrencyPairPreference] = None
    session_consistency_score: float = 0.8
    last_session_update: Optional[datetime] = None
    
    def __post_init__(self):
        if self.preferred_sessions is None:
            self.preferred_sessions = []
        if self.session_performance_history is None:
            self.session_performance_history = {}
        if self.preferred_pairs is None:
            self.preferred_pairs = []


class SessionPreferences:
    """
    Manages session-based trading preferences for human-like behavior.
    
    Implements session consistency patterns including:
    - Trader location-based session preferences
    - Consistent session focus and behavior patterns  
    - Currency pair specialization by session
    - Performance-based session preference evolution
    - Geographic timezone awareness
    """
    
    def __init__(self, config: SessionPreferencesConfig = None):
        self.config = config or SessionPreferencesConfig()
        self.session_states: Dict[str, SessionState] = {}
        
        # Define session timezone mappings
        self.session_timezones = {
            TradingSession.ASIAN: pytz.timezone('Asia/Tokyo'),
            TradingSession.LONDON: pytz.timezone('Europe/London'),
            TradingSession.NEWYORK: pytz.timezone('America/New_York'),
            TradingSession.OVERLAP_LONDON_NY: pytz.timezone('Europe/London'),
        }
        
        # Define location-based default preferences
        self.location_preferences = {
            TraderLocation.LONDON: {
                'primary_sessions': [TradingSession.LONDON, TradingSession.OVERLAP_LONDON_NY],
                'pairs': ['GBPUSD', 'EURGBP', 'GBPJPY', 'EURUSD']
            },
            TraderLocation.NEW_YORK: {
                'primary_sessions': [TradingSession.NEWYORK, TradingSession.OVERLAP_LONDON_NY],
                'pairs': ['EURUSD', 'GBPUSD', 'USDCAD', 'USDJPY']
            },
            TraderLocation.TOKYO: {
                'primary_sessions': [TradingSession.ASIAN],
                'pairs': ['USDJPY', 'EURJPY', 'GBPJPY', 'AUDJPY']
            },
            TraderLocation.SYDNEY: {
                'primary_sessions': [TradingSession.ASIAN],
                'pairs': ['AUDUSD', 'NZDUSD', 'AUDNZD', 'AUDJPY']
            }
        }
        
    def initialize_preferences(self, personality_id: str, trader_location: TraderLocation = None) -> SessionState:
        """
        Initialize session preferences for a trading personality.
        
        Args:
            personality_id: Trading personality identifier
            trader_location: Trader's geographic location
            
        Returns:
            Initialized session state
        """
        if trader_location is None:
            trader_location = self.config.trader_location
            
        state = SessionState()
        
        # Set preferred sessions based on location
        location_prefs = self.location_preferences.get(trader_location, 
                                                      self.location_preferences[TraderLocation.LONDON])
        
        state.preferred_sessions = location_prefs['primary_sessions'].copy()
        
        # Initialize currency pair preferences
        if self.config.pair_specialization:
            state.preferred_pairs = [
                CurrencyPairPreference(
                    pair=pair,
                    preference=0.7 + (0.3 * hash(pair + personality_id) / 2**31),  # Consistent randomization
                    session_multiplier=1.0
                )
                for pair in location_prefs['pairs']
            ]
        
        # Initialize session performance history with neutral values
        for session in TradingSession:
            state.session_performance_history[session.value] = 0.0
            
        state.session_consistency_score = self.config.session_consistency
        
        self.session_states[personality_id] = state
        
        logger.info(f"Initialized session preferences for {personality_id}: "
                   f"Location: {trader_location.value}, Sessions: {[s.value for s in state.preferred_sessions]}")
        
        return state
    
    def calculate_session_activity_modifier(self, personality_id: str, current_session: TradingSession,
                                          timestamp: datetime = None) -> float:
        """
        Calculate activity modifier based on session preferences.
        
        Args:
            personality_id: Trading personality identifier
            current_session: Current trading session
            timestamp: Current timestamp
            
        Returns:
            Activity multiplier for current session
        """
        if personality_id not in self.session_states:
            self.initialize_preferences(personality_id)
            
        state = self.session_states[personality_id]
        
        base_multiplier = 1.0
        
        # Apply home session bias
        if current_session in state.preferred_sessions:
            base_multiplier = self.config.home_session_bias
            
        # Apply overlap session bonus
        elif current_session == TradingSession.OVERLAP_LONDON_NY:
            base_multiplier = self.config.overlap_session_bonus
            
        # Apply off-hours penalty
        elif current_session == TradingSession.OFF_HOURS:
            base_multiplier = self.config.off_hours_penalty
            
        # Apply session performance history
        session_performance = state.session_performance_history.get(current_session.value, 0.0)
        performance_modifier = 1.0 + (session_performance * 0.1)  # ±10% based on performance
        
        # Apply consistency factor
        consistency_factor = state.session_consistency_score
        final_modifier = base_multiplier * performance_modifier * consistency_factor
        
        return max(0.1, final_modifier)  # Minimum 10% activity
    
    def get_pair_preference(self, personality_id: str, currency_pair: str, 
                           current_session: TradingSession) -> float:
        """
        Get preference score for trading a specific currency pair in current session.
        
        Args:
            personality_id: Trading personality identifier
            currency_pair: Currency pair symbol (e.g., 'EURUSD')
            current_session: Current trading session
            
        Returns:
            Preference score (0-1, higher is more preferred)
        """
        if personality_id not in self.session_states:
            self.initialize_preferences(personality_id)
            
        state = self.session_states[personality_id]
        
        # Find pair preference
        pair_pref = next(
            (p for p in state.preferred_pairs if p.pair == currency_pair),
            None
        )
        
        if pair_pref:
            base_preference = pair_pref.preference
            session_multiplier = pair_pref.session_multiplier
        else:
            # Default preference for non-specialized pairs
            base_preference = 0.3
            session_multiplier = 1.0
            
        # Adjust based on session appropriateness
        session_adjustment = 1.0
        if current_session in state.preferred_sessions:
            session_adjustment = 1.2  # 20% boost during preferred sessions
        elif current_session == TradingSession.OFF_HOURS:
            session_adjustment = 0.5  # 50% reduction during off hours
            
        return min(1.0, base_preference * session_multiplier * session_adjustment)
    
    def update_session_performance(self, personality_id: str, session: TradingSession, 
                                 performance_score: float) -> None:
        """
        Update session performance history to evolve preferences.
        
        Args:
            personality_id: Trading personality identifier
            session: Trading session
            performance_score: Performance score (-1 to 1, where 1 is excellent)
        """
        if personality_id not in self.session_states:
            self.initialize_preferences(personality_id)
            
        state = self.session_states[personality_id]
        
        # Update performance with exponential moving average
        current_perf = state.session_performance_history.get(session.value, 0.0)
        alpha = 0.1  # Learning rate
        new_perf = current_perf * (1 - alpha) + performance_score * alpha
        
        state.session_performance_history[session.value] = max(-1.0, min(1.0, new_perf))
        
        # Evolve preferred sessions based on performance
        if performance_score > 0.5 and session not in state.preferred_sessions:
            # Add well-performing session to preferences
            if len(state.preferred_sessions) < 3:  # Max 3 preferred sessions
                state.preferred_sessions.append(session)
                logger.info(f"Added {session.value} to preferred sessions for {personality_id}")
                
        elif performance_score < -0.5 and session in state.preferred_sessions:
            # Remove poorly performing session from preferences
            if len(state.preferred_sessions) > 1:  # Keep at least 1 preferred session
                state.preferred_sessions.remove(session)
                logger.info(f"Removed {session.value} from preferred sessions for {personality_id}")
    
    def should_focus_on_session(self, personality_id: str, session: TradingSession, 
                               timestamp: datetime = None) -> Tuple[bool, float, str]:
        """
        Determine if trader should focus on specific session.
        
        Args:
            personality_id: Trading personality identifier
            session: Trading session to check
            timestamp: Current timestamp
            
        Returns:
            Tuple of (should_focus, focus_intensity, reason)
        """
        activity_modifier = self.calculate_session_activity_modifier(personality_id, session, timestamp)
        
        if activity_modifier > 1.2:
            return True, activity_modifier, f"High preference for {session.value} session"
        elif activity_modifier > 1.0:
            return True, activity_modifier, f"Preferred {session.value} session"
        elif activity_modifier < 0.5:
            return False, activity_modifier, f"Low preference for {session.value} session"
        else:
            return False, activity_modifier, f"Neutral on {session.value} session"
    
    def get_session_info(self, personality_id: str) -> Dict:
        """Get session preference information for a personality"""
        if personality_id not in self.session_states:
            self.initialize_preferences(personality_id)
            
        state = self.session_states[personality_id]
        
        return {
            'preferred_sessions': [s.value for s in state.preferred_sessions],
            'session_performance': state.session_performance_history.copy(),
            'preferred_pairs': [
                {'pair': p.pair, 'preference': p.preference}
                for p in state.preferred_pairs
            ],
            'consistency_score': state.session_consistency_score,
            'trader_location': self.config.trader_location.value
        }
    
    def reset_session_preferences(self, personality_id: str) -> None:
        """Reset session preferences for a personality"""
        if personality_id in self.session_states:
            del self.session_states[personality_id]
            logger.info(f"Reset session preferences for personality {personality_id}")
    
    def get_behavioral_impact(self, personality_id: str, current_session: TradingSession,
                             currency_pair: str = None, timestamp: datetime = None) -> Dict:
        """
        Get behavioral impact of session preferences.
        
        Returns:
            Dict with session-based behavioral modifications
        """
        should_focus, focus_intensity, focus_reason = self.should_focus_on_session(
            personality_id, current_session, timestamp)
        
        activity_modifier = self.calculate_session_activity_modifier(
            personality_id, current_session, timestamp)
        
        pair_preference = 0.5  # Default
        if currency_pair:
            pair_preference = self.get_pair_preference(personality_id, currency_pair, current_session)
            
        impact = {
            'session_activity_multiplier': activity_modifier,
            'should_focus_session': should_focus,
            'focus_intensity': focus_intensity,
            'focus_reason': focus_reason,
            'pair_preference': pair_preference,
            'session_specialization': current_session.value,
            'consistency_factor': self.session_states.get(personality_id, SessionState()).session_consistency_score,
            'preferred_pairs': [p.pair for p in self.session_states.get(personality_id, SessionState()).preferred_pairs],
            'session_bias': 'bullish' if activity_modifier > 1.0 else 'bearish'
        }
        
        return impact