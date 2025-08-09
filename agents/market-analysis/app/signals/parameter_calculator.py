"""
Signal Parameter Calculator

Calculates precise entry, stop loss, and take profit parameters for different
Wyckoff pattern types with dynamic risk-reward optimization.
"""

from typing import Dict, List, Tuple, Optional
import pandas as pd
import numpy as np
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta
import logging

from .signal_metadata import EntryConfirmation

logger = logging.getLogger(__name__)


class SignalParameterCalculator:
    """
    Calculates precise trading parameters based on Wyckoff patterns and market context.
    
    Provides pattern-specific calculation methods for:
    - Entry prices with confirmation requirements
    - Stop loss levels based on pattern invalidation
    - Take profit targets using measured moves
    - Risk-reward optimization
    """
    
    def __init__(self,
                 atr_multiplier_entry: float = 0.5,
                 atr_multiplier_stop: float = 1.0,
                 min_risk_reward: float = 2.0,
                 max_risk_reward: float = 10.0):
        """
        Initialize parameter calculator.
        
        Args:
            atr_multiplier_entry: ATR multiplier for entry buffer
            atr_multiplier_stop: ATR multiplier for stop buffer  
            min_risk_reward: Minimum required risk-reward ratio
            max_risk_reward: Maximum risk-reward ratio for capping
        """
        self.atr_multiplier_entry = atr_multiplier_entry
        self.atr_multiplier_stop = atr_multiplier_stop
        self.min_risk_reward = min_risk_reward
        self.max_risk_reward = max_risk_reward
    
    def calculate_signal_parameters(self,
                                   pattern: Dict,
                                   price_data: pd.DataFrame,
                                   volume_data: pd.Series,
                                   market_context: Dict) -> Dict:
        """
        Calculate comprehensive signal parameters based on pattern type.
        
        Args:
            pattern: Detected Wyckoff pattern data
            price_data: OHLC price data
            volume_data: Volume data
            market_context: Market context information
            
        Returns:
            Dict with calculated parameters and metadata
        """
        pattern_type = pattern.get('type', 'unknown')
        
        # Calculate ATR for dynamic sizing
        atr = self._calculate_atr(price_data)
        current_price = price_data['close'].iloc[-1]
        
        # Pattern-specific parameter calculation
        if pattern_type == 'accumulation':
            params = self._calculate_accumulation_parameters(pattern, price_data, atr)
        elif pattern_type == 'spring':
            params = self._calculate_spring_parameters(pattern, price_data, atr)
        elif pattern_type == 'distribution':
            params = self._calculate_distribution_parameters(pattern, price_data, atr)
        elif pattern_type == 'upthrust':
            params = self._calculate_upthrust_parameters(pattern, price_data, atr)
        elif pattern_type == 'sign_of_strength':
            params = self._calculate_sos_parameters(pattern, price_data, atr)
        elif pattern_type == 'sign_of_weakness':
            params = self._calculate_sow_parameters(pattern, price_data, atr)
        elif pattern_type == 'backup':
            params = self._calculate_backup_parameters(pattern, price_data, atr)
        elif pattern_type == 'test':
            params = self._calculate_test_parameters(pattern, price_data, atr)
        else:
            # Generic calculation for unknown patterns
            params = self._calculate_generic_parameters(pattern, price_data, atr)
        
        # Enhance parameters with market context
        enhanced_params = self._enhance_with_market_context(params, market_context, atr)
        
        # Calculate entry confirmation requirements
        entry_confirmation = self._calculate_entry_confirmation(
            pattern, enhanced_params, volume_data, atr
        )
        
        # Validate and optimize risk-reward ratio
        optimized_params = self._optimize_risk_reward(enhanced_params, pattern, price_data)
        
        # Add timing estimates
        timing_estimates = self._estimate_timing_parameters(pattern, market_context)
        
        return {
            **optimized_params,
            'entry_confirmation': entry_confirmation,
            'timing_estimates': timing_estimates,
            'atr_current': float(atr),
            'calculation_metadata': {
                'pattern_type': pattern_type,
                'calculation_time': datetime.now(),
                'price_at_calculation': float(current_price),
                'market_context_used': market_context,
                'optimization_applied': True
            }
        }
    
    def _calculate_spring_parameters(self, pattern: Dict, price_data: pd.DataFrame, atr: float) -> Dict:
        """Calculate parameters for spring pattern (bullish)"""
        spring_data = pattern.get('spring_data', {})
        
        # Key levels from pattern
        spring_low = spring_data.get('spring_low', price_data['low'].iloc[-10:].min())
        spring_high = spring_data.get('spring_high', 0)
        accumulation_high = pattern.get('resistance_level', price_data['high'].iloc[-50:].max())
        accumulation_low = pattern.get('support_level', price_data['low'].iloc[-50:].min())
        accumulation_range = accumulation_high - accumulation_low
        
        # Entry: Above spring high with buffer
        entry_buffer = atr * self.atr_multiplier_entry
        entry_price = spring_high + entry_buffer
        
        # Stop loss: Below spring low with buffer
        stop_buffer = atr * self.atr_multiplier_stop
        stop_loss = spring_low - stop_buffer
        
        # Take profit levels using measured moves
        # TP1: Accumulation high (conservative)
        take_profit_1 = accumulation_high
        
        # TP2: Measured move (accumulation range projected from entry)
        take_profit_2 = entry_price + accumulation_range
        
        # TP3: Extended target (1.618 Fibonacci extension)
        take_profit_3 = entry_price + (accumulation_range * 1.618)
        
        return {
            'signal_type': 'long',
            'entry_price': Decimal(str(round(entry_price, 5))),
            'stop_loss': Decimal(str(round(stop_loss, 5))),
            'take_profit_1': Decimal(str(round(take_profit_1, 5))),
            'take_profit_2': Decimal(str(round(take_profit_2, 5))),
            'take_profit_3': Decimal(str(round(take_profit_3, 5))),
            'pattern_specific_data': {
                'spring_low': spring_low,
                'spring_high': spring_high,
                'accumulation_range': accumulation_range,
                'entry_buffer_atr': self.atr_multiplier_entry,
                'stop_buffer_atr': self.atr_multiplier_stop
            }
        }
    
    def _calculate_accumulation_parameters(self, pattern: Dict, price_data: pd.DataFrame, atr: float) -> Dict:
        """Calculate parameters for accumulation pattern (bullish)"""
        # Key levels from pattern
        resistance_level = pattern.get('resistance_level', price_data['high'].iloc[-30:].max())
        support_level = pattern.get('support_level', price_data['low'].iloc[-30:].min())
        accumulation_range = resistance_level - support_level
        current_price = price_data['close'].iloc[-1]
        
        # Entry: Above resistance with buffer (breakout entry)
        entry_buffer = atr * self.atr_multiplier_entry
        entry_price = resistance_level + entry_buffer
        
        # Stop loss: Below support level
        stop_buffer = atr * self.atr_multiplier_stop
        stop_loss = support_level - stop_buffer
        
        # Take profit levels
        # TP1: Conservative target (0.618 * range above entry)
        take_profit_1 = entry_price + (accumulation_range * 0.618)
        
        # TP2: Full measured move
        take_profit_2 = entry_price + accumulation_range
        
        # TP3: Extended target
        take_profit_3 = entry_price + (accumulation_range * 1.618)
        
        return {
            'signal_type': 'long',
            'entry_price': Decimal(str(round(entry_price, 5))),
            'stop_loss': Decimal(str(round(stop_loss, 5))),
            'take_profit_1': Decimal(str(round(take_profit_1, 5))),
            'take_profit_2': Decimal(str(round(take_profit_2, 5))),
            'take_profit_3': Decimal(str(round(take_profit_3, 5))),
            'pattern_specific_data': {
                'resistance_level': resistance_level,
                'support_level': support_level,
                'accumulation_range': accumulation_range,
                'range_position_at_signal': (current_price - support_level) / accumulation_range
            }
        }
    
    def _calculate_distribution_parameters(self, pattern: Dict, price_data: pd.DataFrame, atr: float) -> Dict:
        """Calculate parameters for distribution pattern (bearish)"""
        # Key levels from pattern
        resistance_level = pattern.get('resistance_level', price_data['high'].iloc[-30:].max())
        support_level = pattern.get('support_level', price_data['low'].iloc[-30:].min())
        distribution_range = resistance_level - support_level
        
        # Entry: Below support with buffer (breakdown entry)
        entry_buffer = atr * self.atr_multiplier_entry
        entry_price = support_level - entry_buffer
        
        # Stop loss: Above resistance level
        stop_buffer = atr * self.atr_multiplier_stop
        stop_loss = resistance_level + stop_buffer
        
        # Take profit levels (short positions)
        # TP1: Conservative target
        take_profit_1 = entry_price - (distribution_range * 0.618)
        
        # TP2: Full measured move
        take_profit_2 = entry_price - distribution_range
        
        # TP3: Extended target
        take_profit_3 = entry_price - (distribution_range * 1.618)
        
        return {
            'signal_type': 'short',
            'entry_price': Decimal(str(round(entry_price, 5))),
            'stop_loss': Decimal(str(round(stop_loss, 5))),
            'take_profit_1': Decimal(str(round(take_profit_1, 5))),
            'take_profit_2': Decimal(str(round(take_profit_2, 5))),
            'take_profit_3': Decimal(str(round(take_profit_3, 5))),
            'pattern_specific_data': {
                'resistance_level': resistance_level,
                'support_level': support_level,
                'distribution_range': distribution_range
            }
        }
    
    def _calculate_upthrust_parameters(self, pattern: Dict, price_data: pd.DataFrame, atr: float) -> Dict:
        """Calculate parameters for upthrust pattern (bearish)"""
        upthrust_data = pattern.get('upthrust_data', {})
        
        # Key levels
        upthrust_high = upthrust_data.get('upthrust_high', price_data['high'].iloc[-5:].max())
        upthrust_low = upthrust_data.get('upthrust_low', 0)
        distribution_high = pattern.get('resistance_level', price_data['high'].iloc[-50:].max())
        distribution_low = pattern.get('support_level', price_data['low'].iloc[-50:].min())
        distribution_range = distribution_high - distribution_low
        
        # Entry: Below upthrust low with buffer
        entry_buffer = atr * self.atr_multiplier_entry
        entry_price = upthrust_low - entry_buffer
        
        # Stop loss: Above upthrust high with buffer
        stop_buffer = atr * self.atr_multiplier_stop
        stop_loss = upthrust_high + stop_buffer
        
        # Take profit levels
        take_profit_1 = distribution_low  # Support level
        take_profit_2 = entry_price - distribution_range
        take_profit_3 = entry_price - (distribution_range * 1.618)
        
        return {
            'signal_type': 'short',
            'entry_price': Decimal(str(round(entry_price, 5))),
            'stop_loss': Decimal(str(round(stop_loss, 5))),
            'take_profit_1': Decimal(str(round(take_profit_1, 5))),
            'take_profit_2': Decimal(str(round(take_profit_2, 5))),
            'take_profit_3': Decimal(str(round(take_profit_3, 5))),
            'pattern_specific_data': {
                'upthrust_high': upthrust_high,
                'upthrust_low': upthrust_low,
                'distribution_range': distribution_range
            }
        }
    
    def _calculate_sos_parameters(self, pattern: Dict, price_data: pd.DataFrame, atr: float) -> Dict:
        """Calculate parameters for Sign of Strength pattern (bullish)"""
        # Entry on pullback to support
        support_level = pattern.get('support_level', price_data['low'].iloc[-20:].min())
        recent_high = price_data['high'].iloc[-10:].max()
        
        # Entry near support with small buffer
        entry_buffer = atr * (self.atr_multiplier_entry * 0.5)  # Smaller buffer for SoS
        entry_price = support_level + entry_buffer
        
        # Tight stop below support
        stop_loss = support_level - (atr * 0.5)
        
        # Targets based on recent strength
        range_size = recent_high - support_level
        take_profit_1 = entry_price + (range_size * 0.8)
        take_profit_2 = entry_price + range_size
        take_profit_3 = entry_price + (range_size * 1.5)
        
        return {
            'signal_type': 'long',
            'entry_price': Decimal(str(round(entry_price, 5))),
            'stop_loss': Decimal(str(round(stop_loss, 5))),
            'take_profit_1': Decimal(str(round(take_profit_1, 5))),
            'take_profit_2': Decimal(str(round(take_profit_2, 5))),
            'take_profit_3': Decimal(str(round(take_profit_3, 5))),
            'pattern_specific_data': {
                'support_level': support_level,
                'recent_high': recent_high,
                'strength_range': range_size
            }
        }
    
    def _calculate_sow_parameters(self, pattern: Dict, price_data: pd.DataFrame, atr: float) -> Dict:
        """Calculate parameters for Sign of Weakness pattern (bearish)"""
        # Entry on bounce to resistance
        resistance_level = pattern.get('resistance_level', price_data['high'].iloc[-20:].max())
        recent_low = price_data['low'].iloc[-10:].min()
        
        # Entry near resistance
        entry_buffer = atr * (self.atr_multiplier_entry * 0.5)
        entry_price = resistance_level - entry_buffer
        
        # Stop above resistance
        stop_loss = resistance_level + (atr * 0.5)
        
        # Targets based on recent weakness
        range_size = resistance_level - recent_low
        take_profit_1 = entry_price - (range_size * 0.8)
        take_profit_2 = entry_price - range_size
        take_profit_3 = entry_price - (range_size * 1.5)
        
        return {
            'signal_type': 'short',
            'entry_price': Decimal(str(round(entry_price, 5))),
            'stop_loss': Decimal(str(round(stop_loss, 5))),
            'take_profit_1': Decimal(str(round(take_profit_1, 5))),
            'take_profit_2': Decimal(str(round(take_profit_2, 5))),
            'take_profit_3': Decimal(str(round(take_profit_3, 5))),
            'pattern_specific_data': {
                'resistance_level': resistance_level,
                'recent_low': recent_low,
                'weakness_range': range_size
            }
        }
    
    def _calculate_backup_parameters(self, pattern: Dict, price_data: pd.DataFrame, atr: float) -> Dict:
        """Calculate parameters for backup/pullback patterns"""
        signal_type = 'long' if pattern.get('direction') == 'bullish' else 'short'
        
        if signal_type == 'long':
            # Bullish backup - buy the dip
            support_level = pattern.get('support_level', price_data['low'].iloc[-15:].min())
            entry_price = support_level + (atr * 0.3)
            stop_loss = support_level - (atr * 0.8)
            
            recent_high = price_data['high'].iloc[-30:].max()
            take_profit_1 = entry_price + ((recent_high - entry_price) * 0.7)
            take_profit_2 = recent_high
            take_profit_3 = recent_high + (atr * 2)
        else:
            # Bearish backup - sell the bounce
            resistance_level = pattern.get('resistance_level', price_data['high'].iloc[-15:].max())
            entry_price = resistance_level - (atr * 0.3)
            stop_loss = resistance_level + (atr * 0.8)
            
            recent_low = price_data['low'].iloc[-30:].min()
            take_profit_1 = entry_price - ((entry_price - recent_low) * 0.7)
            take_profit_2 = recent_low
            take_profit_3 = recent_low - (atr * 2)
        
        return {
            'signal_type': signal_type,
            'entry_price': Decimal(str(round(entry_price, 5))),
            'stop_loss': Decimal(str(round(stop_loss, 5))),
            'take_profit_1': Decimal(str(round(take_profit_1, 5))),
            'take_profit_2': Decimal(str(round(take_profit_2, 5))),
            'take_profit_3': Decimal(str(round(take_profit_3, 5))),
            'pattern_specific_data': {
                'backup_type': signal_type,
                'key_level': support_level if signal_type == 'long' else resistance_level
            }
        }
    
    def _calculate_test_parameters(self, pattern: Dict, price_data: pd.DataFrame, atr: float) -> Dict:
        """Calculate parameters for test patterns"""
        test_data = pattern.get('test_data', {})
        signal_type = 'long' if pattern.get('direction') == 'bullish' else 'short'
        
        if signal_type == 'long':
            # Test of support - bullish
            test_level = test_data.get('test_level', price_data['low'].iloc[-5:].min())
            entry_price = test_level + (atr * 0.2)
            stop_loss = test_level - (atr * 0.6)
            
            resistance = pattern.get('resistance_level', price_data['high'].iloc[-20:].max())
            take_profit_1 = entry_price + ((resistance - entry_price) * 0.6)
            take_profit_2 = resistance
            take_profit_3 = resistance + (atr * 1.5)
        else:
            # Test of resistance - bearish
            test_level = test_data.get('test_level', price_data['high'].iloc[-5:].max())
            entry_price = test_level - (atr * 0.2)
            stop_loss = test_level + (atr * 0.6)
            
            support = pattern.get('support_level', price_data['low'].iloc[-20:].min())
            take_profit_1 = entry_price - ((entry_price - support) * 0.6)
            take_profit_2 = support
            take_profit_3 = support - (atr * 1.5)
        
        return {
            'signal_type': signal_type,
            'entry_price': Decimal(str(round(entry_price, 5))),
            'stop_loss': Decimal(str(round(stop_loss, 5))),
            'take_profit_1': Decimal(str(round(take_profit_1, 5))),
            'take_profit_2': Decimal(str(round(take_profit_2, 5))),
            'take_profit_3': Decimal(str(round(take_profit_3, 5))),
            'pattern_specific_data': {
                'test_level': test_data.get('test_level'),
                'test_type': signal_type
            }
        }
    
    def _calculate_generic_parameters(self, pattern: Dict, price_data: pd.DataFrame, atr: float) -> Dict:
        """Generic parameter calculation for unknown patterns"""
        # Determine signal direction
        signal_type = 'long' if pattern.get('direction') == 'bullish' else 'short'
        current_price = price_data['close'].iloc[-1]
        
        if signal_type == 'long':
            # Generic long setup
            support = price_data['low'].iloc[-20:].min()
            resistance = price_data['high'].iloc[-20:].max()
            
            entry_price = current_price + (atr * 0.2)
            stop_loss = support - (atr * 0.5)
            take_profit_1 = current_price + (atr * 2)
            take_profit_2 = resistance
            take_profit_3 = resistance + (atr * 1)
        else:
            # Generic short setup
            support = price_data['low'].iloc[-20:].min()
            resistance = price_data['high'].iloc[-20:].max()
            
            entry_price = current_price - (atr * 0.2)
            stop_loss = resistance + (atr * 0.5)
            take_profit_1 = current_price - (atr * 2)
            take_profit_2 = support
            take_profit_3 = support - (atr * 1)
        
        return {
            'signal_type': signal_type,
            'entry_price': Decimal(str(round(entry_price, 5))),
            'stop_loss': Decimal(str(round(stop_loss, 5))),
            'take_profit_1': Decimal(str(round(take_profit_1, 5))),
            'take_profit_2': Decimal(str(round(take_profit_2, 5))),
            'take_profit_3': Decimal(str(round(take_profit_3, 5))),
            'pattern_specific_data': {
                'calculation_type': 'generic',
                'pattern_direction': signal_type
            }
        }
    
    def _enhance_with_market_context(self, params: Dict, market_context: Dict, atr: float) -> Dict:
        """Enhance parameters based on market context"""
        enhanced_params = params.copy()
        
        # Adjust for volatility regime
        volatility_regime = market_context.get('volatility_analysis', {}).get('regime', 'normal')
        
        if volatility_regime == 'high':
            # Widen stops in high volatility
            current_stop = enhanced_params['stop_loss']
            entry = enhanced_params['entry_price']
            signal_type = enhanced_params['signal_type']
            
            if signal_type == 'long':
                enhanced_params['stop_loss'] = Decimal(str(round(float(current_stop) - atr * 0.3, 5)))
            else:
                enhanced_params['stop_loss'] = Decimal(str(round(float(current_stop) + atr * 0.3, 5)))
        
        elif volatility_regime == 'low':
            # Tighten stops in low volatility
            current_stop = enhanced_params['stop_loss']
            entry = enhanced_params['entry_price']
            signal_type = enhanced_params['signal_type']
            
            if signal_type == 'long':
                enhanced_params['stop_loss'] = Decimal(str(round(float(current_stop) + atr * 0.2, 5)))
            else:
                enhanced_params['stop_loss'] = Decimal(str(round(float(current_stop) - atr * 0.2, 5)))
        
        # Adjust for market state
        market_state = market_context.get('market_state', 'unknown')
        if market_state in ['ranging', 'choppy']:
            # More conservative targets in ranging markets
            tp1 = enhanced_params['take_profit_1']
            entry = enhanced_params['entry_price']
            
            # Reduce first target by 20%
            if enhanced_params['signal_type'] == 'long':
                new_tp1 = float(entry) + (float(tp1) - float(entry)) * 0.8
            else:
                new_tp1 = float(entry) - (float(entry) - float(tp1)) * 0.8
            
            enhanced_params['take_profit_1'] = Decimal(str(round(new_tp1, 5)))
        
        return enhanced_params
    
    def _calculate_entry_confirmation(self,
                                    pattern: Dict,
                                    params: Dict,
                                    volume_data: pd.Series,
                                    atr: float) -> EntryConfirmation:
        """Calculate entry confirmation requirements"""
        pattern_type = pattern.get('type', 'unknown')
        
        # Base confirmation requirements
        volume_spike_required = True
        volume_threshold = 2.0
        momentum_threshold = 0.3
        timeout_minutes = 60
        
        # Pattern-specific adjustments
        if pattern_type in ['spring', 'upthrust']:
            # These patterns require strong volume confirmation
            volume_threshold = 2.5
            momentum_threshold = 0.4
            timeout_minutes = 30  # Shorter timeout for breakout patterns
        
        elif pattern_type in ['accumulation', 'distribution']:
            # These patterns allow more time for confirmation
            timeout_minutes = 120
            volume_threshold = 1.8
        
        elif pattern_type in ['sign_of_strength', 'sign_of_weakness']:
            # These require immediate confirmation
            timeout_minutes = 15
            momentum_threshold = 0.5
        
        # Calculate average volume for threshold
        avg_volume = volume_data.iloc[-20:].mean() if len(volume_data) >= 20 else volume_data.mean()
        
        return EntryConfirmation(
            volume_spike_required=volume_spike_required,
            volume_threshold_multiplier=volume_threshold,
            momentum_threshold=momentum_threshold,
            timeout_minutes=timeout_minutes,
            price_confirmation_required=True,
            min_candle_close_percentage=0.7
        )
    
    def _optimize_risk_reward(self, params: Dict, pattern: Dict, price_data: pd.DataFrame) -> Dict:
        """Optimize parameters to meet minimum risk-reward requirements"""
        optimized_params = params.copy()
        
        entry = float(optimized_params['entry_price'])
        stop = float(optimized_params['stop_loss'])
        tp1 = float(optimized_params['take_profit_1'])
        
        # Calculate current R:R
        if optimized_params['signal_type'] == 'long':
            risk = entry - stop
            reward = tp1 - entry
        else:
            risk = stop - entry
            reward = entry - tp1
        
        current_rr = reward / risk if risk > 0 else 0
        
        # If R:R is below minimum, try to optimize
        if current_rr < self.min_risk_reward:
            # Strategy 1: Extend first target
            if optimized_params['signal_type'] == 'long':
                new_tp1 = entry + (risk * self.min_risk_reward)
            else:
                new_tp1 = entry - (risk * self.min_risk_reward)
            
            optimized_params['take_profit_1'] = Decimal(str(round(new_tp1, 5)))
            
            # Recalculate other targets proportionally
            if 'take_profit_2' in optimized_params and optimized_params['take_profit_2']:
                tp2 = float(optimized_params['take_profit_2'])
                if optimized_params['signal_type'] == 'long':
                    new_tp2 = entry + (risk * (self.min_risk_reward * 1.5))
                else:
                    new_tp2 = entry - (risk * (self.min_risk_reward * 1.5))
                optimized_params['take_profit_2'] = Decimal(str(round(new_tp2, 5)))
            
            if 'take_profit_3' in optimized_params and optimized_params['take_profit_3']:
                if optimized_params['signal_type'] == 'long':
                    new_tp3 = entry + (risk * (self.min_risk_reward * 2.0))
                else:
                    new_tp3 = entry - (risk * (self.min_risk_reward * 2.0))
                optimized_params['take_profit_3'] = Decimal(str(round(new_tp3, 5)))
        
        # Cap R:R at maximum to avoid unrealistic targets
        elif current_rr > self.max_risk_reward:
            if optimized_params['signal_type'] == 'long':
                capped_tp1 = entry + (risk * self.max_risk_reward)
            else:
                capped_tp1 = entry - (risk * self.max_risk_reward)
            optimized_params['take_profit_1'] = Decimal(str(round(capped_tp1, 5)))
        
        # Recalculate final risk-reward ratio after optimization
        final_entry = float(optimized_params['entry_price'])
        final_stop = float(optimized_params['stop_loss'])
        final_tp1 = float(optimized_params['take_profit_1'])
        
        if optimized_params['signal_type'] == 'long':
            final_risk = final_entry - final_stop
            final_reward = final_tp1 - final_entry
        else:
            final_risk = final_stop - final_entry
            final_reward = final_entry - final_tp1
        
        final_rr = final_reward / final_risk if final_risk > 0 else 0
        optimized_params['risk_reward_ratio'] = round(final_rr, 2)
        
        return optimized_params
    
    def _estimate_timing_parameters(self, pattern: Dict, market_context: Dict) -> Dict:
        """Estimate timing parameters for the signal"""
        pattern_type = pattern.get('type', 'unknown')
        
        # Base hold times by pattern type (in hours)
        base_hold_times = {
            'spring': 18,
            'upthrust': 18,
            'accumulation': 48,
            'distribution': 48,
            'sign_of_strength': 12,
            'sign_of_weakness': 12,
            'backup': 24,
            'test': 8
        }
        
        base_hold_time = base_hold_times.get(pattern_type, 24)
        
        # Adjust for market context
        market_state = market_context.get('market_state', 'unknown')
        volatility_regime = market_context.get('volatility_analysis', {}).get('regime', 'normal')
        
        # Market state adjustments
        if market_state == 'trending':
            hold_time_multiplier = 1.2
        elif market_state == 'ranging':
            hold_time_multiplier = 0.8
        elif market_state == 'choppy':
            hold_time_multiplier = 0.5
        else:
            hold_time_multiplier = 1.0
        
        # Volatility adjustments
        if volatility_regime == 'high':
            hold_time_multiplier *= 0.8
        elif volatility_regime == 'low':
            hold_time_multiplier *= 1.3
        
        expected_hold_time = int(base_hold_time * hold_time_multiplier)
        
        # Calculate signal validity period (usually 2-3x expected hold time)
        validity_hours = expected_hold_time * 2
        valid_until = datetime.now() + timedelta(hours=validity_hours)
        
        return {
            'expected_hold_time_hours': expected_hold_time,
            'valid_until': valid_until,
            'validity_hours': validity_hours,
            'base_hold_time': base_hold_time,
            'adjustments_applied': {
                'market_state_multiplier': 1.2 if market_state == 'trending' else 0.8 if market_state == 'ranging' else 1.0,
                'volatility_multiplier': 0.8 if volatility_regime == 'high' else 1.3 if volatility_regime == 'low' else 1.0
            }
        }
    
    def _calculate_atr(self, price_data: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range"""
        if len(price_data) < period:
            # Use available data if less than period
            period = len(price_data)
        
        high = price_data['high']
        low = price_data['low']
        close = price_data['close']
        
        # True Range calculation
        tr1 = high - low
        tr2 = np.abs(high - close.shift(1))
        tr3 = np.abs(low - close.shift(1))
        
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.rolling(period).mean().iloc[-1]
        
        return float(atr) if not np.isnan(atr) else 0.001  # Fallback to small value