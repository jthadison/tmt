"""
Parameter Stability Analyzer - Story 11.3, Task 5

Analyzes parameter stability across walk-forward windows including:
- Parameter evolution tracking
- Variance and standard deviation calculation
- Baseline comparison
- Final parameter recommendation
"""

import numpy as np
from typing import List, Dict, Any, Tuple
import logging

from .models import WindowResult

logger = logging.getLogger(__name__)


class ParameterStabilityAnalyzer:
    """
    Analyzes parameter stability across walk-forward windows

    Tracks how parameters change across windows and identifies
    unstable parameters that vary significantly.
    """

    def __init__(self):
        """Initialize parameter stability analyzer"""
        pass

    def track_parameter_evolution(
        self,
        windows: List[WindowResult]
    ) -> Dict[str, List[float]]:
        """
        Track parameter evolution across windows

        Args:
            windows: List of walk-forward window results

        Returns:
            Dict mapping parameter name to list of values across windows

        Example:
            >>> analyzer = ParameterStabilityAnalyzer()
            >>> evolution = analyzer.track_parameter_evolution(windows)
            >>> evolution['confidence_threshold']
            [55.0, 60.0, 55.0, 65.0, ...]
        """

        if not windows:
            return {}

        # Get parameter names from first window
        param_names = list(windows[0].optimized_params.keys())

        # Track each parameter across windows
        parameter_evolution = {param_name: [] for param_name in param_names}

        for window in windows:
            for param_name in param_names:
                value = window.optimized_params.get(param_name)
                if value is not None:
                    parameter_evolution[param_name].append(value)

        logger.info(
            f"Tracked {len(param_names)} parameters "
            f"across {len(windows)} windows"
        )

        return parameter_evolution

    def calculate_parameter_statistics(
        self,
        parameter_evolution: Dict[str, List[float]]
    ) -> Dict[str, Dict[str, float]]:
        """
        Calculate statistics for each parameter

        Args:
            parameter_evolution: Dict mapping parameter name to values

        Returns:
            Dict mapping parameter name to statistics dict containing:
            - mean: Average value
            - median: Median value
            - std_dev: Standard deviation
            - min: Minimum value
            - max: Maximum value
            - range: Max - min
            - cv: Coefficient of variation (std_dev / mean)
        """

        statistics = {}

        for param_name, values in parameter_evolution.items():
            if not values:
                continue

            values_array = np.array(values)

            mean_val = np.mean(values_array)
            median_val = np.median(values_array)
            std_dev = np.std(values_array)
            min_val = np.min(values_array)
            max_val = np.max(values_array)
            range_val = max_val - min_val

            # Coefficient of variation (normalized std dev)
            cv = (std_dev / abs(mean_val)) if mean_val != 0 else 0.0

            statistics[param_name] = {
                'mean': float(mean_val),
                'median': float(median_val),
                'std_dev': float(std_dev),
                'min': float(min_val),
                'max': float(max_val),
                'range': float(range_val),
                'cv': float(cv),
                'n_samples': len(values)
            }

            logger.debug(
                f"Parameter '{param_name}': "
                f"mean={mean_val:.3f}, std={std_dev:.3f}, "
                f"CV={cv:.3f}, range=[{min_val:.3f}, {max_val:.3f}]"
            )

        return statistics

    def identify_unstable_parameters(
        self,
        parameter_statistics: Dict[str, Dict[str, float]],
        cv_threshold: float = 0.15
    ) -> List[str]:
        """
        Identify parameters with high variance (unstable)

        Args:
            parameter_statistics: Parameter statistics from calculate_parameter_statistics()
            cv_threshold: Coefficient of variation threshold for instability (default: 0.15)

        Returns:
            List of parameter names with high variance
        """

        unstable_params = []

        for param_name, stats in parameter_statistics.items():
            cv = stats.get('cv', 0.0)

            if cv > cv_threshold:
                unstable_params.append(param_name)
                logger.warning(
                    f"Parameter '{param_name}' is unstable: "
                    f"CV={cv:.3f} > threshold={cv_threshold}"
                )

        if unstable_params:
            logger.info(
                f"Identified {len(unstable_params)} unstable parameters: "
                f"{', '.join(unstable_params)}"
            )
        else:
            logger.info("All parameters are stable")

        return unstable_params

    def calculate_baseline_deviations(
        self,
        parameter_statistics: Dict[str, Dict[str, float]],
        baseline_params: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Calculate deviation of final parameters from baseline

        Args:
            parameter_statistics: Parameter statistics
            baseline_params: Baseline parameters

        Returns:
            Dict mapping parameter name to deviation percentage
        """

        deviations = {}

        for param_name, stats in parameter_statistics.items():
            if param_name not in baseline_params:
                continue

            final_value = stats['mean']  # Use mean as final recommended value
            baseline_value = baseline_params[param_name]

            if baseline_value == 0:
                deviations[param_name] = 0.0
                continue

            # Calculate percentage deviation
            deviation_pct = ((final_value - baseline_value) / baseline_value) * 100

            deviations[param_name] = deviation_pct

            logger.debug(
                f"Parameter '{param_name}': "
                f"baseline={baseline_value:.2f}, "
                f"recommended={final_value:.2f}, "
                f"deviation={deviation_pct:+.1f}%"
            )

        return deviations

    def recommend_final_parameters(
        self,
        parameter_evolution: Dict[str, List[float]],
        windows: List[WindowResult],
        strategy: str = "median"
    ) -> Dict[str, Any]:
        """
        Recommend final parameters based on walk-forward results

        Args:
            parameter_evolution: Parameter evolution across windows
            windows: Window results
            strategy: Recommendation strategy:
                - "median": Use median value across windows (robust to outliers)
                - "mean": Use mean value across windows
                - "best_window": Use parameters from best performing window
                - "recent": Use parameters from most recent windows (last 3)

        Returns:
            Dict of recommended parameters
        """

        recommended = {}

        if strategy == "median":
            # Use median value (robust to outliers)
            for param_name, values in parameter_evolution.items():
                recommended[param_name] = float(np.median(values))

        elif strategy == "mean":
            # Use mean value
            for param_name, values in parameter_evolution.items():
                recommended[param_name] = float(np.mean(values))

        elif strategy == "best_window":
            # Find window with best out-of-sample Sharpe ratio
            best_window = max(
                windows,
                key=lambda w: w.out_of_sample_sharpe
            )
            recommended = best_window.optimized_params.copy()

        elif strategy == "recent":
            # Use mean of last 3 windows (adapt to recent market conditions)
            n_recent = min(3, len(windows))
            recent_windows = windows[-n_recent:]

            for param_name in parameter_evolution.keys():
                recent_values = [
                    w.optimized_params[param_name]
                    for w in recent_windows
                ]
                recommended[param_name] = float(np.mean(recent_values))

        else:
            raise ValueError(f"Unknown recommendation strategy: {strategy}")

        logger.info(
            f"Recommended parameters using '{strategy}' strategy: "
            f"{recommended}"
        )

        return recommended

    def calculate_stability_score(
        self,
        parameter_evolution: Dict[str, List[float]]
    ) -> float:
        """
        Calculate overall parameter stability score

        Lower coefficient of variation across all parameters = higher stability.

        Args:
            parameter_evolution: Parameter evolution across windows

        Returns:
            Stability score (0-1, higher is better)
            - 1.0 = perfectly stable (no variance)
            - 0.0 = highly unstable (extreme variance)
        """

        if not parameter_evolution:
            return 1.0

        # Calculate CV for each parameter
        cvs = []

        for param_name, values in parameter_evolution.items():
            if len(values) < 2:
                continue

            values_array = np.array(values)
            mean_val = np.mean(values_array)
            std_val = np.std(values_array)

            if mean_val != 0:
                cv = std_val / abs(mean_val)
                cvs.append(cv)

        if not cvs:
            return 1.0

        # Average CV across all parameters
        avg_cv = np.mean(cvs)

        # Convert to stability score (inverse relationship)
        # CV of 0 = perfect stability (score 1.0)
        # CV of 0.5+ = low stability (score approaching 0)
        stability_score = 1.0 / (1.0 + avg_cv)

        logger.info(
            f"Overall parameter stability score: {stability_score:.3f} "
            f"(avg CV: {avg_cv:.3f})"
        )

        return stability_score

    def generate_stability_report(
        self,
        windows: List[WindowResult],
        baseline_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate comprehensive parameter stability report

        Args:
            windows: Walk-forward window results
            baseline_params: Baseline parameters

        Returns:
            Dict containing stability analysis results
        """

        # Track parameter evolution
        parameter_evolution = self.track_parameter_evolution(windows)

        # Calculate statistics
        parameter_statistics = self.calculate_parameter_statistics(parameter_evolution)

        # Identify unstable parameters
        unstable_params = self.identify_unstable_parameters(parameter_statistics)

        # Calculate baseline deviations
        baseline_deviations = self.calculate_baseline_deviations(
            parameter_statistics, baseline_params
        )

        # Recommend final parameters
        recommended_params = self.recommend_final_parameters(
            parameter_evolution, windows, strategy="median"
        )

        # Calculate overall stability score
        stability_score = self.calculate_stability_score(parameter_evolution)

        report = {
            'parameter_evolution': parameter_evolution,
            'parameter_statistics': parameter_statistics,
            'unstable_parameters': unstable_params,
            'baseline_deviations': baseline_deviations,
            'recommended_parameters': recommended_params,
            'stability_score': stability_score,
            'total_parameters': len(parameter_evolution),
            'stable_parameters': len(parameter_evolution) - len(unstable_params)
        }

        logger.info(
            f"Stability Report: "
            f"Score={stability_score:.3f}, "
            f"Stable={report['stable_parameters']}/{report['total_parameters']} parameters"
        )

        return report
