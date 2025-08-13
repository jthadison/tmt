"""
Manual Adjustments Module - Implements manual adjustment patterns for human-like trading.

This module simulates human-like manual adjustments including preferences for round numbers,
psychological levels, second-guessing behavior, and occasional manual-looking modifications.
"""

import logging
import random
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class AdjustmentType(Enum):
    """Types of manual adjustments"""
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    POSITION_SIZE = "position_size"
    ENTRY_PRICE = "entry_price"


class TriggerType(Enum):
    """Types of adjustment triggers"""
    ROUND_NUMBER = "round_number"
    PSYCHOLOGICAL_LEVEL = "psychological_level"
    SECOND_GUESSING = "second_guessing"
    ERROR_CORRECTION = "error_correction"
    MARKET_CONDITION = "market_condition"


@dataclass
class ManualAdjustment:
    """Represents a manual adjustment to be made"""
    id: str
    position_id: str
    adjustment_type: AdjustmentType
    original_value: float
    new_value: float
    reasoning: str
    trigger_type: TriggerType
    scheduled_for: datetime
    created_at: datetime
    executed: bool = False


@dataclass
class ManualAdjustmentConfig:
    """Configuration for manual adjustment patterns"""
    round_number_preference: float = 0.3        # 0-1, attraction to round numbers
    adjustment_frequency: float = 0.15          # How often to make adjustments per day
    psychological_levels: bool = True           # Prefer .00, .50 levels
    error_rate: float = 0.02                   # Occasional "typos" or mistakes
    second_guessing: float = 0.1               # Tendency to modify orders
    max_adjustments_per_day: int = 5           # Maximum adjustments per day
    min_time_between_adjustments: int = 30     # Minutes between adjustments
    round_number_threshold: float = 3.0        # Pips within round number to adjust


@dataclass
class AdjustmentState:
    """Current adjustment state for a trading personality"""
    adjustments_made_today: int = 0
    last_adjustment_time: Optional[datetime] = None
    pending_adjustments: List[ManualAdjustment] = None
    adjustment_history: List[ManualAdjustment] = None
    daily_reset_date: Optional[datetime] = None
    
    def __post_init__(self):
        if self.pending_adjustments is None:
            self.pending_adjustments = []
        if self.adjustment_history is None:
            self.adjustment_history = []


class ManualAdjustments:
    """
    Manages manual adjustment behavioral patterns for human-like trading.
    
    Implements manual adjustment patterns including:
    - Round number preference and psychological level attraction
    - Second-guessing and order modifications
    - Occasional manual-looking adjustments
    - Error simulation and correction behaviors
    - Realistic timing and frequency of adjustments
    """
    
    def __init__(self, config: ManualAdjustmentConfig = None):
        self.config = config or ManualAdjustmentConfig()
        self.adjustment_states: Dict[str, AdjustmentState] = {}
        
    def generate_adjustments(self, personality_id: str, signal: Dict, 
                           current_positions: List[Dict] = None) -> List[ManualAdjustment]:
        """
        Generate potential manual adjustments for a trading signal.
        
        Args:
            personality_id: Trading personality identifier
            signal: Trading signal with 'stop_loss', 'take_profit', 'size', etc.
            current_positions: List of current positions
            
        Returns:
            List of ManualAdjustment objects
        """
        if current_positions is None:
            current_positions = []
            
        adjustments = []
        current_time = datetime.now()
        
        # Initialize state if needed
        if personality_id not in self.adjustment_states:
            self.adjustment_states[personality_id] = AdjustmentState()
            
        state = self.adjustment_states[personality_id]
        
        # Check if new day (reset daily counters)
        if self._is_new_day(state.daily_reset_date, current_time):
            self._reset_daily_counters(state, current_time)
            
        # Check if we can make more adjustments today
        if state.adjustments_made_today >= self.config.max_adjustments_per_day:
            return []
            
        # Check minimum time between adjustments
        if (state.last_adjustment_time and 
            (current_time - state.last_adjustment_time).total_seconds() < 
            self.config.min_time_between_adjustments * 60):
            return []
            
        # Generate round number adjustments
        if random.random() < self.config.round_number_preference:
            round_adjustment = self._generate_round_number_adjustment(signal, current_time)
            if round_adjustment:
                adjustments.append(round_adjustment)
                
        # Generate second-guessing adjustments
        if random.random() < self.config.second_guessing:
            second_guess_adjustment = self._generate_second_guessing_adjustment(signal, current_time)
            if second_guess_adjustment:
                adjustments.append(second_guess_adjustment)
                
        # Generate psychological level adjustments
        if self.config.psychological_levels and random.random() < 0.2:
            psych_adjustment = self._generate_psychological_level_adjustment(signal, current_time)
            if psych_adjustment:
                adjustments.append(psych_adjustment)
                
        # Generate error corrections (rare)
        if random.random() < self.config.error_rate:
            error_adjustment = self._generate_error_correction(signal, current_time)
            if error_adjustment:
                adjustments.append(error_adjustment)
                
        # Limit to reasonable number per signal
        return adjustments[:2]  # Maximum 2 adjustments per signal
    
    def _generate_round_number_adjustment(self, signal: Dict, current_time: datetime) -> Optional[ManualAdjustment]:
        """Generate adjustment to move levels to round numbers"""
        stop_loss = signal.get('stop_loss')
        take_profit = signal.get('take_profit')
        
        # Check stop loss for round number adjustment
        if stop_loss and not self._is_round_number(stop_loss):
            rounded_sl = self._round_to_nearest_level(stop_loss, 10)  # Round to nearest 10 pips
            if abs(rounded_sl - stop_loss) <= self.config.round_number_threshold:
                return ManualAdjustment(
                    id=f"adj_{int(current_time.timestamp())}",
                    position_id=signal.get('position_id', 'new_position'),
                    adjustment_type=AdjustmentType.STOP_LOSS,
                    original_value=stop_loss,
                    new_value=rounded_sl,
                    reasoning=f"Adjusted stop loss to round number {rounded_sl}",
                    trigger_type=TriggerType.ROUND_NUMBER,
                    scheduled_for=current_time + timedelta(seconds=random.randint(5, 30)),
                    created_at=current_time
                )
                
        # Check take profit for round number adjustment
        if take_profit and not self._is_round_number(take_profit):
            rounded_tp = self._round_to_nearest_level(take_profit, 10)
            if abs(rounded_tp - take_profit) <= self.config.round_number_threshold:
                return ManualAdjustment(
                    id=f"adj_{int(current_time.timestamp())}_tp",
                    position_id=signal.get('position_id', 'new_position'),
                    adjustment_type=AdjustmentType.TAKE_PROFIT,
                    original_value=take_profit,
                    new_value=rounded_tp,
                    reasoning=f"Adjusted take profit to round number {rounded_tp}",
                    trigger_type=TriggerType.ROUND_NUMBER,
                    scheduled_for=current_time + timedelta(seconds=random.randint(5, 30)),
                    created_at=current_time
                )
        
        return None
    
    def _generate_second_guessing_adjustment(self, signal: Dict, current_time: datetime) -> Optional[ManualAdjustment]:
        """Generate second-guessing style adjustments"""
        take_profit = signal.get('take_profit')
        
        if take_profit:
            # Randomly adjust take profit by small amount (second thoughts)
            adjustment_factor = random.uniform(0.95, 1.05)  # ±5% adjustment
            new_tp = take_profit * adjustment_factor
            
            reasons = [
                "Second thoughts on profit target",
                "Market conditions changed, adjusting target",
                "Being more conservative with target",
                "Extending target for better R:R"
            ]
            
            return ManualAdjustment(
                id=f"adj_{int(current_time.timestamp())}_sg",
                position_id=signal.get('position_id', 'new_position'),
                adjustment_type=AdjustmentType.TAKE_PROFIT,
                original_value=take_profit,
                new_value=new_tp,
                reasoning=random.choice(reasons),
                trigger_type=TriggerType.SECOND_GUESSING,
                scheduled_for=current_time + timedelta(minutes=random.randint(2, 10)),
                created_at=current_time
            )
        
        return None
    
    def _generate_psychological_level_adjustment(self, signal: Dict, current_time: datetime) -> Optional[ManualAdjustment]:
        """Generate adjustments to psychological levels (.00, .50)"""
        stop_loss = signal.get('stop_loss')
        
        if stop_loss:
            # Find nearest .00 or .50 level
            nearest_psych = self._find_nearest_psychological_level(stop_loss)
            if abs(nearest_psych - stop_loss) <= self.config.round_number_threshold:
                return ManualAdjustment(
                    id=f"adj_{int(current_time.timestamp())}_psych",
                    position_id=signal.get('position_id', 'new_position'),
                    adjustment_type=AdjustmentType.STOP_LOSS,
                    original_value=stop_loss,
                    new_value=nearest_psych,
                    reasoning=f"Moved stop to psychological level {nearest_psych:.2f}",
                    trigger_type=TriggerType.PSYCHOLOGICAL_LEVEL,
                    scheduled_for=current_time + timedelta(seconds=random.randint(10, 60)),
                    created_at=current_time
                )
        
        return None
    
    def _generate_error_correction(self, signal: Dict, current_time: datetime) -> Optional[ManualAdjustment]:
        """Generate error correction adjustments (simulating typos)"""
        position_size = signal.get('size', signal.get('position_size'))
        
        if position_size:
            # Simulate "typo" correction - small size adjustment
            error_factor = random.choice([0.98, 1.02])  # ±2% "error"
            corrected_size = position_size * error_factor
            
            return ManualAdjustment(
                id=f"adj_{int(current_time.timestamp())}_err",
                position_id=signal.get('position_id', 'new_position'),
                adjustment_type=AdjustmentType.POSITION_SIZE,
                original_value=position_size,
                new_value=corrected_size,
                reasoning="Correcting position size (typo)",
                trigger_type=TriggerType.ERROR_CORRECTION,
                scheduled_for=current_time + timedelta(seconds=random.randint(2, 15)),
                created_at=current_time
            )
        
        return None
    
    def _is_round_number(self, value: float, precision: int = 10) -> bool:
        """Check if value is a round number"""
        return (value * precision) % precision == 0
    
    def _round_to_nearest_level(self, value: float, level: int) -> float:
        """Round value to nearest level (e.g., nearest 10 pips)"""
        return round(value * level) / level
    
    def _find_nearest_psychological_level(self, value: float) -> float:
        """Find nearest psychological level (.00 or .50)"""
        integer_part = int(value)
        decimal_part = value - integer_part
        
        if decimal_part < 0.25:
            return float(integer_part)
        elif decimal_part < 0.75:
            return integer_part + 0.5
        else:
            return float(integer_part + 1)
    
    def schedule_adjustment(self, personality_id: str, adjustment: ManualAdjustment) -> None:
        """Schedule an adjustment for execution"""
        if personality_id not in self.adjustment_states:
            self.adjustment_states[personality_id] = AdjustmentState()
            
        state = self.adjustment_states[personality_id]
        state.pending_adjustments.append(adjustment)
        
        logger.info(f"Scheduled adjustment {adjustment.id} for {personality_id}: "
                   f"{adjustment.adjustment_type.value} {adjustment.original_value} -> {adjustment.new_value}")
    
    def get_due_adjustments(self, personality_id: str, current_time: datetime = None) -> List[ManualAdjustment]:
        """Get adjustments that are due for execution"""
        if current_time is None:
            current_time = datetime.now()
            
        if personality_id not in self.adjustment_states:
            return []
            
        state = self.adjustment_states[personality_id]
        due_adjustments = []
        
        for adjustment in state.pending_adjustments[:]:
            if current_time >= adjustment.scheduled_for and not adjustment.executed:
                due_adjustments.append(adjustment)
                
        return due_adjustments
    
    def execute_adjustment(self, personality_id: str, adjustment_id: str) -> bool:
        """Mark adjustment as executed"""
        if personality_id not in self.adjustment_states:
            return False
            
        state = self.adjustment_states[personality_id]
        
        for adjustment in state.pending_adjustments:
            if adjustment.id == adjustment_id:
                adjustment.executed = True
                state.adjustment_history.append(adjustment)
                state.adjustments_made_today += 1
                state.last_adjustment_time = datetime.now()
                
                # Remove from pending
                state.pending_adjustments.remove(adjustment)
                
                logger.info(f"Executed adjustment {adjustment_id} for {personality_id}")
                return True
                
        return False
    
    def _is_new_day(self, last_date: Optional[datetime], current_time: datetime) -> bool:
        """Check if it's a new trading day"""
        if last_date is None:
            return True
        return last_date.date() != current_time.date()
    
    def _reset_daily_counters(self, state: AdjustmentState, current_time: datetime) -> None:
        """Reset daily adjustment counters"""
        state.adjustments_made_today = 0
        state.daily_reset_date = current_time
        
        # Clear old pending adjustments (older than 24 hours)
        cutoff_time = current_time - timedelta(hours=24)
        state.pending_adjustments = [
            adj for adj in state.pending_adjustments 
            if adj.created_at > cutoff_time
        ]
        
        logger.debug(f"Reset daily adjustment counters")
    
    def get_adjustment_info(self, personality_id: str) -> Dict:
        """Get adjustment information for a personality"""
        if personality_id not in self.adjustment_states:
            return {
                'adjustments_made_today': 0,
                'pending_adjustments': 0,
                'last_adjustment_time': None,
                'adjustment_frequency': self.config.adjustment_frequency,
                'round_number_preference': self.config.round_number_preference
            }
            
        state = self.adjustment_states[personality_id]
        
        return {
            'adjustments_made_today': state.adjustments_made_today,
            'pending_adjustments': len(state.pending_adjustments),
            'last_adjustment_time': state.last_adjustment_time,
            'adjustment_frequency': self.config.adjustment_frequency,
            'round_number_preference': self.config.round_number_preference,
            'history_count': len(state.adjustment_history)
        }
    
    def reset_adjustment_state(self, personality_id: str) -> None:
        """Reset adjustment state for a personality"""
        if personality_id in self.adjustment_states:
            del self.adjustment_states[personality_id]
            logger.info(f"Reset adjustment state for personality {personality_id}")
    
    def get_behavioral_impact(self, personality_id: str, signal: Dict = None) -> Dict:
        """
        Get behavioral impact of manual adjustments.
        
        Returns:
            Dict with behavioral modifications and adjustment suggestions
        """
        if signal is None:
            signal = {}
            
        adjustments = self.generate_adjustments(personality_id, signal)
        info = self.get_adjustment_info(personality_id)
        
        impact = {
            'suggested_adjustments': [
                {
                    'type': adj.adjustment_type.value,
                    'original': adj.original_value,
                    'new': adj.new_value,
                    'reason': adj.reasoning,
                    'trigger': adj.trigger_type.value
                }
                for adj in adjustments
            ],
            'adjustment_tendency': info['round_number_preference'],
            'daily_adjustments_made': info['adjustments_made_today'],
            'pending_adjustments': info['pending_adjustments'],
            'order_modification_bias': self.config.second_guessing,
            'precision_preference': 'round_numbers' if self.config.psychological_levels else 'exact'
        }
        
        return impact