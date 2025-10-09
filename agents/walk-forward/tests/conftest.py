"""
Test fixtures for walk-forward optimization tests
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from app.models import (
    WalkForwardConfig, WindowResult, WindowType,
    OptimizationMethod, EquityPoint
)


@pytest.fixture
def sample_config():
    """Sample walk-forward configuration"""
    return WalkForwardConfig(
        start_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        training_window_days=90,
        testing_window_days=30,
        step_size_days=30,
        window_type=WindowType.ROLLING,
        instruments=["EUR_USD", "GBP_USD"],
        initial_capital=100000.0,
        risk_percentage=0.02,
        parameter_ranges={
            "confidence_threshold": (50.0, 70.0, 10.0),
            "min_risk_reward": (1.5, 2.5, 0.5)
        },
        baseline_parameters={
            "confidence_threshold": 55.0,
            "min_risk_reward": 1.8
        },
        optimization_method=OptimizationMethod.GRID_SEARCH,
        n_workers=2
    )


@pytest.fixture
def sample_window_result():
    """Sample window result"""
    return WindowResult(
        window_index=0,
        train_start=datetime(2023, 1, 1, tzinfo=timezone.utc),
        train_end=datetime(2023, 4, 1, tzinfo=timezone.utc),
        test_start=datetime(2023, 4, 1, tzinfo=timezone.utc),
        test_end=datetime(2023, 5, 1, tzinfo=timezone.utc),
        optimized_params={
            "confidence_threshold": 60.0,
            "min_risk_reward": 2.0
        },
        in_sample_sharpe=2.0,
        in_sample_drawdown=-8.5,
        in_sample_win_rate=0.65,
        in_sample_total_return=12.5,
        in_sample_total_trades=50,
        out_of_sample_sharpe=1.5,
        out_of_sample_drawdown=-10.2,
        out_of_sample_win_rate=0.62,
        out_of_sample_total_return=8.3,
        out_of_sample_total_trades=15,
        overfitting_score=0.25,
        performance_degradation=33.6,
        total_param_combinations_tested=12,
        optimization_time_seconds=45.2
    )


@pytest.fixture
def sample_windows() -> List[WindowResult]:
    """Generate sample window results for testing"""
    windows = []

    base_date = datetime(2023, 1, 1, tzinfo=timezone.utc)

    for i in range(12):
        train_start = base_date + timedelta(days=i * 30)
        train_end = train_start + timedelta(days=90)
        test_start = train_end
        test_end = test_start + timedelta(days=30)

        # Generate varied but realistic metrics
        in_sample_sharpe = 1.8 + (i % 3) * 0.2 + np.random.uniform(-0.1, 0.1)
        out_of_sample_sharpe = in_sample_sharpe * (0.7 + np.random.uniform(0, 0.2))

        window = WindowResult(
            window_index=i,
            train_start=train_start,
            train_end=train_end,
            test_start=test_start,
            test_end=test_end,
            optimized_params={
                "confidence_threshold": 55.0 + (i % 4) * 5.0,
                "min_risk_reward": 1.8 + (i % 3) * 0.2
            },
            in_sample_sharpe=in_sample_sharpe,
            in_sample_drawdown=-8.0 - (i % 3) * 2.0,
            in_sample_win_rate=0.60 + (i % 5) * 0.02,
            in_sample_total_return=10.0 + (i % 4) * 2.0,
            in_sample_total_trades=40 + (i % 3) * 10,
            out_of_sample_sharpe=out_of_sample_sharpe,
            out_of_sample_drawdown=-10.0 - (i % 3) * 1.5,
            out_of_sample_win_rate=0.58 + (i % 5) * 0.02,
            out_of_sample_total_return=7.0 + (i % 4) * 1.5,
            out_of_sample_total_trades=12 + (i % 3) * 3,
            overfitting_score=(in_sample_sharpe - out_of_sample_sharpe) / in_sample_sharpe,
            performance_degradation=20.0 + (i % 4) * 5.0,
            total_param_combinations_tested=12,
            optimization_time_seconds=40.0 + (i % 5) * 5.0
        )

        windows.append(window)

    return windows


@pytest.fixture
def sample_market_data() -> Dict[str, pd.DataFrame]:
    """Generate sample market data for testing"""
    np.random.seed(42)

    market_data = {}

    for instrument in ["EUR_USD", "GBP_USD"]:
        # Generate 1 year of hourly data
        dates = pd.date_range(
            start=datetime(2023, 1, 1, tzinfo=timezone.utc),
            end=datetime(2024, 1, 1, tzinfo=timezone.utc),
            freq='H'
        )

        # Generate realistic OHLCV data
        close_prices = 1.1000 + np.cumsum(np.random.randn(len(dates)) * 0.0001)

        df = pd.DataFrame({
            'open': close_prices + np.random.uniform(-0.0005, 0.0005, len(dates)),
            'high': close_prices + np.abs(np.random.uniform(0, 0.001, len(dates))),
            'low': close_prices - np.abs(np.random.uniform(0, 0.001, len(dates))),
            'close': close_prices,
            'volume': np.random.randint(1000, 10000, len(dates))
        }, index=dates)

        market_data[instrument] = df

    return market_data


@pytest.fixture
def parameter_evolution():
    """Sample parameter evolution data"""
    return {
        "confidence_threshold": [55.0, 60.0, 55.0, 65.0, 60.0, 55.0, 60.0, 65.0, 60.0, 55.0, 60.0, 55.0],
        "min_risk_reward": [1.8, 2.0, 1.8, 2.2, 2.0, 1.8, 2.0, 2.2, 2.0, 1.8, 2.0, 1.8]
    }


@pytest.fixture
def baseline_parameters():
    """Sample baseline parameters"""
    return {
        "confidence_threshold": 55.0,
        "min_risk_reward": 1.8
    }
