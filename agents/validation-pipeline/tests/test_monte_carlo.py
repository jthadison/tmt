"""
Tests for Monte Carlo Simulator - Story 11.7
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from app.monte_carlo import MonteCarloSimulator
from app.models import MonteCarloConfig


class TestMonteCarloSimulator:
    """Test Monte Carlo simulation functionality"""

    def test_simulator_initialization(self):
        """Test Monte Carlo simulator initialization"""
        config = MonteCarloConfig(
            num_runs=100,
            entry_price_variation_pips=5.0,
            parallel_workers=2
        )

        simulator = MonteCarloSimulator(config)

        assert simulator.config.num_runs == 100
        assert simulator.config.entry_price_variation_pips == 5.0
        assert simulator.config.parallel_workers == 2

    def test_apply_randomization(self, sample_historical_data):
        """Test data randomization application"""
        config = MonteCarloConfig(num_runs=10)
        simulator = MonteCarloSimulator(config)

        original_data = sample_historical_data.copy()
        randomized_data = simulator._apply_randomization(
            sample_historical_data.copy(),
            simulator.rng
        )

        # Data should be modified
        assert not randomized_data['close'].equals(original_data['close'])

        # Shape should remain the same
        assert len(randomized_data) == len(original_data)

        # Columns should be the same
        assert list(randomized_data.columns) == list(original_data.columns)

    def test_calculate_confidence_interval(self):
        """Test confidence interval calculation"""
        config = MonteCarloConfig()
        simulator = MonteCarloSimulator(config)

        values = [1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0]

        lower, upper = simulator._calculate_ci(values, 0.95)

        assert lower < upper
        assert lower >= min(values)
        assert upper <= max(values)

    @pytest.mark.asyncio
    async def test_run_batch_with_small_dataset(self, sample_historical_data, mock_backtest_config):
        """Test running a small batch of simulations"""
        config = MonteCarloConfig(num_runs=5, parallel_workers=1)
        simulator = MonteCarloSimulator(config)

        # Run small batch
        sharpe_ratios, max_drawdowns, win_rates = simulator._run_batch(
            0, 2,  # Just 2 runs
            mock_backtest_config.model_dump(),
            sample_historical_data
        )

        # Should have results for 2 runs
        assert len(sharpe_ratios) == 2
        assert len(max_drawdowns) == 2
        assert len(win_rates) == 2

        # Values should be in reasonable ranges
        for sharpe in sharpe_ratios:
            assert isinstance(sharpe, float)

        for dd in max_drawdowns:
            assert isinstance(dd, float)
            assert 0 <= dd <= 1

        for wr in win_rates:
            assert isinstance(wr, float)
            assert 0 <= wr <= 1

    def test_monte_carlo_config_defaults(self):
        """Test Monte Carlo config default values"""
        config = MonteCarloConfig()

        assert config.num_runs == 1000
        assert config.entry_price_variation_pips == 5.0
        assert config.exit_timing_variation_hours == 2
        assert config.slippage_range_pips == (0.0, 3.0)
        assert config.confidence_level == 0.95
        assert config.parallel_workers == 4

    def test_price_variation_range(self):
        """Test that price variations are within expected range"""
        config = MonteCarloConfig(entry_price_variation_pips=10.0)
        simulator = MonteCarloSimulator(config)

        # Create simple data
        data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=100, freq='H'),
            'open': [1.1000] * 100,
            'high': [1.1010] * 100,
            'low': [1.0990] * 100,
            'close': [1.1000] * 100,
            'volume': [1000] * 100
        })

        randomized = simulator._apply_randomization(data.copy(), simulator.rng)

        # Calculate max deviation
        max_deviation = abs(randomized['close'] - data['close']).max()

        # Should be within ±10 pips (0.001)
        assert max_deviation <= 0.001

    def test_reproducible_results(self, sample_historical_data):
        """Test that results are reproducible with same seed"""
        config = MonteCarloConfig(num_runs=5)

        # Run twice with same seed
        simulator1 = MonteCarloSimulator(config)
        data1 = simulator1._apply_randomization(
            sample_historical_data.copy(),
            np.random.default_rng(seed=42)
        )

        simulator2 = MonteCarloSimulator(config)
        data2 = simulator2._apply_randomization(
            sample_historical_data.copy(),
            np.random.default_rng(seed=42)
        )

        # Results should be identical
        pd.testing.assert_frame_equal(data1, data2)
