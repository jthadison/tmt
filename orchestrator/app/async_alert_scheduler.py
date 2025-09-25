"""
Async Performance Alert Scheduler with Context Management

Replaces the thread-based scheduler with proper async context management,
retry logic, and configurable schedule times.
"""

import asyncio
import logging
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path
from contextlib import asynccontextmanager
import functools

from .performance_alerts import get_alert_system
from .performance_tracking import PerformanceTracker, AlertSeverity
from .monte_carlo_projections import get_monte_carlo_engine
from .alert_schedule_config import get_schedule_config, AlertScheduleConfig

logger = logging.getLogger(__name__)


class ScheduleFrequency(Enum):
    """Schedule frequency types"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass
class RetryConfig:
    """Retry configuration for failed alert executions"""
    max_attempts: int = 3
    initial_delay: float = 60.0  # seconds
    backoff_multiplier: float = 2.0
    max_delay: float = 300.0  # 5 minutes max


@dataclass
class AlertExecution:
    """Alert execution tracking"""
    alert_name: str
    execution_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    success: bool = False
    error_message: Optional[str] = None
    attempt_count: int = 1
    retry_after: Optional[datetime] = None


@dataclass
class ScheduledAlert:
    """Enhanced scheduled alert configuration"""
    name: str
    frequency: ScheduleFrequency
    time_of_day: time
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    alert_function: Optional[str] = None
    retry_config: RetryConfig = field(default_factory=RetryConfig)
    execution_history: List[AlertExecution] = field(default_factory=list)


class AsyncPerformanceAlertScheduler:
    """
    Async performance alert scheduler with proper context management

    Features:
    - Async/await throughout for proper concurrency
    - Configurable schedule times via environment variables
    - Retry logic with exponential backoff
    - Proper context management with async context managers
    - Enhanced error handling and recovery
    """

    def __init__(self, config: Optional[AlertScheduleConfig] = None):
        self.config = config or get_schedule_config()
        self.alert_system = get_alert_system()
        self.performance_tracker = None
        self.monte_carlo = get_monte_carlo_engine()

        # Async state management
        self._running = False
        self._scheduler_task: Optional[asyncio.Task] = None
        self._alert_tasks: Dict[str, asyncio.Task] = {}
        self._shutdown_event = asyncio.Event()

        # Schedule configuration
        self.scheduled_alerts = self._initialize_scheduled_alerts()

        # Alert storage
        self.alerts_history_path = Path("performance_alerts/scheduled")
        self.alerts_history_path.mkdir(parents=True, exist_ok=True)

        logger.info("Async Performance Alert Scheduler initialized")

    def _initialize_scheduled_alerts(self) -> List[ScheduledAlert]:
        """Initialize scheduled alerts with configurable times"""
        return [
            ScheduledAlert(
                name="daily_pnl_check",
                frequency=ScheduleFrequency.DAILY,
                time_of_day=self.config.get_daily_pnl_time(),
                alert_function="check_daily_pnl_vs_projection",
                retry_config=RetryConfig(
                    max_attempts=self.config.max_retry_attempts,
                    initial_delay=self.config.retry_delay_seconds,
                    backoff_multiplier=self.config.retry_backoff_multiplier
                )
            ),
            ScheduledAlert(
                name="weekly_stability_check",
                frequency=ScheduleFrequency.WEEKLY,
                time_of_day=self.config.get_weekly_stability_time(),
                alert_function="check_weekly_stability_score",
                retry_config=RetryConfig(
                    max_attempts=self.config.max_retry_attempts,
                    initial_delay=self.config.retry_delay_seconds,
                    backoff_multiplier=self.config.retry_backoff_multiplier
                )
            ),
            ScheduledAlert(
                name="monthly_forward_test_update",
                frequency=ScheduleFrequency.MONTHLY,
                time_of_day=self.config.get_monthly_forward_time(),
                alert_function="update_monthly_forward_test",
                retry_config=RetryConfig(
                    max_attempts=self.config.max_retry_attempts,
                    initial_delay=self.config.retry_delay_seconds,
                    backoff_multiplier=self.config.retry_backoff_multiplier
                )
            ),
            ScheduledAlert(
                name="performance_threshold_check",
                frequency=ScheduleFrequency.DAILY,
                time_of_day=self.config.get_threshold_time_1(),
                alert_function="check_performance_thresholds",
                retry_config=RetryConfig(max_attempts=2)  # Shorter retry for thresholds
            ),
            ScheduledAlert(
                name="evening_performance_check",
                frequency=ScheduleFrequency.DAILY,
                time_of_day=self.config.get_threshold_time_2(),
                alert_function="check_performance_thresholds",
                retry_config=RetryConfig(max_attempts=2)
            )
        ]

    @asynccontextmanager
    async def _scheduler_context(self):
        """Async context manager for proper scheduler lifecycle"""
        try:
            logger.info("Starting performance alert scheduler context")

            # Initialize performance tracker
            from .performance_tracking import get_performance_tracker
            self.performance_tracker = get_performance_tracker()

            # Start scheduler loop
            self._running = True
            self._scheduler_task = asyncio.create_task(self._scheduler_loop())

            yield self

        except Exception as e:
            logger.error(f"Error in scheduler context: {e}")
            raise
        finally:
            logger.info("Stopping performance alert scheduler context")
            await self._shutdown()

    async def start(self):
        """Start the async scheduler"""
        if self._running:
            logger.warning("Scheduler already running")
            return

        try:
            async with self._scheduler_context():
                # Keep running until shutdown
                await self._shutdown_event.wait()

        except Exception as e:
            logger.error(f"Error starting scheduler: {e}")
            raise

    async def stop(self):
        """Stop the async scheduler"""
        if not self._running:
            return

        logger.info("Stopping async performance alert scheduler")
        self._shutdown_event.set()

    async def _shutdown(self):
        """Internal shutdown procedure"""
        self._running = False

        # Cancel scheduler task
        if self._scheduler_task and not self._scheduler_task.done():
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass

        # Cancel all alert tasks
        for task in self._alert_tasks.values():
            if not task.done():
                task.cancel()

        if self._alert_tasks:
            await asyncio.gather(*self._alert_tasks.values(), return_exceptions=True)

        self._alert_tasks.clear()
        logger.info("Scheduler shutdown complete")

    async def _scheduler_loop(self):
        """Main scheduler loop with async/await"""
        try:
            while self._running:
                current_time = datetime.utcnow()

                # Check each alert for execution
                for alert_config in self.scheduled_alerts:
                    if not alert_config.enabled:
                        continue

                    # Check if it's time to run
                    if self._should_execute_alert(alert_config, current_time):
                        await self._schedule_alert_execution(alert_config)

                    # Check for retry executions
                    await self._check_retry_executions(alert_config, current_time)

                # Sleep for 30 seconds before next check
                try:
                    await asyncio.sleep(30)
                except asyncio.CancelledError:
                    break

        except asyncio.CancelledError:
            logger.info("Scheduler loop cancelled")
        except Exception as e:
            logger.error(f"Error in scheduler loop: {e}")

    def _should_execute_alert(self, alert_config: ScheduledAlert, current_time: datetime) -> bool:
        """Check if alert should be executed"""
        try:
            # Calculate next run time
            next_run = self._calculate_next_run_time(alert_config)
            if next_run is None:
                return False

            # Update next_run if not set
            if alert_config.next_run is None:
                alert_config.next_run = next_run

            # Check if current time is past next run time
            if current_time >= alert_config.next_run:
                # Update next run time for future
                alert_config.next_run = self._calculate_next_run_time(alert_config)
                return True

            return False

        except Exception as e:
            logger.error(f"Error checking execution time for {alert_config.name}: {e}")
            return False

    async def _schedule_alert_execution(self, alert_config: ScheduledAlert):
        """Schedule alert execution with retry logic"""
        try:
            execution_id = f"{alert_config.name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

            # Cancel any existing task for this alert
            if alert_config.name in self._alert_tasks:
                existing_task = self._alert_tasks[alert_config.name]
                if not existing_task.done():
                    existing_task.cancel()

            # Create new execution task
            task = asyncio.create_task(
                self._execute_alert_with_retry(alert_config, execution_id)
            )
            self._alert_tasks[alert_config.name] = task

            logger.info(f"Scheduled alert execution: {alert_config.name} ({execution_id})")

        except Exception as e:
            logger.error(f"Error scheduling alert execution for {alert_config.name}: {e}")

    async def _execute_alert_with_retry(self, alert_config: ScheduledAlert, execution_id: str):
        """Execute alert with retry logic"""
        execution = AlertExecution(
            alert_name=alert_config.name,
            execution_id=execution_id,
            started_at=datetime.utcnow()
        )

        try:
            for attempt in range(1, alert_config.retry_config.max_attempts + 1):
                execution.attempt_count = attempt

                try:
                    logger.info(f"Executing alert {alert_config.name} (attempt {attempt})")

                    # Execute the alert function
                    await self._execute_alert_function(alert_config)

                    # Success
                    execution.success = True
                    execution.completed_at = datetime.utcnow()
                    alert_config.last_run = execution.completed_at

                    logger.info(f"Alert {alert_config.name} executed successfully")
                    break

                except Exception as e:
                    logger.error(f"Alert {alert_config.name} failed (attempt {attempt}): {e}")
                    execution.error_message = str(e)

                    # Check if we should retry
                    if attempt < alert_config.retry_config.max_attempts:
                        delay = self._calculate_retry_delay(alert_config.retry_config, attempt)
                        execution.retry_after = datetime.utcnow() + timedelta(seconds=delay)

                        logger.info(f"Retrying {alert_config.name} in {delay} seconds")
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"Alert {alert_config.name} failed after {attempt} attempts")
                        execution.completed_at = datetime.utcnow()

        except asyncio.CancelledError:
            logger.info(f"Alert execution cancelled: {alert_config.name}")
            execution.error_message = "Execution cancelled"
            execution.completed_at = datetime.utcnow()
        except Exception as e:
            logger.error(f"Unexpected error executing alert {alert_config.name}: {e}")
            execution.error_message = f"Unexpected error: {e}"
            execution.completed_at = datetime.utcnow()
        finally:
            # Record execution
            alert_config.execution_history.append(execution)

            # Keep only last 10 executions
            if len(alert_config.execution_history) > 10:
                alert_config.execution_history = alert_config.execution_history[-10:]

            # Clean up task reference
            if alert_config.name in self._alert_tasks:
                del self._alert_tasks[alert_config.name]

    def _calculate_retry_delay(self, retry_config: RetryConfig, attempt: int) -> float:
        """Calculate retry delay with exponential backoff"""
        delay = retry_config.initial_delay * (retry_config.backoff_multiplier ** (attempt - 1))
        return min(delay, retry_config.max_delay)

    async def _check_retry_executions(self, alert_config: ScheduledAlert, current_time: datetime):
        """Check for pending retry executions"""
        # This is handled within _execute_alert_with_retry now
        pass

    async def _execute_alert_function(self, alert_config: ScheduledAlert):
        """Execute the specific alert function"""
        function_name = alert_config.alert_function

        if function_name == "check_daily_pnl_vs_projection":
            await self._check_daily_pnl_vs_projection()
        elif function_name == "check_weekly_stability_score":
            await self._check_weekly_stability_score()
        elif function_name == "update_monthly_forward_test":
            await self._update_monthly_forward_test()
        elif function_name == "check_performance_thresholds":
            await self._check_performance_thresholds()
        else:
            raise ValueError(f"Unknown alert function: {function_name}")

    # Alert function implementations (moved from original scheduler)
    async def _check_daily_pnl_vs_projection(self):
        """Daily P&L vs projection comparison"""
        try:
            if not self.performance_tracker:
                logger.warning("Performance tracker not available for daily P&L check")
                return

            current_metrics = await self.performance_tracker.get_current_metrics()
            if not current_metrics:
                logger.warning("No performance metrics available for daily check")
                return

            projections = await self.monte_carlo.get_daily_projections()
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
            raise

    async def _check_weekly_stability_score(self):
        """Weekly stability score monitoring"""
        try:
            if not self.performance_tracker:
                logger.warning("Performance tracker not available for stability check")
                return

            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=7)

            stability_metrics = await self.performance_tracker.calculate_stability_score(
                start_date, end_date
            )

            if not stability_metrics:
                logger.warning("No stability metrics available for weekly check")
                return

            alerts = []

            # Check stability thresholds from config
            walk_forward_score = stability_metrics.get("walk_forward_stability", 0)
            if walk_forward_score < 50:
                alerts.append(await self._create_stability_alert(
                    AlertSeverity.CRITICAL,
                    f"Walk-forward stability critically low: {walk_forward_score:.1f}/100",
                    walk_forward_score, 60.0, "walk_forward_stability"
                ))
            elif walk_forward_score < 60:
                alerts.append(await self._create_stability_alert(
                    AlertSeverity.WARNING,
                    f"Walk-forward stability below target: {walk_forward_score:.1f}/100",
                    walk_forward_score, 60.0, "walk_forward_stability"
                ))

            out_of_sample_score = stability_metrics.get("out_of_sample_validation", 0)
            if out_of_sample_score < 50:
                alerts.append(await self._create_stability_alert(
                    AlertSeverity.CRITICAL,
                    f"Out-of-sample validation critically low: {out_of_sample_score:.1f}/100",
                    out_of_sample_score, 70.0, "out_of_sample_validation"
                ))
            elif out_of_sample_score < 70:
                alerts.append(await self._create_stability_alert(
                    AlertSeverity.WARNING,
                    f"Out-of-sample validation below target: {out_of_sample_score:.1f}/100",
                    out_of_sample_score, 70.0, "out_of_sample_validation"
                ))

            if alerts:
                await self.alert_system.save_alerts(alerts)
                await self._save_scheduled_alert_summary("weekly_stability_check", alerts)
                logger.info(f"Weekly stability check completed with {len(alerts)} alerts")
            else:
                logger.info("Weekly stability check completed - no alerts generated")

        except Exception as e:
            logger.error(f"Error in weekly stability score check: {e}")
            raise

    async def _update_monthly_forward_test(self):
        """Monthly forward test updates and validation"""
        try:
            logger.info("Starting monthly forward test update")

            updated_projections = await self.monte_carlo.run_monthly_forward_test_update()
            if not updated_projections:
                raise Exception("Failed to generate updated forward test projections")

            alerts = []
            previous_projections = await self.monte_carlo.get_previous_month_projections()

            if previous_projections:
                current_expected = updated_projections.get("expected_monthly_pnl", 0)
                previous_expected = previous_projections.get("expected_monthly_pnl", 0)

                if previous_expected != 0:
                    change_pct = ((current_expected - previous_expected) / abs(previous_expected)) * 100

                    if abs(change_pct) > 25:
                        severity = AlertSeverity.CRITICAL if abs(change_pct) > 50 else AlertSeverity.WARNING
                        alerts.append(await self._create_forward_test_alert(
                            severity,
                            f"Monthly forward test projection changed {change_pct:+.1f}%",
                            current_expected, previous_expected, "expected_pnl_change"
                        ))

            stability_score = updated_projections.get("walk_forward_stability", 0)
            validation_score = updated_projections.get("out_of_sample_validation", 0)

            if stability_score < 34.4 or validation_score < 17.4:
                alerts.append(await self._create_forward_test_alert(
                    AlertSeverity.CRITICAL,
                    f"Forward test metrics degraded: Stability {stability_score:.1f}, Validation {validation_score:.1f}",
                    min(stability_score, validation_score), 34.4, "metric_degradation"
                ))

            if alerts:
                await self.alert_system.save_alerts(alerts)
                await self._save_scheduled_alert_summary("monthly_forward_test_update", alerts)
                logger.info(f"Monthly forward test update completed with {len(alerts)} alerts")
            else:
                logger.info("Monthly forward test update completed - no alerts generated")

        except Exception as e:
            logger.error(f"Error in monthly forward test update: {e}")
            raise

    async def _check_performance_thresholds(self):
        """Check performance thresholds for immediate alerts"""
        try:
            if not self.performance_tracker:
                logger.warning("Performance tracker not available for threshold check")
                return

            current_metrics = await self.performance_tracker.get_current_metrics()
            if not current_metrics:
                return

            alerts = await self.alert_system.evaluate_performance_alerts(current_metrics)
            critical_alerts = [a for a in alerts if a.severity in [AlertSeverity.CRITICAL, AlertSeverity.EMERGENCY]]

            if critical_alerts:
                await self.alert_system.save_alerts(critical_alerts)
                await self._save_scheduled_alert_summary("performance_threshold_check", critical_alerts)
                logger.warning(f"Performance threshold check generated {len(critical_alerts)} critical alerts")
            else:
                logger.debug("Performance threshold check completed - no critical alerts")

        except Exception as e:
            logger.error(f"Error in performance threshold check: {e}")
            raise

    # Helper methods (similar to original implementation but async)
    async def _create_stability_alert(self, severity: AlertSeverity, message: str,
                                    current_value: float, expected_value: float, metric_type: str):
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

    async def _create_forward_test_alert(self, severity: AlertSeverity, message: str,
                                       current_value: float, expected_value: float, alert_type: str):
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
                days_until_target = (7 - now.weekday()) % 7
                if days_until_target == 0 and target_time > now:
                    next_target = today
                else:
                    next_target = today + timedelta(days=days_until_target if days_until_target > 0 else 7)
                return datetime.combine(next_target, alert_config.time_of_day)

            elif alert_config.frequency == ScheduleFrequency.MONTHLY:
                if today.day == self.config.monthly_forward_day and target_time > now:
                    return target_time
                else:
                    next_month = today.replace(day=1) + timedelta(days=32)
                    next_first = next_month.replace(day=self.config.monthly_forward_day)
                    return datetime.combine(next_first, alert_config.time_of_day)

            return None

        except Exception as e:
            logger.error(f"Error calculating next run time: {e}")
            return None

    def get_schedule_status(self) -> Dict[str, Any]:
        """Get current schedule status and execution history"""
        try:
            status = {
                "scheduler_running": self._running,
                "configuration": self.config.to_dict(),
                "scheduled_alerts": []
            }

            for alert_config in self.scheduled_alerts:
                alert_status = {
                    "name": alert_config.name,
                    "frequency": alert_config.frequency.value,
                    "enabled": alert_config.enabled,
                    "time_of_day": alert_config.time_of_day.strftime("%H:%M UTC"),
                    "last_run": alert_config.last_run.isoformat() if alert_config.last_run else None,
                    "next_run": alert_config.next_run.isoformat() if alert_config.next_run else None,
                    "retry_config": {
                        "max_attempts": alert_config.retry_config.max_attempts,
                        "initial_delay": alert_config.retry_config.initial_delay,
                        "backoff_multiplier": alert_config.retry_config.backoff_multiplier
                    },
                    "recent_executions": [
                        {
                            "execution_id": ex.execution_id,
                            "started_at": ex.started_at.isoformat(),
                            "completed_at": ex.completed_at.isoformat() if ex.completed_at else None,
                            "success": ex.success,
                            "attempt_count": ex.attempt_count,
                            "error_message": ex.error_message
                        }
                        for ex in alert_config.execution_history[-5:]  # Last 5 executions
                    ]
                }

                status["scheduled_alerts"].append(alert_status)

            return status

        except Exception as e:
            logger.error(f"Error getting schedule status: {e}")
            return {"error": str(e)}


# Global instance
_async_alert_scheduler: Optional[AsyncPerformanceAlertScheduler] = None


def get_async_alert_scheduler() -> AsyncPerformanceAlertScheduler:
    """Get global async performance alert scheduler instance"""
    global _async_alert_scheduler
    if _async_alert_scheduler is None:
        _async_alert_scheduler = AsyncPerformanceAlertScheduler()
    return _async_alert_scheduler