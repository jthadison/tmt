"""
Monte Carlo Simulator - Story 11.7, Task 2

Runs Monte Carlo simulations with parameter randomization to test
robustness of trading parameters under various conditions.
"""

import asyncio
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import logging
from concurrent.futures import ProcessPoolExecutor
import multiprocessing

from .models import (
    MonteCarloConfig, MonteCarloValidationResult
)

# Import backtesting components - optional for testing
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../backtesting')))

try:
    from app.backtesting.engine import BacktestEngine
    from app.backtesting.models import BacktestConfig, TradingSession
except ImportError:
    # Allow module import without backtesting for testing
    BacktestEngine = None
    BacktestConfig = None
    TradingSession = None

logger = logging.getLogger(__name__)


class MonteCarloSimulator:
    """
    Monte Carlo simulation for parameter validation

    Tests parameter robustness by running multiple simulations with:
    - Entry price variation (±5 pips)
    - Exit timing variation (±2 hours)
    - Slippage variation (0-3 pips)

    Calculates 95% confidence intervals for key metrics.
    """

    def __init__(self, config: MonteCarloConfig):
        """
        Initialize Monte Carlo simulator

        Args:
            config: Monte Carlo configuration
        """
        self.config = config
        self.rng = np.random.default_rng(seed=42)  # Reproducible results

    async def run_simulation(
        self,
        backtest_config: BacktestConfig,
        historical_data: pd.DataFrame
    ) -> MonteCarloValidationResult:
        """
        Run Monte Carlo simulation

        Args:
            backtest_config: Base backtest configuration
            historical_data: Historical market data

        Returns:
            Monte Carlo validation result with confidence intervals
        """
        logger.info(f"Starting Monte Carlo simulation with {self.config.num_runs} runs")
        start_time = datetime.now()

        # Run simulations in parallel
        sharpe_ratios = []
        max_drawdowns = []
        win_rates = []

        # Use process pool for CPU-intensive work
        num_workers = min(self.config.parallel_workers, multiprocessing.cpu_count())

        # Split runs into batches for parallel processing
        batch_size = self.config.num_runs // num_workers
        batches = [
            (i * batch_size, min((i + 1) * batch_size, self.config.num_runs))
            for i in range(num_workers)
        ]

        # Handle remainder
        if batches[-1][1] < self.config.num_runs:
            batches[-1] = (batches[-1][0], self.config.num_runs)

        # Run batches in parallel
        loop = asyncio.get_event_loop()
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                loop.run_in_executor(
                    executor,
                    self._run_batch,
                    start_run,
                    end_run,
                    backtest_config.model_dump(),
                    historical_data
                )
                for start_run, end_run in batches
            ]

            batch_results = await asyncio.gather(*futures)

        # Aggregate results from all batches
        for batch_sharpes, batch_drawdowns, batch_winrates in batch_results:
            sharpe_ratios.extend(batch_sharpes)
            max_drawdowns.extend(batch_drawdowns)
            win_rates.extend(batch_winrates)

        # Calculate statistics
        sharpe_mean = float(np.mean(sharpe_ratios))
        sharpe_std = float(np.std(sharpe_ratios))

        # Calculate 95% confidence intervals
        sharpe_95ci_lower, sharpe_95ci_upper = self._calculate_ci(
            sharpe_ratios, self.config.confidence_level
        )
        drawdown_95ci_lower, drawdown_95ci_upper = self._calculate_ci(
            max_drawdowns, self.config.confidence_level
        )
        win_rate_95ci_lower, win_rate_95ci_upper = self._calculate_ci(
            win_rates, self.config.confidence_level
        )

        # Check if lower bound of Sharpe CI meets threshold
        passed = sharpe_95ci_lower >= 0.8

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"Monte Carlo completed in {duration:.1f}s - "
            f"Sharpe 95% CI: [{sharpe_95ci_lower:.2f}, {sharpe_95ci_upper:.2f}]"
        )

        message = (
            f"Monte Carlo ({self.config.num_runs} runs): "
            f"Sharpe 95% CI [{sharpe_95ci_lower:.2f}, {sharpe_95ci_upper:.2f}] "
            f"(threshold: >= 0.8)"
        )

        return MonteCarloValidationResult(
            passed=passed,
            num_runs=self.config.num_runs,
            sharpe_mean=sharpe_mean,
            sharpe_std=sharpe_std,
            sharpe_95ci_lower=sharpe_95ci_lower,
            sharpe_95ci_upper=sharpe_95ci_upper,
            drawdown_95ci_lower=drawdown_95ci_lower,
            drawdown_95ci_upper=drawdown_95ci_upper,
            win_rate_95ci_lower=win_rate_95ci_lower,
            win_rate_95ci_upper=win_rate_95ci_upper,
            threshold=0.8,
            message=message
        )

    def _run_batch(
        self,
        start_run: int,
        end_run: int,
        backtest_config_dict: Dict[str, Any],
        historical_data: pd.DataFrame
    ) -> tuple[List[float], List[float], List[float]]:
        """
        Run a batch of simulations (for parallel processing)

        Args:
            start_run: Starting run index
            end_run: Ending run index
            backtest_config_dict: Backtest config as dict
            historical_data: Historical market data

        Returns:
            Tuple of (sharpe_ratios, max_drawdowns, win_rates)
        """
        sharpe_ratios = []
        max_drawdowns = []
        win_rates = []

        # Create RNG for this batch (with different seed per batch)
        batch_rng = np.random.default_rng(seed=42 + start_run)

        for run_idx in range(start_run, end_run):
            # Apply randomization
            randomized_data = self._apply_randomization(
                historical_data.copy(), batch_rng
            )

            # Run backtest with randomized data
            backtest_config = BacktestConfig(**backtest_config_dict)
            engine = BacktestEngine(backtest_config)

            try:
                result = engine.run_backtest(randomized_data)

                sharpe_ratios.append(result.metrics.sharpe_ratio)
                max_drawdowns.append(result.metrics.max_drawdown_pct / 100.0)
                win_rates.append(result.metrics.win_rate / 100.0)

            except Exception as e:
                logger.warning(f"Run {run_idx} failed: {e}")
                # Use conservative estimates for failed runs
                sharpe_ratios.append(0.0)
                max_drawdowns.append(1.0)
                win_rates.append(0.0)

        return sharpe_ratios, max_drawdowns, win_rates

    def _apply_randomization(
        self, data: pd.DataFrame, rng: np.random.Generator
    ) -> pd.DataFrame:
        """
        Apply randomization to market data

        Args:
            data: Original market data
            rng: Random number generator

        Returns:
            Randomized market data
        """
        # Entry price variation: ±5 pips (0.0005 for most forex pairs)
        price_variation = self.config.entry_price_variation_pips * 0.0001

        # Apply random price shifts
        for col in ['open', 'high', 'low', 'close']:
            if col in data.columns:
                shift = rng.uniform(-price_variation, price_variation, size=len(data))
                data[col] = data[col] + shift

        # Exit timing variation: ±2 hours (shift bars)
        # Randomly shift data by up to 2 bars in either direction
        max_shift = self.config.exit_timing_variation_hours
        shift_bars = rng.integers(-max_shift, max_shift + 1)
        if shift_bars != 0:
            data = data.shift(shift_bars).fillna(method='bfill').fillna(method='ffill')

        # Slippage variation: 0-3 pips (applied in order simulator)
        # We'll store this as metadata for the backtest engine
        slippage_pips = rng.uniform(
            self.config.slippage_range_pips[0],
            self.config.slippage_range_pips[1]
        )
        data.attrs['mc_slippage_pips'] = slippage_pips

        return data

    def _calculate_ci(
        self, values: List[float], confidence_level: float
    ) -> tuple[float, float]:
        """
        Calculate confidence interval

        Args:
            values: List of values
            confidence_level: Confidence level (e.g., 0.95 for 95% CI)

        Returns:
            Tuple of (lower_bound, upper_bound)
        """
        alpha = 1 - confidence_level
        lower_percentile = (alpha / 2) * 100
        upper_percentile = (1 - alpha / 2) * 100

        lower = float(np.percentile(values, lower_percentile))
        upper = float(np.percentile(values, upper_percentile))

        return lower, upper
