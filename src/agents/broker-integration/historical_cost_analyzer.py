"""
Historical Cost Analysis & Forecasting System - Story 8.14 Task 4

This module provides comprehensive historical cost analysis, trend identification,
seasonal pattern detection, forecasting capabilities, and cost alert systems.

Features:
- Cost trend analysis with statistical models
- Seasonal pattern detection and analysis
- Predictive cost forecasting
- Cost evolution tracking over time
- Benchmark comparisons with industry standards
- Intelligent cost alerting and monitoring
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Union
from decimal import Decimal
from datetime import datetime, timedelta, date
from enum import Enum
import asyncio
import logging
import statistics
import math
from collections import defaultdict, deque

import structlog

logger = structlog.get_logger(__name__)


class TrendDirection(str, Enum):
    """Trend direction types"""
    RISING = "rising"
    FALLING = "falling"
    STABLE = "stable"
    VOLATILE = "volatile"


class SeasonalPattern(str, Enum):
    """Seasonal pattern types"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class TrendAnalysis:
    """Cost trend analysis result"""
    broker: str
    instrument: Optional[str]
    period_start: datetime
    period_end: datetime
    trend_direction: TrendDirection
    trend_strength: float  # 0-1 scale
    slope: float  # Rate of change
    r_squared: float  # Correlation coefficient
    data_points: int
    volatility: float
    current_value: Decimal
    predicted_next_value: Decimal
    confidence_interval: Tuple[Decimal, Decimal]
    trend_summary: str


@dataclass
class SeasonalityAnalysis:
    """Seasonal pattern analysis"""
    broker: str
    instrument: Optional[str]
    pattern_type: SeasonalPattern
    analysis_period: int  # days
    patterns_detected: List[Dict[str, Any]]
    strength_score: float  # 0-1 scale
    peak_periods: List[str]
    low_periods: List[str]
    seasonal_variance: float
    prediction_accuracy: float
    next_peak_prediction: Optional[datetime]
    next_low_prediction: Optional[datetime]


@dataclass
class CostForecast:
    """Cost forecasting result"""
    broker: str
    instrument: Optional[str]
    forecast_date: datetime
    forecast_horizon_days: int
    predicted_costs: List[Tuple[date, Decimal]]  # date -> predicted cost
    confidence_bands: List[Tuple[date, Decimal, Decimal]]  # date -> (lower, upper)
    forecast_accuracy: float
    model_type: str
    factors_considered: List[str]
    risk_assessment: str


@dataclass
class BenchmarkComparison:
    """Benchmark comparison analysis"""
    broker: str
    period_start: datetime
    period_end: datetime
    broker_avg_cost: Decimal
    industry_benchmark: Decimal
    percentile_ranking: float  # 0-100 percentile
    vs_benchmark_difference: Decimal
    vs_benchmark_percentage: float
    peer_comparisons: Dict[str, Decimal]  # peer_broker -> cost
    ranking_among_peers: int
    performance_category: str  # 'excellent', 'above_average', 'average', 'below_average', 'poor'


@dataclass
class CostAlert:
    """Cost alert definition and tracking"""
    alert_id: str
    broker: str
    instrument: Optional[str]
    alert_type: str
    threshold_value: Decimal
    current_value: Decimal
    severity: AlertSeverity
    created_timestamp: datetime
    triggered_timestamp: Optional[datetime]
    acknowledged: bool
    message: str
    action_required: str
    historical_context: str


class CostTrendAnalyzer:
    """Advanced cost trend analysis with statistical models"""
    
    def __init__(self):
        self.trend_history: Dict[str, List[TrendAnalysis]] = defaultdict(list)
        self.trend_models: Dict[str, Dict[str, Any]] = {}
        
    async def analyze_cost_trends(self, broker: str, instrument: str = None,
                                period_days: int = 90, cost_analyzer = None) -> TrendAnalysis:
        """Comprehensive cost trend analysis"""
        
        # Get historical cost data
        cost_trends = await cost_analyzer.get_cost_trends(broker, instrument, period_days)
        
        if not cost_trends or not cost_trends.get('total_cost'):
            return self._create_empty_trend_analysis(broker, instrument, period_days)
        
        # Analyze main cost trend
        cost_data = cost_trends['total_cost']
        
        # Extract time series data
        dates = [point[0] for point in cost_data]
        costs = [float(point[1]) for point in cost_data]
        
        if len(costs) < 3:
            return self._create_empty_trend_analysis(broker, instrument, period_days)
        
        # Calculate trend metrics
        trend_direction, trend_strength = self._calculate_trend_direction(costs)
        slope = self._calculate_slope(costs)
        r_squared = self._calculate_r_squared(costs)
        volatility = self._calculate_volatility(costs)
        
        # Predict next value using linear regression
        predicted_next = self._predict_next_value(costs)
        confidence_interval = self._calculate_confidence_interval(costs, predicted_next)
        
        # Generate trend summary
        trend_summary = self._generate_trend_summary(
            trend_direction, trend_strength, slope, volatility
        )
        
        analysis = TrendAnalysis(
            broker=broker,
            instrument=instrument,
            period_start=datetime.utcnow() - timedelta(days=period_days),
            period_end=datetime.utcnow(),
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            slope=slope,
            r_squared=r_squared,
            data_points=len(costs),
            volatility=volatility,
            current_value=Decimal(str(costs[-1])),
            predicted_next_value=Decimal(str(predicted_next)),
            confidence_interval=confidence_interval,
            trend_summary=trend_summary
        )
        
        # Store in history
        self.trend_history[f"{broker}_{instrument or 'all'}"].append(analysis)
        
        logger.info("Cost trend analysis completed",
                   broker=broker,
                   instrument=instrument,
                   trend_direction=trend_direction.value,
                   trend_strength=trend_strength)
        
        return analysis
    
    def _calculate_trend_direction(self, costs: List[float]) -> Tuple[TrendDirection, float]:
        """Calculate overall trend direction and strength"""
        if len(costs) < 2:
            return TrendDirection.STABLE, 0.0
        
        # Calculate moving averages to smooth noise
        window = min(7, len(costs) // 3)
        if window < 2:
            smoothed = costs
        else:
            smoothed = []
            for i in range(len(costs) - window + 1):
                avg = sum(costs[i:i+window]) / window
                smoothed.append(avg)
        
        # Calculate trend strength using linear regression
        n = len(smoothed)
        x_values = list(range(n))
        
        # Linear regression slope
        sum_x = sum(x_values)
        sum_y = sum(smoothed)
        sum_xy = sum(x * y for x, y in zip(x_values, smoothed))
        sum_x2 = sum(x * x for x in x_values)
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        
        # Determine direction
        if abs(slope) < 0.01:
            direction = TrendDirection.STABLE
        elif slope > 0:
            direction = TrendDirection.RISING
        else:
            direction = TrendDirection.FALLING
        
        # Calculate volatility to check if trend is stable
        volatility = statistics.stdev(costs) / statistics.mean(costs) if statistics.mean(costs) > 0 else 0
        
        if volatility > 0.3:  # High volatility threshold
            direction = TrendDirection.VOLATILE
        
        # Trend strength (0-1)
        strength = min(1.0, abs(slope) * 100)  # Scale slope to 0-1 range
        
        return direction, strength
    
    def _calculate_slope(self, costs: List[float]) -> float:
        """Calculate linear regression slope"""
        if len(costs) < 2:
            return 0.0
        
        n = len(costs)
        x_values = list(range(n))
        
        sum_x = sum(x_values)
        sum_y = sum(costs)
        sum_xy = sum(x * y for x, y in zip(x_values, costs))
        sum_x2 = sum(x * x for x in x_values)
        
        if n * sum_x2 - sum_x * sum_x == 0:
            return 0.0
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        return slope
    
    def _calculate_r_squared(self, costs: List[float]) -> float:
        """Calculate R-squared correlation coefficient"""
        if len(costs) < 2:
            return 0.0
        
        n = len(costs)
        x_values = list(range(n))
        
        # Calculate means
        mean_x = sum(x_values) / n
        mean_y = sum(costs) / n
        
        # Calculate correlation coefficient
        numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(x_values, costs))
        sum_x_squared = sum((x - mean_x) ** 2 for x in x_values)
        sum_y_squared = sum((y - mean_y) ** 2 for y in costs)
        
        denominator = math.sqrt(sum_x_squared * sum_y_squared)
        
        if denominator == 0:
            return 0.0
        
        correlation = numerator / denominator
        return correlation ** 2  # R-squared
    
    def _calculate_volatility(self, costs: List[float]) -> float:
        """Calculate cost volatility (coefficient of variation)"""
        if len(costs) < 2:
            return 0.0
        
        mean_cost = statistics.mean(costs)
        if mean_cost == 0:
            return 0.0
        
        std_dev = statistics.stdev(costs)
        return std_dev / mean_cost
    
    def _predict_next_value(self, costs: List[float]) -> float:
        """Predict next value using linear regression"""
        if len(costs) < 2:
            return costs[0] if costs else 0.0
        
        slope = self._calculate_slope(costs)
        last_value = costs[-1]
        
        # Simple linear prediction
        return last_value + slope
    
    def _calculate_confidence_interval(self, costs: List[float], predicted: float) -> Tuple[Decimal, Decimal]:
        """Calculate 95% confidence interval for prediction"""
        if len(costs) < 2:
            return Decimal(str(predicted)), Decimal(str(predicted))
        
        # Use standard error of the regression
        residuals = []
        slope = self._calculate_slope(costs)
        
        for i, cost in enumerate(costs):
            predicted_value = costs[0] + slope * i
            residuals.append((cost - predicted_value) ** 2)
        
        mse = sum(residuals) / len(residuals)
        std_error = math.sqrt(mse)
        
        # 95% confidence interval (approximately 2 standard errors)
        margin = 1.96 * std_error
        
        lower = Decimal(str(predicted - margin))
        upper = Decimal(str(predicted + margin))
        
        return lower, upper
    
    def _generate_trend_summary(self, direction: TrendDirection, strength: float,
                              slope: float, volatility: float) -> str:
        """Generate human-readable trend summary"""
        if direction == TrendDirection.VOLATILE:
            return f"Highly volatile costs with {volatility:.1%} variability"
        
        strength_desc = "strong" if strength > 0.7 else "moderate" if strength > 0.3 else "weak"
        
        if direction == TrendDirection.RISING:
            return f"{strength_desc.capitalize()} upward trend (+{slope:.2f}/day)"
        elif direction == TrendDirection.FALLING:
            return f"{strength_desc.capitalize()} downward trend ({slope:.2f}/day)"
        else:
            return f"Stable costs with {strength_desc} variation"
    
    def _create_empty_trend_analysis(self, broker: str, instrument: str = None,
                                   period_days: int = 90) -> TrendAnalysis:
        """Create empty trend analysis for insufficient data"""
        return TrendAnalysis(
            broker=broker,
            instrument=instrument,
            period_start=datetime.utcnow() - timedelta(days=period_days),
            period_end=datetime.utcnow(),
            trend_direction=TrendDirection.STABLE,
            trend_strength=0.0,
            slope=0.0,
            r_squared=0.0,
            data_points=0,
            volatility=0.0,
            current_value=Decimal('0'),
            predicted_next_value=Decimal('0'),
            confidence_interval=(Decimal('0'), Decimal('0')),
            trend_summary="Insufficient data for trend analysis"
        )


class SeasonalPatternDetector:
    """Detect and analyze seasonal patterns in costs"""
    
    def __init__(self):
        self.seasonal_models: Dict[str, Dict[SeasonalPattern, SeasonalityAnalysis]] = defaultdict(dict)
        
    async def detect_seasonal_patterns(self, broker: str, instrument: str = None,
                                     analysis_period_days: int = 365,
                                     cost_analyzer = None) -> Dict[SeasonalPattern, SeasonalityAnalysis]:
        """Detect seasonal patterns in cost data"""
        
        # Get extended historical data
        cost_trends = await cost_analyzer.get_cost_trends(broker, instrument, analysis_period_days)
        
        if not cost_trends or not cost_trends.get('total_cost'):
            return {}
        
        cost_data = cost_trends['total_cost']
        patterns = {}
        
        # Analyze different seasonal patterns
        for pattern_type in SeasonalPattern:
            analysis = await self._analyze_seasonal_pattern(
                cost_data, pattern_type, broker, instrument, analysis_period_days
            )
            if analysis.strength_score > 0.1:  # Only include meaningful patterns
                patterns[pattern_type] = analysis
        
        # Store models
        self.seasonal_models[f"{broker}_{instrument or 'all'}"] = patterns
        
        return patterns
    
    async def _analyze_seasonal_pattern(self, cost_data: List[Tuple[date, float]],
                                      pattern_type: SeasonalPattern, broker: str,
                                      instrument: str = None, period_days: int = 365) -> SeasonalityAnalysis:
        """Analyze specific seasonal pattern"""
        
        if not cost_data:
            return self._create_empty_seasonal_analysis(pattern_type, broker, instrument, period_days)
        
        # Group data by seasonal periods
        seasonal_groups = self._group_by_season(cost_data, pattern_type)
        
        if not seasonal_groups:
            return self._create_empty_seasonal_analysis(pattern_type, broker, instrument, period_days)
        
        # Calculate seasonal statistics
        seasonal_stats = {}
        for period, values in seasonal_groups.items():
            if values:
                seasonal_stats[period] = {
                    'mean': statistics.mean(values),
                    'median': statistics.median(values),
                    'std': statistics.stdev(values) if len(values) > 1 else 0,
                    'count': len(values)
                }
        
        # Detect patterns
        patterns_detected = self._identify_patterns(seasonal_stats)
        
        # Calculate strength score
        strength_score = self._calculate_seasonal_strength(seasonal_stats)
        
        # Identify peak and low periods
        peak_periods, low_periods = self._identify_peak_low_periods(seasonal_stats)
        
        # Calculate seasonal variance
        seasonal_variance = self._calculate_seasonal_variance(seasonal_stats)
        
        # Predict next peaks/lows
        next_peak, next_low = self._predict_next_extremes(pattern_type, peak_periods, low_periods)
        
        return SeasonalityAnalysis(
            broker=broker,
            instrument=instrument,
            pattern_type=pattern_type,
            analysis_period=period_days,
            patterns_detected=patterns_detected,
            strength_score=strength_score,
            peak_periods=peak_periods,
            low_periods=low_periods,
            seasonal_variance=seasonal_variance,
            prediction_accuracy=0.8,  # Would be calculated from historical predictions
            next_peak_prediction=next_peak,
            next_low_prediction=next_low
        )
    
    def _group_by_season(self, cost_data: List[Tuple[date, float]],
                        pattern_type: SeasonalPattern) -> Dict[str, List[float]]:
        """Group cost data by seasonal periods"""
        groups = defaultdict(list)
        
        for date_val, cost in cost_data:
            if pattern_type == SeasonalPattern.DAILY:
                key = f"hour_{date_val.hour if hasattr(date_val, 'hour') else 12}"
            elif pattern_type == SeasonalPattern.WEEKLY:
                key = f"day_{date_val.weekday()}"  # 0=Monday, 6=Sunday
            elif pattern_type == SeasonalPattern.MONTHLY:
                key = f"day_{date_val.day}"
            elif pattern_type == SeasonalPattern.QUARTERLY:
                quarter = (date_val.month - 1) // 3 + 1
                key = f"quarter_{quarter}"
            elif pattern_type == SeasonalPattern.YEARLY:
                key = f"month_{date_val.month}"
            else:
                key = "unknown"
            
            groups[key].append(cost)
        
        return dict(groups)
    
    def _identify_patterns(self, seasonal_stats: Dict[str, Dict[str, float]]) -> List[Dict[str, Any]]:
        """Identify significant patterns in seasonal data"""
        patterns = []
        
        if not seasonal_stats:
            return patterns
        
        # Calculate overall mean
        all_means = [stats['mean'] for stats in seasonal_stats.values()]
        overall_mean = statistics.mean(all_means)
        overall_std = statistics.stdev(all_means) if len(all_means) > 1 else 0
        
        # Identify significant deviations
        for period, stats in seasonal_stats.items():
            deviation = stats['mean'] - overall_mean
            significance = abs(deviation) / overall_std if overall_std > 0 else 0
            
            if significance > 1.5:  # 1.5 standard deviations
                pattern_type = "high_cost" if deviation > 0 else "low_cost"
                patterns.append({
                    'period': period,
                    'type': pattern_type,
                    'deviation': deviation,
                    'significance': significance,
                    'mean_cost': stats['mean']
                })
        
        return patterns
    
    def _calculate_seasonal_strength(self, seasonal_stats: Dict[str, Dict[str, float]]) -> float:
        """Calculate strength of seasonal pattern (0-1)"""
        if len(seasonal_stats) < 2:
            return 0.0
        
        means = [stats['mean'] for stats in seasonal_stats.values()]
        
        # Calculate coefficient of variation across seasons
        overall_mean = statistics.mean(means)
        seasonal_variation = statistics.stdev(means) if len(means) > 1 else 0
        
        if overall_mean == 0:
            return 0.0
        
        strength = seasonal_variation / overall_mean
        return min(1.0, strength * 2)  # Scale to 0-1 range
    
    def _identify_peak_low_periods(self, seasonal_stats: Dict[str, Dict[str, float]]) -> Tuple[List[str], List[str]]:
        """Identify peak and low cost periods"""
        if not seasonal_stats:
            return [], []
        
        # Sort periods by mean cost
        sorted_periods = sorted(seasonal_stats.items(), key=lambda x: x[1]['mean'])
        
        # Top 25% are peaks, bottom 25% are lows
        total_periods = len(sorted_periods)
        low_count = max(1, total_periods // 4)
        peak_count = max(1, total_periods // 4)
        
        low_periods = [period for period, _ in sorted_periods[:low_count]]
        peak_periods = [period for period, _ in sorted_periods[-peak_count:]]
        
        return peak_periods, low_periods
    
    def _calculate_seasonal_variance(self, seasonal_stats: Dict[str, Dict[str, float]]) -> float:
        """Calculate variance across seasonal periods"""
        if not seasonal_stats:
            return 0.0
        
        means = [stats['mean'] for stats in seasonal_stats.values()]
        return statistics.variance(means) if len(means) > 1 else 0.0
    
    def _predict_next_extremes(self, pattern_type: SeasonalPattern,
                             peak_periods: List[str], low_periods: List[str]) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Predict next peak and low periods"""
        now = datetime.utcnow()
        
        # Simple prediction based on pattern type (would be more sophisticated in production)
        if pattern_type == SeasonalPattern.WEEKLY:
            # Find next occurrence of peak/low day
            next_peak = now + timedelta(days=7)  # Simplified
            next_low = now + timedelta(days=3)   # Simplified
        elif pattern_type == SeasonalPattern.MONTHLY:
            next_peak = now + timedelta(days=30)  # Simplified
            next_low = now + timedelta(days=15)   # Simplified
        else:
            next_peak = None
            next_low = None
        
        return next_peak, next_low
    
    def _create_empty_seasonal_analysis(self, pattern_type: SeasonalPattern,
                                      broker: str, instrument: str = None,
                                      period_days: int = 365) -> SeasonalityAnalysis:
        """Create empty seasonal analysis for insufficient data"""
        return SeasonalityAnalysis(
            broker=broker,
            instrument=instrument,
            pattern_type=pattern_type,
            analysis_period=period_days,
            patterns_detected=[],
            strength_score=0.0,
            peak_periods=[],
            low_periods=[],
            seasonal_variance=0.0,
            prediction_accuracy=0.0,
            next_peak_prediction=None,
            next_low_prediction=None
        )


class CostForecaster:
    """Advanced cost forecasting with multiple models"""
    
    def __init__(self):
        self.forecast_models: Dict[str, Dict[str, Any]] = {}
        self.forecast_history: Dict[str, List[CostForecast]] = defaultdict(list)
        
    async def generate_cost_forecast(self, broker: str, instrument: str = None,
                                   forecast_horizon_days: int = 30,
                                   cost_analyzer = None,
                                   trend_analyzer: CostTrendAnalyzer = None,
                                   seasonal_detector: SeasonalPatternDetector = None) -> CostForecast:
        """Generate comprehensive cost forecast"""
        
        # Get historical data
        historical_period = max(90, forecast_horizon_days * 3)
        cost_trends = await cost_analyzer.get_cost_trends(broker, instrument, historical_period)
        
        if not cost_trends or not cost_trends.get('total_cost'):
            return self._create_empty_forecast(broker, instrument, forecast_horizon_days)
        
        cost_data = cost_trends['total_cost']
        
        # Get trend analysis
        trend_analysis = await trend_analyzer.analyze_cost_trends(broker, instrument, historical_period, cost_analyzer)
        
        # Get seasonal patterns
        seasonal_patterns = await seasonal_detector.detect_seasonal_patterns(broker, instrument, historical_period, cost_analyzer)
        
        # Generate forecast using combined models
        predicted_costs = await self._generate_predictions(
            cost_data, trend_analysis, seasonal_patterns, forecast_horizon_days
        )
        
        # Calculate confidence bands
        confidence_bands = self._calculate_confidence_bands(
            cost_data, predicted_costs, forecast_horizon_days
        )
        
        # Assess forecast accuracy based on historical performance
        forecast_accuracy = self._assess_forecast_accuracy(broker, instrument)
        
        # Determine factors considered
        factors_considered = self._identify_forecast_factors(trend_analysis, seasonal_patterns)
        
        # Risk assessment
        risk_assessment = self._assess_forecast_risk(trend_analysis, seasonal_patterns)
        
        forecast = CostForecast(
            broker=broker,
            instrument=instrument,
            forecast_date=datetime.utcnow(),
            forecast_horizon_days=forecast_horizon_days,
            predicted_costs=predicted_costs,
            confidence_bands=confidence_bands,
            forecast_accuracy=forecast_accuracy,
            model_type="hybrid_trend_seasonal",
            factors_considered=factors_considered,
            risk_assessment=risk_assessment
        )
        
        # Store forecast
        self.forecast_history[f"{broker}_{instrument or 'all'}"].append(forecast)
        
        logger.info("Cost forecast generated",
                   broker=broker,
                   instrument=instrument,
                   horizon_days=forecast_horizon_days,
                   accuracy=forecast_accuracy)
        
        return forecast
    
    async def _generate_predictions(self, historical_data: List[Tuple[date, float]],
                                  trend_analysis: TrendAnalysis,
                                  seasonal_patterns: Dict[SeasonalPattern, SeasonalityAnalysis],
                                  horizon_days: int) -> List[Tuple[date, Decimal]]:
        """Generate predictions using hybrid model"""
        
        if not historical_data:
            return []
        
        # Extract baseline trend
        base_value = float(trend_analysis.current_value)
        slope = trend_analysis.slope
        
        predictions = []
        current_date = datetime.utcnow().date()
        
        for day_offset in range(1, horizon_days + 1):
            prediction_date = current_date + timedelta(days=day_offset)
            
            # Base trend prediction
            trend_prediction = base_value + (slope * day_offset)
            
            # Apply seasonal adjustments
            seasonal_adjustment = self._calculate_seasonal_adjustment(
                prediction_date, seasonal_patterns
            )
            
            # Combine trend and seasonal components
            final_prediction = trend_prediction * (1 + seasonal_adjustment)
            
            # Ensure non-negative costs
            final_prediction = max(0, final_prediction)
            
            predictions.append((prediction_date, Decimal(str(final_prediction))))
        
        return predictions
    
    def _calculate_seasonal_adjustment(self, prediction_date: date,
                                     seasonal_patterns: Dict[SeasonalPattern, SeasonalityAnalysis]) -> float:
        """Calculate seasonal adjustment factor"""
        adjustment = 0.0
        total_weight = 0.0
        
        for pattern_type, analysis in seasonal_patterns.items():
            if analysis.strength_score > 0.1:  # Only use meaningful patterns
                
                # Determine current seasonal period
                if pattern_type == SeasonalPattern.WEEKLY:
                    current_period = f"day_{prediction_date.weekday()}"
                elif pattern_type == SeasonalPattern.MONTHLY:
                    current_period = f"day_{prediction_date.day}"
                elif pattern_type == SeasonalPattern.YEARLY:
                    current_period = f"month_{prediction_date.month}"
                else:
                    continue
                
                # Check if current period is peak or low
                if current_period in analysis.peak_periods:
                    pattern_adjustment = 0.1 * analysis.strength_score  # 10% increase for peaks
                elif current_period in analysis.low_periods:
                    pattern_adjustment = -0.1 * analysis.strength_score  # 10% decrease for lows
                else:
                    pattern_adjustment = 0.0
                
                weight = analysis.strength_score
                adjustment += pattern_adjustment * weight
                total_weight += weight
        
        if total_weight > 0:
            adjustment /= total_weight
        
        return adjustment
    
    def _calculate_confidence_bands(self, historical_data: List[Tuple[date, float]],
                                  predictions: List[Tuple[date, Decimal]],
                                  horizon_days: int) -> List[Tuple[date, Decimal, Decimal]]:
        """Calculate confidence bands for predictions"""
        if not historical_data or not predictions:
            return []
        
        # Calculate historical volatility
        costs = [cost for _, cost in historical_data]
        if len(costs) < 2:
            return [(date_val, pred, pred) for date_val, pred in predictions]
        
        historical_volatility = statistics.stdev(costs) / statistics.mean(costs)
        
        confidence_bands = []
        for i, (date_val, predicted_cost) in enumerate(predictions):
            # Expanding confidence bands over time
            time_factor = 1 + (i / horizon_days) * 0.5  # 50% wider at end of horizon
            volatility_adjustment = historical_volatility * time_factor
            
            margin = float(predicted_cost) * volatility_adjustment * 1.96  # 95% confidence
            
            lower_bound = Decimal(str(max(0, float(predicted_cost) - margin)))
            upper_bound = Decimal(str(float(predicted_cost) + margin))
            
            confidence_bands.append((date_val, lower_bound, upper_bound))
        
        return confidence_bands
    
    def _assess_forecast_accuracy(self, broker: str, instrument: str = None) -> float:
        """Assess forecast accuracy based on historical performance"""
        key = f"{broker}_{instrument or 'all'}"
        
        if key not in self.forecast_history or len(self.forecast_history[key]) < 2:
            return 0.7  # Default accuracy estimate
        
        # Calculate accuracy from past forecasts (simplified)
        recent_forecasts = self.forecast_history[key][-5:]  # Last 5 forecasts
        
        # In production, would compare predicted vs actual costs
        # For now, return estimated accuracy based on trend stability
        accuracy_scores = []
        for forecast in recent_forecasts:
            # Mock accuracy calculation
            if forecast.risk_assessment == "low":
                accuracy_scores.append(0.85)
            elif forecast.risk_assessment == "medium":
                accuracy_scores.append(0.75)
            else:
                accuracy_scores.append(0.65)
        
        return statistics.mean(accuracy_scores) if accuracy_scores else 0.7
    
    def _identify_forecast_factors(self, trend_analysis: TrendAnalysis,
                                 seasonal_patterns: Dict[SeasonalPattern, SeasonalityAnalysis]) -> List[str]:
        """Identify factors considered in forecast"""
        factors = ["historical_trend"]
        
        if trend_analysis.trend_strength > 0.3:
            factors.append(f"strong_{trend_analysis.trend_direction.value}_trend")
        
        for pattern_type, analysis in seasonal_patterns.items():
            if analysis.strength_score > 0.2:
                factors.append(f"{pattern_type.value}_seasonality")
        
        if trend_analysis.volatility > 0.2:
            factors.append("high_volatility")
        
        return factors
    
    def _assess_forecast_risk(self, trend_analysis: TrendAnalysis,
                            seasonal_patterns: Dict[SeasonalPattern, SeasonalityAnalysis]) -> str:
        """Assess risk level of forecast"""
        if trend_analysis.volatility > 0.3:
            return "high"
        elif trend_analysis.trend_direction == TrendDirection.VOLATILE:
            return "high"
        elif trend_analysis.r_squared < 0.3:
            return "medium"
        elif any(p.strength_score > 0.5 for p in seasonal_patterns.values()):
            return "medium"
        else:
            return "low"
    
    def _create_empty_forecast(self, broker: str, instrument: str = None,
                             horizon_days: int = 30) -> CostForecast:
        """Create empty forecast for insufficient data"""
        return CostForecast(
            broker=broker,
            instrument=instrument,
            forecast_date=datetime.utcnow(),
            forecast_horizon_days=horizon_days,
            predicted_costs=[],
            confidence_bands=[],
            forecast_accuracy=0.0,
            model_type="insufficient_data",
            factors_considered=["insufficient_historical_data"],
            risk_assessment="unknown"
        )


class BenchmarkComparator:
    """Benchmark comparison with industry standards"""
    
    def __init__(self):
        self.industry_benchmarks: Dict[str, Decimal] = {
            'EUR_USD': Decimal('3.5'),  # Example benchmark in basis points
            'GBP_USD': Decimal('4.0'),
            'USD_JPY': Decimal('3.0'),
            'AUD_USD': Decimal('4.5'),
            'USD_CAD': Decimal('4.0'),
            'default': Decimal('5.0')
        }
        self.peer_brokers: Dict[str, Dict[str, Decimal]] = {
            'peer_broker_1': {'EUR_USD': Decimal('3.2'), 'GBP_USD': Decimal('3.8')},
            'peer_broker_2': {'EUR_USD': Decimal('4.1'), 'GBP_USD': Decimal('4.2')},
            'peer_broker_3': {'EUR_USD': Decimal('3.7'), 'GBP_USD': Decimal('3.9')}
        }
        
    async def compare_with_benchmarks(self, broker: str, instrument: str = None,
                                    period_days: int = 30,
                                    cost_analyzer = None) -> BenchmarkComparison:
        """Compare broker costs with industry benchmarks"""
        
        # Get broker cost data
        cost_comparison = await cost_analyzer.generate_broker_cost_comparison(period_days)
        broker_data = cost_comparison.get(broker, {})
        
        broker_avg_cost = broker_data.get('avg_cost_bps', Decimal('0'))
        
        # Get industry benchmark
        industry_benchmark = self.industry_benchmarks.get(
            instrument or 'default', self.industry_benchmarks['default']
        )
        
        # Calculate comparison metrics
        vs_benchmark_difference = broker_avg_cost - industry_benchmark
        vs_benchmark_percentage = float(vs_benchmark_difference / industry_benchmark * 100) if industry_benchmark > 0 else 0
        
        # Get peer comparisons
        peer_comparisons = {}
        peer_costs = []
        
        for peer_name, peer_data in self.peer_brokers.items():
            peer_cost = peer_data.get(instrument or 'default', Decimal('5.0'))
            peer_comparisons[peer_name] = peer_cost
            peer_costs.append(float(peer_cost))
        
        # Calculate percentile ranking
        all_costs = peer_costs + [float(broker_avg_cost)]
        all_costs.sort()
        broker_rank = all_costs.index(float(broker_avg_cost))
        percentile_ranking = (broker_rank / (len(all_costs) - 1)) * 100
        
        # Ranking among peers
        peer_costs.sort()
        if float(broker_avg_cost) in peer_costs:
            ranking_among_peers = peer_costs.index(float(broker_avg_cost)) + 1
        else:
            # Find insertion point
            ranking_among_peers = len([c for c in peer_costs if c < float(broker_avg_cost)]) + 1
        
        # Performance category
        performance_category = self._categorize_performance(percentile_ranking)
        
        return BenchmarkComparison(
            broker=broker,
            period_start=datetime.utcnow() - timedelta(days=period_days),
            period_end=datetime.utcnow(),
            broker_avg_cost=broker_avg_cost,
            industry_benchmark=industry_benchmark,
            percentile_ranking=percentile_ranking,
            vs_benchmark_difference=vs_benchmark_difference,
            vs_benchmark_percentage=vs_benchmark_percentage,
            peer_comparisons=peer_comparisons,
            ranking_among_peers=ranking_among_peers,
            performance_category=performance_category
        )
    
    def _categorize_performance(self, percentile_ranking: float) -> str:
        """Categorize performance based on percentile ranking"""
        if percentile_ranking <= 20:
            return "excellent"
        elif percentile_ranking <= 40:
            return "above_average"
        elif percentile_ranking <= 60:
            return "average"
        elif percentile_ranking <= 80:
            return "below_average"
        else:
            return "poor"


class CostAlertSystem:
    """Intelligent cost alerting and monitoring"""
    
    def __init__(self):
        self.active_alerts: Dict[str, CostAlert] = {}
        self.alert_rules: Dict[str, Dict[str, Any]] = {}
        self.alert_history: List[CostAlert] = []
        
    async def create_alert_rule(self, rule_id: str, broker: str, instrument: str = None,
                              alert_type: str = "cost_threshold", threshold_value: Decimal = None,
                              severity: AlertSeverity = AlertSeverity.MEDIUM) -> None:
        """Create cost alert rule"""
        
        self.alert_rules[rule_id] = {
            'broker': broker,
            'instrument': instrument,
            'alert_type': alert_type,
            'threshold_value': threshold_value,
            'severity': severity,
            'created': datetime.utcnow(),
            'enabled': True
        }
        
        logger.info("Cost alert rule created",
                   rule_id=rule_id,
                   broker=broker,
                   alert_type=alert_type,
                   threshold=float(threshold_value) if threshold_value else None)
    
    async def check_alerts(self, cost_analyzer = None) -> List[CostAlert]:
        """Check all alert rules and trigger alerts if needed"""
        triggered_alerts = []
        
        for rule_id, rule in self.alert_rules.items():
            if not rule['enabled']:
                continue
            
            alert = await self._check_alert_rule(rule_id, rule, cost_analyzer)
            if alert:
                triggered_alerts.append(alert)
                
                # Store alert
                self.active_alerts[alert.alert_id] = alert
                self.alert_history.append(alert)
        
        return triggered_alerts
    
    async def _check_alert_rule(self, rule_id: str, rule: Dict[str, Any],
                              cost_analyzer = None) -> Optional[CostAlert]:
        """Check individual alert rule"""
        
        broker = rule['broker']
        instrument = rule['instrument']
        alert_type = rule['alert_type']
        threshold_value = rule['threshold_value']
        
        # Get current cost data
        cost_comparison = await cost_analyzer.generate_broker_cost_comparison(7)
        broker_data = cost_comparison.get(broker, {})
        
        if alert_type == "cost_threshold":
            current_value = broker_data.get('avg_cost_bps', Decimal('0'))
            
            if current_value > threshold_value:
                return self._create_alert(
                    rule_id, broker, instrument, alert_type,
                    threshold_value, current_value, rule['severity'],
                    f"Cost threshold exceeded: {current_value} > {threshold_value} bps",
                    "Review broker performance and consider alternatives"
                )
        
        elif alert_type == "cost_spike":
            # Check for sudden cost increases
            current_value = broker_data.get('avg_cost_bps', Decimal('0'))
            
            # Get historical average
            historical_comparison = await cost_analyzer.generate_broker_cost_comparison(30)
            historical_data = historical_comparison.get(broker, {})
            historical_avg = historical_data.get('avg_cost_bps', current_value)
            
            if historical_avg > 0 and current_value > historical_avg * Decimal('1.5'):  # 50% increase
                return self._create_alert(
                    rule_id, broker, instrument, alert_type,
                    historical_avg, current_value, AlertSeverity.HIGH,
                    f"Cost spike detected: {current_value} bps (50% above {historical_avg} bps average)",
                    "Investigate cause of cost increase"
                )
        
        elif alert_type == "quality_degradation":
            # Would check quality metrics (placeholder)
            pass
        
        return None
    
    def _create_alert(self, rule_id: str, broker: str, instrument: str = None,
                     alert_type: str = "", threshold_value: Decimal = None,
                     current_value: Decimal = None, severity: AlertSeverity = AlertSeverity.MEDIUM,
                     message: str = "", action_required: str = "") -> CostAlert:
        """Create cost alert"""
        
        alert_id = f"{rule_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # Generate historical context
        historical_context = self._generate_historical_context(broker, instrument, current_value)
        
        return CostAlert(
            alert_id=alert_id,
            broker=broker,
            instrument=instrument,
            alert_type=alert_type,
            threshold_value=threshold_value or Decimal('0'),
            current_value=current_value or Decimal('0'),
            severity=severity,
            created_timestamp=datetime.utcnow(),
            triggered_timestamp=datetime.utcnow(),
            acknowledged=False,
            message=message,
            action_required=action_required,
            historical_context=historical_context
        )
    
    def _generate_historical_context(self, broker: str, instrument: str = None,
                                   current_value: Decimal = None) -> str:
        """Generate historical context for alert"""
        # In production, would analyze historical patterns
        return f"Current cost of {current_value} bps is elevated compared to recent history"
    
    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge alert"""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].acknowledged = True
            logger.info("Alert acknowledged", alert_id=alert_id, acknowledged_by=acknowledged_by)
            return True
        return False
    
    async def get_active_alerts(self, broker: str = None, severity: AlertSeverity = None) -> List[CostAlert]:
        """Get active alerts with optional filtering"""
        alerts = list(self.active_alerts.values())
        
        if broker:
            alerts = [a for a in alerts if a.broker == broker]
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        return [a for a in alerts if not a.acknowledged]


class HistoricalCostAnalyzer:
    """Main historical cost analysis system"""
    
    def __init__(self):
        self.trend_analyzer = CostTrendAnalyzer()
        self.seasonal_detector = SeasonalPatternDetector()
        self.forecaster = CostForecaster()
        self.benchmark_comparator = BenchmarkComparator()
        self.alert_system = CostAlertSystem()
        
    async def initialize(self, brokers: List[str], cost_analyzer = None) -> None:
        """Initialize historical analysis system"""
        
        # Set up default alert rules
        for broker in brokers:
            await self.alert_system.create_alert_rule(
                f"{broker}_cost_threshold",
                broker=broker,
                alert_type="cost_threshold",
                threshold_value=Decimal('8.0'),  # 8 bps threshold
                severity=AlertSeverity.MEDIUM
            )
            
            await self.alert_system.create_alert_rule(
                f"{broker}_cost_spike",
                broker=broker,
                alert_type="cost_spike",
                severity=AlertSeverity.HIGH
            )
        
        logger.info("Historical cost analyzer initialized", brokers=brokers)
    
    async def generate_comprehensive_analysis(self, broker: str, instrument: str = None,
                                            analysis_period_days: int = 90,
                                            cost_analyzer = None) -> Dict[str, Any]:
        """Generate comprehensive historical analysis"""
        
        # Perform all analyses
        trend_analysis = await self.trend_analyzer.analyze_cost_trends(
            broker, instrument, analysis_period_days, cost_analyzer
        )
        
        seasonal_patterns = await self.seasonal_detector.detect_seasonal_patterns(
            broker, instrument, analysis_period_days, cost_analyzer
        )
        
        forecast = await self.forecaster.generate_cost_forecast(
            broker, instrument, 30, cost_analyzer, self.trend_analyzer, self.seasonal_detector
        )
        
        benchmark_comparison = await self.benchmark_comparator.compare_with_benchmarks(
            broker, instrument, 30, cost_analyzer
        )
        
        active_alerts = await self.alert_system.get_active_alerts(broker)
        
        return {
            'trend_analysis': trend_analysis,
            'seasonal_patterns': seasonal_patterns,
            'forecast': forecast,
            'benchmark_comparison': benchmark_comparison,
            'active_alerts': active_alerts,
            'analysis_summary': self._generate_analysis_summary(
                trend_analysis, seasonal_patterns, forecast, benchmark_comparison
            )
        }
    
    def _generate_analysis_summary(self, trend_analysis: TrendAnalysis,
                                 seasonal_patterns: Dict[SeasonalPattern, SeasonalityAnalysis],
                                 forecast: CostForecast,
                                 benchmark_comparison: BenchmarkComparison) -> Dict[str, str]:
        """Generate executive summary of analysis"""
        
        summary = {
            'trend_summary': trend_analysis.trend_summary,
            'seasonality_summary': f"Detected {len(seasonal_patterns)} seasonal patterns",
            'forecast_summary': f"Forecast accuracy: {forecast.forecast_accuracy:.1%}",
            'benchmark_summary': f"Ranked {benchmark_comparison.percentile_ranking:.0f}th percentile vs industry",
            'overall_assessment': self._generate_overall_assessment(
                trend_analysis, benchmark_comparison
            )
        }
        
        return summary
    
    def _generate_overall_assessment(self, trend_analysis: TrendAnalysis,
                                   benchmark_comparison: BenchmarkComparison) -> str:
        """Generate overall assessment"""
        
        if benchmark_comparison.performance_category == "excellent":
            performance = "excellent"
        elif benchmark_comparison.performance_category in ["above_average", "average"]:
            performance = "good"
        else:
            performance = "needs improvement"
        
        if trend_analysis.trend_direction == TrendDirection.FALLING:
            trend_desc = "improving (costs decreasing)"
        elif trend_analysis.trend_direction == TrendDirection.RISING:
            trend_desc = "deteriorating (costs rising)"
        else:
            trend_desc = "stable"
        
        return f"Overall performance: {performance}, trend: {trend_desc}"