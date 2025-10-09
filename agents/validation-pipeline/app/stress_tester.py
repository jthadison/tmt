"""
Stress Testing Framework - Story 11.7, Task 3

Tests trading parameters during historical crisis periods to ensure
resilience during extreme market conditions.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from .models import (
    CrisisPeriod, StressTestResult, StressTestValidationResult
)

# Import backtesting components - optional for testing
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../backtesting')))

try:
    from app.backtesting.engine import BacktestEngine
    from app.backtesting.models import BacktestConfig
except ImportError:
    # Allow module import without backtesting for testing
    BacktestEngine = None
    BacktestConfig = None

logger = logging.getLogger(__name__)


# Define historical crisis periods
CRISIS_PERIODS = [
    CrisisPeriod(
        name="2008 Financial Crisis",
        start=datetime(2008, 9, 1),
        end=datetime(2008, 12, 31),
        max_drawdown_threshold=0.25,
        recovery_days_threshold=90
    ),
    CrisisPeriod(
        name="2015 CHF Flash Crash",
        start=datetime(2015, 1, 10),
        end=datetime(2015, 1, 20),
        max_drawdown_threshold=0.25,
        recovery_days_threshold=90
    ),
    CrisisPeriod(
        name="2020 COVID Crash",
        start=datetime(2020, 3, 1),
        end=datetime(2020, 3, 31),
        max_drawdown_threshold=0.25,
        recovery_days_threshold=90
    )
]


class StressTester:
    """
    Stress testing framework for parameter validation

    Tests parameters during historical crisis periods:
    - 2008 Financial Crisis
    - 2015 CHF Flash Crash
    - 2020 COVID Crash

    Validates:
    - Maximum drawdown < 25% during crisis
    - Recovery within 90 days post-crisis
    """

    def __init__(self, crisis_periods: Optional[List[CrisisPeriod]] = None):
        """
        Initialize stress tester

        Args:
            crisis_periods: List of crisis periods to test (defaults to standard periods)
        """
        self.crisis_periods = crisis_periods or CRISIS_PERIODS

    async def run_stress_tests(
        self,
        backtest_config: BacktestConfig,
        historical_data: pd.DataFrame
    ) -> StressTestValidationResult:
        """
        Run stress tests across all crisis periods

        Args:
            backtest_config: Backtest configuration
            historical_data: Full historical market data

        Returns:
            Stress test validation result
        """
        logger.info(f"Running stress tests across {len(self.crisis_periods)} crisis periods")

        crisis_results = []
        all_passed = True

        for crisis in self.crisis_periods:
            result = await self._test_crisis_period(
                crisis, backtest_config, historical_data
            )
            crisis_results.append(result)

            if not result.passed:
                all_passed = False

        # Generate summary message
        passed_count = sum(1 for r in crisis_results if r.passed)
        message = (
            f"Stress testing: {passed_count}/{len(crisis_results)} crisis periods passed. "
        )

        if all_passed:
            message += "Parameters show resilience to extreme market conditions."
        else:
            failed_crises = [r.crisis_name for r in crisis_results if not r.passed]
            message += f"Failed: {', '.join(failed_crises)}"

        return StressTestValidationResult(
            passed=all_passed,
            crisis_results=crisis_results,
            message=message
        )

    async def _test_crisis_period(
        self,
        crisis: CrisisPeriod,
        backtest_config: BacktestConfig,
        historical_data: pd.DataFrame
    ) -> StressTestResult:
        """
        Test parameters during a specific crisis period

        Args:
            crisis: Crisis period definition
            backtest_config: Backtest configuration
            historical_data: Historical market data

        Returns:
            Stress test result for this crisis
        """
        logger.info(f"Testing crisis period: {crisis.name}")

        # Extract data for crisis period + recovery period
        crisis_data = self._extract_crisis_data(
            historical_data, crisis.start, crisis.end
        )

        if crisis_data.empty:
            logger.warning(f"No data available for {crisis.name}")
            return StressTestResult(
                crisis_name=crisis.name,
                passed=False,
                max_drawdown=1.0,
                max_drawdown_threshold=crisis.max_drawdown_threshold,
                recovery_days=None,
                recovery_threshold=crisis.recovery_days_threshold,
                num_trades=0,
                message=f"{crisis.name}: No historical data available"
            )

        # Extract recovery period data (90 days after crisis end)
        recovery_end = crisis.end + timedelta(days=crisis.recovery_days_threshold)
        recovery_data = self._extract_crisis_data(
            historical_data, crisis.end, recovery_end
        )

        # Run backtest on crisis period
        crisis_config = backtest_config.model_copy()
        crisis_config.start_date = crisis.start
        crisis_config.end_date = crisis.end

        engine = BacktestEngine(crisis_config)

        try:
            crisis_result = engine.run_backtest(crisis_data)

            max_drawdown = crisis_result.metrics.max_drawdown_pct / 100.0
            num_trades = len(crisis_result.trades)

            # Check drawdown threshold
            drawdown_passed = max_drawdown <= crisis.max_drawdown_threshold

            # Calculate recovery time if there was a drawdown
            recovery_days = None
            recovery_passed = True

            if max_drawdown > 0.05 and not recovery_data.empty:  # Significant drawdown
                recovery_days = self._calculate_recovery_time(
                    crisis_result, recovery_data, crisis_config
                )

                if recovery_days is not None:
                    recovery_passed = recovery_days <= crisis.recovery_days_threshold
                else:
                    # Failed to recover
                    recovery_passed = False
                    recovery_days = 999  # Indicate no recovery

            # Overall pass if both drawdown and recovery passed
            passed = drawdown_passed and recovery_passed

            # Generate message
            if passed:
                message = (
                    f"{crisis.name}: PASSED - "
                    f"Max DD: {max_drawdown*100:.1f}% "
                    f"(threshold: {crisis.max_drawdown_threshold*100:.1f}%)"
                )
                if recovery_days is not None:
                    message += f", Recovery: {recovery_days} days"
            else:
                message = f"{crisis.name}: FAILED - "
                if not drawdown_passed:
                    message += (
                        f"Max DD {max_drawdown*100:.1f}% exceeds "
                        f"{crisis.max_drawdown_threshold*100:.1f}% threshold. "
                    )
                if not recovery_passed:
                    message += f"Recovery took {recovery_days} days (> {crisis.recovery_days_threshold})"

            return StressTestResult(
                crisis_name=crisis.name,
                passed=passed,
                max_drawdown=max_drawdown,
                max_drawdown_threshold=crisis.max_drawdown_threshold,
                recovery_days=recovery_days,
                recovery_threshold=crisis.recovery_days_threshold,
                num_trades=num_trades,
                message=message
            )

        except Exception as e:
            logger.error(f"Stress test failed for {crisis.name}: {e}")
            return StressTestResult(
                crisis_name=crisis.name,
                passed=False,
                max_drawdown=1.0,
                max_drawdown_threshold=crisis.max_drawdown_threshold,
                recovery_days=None,
                recovery_threshold=crisis.recovery_days_threshold,
                num_trades=0,
                message=f"{crisis.name}: FAILED - Error during backtest: {str(e)}"
            )

    def _extract_crisis_data(
        self,
        historical_data: pd.DataFrame,
        start: datetime,
        end: datetime
    ) -> pd.DataFrame:
        """
        Extract data for a specific date range

        Args:
            historical_data: Full historical data
            start: Start date
            end: End date

        Returns:
            Filtered data for the date range
        """
        # Ensure timestamp column exists
        if 'timestamp' not in historical_data.columns:
            if historical_data.index.name == 'timestamp':
                historical_data = historical_data.reset_index()
            else:
                logger.warning("No timestamp column found in data")
                return pd.DataFrame()

        # Convert timestamp to datetime if needed
        if not pd.api.types.is_datetime64_any_dtype(historical_data['timestamp']):
            historical_data['timestamp'] = pd.to_datetime(historical_data['timestamp'])

        # Filter data
        mask = (historical_data['timestamp'] >= start) & (historical_data['timestamp'] <= end)
        return historical_data[mask].copy()

    def _calculate_recovery_time(
        self,
        crisis_result,
        recovery_data: pd.DataFrame,
        backtest_config: BacktestConfig
    ) -> Optional[int]:
        """
        Calculate time to recover from drawdown

        Args:
            crisis_result: Backtest result from crisis period
            recovery_data: Market data for recovery period
            backtest_config: Backtest configuration

        Returns:
            Number of days to recover, or None if no recovery
        """
        # Get peak equity before drawdown
        if not crisis_result.equity_curve:
            return None

        peak_equity = max(point.equity for point in crisis_result.equity_curve)

        # Run backtest on recovery period
        recovery_config = backtest_config.model_copy()
        recovery_config.start_date = recovery_data['timestamp'].min()
        recovery_config.end_date = recovery_data['timestamp'].max()
        recovery_config.initial_balance = crisis_result.equity_curve[-1].equity

        engine = BacktestEngine(recovery_config)

        try:
            recovery_result = engine.run_backtest(recovery_data)

            # Find when equity recovered to peak
            for point in recovery_result.equity_curve:
                if point.equity >= peak_equity:
                    # Calculate days from crisis end
                    days = (point.timestamp - recovery_data['timestamp'].min()).days
                    return days

            # No recovery within period
            return None

        except Exception as e:
            logger.warning(f"Recovery calculation failed: {e}")
            return None
