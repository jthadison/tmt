"""Data quality monitoring system for market data feeds."""

import logging
import statistics
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum

import numpy as np

from .data_normalizer import MarketTick

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Data quality alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class DataQualityAlert:
    """Data quality alert information."""
    alert_type: str
    severity: AlertSeverity
    symbol: str
    source: str
    timestamp: datetime
    description: str
    value: Optional[float] = None
    threshold: Optional[float] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)


class DataQualityMonitor:
    """
    Comprehensive data quality monitoring system.
    
    Monitors market data for gaps, spikes, anomalies, and inconsistencies
    with real-time alerting and quality metrics reporting.
    """
    
    def __init__(self, window_size: int = 1000, spike_threshold: float = 3.0):
        """
        Initialize data quality monitor.
        
        @param window_size: Number of recent data points to analyze
        @param spike_threshold: Standard deviation threshold for spike detection
        """
        self.window_size = window_size
        self.spike_threshold = spike_threshold
        
        # Data storage for analysis
        self.price_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))
        self.volume_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))
        self.timestamp_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))
        
        # Quality metrics
        self.quality_metrics: Dict[str, Dict[str, float]] = defaultdict(dict)
        self.alerts: List[DataQualityAlert] = []
        self.max_alerts = 1000  # Keep last 1000 alerts
        
        # Gap detection
        self.last_timestamps: Dict[str, datetime] = {}
        self.expected_intervals: Dict[str, timedelta] = defaultdict(lambda: timedelta(minutes=1))
        
        # Anomaly detection parameters
        self.volatility_threshold = 0.05  # 5% volatility threshold
        self.volume_spike_threshold = 5.0  # 5x normal volume
        
    def analyze_tick(self, tick: MarketTick) -> List[DataQualityAlert]:
        """
        Analyze market tick for quality issues.
        
        @param tick: MarketTick to analyze
        @returns: List of quality alerts detected
        """
        alerts = []
        key = f"{tick.symbol}_{tick.source}"
        
        try:
            # Store tick data for analysis
            self._store_tick_data(tick, key)
            
            # Run quality checks
            alerts.extend(self._check_price_spikes(tick, key))
            alerts.extend(self._check_volume_anomalies(tick, key))
            alerts.extend(self._check_data_gaps(tick, key))
            alerts.extend(self._check_price_consistency(tick, key))
            alerts.extend(self._check_timestamp_sequence(tick, key))
            
            # Update quality metrics
            self._update_quality_metrics(tick, key, alerts)
            
            # Store alerts
            self.alerts.extend(alerts)
            self._cleanup_old_alerts()
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error analyzing tick for {tick.symbol}: {e}")
            return []
            
    def _store_tick_data(self, tick: MarketTick, key: str):
        """Store tick data in analysis windows."""
        self.price_history[key].append(float(tick.close))
        self.volume_history[key].append(tick.volume)
        self.timestamp_history[key].append(tick.timestamp)
        self.last_timestamps[key] = tick.timestamp
        
    def _check_price_spikes(self, tick: MarketTick, key: str) -> List[DataQualityAlert]:
        """Detect price spikes using statistical analysis."""
        alerts = []
        prices = list(self.price_history[key])
        
        if len(prices) < 10:  # Need minimum data for analysis
            return alerts
            
        try:
            # Calculate price changes
            price_changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]
            
            if not price_changes:
                return alerts
                
            # Statistical analysis
            mean_change = statistics.mean(price_changes)
            std_change = statistics.stdev(price_changes) if len(price_changes) > 1 else 0
            
            if std_change == 0:  # No variation
                return alerts
                
            current_change = prices[-1] - prices[-2] if len(prices) >= 2 else 0
            z_score = abs(current_change - mean_change) / std_change
            
            # Detect spike
            if z_score > self.spike_threshold:
                severity = self._get_spike_severity(z_score)
                
                alert = DataQualityAlert(
                    alert_type="price_spike",
                    severity=severity,
                    symbol=tick.symbol,
                    source=tick.source,
                    timestamp=tick.timestamp,
                    description=f"Price spike detected: {z_score:.2f}σ deviation",
                    value=current_change,
                    threshold=self.spike_threshold,
                    additional_data={
                        "z_score": z_score,
                        "price_change": current_change,
                        "previous_price": prices[-2],
                        "current_price": prices[-1]
                    }
                )
                alerts.append(alert)
                
        except (ValueError, ZeroDivisionError) as e:
            logger.debug(f"Statistical analysis error for {tick.symbol}: {e}")
            
        return alerts
        
    def _check_volume_anomalies(self, tick: MarketTick, key: str) -> List[DataQualityAlert]:
        """Detect volume anomalies."""
        alerts = []
        volumes = list(self.volume_history[key])
        
        if len(volumes) < 10:
            return alerts
            
        try:
            # Skip analysis for forex (volume typically 0)
            if all(v == 0 for v in volumes):
                return alerts
                
            # Calculate volume statistics
            recent_volumes = volumes[-10:]  # Last 10 data points
            avg_volume = statistics.mean(recent_volumes)
            
            if avg_volume == 0:
                return alerts
                
            current_volume = tick.volume
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
            
            # Detect volume spike
            if volume_ratio > self.volume_spike_threshold:
                alert = DataQualityAlert(
                    alert_type="volume_spike",
                    severity=AlertSeverity.MEDIUM,
                    symbol=tick.symbol,
                    source=tick.source,
                    timestamp=tick.timestamp,
                    description=f"Volume spike: {volume_ratio:.1f}x normal volume",
                    value=current_volume,
                    threshold=self.volume_spike_threshold,
                    additional_data={
                        "volume_ratio": volume_ratio,
                        "average_volume": avg_volume,
                        "current_volume": current_volume
                    }
                )
                alerts.append(alert)
                
            # Detect zero volume (for non-forex)
            elif current_volume == 0 and avg_volume > 0:
                alert = DataQualityAlert(
                    alert_type="zero_volume",
                    severity=AlertSeverity.LOW,
                    symbol=tick.symbol,
                    source=tick.source,
                    timestamp=tick.timestamp,
                    description="Zero volume detected for active symbol",
                    value=0,
                    additional_data={"average_volume": avg_volume}
                )
                alerts.append(alert)
                
        except (ValueError, ZeroDivisionError) as e:
            logger.debug(f"Volume analysis error for {tick.symbol}: {e}")
            
        return alerts
        
    def _check_data_gaps(self, tick: MarketTick, key: str) -> List[DataQualityAlert]:
        """Detect data gaps based on timestamp intervals."""
        alerts = []
        
        if key not in self.last_timestamps:
            return alerts
            
        last_timestamp = self.last_timestamps[key]
        current_timestamp = tick.timestamp
        gap_duration = current_timestamp - last_timestamp
        expected_interval = self.expected_intervals[key]
        
        # Allow 50% tolerance for expected interval
        gap_threshold = expected_interval * 1.5
        
        if gap_duration > gap_threshold:
            severity = AlertSeverity.HIGH if gap_duration > expected_interval * 5 else AlertSeverity.MEDIUM
            
            alert = DataQualityAlert(
                alert_type="data_gap",
                severity=severity,
                symbol=tick.symbol,
                source=tick.source,
                timestamp=tick.timestamp,
                description=f"Data gap detected: {gap_duration.total_seconds():.0f}s",
                value=gap_duration.total_seconds(),
                threshold=gap_threshold.total_seconds(),
                additional_data={
                    "gap_duration": gap_duration.total_seconds(),
                    "expected_interval": expected_interval.total_seconds(),
                    "last_timestamp": last_timestamp.isoformat(),
                    "current_timestamp": current_timestamp.isoformat()
                }
            )
            alerts.append(alert)
            
        return alerts
        
    def _check_price_consistency(self, tick: MarketTick, key: str) -> List[DataQualityAlert]:
        """Check OHLC price consistency."""
        alerts = []
        
        try:
            # Validate OHLC relationships
            open_price = float(tick.open)
            high_price = float(tick.high)
            low_price = float(tick.low)
            close_price = float(tick.close)
            
            inconsistencies = []
            
            if high_price < max(open_price, close_price):
                inconsistencies.append(f"High ({high_price}) < max(open, close)")
                
            if low_price > min(open_price, close_price):
                inconsistencies.append(f"Low ({low_price}) > min(open, close)")
                
            if high_price < low_price:
                inconsistencies.append(f"High ({high_price}) < Low ({low_price})")
                
            if inconsistencies:
                alert = DataQualityAlert(
                    alert_type="price_consistency",
                    severity=AlertSeverity.HIGH,
                    symbol=tick.symbol,
                    source=tick.source,
                    timestamp=tick.timestamp,
                    description=f"OHLC inconsistency: {', '.join(inconsistencies)}",
                    additional_data={
                        "open": open_price,
                        "high": high_price,
                        "low": low_price,
                        "close": close_price,
                        "inconsistencies": inconsistencies
                    }
                )
                alerts.append(alert)
                
        except (ValueError, TypeError) as e:
            logger.error(f"Price consistency check error for {tick.symbol}: {e}")
            
        return alerts
        
    def _check_timestamp_sequence(self, tick: MarketTick, key: str) -> List[DataQualityAlert]:
        """Check timestamp sequence consistency."""
        alerts = []
        timestamps = list(self.timestamp_history[key])
        
        if len(timestamps) < 2:
            return alerts
            
        current_time = timestamps[-1]
        previous_time = timestamps[-2]
        
        # Check for backwards timestamps
        if current_time < previous_time:
            alert = DataQualityAlert(
                alert_type="timestamp_sequence",
                severity=AlertSeverity.HIGH,
                symbol=tick.symbol,
                source=tick.source,
                timestamp=tick.timestamp,
                description="Timestamp sequence error: current < previous",
                additional_data={
                    "current_timestamp": current_time.isoformat(),
                    "previous_timestamp": previous_time.isoformat(),
                    "time_diff": (current_time - previous_time).total_seconds()
                }
            )
            alerts.append(alert)
            
        return alerts
        
    def _get_spike_severity(self, z_score: float) -> AlertSeverity:
        """Determine spike severity based on z-score."""
        if z_score > 10:
            return AlertSeverity.CRITICAL
        elif z_score > 6:
            return AlertSeverity.HIGH
        elif z_score > 4:
            return AlertSeverity.MEDIUM
        else:
            return AlertSeverity.LOW
            
    def _update_quality_metrics(self, tick: MarketTick, key: str, alerts: List[DataQualityAlert]):
        """Update quality metrics for symbol."""
        if key not in self.quality_metrics:
            self.quality_metrics[key] = {
                "total_ticks": 0,
                "alert_count": 0,
                "quality_score": 1.0,
                "last_update": tick.timestamp.isoformat()
            }
            
        metrics = self.quality_metrics[key]
        metrics["total_ticks"] += 1
        metrics["alert_count"] += len(alerts)
        metrics["last_update"] = tick.timestamp.isoformat()
        
        # Calculate quality score (1.0 = perfect, 0.0 = poor)
        if metrics["total_ticks"] > 0:
            alert_rate = metrics["alert_count"] / metrics["total_ticks"]
            metrics["quality_score"] = max(0.0, 1.0 - (alert_rate * 2))  # Scale factor of 2
            
    def _cleanup_old_alerts(self):
        """Remove old alerts to maintain memory efficiency."""
        if len(self.alerts) > self.max_alerts:
            # Keep most recent alerts
            self.alerts = self.alerts[-self.max_alerts:]
            
    def get_quality_report(self, symbol: Optional[str] = None, hours: int = 24) -> Dict[str, Any]:
        """
        Generate data quality report.
        
        @param symbol: Optional symbol filter
        @param hours: Hours of history to include
        @returns: Quality report dictionary
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        # Filter alerts by time and symbol
        filtered_alerts = [
            alert for alert in self.alerts
            if alert.timestamp >= cutoff_time and (not symbol or alert.symbol == symbol)
        ]
        
        # Group alerts by type and severity
        alert_summary = defaultdict(lambda: defaultdict(int))
        for alert in filtered_alerts:
            alert_summary[alert.alert_type][alert.severity.value] += 1
            
        # Calculate overall quality metrics
        total_alerts = len(filtered_alerts)
        symbols_with_issues = len(set(alert.symbol for alert in filtered_alerts))
        
        report = {
            "report_period": f"{hours} hours",
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_alerts": total_alerts,
                "symbols_with_issues": symbols_with_issues,
                "alert_types": len(alert_summary),
                "most_common_issue": max(alert_summary.keys(), key=lambda k: sum(alert_summary[k].values())) if alert_summary else None
            },
            "alert_breakdown": dict(alert_summary),
            "quality_metrics": dict(self.quality_metrics) if not symbol else {
                k: v for k, v in self.quality_metrics.items() if k.startswith(f"{symbol}_")
            },
            "recent_alerts": [
                {
                    "type": alert.alert_type,
                    "severity": alert.severity.value,
                    "symbol": alert.symbol,
                    "source": alert.source,
                    "timestamp": alert.timestamp.isoformat(),
                    "description": alert.description
                }
                for alert in filtered_alerts[-10:]  # Last 10 alerts
            ]
        }
        
        return report
        
    def get_symbol_health(self, symbol: str) -> Dict[str, Any]:
        """
        Get health status for specific symbol.
        
        @param symbol: Symbol to analyze
        @returns: Health status dictionary
        """
        symbol_alerts = [alert for alert in self.alerts if alert.symbol == symbol]
        recent_alerts = [alert for alert in symbol_alerts if alert.timestamp >= datetime.now() - timedelta(hours=1)]
        
        # Find quality metrics for this symbol
        symbol_metrics = {
            k: v for k, v in self.quality_metrics.items() if k.startswith(f"{symbol}_")
        }
        
        # Calculate overall health score
        if symbol_metrics:
            avg_quality_score = statistics.mean(metrics["quality_score"] for metrics in symbol_metrics.values())
        else:
            avg_quality_score = 1.0
            
        # Determine health status
        if avg_quality_score > 0.9 and len(recent_alerts) == 0:
            health_status = "excellent"
        elif avg_quality_score > 0.7 and len(recent_alerts) < 3:
            health_status = "good"
        elif avg_quality_score > 0.5 and len(recent_alerts) < 10:
            health_status = "fair"
        else:
            health_status = "poor"
            
        return {
            "symbol": symbol,
            "health_status": health_status,
            "quality_score": avg_quality_score,
            "total_alerts": len(symbol_alerts),
            "recent_alerts": len(recent_alerts),
            "data_sources": len(symbol_metrics),
            "last_update": max(
                (metrics["last_update"] for metrics in symbol_metrics.values()),
                default=None
            )
        }