"""
Execution precision monitoring for detecting too-perfect trading patterns
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from decimal import Decimal
import numpy as np
from collections import defaultdict
import logging
import math

logger = logging.getLogger(__name__)


@dataclass
class PrecisionScore:
    """Represents precision measurement for a specific aspect"""
    category: str  # 'entry_timing', 'position_sizing', 'level_placement'
    score: float  # 0-1, where 1 is perfect precision (suspicious)
    timestamp: datetime
    sample_size: int
    details: Dict[str, Any]


@dataclass
class SuspiciousPattern:
    """Represents a detected suspicious precision pattern"""
    pattern_type: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    description: str
    affected_trades: int
    recommendation: str
    detected_at: datetime


@dataclass
class PrecisionAnalysis:
    """Complete precision analysis results"""
    metrics: Dict[str, float]
    overall_score: float
    suspicious: bool
    suspicious_patterns: List[SuspiciousPattern]
    recommendations: List[str]
    variance_metrics: Dict[str, float]


@dataclass
class PrecisionThresholds:
    """Configuration thresholds for precision monitoring"""
    # Maximum acceptable precision scores (lower = more human-like)
    max_entry_precision: float = 0.15  # 15% precision score
    max_sizing_precision: float = 0.20  # 20% precision score  
    max_level_precision: float = 0.10  # 10% precision score
    max_timing_precision: float = 0.12  # 12% precision score
    
    # Minimum required variance
    min_entry_variance: float = 0.30  # 30% coefficient of variation
    min_sizing_variance: float = 0.25  # 25% coefficient of variation
    min_level_variance: float = 0.35  # 35% coefficient of variation
    
    # Pattern detection
    min_sample_size: int = 10  # Minimum trades for analysis
    suspicious_threshold: float = 0.25  # Overall threshold for suspicion
    critical_threshold: float = 0.40  # Critical alert threshold


class PrecisionMonitor:
    """Monitors trading execution for suspicious precision patterns"""
    
    def __init__(self, thresholds: Optional[PrecisionThresholds] = None):
        self.thresholds = thresholds or PrecisionThresholds()
        self.precision_history: List[PrecisionScore] = []
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def analyze_precision(self, trades: List[Any]) -> PrecisionAnalysis:
        """
        Perform complete precision analysis on trading data
        """
        if len(trades) < self.thresholds.min_sample_size:
            return self._create_insufficient_data_analysis()
        
        # Calculate various precision metrics
        metrics = {}
        
        # Entry timing precision
        entry_precision = self.calculate_entry_timing_precision(trades)
        metrics['entry_timing'] = entry_precision
        
        # Position sizing precision  
        sizing_precision = self.calculate_position_sizing_precision(trades)
        metrics['position_sizing'] = sizing_precision
        
        # Level placement precision
        level_precision = self.calculate_level_placement_precision(trades)
        metrics['level_placement'] = level_precision
        
        # Execution delay precision
        delay_precision = self.calculate_execution_delay_precision(trades)
        metrics['execution_delay'] = delay_precision
        
        # Calculate variance metrics
        variance_metrics = self.calculate_variance_metrics(trades)
        
        # Calculate overall precision score
        overall_score = self._calculate_overall_score(metrics)
        
        # Detect suspicious patterns
        suspicious_patterns = self._detect_suspicious_patterns(
            metrics, variance_metrics, trades
        )
        
        # Determine if overall pattern is suspicious
        suspicious = overall_score > self.thresholds.suspicious_threshold
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            metrics, variance_metrics, suspicious_patterns
        )
        
        # Store in history
        self._update_precision_history(metrics, overall_score, len(trades))
        
        return PrecisionAnalysis(
            metrics=metrics,
            overall_score=overall_score,
            suspicious=suspicious,
            suspicious_patterns=suspicious_patterns,
            recommendations=recommendations,
            variance_metrics=variance_metrics
        )
    
    def calculate_entry_timing_precision(self, trades: List[Any]) -> float:
        """
        Calculate precision in entry timing patterns
        """
        if not trades:
            return 0.0
        
        # Extract entry delays (time from signal to execution)
        entry_delays = []
        for trade in trades:
            if hasattr(trade, 'signal_time') and hasattr(trade, 'entry_time'):
                delay = (trade.entry_time - trade.signal_time).total_seconds()
                entry_delays.append(delay)
        
        if len(entry_delays) < 2:
            return 0.0
        
        # Calculate coefficient of variation
        mean_delay = np.mean(entry_delays)
        std_delay = np.std(entry_delays)
        
        if mean_delay == 0:
            return 1.0  # Perfect precision (suspicious)
        
        cv = std_delay / mean_delay
        
        # Convert to precision score (0 = high variance, 1 = no variance)
        precision_score = max(0, 1 - cv)
        
        # Check for patterns in delays
        pattern_score = self._detect_delay_patterns(entry_delays)
        
        # Combine scores
        return (precision_score * 0.7 + pattern_score * 0.3)
    
    def calculate_position_sizing_precision(self, trades: List[Any]) -> float:
        """
        Calculate precision in position sizing
        """
        if not trades:
            return 0.0
        
        # Extract position sizes
        sizes = []
        for trade in trades:
            if hasattr(trade, 'size'):
                sizes.append(float(trade.size))
        
        if len(sizes) < 2:
            return 0.0
        
        # Check for round number patterns
        round_number_score = self._calculate_round_number_score(sizes)
        
        # Calculate variance in sizes
        mean_size = np.mean(sizes)
        std_size = np.std(sizes)
        
        if mean_size == 0:
            return 1.0
        
        cv = std_size / mean_size
        variance_score = max(0, 1 - cv * 2)  # Scale for sensitivity
        
        # Check for systematic sizing patterns
        pattern_score = self._detect_sizing_patterns(sizes)
        
        # Combine scores (weighted)
        return (round_number_score * 0.4 + variance_score * 0.3 + pattern_score * 0.3)
    
    def calculate_level_placement_precision(self, trades: List[Any]) -> float:
        """
        Calculate precision in stop loss and take profit placement
        """
        if not trades:
            return 0.0
        
        stop_distances = []
        tp_distances = []
        
        for trade in trades:
            if hasattr(trade, 'entry_price'):
                entry = float(trade.entry_price)
                
                if hasattr(trade, 'stop_loss') and trade.stop_loss:
                    sl_distance = abs(entry - float(trade.stop_loss))
                    stop_distances.append(sl_distance)
                
                if hasattr(trade, 'take_profit') and trade.take_profit:
                    tp_distance = abs(float(trade.take_profit) - entry)
                    tp_distances.append(tp_distance)
        
        precision_scores = []
        
        # Analyze stop loss precision
        if len(stop_distances) >= 2:
            sl_precision = self._calculate_level_precision(stop_distances)
            precision_scores.append(sl_precision)
        
        # Analyze take profit precision
        if len(tp_distances) >= 2:
            tp_precision = self._calculate_level_precision(tp_distances)
            precision_scores.append(tp_precision)
        
        # Check for fixed risk/reward ratios
        if stop_distances and tp_distances:
            rr_precision = self._calculate_risk_reward_precision(
                stop_distances, tp_distances
            )
            precision_scores.append(rr_precision)
        
        if not precision_scores:
            return 0.0
        
        return np.mean(precision_scores)
    
    def calculate_execution_delay_precision(self, trades: List[Any]) -> float:
        """
        Calculate precision in execution delays
        """
        delays = []
        
        for trade in trades:
            if hasattr(trade, 'execution_delay_ms'):
                delays.append(trade.execution_delay_ms)
            elif hasattr(trade, 'signal_time') and hasattr(trade, 'entry_time'):
                delay_ms = (trade.entry_time - trade.signal_time).total_seconds() * 1000
                delays.append(delay_ms)
        
        if len(delays) < 2:
            return 0.0
        
        # Check if delays are too consistent
        mean_delay = np.mean(delays)
        std_delay = np.std(delays)
        
        if mean_delay == 0:
            return 1.0
        
        cv = std_delay / mean_delay
        
        # Check for suspicious patterns
        if cv < 0.1:  # Very low variation
            return 0.9
        elif cv < 0.2:
            return 0.7
        elif cv < 0.3:
            return 0.5
        else:
            return max(0, 1 - cv)
    
    def calculate_variance_metrics(self, trades: List[Any]) -> Dict[str, float]:
        """
        Calculate variance metrics for different trading aspects
        """
        metrics = {}
        
        # Entry timing variance
        entry_times = []
        for trade in trades:
            if hasattr(trade, 'entry_time'):
                # Extract time of day in minutes
                entry_time = trade.entry_time
                minutes_of_day = entry_time.hour * 60 + entry_time.minute
                entry_times.append(minutes_of_day)
        
        if len(entry_times) >= 2:
            metrics['entry_time_variance'] = np.std(entry_times) / (np.mean(entry_times) + 1)
        
        # Size variance
        sizes = [float(trade.size) for trade in trades if hasattr(trade, 'size')]
        if len(sizes) >= 2:
            metrics['size_variance'] = np.std(sizes) / (np.mean(sizes) + 0.0001)
        
        # Duration variance
        durations = []
        for trade in trades:
            if hasattr(trade, 'entry_time') and hasattr(trade, 'exit_time') and trade.exit_time:
                duration = (trade.exit_time - trade.entry_time).total_seconds() / 60
                durations.append(duration)
        
        if len(durations) >= 2:
            metrics['duration_variance'] = np.std(durations) / (np.mean(durations) + 1)
        
        return metrics
    
    def _calculate_overall_score(self, metrics: Dict[str, float]) -> float:
        """
        Calculate weighted overall precision score
        """
        weights = {
            'entry_timing': 0.25,
            'position_sizing': 0.25,
            'level_placement': 0.30,
            'execution_delay': 0.20
        }
        
        total_score = 0
        total_weight = 0
        
        for metric, value in metrics.items():
            if metric in weights:
                total_score += value * weights[metric]
                total_weight += weights[metric]
        
        if total_weight == 0:
            return 0.0
        
        return total_score / total_weight
    
    def _detect_delay_patterns(self, delays: List[float]) -> float:
        """
        Detect patterns in execution delays
        """
        if len(delays) < 3:
            return 0.0
        
        # Check for regular intervals
        intervals = []
        for i in range(1, len(delays)):
            intervals.append(delays[i] - delays[i-1])
        
        if not intervals:
            return 0.0
        
        # Calculate regularity
        mean_interval = np.mean(np.abs(intervals))
        std_interval = np.std(intervals)
        
        if mean_interval == 0:
            return 1.0
        
        regularity = 1 - min(1, std_interval / mean_interval)
        
        return regularity
    
    def _calculate_round_number_score(self, values: List[float]) -> float:
        """
        Calculate how often values are round numbers
        """
        round_count = 0
        
        for value in values:
            # Check if value is close to a round number
            if self._is_round_number(value):
                round_count += 1
        
        round_ratio = round_count / len(values)
        
        # High ratio of round numbers is suspicious
        if round_ratio > 0.8:
            return 0.9
        elif round_ratio > 0.6:
            return 0.7
        elif round_ratio > 0.4:
            return 0.5
        else:
            return round_ratio * 0.5
    
    def _is_round_number(self, value: float) -> bool:
        """
        Check if a value is a round number
        """
        # Check for whole numbers
        if abs(value - round(value)) < 0.001:
            return True
        
        # Check for common fractions (0.25, 0.5, 0.75)
        fractional_part = value - int(value)
        common_fractions = [0.25, 0.5, 0.75]
        
        for fraction in common_fractions:
            if abs(fractional_part - fraction) < 0.001:
                return True
        
        # Check for round decimals (e.g., 1.10, 1.20)
        if abs((value * 10) - round(value * 10)) < 0.001:
            return True
        
        return False
    
    def _detect_sizing_patterns(self, sizes: List[float]) -> float:
        """
        Detect systematic patterns in position sizing
        """
        if len(sizes) < 3:
            return 0.0
        
        # Check for fixed sizing
        unique_sizes = len(set(sizes))
        if unique_sizes == 1:
            return 1.0  # All same size - highly suspicious
        
        # Check for systematic progression
        ratios = []
        for i in range(1, len(sizes)):
            if sizes[i-1] != 0:
                ratios.append(sizes[i] / sizes[i-1])
        
        if ratios:
            # Check if ratios are consistent (martingale, anti-martingale)
            ratio_cv = np.std(ratios) / (np.mean(ratios) + 0.0001)
            if ratio_cv < 0.1:  # Very consistent ratios
                return 0.8
        
        # Check for limited set of sizes
        size_variety = unique_sizes / len(sizes)
        return max(0, 1 - size_variety * 2)
    
    def _calculate_level_precision(self, distances: List[float]) -> float:
        """
        Calculate precision in stop/target level placement
        """
        if len(distances) < 2:
            return 0.0
        
        # Check for fixed distances
        unique_distances = len(set(np.round(distances, 4)))
        if unique_distances == 1:
            return 1.0
        
        # Calculate coefficient of variation
        mean_distance = np.mean(distances)
        std_distance = np.std(distances)
        
        if mean_distance == 0:
            return 1.0
        
        cv = std_distance / mean_distance
        
        # Check for pip-perfect placement
        pip_perfect_count = sum(1 for d in distances if self._is_pip_perfect(d))
        pip_perfect_ratio = pip_perfect_count / len(distances)
        
        precision = max(0, 1 - cv) * 0.6 + pip_perfect_ratio * 0.4
        
        return min(1.0, precision)
    
    def _is_pip_perfect(self, distance: float) -> bool:
        """
        Check if distance is at exact pip values
        """
        # For forex, check if distance is at exact pip boundaries
        # Assuming 4 or 5 decimal places
        pips = distance * 10000  # Convert to pips
        return abs(pips - round(pips)) < 0.01
    
    def _calculate_risk_reward_precision(
        self, 
        stop_distances: List[float], 
        tp_distances: List[float]
    ) -> float:
        """
        Calculate precision in risk/reward ratios
        """
        ratios = []
        
        min_length = min(len(stop_distances), len(tp_distances))
        for i in range(min_length):
            if stop_distances[i] > 0:
                ratio = tp_distances[i] / stop_distances[i]
                ratios.append(ratio)
        
        if len(ratios) < 2:
            return 0.0
        
        # Check for fixed ratios (1:1, 1:2, 1:3, etc.)
        fixed_ratio_count = 0
        common_ratios = [1.0, 1.5, 2.0, 2.5, 3.0]
        
        for ratio in ratios:
            for common in common_ratios:
                if abs(ratio - common) < 0.05:
                    fixed_ratio_count += 1
                    break
        
        fixed_ratio_score = fixed_ratio_count / len(ratios)
        
        # Check for consistency
        ratio_cv = np.std(ratios) / (np.mean(ratios) + 0.0001)
        consistency_score = max(0, 1 - ratio_cv)
        
        return fixed_ratio_score * 0.6 + consistency_score * 0.4
    
    def _detect_suspicious_patterns(
        self,
        metrics: Dict[str, float],
        variance_metrics: Dict[str, float],
        trades: List[Any]
    ) -> List[SuspiciousPattern]:
        """
        Detect specific suspicious precision patterns
        """
        patterns = []
        
        # Check entry timing precision
        if metrics.get('entry_timing', 0) > self.thresholds.max_entry_precision:
            patterns.append(SuspiciousPattern(
                pattern_type='entry_timing_precision',
                severity=self._get_severity(metrics['entry_timing'], 
                                           self.thresholds.max_entry_precision),
                description='Entry timing is too precise - lacks human variation',
                affected_trades=len(trades),
                recommendation='Add random delays of 0.5-3 seconds to entry execution',
                detected_at=datetime.now()
            ))
        
        # Check position sizing precision
        if metrics.get('position_sizing', 0) > self.thresholds.max_sizing_precision:
            patterns.append(SuspiciousPattern(
                pattern_type='position_sizing_precision',
                severity=self._get_severity(metrics['position_sizing'],
                                           self.thresholds.max_sizing_precision),
                description='Position sizing is too systematic',
                affected_trades=len(trades),
                recommendation='Vary position sizes by ±5-15% randomly',
                detected_at=datetime.now()
            ))
        
        # Check level placement precision
        if metrics.get('level_placement', 0) > self.thresholds.max_level_precision:
            patterns.append(SuspiciousPattern(
                pattern_type='level_placement_precision',
                severity=self._get_severity(metrics['level_placement'],
                                           self.thresholds.max_level_precision),
                description='Stop loss and take profit levels are too precise',
                affected_trades=len(trades),
                recommendation='Add variation to SL/TP placement (±2-5 pips)',
                detected_at=datetime.now()
            ))
        
        # Check for low variance
        for metric_name, min_variance in [
            ('entry_time_variance', self.thresholds.min_entry_variance),
            ('size_variance', self.thresholds.min_sizing_variance)
        ]:
            if metric_name in variance_metrics:
                if variance_metrics[metric_name] < min_variance:
                    patterns.append(SuspiciousPattern(
                        pattern_type=f'low_{metric_name}',
                        severity='high',
                        description=f'Insufficient variance in {metric_name.replace("_", " ")}',
                        affected_trades=len(trades),
                        recommendation=f'Increase {metric_name.replace("_", " ")} to appear more human',
                        detected_at=datetime.now()
                    ))
        
        return patterns
    
    def _get_severity(self, score: float, threshold: float) -> str:
        """
        Determine severity based on how much score exceeds threshold
        """
        ratio = score / threshold
        
        if ratio > 3:
            return 'critical'
        elif ratio > 2:
            return 'high'
        elif ratio > 1.5:
            return 'medium'
        else:
            return 'low'
    
    def _generate_recommendations(
        self,
        metrics: Dict[str, float],
        variance_metrics: Dict[str, float],
        suspicious_patterns: List[SuspiciousPattern]
    ) -> List[str]:
        """
        Generate specific recommendations to reduce precision
        """
        recommendations = []
        
        # Overall precision recommendations
        overall_score = self._calculate_overall_score(metrics)
        
        if overall_score > self.thresholds.critical_threshold:
            recommendations.append("CRITICAL: Trading patterns are too precise - immediate adjustments required")
            recommendations.append("Implement all variance injection mechanisms immediately")
        elif overall_score > self.thresholds.suspicious_threshold:
            recommendations.append("WARNING: Precision levels approaching suspicious thresholds")
        
        # Specific recommendations based on metrics
        if metrics.get('entry_timing', 0) > self.thresholds.max_entry_precision:
            recommendations.append("Add random delays between 0.5-3 seconds for entry execution")
            recommendations.append("Vary reaction times to signals naturally")
        
        if metrics.get('position_sizing', 0) > self.thresholds.max_sizing_precision:
            recommendations.append("Implement position size randomization (±5-15%)")
            recommendations.append("Avoid round numbers in position sizing")
            recommendations.append("Use varied lot sizes that appear manually calculated")
        
        if metrics.get('level_placement', 0) > self.thresholds.max_level_precision:
            recommendations.append("Randomize SL/TP placement by ±2-5 pips")
            recommendations.append("Avoid exact pip values and round numbers")
            recommendations.append("Vary risk/reward ratios between trades")
        
        if metrics.get('execution_delay', 0) > self.thresholds.max_timing_precision:
            recommendations.append("Introduce variable processing delays")
            recommendations.append("Simulate human reaction time variation")
        
        # Variance-based recommendations
        if variance_metrics.get('entry_time_variance', 1) < self.thresholds.min_entry_variance:
            recommendations.append("Increase variation in trading times throughout the day")
        
        if variance_metrics.get('size_variance', 1) < self.thresholds.min_sizing_variance:
            recommendations.append("Use more diverse position sizes")
        
        if variance_metrics.get('duration_variance', 1) < 0.3:
            recommendations.append("Vary trade holding periods more significantly")
        
        return recommendations
    
    def _create_insufficient_data_analysis(self) -> PrecisionAnalysis:
        """
        Create analysis result when insufficient data
        """
        return PrecisionAnalysis(
            metrics={},
            overall_score=0.0,
            suspicious=False,
            suspicious_patterns=[],
            recommendations=["Insufficient data for precision analysis - need at least 10 trades"],
            variance_metrics={}
        )
    
    def _update_precision_history(
        self,
        metrics: Dict[str, float],
        overall_score: float,
        sample_size: int
    ):
        """
        Update precision score history for trend analysis
        """
        for category, score in metrics.items():
            self.precision_history.append(PrecisionScore(
                category=category,
                score=score,
                timestamp=datetime.now(),
                sample_size=sample_size,
                details={'overall_score': overall_score}
            ))
        
        # Keep only last 1000 entries
        if len(self.precision_history) > 1000:
            self.precision_history = self.precision_history[-1000:]
    
    def get_precision_trends(self, lookback_hours: int = 24) -> Dict[str, Any]:
        """
        Analyze trends in precision scores over time
        """
        cutoff_time = datetime.now() - timedelta(hours=lookback_hours)
        recent_scores = [s for s in self.precision_history if s.timestamp >= cutoff_time]
        
        if not recent_scores:
            return {'status': 'no_data', 'trends': {}}
        
        # Group by category
        category_scores = defaultdict(list)
        for score in recent_scores:
            category_scores[score.category].append(score.score)
        
        trends = {}
        for category, scores in category_scores.items():
            if len(scores) >= 2:
                # Calculate trend (positive = increasing precision = bad)
                trend = np.polyfit(range(len(scores)), scores, 1)[0]
                trends[category] = {
                    'direction': 'increasing' if trend > 0 else 'decreasing',
                    'magnitude': abs(trend),
                    'current': scores[-1],
                    'average': np.mean(scores)
                }
        
        return {'status': 'analyzed', 'trends': trends}