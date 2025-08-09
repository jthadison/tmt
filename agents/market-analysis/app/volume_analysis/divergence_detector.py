"""
Volume Divergence Detection System

Implements comprehensive volume divergence analysis as specified in Story 3.3, Task 2:
- Bullish divergence: price makes lower low, volume makes higher low
- Bearish divergence: price makes higher high, volume makes lower high  
- Hidden divergence detection for trend continuation
- Multi-timeframe validation
- Divergence outcome tracking
"""

from typing import Dict, List, Tuple, Optional
import pandas as pd
import numpy as np
from decimal import Decimal
from datetime import datetime
import logging
from scipy.signal import find_peaks

logger = logging.getLogger(__name__)


class VolumeDivergenceDetector:
    """
    Advanced volume divergence detection with multi-timeframe analysis.
    
    Detects regular and hidden divergences between price and volume
    with strength scoring and outcome validation.
    """
    
    def __init__(self, 
                 lookback_window: int = 50,
                 min_peak_distance: int = 5,
                 peak_prominence: float = 0.1):
        """
        Initialize divergence detector.
        
        Args:
            lookback_window: Number of periods to analyze for divergences
            min_peak_distance: Minimum distance between peaks/troughs
            peak_prominence: Minimum prominence for peak detection
        """
        self.lookback_window = lookback_window
        self.min_peak_distance = min_peak_distance
        self.peak_prominence = peak_prominence
        
    def detect_divergences(self, 
                         price_data: pd.DataFrame, 
                         volume_data: pd.Series,
                         timeframes: List[str] = None) -> Dict:
        """
        Detect all types of volume divergences with multi-timeframe analysis.
        
        Args:
            price_data: DataFrame with OHLC data
            volume_data: Series with volume data
            timeframes: Optional list of timeframes for validation
            
        Returns:
            Dict containing all detected divergences with classifications
        """
        if len(price_data) != len(volume_data):
            return {'error': 'Price and volume data length mismatch'}
            
        if len(price_data) < self.lookback_window:
            return {'error': f'Insufficient data - need at least {self.lookback_window} periods'}
        
        # Extract recent data for analysis
        recent_price = price_data.iloc[-self.lookback_window:]
        recent_volume = volume_data.iloc[-self.lookback_window:]
        
        # Find price and volume extremes
        price_peaks, price_troughs = self.find_price_extremes(recent_price)
        volume_peaks, volume_troughs = self.find_volume_extremes(recent_volume)
        
        # Detect different types of divergences
        regular_bullish = self.detect_regular_bullish_divergence(
            recent_price, recent_volume, price_troughs, volume_troughs
        )
        
        regular_bearish = self.detect_regular_bearish_divergence(
            recent_price, recent_volume, price_peaks, volume_peaks
        )
        
        hidden_bullish = self.detect_hidden_bullish_divergence(
            recent_price, recent_volume, price_troughs, volume_troughs
        )
        
        hidden_bearish = self.detect_hidden_bearish_divergence(
            recent_price, recent_volume, price_peaks, volume_peaks
        )
        
        # Combine all divergences
        all_divergences = (regular_bullish + regular_bearish + 
                          hidden_bullish + hidden_bearish)
        
        # Validate with multiple timeframes if provided
        if timeframes:
            for div in all_divergences:
                div['timeframe_validation'] = self.validate_multiframe(div, timeframes)
        
        # Analyze divergence patterns
        pattern_analysis = self.analyze_divergence_patterns(all_divergences)
        
        return {
            'total_divergences': len(all_divergences),
            'regular_bullish': regular_bullish,
            'regular_bearish': regular_bearish,
            'hidden_bullish': hidden_bullish,
            'hidden_bearish': hidden_bearish,
            'all_divergences': all_divergences,
            'pattern_analysis': pattern_analysis,
            'strength_distribution': self._analyze_strength_distribution(all_divergences),
            'recent_divergences': self._get_recent_divergences(all_divergences),
            'alerts': self._generate_divergence_alerts(all_divergences)
        }
    
    def find_price_extremes(self, price_data: pd.DataFrame) -> Tuple[List[Dict], List[Dict]]:
        """
        Find price peaks and troughs using sophisticated peak detection.
        
        Returns:
            Tuple of (peaks, troughs) as lists of dicts with index, value, timestamp
        """
        closes = price_data['close'].values
        highs = price_data['high'].values
        lows = price_data['low'].values
        
        # Find peaks in highs
        peak_indices, peak_props = find_peaks(
            highs, 
            distance=self.min_peak_distance,
            prominence=self.peak_prominence * np.std(highs)
        )
        
        # Find troughs in lows (peaks in inverted data)
        trough_indices, trough_props = find_peaks(
            -lows,
            distance=self.min_peak_distance, 
            prominence=self.peak_prominence * np.std(lows)
        )
        
        peaks = []
        for i in peak_indices:
            peaks.append({
                'index': i,
                'global_index': price_data.index[i],
                'price': highs[i],
                'close_price': closes[i],
                'timestamp': price_data.index[i],
                'type': 'peak'
            })
        
        troughs = []
        for i in trough_indices:
            troughs.append({
                'index': i,
                'global_index': price_data.index[i],
                'price': lows[i],
                'close_price': closes[i], 
                'timestamp': price_data.index[i],
                'type': 'trough'
            })
        
        return peaks, troughs
    
    def find_volume_extremes(self, volume_data: pd.Series) -> Tuple[List[Dict], List[Dict]]:
        """
        Find volume peaks and troughs.
        
        Returns:
            Tuple of (peaks, troughs) as lists of dicts with index, value, timestamp
        """
        volumes = volume_data.values
        
        # Find volume peaks
        peak_indices, peak_props = find_peaks(
            volumes,
            distance=self.min_peak_distance,
            prominence=self.peak_prominence * np.std(volumes)
        )
        
        # Find volume troughs (peaks in inverted data)
        trough_indices, trough_props = find_peaks(
            -volumes,
            distance=self.min_peak_distance,
            prominence=self.peak_prominence * np.std(volumes)
        )
        
        peaks = []
        for i in peak_indices:
            peaks.append({
                'index': i,
                'global_index': volume_data.index[i],
                'volume': volumes[i],
                'timestamp': volume_data.index[i],
                'type': 'peak'
            })
        
        troughs = []
        for i in trough_indices:
            troughs.append({
                'index': i,
                'global_index': volume_data.index[i],
                'volume': volumes[i],
                'timestamp': volume_data.index[i],
                'type': 'trough'
            })
        
        return peaks, troughs
    
    def detect_regular_bullish_divergence(self,
                                        price_data: pd.DataFrame,
                                        volume_data: pd.Series,
                                        price_troughs: List[Dict],
                                        volume_troughs: List[Dict]) -> List[Dict]:
        """
        Detect regular bullish divergence: price makes lower low, volume makes higher low.
        """
        divergences = []
        
        # Need at least 2 troughs for comparison
        if len(price_troughs) < 2 or len(volume_troughs) < 2:
            return divergences
        
        # Compare consecutive price troughs
        for i in range(1, len(price_troughs)):
            current_price_trough = price_troughs[i]
            previous_price_trough = price_troughs[i-1]
            
            # Check if price made lower low
            if current_price_trough['price'] < previous_price_trough['price']:
                
                # Find corresponding volume troughs around the same time
                current_vol_trough = self._find_nearest_extreme(
                    volume_troughs, current_price_trough['index'], tolerance=5
                )
                previous_vol_trough = self._find_nearest_extreme(
                    volume_troughs, previous_price_trough['index'], tolerance=5
                )
                
                if current_vol_trough and previous_vol_trough:
                    # Check if volume made higher low
                    if current_vol_trough['volume'] > previous_vol_trough['volume']:
                        
                        # Calculate divergence strength
                        price_change_pct = ((current_price_trough['price'] - previous_price_trough['price']) / 
                                          previous_price_trough['price']) * 100
                        volume_change_pct = ((current_vol_trough['volume'] - previous_vol_trough['volume']) / 
                                           previous_vol_trough['volume']) * 100
                        
                        strength = self.calculate_divergence_strength(
                            price_change_pct, volume_change_pct, 'bullish'
                        )
                        
                        # Validate divergence quality
                        validation = self.validate_divergence_quality(
                            price_data, volume_data, current_price_trough, previous_price_trough
                        )
                        
                        divergence = {
                            'type': 'regular_bullish',
                            'start_timestamp': previous_price_trough['timestamp'],
                            'end_timestamp': current_price_trough['timestamp'],
                            'price_trough_1': previous_price_trough,
                            'price_trough_2': current_price_trough,
                            'volume_trough_1': previous_vol_trough,
                            'volume_trough_2': current_vol_trough,
                            'price_change_pct': price_change_pct,
                            'volume_change_pct': volume_change_pct,
                            'strength': strength,
                            'validation': validation,
                            'confidence': self.calculate_divergence_confidence(strength, validation),
                            'outcome_tracking': self.track_divergence_outcome(
                                price_data, current_price_trough['index'], 'bullish'
                            )
                        }
                        
                        divergences.append(divergence)
        
        return divergences
    
    def detect_regular_bearish_divergence(self,
                                        price_data: pd.DataFrame,
                                        volume_data: pd.Series,
                                        price_peaks: List[Dict],
                                        volume_peaks: List[Dict]) -> List[Dict]:
        """
        Detect regular bearish divergence: price makes higher high, volume makes lower high.
        """
        divergences = []
        
        # Need at least 2 peaks for comparison
        if len(price_peaks) < 2 or len(volume_peaks) < 2:
            return divergences
        
        # Compare consecutive price peaks
        for i in range(1, len(price_peaks)):
            current_price_peak = price_peaks[i]
            previous_price_peak = price_peaks[i-1]
            
            # Check if price made higher high
            if current_price_peak['price'] > previous_price_peak['price']:
                
                # Find corresponding volume peaks around the same time
                current_vol_peak = self._find_nearest_extreme(
                    volume_peaks, current_price_peak['index'], tolerance=5
                )
                previous_vol_peak = self._find_nearest_extreme(
                    volume_peaks, previous_price_peak['index'], tolerance=5
                )
                
                if current_vol_peak and previous_vol_peak:
                    # Check if volume made lower high
                    if current_vol_peak['volume'] < previous_vol_peak['volume']:
                        
                        # Calculate divergence strength
                        price_change_pct = ((current_price_peak['price'] - previous_price_peak['price']) / 
                                          previous_price_peak['price']) * 100
                        volume_change_pct = ((current_vol_peak['volume'] - previous_vol_peak['volume']) / 
                                           previous_vol_peak['volume']) * 100
                        
                        strength = self.calculate_divergence_strength(
                            price_change_pct, volume_change_pct, 'bearish'
                        )
                        
                        # Validate divergence quality
                        validation = self.validate_divergence_quality(
                            price_data, volume_data, current_price_peak, previous_price_peak
                        )
                        
                        divergence = {
                            'type': 'regular_bearish',
                            'start_timestamp': previous_price_peak['timestamp'],
                            'end_timestamp': current_price_peak['timestamp'],
                            'price_peak_1': previous_price_peak,
                            'price_peak_2': current_price_peak,
                            'volume_peak_1': previous_vol_peak,
                            'volume_peak_2': current_vol_peak,
                            'price_change_pct': price_change_pct,
                            'volume_change_pct': volume_change_pct,
                            'strength': strength,
                            'validation': validation,
                            'confidence': self.calculate_divergence_confidence(strength, validation),
                            'outcome_tracking': self.track_divergence_outcome(
                                price_data, current_price_peak['index'], 'bearish'
                            )
                        }
                        
                        divergences.append(divergence)
        
        return divergences
    
    def detect_hidden_bullish_divergence(self,
                                       price_data: pd.DataFrame,
                                       volume_data: pd.Series,
                                       price_troughs: List[Dict],
                                       volume_troughs: List[Dict]) -> List[Dict]:
        """
        Detect hidden bullish divergence: price makes higher low, volume makes lower low.
        
        This pattern indicates trend continuation in an uptrend.
        """
        divergences = []
        
        if len(price_troughs) < 2 or len(volume_troughs) < 2:
            return divergences
        
        for i in range(1, len(price_troughs)):
            current_price_trough = price_troughs[i]
            previous_price_trough = price_troughs[i-1]
            
            # Check if price made higher low (continuation pattern)
            if current_price_trough['price'] > previous_price_trough['price']:
                
                current_vol_trough = self._find_nearest_extreme(
                    volume_troughs, current_price_trough['index'], tolerance=5
                )
                previous_vol_trough = self._find_nearest_extreme(
                    volume_troughs, previous_price_trough['index'], tolerance=5
                )
                
                if current_vol_trough and previous_vol_trough:
                    # Check if volume made lower low
                    if current_vol_trough['volume'] < previous_vol_trough['volume']:
                        
                        price_change_pct = ((current_price_trough['price'] - previous_price_trough['price']) / 
                                          previous_price_trough['price']) * 100
                        volume_change_pct = ((current_vol_trough['volume'] - previous_vol_trough['volume']) / 
                                           previous_vol_trough['volume']) * 100
                        
                        strength = self.calculate_divergence_strength(
                            price_change_pct, volume_change_pct, 'hidden_bullish'
                        )
                        
                        validation = self.validate_divergence_quality(
                            price_data, volume_data, current_price_trough, previous_price_trough
                        )
                        
                        divergence = {
                            'type': 'hidden_bullish',
                            'start_timestamp': previous_price_trough['timestamp'],
                            'end_timestamp': current_price_trough['timestamp'],
                            'price_trough_1': previous_price_trough,
                            'price_trough_2': current_price_trough,
                            'volume_trough_1': previous_vol_trough,
                            'volume_trough_2': current_vol_trough,
                            'price_change_pct': price_change_pct,
                            'volume_change_pct': volume_change_pct,
                            'strength': strength,
                            'validation': validation,
                            'confidence': self.calculate_divergence_confidence(strength, validation),
                            'continuation_signal': True,
                            'outcome_tracking': self.track_divergence_outcome(
                                price_data, current_price_trough['index'], 'continuation_bullish'
                            )
                        }
                        
                        divergences.append(divergence)
        
        return divergences
    
    def detect_hidden_bearish_divergence(self,
                                       price_data: pd.DataFrame,
                                       volume_data: pd.Series,
                                       price_peaks: List[Dict],
                                       volume_peaks: List[Dict]) -> List[Dict]:
        """
        Detect hidden bearish divergence: price makes lower high, volume makes higher high.
        
        This pattern indicates trend continuation in a downtrend.
        """
        divergences = []
        
        if len(price_peaks) < 2 or len(volume_peaks) < 2:
            return divergences
        
        for i in range(1, len(price_peaks)):
            current_price_peak = price_peaks[i]
            previous_price_peak = price_peaks[i-1]
            
            # Check if price made lower high (continuation pattern)
            if current_price_peak['price'] < previous_price_peak['price']:
                
                current_vol_peak = self._find_nearest_extreme(
                    volume_peaks, current_price_peak['index'], tolerance=5
                )
                previous_vol_peak = self._find_nearest_extreme(
                    volume_peaks, previous_price_peak['index'], tolerance=5
                )
                
                if current_vol_peak and previous_vol_peak:
                    # Check if volume made higher high
                    if current_vol_peak['volume'] > previous_vol_peak['volume']:
                        
                        price_change_pct = ((current_price_peak['price'] - previous_price_peak['price']) / 
                                          previous_price_peak['price']) * 100
                        volume_change_pct = ((current_vol_peak['volume'] - previous_vol_peak['volume']) / 
                                           previous_vol_peak['volume']) * 100
                        
                        strength = self.calculate_divergence_strength(
                            price_change_pct, volume_change_pct, 'hidden_bearish'
                        )
                        
                        validation = self.validate_divergence_quality(
                            price_data, volume_data, current_price_peak, previous_price_peak
                        )
                        
                        divergence = {
                            'type': 'hidden_bearish',
                            'start_timestamp': previous_price_peak['timestamp'],
                            'end_timestamp': current_price_peak['timestamp'],
                            'price_peak_1': previous_price_peak,
                            'price_peak_2': current_price_peak,
                            'volume_peak_1': previous_vol_peak,
                            'volume_peak_2': current_vol_peak,
                            'price_change_pct': price_change_pct,
                            'volume_change_pct': volume_change_pct,
                            'strength': strength,
                            'validation': validation,
                            'confidence': self.calculate_divergence_confidence(strength, validation),
                            'continuation_signal': True,
                            'outcome_tracking': self.track_divergence_outcome(
                                price_data, current_price_peak['index'], 'continuation_bearish'
                            )
                        }
                        
                        divergences.append(divergence)
        
        return divergences
    
    def calculate_divergence_strength(self, 
                                    price_change_pct: float, 
                                    volume_change_pct: float, 
                                    div_type: str) -> Dict:
        """
        Calculate the strength of a detected divergence.
        
        Returns:
            Dict with strength metrics and classification
        """
        # Magnitude of price and volume changes
        price_magnitude = abs(price_change_pct)
        volume_magnitude = abs(volume_change_pct)
        
        # Divergence intensity (how opposite the directions are)
        if div_type in ['regular_bullish', 'hidden_bullish']:
            # For bullish: more negative price, more positive volume = stronger
            if div_type == 'regular_bullish':
                divergence_intensity = abs(price_change_pct) + volume_change_pct
            else:  # hidden_bullish
                divergence_intensity = price_change_pct + abs(volume_change_pct)
        else:
            # For bearish: more positive price, more negative volume = stronger
            if div_type == 'regular_bearish':
                divergence_intensity = price_change_pct + abs(volume_change_pct)
            else:  # hidden_bearish
                divergence_intensity = abs(price_change_pct) + volume_change_pct
        
        # Strength score (0-100)
        strength_score = min(100, (price_magnitude + volume_magnitude) * 2)
        
        # Classify strength
        if strength_score >= 75:
            strength_class = 'very_strong'
        elif strength_score >= 50:
            strength_class = 'strong'  
        elif strength_score >= 25:
            strength_class = 'moderate'
        else:
            strength_class = 'weak'
        
        return {
            'score': strength_score,
            'classification': strength_class,
            'price_magnitude': price_magnitude,
            'volume_magnitude': volume_magnitude,
            'divergence_intensity': divergence_intensity
        }
    
    def validate_divergence_quality(self,
                                  price_data: pd.DataFrame,
                                  volume_data: pd.Series,
                                  current_extreme: Dict,
                                  previous_extreme: Dict) -> Dict:
        """
        Validate the quality and reliability of a detected divergence.
        """
        validation_score = 0
        validation_factors = []
        
        # Time separation validation (extremes shouldn't be too close)
        time_separation = current_extreme['index'] - previous_extreme['index']
        if time_separation >= 10:
            validation_score += 25
            validation_factors.append('adequate_time_separation')
        elif time_separation >= 5:
            validation_score += 15
            validation_factors.append('moderate_time_separation')
        
        # Trend context validation
        trend_context = self._analyze_trend_between_extremes(
            price_data, previous_extreme['index'], current_extreme['index']
        )
        if trend_context['consistent_trend']:
            validation_score += 20
            validation_factors.append('consistent_trend')
        
        # Volume pattern validation (volume should show clear pattern)
        volume_pattern = self._analyze_volume_pattern_between_extremes(
            volume_data, previous_extreme['index'], current_extreme['index']
        )
        if volume_pattern['clear_pattern']:
            validation_score += 20
            validation_factors.append('clear_volume_pattern')
        
        # Market structure validation (clean swings)
        structure_validation = self._validate_market_structure(
            price_data, previous_extreme['index'], current_extreme['index']
        )
        if structure_validation['clean_structure']:
            validation_score += 15
            validation_factors.append('clean_market_structure')
        
        # Magnitude validation (changes should be significant)
        price_change = abs(current_extreme['price'] - previous_extreme['price'])
        avg_price = (current_extreme['price'] + previous_extreme['price']) / 2
        if price_change / avg_price > 0.01:  # 1% minimum change
            validation_score += 20
            validation_factors.append('significant_price_change')
        
        return {
            'score': validation_score,
            'factors': validation_factors,
            'time_separation': time_separation,
            'trend_context': trend_context,
            'volume_pattern': volume_pattern,
            'structure_validation': structure_validation
        }
    
    def calculate_divergence_confidence(self, strength: Dict, validation: Dict) -> float:
        """
        Calculate overall confidence score for divergence (0-100).
        """
        # Weight strength and validation scores
        strength_weight = 0.6
        validation_weight = 0.4
        
        confidence = (strength['score'] * strength_weight + 
                     validation['score'] * validation_weight)
        
        return round(min(100, max(0, confidence)), 2)
    
    def track_divergence_outcome(self,
                               price_data: pd.DataFrame,
                               divergence_index: int,
                               expected_direction: str) -> Dict:
        """
        Track the outcome of a divergence signal for strategy validation.
        
        Looks forward to see if the divergence led to the expected price movement.
        """
        # Look forward up to 20 periods
        lookforward_periods = min(20, len(price_data) - divergence_index - 1)
        
        if lookforward_periods < 3:
            return {'outcome': 'insufficient_data'}
        
        divergence_price = price_data.iloc[divergence_index]['close']
        future_prices = price_data.iloc[divergence_index+1:divergence_index+1+lookforward_periods]
        
        if len(future_prices) == 0:
            return {'outcome': 'no_future_data'}
        
        # Calculate price movements
        max_future_price = future_prices['high'].max()
        min_future_price = future_prices['low'].min()
        final_price = future_prices['close'].iloc[-1]
        
        max_gain_pct = ((max_future_price - divergence_price) / divergence_price) * 100
        max_loss_pct = ((min_future_price - divergence_price) / divergence_price) * 100
        final_change_pct = ((final_price - divergence_price) / divergence_price) * 100
        
        # Determine outcome based on expected direction
        if expected_direction in ['bullish', 'continuation_bullish']:
            if max_gain_pct > 2.0:  # At least 2% gain
                outcome = 'successful'
            elif max_loss_pct < -2.0:  # More than 2% loss
                outcome = 'failed'
            else:
                outcome = 'neutral'
        else:  # bearish or continuation_bearish
            if max_loss_pct < -2.0:  # At least 2% decline
                outcome = 'successful'
            elif max_gain_pct > 2.0:  # More than 2% gain
                outcome = 'failed'
            else:
                outcome = 'neutral'
        
        return {
            'outcome': outcome,
            'max_gain_pct': max_gain_pct,
            'max_loss_pct': max_loss_pct,
            'final_change_pct': final_change_pct,
            'periods_tracked': lookforward_periods,
            'expected_direction': expected_direction
        }
    
    def validate_multiframe(self, divergence: Dict, timeframes: List[str]) -> Dict:
        """
        Validate divergence across multiple timeframes.
        
        This is a placeholder for multi-timeframe validation that would
        require additional timeframe data.
        """
        # Placeholder implementation - would need actual multi-timeframe data
        return {
            'validated_timeframes': [],
            'confirmation_score': 0,
            'note': 'Multi-timeframe validation requires additional data'
        }
    
    def analyze_divergence_patterns(self, divergences: List[Dict]) -> Dict:
        """
        Analyze patterns and trends in detected divergences.
        """
        if not divergences:
            return {'pattern': 'no_divergences'}
        
        # Count by type
        type_counts = {}
        for div in divergences:
            div_type = div['type']
            type_counts[div_type] = type_counts.get(div_type, 0) + 1
        
        # Analyze success rates
        successful_outcomes = sum(1 for div in divergences 
                                if div.get('outcome_tracking', {}).get('outcome') == 'successful')
        success_rate = (successful_outcomes / len(divergences)) * 100 if divergences else 0
        
        # Find dominant pattern
        if type_counts:
            dominant_type = max(type_counts.items(), key=lambda x: x[1])
        else:
            dominant_type = ('none', 0)
        
        return {
            'total_divergences': len(divergences),
            'type_distribution': type_counts,
            'dominant_pattern': dominant_type[0],
            'success_rate': round(success_rate, 2),
            'avg_strength': np.mean([div['strength']['score'] for div in divergences]),
            'avg_confidence': np.mean([div['confidence'] for div in divergences])
        }
    
    # Helper methods
    def _find_nearest_extreme(self, extremes: List[Dict], target_index: int, tolerance: int = 5) -> Optional[Dict]:
        """Find the nearest extreme point within tolerance."""
        best_extreme = None
        min_distance = float('inf')
        
        for extreme in extremes:
            distance = abs(extreme['index'] - target_index)
            if distance <= tolerance and distance < min_distance:
                min_distance = distance
                best_extreme = extreme
        
        return best_extreme
    
    def _analyze_strength_distribution(self, divergences: List[Dict]) -> Dict:
        """Analyze the distribution of divergence strengths."""
        if not divergences:
            return {}
        
        strengths = [div['strength']['score'] for div in divergences]
        
        return {
            'mean': np.mean(strengths),
            'median': np.median(strengths),
            'std_dev': np.std(strengths),
            'min': min(strengths),
            'max': max(strengths),
            'strong_divergences': sum(1 for s in strengths if s >= 50)
        }
    
    def _get_recent_divergences(self, divergences: List[Dict], lookback: int = 10) -> List[Dict]:
        """Get divergences from recent periods."""
        if not divergences:
            return []
        
        # Sort by end timestamp and get most recent
        sorted_divs = sorted(divergences, key=lambda x: x['end_timestamp'], reverse=True)
        return sorted_divs[:lookback]
    
    def _generate_divergence_alerts(self, divergences: List[Dict]) -> List[Dict]:
        """Generate trading alerts for high-confidence divergences."""
        alerts = []
        
        high_confidence_divs = [div for div in divergences if div['confidence'] >= 60]
        
        for div in high_confidence_divs:
            alert = {
                'timestamp': div['end_timestamp'],
                'alert_type': 'volume_divergence',
                'divergence_type': div['type'],
                'confidence': div['confidence'],
                'strength': div['strength']['classification'],
                'message': self._generate_divergence_alert_message(div),
                'expected_direction': self._get_expected_direction(div['type']),
                'risk_level': self._assess_risk_level(div)
            }
            alerts.append(alert)
        
        return alerts
    
    def _analyze_trend_between_extremes(self, price_data: pd.DataFrame, start_idx: int, end_idx: int) -> Dict:
        """Analyze trend consistency between two extreme points."""
        if end_idx <= start_idx:
            return {'consistent_trend': False}
        
        period_data = price_data.iloc[start_idx:end_idx+1]
        closes = period_data['close'].values
        
        # Linear regression to find trend
        x = np.arange(len(closes))
        slope, _ = np.polyfit(x, closes, 1)
        
        # Calculate R-squared
        y_pred = np.polyval([slope, closes[0]], x)
        ss_res = np.sum((closes - y_pred) ** 2)
        ss_tot = np.sum((closes - np.mean(closes)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        
        consistent_trend = r_squared > 0.3  # 30% correlation threshold
        
        return {
            'consistent_trend': consistent_trend,
            'slope': slope,
            'r_squared': r_squared,
            'trend_direction': 'up' if slope > 0 else 'down'
        }
    
    def _analyze_volume_pattern_between_extremes(self, volume_data: pd.Series, start_idx: int, end_idx: int) -> Dict:
        """Analyze volume pattern between extreme points."""
        if end_idx <= start_idx:
            return {'clear_pattern': False}
        
        period_volume = volume_data.iloc[start_idx:end_idx+1]
        
        # Check for clear pattern (increasing, decreasing, or stable)
        first_half = period_volume.iloc[:len(period_volume)//2]
        second_half = period_volume.iloc[len(period_volume)//2:]
        
        first_avg = first_half.mean()
        second_avg = second_half.mean()
        
        change_pct = abs((second_avg - first_avg) / first_avg) * 100 if first_avg > 0 else 0
        clear_pattern = change_pct > 20  # 20% change threshold
        
        return {
            'clear_pattern': clear_pattern,
            'pattern_strength': change_pct,
            'pattern_direction': 'increasing' if second_avg > first_avg else 'decreasing'
        }
    
    def _validate_market_structure(self, price_data: pd.DataFrame, start_idx: int, end_idx: int) -> Dict:
        """Validate clean market structure between extreme points."""
        if end_idx <= start_idx:
            return {'clean_structure': False}
        
        period_data = price_data.iloc[start_idx:end_idx+1]
        
        # Check for excessive whipsaws or noise
        price_changes = period_data['close'].pct_change().dropna()
        volatility = price_changes.std()
        
        # Clean structure has moderate volatility (not too choppy)
        clean_structure = volatility < 0.05  # 5% daily volatility threshold
        
        return {
            'clean_structure': clean_structure,
            'volatility': volatility,
            'structure_quality': 'clean' if clean_structure else 'noisy'
        }
    
    def _generate_divergence_alert_message(self, divergence: Dict) -> str:
        """Generate human-readable alert message for divergence."""
        div_type = divergence['type'].replace('_', ' ').title()
        confidence = divergence['confidence']
        strength = divergence['strength']['classification']
        
        return f"{div_type} divergence detected (Confidence: {confidence}%, Strength: {strength})"
    
    def _get_expected_direction(self, div_type: str) -> str:
        """Get expected price direction for divergence type."""
        if 'bullish' in div_type:
            return 'up'
        elif 'bearish' in div_type:
            return 'down'
        else:
            return 'neutral'
    
    def _assess_risk_level(self, divergence: Dict) -> str:
        """Assess risk level for divergence signal."""
        confidence = divergence['confidence']
        validation_score = divergence['validation']['score']
        
        if confidence >= 70 and validation_score >= 70:
            return 'low'
        elif confidence >= 50 and validation_score >= 50:
            return 'medium'
        else:
            return 'high'