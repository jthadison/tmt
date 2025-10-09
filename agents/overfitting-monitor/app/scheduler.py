"""
Scheduled Monitoring Job - Story 11.4, Task 2

Hourly overfitting score calculation and monitoring.
"""

import logging
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .monitor import OverfittingMonitor
from .alert_service import AlertService
from .performance_tracker import PerformanceTracker
from .database import get_database
from .models import OverfittingScore, AlertLevel

logger = logging.getLogger(__name__)


class MonitoringScheduler:
    """
    Scheduled monitoring job manager

    Runs hourly overfitting calculations and performance checks.
    """

    def __init__(
        self,
        monitor: OverfittingMonitor,
        alert_service: AlertService,
        performance_tracker: PerformanceTracker,
        baseline_parameters: Dict[str, Any],
        current_parameters_provider: Any  # Callable that returns current params
    ):
        """
        Initialize monitoring scheduler

        @param monitor: OverfittingMonitor instance
        @param alert_service: AlertService instance
        @param performance_tracker: PerformanceTracker instance
        @param baseline_parameters: Baseline parameters for comparison
        @param current_parameters_provider: Callable that returns current parameters
        """
        self.monitor = monitor
        self.alert_service = alert_service
        self.performance_tracker = performance_tracker
        self.baseline_parameters = baseline_parameters
        self.current_parameters_provider = current_parameters_provider

        self.scheduler = AsyncIOScheduler()
        self.running = False

        # Expected backtest metrics (loaded from configuration)
        self.expected_backtest_sharpe = 1.8
        self.expected_backtest_win_rate = 60.0
        self.expected_backtest_profit_factor = 2.0

    async def start(self):
        """Start scheduled monitoring"""
        if self.running:
            logger.warning("Scheduler already running")
            return

        # Schedule hourly overfitting calculation
        self.scheduler.add_job(
            self._calculate_overfitting_task,
            CronTrigger(minute=0),  # Run at the top of every hour
            id="overfitting_calculation",
            name="Hourly Overfitting Calculation",
            replace_existing=True
        )

        # Schedule parameter drift tracking (every 6 hours)
        self.scheduler.add_job(
            self._track_parameter_drift_task,
            CronTrigger(hour="*/6", minute=15),
            id="parameter_drift_tracking",
            name="Parameter Drift Tracking",
            replace_existing=True
        )

        # Schedule performance degradation check (every 4 hours)
        self.scheduler.add_job(
            self._check_performance_degradation_task,
            CronTrigger(hour="*/4", minute=30),
            id="performance_degradation_check",
            name="Performance Degradation Check",
            replace_existing=True
        )

        # Start scheduler
        self.scheduler.start()
        self.running = True

        logger.info("Monitoring scheduler started")

        # Run initial calculation immediately
        await self._calculate_overfitting_task()

    async def stop(self):
        """Stop scheduled monitoring"""
        if not self.running:
            return

        self.scheduler.shutdown(wait=True)
        self.running = False

        logger.info("Monitoring scheduler stopped")

    async def _calculate_overfitting_task(self):
        """
        Hourly overfitting score calculation task

        Calculates overfitting score and checks thresholds.
        """
        try:
            logger.info("Starting overfitting score calculation")

            # Get current parameters from configuration
            current_params = await self._get_current_parameters()

            if not current_params:
                logger.warning("No current parameters available, skipping calculation")
                return

            # Calculate overfitting score
            score = self.monitor.calculate_overfitting_score(current_params)

            # Store in database
            db = await get_database()
            await db.store_overfitting_score(score)

            logger.info(
                f"Overfitting score calculated and stored: {score.score:.3f} "
                f"(alert_level={score.alert_level.value})"
            )

            # Check thresholds and create alerts
            alert = await self.alert_service.check_overfitting_thresholds(
                overfitting_score=score.score,
                warning_threshold=self.monitor.warning_threshold,
                critical_threshold=self.monitor.critical_threshold
            )

            if alert:
                logger.warning(f"Overfitting alert created: {alert.severity.value}")

        except Exception as e:
            logger.error(f"Error in overfitting calculation task: {e}", exc_info=True)

    async def _track_parameter_drift_task(self):
        """
        Parameter drift tracking task

        Tracks parameter changes over time (7-day, 30-day trends).
        """
        try:
            logger.info("Starting parameter drift tracking")

            db = await get_database()
            current_params = await self._get_current_parameters()

            if not current_params:
                logger.warning("No current parameters available, skipping drift tracking")
                return

            # Get current time
            now = datetime.now(timezone.utc)
            time_7d_ago = now - timedelta(days=7)
            time_30d_ago = now - timedelta(days=30)

            # Track drift for each parameter in each session
            for session, params in current_params.items():
                for param_name, current_value in params.items():
                    if param_name not in self.baseline_parameters:
                        continue

                    baseline_value = self.baseline_parameters[param_name]

                    # Get historical values for this parameter
                    history_7d = await db.get_parameter_drift_history(
                        param_name, time_7d_ago, now
                    )
                    history_30d = await db.get_parameter_drift_history(
                        param_name, time_30d_ago, now
                    )

                    # Extract values
                    values_7d = [h['current_value'] for h in history_7d]
                    values_30d = [h['current_value'] for h in history_30d]

                    # Calculate drift
                    drift = self.monitor.calculate_parameter_drift(
                        param_name=f"{session}_{param_name}",
                        current_value=current_value,
                        baseline_value=baseline_value,
                        historical_values_7d=values_7d,
                        historical_values_30d=values_30d
                    )

                    # Store drift data
                    await db.store_parameter_drift(drift)

                    # Check drift thresholds
                    exceeds, severity = self.monitor.check_drift_threshold(
                        drift.drift_7d_pct, drift.drift_30d_pct
                    )

                    if exceeds:
                        # Create drift alert
                        await self.alert_service.check_drift_threshold(
                            parameter_name=drift.parameter_name,
                            drift_pct=max(abs(drift.drift_7d_pct), abs(drift.drift_30d_pct)),
                            max_drift_pct=self.monitor.max_drift_pct
                        )

            logger.info("Parameter drift tracking completed")

        except Exception as e:
            logger.error(f"Error in parameter drift tracking task: {e}", exc_info=True)

    async def _check_performance_degradation_task(self):
        """
        Performance degradation check task

        Compares live vs backtest performance.
        """
        try:
            logger.info("Starting performance degradation check")

            # Calculate performance metrics
            metrics = self.performance_tracker.compare_performance(
                backtest_sharpe=self.expected_backtest_sharpe,
                backtest_win_rate=self.expected_backtest_win_rate,
                backtest_profit_factor=self.expected_backtest_profit_factor
            )

            # Store metrics in database
            db = await get_database()
            await db.store_performance_metrics(metrics)

            logger.info(
                f"Performance metrics stored: "
                f"Sharpe {metrics.live_sharpe:.2f} vs {metrics.backtest_sharpe:.2f}, "
                f"degradation={metrics.degradation_score:.3f}"
            )

            # Check performance degradation thresholds
            alert = await self.alert_service.check_performance_degradation(
                live_sharpe=metrics.live_sharpe,
                backtest_sharpe=metrics.backtest_sharpe,
                threshold_ratio=self.performance_tracker.degradation_threshold
            )

            if alert:
                logger.warning(
                    f"Performance degradation alert created: {alert.severity.value}"
                )

            # Check for regime changes
            regime_change, description = self.performance_tracker.detect_regime_change()

            if regime_change:
                # Create regime change alert
                await self.alert_service.create_alert(
                    severity=AlertLevel.WARNING,
                    metric="regime_change",
                    value=1.0,
                    threshold=0.5,
                    message=f"Regime change detected: {description}",
                    recommendation="Review market conditions and consider parameter re-optimization."
                )

        except Exception as e:
            logger.error(f"Error in performance degradation check task: {e}", exc_info=True)

    async def _get_current_parameters(self) -> Dict[str, Dict[str, Any]]:
        """
        Get current trading parameters

        @returns: Dictionary of session-specific parameters
        """
        try:
            # Call the parameters provider (could be API call, config read, etc.)
            if callable(self.current_parameters_provider):
                params = await self.current_parameters_provider()
                return params
            else:
                return self.current_parameters_provider

        except Exception as e:
            logger.error(f"Error getting current parameters: {e}")
            return {}

    def set_expected_backtest_metrics(
        self,
        sharpe: float,
        win_rate: float,
        profit_factor: float
    ):
        """
        Update expected backtest metrics

        @param sharpe: Expected Sharpe ratio
        @param win_rate: Expected win rate %
        @param profit_factor: Expected profit factor
        """
        self.expected_backtest_sharpe = sharpe
        self.expected_backtest_win_rate = win_rate
        self.expected_backtest_profit_factor = profit_factor

        logger.info(
            f"Updated expected backtest metrics: "
            f"Sharpe={sharpe:.2f}, WR={win_rate:.1f}%, PF={profit_factor:.2f}"
        )
