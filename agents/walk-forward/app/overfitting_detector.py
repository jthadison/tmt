"""
Overfitting Detection - Story 11.3, Task 4

Detects overfitting in walk-forward optimization by analyzing:
- In-sample vs out-of-sample performance degradation
- Parameter deviation from universal baseline
- Performance stability across windows
"""

import numpy as np
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class OverfittingAlert:
    """Represents an overfitting detection alert"""
    severity: str  # 'warning', 'critical'
    message: str
    metric: str
    value: float
    threshold: float


class OverfittingDetector:
    """
    Detects overfitting in parameter optimization

    Implements multiple overfitting detection strategies:
    1. Performance degradation: Compare in-sample vs out-of-sample performance
    2. Parameter stability: Analyze parameter variance across windows
    3. Baseline deviation: Check deviation from universal baseline
    """

    def __init__(
        self,
        warning_threshold: float = 0.3,
        critical_threshold: float = 0.5,
        max_baseline_deviation_pct: float = 20.0
    ):
        """
        Initialize overfitting detector

        Args:
            warning_threshold: Overfitting score threshold for warnings (default: 0.3)
            critical_threshold: Overfitting score threshold for critical alerts (default: 0.5)
            max_baseline_deviation_pct: Max allowed deviation from baseline % (default: 20%)
        """
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.max_baseline_deviation_pct = max_baseline_deviation_pct

    def calculate_overfitting_score(
        self,
        in_sample_sharpe: float,
        out_of_sample_sharpe: float
    ) -> float:
        """
        Calculate overfitting score

        Formula: (in_sample_sharpe - out_of_sample_sharpe) / in_sample_sharpe

        Interpretation:
        - < 0.3: Acceptable (OOS >= 70% of IS)
        - 0.3 - 0.5: Warning (potential overfitting)
        - > 0.5: Critical (severe overfitting)

        Args:
            in_sample_sharpe: In-sample (training) Sharpe ratio
            out_of_sample_sharpe: Out-of-sample (testing) Sharpe ratio

        Returns:
            Overfitting score (0 to 1+, lower is better)

        Example:
            >>> detector = OverfittingDetector()
            >>> score = detector.calculate_overfitting_score(2.0, 1.4)
            >>> score
            0.3  # Warning threshold
        """

        # Handle edge cases
        if in_sample_sharpe <= 0:
            logger.warning(
                f"In-sample Sharpe ratio is non-positive ({in_sample_sharpe}), "
                "cannot calculate meaningful overfitting score"
            )
            return 1.0  # Maximum overfitting

        # Calculate degradation ratio
        degradation = in_sample_sharpe - out_of_sample_sharpe
        overfitting_score = degradation / in_sample_sharpe

        # Clamp to reasonable range [0, 1.5]
        # Score > 1.0 means OOS performance is negative
        overfitting_score = max(0.0, min(1.5, overfitting_score))

        return overfitting_score

    def check_overfitting(
        self,
        in_sample_sharpe: float,
        out_of_sample_sharpe: float
    ) -> List[OverfittingAlert]:
        """
        Check for overfitting and generate alerts

        Args:
            in_sample_sharpe: In-sample Sharpe ratio
            out_of_sample_sharpe: Out-of-sample Sharpe ratio

        Returns:
            List of overfitting alerts (empty if no overfitting detected)
        """

        alerts = []

        # Calculate overfitting score
        score = self.calculate_overfitting_score(in_sample_sharpe, out_of_sample_sharpe)

        # Check against thresholds
        if score >= self.critical_threshold:
            alerts.append(OverfittingAlert(
                severity='critical',
                message=(
                    f"CRITICAL OVERFITTING: Out-of-sample performance "
                    f"({out_of_sample_sharpe:.2f}) is only "
                    f"{(1 - score) * 100:.0f}% of in-sample ({in_sample_sharpe:.2f})"
                ),
                metric='overfitting_score',
                value=score,
                threshold=self.critical_threshold
            ))
        elif score >= self.warning_threshold:
            alerts.append(OverfittingAlert(
                severity='warning',
                message=(
                    f"POTENTIAL OVERFITTING: Out-of-sample performance "
                    f"({out_of_sample_sharpe:.2f}) is only "
                    f"{(1 - score) * 100:.0f}% of in-sample ({in_sample_sharpe:.2f})"
                ),
                metric='overfitting_score',
                value=score,
                threshold=self.warning_threshold
            ))

        return alerts

    def calculate_parameter_stability(
        self,
        parameter_values: List[float],
        param_name: str
    ) -> Tuple[float, float]:
        """
        Calculate parameter stability across windows

        Uses coefficient of variation (CV) to measure stability:
        CV = std_dev / mean

        Lower CV indicates more stable parameters.

        Args:
            parameter_values: List of parameter values across windows
            param_name: Parameter name (for logging)

        Returns:
            Tuple of (coefficient_of_variation, stability_score)
            - CV: 0-1+, lower is more stable
            - Stability score: 0-1, higher is more stable (1 - normalized_CV)
        """

        if len(parameter_values) < 2:
            logger.warning(
                f"Not enough data to calculate stability for '{param_name}' "
                f"({len(parameter_values)} values)"
            )
            return 0.0, 1.0

        values = np.array(parameter_values)

        # Calculate coefficient of variation
        mean_val = np.mean(values)
        std_val = np.std(values)

        if mean_val == 0:
            logger.warning(
                f"Mean value is zero for '{param_name}', "
                "cannot calculate coefficient of variation"
            )
            return 0.0, 1.0

        cv = std_val / abs(mean_val)

        # Calculate stability score (inverse of CV, clamped to [0, 1])
        # CV of 0 = perfect stability (score 1.0)
        # CV of 1+ = high variance (score approaching 0)
        stability_score = 1.0 / (1.0 + cv)

        logger.debug(
            f"Parameter '{param_name}': mean={mean_val:.3f}, "
            f"std={std_val:.3f}, CV={cv:.3f}, stability={stability_score:.3f}"
        )

        return cv, stability_score

    def calculate_overall_stability(
        self,
        parameter_evolution: Dict[str, List[float]]
    ) -> float:
        """
        Calculate overall parameter stability across all parameters

        Args:
            parameter_evolution: Dict mapping parameter name to list of values across windows

        Returns:
            Overall stability score (0-1, higher is better)
        """

        if not parameter_evolution:
            return 1.0

        stability_scores = []

        for param_name, values in parameter_evolution.items():
            _, stability = self.calculate_parameter_stability(values, param_name)
            stability_scores.append(stability)

        # Overall stability is average of individual stabilities
        overall_stability = np.mean(stability_scores)

        logger.info(
            f"Overall parameter stability: {overall_stability:.3f} "
            f"(based on {len(stability_scores)} parameters)"
        )

        return overall_stability

    def check_baseline_deviation(
        self,
        optimized_params: Dict[str, Any],
        baseline_params: Dict[str, Any]
    ) -> List[OverfittingAlert]:
        """
        Check if optimized parameters deviate too much from baseline

        Large deviations from universal baseline may indicate overfitting
        to specific market conditions.

        Args:
            optimized_params: Optimized parameters
            baseline_params: Baseline (universal) parameters

        Returns:
            List of alerts for parameters with excessive deviation
        """

        alerts = []

        for param_name in optimized_params.keys():
            if param_name not in baseline_params:
                continue

            optimized_val = optimized_params[param_name]
            baseline_val = baseline_params[param_name]

            # Calculate percentage deviation
            if baseline_val == 0:
                continue  # Skip if baseline is zero

            deviation_pct = abs((optimized_val - baseline_val) / baseline_val) * 100

            if deviation_pct > self.max_baseline_deviation_pct:
                alerts.append(OverfittingAlert(
                    severity='warning',
                    message=(
                        f"Parameter '{param_name}' deviates {deviation_pct:.1f}% "
                        f"from baseline (optimized={optimized_val:.2f}, "
                        f"baseline={baseline_val:.2f})"
                    ),
                    metric=f'{param_name}_baseline_deviation',
                    value=deviation_pct,
                    threshold=self.max_baseline_deviation_pct
                ))

        return alerts

    def generate_overfitting_report(
        self,
        windows: List[Dict[str, Any]],
        parameter_evolution: Dict[str, List[float]],
        baseline_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate comprehensive overfitting analysis report

        Args:
            windows: List of window results
            parameter_evolution: Parameter values across windows
            baseline_params: Baseline parameters

        Returns:
            Dict containing overfitting analysis results
        """

        all_alerts = []

        # Check overfitting for each window
        for idx, window in enumerate(windows):
            window_alerts = self.check_overfitting(
                in_sample_sharpe=window.get('in_sample_sharpe', 0.0),
                out_of_sample_sharpe=window.get('out_of_sample_sharpe', 0.0)
            )

            for alert in window_alerts:
                alert.message = f"Window {idx}: {alert.message}"
                all_alerts.append(alert)

        # Check baseline deviation for each window
        for idx, window in enumerate(windows):
            optimized_params = window.get('optimized_params', {})
            baseline_alerts = self.check_baseline_deviation(
                optimized_params, baseline_params
            )

            for alert in baseline_alerts:
                alert.message = f"Window {idx}: {alert.message}"
                all_alerts.append(alert)

        # Calculate parameter stability
        overall_stability = self.calculate_overall_stability(parameter_evolution)

        # Calculate average overfitting score
        overfitting_scores = [
            self.calculate_overfitting_score(
                w.get('in_sample_sharpe', 0.0),
                w.get('out_of_sample_sharpe', 0.0)
            )
            for w in windows
        ]
        avg_overfitting_score = np.mean(overfitting_scores) if overfitting_scores else 0.0

        # Determine overall overfitting status
        critical_alerts = [a for a in all_alerts if a.severity == 'critical']
        warning_alerts = [a for a in all_alerts if a.severity == 'warning']

        if critical_alerts:
            overfitting_status = 'CRITICAL'
        elif warning_alerts:
            overfitting_status = 'WARNING'
        else:
            overfitting_status = 'ACCEPTABLE'

        report = {
            'overfitting_status': overfitting_status,
            'avg_overfitting_score': avg_overfitting_score,
            'parameter_stability_score': overall_stability,
            'total_alerts': len(all_alerts),
            'critical_alerts': len(critical_alerts),
            'warning_alerts': len(warning_alerts),
            'alerts': [
                {
                    'severity': a.severity,
                    'message': a.message,
                    'metric': a.metric,
                    'value': a.value,
                    'threshold': a.threshold
                }
                for a in all_alerts
            ]
        }

        logger.info(
            f"Overfitting Report: {overfitting_status} - "
            f"Avg Score: {avg_overfitting_score:.3f}, "
            f"Stability: {overall_stability:.3f}, "
            f"Alerts: {len(all_alerts)} ({len(critical_alerts)} critical, {len(warning_alerts)} warning)"
        )

        return report
