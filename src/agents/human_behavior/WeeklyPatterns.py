"""
Weekly Patterns Module - Implements end-of-week behavioral patterns for human-like trading.

This module handles weekly trading behavior patterns including end-of-week position
flattening, Friday afternoon caution, weekend gap aversion, and Monday morning behavior.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class DayOfWeek(Enum):
    """Days of the week for trading pattern recognition"""
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


class FridayBehavior(Enum):
    """Types of Friday behavior patterns"""
    NORMAL = "normal"
    REDUCING = "reducing"
    FLATTENING = "flattening"


@dataclass
class WeeklyPatternsConfig:
    """Configuration for weekly behavior patterns"""
    end_of_week_flattening: bool = True          # Flatten positions on Friday
    friday_reduction: float = 0.3                # % activity reduction on Friday
    monday_morning_caution: float = 0.2          # Extra caution Monday morning
    weekend_gap_aversion: float = 0.4            # Avoid weekend gap risk
    friday_afternoon_start: int = 14             # Hour when Friday afternoon begins (2 PM)
    monday_caution_hours: int = 2                # Hours of extra caution Monday morning
    flattening_probability: float = 0.6          # Probability of flattening positions
    position_size_reduction_friday: float = 0.5  # Position size reduction on Friday


@dataclass
class WeeklyState:
    """Current weekly pattern state for a trading personality"""
    weekly_pnl: float = 0.0                      # This week's P&L
    positions_to_flatten: List[str] = None       # Positions marked for flattening
    friday_behavior: FridayBehavior = FridayBehavior.NORMAL
    week_start_date: Optional[datetime] = None   # Start of current trading week
    positions_flattened_friday: List[str] = None # Positions flattened on Friday
    monday_caution_active: bool = False          # Monday morning caution active
    last_weekly_update: Optional[datetime] = None
    
    def __post_init__(self):
        if self.positions_to_flatten is None:
            self.positions_to_flatten = []
        if self.positions_flattened_friday is None:
            self.positions_flattened_friday = []


class WeeklyPatterns:
    """
    Manages weekly behavioral patterns for human-like trading behavior.
    
    Implements weekly trading patterns including:
    - End-of-week position flattening for some personalities
    - Friday afternoon activity reduction and caution
    - Weekend gap risk aversion
    - Monday morning cautious behavior
    - Weekly P&L tracking and reset
    """
    
    def __init__(self, config: WeeklyPatternsConfig = None):
        self.config = config or WeeklyPatternsConfig()
        self.weekly_states: Dict[str, WeeklyState] = {}
        
    def update_weekly_state(self, personality_id: str, trade_result: Dict) -> WeeklyState:
        """
        Update weekly state based on trade result.
        
        Args:
            personality_id: Trading personality identifier
            trade_result: Dict with 'pnl', 'timestamp', 'trade_id', 'position_id' keys
            
        Returns:
            Updated weekly state
        """
        if personality_id not in self.weekly_states:
            self.weekly_states[personality_id] = WeeklyState()
            
        state = self.weekly_states[personality_id]
        pnl = trade_result.get('pnl', 0)
        timestamp = trade_result.get('timestamp', datetime.now())
        
        # Check if we're in a new week
        if self._is_new_week(state.last_weekly_update, timestamp):
            self._reset_weekly_counters(state, timestamp)
            
        # Update weekly P&L
        state.weekly_pnl += pnl
        
        # Update Friday behavior based on current day and time
        current_day = timestamp.weekday()
        current_hour = timestamp.hour
        
        if current_day == DayOfWeek.FRIDAY.value:
            state.friday_behavior = self._determine_friday_behavior(timestamp, state)
        else:
            state.friday_behavior = FridayBehavior.NORMAL
            
        # Update Monday caution status
        if current_day == DayOfWeek.MONDAY.value:
            if current_hour < self.config.monday_caution_hours:
                state.monday_caution_active = True
            else:
                state.monday_caution_active = False
        else:
            state.monday_caution_active = False
            
        state.last_weekly_update = timestamp
        
        logger.info(f"Updated weekly state for {personality_id}: "
                   f"Weekly P&L: ${state.weekly_pnl:.2f}, Friday behavior: {state.friday_behavior.value}, "
                   f"Monday caution: {state.monday_caution_active}")
        
        return state
    
    def should_reduce_activity(self, personality_id: str, timestamp: datetime = None) -> Tuple[bool, float, str]:
        """
        Check if activity should be reduced based on weekly patterns.
        
        Args:
            personality_id: Trading personality identifier
            timestamp: Current timestamp (default: now)
            
        Returns:
            Tuple of (should_reduce, reduction_factor, reason)
        """
        if timestamp is None:
            timestamp = datetime.now()
            
        current_day = timestamp.weekday()
        current_hour = timestamp.hour
        
        # Friday afternoon reduction
        if (current_day == DayOfWeek.FRIDAY.value and 
            current_hour >= self.config.friday_afternoon_start):
            return (True, 1.0 - self.config.friday_reduction, 
                   "Friday afternoon activity reduction")
        
        # Monday morning caution
        if (current_day == DayOfWeek.MONDAY.value and 
            current_hour < self.config.monday_caution_hours):
            return (True, 1.0 - self.config.monday_morning_caution, 
                   "Monday morning caution")
        
        return False, 1.0, ""
    
    def should_flatten_positions(self, personality_id: str, current_positions: List[str], 
                                timestamp: datetime = None) -> Tuple[bool, List[str], str]:
        """
        Determine if positions should be flattened based on weekly patterns.
        
        Args:
            personality_id: Trading personality identifier
            current_positions: List of current position IDs
            timestamp: Current timestamp (default: now)
            
        Returns:
            Tuple of (should_flatten, positions_to_flatten, reason)
        """
        if timestamp is None:
            timestamp = datetime.now()
            
        if not self.config.end_of_week_flattening:
            return False, [], "End-of-week flattening disabled"
            
        current_day = timestamp.weekday()
        current_hour = timestamp.hour
        
        # Friday afternoon flattening
        if (current_day == DayOfWeek.FRIDAY.value and 
            current_hour >= self.config.friday_afternoon_start):
            
            # Use probability-based flattening
            import random
            if random.random() < self.config.flattening_probability:
                # Select portion of positions to flatten
                num_to_flatten = max(1, len(current_positions) // 2)  # At least half
                positions_to_flatten = current_positions[:num_to_flatten]
                
                return (True, positions_to_flatten, 
                       "Friday afternoon position flattening")
        
        return False, [], ""
    
    def calculate_position_size_modifier(self, personality_id: str, timestamp: datetime = None) -> float:
        """
        Calculate position size modifier based on weekly patterns.
        
        Args:
            personality_id: Trading personality identifier
            timestamp: Current timestamp (default: now)
            
        Returns:
            Position size multiplier (1.0 = normal, <1.0 = reduced size)
        """
        if timestamp is None:
            timestamp = datetime.now()
            
        current_day = timestamp.weekday()
        current_hour = timestamp.hour
        
        modifier = 1.0
        
        # Friday afternoon size reduction
        if (current_day == DayOfWeek.FRIDAY.value and 
            current_hour >= self.config.friday_afternoon_start):
            modifier *= (1.0 - self.config.position_size_reduction_friday)
            
        # Monday morning size reduction
        if (current_day == DayOfWeek.MONDAY.value and 
            current_hour < self.config.monday_caution_hours):
            modifier *= (1.0 - self.config.monday_morning_caution)
            
        # Weekend gap aversion (Sunday evening prep)
        if (current_day == DayOfWeek.SUNDAY.value and current_hour >= 18):
            modifier *= (1.0 - self.config.weekend_gap_aversion)
            
        return modifier
    
    def get_early_exit_bias(self, personality_id: str, timestamp: datetime = None) -> float:
        """
        Calculate bias toward early position exits based on weekly patterns.
        
        Args:
            personality_id: Trading personality identifier
            timestamp: Current timestamp (default: now)
            
        Returns:
            Early exit bias (0.0 = normal, >0.0 = more likely to exit early)
        """
        if timestamp is None:
            timestamp = datetime.now()
            
        current_day = timestamp.weekday()
        current_hour = timestamp.hour
        
        bias = 0.0
        
        # Friday afternoon exit bias
        if (current_day == DayOfWeek.FRIDAY.value and 
            current_hour >= self.config.friday_afternoon_start):
            bias += 0.3  # 30% more likely to exit early
            
            # Additional exit bias if we have state and are in flattening mode
            if personality_id in self.weekly_states:
                state = self.weekly_states[personality_id]
                if state.friday_behavior == FridayBehavior.FLATTENING:
                    bias += 0.5  # 50% more likely to exit early
            
        return min(bias, 0.8)  # Cap at 80% bias
    
    def _determine_friday_behavior(self, timestamp: datetime, state: WeeklyState) -> FridayBehavior:
        """Determine Friday behavior based on time and conditions"""
        current_hour = timestamp.hour
        
        if current_hour < self.config.friday_afternoon_start:
            return FridayBehavior.NORMAL
        elif current_hour < 16:  # 2-4 PM: reducing phase
            return FridayBehavior.REDUCING
        else:  # After 4 PM: flattening phase
            import random
            if random.random() < self.config.flattening_probability:
                return FridayBehavior.FLATTENING
            else:
                return FridayBehavior.REDUCING
    
    def _is_new_week(self, last_update: Optional[datetime], current_time: datetime) -> bool:
        """Check if we've moved to a new trading week (Monday start)"""
        if last_update is None:
            return True
            
        # Get Monday of current week
        days_since_monday = current_time.weekday()
        current_week_monday = current_time - timedelta(days=days_since_monday)
        current_week_monday = current_week_monday.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Get Monday of last update week
        last_days_since_monday = last_update.weekday()
        last_week_monday = last_update - timedelta(days=last_days_since_monday)
        last_week_monday = last_week_monday.replace(hour=0, minute=0, second=0, microsecond=0)
        
        return current_week_monday > last_week_monday
    
    def _reset_weekly_counters(self, state: WeeklyState, timestamp: datetime) -> None:
        """Reset weekly counters for new week"""
        # Get Monday of current week
        days_since_monday = timestamp.weekday()
        week_start = timestamp - timedelta(days=days_since_monday)
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        
        state.week_start_date = week_start
        state.weekly_pnl = 0.0
        state.positions_to_flatten = []
        state.positions_flattened_friday = []
        state.friday_behavior = FridayBehavior.NORMAL
        state.monday_caution_active = False
        
        logger.info(f"Reset weekly counters, new week starting: {week_start}")
    
    def get_weekly_info(self, personality_id: str) -> Dict:
        """Get current weekly pattern information for a personality"""
        if personality_id not in self.weekly_states:
            return {
                'weekly_pnl': 0.0,
                'friday_behavior': FridayBehavior.NORMAL.value,
                'monday_caution_active': False,
                'positions_to_flatten': [],
                'week_start_date': None,
                'activity_modifier': 1.0,
                'size_modifier': 1.0,
                'early_exit_bias': 0.0
            }
            
        state = self.weekly_states[personality_id]
        current_time = datetime.now()
        
        should_reduce, activity_modifier, _ = self.should_reduce_activity(personality_id, current_time)
        
        return {
            'weekly_pnl': state.weekly_pnl,
            'friday_behavior': state.friday_behavior.value,
            'monday_caution_active': state.monday_caution_active,
            'positions_to_flatten': state.positions_to_flatten.copy(),
            'week_start_date': state.week_start_date,
            'activity_modifier': activity_modifier,
            'size_modifier': self.calculate_position_size_modifier(personality_id, current_time),
            'early_exit_bias': self.get_early_exit_bias(personality_id, current_time)
        }
    
    def reset_weekly_state(self, personality_id: str) -> None:
        """Reset weekly state for a personality"""
        if personality_id in self.weekly_states:
            del self.weekly_states[personality_id]
            logger.info(f"Reset weekly state for personality {personality_id}")
    
    def mark_position_flattened(self, personality_id: str, position_id: str) -> None:
        """Mark a position as flattened for tracking purposes"""
        if personality_id not in self.weekly_states:
            self.weekly_states[personality_id] = WeeklyState()
            
        state = self.weekly_states[personality_id]
        if position_id not in state.positions_flattened_friday:
            state.positions_flattened_friday.append(position_id)
            
        # Remove from to-flatten list if present
        if position_id in state.positions_to_flatten:
            state.positions_to_flatten.remove(position_id)
            
        logger.info(f"Marked position {position_id} as flattened for {personality_id}")
    
    def get_behavioral_impact(self, personality_id: str, current_positions: List[str] = None, 
                             timestamp: datetime = None) -> Dict:
        """
        Get the behavioral impact of weekly patterns for decision making.
        
        Args:
            personality_id: Trading personality identifier
            current_positions: List of current position IDs
            timestamp: Current timestamp (default: now)
            
        Returns:
            Dict with behavioral modifications to apply
        """
        if timestamp is None:
            timestamp = datetime.now()
            
        if current_positions is None:
            current_positions = []
            
        should_reduce, activity_modifier, activity_reason = self.should_reduce_activity(
            personality_id, timestamp)
        should_flatten, positions_to_flatten, flatten_reason = self.should_flatten_positions(
            personality_id, current_positions, timestamp)
        
        info = self.get_weekly_info(personality_id)
        
        impact = {
            'activity_multiplier': activity_modifier,
            'position_size_multiplier': self.calculate_position_size_modifier(personality_id, timestamp),
            'early_exit_bias': self.get_early_exit_bias(personality_id, timestamp),
            'should_reduce_activity': should_reduce,
            'activity_reduction_reason': activity_reason,
            'should_flatten_positions': should_flatten,
            'positions_to_flatten': positions_to_flatten,
            'flatten_reason': flatten_reason,
            'friday_behavior': info['friday_behavior'],
            'monday_caution_active': info['monday_caution_active'],
            'skip_new_positions': False,
            'tighten_stops': False
        }
        
        # Additional behavioral modifications based on weekly state
        current_day = timestamp.weekday()
        current_hour = timestamp.hour
        
        # Skip new positions on Friday afternoon for some personalities
        if (current_day == DayOfWeek.FRIDAY.value and 
            current_hour >= self.config.friday_afternoon_start):
            impact['skip_new_positions'] = True
            
        # Tighten stops on Friday for risk management
        if current_day == DayOfWeek.FRIDAY.value:
            impact['tighten_stops'] = True
            
        return impact