"""
Volume Classification System

Implements smart money vs retail volume classification as specified in Story 3.3, Task 5:
- Volume pattern analysis during different market hours
- Institutional volume classification: large size, low spread impact
- Retail volume identification: small size, high frequency, emotional
- Smart money accumulation detection algorithms
- Retail distribution identification
- Institutional vs retail sentiment indicators
"""

from typing import Dict, List, Tuple, Optional, Union
import pandas as pd
import numpy as np
from decimal import Decimal
from datetime import datetime, time, timedelta
import logging

logger = logging.getLogger(__name__)


class VolumeClassifier:
    """
    Advanced volume classification system to distinguish between smart money
    and retail trading patterns.
    
    Analyzes volume characteristics, timing patterns, price impact, and
    market microstructure to classify trading activity.
    """
    
    def __init__(self,
                 institutional_hours: List[Tuple[time, time]] = None,
                 large_volume_threshold_pct: float = 90.0,
                 frequency_analysis_window: int = 20):
        """
        Initialize volume classifier.
        
        Args:
            institutional_hours: List of (start, end) time tuples for institutional trading
            large_volume_threshold_pct: Percentile threshold for large volume classification  
            frequency_analysis_window: Window for analyzing trade frequency patterns
        """
        # Default institutional trading hours (London + NY sessions in GMT)
        self.institutional_hours = institutional_hours or [
            (time(8, 0), time(12, 0)),   # London session
            (time(13, 0), time(17, 0))   # New York session
        ]
        
        self.large_volume_threshold_pct = large_volume_threshold_pct
        self.frequency_analysis_window = frequency_analysis_window
        
        # Smart money characteristics
        self.smart_money_indicators = {
            'size_factor_weight': 0.25,
            'timing_factor_weight': 0.20,
            'price_impact_weight': 0.25,
            'spread_factor_weight': 0.15,
            'session_factor_weight': 0.15
        }
        
    def classify_volume_type(self,
                           price_data: pd.DataFrame,
                           volume_data: pd.Series,
                           timestamps: pd.Series = None) -> Dict:
        """
        Classify volume as smart money vs retail based on multiple factors.
        
        Args:
            price_data: DataFrame with OHLC data
            volume_data: Series with volume data
            timestamps: Optional timestamps (will use index if not provided)
            
        Returns:
            Dict containing volume classifications and analysis
        """
        if len(price_data) != len(volume_data):
            return {'error': 'Price and volume data length mismatch'}
        
        if len(price_data) < self.frequency_analysis_window:
            return {'error': f'Insufficient data - need at least {self.frequency_analysis_window} periods'}
        
        # Use index as timestamps if not provided
        if timestamps is None:
            timestamps = price_data.index
        
        # Ensure we have datetime index
        if hasattr(timestamps, 'iloc'):
            # It's a Series or Index
            first_timestamp = timestamps.iloc[0] if len(timestamps) > 0 else None
        else:
            # It's already an Index
            first_timestamp = timestamps[0] if len(timestamps) > 0 else None
            
        if first_timestamp is not None and isinstance(first_timestamp, (datetime, pd.Timestamp)):
            use_time_analysis = True
        else:
            logger.warning("Timestamps not in datetime format - using sequential analysis")
            use_time_analysis = False
        
        classifications = []
        
        for i, (idx, candle) in enumerate(price_data.iterrows()):
            volume = volume_data.iloc[i]
            if use_time_analysis:
                timestamp = timestamps[i] if hasattr(timestamps, '__getitem__') else timestamps.iloc[i]
            else:
                timestamp = i
            
            # Analyze classification factors
            factors = {
                'size_factor': self.analyze_volume_size(volume, i, volume_data),
                'timing_factor': self.analyze_volume_timing(timestamp, use_time_analysis),
                'price_impact': self.analyze_price_impact(candle, volume, i, price_data),
                'spread_factor': self.analyze_spread_during_volume(candle),
                'session_factor': self.analyze_session_context(timestamp, use_time_analysis),
                'frequency_pattern': self.analyze_frequency_pattern(volume_data, i),
                'order_flow_pattern': self.analyze_order_flow_pattern(price_data, volume_data, i)
            }
            
            # Calculate smart money score
            smart_money_score = self.calculate_smart_money_score(factors)
            
            # Determine classification
            if smart_money_score >= 0.7:
                classification = 'smart_money'
                confidence = smart_money_score
            elif smart_money_score <= 0.3:
                classification = 'retail'
                confidence = 1 - smart_money_score
            else:
                classification = 'mixed'
                confidence = 0.5
            
            # Additional pattern analysis
            accumulation_pattern = self.detect_accumulation_pattern(price_data, volume_data, i)
            distribution_pattern = self.detect_distribution_pattern(price_data, volume_data, i)
            
            classification_entry = {
                'timestamp': timestamp,
                'index': i,
                'volume': float(volume),
                'classification': classification,
                'confidence': round(confidence, 3),
                'smart_money_score': round(smart_money_score, 3),
                'factors': factors,
                'accumulation_pattern': accumulation_pattern,
                'distribution_pattern': distribution_pattern,
                'trading_intensity': self.calculate_trading_intensity(factors)
            }
            
            classifications.append(classification_entry)
        
        # Aggregate analysis
        aggregate_analysis = self.analyze_volume_patterns(classifications)
        
        # Detect institutional flow patterns
        institutional_flow = self.detect_institutional_flow_patterns(classifications, price_data)
        
        # Calculate sentiment indicators
        sentiment_indicators = self.calculate_sentiment_indicators(classifications, price_data)
        
        return {
            'classifications': classifications,
            'total_periods': len(classifications),
            'smart_money_periods': sum(1 for c in classifications if c['classification'] == 'smart_money'),
            'retail_periods': sum(1 for c in classifications if c['classification'] == 'retail'),
            'mixed_periods': sum(1 for c in classifications if c['classification'] == 'mixed'),
            'aggregate_analysis': aggregate_analysis,
            'institutional_flow': institutional_flow,
            'sentiment_indicators': sentiment_indicators,
            'classification_distribution': self._calculate_classification_distribution(classifications),
            'alerts': self._generate_volume_classification_alerts(classifications, aggregate_analysis)
        }
    
    def analyze_volume_size(self, volume: float, index: int, volume_data: pd.Series) -> Dict:
        """
        Analyze volume size characteristics for smart money identification.
        
        Large volume with efficient execution typically indicates institutional activity.
        """
        # Calculate percentile ranking of current volume
        if index < 20:
            comparison_data = volume_data[:index+1]
        else:
            comparison_data = volume_data[max(0, index-50):index+1]
        
        if len(comparison_data) == 0:
            return {'score': 0.5, 'percentile': 50, 'size_category': 'unknown'}
        
        percentile = (comparison_data < volume).sum() / len(comparison_data) * 100
        
        # Volume size categories
        if percentile >= self.large_volume_threshold_pct:
            size_category = 'very_large'
            score = 0.9  # High smart money probability
        elif percentile >= 75:
            size_category = 'large'
            score = 0.7
        elif percentile >= 50:
            size_category = 'medium'
            score = 0.5
        elif percentile >= 25:
            size_category = 'small'
            score = 0.3
        else:
            size_category = 'very_small'
            score = 0.1  # High retail probability
        
        # Additional size analysis
        if len(comparison_data) >= 20:
            recent_avg = volume_data[max(0, index-19):index+1].mean()
            size_ratio = volume / recent_avg if recent_avg > 0 else 1
        else:
            size_ratio = 1
        
        return {
            'score': score,
            'percentile': round(percentile, 2),
            'size_category': size_category,
            'size_ratio': round(size_ratio, 2),
            'absolute_volume': float(volume)
        }
    
    def analyze_volume_timing(self, timestamp: Union[datetime, int], use_time_analysis: bool) -> Dict:
        """
        Analyze timing patterns to identify institutional vs retail activity.
        
        Institutional activity tends to cluster during specific hours.
        """
        if not use_time_analysis:
            return {'score': 0.5, 'session': 'unknown', 'institutional_hours': False}
        
        if isinstance(timestamp, (int, np.integer)):
            return {'score': 0.5, 'session': 'sequential', 'institutional_hours': False}
        
        # Convert to time for analysis
        trade_time = timestamp.time() if hasattr(timestamp, 'time') else time(12, 0)
        
        # Check if within institutional hours
        institutional_hours = False
        for start_time, end_time in self.institutional_hours:
            if start_time <= trade_time <= end_time:
                institutional_hours = True
                break
        
        # Score based on timing
        if institutional_hours:
            # High institutional probability during institutional hours
            score = 0.8
            session = 'institutional'
        elif time(20, 0) <= trade_time or trade_time <= time(6, 0):
            # Off-hours trading often retail or algorithmic
            score = 0.3
            session = 'off_hours'
        elif time(17, 0) <= trade_time <= time(20, 0):
            # Overlap/retail hours
            score = 0.4
            session = 'retail_overlap'
        else:
            # Standard trading hours but outside institutional peak
            score = 0.5
            session = 'standard'
        
        return {
            'score': score,
            'session': session,
            'institutional_hours': institutional_hours,
            'trade_time': trade_time.strftime('%H:%M:%S')
        }
    
    def analyze_price_impact(self,
                           candle: pd.Series,
                           volume: float,
                           index: int,
                           price_data: pd.DataFrame) -> Dict:
        """
        Analyze price impact of volume to identify smart vs retail money.
        
        Smart money typically has lower price impact per unit volume (efficient execution).
        """
        open_price = candle['open']
        close_price = candle['close']
        high_price = candle['high']
        low_price = candle['low']
        
        # Calculate price movement and impact
        price_change = abs(close_price - open_price)
        price_range = high_price - low_price
        
        # Avoid division by zero
        if volume == 0:
            return {'score': 0.5, 'impact_efficiency': 0, 'impact_category': 'unknown'}
        
        # Price impact per unit volume
        if price_range > 0:
            impact_per_volume = price_range / volume
        else:
            impact_per_volume = 0
        
        # Compare with recent periods to normalize
        if index >= 10:
            recent_candles = price_data.iloc[max(0, index-10):index]
            recent_ranges = (recent_candles['high'] - recent_candles['low']).mean()
            
            # Normalize impact
            normalized_impact = impact_per_volume / recent_ranges if recent_ranges > 0 else 0
        else:
            normalized_impact = 0
        
        # Score based on impact efficiency (lower impact = higher smart money probability)
        if normalized_impact < 0.01:  # Very low impact
            score = 0.9
            impact_category = 'very_low_impact'
        elif normalized_impact < 0.05:
            score = 0.7
            impact_category = 'low_impact'  
        elif normalized_impact < 0.1:
            score = 0.5
            impact_category = 'medium_impact'
        elif normalized_impact < 0.2:
            score = 0.3
            impact_category = 'high_impact'
        else:
            score = 0.1
            impact_category = 'very_high_impact'
        
        # Additional analysis
        body_to_range_ratio = price_change / price_range if price_range > 0 else 0
        
        return {
            'score': score,
            'impact_per_volume': round(impact_per_volume, 8),
            'normalized_impact': round(normalized_impact, 6),
            'impact_category': impact_category,
            'price_change': round(price_change, 5),
            'price_range': round(price_range, 5),
            'body_to_range_ratio': round(body_to_range_ratio, 3)
        }
    
    def analyze_spread_during_volume(self, candle: pd.Series) -> Dict:
        """
        Analyze bid-ask spread behavior during volume periods.
        
        Note: This is simplified as we don't have actual bid-ask data.
        Using high-low range as proxy for spread behavior.
        """
        high_price = candle['high']
        low_price = candle['low']
        close_price = candle['close']
        
        spread_proxy = high_price - low_price
        mid_price = (high_price + low_price) / 2
        
        # Normalize spread
        spread_pct = (spread_proxy / mid_price) * 100 if mid_price > 0 else 0
        
        # Score based on spread characteristics
        # Tighter spreads during high volume suggest institutional activity
        if spread_pct < 0.1:
            score = 0.8
            spread_category = 'very_tight'
        elif spread_pct < 0.3:
            score = 0.6
            spread_category = 'tight'
        elif spread_pct < 0.5:
            score = 0.5
            spread_category = 'normal'
        elif spread_pct < 1.0:
            score = 0.3
            spread_category = 'wide'
        else:
            score = 0.1
            spread_category = 'very_wide'
        
        # Close position within range (institutional tends to close near mid)
        close_position = (close_price - low_price) / spread_proxy if spread_proxy > 0 else 0.5
        mid_proximity_score = 1 - abs(close_position - 0.5) * 2  # Higher score for closer to mid
        
        return {
            'score': (score + mid_proximity_score * 0.3) / 1.3,  # Weighted combination
            'spread_proxy': round(spread_proxy, 5),
            'spread_pct': round(spread_pct, 3),
            'spread_category': spread_category,
            'close_position': round(close_position, 3),
            'mid_proximity_score': round(mid_proximity_score, 3)
        }
    
    def analyze_session_context(self, timestamp: Union[datetime, int], use_time_analysis: bool) -> Dict:
        """
        Analyze broader session context for volume classification.
        """
        if not use_time_analysis:
            return {'score': 0.5, 'session_phase': 'unknown', 'liquidity_context': 'normal'}
        
        if isinstance(timestamp, (int, np.integer)):
            return {'score': 0.5, 'session_phase': 'sequential', 'liquidity_context': 'normal'}
        
        trade_time = timestamp.time() if hasattr(timestamp, 'time') else time(12, 0)
        
        # Session phase analysis
        if time(9, 30) <= trade_time <= time(10, 30):
            session_phase = 'opening_hour'
            score = 0.7  # High institutional activity at open
        elif time(15, 30) <= trade_time <= time(16, 0):
            session_phase = 'closing_hour'  
            score = 0.8  # Very high institutional activity at close
        elif time(11, 0) <= trade_time <= time(14, 0):
            session_phase = 'midday_lull'
            score = 0.3  # Lower institutional activity
        elif time(10, 30) <= trade_time <= time(11, 0) or time(14, 0) <= trade_time <= time(15, 30):
            session_phase = 'active_trading'
            score = 0.6  # Moderate institutional activity
        else:
            session_phase = 'off_hours'
            score = 0.2  # Minimal institutional activity
        
        # Liquidity context (simplified)
        if session_phase in ['opening_hour', 'closing_hour']:
            liquidity_context = 'high'
        elif session_phase in ['active_trading']:
            liquidity_context = 'normal'
        elif session_phase == 'midday_lull':
            liquidity_context = 'low'
        else:
            liquidity_context = 'very_low'
        
        return {
            'score': score,
            'session_phase': session_phase,
            'liquidity_context': liquidity_context,
            'trade_time': trade_time.strftime('%H:%M:%S')
        }
    
    def analyze_frequency_pattern(self, volume_data: pd.Series, index: int) -> Dict:
        """
        Analyze trading frequency patterns to identify retail vs institutional behavior.
        
        Retail: High frequency, smaller sizes
        Institutional: Lower frequency, larger sizes
        """
        if index < 5:
            return {'score': 0.5, 'frequency_category': 'insufficient_data'}
        
        # Analyze recent volume pattern
        window_start = max(0, index - self.frequency_analysis_window + 1)
        window_end = index + 1
        
        recent_volumes = volume_data.iloc[window_start:window_end]
        
        if len(recent_volumes) < 3:
            return {'score': 0.5, 'frequency_category': 'insufficient_data'}
        
        # Calculate frequency metrics
        non_zero_volumes = recent_volumes[recent_volumes > 0]
        avg_volume = non_zero_volumes.mean() if len(non_zero_volumes) > 0 else 0
        volume_std = non_zero_volumes.std() if len(non_zero_volumes) > 1 else 0
        
        current_volume = volume_data.iloc[index]
        
        # Coefficient of variation (volatility of volume)
        cv = volume_std / avg_volume if avg_volume > 0 else 0
        
        # Score based on frequency patterns
        # Lower CV and higher average volume = more institutional
        if cv < 0.5 and current_volume > avg_volume * 1.5:
            score = 0.8
            frequency_category = 'consistent_large'
        elif cv < 0.8 and current_volume > avg_volume:
            score = 0.6
            frequency_category = 'consistent_medium'
        elif cv > 2.0 and current_volume < avg_volume * 0.5:
            score = 0.2
            frequency_category = 'erratic_small'
        elif cv > 1.5:
            score = 0.3
            frequency_category = 'erratic'
        else:
            score = 0.5
            frequency_category = 'mixed_pattern'
        
        return {
            'score': score,
            'frequency_category': frequency_category,
            'coefficient_of_variation': round(cv, 3),
            'avg_volume': round(avg_volume, 2),
            'volume_consistency': round(1 / (1 + cv), 3) if cv > 0 else 1.0
        }
    
    def analyze_order_flow_pattern(self,
                                 price_data: pd.DataFrame,
                                 volume_data: pd.Series,
                                 index: int) -> Dict:
        """
        Analyze order flow patterns to identify smart money footprints.
        """
        if index < 5:
            return {'score': 0.5, 'flow_pattern': 'insufficient_data'}
        
        # Look at recent price-volume relationship
        lookback = min(5, index)
        recent_candles = price_data.iloc[index-lookback:index+1]
        recent_volumes = volume_data.iloc[index-lookback:index+1]
        
        # Analyze volume on up vs down moves
        up_moves = recent_candles[recent_candles['close'] > recent_candles['open']]
        down_moves = recent_candles[recent_candles['close'] < recent_candles['open']]
        
        if len(up_moves) > 0 and len(down_moves) > 0:
            up_volume_avg = recent_volumes[recent_candles['close'] > recent_candles['open']].mean()
            down_volume_avg = recent_volumes[recent_candles['close'] < recent_candles['open']].mean()
            
            # Smart money often shows volume on strength, dryup on weakness
            if up_volume_avg > down_volume_avg * 1.3:
                score = 0.7
                flow_pattern = 'volume_on_strength'
            elif down_volume_avg > up_volume_avg * 1.3:
                score = 0.3
                flow_pattern = 'volume_on_weakness'
            else:
                score = 0.5
                flow_pattern = 'balanced_flow'
        else:
            score = 0.5
            flow_pattern = 'insufficient_moves'
            up_volume_avg = down_volume_avg = 0
        
        return {
            'score': score,
            'flow_pattern': flow_pattern,
            'up_volume_avg': round(up_volume_avg, 2) if up_volume_avg > 0 else 0,
            'down_volume_avg': round(down_volume_avg, 2) if down_volume_avg > 0 else 0,
            'volume_bias_ratio': round(up_volume_avg / down_volume_avg, 2) if down_volume_avg > 0 else 1
        }
    
    def calculate_smart_money_score(self, factors: Dict) -> float:
        """
        Calculate overall smart money probability score from all factors.
        """
        # Weight the different factors according to their importance
        weighted_score = 0.0
        total_weight = 0.0
        
        for factor_name, weight in self.smart_money_indicators.items():
            if factor_name.replace('_weight', '') in factors:
                factor_score = factors[factor_name.replace('_weight', '')]['score']
                weighted_score += factor_score * weight
                total_weight += weight
        
        # Add additional factors with smaller weights
        additional_factors = ['frequency_pattern', 'order_flow_pattern']
        additional_weight = 0.1
        
        for factor_name in additional_factors:
            if factor_name in factors:
                factor_score = factors[factor_name]['score']
                weighted_score += factor_score * additional_weight
                total_weight += additional_weight
        
        # Normalize to 0-1 range
        final_score = weighted_score / total_weight if total_weight > 0 else 0.5
        
        return max(0.0, min(1.0, final_score))
    
    def detect_accumulation_pattern(self,
                                  price_data: pd.DataFrame,
                                  volume_data: pd.Series,
                                  index: int) -> Dict:
        """
        Detect smart money accumulation patterns.
        
        Characteristics: High volume on up moves, low volume on down moves
        """
        if index < 10:
            return {'detected': False, 'reason': 'insufficient_data'}
        
        # Analyze recent 10 periods
        lookback = min(10, index)
        recent_candles = price_data.iloc[index-lookback:index+1]
        recent_volumes = volume_data.iloc[index-lookback:index+1]
        
        # Separate up and down moves
        up_candles = recent_candles[recent_candles['close'] > recent_candles['open']]
        down_candles = recent_candles[recent_candles['close'] < recent_candles['open']]
        
        if len(up_candles) < 2 or len(down_candles) < 2:
            return {'detected': False, 'reason': 'insufficient_directional_moves'}
        
        # Get corresponding volumes
        up_volumes = recent_volumes[recent_candles['close'] > recent_candles['open']]
        down_volumes = recent_volumes[recent_candles['close'] < recent_candles['open']]
        
        up_vol_avg = up_volumes.mean()
        down_vol_avg = down_volumes.mean()
        
        # Accumulation pattern: volume on strength > volume on weakness
        volume_ratio = up_vol_avg / down_vol_avg if down_vol_avg > 0 else 1
        
        # Additional checks
        price_trend = (recent_candles['close'].iloc[-1] - recent_candles['close'].iloc[0]) / recent_candles['close'].iloc[0] * 100
        
        # Detect accumulation
        if volume_ratio > 1.5 and abs(price_trend) < 5:  # High volume on strength, sideways price
            detected = True
            strength = min(100, (volume_ratio - 1) * 50)
            pattern_type = 'strong_accumulation' if volume_ratio > 2.0 else 'moderate_accumulation'
        else:
            detected = False
            strength = 0
            pattern_type = 'no_accumulation'
        
        return {
            'detected': detected,
            'pattern_type': pattern_type,
            'strength': round(strength, 2),
            'volume_ratio': round(volume_ratio, 2),
            'up_volume_avg': round(up_vol_avg, 2),
            'down_volume_avg': round(down_vol_avg, 2),
            'price_trend_pct': round(price_trend, 2)
        }
    
    def detect_distribution_pattern(self,
                                  price_data: pd.DataFrame,
                                  volume_data: pd.Series,
                                  index: int) -> Dict:
        """
        Detect retail distribution patterns (opposite of accumulation).
        """
        if index < 10:
            return {'detected': False, 'reason': 'insufficient_data'}
        
        # Analyze recent 10 periods
        lookback = min(10, index)
        recent_candles = price_data.iloc[index-lookback:index+1]
        recent_volumes = volume_data.iloc[index-lookback:index+1]
        
        # Separate up and down moves
        up_candles = recent_candles[recent_candles['close'] > recent_candles['open']]
        down_candles = recent_candles[recent_candles['close'] < recent_candles['open']]
        
        if len(up_candles) < 2 or len(down_candles) < 2:
            return {'detected': False, 'reason': 'insufficient_directional_moves'}
        
        # Get corresponding volumes
        up_volumes = recent_volumes[recent_candles['close'] > recent_candles['open']]
        down_volumes = recent_volumes[recent_candles['close'] < recent_candles['open']]
        
        up_vol_avg = up_volumes.mean()
        down_vol_avg = down_volumes.mean()
        
        # Distribution pattern: volume on weakness > volume on strength
        volume_ratio = down_vol_avg / up_vol_avg if up_vol_avg > 0 else 1
        
        # Additional checks
        price_trend = (recent_candles['close'].iloc[-1] - recent_candles['close'].iloc[0]) / recent_candles['close'].iloc[0] * 100
        
        # Detect distribution
        if volume_ratio > 1.5 and abs(price_trend) < 5:  # High volume on weakness, sideways price
            detected = True
            strength = min(100, (volume_ratio - 1) * 50)
            pattern_type = 'strong_distribution' if volume_ratio > 2.0 else 'moderate_distribution'
        else:
            detected = False
            strength = 0
            pattern_type = 'no_distribution'
        
        return {
            'detected': detected,
            'pattern_type': pattern_type,
            'strength': round(strength, 2),
            'volume_ratio': round(volume_ratio, 2),
            'up_volume_avg': round(up_vol_avg, 2),
            'down_volume_avg': round(down_vol_avg, 2),
            'price_trend_pct': round(price_trend, 2)
        }
    
    def calculate_trading_intensity(self, factors: Dict) -> Dict:
        """
        Calculate overall trading intensity and characteristics.
        """
        # Combine size and frequency factors
        size_score = factors.get('size_factor', {}).get('score', 0.5)
        frequency_score = factors.get('frequency_pattern', {}).get('score', 0.5)
        
        # Calculate intensity
        intensity = (size_score + frequency_score) / 2
        
        if intensity >= 0.8:
            intensity_level = 'very_high'
        elif intensity >= 0.6:
            intensity_level = 'high'
        elif intensity >= 0.4:
            intensity_level = 'moderate'
        elif intensity >= 0.2:
            intensity_level = 'low'
        else:
            intensity_level = 'very_low'
        
        return {
            'intensity_score': round(intensity, 3),
            'intensity_level': intensity_level,
            'size_component': round(size_score, 3),
            'frequency_component': round(frequency_score, 3)
        }
    
    def analyze_volume_patterns(self, classifications: List[Dict]) -> Dict:
        """
        Analyze overall patterns in volume classifications.
        """
        if not classifications:
            return {'pattern': 'no_data'}
        
        # Count classifications
        smart_money_count = sum(1 for c in classifications if c['classification'] == 'smart_money')
        retail_count = sum(1 for c in classifications if c['classification'] == 'retail')
        mixed_count = sum(1 for c in classifications if c['classification'] == 'mixed')
        
        total_count = len(classifications)
        
        # Calculate percentages
        smart_money_pct = (smart_money_count / total_count) * 100
        retail_pct = (retail_count / total_count) * 100
        mixed_pct = (mixed_count / total_count) * 100
        
        # Determine dominant pattern
        if smart_money_pct > 60:
            dominant_pattern = 'institutional_dominance'
        elif retail_pct > 60:
            dominant_pattern = 'retail_dominance'
        elif smart_money_pct > retail_pct * 1.5:
            dominant_pattern = 'institutional_bias'
        elif retail_pct > smart_money_pct * 1.5:
            dominant_pattern = 'retail_bias'
        else:
            dominant_pattern = 'balanced_activity'
        
        # Recent pattern analysis (last 20%)
        recent_count = max(5, total_count // 5)
        recent_classifications = classifications[-recent_count:]
        
        recent_smart_money = sum(1 for c in recent_classifications if c['classification'] == 'smart_money')
        recent_pattern = 'increasing_institutional' if recent_smart_money > len(recent_classifications) * 0.6 else 'mixed'
        
        return {
            'dominant_pattern': dominant_pattern,
            'smart_money_pct': round(smart_money_pct, 2),
            'retail_pct': round(retail_pct, 2),
            'mixed_pct': round(mixed_pct, 2),
            'total_periods': total_count,
            'recent_pattern': recent_pattern,
            'pattern_strength': max(smart_money_pct, retail_pct, mixed_pct),
            'activity_balance': abs(smart_money_pct - retail_pct)
        }
    
    def detect_institutional_flow_patterns(self,
                                         classifications: List[Dict],
                                         price_data: pd.DataFrame) -> Dict:
        """
        Detect institutional flow patterns and accumulation/distribution phases.
        """
        if len(classifications) < 20:
            return {'pattern': 'insufficient_data'}
        
        # Analyze institutional activity correlation with price movement
        smart_money_periods = [c for c in classifications if c['classification'] == 'smart_money']
        
        if len(smart_money_periods) < 5:
            return {'pattern': 'minimal_institutional_activity'}
        
        # Analyze institutional flow direction
        accumulation_periods = sum(1 for c in smart_money_periods if c.get('accumulation_pattern', {}).get('detected', False))
        distribution_periods = sum(1 for c in smart_money_periods if c.get('distribution_pattern', {}).get('detected', False))
        
        # Calculate flow bias
        if accumulation_periods > distribution_periods * 1.5:
            flow_direction = 'net_accumulation'
            flow_strength = min(100, (accumulation_periods / len(smart_money_periods)) * 100)
        elif distribution_periods > accumulation_periods * 1.5:
            flow_direction = 'net_distribution'
            flow_strength = min(100, (distribution_periods / len(smart_money_periods)) * 100)
        else:
            flow_direction = 'balanced_flow'
            flow_strength = 50
        
        # Analyze timing of institutional activity
        institutional_indices = [c['index'] for c in smart_money_periods]
        if institutional_indices:
            recent_institutional_activity = sum(1 for idx in institutional_indices if idx >= len(classifications) - 20)
            institutional_momentum = recent_institutional_activity / min(20, len(classifications)) * 100
        else:
            institutional_momentum = 0
        
        return {
            'flow_direction': flow_direction,
            'flow_strength': round(flow_strength, 2),
            'accumulation_periods': accumulation_periods,
            'distribution_periods': distribution_periods,
            'institutional_periods': len(smart_money_periods),
            'institutional_momentum': round(institutional_momentum, 2),
            'pattern_confidence': min(100, len(smart_money_periods) * 5)
        }
    
    def calculate_sentiment_indicators(self,
                                     classifications: List[Dict],
                                     price_data: pd.DataFrame) -> Dict:
        """
        Calculate institutional vs retail sentiment indicators.
        """
        if len(classifications) < 10:
            return {'sentiment': 'insufficient_data'}
        
        # Recent sentiment analysis (last 20 periods)
        recent_count = min(20, len(classifications))
        recent_classifications = classifications[-recent_count:]
        
        recent_smart_money = sum(1 for c in recent_classifications if c['classification'] == 'smart_money')
        recent_retail = sum(1 for c in recent_classifications if c['classification'] == 'retail')
        
        # Calculate sentiment scores
        institutional_sentiment = (recent_smart_money / recent_count) * 100
        retail_sentiment = (recent_retail / recent_count) * 100
        
        # Overall sentiment
        if institutional_sentiment > 70:
            overall_sentiment = 'strong_institutional_bullish'
        elif institutional_sentiment > 55:
            overall_sentiment = 'institutional_bullish'
        elif retail_sentiment > 70:
            overall_sentiment = 'strong_retail_bearish'
        elif retail_sentiment > 55:
            overall_sentiment = 'retail_bearish'
        else:
            overall_sentiment = 'neutral'
        
        # Sentiment momentum
        if len(classifications) >= 40:
            earlier_period = classifications[-40:-20]
            earlier_smart_money = sum(1 for c in earlier_period if c['classification'] == 'smart_money')
            earlier_institutional_pct = (earlier_smart_money / len(earlier_period)) * 100
            
            sentiment_change = institutional_sentiment - earlier_institutional_pct
            
            if sentiment_change > 10:
                sentiment_momentum = 'improving_institutional'
            elif sentiment_change < -10:
                sentiment_momentum = 'weakening_institutional'
            else:
                sentiment_momentum = 'stable'
        else:
            sentiment_change = 0
            sentiment_momentum = 'unknown'
        
        return {
            'overall_sentiment': overall_sentiment,
            'institutional_sentiment': round(institutional_sentiment, 2),
            'retail_sentiment': round(retail_sentiment, 2),
            'sentiment_momentum': sentiment_momentum,
            'sentiment_change': round(sentiment_change, 2),
            'confidence_level': min(100, recent_count * 5)
        }
    
    # Helper methods
    def _calculate_classification_distribution(self, classifications: List[Dict]) -> Dict:
        """Calculate distribution statistics for classifications."""
        if not classifications:
            return {}
        
        confidence_scores = [c['confidence'] for c in classifications]
        smart_money_scores = [c['smart_money_score'] for c in classifications]
        
        return {
            'avg_confidence': round(np.mean(confidence_scores), 3),
            'avg_smart_money_score': round(np.mean(smart_money_scores), 3),
            'confidence_std': round(np.std(confidence_scores), 3),
            'high_confidence_periods': sum(1 for c in confidence_scores if c > 0.7),
            'classification_certainty': sum(1 for c in confidence_scores if c > 0.6) / len(classifications) * 100
        }
    
    def _generate_volume_classification_alerts(self,
                                             classifications: List[Dict],
                                             aggregate_analysis: Dict) -> List[Dict]:
        """Generate alerts based on volume classification analysis."""
        alerts = []
        
        # Strong institutional activity alert
        recent_smart_money = sum(1 for c in classifications[-10:] if c['classification'] == 'smart_money') if len(classifications) >= 10 else 0
        
        if recent_smart_money >= 7:  # 70% of recent periods
            alerts.append({
                'type': 'institutional_activity',
                'message': f'Strong institutional activity detected - {recent_smart_money}/10 recent periods',
                'strength': min(100, recent_smart_money * 10),
                'priority': 'high'
            })
        
        # Accumulation/Distribution alerts
        for classification in classifications[-5:]:  # Check last 5 periods
            if classification.get('accumulation_pattern', {}).get('detected', False):
                strength = classification['accumulation_pattern']['strength']
                if strength > 60:
                    alerts.append({
                        'type': 'accumulation_detected',
                        'message': f'Smart money accumulation pattern detected (strength: {strength})',
                        'strength': strength,
                        'timestamp': classification['timestamp'],
                        'priority': 'medium'
                    })
            
            elif classification.get('distribution_pattern', {}).get('detected', False):
                strength = classification['distribution_pattern']['strength']
                if strength > 60:
                    alerts.append({
                        'type': 'distribution_detected',
                        'message': f'Retail distribution pattern detected (strength: {strength})',
                        'strength': strength,
                        'timestamp': classification['timestamp'],
                        'priority': 'medium'
                    })
        
        # Pattern change alerts
        if aggregate_analysis.get('dominant_pattern') in ['institutional_dominance', 'retail_dominance']:
            pattern_strength = aggregate_analysis.get('pattern_strength', 0)
            if pattern_strength > 70:
                alerts.append({
                    'type': 'pattern_dominance',
                    'message': f"{aggregate_analysis['dominant_pattern']} detected with {pattern_strength}% strength",
                    'strength': pattern_strength,
                    'priority': 'medium'
                })
        
        return alerts