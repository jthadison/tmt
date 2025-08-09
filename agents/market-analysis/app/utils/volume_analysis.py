"""
Volume Analysis Utilities

Provides common volume analysis functions used across
the Wyckoff Pattern Detection Engine components:
- Volume trend analysis
- Volume-price divergence detection
- Volume confirmation patterns
- Volume distribution analysis
"""

from typing import Dict, List, Tuple, Optional
from decimal import Decimal
import pandas as pd
import numpy as np
from datetime import datetime


class VolumeAnalyzer:
    """Analyzes volume patterns and relationships with price"""
    
    def __init__(self, lookback_periods: int = 20):
        self.lookback_periods = lookback_periods
    
    def analyze_volume_trend(self, volume_data: pd.Series, periods: int = 20) -> Dict:
        """
        Analyze volume trend over specified periods
        
        Returns:
            Dict with volume trend analysis including direction, strength, and consistency
        """
        if len(volume_data) < periods:
            periods = len(volume_data)
        
        recent_volume = volume_data.iloc[-periods:]
        
        # Linear regression on volume
        x = np.arange(len(recent_volume))
        slope, intercept = np.polyfit(x, recent_volume.values, 1)
        
        # Normalize slope to percentage change per period
        avg_volume = recent_volume.mean()
        slope_pct = (slope / avg_volume) * 100 if avg_volume > 0 else 0
        
        # Calculate R-squared for trend consistency
        y_pred = slope * x + intercept
        ss_res = np.sum((recent_volume.values - y_pred) ** 2)
        ss_tot = np.sum((recent_volume.values - recent_volume.mean()) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        
        # Determine trend direction
        if slope_pct > 0.5:
            direction = 'increasing'
        elif slope_pct < -0.5:
            direction = 'decreasing'
        else:
            direction = 'stable'
        
        # Calculate trend strength (0-100)
        strength = min(100, abs(slope_pct) * 10 + r_squared * 50)
        
        return {
            'direction': direction,
            'strength': round(strength, 2),
            'slope_percentage': round(slope_pct, 3),
            'r_squared': round(r_squared, 3),
            'avg_volume': round(avg_volume, 2),
            'current_volume': round(recent_volume.iloc[-1], 2),
            'volume_change_pct': round(slope_pct * periods, 2)
        }
    
    def detect_volume_price_divergence(self,
                                     price_data: pd.DataFrame,
                                     volume_data: pd.Series,
                                     periods: int = 14) -> Dict:
        """
        Detect divergence between price and volume trends
        
        Bullish divergence: Price makes lower lows while volume makes higher lows
        Bearish divergence: Price makes higher highs while volume makes lower highs
        """
        if len(price_data) < periods or len(volume_data) < periods:
            return {'divergence_detected': False, 'reason': 'Insufficient data'}
        
        # Get recent data
        recent_prices = price_data.iloc[-periods:]
        recent_volume = volume_data.iloc[-periods:]
        
        # Calculate price and volume trends
        price_trend = self._calculate_trend_slope(recent_prices['close'].values)
        volume_trend = self._calculate_trend_slope(recent_volume.values)
        
        # Detect divergence patterns
        divergence_type = None
        divergence_strength = 0
        
        # Bullish divergence: Price down, Volume up
        if price_trend['direction'] == 'down' and volume_trend['direction'] == 'up':
            divergence_type = 'bullish'
            divergence_strength = (abs(price_trend['slope']) + abs(volume_trend['slope'])) / 2
        
        # Bearish divergence: Price up, Volume down
        elif price_trend['direction'] == 'up' and volume_trend['direction'] == 'down':
            divergence_type = 'bearish'
            divergence_strength = (abs(price_trend['slope']) + abs(volume_trend['slope'])) / 2
        
        # Hidden bullish divergence: Price higher lows, Volume lower lows
        elif price_trend['direction'] == 'up' and volume_trend['direction'] == 'down':
            if self._check_hidden_bullish_divergence(recent_prices, recent_volume):
                divergence_type = 'hidden_bullish'
                divergence_strength = (price_trend['strength'] + volume_trend['strength']) / 2
        
        # Hidden bearish divergence: Price lower highs, Volume higher highs
        elif price_trend['direction'] == 'down' and volume_trend['direction'] == 'up':
            if self._check_hidden_bearish_divergence(recent_prices, recent_volume):
                divergence_type = 'hidden_bearish'
                divergence_strength = (price_trend['strength'] + volume_trend['strength']) / 2
        
        return {
            'divergence_detected': divergence_type is not None,
            'divergence_type': divergence_type,
            'strength': round(divergence_strength, 2),
            'price_trend': price_trend,
            'volume_trend': volume_trend,
            'confidence': self._calculate_divergence_confidence(price_trend, volume_trend)
        }
    
    def analyze_volume_confirmation(self,
                                  price_data: pd.DataFrame,
                                  volume_data: pd.Series,
                                  move_type: str = 'auto') -> Dict:
        """
        Analyze volume confirmation for price moves
        
        Args:
            move_type: 'up', 'down', or 'auto' to detect automatically
        
        Returns:
            Dict with volume confirmation analysis
        """
        if len(price_data) != len(volume_data):
            return {'error': 'Price and volume data length mismatch'}
        
        # Determine move type if auto
        if move_type == 'auto':
            price_change = price_data['close'].iloc[-1] - price_data['close'].iloc[0]
            move_type = 'up' if price_change > 0 else 'down'
        
        # Calculate volume metrics
        avg_volume = volume_data.mean()
        recent_volume = volume_data.iloc[-min(5, len(volume_data)):].mean()
        volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1
        
        # Analyze volume on directional moves
        if move_type == 'up':
            up_candles = price_data['close'] > price_data['open']
            up_volume = volume_data[up_candles].mean() if up_candles.any() else 0
            confirmation_ratio = up_volume / avg_volume if avg_volume > 0 else 0
            ideal_confirmation = confirmation_ratio > 1.2  # 20% above average
        else:
            down_candles = price_data['close'] < price_data['open']
            down_volume = volume_data[down_candles].mean() if down_candles.any() else 0
            confirmation_ratio = down_volume / avg_volume if avg_volume > 0 else 0
            ideal_confirmation = confirmation_ratio > 1.2
        
        # Volume expansion analysis
        expansion_detected = volume_ratio > 1.3  # 30% above average
        
        # Overall confirmation score
        confirmation_score = 0
        if ideal_confirmation:
            confirmation_score += 40
        if expansion_detected:
            confirmation_score += 30
        if confirmation_ratio > 1.0:
            confirmation_score += min(30, (confirmation_ratio - 1) * 100)
        
        confirmation_level = 'strong' if confirmation_score >= 70 else 'moderate' if confirmation_score >= 40 else 'weak'
        
        return {
            'move_type': move_type,
            'confirmation_level': confirmation_level,
            'confirmation_score': round(confirmation_score, 2),
            'volume_ratio': round(volume_ratio, 2),
            'confirmation_ratio': round(confirmation_ratio, 2),
            'volume_expansion': expansion_detected,
            'avg_volume': round(avg_volume, 2),
            'recent_volume': round(recent_volume, 2),
            'directional_volume': round(up_volume if move_type == 'up' else down_volume, 2)
        }
    
    def calculate_volume_distribution(self,
                                    price_data: pd.DataFrame,
                                    volume_data: pd.Series,
                                    bins: int = 20) -> Dict:
        """
        Calculate volume distribution across different price ranges
        
        Returns:
            Dict with volume distribution analysis
        """
        if len(price_data) != len(volume_data):
            return {'error': 'Data length mismatch'}
        
        # Calculate price range
        price_high = price_data['high'].max()
        price_low = price_data['low'].min()
        price_range = price_high - price_low
        bin_size = price_range / bins
        
        # Initialize volume bins
        volume_bins = {}
        for i in range(bins):
            bin_low = price_low + (i * bin_size)
            bin_high = bin_low + bin_size
            volume_bins[f'bin_{i}'] = {
                'price_low': bin_low,
                'price_high': bin_high,
                'volume': 0,
                'touches': 0
            }
        
        # Distribute volume across bins
        for i, (idx, candle) in enumerate(price_data.iterrows()):
            volume = volume_data.iloc[i]
            
            # Find which bin(s) this candle touches
            candle_low = candle['low']
            candle_high = candle['high']
            
            for bin_key, bin_data in volume_bins.items():
                # Check if candle overlaps with this bin
                if not (candle_high < bin_data['price_low'] or candle_low > bin_data['price_high']):
                    # Calculate overlap percentage
                    overlap_low = max(candle_low, bin_data['price_low'])
                    overlap_high = min(candle_high, bin_data['price_high'])
                    overlap_size = overlap_high - overlap_low
                    candle_size = candle_high - candle_low
                    
                    if candle_size > 0:
                        overlap_percentage = overlap_size / candle_size
                        bin_data['volume'] += volume * overlap_percentage
                        bin_data['touches'] += 1
                    elif candle_size == 0:  # Doji candle
                        bin_data['volume'] += volume
                        bin_data['touches'] += 1
        
        # Find high volume areas
        sorted_bins = sorted(volume_bins.values(), key=lambda x: x['volume'], reverse=True)
        total_volume = sum(bin_data['volume'] for bin_data in volume_bins.values())
        
        # Calculate percentiles
        high_volume_threshold = np.percentile([bin_data['volume'] for bin_data in volume_bins.values()], 80)
        high_volume_areas = [
            {
                'price_level': (bin_data['price_low'] + bin_data['price_high']) / 2,
                'volume': bin_data['volume'],
                'volume_percentage': (bin_data['volume'] / total_volume) * 100 if total_volume > 0 else 0,
                'touches': bin_data['touches']
            }
            for bin_data in sorted_bins[:5] if bin_data['volume'] >= high_volume_threshold
        ]
        
        return {
            'total_volume': round(total_volume, 2),
            'bins_count': bins,
            'bin_size': round(bin_size, 5),
            'price_range': round(price_range, 5),
            'high_volume_areas': high_volume_areas,
            'volume_concentration': {
                'top_20_percent_volume': sum(bin_data['volume'] for bin_data in sorted_bins[:int(bins * 0.2)]),
                'bottom_20_percent_volume': sum(bin_data['volume'] for bin_data in sorted_bins[-int(bins * 0.2):])
            }
        }
    
    def detect_volume_spikes(self,
                           volume_data: pd.Series,
                           spike_threshold: float = 2.0,
                           periods: int = 20) -> Dict:
        """
        Detect volume spikes relative to recent average
        
        Args:
            spike_threshold: Multiple of average volume to be considered a spike
            periods: Number of periods to use for average calculation
        """
        if len(volume_data) < periods:
            periods = len(volume_data)
        
        spikes = []
        avg_volume = volume_data.rolling(window=periods).mean()
        
        for i in range(periods, len(volume_data)):
            current_volume = volume_data.iloc[i]
            avg_vol = avg_volume.iloc[i]
            
            if current_volume > avg_vol * spike_threshold:
                spike_ratio = current_volume / avg_vol
                spikes.append({
                    'index': i,
                    'volume': current_volume,
                    'average_volume': avg_vol,
                    'spike_ratio': round(spike_ratio, 2),
                    'spike_strength': 'extreme' if spike_ratio > 5 else 'strong' if spike_ratio > 3 else 'moderate'
                })
        
        # Recent spike analysis
        recent_spikes = [spike for spike in spikes if spike['index'] >= len(volume_data) - min(10, len(volume_data) // 4)]
        
        return {
            'total_spikes': len(spikes),
            'recent_spikes': len(recent_spikes),
            'spike_threshold': spike_threshold,
            'all_spikes': spikes,
            'recent_spike_data': recent_spikes,
            'avg_spike_ratio': round(sum(spike['spike_ratio'] for spike in spikes) / len(spikes), 2) if spikes else 0,
            'max_spike_ratio': max(spike['spike_ratio'] for spike in spikes) if spikes else 0
        }
    
    def analyze_volume_patterns(self,
                              volume_data: pd.Series,
                              pattern_window: int = 10) -> Dict:
        """
        Analyze common volume patterns
        
        Patterns:
        - Climax volume (extremely high volume)
        - Churning (high volume with little price movement)
        - Effort vs Result (volume vs price relationship)
        - Volume dry-up (decreasing volume)
        """
        if len(volume_data) < pattern_window:
            return {'patterns': [], 'analysis': 'Insufficient data'}
        
        patterns = []
        
        # Recent volume window
        recent_volume = volume_data.iloc[-pattern_window:]
        avg_volume = volume_data.mean()
        
        # Pattern 1: Climax Volume
        max_recent_volume = recent_volume.max()
        if max_recent_volume > avg_volume * 3:
            patterns.append({
                'pattern': 'climax_volume',
                'strength': 'strong' if max_recent_volume > avg_volume * 5 else 'moderate',
                'description': 'Extremely high volume detected - potential climax',
                'volume_ratio': round(max_recent_volume / avg_volume, 2)
            })
        
        # Pattern 2: Volume Dry-up
        recent_avg = recent_volume.mean()
        if recent_avg < avg_volume * 0.6:
            patterns.append({
                'pattern': 'volume_dryup',
                'strength': 'strong' if recent_avg < avg_volume * 0.4 else 'moderate',
                'description': 'Volume drying up - potential consolidation or reversal preparation',
                'volume_ratio': round(recent_avg / avg_volume, 2)
            })
        
        # Pattern 3: Increasing Volume Trend
        volume_trend = self.analyze_volume_trend(recent_volume, min(pattern_window, len(recent_volume)))
        if volume_trend['direction'] == 'increasing' and volume_trend['strength'] > 60:
            patterns.append({
                'pattern': 'increasing_volume',
                'strength': 'strong' if volume_trend['strength'] > 80 else 'moderate',
                'description': 'Volume increasing trend - growing interest',
                'trend_strength': volume_trend['strength']
            })
        
        # Pattern 4: Volume Oscillation
        volume_std = recent_volume.std()
        volume_cv = volume_std / recent_volume.mean() if recent_volume.mean() > 0 else 0
        if volume_cv > 0.5:
            patterns.append({
                'pattern': 'volume_oscillation',
                'strength': 'strong' if volume_cv > 0.8 else 'moderate',
                'description': 'High volume volatility - uncertain sentiment',
                'coefficient_variation': round(volume_cv, 3)
            })
        
        return {
            'patterns_detected': len(patterns),
            'patterns': patterns,
            'recent_avg_volume': round(recent_volume.mean(), 2),
            'overall_avg_volume': round(avg_volume, 2),
            'volume_trend': volume_trend,
            'analysis': f'{len(patterns)} volume patterns detected in recent {pattern_window} periods'
        }
    
    def _calculate_trend_slope(self, data: np.ndarray) -> Dict:
        """Calculate trend slope and characteristics"""
        if len(data) < 2:
            return {'direction': 'flat', 'slope': 0, 'strength': 0}
        
        x = np.arange(len(data))
        slope, intercept = np.polyfit(x, data, 1)
        
        # Calculate R-squared
        y_pred = slope * x + intercept
        ss_res = np.sum((data - y_pred) ** 2)
        ss_tot = np.sum((data - np.mean(data)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        
        # Determine direction
        avg_value = np.mean(data)
        slope_pct = (slope / avg_value) * 100 if avg_value != 0 else 0
        
        if slope_pct > 0.5:
            direction = 'up'
        elif slope_pct < -0.5:
            direction = 'down'
        else:
            direction = 'flat'
        
        strength = min(100, abs(slope_pct) * 10 + r_squared * 50)
        
        return {
            'direction': direction,
            'slope': slope,
            'slope_percentage': round(slope_pct, 3),
            'strength': round(strength, 2),
            'r_squared': round(r_squared, 3)
        }
    
    def _check_hidden_bullish_divergence(self, price_data: pd.DataFrame, volume_data: pd.Series) -> bool:
        """Check for hidden bullish divergence pattern"""
        # This is a simplified check - full implementation would analyze swing points
        recent_prices = price_data['close'].iloc[-10:]
        recent_volume = volume_data.iloc[-10:]
        
        # Look for higher lows in price with lower lows in volume
        price_min_idx = recent_prices.idxmin()
        volume_min_idx = recent_volume.idxmin()
        
        # Simplified check - would need more sophisticated swing analysis
        return price_min_idx != volume_min_idx
    
    def _check_hidden_bearish_divergence(self, price_data: pd.DataFrame, volume_data: pd.Series) -> bool:
        """Check for hidden bearish divergence pattern"""
        # This is a simplified check - full implementation would analyze swing points
        recent_prices = price_data['close'].iloc[-10:]
        recent_volume = volume_data.iloc[-10:]
        
        # Look for lower highs in price with higher highs in volume
        price_max_idx = recent_prices.idxmax()
        volume_max_idx = recent_volume.idxmax()
        
        # Simplified check - would need more sophisticated swing analysis
        return price_max_idx != volume_max_idx
    
    def _calculate_divergence_confidence(self, price_trend: Dict, volume_trend: Dict) -> float:
        """Calculate confidence level for divergence detection"""
        # Base confidence on trend strengths
        price_strength = price_trend.get('strength', 0)
        volume_strength = volume_trend.get('strength', 0)
        
        # Higher strength in both trends = higher confidence
        avg_strength = (price_strength + volume_strength) / 2
        
        # R-squared values add to confidence
        price_r2 = price_trend.get('r_squared', 0)
        volume_r2 = volume_trend.get('r_squared', 0)
        avg_r2 = (price_r2 + volume_r2) / 2
        
        # Combined confidence score
        confidence = (avg_strength * 0.6) + (avg_r2 * 40)
        return round(min(100, max(0, confidence)), 2)