"""
Market State Detection

Advanced market state detection to filter signal generation based on
market conditions and avoid generating signals in unsuitable environments.
"""

from typing import Dict, List, Tuple, Optional
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class MarketStateDetector:
    """
    Detects current market state to determine suitability for signal generation.
    
    Analyzes market conditions including:
    - Trending vs ranging vs choppy conditions
    - Volatility regime classification
    - Market session and liquidity considerations
    - Volume characteristics
    """
    
    def __init__(self,
                 volatility_lookback: int = 20,
                 trend_lookback: int = 50,
                 range_threshold: float = 0.3,
                 choppy_threshold: float = 0.6):
        """
        Initialize market state detector.
        
        Args:
            volatility_lookback: Periods for volatility calculation
            trend_lookback: Periods for trend analysis
            range_threshold: Threshold for ranging market detection
            choppy_threshold: Threshold for choppy market detection
        """
        self.volatility_lookback = volatility_lookback
        self.trend_lookback = trend_lookback
        self.range_threshold = range_threshold
        self.choppy_threshold = choppy_threshold
    
    def detect_market_state(self, 
                           price_data: pd.DataFrame, 
                           volume_data: pd.Series) -> Dict:
        """
        Detect comprehensive market state.
        
        Args:
            price_data: OHLC price data
            volume_data: Volume data
            
        Returns:
            Dict containing market state analysis
        """
        if len(price_data) < self.trend_lookback:
            return {'error': 'Insufficient data for market state detection'}
        
        # Detect trend state
        trend_analysis = self._detect_trend_state(price_data)
        
        # Detect volatility regime
        volatility_analysis = self._detect_volatility_regime(price_data)
        
        # Detect market structure
        structure_analysis = self._analyze_market_structure(price_data)
        
        # Analyze volume characteristics
        volume_analysis = self._analyze_volume_characteristics(volume_data)
        
        # Determine session characteristics
        session_analysis = self._analyze_trading_session(price_data)
        
        # Combine analyses to determine overall market state
        overall_state = self._determine_overall_state(
            trend_analysis, volatility_analysis, structure_analysis
        )
        
        # Generate trading suitability assessment
        suitability = self._assess_trading_suitability(
            overall_state, volatility_analysis, volume_analysis
        )
        
        return {
            'market_state': overall_state,
            'trend_analysis': trend_analysis,
            'volatility_analysis': volatility_analysis,
            'structure_analysis': structure_analysis,
            'volume_analysis': volume_analysis,
            'session_analysis': session_analysis,
            'trading_suitability': suitability,
            'timestamp': datetime.now(),
            'signals_recommended': suitability['suitable_for_signals']
        }
    
    def _detect_trend_state(self, price_data: pd.DataFrame) -> Dict:
        """Detect trend state using multiple methods"""
        closes = price_data['close']
        
        # Method 1: Moving average analysis
        short_ma = closes.rolling(10).mean()
        medium_ma = closes.rolling(20).mean()
        long_ma = closes.rolling(50).mean()
        
        current_price = closes.iloc[-1]
        ma_alignment = self._check_ma_alignment(current_price, short_ma.iloc[-1], 
                                               medium_ma.iloc[-1], long_ma.iloc[-1])
        
        # Method 2: Linear regression trend strength
        recent_closes = closes.iloc[-self.trend_lookback:]
        x = np.arange(len(recent_closes))
        slope, intercept = np.polyfit(x, recent_closes, 1)
        
        # Calculate R-squared for trend strength
        y_pred = slope * x + intercept
        ss_res = np.sum((recent_closes - y_pred) ** 2)
        ss_tot = np.sum((recent_closes - np.mean(recent_closes)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        
        # Normalize slope for comparison
        avg_price = np.mean(recent_closes)
        slope_normalized = (slope / avg_price) * 100 if avg_price != 0 else 0
        
        # Method 3: Higher highs/lower lows analysis
        highs = price_data['high'].iloc[-self.trend_lookback:]
        lows = price_data['low'].iloc[-self.trend_lookback:]
        
        recent_high = highs.iloc[-10:].max()
        previous_high = highs.iloc[-20:-10].max()
        recent_low = lows.iloc[-10:].min()
        previous_low = lows.iloc[-20:-10].min()
        
        higher_highs = recent_high > previous_high
        higher_lows = recent_low > previous_low
        lower_highs = recent_high < previous_high
        lower_lows = recent_low < previous_low
        
        # Determine trend direction and strength
        if slope_normalized > 0.1 and r_squared > 0.7 and higher_highs and higher_lows:
            trend_direction = 'strong_uptrend'
            trend_strength = min(100, abs(slope_normalized) * 10 + r_squared * 50)
        elif slope_normalized > 0.05 and (higher_highs or higher_lows):
            trend_direction = 'uptrend'
            trend_strength = min(100, abs(slope_normalized) * 15 + r_squared * 40)
        elif slope_normalized < -0.1 and r_squared > 0.7 and lower_highs and lower_lows:
            trend_direction = 'strong_downtrend'
            trend_strength = min(100, abs(slope_normalized) * 10 + r_squared * 50)
        elif slope_normalized < -0.05 and (lower_highs or lower_lows):
            trend_direction = 'downtrend'
            trend_strength = min(100, abs(slope_normalized) * 15 + r_squared * 40)
        else:
            trend_direction = 'sideways'
            trend_strength = max(0, 100 - abs(slope_normalized) * 20)
        
        return {
            'direction': trend_direction,
            'strength': round(trend_strength, 2),
            'slope_normalized': round(slope_normalized, 4),
            'r_squared': round(r_squared, 3),
            'ma_alignment': ma_alignment,
            'higher_highs': higher_highs,
            'higher_lows': higher_lows,
            'lower_highs': lower_highs,
            'lower_lows': lower_lows
        }
    
    def _detect_volatility_regime(self, price_data: pd.DataFrame) -> Dict:
        """Detect current volatility regime"""
        # Calculate True Range
        tr = self._calculate_true_range(price_data)
        
        # Calculate ATR
        atr = tr.rolling(self.volatility_lookback).mean()
        current_atr = atr.iloc[-1]
        
        # Calculate ATR as percentage of price
        current_price = price_data['close'].iloc[-1]
        atr_percentage = (current_atr / current_price) * 100
        
        # Historical ATR percentiles for regime classification
        historical_atr_pct = (atr / price_data['close']) * 100
        atr_percentiles = np.percentile(historical_atr_pct.dropna(), [25, 50, 75, 90])
        
        # Classify volatility regime
        if atr_percentage > atr_percentiles[3]:  # 90th percentile
            regime = 'extreme'
        elif atr_percentage > atr_percentiles[2]:  # 75th percentile
            regime = 'high'
        elif atr_percentage < atr_percentiles[0]:  # 25th percentile
            regime = 'low'
        else:
            regime = 'normal'
        
        # Calculate volatility trend
        recent_atr = atr.iloc[-10:]
        atr_slope = np.polyfit(range(len(recent_atr)), recent_atr, 1)[0]
        volatility_trend = 'increasing' if atr_slope > 0 else 'decreasing'
        
        return {
            'regime': regime,
            'atr_current': float(current_atr),
            'atr_percentage': round(atr_percentage, 3),
            'atr_percentiles': [round(p, 3) for p in atr_percentiles],
            'volatility_trend': volatility_trend,
            'atr_slope': round(float(atr_slope), 6)
        }
    
    def _analyze_market_structure(self, price_data: pd.DataFrame) -> Dict:
        """Analyze market structure for ranging vs trending behavior"""
        closes = price_data['close']
        highs = price_data['high']
        lows = price_data['low']
        
        # Calculate recent range
        recent_data = price_data.iloc[-self.trend_lookback:]
        range_high = recent_data['high'].max()
        range_low = recent_data['low'].min()
        range_size = range_high - range_low
        
        # Calculate current position within range
        current_price = closes.iloc[-1]
        range_position = (current_price - range_low) / range_size if range_size > 0 else 0.5
        
        # Analyze price action within range
        breaks_above_mid = np.sum(closes.iloc[-20:] > (range_high + range_low) / 2)
        breaks_below_mid = np.sum(closes.iloc[-20:] < (range_high + range_low) / 2)
        
        # Calculate ranging behavior score
        range_touches = 0
        for i in range(-20, 0):
            if len(price_data) + i >= 0:
                price = closes.iloc[i]
                if abs(price - range_high) / range_size < 0.02:  # Within 2% of range high
                    range_touches += 1
                elif abs(price - range_low) / range_size < 0.02:  # Within 2% of range low
                    range_touches += 1
        
        ranging_score = min(100, range_touches * 10)
        
        # Detect breakout conditions
        current_above_range = current_price > range_high * 1.001  # 0.1% buffer
        current_below_range = current_price < range_low * 0.999
        
        if current_above_range:
            structure_state = 'upside_breakout'
        elif current_below_range:
            structure_state = 'downside_breakout'
        elif ranging_score > 50:
            structure_state = 'ranging'
        else:
            structure_state = 'transitional'
        
        # Calculate choppiness index
        choppiness = self._calculate_choppiness_index(price_data)
        
        return {
            'state': structure_state,
            'range_high': float(range_high),
            'range_low': float(range_low),
            'range_size': float(range_size),
            'range_position': round(range_position, 3),
            'ranging_score': round(ranging_score, 2),
            'choppiness_index': round(choppiness, 2),
            'range_touches': range_touches,
            'breakout_above': current_above_range,
            'breakout_below': current_below_range
        }
    
    def _analyze_volume_characteristics(self, volume_data: pd.Series) -> Dict:
        """Analyze volume characteristics"""
        if len(volume_data) < self.volatility_lookback:
            return {'error': 'Insufficient volume data'}
        
        current_volume = volume_data.iloc[-1]
        avg_volume = volume_data.iloc[-self.volatility_lookback:].mean()
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        # Volume trend
        recent_volume = volume_data.iloc[-10:]
        volume_trend_slope = np.polyfit(range(len(recent_volume)), recent_volume, 1)[0]
        volume_trend = 'increasing' if volume_trend_slope > 0 else 'decreasing'
        
        # Volume regime classification
        volume_percentiles = np.percentile(volume_data.iloc[-100:], [25, 50, 75, 90])
        
        if current_volume > volume_percentiles[3]:
            volume_regime = 'spike'
        elif current_volume > volume_percentiles[2]:
            volume_regime = 'high'
        elif current_volume < volume_percentiles[0]:
            volume_regime = 'low'
        else:
            volume_regime = 'normal'
        
        return {
            'regime': volume_regime,
            'current_volume': float(current_volume),
            'average_volume': float(avg_volume),
            'volume_ratio': round(volume_ratio, 2),
            'volume_trend': volume_trend,
            'volume_percentiles': [float(p) for p in volume_percentiles]
        }
    
    def _analyze_trading_session(self, price_data: pd.DataFrame) -> Dict:
        """Analyze current trading session characteristics"""
        if price_data.empty:
            return {'error': 'No price data provided'}
        
        # Get current time (assuming UTC)
        current_time = datetime.now()
        hour = current_time.hour
        
        # Determine session
        if 0 <= hour < 8:
            session = 'asian'
            liquidity_score = 60
        elif 8 <= hour < 13:
            session = 'london'
            liquidity_score = 90
        elif 13 <= hour < 17:
            session = 'overlap'  # London-New York overlap
            liquidity_score = 100
        elif 17 <= hour < 22:
            session = 'new_york'
            liquidity_score = 85
        else:
            session = 'off_hours'
            liquidity_score = 40
        
        # Analyze recent price action for session characteristics
        recent_data = price_data.iloc[-20:]  # Last 20 bars
        session_range = recent_data['high'].max() - recent_data['low'].min()
        avg_bar_range = (recent_data['high'] - recent_data['low']).mean()
        
        return {
            'current_session': session,
            'liquidity_score': liquidity_score,
            'session_range': float(session_range),
            'avg_bar_range': float(avg_bar_range),
            'hour_utc': hour,
            'suitable_for_trading': liquidity_score >= 70
        }
    
    def _determine_overall_state(self, 
                               trend_analysis: Dict,
                               volatility_analysis: Dict,
                               structure_analysis: Dict) -> str:
        """Determine overall market state"""
        trend_direction = trend_analysis['direction']
        volatility_regime = volatility_analysis['regime']
        structure_state = structure_analysis['state']
        choppiness = structure_analysis['choppiness_index']
        
        # High choppiness indicates difficult trading conditions
        if choppiness > self.choppy_threshold * 100:
            return 'choppy'
        
        # Breakout conditions
        if structure_state in ['upside_breakout', 'downside_breakout']:
            if volatility_regime in ['normal', 'high']:
                return 'breakout'
            else:
                return 'false_breakout_risk'
        
        # Trending conditions
        if trend_direction in ['strong_uptrend', 'strong_downtrend']:
            if volatility_regime != 'extreme':
                return 'trending'
            else:
                return 'volatile_trend'
        elif trend_direction in ['uptrend', 'downtrend']:
            return 'weak_trend'
        
        # Ranging conditions
        if structure_state == 'ranging':
            if volatility_regime == 'low':
                return 'tight_range'
            else:
                return 'ranging'
        
        # Default
        return 'transitional'
    
    def _assess_trading_suitability(self,
                                  overall_state: str,
                                  volatility_analysis: Dict,
                                  volume_analysis: Dict) -> Dict:
        """Assess suitability for signal generation"""
        
        # Base suitability scores for different market states
        state_scores = {
            'trending': 90,
            'breakout': 85,
            'ranging': 70,
            'weak_trend': 60,
            'transitional': 50,
            'volatile_trend': 40,
            'tight_range': 30,
            'choppy': 20,
            'false_breakout_risk': 15
        }
        
        base_score = state_scores.get(overall_state, 50)
        
        # Adjust for volatility
        volatility_adjustments = {
            'low': -10,
            'normal': 10,
            'high': 5,
            'extreme': -20
        }
        base_score += volatility_adjustments.get(volatility_analysis['regime'], 0)
        
        # Adjust for volume
        volume_adjustments = {
            'low': -15,
            'normal': 5,
            'high': 10,
            'spike': 0  # Can be good or bad depending on context
        }
        base_score += volume_adjustments.get(volume_analysis['regime'], 0)
        
        final_score = max(0, min(100, base_score))
        
        # Determine if suitable for signals (threshold at 60)
        suitable_for_signals = final_score >= 60
        
        # Generate recommendations
        recommendations = []
        if not suitable_for_signals:
            if overall_state == 'choppy':
                recommendations.append("Avoid signals in choppy market conditions")
            elif volatility_analysis['regime'] == 'extreme':
                recommendations.append("Wait for volatility to normalize")
            elif volume_analysis['regime'] == 'low':
                recommendations.append("Low volume - wait for better participation")
            else:
                recommendations.append("Market conditions not favorable for signals")
        else:
            recommendations.append(f"Market conditions suitable for {overall_state} strategies")
        
        return {
            'suitable_for_signals': suitable_for_signals,
            'suitability_score': round(final_score, 2),
            'recommended_signal_types': self._get_recommended_signal_types(overall_state),
            'recommendations': recommendations,
            'risk_level': self._assess_risk_level(overall_state, volatility_analysis['regime'])
        }
    
    def _get_recommended_signal_types(self, market_state: str) -> List[str]:
        """Get recommended signal types for current market state"""
        recommendations = {
            'trending': ['trend_following', 'pullback_entries'],
            'breakout': ['breakout_entries', 'momentum'],
            'ranging': ['mean_reversion', 'support_resistance'],
            'weak_trend': ['pullback_entries', 'mean_reversion'],
            'volatile_trend': ['reduced_size', 'tight_stops'],
            'transitional': ['high_confidence_only'],
            'choppy': [],  # No recommendations
            'tight_range': ['scalping_only'],
            'false_breakout_risk': []
        }
        return recommendations.get(market_state, [])
    
    def _assess_risk_level(self, market_state: str, volatility_regime: str) -> str:
        """Assess current risk level"""
        high_risk_states = ['choppy', 'false_breakout_risk', 'volatile_trend']
        high_risk_volatility = ['extreme']
        
        if market_state in high_risk_states or volatility_regime in high_risk_volatility:
            return 'high'
        elif market_state in ['transitional', 'weak_trend'] or volatility_regime == 'low':
            return 'medium'
        else:
            return 'low'
    
    # Helper methods
    def _calculate_true_range(self, price_data: pd.DataFrame) -> pd.Series:
        """Calculate True Range"""
        high = price_data['high']
        low = price_data['low']
        close_prev = price_data['close'].shift(1)
        
        tr1 = high - low
        tr2 = np.abs(high - close_prev)
        tr3 = np.abs(low - close_prev)
        
        return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    def _check_ma_alignment(self, price: float, short_ma: float, 
                           medium_ma: float, long_ma: float) -> str:
        """Check moving average alignment"""
        if price > short_ma > medium_ma > long_ma:
            return 'bullish_aligned'
        elif price < short_ma < medium_ma < long_ma:
            return 'bearish_aligned'
        elif short_ma > medium_ma > long_ma:
            return 'bullish_mas'
        elif short_ma < medium_ma < long_ma:
            return 'bearish_mas'
        else:
            return 'mixed'
    
    def _calculate_choppiness_index(self, price_data: pd.DataFrame, period: int = 20) -> float:
        """Calculate Choppiness Index"""
        if len(price_data) < period:
            return 50.0  # Neutral value
        
        recent_data = price_data.iloc[-period:]
        tr = self._calculate_true_range(recent_data)
        atr_sum = tr.sum()
        
        highest_high = recent_data['high'].max()
        lowest_low = recent_data['low'].min()
        
        if highest_high == lowest_low:
            return 100.0  # Maximum choppiness
        
        choppiness = 100 * np.log10(atr_sum / (highest_high - lowest_low)) / np.log10(period)
        return max(0.0, min(100.0, choppiness))
    
    def is_suitable_for_signals(self, market_state_analysis: Dict) -> bool:
        """Quick check if market is suitable for signal generation"""
        return market_state_analysis.get('trading_suitability', {}).get('suitable_for_signals', False)