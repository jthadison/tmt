"""
Performance Alert System

Implements comprehensive alert system for performance tracking including:
- Confidence interval breach alerts
- Rolling Sharpe ratio monitoring
- Real-time performance deviation alerts
- Emergency escalation procedures
"""

import asyncio
import logging
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path

from .performance_tracking import PerformanceAlert, AlertSeverity, PerformanceMetrics
from .monte_carlo_projections import get_monte_carlo_engine

logger = logging.getLogger(__name__)


class AlertChannel(Enum):
    """Alert delivery channels"""
    EMAIL = "email"
    SMS = "sms"
    DASHBOARD = "dashboard"
    WEBHOOK = "webhook"
    SLACK = "slack"
    TERMINAL_BELL = "terminal_bell"


class AlertRule(Enum):
    """Pre-defined alert rule types"""
    CONFIDENCE_BREACH = "confidence_breach"
    SHARPE_DEGRADATION = "sharpe_degradation"
    DRAWDOWN_LIMIT = "drawdown_limit"
    PNL_DEVIATION = "pnl_deviation"
    VOLATILITY_SPIKE = "volatility_spike"
    PROJECTION_FAILURE = "projection_failure"


@dataclass
class AlertRule_Config:
    """Configuration for alert rules"""
    rule_type: AlertRule
    severity: AlertSeverity
    threshold: float
    evaluation_window: int  # Number of periods to evaluate
    channels: List[AlertChannel]
    escalation_delay_minutes: int = 15
    suppress_similar_alerts_minutes: int = 60
    require_acknowledgment: bool = False
    custom_message_template: Optional[str] = None


@dataclass
class AlertSubscription:
    """Alert subscription configuration"""
    subscriber_id: str
    subscriber_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    webhook_url: Optional[str] = None
    slack_channel: Optional[str] = None
    severity_filter: List[AlertSeverity] = field(default_factory=lambda: [AlertSeverity.CRITICAL, AlertSeverity.WARNING])
    rule_filter: List[AlertRule] = field(default_factory=list)
    active_hours: Optional[Tuple[int, int]] = None  # (start_hour, end_hour) in UTC
    enabled: bool = True


@dataclass
class AlertDelivery:
    """Alert delivery record"""
    alert_id: str
    subscriber_id: str
    channel: AlertChannel
    delivery_timestamp: datetime
    delivery_status: str  # "sent", "failed", "pending"
    acknowledgment_timestamp: Optional[datetime] = None
    error_message: Optional[str] = None


class SharpeRatioMonitor:
    """
    Rolling Sharpe ratio monitoring system

    Tracks Sharpe ratio degradation and alerts on significant changes
    """

    def __init__(self, window_days: int = 30):
        self.window_days = window_days
        self.sharpe_history: List[Tuple[datetime, float]] = []
        self.alert_thresholds = {
            "degradation_warning": -0.3,    # 30% degradation
            "degradation_critical": -0.5,   # 50% degradation
            "absolute_warning": 0.8,        # Sharpe below 0.8
            "absolute_critical": 0.5        # Sharpe below 0.5
        }

    async def update_sharpe_ratio(self, timestamp: datetime, sharpe_ratio: float) -> List[PerformanceAlert]:
        """Update Sharpe ratio and check for alerts"""
        try:
            # Add new reading
            self.sharpe_history.append((timestamp, sharpe_ratio))

            # Remove old readings outside window
            cutoff_date = timestamp - timedelta(days=self.window_days)
            self.sharpe_history = [
                (ts, sr) for ts, sr in self.sharpe_history
                if ts >= cutoff_date
            ]

            # Generate alerts
            alerts = []

            # Check absolute thresholds
            if sharpe_ratio < self.alert_thresholds["absolute_critical"]:
                alerts.append(self._create_sharpe_alert(
                    AlertSeverity.CRITICAL,
                    f"Sharpe ratio {sharpe_ratio:.2f} below critical threshold",
                    sharpe_ratio,
                    timestamp
                ))
            elif sharpe_ratio < self.alert_thresholds["absolute_warning"]:
                alerts.append(self._create_sharpe_alert(
                    AlertSeverity.WARNING,
                    f"Sharpe ratio {sharpe_ratio:.2f} below warning threshold",
                    sharpe_ratio,
                    timestamp
                ))

            # Check for degradation trends
            if len(self.sharpe_history) >= 7:  # Need at least a week of data
                recent_avg = sum(sr for _, sr in self.sharpe_history[-7:]) / 7
                older_avg = sum(sr for _, sr in self.sharpe_history[-14:-7]) / 7 if len(self.sharpe_history) >= 14 else recent_avg

                if older_avg > 0:
                    degradation_pct = (recent_avg - older_avg) / older_avg

                    if degradation_pct < self.alert_thresholds["degradation_critical"]:
                        alerts.append(self._create_sharpe_alert(
                            AlertSeverity.CRITICAL,
                            f"Sharpe ratio degradation {degradation_pct:.1%} over past week",
                            degradation_pct,
                            timestamp
                        ))
                    elif degradation_pct < self.alert_thresholds["degradation_warning"]:
                        alerts.append(self._create_sharpe_alert(
                            AlertSeverity.WARNING,
                            f"Sharpe ratio degradation {degradation_pct:.1%} over past week",
                            degradation_pct,
                            timestamp
                        ))

            return alerts

        except Exception as e:
            logger.error(f"Error updating Sharpe ratio: {e}")
            return []

    def _create_sharpe_alert(
        self,
        severity: AlertSeverity,
        message: str,
        value: float,
        timestamp: datetime
    ) -> PerformanceAlert:
        """Create Sharpe ratio alert"""
        alert_id = f"sharpe_{severity.value}_{timestamp.strftime('%Y%m%d_%H%M%S')}"

        return PerformanceAlert(
            alert_id=alert_id,
            timestamp=timestamp,
            severity=severity,
            alert_type="Rolling Sharpe Ratio",
            message=message,
            current_value=value,
            expected_value=1.0,  # Target Sharpe ratio
            deviation_pct=((value - 1.0) / 1.0) * 100 if value != 0 else -100,
            details={
                "window_days": self.window_days,
                "historical_count": len(self.sharpe_history),
                "alert_rule": AlertRule.SHARPE_DEGRADATION.value
            },
            action_required=severity == AlertSeverity.CRITICAL
        )

    def get_sharpe_trend_analysis(self) -> Dict:
        """Get comprehensive Sharpe ratio trend analysis"""
        try:
            if len(self.sharpe_history) < 2:
                return {"error": "Insufficient data for trend analysis"}

            # Calculate various statistics
            current_sharpe = self.sharpe_history[-1][1]
            all_sharpe_values = [sr for _, sr in self.sharpe_history]

            mean_sharpe = sum(all_sharpe_values) / len(all_sharpe_values)
            min_sharpe = min(all_sharpe_values)
            max_sharpe = max(all_sharpe_values)

            # Calculate trend (simple linear)
            if len(self.sharpe_history) >= 5:
                recent_values = all_sharpe_values[-5:]
                trend_direction = "IMPROVING" if recent_values[-1] > recent_values[0] else "DEGRADING"
            else:
                trend_direction = "INSUFFICIENT_DATA"

            return {
                "current_sharpe_ratio": current_sharpe,
                "window_statistics": {
                    "mean": mean_sharpe,
                    "min": min_sharpe,
                    "max": max_sharpe,
                    "data_points": len(all_sharpe_values)
                },
                "trend_analysis": {
                    "direction": trend_direction,
                    "volatility": max_sharpe - min_sharpe
                },
                "alert_levels": self.alert_thresholds
            }

        except Exception as e:
            logger.error(f"Error in Sharpe trend analysis: {e}")
            return {"error": str(e)}


class ConfidenceIntervalBreachMonitor:
    """
    Monitors confidence interval breaches and tracks breach patterns
    """

    def __init__(self):
        self.breach_history: List[Tuple[datetime, str, float, float, float]] = []  # timestamp, level, actual, lower, upper
        self.consecutive_breaches = 0
        self.breach_thresholds = {
            "consecutive_warning": 3,
            "consecutive_critical": 5,
            "breach_rate_warning": 0.15,    # 15% breach rate over window
            "breach_rate_critical": 0.25    # 25% breach rate over window
        }

    async def check_confidence_breach(
        self,
        timestamp: datetime,
        actual_value: float,
        confidence_intervals: Dict[str, Tuple[float, float]]
    ) -> List[PerformanceAlert]:
        """Check for confidence interval breaches and generate alerts"""
        try:
            alerts = []
            breach_detected = False

            # Check each confidence level
            for level, (lower, upper) in confidence_intervals.items():
                if actual_value < lower or actual_value > upper:
                    # Record breach
                    self.breach_history.append((timestamp, level, actual_value, lower, upper))
                    breach_detected = True

                    # Create immediate breach alert
                    alerts.append(self._create_breach_alert(
                        AlertSeverity.WARNING,
                        f"Confidence interval breach ({level})",
                        actual_value, lower, upper, level, timestamp
                    ))

            # Update consecutive breach counter
            if breach_detected:
                self.consecutive_breaches += 1
            else:
                self.consecutive_breaches = 0

            # Check for consecutive breach alerts
            if self.consecutive_breaches >= self.breach_thresholds["consecutive_critical"]:
                alerts.append(self._create_consecutive_breach_alert(
                    AlertSeverity.CRITICAL, self.consecutive_breaches, timestamp
                ))
            elif self.consecutive_breaches >= self.breach_thresholds["consecutive_warning"]:
                alerts.append(self._create_consecutive_breach_alert(
                    AlertSeverity.WARNING, self.consecutive_breaches, timestamp
                ))

            # Check breach rate over last 30 days
            breach_rate_alert = await self._check_breach_rate(timestamp)
            if breach_rate_alert:
                alerts.append(breach_rate_alert)

            return alerts

        except Exception as e:
            logger.error(f"Error checking confidence breach: {e}")
            return []

    def _create_breach_alert(
        self,
        severity: AlertSeverity,
        message: str,
        actual: float,
        lower: float,
        upper: float,
        level: str,
        timestamp: datetime
    ) -> PerformanceAlert:
        """Create confidence breach alert"""
        alert_id = f"confidence_breach_{level}_{timestamp.strftime('%Y%m%d_%H%M%S')}"

        return PerformanceAlert(
            alert_id=alert_id,
            timestamp=timestamp,
            severity=severity,
            alert_type="Confidence Interval Breach",
            message=message,
            current_value=actual,
            expected_value=f"[{lower:.2f}, {upper:.2f}]",
            deviation_pct=max(
                ((actual - upper) / upper) * 100 if actual > upper else 0,
                ((lower - actual) / abs(lower)) * 100 if actual < lower else 0
            ),
            details={
                "confidence_level": level,
                "interval_lower": lower,
                "interval_upper": upper,
                "consecutive_breaches": self.consecutive_breaches,
                "alert_rule": AlertRule.CONFIDENCE_BREACH.value
            }
        )

    def _create_consecutive_breach_alert(
        self,
        severity: AlertSeverity,
        consecutive_count: int,
        timestamp: datetime
    ) -> PerformanceAlert:
        """Create consecutive breach alert"""
        alert_id = f"consecutive_breach_{severity.value}_{timestamp.strftime('%Y%m%d_%H%M%S')}"

        return PerformanceAlert(
            alert_id=alert_id,
            timestamp=timestamp,
            severity=severity,
            alert_type="Consecutive Confidence Breaches",
            message=f"{consecutive_count} consecutive confidence interval breaches detected",
            current_value=consecutive_count,
            expected_value="<3",
            deviation_pct=((consecutive_count - 2) / 2) * 100,
            details={
                "consecutive_count": consecutive_count,
                "threshold_warning": self.breach_thresholds["consecutive_warning"],
                "threshold_critical": self.breach_thresholds["consecutive_critical"],
                "alert_rule": AlertRule.CONFIDENCE_BREACH.value
            },
            action_required=severity == AlertSeverity.CRITICAL
        )

    async def _check_breach_rate(self, timestamp: datetime) -> Optional[PerformanceAlert]:
        """Check breach rate over last 30 days"""
        try:
            cutoff_date = timestamp - timedelta(days=30)
            recent_breaches = [b for b in self.breach_history if b[0] >= cutoff_date]

            if len(recent_breaches) == 0:
                return None

            # Calculate breach rate (assuming daily observations)
            days_in_period = min(30, (timestamp - min(b[0] for b in recent_breaches)).days + 1)
            breach_rate = len(recent_breaches) / days_in_period

            if breach_rate >= self.breach_thresholds["breach_rate_critical"]:
                return self._create_breach_rate_alert(
                    AlertSeverity.CRITICAL, breach_rate, timestamp
                )
            elif breach_rate >= self.breach_thresholds["breach_rate_warning"]:
                return self._create_breach_rate_alert(
                    AlertSeverity.WARNING, breach_rate, timestamp
                )

            return None

        except Exception as e:
            logger.error(f"Error checking breach rate: {e}")
            return None

    def _create_breach_rate_alert(
        self,
        severity: AlertSeverity,
        breach_rate: float,
        timestamp: datetime
    ) -> PerformanceAlert:
        """Create breach rate alert"""
        alert_id = f"breach_rate_{severity.value}_{timestamp.strftime('%Y%m%d_%H%M%S')}"

        return PerformanceAlert(
            alert_id=alert_id,
            timestamp=timestamp,
            severity=severity,
            alert_type="High Confidence Breach Rate",
            message=f"Confidence breach rate {breach_rate:.1%} over last 30 days",
            current_value=breach_rate,
            expected_value="<10%",
            deviation_pct=((breach_rate - 0.1) / 0.1) * 100,
            details={
                "breach_rate_30_days": breach_rate,
                "threshold_warning": self.breach_thresholds["breach_rate_warning"],
                "threshold_critical": self.breach_thresholds["breach_rate_critical"],
                "alert_rule": AlertRule.CONFIDENCE_BREACH.value
            },
            action_required=severity == AlertSeverity.CRITICAL
        )


class PerformanceAlertSystem:
    """
    Comprehensive performance alert system integrating all monitoring components
    """

    def __init__(self):
        self.sharpe_monitor = SharpeRatioMonitor(window_days=30)
        self.confidence_monitor = ConfidenceIntervalBreachMonitor()
        self.monte_carlo = get_monte_carlo_engine()

        # Alert configuration
        self.alert_rules: List[AlertRule_Config] = self._initialize_alert_rules()
        self.subscribers: List[AlertSubscription] = []
        self.delivery_history: List[AlertDelivery] = []
        self.suppressed_alerts: Dict[str, datetime] = {}

        # Storage
        self.alerts_dir = Path("performance_alerts")
        self.alerts_dir.mkdir(exist_ok=True)

        logger.info("Performance Alert System initialized")

    def _initialize_alert_rules(self) -> List[AlertRule_Config]:
        """Initialize default alert rules"""
        return [
            AlertRule_Config(
                rule_type=AlertRule.CONFIDENCE_BREACH,
                severity=AlertSeverity.WARNING,
                threshold=3.0,  # 3 consecutive breaches
                evaluation_window=5,
                channels=[AlertChannel.DASHBOARD, AlertChannel.TERMINAL_BELL],
                escalation_delay_minutes=15,
                suppress_similar_alerts_minutes=60
            ),
            AlertRule_Config(
                rule_type=AlertRule.CONFIDENCE_BREACH,
                severity=AlertSeverity.CRITICAL,
                threshold=5.0,  # 5 consecutive breaches
                evaluation_window=10,
                channels=[AlertChannel.DASHBOARD, AlertChannel.EMAIL, AlertChannel.TERMINAL_BELL],
                escalation_delay_minutes=5,
                require_acknowledgment=True
            ),
            AlertRule_Config(
                rule_type=AlertRule.SHARPE_DEGRADATION,
                severity=AlertSeverity.WARNING,
                threshold=0.8,  # Sharpe below 0.8
                evaluation_window=7,
                channels=[AlertChannel.DASHBOARD],
                suppress_similar_alerts_minutes=120
            ),
            AlertRule_Config(
                rule_type=AlertRule.SHARPE_DEGRADATION,
                severity=AlertSeverity.CRITICAL,
                threshold=0.5,  # Sharpe below 0.5
                evaluation_window=5,
                channels=[AlertChannel.DASHBOARD, AlertChannel.EMAIL, AlertChannel.TERMINAL_BELL],
                require_acknowledgment=True
            ),
            AlertRule_Config(
                rule_type=AlertRule.DRAWDOWN_LIMIT,
                severity=AlertSeverity.WARNING,
                threshold=0.08,  # 8% drawdown
                evaluation_window=1,
                channels=[AlertChannel.DASHBOARD, AlertChannel.TERMINAL_BELL]
            ),
            AlertRule_Config(
                rule_type=AlertRule.DRAWDOWN_LIMIT,
                severity=AlertSeverity.CRITICAL,
                threshold=0.12,  # 12% drawdown
                evaluation_window=1,
                channels=[AlertChannel.DASHBOARD, AlertChannel.EMAIL, AlertChannel.TERMINAL_BELL],
                require_acknowledgment=True
            ),
            AlertRule_Config(
                rule_type=AlertRule.PNL_DEVIATION,
                severity=AlertSeverity.WARNING,
                threshold=0.25,  # 25% deviation from projection
                evaluation_window=1,
                channels=[AlertChannel.DASHBOARD]
            ),
            AlertRule_Config(
                rule_type=AlertRule.PNL_DEVIATION,
                severity=AlertSeverity.CRITICAL,
                threshold=0.50,  # 50% deviation from projection
                evaluation_window=1,
                channels=[AlertChannel.DASHBOARD, AlertChannel.EMAIL, AlertChannel.TERMINAL_BELL],
                require_acknowledgment=True
            )
        ]

    async def evaluate_performance_alerts(
        self,
        metrics: PerformanceMetrics,
        monte_carlo_confidence_intervals: Optional[Dict] = None
    ) -> List[PerformanceAlert]:
        """
        Evaluate all alert conditions and generate alerts

        Args:
            metrics: Current performance metrics
            monte_carlo_confidence_intervals: Confidence intervals from Monte Carlo simulation

        Returns:
            List of generated alerts
        """
        try:
            all_alerts = []

            # Update Sharpe ratio monitoring
            sharpe_alerts = await self.sharpe_monitor.update_sharpe_ratio(
                metrics.timestamp, metrics.rolling_sharpe_ratio
            )
            all_alerts.extend(sharpe_alerts)

            # Check confidence interval breaches if available
            if monte_carlo_confidence_intervals:
                confidence_alerts = await self.confidence_monitor.check_confidence_breach(
                    metrics.timestamp, metrics.actual_pnl, monte_carlo_confidence_intervals
                )
                all_alerts.extend(confidence_alerts)

            # Check drawdown alerts
            drawdown_alerts = self._check_drawdown_alerts(metrics)
            all_alerts.extend(drawdown_alerts)

            # Check P&L deviation alerts
            pnl_deviation_alerts = self._check_pnl_deviation_alerts(metrics)
            all_alerts.extend(pnl_deviation_alerts)

            # Filter suppressed alerts
            filtered_alerts = self._filter_suppressed_alerts(all_alerts)

            # Log alert summary
            if filtered_alerts:
                critical_count = len([a for a in filtered_alerts if a.severity == AlertSeverity.CRITICAL])
                warning_count = len([a for a in filtered_alerts if a.severity == AlertSeverity.WARNING])
                logger.warning(f"Generated {len(filtered_alerts)} alerts: {critical_count} critical, {warning_count} warning")

            return filtered_alerts

        except Exception as e:
            logger.error(f"Error evaluating performance alerts: {e}")
            return []

    def _check_drawdown_alerts(self, metrics: PerformanceMetrics) -> List[PerformanceAlert]:
        """Check for drawdown-related alerts"""
        alerts = []

        try:
            if metrics.drawdown_current >= 0.12:
                alerts.append(self._create_standard_alert(
                    AlertSeverity.CRITICAL,
                    "Drawdown - Critical",
                    f"Current drawdown {metrics.drawdown_current:.1%} exceeds critical threshold",
                    metrics.drawdown_current,
                    0.12,
                    metrics.timestamp,
                    {"max_drawdown": metrics.drawdown_max, "alert_rule": AlertRule.DRAWDOWN_LIMIT.value}
                ))
            elif metrics.drawdown_current >= 0.08:
                alerts.append(self._create_standard_alert(
                    AlertSeverity.WARNING,
                    "Drawdown - Warning",
                    f"Current drawdown {metrics.drawdown_current:.1%} exceeds warning threshold",
                    metrics.drawdown_current,
                    0.08,
                    metrics.timestamp,
                    {"max_drawdown": metrics.drawdown_max, "alert_rule": AlertRule.DRAWDOWN_LIMIT.value}
                ))

        except Exception as e:
            logger.error(f"Error checking drawdown alerts: {e}")

        return alerts

    def _check_pnl_deviation_alerts(self, metrics: PerformanceMetrics) -> List[PerformanceAlert]:
        """Check for P&L deviation alerts"""
        alerts = []

        try:
            deviation_pct = abs(metrics.pnl_deviation_pct)

            if deviation_pct >= 50.0:
                alerts.append(self._create_standard_alert(
                    AlertSeverity.CRITICAL,
                    "P&L Deviation - Critical",
                    f"P&L deviation {deviation_pct:.1f}% exceeds critical threshold",
                    deviation_pct,
                    50.0,
                    metrics.timestamp,
                    {
                        "actual_pnl": metrics.actual_pnl,
                        "projected_pnl": metrics.projected_pnl,
                        "alert_rule": AlertRule.PNL_DEVIATION.value
                    }
                ))
            elif deviation_pct >= 25.0:
                alerts.append(self._create_standard_alert(
                    AlertSeverity.WARNING,
                    "P&L Deviation - Warning",
                    f"P&L deviation {deviation_pct:.1f}% exceeds warning threshold",
                    deviation_pct,
                    25.0,
                    metrics.timestamp,
                    {
                        "actual_pnl": metrics.actual_pnl,
                        "projected_pnl": metrics.projected_pnl,
                        "alert_rule": AlertRule.PNL_DEVIATION.value
                    }
                ))

        except Exception as e:
            logger.error(f"Error checking P&L deviation alerts: {e}")

        return alerts

    def _create_standard_alert(
        self,
        severity: AlertSeverity,
        alert_type: str,
        message: str,
        current_value: float,
        expected_value: float,
        timestamp: datetime,
        details: Dict
    ) -> PerformanceAlert:
        """Create standard alert"""
        alert_id = f"{alert_type.lower().replace(' ', '_')}_{severity.value}_{timestamp.strftime('%Y%m%d_%H%M%S')}"

        deviation_pct = 0.0
        if expected_value != 0:
            deviation_pct = ((current_value - expected_value) / expected_value) * 100

        return PerformanceAlert(
            alert_id=alert_id,
            timestamp=timestamp,
            severity=severity,
            alert_type=alert_type,
            message=message,
            current_value=current_value,
            expected_value=expected_value,
            deviation_pct=deviation_pct,
            details=details,
            action_required=severity == AlertSeverity.CRITICAL
        )

    def _filter_suppressed_alerts(self, alerts: List[PerformanceAlert]) -> List[PerformanceAlert]:
        """Filter out suppressed alerts based on suppression rules"""
        try:
            filtered_alerts = []
            current_time = datetime.utcnow()

            for alert in alerts:
                # Create suppression key
                suppression_key = f"{alert.alert_type}_{alert.severity.value}"

                # Check if alert is suppressed
                if suppression_key in self.suppressed_alerts:
                    suppression_time = self.suppressed_alerts[suppression_key]

                    # Find matching rule for suppression period
                    suppression_minutes = 60  # Default
                    for rule in self.alert_rules:
                        if (rule.rule_type.value in alert.details.get("alert_rule", "") and
                            rule.severity == alert.severity):
                            suppression_minutes = rule.suppress_similar_alerts_minutes
                            break

                    if current_time < suppression_time + timedelta(minutes=suppression_minutes):
                        logger.debug(f"Suppressing alert: {suppression_key}")
                        continue

                # Add alert to filtered list and update suppression
                filtered_alerts.append(alert)
                self.suppressed_alerts[suppression_key] = current_time

            return filtered_alerts

        except Exception as e:
            logger.error(f"Error filtering suppressed alerts: {e}")
            return alerts

    async def save_alerts(self, alerts: List[PerformanceAlert]):
        """Save alerts to persistent storage"""
        try:
            if not alerts:
                return

            timestamp = alerts[0].timestamp.strftime("%Y%m%d_%H%M%S")
            filename = f"alerts_{timestamp}.json"
            filepath = self.alerts_dir / filename

            alerts_data = []
            for alert in alerts:
                alert_data = {
                    "alert_id": alert.alert_id,
                    "timestamp": alert.timestamp.isoformat(),
                    "severity": alert.severity.value,
                    "alert_type": alert.alert_type,
                    "message": alert.message,
                    "current_value": alert.current_value,
                    "expected_value": alert.expected_value,
                    "deviation_pct": alert.deviation_pct,
                    "details": alert.details,
                    "action_required": alert.action_required
                }
                alerts_data.append(alert_data)

            with open(filepath, 'w') as f:
                json.dump(alerts_data, f, indent=2)

            logger.info(f"Saved {len(alerts)} alerts to {filepath}")

        except Exception as e:
            logger.error(f"Error saving alerts: {e}")

    def add_subscriber(self, subscription: AlertSubscription):
        """Add alert subscriber"""
        self.subscribers.append(subscription)
        logger.info(f"Added alert subscriber: {subscription.subscriber_name}")

    def get_alert_summary(self, hours: int = 24) -> Dict:
        """Get alert summary for last N hours"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)

            # This would typically read from persistent storage
            # For now, return a summary based on current state
            return {
                "period_hours": hours,
                "total_alerts": 0,  # Would count from storage
                "critical_alerts": 0,
                "warning_alerts": 0,
                "breach_rate": {
                    "consecutive_breaches": self.confidence_monitor.consecutive_breaches,
                    "recent_breach_count": len([
                        b for b in self.confidence_monitor.breach_history
                        if b[0] >= cutoff_time
                    ])
                },
                "sharpe_status": self.sharpe_monitor.get_sharpe_trend_analysis(),
                "active_suppressions": len(self.suppressed_alerts)
            }

        except Exception as e:
            logger.error(f"Error getting alert summary: {e}")
            return {"error": str(e)}


# Global instance
_alert_system: Optional[PerformanceAlertSystem] = None


def get_alert_system() -> PerformanceAlertSystem:
    """Get global performance alert system instance"""
    global _alert_system
    if _alert_system is None:
        _alert_system = PerformanceAlertSystem()
    return _alert_system