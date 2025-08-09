"""
Volume Spike Detection System

Implements comprehensive volume spike detection with price action context
as specified in Story 3.3, Task 1.
"""

from typing import Dict, List, Tuple, Optional
import pandas as pd
import numpy as np
from decimal import Decimal
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class VolumeSpikeDetector:
    """
    Advanced volume spike detection with price context analysis.
    
    Detects volume spikes >2x, >3x, >5x average with severity levels
    and analyzes price context during spikes for classification.
    """
    
    def __init__(self, 
                 lookback_periods: List[int] = None,
                 spike_thresholds: Dict[str, float] = None):
        """
        Initialize volume spike detector.
        
        Args:
            lookback_periods: List of periods for rolling averages [20, 50, 200]
            spike_thresholds: Dict of severity thresholds {'moderate': 2.0, 'strong': 3.0, 'extreme': 5.0}
        """
        self.lookback_periods = lookback_periods or [20, 50, 200]  # Short, medium, long-term
        self.spike_thresholds = spike_thresholds or {
            'moderate': 2.0,  # 2x average volume
            'strong': 3.0,    # 3x average volume  
            'extreme': 5.0    # 5x average volume
        }
        
    def detect_volume_spikes(self, 
                           price_data: pd.DataFrame, 
                           volume_data: pd.Series) -> Dict:
        """
        Detect volume spikes with comprehensive price action context.
        
        Args:
            price_data: DataFrame with OHLC data
            volume_data: Series with volume data
            
        Returns:
            Dict containing all detected spikes with classifications
        """
        if len(price_data) != len(volume_data):
            return {'error': 'Price and volume data length mismatch'}
            
        if len(volume_data) < max(self.lookback_periods):
            return {'error': f'Insufficient data - need at least {max(self.lookback_periods)} periods'}
            
        spikes = []
        max_lookback = max(self.lookback_periods)
        
        # Iterate through data starting from max lookback period
        for i in range(max_lookback, len(volume_data)):
            current_volume = volume_data.iloc[i]
            current_price = price_data.iloc[i]
            
            # Check each lookback period
            for period in self.lookback_periods:
                avg_volume = volume_data.iloc[i-period:i].mean()
                
                # Check each severity threshold
                for severity, threshold in self.spike_thresholds.items():
                    if current_volume > avg_volume * threshold:
                        # Analyze price context during spike
                        spike_context = self.analyze_price_context(
                            price_data, i, period
                        )
                        
                        # Classify the spike type
                        spike_classification = self.classify_spike(spike_context)
                        
                        # Calculate spike duration and follow-through
                        duration_analysis = self.analyze_spike_duration(
                            volume_data, i, avg_volume * threshold
                        )
                        
                        spike_data = {
                            'timestamp': current_price.name if hasattr(current_price, 'name') else i,
                            'index': i,
                            'volume': float(current_volume),
                            'average_volume': float(avg_volume),
                            'spike_ratio': float(current_volume / avg_volume),
                            'severity': severity,
                            'lookback_period': period,
                            'price_context': spike_context,
                            'classification': spike_classification,
                            'duration_analysis': duration_analysis,
                            'alert_score': self.calculate_alert_score(
                                current_volume / avg_volume, spike_context, spike_classification
                            )
                        }
                        
                        spikes.append(spike_data)
        
        # Aggregate and analyze spike patterns
        analysis_summary = self.analyze_spike_patterns(spikes)
        
        return {
            'total_spikes': len(spikes),
            'spikes_by_severity': self._group_spikes_by_severity(spikes),
            'recent_spikes': self._get_recent_spikes(spikes, len(volume_data)),
            'spike_classifications': self._group_spikes_by_classification(spikes),
            'all_spikes': spikes,
            'pattern_analysis': analysis_summary,
            'alerts': self._generate_spike_alerts(spikes)
        }
    
    def analyze_price_context(self, 
                            price_data: pd.DataFrame, 
                            spike_index: int, 
                            lookback_period: int) -> Dict:
        """
        Analyze price action context during volume spike.
        
        Returns detailed price context including breakouts, reversals, trends.
        """
        current_candle = price_data.iloc[spike_index]
        previous_period = price_data.iloc[spike_index-lookback_period:spike_index]
        
        # Basic price metrics
        open_price = current_candle['open']
        close_price = current_candle['close']
        high_price = current_candle['high']
        low_price = current_candle['low']
        
        price_change = close_price - open_price
        price_change_pct = (price_change / open_price) * 100 if open_price > 0 else 0
        
        # Range analysis
        true_range = max(
            high_price - low_price,
            abs(high_price - previous_period['close'].iloc[-1]),
            abs(low_price - previous_period['close'].iloc[-1])
        )
        avg_true_range = self._calculate_atr(previous_period, 14)
        range_expansion = true_range / avg_true_range if avg_true_range > 0 else 1
        
        # Breakout detection
        recent_high = previous_period['high'].max()
        recent_low = previous_period['low'].min()
        breakout_direction = 'none'
        
        if high_price > recent_high:
            breakout_direction = 'upward'
        elif low_price < recent_low:
            breakout_direction = 'downward'
            
        # Reversal pattern detection
        reversal_signal = self._detect_reversal_pattern(price_data, spike_index, lookback_period)
        
        # Trend context
        trend_context = self._analyze_trend_context(previous_period)
        
        # Gap analysis
        gap_analysis = self._analyze_gaps(price_data, spike_index)
        
        return {
            'price_change': float(price_change),
            'price_change_pct': float(price_change_pct),
            'range_expansion': float(range_expansion),
            'breakout_direction': breakout_direction,
            'reversal_signal': reversal_signal,
            'trend_context': trend_context,
            'gap_analysis': gap_analysis,
            'candle_type': self._classify_candle_type(current_candle),
            'support_resistance_context': self._analyze_sr_context(previous_period, current_candle)
        }
    
    def classify_spike(self, context: Dict) -> Dict:
        """
        Classify volume spike type based on price action context.
        
        Classifications: accumulation, distribution, breakout, panic, reversal
        """
        classification = 'neutral'
        confidence = 0.5
        reasons = []
        
        # Breakout classification
        if context['breakout_direction'] != 'none':
            classification = 'breakout'
            confidence = 0.8
            reasons.append(f"Price breakout {context['breakout_direction']}")
            
        # Reversal classification
        elif context['reversal_signal']['detected']:
            classification = 'reversal'
            confidence = context['reversal_signal']['confidence'] / 100
            reasons.append("Reversal pattern detected")
            
        # Accumulation vs Distribution based on price action
        elif context['price_change_pct'] > 1.0:  # Strong positive move
            if context['trend_context']['direction'] == 'up':
                classification = 'accumulation'
                confidence = 0.7
                reasons.append("Strong upward move in uptrend")
            else:
                classification = 'short_covering'
                confidence = 0.6
                reasons.append("Strong upward move against downtrend")
                
        elif context['price_change_pct'] < -1.0:  # Strong negative move
            if context['trend_context']['direction'] == 'down':
                classification = 'distribution'
                confidence = 0.7
                reasons.append("Strong downward move in downtrend")
            else:
                classification = 'panic'
                confidence = 0.6
                reasons.append("Strong downward move against uptrend")
                
        # Range expansion classification
        if context['range_expansion'] > 2.0:
            if classification == 'neutral':
                classification = 'volatility_expansion'
                confidence = 0.6
                reasons.append("Significant range expansion")
        
        return {
            'type': classification,
            'confidence': confidence,
            'reasons': reasons,
            'secondary_signals': self._identify_secondary_signals(context)
        }
    
    def analyze_spike_duration(self, 
                             volume_data: pd.Series, 
                             spike_index: int, 
                             threshold_volume: float) -> Dict:
        """
        Analyze spike duration and follow-through patterns.
        """
        # Look forward to see if volume remains elevated
        follow_through_periods = min(5, len(volume_data) - spike_index - 1)
        follow_through_volume = []
        
        for i in range(1, follow_through_periods + 1):
            if spike_index + i < len(volume_data):
                follow_through_volume.append(volume_data.iloc[spike_index + i])
        
        # Calculate follow-through metrics
        if follow_through_volume:
            avg_follow_through = np.mean(follow_through_volume)
            follow_through_ratio = avg_follow_through / threshold_volume
            sustained_periods = sum(1 for vol in follow_through_volume if vol > threshold_volume)
        else:
            avg_follow_through = 0
            follow_through_ratio = 0
            sustained_periods = 0
        
        # Look backward to see if this was part of a volume surge
        lookback_periods = min(5, spike_index)
        pre_spike_volume = []
        
        for i in range(1, lookback_periods + 1):
            pre_spike_volume.append(volume_data.iloc[spike_index - i])
        
        pre_spike_elevated = sum(1 for vol in pre_spike_volume if vol > threshold_volume)
        
        return {
            'follow_through_periods': follow_through_periods,
            'avg_follow_through_volume': float(avg_follow_through),
            'follow_through_ratio': float(follow_through_ratio),
            'sustained_periods': sustained_periods,
            'pre_spike_elevated_periods': pre_spike_elevated,
            'spike_isolation': pre_spike_elevated == 0 and sustained_periods == 0,
            'volume_surge_pattern': pre_spike_elevated > 0 or sustained_periods > 0
        }
    
    def calculate_alert_score(self, 
                            spike_ratio: float, 
                            context: Dict, 
                            classification: Dict) -> int:
        """
        Calculate alert score (0-100) for volume spike significance.
        """
        score = 0
        
        # Base score from spike magnitude
        if spike_ratio >= 5.0:
            score += 30
        elif spike_ratio >= 3.0:
            score += 20
        elif spike_ratio >= 2.0:
            score += 10
            
        # Price context bonuses
        if context['breakout_direction'] != 'none':
            score += 25
        if context['reversal_signal']['detected']:
            score += 20
        if context['range_expansion'] > 1.5:
            score += 15
        if abs(context['price_change_pct']) > 2.0:
            score += 10
            
        # Classification bonuses
        if classification['confidence'] > 0.7:
            score += 15
        if classification['type'] in ['breakout', 'reversal']:
            score += 10
            
        return min(100, score)
    
    def analyze_spike_patterns(self, spikes: List[Dict]) -> Dict:
        """
        Analyze overall patterns in detected volume spikes.
        """
        if not spikes:
            return {'pattern': 'no_spikes'}
        
        # Time-based clustering
        recent_spikes = [s for s in spikes if s['index'] >= max(s['index'] for s in spikes) - 20]
        
        # Classification distribution
        classifications = [s['classification']['type'] for s in spikes]
        classification_counts = {}
        for cls in classifications:
            classification_counts[cls] = classification_counts.get(cls, 0) + 1
        
        # Severity distribution
        severity_counts = {}
        for spike in spikes:
            sev = spike['severity']
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
        
        # Pattern identification
        pattern = 'mixed'
        if len(recent_spikes) >= 3:
            if sum(1 for s in recent_spikes if s['classification']['type'] == 'distribution') >= 2:
                pattern = 'distribution_pattern'
            elif sum(1 for s in recent_spikes if s['classification']['type'] == 'accumulation') >= 2:
                pattern = 'accumulation_pattern'
            elif sum(1 for s in recent_spikes if s['classification']['type'] == 'breakout') >= 2:
                pattern = 'breakout_pattern'
        
        return {
            'dominant_pattern': pattern,
            'total_spikes': len(spikes),
            'recent_spike_cluster': len(recent_spikes),
            'classification_distribution': classification_counts,
            'severity_distribution': severity_counts,
            'avg_alert_score': np.mean([s['alert_score'] for s in spikes]),
            'pattern_confidence': self._calculate_pattern_confidence(spikes, pattern)
        }
    
    # Helper methods
    def _group_spikes_by_severity(self, spikes: List[Dict]) -> Dict:
        """Group spikes by severity level."""
        groups = {'moderate': [], 'strong': [], 'extreme': []}
        for spike in spikes:
            groups[spike['severity']].append(spike)
        return groups
    
    def _get_recent_spikes(self, spikes: List[Dict], total_periods: int, lookback: int = 10) -> List[Dict]:
        """Get spikes from recent periods."""
        cutoff_index = total_periods - lookback
        return [spike for spike in spikes if spike['index'] >= cutoff_index]
    
    def _group_spikes_by_classification(self, spikes: List[Dict]) -> Dict:
        """Group spikes by classification type."""
        groups = {}
        for spike in spikes:
            cls_type = spike['classification']['type']
            if cls_type not in groups:
                groups[cls_type] = []
            groups[cls_type].append(spike)
        return groups
    
    def _generate_spike_alerts(self, spikes: List[Dict]) -> List[Dict]:
        """Generate trading alerts from high-significance spikes."""
        alerts = []
        high_score_spikes = [s for s in spikes if s['alert_score'] >= 70]
        
        for spike in high_score_spikes:
            alert = {
                'timestamp': spike['timestamp'],
                'alert_type': 'volume_spike',
                'severity': spike['severity'],
                'classification': spike['classification']['type'],
                'message': self._generate_alert_message(spike),
                'score': spike['alert_score'],
                'action_suggested': self._suggest_action(spike)
            }
            alerts.append(alert)
        
        return alerts
    
    def _calculate_atr(self, price_data: pd.DataFrame, periods: int) -> float:
        """Calculate Average True Range."""
        if len(price_data) < 2:
            return 0
            
        true_ranges = []
        for i in range(1, len(price_data)):
            current = price_data.iloc[i]
            previous = price_data.iloc[i-1]
            
            tr = max(
                current['high'] - current['low'],
                abs(current['high'] - previous['close']),
                abs(current['low'] - previous['close'])
            )
            true_ranges.append(tr)
        
        return np.mean(true_ranges[-periods:]) if true_ranges else 0
    
    def _detect_reversal_pattern(self, price_data: pd.DataFrame, index: int, lookback: int) -> Dict:
        """Detect potential reversal patterns."""
        # Simplified reversal detection - could be enhanced
        current = price_data.iloc[index]
        previous_period = price_data.iloc[max(0, index-lookback):index]
        
        if len(previous_period) < 3:
            return {'detected': False, 'confidence': 0}
        
        # Check for hammer/doji patterns
        body_size = abs(current['close'] - current['open'])
        total_range = current['high'] - current['low']
        
        if total_range > 0:
            body_ratio = body_size / total_range
            if body_ratio < 0.3:  # Small body relative to range
                return {'detected': True, 'confidence': 60, 'pattern': 'small_body'}
        
        # Check for gap reversal
        prev_close = previous_period['close'].iloc[-1]
        gap_size = abs(current['open'] - prev_close)
        
        if gap_size > total_range * 0.5:  # Significant gap
            return {'detected': True, 'confidence': 70, 'pattern': 'gap_reversal'}
        
        return {'detected': False, 'confidence': 0}
    
    def _analyze_trend_context(self, price_data: pd.DataFrame) -> Dict:
        """Analyze the prevailing trend context."""
        if len(price_data) < 10:
            return {'direction': 'unknown', 'strength': 0}
        
        closes = price_data['close']
        slope, _ = np.polyfit(range(len(closes)), closes, 1)
        
        # Normalize slope
        avg_price = closes.mean()
        slope_pct = (slope / avg_price) * 100 if avg_price > 0 else 0
        
        if slope_pct > 0.1:
            direction = 'up'
        elif slope_pct < -0.1:
            direction = 'down'
        else:
            direction = 'sideways'
        
        strength = min(100, abs(slope_pct) * 50)
        
        return {
            'direction': direction,
            'strength': strength,
            'slope_percentage': slope_pct
        }
    
    def _analyze_gaps(self, price_data: pd.DataFrame, index: int) -> Dict:
        """Analyze gaps in price action."""
        if index == 0:
            return {'gap_detected': False}
        
        current = price_data.iloc[index]
        previous = price_data.iloc[index - 1]
        
        gap_up = current['low'] > previous['high']
        gap_down = current['high'] < previous['low']
        
        if gap_up:
            gap_size = current['low'] - previous['high']
            gap_pct = (gap_size / previous['close']) * 100
            return {'gap_detected': True, 'direction': 'up', 'size': gap_size, 'percentage': gap_pct}
        elif gap_down:
            gap_size = previous['low'] - current['high'] 
            gap_pct = (gap_size / previous['close']) * 100
            return {'gap_detected': True, 'direction': 'down', 'size': gap_size, 'percentage': gap_pct}
        else:
            return {'gap_detected': False}
    
    def _classify_candle_type(self, candle: pd.Series) -> str:
        """Classify the type of candlestick."""
        open_price = candle['open']
        close_price = candle['close']
        high_price = candle['high']
        low_price = candle['low']
        
        body_size = abs(close_price - open_price)
        total_range = high_price - low_price
        
        if total_range == 0:
            return 'doji'
        
        body_ratio = body_size / total_range
        
        if body_ratio > 0.7:
            return 'marubozu' if close_price > open_price else 'black_marubozu'
        elif body_ratio < 0.1:
            return 'doji'
        elif body_ratio < 0.3:
            return 'spinning_top'
        else:
            return 'normal_candle'
    
    def _analyze_sr_context(self, price_data: pd.DataFrame, current_candle: pd.Series) -> Dict:
        """Analyze support/resistance context."""
        highs = price_data['high']
        lows = price_data['low']
        
        resistance_level = highs.max()
        support_level = lows.min()
        
        current_close = current_candle['close']
        
        near_resistance = abs(current_close - resistance_level) < (resistance_level * 0.01)
        near_support = abs(current_close - support_level) < (support_level * 0.01)
        
        return {
            'near_resistance': near_resistance,
            'near_support': near_support,
            'resistance_level': resistance_level,
            'support_level': support_level
        }
    
    def _identify_secondary_signals(self, context: Dict) -> List[str]:
        """Identify secondary signals from price context."""
        signals = []
        
        if context['range_expansion'] > 2.0:
            signals.append('high_volatility')
        if context['gap_analysis']['gap_detected']:
            signals.append(f"gap_{context['gap_analysis']['direction']}")
        if context['support_resistance_context']['near_resistance']:
            signals.append('at_resistance')
        if context['support_resistance_context']['near_support']:
            signals.append('at_support')
        
        return signals
    
    def _calculate_pattern_confidence(self, spikes: List[Dict], pattern: str) -> float:
        """Calculate confidence level for identified pattern."""
        if not spikes:
            return 0.0
        
        if pattern == 'no_spikes':
            return 1.0
        
        # Base confidence on classification consistency and alert scores
        avg_confidence = np.mean([s['classification']['confidence'] for s in spikes])
        avg_alert_score = np.mean([s['alert_score'] for s in spikes])
        
        # Normalize to 0-1 range
        confidence = (avg_confidence + (avg_alert_score / 100)) / 2
        return round(confidence, 3)
    
    def _generate_alert_message(self, spike: Dict) -> str:
        """Generate human-readable alert message."""
        severity = spike['severity']
        classification = spike['classification']['type']
        ratio = spike['spike_ratio']
        
        return f"{severity.title()} volume spike detected ({ratio:.1f}x average) - {classification} pattern identified"
    
    def _suggest_action(self, spike: Dict) -> str:
        """Suggest trading action based on spike analysis."""
        classification = spike['classification']['type']
        context = spike['price_context']
        
        if classification == 'breakout' and context['breakout_direction'] == 'upward':
            return 'monitor_for_long_entry'
        elif classification == 'breakout' and context['breakout_direction'] == 'downward':
            return 'monitor_for_short_entry'
        elif classification == 'distribution':
            return 'consider_profit_taking'
        elif classification == 'accumulation':
            return 'monitor_for_accumulation'
        elif classification == 'reversal':
            return 'watch_for_trend_change'
        else:
            return 'monitor_price_action'