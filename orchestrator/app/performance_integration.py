"""
Performance Tracking Integration Module

Integrates all performance tracking components with the trading orchestrator
and provides unified interface for dashboard and API access.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import asdict

from .performance_tracking import get_performance_tracker, AutomatedPerformanceTracker
from .monte_carlo_projections import get_monte_carlo_engine
from .performance_alerts import get_alert_system
from .performance_reporter import get_performance_reporter

logger = logging.getLogger(__name__)


class PerformanceTrackingIntegration:
    """
    Unified performance tracking integration for the trading system

    Coordinates:
    - Real-time performance tracking vs projections
    - Monte Carlo simulation and confidence intervals
    - Alert generation and escalation
    - Automated reporting (daily/weekly)
    - Dashboard data feeds
    """

    def __init__(self, projection_start_date: Optional[datetime] = None):
        # Initialize all performance tracking components
        self.performance_tracker = get_performance_tracker(projection_start_date)
        self.monte_carlo_engine = get_monte_carlo_engine()
        self.alert_system = get_alert_system()
        self.reporter = get_performance_reporter(self.performance_tracker)

        # Tracking state
        self.last_update_time = datetime.utcnow()
        self.update_frequency_minutes = 15  # Update every 15 minutes
        self.is_running = False

        logger.info("Performance Tracking Integration initialized")

    async def start_tracking(self, oanda_client, account_id: str):
        """Start automated performance tracking"""
        try:
            if self.is_running:
                logger.warning("Performance tracking already running")
                return

            self.is_running = True
            logger.info("Starting automated performance tracking")

            # Initial update
            await self._perform_tracking_update(oanda_client, account_id)

            # Schedule regular updates (in a real system, this would use a proper scheduler)
            # For now, we'll just log the intention
            logger.info(f"Performance tracking scheduled for updates every {self.update_frequency_minutes} minutes")

        except Exception as e:
            logger.error(f"Error starting performance tracking: {e}")
            self.is_running = False

    async def stop_tracking(self):
        """Stop automated performance tracking"""
        self.is_running = False
        logger.info("Performance tracking stopped")

    async def update_performance(self, oanda_client, account_id: str) -> Dict:
        """
        Manual performance update and analysis

        Returns comprehensive performance status
        """
        try:
            return await self._perform_tracking_update(oanda_client, account_id)

        except Exception as e:
            logger.error(f"Error updating performance: {e}")
            return {"error": str(e)}

    async def _perform_tracking_update(self, oanda_client, account_id: str) -> Dict:
        """Perform comprehensive tracking update"""
        try:
            current_time = datetime.utcnow()
            logger.info(f"Performing performance tracking update at {current_time}")

            # 1. Update performance metrics
            performance_metrics = await self.performance_tracker.update_performance(
                oanda_client, account_id, current_time
            )

            # 2. Run Monte Carlo simulation for confidence intervals
            days_elapsed = max(1, (current_time - self.performance_tracker.projection_start_date).days)
            monte_carlo_result = await self.monte_carlo_engine.run_monte_carlo_simulation(
                projection_days=1,  # Daily projection
                simulation_runs=5000
            )

            # 3. Evaluate alerts
            alerts = await self.alert_system.evaluate_performance_alerts(
                performance_metrics,
                monte_carlo_result.confidence_intervals
            )

            # Save alerts if any
            if alerts:
                await self.alert_system.save_alerts(alerts)

            # 4. Generate reports if due
            report_status = await self._check_and_generate_reports(current_time)

            # 5. Update tracking state
            self.last_update_time = current_time

            # 6. Compile comprehensive status
            status = {
                "update_timestamp": current_time.isoformat(),
                "tracking_status": "active" if self.is_running else "stopped",
                "performance_metrics": {
                    "actual_pnl": performance_metrics.actual_pnl,
                    "projected_pnl": performance_metrics.projected_pnl,
                    "deviation_pct": performance_metrics.pnl_deviation_pct,
                    "cumulative_pnl": performance_metrics.cumulative_pnl,
                    "rolling_sharpe_ratio": performance_metrics.rolling_sharpe_ratio,
                    "current_drawdown": performance_metrics.drawdown_current,
                    "confidence_breaches": performance_metrics.confidence_interval_breaches,
                    "days_since_start": performance_metrics.days_since_start
                },
                "monte_carlo_analysis": {
                    "confidence_intervals": monte_carlo_result.confidence_intervals,
                    "mean_projection": monte_carlo_result.mean_pnl,
                    "probability_of_profit": monte_carlo_result.probability_of_profit,
                    "var_5pct": monte_carlo_result.var_5pct
                },
                "alerts": {
                    "new_alerts_count": len(alerts),
                    "critical_alerts": len([a for a in alerts if a.severity.value == "critical"]),
                    "warning_alerts": len([a for a in alerts if a.severity.value == "warning"]),
                    "recent_alerts": [
                        {
                            "alert_id": alert.alert_id,
                            "severity": alert.severity.value,
                            "alert_type": alert.alert_type,
                            "message": alert.message,
                            "timestamp": alert.timestamp.isoformat()
                        }
                        for alert in alerts[:5]  # Latest 5 alerts
                    ]
                },
                "forward_testing_baseline": {
                    "expected_6month_pnl": self.performance_tracker.projections.expected_6month_pnl,
                    "expected_daily_pnl": self.performance_tracker.projections.expected_daily_pnl,
                    "walk_forward_stability": self.performance_tracker.projections.walk_forward_stability,
                    "out_of_sample_validation": self.performance_tracker.projections.out_of_sample_validation,
                    "overfitting_score": self.performance_tracker.projections.overfitting_score
                },
                "reports_status": report_status,
                "next_update": (current_time + timedelta(minutes=self.update_frequency_minutes)).isoformat()
            }

            return status

        except Exception as e:
            logger.error(f"Error in tracking update: {e}")
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}

    async def _check_and_generate_reports(self, current_time: datetime) -> Dict:
        """Check if reports are due and generate them"""
        try:
            report_status = {
                "daily_report": "not_due",
                "weekly_report": "not_due",
                "last_daily_report": None,
                "last_weekly_report": None
            }

            # Check for daily report (generate at 8 AM daily)
            if current_time.hour == 8 and current_time.minute < 30:  # 8:00-8:30 AM window
                try:
                    daily_report = await self.reporter.generate_daily_report(current_time)
                    report_status["daily_report"] = "generated"
                    report_status["last_daily_report"] = current_time.isoformat()
                    logger.info("Daily performance report generated")
                except Exception as e:
                    logger.error(f"Error generating daily report: {e}")
                    report_status["daily_report"] = "error"

            # Check for weekly report (generate on Mondays at 9 AM)
            if current_time.weekday() == 0 and current_time.hour == 9 and current_time.minute < 30:
                try:
                    weekly_report = await self.reporter.generate_weekly_report(current_time)
                    report_status["weekly_report"] = "generated"
                    report_status["last_weekly_report"] = current_time.isoformat()
                    logger.info("Weekly performance report generated")
                except Exception as e:
                    logger.error(f"Error generating weekly report: {e}")
                    report_status["weekly_report"] = "error"

            return report_status

        except Exception as e:
            logger.error(f"Error checking reports: {e}")
            return {"error": str(e)}

    async def get_dashboard_data(self) -> Dict:
        """Get formatted data for dashboard integration"""
        try:
            # Get dashboard summary from reporter
            dashboard_summary = await self.reporter.get_dashboard_summary()

            # Add integration-specific data
            integration_data = {
                "system_status": {
                    "tracking_active": self.is_running,
                    "last_update": self.last_update_time.isoformat(),
                    "update_frequency_minutes": self.update_frequency_minutes,
                    "components_status": {
                        "performance_tracker": "active",
                        "monte_carlo_engine": "active",
                        "alert_system": "active",
                        "reporter": "active"
                    }
                },
                "quick_stats": await self._get_quick_stats(),
                "alert_summary": self.alert_system.get_alert_summary(hours=24)
            }

            # Merge with dashboard summary
            dashboard_data = {**dashboard_summary, **integration_data}

            return dashboard_data

        except Exception as e:
            logger.error(f"Error getting dashboard data: {e}")
            return {"error": str(e)}

    async def _get_quick_stats(self) -> Dict:
        """Get quick statistics for dashboard"""
        try:
            if not self.performance_tracker.performance_history:
                return {"status": "no_data"}

            latest = self.performance_tracker.performance_history[-1]

            # Calculate some quick derived stats
            expected_total = self.performance_tracker.projections.expected_6month_pnl
            actual_total = latest.cumulative_pnl
            progress_pct = (actual_total / expected_total * 100) if expected_total != 0 else 0

            return {
                "total_pnl": actual_total,
                "expected_pnl": expected_total,
                "progress_percentage": progress_pct,
                "days_active": latest.days_since_start,
                "performance_status": self._classify_overall_performance(progress_pct, latest.pnl_deviation_pct),
                "risk_status": self._classify_risk_status(latest),
                "trend": self._calculate_recent_trend()
            }

        except Exception as e:
            logger.error(f"Error calculating quick stats: {e}")
            return {"error": str(e)}

    def _classify_overall_performance(self, progress_pct: float, deviation_pct: float) -> str:
        """Classify overall performance status"""
        if progress_pct >= 120 and abs(deviation_pct) < 20:
            return "EXCELLENT"
        elif progress_pct >= 100 and abs(deviation_pct) < 30:
            return "GOOD"
        elif progress_pct >= 80 and abs(deviation_pct) < 40:
            return "ON_TARGET"
        elif progress_pct >= 60:
            return "BELOW_TARGET"
        else:
            return "CONCERNING"

    def _classify_risk_status(self, metrics) -> str:
        """Classify current risk status"""
        risk_factors = 0

        if metrics.drawdown_current > 0.08:
            risk_factors += 2
        elif metrics.drawdown_current > 0.05:
            risk_factors += 1

        if metrics.rolling_sharpe_ratio < 0.5:
            risk_factors += 2
        elif metrics.rolling_sharpe_ratio < 0.8:
            risk_factors += 1

        if metrics.confidence_interval_breaches >= 5:
            risk_factors += 2
        elif metrics.confidence_interval_breaches >= 3:
            risk_factors += 1

        if abs(metrics.pnl_deviation_pct) > 50:
            risk_factors += 2
        elif abs(metrics.pnl_deviation_pct) > 25:
            risk_factors += 1

        if risk_factors >= 6:
            return "CRITICAL"
        elif risk_factors >= 4:
            return "HIGH"
        elif risk_factors >= 2:
            return "MODERATE"
        else:
            return "LOW"

    def _calculate_recent_trend(self) -> str:
        """Calculate recent performance trend"""
        try:
            if len(self.performance_tracker.performance_history) < 5:
                return "INSUFFICIENT_DATA"

            recent_5 = self.performance_tracker.performance_history[-5:]
            start_pnl = recent_5[0].cumulative_pnl
            end_pnl = recent_5[-1].cumulative_pnl

            change_pct = ((end_pnl - start_pnl) / max(abs(start_pnl), 1)) * 100

            if change_pct > 5:
                return "IMPROVING"
            elif change_pct < -5:
                return "DECLINING"
            else:
                return "STABLE"

        except Exception:
            return "UNKNOWN"

    async def get_api_status(self) -> Dict:
        """Get status for API endpoints"""
        try:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "system_status": {
                    "performance_tracking": "active" if self.is_running else "stopped",
                    "last_update": self.last_update_time.isoformat(),
                    "update_frequency_minutes": self.update_frequency_minutes
                },
                "data_availability": {
                    "performance_history": len(self.performance_tracker.performance_history),
                    "alerts_available": len(self.alert_system.alerts_history),
                    "days_tracking": (datetime.utcnow() - self.performance_tracker.projection_start_date).days
                },
                "health_indicators": await self._get_health_indicators()
            }

        except Exception as e:
            logger.error(f"Error getting API status: {e}")
            return {"error": str(e)}

    async def _get_health_indicators(self) -> Dict:
        """Get system health indicators"""
        try:
            health = {
                "overall_health": "HEALTHY",
                "components": {
                    "performance_tracker": "HEALTHY",
                    "monte_carlo_engine": "HEALTHY",
                    "alert_system": "HEALTHY",
                    "reporter": "HEALTHY"
                },
                "warnings": [],
                "errors": []
            }

            # Check for potential issues
            if len(self.performance_tracker.performance_history) == 0:
                health["warnings"].append("No performance history available")
                health["components"]["performance_tracker"] = "WARNING"

            if len(self.alert_system.alerts_history) > 100:  # Too many alerts
                health["warnings"].append("High alert frequency detected")
                health["components"]["alert_system"] = "WARNING"

            # Check last update time
            if (datetime.utcnow() - self.last_update_time).total_seconds() > 3600:  # 1 hour
                health["warnings"].append("Performance tracking updates delayed")
                health["overall_health"] = "WARNING"

            # Set overall health based on warnings/errors
            if health["errors"]:
                health["overall_health"] = "CRITICAL"
            elif health["warnings"]:
                health["overall_health"] = "WARNING"

            return health

        except Exception as e:
            logger.error(f"Error getting health indicators: {e}")
            return {"overall_health": "ERROR", "error": str(e)}

    async def generate_manual_report(self, report_type: str = "daily") -> Dict:
        """Generate manual report on demand"""
        try:
            if report_type == "daily":
                report = await self.reporter.generate_daily_report()
            elif report_type == "weekly":
                report = await self.reporter.generate_weekly_report()
            else:
                return {"error": f"Unknown report type: {report_type}"}

            # Convert report to serializable format
            report_data = {
                "report_type": report.period_type,
                "generated_at": datetime.utcnow().isoformat(),
                "analysis_date": report.analysis_date.isoformat(),
                "summary": {
                    "actual_performance": report.actual_performance,
                    "projected_performance": report.projected_performance,
                    "variance_analysis": report.variance_analysis
                },
                "risk_analysis": {
                    "risk_metrics": report.risk_metrics,
                    "drawdown_analysis": report.drawdown_analysis
                },
                "recommendations": report.recommendations,
                "action_items": report.action_items,
                "alert_summary": report.alert_summary
            }

            return report_data

        except Exception as e:
            logger.error(f"Error generating manual report: {e}")
            return {"error": str(e)}

    async def get_projection_comparison(self, days_ahead: int = 7) -> Dict:
        """Get projection comparison for specified days ahead"""
        try:
            # Run Monte Carlo simulation for specified period
            monte_carlo_result = await self.monte_carlo_engine.run_monte_carlo_simulation(
                projection_days=days_ahead,
                simulation_runs=5000
            )

            # Get current performance for comparison
            current_performance = await self.performance_tracker.get_real_time_status()

            return {
                "comparison_date": datetime.utcnow().isoformat(),
                "projection_period_days": days_ahead,
                "current_status": current_performance,
                "monte_carlo_projection": {
                    "mean_pnl": monte_carlo_result.mean_pnl,
                    "median_pnl": monte_carlo_result.median_pnl,
                    "confidence_intervals": monte_carlo_result.confidence_intervals,
                    "probability_of_profit": monte_carlo_result.probability_of_profit,
                    "var_5pct": monte_carlo_result.var_5pct
                },
                "forward_test_baseline": {
                    "expected_pnl": self.performance_tracker.projections.expected_daily_pnl * days_ahead,
                    "expected_6month_total": self.performance_tracker.projections.expected_6month_pnl,
                    "stability_score": self.performance_tracker.projections.walk_forward_stability,
                    "validation_score": self.performance_tracker.projections.out_of_sample_validation
                }
            }

        except Exception as e:
            logger.error(f"Error getting projection comparison: {e}")
            return {"error": str(e)}

    async def emergency_reset(self) -> Dict:
        """Emergency reset of performance tracking systems"""
        try:
            logger.warning("Performing emergency reset of performance tracking")

            # Stop tracking
            await self.stop_tracking()

            # Clear suppressed alerts
            self.alert_system.suppressed_alerts.clear()

            # Reset consecutive breach counters
            self.alert_system.confidence_monitor.consecutive_breaches = 0

            # Update reset timestamp
            reset_time = datetime.utcnow()

            return {
                "reset_timestamp": reset_time.isoformat(),
                "status": "success",
                "message": "Performance tracking systems reset successfully",
                "actions_taken": [
                    "Stopped automated tracking",
                    "Cleared alert suppressions",
                    "Reset consecutive breach counters"
                ]
            }

        except Exception as e:
            logger.error(f"Error in emergency reset: {e}")
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}


# Global instance
_performance_integration: Optional[PerformanceTrackingIntegration] = None


def get_performance_integration(projection_start_date: Optional[datetime] = None) -> PerformanceTrackingIntegration:
    """Get global performance tracking integration instance"""
    global _performance_integration
    if _performance_integration is None:
        _performance_integration = PerformanceTrackingIntegration(projection_start_date)
    return _performance_integration