"""
Daily/Weekly Performance Alert Scheduler

Implements scheduled performance monitoring as specified in forward testing
next steps action item #12:
- Daily P&L vs projection alerts
- Weekly stability score monitoring
- Monthly forward test updates
- Performance threshold notifications
"""

import asyncio
import logging
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
import schedule
import threading

from .performance_alerts import get_alert_system
from .performance_tracking import PerformanceTracker, AlertSeverity
from .monte_carlo_projections import get_monte_carlo_engine

logger = logging.getLogger(__name__)


class ScheduleFrequency(Enum):
    """Schedule frequency types"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass
class ScheduledAlert:
    """Configuration for scheduled alert"""
    name: str
    frequency: ScheduleFrequency
    time_of_day: time  # When to run (UTC)
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    alert_function: Optional[str] = None  # Function name to call


class PerformanceAlertScheduler:
    """
    Scheduler for daily/weekly/monthly performance alerts

    Handles:
    - Daily P&L vs projection comparison at market close
    - Weekly stability score updates every Monday
    - Monthly forward test validation on 1st of month
    - Performance threshold breach notifications
    """

    def __init__(self):
        self.alert_system = get_alert_system()
        self.performance_tracker = None  # Will be initialized when needed
        self.monte_carlo = get_monte_carlo_engine()

        # Scheduler state
        self.running = False
        self.scheduler_thread = None

        # Schedule configuration
        self.scheduled_alerts = self._initialize_scheduled_alerts()

        # Alert storage
        self.alerts_history_path = Path("performance_alerts/scheduled")
        self.alerts_history_path.mkdir(parents=True, exist_ok=True)

        logger.info("Performance Alert Scheduler initialized")

    def _initialize_scheduled_alerts(self) -> List[ScheduledAlert]:
        """Initialize default scheduled alert configurations"""
        return [
            # Daily P&L vs projection alerts at 17:00 UTC (NY market close)
            ScheduledAlert(
                name="daily_pnl_check",
                frequency=ScheduleFrequency.DAILY,
                time_of_day=time(17, 0),  # 17:00 UTC
                alert_function="check_daily_pnl_vs_projection"
            ),

            # Weekly stability score monitoring every Monday at 08:00 UTC
            ScheduledAlert(
                name="weekly_stability_check",
                frequency=ScheduleFrequency.WEEKLY,
                time_of_day=time(8, 0),  # 08:00 UTC Monday
                alert_function="check_weekly_stability_score"
            ),

            # Monthly forward test updates on 1st of month at 09:00 UTC
            ScheduledAlert(
                name="monthly_forward_test_update",
                frequency=ScheduleFrequency.MONTHLY,
                time_of_day=time(9, 0),  # 09:00 UTC 1st of month
                alert_function="update_monthly_forward_test"
            ),

            # Performance threshold notifications twice daily
            ScheduledAlert(
                name="performance_threshold_check",
                frequency=ScheduleFrequency.DAILY,
                time_of_day=time(12, 0),  # 12:00 UTC (mid-day check)
                alert_function="check_performance_thresholds"
            ),

            # Additional evening performance check
            ScheduledAlert(
                name="evening_performance_check",
                frequency=ScheduleFrequency.DAILY,
                time_of_day=time(22, 0),  # 22:00 UTC (evening check)
                alert_function="check_performance_thresholds"
            )
        ]

    async def start(self):
        """Start the performance alert scheduler"""
        try:
            if self.running:
                logger.warning("Performance alert scheduler already running")
                return

            logger.info("Starting Performance Alert Scheduler...")

            # Initialize performance tracker
            from .performance_tracking import get_performance_tracker
            self.performance_tracker = get_performance_tracker()

            # Schedule all alerts
            self._setup_schedules()

            # Start scheduler in background thread
            self.running = True
            self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
            self.scheduler_thread.start()

            logger.info("Performance Alert Scheduler started successfully")

        except Exception as e:
            logger.error(f"Failed to start Performance Alert Scheduler: {e}")
            raise

    async def stop(self):
        """Stop the performance alert scheduler"""
        try:
            if not self.running:
                return

            logger.info("Stopping Performance Alert Scheduler...")

            self.running = False
            schedule.clear()

            if self.scheduler_thread and self.scheduler_thread.is_alive():
                self.scheduler_thread.join(timeout=5)

            logger.info("Performance Alert Scheduler stopped")

        except Exception as e:
            logger.error(f"Error stopping Performance Alert Scheduler: {e}")

    def _setup_schedules(self):
        """Setup all scheduled alerts"""
        try:
            schedule.clear()

            for alert_config in self.scheduled_alerts:
                if not alert_config.enabled:
                    continue

                if alert_config.frequency == ScheduleFrequency.DAILY:
                    schedule.every().day.at(alert_config.time_of_day.strftime("%H:%M")).do(
                        self._execute_scheduled_alert, alert_config
                    )
                elif alert_config.frequency == ScheduleFrequency.WEEKLY:
                    schedule.every().monday.at(alert_config.time_of_day.strftime("%H:%M")).do(
                        self._execute_scheduled_alert, alert_config
                    )
                elif alert_config.frequency == ScheduleFrequency.MONTHLY:
                    # Monthly scheduling handled separately in _run_scheduler
                    pass

            logger.info(f"Scheduled {len([a for a in self.scheduled_alerts if a.enabled])} alert jobs")

        except Exception as e:
            logger.error(f"Error setting up schedules: {e}")

    def _run_scheduler(self):
        """Run the scheduler loop in background thread"""
        try:
            while self.running:
                # Run pending scheduled jobs
                schedule.run_pending()

                # Handle monthly jobs manually
                self._check_monthly_jobs()

                # Sleep for 60 seconds before next check
                if self.running:
                    threading.Event().wait(60)

        except Exception as e:
            logger.error(f"Error in scheduler loop: {e}")

    def _check_monthly_jobs(self):
        """Check and execute monthly jobs on 1st of month"""
        try:
            now = datetime.utcnow()

            # Only run on 1st of month
            if now.day != 1:
                return

            for alert_config in self.scheduled_alerts:
                if (alert_config.frequency == ScheduleFrequency.MONTHLY and
                    alert_config.enabled):

                    # Check if we should run based on time of day
                    if (now.time() >= alert_config.time_of_day and
                        (not alert_config.last_run or
                         alert_config.last_run.day != now.day)):

                        self._execute_scheduled_alert(alert_config)

        except Exception as e:
            logger.error(f"Error checking monthly jobs: {e}")

    def _execute_scheduled_alert(self, alert_config: ScheduledAlert):
        """Execute a scheduled alert"""
        try:
            logger.info(f"Executing scheduled alert: {alert_config.name}")

            # Update run time
            alert_config.last_run = datetime.utcnow()

            # Call the appropriate alert function
            if alert_config.alert_function == "check_daily_pnl_vs_projection":
                asyncio.run(self._check_daily_pnl_vs_projection())
            elif alert_config.alert_function == "check_weekly_stability_score":
                asyncio.run(self._check_weekly_stability_score())
            elif alert_config.alert_function == "update_monthly_forward_test":
                asyncio.run(self._update_monthly_forward_test())
            elif alert_config.alert_function == "check_performance_thresholds":
                asyncio.run(self._check_performance_thresholds())
            else:
                logger.warning(f"Unknown alert function: {alert_config.alert_function}")

            logger.info(f"Completed scheduled alert: {alert_config.name}")

        except Exception as e:
            logger.error(f"Error executing scheduled alert {alert_config.name}: {e}")

    async def _check_daily_pnl_vs_projection(self):
        """Daily P&L vs projection comparison"""
        try:
            if not self.performance_tracker:
                logger.warning("Performance tracker not available for daily P&L check")
                return

            # Get current day's performance
            current_metrics = await self.performance_tracker.get_current_metrics()
            if not current_metrics:
                logger.warning("No performance metrics available for daily check")
                return

            # Get Monte Carlo projections for comparison
            projections = await self.monte_carlo.get_daily_projections()

            # Generate alerts through the alert system
            alerts = await self.alert_system.evaluate_performance_alerts(
                current_metrics, projections.get("confidence_intervals")
            )

            if alerts:
                await self.alert_system.save_alerts(alerts)
                await self._save_scheduled_alert_summary("daily_pnl_check", alerts)

                critical_alerts = [a for a in alerts if a.severity == AlertSeverity.CRITICAL]
                if critical_alerts:
                    logger.critical(f"Daily P&L check generated {len(critical_alerts)} critical alerts")
                else:
                    logger.info(f"Daily P&L check completed with {len(alerts)} alerts")
            else:
                logger.info("Daily P&L check completed - no alerts generated")

        except Exception as e:
            logger.error(f"Error in daily P&L vs projection check: {e}")

    async def _check_weekly_stability_score(self):
        """Weekly stability score monitoring"""
        try:
            if not self.performance_tracker:
                logger.warning("Performance tracker not available for stability check")
                return

            # Calculate stability metrics over past week
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=7)

            stability_metrics = await self.performance_tracker.calculate_stability_score(
                start_date, end_date
            )

            if not stability_metrics:
                logger.warning("No stability metrics available for weekly check")
                return

            alerts = []

            # Check walk-forward stability threshold (target >60/100)
            walk_forward_score = stability_metrics.get("walk_forward_stability", 0)
            if walk_forward_score < 50:
                alerts.append(await self._create_stability_alert(
                    AlertSeverity.CRITICAL,
                    f"Walk-forward stability critically low: {walk_forward_score:.1f}/100",
                    walk_forward_score,
                    60.0,
                    "walk_forward_stability"
                ))
            elif walk_forward_score < 60:
                alerts.append(await self._create_stability_alert(
                    AlertSeverity.WARNING,
                    f"Walk-forward stability below target: {walk_forward_score:.1f}/100",
                    walk_forward_score,
                    60.0,
                    "walk_forward_stability"
                ))

            # Check out-of-sample validation (target >70/100)
            out_of_sample_score = stability_metrics.get("out_of_sample_validation", 0)
            if out_of_sample_score < 50:
                alerts.append(await self._create_stability_alert(
                    AlertSeverity.CRITICAL,
                    f"Out-of-sample validation critically low: {out_of_sample_score:.1f}/100",
                    out_of_sample_score,
                    70.0,
                    "out_of_sample_validation"
                ))
            elif out_of_sample_score < 70:
                alerts.append(await self._create_stability_alert(
                    AlertSeverity.WARNING,
                    f"Out-of-sample validation below target: {out_of_sample_score:.1f}/100",
                    out_of_sample_score,
                    70.0,
                    "out_of_sample_validation"
                ))

            if alerts:
                await self.alert_system.save_alerts(alerts)
                await self._save_scheduled_alert_summary("weekly_stability_check", alerts)
                logger.info(f"Weekly stability check completed with {len(alerts)} alerts")
            else:
                logger.info("Weekly stability check completed - no alerts generated")

        except Exception as e:
            logger.error(f"Error in weekly stability score check: {e}")

    async def _update_monthly_forward_test(self):
        """Monthly forward test updates and validation"""
        try:
            logger.info("Starting monthly forward test update...")

            # Trigger Monte Carlo engine to update projections
            updated_projections = await self.monte_carlo.run_monthly_forward_test_update()

            if not updated_projections:
                logger.error("Failed to generate updated forward test projections")
                return

            alerts = []

            # Compare new projections with previous month
            previous_projections = await self.monte_carlo.get_previous_month_projections()

            if previous_projections:
                # Check for significant changes in expected P&L
                current_expected = updated_projections.get("expected_monthly_pnl", 0)
                previous_expected = previous_projections.get("expected_monthly_pnl", 0)

                if previous_expected != 0:
                    change_pct = ((current_expected - previous_expected) / abs(previous_expected)) * 100

                    if abs(change_pct) > 25:  # 25% change threshold
                        severity = AlertSeverity.CRITICAL if abs(change_pct) > 50 else AlertSeverity.WARNING
                        alerts.append(await self._create_forward_test_alert(
                            severity,
                            f"Monthly forward test projection changed {change_pct:+.1f}%",
                            current_expected,
                            previous_expected,
                            "expected_pnl_change"
                        ))

            # Check overall forward test health metrics
            stability_score = updated_projections.get("walk_forward_stability", 0)
            validation_score = updated_projections.get("out_of_sample_validation", 0)

            if stability_score < 34.4 or validation_score < 17.4:  # Below current baseline
                alerts.append(await self._create_forward_test_alert(
                    AlertSeverity.CRITICAL,
                    f"Forward test metrics degraded: Stability {stability_score:.1f}, Validation {validation_score:.1f}",
                    min(stability_score, validation_score),
                    34.4,  # Current baseline
                    "metric_degradation"
                ))

            if alerts:
                await self.alert_system.save_alerts(alerts)
                await self._save_scheduled_alert_summary("monthly_forward_test_update", alerts)
                logger.info(f"Monthly forward test update completed with {len(alerts)} alerts")
            else:
                logger.info("Monthly forward test update completed - no alerts generated")

        except Exception as e:
            logger.error(f"Error in monthly forward test update: {e}")

    async def _check_performance_thresholds(self):
        """Check performance thresholds for immediate alerts"""
        try:
            if not self.performance_tracker:
                logger.warning("Performance tracker not available for threshold check")
                return

            current_metrics = await self.performance_tracker.get_current_metrics()
            if not current_metrics:
                return

            # Use existing alert system for threshold checks
            alerts = await self.alert_system.evaluate_performance_alerts(current_metrics)

            # Filter for only immediate/critical alerts during threshold checks
            critical_alerts = [a for a in alerts if a.severity in [AlertSeverity.CRITICAL, AlertSeverity.EMERGENCY]]

            if critical_alerts:
                await self.alert_system.save_alerts(critical_alerts)
                await self._save_scheduled_alert_summary("performance_threshold_check", critical_alerts)
                logger.warning(f"Performance threshold check generated {len(critical_alerts)} critical alerts")
            else:
                logger.debug("Performance threshold check completed - no critical alerts")

        except Exception as e:
            logger.error(f"Error in performance threshold check: {e}")

    async def _create_stability_alert(
        self,
        severity: AlertSeverity,
        message: str,
        current_value: float,
        expected_value: float,
        metric_type: str
    ):
        """Create stability-related alert"""
        from .performance_tracking import PerformanceAlert

        alert_id = f"stability_{metric_type}_{severity.value}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        deviation_pct = ((current_value - expected_value) / expected_value) * 100 if expected_value != 0 else 0

        return PerformanceAlert(
            alert_id=alert_id,
            timestamp=datetime.utcnow(),
            severity=severity,
            alert_type="Weekly Stability Monitoring",
            message=message,
            current_value=current_value,
            expected_value=expected_value,
            deviation_pct=deviation_pct,
            details={
                "metric_type": metric_type,
                "scheduled_check": True,
                "check_type": "weekly_stability"
            },
            action_required=severity == AlertSeverity.CRITICAL
        )

    async def _create_forward_test_alert(
        self,
        severity: AlertSeverity,
        message: str,
        current_value: float,
        expected_value: float,
        alert_type: str
    ):
        """Create forward test related alert"""
        from .performance_tracking import PerformanceAlert

        alert_id = f"forward_test_{alert_type}_{severity.value}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        deviation_pct = ((current_value - expected_value) / abs(expected_value)) * 100 if expected_value != 0 else 0

        return PerformanceAlert(
            alert_id=alert_id,
            timestamp=datetime.utcnow(),
            severity=severity,
            alert_type="Monthly Forward Test Update",
            message=message,
            current_value=current_value,
            expected_value=expected_value,
            deviation_pct=deviation_pct,
            details={
                "alert_type": alert_type,
                "scheduled_check": True,
                "check_type": "monthly_forward_test"
            },
            action_required=severity == AlertSeverity.CRITICAL
        )

    async def _save_scheduled_alert_summary(self, check_name: str, alerts: List):
        """Save summary of scheduled alert execution"""
        try:
            timestamp = datetime.utcnow()
            summary = {
                "check_name": check_name,
                "execution_timestamp": timestamp.isoformat(),
                "alerts_generated": len(alerts),
                "critical_count": len([a for a in alerts if a.severity == AlertSeverity.CRITICAL]),
                "warning_count": len([a for a in alerts if a.severity == AlertSeverity.WARNING]),
                "alert_details": [
                    {
                        "alert_id": alert.alert_id,
                        "severity": alert.severity.value,
                        "message": alert.message
                    } for alert in alerts
                ]
            }

            filename = f"scheduled_summary_{check_name}_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
            filepath = self.alerts_history_path / filename

            with open(filepath, 'w') as f:
                json.dump(summary, f, indent=2)

            logger.debug(f"Saved scheduled alert summary to {filepath}")

        except Exception as e:
            logger.error(f"Error saving scheduled alert summary: {e}")

    def get_schedule_status(self) -> Dict[str, Any]:
        """Get current schedule status and next run times"""
        try:
            status = {
                "scheduler_running": self.running,
                "scheduled_alerts": []
            }

            for alert_config in self.scheduled_alerts:
                alert_status = {
                    "name": alert_config.name,
                    "frequency": alert_config.frequency.value,
                    "enabled": alert_config.enabled,
                    "last_run": alert_config.last_run.isoformat() if alert_config.last_run else None,
                    "time_of_day": alert_config.time_of_day.strftime("%H:%M UTC")
                }

                # Calculate next run time
                if alert_config.enabled:
                    next_run = self._calculate_next_run_time(alert_config)
                    alert_status["next_run"] = next_run.isoformat() if next_run else None

                status["scheduled_alerts"].append(alert_status)

            return status

        except Exception as e:
            logger.error(f"Error getting schedule status: {e}")
            return {"error": str(e)}

    def _calculate_next_run_time(self, alert_config: ScheduledAlert) -> Optional[datetime]:
        """Calculate next run time for an alert"""
        try:
            now = datetime.utcnow()
            today = now.date()
            target_time = datetime.combine(today, alert_config.time_of_day)

            if alert_config.frequency == ScheduleFrequency.DAILY:
                if target_time > now:
                    return target_time
                else:
                    return target_time + timedelta(days=1)

            elif alert_config.frequency == ScheduleFrequency.WEEKLY:
                # Find next Monday
                days_until_monday = (7 - now.weekday()) % 7
                if days_until_monday == 0 and target_time > now:
                    next_monday = today
                else:
                    next_monday = today + timedelta(days=days_until_monday if days_until_monday > 0 else 7)
                return datetime.combine(next_monday, alert_config.time_of_day)

            elif alert_config.frequency == ScheduleFrequency.MONTHLY:
                # Find next 1st of month
                if today.day == 1 and target_time > now:
                    return target_time
                else:
                    next_month = today.replace(day=1) + timedelta(days=32)
                    next_first = next_month.replace(day=1)
                    return datetime.combine(next_first, alert_config.time_of_day)

            return None

        except Exception as e:
            logger.error(f"Error calculating next run time: {e}")
            return None


# Global instance
_alert_scheduler: Optional[PerformanceAlertScheduler] = None


def get_alert_scheduler() -> PerformanceAlertScheduler:
    """Get global performance alert scheduler instance"""
    global _alert_scheduler
    if _alert_scheduler is None:
        _alert_scheduler = PerformanceAlertScheduler()
    return _alert_scheduler