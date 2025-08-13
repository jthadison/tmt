"""
Daily Routines Module - Implements daily routine patterns for human-like trading behavior.

This module handles time-of-day trading behavior patterns including lunch breaks,
session-based activity patterns, morning warmup, evening winddown, and consistent
daily schedules that mimic real trader behavior.
"""

import logging
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import pytz

logger = logging.getLogger(__name__)


class TradingSession(Enum):
    """Trading session types"""
    ASIAN = "asian"
    LONDON = "london"
    NEWYORK = "newyork"
    OVERLAP_LONDON_NY = "overlap_london_ny"
    OFF_HOURS = "off_hours"


class ActivityLevel(Enum):
    """Activity level states throughout the day"""
    SLEEPING = "sleeping"
    WARMING_UP = "warming_up"
    ACTIVE = "active"
    LUNCH_BREAK = "lunch_break"
    WINDING_DOWN = "winding_down"


@dataclass
class SessionPreference:
    """Preference settings for trading sessions"""
    session: TradingSession
    preference: float = 0.5          # 0-1, how much this trader likes this session
    activity_multiplier: float = 1.0 # Activity level during this session
    pair_preferences: List[str] = None # Preferred pairs during this session
    
    def __post_init__(self):
        if self.pair_preferences is None:
            self.pair_preferences = []


@dataclass
class DailyRoutineConfig:
    """Configuration for daily routine patterns"""
    timezone: str = "UTC"                        # Trader's timezone
    lunch_breaks: bool = True                    # Take lunch breaks
    lunch_start_time: str = "12:00"             # Lunch start time (24h format)
    lunch_duration: int = 60                     # Lunch duration in minutes
    morning_warmup: bool = True                  # Gradual activity increase in morning
    evening_winddown: bool = True                # Gradual activity decrease in evening
    work_start_hour: int = 7                     # Start of trading day
    work_end_hour: int = 19                      # End of trading day
    session_preferences: List[SessionPreference] = None
    activity_variation: float = 0.2              # Random variation in activity (0-1)
    break_probability: float = 0.1               # Probability of random short breaks
    
    def __post_init__(self):
        if self.session_preferences is None:
            # Default session preferences
            self.session_preferences = [
                SessionPreference(TradingSession.LONDON, 0.8, 1.2),
                SessionPreference(TradingSession.NEWYORK, 0.7, 1.0),
                SessionPreference(TradingSession.OVERLAP_LONDON_NY, 0.9, 1.3),
                SessionPreference(TradingSession.ASIAN, 0.3, 0.5)
            ]


@dataclass
class DailyState:
    """Current daily routine state for a trading personality"""
    current_activity_level: ActivityLevel = ActivityLevel.ACTIVE
    current_session: TradingSession = TradingSession.OFF_HOURS
    in_lunch_break: bool = False
    lunch_break_start: Optional[datetime] = None
    daily_activity: float = 1.0                  # 0-1 current activity level
    morning_warmup_progress: float = 1.0         # 0-1 warmup progress
    evening_winddown_progress: float = 0.0       # 0-1 winddown progress
    session_start_time: Optional[datetime] = None
    last_break_time: Optional[datetime] = None
    trades_today: int = 0
    last_daily_update: Optional[datetime] = None


class DailyRoutines:
    """
    Manages daily routine behavioral patterns for human-like trading behavior.
    
    Implements daily trading patterns including:
    - Lunch break patterns for day-trader personalities
    - Session-based activity patterns and preferences  
    - Morning warmup and evening winddown behaviors
    - Time-of-day trading preferences and consistency
    - Random variation and micro-breaks for realism
    """
    
    def __init__(self, config: DailyRoutineConfig = None):
        self.config = config or DailyRoutineConfig()
        self.daily_states: Dict[str, DailyState] = {}
        
        # Setup timezone
        try:
            self.trader_timezone = pytz.timezone(self.config.timezone)
        except:
            self.trader_timezone = pytz.UTC
            logger.warning(f"Invalid timezone {self.config.timezone}, using UTC")
            
    def update_daily_state(self, personality_id: str, timestamp: datetime = None) -> DailyState:
        """
        Update daily routine state based on current time.
        
        Args:
            personality_id: Trading personality identifier
            timestamp: Current timestamp (default: now)
            
        Returns:
            Updated daily state
        """
        if timestamp is None:
            timestamp = datetime.now(pytz.UTC)
            
        if personality_id not in self.daily_states:
            self.daily_states[personality_id] = DailyState()
            
        state = self.daily_states[personality_id]
        
        # Convert to trader's timezone
        trader_time = timestamp.astimezone(self.trader_timezone)
        
        # Check if new day
        if self._is_new_day(state.last_daily_update, trader_time):
            self._reset_daily_counters(state, trader_time)
            
        # Update current session
        state.current_session = self._determine_current_session(trader_time)
        
        # Update activity level based on time of day
        state.current_activity_level = self._determine_activity_level(trader_time, state)
        
        # Update lunch break status
        self._update_lunch_break_status(trader_time, state)
        
        # Calculate current activity multiplier
        state.daily_activity = self._calculate_daily_activity(trader_time, state)
        
        state.last_daily_update = trader_time
        
        logger.debug(f"Updated daily state for {personality_id}: "
                    f"Activity level: {state.current_activity_level.value}, "
                    f"Session: {state.current_session.value}, "
                    f"Daily activity: {state.daily_activity:.3f}")
        
        return state
    
    def should_take_lunch_break(self, personality_id: str, timestamp: datetime = None) -> Tuple[bool, str]:
        """
        Check if trader should take lunch break.
        
        Args:
            personality_id: Trading personality identifier
            timestamp: Current timestamp (default: now)
            
        Returns:
            Tuple of (should_break, reason)
        """
        if not self.config.lunch_breaks:
            return False, "Lunch breaks disabled"
            
        if timestamp is None:
            timestamp = datetime.now(pytz.UTC)
            
        trader_time = timestamp.astimezone(self.trader_timezone)
        
        # Parse lunch start time
        lunch_start = time.fromisoformat(self.config.lunch_start_time)
        lunch_end_dt = datetime.combine(trader_time.date(), lunch_start) + timedelta(minutes=self.config.lunch_duration)
        lunch_end = lunch_end_dt.time()
        
        current_time = trader_time.time()
        
        # Check if within lunch window
        if lunch_start <= current_time <= lunch_end:
            return True, "Lunch break time"
            
        return False, ""
    
    def calculate_session_activity_modifier(self, personality_id: str, timestamp: datetime = None) -> float:
        """
        Calculate activity modifier based on current trading session.
        
        Args:
            personality_id: Trading personality identifier
            timestamp: Current timestamp (default: now)
            
        Returns:
            Activity multiplier (1.0 = normal, >1.0 = more active, <1.0 = less active)
        """
        if timestamp is None:
            timestamp = datetime.now(pytz.UTC)
            
        self.update_daily_state(personality_id, timestamp)
        state = self.daily_states[personality_id]
        current_session = state.current_session
        
        # Find session preference
        session_pref = next(
            (pref for pref in self.config.session_preferences 
             if pref.session == current_session), 
            None
        )
        
        if session_pref:
            base_multiplier = session_pref.activity_multiplier * session_pref.preference
        else:
            base_multiplier = 0.3  # Low activity during non-preferred sessions
            
        # Apply daily activity level
        return base_multiplier * state.daily_activity
    
    def should_skip_trading(self, personality_id: str, timestamp: datetime = None) -> Tuple[bool, str]:
        """
        Determine if trading should be skipped based on daily routines.
        
        Args:
            personality_id: Trading personality identifier
            timestamp: Current timestamp (default: now)
            
        Returns:
            Tuple of (should_skip, reason)
        """
        if timestamp is None:
            timestamp = datetime.now(pytz.UTC)
            
        self.update_daily_state(personality_id, timestamp)
        state = self.daily_states[personality_id]
        
        # Skip during lunch break
        if state.in_lunch_break:
            return True, "On lunch break"
            
        # Skip if outside work hours
        trader_time = timestamp.astimezone(self.trader_timezone)
        current_hour = trader_time.hour
        
        if current_hour < self.config.work_start_hour or current_hour >= self.config.work_end_hour:
            return True, "Outside work hours"
            
        # Skip during very low activity periods
        if state.daily_activity < 0.2:
            return True, "Low activity period"
            
        # Random micro-breaks
        import random
        if random.random() < self.config.break_probability * 0.1:  # Very low probability
            return True, "Taking a short break"
            
        return False, ""
    
    def _determine_current_session(self, trader_time: datetime) -> TradingSession:
        """Determine current trading session based on UTC time"""
        utc_time = trader_time.astimezone(pytz.UTC)
        utc_hour = utc_time.hour
        
        # Trading session times in UTC
        if 0 <= utc_hour < 7:  # Asian session
            return TradingSession.ASIAN
        elif 7 <= utc_hour < 13:  # London session
            return TradingSession.LONDON
        elif 13 <= utc_hour < 15:  # London/NY overlap
            return TradingSession.OVERLAP_LONDON_NY
        elif 15 <= utc_hour < 22:  # New York session
            return TradingSession.NEWYORK
        else:  # Off hours
            return TradingSession.OFF_HOURS
            
    def _determine_activity_level(self, trader_time: datetime, state: DailyState) -> ActivityLevel:
        """Determine current activity level based on time and state"""
        current_hour = trader_time.hour
        
        # Check lunch break first
        if state.in_lunch_break:
            return ActivityLevel.LUNCH_BREAK
            
        # Check work hours
        if current_hour < self.config.work_start_hour:
            return ActivityLevel.SLEEPING
        elif current_hour >= self.config.work_end_hour:
            return ActivityLevel.WINDING_DOWN
            
        # Morning warmup period
        if (self.config.morning_warmup and 
            current_hour < self.config.work_start_hour + 2):
            return ActivityLevel.WARMING_UP
            
        # Evening winddown period  
        if (self.config.evening_winddown and
            current_hour >= self.config.work_end_hour - 2):
            return ActivityLevel.WINDING_DOWN
            
        return ActivityLevel.ACTIVE
    
    def _update_lunch_break_status(self, trader_time: datetime, state: DailyState) -> None:
        """Update lunch break status based on current time"""
        should_break, _ = self.should_take_lunch_break("", trader_time)
        
        if should_break and not state.in_lunch_break:
            # Start lunch break
            state.in_lunch_break = True
            state.lunch_break_start = trader_time
            logger.debug(f"Started lunch break at {trader_time}")
            
        elif not should_break and state.in_lunch_break:
            # End lunch break
            state.in_lunch_break = False
            state.lunch_break_start = None
            logger.debug(f"Ended lunch break at {trader_time}")
    
    def _calculate_daily_activity(self, trader_time: datetime, state: DailyState) -> float:
        """Calculate overall daily activity level"""
        base_activity = 1.0
        current_hour = trader_time.hour
        
        # Morning warmup effect
        if (self.config.morning_warmup and 
            self.config.work_start_hour <= current_hour < self.config.work_start_hour + 2):
            warmup_progress = (current_hour - self.config.work_start_hour) / 2.0
            base_activity = 0.4 + (0.6 * warmup_progress)  # Ramp from 40% to 100%
            
        # Evening winddown effect
        elif (self.config.evening_winddown and
              self.config.work_end_hour - 2 <= current_hour < self.config.work_end_hour):
            winddown_progress = (self.config.work_end_hour - current_hour) / 2.0
            base_activity = 0.4 + (0.6 * winddown_progress)  # Ramp down to 40%
            
        # Lunch break effect
        if state.in_lunch_break:
            base_activity = 0.0
            
        # Outside work hours
        if current_hour < self.config.work_start_hour or current_hour >= self.config.work_end_hour:
            base_activity = 0.1  # Very low activity
            
        # Add random variation
        import random
        variation = 1.0 + (random.random() - 0.5) * self.config.activity_variation
        base_activity *= variation
        
        return max(0.0, min(1.0, base_activity))  # Clamp between 0 and 1
    
    def _is_new_day(self, last_update: Optional[datetime], current_time: datetime) -> bool:
        """Check if we've moved to a new trading day"""
        if last_update is None:
            return True
            
        return last_update.date() != current_time.date()
    
    def _reset_daily_counters(self, state: DailyState, trader_time: datetime) -> None:
        """Reset daily counters for new day"""
        state.trades_today = 0
        state.in_lunch_break = False
        state.lunch_break_start = None
        state.morning_warmup_progress = 0.0
        state.evening_winddown_progress = 0.0
        state.last_break_time = None
        
        logger.debug(f"Reset daily counters for new day: {trader_time.date()}")
    
    def get_daily_info(self, personality_id: str, timestamp: datetime = None) -> Dict:
        """Get current daily routine information for a personality"""
        if timestamp is None:
            timestamp = datetime.now(pytz.UTC)
            
        if personality_id not in self.daily_states:
            self.update_daily_state(personality_id, timestamp)
            
        state = self.daily_states[personality_id]
        should_skip, skip_reason = self.should_skip_trading(personality_id, timestamp)
        should_lunch, lunch_reason = self.should_take_lunch_break(personality_id, timestamp)
        
        return {
            'current_activity_level': state.current_activity_level.value,
            'current_session': state.current_session.value,
            'in_lunch_break': state.in_lunch_break,
            'daily_activity': state.daily_activity,
            'should_skip_trading': should_skip,
            'skip_reason': skip_reason,
            'should_take_lunch': should_lunch,
            'lunch_reason': lunch_reason,
            'trades_today': state.trades_today,
            'session_activity_modifier': self.calculate_session_activity_modifier(personality_id, timestamp)
        }
    
    def increment_trade_count(self, personality_id: str) -> None:
        """Increment daily trade count"""
        if personality_id in self.daily_states:
            self.daily_states[personality_id].trades_today += 1
    
    def reset_daily_state(self, personality_id: str) -> None:
        """Reset daily state for a personality"""
        if personality_id in self.daily_states:
            del self.daily_states[personality_id]
            logger.info(f"Reset daily state for personality {personality_id}")
    
    def get_behavioral_impact(self, personality_id: str, timestamp: datetime = None) -> Dict:
        """
        Get the behavioral impact of daily routines for decision making.
        
        Args:
            personality_id: Trading personality identifier
            timestamp: Current timestamp (default: now)
            
        Returns:
            Dict with behavioral modifications to apply
        """
        if timestamp is None:
            timestamp = datetime.now(pytz.UTC)
            
        info = self.get_daily_info(personality_id, timestamp)
        
        impact = {
            'activity_multiplier': info['session_activity_modifier'],
            'skip_trade': info['should_skip_trading'],
            'skip_reason': info['skip_reason'],
            'session_focus': info['current_session'],
            'time_of_day_bias': 0.0,
            'patience_modifier': 1.0,
            'risk_adjustment': 0.0
        }
        
        # Adjust behavior based on activity level
        activity_level = ActivityLevel(info['current_activity_level'])
        
        if activity_level == ActivityLevel.WARMING_UP:
            impact['patience_modifier'] = 1.3  # More patient during warmup
            impact['risk_adjustment'] = -0.1   # Slightly more conservative
        elif activity_level == ActivityLevel.WINDING_DOWN:
            impact['patience_modifier'] = 0.8  # Less patient, want to close out
            impact['time_of_day_bias'] = 0.2   # Bias toward exiting positions
        elif activity_level == ActivityLevel.LUNCH_BREAK:
            impact['skip_trade'] = True
            impact['skip_reason'] = "On lunch break"
            
        # Session-specific adjustments
        current_session = TradingSession(info['current_session'])
        if current_session == TradingSession.OVERLAP_LONDON_NY:
            impact['risk_adjustment'] = 0.1    # Slightly more aggressive during overlap
        elif current_session == TradingSession.OFF_HOURS:
            impact['risk_adjustment'] = -0.2   # More conservative during off hours
            
        return impact