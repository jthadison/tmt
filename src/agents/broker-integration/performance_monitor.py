"""
Performance Monitoring and SLA Tracking for Broker Integration
Story 8.13: Production Deployment & Monitoring
"""
import asyncio
import time
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import statistics
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

class SLAType(Enum):
    AVAILABILITY = "availability"
    LATENCY = "latency"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"

class PerformanceLevel(Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    DEGRADED = "degraded"
    CRITICAL = "critical"

@dataclass
class SLATarget:
    """SLA target definition"""
    type: SLAType
    target_value: float
    measurement_window: int  # seconds
    breach_threshold: float  # percentage of time can be below target
    description: str

@dataclass
class PerformanceMetric:
    """Performance metric data point"""
    timestamp: float
    value: float
    broker: str
    metric_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SLAStatus:
    """Current SLA compliance status"""
    sla_type: SLAType
    current_value: float
    target_value: float
    compliance_percentage: float
    status: PerformanceLevel
    last_breach: Optional[datetime] = None
    consecutive_breaches: int = 0

class PerformanceMonitor:
    """Comprehensive performance monitoring and SLA tracking"""
    
    def __init__(self):
        self.sla_targets = self._initialize_sla_targets()
        self.metrics_buffer: Dict[str, deque] = defaultdict(lambda: deque(maxlen=3600))  # 1 hour buffer
        self.sla_statuses: Dict[Tuple[str, SLAType], SLAStatus] = {}
        self.performance_history: Dict[str, List[PerformanceMetric]] = defaultdict(list)
        self.running = False
        self.start_time = time.time()
        
    def _initialize_sla_targets(self) -> Dict[SLAType, SLATarget]:
        """Initialize SLA targets based on business requirements"""
        return {
            SLAType.AVAILABILITY: SLATarget(
                type=SLAType.AVAILABILITY,
                target_value=99.5,  # 99.5% uptime
                measurement_window=300,  # 5 minutes
                breach_threshold=5.0,  # 5% of time can be below target
                description="Service availability SLA"
            ),
            SLAType.LATENCY: SLATarget(
                type=SLAType.LATENCY,
                target_value=1.0,  # 1 second P95 latency
                measurement_window=300,  # 5 minutes
                breach_threshold=10.0,  # 10% of time can exceed target
                description="P95 response time SLA"
            ),
            SLAType.ERROR_RATE: SLATarget(
                type=SLAType.ERROR_RATE,
                target_value=0.1,  # 0.1% error rate
                measurement_window=300,  # 5 minutes
                breach_threshold=5.0,  # 5% of time can exceed target
                description="Error rate SLA"
            ),
            SLAType.THROUGHPUT: SLATarget(
                type=SLAType.THROUGHPUT,
                target_value=100.0,  # 100 requests/second minimum
                measurement_window=300,  # 5 minutes
                breach_threshold=15.0,  # 15% of time can be below target
                description="Minimum throughput SLA"
            )
        }
    
    async def start_monitoring(self):
        """Start performance monitoring"""
        self.running = True
        logger.info("Performance monitoring started")
        
        # Start monitoring tasks
        asyncio.create_task(self._monitor_sla_compliance())
        asyncio.create_task(self._track_performance_trends())
        asyncio.create_task(self._generate_performance_reports())
    
    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.running = False
        logger.info("Performance monitoring stopped")
    
    def record_metric(self, broker: str, metric_type: str, value: float, metadata: Dict[str, Any] = None):
        """Record a performance metric"""
        metric = PerformanceMetric(
            timestamp=time.time(),
            value=value,
            broker=broker,
            metric_type=metric_type,
            metadata=metadata or {}
        )
        
        key = f"{broker}:{metric_type}"
        self.metrics_buffer[key].append(metric)
        self.performance_history[key].append(metric)
        
        # Keep history manageable (last 24 hours)
        cutoff_time = time.time() - 86400
        self.performance_history[key] = [
            m for m in self.performance_history[key] 
            if m.timestamp > cutoff_time
        ]
    
    def calculate_availability(self, broker: str, window_seconds: int = 300) -> float:
        """Calculate service availability percentage"""
        key = f"{broker}:health_status"
        if key not in self.metrics_buffer:
            return 0.0
        
        cutoff_time = time.time() - window_seconds
        recent_metrics = [
            m for m in self.metrics_buffer[key] 
            if m.timestamp > cutoff_time
        ]
        
        if not recent_metrics:
            return 0.0
        
        healthy_count = sum(1 for m in recent_metrics if m.value == 1.0)
        return (healthy_count / len(recent_metrics)) * 100
    
    def calculate_p95_latency(self, broker: str, window_seconds: int = 300) -> float:
        """Calculate P95 latency"""
        key = f"{broker}:request_latency"
        if key not in self.metrics_buffer:
            return float('inf')
        
        cutoff_time = time.time() - window_seconds
        recent_metrics = [
            m.value for m in self.metrics_buffer[key] 
            if m.timestamp > cutoff_time
        ]
        
        if not recent_metrics:
            return float('inf')
        
        return statistics.quantiles(recent_metrics, n=20)[18]  # 95th percentile
    
    def calculate_error_rate(self, broker: str, window_seconds: int = 300) -> float:
        """Calculate error rate percentage"""
        total_key = f"{broker}:total_requests"
        error_key = f"{broker}:error_requests"
        
        cutoff_time = time.time() - window_seconds
        
        total_requests = sum(
            m.value for m in self.metrics_buffer.get(total_key, [])
            if m.timestamp > cutoff_time
        )
        
        error_requests = sum(
            m.value for m in self.metrics_buffer.get(error_key, [])
            if m.timestamp > cutoff_time
        )
        
        if total_requests == 0:
            return 0.0
        
        return (error_requests / total_requests) * 100
    
    def calculate_throughput(self, broker: str, window_seconds: int = 300) -> float:
        """Calculate requests per second throughput"""
        key = f"{broker}:total_requests"
        if key not in self.metrics_buffer:
            return 0.0
        
        cutoff_time = time.time() - window_seconds
        recent_metrics = [
            m for m in self.metrics_buffer[key] 
            if m.timestamp > cutoff_time
        ]
        
        if len(recent_metrics) < 2:
            return 0.0
        
        total_requests = sum(m.value for m in recent_metrics)
        time_span = recent_metrics[-1].timestamp - recent_metrics[0].timestamp
        
        if time_span == 0:
            return 0.0
        
        return total_requests / time_span
    
    def get_sla_status(self, broker: str, sla_type: SLAType) -> SLAStatus:
        """Get current SLA status for broker and type"""
        key = (broker, sla_type)
        
        if key not in self.sla_statuses:
            self.sla_statuses[key] = SLAStatus(
                sla_type=sla_type,
                current_value=0.0,
                target_value=self.sla_targets[sla_type].target_value,
                compliance_percentage=0.0,
                status=PerformanceLevel.CRITICAL
            )
        
        return self.sla_statuses[key]
    
    def _update_sla_status(self, broker: str, sla_type: SLAType, current_value: float):
        """Update SLA status based on current metrics"""
        target = self.sla_targets[sla_type]
        key = (broker, sla_type)
        
        # Calculate compliance based on SLA type
        if sla_type == SLAType.AVAILABILITY:
            compliance = min(100.0, (current_value / target.target_value) * 100)
            is_meeting_target = current_value >= target.target_value
        elif sla_type == SLAType.ERROR_RATE:
            compliance = max(0.0, 100.0 - (current_value / target.target_value) * 100)
            is_meeting_target = current_value <= target.target_value
        elif sla_type == SLAType.LATENCY:
            compliance = max(0.0, 100.0 - ((current_value - target.target_value) / target.target_value) * 100)
            is_meeting_target = current_value <= target.target_value
        else:  # THROUGHPUT
            compliance = min(100.0, (current_value / target.target_value) * 100)
            is_meeting_target = current_value >= target.target_value
        
        # Determine performance level
        if compliance >= 99.0:
            status = PerformanceLevel.EXCELLENT
        elif compliance >= 95.0:
            status = PerformanceLevel.GOOD
        elif compliance >= 90.0:
            status = PerformanceLevel.DEGRADED
        else:
            status = PerformanceLevel.CRITICAL
        
        # Update SLA status
        sla_status = self.get_sla_status(broker, sla_type)
        sla_status.current_value = current_value
        sla_status.compliance_percentage = compliance
        sla_status.status = status
        
        # Track breaches
        if not is_meeting_target:
            if sla_status.last_breach is None or \
               (datetime.now() - sla_status.last_breach).total_seconds() > 300:
                sla_status.consecutive_breaches = 1
            else:
                sla_status.consecutive_breaches += 1
            sla_status.last_breach = datetime.now()
        else:
            sla_status.consecutive_breaches = 0
    
    async def _monitor_sla_compliance(self):
        """Monitor SLA compliance continuously"""
        while self.running:
            try:
                brokers = ['oanda', 'tradelocker', 'dxtrade']
                
                for broker in brokers:
                    # Check availability SLA
                    availability = self.calculate_availability(broker)
                    self._update_sla_status(broker, SLAType.AVAILABILITY, availability)
                    
                    # Check latency SLA
                    p95_latency = self.calculate_p95_latency(broker)
                    if p95_latency != float('inf'):
                        self._update_sla_status(broker, SLAType.LATENCY, p95_latency)
                    
                    # Check error rate SLA
                    error_rate = self.calculate_error_rate(broker)
                    self._update_sla_status(broker, SLAType.ERROR_RATE, error_rate)
                    
                    # Check throughput SLA
                    throughput = self.calculate_throughput(broker)
                    self._update_sla_status(broker, SLAType.THROUGHPUT, throughput)
                
                await asyncio.sleep(30)  # Check SLAs every 30 seconds
                
            except Exception as e:
                logger.error(f"Error monitoring SLA compliance: {e}")
                await asyncio.sleep(60)
    
    async def _track_performance_trends(self):
        """Track performance trends and detect anomalies"""
        while self.running:
            try:
                brokers = ['oanda', 'tradelocker', 'dxtrade']
                
                for broker in brokers:
                    # Analyze latency trends
                    await self._analyze_latency_trends(broker)
                    
                    # Analyze throughput trends
                    await self._analyze_throughput_trends(broker)
                    
                    # Analyze error rate trends
                    await self._analyze_error_trends(broker)
                
                await asyncio.sleep(300)  # Analyze trends every 5 minutes
                
            except Exception as e:
                logger.error(f"Error tracking performance trends: {e}")
                await asyncio.sleep(300)
    
    async def _analyze_latency_trends(self, broker: str):
        """Analyze latency trends for anomaly detection"""
        key = f"{broker}:request_latency"
        if key not in self.metrics_buffer:
            return
        
        # Get last hour of data
        cutoff_time = time.time() - 3600
        recent_metrics = [
            m.value for m in self.metrics_buffer[key] 
            if m.timestamp > cutoff_time
        ]
        
        if len(recent_metrics) < 10:
            return
        
        # Calculate trend metrics
        mean_latency = statistics.mean(recent_metrics)
        median_latency = statistics.median(recent_metrics)
        stdev_latency = statistics.stdev(recent_metrics) if len(recent_metrics) > 1 else 0
        
        # Detect anomalies (values > mean + 2*stdev)
        anomaly_threshold = mean_latency + (2 * stdev_latency)
        anomalies = [m for m in recent_metrics if m > anomaly_threshold]
        
        if len(anomalies) > len(recent_metrics) * 0.05:  # More than 5% anomalies
            logger.warning(f"High latency anomalies detected for {broker}: "
                         f"{len(anomalies)} anomalies out of {len(recent_metrics)} samples")
    
    async def _analyze_throughput_trends(self, broker: str):
        """Analyze throughput trends"""
        key = f"{broker}:total_requests"
        if key not in self.metrics_buffer:
            return
        
        # Calculate 5-minute throughput windows
        current_time = time.time()
        windows = []
        
        for i in range(12):  # Last 12 windows (1 hour)
            window_start = current_time - (i + 1) * 300
            window_end = current_time - i * 300
            
            window_metrics = [
                m.value for m in self.metrics_buffer[key]
                if window_start <= m.timestamp < window_end
            ]
            
            if window_metrics:
                window_throughput = sum(window_metrics) / 300  # requests per second
                windows.append(window_throughput)
        
        if len(windows) >= 6:  # Need at least 30 minutes of data
            # Detect declining throughput trend
            recent_avg = statistics.mean(windows[:3])  # Last 15 minutes
            historical_avg = statistics.mean(windows[6:])  # 30-45 minutes ago
            
            if recent_avg < historical_avg * 0.8:  # 20% decline
                logger.warning(f"Declining throughput trend detected for {broker}: "
                             f"Recent: {recent_avg:.2f} req/s, Historical: {historical_avg:.2f} req/s")
    
    async def _analyze_error_trends(self, broker: str):
        """Analyze error rate trends"""
        total_key = f"{broker}:total_requests"
        error_key = f"{broker}:error_requests"
        
        # Calculate error rates over time windows
        current_time = time.time()
        error_rates = []
        
        for i in range(12):  # Last 12 windows (1 hour)
            window_start = current_time - (i + 1) * 300
            window_end = current_time - i * 300
            
            total_requests = sum(
                m.value for m in self.metrics_buffer.get(total_key, [])
                if window_start <= m.timestamp < window_end
            )
            
            error_requests = sum(
                m.value for m in self.metrics_buffer.get(error_key, [])
                if window_start <= m.timestamp < window_end
            )
            
            if total_requests > 0:
                error_rate = (error_requests / total_requests) * 100
                error_rates.append(error_rate)
        
        if len(error_rates) >= 6:
            # Detect increasing error rate trend
            recent_avg = statistics.mean(error_rates[:3])  # Last 15 minutes
            historical_avg = statistics.mean(error_rates[6:])  # 30-45 minutes ago
            
            if recent_avg > historical_avg * 2 and recent_avg > 1.0:  # 2x increase and > 1%
                logger.warning(f"Increasing error rate trend detected for {broker}: "
                             f"Recent: {recent_avg:.2f}%, Historical: {historical_avg:.2f}%")
    
    async def _generate_performance_reports(self):
        """Generate periodic performance reports"""
        while self.running:
            try:
                await asyncio.sleep(3600)  # Generate reports every hour
                
                report = self.generate_performance_report()
                logger.info(f"Performance Report: {report}")
                
            except Exception as e:
                logger.error(f"Error generating performance reports: {e}")
                await asyncio.sleep(3600)
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        brokers = ['oanda', 'tradelocker', 'dxtrade']
        report = {
            'timestamp': datetime.now().isoformat(),
            'report_period': '1_hour',
            'brokers': {}
        }
        
        for broker in brokers:
            broker_report = {
                'availability': self.calculate_availability(broker, 3600),
                'p95_latency': self.calculate_p95_latency(broker, 3600),
                'error_rate': self.calculate_error_rate(broker, 3600),
                'throughput': self.calculate_throughput(broker, 3600),
                'sla_status': {}
            }
            
            # Add SLA status for each type
            for sla_type in SLAType:
                sla_status = self.get_sla_status(broker, sla_type)
                broker_report['sla_status'][sla_type.value] = {
                    'compliance_percentage': sla_status.compliance_percentage,
                    'status': sla_status.status.value,
                    'consecutive_breaches': sla_status.consecutive_breaches
                }
            
            report['brokers'][broker] = broker_report
        
        return report
    
    def get_capacity_recommendations(self) -> Dict[str, Any]:
        """Generate capacity planning recommendations"""
        recommendations = {
            'timestamp': datetime.now().isoformat(),
            'brokers': {}
        }
        
        brokers = ['oanda', 'tradelocker', 'dxtrade']
        
        for broker in brokers:
            current_throughput = self.calculate_throughput(broker, 3600)
            peak_throughput = current_throughput * 1.5  # Assume 50% growth
            
            # Calculate recommended resources
            current_connections = 20  # Default pool size
            recommended_connections = max(current_connections, int(peak_throughput / 5))
            
            recommendations['brokers'][broker] = {
                'current_throughput': current_throughput,
                'projected_peak_throughput': peak_throughput,
                'current_connection_pool_size': current_connections,
                'recommended_connection_pool_size': recommended_connections,
                'scaling_factor': recommended_connections / current_connections
            }
        
        return recommendations

# Global performance monitor instance
performance_monitor: Optional[PerformanceMonitor] = None

def get_performance_monitor() -> PerformanceMonitor:
    """Get or create global performance monitor"""
    global performance_monitor
    if performance_monitor is None:
        performance_monitor = PerformanceMonitor()
    return performance_monitor

async def initialize_performance_monitoring():
    """Initialize performance monitoring"""
    global performance_monitor
    performance_monitor = PerformanceMonitor()
    await performance_monitor.start_monitoring()
    return performance_monitor