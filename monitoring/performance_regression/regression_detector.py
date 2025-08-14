"""
Performance Regression Detection Pipeline for TMT Trading System

Automatically detects performance degradation and alerts before SLA breaches.
Implements statistical analysis and machine learning for early warning system.
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import aiohttp
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from scipy import stats
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RegressionSeverity(Enum):
    """Regression severity levels"""
    MINOR = "minor"
    MODERATE = "moderate"
    SEVERE = "severe"
    CRITICAL = "critical"


class MetricType(Enum):
    """Types of metrics monitored"""
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    RESOURCE_USAGE = "resource_usage"
    BUSINESS_METRIC = "business_metric"


@dataclass
class RegressionAlert:
    """Performance regression alert"""
    metric_name: str
    metric_type: MetricType
    current_value: float
    baseline_value: float
    deviation_percentage: float
    severity: RegressionSeverity
    detection_time: datetime
    confidence_score: float
    trend_duration: timedelta
    affected_components: List[str]
    suggested_actions: List[str]
    alert_id: str


@dataclass
class MetricBaseline:
    """Baseline statistics for a metric"""
    metric_name: str
    mean: float
    std: float
    p95: float
    p99: float
    min_value: float
    max_value: float
    sample_count: int
    baseline_period: Tuple[datetime, datetime]
    last_updated: datetime


class PerformanceRegressionDetector:
    """
    Detects performance regressions using statistical analysis and ML models.
    
    Features:
    - Statistical anomaly detection
    - Trend analysis
    - Machine learning-based anomaly detection
    - Multi-metric correlation analysis
    - Early warning system
    """
    
    def __init__(self, prometheus_url: str = "http://localhost:9090"):
        self.prometheus_url = prometheus_url
        self.baselines: Dict[str, MetricBaseline] = {}
        self.isolation_forests: Dict[str, IsolationForest] = {}
        self.scalers: Dict[str, StandardScaler] = {}
        
        # Configuration
        self.baseline_window = timedelta(days=7)  # Use last 7 days for baseline
        self.detection_window = timedelta(hours=1)  # Detect over last hour
        self.confidence_threshold = 0.8  # Minimum confidence for alerts
        self.severity_thresholds = {
            RegressionSeverity.CRITICAL: 0.50,  # 50% degradation
            RegressionSeverity.SEVERE: 0.30,    # 30% degradation
            RegressionSeverity.MODERATE: 0.15,  # 15% degradation
            RegressionSeverity.MINOR: 0.05      # 5% degradation
        }
        
        # Critical metrics configuration
        self.critical_metrics = {
            "signal_execution_latency": {
                "query": "histogram_quantile(0.95, rate(tmt_signal_execution_duration_seconds_bucket[5m]))",
                "type": MetricType.LATENCY,
                "threshold": 0.1,  # 100ms SLA
                "direction": "higher_is_worse"
            },
            "trade_execution_success_rate": {
                "query": "rate(tmt_trade_execution_success_total[5m]) / rate(tmt_trade_execution_total[5m])",
                "type": MetricType.THROUGHPUT,
                "threshold": 0.995,  # 99.5% success rate
                "direction": "lower_is_worse"
            },
            "system_uptime": {
                "query": "avg_over_time(up[5m])",
                "type": MetricType.THROUGHPUT,
                "threshold": 0.995,  # 99.5% uptime
                "direction": "lower_is_worse"
            },
            "database_query_latency": {
                "query": "rate(tmt_db_query_duration_seconds_sum[5m]) / rate(tmt_db_query_duration_seconds_count[5m])",
                "type": MetricType.LATENCY,
                "threshold": 0.01,  # 10ms
                "direction": "higher_is_worse"
            },
            "agent_communication_latency": {
                "query": "histogram_quantile(0.95, rate(tmt_agent_communication_duration_seconds_bucket[5m]))",
                "type": MetricType.LATENCY,
                "threshold": 0.05,  # 50ms
                "direction": "higher_is_worse"
            }
        }
    
    async def initialize_baselines(self) -> None:
        """Initialize baselines for all critical metrics"""
        logger.info("Initializing performance baselines...")
        
        for metric_name, config in self.critical_metrics.items():
            try:
                baseline = await self.calculate_baseline(metric_name, config["query"])
                self.baselines[metric_name] = baseline
                
                # Train isolation forest for anomaly detection
                await self.train_anomaly_detector(metric_name, config["query"])
                
                logger.info(f"Baseline initialized for {metric_name}: mean={baseline.mean:.4f}, p95={baseline.p95:.4f}")
                
            except Exception as e:
                logger.error(f"Failed to initialize baseline for {metric_name}: {e}")
    
    async def calculate_baseline(self, metric_name: str, query: str) -> MetricBaseline:
        """Calculate baseline statistics for a metric"""
        end_time = datetime.utcnow()
        start_time = end_time - self.baseline_window
        
        # Fetch historical data
        data = await self.fetch_metric_data(query, start_time, end_time, step="5m")
        
        if not data:
            raise ValueError(f"No data available for metric {metric_name}")
        
        values = [float(point[1]) for point in data]
        
        return MetricBaseline(
            metric_name=metric_name,
            mean=np.mean(values),
            std=np.std(values),
            p95=np.percentile(values, 95),
            p99=np.percentile(values, 99),
            min_value=np.min(values),
            max_value=np.max(values),
            sample_count=len(values),
            baseline_period=(start_time, end_time),
            last_updated=datetime.utcnow()
        )
    
    async def train_anomaly_detector(self, metric_name: str, query: str) -> None:
        """Train isolation forest for anomaly detection"""
        end_time = datetime.utcnow()
        start_time = end_time - self.baseline_window
        
        # Fetch training data
        data = await self.fetch_metric_data(query, start_time, end_time, step="1m")
        
        if len(data) < 100:  # Minimum samples for training
            logger.warning(f"Insufficient data for ML training: {metric_name}")
            return
        
        # Prepare features: value, hour of day, day of week
        features = []
        for timestamp, value in data:
            dt = datetime.fromtimestamp(timestamp)
            features.append([
                float(value),
                dt.hour,
                dt.weekday(),
                dt.minute
            ])
        
        features_array = np.array(features)
        
        # Scale features
        scaler = StandardScaler()
        scaled_features = scaler.fit_transform(features_array)
        
        # Train isolation forest
        iso_forest = IsolationForest(
            contamination=0.1,  # Expect 10% anomalies
            random_state=42,
            n_estimators=100
        )
        iso_forest.fit(scaled_features)
        
        # Store models
        self.scalers[metric_name] = scaler
        self.isolation_forests[metric_name] = iso_forest
        
        logger.info(f"Anomaly detector trained for {metric_name}")
    
    async def detect_regressions(self) -> List[RegressionAlert]:
        """Detect performance regressions across all metrics"""
        alerts = []
        
        for metric_name, config in self.critical_metrics.items():
            try:
                alert = await self.analyze_metric_regression(metric_name, config)
                if alert:
                    alerts.append(alert)
            except Exception as e:
                logger.error(f"Regression analysis failed for {metric_name}: {e}")
        
        return alerts
    
    async def analyze_metric_regression(self, metric_name: str, config: Dict) -> Optional[RegressionAlert]:
        """Analyze single metric for performance regression"""
        if metric_name not in self.baselines:
            logger.warning(f"No baseline available for {metric_name}")
            return None
        
        baseline = self.baselines[metric_name]
        
        # Fetch recent data
        end_time = datetime.utcnow()
        start_time = end_time - self.detection_window
        
        recent_data = await self.fetch_metric_data(
            config["query"], start_time, end_time, step="1m"
        )
        
        if not recent_data:
            logger.warning(f"No recent data for {metric_name}")
            return None
        
        current_values = [float(point[1]) for point in recent_data]
        current_mean = np.mean(current_values)
        
        # Statistical analysis
        stat_result = await self.statistical_analysis(
            baseline, current_values, config["direction"]
        )
        
        # ML anomaly detection
        ml_result = await self.ml_anomaly_detection(
            metric_name, recent_data
        )
        
        # Trend analysis
        trend_result = await self.trend_analysis(current_values)
        
        # Combine analyses for final decision
        confidence_score = self.calculate_confidence_score(
            stat_result, ml_result, trend_result
        )
        
        if confidence_score < self.confidence_threshold:
            return None
        
        # Determine severity
        severity = self.determine_severity(
            baseline.mean, current_mean, config["direction"]
        )
        
        # Calculate deviation percentage
        if config["direction"] == "higher_is_worse":
            deviation = (current_mean - baseline.mean) / baseline.mean
        else:
            deviation = (baseline.mean - current_mean) / baseline.mean
        
        # Generate suggested actions
        suggested_actions = self.generate_suggested_actions(
            metric_name, severity, deviation
        )
        
        return RegressionAlert(
            metric_name=metric_name,
            metric_type=config["type"],
            current_value=current_mean,
            baseline_value=baseline.mean,
            deviation_percentage=deviation * 100,
            severity=severity,
            detection_time=datetime.utcnow(),
            confidence_score=confidence_score,
            trend_duration=self.detection_window,
            affected_components=self.identify_affected_components(metric_name),
            suggested_actions=suggested_actions,
            alert_id=self.generate_alert_id(metric_name)
        )
    
    async def statistical_analysis(self, baseline: MetricBaseline, 
                                 current_values: List[float], 
                                 direction: str) -> Dict:
        """Perform statistical analysis for regression detection"""
        current_mean = np.mean(current_values)
        current_std = np.std(current_values)
        
        # Z-score analysis
        z_score = abs(current_mean - baseline.mean) / baseline.std
        z_score_significant = z_score > 2.0  # 95% confidence
        
        # T-test for means comparison
        baseline_samples = np.random.normal(
            baseline.mean, baseline.std, baseline.sample_count
        )
        t_stat, p_value = stats.ttest_ind(baseline_samples, current_values)
        t_test_significant = p_value < 0.05
        
        # Check if regression in correct direction
        is_regression = False
        if direction == "higher_is_worse" and current_mean > baseline.mean:
            is_regression = True
        elif direction == "lower_is_worse" and current_mean < baseline.mean:
            is_regression = True
        
        return {
            "z_score": z_score,
            "z_score_significant": z_score_significant,
            "t_test_p_value": p_value,
            "t_test_significant": t_test_significant,
            "is_regression": is_regression,
            "deviation_magnitude": abs(current_mean - baseline.mean) / baseline.mean
        }
    
    async def ml_anomaly_detection(self, metric_name: str, 
                                 recent_data: List[Tuple[float, str]]) -> Dict:
        """Use ML models to detect anomalies"""
        if metric_name not in self.isolation_forests:
            return {"anomaly_detected": False, "anomaly_score": 0.0}
        
        iso_forest = self.isolation_forests[metric_name]
        scaler = self.scalers[metric_name]
        
        # Prepare features for recent data
        features = []
        for timestamp, value in recent_data:
            dt = datetime.fromtimestamp(timestamp)
            features.append([
                float(value),
                dt.hour,
                dt.weekday(),
                dt.minute
            ])
        
        if not features:
            return {"anomaly_detected": False, "anomaly_score": 0.0}
        
        features_array = np.array(features)
        scaled_features = scaler.transform(features_array)
        
        # Predict anomalies
        predictions = iso_forest.predict(scaled_features)
        anomaly_scores = iso_forest.decision_function(scaled_features)
        
        # Calculate metrics
        anomaly_count = np.sum(predictions == -1)
        anomaly_percentage = anomaly_count / len(predictions)
        avg_anomaly_score = np.mean(anomaly_scores)
        
        return {
            "anomaly_detected": anomaly_percentage > 0.3,  # 30% threshold
            "anomaly_score": abs(avg_anomaly_score),
            "anomaly_percentage": anomaly_percentage
        }
    
    async def trend_analysis(self, values: List[float]) -> Dict:
        """Analyze trend in recent values"""
        if len(values) < 3:
            return {"trend_detected": False, "slope": 0.0}
        
        x = np.arange(len(values))
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, values)
        
        # Significant trend if R² > 0.5 and p < 0.05
        trend_significant = r_value**2 > 0.5 and p_value < 0.05
        
        return {
            "trend_detected": trend_significant,
            "slope": slope,
            "r_squared": r_value**2,
            "p_value": p_value
        }
    
    def calculate_confidence_score(self, stat_result: Dict, 
                                 ml_result: Dict, 
                                 trend_result: Dict) -> float:
        """Calculate overall confidence score for regression detection"""
        score = 0.0
        
        # Statistical significance (40% weight)
        if stat_result["is_regression"]:
            if stat_result["z_score_significant"] and stat_result["t_test_significant"]:
                score += 0.4
            elif stat_result["z_score_significant"] or stat_result["t_test_significant"]:
                score += 0.2
        
        # ML anomaly detection (35% weight)
        if ml_result["anomaly_detected"]:
            score += 0.35 * min(ml_result["anomaly_score"], 1.0)
        
        # Trend analysis (25% weight)
        if trend_result["trend_detected"]:
            score += 0.25 * min(trend_result["r_squared"], 1.0)
        
        return score
    
    def determine_severity(self, baseline_value: float, 
                         current_value: float, 
                         direction: str) -> RegressionSeverity:
        """Determine severity of performance regression"""
        if direction == "higher_is_worse":
            deviation = (current_value - baseline_value) / baseline_value
        else:
            deviation = (baseline_value - current_value) / baseline_value
        
        if deviation >= self.severity_thresholds[RegressionSeverity.CRITICAL]:
            return RegressionSeverity.CRITICAL
        elif deviation >= self.severity_thresholds[RegressionSeverity.SEVERE]:
            return RegressionSeverity.SEVERE
        elif deviation >= self.severity_thresholds[RegressionSeverity.MODERATE]:
            return RegressionSeverity.MODERATE
        else:
            return RegressionSeverity.MINOR
    
    def generate_suggested_actions(self, metric_name: str, 
                                 severity: RegressionSeverity, 
                                 deviation: float) -> List[str]:
        """Generate suggested actions based on regression analysis"""
        actions = []
        
        if metric_name == "signal_execution_latency":
            actions.extend([
                "Check database query performance",
                "Review agent communication patterns",
                "Verify network latency to brokers",
                "Scale processing resources if needed"
            ])
        elif metric_name == "trade_execution_success_rate":
            actions.extend([
                "Check broker API connectivity",
                "Review order validation logic",
                "Verify account balance and margin",
                "Investigate execution engine errors"
            ])
        elif metric_name == "system_uptime":
            actions.extend([
                "Check system resource utilization",
                "Review application logs for errors",
                "Verify infrastructure health",
                "Check for memory leaks or crashes"
            ])
        
        if severity in [RegressionSeverity.CRITICAL, RegressionSeverity.SEVERE]:
            actions.extend([
                "Escalate to on-call engineer immediately",
                "Consider activating circuit breakers",
                "Prepare for potential rollback"
            ])
        
        return actions
    
    def identify_affected_components(self, metric_name: str) -> List[str]:
        """Identify components affected by the regression"""
        component_map = {
            "signal_execution_latency": ["signal-processor", "execution-engine", "database"],
            "trade_execution_success_rate": ["execution-engine", "broker-api", "compliance"],
            "system_uptime": ["all-components"],
            "database_query_latency": ["database", "data-access-layer"],
            "agent_communication_latency": ["message-queue", "agent-network"]
        }
        
        return component_map.get(metric_name, ["unknown"])
    
    def generate_alert_id(self, metric_name: str) -> str:
        """Generate unique alert ID"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return f"PERF_REG_{metric_name.upper()}_{timestamp}"
    
    async def fetch_metric_data(self, query: str, start_time: datetime, 
                              end_time: datetime, step: str = "1m") -> List[Tuple[float, str]]:
        """Fetch metric data from Prometheus"""
        url = f"{self.prometheus_url}/api/v1/query_range"
        params = {
            "query": query,
            "start": start_time.timestamp(),
            "end": end_time.timestamp(),
            "step": step
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data["data"]["result"]:
                            return data["data"]["result"][0]["values"]
                    return []
        except Exception as e:
            logger.error(f"Failed to fetch metric data: {e}")
            return []
    
    async def send_regression_alert(self, alert: RegressionAlert) -> None:
        """Send regression alert to monitoring systems"""
        alert_data = {
            "alert_id": alert.alert_id,
            "metric": alert.metric_name,
            "severity": alert.severity.value,
            "current_value": alert.current_value,
            "baseline_value": alert.baseline_value,
            "deviation_percentage": alert.deviation_percentage,
            "confidence": alert.confidence_score,
            "timestamp": alert.detection_time.isoformat(),
            "suggested_actions": alert.suggested_actions
        }
        
        # Send to AlertManager
        await self.send_to_alertmanager(alert_data)
        
        # Log alert
        logger.warning(f"Performance regression detected: {alert.metric_name} "
                      f"degraded by {alert.deviation_percentage:.1f}% "
                      f"(severity: {alert.severity.value})")
    
    async def send_to_alertmanager(self, alert_data: Dict) -> None:
        """Send alert to AlertManager"""
        url = "http://localhost:9093/api/v1/alerts"
        
        alert_payload = [{
            "labels": {
                "alertname": "PerformanceRegression",
                "severity": alert_data["severity"],
                "metric": alert_data["metric"],
                "component": "performance_regression_detector"
            },
            "annotations": {
                "summary": f"Performance regression detected in {alert_data['metric']}",
                "description": f"Metric {alert_data['metric']} degraded by {alert_data['deviation_percentage']:.1f}%",
                "current_value": str(alert_data["current_value"]),
                "baseline_value": str(alert_data["baseline_value"]),
                "confidence": str(alert_data["confidence"]),
                "suggested_actions": ", ".join(alert_data["suggested_actions"])
            },
            "startsAt": alert_data["timestamp"]
        }]
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=alert_payload) as response:
                    if response.status == 200:
                        logger.info(f"Alert sent to AlertManager: {alert_data['alert_id']}")
                    else:
                        logger.error(f"Failed to send alert to AlertManager: {response.status}")
        except Exception as e:
            logger.error(f"Error sending alert to AlertManager: {e}")


async def main():
    """Main function to run regression detection"""
    detector = PerformanceRegressionDetector()
    
    # Initialize baselines
    await detector.initialize_baselines()
    
    # Run detection loop
    while True:
        try:
            alerts = await detector.detect_regressions()
            
            for alert in alerts:
                await detector.send_regression_alert(alert)
            
            if alerts:
                logger.info(f"Detected {len(alerts)} performance regressions")
            
            # Wait before next detection cycle
            await asyncio.sleep(300)  # Check every 5 minutes
            
        except Exception as e:
            logger.error(f"Error in regression detection loop: {e}")
            await asyncio.sleep(60)  # Wait 1 minute before retry


if __name__ == "__main__":
    asyncio.run(main())