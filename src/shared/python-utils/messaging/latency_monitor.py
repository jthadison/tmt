"""
Message Latency Monitoring for Inter-Agent Communication

Provides comprehensive latency tracking with:
- End-to-end message latency measurement (<10ms target)
- Per-topic and per-event-type metrics
- Real-time latency percentiles and alerting
- Message flow tracing and bottleneck detection
- SLA monitoring and reporting
"""

import asyncio
import time
from collections import deque, defaultdict
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Tuple, Deque
from dataclasses import dataclass
from enum import Enum
import statistics

import structlog
from prometheus_client import Histogram, Counter, Gauge, Summary

from .event_schemas import BaseEvent, EventType


logger = structlog.get_logger(__name__)

# Prometheus metrics for latency monitoring
MESSAGE_LATENCY_HISTOGRAM = Histogram(
    'message_latency_seconds',
    'Message latency from production to consumption',
    ['source_agent', 'target_agent', 'event_type', 'topic'],
    buckets=(0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0)
)

MESSAGE_LATENCY_SUMMARY = Summary(
    'message_latency_summary_seconds',
    'Message latency summary statistics',
    ['source_agent', 'target_agent', 'event_type']
)

LATENCY_SLA_VIOLATIONS = Counter(
    'message_latency_sla_violations_total',
    'Number of messages violating latency SLA',
    ['source_agent', 'target_agent', 'event_type', 'sla_threshold']
)

CURRENT_MESSAGE_LATENCY = Gauge(
    'message_latency_current_seconds',
    'Current message latency for real-time monitoring',
    ['source_agent', 'target_agent', 'event_type']
)

LATENCY_PERCENTILES = Gauge(
    'message_latency_percentile_seconds',
    'Message latency percentiles',
    ['source_agent', 'target_agent', 'event_type', 'percentile']
)


class LatencySeverity(Enum):
    """Latency alert severity levels"""
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class LatencyMeasurement:
    """Individual latency measurement"""
    correlation_id: str
    event_type: EventType
    source_agent: str
    target_agent: str
    topic: str
    produced_at: datetime
    consumed_at: datetime
    latency_ms: float
    
    @property
    def latency_seconds(self) -> float:
        return self.latency_ms / 1000.0


@dataclass
class LatencyAlert:
    """Latency alert information"""
    severity: LatencySeverity
    message: str
    correlation_id: str
    event_type: EventType
    source_agent: str
    target_agent: str
    actual_latency_ms: float
    threshold_ms: float
    timestamp: datetime


class LatencySLA:
    """Service Level Agreement definition for latency"""
    
    def __init__(
        self,
        target_latency_ms: float = 10.0,
        warning_threshold_ms: float = 20.0,
        critical_threshold_ms: float = 50.0,
        emergency_threshold_ms: float = 100.0,
        violation_rate_threshold: float = 0.05  # 5% of messages
    ):
        self.target_latency_ms = target_latency_ms
        self.warning_threshold_ms = warning_threshold_ms
        self.critical_threshold_ms = critical_threshold_ms
        self.emergency_threshold_ms = emergency_threshold_ms
        self.violation_rate_threshold = violation_rate_threshold
    
    def get_severity(self, latency_ms: float) -> LatencySeverity:
        """Get severity level for a latency measurement"""
        if latency_ms >= self.emergency_threshold_ms:
            return LatencySeverity.EMERGENCY
        elif latency_ms >= self.critical_threshold_ms:
            return LatencySeverity.CRITICAL
        elif latency_ms >= self.warning_threshold_ms:
            return LatencySeverity.WARNING
        else:
            return LatencySeverity.NORMAL


class LatencyMonitor:
    """
    Comprehensive message latency monitoring system.
    
    Tracks end-to-end message latency between agents with:
    - Real-time latency measurement and alerting
    - Statistical analysis and percentile tracking
    - SLA violation detection and reporting
    - Historical data retention and trend analysis
    - Integration with Prometheus metrics
    """
    
    def __init__(
        self,
        sla: Optional[LatencySLA] = None,
        history_retention_hours: int = 24,
        measurement_window_minutes: int = 5,
        enable_alerts: bool = True,
        alert_callback: Optional[callable] = None
    ):
        self.sla = sla or LatencySLA()
        self.history_retention_hours = history_retention_hours
        self.measurement_window_minutes = measurement_window_minutes
        self.enable_alerts = enable_alerts
        self.alert_callback = alert_callback
        
        # Historical data storage
        self._measurements: List[LatencyMeasurement] = []
        self._measurements_by_flow: Dict[str, List[LatencyMeasurement]] = defaultdict(list)
        
        # Real-time window data for percentile calculation
        self._windowed_measurements: Dict[str, Deque[LatencyMeasurement]] = defaultdict(
            lambda: deque(maxlen=1000)
        )
        
        # Alert state tracking
        self._recent_alerts: List[LatencyAlert] = []
        self._violation_counts: Dict[str, int] = defaultdict(int)
        self._total_message_counts: Dict[str, int] = defaultdict(int)
        
        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._metrics_update_task: Optional[asyncio.Task] = None
        self._start_time = time.time()
        
        logger.info(
            "LatencyMonitor initialized",
            target_latency_ms=self.sla.target_latency_ms,
            warning_threshold_ms=self.sla.warning_threshold_ms,
            critical_threshold_ms=self.sla.critical_threshold_ms
        )
    
    async def start(self) -> None:
        """Start background monitoring tasks"""
        if not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(self._cleanup_old_data())
        
        if not self._metrics_update_task:
            self._metrics_update_task = asyncio.create_task(self._update_metrics_periodically())
        
        logger.info("LatencyMonitor background tasks started")
    
    async def stop(self) -> None:
        """Stop background monitoring tasks"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        if self._metrics_update_task:
            self._metrics_update_task.cancel()
            try:
                await self._metrics_update_task
            except asyncio.CancelledError:
                pass
        
        logger.info("LatencyMonitor background tasks stopped")
    
    def record_message_produced(
        self,
        event: BaseEvent,
        topic: str,
        produced_at: Optional[datetime] = None
    ) -> None:
        """
        Record that a message was produced.
        
        This is called when a message is sent to Kafka.
        """
        # For now, we store the production timestamp in the event
        # The actual latency measurement happens when consumed
        pass
    
    def record_message_consumed(
        self,
        event: BaseEvent,
        topic: str,
        target_agent: str,
        consumed_at: Optional[datetime] = None
    ) -> None:
        """
        Record that a message was consumed and calculate latency.
        
        Args:
            event: The consumed event
            topic: Kafka topic name
            target_agent: Agent that consumed the message
            consumed_at: When the message was consumed (defaults to now)
        """
        consumed_at = consumed_at or datetime.now(timezone.utc)
        produced_at = event.timestamp
        
        if not produced_at:
            logger.warning(
                "Cannot calculate latency - missing production timestamp",
                correlation_id=event.correlation_id,
                event_type=event.event_type.value
            )
            return
        
        # Calculate latency
        latency_delta = consumed_at - produced_at
        latency_ms = latency_delta.total_seconds() * 1000
        
        # Create measurement
        measurement = LatencyMeasurement(
            correlation_id=event.correlation_id,
            event_type=event.event_type,
            source_agent=event.source_agent,
            target_agent=target_agent,
            topic=topic,
            produced_at=produced_at,
            consumed_at=consumed_at,
            latency_ms=latency_ms
        )
        
        # Store measurement
        self._record_measurement(measurement)
        
        # Update metrics
        self._update_prometheus_metrics(measurement)
        
        # Check for SLA violations
        if self.enable_alerts:
            self._check_sla_violation(measurement)
        
        logger.debug(
            "Message latency recorded",
            correlation_id=event.correlation_id,
            latency_ms=round(latency_ms, 2),
            source_agent=event.source_agent,
            target_agent=target_agent,
            event_type=event.event_type.value
        )
    
    def _record_measurement(self, measurement: LatencyMeasurement) -> None:
        """Store measurement in historical data"""
        # Add to global measurements
        self._measurements.append(measurement)
        
        # Add to flow-specific measurements
        flow_key = f"{measurement.source_agent}->{measurement.target_agent}"
        self._measurements_by_flow[flow_key].append(measurement)
        
        # Add to windowed measurements for real-time analysis
        self._windowed_measurements[flow_key].append(measurement)
        
        # Update message counts
        self._total_message_counts[flow_key] += 1
    
    def _update_prometheus_metrics(self, measurement: LatencyMeasurement) -> None:
        """Update Prometheus metrics with measurement"""
        labels = {
            'source_agent': measurement.source_agent,
            'target_agent': measurement.target_agent,
            'event_type': measurement.event_type.value,
            'topic': measurement.topic
        }
        
        # Update histogram
        MESSAGE_LATENCY_HISTOGRAM.labels(**labels).observe(measurement.latency_seconds)
        
        # Update summary (without topic label)
        summary_labels = {k: v for k, v in labels.items() if k != 'topic'}
        MESSAGE_LATENCY_SUMMARY.labels(**summary_labels).observe(measurement.latency_seconds)
        
        # Update current latency gauge
        CURRENT_MESSAGE_LATENCY.labels(**summary_labels).set(measurement.latency_seconds)
    
    def _check_sla_violation(self, measurement: LatencyMeasurement) -> None:
        """Check if measurement violates SLA and generate alerts"""
        severity = self.sla.get_severity(measurement.latency_ms)
        flow_key = f"{measurement.source_agent}->{measurement.target_agent}"
        
        # Track violations
        if severity != LatencySeverity.NORMAL:
            self._violation_counts[flow_key] += 1
            
            # Update Prometheus violation counter
            LATENCY_SLA_VIOLATIONS.labels(
                source_agent=measurement.source_agent,
                target_agent=measurement.target_agent,
                event_type=measurement.event_type.value,
                sla_threshold=str(int(self.sla.target_latency_ms))
            ).inc()
            
            # Create alert
            alert = LatencyAlert(
                severity=severity,
                message=f"Message latency {measurement.latency_ms:.1f}ms exceeds {severity.value} threshold",
                correlation_id=measurement.correlation_id,
                event_type=measurement.event_type,
                source_agent=measurement.source_agent,
                target_agent=measurement.target_agent,
                actual_latency_ms=measurement.latency_ms,
                threshold_ms=self._get_threshold_for_severity(severity),
                timestamp=measurement.consumed_at
            )
            
            self._recent_alerts.append(alert)
            
            # Trigger alert callback if configured
            if self.alert_callback:
                try:
                    self.alert_callback(alert)
                except Exception as e:
                    logger.error(f"Alert callback failed: {e}")
            
            logger.warning(
                "Latency SLA violation",
                severity=severity.value,
                correlation_id=measurement.correlation_id,
                latency_ms=round(measurement.latency_ms, 2),
                threshold_ms=alert.threshold_ms,
                source_agent=measurement.source_agent,
                target_agent=measurement.target_agent
            )
    
    def _get_threshold_for_severity(self, severity: LatencySeverity) -> float:
        """Get threshold value for severity level"""
        if severity == LatencySeverity.WARNING:
            return self.sla.warning_threshold_ms
        elif severity == LatencySeverity.CRITICAL:
            return self.sla.critical_threshold_ms
        elif severity == LatencySeverity.EMERGENCY:
            return self.sla.emergency_threshold_ms
        return self.sla.target_latency_ms
    
    async def _cleanup_old_data(self) -> None:
        """Background task to clean up old measurement data"""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self.history_retention_hours)
                
                # Clean up measurements
                self._measurements = [
                    m for m in self._measurements
                    if m.consumed_at > cutoff_time
                ]
                
                # Clean up flow measurements
                for flow_key in list(self._measurements_by_flow.keys()):
                    self._measurements_by_flow[flow_key] = [
                        m for m in self._measurements_by_flow[flow_key]
                        if m.consumed_at > cutoff_time
                    ]
                
                # Clean up alerts (keep last 100)
                if len(self._recent_alerts) > 100:
                    self._recent_alerts = self._recent_alerts[-100:]
                
                logger.debug("Old latency measurement data cleaned up")
                
            except Exception as e:
                logger.error(f"Error cleaning up latency data: {e}")
    
    async def _update_metrics_periodically(self) -> None:
        """Background task to update percentile metrics"""
        while True:
            try:
                await asyncio.sleep(30)  # Update every 30 seconds
                
                for flow_key, measurements in self._windowed_measurements.items():
                    if not measurements:
                        continue
                    
                    # Extract latencies
                    latencies = [m.latency_seconds for m in measurements]
                    
                    # Get flow components
                    source_agent, target_agent = flow_key.split('->')
                    
                    # Calculate percentiles
                    if len(latencies) >= 10:  # Need minimum data points
                        percentiles = [50, 90, 95, 99]
                        for p in percentiles:
                            percentile_value = statistics.quantiles(latencies, n=100)[p-1]
                            
                            # Update Prometheus gauge (use representative event type)
                            event_type_str = measurements[-1].event_type.value
                            
                            LATENCY_PERCENTILES.labels(
                                source_agent=source_agent,
                                target_agent=target_agent,
                                event_type=event_type_str,
                                percentile=str(p)
                            ).set(percentile_value)
                
            except Exception as e:
                logger.error(f"Error updating latency percentiles: {e}")
    
    def get_latency_statistics(
        self,
        source_agent: Optional[str] = None,
        target_agent: Optional[str] = None,
        event_type: Optional[EventType] = None,
        time_window_minutes: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get latency statistics for specified criteria.
        
        Args:
            source_agent: Filter by source agent
            target_agent: Filter by target agent  
            event_type: Filter by event type
            time_window_minutes: Only include measurements from last N minutes
            
        Returns:
            Dictionary with latency statistics
        """
        # Filter measurements
        measurements = self._measurements
        
        if time_window_minutes:
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=time_window_minutes)
            measurements = [m for m in measurements if m.consumed_at > cutoff_time]
        
        if source_agent:
            measurements = [m for m in measurements if m.source_agent == source_agent]
        
        if target_agent:
            measurements = [m for m in measurements if m.target_agent == target_agent]
        
        if event_type:
            measurements = [m for m in measurements if m.event_type == event_type]
        
        if not measurements:
            return {"error": "No measurements found for criteria"}
        
        # Calculate statistics
        latencies = [m.latency_ms for m in measurements]
        
        stats = {
            "total_messages": len(measurements),
            "min_latency_ms": min(latencies),
            "max_latency_ms": max(latencies),
            "avg_latency_ms": statistics.mean(latencies),
            "median_latency_ms": statistics.median(latencies),
        }
        
        # Calculate percentiles if we have enough data
        if len(latencies) >= 10:
            try:
                percentiles = statistics.quantiles(latencies, n=100)
                stats.update({
                    "p50_latency_ms": percentiles[49],  # 50th percentile
                    "p90_latency_ms": percentiles[89],  # 90th percentile  
                    "p95_latency_ms": percentiles[94],  # 95th percentile
                    "p99_latency_ms": percentiles[98],  # 99th percentile
                })
            except statistics.StatisticsError:
                pass
        
        # SLA compliance
        violations = len([l for l in latencies if l > self.sla.target_latency_ms])
        stats["sla_compliance_rate"] = (len(latencies) - violations) / len(latencies)
        stats["sla_violations"] = violations
        
        return stats
    
    def get_flow_statistics(self) -> Dict[str, Any]:
        """Get statistics for all agent-to-agent flows"""
        flow_stats = {}
        
        for flow_key, measurements in self._measurements_by_flow.items():
            if not measurements:
                continue
            
            recent_measurements = [
                m for m in measurements
                if m.consumed_at > datetime.now(timezone.utc) - timedelta(minutes=self.measurement_window_minutes)
            ]
            
            if recent_measurements:
                latencies = [m.latency_ms for m in recent_measurements]
                violations = self._violation_counts.get(flow_key, 0)
                total_messages = self._total_message_counts.get(flow_key, 0)
                
                flow_stats[flow_key] = {
                    "recent_messages": len(recent_measurements),
                    "total_messages": total_messages,
                    "avg_latency_ms": statistics.mean(latencies),
                    "max_latency_ms": max(latencies),
                    "violation_count": violations,
                    "violation_rate": violations / total_messages if total_messages > 0 else 0
                }
        
        return flow_stats
    
    def get_recent_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent latency alerts"""
        return [
            {
                "severity": alert.severity.value,
                "message": alert.message,
                "correlation_id": alert.correlation_id,
                "event_type": alert.event_type.value,
                "source_agent": alert.source_agent,
                "target_agent": alert.target_agent,
                "actual_latency_ms": round(alert.actual_latency_ms, 2),
                "threshold_ms": alert.threshold_ms,
                "timestamp": alert.timestamp.isoformat()
            }
            for alert in self._recent_alerts[-limit:]
        ]
    
    def is_healthy(self) -> bool:
        """Check if latency monitoring indicates healthy system"""
        # Check recent violation rates
        recent_time = datetime.now(timezone.utc) - timedelta(minutes=5)
        
        recent_measurements = [
            m for m in self._measurements
            if m.consumed_at > recent_time
        ]
        
        if not recent_measurements:
            return True  # No data, assume healthy
        
        violations = len([
            m for m in recent_measurements
            if m.latency_ms > self.sla.critical_threshold_ms
        ])
        
        violation_rate = violations / len(recent_measurements)
        return violation_rate < self.sla.violation_rate_threshold