"""
Advanced Risk Alerting and Notification System.

Provides intelligent risk scoring, threshold-based alerting, escalation
management, and multi-channel notification capabilities.
"""

import asyncio
import json
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Set, Callable, Any
from uuid import UUID, uuid4

from ..core.models import (
    RiskAlert,
    RiskMetrics,
    AlertSeverity,
    RiskLevel,
    Position
)


class AlertChannel(str, Enum):
    """Alert notification channels."""
    EMAIL = "email"
    SMS = "sms" 
    SLACK = "slack"
    WEBHOOK = "webhook"
    DASHBOARD = "dashboard"
    API = "api"


class AlertCondition(str, Enum):
    """Alert trigger conditions."""
    THRESHOLD_EXCEEDED = "threshold_exceeded"
    TREND_DETECTED = "trend_detected"
    ANOMALY_DETECTED = "anomaly_detected"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    CORRELATION_SPIKE = "correlation_spike"
    VOLATILITY_SPIKE = "volatility_spike"


class EscalationLevel(str, Enum):
    """Alert escalation levels."""
    L1_MONITORING = "l1_monitoring"
    L2_ANALYST = "l2_analyst"
    L3_MANAGER = "l3_manager"
    L4_EXECUTIVE = "l4_executive"


class RiskAlertManager:
    """
    Comprehensive risk alerting system with intelligent scoring,
    threshold management, and multi-channel notifications.
    """
    
    def __init__(self):
        # Alert configuration
        self.alert_rules: Dict[str, Dict] = {}
        self.alert_thresholds: Dict[str, Dict[str, float]] = {}
        self.notification_channels: Dict[AlertChannel, Callable] = {}
        
        # Alert state management
        self.active_alerts: Dict[str, RiskAlert] = {}
        self.alert_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.alert_cooldowns: Dict[str, datetime] = {}
        self.escalation_timers: Dict[str, datetime] = {}
        
        # Performance tracking
        self.alert_processing_times: List[float] = []
        self.alerts_processed = 0
        self.false_positive_rate = 0.0
        
        # Advanced features
        self.ml_risk_model = None  # Placeholder for ML model
        self.risk_score_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=500))
        self.anomaly_detection_enabled = True
        
        # Default alert rules
        self._setup_default_alert_rules()
    
    def _setup_default_alert_rules(self):
        """Setup default alert rules and thresholds."""
        
        # Risk score thresholds
        self.alert_thresholds['risk_score'] = {
            'warning': 70.0,
            'critical': 85.0,
            'emergency': 95.0
        }
        
        # Position size thresholds
        self.alert_thresholds['position_size'] = {
            'warning': 50000.0,
            'critical': 100000.0,
            'emergency': 200000.0
        }
        
        # P&L thresholds
        self.alert_thresholds['daily_pl'] = {
            'warning': -500.0,
            'critical': -1000.0,
            'emergency': -2000.0
        }
        
        # Leverage thresholds
        self.alert_thresholds['leverage'] = {
            'warning': 20.0,
            'critical': 25.0,
            'emergency': 30.0
        }
        
        # Drawdown thresholds
        self.alert_thresholds['drawdown'] = {
            'warning': 0.05,  # 5%
            'critical': 0.10,  # 10%
            'emergency': 0.15  # 15%
        }
        
        # VaR thresholds
        self.alert_thresholds['var'] = {
            'warning': 1000.0,
            'critical': 2000.0,
            'emergency': 3000.0
        }
    
    async def process_risk_metrics(
        self, 
        account_id: str, 
        risk_metrics: RiskMetrics,
        positions: List[Position]
    ) -> List[RiskAlert]:
        """Process risk metrics and generate alerts."""
        start_time = time.perf_counter()
        
        alerts_generated = []
        
        try:
            # Update risk score history
            self._update_risk_score_history(account_id, risk_metrics.risk_score)
            
            # Check threshold-based alerts
            threshold_alerts = await self._check_threshold_alerts(account_id, risk_metrics)
            alerts_generated.extend(threshold_alerts)
            
            # Check trend-based alerts
            trend_alerts = await self._check_trend_alerts(account_id, risk_metrics)
            alerts_generated.extend(trend_alerts)
            
            # Check anomaly detection alerts
            if self.anomaly_detection_enabled:
                anomaly_alerts = await self._check_anomaly_alerts(account_id, risk_metrics)
                alerts_generated.extend(anomaly_alerts)
            
            # Check position-specific alerts
            position_alerts = await self._check_position_alerts(account_id, positions)
            alerts_generated.extend(position_alerts)
            
            # Check correlation alerts
            correlation_alerts = await self._check_correlation_alerts(account_id, risk_metrics, positions)
            alerts_generated.extend(correlation_alerts)
            
            # Process new alerts
            for alert in alerts_generated:
                await self._process_new_alert(alert)
            
            # Check existing alerts for escalation
            await self._check_alert_escalations(account_id)
            
            # Performance tracking
            processing_time = (time.perf_counter() - start_time) * 1000
            self.alert_processing_times.append(processing_time)
            self.alerts_processed += 1
            
            # Keep only last 1000 measurements
            if len(self.alert_processing_times) > 1000:
                self.alert_processing_times = self.alert_processing_times[-1000:]
            
            return alerts_generated
            
        except Exception as e:
            # Generate error alert
            error_alert = RiskAlert(
                account_id=account_id,
                alert_type="system_error",
                severity=AlertSeverity.ERROR,
                title="Alert Processing Error",
                message=f"Error processing risk alerts: {str(e)}",
                risk_score=100.0,
                risk_level=RiskLevel.CRITICAL
            )
            return [error_alert]
    
    async def _check_threshold_alerts(
        self, 
        account_id: str, 
        risk_metrics: RiskMetrics
    ) -> List[RiskAlert]:
        """Check for threshold-based alerts."""
        alerts = []
        
        # Risk score alerts
        risk_score = risk_metrics.risk_score
        if risk_score >= self.alert_thresholds['risk_score']['emergency']:
            alerts.append(self._create_alert(
                account_id, "risk_score_emergency", AlertSeverity.CRITICAL,
                f"Emergency risk score: {risk_score:.1f}%",
                f"Account risk score has reached emergency level ({risk_score:.1f}%). Immediate action required.",
                {"risk_score": risk_score, "threshold": self.alert_thresholds['risk_score']['emergency']},
                risk_score, risk_metrics.risk_level
            ))
        
        elif risk_score >= self.alert_thresholds['risk_score']['critical']:
            alerts.append(self._create_alert(
                account_id, "risk_score_critical", AlertSeverity.ERROR,
                f"Critical risk score: {risk_score:.1f}%",
                f"Account risk score is critically high ({risk_score:.1f}%). Review positions immediately.",
                {"risk_score": risk_score, "threshold": self.alert_thresholds['risk_score']['critical']},
                risk_score, risk_metrics.risk_level
            ))
        
        elif risk_score >= self.alert_thresholds['risk_score']['warning']:
            alerts.append(self._create_alert(
                account_id, "risk_score_warning", AlertSeverity.WARNING,
                f"High risk score: {risk_score:.1f}%",
                f"Account risk score is elevated ({risk_score:.1f}%). Monitor closely.",
                {"risk_score": risk_score, "threshold": self.alert_thresholds['risk_score']['warning']},
                risk_score, risk_metrics.risk_level
            ))
        
        # Leverage alerts
        leverage = float(risk_metrics.current_leverage)
        if leverage >= self.alert_thresholds['leverage']['emergency']:
            alerts.append(self._create_alert(
                account_id, "leverage_emergency", AlertSeverity.CRITICAL,
                f"Emergency leverage: {leverage:.1f}x",
                f"Account leverage is at emergency level ({leverage:.1f}x). Reduce positions immediately.",
                {"leverage": leverage, "threshold": self.alert_thresholds['leverage']['emergency']},
                risk_score, risk_metrics.risk_level
            ))
        
        # Daily P&L alerts
        daily_pl = float(risk_metrics.daily_pl)
        if daily_pl <= self.alert_thresholds['daily_pl']['emergency']:
            alerts.append(self._create_alert(
                account_id, "daily_loss_emergency", AlertSeverity.CRITICAL,
                f"Emergency daily loss: ${daily_pl:,.2f}",
                f"Daily loss has reached emergency threshold (${daily_pl:,.2f}). Consider kill switch activation.",
                {"daily_pl": daily_pl, "threshold": self.alert_thresholds['daily_pl']['emergency']},
                risk_score, risk_metrics.risk_level
            ))
        
        # VaR alerts
        var_95 = float(risk_metrics.var_95)
        if var_95 >= self.alert_thresholds['var']['critical']:
            alerts.append(self._create_alert(
                account_id, "var_critical", AlertSeverity.ERROR,
                f"Critical VaR: ${var_95:,.2f}",
                f"95% Value at Risk is critically high (${var_95:,.2f}). Review risk exposure.",
                {"var_95": var_95, "threshold": self.alert_thresholds['var']['critical']},
                risk_score, risk_metrics.risk_level
            ))
        
        return alerts
    
    async def _check_trend_alerts(
        self, 
        account_id: str, 
        risk_metrics: RiskMetrics
    ) -> List[RiskAlert]:
        """Check for trend-based alerts."""
        alerts = []
        
        risk_history = list(self.risk_score_history[account_id])
        
        if len(risk_history) < 10:  # Need sufficient history
            return alerts
        
        recent_scores = [score for _, score in risk_history[-10:]]
        
        # Rising risk trend
        if len(recent_scores) >= 5:
            trend_slope = self._calculate_trend_slope(recent_scores)
            
            if trend_slope > 2.0:  # Risk increasing by >2 points per period
                alerts.append(self._create_alert(
                    account_id, "rising_risk_trend", AlertSeverity.WARNING,
                    "Rising risk trend detected",
                    f"Risk score has been consistently increasing (slope: {trend_slope:.1f}). Monitor trend closely.",
                    {"trend_slope": trend_slope, "recent_scores": recent_scores[-5:]},
                    risk_metrics.risk_score, risk_metrics.risk_level
                ))
        
        # Risk volatility
        if len(recent_scores) >= 10:
            risk_volatility = self._calculate_volatility(recent_scores)
            
            if risk_volatility > 15.0:  # High risk score volatility
                alerts.append(self._create_alert(
                    account_id, "high_risk_volatility", AlertSeverity.WARNING,
                    "High risk volatility detected",
                    f"Risk score volatility is high ({risk_volatility:.1f}). Indicates unstable risk profile.",
                    {"risk_volatility": risk_volatility},
                    risk_metrics.risk_score, risk_metrics.risk_level
                ))
        
        return alerts
    
    async def _check_anomaly_alerts(
        self, 
        account_id: str, 
        risk_metrics: RiskMetrics
    ) -> List[RiskAlert]:
        """Check for anomaly-based alerts using statistical methods."""
        alerts = []
        
        risk_history = list(self.risk_score_history[account_id])
        
        if len(risk_history) < 50:  # Need sufficient baseline
            return alerts
        
        scores = [score for _, score in risk_history]
        current_score = risk_metrics.risk_score
        
        # Statistical anomaly detection
        mean_score = sum(scores) / len(scores)
        std_dev = (sum((x - mean_score) ** 2 for x in scores) / len(scores)) ** 0.5
        
        z_score = abs(current_score - mean_score) / std_dev if std_dev > 0 else 0
        
        if z_score > 3.0:  # 3-sigma anomaly
            alerts.append(self._create_alert(
                account_id, "risk_score_anomaly", AlertSeverity.WARNING,
                f"Risk score anomaly detected (Z-score: {z_score:.1f})",
                f"Current risk score ({current_score:.1f}) is statistically unusual (Z-score: {z_score:.1f}).",
                {"z_score": z_score, "mean_score": mean_score, "std_dev": std_dev},
                current_score, risk_metrics.risk_level
            ))
        
        return alerts
    
    async def _check_position_alerts(
        self, 
        account_id: str, 
        positions: List[Position]
    ) -> List[RiskAlert]:
        """Check for position-specific alerts."""
        alerts = []
        
        for position in positions:
            # Large position alerts
            notional_value = float(position.notional_value)
            if notional_value >= self.alert_thresholds['position_size']['critical']:
                alerts.append(self._create_alert(
                    account_id, f"large_position_{position.instrument}", AlertSeverity.ERROR,
                    f"Critical position size: {position.instrument}",
                    f"Position in {position.instrument} is critically large (${notional_value:,.0f}).",
                    {"instrument": position.instrument, "notional_value": notional_value},
                    80.0, RiskLevel.HIGH,
                    affected_positions=[str(position.position_id)]
                ))
            
            # Underwater position alerts
            unrealized_pl = float(position.unrealized_pl)
            if position.market_value != 0:
                pl_percentage = unrealized_pl / float(position.market_value)
                
                if pl_percentage <= -0.10:  # -10% unrealized loss
                    alerts.append(self._create_alert(
                        account_id, f"underwater_position_{position.instrument}", AlertSeverity.WARNING,
                        f"Underwater position: {position.instrument}",
                        f"Position in {position.instrument} has {pl_percentage:.1%} unrealized loss.",
                        {"instrument": position.instrument, "pl_percentage": pl_percentage, "unrealized_pl": unrealized_pl},
                        60.0, RiskLevel.MEDIUM,
                        affected_positions=[str(position.position_id)]
                    ))
        
        return alerts
    
    async def _check_correlation_alerts(
        self, 
        account_id: str, 
        risk_metrics: RiskMetrics,
        positions: List[Position]
    ) -> List[RiskAlert]:
        """Check for correlation-related alerts."""
        alerts = []
        
        correlation_risk = risk_metrics.correlation_risk
        
        # High correlation risk
        if correlation_risk >= 0.8:
            correlated_instruments = [pos.instrument for pos in positions]
            
            alerts.append(self._create_alert(
                account_id, "high_correlation_risk", AlertSeverity.WARNING,
                f"High correlation risk: {correlation_risk:.1%}",
                f"Portfolio correlation risk is high ({correlation_risk:.1%}). Positions may move together.",
                {"correlation_risk": correlation_risk, "instruments": correlated_instruments},
                risk_metrics.risk_score, risk_metrics.risk_level
            ))
        
        # Low diversification
        if risk_metrics.sector_diversification < 0.3:
            alerts.append(self._create_alert(
                account_id, "low_diversification", AlertSeverity.WARNING,
                f"Low diversification: {risk_metrics.sector_diversification:.1%}",
                f"Portfolio diversification is low ({risk_metrics.sector_diversification:.1%}). Consider spreading risk.",
                {"diversification": risk_metrics.sector_diversification},
                risk_metrics.risk_score, risk_metrics.risk_level
            ))
        
        return alerts
    
    def _create_alert(
        self,
        account_id: str,
        alert_type: str,
        severity: AlertSeverity,
        title: str,
        message: str,
        details: Dict,
        risk_score: float,
        risk_level: RiskLevel,
        affected_positions: List[str] = None
    ) -> RiskAlert:
        """Create a new risk alert."""
        
        # Check cooldown
        cooldown_key = f"{account_id}_{alert_type}"
        now = datetime.now()
        
        if cooldown_key in self.alert_cooldowns:
            last_alert = self.alert_cooldowns[cooldown_key]
            if (now - last_alert).total_seconds() < 300:  # 5-minute cooldown
                return None
        
        # Generate recommended actions
        recommended_actions = self._generate_recommended_actions(alert_type, severity, details)
        
        alert = RiskAlert(
            account_id=account_id,
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            details=details,
            risk_score=risk_score,
            risk_level=risk_level,
            affected_positions=affected_positions or [],
            recommended_actions=recommended_actions
        )
        
        # Set cooldown
        self.alert_cooldowns[cooldown_key] = now
        
        return alert
    
    def _generate_recommended_actions(
        self, 
        alert_type: str, 
        severity: AlertSeverity, 
        details: Dict
    ) -> List[str]:
        """Generate recommended actions based on alert type and severity."""
        actions = []
        
        if "risk_score" in alert_type:
            if severity == AlertSeverity.CRITICAL:
                actions.extend([
                    "Activate kill switch if necessary",
                    "Close high-risk positions immediately",
                    "Review all open positions",
                    "Contact risk manager"
                ])
            else:
                actions.extend([
                    "Review position sizes",
                    "Check leverage levels",
                    "Monitor closely for 30 minutes"
                ])
        
        elif "leverage" in alert_type:
            actions.extend([
                "Reduce position sizes",
                "Close least profitable positions",
                "Add margin if available",
                "Review leverage settings"
            ])
        
        elif "daily_loss" in alert_type:
            actions.extend([
                "Stop new position entries",
                "Review stop losses",
                "Consider position exits",
                "Analyze loss sources"
            ])
        
        elif "position" in alert_type:
            actions.extend([
                "Review position sizing",
                "Consider partial exit",
                "Tighten stop loss",
                "Monitor position closely"
            ])
        
        elif "correlation" in alert_type:
            actions.extend([
                "Diversify portfolio",
                "Reduce correlated positions",
                "Add uncorrelated assets",
                "Review position allocation"
            ])
        
        return actions
    
    async def _process_new_alert(self, alert: RiskAlert):
        """Process and store new alert."""
        if alert is None:
            return
        
        # Store alert
        alert_key = f"{alert.account_id}_{alert.alert_type}"
        self.active_alerts[alert_key] = alert
        self.alert_history[alert.account_id].append(alert)
        
        # Send notifications
        await self._send_alert_notifications(alert)
        
        # Set escalation timer for critical alerts
        if alert.severity in [AlertSeverity.ERROR, AlertSeverity.CRITICAL]:
            self.escalation_timers[alert_key] = datetime.now()
        
        print(f"Alert generated: {alert.title} for account {alert.account_id}")
    
    async def _send_alert_notifications(self, alert: RiskAlert):
        """Send alert notifications through configured channels."""
        # Dashboard notification (always enabled)
        await self._send_dashboard_notification(alert)
        
        # Email for critical alerts
        if alert.severity in [AlertSeverity.ERROR, AlertSeverity.CRITICAL]:
            await self._send_email_notification(alert)
        
        # SMS for emergency alerts
        if alert.severity == AlertSeverity.CRITICAL and "emergency" in alert.alert_type:
            await self._send_sms_notification(alert)
        
        # Webhook notifications
        await self._send_webhook_notification(alert)
    
    async def _send_dashboard_notification(self, alert: RiskAlert):
        """Send alert to dashboard."""
        # In production, this would update the dashboard UI
        notification_data = {
            "type": "risk_alert",
            "alert_id": str(alert.alert_id),
            "account_id": alert.account_id,
            "severity": alert.severity.value,
            "title": alert.title,
            "message": alert.message,
            "timestamp": alert.triggered_at.isoformat()
        }
        print(f"Dashboard alert: {json.dumps(notification_data, indent=2)}")
    
    async def _send_email_notification(self, alert: RiskAlert):
        """Send email notification."""
        # In production, integrate with email service
        print(f"Email alert sent for {alert.account_id}: {alert.title}")
    
    async def _send_sms_notification(self, alert: RiskAlert):
        """Send SMS notification."""
        # In production, integrate with SMS service
        print(f"SMS alert sent for {alert.account_id}: {alert.title}")
    
    async def _send_webhook_notification(self, alert: RiskAlert):
        """Send webhook notification."""
        # In production, send to configured webhook endpoints
        webhook_payload = {
            "alert_id": str(alert.alert_id),
            "account_id": alert.account_id,
            "alert_type": alert.alert_type,
            "severity": alert.severity.value,
            "title": alert.title,
            "message": alert.message,
            "risk_score": alert.risk_score,
            "details": alert.details,
            "triggered_at": alert.triggered_at.isoformat()
        }
        print(f"Webhook alert: {json.dumps(webhook_payload)}")
    
    async def _check_alert_escalations(self, account_id: str):
        """Check for alerts that need escalation."""
        now = datetime.now()
        escalation_threshold = timedelta(minutes=30)  # 30-minute escalation
        
        alerts_to_escalate = []
        
        for alert_key, escalation_time in list(self.escalation_timers.items()):
            if account_id in alert_key and (now - escalation_time) > escalation_threshold:
                if alert_key in self.active_alerts:
                    alert = self.active_alerts[alert_key]
                    if not alert.acknowledged_at:  # Only escalate unacknowledged alerts
                        alerts_to_escalate.append(alert)
        
        # Process escalations
        for alert in alerts_to_escalate:
            await self._escalate_alert(alert)
    
    async def _escalate_alert(self, alert: RiskAlert):
        """Escalate an unresolved alert."""
        print(f"Escalating alert {alert.alert_id} for account {alert.account_id}")
        
        # Send escalation notifications
        escalation_message = f"ESCALATION: {alert.title} - Unresolved for 30+ minutes"
        
        # In production, notify senior staff, managers, etc.
        print(f"Escalation notification: {escalation_message}")
    
    def acknowledge_alert(self, alert_id: UUID, acknowledged_by: str) -> bool:
        """Acknowledge an alert."""
        for alert in self.active_alerts.values():
            if alert.alert_id == alert_id:
                alert.acknowledged_at = datetime.now()
                print(f"Alert {alert_id} acknowledged by {acknowledged_by}")
                return True
        return False
    
    def resolve_alert(self, alert_id: UUID, resolved_by: str, resolution_notes: str = "") -> bool:
        """Resolve an alert."""
        alert_to_remove = None
        
        for alert_key, alert in self.active_alerts.items():
            if alert.alert_id == alert_id:
                alert.resolved_at = datetime.now()
                alert_to_remove = alert_key
                print(f"Alert {alert_id} resolved by {resolved_by}: {resolution_notes}")
                break
        
        if alert_to_remove:
            del self.active_alerts[alert_to_remove]
            if alert_to_remove in self.escalation_timers:
                del self.escalation_timers[alert_to_remove]
            return True
        
        return False
    
    def get_active_alerts(self, account_id: Optional[str] = None) -> List[RiskAlert]:
        """Get active alerts, optionally filtered by account."""
        if account_id:
            return [
                alert for alert in self.active_alerts.values() 
                if alert.account_id == account_id
            ]
        return list(self.active_alerts.values())
    
    def get_alert_history(
        self, 
        account_id: str, 
        hours: int = 24
    ) -> List[RiskAlert]:
        """Get alert history for specified time period."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        return [
            alert for alert in self.alert_history.get(account_id, [])
            if alert.triggered_at >= cutoff_time
        ]
    
    def _update_risk_score_history(self, account_id: str, risk_score: float):
        """Update risk score history for trend analysis."""
        now = datetime.now()
        self.risk_score_history[account_id].append((now, risk_score))
    
    def _calculate_trend_slope(self, values: List[float]) -> float:
        """Calculate trend slope using linear regression."""
        n = len(values)
        if n < 2:
            return 0.0
        
        x_sum = sum(range(n))
        y_sum = sum(values)
        xy_sum = sum(i * val for i, val in enumerate(values))
        x2_sum = sum(i**2 for i in range(n))
        
        if n * x2_sum == x_sum**2:
            return 0.0
        
        slope = (n * xy_sum - x_sum * y_sum) / (n * x2_sum - x_sum**2)
        return slope
    
    def _calculate_volatility(self, values: List[float]) -> float:
        """Calculate volatility (standard deviation)."""
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get alert manager performance metrics."""
        total_alerts = sum(len(history) for history in self.alert_history.values())
        
        return {
            'alerts_processed': self.alerts_processed,
            'active_alerts': len(self.active_alerts),
            'total_alerts_generated': total_alerts,
            'avg_processing_time_ms': (
                sum(self.alert_processing_times) / len(self.alert_processing_times)
                if self.alert_processing_times else 0.0
            ),
            'false_positive_rate': self.false_positive_rate,
            'alerts_under_escalation': len(self.escalation_timers),
            'monitored_accounts': len(self.risk_score_history)
        }
    
    def update_alert_thresholds(self, thresholds: Dict[str, Dict[str, float]]):
        """Update alert thresholds."""
        self.alert_thresholds.update(thresholds)
        print(f"Updated alert thresholds: {list(thresholds.keys())}")
    
    def set_notification_channel(self, channel: AlertChannel, handler: Callable):
        """Set notification channel handler."""
        self.notification_channels[channel] = handler
        print(f"Configured notification channel: {channel.value}")