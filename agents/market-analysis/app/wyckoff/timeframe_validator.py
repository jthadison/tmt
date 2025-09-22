"""
Multi-Timeframe Validation Module

Implements hierarchical timeframe analysis for Wyckoff patterns:
- Timeframe hierarchy: M5 → M15 → H1 → H4 → D1
- Pattern alignment detection across timeframes
- Higher timeframe trend confirmation
- Timeframe divergence detection and warnings
- Pattern strength amplification with timeframe alignment
- Conflicting timeframe pattern resolution logic
"""

from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class TimeframeHierarchy(Enum):
    """Timeframe hierarchy with weights"""
    M5 = ("5m", 0.10, 1)
    M15 = ("15m", 0.20, 2)  
    H1 = ("1h", 0.30, 3)
    H4 = ("4h", 0.30, 4)
    D1 = ("1d", 0.10, 5)


@dataclass
class TimeframePattern:
    """Pattern detected on a specific timeframe"""
    timeframe: str
    pattern_type: str  # accumulation, markup, distribution, markdown, spring, upthrust
    confidence: Decimal
    strength: Decimal
    key_levels: Dict[str, float]
    detection_time: datetime
    trend_direction: str  # up, down, sideways
    trend_strength: Decimal


@dataclass
class MultiTimeframeResult:
    """Complete multi-timeframe analysis result"""
    primary_pattern: TimeframePattern
    timeframe_patterns: Dict[str, TimeframePattern]
    alignment_score: Decimal  # 0-100 alignment strength
    conflicts: List[Dict]  # Conflicting patterns
    dominant_timeframe: str
    recommendation: str
    confluence_zones: List[Dict]  # Areas where multiple TFs agree


class MultiTimeframeValidator:
    """Validates patterns across multiple timeframes"""
    
    def __init__(self):
        self.timeframes = ['5m', '15m', '1h', '4h', '1d']
        self.hierarchy_weights = {tf.value[0]: tf.value[1] for tf in TimeframeHierarchy}
        self.hierarchy_ranks = {tf.value[0]: tf.value[2] for tf in TimeframeHierarchy}
        
        # Timeframe confirmation relationships
        self.confirmation_matrix = {
            '5m': ['15m'],
            '15m': ['1h'], 
            '1h': ['4h'],
            '4h': ['1d'],
            '1d': []  # Highest timeframe
        }
    
    def validate_pattern_alignment(self,
                                 symbol: str,
                                 timeframe_data: Dict[str, Dict],
                                 primary_timeframe: str = '1h') -> MultiTimeframeResult:
        """
        Check if pattern is aligned across multiple timeframes
        Higher timeframe confirmation increases confidence
        
        Args:
            symbol: Trading symbol
            timeframe_data: Dict of timeframe -> {price_data, volume_data, pattern_result}
            primary_timeframe: Primary timeframe for analysis
        """
        
        # Extract patterns from each timeframe
        timeframe_patterns = {}
        for tf, data in timeframe_data.items():
            pattern_result = data.get('pattern_result')
            if pattern_result and pattern_result.get('detected', False):
                pattern = TimeframePattern(
                    timeframe=tf,
                    pattern_type=pattern_result['phase'],
                    confidence=pattern_result['confidence'],
                    strength=pattern_result.get('strength', Decimal('50')),
                    key_levels=pattern_result.get('key_levels', {}),
                    detection_time=datetime.now(),
                    trend_direction=self._determine_trend_direction(data['price_data']),
                    trend_strength=self._calculate_trend_strength(data['price_data'])
                )
                timeframe_patterns[tf] = pattern
        
        if not timeframe_patterns:
            return self._create_empty_result("No patterns detected on any timeframe")
        
        # Calculate alignment score
        alignment_score = self._calculate_alignment_score(timeframe_patterns)
        
        # Identify conflicts
        conflicts = self._identify_conflicts(timeframe_patterns)
        
        # Determine dominant timeframe
        dominant_timeframe = self._identify_dominant_timeframe(timeframe_patterns)
        
        # Find confluence zones
        confluence_zones = self._find_confluence_zones(timeframe_patterns)
        
        # Generate recommendation
        recommendation = self._generate_recommendation(
            timeframe_patterns, alignment_score, conflicts, dominant_timeframe
        )
        
        # Select primary pattern
        primary_pattern = timeframe_patterns.get(primary_timeframe) or timeframe_patterns[dominant_timeframe]
        
        return MultiTimeframeResult(
            primary_pattern=primary_pattern,
            timeframe_patterns=timeframe_patterns,
            alignment_score=alignment_score,
            conflicts=conflicts,
            dominant_timeframe=dominant_timeframe,
            recommendation=recommendation,
            confluence_zones=confluence_zones
        )
    
    def check_higher_timeframe_trend_confirmation(self,
                                                timeframe_patterns: Dict[str, TimeframePattern],
                                                base_timeframe: str) -> Dict:
        """
        Check if higher timeframes confirm the trend/pattern
        
        Returns confirmation analysis with strength scores
        """
        base_pattern = timeframe_patterns.get(base_timeframe)
        if not base_pattern:
            return {'confirmed': False, 'reason': 'No base pattern found'}
        
        # Get higher timeframes
        base_rank = self.hierarchy_ranks.get(base_timeframe, 0)
        higher_timeframes = [tf for tf, rank in self.hierarchy_ranks.items() if rank > base_rank]
        
        confirmations = []
        contradictions = []
        
        for tf in higher_timeframes:
            if tf not in timeframe_patterns:
                continue
                
            higher_pattern = timeframe_patterns[tf]
            
            # Check pattern type alignment
            pattern_alignment = self._check_pattern_type_alignment(
                base_pattern.pattern_type, higher_pattern.pattern_type
            )
            
            # Check trend alignment  
            trend_alignment = self._check_trend_alignment(
                base_pattern.trend_direction, higher_pattern.trend_direction
            )
            
            # Check level confluence
            level_confluence = self._check_level_confluence(
                base_pattern.key_levels, higher_pattern.key_levels
            )
            
            alignment_data = {
                'timeframe': tf,
                'pattern_alignment': pattern_alignment,
                'trend_alignment': trend_alignment,
                'level_confluence': level_confluence,
                'overall_alignment': (pattern_alignment['score'] + trend_alignment['score'] + level_confluence['score']) / 3
            }
            
            if alignment_data['overall_alignment'] >= 50:  # Relaxed from 60% to 50%
                confirmations.append(alignment_data)
            else:
                contradictions.append(alignment_data)
        
        # Calculate overall confirmation strength
        total_confirmations = len(confirmations)
        total_contradictions = len(contradictions)
        total_higher_tfs = len(higher_timeframes)
        
        if total_higher_tfs == 0:
            confirmation_strength = 50  # Neutral if no higher timeframes
        else:
            confirmation_ratio = total_confirmations / total_higher_tfs
            confirmation_strength = confirmation_ratio * 100
        
        return {
            'confirmed': confirmation_strength >= 50,  # Reduced from 60% for more confirmations
            'confirmation_strength': confirmation_strength,
            'confirmations': confirmations,
            'contradictions': contradictions,
            'higher_timeframes_analyzed': total_higher_tfs
        }
    
    def detect_timeframe_divergences(self,
                                   timeframe_patterns: Dict[str, TimeframePattern]) -> List[Dict]:
        """
        Detect divergence patterns between timeframes
        
        Divergences can signal potential pattern failures or transitions
        """
        divergences = []
        
        # Compare adjacent timeframes in hierarchy
        for i, tf in enumerate(self.timeframes[:-1]):
            current_tf = tf
            next_tf = self.timeframes[i + 1]
            
            if current_tf not in timeframe_patterns or next_tf not in timeframe_patterns:
                continue
            
            current_pattern = timeframe_patterns[current_tf]
            next_pattern = timeframe_patterns[next_tf]
            
            # Check for various types of divergences
            divergence_checks = [
                self._check_pattern_type_divergence(current_pattern, next_pattern),
                self._check_trend_divergence(current_pattern, next_pattern),
                self._check_confidence_divergence(current_pattern, next_pattern),
                self._check_timing_divergence(current_pattern, next_pattern)
            ]
            
            for divergence in divergence_checks:
                if divergence['detected']:
                    divergence['timeframes'] = (current_tf, next_tf)
                    divergences.append(divergence)
        
        return divergences
    
    def amplify_pattern_strength_with_alignment(self,
                                              base_pattern: TimeframePattern,
                                              alignment_data: Dict) -> Decimal:
        """
        Amplify pattern strength based on timeframe alignment
        
        Strong alignment across timeframes increases pattern reliability
        """
        base_strength = base_pattern.confidence
        alignment_score = alignment_data.get('alignment_score', Decimal('50'))
        
        # Amplification factors based on alignment
        if alignment_score >= 80:
            amplification_factor = Decimal('1.3')  # 30% boost
        elif alignment_score >= 60:
            amplification_factor = Decimal('1.2')  # 20% boost
        elif alignment_score >= 40:
            amplification_factor = Decimal('1.1')  # 10% boost
        else:
            amplification_factor = Decimal('0.9')   # 10% reduction for poor alignment
        
        # Additional boost for higher timeframe confirmation
        confirmations = alignment_data.get('confirmations', [])
        higher_tf_bonus = Decimal(str(len(confirmations) * 5))  # 5% per confirming higher TF
        
        amplified_strength = base_strength * amplification_factor + higher_tf_bonus
        return min(Decimal('100'), max(Decimal('0'), amplified_strength))
    
    def resolve_conflicting_patterns(self,
                                   conflicting_patterns: List[TimeframePattern],
                                   resolution_strategy: str = 'weighted_hierarchy') -> TimeframePattern:
        """
        Resolve conflicts between patterns on different timeframes
        
        Strategies:
        - weighted_hierarchy: Use hierarchy weights to resolve
        - highest_confidence: Choose highest confidence pattern
        - consensus: Try to find consensus pattern
        """
        if not conflicting_patterns:
            return None
        
        if len(conflicting_patterns) == 1:
            return conflicting_patterns[0]
        
        if resolution_strategy == 'weighted_hierarchy':
            return self._resolve_by_hierarchy(conflicting_patterns)
        elif resolution_strategy == 'highest_confidence':
            return max(conflicting_patterns, key=lambda p: p.confidence)
        elif resolution_strategy == 'consensus':
            return self._resolve_by_consensus(conflicting_patterns)
        else:
            # Default: use hierarchy
            return self._resolve_by_hierarchy(conflicting_patterns)
    
    def _calculate_alignment_score(self, timeframe_patterns: Dict[str, TimeframePattern]) -> Decimal:
        """Calculate overall alignment score across timeframes"""
        if len(timeframe_patterns) < 2:
            return Decimal('50')  # Neutral score for single timeframe
        
        pattern_types = [p.pattern_type for p in timeframe_patterns.values()]
        trend_directions = [p.trend_direction for p in timeframe_patterns.values()]
        
        # Calculate pattern type consensus
        pattern_consensus = self._calculate_consensus_score(pattern_types)
        
        # Calculate trend direction consensus  
        trend_consensus = self._calculate_consensus_score(trend_directions)
        
        # Calculate confidence alignment
        confidences = [float(p.confidence) for p in timeframe_patterns.values()]
        confidence_std = np.std(confidences)
        confidence_alignment = max(0, 100 - (confidence_std * 2))  # Lower std = higher alignment
        
        # Weighted combination
        alignment_score = (
            pattern_consensus * 0.4 +
            trend_consensus * 0.4 +
            confidence_alignment * 0.2
        )
        
        return Decimal(str(round(alignment_score, 2)))
    
    def _calculate_consensus_score(self, values: List[str]) -> float:
        """Calculate consensus score for a list of categorical values"""
        if not values:
            return 50
        
        # Count frequency of each value
        value_counts = {}
        for value in values:
            value_counts[value] = value_counts.get(value, 0) + 1
        
        # Calculate consensus as percentage of most common value
        max_count = max(value_counts.values())
        consensus_ratio = max_count / len(values)
        
        return consensus_ratio * 100
    
    def _identify_conflicts(self, timeframe_patterns: Dict[str, TimeframePattern]) -> List[Dict]:
        """Identify conflicting patterns between timeframes"""
        conflicts = []
        
        # Group patterns by adjacent timeframe pairs
        for i, tf in enumerate(self.timeframes[:-1]):
            next_tf = self.timeframes[i + 1]
            
            if tf not in timeframe_patterns or next_tf not in timeframe_patterns:
                continue
            
            pattern1 = timeframe_patterns[tf]
            pattern2 = timeframe_patterns[next_tf]
            
            # Check for conflicts
            if self._patterns_conflict(pattern1, pattern2):
                conflict = {
                    'timeframes': (tf, next_tf),
                    'patterns': (pattern1.pattern_type, pattern2.pattern_type),
                    'trends': (pattern1.trend_direction, pattern2.trend_direction),
                    'confidences': (pattern1.confidence, pattern2.confidence),
                    'conflict_type': self._classify_conflict_type(pattern1, pattern2),
                    'severity': self._calculate_conflict_severity(pattern1, pattern2)
                }
                conflicts.append(conflict)
        
        return conflicts
    
    def _patterns_conflict(self, pattern1: TimeframePattern, pattern2: TimeframePattern) -> bool:
        """Check if two patterns conflict with each other"""
        # Pattern type conflicts
        opposing_patterns = {
            'accumulation': ['distribution'],
            'markup': ['markdown'],
            'distribution': ['accumulation'],
            'markdown': ['markup']
        }
        
        if pattern2.pattern_type in opposing_patterns.get(pattern1.pattern_type, []):
            return True
        
        # Trend direction conflicts
        opposing_trends = {'up': 'down', 'down': 'up'}
        if pattern2.trend_direction == opposing_trends.get(pattern1.trend_direction):
            return True
        
        return False
    
    def _classify_conflict_type(self, pattern1: TimeframePattern, pattern2: TimeframePattern) -> str:
        """Classify the type of conflict between patterns"""
        if pattern1.pattern_type != pattern2.pattern_type:
            return 'pattern_type_conflict'
        elif pattern1.trend_direction != pattern2.trend_direction:
            return 'trend_direction_conflict'
        elif abs(pattern1.confidence - pattern2.confidence) > 30:
            return 'confidence_conflict'
        else:
            return 'general_conflict'
    
    def _calculate_conflict_severity(self, pattern1: TimeframePattern, pattern2: TimeframePattern) -> str:
        """Calculate severity of conflict between patterns"""
        # Pattern type opposition severity
        pattern_opposition = {
            ('accumulation', 'distribution'): 'high',
            ('markup', 'markdown'): 'high',
            ('accumulation', 'markdown'): 'medium',
            ('distribution', 'markup'): 'medium'
        }
        
        pattern_key = tuple(sorted([pattern1.pattern_type, pattern2.pattern_type]))
        pattern_severity = pattern_opposition.get(pattern_key, 'low')
        
        # Confidence difference severity
        conf_diff = abs(pattern1.confidence - pattern2.confidence)
        if conf_diff > 40:
            conf_severity = 'high'
        elif conf_diff > 20:
            conf_severity = 'medium' 
        else:
            conf_severity = 'low'
        
        # Return highest severity
        severities = ['low', 'medium', 'high']
        pattern_idx = severities.index(pattern_severity)
        conf_idx = severities.index(conf_severity)
        
        return severities[max(pattern_idx, conf_idx)]
    
    def _identify_dominant_timeframe(self, timeframe_patterns: Dict[str, TimeframePattern]) -> str:
        """Identify the dominant timeframe based on pattern strength and hierarchy"""
        if not timeframe_patterns:
            return '1h'  # Default
        
        # Score each timeframe based on confidence and hierarchy weight
        timeframe_scores = {}
        for tf, pattern in timeframe_patterns.items():
            hierarchy_weight = self.hierarchy_weights.get(tf, 0.2)
            confidence_score = float(pattern.confidence) / 100
            
            # Combined score
            total_score = confidence_score * 0.7 + hierarchy_weight * 0.3
            timeframe_scores[tf] = total_score
        
        return max(timeframe_scores.keys(), key=lambda k: timeframe_scores[k])
    
    def _find_confluence_zones(self, timeframe_patterns: Dict[str, TimeframePattern]) -> List[Dict]:
        """Find areas where multiple timeframes agree on key levels"""
        confluence_zones = []
        
        # Collect all key levels from all timeframes
        all_levels = {}
        for tf, pattern in timeframe_patterns.items():
            for level_type, level_value in pattern.key_levels.items():
                if level_value is None:
                    continue
                    
                level_key = f"{level_type}_{level_value:.5f}"
                if level_key not in all_levels:
                    all_levels[level_key] = []
                
                all_levels[level_key].append({
                    'timeframe': tf,
                    'level_type': level_type,
                    'level_value': level_value,
                    'pattern_confidence': pattern.confidence
                })
        
        # Find levels with multiple timeframe agreement
        for level_key, level_data in all_levels.items():
            if len(level_data) >= 2:  # At least 2 timeframes agree
                avg_confidence = sum(float(d['pattern_confidence']) for d in level_data) / len(level_data)
                
                confluence_zone = {
                    'level_value': level_data[0]['level_value'],
                    'level_type': level_data[0]['level_type'],
                    'timeframes': [d['timeframe'] for d in level_data],
                    'confluence_strength': len(level_data) * 20,  # 20 points per timeframe
                    'avg_confidence': avg_confidence,
                    'zone_quality': 'high' if len(level_data) >= 3 else 'medium'
                }
                confluence_zones.append(confluence_zone)
        
        # Sort by confluence strength
        confluence_zones.sort(key=lambda x: x['confluence_strength'], reverse=True)
        return confluence_zones
    
    def _generate_recommendation(self,
                               timeframe_patterns: Dict[str, TimeframePattern],
                               alignment_score: Decimal,
                               conflicts: List[Dict],
                               dominant_timeframe: str) -> str:
        """Generate trading recommendation based on multi-timeframe analysis"""
        dominant_pattern = timeframe_patterns[dominant_timeframe]
        
        # Base recommendation from dominant timeframe
        if alignment_score >= 75 and len(conflicts) == 0:
            base_rec = f"Strong {dominant_pattern.pattern_type.upper()} signal"
        elif alignment_score >= 55 and len(conflicts) <= 1:
            base_rec = f"Moderate {dominant_pattern.pattern_type.upper()} signal"
        else:
            base_rec = "Mixed signals - Exercise caution"
        
        # Add conflict warnings
        if conflicts:
            severity_counts = {}
            for conflict in conflicts:
                severity = conflict['severity']
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            if severity_counts.get('high', 0) > 0:
                base_rec += " - High severity conflicts detected"
            elif severity_counts.get('medium', 0) > 0:
                base_rec += " - Medium conflicts present"
        
        return base_rec
    
    def _determine_trend_direction(self, price_data: pd.DataFrame) -> str:
        """Determine trend direction from price data"""
        if len(price_data) < 10:
            return 'sideways'
        
        # Calculate linear regression slope
        closes = price_data['close'].values
        x = np.arange(len(closes))
        slope = np.polyfit(x, closes, 1)[0]
        
        # Normalize slope as percentage change per period
        avg_price = np.mean(closes)
        slope_pct = (slope / avg_price) * 100 if avg_price != 0 else 0
        
        if slope_pct > 0.1:
            return 'up'
        elif slope_pct < -0.1:
            return 'down'
        else:
            return 'sideways'
    
    def _calculate_trend_strength(self, price_data: pd.DataFrame) -> Decimal:
        """Calculate trend strength from price data"""
        if len(price_data) < 10:
            return Decimal('50')
        
        # Calculate R-squared of linear regression
        closes = price_data['close'].values
        x = np.arange(len(closes))
        
        # Linear regression
        coeffs = np.polyfit(x, closes, 1)
        y_pred = np.polyval(coeffs, x)
        
        # R-squared calculation
        ss_res = np.sum((closes - y_pred) ** 2)
        ss_tot = np.sum((closes - np.mean(closes)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        
        # Convert to 0-100 scale
        strength = max(0, min(100, r_squared * 100))
        return Decimal(str(round(strength, 2)))
    
    def _create_empty_result(self, reason: str) -> MultiTimeframeResult:
        """Create empty result for cases with no patterns"""
        empty_pattern = TimeframePattern(
            timeframe='1h',
            pattern_type='none',
            confidence=Decimal('0'),
            strength=Decimal('0'),
            key_levels={},
            detection_time=datetime.now(),
            trend_direction='sideways',
            trend_strength=Decimal('0')
        )
        
        return MultiTimeframeResult(
            primary_pattern=empty_pattern,
            timeframe_patterns={},
            alignment_score=Decimal('0'),
            conflicts=[],
            dominant_timeframe='1h',
            recommendation=f"No action - {reason}",
            confluence_zones=[]
        )
    
    def _check_pattern_type_alignment(self, base_pattern: str, higher_pattern: str) -> Dict:
        """Check alignment between pattern types"""
        # Pattern compatibility matrix
        compatible_patterns = {
            'accumulation': ['accumulation', 'sideways'],
            'markup': ['markup', 'accumulation'],  # Markup can follow accumulation
            'distribution': ['distribution', 'sideways'],
            'markdown': ['markdown', 'distribution']  # Markdown can follow distribution
        }
        
        compatible = higher_pattern in compatible_patterns.get(base_pattern, [])
        score = 80 if compatible else 20
        
        return {
            'compatible': compatible,
            'score': score,
            'base_pattern': base_pattern,
            'higher_pattern': higher_pattern
        }
    
    def _check_trend_alignment(self, base_trend: str, higher_trend: str) -> Dict:
        """Check alignment between trend directions"""
        if base_trend == higher_trend:
            score = 90
            compatible = True
        elif base_trend == 'sideways' or higher_trend == 'sideways':
            score = 60  # Neutral alignment
            compatible = True
        else:
            score = 10  # Opposing trends
            compatible = False
        
        return {
            'compatible': compatible,
            'score': score,
            'base_trend': base_trend,
            'higher_trend': higher_trend
        }
    
    def _check_level_confluence(self, base_levels: Dict, higher_levels: Dict) -> Dict:
        """Check confluence between key levels"""
        confluences = []
        tolerance = 0.002  # 0.2% tolerance
        
        for base_type, base_value in base_levels.items():
            if base_value is None:
                continue
            
            for higher_type, higher_value in higher_levels.items():
                if higher_value is None:
                    continue
                
                # Check if levels are close
                if abs(base_value - higher_value) / base_value <= tolerance:
                    confluences.append({
                        'base_level': (base_type, base_value),
                        'higher_level': (higher_type, higher_value),
                        'difference': abs(base_value - higher_value) / base_value
                    })
        
        confluence_score = min(100, len(confluences) * 25)  # 25 points per confluence
        
        return {
            'confluences': confluences,
            'score': confluence_score,
            'confluence_count': len(confluences)
        }
    
    def _check_pattern_type_divergence(self, pattern1: TimeframePattern, pattern2: TimeframePattern) -> Dict:
        """Check for pattern type divergence"""
        divergent = self._patterns_conflict(pattern1, pattern2)
        
        return {
            'detected': divergent,
            'type': 'pattern_type_divergence',
            'severity': 'high' if divergent else 'none',
            'details': f"{pattern1.pattern_type} vs {pattern2.pattern_type}"
        }
    
    def _check_trend_divergence(self, pattern1: TimeframePattern, pattern2: TimeframePattern) -> Dict:
        """Check for trend divergence"""
        trend_conflict = (pattern1.trend_direction != pattern2.trend_direction and 
                         'sideways' not in [pattern1.trend_direction, pattern2.trend_direction])
        
        return {
            'detected': trend_conflict,
            'type': 'trend_divergence',
            'severity': 'medium' if trend_conflict else 'none',
            'details': f"{pattern1.trend_direction} vs {pattern2.trend_direction}"
        }
    
    def _check_confidence_divergence(self, pattern1: TimeframePattern, pattern2: TimeframePattern) -> Dict:
        """Check for confidence divergence"""
        conf_diff = abs(pattern1.confidence - pattern2.confidence)
        divergent = conf_diff > 30
        
        severity = 'high' if conf_diff > 50 else 'medium' if conf_diff > 30 else 'none'
        
        return {
            'detected': divergent,
            'type': 'confidence_divergence',
            'severity': severity,
            'details': f"Confidence difference: {conf_diff}%"
        }
    
    def _check_timing_divergence(self, pattern1: TimeframePattern, pattern2: TimeframePattern) -> Dict:
        """Check for timing divergence in pattern detection"""
        time_diff = abs((pattern1.detection_time - pattern2.detection_time).total_seconds())
        divergent = time_diff > 3600  # More than 1 hour apart
        
        return {
            'detected': divergent,
            'type': 'timing_divergence',
            'severity': 'low' if divergent else 'none',
            'details': f"Detection time difference: {time_diff/3600:.1f} hours"
        }
    
    def _resolve_by_hierarchy(self, conflicting_patterns: List[TimeframePattern]) -> TimeframePattern:
        """Resolve conflicts using hierarchy weights"""
        best_score = -1
        best_pattern = None
        
        for pattern in conflicting_patterns:
            hierarchy_weight = self.hierarchy_weights.get(pattern.timeframe, 0.1)
            confidence_weight = float(pattern.confidence) / 100
            
            score = hierarchy_weight * 0.6 + confidence_weight * 0.4
            
            if score > best_score:
                best_score = score
                best_pattern = pattern
        
        return best_pattern
    
    def _resolve_by_consensus(self, conflicting_patterns: List[TimeframePattern]) -> TimeframePattern:
        """Resolve conflicts by finding consensus pattern"""
        # Group by pattern type
        pattern_groups = {}
        for pattern in conflicting_patterns:
            pattern_type = pattern.pattern_type
            if pattern_type not in pattern_groups:
                pattern_groups[pattern_type] = []
            pattern_groups[pattern_type].append(pattern)
        
        # Find most common pattern type
        largest_group = max(pattern_groups.values(), key=len)
        
        # Return highest confidence pattern from largest group
        return max(largest_group, key=lambda p: p.confidence)