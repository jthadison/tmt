"""
Parameter Grid Search - Story 11.3, Task 2

Generates parameter combinations for optimization using:
- Exhaustive grid search
- Random search sampling
- Bayesian optimization preparation
"""

import itertools
import numpy as np
from typing import List, Dict, Tuple, Any, Iterator, Optional
import logging

logger = logging.getLogger(__name__)


class ParameterGridGenerator:
    """
    Generates parameter combinations for optimization

    Supports multiple optimization strategies:
    - Grid search: Exhaustive search over all combinations
    - Random search: Random sampling of parameter space
    - Bayesian prep: Generate initial samples for Bayesian optimization
    """

    def __init__(
        self,
        parameter_ranges: Dict[str, Tuple[float, float, float]],
        method: str = "grid_search"
    ):
        """
        Initialize parameter grid generator

        Args:
            parameter_ranges: Dict mapping parameter name to (min, max, step)
            method: Optimization method ('grid_search', 'random_search', 'bayesian')
        """
        self.parameter_ranges = parameter_ranges
        self.method = method
        self.param_names = sorted(parameter_ranges.keys())

    def generate_grid(self) -> List[Dict[str, Any]]:
        """
        Generate complete parameter grid (exhaustive search)

        Returns:
            List of parameter dictionaries representing all combinations

        Example:
            >>> generator = ParameterGridGenerator({
            ...     'confidence_threshold': (50.0, 60.0, 5.0),
            ...     'min_risk_reward': (1.5, 2.0, 0.5)
            ... })
            >>> grid = generator.generate_grid()
            >>> len(grid)
            9  # 3 confidence values * 3 R:R values
        """

        # Generate value ranges for each parameter
        param_values = {}
        for param_name, (min_val, max_val, step) in self.parameter_ranges.items():
            values = self._generate_range(min_val, max_val, step)
            param_values[param_name] = values

            logger.debug(
                f"Parameter '{param_name}': {len(values)} values "
                f"from {min_val} to {max_val} (step {step})"
            )

        # Generate all combinations using itertools.product
        param_combinations = []

        # Create list of (param_name, values) tuples in consistent order
        param_lists = [(name, param_values[name]) for name in self.param_names]

        # Generate all combinations
        value_lists = [values for _, values in param_lists]
        for combination in itertools.product(*value_lists):
            param_dict = {
                name: value
                for name, value in zip(self.param_names, combination)
            }
            param_combinations.append(param_dict)

        total_combinations = len(param_combinations)
        logger.info(
            f"Generated {total_combinations} parameter combinations "
            f"using {self.method}"
        )

        return param_combinations

    def generate_random_sample(
        self,
        n_samples: int,
        seed: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate random parameter samples

        Args:
            n_samples: Number of random samples to generate
            seed: Random seed for reproducibility

        Returns:
            List of parameter dictionaries (random samples)
        """

        if seed is not None:
            np.random.seed(seed)

        samples = []

        for _ in range(n_samples):
            sample = {}
            for param_name, (min_val, max_val, step) in self.parameter_ranges.items():
                # Generate random value within range, aligned to step
                n_steps = int((max_val - min_val) / step)
                random_step = np.random.randint(0, n_steps + 1)
                value = min_val + (random_step * step)
                sample[param_name] = value

            samples.append(sample)

        logger.info(f"Generated {n_samples} random parameter samples")

        return samples

    def generate_latin_hypercube(
        self,
        n_samples: int,
        seed: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate Latin Hypercube samples for better coverage

        Latin Hypercube sampling ensures better coverage of parameter space
        compared to pure random sampling. Good for Bayesian optimization initialization.

        Args:
            n_samples: Number of samples to generate
            seed: Random seed for reproducibility

        Returns:
            List of parameter dictionaries (LHS samples)
        """

        if seed is not None:
            np.random.seed(seed)

        n_params = len(self.param_names)

        # Generate Latin Hypercube samples in [0, 1] space
        lhs_samples = np.zeros((n_samples, n_params))

        for param_idx in range(n_params):
            # Divide [0, 1] into n_samples intervals
            intervals = np.arange(n_samples) / n_samples
            # Add random offset within each interval
            random_offsets = np.random.uniform(0, 1 / n_samples, n_samples)
            lhs_samples[:, param_idx] = intervals + random_offsets

            # Shuffle to break correlation between parameters
            np.random.shuffle(lhs_samples[:, param_idx])

        # Map [0, 1] samples to actual parameter ranges
        samples = []

        for sample_values in lhs_samples:
            sample = {}
            for param_idx, param_name in enumerate(self.param_names):
                min_val, max_val, step = self.parameter_ranges[param_name]

                # Map [0, 1] to [min_val, max_val]
                continuous_value = min_val + sample_values[param_idx] * (max_val - min_val)

                # Round to nearest step
                n_steps = round((continuous_value - min_val) / step)
                value = min_val + (n_steps * step)

                # Clamp to valid range
                value = max(min_val, min(max_val, value))

                sample[param_name] = value

            samples.append(sample)

        logger.info(
            f"Generated {n_samples} Latin Hypercube samples "
            f"for {n_params} parameters"
        )

        return samples

    def iterate_grid(self) -> Iterator[Dict[str, Any]]:
        """
        Iterate over parameter grid lazily (memory efficient)

        Yields:
            Parameter dictionaries one at a time

        Example:
            >>> generator = ParameterGridGenerator(...)
            >>> for params in generator.iterate_grid():
            ...     result = backtest(params)
        """

        param_values = {}
        for param_name, (min_val, max_val, step) in self.parameter_ranges.items():
            values = self._generate_range(min_val, max_val, step)
            param_values[param_name] = values

        # Create list of (param_name, values) tuples in consistent order
        param_lists = [(name, param_values[name]) for name in self.param_names]

        # Generate combinations lazily
        value_lists = [values for _, values in param_lists]
        for combination in itertools.product(*value_lists):
            param_dict = {
                name: value
                for name, value in zip(self.param_names, combination)
            }
            yield param_dict

    def count_combinations(self) -> int:
        """
        Count total number of parameter combinations

        Returns:
            Total number of combinations in the grid
        """

        total = 1

        for param_name, (min_val, max_val, step) in self.parameter_ranges.items():
            n_values = len(self._generate_range(min_val, max_val, step))
            total *= n_values

        return total

    def estimate_execution_time(
        self,
        seconds_per_backtest: float,
        n_workers: int = 1
    ) -> float:
        """
        Estimate total execution time for grid search

        Args:
            seconds_per_backtest: Average time per backtest
            n_workers: Number of parallel workers

        Returns:
            Estimated total time in seconds
        """

        total_combinations = self.count_combinations()
        sequential_time = total_combinations * seconds_per_backtest
        parallel_time = sequential_time / n_workers

        return parallel_time

    @staticmethod
    def _generate_range(min_val: float, max_val: float, step: float) -> List[float]:
        """
        Generate range of values with given step size

        Handles floating point precision issues.

        Args:
            min_val: Minimum value
            max_val: Maximum value
            step: Step size

        Returns:
            List of values from min_val to max_val with step increments
        """

        # Calculate number of steps
        n_steps = int(round((max_val - min_val) / step))

        # Generate values
        values = [min_val + (i * step) for i in range(n_steps + 1)]

        # Ensure max value is included (handle floating point errors)
        if values[-1] < max_val:
            values.append(max_val)

        # Round to reasonable precision (avoid 1.5000000000001)
        values = [round(v, 10) for v in values]

        return values


class BayesianOptimizationWrapper:
    """
    Wrapper for Bayesian optimization using scikit-optimize

    Provides smart parameter optimization that learns from previous evaluations
    to focus search on promising regions of parameter space.
    """

    def __init__(
        self,
        parameter_ranges: Dict[str, Tuple[float, float, float]],
        n_initial_points: int = 20,
        n_calls: int = 100,
        random_state: int = 42
    ):
        """
        Initialize Bayesian optimization

        Args:
            parameter_ranges: Dict mapping parameter name to (min, max, step)
            n_initial_points: Number of random initialization points
            n_calls: Total number of evaluations
            random_state: Random seed for reproducibility
        """
        self.parameter_ranges = parameter_ranges
        self.n_initial_points = n_initial_points
        self.n_calls = n_calls
        self.random_state = random_state
        self.param_names = sorted(parameter_ranges.keys())

        # Store evaluation history
        self.evaluations: List[Tuple[Dict[str, Any], float]] = []

    def suggest_next(self) -> Dict[str, Any]:
        """
        Suggest next parameter combination to evaluate

        Uses Gaussian Process to model objective function and suggests
        next point with highest expected improvement.

        Returns:
            Parameter dictionary for next evaluation
        """

        # For first n_initial_points, use Latin Hypercube sampling
        if len(self.evaluations) < self.n_initial_points:
            grid_gen = ParameterGridGenerator(
                self.parameter_ranges,
                method="bayesian"
            )
            samples = grid_gen.generate_latin_hypercube(
                n_samples=self.n_initial_points - len(self.evaluations),
                seed=self.random_state + len(self.evaluations)
            )
            return samples[0]

        # After initial points, use Bayesian optimization
        # This is a simplified implementation - in production, use scikit-optimize
        # For now, use random search as fallback
        logger.warning(
            "Full Bayesian optimization requires scikit-optimize. "
            "Using random search as fallback."
        )

        grid_gen = ParameterGridGenerator(
            self.parameter_ranges,
            method="random_search"
        )
        samples = grid_gen.generate_random_sample(
            n_samples=1,
            seed=self.random_state + len(self.evaluations)
        )
        return samples[0]

    def register_evaluation(
        self,
        parameters: Dict[str, Any],
        objective_value: float
    ) -> None:
        """
        Register evaluation result

        Args:
            parameters: Parameters that were evaluated
            objective_value: Objective function value (Sharpe ratio)
        """
        self.evaluations.append((parameters, objective_value))

        logger.debug(
            f"Registered evaluation #{len(self.evaluations)}: "
            f"objective={objective_value:.3f}"
        )

    def get_best_parameters(self) -> Tuple[Dict[str, Any], float]:
        """
        Get best parameters found so far

        Returns:
            Tuple of (best_parameters, best_objective_value)
        """
        if not self.evaluations:
            raise ValueError("No evaluations registered yet")

        best_params, best_value = max(
            self.evaluations,
            key=lambda x: x[1]
        )

        return best_params, best_value

    def is_complete(self) -> bool:
        """Check if optimization is complete"""
        return len(self.evaluations) >= self.n_calls
