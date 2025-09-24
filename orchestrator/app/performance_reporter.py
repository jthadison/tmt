"""
Automated Performance Reporting System

Generates comprehensive daily/weekly performance reports comparing actual results
against projections with detailed analysis and recommendations.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
import statistics
from pathlib import Path

from .performance_tracking import AutomatedPerformanceTracker, PerformanceReport, PerformanceMetrics
from .monte_carlo_projections import get_monte_carlo_engine, MonteCarloResult
from .performance_alerts import get_alert_system

logger = logging.getLogger(__name__)


@dataclass
class ReportSchedule:
    """Report generation schedule configuration"""
    report_type: str
    frequency: str  # "daily", "weekly", "monthly"
    time_of_day: str  # "09:00", "17:00", etc.
    recipients: List[str]
    enabled: bool = True
    last_generated: Optional[datetime] = None
    next_due: Optional[datetime] = None


@dataclass
class PerformanceAnalysis:
    """Detailed performance analysis for reporting"""
    period_type: str
    analysis_date: datetime

    # Performance vs Projections
    actual_performance: Dict
    projected_performance: Dict
    variance_analysis: Dict

    # Monte Carlo Analysis
    monte_carlo_results: Optional[Dict]
    confidence_analysis: Dict

    # Risk Analysis
    risk_metrics: Dict
    drawdown_analysis: Dict
    volatility_analysis: Dict

    # Alert Summary
    alert_summary: Dict

    # Forward Testing Comparison
    forward_test_comparison: Dict

    # Recommendations
    recommendations: List[str]
    action_items: List[str]


class AutomatedPerformanceReporter:
    """
    Automated performance reporting system with comprehensive analysis

    Features:
    - Daily/weekly automated reports
    - Monte Carlo projection comparison
    - Forward testing baseline analysis
    - Alert integration and escalation
    - Trend analysis and forecasting
    """

    def __init__(self, performance_tracker: AutomatedPerformanceTracker):
        self.performance_tracker = performance_tracker
        self.monte_carlo = get_monte_carlo_engine()
        self.alert_system = get_alert_system()

        # Report configuration
        self.reports_dir = Path("performance_reports")
        self.reports_dir.mkdir(exist_ok=True)

        # Report schedules
        self.report_schedules = self._initialize_report_schedules()

        # Template configurations
        self.report_templates = self._initialize_report_templates()

        logger.info("Automated Performance Reporter initialized")

    def _initialize_report_schedules(self) -> List[ReportSchedule]:
        """Initialize default report schedules"""
        return [
            ReportSchedule(
                report_type="daily_summary",
                frequency="daily",
                time_of_day="08:00",
                recipients=["trading_team", "risk_management"],
                enabled=True
            ),
            ReportSchedule(
                report_type="weekly_analysis",
                frequency="weekly",
                time_of_day="09:00",
                recipients=["trading_team", "risk_management", "senior_management"],
                enabled=True
            ),
            ReportSchedule(
                report_type="monthly_comprehensive",
                frequency="monthly",
                time_of_day="10:00",
                recipients=["all_stakeholders"],
                enabled=True
            )
        ]

    def _initialize_report_templates(self) -> Dict:
        """Initialize report template configurations"""
        return {
            "daily_summary": {
                "title": "Daily Performance Summary",
                "sections": [
                    "executive_summary",
                    "performance_vs_projection",
                    "risk_metrics",
                    "alerts_summary",
                    "next_day_outlook"
                ],
                "charts": ["daily_pnl_trend", "confidence_intervals", "sharpe_evolution"],
                "format": "html"
            },
            "weekly_analysis": {
                "title": "Weekly Performance Analysis",
                "sections": [
                    "executive_summary",
                    "weekly_performance_review",
                    "monte_carlo_analysis",
                    "forward_test_comparison",
                    "risk_assessment",
                    "alert_analysis",
                    "recommendations"
                ],
                "charts": [
                    "weekly_pnl_performance",
                    "monte_carlo_confidence_bands",
                    "sharpe_ratio_evolution",
                    "drawdown_analysis",
                    "projection_accuracy"
                ],
                "format": "html"
            },
            "monthly_comprehensive": {
                "title": "Monthly Comprehensive Performance Report",
                "sections": [
                    "executive_summary",
                    "monthly_performance_overview",
                    "forward_test_validation",
                    "monte_carlo_validation",
                    "risk_management_review",
                    "deployment_phase_analysis",
                    "system_health_assessment",
                    "strategic_recommendations"
                ],
                "charts": [
                    "monthly_pnl_performance",
                    "forward_test_comparison",
                    "monte_carlo_validation",
                    "risk_evolution",
                    "alert_frequency_analysis",
                    "projection_accuracy_trends"
                ],
                "format": "html"
            }
        }

    async def generate_daily_report(
        self,
        report_date: Optional[datetime] = None,
        save_to_file: bool = True
    ) -> PerformanceAnalysis:
        """Generate comprehensive daily performance report"""
        try:
            report_date = report_date or datetime.utcnow()
            logger.info(f"Generating daily performance report for {report_date.date()}")

            # Get performance data
            if not self.performance_tracker.performance_history:
                logger.warning("No performance history available for daily report")
                return self._create_empty_analysis("daily", report_date)

            # Get latest metrics
            latest_metrics = self.performance_tracker.performance_history[-1]

            # Generate Monte Carlo analysis for validation
            monte_carlo_result = await self.monte_carlo.run_monte_carlo_simulation(1, 1000)  # 1-day projection

            # Perform comprehensive analysis
            analysis = await self._perform_daily_analysis(
                latest_metrics, monte_carlo_result, report_date
            )

            # Generate formatted report
            if save_to_file:
                await self._save_formatted_report(analysis, "daily")

            logger.info("Daily performance report generated successfully")
            return analysis

        except Exception as e:
            logger.error(f"Error generating daily report: {e}")
            return self._create_empty_analysis("daily", report_date or datetime.utcnow())

    async def generate_weekly_report(
        self,
        report_date: Optional[datetime] = None,
        save_to_file: bool = True
    ) -> PerformanceAnalysis:
        """Generate comprehensive weekly performance report"""
        try:
            report_date = report_date or datetime.utcnow()
            logger.info(f"Generating weekly performance report for week ending {report_date.date()}")

            # Get week's performance data
            week_start = report_date - timedelta(days=report_date.weekday())
            week_end = report_date

            week_metrics = [
                m for m in self.performance_tracker.performance_history
                if week_start <= m.timestamp <= week_end
            ]

            if not week_metrics:
                logger.warning("No performance data available for weekly report")
                return self._create_empty_analysis("weekly", report_date)

            # Generate Monte Carlo analysis for week projection
            monte_carlo_result = await self.monte_carlo.run_monte_carlo_simulation(7, 5000)

            # Perform comprehensive weekly analysis
            analysis = await self._perform_weekly_analysis(
                week_metrics, monte_carlo_result, report_date
            )

            # Generate formatted report
            if save_to_file:
                await self._save_formatted_report(analysis, "weekly")

            logger.info("Weekly performance report generated successfully")
            return analysis

        except Exception as e:
            logger.error(f"Error generating weekly report: {e}")
            return self._create_empty_analysis("weekly", report_date or datetime.utcnow())

    async def _perform_daily_analysis(
        self,
        metrics: PerformanceMetrics,
        monte_carlo: MonteCarloResult,
        report_date: datetime
    ) -> PerformanceAnalysis:
        """Perform detailed daily performance analysis"""
        try:
            # Actual vs Projected Performance
            actual_performance = {
                "daily_pnl": metrics.actual_pnl,
                "cumulative_pnl": metrics.cumulative_pnl,
                "rolling_sharpe": metrics.rolling_sharpe_ratio,
                "current_drawdown": metrics.drawdown_current,
                "trade_count": metrics.trade_count
            }

            projected_performance = {
                "daily_pnl": metrics.projected_pnl,
                "cumulative_projected": metrics.cumulative_projected_pnl,
                "monte_carlo_mean": monte_carlo.mean_pnl,
                "monte_carlo_median": monte_carlo.median_pnl
            }

            # Variance Analysis
            variance_analysis = {
                "pnl_variance": metrics.actual_pnl - metrics.projected_pnl,
                "pnl_variance_pct": metrics.pnl_deviation_pct,
                "cumulative_variance": metrics.cumulative_pnl - metrics.cumulative_projected_pnl,
                "performance_classification": self._classify_daily_performance(metrics.pnl_deviation_pct)
            }

            # Monte Carlo Analysis
            monte_carlo_analysis = {
                "actual_vs_confidence_95": self._check_confidence_position(
                    metrics.actual_pnl, monte_carlo.confidence_intervals.get("95%", (0, 0))
                ),
                "probability_score": self._calculate_probability_score(
                    metrics.actual_pnl, monte_carlo
                ),
                "var_analysis": {
                    "var_5pct": monte_carlo.var_5pct,
                    "var_1pct": monte_carlo.var_1pct,
                    "actual_vs_var": metrics.actual_pnl - monte_carlo.var_5pct
                }
            }

            # Confidence Analysis
            confidence_analysis = {
                "within_95_confidence": monte_carlo.confidence_intervals.get("95%", (0, 0))[0] <= metrics.actual_pnl <= monte_carlo.confidence_intervals.get("95%", (0, 0))[1],
                "within_80_confidence": monte_carlo.confidence_intervals.get("80%", (0, 0))[0] <= metrics.actual_pnl <= monte_carlo.confidence_intervals.get("80%", (0, 0))[1],
                "confidence_breach_count": metrics.confidence_interval_breaches,
                "breach_severity": "HIGH" if metrics.confidence_interval_breaches >= 5 else "MODERATE" if metrics.confidence_interval_breaches >= 3 else "LOW"
            }

            # Risk Metrics
            risk_metrics = {
                "current_drawdown": metrics.drawdown_current,
                "max_drawdown": metrics.drawdown_max,
                "rolling_sharpe": metrics.rolling_sharpe_ratio,
                "volatility_estimate": monte_carlo.std_deviation,
                "risk_level": self._assess_daily_risk_level(metrics)
            }

            # Drawdown Analysis
            drawdown_analysis = {
                "current_drawdown_pct": metrics.drawdown_current * 100,
                "drawdown_severity": "CRITICAL" if metrics.drawdown_current > 0.12 else "HIGH" if metrics.drawdown_current > 0.08 else "MODERATE" if metrics.drawdown_current > 0.05 else "LOW",
                "recovery_required": (1 / (1 - metrics.drawdown_current) - 1) * 100 if metrics.drawdown_current > 0 else 0,
                "historical_context": self._get_drawdown_context(metrics)
            }

            # Alert Summary
            alert_summary = self.alert_system.get_alert_summary(hours=24)

            # Forward Test Comparison
            forward_test_comparison = {
                "vs_expected_6month_pnl": {
                    "progress_pct": (metrics.cumulative_pnl / self.performance_tracker.projections.expected_6month_pnl) * 100,
                    "on_track": abs(metrics.pnl_deviation_pct) < 20,
                    "days_into_projection": metrics.days_since_start
                },
                "stability_concerns": {
                    "walk_forward_stability": self.performance_tracker.projections.walk_forward_stability,
                    "out_of_sample_validation": self.performance_tracker.projections.out_of_sample_validation,
                    "overfitting_risk": self.performance_tracker.projections.overfitting_score > 0.5
                }
            }

            # Generate recommendations
            recommendations = self._generate_daily_recommendations(
                metrics, monte_carlo, variance_analysis, risk_metrics
            )

            action_items = self._generate_daily_action_items(
                metrics, confidence_analysis, alert_summary
            )

            return PerformanceAnalysis(
                period_type="daily",
                analysis_date=report_date,
                actual_performance=actual_performance,
                projected_performance=projected_performance,
                variance_analysis=variance_analysis,
                monte_carlo_results=monte_carlo.__dict__,
                confidence_analysis=confidence_analysis,
                risk_metrics=risk_metrics,
                drawdown_analysis=drawdown_analysis,
                volatility_analysis={},  # Simplified for daily
                alert_summary=alert_summary,
                forward_test_comparison=forward_test_comparison,
                recommendations=recommendations,
                action_items=action_items
            )

        except Exception as e:
            logger.error(f"Error in daily analysis: {e}")
            return self._create_empty_analysis("daily", report_date)

    async def _perform_weekly_analysis(
        self,
        week_metrics: List[PerformanceMetrics],
        monte_carlo: MonteCarloResult,
        report_date: datetime
    ) -> PerformanceAnalysis:
        """Perform detailed weekly performance analysis"""
        try:
            if not week_metrics:
                return self._create_empty_analysis("weekly", report_date)

            # Calculate weekly aggregates
            latest_metrics = week_metrics[-1]
            week_start_pnl = week_metrics[0].cumulative_pnl
            week_end_pnl = latest_metrics.cumulative_pnl
            weekly_pnl = week_end_pnl - week_start_pnl

            # Weekly performance summary
            actual_performance = {
                "weekly_pnl": weekly_pnl,
                "cumulative_pnl": latest_metrics.cumulative_pnl,
                "avg_daily_pnl": weekly_pnl / len(week_metrics),
                "best_day": max(m.actual_pnl for m in week_metrics),
                "worst_day": min(m.actual_pnl for m in week_metrics),
                "positive_days": len([m for m in week_metrics if m.actual_pnl > 0]),
                "total_days": len(week_metrics),
                "weekly_sharpe": self._calculate_weekly_sharpe(week_metrics)
            }

            projected_performance = {
                "weekly_projected": self.performance_tracker.projections.expected_weekly_pnl,
                "monte_carlo_weekly": monte_carlo.mean_pnl,
                "confidence_intervals": monte_carlo.confidence_intervals
            }

            # Weekly variance analysis
            weekly_projection = self.performance_tracker.projections.expected_weekly_pnl
            variance_analysis = {
                "weekly_variance": weekly_pnl - weekly_projection,
                "weekly_variance_pct": ((weekly_pnl - weekly_projection) / max(abs(weekly_projection), 1)) * 100,
                "consistency_score": self._calculate_weekly_consistency(week_metrics),
                "performance_classification": self._classify_weekly_performance(weekly_pnl, weekly_projection)
            }

            # Enhanced Monte Carlo analysis
            monte_carlo_analysis = {
                "percentile_ranking": self._calculate_percentile_ranking(weekly_pnl, monte_carlo),
                "probability_of_result": self._calculate_result_probability(weekly_pnl, monte_carlo),
                "confidence_analysis": self._analyze_weekly_confidence(weekly_pnl, monte_carlo),
                "tail_risk_assessment": self._assess_tail_risk(weekly_pnl, monte_carlo)
            }

            # Risk metrics
            risk_metrics = {
                "weekly_volatility": statistics.stdev([m.actual_pnl for m in week_metrics]) if len(week_metrics) > 1 else 0,
                "max_daily_loss": min(m.actual_pnl for m in week_metrics),
                "max_intraweek_drawdown": max(m.drawdown_current for m in week_metrics),
                "sharpe_evolution": [m.rolling_sharpe_ratio for m in week_metrics],
                "risk_adjusted_return": weekly_pnl / max(statistics.stdev([m.actual_pnl for m in week_metrics]), 1) if len(week_metrics) > 1 else 0
            }

            # Volatility analysis
            volatility_analysis = {
                "realized_volatility": statistics.stdev([m.actual_pnl for m in week_metrics]) if len(week_metrics) > 1 else 0,
                "monte_carlo_volatility": monte_carlo.std_deviation,
                "volatility_ratio": (statistics.stdev([m.actual_pnl for m in week_metrics]) / monte_carlo.std_deviation) if monte_carlo.std_deviation > 0 and len(week_metrics) > 1 else 1,
                "volatility_clustering": self._analyze_volatility_clustering(week_metrics)
            }

            # Alert analysis
            alert_summary = self.alert_system.get_alert_summary(hours=168)  # 7 days

            # Forward test comparison with more detail
            forward_test_comparison = {
                "vs_expected_performance": {
                    "6month_progress": (latest_metrics.cumulative_pnl / self.performance_tracker.projections.expected_6month_pnl) * 100,
                    "weekly_vs_expected": (weekly_pnl / weekly_projection) * 100,
                    "trend_analysis": self._analyze_weekly_trend(week_metrics)
                },
                "model_validation": {
                    "walk_forward_stability": self.performance_tracker.projections.walk_forward_stability,
                    "out_of_sample_validation": self.performance_tracker.projections.out_of_sample_validation,
                    "overfitting_concerns": self.performance_tracker.projections.overfitting_score > 0.5,
                    "kurtosis_risk": self.performance_tracker.projections.kurtosis_exposure
                }
            }

            # Enhanced recommendations
            recommendations = self._generate_weekly_recommendations(
                actual_performance, variance_analysis, risk_metrics, monte_carlo_analysis
            )

            action_items = self._generate_weekly_action_items(
                variance_analysis, alert_summary, forward_test_comparison
            )

            return PerformanceAnalysis(
                period_type="weekly",
                analysis_date=report_date,
                actual_performance=actual_performance,
                projected_performance=projected_performance,
                variance_analysis=variance_analysis,
                monte_carlo_results=monte_carlo.__dict__,
                confidence_analysis=monte_carlo_analysis,
                risk_metrics=risk_metrics,
                drawdown_analysis={},  # Simplified for weekly
                volatility_analysis=volatility_analysis,
                alert_summary=alert_summary,
                forward_test_comparison=forward_test_comparison,
                recommendations=recommendations,
                action_items=action_items
            )

        except Exception as e:
            logger.error(f"Error in weekly analysis: {e}")
            return self._create_empty_analysis("weekly", report_date)

    def _classify_daily_performance(self, deviation_pct: float) -> str:
        """Classify daily performance based on deviation"""
        abs_deviation = abs(deviation_pct)
        if abs_deviation <= 10:
            return "ON_TARGET"
        elif abs_deviation <= 25:
            return "ACCEPTABLE_VARIANCE"
        elif abs_deviation <= 50:
            return "HIGH_VARIANCE"
        else:
            return "EXTREME_VARIANCE"

    def _classify_weekly_performance(self, actual: float, projected: float) -> str:
        """Classify weekly performance"""
        if projected == 0:
            return "NO_BASELINE"

        ratio = actual / projected
        if ratio >= 1.2:
            return "EXCELLENT"
        elif ratio >= 1.1:
            return "GOOD"
        elif ratio >= 0.9:
            return "ON_TARGET"
        elif ratio >= 0.8:
            return "BELOW_TARGET"
        else:
            return "CONCERNING"

    def _check_confidence_position(self, actual: float, interval: Tuple[float, float]) -> str:
        """Check position within confidence interval"""
        lower, upper = interval
        if actual < lower:
            return "BELOW_INTERVAL"
        elif actual > upper:
            return "ABOVE_INTERVAL"
        else:
            return "WITHIN_INTERVAL"

    def _calculate_probability_score(self, actual: float, monte_carlo: MonteCarloResult) -> float:
        """Calculate probability score for actual result"""
        try:
            if not monte_carlo.percentile_distribution:
                return 0.5

            # Find percentile of actual result
            percentiles = ["P5", "P10", "P25", "P50", "P75", "P90", "P95"]
            percentile_values = [monte_carlo.percentile_distribution.get(p, 0) for p in percentiles]

            # Find position
            for i, value in enumerate(percentile_values):
                if actual <= value:
                    return [0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95][i]

            return 0.99  # Above P95

        except Exception:
            return 0.5

    def _assess_daily_risk_level(self, metrics: PerformanceMetrics) -> str:
        """Assess daily risk level"""
        risk_factors = []

        if metrics.drawdown_current > 0.12:
            risk_factors.append("HIGH_DRAWDOWN")
        if metrics.rolling_sharpe_ratio < 0.5:
            risk_factors.append("LOW_SHARPE")
        if metrics.confidence_interval_breaches >= 5:
            risk_factors.append("CONFIDENCE_BREACHES")
        if abs(metrics.pnl_deviation_pct) > 50:
            risk_factors.append("HIGH_DEVIATION")

        if len(risk_factors) >= 3:
            return "CRITICAL"
        elif len(risk_factors) >= 2:
            return "HIGH"
        elif len(risk_factors) >= 1:
            return "MODERATE"
        else:
            return "LOW"

    def _get_drawdown_context(self, metrics: PerformanceMetrics) -> str:
        """Get drawdown context description"""
        if metrics.drawdown_current == 0:
            return "No current drawdown"
        elif metrics.drawdown_current < 0.02:
            return "Minor drawdown - normal trading variance"
        elif metrics.drawdown_current < 0.05:
            return "Moderate drawdown - monitor closely"
        elif metrics.drawdown_current < 0.08:
            return "Significant drawdown - risk management required"
        elif metrics.drawdown_current < 0.12:
            return "Large drawdown - immediate attention needed"
        else:
            return "Critical drawdown - emergency procedures may be required"

    def _calculate_weekly_sharpe(self, metrics: List[PerformanceMetrics]) -> float:
        """Calculate weekly Sharpe ratio"""
        try:
            if len(metrics) < 2:
                return 0.0

            daily_returns = [m.actual_pnl for m in metrics]
            mean_return = statistics.mean(daily_returns)
            return_std = statistics.stdev(daily_returns)

            if return_std == 0:
                return 0.0

            # Annualized Sharpe ratio
            return (mean_return / return_std) * (252 ** 0.5)

        except Exception:
            return 0.0

    def _calculate_weekly_consistency(self, metrics: List[PerformanceMetrics]) -> float:
        """Calculate weekly performance consistency score"""
        try:
            if len(metrics) < 2:
                return 0.0

            daily_returns = [m.actual_pnl for m in metrics]
            positive_days = len([r for r in daily_returns if r > 0])
            total_days = len(daily_returns)

            # Consistency score based on positive day ratio and volatility
            positive_ratio = positive_days / total_days
            volatility = statistics.stdev(daily_returns)
            mean_return = statistics.mean(daily_returns)

            # Higher score for more positive days and lower volatility
            consistency = positive_ratio * 0.7 + (1 - min(volatility / max(abs(mean_return), 1), 1)) * 0.3
            return min(1.0, max(0.0, consistency))

        except Exception:
            return 0.0

    def _generate_daily_recommendations(
        self,
        metrics: PerformanceMetrics,
        monte_carlo: MonteCarloResult,
        variance_analysis: Dict,
        risk_metrics: Dict
    ) -> List[str]:
        """Generate daily recommendations"""
        recommendations = []

        try:
            # Performance-based recommendations
            if abs(variance_analysis["pnl_variance_pct"]) > 50:
                recommendations.append("Review projection model accuracy - large deviations detected")

            if metrics.rolling_sharpe_ratio < 0.8:
                recommendations.append("Consider reducing position sizes - poor risk-adjusted returns")

            if metrics.drawdown_current > 0.08:
                recommendations.append("Implement additional risk controls - drawdown exceeds 8%")

            if metrics.confidence_interval_breaches >= 3:
                recommendations.append("Reassess Monte Carlo model parameters - multiple confidence breaches")

            # Forward testing specific
            if variance_analysis["performance_classification"] == "EXTREME_VARIANCE":
                recommendations.append("Investigate potential model overfitting concerns")

            # Risk management
            if risk_metrics["risk_level"] in ["HIGH", "CRITICAL"]:
                recommendations.append("Consider reducing trading exposure until performance stabilizes")

            # Default positive recommendation
            if not recommendations:
                recommendations.append("Performance within acceptable parameters - continue monitoring")

        except Exception as e:
            logger.error(f"Error generating daily recommendations: {e}")
            recommendations.append("Unable to generate recommendations due to system error")

        return recommendations[:5]  # Limit to top 5

    def _generate_daily_action_items(
        self,
        metrics: PerformanceMetrics,
        confidence_analysis: Dict,
        alert_summary: Dict
    ) -> List[str]:
        """Generate daily action items"""
        action_items = []

        try:
            # Critical actions
            if metrics.drawdown_current > 0.12:
                action_items.append("URGENT: Review emergency risk procedures")

            if confidence_analysis.get("breach_severity") == "HIGH":
                action_items.append("Validate Monte Carlo model assumptions")

            if alert_summary.get("critical_alerts", 0) > 0:
                action_items.append("Address critical performance alerts")

            # Regular monitoring
            if metrics.days_since_start % 7 == 0:  # Weekly
                action_items.append("Conduct weekly forward test validation")

            if metrics.days_since_start >= 30:  # Monthly
                action_items.append("Update Monte Carlo parameters with recent data")

        except Exception as e:
            logger.error(f"Error generating daily action items: {e}")

        return action_items

    def _generate_weekly_recommendations(
        self,
        performance: Dict,
        variance: Dict,
        risk: Dict,
        monte_carlo: Dict
    ) -> List[str]:
        """Generate weekly recommendations"""
        recommendations = []

        try:
            # Performance analysis
            if variance["performance_classification"] in ["BELOW_TARGET", "CONCERNING"]:
                recommendations.append("Review trading strategy parameters for underperformance")

            if performance["positive_days"] / performance["total_days"] < 0.5:
                recommendations.append("Analyze factors contributing to negative day frequency")

            if risk["weekly_volatility"] > 200:  # High volatility
                recommendations.append("Consider volatility-adjusted position sizing")

            # Monte Carlo validation
            percentile = monte_carlo.get("percentile_ranking", 50)
            if percentile < 20:
                recommendations.append("Investigate systematic underperformance vs Monte Carlo projections")

        except Exception as e:
            logger.error(f"Error generating weekly recommendations: {e}")

        return recommendations[:5]

    def _generate_weekly_action_items(
        self,
        variance: Dict,
        alerts: Dict,
        forward_test: Dict
    ) -> List[str]:
        """Generate weekly action items"""
        action_items = []

        try:
            if variance["weekly_variance_pct"] < -30:
                action_items.append("Conduct comprehensive model review")

            if forward_test["model_validation"]["overfitting_concerns"]:
                action_items.append("Implement overfitting mitigation measures")

        except Exception as e:
            logger.error(f"Error generating weekly action items: {e}")

        return action_items

    def _calculate_percentile_ranking(self, actual: float, monte_carlo: MonteCarloResult) -> float:
        """Calculate percentile ranking of actual result"""
        try:
            percentiles = [
                ("P5", 5), ("P10", 10), ("P25", 25), ("P50", 50),
                ("P75", 75), ("P90", 90), ("P95", 95)
            ]

            for p_name, p_value in percentiles:
                if actual <= monte_carlo.percentile_distribution.get(p_name, 0):
                    return p_value

            return 99  # Above 95th percentile

        except Exception:
            return 50  # Default to median

    def _calculate_result_probability(self, actual: float, monte_carlo: MonteCarloResult) -> float:
        """Calculate probability of achieving actual result"""
        # Simplified probability calculation
        try:
            if actual >= monte_carlo.mean_pnl:
                return monte_carlo.probability_of_profit
            else:
                return monte_carlo.probability_of_loss
        except Exception:
            return 0.5

    def _analyze_weekly_confidence(self, weekly_pnl: float, monte_carlo: MonteCarloResult) -> Dict:
        """Analyze weekly confidence intervals"""
        try:
            confidence_levels = ["95%", "90%", "80%", "68%"]
            analysis = {}

            for level in confidence_levels:
                interval = monte_carlo.confidence_intervals.get(level, (0, 0))
                lower, upper = interval
                within_interval = lower <= weekly_pnl <= upper
                analysis[f"within_{level}"] = within_interval

            return analysis

        except Exception:
            return {}

    def _assess_tail_risk(self, actual: float, monte_carlo: MonteCarloResult) -> Dict:
        """Assess tail risk based on actual vs Monte Carlo"""
        try:
            return {
                "vs_var_5pct": actual - monte_carlo.var_5pct,
                "vs_var_1pct": actual - monte_carlo.var_1pct,
                "tail_risk_level": "HIGH" if actual < monte_carlo.var_1pct else "MODERATE" if actual < monte_carlo.var_5pct else "LOW"
            }
        except Exception:
            return {"tail_risk_level": "UNKNOWN"}

    def _analyze_volatility_clustering(self, metrics: List[PerformanceMetrics]) -> Dict:
        """Analyze volatility clustering in returns"""
        try:
            if len(metrics) < 3:
                return {"insufficient_data": True}

            returns = [m.actual_pnl for m in metrics]
            volatilities = []

            # Calculate rolling volatility
            for i in range(2, len(returns)):
                recent_returns = returns[max(0, i-2):i+1]
                vol = statistics.stdev(recent_returns) if len(recent_returns) > 1 else 0
                volatilities.append(vol)

            if len(volatilities) < 2:
                return {"insufficient_data": True}

            # Analyze clustering
            avg_volatility = statistics.mean(volatilities)
            vol_std = statistics.stdev(volatilities)

            return {
                "average_volatility": avg_volatility,
                "volatility_std": vol_std,
                "clustering_coefficient": vol_std / avg_volatility if avg_volatility > 0 else 0
            }

        except Exception:
            return {"error": True}

    def _analyze_weekly_trend(self, metrics: List[PerformanceMetrics]) -> Dict:
        """Analyze weekly performance trend"""
        try:
            if len(metrics) < 3:
                return {"trend": "INSUFFICIENT_DATA"}

            returns = [m.actual_pnl for m in metrics]
            start_return = returns[0]
            end_return = returns[-1]

            # Calculate trend
            if end_return > start_return * 1.1:
                trend = "IMPROVING"
            elif end_return < start_return * 0.9:
                trend = "DECLINING"
            else:
                trend = "STABLE"

            return {
                "trend": trend,
                "start_return": start_return,
                "end_return": end_return,
                "total_change": end_return - start_return
            }

        except Exception:
            return {"trend": "ERROR"}

    async def _save_formatted_report(self, analysis: PerformanceAnalysis, report_type: str):
        """Save formatted report to file"""
        try:
            timestamp = analysis.analysis_date.strftime("%Y%m%d_%H%M%S")
            filename = f"performance_report_{report_type}_{timestamp}.json"
            filepath = self.reports_dir / filename

            # Convert analysis to dictionary for JSON serialization
            report_data = {
                "report_metadata": {
                    "period_type": analysis.period_type,
                    "analysis_date": analysis.analysis_date.isoformat(),
                    "generated_at": datetime.utcnow().isoformat(),
                    "report_version": "1.0"
                },
                "performance_summary": {
                    "actual_performance": analysis.actual_performance,
                    "projected_performance": analysis.projected_performance,
                    "variance_analysis": analysis.variance_analysis
                },
                "risk_analysis": {
                    "risk_metrics": analysis.risk_metrics,
                    "drawdown_analysis": analysis.drawdown_analysis,
                    "volatility_analysis": analysis.volatility_analysis
                },
                "monte_carlo_analysis": analysis.monte_carlo_results,
                "confidence_analysis": analysis.confidence_analysis,
                "forward_test_comparison": analysis.forward_test_comparison,
                "alert_summary": analysis.alert_summary,
                "recommendations": analysis.recommendations,
                "action_items": analysis.action_items
            }

            with open(filepath, 'w') as f:
                json.dump(report_data, f, indent=2)

            logger.info(f"Formatted report saved: {filepath}")

        except Exception as e:
            logger.error(f"Error saving formatted report: {e}")

    def _create_empty_analysis(self, period_type: str, report_date: datetime) -> PerformanceAnalysis:
        """Create empty analysis structure"""
        return PerformanceAnalysis(
            period_type=period_type,
            analysis_date=report_date,
            actual_performance={},
            projected_performance={},
            variance_analysis={},
            monte_carlo_results=None,
            confidence_analysis={},
            risk_metrics={},
            drawdown_analysis={},
            volatility_analysis={},
            alert_summary={},
            forward_test_comparison={},
            recommendations=["Insufficient data for analysis"],
            action_items=["Ensure performance tracking system is collecting data"]
        )

    async def get_dashboard_summary(self) -> Dict:
        """Get summary data for dashboard integration"""
        try:
            if not self.performance_tracker.performance_history:
                return {"status": "no_data"}

            latest_metrics = self.performance_tracker.performance_history[-1]

            # Generate quick Monte Carlo for current day
            monte_carlo = await self.monte_carlo.run_monte_carlo_simulation(1, 1000)

            return {
                "status": "active",
                "last_update": latest_metrics.timestamp.isoformat(),
                "current_performance": {
                    "actual_pnl": latest_metrics.actual_pnl,
                    "projected_pnl": latest_metrics.projected_pnl,
                    "deviation_pct": latest_metrics.pnl_deviation_pct,
                    "classification": self._classify_daily_performance(latest_metrics.pnl_deviation_pct)
                },
                "risk_status": {
                    "current_drawdown": latest_metrics.drawdown_current,
                    "rolling_sharpe": latest_metrics.rolling_sharpe_ratio,
                    "confidence_breaches": latest_metrics.confidence_interval_breaches,
                    "risk_level": self._assess_daily_risk_level(latest_metrics)
                },
                "monte_carlo": {
                    "confidence_95": monte_carlo.confidence_intervals.get("95%", (0, 0)),
                    "mean_projection": monte_carlo.mean_pnl,
                    "probability_of_profit": monte_carlo.probability_of_profit
                },
                "alerts": self.alert_system.get_alert_summary(hours=24),
                "next_reports": {
                    "daily": (datetime.utcnow() + timedelta(days=1)).isoformat(),
                    "weekly": self._get_next_monday().isoformat()
                }
            }

        except Exception as e:
            logger.error(f"Error getting dashboard summary: {e}")
            return {"status": "error", "message": str(e)}

    def _get_next_monday(self) -> datetime:
        """Get next Monday date"""
        today = datetime.utcnow()
        days_ahead = 7 - today.weekday()  # Monday is 0
        return today + timedelta(days=days_ahead)


# Global instance
_performance_reporter: Optional[AutomatedPerformanceReporter] = None


def get_performance_reporter(performance_tracker: AutomatedPerformanceTracker) -> AutomatedPerformanceReporter:
    """Get global performance reporter instance"""
    global _performance_reporter
    if _performance_reporter is None:
        _performance_reporter = AutomatedPerformanceReporter(performance_tracker)
    return _performance_reporter