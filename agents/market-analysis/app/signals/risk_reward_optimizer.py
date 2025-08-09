"""
Risk-Reward Optimizer

Advanced risk-reward ratio optimization system that ensures all signals meet
minimum R:R requirements while maximizing profit potential through intelligent
parameter adjustments.
"""

from typing import Dict, List, Tuple, Optional
import pandas as pd
import numpy as np
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class RiskRewardOptimizer:
    """
    Optimizes signal parameters to achieve target risk-reward ratios.
    
    Uses multiple strategies to improve R:R ratios:
    - Entry price optimization
    - Stop loss adjustment based on volatility
    - Target extension using higher timeframe levels
    - Dynamic position sizing recommendations
    """
    
    def __init__(self,
                 min_risk_reward: float = 2.0,
                 target_risk_reward: float = 3.0,
                 max_risk_reward: float = 8.0,
                 max_entry_adjustment_atr: float = 0.5,
                 max_stop_adjustment_atr: float = 0.3):
        """
        Initialize risk-reward optimizer.
        
        Args:
            min_risk_reward: Minimum acceptable R:R ratio
            target_risk_reward: Target R:R ratio to aim for
            max_risk_reward: Maximum R:R ratio (cap unrealistic targets)
            max_entry_adjustment_atr: Max ATR adjustment for entry optimization
            max_stop_adjustment_atr: Max ATR adjustment for stop optimization
        """
        self.min_risk_reward = min_risk_reward
        self.target_risk_reward = target_risk_reward
        self.max_risk_reward = max_risk_reward
        self.max_entry_adjustment_atr = max_entry_adjustment_atr
        self.max_stop_adjustment_atr = max_stop_adjustment_atr
    
    def optimize_signal_parameters(self,
                                  signal_params: Dict,
                                  pattern: Dict,
                                  price_data: pd.DataFrame,
                                  market_context: Dict,
                                  volume_analysis: Dict = None) -> Dict:
        """
        Optimize signal parameters to meet risk-reward requirements.
        
        Args:
            signal_params: Current signal parameters
            pattern: Pattern data for context
            price_data: OHLC price data
            market_context: Market state information
            volume_analysis: Volume analysis data
            
        Returns:
            Optimized signal parameters with metadata
        """
        if not signal_params or 'entry_price' not in signal_params:
            return {'error': 'Invalid signal parameters provided'}
        
        # Calculate current R:R ratio
        current_rr = self._calculate_risk_reward_ratio(signal_params)
        
        # If already meets requirements, minimal optimization
        if current_rr >= self.min_risk_reward:
            return self._fine_tune_parameters(signal_params, pattern, price_data, market_context)
        
        # Apply optimization strategies in order of preference
        optimized_params = signal_params.copy()
        optimization_log = []
        
        # Strategy 1: Optimize entry price
        entry_optimized = self._optimize_entry_price(optimized_params, pattern, price_data)
        if entry_optimized['success']:
            optimized_params = entry_optimized['params']
            optimization_log.append('entry_price_optimized')
            
        # Check R:R after entry optimization
        current_rr = self._calculate_risk_reward_ratio(optimized_params)
        
        # Strategy 2: Extend targets if still below minimum
        if current_rr < self.min_risk_reward:
            target_optimized = self._extend_targets(optimized_params, pattern, price_data, market_context)
            if target_optimized['success']:
                optimized_params = target_optimized['params']
                optimization_log.append('targets_extended')
        
        # Check R:R after target extension
        current_rr = self._calculate_risk_reward_ratio(optimized_params)
        
        # Strategy 3: Adjust stop loss if still insufficient
        if current_rr < self.min_risk_reward:
            stop_optimized = self._optimize_stop_loss(optimized_params, pattern, price_data, market_context)
            if stop_optimized['success']:
                optimized_params = stop_optimized['params']
                optimization_log.append('stop_loss_optimized')
        
        # Final R:R check
        final_rr = self._calculate_risk_reward_ratio(optimized_params)
        
        # If still can't meet minimum, mark as invalid
        if final_rr < self.min_risk_reward:
            return {
                'success': False,
                'reason': 'unable_to_meet_minimum_rr',
                'current_rr': final_rr,
                'min_required_rr': self.min_risk_reward,
                'optimization_attempted': optimization_log
            }
        
        # Add optimization metadata
        optimized_params['optimization_metadata'] = {
            'original_rr': self._calculate_risk_reward_ratio(signal_params),
            'optimized_rr': final_rr,
            'optimization_strategies_applied': optimization_log,
            'optimization_successful': True,
            'meets_minimum_rr': final_rr >= self.min_risk_reward,
            'optimization_timestamp': datetime.now()
        }
        
        # Calculate position sizing recommendations
        optimized_params['position_sizing'] = self._calculate_position_sizing(
            optimized_params, market_context
        )
        
        return {
            'success': True,
            'params': optimized_params,
            'optimization_summary': {
                'improvement': final_rr - self._calculate_risk_reward_ratio(signal_params),
                'strategies_used': optimization_log,
                'final_rr': final_rr
            }
        }
    
    def _calculate_risk_reward_ratio(self, params: Dict) -> float:
        """Calculate risk-reward ratio for given parameters"""
        try:
            entry = float(params['entry_price'])
            stop = float(params['stop_loss'])
            tp1 = float(params['take_profit_1'])
            signal_type = params['signal_type']
            
            if signal_type == 'long':
                risk = entry - stop
                reward = tp1 - entry
            else:  # short
                risk = stop - entry
                reward = entry - tp1
            
            return reward / risk if risk > 0 else 0.0
        except (KeyError, ValueError, ZeroDivisionError):
            return 0.0
    
    def _optimize_entry_price(self, params: Dict, pattern: Dict, price_data: pd.DataFrame) -> Dict:
        """
        Optimize entry price to improve R:R ratio while maintaining signal validity.
        """
        try:
            current_entry = float(params['entry_price'])
            stop_loss = float(params['stop_loss'])
            signal_type = params['signal_type']
            
            # Calculate ATR for adjustment limits
            atr = self._calculate_atr(price_data)
            max_adjustment = atr * self.max_entry_adjustment_atr
            
            # Get key levels for entry optimization
            key_levels = self._identify_key_levels(price_data, pattern)
            
            # Find optimal entry based on signal type
            if signal_type == 'long':
                # For long signals, try to get closer to support/resistance
                resistance_level = key_levels.get('resistance', current_entry)
                
                # Try entry at resistance + small buffer (breakout entry)
                optimal_entry = resistance_level + (atr * 0.1)
                
                # Ensure it's within adjustment limits
                if abs(optimal_entry - current_entry) <= max_adjustment:
                    new_params = params.copy()
                    new_params['entry_price'] = Decimal(str(round(optimal_entry, 5)))
                    
                    # Verify R:R improvement
                    new_rr = self._calculate_risk_reward_ratio(new_params)
                    original_rr = self._calculate_risk_reward_ratio(params)
                    
                    if new_rr > original_rr:
                        return {'success': True, 'params': new_params}
            
            else:  # short signal
                # For short signals, get closer to resistance
                support_level = key_levels.get('support', current_entry)
                
                # Try entry at support - small buffer (breakdown entry)
                optimal_entry = support_level - (atr * 0.1)
                
                # Ensure within limits
                if abs(optimal_entry - current_entry) <= max_adjustment:
                    new_params = params.copy()
                    new_params['entry_price'] = Decimal(str(round(optimal_entry, 5)))
                    
                    # Verify improvement
                    new_rr = self._calculate_risk_reward_ratio(new_params)
                    original_rr = self._calculate_risk_reward_ratio(params)
                    
                    if new_rr > original_rr:
                        return {'success': True, 'params': new_params}
            
            return {'success': False, 'reason': 'no_improvement_found'}
            
        except Exception as e:
            logger.error(f"Error optimizing entry price: {e}")
            return {'success': False, 'reason': 'optimization_error'}
    
    def _extend_targets(self, params: Dict, pattern: Dict, price_data: pd.DataFrame, market_context: Dict) -> Dict:
        """
        Extend take profit targets to improve R:R ratio.
        """
        try:
            entry = float(params['entry_price'])
            stop = float(params['stop_loss'])
            signal_type = params['signal_type']
            
            # Calculate current risk
            if signal_type == 'long':
                risk = entry - stop
            else:
                risk = stop - entry
            
            # Calculate target R:R levels
            target_rr_levels = [self.target_risk_reward, self.target_risk_reward * 1.5, self.target_risk_reward * 2.0]
            
            # Find higher timeframe levels for realistic targets
            extended_levels = self._find_extended_target_levels(price_data, pattern, signal_type)
            
            new_params = params.copy()
            
            # Set new targets
            if signal_type == 'long':
                # Long targets
                new_tp1 = entry + (risk * target_rr_levels[0])
                new_tp2 = entry + (risk * target_rr_levels[1])
                new_tp3 = entry + (risk * target_rr_levels[2])
                
                # Adjust targets to extended levels if available and reasonable
                if extended_levels.get('resistance_1') and extended_levels['resistance_1'] > new_tp1:
                    new_tp1 = min(new_tp1 * 1.2, extended_levels['resistance_1'])
                
                if extended_levels.get('resistance_2') and extended_levels['resistance_2'] > new_tp2:
                    new_tp2 = min(new_tp2, extended_levels['resistance_2'])
            
            else:
                # Short targets
                new_tp1 = entry - (risk * target_rr_levels[0])
                new_tp2 = entry - (risk * target_rr_levels[1])
                new_tp3 = entry - (risk * target_rr_levels[2])
                
                # Adjust to extended levels
                if extended_levels.get('support_1') and extended_levels['support_1'] < new_tp1:
                    new_tp1 = max(new_tp1 * 1.2, extended_levels['support_1'])
                
                if extended_levels.get('support_2') and extended_levels['support_2'] < new_tp2:
                    new_tp2 = max(new_tp2, extended_levels['support_2'])
            
            # Update parameters
            new_params['take_profit_1'] = Decimal(str(round(new_tp1, 5)))
            new_params['take_profit_2'] = Decimal(str(round(new_tp2, 5)))
            new_params['take_profit_3'] = Decimal(str(round(new_tp3, 5)))
            
            # Verify improvement
            new_rr = self._calculate_risk_reward_ratio(new_params)
            if new_rr >= self.min_risk_reward:
                return {'success': True, 'params': new_params}
            else:
                return {'success': False, 'reason': 'insufficient_improvement'}
                
        except Exception as e:
            logger.error(f"Error extending targets: {e}")
            return {'success': False, 'reason': 'extension_error'}
    
    def _optimize_stop_loss(self, params: Dict, pattern: Dict, price_data: pd.DataFrame, market_context: Dict) -> Dict:
        """
        Optimize stop loss placement to improve R:R while maintaining pattern validity.
        """
        try:
            entry = float(params['entry_price'])
            current_stop = float(params['stop_loss'])
            signal_type = params['signal_type']
            
            # Calculate ATR for adjustment limits
            atr = self._calculate_atr(price_data)
            max_adjustment = atr * self.max_stop_adjustment_atr
            
            # Get pattern invalidation level
            invalidation_level = self._get_pattern_invalidation_level(pattern, price_data)
            
            # Determine optimal stop based on signal type
            if signal_type == 'long':
                # For long signals, can tighten stop if not risking pattern invalidation
                min_stop = invalidation_level - (atr * 0.2) if invalidation_level else current_stop
                optimal_stop = max(min_stop, current_stop + max_adjustment)
                
                # Ensure we're not making stop too tight (min 0.5 ATR risk)
                min_risk_stop = entry - (atr * 0.5)
                optimal_stop = min(optimal_stop, min_risk_stop)
                
            else:  # short signal
                # For short signals
                max_stop = invalidation_level + (atr * 0.2) if invalidation_level else current_stop
                optimal_stop = min(max_stop, current_stop - max_adjustment)
                
                # Ensure minimum risk
                min_risk_stop = entry + (atr * 0.5)
                optimal_stop = max(optimal_stop, min_risk_stop)
            
            # Only apply if it improves R:R
            new_params = params.copy()
            new_params['stop_loss'] = Decimal(str(round(optimal_stop, 5)))
            
            new_rr = self._calculate_risk_reward_ratio(new_params)
            original_rr = self._calculate_risk_reward_ratio(params)
            
            if new_rr > original_rr and abs(optimal_stop - current_stop) <= max_adjustment:
                return {'success': True, 'params': new_params}
            else:
                return {'success': False, 'reason': 'no_valid_improvement'}
                
        except Exception as e:
            logger.error(f"Error optimizing stop loss: {e}")
            return {'success': False, 'reason': 'stop_optimization_error'}
    
    def _fine_tune_parameters(self, params: Dict, pattern: Dict, price_data: pd.DataFrame, market_context: Dict) -> Dict:
        """
        Fine-tune parameters that already meet minimum R:R requirements.
        """
        fine_tuned = params.copy()
        
        # Add position sizing recommendations
        fine_tuned['position_sizing'] = self._calculate_position_sizing(fine_tuned, market_context)
        
        # Add trailing stop recommendations
        fine_tuned['trailing_stop'] = self._calculate_trailing_stop_recommendations(fine_tuned, pattern)
        
        # Add partial profit-taking levels
        fine_tuned['profit_taking_plan'] = self._create_profit_taking_plan(fine_tuned)
        
        fine_tuned['optimization_metadata'] = {
            'original_rr': self._calculate_risk_reward_ratio(params),
            'optimized_rr': self._calculate_risk_reward_ratio(fine_tuned),
            'optimization_strategies_applied': ['fine_tuning'],
            'optimization_successful': True,
            'meets_minimum_rr': True,
            'optimization_timestamp': datetime.now()
        }
        
        return {'success': True, 'params': fine_tuned}
    
    def _identify_key_levels(self, price_data: pd.DataFrame, pattern: Dict) -> Dict:
        """Identify key support and resistance levels"""
        # Use pattern levels if available
        support = pattern.get('support_level')
        resistance = pattern.get('resistance_level')
        
        # If not available, calculate from recent price action
        if not support:
            support = price_data['low'].iloc[-50:].min()
        if not resistance:
            resistance = price_data['high'].iloc[-50:].max()
        
        # Find additional levels using pivot points
        recent_data = price_data.iloc[-100:]  # Last 100 bars
        pivots = self._find_pivot_levels(recent_data)
        
        return {
            'support': support,
            'resistance': resistance,
            'pivot_supports': pivots['supports'],
            'pivot_resistances': pivots['resistances']
        }
    
    def _find_extended_target_levels(self, price_data: pd.DataFrame, pattern: Dict, signal_type: str) -> Dict:
        """Find extended levels for target placement"""
        # Look at longer timeframe structure (simulate with longer lookback)
        extended_data = price_data.iloc[-200:] if len(price_data) >= 200 else price_data
        
        if signal_type == 'long':
            # Find resistance levels above current price
            current_price = price_data['close'].iloc[-1]
            highs = extended_data['high']
            
            resistance_candidates = []
            for i in range(len(highs) - 10):
                if highs.iloc[i] == highs.iloc[i-5:i+5].max():
                    if highs.iloc[i] > current_price:
                        resistance_candidates.append(highs.iloc[i])
            
            resistance_candidates.sort()
            
            return {
                'resistance_1': resistance_candidates[0] if resistance_candidates else None,
                'resistance_2': resistance_candidates[1] if len(resistance_candidates) > 1 else None,
                'resistance_3': resistance_candidates[2] if len(resistance_candidates) > 2 else None
            }
        
        else:  # short signal
            # Find support levels below current price
            current_price = price_data['close'].iloc[-1]
            lows = extended_data['low']
            
            support_candidates = []
            for i in range(len(lows) - 10):
                if lows.iloc[i] == lows.iloc[i-5:i+5].min():
                    if lows.iloc[i] < current_price:
                        support_candidates.append(lows.iloc[i])
            
            support_candidates.sort(reverse=True)  # Descending order
            
            return {
                'support_1': support_candidates[0] if support_candidates else None,
                'support_2': support_candidates[1] if len(support_candidates) > 1 else None,
                'support_3': support_candidates[2] if len(support_candidates) > 2 else None
            }
    
    def _get_pattern_invalidation_level(self, pattern: Dict, price_data: pd.DataFrame) -> Optional[float]:
        """Get the level where pattern becomes invalid"""
        pattern_type = pattern.get('type', 'unknown')
        
        if pattern_type == 'spring':
            # Spring invalid if price goes below spring low
            return pattern.get('spring_data', {}).get('spring_low')
        elif pattern_type == 'upthrust':
            # Upthrust invalid if price goes above upthrust high
            return pattern.get('upthrust_data', {}).get('upthrust_high')
        elif pattern_type in ['accumulation', 'distribution']:
            # Invalid if breaks back into range
            if pattern_type == 'accumulation':
                return pattern.get('support_level')
            else:
                return pattern.get('resistance_level')
        
        # Default: use recent swing point
        if pattern.get('direction') == 'bullish':
            return price_data['low'].iloc[-20:].min()
        else:
            return price_data['high'].iloc[-20:].max()
    
    def _calculate_position_sizing(self, params: Dict, market_context: Dict) -> Dict:
        """Calculate position sizing recommendations"""
        rr_ratio = self._calculate_risk_reward_ratio(params)
        
        # Base position size as % of account (higher R:R allows larger size)
        if rr_ratio >= 4.0:
            base_size_percent = 2.0
        elif rr_ratio >= 3.0:
            base_size_percent = 1.5
        elif rr_ratio >= 2.5:
            base_size_percent = 1.2
        else:
            base_size_percent = 1.0
        
        # Adjust for market volatility
        volatility_regime = market_context.get('volatility_analysis', {}).get('regime', 'normal')
        volatility_adjustments = {
            'low': 1.2,
            'normal': 1.0,
            'high': 0.8,
            'extreme': 0.5
        }
        
        adjusted_size = base_size_percent * volatility_adjustments.get(volatility_regime, 1.0)
        
        # Adjust for market state
        market_state = market_context.get('market_state', 'unknown')
        if market_state == 'choppy':
            adjusted_size *= 0.5
        elif market_state == 'trending':
            adjusted_size *= 1.1
        
        return {
            'recommended_size_percent': round(adjusted_size, 2),
            'base_size_percent': base_size_percent,
            'volatility_adjustment': volatility_adjustments.get(volatility_regime, 1.0),
            'risk_per_trade_percent': round(adjusted_size / rr_ratio, 3),
            'sizing_rationale': f"Based on {rr_ratio:.1f}:1 R:R in {volatility_regime} volatility {market_state} market"
        }
    
    def _calculate_trailing_stop_recommendations(self, params: Dict, pattern: Dict) -> Dict:
        """Calculate trailing stop recommendations"""
        pattern_type = pattern.get('type', 'unknown')
        
        # Pattern-specific trailing stop strategies
        if pattern_type in ['spring', 'accumulation']:
            # Trend following patterns - use ATR trailing
            return {
                'strategy': 'atr_trailing',
                'atr_multiplier': 1.5,
                'activation_level': 'take_profit_1',
                'trail_increment_percent': 0.5
            }
        elif pattern_type in ['sign_of_strength', 'backup']:
            # Momentum patterns - tighter trailing
            return {
                'strategy': 'tight_trailing',
                'atr_multiplier': 1.0,
                'activation_level': 'breakeven',
                'trail_increment_percent': 0.3
            }
        else:
            # Default trailing strategy
            return {
                'strategy': 'standard_trailing',
                'atr_multiplier': 1.2,
                'activation_level': 'take_profit_1',
                'trail_increment_percent': 0.4
            }
    
    def _create_profit_taking_plan(self, params: Dict) -> Dict:
        """Create systematic profit-taking plan"""
        rr_ratio = self._calculate_risk_reward_ratio(params)
        
        # Different plans based on R:R ratio
        if rr_ratio >= 4.0:
            # High R:R - take profits in stages
            return {
                'tp1_percentage': 25,  # Take 25% at TP1
                'tp2_percentage': 50,  # Take 50% at TP2
                'tp3_percentage': 25,  # Hold 25% to TP3 or trailing
                'strategy': 'staged_profit_taking'
            }
        elif rr_ratio >= 3.0:
            return {
                'tp1_percentage': 33,
                'tp2_percentage': 67,
                'strategy': 'two_stage_profit_taking'
            }
        else:
            return {
                'tp1_percentage': 50,
                'tp2_percentage': 50,
                'strategy': 'split_profit_taking'
            }
    
    def _find_pivot_levels(self, price_data: pd.DataFrame) -> Dict:
        """Find pivot support and resistance levels"""
        highs = price_data['high']
        lows = price_data['low']
        
        # Simple pivot detection (local maxima/minima)
        pivot_supports = []
        pivot_resistances = []
        
        for i in range(5, len(price_data) - 5):
            # Pivot high
            if highs.iloc[i] == highs.iloc[i-5:i+6].max():
                pivot_resistances.append(highs.iloc[i])
            
            # Pivot low
            if lows.iloc[i] == lows.iloc[i-5:i+6].min():
                pivot_supports.append(lows.iloc[i])
        
        return {
            'supports': sorted(pivot_supports, reverse=True)[:3],  # Top 3 support levels
            'resistances': sorted(pivot_resistances)[:3]  # Top 3 resistance levels
        }
    
    def _calculate_atr(self, price_data: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range"""
        if len(price_data) < period:
            period = len(price_data)
        
        high = price_data['high']
        low = price_data['low']
        close = price_data['close']
        
        tr1 = high - low
        tr2 = np.abs(high - close.shift(1))
        tr3 = np.abs(low - close.shift(1))
        
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.rolling(period).mean().iloc[-1]
        
        return float(atr) if not np.isnan(atr) else 0.001
    
    def validate_risk_reward_ratio(self, params: Dict) -> Dict:
        """Validate that parameters meet minimum R:R requirements"""
        rr_ratio = self._calculate_risk_reward_ratio(params)
        
        return {
            'meets_minimum': rr_ratio >= self.min_risk_reward,
            'current_rr': round(rr_ratio, 2),
            'minimum_required': self.min_risk_reward,
            'rating': self._rate_risk_reward(rr_ratio),
            'recommendations': self._get_rr_recommendations(rr_ratio)
        }
    
    def _rate_risk_reward(self, rr_ratio: float) -> str:
        """Rate the quality of risk-reward ratio"""
        if rr_ratio >= 5.0:
            return 'excellent'
        elif rr_ratio >= 3.5:
            return 'very_good'
        elif rr_ratio >= 2.5:
            return 'good'
        elif rr_ratio >= 2.0:
            return 'acceptable'
        else:
            return 'poor'
    
    def _get_rr_recommendations(self, rr_ratio: float) -> List[str]:
        """Get recommendations based on R:R ratio"""
        recommendations = []
        
        if rr_ratio < 2.0:
            recommendations.append("Risk-reward ratio below minimum - avoid this signal")
        elif rr_ratio < 2.5:
            recommendations.append("Consider smaller position size due to modest R:R")
        elif rr_ratio >= 4.0:
            recommendations.append("Excellent R:R - consider larger position size")
            recommendations.append("Consider taking partial profits at first target")
        
        return recommendations