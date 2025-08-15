"""
Latency Monitoring System
Story 8.5: Real-Time Price Streaming - Task 6: Create latency monitoring system
"""
import asyncio
import logging
from typing import Dict, List, Optional, Callable, Any, NamedTuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import deque, defaultdict
import statistics
import json

logger = logging.getLogger(__name__)

class LatencyThreshold(Enum):
    """Latency threshold levels"""
    EXCELLENT = "excellent"    # < 50ms
    GOOD = "good"             # 50-100ms  
    ACCEPTABLE = "acceptable"  # 100-200ms
    POOR = "poor"             # 200-500ms
    CRITICAL = "critical"      # > 500ms

class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

@dataclass
class LatencyMeasurement:
    """Single latency measurement"""
    component: str
    measurement_type: str
    latency_ms: float
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    
class LatencyPoint(NamedTuple):
    """Latency measurement point"""
    name: str
    timestamp: datetime

@dataclass
class EndToEndTrace:
    """End-to-end latency trace"""
    trace_id: str
    instrument: str
    start_time: datetime
    points: List[LatencyPoint] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_point(self, name: str, timestamp: Optional[datetime] = None):
        """Add measurement point to trace"""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        self.points.append(LatencyPoint(name, timestamp))
        
    def get_total_latency(self) -> float:
        """Get total end-to-end latency in milliseconds"""
        if len(self.points) < 2:
            return 0.0
        
        return (self.points[-1].timestamp - self.start_time).total_seconds() * 1000
        
    def get_segment_latencies(self) -> Dict[str, float]:
        """Get latency for each segment"""
        if len(self.points) < 2:
            return {}
            
        latencies = {}
        prev_time = self.start_time
        
        for point in self.points:
            segment_latency = (point.timestamp - prev_time).total_seconds() * 1000
            latencies[point.name] = segment_latency
            prev_time = point.timestamp
            
        return latencies

@dataclass 
class LatencyAlert:
    """Latency alert"""
    severity: AlertSeverity
    component: str
    message: str
    latency_ms: float
    threshold_ms: float
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

class LatencyStats:
    """Latency statistics calculator"""
    
    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        self.measurements: deque = deque(maxlen=window_size)
        
    def add_measurement(self, latency_ms: float):
        """Add latency measurement"""
        self.measurements.append(latency_ms)
        
    def get_stats(self) -> Dict[str, float]:
        """Get statistical summary"""
        if not self.measurements:
            return {
                'count': 0,
                'mean': 0.0,
                'median': 0.0,
                'p95': 0.0,
                'p99': 0.0,
                'min': 0.0,
                'max': 0.0,
                'std_dev': 0.0
            }
            
        measurements = list(self.measurements)
        
        return {
            'count': len(measurements),
            'mean': statistics.mean(measurements),
            'median': statistics.median(measurements),
            'p95': self._percentile(measurements, 95),
            'p99': self._percentile(measurements, 99),
            'min': min(measurements),
            'max': max(measurements),
            'std_dev': statistics.stdev(measurements) if len(measurements) > 1 else 0.0
        }
        
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = (percentile / 100) * (len(sorted_data) - 1)
        
        if index.is_integer():
            return sorted_data[int(index)]
        else:
            lower = sorted_data[int(index)]
            upper = sorted_data[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))

class NetworkPerformanceMonitor:
    """Monitors network performance metrics"""
    
    def __init__(self):
        self.connection_tests: deque = deque(maxlen=100)
        self.packet_loss_history: deque = deque(maxlen=100)
        self.jitter_history: deque = deque(maxlen=100)
        
    async def test_connectivity(self, host: str, port: int, timeout: float = 5.0) -> Dict[str, Any]:
        """Test network connectivity to host"""
        start_time = datetime.now(timezone.utc)
        
        try:
            # Test TCP connection
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=timeout
            )
            
            # Close connection immediately
            writer.close()
            await writer.wait_closed()
            
            latency = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            result = {
                'success': True,
                'latency_ms': latency,
                'timestamp': start_time,
                'host': host,
                'port': port
            }
            
            self.connection_tests.append(result)
            return result
            
        except asyncio.TimeoutError:
            result = {
                'success': False,
                'error': 'timeout',
                'timestamp': start_time,
                'host': host,
                'port': port
            }
            self.connection_tests.append(result)
            return result
            
        except Exception as e:
            result = {
                'success': False,
                'error': str(e),
                'timestamp': start_time,
                'host': host,
                'port': port
            }
            self.connection_tests.append(result)
            return result
            
    def get_network_stats(self) -> Dict[str, Any]:
        """Get network performance statistics"""
        if not self.connection_tests:
            return {
                'connection_success_rate': 0.0,
                'avg_latency_ms': 0.0,
                'tests_count': 0
            }
            
        successful_tests = [test for test in self.connection_tests if test['success']]
        
        return {
            'connection_success_rate': len(successful_tests) / len(self.connection_tests),
            'avg_latency_ms': statistics.mean([test['latency_ms'] for test in successful_tests]) if successful_tests else 0.0,
            'tests_count': len(self.connection_tests),
            'last_test': list(self.connection_tests)[-1] if self.connection_tests else None
        }

class LatencyOptimizer:
    """Provides latency optimization recommendations"""
    
    def __init__(self):
        self.recommendations_cache: Dict[str, List[str]] = {}
        
    def analyze_latency_profile(self, stats: Dict[str, LatencyStats]) -> List[str]:
        """Analyze latency profile and provide recommendations"""
        recommendations = []
        
        for component, latency_stats in stats.items():
            component_stats = latency_stats.get_stats()
            
            if component_stats['count'] == 0:
                continue
                
            mean_latency = component_stats['mean']
            p99_latency = component_stats['p99']
            std_dev = component_stats['std_dev']
            
            # High latency recommendations
            if mean_latency > 200:
                recommendations.append(
                    f"{component}: Mean latency {mean_latency:.1f}ms is high. "
                    "Consider optimizing data processing or upgrading network connection."
                )
                
            # High variability recommendations  
            if std_dev > 50:
                recommendations.append(
                    f"{component}: High latency variability (σ={std_dev:.1f}ms). "
                    "Check for network congestion or resource contention."
                )
                
            # P99 tail latency recommendations
            if p99_latency > 500:
                recommendations.append(
                    f"{component}: P99 latency {p99_latency:.1f}ms indicates tail latency issues. "
                    "Consider connection pooling or request batching."
                )
                
        # General recommendations
        if not recommendations:
            recommendations.append(
                "Latency performance is within acceptable ranges. "
                "Monitor trends for any degradation."
            )
            
        return recommendations
        
    def get_optimization_suggestions(self, component: str, latency_ms: float) -> List[str]:
        """Get specific optimization suggestions for a component"""
        suggestions = []
        
        if component == "oanda_stream":
            if latency_ms > 100:
                suggestions.extend([
                    "Ensure stable internet connection with low jitter",
                    "Consider upgrading to premium internet plan",
                    "Check for background applications consuming bandwidth",
                    "Optimize WebSocket message handling"
                ])
        elif component == "price_processing":
            if latency_ms > 50:
                suggestions.extend([
                    "Optimize price calculation algorithms",
                    "Consider using compiled math libraries",
                    "Reduce unnecessary data transformations",
                    "Implement price calculation caching"
                ])
        elif component == "distribution_server":
            if latency_ms > 30:
                suggestions.extend([
                    "Enable message compression",
                    "Implement message batching",
                    "Optimize WebSocket send operations",
                    "Consider using binary message format"
                ])
                
        return suggestions

class LatencyMonitor:
    """Comprehensive latency monitoring system"""
    
    def __init__(self):
        # Component statistics
        self.component_stats: Dict[str, LatencyStats] = defaultdict(lambda: LatencyStats())
        
        # Active traces
        self.active_traces: Dict[str, EndToEndTrace] = {}
        self.completed_traces: deque = deque(maxlen=1000)
        
        # Alerting
        self.alert_callbacks: List[Callable[[LatencyAlert], None]] = []
        self.alert_history: deque = deque(maxlen=500)
        
        # Thresholds (in milliseconds)
        self.component_thresholds: Dict[str, Dict[str, float]] = {
            'oanda_stream': {
                'warning': 100.0,
                'critical': 300.0
            },
            'price_processing': {
                'warning': 50.0,
                'critical': 150.0
            },
            'distribution_server': {
                'warning': 30.0,
                'critical': 100.0
            },
            'end_to_end': {
                'warning': 200.0,
                'critical': 500.0
            }
        }
        
        # Network monitoring
        self.network_monitor = NetworkPerformanceMonitor()
        
        # Optimization
        self.optimizer = LatencyOptimizer()
        
        # Background tasks
        self.monitoring_task: Optional[asyncio.Task] = None
        self.network_test_task: Optional[asyncio.Task] = None
        self.is_running = False
        
        # Configuration
        self.network_test_interval = 60  # seconds
        self.trace_timeout = 30  # seconds
        
    async def start_monitoring(self):
        """Start background monitoring tasks"""
        if self.is_running:
            return
            
        self.is_running = True
        
        # Start background tasks
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        self.network_test_task = asyncio.create_task(self._network_test_loop())
        
        logger.info("Latency monitoring started")
        
    async def stop_monitoring(self):
        """Stop background monitoring"""
        if not self.is_running:
            return
            
        self.is_running = False
        
        # Cancel tasks
        if self.monitoring_task:
            self.monitoring_task.cancel()
        if self.network_test_task:
            self.network_test_task.cancel()
            
        logger.info("Latency monitoring stopped")
        
    def add_measurement(self, component: str, measurement_type: str, latency_ms: float, 
                       metadata: Optional[Dict[str, Any]] = None):
        """Add latency measurement for component"""
        measurement = LatencyMeasurement(
            component=component,
            measurement_type=measurement_type,
            latency_ms=latency_ms,
            timestamp=datetime.now(timezone.utc),
            metadata=metadata or {}
        )
        
        # Update statistics
        self.component_stats[component].add_measurement(latency_ms)
        
        # Check thresholds and generate alerts
        self._check_thresholds(measurement)
        
    def start_trace(self, trace_id: str, instrument: str, metadata: Optional[Dict[str, Any]] = None) -> EndToEndTrace:
        """Start end-to-end latency trace"""
        trace = EndToEndTrace(
            trace_id=trace_id,
            instrument=instrument,
            start_time=datetime.now(timezone.utc),
            metadata=metadata or {}
        )
        
        self.active_traces[trace_id] = trace
        return trace
        
    def add_trace_point(self, trace_id: str, point_name: str, timestamp: Optional[datetime] = None):
        """Add point to active trace"""
        if trace_id in self.active_traces:
            self.active_traces[trace_id].add_point(point_name, timestamp)
            
    def complete_trace(self, trace_id: str) -> Optional[EndToEndTrace]:
        """Complete and analyze trace"""
        if trace_id not in self.active_traces:
            return None
            
        trace = self.active_traces.pop(trace_id)
        
        # Calculate end-to-end latency
        total_latency = trace.get_total_latency()
        
        # Add to measurements
        self.add_measurement(
            'end_to_end',
            'trace_complete',
            total_latency,
            {
                'instrument': trace.instrument,
                'segments': trace.get_segment_latencies(),
                'points': len(trace.points)
            }
        )
        
        # Store completed trace
        self.completed_traces.append(trace)
        
        return trace
        
    def add_alert_callback(self, callback: Callable[[LatencyAlert], None]):
        """Add callback for latency alerts"""
        self.alert_callbacks.append(callback)
        
    def _check_thresholds(self, measurement: LatencyMeasurement):
        """Check measurement against thresholds and generate alerts"""
        component = measurement.component
        latency_ms = measurement.latency_ms
        
        if component not in self.component_thresholds:
            return
            
        thresholds = self.component_thresholds[component]
        
        alert = None
        
        if latency_ms >= thresholds.get('critical', float('inf')):
            alert = LatencyAlert(
                severity=AlertSeverity.CRITICAL,
                component=component,
                message=f"Critical latency: {latency_ms:.1f}ms (threshold: {thresholds['critical']}ms)",
                latency_ms=latency_ms,
                threshold_ms=thresholds['critical'],
                timestamp=measurement.timestamp,
                metadata=measurement.metadata
            )
        elif latency_ms >= thresholds.get('warning', float('inf')):
            alert = LatencyAlert(
                severity=AlertSeverity.WARNING,
                component=component,
                message=f"High latency warning: {latency_ms:.1f}ms (threshold: {thresholds['warning']}ms)",
                latency_ms=latency_ms,
                threshold_ms=thresholds['warning'],
                timestamp=measurement.timestamp,
                metadata=measurement.metadata
            )
            
        if alert:
            self.alert_history.append(alert)
            self._notify_alert(alert)
            
    def _notify_alert(self, alert: LatencyAlert):
        """Notify alert callbacks"""
        for callback in self.alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(alert))
                else:
                    callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
                
    async def _monitoring_loop(self):
        """Background monitoring loop"""
        while self.is_running:
            try:
                # Clean up expired traces
                await self._cleanup_expired_traces()
                
                # Generate periodic reports
                if int(datetime.now(timezone.utc).timestamp()) % 300 == 0:  # Every 5 minutes
                    await self._generate_periodic_report()
                    
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)
                
    async def _cleanup_expired_traces(self):
        """Clean up traces that have exceeded timeout"""
        current_time = datetime.now(timezone.utc)
        expired_traces = []
        
        for trace_id, trace in self.active_traces.items():
            if (current_time - trace.start_time).total_seconds() > self.trace_timeout:
                expired_traces.append(trace_id)
                
        for trace_id in expired_traces:
            logger.warning(f"Trace {trace_id} expired after {self.trace_timeout}s")
            self.active_traces.pop(trace_id, None)
            
    async def _network_test_loop(self):
        """Background network testing loop"""
        while self.is_running:
            try:
                # Test OANDA connectivity
                await self.network_monitor.test_connectivity(
                    'stream-fxpractice.oanda.com', 443
                )
                
                await asyncio.sleep(self.network_test_interval)
                
            except Exception as e:
                logger.error(f"Error in network test loop: {e}")
                await asyncio.sleep(30)
                
    async def _generate_periodic_report(self):
        """Generate periodic latency report"""
        logger.info("Generating latency performance report")
        
        # Get optimization recommendations
        recommendations = self.optimizer.analyze_latency_profile(self.component_stats)
        
        if recommendations:
            logger.info("Latency optimization recommendations:")
            for rec in recommendations:
                logger.info(f"  - {rec}")
                
    def get_latency_stats(self) -> Dict[str, Any]:
        """Get comprehensive latency statistics"""
        stats = {}
        
        for component, latency_stats in self.component_stats.items():
            stats[component] = latency_stats.get_stats()
            
        return stats
        
    def get_latency_visualization_data(self, component: str, window_minutes: int = 60) -> Dict[str, Any]:
        """Get data for latency visualization"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
        
        # This is a simplified version - in production, you'd store timestamped measurements
        component_stats = self.component_stats.get(component)
        if not component_stats:
            return {
                'component': component,
                'data_points': [],
                'stats': {},
                'time_range': window_minutes
            }
            
        stats = component_stats.get_stats()
        
        return {
            'component': component,
            'data_points': list(component_stats.measurements)[-100:],  # Last 100 points
            'stats': stats,
            'time_range': window_minutes,
            'threshold': self.component_thresholds.get(component, {})
        }
        
    def get_system_health_summary(self) -> Dict[str, Any]:
        """Get overall system health summary"""
        all_stats = self.get_latency_stats()
        network_stats = self.network_monitor.get_network_stats()
        
        # Calculate overall health score (0-100)
        health_score = 100
        
        for component, stats in all_stats.items():
            if stats['count'] > 0:
                mean_latency = stats['mean']
                thresholds = self.component_thresholds.get(component, {})
                
                if mean_latency > thresholds.get('critical', float('inf')):
                    health_score -= 30
                elif mean_latency > thresholds.get('warning', float('inf')):
                    health_score -= 15
                    
        # Factor in network connectivity
        if network_stats['connection_success_rate'] < 0.95:
            health_score -= 20
            
        health_score = max(0, health_score)
        
        return {
            'health_score': health_score,
            'status': self._get_health_status(health_score),
            'latency_stats': all_stats,
            'network_stats': network_stats,
            'active_traces': len(self.active_traces),
            'recent_alerts': len([a for a in self.alert_history if 
                                (datetime.now(timezone.utc) - a.timestamp).total_seconds() < 300]),
            'recommendations': self.optimizer.analyze_latency_profile(self.component_stats)
        }
        
    def _get_health_status(self, health_score: int) -> str:
        """Get health status based on score"""
        if health_score >= 90:
            return "excellent"
        elif health_score >= 75:
            return "good"
        elif health_score >= 60:
            return "acceptable"
        elif health_score >= 40:
            return "poor"
        else:
            return "critical"