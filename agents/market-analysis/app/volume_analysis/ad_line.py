"""
Accumulation/Distribution Line Implementation

Implements comprehensive A/D line analysis as specified in Story 3.3, Task 3:
- A/D line calculation: ((C-L)-(H-C))/(H-L) * Volume
- Cumulative A/D line for trend analysis  
- A/D line divergence detection with price action
- A/D oscillator for momentum analysis
- A/D line trend strength indicators
- A/D line breakout and breakdown signals
"""

from typing import Dict, List, Tuple, Optional, Union
import pandas as pd
import numpy as np
from decimal import Decimal
from datetime import datetime
import logging
from scipy import stats

logger = logging.getLogger(__name__)


class AccumulationDistributionLine:
    """
    Advanced Accumulation/Distribution Line analysis with divergence detection
    and momentum indicators.
    
    The A/D line measures the flow of money into or out of a security by
    combining price and volume information.
    """
    
    def __init__(self, 
                 divergence_lookback: int = 20,
                 oscillator_period: int = 14,
                 trend_periods: List[int] = None):
        """
        Initialize A/D Line analyzer.
        
        Args:
            divergence_lookback: Periods to look back for divergence detection
            oscillator_period: Period for A/D oscillator calculation
            trend_periods: List of periods for trend strength analysis
        """
        self.divergence_lookback = divergence_lookback
        self.oscillator_period = oscillator_period
        self.trend_periods = trend_periods or [10, 20, 50]
        
    def calculate_ad_line(self, price_data: pd.DataFrame, volume_data: pd.Series) -> Dict:
        """
        Calculate comprehensive A/D line analysis.
        
        Args:
            price_data: DataFrame with OHLC data
            volume_data: Series with volume data
            
        Returns:
            Dict containing A/D line values and analysis
        """
        if len(price_data) != len(volume_data):
            return {'error': 'Price and volume data length mismatch'}
        
        if len(price_data) < max(self.trend_periods):
            return {'error': f'Insufficient data - need at least {max(self.trend_periods)} periods'}
        
        # Calculate basic A/D line
        ad_values = self._calculate_raw_ad_line(price_data, volume_data)
        
        # Calculate cumulative A/D line
        cumulative_ad = self._calculate_cumulative_ad_line(ad_values)
        
        # Detect A/D line divergences with price
        divergence_analysis = self.detect_ad_divergences(
            price_data, cumulative_ad, self.divergence_lookback
        )
        
        # Calculate A/D oscillator
        ad_oscillator = self.calculate_ad_oscillator(cumulative_ad, self.oscillator_period)
        
        # Analyze trend strength
        trend_analysis = self.analyze_ad_trend_strength(cumulative_ad, self.trend_periods)
        
        # Detect breakout and breakdown signals
        signal_analysis = self.detect_ad_signals(cumulative_ad, price_data)
        
        # Money flow analysis
        money_flow_analysis = self.analyze_money_flow_patterns(ad_values, volume_data)
        
        return {
            'ad_values': ad_values,
            'cumulative_ad': cumulative_ad,
            'divergence_analysis': divergence_analysis,
            'ad_oscillator': ad_oscillator,
            'trend_analysis': trend_analysis,
            'signal_analysis': signal_analysis,
            'money_flow_analysis': money_flow_analysis,
            'current_ad_value': cumulative_ad[-1] if cumulative_ad else 0,
            'ad_trend': self._determine_current_ad_trend(cumulative_ad),
            'alerts': self._generate_ad_alerts(divergence_analysis, signal_analysis)
        }
    
    def _calculate_raw_ad_line(self, price_data: pd.DataFrame, volume_data: pd.Series) -> List[Dict]:
        """
        Calculate raw A/D line values for each period.
        
        Formula: ((Close - Low) - (High - Close)) / (High - Low) * Volume
        """
        ad_values = []
        
        for i, (idx, candle) in enumerate(price_data.iterrows()):
            high = candle['high']
            low = candle['low']
            close = candle['close']
            volume = volume_data.iloc[i]
            
            # Avoid division by zero
            if high == low:
                money_flow_multiplier = 0  # No price movement
            else:
                money_flow_multiplier = ((close - low) - (high - close)) / (high - low)
            
            money_flow_volume = money_flow_multiplier * volume
            
            ad_data = {
                'timestamp': idx,
                'index': i,
                'high': float(high),
                'low': float(low),
                'close': float(close),
                'volume': float(volume),
                'money_flow_multiplier': float(money_flow_multiplier),
                'money_flow_volume': float(money_flow_volume),
                'price_position': self._analyze_price_position(high, low, close),
                'volume_weight': float(volume) / float(volume_data.mean()) if volume_data.mean() > 0 else 1
            }
            
            ad_values.append(ad_data)
        
        return ad_values
    
    def _calculate_cumulative_ad_line(self, ad_values: List[Dict]) -> List[float]:
        """
        Calculate cumulative A/D line by summing money flow volumes.
        """
        cumulative_ad = []
        running_total = 0.0
        
        for ad_data in ad_values:
            running_total += ad_data['money_flow_volume']
            cumulative_ad.append(running_total)
        
        return cumulative_ad
    
    def detect_ad_divergences(self,
                            price_data: pd.DataFrame,
                            cumulative_ad: List[float],
                            lookback_periods: int) -> Dict:
        """
        Detect divergences between A/D line and price action.
        
        Returns:
            Dict with detected divergences and analysis
        """
        if len(price_data) < lookback_periods or len(cumulative_ad) < lookback_periods:
            return {'divergences_detected': False, 'reason': 'Insufficient data'}
        
        # Get recent data for analysis
        recent_prices = price_data['close'].iloc[-lookback_periods:].values
        recent_ad = cumulative_ad[-lookback_periods:]
        
        # Find peaks and troughs in both series
        price_peaks, price_troughs = self._find_peaks_troughs(recent_prices)
        ad_peaks, ad_troughs = self._find_peaks_troughs(recent_ad)
        
        # Detect different types of divergences
        bullish_divergences = self._detect_bullish_ad_divergences(
            recent_prices, recent_ad, price_troughs, ad_troughs
        )
        
        bearish_divergences = self._detect_bearish_ad_divergences(
            recent_prices, recent_ad, price_peaks, ad_peaks
        )
        
        # Calculate overall trend correlation
        price_trend_slope, _ = np.polyfit(range(len(recent_prices)), recent_prices, 1)
        ad_trend_slope, _ = np.polyfit(range(len(recent_ad)), recent_ad, 1)
        
        # Correlation analysis
        correlation = np.corrcoef(recent_prices, recent_ad)[0, 1]
        
        # Trend alignment analysis
        price_trend_direction = 'up' if price_trend_slope > 0 else 'down'
        ad_trend_direction = 'up' if ad_trend_slope > 0 else 'down'
        trends_aligned = price_trend_direction == ad_trend_direction
        
        all_divergences = bullish_divergences + bearish_divergences
        
        return {
            'divergences_detected': len(all_divergences) > 0,
            'total_divergences': len(all_divergences),
            'bullish_divergences': bullish_divergences,
            'bearish_divergences': bearish_divergences,
            'all_divergences': all_divergences,
            'correlation': round(correlation, 3) if not np.isnan(correlation) else 0,
            'trends_aligned': trends_aligned,
            'price_trend_direction': price_trend_direction,
            'ad_trend_direction': ad_trend_direction,
            'divergence_strength': self._calculate_divergence_strength(all_divergences),
            'trend_divergence': not trends_aligned and abs(correlation) < 0.5
        }
    
    def calculate_ad_oscillator(self, cumulative_ad: List[float], period: int) -> Dict:
        """
        Calculate A/D oscillator for momentum analysis.
        
        The oscillator shows the momentum of the A/D line.
        """
        if len(cumulative_ad) < period * 2:
            return {'error': 'Insufficient data for oscillator calculation'}
        
        # Convert to pandas series for easier calculation
        ad_series = pd.Series(cumulative_ad)
        
        # Calculate short and long EMAs of A/D line
        short_ema = ad_series.ewm(span=period//2).mean()
        long_ema = ad_series.ewm(span=period).mean()
        
        # Oscillator is the difference
        oscillator = short_ema - long_ema
        
        # Normalize oscillator to percentage
        oscillator_pct = (oscillator / ad_series.rolling(period).mean()) * 100
        
        # Calculate oscillator signals
        oscillator_signals = self._analyze_oscillator_signals(oscillator_pct)
        
        # Current oscillator state
        current_oscillator = oscillator.iloc[-1] if len(oscillator) > 0 else 0
        current_oscillator_pct = oscillator_pct.iloc[-1] if len(oscillator_pct) > 0 else 0
        
        return {
            'oscillator_values': oscillator.tolist(),
            'oscillator_pct': oscillator_pct.tolist(),
            'current_value': float(current_oscillator),
            'current_pct': float(current_oscillator_pct),
            'signals': oscillator_signals,
            'momentum_state': self._classify_momentum_state(current_oscillator_pct),
            'zero_line_crosses': self._count_zero_line_crosses(oscillator_pct)
        }
    
    def analyze_ad_trend_strength(self, cumulative_ad: List[float], periods: List[int]) -> Dict:
        """
        Analyze A/D line trend strength over multiple timeframes.
        """
        if len(cumulative_ad) < max(periods):
            return {'error': 'Insufficient data for trend analysis'}
        
        trend_analysis = {}
        
        for period in periods:
            recent_ad = cumulative_ad[-period:]
            
            # Linear regression for trend
            x = np.arange(len(recent_ad))
            slope, intercept = np.polyfit(x, recent_ad, 1)
            
            # Calculate R-squared
            y_pred = slope * x + intercept
            ss_res = np.sum((np.array(recent_ad) - y_pred) ** 2)
            ss_tot = np.sum((np.array(recent_ad) - np.mean(recent_ad)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
            
            # Trend strength (0-100)
            avg_ad = np.mean(recent_ad)
            slope_normalized = (slope / avg_ad) * 100 if avg_ad != 0 else 0
            trend_strength = min(100, abs(slope_normalized) * 10 + r_squared * 50)
            
            # Trend classification
            if slope_normalized > 0.5:
                trend_direction = 'strong_up'
            elif slope_normalized > 0.1:
                trend_direction = 'up'
            elif slope_normalized < -0.5:
                trend_direction = 'strong_down'
            elif slope_normalized < -0.1:
                trend_direction = 'down'
            else:
                trend_direction = 'sideways'
            
            trend_analysis[f'{period}_period'] = {
                'direction': trend_direction,
                'strength': round(trend_strength, 2),
                'slope': slope,
                'slope_normalized': round(slope_normalized, 3),
                'r_squared': round(r_squared, 3),
                'consistency': 'high' if r_squared > 0.7 else 'medium' if r_squared > 0.3 else 'low'
            }
        
        # Overall trend consensus
        directions = [analysis['direction'] for analysis in trend_analysis.values()]
        strength_avg = np.mean([analysis['strength'] for analysis in trend_analysis.values()])
        
        # Determine consensus
        up_trends = sum(1 for d in directions if 'up' in d)
        down_trends = sum(1 for d in directions if 'down' in d)
        
        if up_trends > down_trends:
            consensus = 'bullish'
        elif down_trends > up_trends:
            consensus = 'bearish'
        else:
            consensus = 'neutral'
        
        return {
            'trend_analysis': trend_analysis,
            'consensus': consensus,
            'average_strength': round(strength_avg, 2),
            'trend_alignment': self._check_trend_alignment(trend_analysis)
        }
    
    def detect_ad_signals(self, cumulative_ad: List[float], price_data: pd.DataFrame) -> Dict:
        """
        Detect A/D line breakout and breakdown signals.
        """
        if len(cumulative_ad) < 20:
            return {'signals_detected': False, 'reason': 'Insufficient data'}
        
        ad_series = pd.Series(cumulative_ad)
        
        # Calculate support and resistance levels for A/D line
        ad_support_resistance = self._calculate_ad_support_resistance(ad_series)
        
        # Detect breakouts/breakdowns
        current_ad = ad_series.iloc[-1]
        recent_ad = ad_series.iloc[-5:]  # Last 5 periods
        
        signals = []
        
        # Breakout above resistance
        if current_ad > ad_support_resistance['resistance']:
            if all(val <= ad_support_resistance['resistance'] for val in recent_ad.iloc[:-1]):
                signals.append({
                    'type': 'ad_breakout',
                    'level': ad_support_resistance['resistance'],
                    'current_value': current_ad,
                    'strength': self._calculate_breakout_strength(ad_series, ad_support_resistance['resistance']),
                    'price_confirmation': self._check_price_confirmation(price_data, 'up')
                })
        
        # Breakdown below support
        elif current_ad < ad_support_resistance['support']:
            if all(val >= ad_support_resistance['support'] for val in recent_ad.iloc[:-1]):
                signals.append({
                    'type': 'ad_breakdown',
                    'level': ad_support_resistance['support'],
                    'current_value': current_ad,
                    'strength': self._calculate_breakout_strength(ad_series, ad_support_resistance['support']),
                    'price_confirmation': self._check_price_confirmation(price_data, 'down')
                })
        
        # A/D line momentum signals
        momentum_signals = self._detect_ad_momentum_signals(ad_series)
        signals.extend(momentum_signals)
        
        return {
            'signals_detected': len(signals) > 0,
            'total_signals': len(signals),
            'signals': signals,
            'support_resistance': ad_support_resistance,
            'current_ad_level': float(current_ad),
            'signal_quality': self._assess_signal_quality(signals)
        }
    
    def analyze_money_flow_patterns(self, ad_values: List[Dict], volume_data: pd.Series) -> Dict:
        """
        Analyze money flow patterns from A/D calculations.
        """
        if not ad_values:
            return {'error': 'No A/D values provided'}
        
        # Extract money flow data
        money_flow_volumes = [ad['money_flow_volume'] for ad in ad_values]
        multipliers = [ad['money_flow_multiplier'] for ad in ad_values]
        
        # Positive vs negative money flow
        positive_flow = sum(mfv for mfv in money_flow_volumes if mfv > 0)
        negative_flow = sum(abs(mfv) for mfv in money_flow_volumes if mfv < 0)
        net_flow = positive_flow - negative_flow
        
        # Money flow ratio
        total_flow = positive_flow + negative_flow
        money_flow_ratio = positive_flow / total_flow if total_flow > 0 else 0.5
        
        # Analyze distribution of price positions
        price_positions = [ad['price_position'] for ad in ad_values]
        position_distribution = {
            'upper_half': sum(1 for p in price_positions if p > 0.5),
            'lower_half': sum(1 for p in price_positions if p < 0.5),
            'middle': sum(1 for p in price_positions if abs(p - 0.5) < 0.1)
        }
        
        # Volume-weighted analysis
        high_volume_periods = [ad for ad in ad_values if ad['volume_weight'] > 1.5]
        high_volume_flow = sum(ad['money_flow_volume'] for ad in high_volume_periods)
        
        # Recent money flow trend
        recent_flow = money_flow_volumes[-10:] if len(money_flow_volumes) >= 10 else money_flow_volumes
        recent_trend = 'increasing' if len(recent_flow) > 1 and recent_flow[-1] > np.mean(recent_flow[:-1]) else 'decreasing'
        
        return {
            'net_money_flow': float(net_flow),
            'positive_flow': float(positive_flow),
            'negative_flow': float(negative_flow),
            'money_flow_ratio': round(money_flow_ratio, 3),
            'flow_bias': 'accumulation' if money_flow_ratio > 0.6 else 'distribution' if money_flow_ratio < 0.4 else 'neutral',
            'position_distribution': position_distribution,
            'high_volume_flow': float(high_volume_flow),
            'recent_trend': recent_trend,
            'flow_consistency': np.std(money_flow_volumes) / np.mean(np.abs(money_flow_volumes)) if money_flow_volumes else 0,
            'dominant_pattern': self._identify_dominant_flow_pattern(ad_values)
        }
    
    # Helper methods
    def _analyze_price_position(self, high: float, low: float, close: float) -> float:
        """
        Analyze where the close price sits within the high-low range.
        Returns value between 0 (at low) and 1 (at high).
        """
        if high == low:
            return 0.5  # No range, assume middle
        return (close - low) / (high - low)
    
    def _find_peaks_troughs(self, data: Union[np.ndarray, List[float]], min_distance: int = 3) -> Tuple[List[int], List[int]]:
        """Find peaks and troughs in data series."""
        from scipy.signal import find_peaks
        
        # Convert to numpy array if needed
        if isinstance(data, list):
            data = np.array(data)
        
        # Find peaks
        peaks, _ = find_peaks(data, distance=min_distance)
        
        # Find troughs (peaks in inverted data)
        troughs, _ = find_peaks(-data, distance=min_distance)
        
        return peaks.tolist(), troughs.tolist()
    
    def _detect_bullish_ad_divergences(self,
                                     prices: np.ndarray,
                                     ad_values: List[float],
                                     price_troughs: List[int],
                                     ad_troughs: List[int]) -> List[Dict]:
        """Detect bullish A/D divergences."""
        divergences = []
        
        if len(price_troughs) < 2 or len(ad_troughs) < 2:
            return divergences
        
        for i in range(1, len(price_troughs)):
            current_price_idx = price_troughs[i]
            prev_price_idx = price_troughs[i-1]
            
            # Find corresponding A/D troughs
            current_ad_idx = min(ad_troughs, key=lambda x: abs(x - current_price_idx))
            prev_ad_idx = min(ad_troughs, key=lambda x: abs(x - prev_price_idx))
            
            # Check for bullish divergence: lower price low, higher A/D low
            if (prices[current_price_idx] < prices[prev_price_idx] and
                ad_values[current_ad_idx] > ad_values[prev_ad_idx]):
                
                divergence = {
                    'type': 'bullish',
                    'start_index': prev_price_idx,
                    'end_index': current_price_idx,
                    'price_change': prices[current_price_idx] - prices[prev_price_idx],
                    'ad_change': ad_values[current_ad_idx] - ad_values[prev_ad_idx],
                    'strength': abs(prices[current_price_idx] - prices[prev_price_idx]) + 
                               abs(ad_values[current_ad_idx] - ad_values[prev_ad_idx])
                }
                divergences.append(divergence)
        
        return divergences
    
    def _detect_bearish_ad_divergences(self,
                                     prices: np.ndarray,
                                     ad_values: List[float],
                                     price_peaks: List[int],
                                     ad_peaks: List[int]) -> List[Dict]:
        """Detect bearish A/D divergences."""
        divergences = []
        
        if len(price_peaks) < 2 or len(ad_peaks) < 2:
            return divergences
        
        for i in range(1, len(price_peaks)):
            current_price_idx = price_peaks[i]
            prev_price_idx = price_peaks[i-1]
            
            # Find corresponding A/D peaks
            current_ad_idx = min(ad_peaks, key=lambda x: abs(x - current_price_idx))
            prev_ad_idx = min(ad_peaks, key=lambda x: abs(x - prev_price_idx))
            
            # Check for bearish divergence: higher price high, lower A/D high
            if (prices[current_price_idx] > prices[prev_price_idx] and
                ad_values[current_ad_idx] < ad_values[prev_ad_idx]):
                
                divergence = {
                    'type': 'bearish',
                    'start_index': prev_price_idx,
                    'end_index': current_price_idx,
                    'price_change': prices[current_price_idx] - prices[prev_price_idx],
                    'ad_change': ad_values[current_ad_idx] - ad_values[prev_ad_idx],
                    'strength': abs(prices[current_price_idx] - prices[prev_price_idx]) + 
                               abs(ad_values[current_ad_idx] - ad_values[prev_ad_idx])
                }
                divergences.append(divergence)
        
        return divergences
    
    def _calculate_divergence_strength(self, divergences: List[Dict]) -> Dict:
        """Calculate overall strength metrics for detected divergences."""
        if not divergences:
            return {'average_strength': 0, 'max_strength': 0, 'total_count': 0}
        
        strengths = [div['strength'] for div in divergences]
        
        return {
            'average_strength': round(np.mean(strengths), 2),
            'max_strength': round(max(strengths), 2),
            'min_strength': round(min(strengths), 2),
            'total_count': len(divergences),
            'strength_distribution': {
                'strong': sum(1 for s in strengths if s > np.percentile(strengths, 75)),
                'moderate': sum(1 for s in strengths if np.percentile(strengths, 25) < s <= np.percentile(strengths, 75)),
                'weak': sum(1 for s in strengths if s <= np.percentile(strengths, 25))
            }
        }
    
    def _analyze_oscillator_signals(self, oscillator_pct: pd.Series) -> List[Dict]:
        """Analyze oscillator for trading signals."""
        signals = []
        
        if len(oscillator_pct) < 10:
            return signals
        
        # Zero line crosses
        for i in range(1, len(oscillator_pct)):
            prev_val = oscillator_pct.iloc[i-1]
            curr_val = oscillator_pct.iloc[i]
            
            # Bullish zero line cross
            if prev_val <= 0 and curr_val > 0:
                signals.append({
                    'type': 'bullish_zero_cross',
                    'index': i,
                    'value': curr_val,
                    'strength': abs(curr_val)
                })
            
            # Bearish zero line cross
            elif prev_val >= 0 and curr_val < 0:
                signals.append({
                    'type': 'bearish_zero_cross',
                    'index': i,
                    'value': curr_val,
                    'strength': abs(curr_val)
                })
        
        return signals
    
    def _classify_momentum_state(self, current_oscillator_pct: float) -> str:
        """Classify current momentum state based on oscillator."""
        if current_oscillator_pct > 5:
            return 'strong_bullish'
        elif current_oscillator_pct > 1:
            return 'bullish'
        elif current_oscillator_pct < -5:
            return 'strong_bearish'
        elif current_oscillator_pct < -1:
            return 'bearish'
        else:
            return 'neutral'
    
    def _count_zero_line_crosses(self, oscillator_pct: pd.Series) -> Dict:
        """Count zero line crosses for momentum analysis."""
        if len(oscillator_pct) < 2:
            return {'total_crosses': 0, 'bullish_crosses': 0, 'bearish_crosses': 0}
        
        total_crosses = 0
        bullish_crosses = 0
        bearish_crosses = 0
        
        for i in range(1, len(oscillator_pct)):
            prev_val = oscillator_pct.iloc[i-1]
            curr_val = oscillator_pct.iloc[i]
            
            if (prev_val <= 0 < curr_val) or (prev_val >= 0 > curr_val):
                total_crosses += 1
                if curr_val > 0:
                    bullish_crosses += 1
                else:
                    bearish_crosses += 1
        
        return {
            'total_crosses': total_crosses,
            'bullish_crosses': bullish_crosses,
            'bearish_crosses': bearish_crosses,
            'cross_frequency': total_crosses / len(oscillator_pct) if len(oscillator_pct) > 0 else 0
        }
    
    def _check_trend_alignment(self, trend_analysis: Dict) -> Dict:
        """Check if trends are aligned across different timeframes."""
        directions = [analysis['direction'] for analysis in trend_analysis.values()]
        
        bullish_count = sum(1 for d in directions if 'up' in d)
        bearish_count = sum(1 for d in directions if 'down' in d)
        neutral_count = len(directions) - bullish_count - bearish_count
        
        if bullish_count > bearish_count and bullish_count > neutral_count:
            alignment = 'bullish'
            strength = bullish_count / len(directions)
        elif bearish_count > bullish_count and bearish_count > neutral_count:
            alignment = 'bearish'
            strength = bearish_count / len(directions)
        else:
            alignment = 'mixed'
            strength = max(bullish_count, bearish_count, neutral_count) / len(directions)
        
        return {
            'alignment': alignment,
            'strength': round(strength, 2),
            'bullish_timeframes': bullish_count,
            'bearish_timeframes': bearish_count,
            'neutral_timeframes': neutral_count
        }
    
    def _calculate_ad_support_resistance(self, ad_series: pd.Series) -> Dict:
        """Calculate support and resistance levels for A/D line."""
        if len(ad_series) < 20:
            return {'support': ad_series.min(), 'resistance': ad_series.max()}
        
        # Use recent 20 periods for S/R calculation
        recent_ad = ad_series.iloc[-20:]
        
        # Simple S/R based on recent range
        support = recent_ad.min()
        resistance = recent_ad.max()
        
        # More sophisticated S/R using clustering (simplified)
        q25 = recent_ad.quantile(0.25)
        q75 = recent_ad.quantile(0.75)
        
        return {
            'support': min(support, q25),
            'resistance': max(resistance, q75),
            'range_pct': ((resistance - support) / abs(support)) * 100 if support != 0 else 0
        }
    
    def _calculate_breakout_strength(self, ad_series: pd.Series, level: float) -> float:
        """Calculate the strength of an A/D line breakout."""
        current_value = ad_series.iloc[-1]
        distance_from_level = abs(current_value - level)
        
        # Normalize by recent volatility
        recent_volatility = ad_series.iloc[-20:].std() if len(ad_series) >= 20 else ad_series.std()
        
        if recent_volatility == 0:
            return 50  # Default moderate strength
        
        strength = min(100, (distance_from_level / recent_volatility) * 20)
        return round(strength, 2)
    
    def _check_price_confirmation(self, price_data: pd.DataFrame, direction: str) -> Dict:
        """Check if price action confirms A/D line signal."""
        if len(price_data) < 5:
            return {'confirmed': False, 'reason': 'Insufficient price data'}
        
        recent_prices = price_data['close'].iloc[-5:]
        price_change = recent_prices.iloc[-1] - recent_prices.iloc[0]
        
        if direction == 'up':
            confirmed = price_change > 0
        else:  # direction == 'down'
            confirmed = price_change < 0
        
        return {
            'confirmed': confirmed,
            'price_change': float(price_change),
            'price_change_pct': (price_change / recent_prices.iloc[0]) * 100 if recent_prices.iloc[0] != 0 else 0
        }
    
    def _detect_ad_momentum_signals(self, ad_series: pd.Series) -> List[Dict]:
        """Detect momentum signals from A/D line."""
        signals = []
        
        if len(ad_series) < 10:
            return signals
        
        # Calculate momentum (rate of change)
        momentum = ad_series.diff(5)  # 5-period momentum
        
        # Recent momentum analysis
        if len(momentum) > 0:
            recent_momentum = momentum.iloc[-1]
            avg_momentum = momentum.iloc[-10:].mean() if len(momentum) >= 10 else momentum.mean()
            
            # Strong momentum signals
            if recent_momentum > avg_momentum * 2:
                signals.append({
                    'type': 'strong_momentum_up',
                    'momentum_value': float(recent_momentum),
                    'strength': min(100, abs(recent_momentum / avg_momentum) * 20)
                })
            elif recent_momentum < avg_momentum * 2:
                signals.append({
                    'type': 'strong_momentum_down',
                    'momentum_value': float(recent_momentum),
                    'strength': min(100, abs(recent_momentum / avg_momentum) * 20)
                })
        
        return signals
    
    def _assess_signal_quality(self, signals: List[Dict]) -> Dict:
        """Assess overall quality of detected signals."""
        if not signals:
            return {'quality': 'no_signals', 'score': 0}
        
        # Calculate average strength
        strengths = [s.get('strength', 50) for s in signals]
        avg_strength = np.mean(strengths)
        
        # Count signal types
        signal_types = [s['type'] for s in signals]
        type_diversity = len(set(signal_types))
        
        # Quality score
        quality_score = (avg_strength + type_diversity * 10) / 2
        
        if quality_score >= 70:
            quality = 'high'
        elif quality_score >= 40:
            quality = 'medium'
        else:
            quality = 'low'
        
        return {
            'quality': quality,
            'score': round(quality_score, 2),
            'signal_count': len(signals),
            'avg_strength': round(avg_strength, 2),
            'type_diversity': type_diversity
        }
    
    def _identify_dominant_flow_pattern(self, ad_values: List[Dict]) -> str:
        """Identify dominant money flow pattern."""
        if len(ad_values) < 10:
            return 'insufficient_data'
        
        # Analyze recent patterns
        recent_flows = [ad['money_flow_volume'] for ad in ad_values[-10:]]
        positive_flows = [f for f in recent_flows if f > 0]
        negative_flows = [f for f in recent_flows if f < 0]
        
        if len(positive_flows) > len(negative_flows) * 1.5:
            return 'accumulation_dominant'
        elif len(negative_flows) > len(positive_flows) * 1.5:
            return 'distribution_dominant'
        else:
            return 'balanced_flow'
    
    def _determine_current_ad_trend(self, cumulative_ad: List[float]) -> str:
        """Determine current A/D line trend."""
        if len(cumulative_ad) < 5:
            return 'insufficient_data'
        
        recent_ad = cumulative_ad[-5:]
        slope, _ = np.polyfit(range(len(recent_ad)), recent_ad, 1)
        
        if slope > 0:
            return 'uptrend'
        elif slope < 0:
            return 'downtrend'
        else:
            return 'sideways'
    
    def _generate_ad_alerts(self, divergence_analysis: Dict, signal_analysis: Dict) -> List[Dict]:
        """Generate alerts from A/D line analysis."""
        alerts = []
        
        # Divergence alerts
        if divergence_analysis.get('divergences_detected', False):
            strong_divergences = [
                div for div in divergence_analysis.get('all_divergences', [])
                if div.get('strength', 0) > 50
            ]
            
            for div in strong_divergences:
                alerts.append({
                    'type': 'ad_divergence',
                    'divergence_type': div['type'],
                    'strength': div['strength'],
                    'message': f"{div['type'].title()} A/D divergence detected with strength {div['strength']:.1f}",
                    'priority': 'high' if div['strength'] > 75 else 'medium'
                })
        
        # Signal alerts
        if signal_analysis.get('signals_detected', False):
            high_quality_signals = [
                sig for sig in signal_analysis.get('signals', [])
                if sig.get('strength', 0) > 60
            ]
            
            for sig in high_quality_signals:
                alerts.append({
                    'type': 'ad_signal',
                    'signal_type': sig['type'],
                    'strength': sig.get('strength', 0),
                    'message': f"A/D line {sig['type']} signal detected",
                    'priority': 'medium'
                })
        
        return alerts