"""Correlation warning and alert management system."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc

from .models import (
    CorrelationAlert, CorrelationMetric, CorrelationSeverity,
    AlertResponse
)

logger = logging.getLogger(__name__)


class AlertChannel(str, Enum):
    """Available alert channels."""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    SMS = "sms"
    DASHBOARD = "dashboard"


class AlertManager:
    """Manages correlation alerts and warning system."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.alert_channels = [AlertChannel.DASHBOARD, AlertChannel.WEBHOOK]
        self.escalation_config = {
            CorrelationSeverity.INFO: {"interval": 3600, "channels": [AlertChannel.DASHBOARD]},
            CorrelationSeverity.WARNING: {"interval": 1800, "channels": [AlertChannel.DASHBOARD, AlertChannel.WEBHOOK]},
            CorrelationSeverity.CRITICAL: {"interval": 300, "channels": [AlertChannel.DASHBOARD, AlertChannel.WEBHOOK, AlertChannel.SLACK]}
        }
        self.alert_cache = {}
    
    async def process_correlation_alert(
        self,
        account1_id: UUID,
        account2_id: UUID,
        correlation: float,
        threshold_config: Optional[Dict[str, float]] = None
    ) -> Optional[AlertResponse]:
        """Process and create correlation alert if threshold exceeded."""
        # Use default thresholds if not provided
        if threshold_config is None:
            threshold_config = {
                CorrelationSeverity.INFO.value: 0.5,
                CorrelationSeverity.WARNING.value: 0.7,
                CorrelationSeverity.CRITICAL.value: 0.9
            }
        
        # Determine severity
        severity = self._determine_severity(correlation, threshold_config)
        
        if not severity:
            return None  # Correlation below all thresholds
        
        # Check for existing unresolved alert
        existing_alert = await self._get_active_alert(account1_id, account2_id)
        
        if existing_alert:
            # Update existing alert if severity changed
            if existing_alert.severity != severity.value:
                existing_alert.correlation_coefficient = correlation
                existing_alert.severity = severity.value
                existing_alert.alert_time = datetime.utcnow()
                self.db.commit()
                
                await self._send_alert_notifications(existing_alert, "severity_update")
                return AlertResponse.from_orm(existing_alert)
            else:
                # Check if enough time has passed for escalation
                await self._check_escalation(existing_alert)
                return None
        
        # Create new alert
        alert = CorrelationAlert(
            account_1_id=account1_id,
            account_2_id=account2_id,
            correlation_coefficient=correlation,
            severity=severity.value
        )
        
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        
        # Send notifications
        await self._send_alert_notifications(alert, "new_alert")
        
        # Cache alert for quick access
        cache_key = f"{account1_id}_{account2_id}"
        self.alert_cache[cache_key] = alert
        
        logger.warning(
            f"New correlation alert: {account1_id} <-> {account2_id} "
            f"correlation={correlation:.3f} severity={severity.value}"
        )
        
        return AlertResponse.from_orm(alert)
    
    async def resolve_alert(
        self,
        alert_id: UUID,
        resolution_action: str,
        correlation_after: Optional[float] = None
    ) -> bool:
        """Resolve a correlation alert."""
        alert = self.db.query(CorrelationAlert).filter(
            CorrelationAlert.alert_id == alert_id
        ).first()
        
        if not alert or alert.resolved_time:
            return False
        
        alert.resolved_time = datetime.utcnow()
        alert.resolution_action = resolution_action
        
        self.db.commit()
        
        # Remove from cache
        cache_key = f"{alert.account_1_id}_{alert.account_2_id}"
        self.alert_cache.pop(cache_key, None)
        
        # Send resolution notification
        await self._send_alert_notifications(alert, "resolved")
        
        logger.info(
            f"Resolved alert {alert_id}: {resolution_action} "
            f"correlation_after={correlation_after}"
        )
        
        return True
    
    async def get_active_alerts(
        self,
        severity_filter: Optional[CorrelationSeverity] = None,
        account_id_filter: Optional[UUID] = None
    ) -> List[AlertResponse]:
        """Get currently active (unresolved) alerts."""
        query = self.db.query(CorrelationAlert).filter(
            CorrelationAlert.resolved_time.is_(None)
        )
        
        if severity_filter:
            query = query.filter(CorrelationAlert.severity == severity_filter.value)
        
        if account_id_filter:
            query = query.filter(
                or_(
                    CorrelationAlert.account_1_id == account_id_filter,
                    CorrelationAlert.account_2_id == account_id_filter
                )
            )
        
        alerts = query.order_by(desc(CorrelationAlert.alert_time)).all()
        
        return [AlertResponse.from_orm(alert) for alert in alerts]
    
    async def get_alert_history(
        self,
        hours: int = 24,
        include_resolved: bool = True
    ) -> List[AlertResponse]:
        """Get alert history for specified time period."""
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        query = self.db.query(CorrelationAlert).filter(
            CorrelationAlert.alert_time >= start_time
        )
        
        if not include_resolved:
            query = query.filter(CorrelationAlert.resolved_time.is_(None))
        
        alerts = query.order_by(desc(CorrelationAlert.alert_time)).all()
        
        return [AlertResponse.from_orm(alert) for alert in alerts]
    
    async def generate_correlation_heatmap_data(
        self,
        account_ids: List[UUID],
        time_window: int = 3600
    ) -> Dict[str, Any]:
        """Generate data for correlation heatmap visualization."""
        recent_time = datetime.utcnow() - timedelta(seconds=time_window * 2)
        
        # Get recent correlation metrics
        correlations = self.db.query(CorrelationMetric).filter(
            and_(
                CorrelationMetric.time_window == time_window,
                CorrelationMetric.calculation_time >= recent_time
            )
        ).all()
        
        # Build heatmap data structure
        heatmap_data = {
            "accounts": [str(acc_id) for acc_id in account_ids],
            "correlations": [],
            "alerts": []
        }
        
        # Create correlation matrix
        n_accounts = len(account_ids)
        correlation_matrix = [[0.0 for _ in range(n_accounts)] for _ in range(n_accounts)]
        
        account_index = {acc_id: i for i, acc_id in enumerate(account_ids)}
        
        for correlation in correlations:
            if (correlation.account_1_id in account_index and 
                correlation.account_2_id in account_index):
                
                i = account_index[correlation.account_1_id]
                j = account_index[correlation.account_2_id]
                
                corr_value = float(correlation.correlation_coefficient)
                correlation_matrix[i][j] = corr_value
                correlation_matrix[j][i] = corr_value
        
        # Set diagonal to 1.0
        for i in range(n_accounts):
            correlation_matrix[i][i] = 1.0
        
        heatmap_data["correlations"] = correlation_matrix
        
        # Add active alerts
        active_alerts = await self.get_active_alerts()
        for alert in active_alerts:
            if (alert.account_1_id in account_ids and 
                alert.account_2_id in account_ids):
                
                heatmap_data["alerts"].append({
                    "account_1": str(alert.account_1_id),
                    "account_2": str(alert.account_2_id),
                    "correlation": float(alert.correlation_coefficient),
                    "severity": alert.severity,
                    "duration": (datetime.utcnow() - alert.alert_time).total_seconds()
                })
        
        return heatmap_data
    
    async def get_alert_statistics(
        self,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get alert statistics for reporting."""
        start_time = datetime.utcnow() - timedelta(days=days)
        
        # Total alerts by severity
        severity_counts = {}
        for severity in CorrelationSeverity:
            count = self.db.query(func.count(CorrelationAlert.alert_id)).filter(
                and_(
                    CorrelationAlert.severity == severity.value,
                    CorrelationAlert.alert_time >= start_time
                )
            ).scalar()
            severity_counts[severity.value] = count
        
        # Resolution statistics
        total_alerts = self.db.query(func.count(CorrelationAlert.alert_id)).filter(
            CorrelationAlert.alert_time >= start_time
        ).scalar()
        
        resolved_alerts = self.db.query(func.count(CorrelationAlert.alert_id)).filter(
            and_(
                CorrelationAlert.alert_time >= start_time,
                CorrelationAlert.resolved_time.isnot(None)
            )
        ).scalar()
        
        # Average resolution time
        avg_resolution_time = self.db.query(
            func.avg(
                func.extract('epoch', CorrelationAlert.resolved_time - CorrelationAlert.alert_time)
            )
        ).filter(
            and_(
                CorrelationAlert.alert_time >= start_time,
                CorrelationAlert.resolved_time.isnot(None)
            )
        ).scalar()
        
        # Most correlated account pairs
        top_pairs = self.db.query(
            CorrelationAlert.account_1_id,
            CorrelationAlert.account_2_id,
            func.count(CorrelationAlert.alert_id).label('alert_count'),
            func.avg(CorrelationAlert.correlation_coefficient).label('avg_correlation')
        ).filter(
            CorrelationAlert.alert_time >= start_time
        ).group_by(
            CorrelationAlert.account_1_id, CorrelationAlert.account_2_id
        ).order_by(desc('alert_count')).limit(10).all()
        
        return {
            "period_days": days,
            "severity_counts": severity_counts,
            "total_alerts": total_alerts,
            "resolved_alerts": resolved_alerts,
            "resolution_rate": resolved_alerts / total_alerts if total_alerts > 0 else 0.0,
            "avg_resolution_time_seconds": float(avg_resolution_time) if avg_resolution_time else 0.0,
            "top_correlated_pairs": [
                {
                    "account_1_id": str(pair.account_1_id),
                    "account_2_id": str(pair.account_2_id),
                    "alert_count": pair.alert_count,
                    "avg_correlation": float(pair.avg_correlation)
                }
                for pair in top_pairs
            ]
        }
    
    async def auto_escalation_monitor(self):
        """Background task to monitor and escalate persistent alerts."""
        while True:
            try:
                active_alerts = await self.get_active_alerts()
                
                for alert in active_alerts:
                    await self._check_escalation(alert)
                
                # Sleep for 5 minutes before next check
                await asyncio.sleep(300)
                
            except Exception as e:
                logger.error(f"Error in escalation monitor: {e}")
                await asyncio.sleep(60)
    
    def _determine_severity(
        self,
        correlation: float,
        threshold_config: Dict[str, float]
    ) -> Optional[CorrelationSeverity]:
        """Determine alert severity based on correlation value."""
        if correlation >= threshold_config.get(CorrelationSeverity.CRITICAL.value, 0.9):
            return CorrelationSeverity.CRITICAL
        elif correlation >= threshold_config.get(CorrelationSeverity.WARNING.value, 0.7):
            return CorrelationSeverity.WARNING
        elif correlation >= threshold_config.get(CorrelationSeverity.INFO.value, 0.5):
            return CorrelationSeverity.INFO
        else:
            return None
    
    async def _get_active_alert(
        self,
        account1_id: UUID,
        account2_id: UUID
    ) -> Optional[CorrelationAlert]:
        """Get existing active alert for account pair."""
        return self.db.query(CorrelationAlert).filter(
            and_(
                or_(
                    and_(
                        CorrelationAlert.account_1_id == account1_id,
                        CorrelationAlert.account_2_id == account2_id
                    ),
                    and_(
                        CorrelationAlert.account_1_id == account2_id,
                        CorrelationAlert.account_2_id == account1_id
                    )
                ),
                CorrelationAlert.resolved_time.is_(None)
            )
        ).first()
    
    async def _check_escalation(self, alert: AlertResponse):
        """Check if alert needs escalation."""
        severity = CorrelationSeverity(alert.severity)
        escalation_interval = self.escalation_config[severity]["interval"]
        
        time_since_alert = (datetime.utcnow() - alert.alert_time).total_seconds()
        
        if time_since_alert >= escalation_interval:
            await self._send_alert_notifications(alert, "escalation")
    
    async def _send_alert_notifications(
        self,
        alert: CorrelationAlert,
        notification_type: str
    ):
        """Send alert notifications through configured channels."""
        severity = CorrelationSeverity(alert.severity)
        channels = self.escalation_config[severity]["channels"]
        
        message = self._format_alert_message(alert, notification_type)
        
        for channel in channels:
            try:
                if channel == AlertChannel.DASHBOARD:
                    await self._send_dashboard_notification(alert, message)
                elif channel == AlertChannel.WEBHOOK:
                    await self._send_webhook_notification(alert, message)
                elif channel == AlertChannel.SLACK:
                    await self._send_slack_notification(alert, message)
                elif channel == AlertChannel.EMAIL:
                    await self._send_email_notification(alert, message)
                elif channel == AlertChannel.SMS:
                    await self._send_sms_notification(alert, message)
                    
            except Exception as e:
                logger.error(f"Failed to send {channel.value} notification: {e}")
    
    def _format_alert_message(
        self,
        alert: CorrelationAlert,
        notification_type: str
    ) -> str:
        """Format alert message for notifications."""
        if notification_type == "new_alert":
            return (
                f"🚨 New Correlation Alert ({alert.severity.upper()})\n"
                f"Accounts: {alert.account_1_id} <-> {alert.account_2_id}\n"
                f"Correlation: {alert.correlation_coefficient:.3f}\n"
                f"Time: {alert.alert_time.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        elif notification_type == "severity_update":
            return (
                f"⚠️ Correlation Alert Severity Updated ({alert.severity.upper()})\n"
                f"Accounts: {alert.account_1_id} <-> {alert.account_2_id}\n"
                f"New Correlation: {alert.correlation_coefficient:.3f}\n"
                f"Updated: {alert.alert_time.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        elif notification_type == "escalation":
            duration = datetime.utcnow() - alert.alert_time
            return (
                f"🔥 ESCALATION: Correlation Alert Unresolved\n"
                f"Accounts: {alert.account_1_id} <-> {alert.account_2_id}\n"
                f"Correlation: {alert.correlation_coefficient:.3f}\n"
                f"Duration: {duration.total_seconds()/3600:.1f} hours\n"
                f"Severity: {alert.severity.upper()}"
            )
        elif notification_type == "resolved":
            return (
                f"✅ Correlation Alert Resolved\n"
                f"Accounts: {alert.account_1_id} <-> {alert.account_2_id}\n"
                f"Resolution: {alert.resolution_action}\n"
                f"Resolved: {alert.resolved_time.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        else:
            return f"Correlation Alert Update: {notification_type}"
    
    async def _send_dashboard_notification(self, alert: CorrelationAlert, message: str):
        """Send notification to dashboard."""
        # This would integrate with WebSocket system for real-time dashboard updates
        logger.info(f"Dashboard notification: {message}")
    
    async def _send_webhook_notification(self, alert: CorrelationAlert, message: str):
        """Send webhook notification."""
        # This would POST to configured webhook URL
        logger.info(f"Webhook notification: {message}")
    
    async def _send_slack_notification(self, alert: CorrelationAlert, message: str):
        """Send Slack notification."""
        # This would send to Slack channel
        logger.info(f"Slack notification: {message}")
    
    async def _send_email_notification(self, alert: CorrelationAlert, message: str):
        """Send email notification."""
        # This would send email
        logger.info(f"Email notification: {message}")
    
    async def _send_sms_notification(self, alert: CorrelationAlert, message: str):
        """Send SMS notification."""
        # This would send SMS
        logger.info(f"SMS notification: {message}")