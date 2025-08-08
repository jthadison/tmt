"""
Market Structure Analysis Utilities

Provides common market structure analysis functions used across
the Wyckoff Pattern Detection Engine components:
- Swing high/low identification
- Trend analysis and strength calculation
- Support/resistance level detection
- Price structure quality assessment
"""

from typing import Dict, List, Tuple, Optional
from decimal import Decimal
import pandas as pd
import numpy as np
from datetime import datetime


class MarketStructureAnalyzer:
    """Analyzes market structure patterns in price data"""
    
    def __init__(self, swing_lookback: int = 3):
        self.swing_lookback = swing_lookback
    
    def identify_swing_highs_lows(self, price_data: pd.DataFrame) -> Dict[str, List[Tuple[int, float]]]:
        """
        Identify swing highs and lows in price data
        
        Returns:
            Dict with 'swing_highs' and 'swing_lows' keys containing
            lists of (index, price) tuples
        """
        swing_highs = []
        swing_lows = []
        
        if len(price_data) < self.swing_lookback * 2 + 1:
            return {'swing_highs': swing_highs, 'swing_lows': swing_lows}
        
        for i in range(self.swing_lookback, len(price_data) - self.swing_lookback):
            current_high = price_data['high'].iloc[i]
            current_low = price_data['low'].iloc[i]
            
            # Check for swing high
            is_swing_high = True
            for j in range(i - self.swing_lookback, i + self.swing_lookback + 1):
                if j != i and price_data['high'].iloc[j] >= current_high:
                    is_swing_high = False
                    break
            
            if is_swing_high:
                swing_highs.append((i, current_high))
            
            # Check for swing low
            is_swing_low = True
            for j in range(i - self.swing_lookback, i + self.swing_lookback + 1):
                if j != i and price_data['low'].iloc[j] <= current_low:
                    is_swing_low = False
                    break
            
            if is_swing_low:
                swing_lows.append((i, current_low))
        
        return {
            'swing_highs': swing_highs,
            'swing_lows': swing_lows
        }
    
    def analyze_trend_direction(self, price_data: pd.DataFrame, period: int = 20) -> Dict:
        """
        Analyze trend direction and strength using multiple methods
        
        Args:
            price_data: OHLC price data
            period: Number of periods to analyze
        
        Returns:
            Dict with trend analysis results
        """
        if len(price_data) < period:
            return {'direction': 'undefined', 'strength': 0, 'confidence': 0}
        
        recent_data = price_data.iloc[-period:] if len(price_data) > period else price_data
        
        # Method 1: Linear regression slope
        closes = recent_data['close'].values
        x = np.arange(len(closes))
        slope, intercept = np.polyfit(x, closes, 1)
        
        # Normalize slope to percentage per period
        avg_price = np.mean(closes)
        slope_pct = (slope / avg_price) * 100 if avg_price != 0 else 0
        
        # Method 2: Moving average comparison
        ma_short = recent_data['close'].rolling(window=min(5, len(recent_data)//2)).mean().iloc[-1]
        ma_long = recent_data['close'].rolling(window=min(10, len(recent_data))).mean().iloc[-1]
        ma_direction = 'up' if ma_short > ma_long else 'down' if ma_short < ma_long else 'sideways'
        
        # Method 3: Higher highs / Lower lows analysis
        swings = self.identify_swing_highs_lows(recent_data)
        hh_ll_direction = self._analyze_swing_structure(swings['swing_highs'], swings['swing_lows'])
        
        # Combine methods for final direction
        slope_direction = 'up' if slope_pct > 0.1 else 'down' if slope_pct < -0.1 else 'sideways'
        
        # Vote-based direction
        directions = [slope_direction, ma_direction, hh_ll_direction]
        direction_counts = {}
        for d in directions:
            direction_counts[d] = direction_counts.get(d, 0) + 1
        
        final_direction = max(direction_counts.keys(), key=lambda k: direction_counts[k])
        confidence = direction_counts[final_direction] / len(directions) * 100
        
        # Calculate strength (R-squared of linear regression)
        y_pred = slope * x + intercept
        ss_res = np.sum((closes - y_pred) ** 2)
        ss_tot = np.sum((closes - np.mean(closes)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        strength = max(0, min(100, r_squared * 100))
        
        return {
            'direction': final_direction,
            'strength': strength,
            'confidence': confidence,
            'slope_percentage': slope_pct,
            'r_squared': r_squared,
            'methods': {
                'slope_direction': slope_direction,
                'ma_direction': ma_direction,
                'swing_direction': hh_ll_direction
            }
        }
    
    def calculate_trend_strength(self, price_data: pd.DataFrame) -> Decimal:
        """
        Calculate overall trend strength score (0-100)
        
        Combines multiple factors:
        - Linear regression R-squared
        - Directional consistency
        - Momentum indicators
        """
        if len(price_data) < 10:
            return Decimal('50')
        
        trend_analysis = self.analyze_trend_direction(price_data)
        
        # Base strength from R-squared
        base_strength = trend_analysis['r_squared']
        
        # Directional consistency bonus
        consistency_bonus = trend_analysis['confidence'] / 100 * 0.2
        
        # Momentum factor
        recent_close = price_data['close'].iloc[-1]
        earlier_close = price_data['close'].iloc[-min(10, len(price_data))]
        momentum = abs(recent_close - earlier_close) / earlier_close if earlier_close != 0 else 0
        momentum_factor = min(0.2, momentum * 2)
        
        total_strength = (base_strength + consistency_bonus + momentum_factor) * 100
        return Decimal(str(round(min(100, max(0, total_strength)), 2)))
    
    def identify_support_resistance_levels(self, 
                                         price_data: pd.DataFrame, 
                                         touch_threshold: int = 2,
                                         tolerance_pct: float = 0.1) -> Dict:
        """
        Identify key support and resistance levels based on price touches
        
        Args:
            price_data: OHLC price data
            touch_threshold: Minimum number of touches required
            tolerance_pct: Tolerance percentage for level matching
        
        Returns:
            Dict with support and resistance levels
        """
        swings = self.identify_swing_highs_lows(price_data)
        
        # Group swing levels by proximity
        resistance_levels = self._group_levels_by_proximity(
            [price for _, price in swings['swing_highs']], 
            tolerance_pct
        )
        
        support_levels = self._group_levels_by_proximity(
            [price for _, price in swings['swing_lows']], 
            tolerance_pct
        )
        
        # Filter by touch count
        significant_resistance = []
        for level_group in resistance_levels:
            if len(level_group['prices']) >= touch_threshold:
                significant_resistance.append({
                    'level': level_group['avg_price'],
                    'touches': len(level_group['prices']),
                    'strength': self._calculate_level_strength(level_group, price_data),
                    'type': 'resistance'
                })
        
        significant_support = []
        for level_group in support_levels:
            if len(level_group['prices']) >= touch_threshold:
                significant_support.append({
                    'level': level_group['avg_price'],
                    'touches': len(level_group['prices']),
                    'strength': self._calculate_level_strength(level_group, price_data),
                    'type': 'support'
                })
        
        # Sort by strength
        significant_resistance.sort(key=lambda x: x['strength'], reverse=True)
        significant_support.sort(key=lambda x: x['strength'], reverse=True)
        
        return {
            'resistance_levels': significant_resistance[:5],  # Top 5
            'support_levels': significant_support[:5],       # Top 5
            'all_swing_highs': swings['swing_highs'],
            'all_swing_lows': swings['swing_lows']
        }
    
    def assess_price_structure_quality(self, price_data: pd.DataFrame, pattern_type: str = 'general') -> Dict:
        """
        Assess the quality of price structure for pattern recognition
        
        Args:
            price_data: OHLC price data
            pattern_type: Type of pattern being assessed (affects scoring weights)
        
        Returns:
            Dict with structure quality metrics
        """
        if len(price_data) < 10:
            return {'quality_score': 50, 'factors': {}}
        
        # Factor 1: Trend consistency
        trend_analysis = self.analyze_trend_direction(price_data)
        trend_consistency = trend_analysis['confidence']
        
        # Factor 2: Volatility assessment
        returns = price_data['close'].pct_change().dropna()
        volatility = returns.std() * 100  # As percentage
        
        # Optimal volatility depends on pattern type
        if pattern_type in ['accumulation', 'distribution']:
            # Lower volatility is better for sideways patterns
            volatility_score = max(0, 100 - (volatility * 50))
        else:
            # Moderate volatility is better for trending patterns
            volatility_score = 100 - abs(volatility - 1.5) * 30
        
        # Factor 3: Price range consistency
        ranges = price_data['high'] - price_data['low']
        range_consistency = 100 - (ranges.std() / ranges.mean() * 100) if ranges.mean() != 0 else 0
        range_consistency = max(0, min(100, range_consistency))
        
        # Factor 4: Gap analysis (fewer gaps = better structure)
        gaps = []
        for i in range(1, len(price_data)):
            prev_close = price_data['close'].iloc[i-1]
            curr_open = price_data['open'].iloc[i]
            gap_size = abs(curr_open - prev_close) / prev_close
            gaps.append(gap_size)
        
        avg_gap = sum(gaps) / len(gaps) if gaps else 0
        gap_score = max(0, 100 - (avg_gap * 1000))  # Penalize large gaps
        
        # Factor 5: Swing structure quality
        swings = self.identify_swing_highs_lows(price_data)
        swing_quality = self._assess_swing_structure_quality(swings, pattern_type)
        
        # Combine factors with pattern-specific weights
        weights = self._get_structure_quality_weights(pattern_type)
        
        factors = {
            'trend_consistency': trend_consistency,
            'volatility_score': volatility_score,
            'range_consistency': range_consistency,
            'gap_score': gap_score,
            'swing_quality': swing_quality
        }
        
        quality_score = sum(factors[factor] * weights[factor] for factor in factors)
        
        return {
            'quality_score': round(quality_score, 2),
            'factors': factors,
            'weights': weights,
            'interpretation': self._interpret_quality_score(quality_score)
        }
    
    def calculate_price_momentum(self, price_data: pd.DataFrame, periods: List[int] = [5, 10, 20]) -> Dict:
        """
        Calculate price momentum across multiple periods
        
        Returns:
            Dict with momentum calculations for different time periods
        """
        momentum_data = {}
        
        current_price = price_data['close'].iloc[-1]
        
        for period in periods:
            if len(price_data) >= period:
                historical_price = price_data['close'].iloc[-period]
                momentum_pct = (current_price - historical_price) / historical_price * 100
                
                # Momentum strength classification
                if abs(momentum_pct) > 5:
                    strength = 'strong'
                elif abs(momentum_pct) > 2:
                    strength = 'moderate'
                else:
                    strength = 'weak'
                
                momentum_data[f'{period}_period'] = {
                    'momentum_percent': momentum_pct,
                    'direction': 'bullish' if momentum_pct > 0 else 'bearish',
                    'strength': strength,
                    'historical_price': historical_price,
                    'current_price': current_price
                }
        
        # Overall momentum assessment
        avg_momentum = sum(data['momentum_percent'] for data in momentum_data.values()) / len(momentum_data) if momentum_data else 0
        
        momentum_data['overall'] = {
            'avg_momentum_percent': avg_momentum,
            'direction': 'bullish' if avg_momentum > 0 else 'bearish',
            'strength': 'strong' if abs(avg_momentum) > 3 else 'moderate' if abs(avg_momentum) > 1 else 'weak'
        }
        
        return momentum_data
    
    def _analyze_swing_structure(self, swing_highs: List[Tuple], swing_lows: List[Tuple]) -> str:
        """Analyze swing structure to determine trend direction"""
        if len(swing_highs) < 2 and len(swing_lows) < 2:
            return 'sideways'
        
        # Check for higher highs pattern
        hh_count = 0
        if len(swing_highs) >= 2:
            for i in range(1, len(swing_highs)):
                if swing_highs[i][1] > swing_highs[i-1][1]:
                    hh_count += 1
        
        # Check for higher lows pattern
        hl_count = 0
        if len(swing_lows) >= 2:
            for i in range(1, len(swing_lows)):
                if swing_lows[i][1] > swing_lows[i-1][1]:
                    hl_count += 1
        
        # Check for lower lows pattern
        ll_count = 0
        if len(swing_lows) >= 2:
            for i in range(1, len(swing_lows)):
                if swing_lows[i][1] < swing_lows[i-1][1]:
                    ll_count += 1
        
        # Check for lower highs pattern
        lh_count = 0
        if len(swing_highs) >= 2:
            for i in range(1, len(swing_highs)):
                if swing_highs[i][1] < swing_highs[i-1][1]:
                    lh_count += 1
        
        # Determine trend based on predominant pattern
        uptrend_score = hh_count + hl_count
        downtrend_score = ll_count + lh_count
        
        if uptrend_score > downtrend_score:
            return 'up'
        elif downtrend_score > uptrend_score:
            return 'down'
        else:
            return 'sideways'
    
    def _group_levels_by_proximity(self, levels: List[float], tolerance_pct: float) -> List[Dict]:
        """Group price levels by proximity within tolerance"""
        if not levels:
            return []
        
        sorted_levels = sorted(levels)
        groups = []
        current_group = [sorted_levels[0]]
        
        for i in range(1, len(sorted_levels)):
            current_level = sorted_levels[i]
            group_avg = sum(current_group) / len(current_group)
            
            # Check if current level is within tolerance of group average
            if abs(current_level - group_avg) / group_avg <= tolerance_pct / 100:
                current_group.append(current_level)
            else:
                # Start new group
                groups.append({
                    'prices': current_group,
                    'avg_price': sum(current_group) / len(current_group),
                    'min_price': min(current_group),
                    'max_price': max(current_group)
                })
                current_group = [current_level]
        
        # Add the last group
        if current_group:
            groups.append({
                'prices': current_group,
                'avg_price': sum(current_group) / len(current_group),
                'min_price': min(current_group),
                'max_price': max(current_group)
            })
        
        return groups
    
    def _calculate_level_strength(self, level_group: Dict, price_data: pd.DataFrame) -> float:
        """Calculate strength score for a support/resistance level"""
        # Base strength from number of touches
        touch_strength = len(level_group['prices']) * 20
        
        # Recency factor (more recent touches are stronger)
        # This would require timestamp analysis in full implementation
        recency_strength = 20
        
        # Volume factor (would require volume analysis)
        volume_strength = 20
        
        # Total strength
        total_strength = min(100, touch_strength + recency_strength + volume_strength)
        return total_strength
    
    def _assess_swing_structure_quality(self, swings: Dict, pattern_type: str) -> float:
        """Assess quality of swing structure"""
        swing_highs = swings['swing_highs']
        swing_lows = swings['swing_lows']
        
        if not swing_highs and not swing_lows:
            return 50  # Neutral score
        
        total_swings = len(swing_highs) + len(swing_lows)
        
        # Check for clear patterns based on pattern type
        if pattern_type in ['accumulation', 'distribution']:
            # For sideways patterns, consistent swing levels are better
            high_consistency = self._calculate_level_consistency([h[1] for h in swing_highs])
            low_consistency = self._calculate_level_consistency([l[1] for l in swing_lows])
            swing_quality = (high_consistency + low_consistency) / 2
        else:
            # For trending patterns, progressive swings are better
            swing_quality = self._calculate_swing_progression_quality(swing_highs, swing_lows, pattern_type)
        
        return swing_quality
    
    def _calculate_level_consistency(self, levels: List[float]) -> float:
        """Calculate how consistent a set of levels are"""
        if len(levels) < 2:
            return 50
        
        mean_level = sum(levels) / len(levels)
        std_dev = np.std(levels)
        coefficient_of_variation = std_dev / mean_level if mean_level != 0 else 1
        
        # Lower CV means higher consistency
        consistency_score = max(0, 100 - (coefficient_of_variation * 100))
        return consistency_score
    
    def _calculate_swing_progression_quality(self, swing_highs: List, swing_lows: List, pattern_type: str) -> float:
        """Calculate quality of swing progression for trending patterns"""
        if pattern_type == 'markup':
            # Look for higher highs and higher lows
            hh_score = self._score_higher_pattern([h[1] for h in swing_highs])
            hl_score = self._score_higher_pattern([l[1] for l in swing_lows])
            return (hh_score + hl_score) / 2
        elif pattern_type == 'markdown':
            # Look for lower highs and lower lows
            lh_score = self._score_lower_pattern([h[1] for h in swing_highs])
            ll_score = self._score_lower_pattern([l[1] for l in swing_lows])
            return (lh_score + ll_score) / 2
        else:
            return 50  # Neutral for other patterns
    
    def _score_higher_pattern(self, levels: List[float]) -> float:
        """Score how well levels follow a higher highs/lows pattern"""
        if len(levels) < 2:
            return 50
        
        higher_count = 0
        total_comparisons = len(levels) - 1
        
        for i in range(1, len(levels)):
            if levels[i] > levels[i-1]:
                higher_count += 1
        
        return (higher_count / total_comparisons) * 100
    
    def _score_lower_pattern(self, levels: List[float]) -> float:
        """Score how well levels follow a lower highs/lows pattern"""
        if len(levels) < 2:
            return 50
        
        lower_count = 0
        total_comparisons = len(levels) - 1
        
        for i in range(1, len(levels)):
            if levels[i] < levels[i-1]:
                lower_count += 1
        
        return (lower_count / total_comparisons) * 100
    
    def _get_structure_quality_weights(self, pattern_type: str) -> Dict[str, float]:
        """Get weights for structure quality factors based on pattern type"""
        base_weights = {
            'trend_consistency': 0.25,
            'volatility_score': 0.20,
            'range_consistency': 0.20,
            'gap_score': 0.15,
            'swing_quality': 0.20
        }
        
        if pattern_type in ['accumulation', 'distribution']:
            # For sideways patterns, emphasize range and volatility consistency
            base_weights['range_consistency'] = 0.30
            base_weights['volatility_score'] = 0.25
            base_weights['trend_consistency'] = 0.15
        elif pattern_type in ['markup', 'markdown']:
            # For trending patterns, emphasize trend consistency and swing quality
            base_weights['trend_consistency'] = 0.35
            base_weights['swing_quality'] = 0.30
            base_weights['volatility_score'] = 0.15
        
        return base_weights
    
    def _interpret_quality_score(self, score: float) -> str:
        """Interpret structure quality score"""
        if score >= 80:
            return "Excellent structure quality - high pattern reliability"
        elif score >= 65:
            return "Good structure quality - reliable for pattern analysis"
        elif score >= 50:
            return "Adequate structure quality - proceed with caution"
        elif score >= 35:
            return "Poor structure quality - low pattern reliability"
        else:
            return "Very poor structure quality - avoid pattern signals"