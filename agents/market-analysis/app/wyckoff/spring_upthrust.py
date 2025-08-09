"""
Spring and Upthrust Detection Module

Implements specialized detection for key Wyckoff patterns:
- Springs: Price breaks below support but recovers with volume (bullish)
- Upthrusts: Price breaks above resistance but fails with volume (bearish)
- False breakout detection using volume profile analysis
- Stop hunt identification for institutional order flow
"""

from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from dataclasses import dataclass
import pandas as pd
import numpy as np
from datetime import datetime


@dataclass
class SpringUpthrustResult:
    """Result from spring/upthrust detection"""
    pattern_type: str  # spring, upthrust, false_breakout, stop_hunt
    strength: Decimal  # 0-100 strength score
    entry_level: float
    stop_level: float
    target_level: float
    volume_confirmation: Decimal
    detection_time: datetime
    key_level: float  # The support/resistance level that was tested


class SpringUpthrustDetector:
    """Detects spring and upthrust patterns with volume confirmation"""
    
    def __init__(self, 
                 min_volume_ratio: float = 1.2,
                 recovery_threshold: float = 0.7,
                 lookback_period: int = 20):
        self.min_volume_ratio = min_volume_ratio
        self.recovery_threshold = recovery_threshold
        self.lookback_period = lookback_period
    
    def detect_springs(self, 
                      price_data: pd.DataFrame, 
                      volume_data: pd.Series,
                      support_level: float) -> List[SpringUpthrustResult]:
        """
        Detect spring patterns: price breaks support but recovers with volume
        
        Spring characteristics:
        - Price breaks below established support level
        - Immediately recovers above support (same candle or next)
        - Volume expansion during the spring action
        - Recovery strength indicates underlying demand
        """
        springs = []
        
        if len(price_data) < 5:
            return springs
        
        avg_volume = volume_data.mean()
        
        for i in range(1, len(price_data)):
            current = price_data.iloc[i]
            previous = price_data.iloc[i-1] if i > 0 else current
            volume = volume_data.iloc[i]
            
            # Check for spring conditions
            spring_detected = self._is_spring_pattern(
                current, previous, volume, support_level, avg_volume
            )
            
            if spring_detected:
                # Calculate spring strength and characteristics
                strength_data = self._calculate_spring_strength(
                    current, volume, support_level, avg_volume
                )
                
                # Generate trading levels
                entry_level = current['close']
                stop_level = support_level * 0.9985  # Slightly below support
                target_level = self._calculate_spring_target(
                    price_data.iloc[:i+1], support_level
                )
                
                spring_result = SpringUpthrustResult(
                    pattern_type='spring',
                    strength=strength_data['strength'],
                    entry_level=entry_level,
                    stop_level=stop_level,
                    target_level=target_level,
                    volume_confirmation=strength_data['volume_confirmation'],
                    detection_time=datetime.now(),
                    key_level=support_level
                )
                
                springs.append(spring_result)
        
        return springs
    
    def detect_upthrusts(self,
                        price_data: pd.DataFrame,
                        volume_data: pd.Series, 
                        resistance_level: float) -> List[SpringUpthrustResult]:
        """
        Detect upthrust patterns: price breaks resistance but fails with volume
        
        Upthrust characteristics:
        - Price breaks above established resistance level
        - Fails to hold above resistance (closes below)
        - Volume expansion during the upthrust action
        - Failure strength indicates supply/selling pressure
        """
        upthrusts = []
        
        if len(price_data) < 5:
            return upthrusts
        
        avg_volume = volume_data.mean()
        
        for i in range(1, len(price_data)):
            current = price_data.iloc[i]
            previous = price_data.iloc[i-1] if i > 0 else current
            volume = volume_data.iloc[i]
            
            # Check for upthrust conditions
            upthrust_detected = self._is_upthrust_pattern(
                current, previous, volume, resistance_level, avg_volume
            )
            
            if upthrust_detected:
                # Calculate upthrust strength and characteristics
                strength_data = self._calculate_upthrust_strength(
                    current, volume, resistance_level, avg_volume
                )
                
                # Generate trading levels
                entry_level = current['close']
                stop_level = resistance_level * 1.0015  # Slightly above resistance
                target_level = self._calculate_upthrust_target(
                    price_data.iloc[:i+1], resistance_level
                )
                
                upthrust_result = SpringUpthrustResult(
                    pattern_type='upthrust',
                    strength=strength_data['strength'], 
                    entry_level=entry_level,
                    stop_level=stop_level,
                    target_level=target_level,
                    volume_confirmation=strength_data['volume_confirmation'],
                    detection_time=datetime.now(),
                    key_level=resistance_level
                )
                
                upthrusts.append(upthrust_result)
        
        return upthrusts
    
    def detect_false_breakouts(self,
                              price_data: pd.DataFrame,
                              volume_data: pd.Series,
                              key_levels: Dict[str, float]) -> List[SpringUpthrustResult]:
        """
        Detect false breakout patterns using volume profile analysis
        
        False breakout characteristics:
        - Price breaks key level but lacks volume conviction
        - Quick reversal back inside the range
        - Lower volume on breakout vs. reversal
        """
        false_breakouts = []
        
        support_level = key_levels.get('support')
        resistance_level = key_levels.get('resistance')
        
        if support_level:
            # Check for false breakdown
            false_breakdowns = self._detect_false_breakdowns(
                price_data, volume_data, support_level
            )
            false_breakouts.extend(false_breakdowns)
        
        if resistance_level:
            # Check for false breakup
            false_breakups = self._detect_false_breakups(
                price_data, volume_data, resistance_level
            )
            false_breakouts.extend(false_breakups)
        
        return false_breakouts
    
    def identify_stop_hunts(self,
                           price_data: pd.DataFrame,
                           volume_data: pd.Series,
                           key_levels: Dict[str, float]) -> List[SpringUpthrustResult]:
        """
        Identify stop hunt patterns where institutional players trigger stops
        
        Stop hunt characteristics:
        - Quick spike through key level
        - Immediate reversal with high volume
        - Minimal time spent beyond the key level
        - Strong directional move after reversal
        """
        stop_hunts = []
        
        for level_name, level_value in key_levels.items():
            if level_value is None:
                continue
            
            hunts = self._detect_stop_hunt_at_level(
                price_data, volume_data, level_value, level_name
            )
            stop_hunts.extend(hunts)
        
        return stop_hunts
    
    def _is_spring_pattern(self,
                          current: pd.Series,
                          previous: pd.Series, 
                          volume: float,
                          support_level: float,
                          avg_volume: float) -> bool:
        """Check if current candle represents a spring pattern"""
        
        # Price must break below support 
        breaks_support = current['low'] < support_level
        
        # Must recover above support (close above support)
        recovers_above = current['close'] > support_level
        
        # Previous close should be near or above support
        previous_valid = previous['close'] >= support_level * 0.999
        
        # Volume should be higher than average
        volume_confirmation = volume > avg_volume * self.min_volume_ratio
        
        # Recovery strength (how much of the candle recovered)
        if current['high'] != current['low']:
            recovery_ratio = (current['close'] - current['low']) / (current['high'] - current['low'])
            strong_recovery = recovery_ratio >= self.recovery_threshold
        else:
            strong_recovery = True  # Doji at support
        
        return (breaks_support and recovers_above and 
                previous_valid and volume_confirmation and strong_recovery)
    
    def _is_upthrust_pattern(self,
                            current: pd.Series,
                            previous: pd.Series,
                            volume: float, 
                            resistance_level: float,
                            avg_volume: float) -> bool:
        """Check if current candle represents an upthrust pattern"""
        
        # Price must break above resistance
        breaks_resistance = current['high'] > resistance_level
        
        # Must fail to hold above resistance (close below resistance)
        fails_to_hold = current['close'] < resistance_level
        
        # Previous close should be near or below resistance
        previous_valid = previous['close'] <= resistance_level * 1.001
        
        # Volume should be higher than average
        volume_confirmation = volume > avg_volume * self.min_volume_ratio
        
        # Failure strength (how much of the upper wick failed)
        if current['high'] != current['low']:
            failure_ratio = (current['high'] - current['close']) / (current['high'] - current['low'])
            strong_failure = failure_ratio >= self.recovery_threshold
        else:
            strong_failure = True  # Doji at resistance
        
        return (breaks_resistance and fails_to_hold and 
                previous_valid and volume_confirmation and strong_failure)
    
    def _calculate_spring_strength(self,
                                  candle: pd.Series,
                                  volume: float,
                                  support_level: float,
                                  avg_volume: float) -> Dict:
        """Calculate spring pattern strength based on multiple factors"""
        
        # Recovery strength (how well price recovered from the low)
        if candle['high'] != candle['low']:
            recovery_ratio = (candle['close'] - candle['low']) / (candle['high'] - candle['low'])
        else:
            recovery_ratio = 1.0
        
        # Volume confirmation strength
        volume_ratio = volume / avg_volume
        volume_strength = min(1.0, (volume_ratio - 1.0) / 2.0)  # Normalize to 0-1
        
        # Penetration depth (how far below support)
        penetration_depth = abs(candle['low'] - support_level) / support_level
        penetration_strength = min(1.0, penetration_depth / 0.002)  # 0.2% max
        
        # Overall strength calculation (0-100)
        strength_score = (
            recovery_ratio * 40 +          # 40% weight on recovery
            volume_strength * 35 +         # 35% weight on volume
            penetration_strength * 25      # 25% weight on penetration
        )
        
        return {
            'strength': Decimal(str(round(strength_score, 2))),
            'volume_confirmation': Decimal(str(round(volume_strength * 100, 2))),
            'recovery_ratio': recovery_ratio,
            'volume_ratio': volume_ratio,
            'penetration_depth': penetration_depth
        }
    
    def _calculate_upthrust_strength(self,
                                    candle: pd.Series,
                                    volume: float,
                                    resistance_level: float,
                                    avg_volume: float) -> Dict:
        """Calculate upthrust pattern strength based on multiple factors"""
        
        # Failure strength (how much of the breakout failed)
        if candle['high'] != candle['low']:
            failure_ratio = (candle['high'] - candle['close']) / (candle['high'] - candle['low'])
        else:
            failure_ratio = 1.0
        
        # Volume confirmation strength
        volume_ratio = volume / avg_volume
        volume_strength = min(1.0, (volume_ratio - 1.0) / 2.0)
        
        # Penetration depth (how far above resistance)
        penetration_depth = abs(candle['high'] - resistance_level) / resistance_level
        penetration_strength = min(1.0, penetration_depth / 0.002)  # 0.2% max
        
        # Overall strength calculation (0-100)
        strength_score = (
            failure_ratio * 40 +           # 40% weight on failure
            volume_strength * 35 +         # 35% weight on volume  
            penetration_strength * 25      # 25% weight on penetration
        )
        
        return {
            'strength': Decimal(str(round(strength_score, 2))),
            'volume_confirmation': Decimal(str(round(volume_strength * 100, 2))),
            'failure_ratio': failure_ratio,
            'volume_ratio': volume_ratio,
            'penetration_depth': penetration_depth
        }
    
    def _calculate_spring_target(self, price_data: pd.DataFrame, support_level: float) -> float:
        """Calculate target level for spring pattern"""
        # Target is typically the recent resistance or swing high
        lookback = min(self.lookback_period, len(price_data))
        recent_high = price_data['high'].iloc[-lookback:].max()
        
        # If recent high is too close to support, extend target
        if recent_high < support_level * 1.01:
            recent_high = support_level * 1.02
        
        return recent_high
    
    def _calculate_upthrust_target(self, price_data: pd.DataFrame, resistance_level: float) -> float:
        """Calculate target level for upthrust pattern"""
        # Target is typically the recent support or swing low
        lookback = min(self.lookback_period, len(price_data))
        recent_low = price_data['low'].iloc[-lookback:].min()
        
        # If recent low is too close to resistance, extend target
        if recent_low > resistance_level * 0.99:
            recent_low = resistance_level * 0.98
        
        return recent_low
    
    def _detect_false_breakdowns(self,
                                price_data: pd.DataFrame,
                                volume_data: pd.Series,
                                support_level: float) -> List[SpringUpthrustResult]:
        """Detect false breakdown patterns below support"""
        false_breakdowns = []
        avg_volume = volume_data.mean()
        
        for i in range(2, len(price_data)):
            current = price_data.iloc[i]
            previous = price_data.iloc[i-1]
            volume = volume_data.iloc[i]
            
            # Check for breakdown with weak volume
            if (current['low'] < support_level and
                current['close'] < support_level and
                volume < avg_volume * 0.8):  # Weak volume
                
                # Check for reversal in next few candles
                reversal_found = False
                for j in range(i+1, min(i+4, len(price_data))):
                    if price_data.iloc[j]['close'] > support_level:
                        reversal_found = True
                        break
                
                if reversal_found:
                    strength = self._calculate_false_breakout_strength(
                        current, volume, support_level, avg_volume, 'breakdown'
                    )
                    
                    result = SpringUpthrustResult(
                        pattern_type='false_breakout',
                        strength=strength['strength'],
                        entry_level=current['close'],
                        stop_level=support_level * 0.995,
                        target_level=support_level * 1.02,
                        volume_confirmation=strength['volume_confirmation'],
                        detection_time=datetime.now(),
                        key_level=support_level
                    )
                    
                    false_breakdowns.append(result)
        
        return false_breakdowns
    
    def _detect_false_breakups(self,
                              price_data: pd.DataFrame,
                              volume_data: pd.Series,
                              resistance_level: float) -> List[SpringUpthrustResult]:
        """Detect false breakup patterns above resistance"""
        false_breakups = []
        avg_volume = volume_data.mean()
        
        for i in range(2, len(price_data)):
            current = price_data.iloc[i]
            previous = price_data.iloc[i-1]
            volume = volume_data.iloc[i]
            
            # Check for breakup with weak volume
            if (current['high'] > resistance_level and
                current['close'] > resistance_level and
                volume < avg_volume * 0.8):  # Weak volume
                
                # Check for reversal in next few candles
                reversal_found = False
                for j in range(i+1, min(i+4, len(price_data))):
                    if price_data.iloc[j]['close'] < resistance_level:
                        reversal_found = True
                        break
                
                if reversal_found:
                    strength = self._calculate_false_breakout_strength(
                        current, volume, resistance_level, avg_volume, 'breakup'
                    )
                    
                    result = SpringUpthrustResult(
                        pattern_type='false_breakout',
                        strength=strength['strength'],
                        entry_level=current['close'],
                        stop_level=resistance_level * 1.005,
                        target_level=resistance_level * 0.98,
                        volume_confirmation=strength['volume_confirmation'],
                        detection_time=datetime.now(),
                        key_level=resistance_level
                    )
                    
                    false_breakups.append(result)
        
        return false_breakups
    
    def _detect_stop_hunt_at_level(self,
                                  price_data: pd.DataFrame,
                                  volume_data: pd.Series,
                                  level_value: float,
                                  level_name: str) -> List[SpringUpthrustResult]:
        """Detect stop hunt patterns at a specific level"""
        stop_hunts = []
        avg_volume = volume_data.mean()
        
        for i in range(1, len(price_data) - 1):
            current = price_data.iloc[i]
            next_candle = price_data.iloc[i+1]
            volume = volume_data.iloc[i]
            
            # Check for quick spike through level with high volume
            if ('support' in level_name.lower() and
                current['low'] < level_value and
                current['close'] > level_value and
                volume > avg_volume * 1.5):
                
                # Check for strong move up after the hunt
                if next_candle['close'] > current['close']:
                    strength = self._calculate_stop_hunt_strength(
                        current, next_candle, volume, level_value, avg_volume
                    )
                    
                    result = SpringUpthrustResult(
                        pattern_type='stop_hunt',
                        strength=strength['strength'],
                        entry_level=current['close'],
                        stop_level=level_value * 0.995,
                        target_level=level_value * 1.03,
                        volume_confirmation=strength['volume_confirmation'],
                        detection_time=datetime.now(),
                        key_level=level_value
                    )
                    
                    stop_hunts.append(result)
            
            elif ('resistance' in level_name.lower() and
                  current['high'] > level_value and
                  current['close'] < level_value and
                  volume > avg_volume * 1.5):
                
                # Check for strong move down after the hunt
                if next_candle['close'] < current['close']:
                    strength = self._calculate_stop_hunt_strength(
                        current, next_candle, volume, level_value, avg_volume
                    )
                    
                    result = SpringUpthrustResult(
                        pattern_type='stop_hunt',
                        strength=strength['strength'],
                        entry_level=current['close'],
                        stop_level=level_value * 1.005,
                        target_level=level_value * 0.97,
                        volume_confirmation=strength['volume_confirmation'],
                        detection_time=datetime.now(),
                        key_level=level_value
                    )
                    
                    stop_hunts.append(result)
        
        return stop_hunts
    
    def _calculate_false_breakout_strength(self,
                                          candle: pd.Series,
                                          volume: float,
                                          level: float,
                                          avg_volume: float,
                                          breakout_type: str) -> Dict:
        """Calculate false breakout pattern strength"""
        
        # Weakness in volume (lower is better for false breakouts)
        volume_ratio = volume / avg_volume
        volume_weakness = max(0, (1.5 - volume_ratio) / 1.5)  # Higher score for lower volume
        
        # Penetration analysis
        if breakout_type == 'breakdown':
            penetration = abs(candle['low'] - level) / level
        else:  # breakup
            penetration = abs(candle['high'] - level) / level
        
        penetration_strength = min(1.0, penetration / 0.003)  # 0.3% max
        
        # Overall strength
        strength_score = (
            volume_weakness * 60 +         # 60% weight on volume weakness
            penetration_strength * 40      # 40% weight on penetration
        )
        
        return {
            'strength': Decimal(str(round(strength_score, 2))),
            'volume_confirmation': Decimal(str(round(volume_weakness * 100, 2))),
            'volume_ratio': volume_ratio,
            'penetration': penetration
        }
    
    def _calculate_stop_hunt_strength(self,
                                     hunt_candle: pd.Series,
                                     follow_candle: pd.Series,
                                     volume: float,
                                     level: float,
                                     avg_volume: float) -> Dict:
        """Calculate stop hunt pattern strength"""
        
        # Volume spike strength
        volume_ratio = volume / avg_volume
        volume_strength = min(1.0, (volume_ratio - 1.0) / 2.0)
        
        # Follow-through strength (how strong was the move after hunt)
        hunt_close = hunt_candle['close']
        follow_close = follow_candle['close']
        
        if hunt_close != 0:
            follow_strength = abs(follow_close - hunt_close) / hunt_close
        else:
            follow_strength = 0
        
        follow_strength = min(1.0, follow_strength / 0.01)  # 1% max
        
        # Speed of reversal (quick spike and reversal)
        if hunt_candle['high'] != hunt_candle['low']:
            spike_ratio = abs(hunt_candle['high'] - hunt_candle['low']) / hunt_candle['close']
        else:
            spike_ratio = 0
        
        spike_strength = min(1.0, spike_ratio / 0.005)  # 0.5% max
        
        # Overall strength
        strength_score = (
            volume_strength * 40 +         # 40% weight on volume
            follow_strength * 35 +         # 35% weight on follow-through
            spike_strength * 25            # 25% weight on spike characteristics
        )
        
        return {
            'strength': Decimal(str(round(strength_score, 2))),
            'volume_confirmation': Decimal(str(round(volume_strength * 100, 2))),
            'volume_ratio': volume_ratio,
            'follow_strength': follow_strength,
            'spike_strength': spike_strength
        }