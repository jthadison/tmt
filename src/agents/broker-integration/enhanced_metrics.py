"""
Enhanced Metrics and Performance Analytics System
Future Enhancement: Advanced metrics collection, trend analysis, and performance insights
"""
import asyncio
import logging
import time
import statistics
import json
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from collections import deque, defaultdict
import math

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics collected"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"
    RATE = "rate"


class TrendDirection(Enum):
    """Trend direction indicators"""
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    VOLATILE = "volatile"
    UNKNOWN = "unknown"


@dataclass
class MetricDataPoint:
    """Single metric data point"""
    timestamp: datetime
    value: float
    labels: Dict[str, str] = None
    
    def __post_init__(self):
        if self.labels is None:
            self.labels = {}
            
    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp.isoformat(),
            'value': self.value,
            'labels': self.labels
        }


@dataclass
class TrendAnalysis:
    """Trend analysis result"""
    direction: TrendDirection
    slope: float
    confidence: float
    correlation_coefficient: float
    volatility: float
    forecast_next_period: Optional[float] = None
    
    def to_dict(self) -> Dict:
        return {
            'direction': self.direction.value,
            'slope': self.slope,
            'confidence': self.confidence,
            'correlation_coefficient': self.correlation_coefficient,
            'volatility': self.volatility,
            'forecast_next_period': self.forecast_next_period
        }


@dataclass
class PerformanceAlert:
    """Performance alert based on metrics analysis"""
    alert_id: str
    metric_name: str
    alert_type: str
    severity: str
    message: str
    current_value: float
    threshold_value: float
    timestamp: datetime
    trend_analysis: Optional[TrendAnalysis] = None
    
    def to_dict(self) -> Dict:
        return {
            'alert_id': self.alert_id,
            'metric_name': self.metric_name,
            'alert_type': self.alert_type,
            'severity': self.severity,
            'message': self.message,
            'current_value': self.current_value,
            'threshold_value': self.threshold_value,
            'timestamp': self.timestamp.isoformat(),
            'trend_analysis': self.trend_analysis.to_dict() if self.trend_analysis else None
        }


class MetricCollector:
    """Advanced metric collection with trend analysis"""
    
    def __init__(self, max_data_points: int = 10000):
        self.max_data_points = max_data_points
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_data_points))
        self.metric_types: Dict[str, MetricType] = {}
        self.metric_metadata: Dict[str, Dict] = {}
        
        # Trend analysis cache
        self.trend_cache: Dict[str, Tuple[TrendAnalysis, datetime]] = {}
        self.trend_cache_ttl = timedelta(minutes=5)
        
        # Performance thresholds
        self.thresholds: Dict[str, Dict[str, float]] = {}
        
    def record_counter(self, name: str, value: float = 1.0, labels: Dict[str, str] = None):
        """Record counter metric"""
        self._record_metric(name, value, MetricType.COUNTER, labels)
        
    def record_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record gauge metric"""
        self._record_metric(name, value, MetricType.GAUGE, labels)
        
    def record_timer(self, name: str, duration_ms: float, labels: Dict[str, str] = None):
        """Record timer metric"""
        self._record_metric(name, duration_ms, MetricType.TIMER, labels)
        
    def record_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record histogram metric"""
        self._record_metric(name, value, MetricType.HISTOGRAM, labels)
        
    def _record_metric(self, name: str, value: float, metric_type: MetricType, labels: Dict[str, str] = None):
        """Internal method to record metric"""
        timestamp = datetime.now(timezone.utc)
        data_point = MetricDataPoint(timestamp, value, labels or {})
        
        self.metrics[name].append(data_point)
        self.metric_types[name] = metric_type
        
        # Update metadata
        if name not in self.metric_metadata:
            self.metric_metadata[name] = {
                'first_recorded': timestamp,
                'total_points': 0,
                'unique_label_combinations': set()
            }
            
        self.metric_metadata[name]['total_points'] += 1
        self.metric_metadata[name]['last_recorded'] = timestamp
        
        # Track unique label combinations
        label_key = json.dumps(labels or {}, sort_keys=True)
        self.metric_metadata[name]['unique_label_combinations'].add(label_key)
        
    def get_metric_statistics(self, name: str, 
                            time_window: Optional[timedelta] = None) -> Dict[str, Any]:
        """Get comprehensive statistics for a metric"""
        if name not in self.metrics:
            return {}
            
        data_points = list(self.metrics[name])
        
        # Filter by time window if specified
        if time_window:
            cutoff = datetime.now(timezone.utc) - time_window
            data_points = [dp for dp in data_points if dp.timestamp >= cutoff]
            
        if not data_points:
            return {}
            
        values = [dp.value for dp in data_points]
        
        stats = {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'mean': statistics.mean(values),
            'median': statistics.median(values),
            'std_dev': statistics.stdev(values) if len(values) > 1 else 0,
            'first_timestamp': data_points[0].timestamp.isoformat(),
            'last_timestamp': data_points[-1].timestamp.isoformat(),
            'metric_type': self.metric_types[name].value
        }
        
        # Add percentiles for larger datasets
        if len(values) >= 10:
            sorted_values = sorted(values)
            stats.update({
                'p50': statistics.median(sorted_values),
                'p90': sorted_values[int(len(sorted_values) * 0.9)],
                'p95': sorted_values[int(len(sorted_values) * 0.95)],
                'p99': sorted_values[int(len(sorted_values) * 0.99)]
            })
            
        # Add rate calculations for counters
        if self.metric_types[name] == MetricType.COUNTER and len(data_points) > 1:
            time_span = (data_points[-1].timestamp - data_points[0].timestamp).total_seconds()
            if time_span > 0:
                stats['rate_per_second'] = (values[-1] - values[0]) / time_span
                
        return stats
        
    def analyze_trend(self, name: str, 
                     time_window: Optional[timedelta] = None,
                     min_data_points: int = 10) -> Optional[TrendAnalysis]:
        """Analyze trend for a metric"""
        # Check cache first
        if name in self.trend_cache:
            cached_analysis, cached_time = self.trend_cache[name]
            if datetime.now(timezone.utc) - cached_time < self.trend_cache_ttl:
                return cached_analysis
                
        if name not in self.metrics:
            return None
            
        data_points = list(self.metrics[name])
        
        # Filter by time window if specified
        if time_window:
            cutoff = datetime.now(timezone.utc) - time_window
            data_points = [dp for dp in data_points if dp.timestamp >= cutoff]
            
        if len(data_points) < min_data_points:
            return None
            
        # Prepare data for analysis
        timestamps = [(dp.timestamp - data_points[0].timestamp).total_seconds() 
                     for dp in data_points]
        values = [dp.value for dp in data_points]
        
        # Linear regression for trend
        n = len(values)
        sum_x = sum(timestamps)
        sum_y = sum(values)
        sum_xy = sum(x * y for x, y in zip(timestamps, values))
        sum_x2 = sum(x * x for x in timestamps)
        
        # Calculate slope and correlation
        if n * sum_x2 - sum_x * sum_x != 0:
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
            
            # Correlation coefficient
            if len(values) > 1:
                mean_x = sum_x / n
                mean_y = sum_y / n
                
                numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(timestamps, values))
                
                sum_sq_x = sum((x - mean_x) ** 2 for x in timestamps)
                sum_sq_y = sum((y - mean_y) ** 2 for y in values)
                
                if sum_sq_x * sum_sq_y > 0:
                    correlation = numerator / math.sqrt(sum_sq_x * sum_sq_y)
                else:
                    correlation = 0
            else:
                correlation = 0
        else:
            slope = 0
            correlation = 0
            
        # Determine trend direction
        abs_slope = abs(slope)
        if abs_slope < 0.001:  # Very small slope
            direction = TrendDirection.STABLE
        elif slope > 0:
            direction = TrendDirection.INCREASING
        else:
            direction = TrendDirection.DECREASING
            
        # Calculate volatility (coefficient of variation)
        mean_val = statistics.mean(values)
        if mean_val != 0 and len(values) > 1:
            volatility = statistics.stdev(values) / abs(mean_val)
        else:
            volatility = 0
            
        # Check for high volatility
        if volatility > 0.5:
            direction = TrendDirection.VOLATILE
            
        # Calculate confidence based on correlation strength and data points
        confidence = min(0.95, abs(correlation) * (math.log(n) / 5))
        
        # Simple forecast for next period
        if len(timestamps) > 0:
            next_time = timestamps[-1] + (timestamps[-1] - timestamps[0]) / n
            forecast = values[-1] + slope * (next_time - timestamps[-1])
        else:
            forecast = None
            
        analysis = TrendAnalysis(
            direction=direction,
            slope=slope,
            confidence=confidence,
            correlation_coefficient=correlation,
            volatility=volatility,
            forecast_next_period=forecast
        )
        
        # Cache the analysis
        self.trend_cache[name] = (analysis, datetime.now(timezone.utc))
        
        return analysis
        
    def set_threshold(self, name: str, alert_type: str, value: float):
        """Set performance threshold for metric"""
        if name not in self.thresholds:
            self.thresholds[name] = {}
        self.thresholds[name][alert_type] = value
        
    def check_thresholds(self, name: str) -> List[PerformanceAlert]:
        """Check if metric has crossed any thresholds"""
        alerts = []
        
        if name not in self.metrics or name not in self.thresholds:
            return alerts
            
        latest_data = list(self.metrics[name])[-1] if self.metrics[name] else None
        if not latest_data:
            return alerts
            
        current_value = latest_data.value
        
        for alert_type, threshold_value in self.thresholds[name].items():
            alert_triggered = False
            severity = "warning"
            
            if alert_type == "max" and current_value > threshold_value:
                alert_triggered = True
                severity = "error" if current_value > threshold_value * 1.2 else "warning"
                
            elif alert_type == "min" and current_value < threshold_value:
                alert_triggered = True
                severity = "error" if current_value < threshold_value * 0.8 else "warning"
                
            if alert_triggered:
                trend_analysis = self.analyze_trend(name, timedelta(hours=1))
                
                alert = PerformanceAlert(
                    alert_id=f"{name}_{alert_type}_{int(time.time())}",
                    metric_name=name,
                    alert_type=alert_type,
                    severity=severity,
                    message=f"Metric {name} {alert_type} threshold exceeded: {current_value:.2f} vs {threshold_value:.2f}",
                    current_value=current_value,
                    threshold_value=threshold_value,
                    timestamp=latest_data.timestamp,
                    trend_analysis=trend_analysis
                )
                
                alerts.append(alert)
                
        return alerts
        
    def get_all_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all collected metrics"""
        summary = {
            'total_metrics': len(self.metrics),
            'total_data_points': sum(len(data) for data in self.metrics.values()),
            'metrics_by_type': defaultdict(int),
            'oldest_data': None,
            'newest_data': None,
            'metrics': {}
        }
        
        all_timestamps = []
        
        for name, data_points in self.metrics.items():
            if data_points:
                metric_type = self.metric_types[name]
                summary['metrics_by_type'][metric_type.value] += 1
                
                timestamps = [dp.timestamp for dp in data_points]
                all_timestamps.extend(timestamps)
                
                # Get basic stats for each metric
                stats = self.get_metric_statistics(name, timedelta(hours=24))
                trend = self.analyze_trend(name, timedelta(hours=1))
                
                summary['metrics'][name] = {
                    'type': metric_type.value,
                    'data_points': len(data_points),
                    'latest_value': data_points[-1].value,
                    'statistics': stats,
                    'trend': trend.to_dict() if trend else None
                }
                
        if all_timestamps:
            summary['oldest_data'] = min(all_timestamps).isoformat()
            summary['newest_data'] = max(all_timestamps).isoformat()
            
        return summary


class PerformanceAnalyzer:
    """Advanced performance analysis and insights"""
    
    def __init__(self, metric_collector: MetricCollector):
        self.metric_collector = metric_collector
        self.analysis_cache = {}
        
    async def analyze_system_performance(self) -> Dict[str, Any]:
        """Comprehensive system performance analysis"""
        analysis = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'overall_health_score': 0.0,
            'performance_insights': [],
            'anomalies_detected': [],
            'recommendations': [],
            'metric_correlations': {},
            'capacity_planning': {}
        }
        
        # Analyze key performance metrics
        key_metrics = [
            'error_rate', 'response_time', 'throughput', 'circuit_breaker_failures',
            'rate_limit_violations', 'degradation_events'
        ]
        
        health_scores = []
        
        for metric_name in key_metrics:
            if metric_name in self.metric_collector.metrics:
                metric_analysis = await self._analyze_metric_performance(metric_name)
                if metric_analysis:
                    health_scores.append(metric_analysis['health_score'])
                    analysis['performance_insights'].append(metric_analysis)
                    
        # Calculate overall health score
        if health_scores:
            analysis['overall_health_score'] = statistics.mean(health_scores)
            
        # Detect anomalies
        analysis['anomalies_detected'] = await self._detect_anomalies()
        
        # Generate recommendations
        analysis['recommendations'] = await self._generate_recommendations(analysis)
        
        # Analyze correlations between metrics
        analysis['metric_correlations'] = await self._analyze_metric_correlations()
        
        # Capacity planning insights
        analysis['capacity_planning'] = await self._generate_capacity_insights()
        
        return analysis
        
    async def _analyze_metric_performance(self, metric_name: str) -> Optional[Dict[str, Any]]:
        """Analyze performance of a specific metric"""
        if metric_name not in self.metric_collector.metrics:
            return None
            
        # Get recent statistics
        stats = self.metric_collector.get_metric_statistics(
            metric_name, timedelta(hours=1)
        )
        
        # Get trend analysis
        trend = self.metric_collector.analyze_trend(
            metric_name, timedelta(hours=2)
        )
        
        if not stats:
            return None
            
        # Calculate health score based on metric type and values
        health_score = await self._calculate_metric_health_score(metric_name, stats, trend)
        
        # Generate insights
        insights = []
        
        if trend:
            if trend.direction == TrendDirection.INCREASING and metric_name in ['error_rate', 'response_time']:
                insights.append(f"Concerning upward trend in {metric_name}")
            elif trend.direction == TrendDirection.VOLATILE:
                insights.append(f"High volatility detected in {metric_name}")
            elif trend.confidence > 0.8:
                insights.append(f"Strong trend pattern in {metric_name}: {trend.direction.value}")
                
        return {
            'metric_name': metric_name,
            'health_score': health_score,
            'statistics': stats,
            'trend_analysis': trend.to_dict() if trend else None,
            'insights': insights
        }
        
    async def _calculate_metric_health_score(self, metric_name: str, 
                                           stats: Dict, trend: Optional[TrendAnalysis]) -> float:
        """Calculate health score for a metric (0-100)"""
        base_score = 100.0
        
        # Metric-specific scoring
        if metric_name == 'error_rate':
            error_rate = stats.get('mean', 0)
            if error_rate > 0.1:  # >10% error rate
                base_score -= 50
            elif error_rate > 0.05:  # >5% error rate
                base_score -= 25
            elif error_rate > 0.01:  # >1% error rate
                base_score -= 10
                
        elif metric_name == 'response_time':
            avg_response = stats.get('mean', 0)
            if avg_response > 5000:  # >5 seconds
                base_score -= 60
            elif avg_response > 2000:  # >2 seconds
                base_score -= 30
            elif avg_response > 1000:  # >1 second
                base_score -= 15
                
        elif metric_name == 'throughput':
            # Higher throughput is generally better
            throughput = stats.get('mean', 0)
            if throughput < 10:  # Low throughput
                base_score -= 20
                
        # Apply trend impact
        if trend:
            if trend.direction == TrendDirection.INCREASING:
                if metric_name in ['error_rate', 'response_time', 'circuit_breaker_failures']:
                    base_score -= 20 * trend.confidence
                elif metric_name in ['throughput']:
                    base_score += 10 * trend.confidence
                    
            elif trend.direction == TrendDirection.VOLATILE:
                base_score -= 15
                
        return max(0, min(100, base_score))
        
    async def _detect_anomalies(self) -> List[Dict[str, Any]]:
        """Detect anomalies in metrics using statistical methods"""
        anomalies = []
        
        for metric_name in self.metric_collector.metrics:
            data_points = list(self.metric_collector.metrics[metric_name])
            
            if len(data_points) < 50:  # Need sufficient data
                continue
                
            recent_points = data_points[-20:]  # Last 20 points
            historical_points = data_points[-100:-20]  # Previous 80 points
            
            if len(historical_points) < 20:
                continue
                
            recent_values = [dp.value for dp in recent_points]
            historical_values = [dp.value for dp in historical_points]
            
            # Statistical anomaly detection
            historical_mean = statistics.mean(historical_values)
            historical_std = statistics.stdev(historical_values)
            
            for point in recent_points:
                # Z-score based anomaly detection
                if historical_std > 0:
                    z_score = abs(point.value - historical_mean) / historical_std
                    
                    if z_score > 3:  # 3 standard deviations
                        anomalies.append({
                            'metric_name': metric_name,
                            'timestamp': point.timestamp.isoformat(),
                            'value': point.value,
                            'expected_range': f"{historical_mean - 2*historical_std:.2f} - {historical_mean + 2*historical_std:.2f}",
                            'severity': 'high' if z_score > 4 else 'medium',
                            'z_score': z_score
                        })
                        
        return anomalies
        
    async def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate performance recommendations based on analysis"""
        recommendations = []
        
        health_score = analysis['overall_health_score']
        
        if health_score < 50:
            recommendations.append("URGENT: System health is critically low - immediate attention required")
        elif health_score < 70:
            recommendations.append("System performance is degraded - review error rates and response times")
        elif health_score < 85:
            recommendations.append("System performance is acceptable but could be optimized")
            
        # Specific recommendations based on insights
        for insight in analysis['performance_insights']:
            metric_name = insight['metric_name']
            trend = insight.get('trend_analysis')
            
            if trend and trend['direction'] == 'increasing':
                if metric_name == 'error_rate':
                    recommendations.append("Consider enabling circuit breaker protection due to rising error rates")
                elif metric_name == 'response_time':
                    recommendations.append("Investigate performance bottlenecks - response times are increasing")
                elif metric_name == 'rate_limit_violations':
                    recommendations.append("Enable adaptive rate limiting to handle increasing load")
                    
        # Anomaly-based recommendations
        for anomaly in analysis['anomalies_detected']:
            if anomaly['severity'] == 'high':
                recommendations.append(f"Investigate {anomaly['metric_name']} anomaly detected at {anomaly['timestamp']}")
                
        return recommendations
        
    async def _analyze_metric_correlations(self) -> Dict[str, Any]:
        """Analyze correlations between different metrics"""
        correlations = {}
        
        metric_names = list(self.metric_collector.metrics.keys())
        
        for i, metric1 in enumerate(metric_names):
            for metric2 in metric_names[i+1:]:
                correlation = await self._calculate_correlation(metric1, metric2)
                if correlation and abs(correlation) > 0.5:  # Strong correlation
                    key = f"{metric1}_vs_{metric2}"
                    correlations[key] = {
                        'correlation_coefficient': correlation,
                        'strength': 'strong' if abs(correlation) > 0.8 else 'moderate',
                        'direction': 'positive' if correlation > 0 else 'negative'
                    }
                    
        return correlations
        
    async def _calculate_correlation(self, metric1: str, metric2: str) -> Optional[float]:
        """Calculate correlation coefficient between two metrics"""
        data1 = list(self.metric_collector.metrics[metric1])
        data2 = list(self.metric_collector.metrics[metric2])
        
        if len(data1) < 10 or len(data2) < 10:
            return None
            
        # Align timestamps and get common data points
        common_points = []
        
        for dp1 in data1[-50:]:  # Last 50 points
            for dp2 in data2:
                time_diff = abs((dp1.timestamp - dp2.timestamp).total_seconds())
                if time_diff < 60:  # Within 1 minute
                    common_points.append((dp1.value, dp2.value))
                    break
                    
        if len(common_points) < 10:
            return None
            
        values1 = [x[0] for x in common_points]
        values2 = [x[1] for x in common_points]
        
        # Calculate correlation coefficient
        try:
            n = len(values1)
            mean1 = statistics.mean(values1)
            mean2 = statistics.mean(values2)
            
            numerator = sum((x - mean1) * (y - mean2) for x, y in zip(values1, values2))
            
            sum_sq1 = sum((x - mean1) ** 2 for x in values1)
            sum_sq2 = sum((y - mean2) ** 2 for y in values2)
            
            if sum_sq1 * sum_sq2 > 0:
                return numerator / math.sqrt(sum_sq1 * sum_sq2)
        except:
            pass
            
        return None
        
    async def _generate_capacity_insights(self) -> Dict[str, Any]:
        """Generate capacity planning insights"""
        insights = {
            'current_utilization': {},
            'projected_capacity_needs': {},
            'scaling_recommendations': []
        }
        
        # Analyze throughput trends for capacity planning
        throughput_metrics = [name for name in self.metric_collector.metrics.keys() 
                            if 'throughput' in name.lower() or 'requests' in name.lower()]
        
        for metric_name in throughput_metrics:
            trend = self.metric_collector.analyze_trend(metric_name, timedelta(hours=24))
            stats = self.metric_collector.get_metric_statistics(metric_name, timedelta(hours=1))
            
            if trend and stats:
                current_rate = stats.get('mean', 0)
                
                # Project future capacity needs
                if trend.direction == TrendDirection.INCREASING and trend.forecast_next_period:
                    projected_increase = (trend.forecast_next_period - current_rate) / current_rate * 100
                    
                    insights['projected_capacity_needs'][metric_name] = {
                        'current_rate': current_rate,
                        'projected_rate': trend.forecast_next_period,
                        'projected_increase_percent': projected_increase
                    }
                    
                    if projected_increase > 50:
                        insights['scaling_recommendations'].append(
                            f"Consider scaling resources for {metric_name} - projected {projected_increase:.1f}% increase"
                        )
                        
        return insights


# Global enhanced metrics system
_global_metric_collector = MetricCollector()
_global_performance_analyzer = PerformanceAnalyzer(_global_metric_collector)


def get_global_metric_collector() -> MetricCollector:
    """Get global metric collector instance"""
    return _global_metric_collector


def get_global_performance_analyzer() -> PerformanceAnalyzer:
    """Get global performance analyzer instance"""
    return _global_performance_analyzer


# Context manager for timing operations
class TimingContext:
    """Context manager for automatically timing operations"""
    
    def __init__(self, metric_name: str, labels: Dict[str, str] = None):
        self.metric_name = metric_name
        self.labels = labels or {}
        self.start_time = None
        
    async def __aenter__(self):
        self.start_time = time.perf_counter()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration_ms = (time.perf_counter() - self.start_time) * 1000
            
            # Add success/failure label
            success_label = 'true' if exc_type is None else 'false'
            labels = {**self.labels, 'success': success_label}
            
            _global_metric_collector.record_timer(self.metric_name, duration_ms, labels)


# Decorator for automatic metric collection
def collect_metrics(metric_name: str, labels: Dict[str, str] = None):
    """Decorator for automatic metric collection"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            async with TimingContext(f"{metric_name}_duration", labels):
                try:
                    result = await func(*args, **kwargs)
                    _global_metric_collector.record_counter(f"{metric_name}_success", labels=labels)
                    return result
                except Exception as e:
                    error_labels = {**(labels or {}), 'error_type': type(e).__name__}
                    _global_metric_collector.record_counter(f"{metric_name}_error", labels=error_labels)
                    raise
        return wrapper
    return decorator