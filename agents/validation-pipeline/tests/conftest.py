"""
Test fixtures for validation pipeline tests
"""

import sys
import os

# Add parent directories to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any


@pytest.fixture
def sample_config_data() -> Dict[str, Any]:
    """Sample parameter configuration data"""
    return {
        "version": "1.0.0",
        "effective_date": "2025-01-01",
        "author": "test_user",
        "reason": "Test configuration for validation",
        "baseline": {
            "confidence_threshold": 70.0,
            "min_risk_reward": 2.5,
            "max_risk_reward": 5.0
        },
        "session_parameters": {
            "tokyo": {
                "confidence_threshold": 85.0,
                "min_risk_reward": 4.0
            },
            "london": {
                "confidence_threshold": 72.0,
                "min_risk_reward": 3.2
            }
        },
        "constraints": {
            "max_confidence_deviation": 20.0,
            "max_risk_reward_deviation": 2.0,
            "max_overfitting_score": 0.3,
            "min_backtest_sharpe": 1.0,
            "min_out_of_sample_ratio": 0.7
        }
    }


@pytest.fixture
def sample_historical_data() -> pd.DataFrame:
    """Generate sample historical market data"""
    # Generate 6 months of hourly data
    dates = pd.date_range(
        end=datetime.now(),
        periods=4320,  # 6 months * 30 days * 24 hours
        freq='H'
    )

    # Generate realistic forex price data
    np.random.seed(42)
    close_prices = 1.1000 + np.cumsum(np.random.randn(len(dates)) * 0.0001)

    data = pd.DataFrame({
        'timestamp': dates,
        'open': close_prices - np.random.rand(len(dates)) * 0.0005,
        'high': close_prices + np.random.rand(len(dates)) * 0.001,
        'low': close_prices - np.random.rand(len(dates)) * 0.001,
        'close': close_prices,
        'volume': np.random.randint(1000, 10000, len(dates))
    })

    return data


@pytest.fixture
def mock_backtest_config():
    """Mock backtest configuration"""
    from app.backtesting.models import BacktestConfig

    return BacktestConfig(
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 6, 30),
        initial_balance=10000.0,
        symbols=['EUR_USD']
    )


@pytest.fixture
def sample_validation_report():
    """Sample validation report for testing"""
    from app.models import (
        ValidationReport, ValidationStatus,
        SchemaValidationResult, OverfittingValidationResult,
        WalkForwardValidationResult, MonteCarloValidationResult,
        StressTestValidationResult, AcceptanceCriteriaValidation
    )

    return ValidationReport(
        job_id="test-job-123",
        config_file="test_config.yaml",
        timestamp=datetime.utcnow(),
        status=ValidationStatus.APPROVED,
        duration_seconds=120.5,
        schema_validation=SchemaValidationResult(
            passed=True,
            errors=[],
            warnings=[]
        ),
        overfitting_validation=OverfittingValidationResult(
            passed=True,
            overfitting_score=0.25,
            threshold=0.3,
            message="Overfitting score within threshold"
        ),
        walk_forward_validation=WalkForwardValidationResult(
            passed=True,
            in_sample_sharpe=1.52,
            out_of_sample_sharpe=1.38,
            max_drawdown=0.12,
            win_rate=0.52,
            profit_factor=1.45,
            num_trades=47,
            avg_out_of_sample_sharpe=1.38,
            message="Walk-forward validation passed"
        ),
        monte_carlo_validation=MonteCarloValidationResult(
            passed=True,
            num_runs=1000,
            sharpe_mean=1.35,
            sharpe_std=0.15,
            sharpe_95ci_lower=1.1,
            sharpe_95ci_upper=1.6,
            drawdown_95ci_lower=0.08,
            drawdown_95ci_upper=0.18,
            win_rate_95ci_lower=0.48,
            win_rate_95ci_upper=0.56,
            threshold=0.8,
            message="Monte Carlo simulation passed"
        ),
        stress_test_validation=StressTestValidationResult(
            passed=True,
            crisis_results=[],
            message="All stress tests passed"
        ),
        acceptance_criteria=AcceptanceCriteriaValidation(
            passed=True,
            all_criteria=[],
            passed_count=8,
            failed_count=0
        ),
        all_checks_passed=True,
        recommendations=[]
    )
