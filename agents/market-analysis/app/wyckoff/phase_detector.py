"""
Wyckoff Phase Detection Algorithm

Implements the four-phase Wyckoff cycle detection:
1. Accumulation - sideways price movement with declining volatility
2. Markup - strong upward price movement with volume confirmation  
3. Distribution - sideways movement at higher levels with volume divergence
4. Markdown - declining price structure with selling pressure
"""

from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from dataclasses import dataclass
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


@dataclass
class PhaseDetectionResult:
    """Result from phase detection analysis"""
    phase: str  # accumulation, markup, distribution, markdown
    confidence: Decimal
    criteria: Dict
    key_levels: Dict
    detection_time: datetime
    timeframe: str


class AccumulationDetector:
    """Detects accumulation phase characteristics"""
    
    def __init__(self, min_period: int = 20, volatility_threshold: float = 0.02):
        self.min_period = min_period
        self.volatility_threshold = volatility_threshold
    
    def detect_accumulation(self, price_data: pd.DataFrame, volume_data: pd.Series) -> Dict:
        """
        Detect accumulation phase characteristics:
        - Sideways price movement with declining volatility
        - Volume increasing on any upward moves
        - Support level holding with volume
        - Spring patterns (false breakdowns)
        """
        if len(price_data) < self.min_period:
            return {'detected': False, 'reason': 'Insufficient data'}
        
        # Calculate price range contraction
        price_range_contraction = self._calculate_range_contraction(price_data)
        
        # Analyze volume on strength vs weakness
        volume_on_strength = self._analyze_volume_strength(price_data, volume_data)
        
        # Identify support levels holding
        support_holding = self._identify_support_levels(price_data, volume_data)
        
        # Detect spring patterns
        spring_patterns = self._detect_springs(price_data, volume_data, support_holding.get('support_level'))
        
        criteria = {
            'price_range_contraction': price_range_contraction,
            'volume_on_strength': volume_on_strength,
            'support_holding': support_holding,
            'spring_patterns': spring_patterns
        }
        
        confidence = self._calculate_phase_confidence(criteria)
        
        return {
            'phase': 'accumulation',
            'confidence': confidence,
            'criteria': criteria,
            'key_levels': self._extract_key_levels(price_data, volume_data, support_holding),
            'detected': confidence > Decimal('60.0')
        }
    
    def _calculate_range_contraction(self, price_data: pd.DataFrame) -> Dict:
        """Calculate if price range is contracting"""
        if len(price_data) < self.min_period:
            return {'score': 0, 'contraction_ratio': 0}
        
        # Calculate rolling range (high - low) over different periods
        recent_period = min(10, len(price_data) // 3)
        earlier_period = min(20, len(price_data) // 2)
        
        recent_range = (price_data['high'].iloc[-recent_period:] - price_data['low'].iloc[-recent_period:]).mean()
        earlier_range = (price_data['high'].iloc[-earlier_period:-recent_period] - price_data['low'].iloc[-earlier_period:-recent_period]).mean()
        
        if earlier_range == 0:
            return {'score': 0, 'contraction_ratio': 0}
        
        contraction_ratio = (earlier_range - recent_range) / earlier_range
        
        # Score based on range contraction (higher score for more contraction)
        score = min(100, max(0, contraction_ratio * 200))  # Scale to 0-100
        
        return {
            'score': score,
            'contraction_ratio': contraction_ratio,
            'recent_range': float(recent_range),
            'earlier_range': float(earlier_range)
        }
    
    def _analyze_volume_strength(self, price_data: pd.DataFrame, volume_data: pd.Series) -> Dict:
        """Analyze volume confirmation on strength vs weakness"""
        if len(price_data) != len(volume_data):
            return {'score': 0, 'strength_volume_ratio': 0}
        
        # Identify up vs down candles
        up_candles = price_data['close'] > price_data['open']
        down_candles = price_data['close'] < price_data['open']
        
        # Calculate average volume on up vs down moves
        up_volume = volume_data[up_candles].mean() if up_candles.any() else 0
        down_volume = volume_data[down_candles].mean() if down_candles.any() else 0
        
        if down_volume == 0:
            strength_volume_ratio = 2.0  # Perfect accumulation pattern
        else:
            strength_volume_ratio = up_volume / down_volume
        
        # Score higher when volume is higher on up moves
        score = min(100, max(0, (strength_volume_ratio - 1) * 50))
        
        return {
            'score': score,
            'strength_volume_ratio': strength_volume_ratio,
            'up_volume_avg': float(up_volume),
            'down_volume_avg': float(down_volume)
        }
    
    def _identify_support_levels(self, price_data: pd.DataFrame, volume_data: pd.Series) -> Dict:
        """Identify support levels that are holding with volume"""
        if len(price_data) < 10:
            return {'score': 0, 'support_level': None, 'touches': 0}
        
        # Find potential support level (lowest low in recent period)
        lookback = min(20, len(price_data))
        support_level = price_data['low'].iloc[-lookback:].min()
        
        # Count touches near support level (within 0.1% tolerance)
        tolerance = support_level * 0.001  # 0.1% tolerance
        touches = 0
        touch_volumes = []
        
        for i, row in price_data.iloc[-lookback:].iterrows():
            if abs(row['low'] - support_level) <= tolerance:
                touches += 1
                if i < len(volume_data):
                    touch_volumes.append(volume_data.iloc[i])
        
        # Analyze if volume increases at support touches
        avg_volume = volume_data.mean()
        support_volume_ratio = (sum(touch_volumes) / len(touch_volumes)) / avg_volume if touch_volumes else 0
        
        # Score based on multiple touches with increasing volume
        score = min(100, (touches * 15) + (support_volume_ratio * 30))
        
        return {
            'score': score,
            'support_level': float(support_level),
            'touches': touches,
            'support_volume_ratio': support_volume_ratio
        }
    
    def _detect_springs(self, price_data: pd.DataFrame, volume_data: pd.Series, support_level: Optional[float]) -> Dict:
        """Detect spring patterns (false breakdowns below support)"""
        if support_level is None or len(price_data) < 5:
            return {'score': 0, 'springs_detected': 0}
        
        springs_detected = 0
        spring_strength_total = 0
        
        for i in range(1, len(price_data)):
            current = price_data.iloc[i]
            previous = price_data.iloc[i-1]
            
            # Check for spring: low breaks support but close recovers above
            if (current['low'] < support_level and 
                current['close'] > support_level and
                previous['close'] >= support_level):
                
                springs_detected += 1
                
                # Calculate spring strength based on recovery and volume
                recovery_ratio = (current['close'] - current['low']) / (current['high'] - current['low'])
                volume_ratio = volume_data.iloc[i] / volume_data.mean()
                spring_strength = recovery_ratio * volume_ratio
                spring_strength_total += spring_strength
        
        avg_spring_strength = spring_strength_total / springs_detected if springs_detected > 0 else 0
        score = min(100, (springs_detected * 30) + (avg_spring_strength * 20))
        
        return {
            'score': score,
            'springs_detected': springs_detected,
            'avg_spring_strength': avg_spring_strength
        }
    
    def _calculate_phase_confidence(self, criteria: Dict) -> Decimal:
        """Calculate overall confidence for accumulation phase"""
        weights = {
            'price_range_contraction': 0.25,
            'volume_on_strength': 0.30,
            'support_holding': 0.30,
            'spring_patterns': 0.15
        }
        
        total_score = 0
        for factor, weight in weights.items():
            factor_score = criteria[factor].get('score', 0)
            total_score += factor_score * weight
        
        return Decimal(str(round(total_score, 2)))
    
    def _extract_key_levels(self, price_data: pd.DataFrame, volume_data: pd.Series, support_data: Dict) -> Dict:
        """Extract key levels for trading decisions"""
        support_level = support_data.get('support_level')
        
        # Find resistance level (highest high in recent period)
        lookback = min(20, len(price_data))
        resistance_level = price_data['high'].iloc[-lookback:].max()
        
        current_price = price_data['close'].iloc[-1]
        
        # Calculate entry, stop, and target levels
        entry_level = current_price
        stop_level = support_level * 0.999 if support_level else current_price * 0.995  # 0.1% below support
        target_level = resistance_level * 1.001 if resistance_level else current_price * 1.02  # 0.1% above resistance
        
        return {
            'support': float(support_level) if support_level else None,
            'resistance': float(resistance_level),
            'entry': float(entry_level),
            'stop': float(stop_level),
            'target': float(target_level),
            'current_price': float(current_price)
        }


class MarkupDetector:
    """Detects markup phase characteristics"""
    
    def __init__(self, min_trend_strength: float = 0.7):
        self.min_trend_strength = min_trend_strength
    
    def detect_markup(self, price_data: pd.DataFrame, volume_data: pd.Series) -> Dict:
        """
        Detect markup phase characteristics:
        - Strong upward price movement
        - Volume confirmation on breakouts
        - Higher highs and higher lows structure
        - Pullbacks to previous resistance as support
        """
        if len(price_data) < 10:
            return {'detected': False, 'reason': 'Insufficient data'}
        
        trend_strength = self._calculate_trend_strength(price_data)
        breakout_volume = self._validate_breakout_volume(price_data, volume_data)
        structure_quality = self._analyze_hh_hl_structure(price_data)
        
        criteria = {
            'trend_strength': trend_strength,
            'breakout_volume': breakout_volume,
            'structure_quality': structure_quality
        }
        
        confidence = self._calculate_markup_confidence(criteria)
        
        return {
            'phase': 'markup',
            'confidence': confidence,
            'criteria': criteria,
            'key_levels': self._extract_markup_levels(price_data),
            'detected': confidence > Decimal('60.0')
        }
    
    def _calculate_trend_strength(self, price_data: pd.DataFrame) -> Dict:
        """Calculate strength of upward trend"""
        if len(price_data) < 5:
            return {'score': 0, 'trend_angle': 0}
        
        # Calculate linear regression slope of closing prices
        y = price_data['close'].values
        x = np.arange(len(y))
        
        # Linear regression
        slope, intercept = np.polyfit(x, y, 1)
        
        # Calculate R-squared to measure trend consistency
        y_pred = slope * x + intercept
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        
        # Normalize slope to percentage per period
        avg_price = np.mean(y)
        trend_strength = (slope / avg_price) * 100 if avg_price != 0 else 0
        
        # Score based on positive slope and consistency
        score = 0
        if trend_strength > 0:
            score = min(100, trend_strength * 50 + r_squared * 50)
        
        return {
            'score': score,
            'trend_angle': trend_strength,
            'r_squared': r_squared,
            'slope': slope
        }
    
    def _validate_breakout_volume(self, price_data: pd.DataFrame, volume_data: pd.Series) -> Dict:
        """Validate volume confirmation on breakouts"""
        if len(price_data) < 10:
            return {'score': 0, 'breakout_volume_ratio': 0}
        
        # Identify potential breakouts (new highs)
        lookback = min(10, len(price_data) // 2)
        breakout_points = []
        
        for i in range(lookback, len(price_data)):
            current_high = price_data['high'].iloc[i]
            previous_highs = price_data['high'].iloc[i-lookback:i]
            
            if current_high > previous_highs.max():
                breakout_points.append((i, volume_data.iloc[i]))
        
        if not breakout_points:
            return {'score': 0, 'breakout_volume_ratio': 0}
        
        # Calculate average volume on breakouts vs normal volume
        breakout_volumes = [vol for _, vol in breakout_points]
        avg_breakout_volume = sum(breakout_volumes) / len(breakout_volumes)
        avg_volume = volume_data.mean()
        
        breakout_volume_ratio = avg_breakout_volume / avg_volume if avg_volume > 0 else 0
        
        # Score higher for volume expansion on breakouts
        score = min(100, (breakout_volume_ratio - 1) * 50)
        
        return {
            'score': max(0, score),
            'breakout_volume_ratio': breakout_volume_ratio,
            'breakouts_detected': len(breakout_points)
        }
    
    def _analyze_hh_hl_structure(self, price_data: pd.DataFrame) -> Dict:
        """Analyze higher highs and higher lows structure quality"""
        if len(price_data) < 6:
            return {'score': 0, 'structure_integrity': 0}
        
        # Find swing highs and lows
        swing_highs = []
        swing_lows = []
        
        for i in range(2, len(price_data) - 2):
            # Swing high: higher than 2 candles before and after
            if (price_data['high'].iloc[i] > price_data['high'].iloc[i-2:i].max() and
                price_data['high'].iloc[i] > price_data['high'].iloc[i+1:i+3].max()):
                swing_highs.append((i, price_data['high'].iloc[i]))
            
            # Swing low: lower than 2 candles before and after
            if (price_data['low'].iloc[i] < price_data['low'].iloc[i-2:i].min() and
                price_data['low'].iloc[i] < price_data['low'].iloc[i+1:i+3].min()):
                swing_lows.append((i, price_data['low'].iloc[i]))
        
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
        
        total_swings = len(swing_highs) + len(swing_lows)
        structure_integrity = (hh_count + hl_count) / total_swings if total_swings > 0 else 0
        
        score = structure_integrity * 100
        
        return {
            'score': score,
            'structure_integrity': structure_integrity,
            'higher_highs': hh_count,
            'higher_lows': hl_count,
            'total_swings': total_swings
        }
    
    def _calculate_markup_confidence(self, criteria: Dict) -> Decimal:
        """Calculate overall confidence for markup phase"""
        weights = {
            'trend_strength': 0.40,
            'breakout_volume': 0.35, 
            'structure_quality': 0.25
        }
        
        total_score = 0
        for factor, weight in weights.items():
            factor_score = criteria[factor].get('score', 0)
            total_score += factor_score * weight
        
        return Decimal(str(round(total_score, 2)))
    
    def _extract_markup_levels(self, price_data: pd.DataFrame) -> Dict:
        """Extract key levels for markup phase"""
        current_price = price_data['close'].iloc[-1]
        recent_high = price_data['high'].iloc[-10:].max()
        recent_low = price_data['low'].iloc[-10:].min()
        
        return {
            'support': float(recent_low),
            'resistance': float(recent_high),
            'entry': float(current_price),
            'stop': float(recent_low * 0.995),
            'target': float(recent_high * 1.02),
            'current_price': float(current_price)
        }


class DistributionDetector:
    """Detects distribution phase characteristics"""
    
    def detect_distribution(self, price_data: pd.DataFrame, volume_data: pd.Series) -> Dict:
        """
        Detect distribution phase characteristics:
        - Sideways movement after uptrend
        - Volume divergence (lower volume on up moves)
        - Resistance holding at higher levels
        - Upthrust patterns (false breakouts above resistance)
        """
        if len(price_data) < 20:
            return {'detected': False, 'reason': 'Insufficient data'}
        
        # Check if we're after an uptrend (prerequisite for distribution)
        prior_trend = self._analyze_prior_trend(price_data)
        if prior_trend['trend_direction'] != 'up':
            return {'detected': False, 'reason': 'No prior uptrend detected'}
        
        sideways_movement = self._detect_sideways_movement(price_data)
        volume_divergence = self._analyze_volume_divergence(price_data, volume_data)
        resistance_holding = self._identify_resistance_levels(price_data, volume_data)
        upthrust_patterns = self._detect_upthrusts(price_data, volume_data, resistance_holding.get('resistance_level'))
        
        criteria = {
            'prior_trend': prior_trend,
            'sideways_movement': sideways_movement,
            'volume_divergence': volume_divergence,
            'resistance_holding': resistance_holding,
            'upthrust_patterns': upthrust_patterns
        }
        
        confidence = self._calculate_distribution_confidence(criteria)
        
        return {
            'phase': 'distribution',
            'confidence': confidence,
            'criteria': criteria,
            'key_levels': self._extract_distribution_levels(price_data, resistance_holding),
            'detected': confidence > Decimal('60.0')
        }
    
    def _analyze_prior_trend(self, price_data: pd.DataFrame) -> Dict:
        """Analyze if there was a prior uptrend"""
        if len(price_data) < 20:
            return {'trend_direction': 'none', 'trend_strength': 0}
        
        # Look at earlier portion of data for trend
        trend_period = len(price_data) // 2
        trend_data = price_data.iloc[:trend_period]
        
        # Calculate linear regression slope
        y = trend_data['close'].values
        x = np.arange(len(y))
        slope, _ = np.polyfit(x, y, 1)
        
        avg_price = np.mean(y)
        trend_strength = (slope / avg_price) * 100 if avg_price != 0 else 0
        
        trend_direction = 'up' if trend_strength > 0.5 else 'down' if trend_strength < -0.5 else 'sideways'
        
        return {
            'trend_direction': trend_direction,
            'trend_strength': trend_strength
        }
    
    def _detect_sideways_movement(self, price_data: pd.DataFrame) -> Dict:
        """Detect sideways movement in recent period"""
        recent_period = min(15, len(price_data) // 2)
        recent_data = price_data.iloc[-recent_period:]
        
        high = recent_data['high'].max()
        low = recent_data['low'].min()
        range_size = (high - low) / low if low > 0 else 0
        
        # Score higher for smaller ranges (more sideways)
        score = max(0, 100 - (range_size * 1000))  # Invert relationship
        
        return {
            'score': score,
            'range_size': range_size,
            'recent_high': float(high),
            'recent_low': float(low)
        }
    
    def _analyze_volume_divergence(self, price_data: pd.DataFrame, volume_data: pd.Series) -> Dict:
        """Analyze volume divergence (decreasing volume on up moves)"""
        if len(price_data) < 10:
            return {'score': 0, 'divergence_ratio': 0}
        
        # Split into two halves to compare volume patterns
        mid_point = len(price_data) // 2
        early_data = price_data.iloc[:mid_point]
        late_data = price_data.iloc[mid_point:]
        early_volume = volume_data.iloc[:mid_point]
        late_volume = volume_data.iloc[mid_point:]
        
        # Calculate volume on up moves for each period
        early_up_moves = early_data['close'] > early_data['open']
        late_up_moves = late_data['close'] > late_data['open']
        
        early_up_volume = early_volume[early_up_moves].mean() if early_up_moves.any() else 0
        late_up_volume = late_volume[late_up_moves].mean() if late_up_moves.any() else 0
        
        if early_up_volume == 0:
            divergence_ratio = 0
        else:
            divergence_ratio = (early_up_volume - late_up_volume) / early_up_volume
        
        # Score higher for negative divergence (decreasing volume on up moves)
        score = min(100, max(0, divergence_ratio * 100))
        
        return {
            'score': score,
            'divergence_ratio': divergence_ratio,
            'early_up_volume': float(early_up_volume),
            'late_up_volume': float(late_up_volume)
        }
    
    def _identify_resistance_levels(self, price_data: pd.DataFrame, volume_data: pd.Series) -> Dict:
        """Identify resistance levels that are holding"""
        lookback = min(20, len(price_data))
        resistance_level = price_data['high'].iloc[-lookback:].max()
        
        # Count touches near resistance level
        tolerance = resistance_level * 0.001
        touches = 0
        touch_volumes = []
        
        for i, row in price_data.iloc[-lookback:].iterrows():
            if abs(row['high'] - resistance_level) <= tolerance:
                touches += 1
                if i < len(volume_data):
                    touch_volumes.append(volume_data.iloc[i])
        
        avg_volume = volume_data.mean()
        resistance_volume_ratio = (sum(touch_volumes) / len(touch_volumes)) / avg_volume if touch_volumes else 0
        
        score = min(100, (touches * 15) + (resistance_volume_ratio * 25))
        
        return {
            'score': score,
            'resistance_level': float(resistance_level),
            'touches': touches,
            'resistance_volume_ratio': resistance_volume_ratio
        }
    
    def _detect_upthrusts(self, price_data: pd.DataFrame, volume_data: pd.Series, resistance_level: Optional[float]) -> Dict:
        """Detect upthrust patterns (false breakouts above resistance)"""
        if resistance_level is None or len(price_data) < 5:
            return {'score': 0, 'upthrusts_detected': 0}
        
        upthrusts_detected = 0
        upthrust_strength_total = 0
        
        for i in range(1, len(price_data)):
            current = price_data.iloc[i]
            previous = price_data.iloc[i-1]
            
            # Check for upthrust: high breaks resistance but close fails to hold above
            if (current['high'] > resistance_level and 
                current['close'] < resistance_level and
                previous['close'] <= resistance_level):
                
                upthrusts_detected += 1
                
                # Calculate upthrust strength based on failure and volume
                failure_ratio = (current['high'] - current['close']) / (current['high'] - current['low'])
                volume_ratio = volume_data.iloc[i] / volume_data.mean()
                upthrust_strength = failure_ratio * volume_ratio
                upthrust_strength_total += upthrust_strength
        
        avg_upthrust_strength = upthrust_strength_total / upthrusts_detected if upthrusts_detected > 0 else 0
        score = min(100, (upthrusts_detected * 30) + (avg_upthrust_strength * 20))
        
        return {
            'score': score,
            'upthrusts_detected': upthrusts_detected,
            'avg_upthrust_strength': avg_upthrust_strength
        }
    
    def _calculate_distribution_confidence(self, criteria: Dict) -> Decimal:
        """Calculate overall confidence for distribution phase"""
        weights = {
            'sideways_movement': 0.25,
            'volume_divergence': 0.30,
            'resistance_holding': 0.30,
            'upthrust_patterns': 0.15
        }
        
        total_score = 0
        for factor, weight in weights.items():
            factor_score = criteria[factor].get('score', 0)
            total_score += factor_score * weight
        
        return Decimal(str(round(total_score, 2)))
    
    def _extract_distribution_levels(self, price_data: pd.DataFrame, resistance_data: Dict) -> Dict:
        """Extract key levels for distribution phase"""
        resistance_level = resistance_data.get('resistance_level')
        
        lookback = min(20, len(price_data))
        support_level = price_data['low'].iloc[-lookback:].min()
        current_price = price_data['close'].iloc[-1]
        
        return {
            'support': float(support_level),
            'resistance': float(resistance_level) if resistance_level else None,
            'entry': float(current_price),
            'stop': float(resistance_level * 1.001) if resistance_level else current_price * 1.005,
            'target': float(support_level * 0.999),
            'current_price': float(current_price)
        }


class MarkdownDetector:
    """Detects markdown phase characteristics"""
    
    def detect_markdown(self, price_data: pd.DataFrame, volume_data: pd.Series) -> Dict:
        """
        Detect markdown phase characteristics:
        - Declining price structure with lower lows and lower highs
        - Selling pressure with volume confirmation
        - Failed rallies with weak volume
        - Breakdown below support levels
        """
        if len(price_data) < 10:
            return {'detected': False, 'reason': 'Insufficient data'}
        
        price_structure = self._analyze_ll_lh_structure(price_data)
        selling_pressure = self._analyze_selling_pressure(price_data, volume_data)
        failed_rallies = self._detect_failed_rallies(price_data, volume_data)
        
        criteria = {
            'price_structure': price_structure,
            'selling_pressure': selling_pressure, 
            'failed_rallies': failed_rallies
        }
        
        confidence = self._calculate_markdown_confidence(criteria)
        
        return {
            'phase': 'markdown',
            'confidence': confidence,
            'criteria': criteria,
            'key_levels': self._extract_markdown_levels(price_data),
            'detected': confidence > Decimal('60.0')
        }
    
    def _analyze_ll_lh_structure(self, price_data: pd.DataFrame) -> Dict:
        """Analyze lower lows and lower highs structure"""
        if len(price_data) < 6:
            return {'score': 0, 'structure_integrity': 0}
        
        # Find swing highs and lows
        swing_highs = []
        swing_lows = []
        
        for i in range(2, len(price_data) - 2):
            # Swing high
            if (price_data['high'].iloc[i] > price_data['high'].iloc[i-2:i].max() and
                price_data['high'].iloc[i] > price_data['high'].iloc[i+1:i+3].max()):
                swing_highs.append((i, price_data['high'].iloc[i]))
            
            # Swing low
            if (price_data['low'].iloc[i] < price_data['low'].iloc[i-2:i].min() and
                price_data['low'].iloc[i] < price_data['low'].iloc[i+1:i+3].min()):
                swing_lows.append((i, price_data['low'].iloc[i]))
        
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
        
        total_swings = len(swing_highs) + len(swing_lows)
        structure_integrity = (ll_count + lh_count) / total_swings if total_swings > 0 else 0
        
        score = structure_integrity * 100
        
        return {
            'score': score,
            'structure_integrity': structure_integrity,
            'lower_lows': ll_count,
            'lower_highs': lh_count,
            'total_swings': total_swings
        }
    
    def _analyze_selling_pressure(self, price_data: pd.DataFrame, volume_data: pd.Series) -> Dict:
        """Analyze selling pressure with volume confirmation"""
        if len(price_data) != len(volume_data):
            return {'score': 0, 'selling_pressure_ratio': 0}
        
        # Identify down vs up candles
        down_candles = price_data['close'] < price_data['open']
        up_candles = price_data['close'] > price_data['open']
        
        # Calculate average volume on down vs up moves
        down_volume = volume_data[down_candles].mean() if down_candles.any() else 0
        up_volume = volume_data[up_candles].mean() if up_candles.any() else 0
        
        if up_volume == 0:
            selling_pressure_ratio = 2.0
        else:
            selling_pressure_ratio = down_volume / up_volume
        
        # Score higher when volume is higher on down moves
        score = min(100, max(0, (selling_pressure_ratio - 1) * 50))
        
        return {
            'score': score,
            'selling_pressure_ratio': selling_pressure_ratio,
            'down_volume_avg': float(down_volume),
            'up_volume_avg': float(up_volume)
        }
    
    def _detect_failed_rallies(self, price_data: pd.DataFrame, volume_data: pd.Series) -> Dict:
        """Detect failed rally attempts with weak volume"""
        if len(price_data) < 10:
            return {'score': 0, 'failed_rallies': 0}
        
        failed_rallies = 0
        avg_volume = volume_data.mean()
        
        # Look for rally attempts (3+ consecutive up candles) that fail
        i = 0
        while i < len(price_data) - 3:
            # Check for rally start (2+ up candles)
            rally_candles = 0
            rally_start = i
            
            while (i < len(price_data) and 
                   price_data['close'].iloc[i] > price_data['open'].iloc[i]):
                rally_candles += 1
                i += 1
            
            # If we had a rally of 2+ candles
            if rally_candles >= 2:
                # Check if rally failed (next candle closes below rally start)
                rally_high = price_data['high'].iloc[rally_start:i].max()
                rally_volume = volume_data.iloc[rally_start:i].mean()
                
                # Check if next few candles show failure
                if i < len(price_data):
                    next_low = price_data['low'].iloc[i:min(i+3, len(price_data))].min()
                    
                    # Rally failed if it broke below start and had weak volume
                    if (next_low < price_data['low'].iloc[rally_start] and 
                        rally_volume < avg_volume * 1.2):
                        failed_rallies += 1
            
            i += 1
        
        score = min(100, failed_rallies * 25)
        
        return {
            'score': score,
            'failed_rallies': failed_rallies
        }
    
    def _calculate_markdown_confidence(self, criteria: Dict) -> Decimal:
        """Calculate overall confidence for markdown phase"""
        weights = {
            'price_structure': 0.40,
            'selling_pressure': 0.35,
            'failed_rallies': 0.25
        }
        
        total_score = 0
        for factor, weight in weights.items():
            factor_score = criteria[factor].get('score', 0)
            total_score += factor_score * weight
        
        return Decimal(str(round(total_score, 2)))
    
    def _extract_markdown_levels(self, price_data: pd.DataFrame) -> Dict:
        """Extract key levels for markdown phase"""
        current_price = price_data['close'].iloc[-1]
        recent_high = price_data['high'].iloc[-10:].max()
        recent_low = price_data['low'].iloc[-10:].min()
        
        return {
            'support': float(recent_low),
            'resistance': float(recent_high),
            'entry': float(current_price),
            'stop': float(recent_high * 1.005),
            'target': float(recent_low * 0.98),
            'current_price': float(current_price)
        }


class WyckoffPhaseDetector:
    """Main Wyckoff phase detection coordinator"""
    
    def __init__(self):
        self.accumulation_detector = AccumulationDetector()
        self.markup_detector = MarkupDetector()
        self.distribution_detector = DistributionDetector()
        self.markdown_detector = MarkdownDetector()
        self.current_phase = None
        self.phase_history = []
    
    def detect_phase(self, symbol: str, price_data: pd.DataFrame, volume_data: pd.Series, timeframe: str = '1h') -> PhaseDetectionResult:
        """
        Detect the current Wyckoff phase for given market data
        
        Args:
            symbol: Trading symbol (e.g., 'EURUSD')
            price_data: DataFrame with OHLC data
            volume_data: Series with volume data
            timeframe: Timeframe string (e.g., '1h', '4h')
            
        Returns:
            PhaseDetectionResult with detected phase and confidence
        """
        if len(price_data) < 10:
            raise ValueError("Insufficient data for phase detection")
        
        # Run all phase detectors
        accumulation_result = self.accumulation_detector.detect_accumulation(price_data, volume_data)
        markup_result = self.markup_detector.detect_markup(price_data, volume_data)
        distribution_result = self.distribution_detector.detect_distribution(price_data, volume_data)
        markdown_result = self.markdown_detector.detect_markdown(price_data, volume_data)
        
        # Determine highest confidence phase
        phase_results = {
            'accumulation': accumulation_result,
            'markup': markup_result,
            'distribution': distribution_result,
            'markdown': markdown_result
        }
        
        # Find phase with highest confidence
        best_phase = None
        best_confidence = Decimal('0')
        best_result = None
        
        for phase_name, result in phase_results.items():
            if result.get('detected', False) and result['confidence'] > best_confidence:
                best_phase = phase_name
                best_confidence = result['confidence']
                best_result = result
        
        # If no phase detected with sufficient confidence, return neutral
        if best_phase is None:
            return PhaseDetectionResult(
                phase='neutral',
                confidence=Decimal('0'),
                criteria={},
                key_levels={},
                detection_time=datetime.now(),
                timeframe=timeframe
            )
        
        # Create phase transition validation
        phase_transition_valid = self._validate_phase_transition(best_phase, best_confidence)
        
        # Update phase history
        if phase_transition_valid:
            self.current_phase = best_phase
            self.phase_history.append({
                'phase': best_phase,
                'confidence': best_confidence,
                'timestamp': datetime.now(),
                'symbol': symbol,
                'timeframe': timeframe
            })
        
        return PhaseDetectionResult(
            phase=best_phase,
            confidence=best_confidence,
            criteria=best_result['criteria'],
            key_levels=best_result['key_levels'],
            detection_time=datetime.now(),
            timeframe=timeframe
        )
    
    def _validate_phase_transition(self, new_phase: str, confidence: Decimal) -> bool:
        """
        Validate that phase transitions follow logical Wyckoff sequence
        
        Valid transitions:
        - accumulation -> markup
        - markup -> distribution  
        - distribution -> markdown
        - markdown -> accumulation
        """
        if self.current_phase is None:
            return True  # First detection always valid
        
        valid_transitions = {
            'accumulation': ['markup', 'accumulation'],  # Can stay in accumulation
            'markup': ['distribution', 'markup'],
            'distribution': ['markdown', 'distribution'], 
            'markdown': ['accumulation', 'markdown']
        }
        
        # Check if transition is valid
        if new_phase not in valid_transitions.get(self.current_phase, []):
            # Require higher confidence for invalid transitions
            return confidence > Decimal('75.0')
        
        return True
    
    def get_phase_history(self, symbol: str = None, limit: int = 10) -> List[Dict]:
        """Get historical phase detections"""
        history = self.phase_history
        
        if symbol:
            history = [h for h in history if h['symbol'] == symbol]
        
        return history[-limit:] if limit else history
    
    def get_current_phase(self) -> Optional[str]:
        """Get the current detected phase"""
        return self.current_phase