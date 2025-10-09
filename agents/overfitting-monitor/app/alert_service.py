"""
Alert Service - Story 11.4, Task 3

Manages overfitting alerts with Slack and email notifications.
"""

import logging
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import httpx
from decimal import Decimal

from .models import OverfittingAlert, AlertLevel

logger = logging.getLogger(__name__)


class AlertService:
    """
    Alert management and notification service

    Handles alert generation, storage, acknowledgment, and delivery
    via Slack and email channels.
    """

    def __init__(
        self,
        slack_webhook_url: Optional[str] = None,
        email_enabled: bool = False,
        sendgrid_api_key: Optional[str] = None,
        alert_recipients: Optional[List[str]] = None
    ):
        """
        Initialize alert service

        @param slack_webhook_url: Slack webhook URL for notifications
        @param email_enabled: Enable email notifications
        @param sendgrid_api_key: SendGrid API key for email
        @param alert_recipients: List of email addresses for alerts
        """
        self.slack_webhook_url = slack_webhook_url
        self.email_enabled = email_enabled
        self.sendgrid_api_key = sendgrid_api_key
        self.alert_recipients = alert_recipients or []

        self.http_client: Optional[httpx.AsyncClient] = None
        self.active_alerts: Dict[str, OverfittingAlert] = {}

    async def initialize(self):
        """Initialize async HTTP client"""
        self.http_client = httpx.AsyncClient(timeout=10.0)
        logger.info("Alert service initialized")

    async def close(self):
        """Close HTTP client"""
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None

    async def create_alert(
        self,
        severity: AlertLevel,
        metric: str,
        value: float,
        threshold: float,
        message: str,
        recommendation: Optional[str] = None
    ) -> OverfittingAlert:
        """
        Create a new overfitting alert

        @param severity: Alert severity level
        @param metric: Metric that triggered alert
        @param value: Current metric value
        @param threshold: Threshold that was exceeded
        @param message: Alert message
        @param recommendation: Recommended action
        @returns: Created alert
        """
        alert = OverfittingAlert(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            severity=severity,
            metric=metric,
            value=value,
            threshold=threshold,
            message=message,
            recommendation=recommendation,
            acknowledged=False
        )

        # Store active alert
        self.active_alerts[alert.id] = alert

        # Send notifications
        await self._send_notifications(alert)

        logger.info(
            f"Alert created: {alert.severity.value} - {alert.metric} "
            f"(value={value:.3f}, threshold={threshold:.3f})"
        )

        return alert

    async def acknowledge_alert(
        self,
        alert_id: str
    ) -> Optional[OverfittingAlert]:
        """
        Acknowledge an alert

        @param alert_id: Alert ID to acknowledge
        @returns: Acknowledged alert or None if not found
        """
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.acknowledged = True
            alert.acknowledged_at = datetime.now(timezone.utc)

            logger.info(f"Alert acknowledged: {alert_id}")
            return alert

        logger.warning(f"Alert not found for acknowledgment: {alert_id}")
        return None

    async def get_active_alerts(
        self,
        severity: Optional[AlertLevel] = None
    ) -> List[OverfittingAlert]:
        """
        Get active (unacknowledged) alerts

        @param severity: Filter by severity level
        @returns: List of active alerts
        """
        alerts = [
            alert for alert in self.active_alerts.values()
            if not alert.acknowledged
        ]

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        return alerts

    async def clear_acknowledged_alerts(self):
        """Remove acknowledged alerts from active storage"""
        initial_count = len(self.active_alerts)

        self.active_alerts = {
            alert_id: alert
            for alert_id, alert in self.active_alerts.items()
            if not alert.acknowledged
        }

        cleared_count = initial_count - len(self.active_alerts)
        if cleared_count > 0:
            logger.info(f"Cleared {cleared_count} acknowledged alerts")

    async def _send_notifications(self, alert: OverfittingAlert):
        """
        Send alert notifications via configured channels

        @param alert: Alert to send
        """
        # Send to Slack
        if self.slack_webhook_url:
            try:
                await self._send_slack_notification(alert)
            except Exception as e:
                logger.error(f"Failed to send Slack notification: {e}")

        # Send to email (if enabled)
        if self.email_enabled and self.sendgrid_api_key:
            try:
                await self._send_email_notification(alert)
            except Exception as e:
                logger.error(f"Failed to send email notification: {e}")

    async def _send_slack_notification(self, alert: OverfittingAlert):
        """
        Send alert to Slack

        @param alert: Alert to send
        """
        if not self.http_client or not self.slack_webhook_url:
            return

        # Color based on severity
        color_map = {
            AlertLevel.NORMAL: "#36a64f",    # Green
            AlertLevel.WARNING: "#ff9900",   # Orange
            AlertLevel.CRITICAL: "#ff0000"   # Red
        }

        # Build Slack message
        message = {
            "attachments": [
                {
                    "color": color_map.get(alert.severity, "#439fe0"),
                    "title": f"🚨 Overfitting Alert: {alert.severity.value.upper()}",
                    "text": alert.message,
                    "fields": [
                        {
                            "title": "Metric",
                            "value": alert.metric,
                            "short": True
                        },
                        {
                            "title": "Current Value",
                            "value": f"{alert.value:.3f}",
                            "short": True
                        },
                        {
                            "title": "Threshold",
                            "value": f"{alert.threshold:.3f}",
                            "short": True
                        },
                        {
                            "title": "Severity",
                            "value": alert.severity.value.upper(),
                            "short": True
                        }
                    ],
                    "footer": "TMT Overfitting Monitor",
                    "ts": int(alert.timestamp.timestamp())
                }
            ]
        }

        # Add recommendation if present
        if alert.recommendation:
            message["attachments"][0]["fields"].append({
                "title": "Recommendation",
                "value": alert.recommendation,
                "short": False
            })

        try:
            response = await self.http_client.post(
                self.slack_webhook_url,
                json=message,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                logger.debug(f"Slack notification sent for alert {alert.id}")
            else:
                logger.error(
                    f"Slack webhook error {response.status_code}: {response.text}"
                )
        except Exception as e:
            logger.error(f"Error sending Slack notification: {e}")

    async def _send_email_notification(self, alert: OverfittingAlert):
        """
        Send alert via email using SendGrid

        @param alert: Alert to send
        """
        if not self.http_client or not self.sendgrid_api_key or not self.alert_recipients:
            return

        # Build email content
        subject = f"[{alert.severity.value.upper()}] Overfitting Alert - {alert.metric}"

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: {'#ff0000' if alert.severity == AlertLevel.CRITICAL else '#ff9900'};">
                Overfitting Alert: {alert.severity.value.upper()}
            </h2>
            <p><strong>Message:</strong> {alert.message}</p>
            <table style="border-collapse: collapse; width: 100%;">
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>Metric</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{alert.metric}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>Current Value</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{alert.value:.3f}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>Threshold</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{alert.threshold:.3f}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>Timestamp</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{alert.timestamp.isoformat()}</td>
                </tr>
            </table>
        """

        if alert.recommendation:
            html_content += f"""
            <div style="margin-top: 20px; padding: 15px; background-color: #f0f0f0; border-left: 4px solid #0066cc;">
                <strong>Recommendation:</strong> {alert.recommendation}
            </div>
            """

        html_content += """
        </body>
        </html>
        """

        # SendGrid API payload
        payload = {
            "personalizations": [
                {
                    "to": [{"email": email} for email in self.alert_recipients],
                    "subject": subject
                }
            ],
            "from": {"email": "noreply@trading-system.com", "name": "TMT Overfitting Monitor"},
            "content": [
                {
                    "type": "text/html",
                    "value": html_content
                }
            ]
        }

        try:
            response = await self.http_client.post(
                "https://api.sendgrid.com/v3/mail/send",
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.sendgrid_api_key}",
                    "Content-Type": "application/json"
                }
            )

            if response.status_code == 202:
                logger.debug(f"Email notification sent for alert {alert.id}")
            else:
                logger.error(
                    f"SendGrid API error {response.status_code}: {response.text}"
                )
        except Exception as e:
            logger.error(f"Error sending email notification: {e}")

    async def check_overfitting_thresholds(
        self,
        overfitting_score: float,
        warning_threshold: float = 0.3,
        critical_threshold: float = 0.5
    ) -> Optional[OverfittingAlert]:
        """
        Check overfitting score against thresholds and create alert if needed

        @param overfitting_score: Current overfitting score
        @param warning_threshold: Warning threshold (default: 0.3)
        @param critical_threshold: Critical threshold (default: 0.5)
        @returns: Created alert or None
        """
        if overfitting_score >= critical_threshold:
            return await self.create_alert(
                severity=AlertLevel.CRITICAL,
                metric="overfitting_score",
                value=overfitting_score,
                threshold=critical_threshold,
                message=f"CRITICAL: Overfitting score ({overfitting_score:.3f}) exceeds critical threshold ({critical_threshold:.3f})",
                recommendation="Review parameter configuration immediately. Consider reverting to baseline parameters or reducing parameter optimization aggressiveness."
            )
        elif overfitting_score >= warning_threshold:
            return await self.create_alert(
                severity=AlertLevel.WARNING,
                metric="overfitting_score",
                value=overfitting_score,
                threshold=warning_threshold,
                message=f"WARNING: Overfitting score ({overfitting_score:.3f}) exceeds warning threshold ({warning_threshold:.3f})",
                recommendation="Monitor parameter performance closely. Consider scheduling parameter review."
            )

        return None

    async def check_drift_threshold(
        self,
        parameter_name: str,
        drift_pct: float,
        max_drift_pct: float = 15.0
    ) -> Optional[OverfittingAlert]:
        """
        Check parameter drift against threshold

        @param parameter_name: Parameter name
        @param drift_pct: Drift percentage
        @param max_drift_pct: Maximum allowed drift (default: 15%)
        @returns: Created alert or None
        """
        if abs(drift_pct) > max_drift_pct:
            return await self.create_alert(
                severity=AlertLevel.WARNING,
                metric=f"parameter_drift_{parameter_name}",
                value=abs(drift_pct),
                threshold=max_drift_pct,
                message=f"Parameter '{parameter_name}' has drifted {drift_pct:.1f}% (exceeds {max_drift_pct:.1f}% threshold)",
                recommendation=f"Review recent changes to '{parameter_name}' parameter. Consider stabilizing or reverting to baseline."
            )

        return None

    async def check_performance_degradation(
        self,
        live_sharpe: float,
        backtest_sharpe: float,
        threshold_ratio: float = 0.7
    ) -> Optional[OverfittingAlert]:
        """
        Check for performance degradation

        @param live_sharpe: Live trading Sharpe ratio
        @param backtest_sharpe: Expected backtest Sharpe ratio
        @param threshold_ratio: Minimum acceptable ratio (default: 0.7 = 70%)
        @returns: Created alert or None
        """
        if backtest_sharpe <= 0:
            return None

        ratio = live_sharpe / backtest_sharpe

        if ratio < threshold_ratio:
            degradation_pct = (1 - ratio) * 100

            return await self.create_alert(
                severity=AlertLevel.CRITICAL if ratio < 0.5 else AlertLevel.WARNING,
                metric="performance_degradation",
                value=ratio,
                threshold=threshold_ratio,
                message=f"Live Sharpe ratio ({live_sharpe:.2f}) is only {ratio*100:.0f}% of backtest expectation ({backtest_sharpe:.2f}) - {degradation_pct:.0f}% degradation",
                recommendation="Investigate regime change or parameter overfitting. Consider running walk-forward optimization to update parameters."
            )

        return None
