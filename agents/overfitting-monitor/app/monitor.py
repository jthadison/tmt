"""
OverfittingMonitor Core Class - Story 11.4, Task 1

Real-time monitoring of parameter drift and overfitting risk.
"""

import logging
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
from decimal import Decimal

from .models import (
    OverfittingScore,
    AlertLevel,
    ParameterDrift,
    ParameterComparison
)

logger = logging.getLogger(__name__)


class OverfittingMonitor:
    """
    Core overfitting monitoring system

    Calculates overfitting scores by comparing current session-specific parameters
    against universal baseline, tracking parameter drift over time.
    """

    def __init__(
        self,
        baseline_parameters: Dict[str, Any],
        warning_threshold: float = 0.3,
        critical_threshold: float = 0.5,
        max_drift_pct: float = 15.0
    ):
        """
        Initialize overfitting monitor

        @param baseline_parameters: Universal baseline parameters for comparison
        @param warning_threshold: Overfitting score threshold for warnings (default: 0.3)
        @param critical_threshold: Overfitting score threshold for critical alerts (default: 0.5)
        @param max_drift_pct: Maximum allowed parameter drift % (default: 15%)
        """
        self.baseline = baseline_parameters
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.max_drift_pct = max_drift_pct

    def calculate_overfitting_score(
        self,
        current_params: Dict[str, Dict[str, Any]]
    ) -> OverfittingScore:
        """
        Calculate overfitting score for current parameters

        Formula combines:
        - Average deviation (40%): Mean deviation across all sessions
        - Maximum deviation (40%): Worst-case session deviation
        - Std deviation (20%): Parameter stability component

        @param current_params: Dict mapping session name to parameters
        @returns: OverfittingScore with calculated metrics

        Example:
            >>> monitor = OverfittingMonitor(baseline={"confidence_threshold": 55.0})
            >>> params = {
            ...     "London": {"confidence_threshold": 72.0},
            ...     "NY": {"confidence_threshold": 70.0}
            ... }
            >>> score = monitor.calculate_overfitting_score(params)
            >>> score.score
            0.28
        """
        deviations = []
        session_deviations = {}

        # Calculate deviation for each session
        for session, params in current_params.items():
            session_dev = self._calculate_session_deviation(params)
            deviations.append(session_dev)
            session_deviations[session] = session_dev

            logger.debug(
                f"Session '{session}' deviation: {session_dev:.3f}"
            )

        if not deviations:
            logger.warning("No session parameters provided for overfitting calculation")
            return OverfittingScore(
                time=datetime.now(timezone.utc),
                score=0.0,
                avg_deviation=0.0,
                max_deviation=0.0,
                session_deviations={},
                alert_level=AlertLevel.NORMAL
            )

        # Calculate aggregate metrics
        avg_deviation = float(np.mean(deviations))
        max_deviation = float(np.max(deviations))
        std_deviation = float(np.std(deviations)) if len(deviations) > 1 else 0.0

        # Combined overfitting score (weighted average)
        # 40% average, 40% max, 20% std dev
        overfitting_score = min(
            1.0,
            avg_deviation * 0.4 + max_deviation * 0.4 + std_deviation * 0.2
        )

        # Determine alert level
        if overfitting_score >= self.critical_threshold:
            alert_level = AlertLevel.CRITICAL
        elif overfitting_score >= self.warning_threshold:
            alert_level = AlertLevel.WARNING
        else:
            alert_level = AlertLevel.NORMAL

        logger.info(
            f"Overfitting score calculated: {overfitting_score:.3f} "
            f"(avg={avg_deviation:.3f}, max={max_deviation:.3f}, "
            f"std={std_deviation:.3f}, alert={alert_level.value})"
        )

        return OverfittingScore(
            time=datetime.now(timezone.utc),
            score=overfitting_score,
            avg_deviation=avg_deviation,
            max_deviation=max_deviation,
            session_deviations=session_deviations,
            alert_level=alert_level
        )

    def _calculate_session_deviation(self, params: Dict[str, Any]) -> float:
        """
        Calculate deviation for a single session's parameters

        Compares each parameter against baseline and normalizes deviations.

        @param params: Session parameters
        @returns: Normalized deviation score (0-1+)
        """
        deviations = []

        for param_name, param_value in params.items():
            if param_name not in self.baseline:
                logger.debug(f"Parameter '{param_name}' not in baseline, skipping")
                continue

            baseline_value = self.baseline[param_name]

            # Normalize deviation based on parameter type
            if param_name == "confidence_threshold":
                # Confidence threshold: normalize by 50 (half of 0-100 range)
                dev = abs(param_value - baseline_value) / 50.0
            elif param_name == "min_risk_reward":
                # Risk reward: normalize by 3 (typical range 1-4)
                dev = abs(param_value - baseline_value) / 3.0
            elif param_name == "vpa_threshold":
                # VPA threshold: already in 0-1 range
                dev = abs(param_value - baseline_value)
            else:
                # Generic: percentage deviation
                if baseline_value != 0:
                    dev = abs(param_value - baseline_value) / abs(baseline_value)
                else:
                    dev = abs(param_value)

            deviations.append(dev)
            logger.debug(
                f"Parameter '{param_name}': current={param_value}, "
                f"baseline={baseline_value}, deviation={dev:.3f}"
            )

        # Average deviation across all parameters
        if not deviations:
            return 0.0

        return float(np.mean(deviations))

    def calculate_parameter_drift(
        self,
        param_name: str,
        current_value: float,
        baseline_value: float,
        historical_values_7d: List[float],
        historical_values_30d: List[float]
    ) -> ParameterDrift:
        """
        Calculate parameter drift over time

        @param param_name: Parameter name
        @param current_value: Current parameter value
        @param baseline_value: Baseline value
        @param historical_values_7d: Historical values for past 7 days
        @param historical_values_30d: Historical values for past 30 days
        @returns: ParameterDrift with calculated metrics
        """
        # Deviation from baseline
        if baseline_value != 0:
            deviation_pct = ((current_value - baseline_value) / abs(baseline_value)) * 100
        else:
            deviation_pct = 0.0

        # 7-day drift (current vs 7 days ago)
        if historical_values_7d and len(historical_values_7d) > 0:
            value_7d_ago = historical_values_7d[0]
            if value_7d_ago != 0:
                drift_7d_pct = ((current_value - value_7d_ago) / abs(value_7d_ago)) * 100
            else:
                drift_7d_pct = 0.0
        else:
            drift_7d_pct = 0.0

        # 30-day drift (current vs 30 days ago)
        if historical_values_30d and len(historical_values_30d) > 0:
            value_30d_ago = historical_values_30d[0]
            if value_30d_ago != 0:
                drift_30d_pct = ((current_value - value_30d_ago) / abs(value_30d_ago)) * 100
            else:
                drift_30d_pct = 0.0
        else:
            drift_30d_pct = 0.0

        logger.debug(
            f"Parameter '{param_name}' drift: "
            f"current={current_value:.2f}, baseline={baseline_value:.2f}, "
            f"7d_drift={drift_7d_pct:.1f}%, 30d_drift={drift_30d_pct:.1f}%"
        )

        return ParameterDrift(
            time=datetime.now(timezone.utc),
            parameter_name=param_name,
            current_value=current_value,
            baseline_value=baseline_value,
            deviation_pct=deviation_pct,
            drift_7d_pct=drift_7d_pct,
            drift_30d_pct=drift_30d_pct
        )

    def compare_parameters(
        self,
        current_params: Dict[str, Dict[str, Any]]
    ) -> ParameterComparison:
        """
        Compare current parameters against baseline

        @param current_params: Current session-specific parameters
        @returns: ParameterComparison with deviation analysis
        """
        all_deviations = {}

        # Calculate deviations for all sessions
        for session, params in current_params.items():
            for param_name, param_value in params.items():
                if param_name in self.baseline:
                    baseline_value = self.baseline[param_name]
                    if baseline_value != 0:
                        deviation_pct = abs(
                            (param_value - baseline_value) / baseline_value
                        ) * 100
                    else:
                        deviation_pct = 0.0

                    key = f"{session}_{param_name}"
                    all_deviations[key] = deviation_pct

        # Assess overfitting risk based on deviations
        if not all_deviations:
            risk_level = "LOW"
        else:
            max_deviation = max(all_deviations.values())
            avg_deviation = np.mean(list(all_deviations.values()))

            if max_deviation > 50 or avg_deviation > 30:
                risk_level = "CRITICAL"
            elif max_deviation > 30 or avg_deviation > 20:
                risk_level = "HIGH"
            elif max_deviation > 15 or avg_deviation > 10:
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"

        logger.info(
            f"Parameter comparison: {len(all_deviations)} parameters compared, "
            f"risk_level={risk_level}"
        )

        return ParameterComparison(
            current_parameters=current_params,
            baseline_parameters=self.baseline,
            deviations=all_deviations,
            overfitting_risk=risk_level
        )

    def check_drift_threshold(
        self,
        drift_7d_pct: float,
        drift_30d_pct: float
    ) -> Tuple[bool, str]:
        """
        Check if parameter drift exceeds thresholds

        @param drift_7d_pct: 7-day drift percentage
        @param drift_30d_pct: 30-day drift percentage
        @returns: Tuple of (exceeds_threshold, severity)
        """
        if abs(drift_7d_pct) > self.max_drift_pct:
            return True, "CRITICAL"
        elif abs(drift_30d_pct) > self.max_drift_pct:
            return True, "WARNING"
        else:
            return False, "NORMAL"
