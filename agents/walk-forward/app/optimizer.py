"""
Walk-Forward Optimizer - Story 11.3, Task 1

Core walk-forward optimization engine that:
- Generates rolling/anchored windows
- Optimizes parameters on training data
- Validates on out-of-sample testing data
- Tracks overfitting and parameter stability
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, AsyncIterator
import logging
import time
import uuid
from decimal import Decimal

from .models import (
    WalkForwardConfig, WindowResult, WalkForwardResult,
    WindowType, OptimizationMethod, EquityPoint
)
from .grid_search import ParameterGridGenerator, BayesianOptimizationWrapper
from .overfitting_detector import OverfittingDetector
from .stability_analyzer import ParameterStabilityAnalyzer

# Import backtesting components
# Use try-except to allow testing without full backtesting system
try:
    import sys
    import os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../backtesting')))

    from app.backtesting.engine import BacktestEngine
    from app.backtesting.models import BacktestConfig
    from app.repositories.historical_data_repository import HistoricalDataRepository
except ImportError:
    # Allow module import for testing without backtesting dependencies
    BacktestEngine = None
    BacktestConfig = None
    HistoricalDataRepository = None

logger = logging.getLogger(__name__)


class WalkForwardOptimizer:
    """
    Walk-forward optimization engine

    Implements complete walk-forward validation:
    1. Generate time windows (rolling or anchored)
    2. For each window:
       a. Optimize parameters on training data
       b. Validate on out-of-sample testing data
    3. Analyze overfitting and parameter stability
    4. Recommend final parameters
    """

    def __init__(
        self,
        config: WalkForwardConfig,
        data_repository: HistoricalDataRepository
    ):
        """
        Initialize walk-forward optimizer

        Args:
            config: Walk-forward configuration
            data_repository: Repository for loading historical data
        """
        self.config = config
        self.data_repository = data_repository

        # Initialize components
        self.overfitting_detector = OverfittingDetector()
        self.stability_analyzer = ParameterStabilityAnalyzer()

        # State tracking
        self.windows: List[WindowResult] = []
        self.total_backtests_run = 0

        logger.info(
            f"WalkForwardOptimizer initialized: "
            f"{config.window_type.value} windows, "
            f"train={config.training_window_days}d, "
            f"test={config.testing_window_days}d, "
            f"step={config.step_size_days}d"
        )

    async def run(self, job_id: str) -> WalkForwardResult:
        """
        Run complete walk-forward optimization

        Args:
            job_id: Unique job identifier

        Returns:
            WalkForwardResult with complete analysis
        """
        start_time = time.time()
        started_at = datetime.utcnow()

        logger.info("=" * 80)
        logger.info("WALK-FORWARD OPTIMIZATION STARTED")
        logger.info("=" * 80)
        logger.info(f"Job ID: {job_id}")
        logger.info(f"Date range: {self.config.start_date} to {self.config.end_date}")
        logger.info(f"Window type: {self.config.window_type.value}")
        logger.info(f"Optimization method: {self.config.optimization_method.value}")
        logger.info("=" * 80)

        # Generate windows
        windows = self.generate_windows()
        logger.info(f"Generated {len(windows)} walk-forward windows")

        # Validate minimum windows requirement
        if len(windows) < 12:
            logger.warning(
                f"Only {len(windows)} windows generated. "
                "Minimum 12 windows recommended for robust validation."
            )

        # Process each window
        for window_idx, (train_start, train_end, test_start, test_end) in enumerate(windows):
            logger.info(f"\n{'=' * 80}")
            logger.info(f"WINDOW {window_idx + 1}/{len(windows)}")
            logger.info(f"Training: {train_start.date()} to {train_end.date()}")
            logger.info(f"Testing: {test_start.date()} to {test_end.date()}")
            logger.info(f"{'=' * 80}")

            window_result = await self._process_window(
                window_idx, train_start, train_end, test_start, test_end
            )

            self.windows.append(window_result)

            logger.info(
                f"Window {window_idx + 1} complete: "
                f"IS Sharpe={window_result.in_sample_sharpe:.2f}, "
                f"OOS Sharpe={window_result.out_of_sample_sharpe:.2f}, "
                f"Overfitting Score={window_result.overfitting_score:.3f}"
            )

        # Generate final results
        execution_time = time.time() - start_time
        completed_at = datetime.utcnow()

        result = await self._generate_final_results(
            job_id, started_at, completed_at, execution_time
        )

        logger.info("=" * 80)
        logger.info("WALK-FORWARD OPTIMIZATION COMPLETED")
        logger.info("=" * 80)
        logger.info(f"Total windows: {len(self.windows)}")
        logger.info(f"Total backtests: {self.total_backtests_run}")
        logger.info(f"Execution time: {execution_time:.1f}s")
        logger.info(f"Avg OOS Sharpe: {result.avg_out_of_sample_sharpe:.2f}")
        logger.info(f"Avg Overfitting Score: {result.avg_overfitting_score:.3f}")
        logger.info(f"Stability Score: {result.parameter_stability_score:.3f}")
        logger.info(f"Acceptance Status: {result.acceptance_status}")
        logger.info("=" * 80)

        return result

    def generate_windows(self) -> List[Tuple[datetime, datetime, datetime, datetime]]:
        """
        Generate walk-forward windows

        Returns:
            List of (train_start, train_end, test_start, test_end) tuples

        Example (rolling):
            Window 1: Train[Jan-Mar], Test[Apr]
            Window 2: Train[Feb-Apr], Test[May]
            Window 3: Train[Mar-May], Test[Jun]

        Example (anchored):
            Window 1: Train[Jan-Mar], Test[Apr]
            Window 2: Train[Jan-Apr], Test[May]
            Window 3: Train[Jan-May], Test[Jun]
        """
        windows = []

        current_train_start = self.config.start_date
        current_test_start = current_train_start + timedelta(days=self.config.training_window_days)

        while True:
            # Calculate window dates
            if self.config.window_type == WindowType.ROLLING:
                # Rolling window: training window moves forward
                train_start = current_train_start
                train_end = current_test_start
            else:
                # Anchored window: training window expands from start
                train_start = self.config.start_date
                train_end = current_test_start

            test_start = train_end
            test_end = test_start + timedelta(days=self.config.testing_window_days)

            # Check if test window exceeds end date
            if test_end > self.config.end_date:
                break

            windows.append((train_start, train_end, test_start, test_end))

            # Move to next window
            current_train_start += timedelta(days=self.config.step_size_days)
            current_test_start = current_train_start + timedelta(days=self.config.training_window_days)

        logger.info(
            f"Generated {len(windows)} {self.config.window_type.value} windows "
            f"(train={self.config.training_window_days}d, "
            f"test={self.config.testing_window_days}d, "
            f"step={self.config.step_size_days}d)"
        )

        return windows

    async def _process_window(
        self,
        window_idx: int,
        train_start: datetime,
        train_end: datetime,
        test_start: datetime,
        test_end: datetime
    ) -> WindowResult:
        """
        Process a single walk-forward window

        Args:
            window_idx: Window index (0-based)
            train_start: Training period start
            train_end: Training period end
            test_start: Testing period start
            test_end: Testing period end

        Returns:
            WindowResult with optimization and validation results
        """
        window_start_time = time.time()

        # Step 1: Optimize parameters on training data
        logger.info(f"Optimizing parameters on training data...")
        optimized_params, optimization_metrics = await self._optimize_on_training(
            train_start, train_end
        )

        logger.info(
            f"Optimization complete: {optimized_params}, "
            f"Training Sharpe={optimization_metrics['sharpe']:.2f}"
        )

        # Step 2: Validate on out-of-sample testing data
        logger.info(f"Validating on out-of-sample testing data...")
        validation_metrics = await self._validate_on_testing(
            test_start, test_end, optimized_params
        )

        logger.info(
            f"Validation complete: "
            f"Testing Sharpe={validation_metrics['sharpe']:.2f}"
        )

        # Step 3: Calculate overfitting metrics
        overfitting_score = self.overfitting_detector.calculate_overfitting_score(
            in_sample_sharpe=optimization_metrics['sharpe'],
            out_of_sample_sharpe=validation_metrics['sharpe']
        )

        performance_degradation = (
            (optimization_metrics['total_return'] - validation_metrics['total_return'])
            / optimization_metrics['total_return'] * 100
            if optimization_metrics['total_return'] != 0 else 0.0
        )

        # Create window result
        window_result = WindowResult(
            window_index=window_idx,
            train_start=train_start,
            train_end=train_end,
            test_start=test_start,
            test_end=test_end,
            optimized_params=optimized_params,
            in_sample_sharpe=optimization_metrics['sharpe'],
            in_sample_drawdown=optimization_metrics['max_drawdown'],
            in_sample_win_rate=optimization_metrics['win_rate'],
            in_sample_total_return=optimization_metrics['total_return'],
            in_sample_total_trades=optimization_metrics['total_trades'],
            out_of_sample_sharpe=validation_metrics['sharpe'],
            out_of_sample_drawdown=validation_metrics['max_drawdown'],
            out_of_sample_win_rate=validation_metrics['win_rate'],
            out_of_sample_total_return=validation_metrics['total_return'],
            out_of_sample_total_trades=validation_metrics['total_trades'],
            overfitting_score=overfitting_score,
            performance_degradation=performance_degradation,
            total_param_combinations_tested=optimization_metrics['combinations_tested'],
            optimization_time_seconds=time.time() - window_start_time
        )

        return window_result

    async def _optimize_on_training(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Tuple[Dict[str, Any], Dict[str, float]]:
        """
        Optimize parameters on training data

        Args:
            start_date: Training period start
            end_date: Training period end

        Returns:
            Tuple of (optimized_parameters, training_metrics)
        """

        # Load training data
        market_data = await self._load_market_data(start_date, end_date)

        # Choose optimization method
        if self.config.optimization_method == OptimizationMethod.GRID_SEARCH:
            return await self._optimize_grid_search(market_data, start_date, end_date)
        elif self.config.optimization_method == OptimizationMethod.BAYESIAN:
            return await self._optimize_bayesian(market_data, start_date, end_date)
        else:
            raise ValueError(f"Unknown optimization method: {self.config.optimization_method}")

    async def _optimize_grid_search(
        self,
        market_data: Dict[str, pd.DataFrame],
        start_date: datetime,
        end_date: datetime
    ) -> Tuple[Dict[str, Any], Dict[str, float]]:
        """Optimize using exhaustive grid search"""

        grid_gen = ParameterGridGenerator(
            parameter_ranges=self.config.parameter_ranges,
            method="grid_search"
        )

        # Generate all parameter combinations
        param_combinations = grid_gen.generate_grid()

        logger.info(f"Testing {len(param_combinations)} parameter combinations (grid search)")

        best_sharpe = -np.inf
        best_params = None
        best_metrics = None

        # Test each combination
        for idx, params in enumerate(param_combinations):
            if (idx + 1) % 10 == 0:
                progress = (idx + 1) / len(param_combinations) * 100
                logger.debug(f"Grid search progress: {idx + 1}/{len(param_combinations)} ({progress:.1f}%)")

            metrics = await self._run_backtest(market_data, start_date, end_date, params)
            self.total_backtests_run += 1

            if metrics['sharpe'] > best_sharpe:
                best_sharpe = metrics['sharpe']
                best_params = params
                best_metrics = metrics

        if best_params is None:
            # Fallback to baseline if all backtests failed
            best_params = self.config.baseline_parameters
            best_metrics = await self._run_backtest(
                market_data, start_date, end_date, best_params
            )

        best_metrics['combinations_tested'] = len(param_combinations)

        return best_params, best_metrics

    async def _optimize_bayesian(
        self,
        market_data: Dict[str, pd.DataFrame],
        start_date: datetime,
        end_date: datetime
    ) -> Tuple[Dict[str, Any], Dict[str, float]]:
        """Optimize using Bayesian optimization"""

        max_iterations = self.config.max_iterations or 100

        bayes_opt = BayesianOptimizationWrapper(
            parameter_ranges=self.config.parameter_ranges,
            n_initial_points=20,
            n_calls=max_iterations,
            random_state=42
        )

        logger.info(f"Running Bayesian optimization ({max_iterations} iterations)")

        iteration = 0
        while not bayes_opt.is_complete() and iteration < max_iterations:
            iteration += 1

            # Get next parameter suggestion
            params = bayes_opt.suggest_next()

            # Run backtest
            metrics = await self._run_backtest(market_data, start_date, end_date, params)
            self.total_backtests_run += 1

            # Register result
            bayes_opt.register_evaluation(params, metrics['sharpe'])

            if iteration % 10 == 0:
                logger.debug(f"Bayesian optimization: {iteration}/{max_iterations} iterations")

        # Get best parameters
        best_params, best_sharpe = bayes_opt.get_best_parameters()

        # Run final backtest to get complete metrics
        best_metrics = await self._run_backtest(
            market_data, start_date, end_date, best_params
        )
        best_metrics['combinations_tested'] = iteration

        logger.info(f"Bayesian optimization complete: {iteration} iterations, best Sharpe={best_sharpe:.2f}")

        return best_params, best_metrics

    async def _validate_on_testing(
        self,
        start_date: datetime,
        end_date: datetime,
        parameters: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Validate parameters on out-of-sample testing data

        Args:
            start_date: Testing period start
            end_date: Testing period end
            parameters: Parameters to validate

        Returns:
            Dict of performance metrics
        """

        # Load testing data
        market_data = await self._load_market_data(start_date, end_date)

        # Run backtest with optimized parameters
        metrics = await self._run_backtest(market_data, start_date, end_date, parameters)
        self.total_backtests_run += 1

        return metrics

    async def _run_backtest(
        self,
        market_data: Dict[str, pd.DataFrame],
        start_date: datetime,
        end_date: datetime,
        parameters: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Run backtest with given parameters

        Args:
            market_data: Market data
            start_date: Backtest start
            end_date: Backtest end
            parameters: Trading parameters

        Returns:
            Dict of performance metrics
        """

        # Create backtest config
        config = BacktestConfig(
            start_date=start_date,
            end_date=end_date,
            instruments=self.config.instruments,
            initial_capital=self.config.initial_capital,
            risk_percentage=self.config.risk_percentage,
            parameters=parameters,
            timeframe="H1"
        )

        # Run backtest
        engine = BacktestEngine(config, enable_validation=False)  # Disable for speed
        result = await engine.run(market_data)

        # Extract metrics
        metrics = {
            'sharpe': result.sharpe_ratio,
            'max_drawdown': result.max_drawdown_pct,
            'win_rate': result.win_rate,
            'total_return': result.total_return_pct,
            'total_trades': result.total_trades
        }

        return metrics

    async def _load_market_data(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, pd.DataFrame]:
        """
        Load market data for given period

        Args:
            start_date: Period start
            end_date: Period end

        Returns:
            Dict mapping instrument to DataFrame
        """

        market_data = {}

        for instrument in self.config.instruments:
            # Load from repository
            candles = await self.data_repository.get_candles(
                instrument=instrument,
                start_date=start_date,
                end_date=end_date,
                granularity="H1"
            )

            # Convert to DataFrame
            df = pd.DataFrame([
                {
                    'timestamp': c.timestamp,
                    'open': float(c.open_price),
                    'high': float(c.high_price),
                    'low': float(c.low_price),
                    'close': float(c.close_price),
                    'volume': int(c.volume)
                }
                for c in candles
            ])

            if not df.empty:
                df.set_index('timestamp', inplace=True)

            market_data[instrument] = df

        return market_data

    async def _generate_final_results(
        self,
        job_id: str,
        started_at: datetime,
        completed_at: datetime,
        execution_time: float
    ) -> WalkForwardResult:
        """Generate final walk-forward results"""

        # Calculate aggregate metrics
        avg_in_sample_sharpe = np.mean([w.in_sample_sharpe for w in self.windows])
        avg_out_of_sample_sharpe = np.mean([w.out_of_sample_sharpe for w in self.windows])
        avg_overfitting_score = np.mean([w.overfitting_score for w in self.windows])

        # Parameter stability analysis
        stability_report = self.stability_analyzer.generate_stability_report(
            self.windows, self.config.baseline_parameters
        )

        # Recommended parameters
        recommended_params = stability_report['recommended_parameters']
        baseline_deviations = stability_report['baseline_deviations']

        # Acceptance criteria validation
        from .validators import AcceptanceCriteriaValidator
        validator = AcceptanceCriteriaValidator()
        acceptance_result = validator.validate(self.windows, avg_overfitting_score)

        # Create result
        result = WalkForwardResult(
            job_id=job_id,
            config=self.config,
            windows=self.windows,
            avg_in_sample_sharpe=avg_in_sample_sharpe,
            avg_out_of_sample_sharpe=avg_out_of_sample_sharpe,
            avg_overfitting_score=avg_overfitting_score,
            parameter_stability_score=stability_report['stability_score'],
            acceptance_status=acceptance_result['status'],
            acceptance_details=acceptance_result['details'],
            acceptance_messages=acceptance_result['messages'],
            recommended_parameters=recommended_params,
            parameter_deviation_from_baseline=baseline_deviations,
            parameter_evolution=stability_report['parameter_evolution'],
            total_backtests_run=self.total_backtests_run,
            total_windows=len(self.windows),
            execution_time_seconds=execution_time,
            started_at=started_at,
            completed_at=completed_at
        )

        return result
