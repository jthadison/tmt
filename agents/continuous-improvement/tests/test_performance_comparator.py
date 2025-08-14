"""
Tests for Performance Comparator
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from performance_comparator import PerformanceComparator
from models import (
    PerformanceMetrics, PerformanceComparison, StatisticalAnalysis,
    TestGroup
)


class TestPerformanceComparator:
    """Test suite for PerformanceComparator"""
    
    @pytest.fixture
    def comparator(self):
        """Create performance comparator for testing"""
        return PerformanceComparator()
    
    @pytest.fixture
    def control_group(self):
        """Create mock control group"""
        return TestGroup(
            group_type="control",
            accounts=["ACC001", "ACC002", "ACC003"],
            allocation_percentage=Decimal('50')
        )
    
    @pytest.fixture
    def treatment_group(self):
        """Create mock treatment group"""
        return TestGroup(
            group_type="treatment",
            accounts=["ACC004", "ACC005", "ACC006"],
            allocation_percentage=Decimal('50')
        )
    
    @pytest.fixture
    def mock_control_performance(self):
        """Create mock control group performance"""
        return PerformanceMetrics(
            total_trades=100,
            winning_trades=55,
            losing_trades=45,
            win_rate=Decimal('0.55'),
            profit_factor=Decimal('1.2'),
            expectancy=Decimal('0.01'),
            sharpe_ratio=Decimal('0.8'),
            max_drawdown=Decimal('0.08'),
            total_return=Decimal('0.05'),
            volatility=Decimal('0.015')
        )
    
    @pytest.fixture
    def mock_treatment_performance(self):
        """Create mock treatment group performance"""
        return PerformanceMetrics(
            total_trades=95,
            winning_trades=60,
            losing_trades=35,
            win_rate=Decimal('0.63'),
            profit_factor=Decimal('1.4'),
            expectancy=Decimal('0.015'),
            sharpe_ratio=Decimal('0.9'),
            max_drawdown=Decimal('0.06'),
            total_return=Decimal('0.08'),
            volatility=Decimal('0.012')
        )
    
    @pytest.mark.asyncio
    async def test_compare_groups(self, comparator, control_group, treatment_group, 
                                mock_control_performance, mock_treatment_performance):
        """Test group performance comparison"""
        with patch.object(comparator, '_get_group_performance') as mock_get_perf:
            mock_get_perf.side_effect = [mock_control_performance, mock_treatment_performance]
            
            comparison = await comparator.compare_groups(control_group, treatment_group)
            
            assert isinstance(comparison, PerformanceComparison)
            assert comparison.control_performance == mock_control_performance
            assert comparison.treatment_performance == mock_treatment_performance
            assert comparison.relative_improvement > 0  # Treatment should be better
            assert comparison.statistical_analysis is not None
    
    @pytest.mark.asyncio
    async def test_get_group_performance(self, comparator, control_group):
        """Test getting group performance metrics"""
        # Mock the performance data provider
        mock_account_perf = PerformanceMetrics(
            total_trades=50,
            winning_trades=30,
            losing_trades=20,
            win_rate=Decimal('0.6'),
            total_return=Decimal('0.03'),
            average_win=Decimal('100'),
            average_loss=Decimal('50'),
            max_drawdown=Decimal('0.05')
        )
        
        with patch.object(comparator.performance_data_provider, 'get_account_performance') as mock_get:
            mock_get.return_value = mock_account_perf
            
            performance = await comparator._get_group_performance(control_group)
            
            assert isinstance(performance, PerformanceMetrics)
            assert performance.total_trades == 150  # 3 accounts * 50 trades
            assert performance.winning_trades == 90   # 3 accounts * 30 wins
    
    @pytest.mark.asyncio
    async def test_calculate_relative_improvement(self, comparator, mock_control_performance, 
                                                mock_treatment_performance):
        """Test relative improvement calculation"""
        improvement = await comparator._calculate_relative_improvement(
            mock_control_performance, mock_treatment_performance
        )
        
        # Treatment expectancy (0.015) vs control (0.01) = 50% improvement
        expected = (Decimal('0.015') - Decimal('0.01')) / Decimal('0.01')
        assert abs(improvement - expected) < Decimal('0.001')
    
    @pytest.mark.asyncio
    async def test_calculate_relative_improvement_zero_baseline(self, comparator):
        """Test relative improvement with zero baseline"""
        control = PerformanceMetrics(expectancy=Decimal('0'))
        treatment = PerformanceMetrics(expectancy=Decimal('0.01'))
        
        improvement = await comparator._calculate_relative_improvement(control, treatment)
        assert improvement == Decimal('0.01')  # Should return absolute difference
    
    @pytest.mark.asyncio
    async def test_perform_statistical_tests(self, comparator):
        """Test statistical testing functionality"""
        # Create sample data
        control_data = [float(np.random.normal(10, 5)) for _ in range(50)]
        treatment_data = [float(np.random.normal(12, 5)) for _ in range(50)]
        
        results = await comparator._perform_statistical_tests(control_data, treatment_data)
        
        assert 'p_value' in results
        assert 't_statistic' in results
        assert 'degrees_of_freedom' in results
        assert 0 <= results['p_value'] <= 1
        assert results['degrees_of_freedom'] == 98  # n1 + n2 - 2
    
    @pytest.mark.asyncio
    async def test_perform_statistical_tests_insufficient_data(self, comparator):
        """Test statistical tests with insufficient data"""
        control_data = [1.0, 2.0]  # Too few samples
        treatment_data = [2.0, 3.0]
        
        results = await comparator._perform_statistical_tests(control_data, treatment_data)
        
        assert results['p_value'] == 1.0  # Should return default values
        assert results['t_statistic'] == 0.0
    
    @pytest.mark.asyncio
    async def test_calculate_effect_size(self, comparator):
        """Test Cohen's d effect size calculation"""
        control_data = [10.0] * 50  # Mean = 10, std = 0
        treatment_data = [12.0] * 50  # Mean = 12, std = 0
        
        # Add some variance
        control_data = [10.0 + np.random.normal(0, 2) for _ in range(50)]
        treatment_data = [12.0 + np.random.normal(0, 2) for _ in range(50)]
        
        effect_size = await comparator._calculate_effect_size(control_data, treatment_data)
        
        # Should be positive (treatment > control) and reasonable magnitude
        assert effect_size > 0
        assert -5 < effect_size < 5  # Reasonable range
    
    @pytest.mark.asyncio
    async def test_calculate_effect_size_insufficient_data(self, comparator):
        """Test effect size calculation with insufficient data"""
        control_data = [1.0]  # Only one sample
        treatment_data = [2.0]
        
        effect_size = await comparator._calculate_effect_size(control_data, treatment_data)
        assert effect_size == 0.0
    
    @pytest.mark.asyncio
    async def test_calculate_confidence_interval(self, comparator):
        """Test confidence interval calculation"""
        control_data = [float(np.random.normal(10, 2)) for _ in range(30)]
        treatment_data = [float(np.random.normal(12, 2)) for _ in range(30)]
        
        ci_lower, ci_upper = await comparator._calculate_confidence_interval(
            control_data, treatment_data
        )
        
        assert ci_lower < ci_upper  # Lower bound should be less than upper
        assert isinstance(ci_lower, float)
        assert isinstance(ci_upper, float)
    
    @pytest.mark.asyncio
    async def test_calculate_confidence_interval_insufficient_data(self, comparator):
        """Test confidence interval with insufficient data"""
        control_data = [1.0, 2.0]  # Too few samples
        treatment_data = [2.0, 3.0]
        
        ci_lower, ci_upper = await comparator._calculate_confidence_interval(
            control_data, treatment_data
        )
        
        assert ci_lower == 0.0
        assert ci_upper == 0.0
    
    def test_remove_outliers(self, comparator):
        """Test outlier removal functionality"""
        # Create data with outliers
        normal_data = [float(np.random.normal(0, 1)) for _ in range(50)]
        outliers = [10.0, -10.0, 15.0]  # Clear outliers
        data_with_outliers = normal_data + outliers
        
        filtered_data = comparator._remove_outliers(data_with_outliers)
        
        # Should remove the extreme outliers
        assert len(filtered_data) < len(data_with_outliers)
        assert 10.0 not in filtered_data
        assert -10.0 not in filtered_data
        assert 15.0 not in filtered_data
    
    def test_remove_outliers_insufficient_data(self, comparator):
        """Test outlier removal with insufficient data"""
        small_data = [1.0, 2.0, 3.0]  # Less than 10 points
        
        filtered_data = comparator._remove_outliers(small_data)
        
        # Should return original data unchanged
        assert filtered_data == small_data
    
    @pytest.mark.asyncio
    async def test_calculate_risk_adjusted_improvement(self, comparator):
        """Test risk-adjusted improvement calculation"""
        control = PerformanceMetrics(
            expectancy=Decimal('0.01'),
            sharpe_ratio=Decimal('0.8'),
            volatility=Decimal('0.015')
        )
        treatment = PerformanceMetrics(
            expectancy=Decimal('0.015'),
            sharpe_ratio=Decimal('0.9'),
            volatility=Decimal('0.012')
        )
        
        risk_adjusted = await comparator._calculate_risk_adjusted_improvement(control, treatment)
        
        # Should use Sharpe ratio difference since both are valid
        expected = treatment.sharpe_ratio - control.sharpe_ratio
        assert risk_adjusted == expected
    
    @pytest.mark.asyncio
    async def test_calculate_risk_adjusted_improvement_no_sharpe(self, comparator):
        """Test risk-adjusted improvement without Sharpe ratios"""
        control = PerformanceMetrics(
            expectancy=Decimal('0.01'),
            sharpe_ratio=Decimal('0'),  # Invalid Sharpe
            volatility=Decimal('0.015')
        )
        treatment = PerformanceMetrics(
            expectancy=Decimal('0.015'),
            sharpe_ratio=Decimal('0'),  # Invalid Sharpe
            volatility=Decimal('0.020')  # Higher volatility
        )
        
        risk_adjusted = await comparator._calculate_risk_adjusted_improvement(control, treatment)
        
        # Should penalize for higher volatility
        return_improvement = treatment.expectancy - control.expectancy
        volatility_penalty = (treatment.volatility - control.volatility) * Decimal('0.5')
        expected = return_improvement - volatility_penalty
        
        assert risk_adjusted == expected
    
    @pytest.mark.asyncio
    async def test_get_comparison_summary(self, comparator, control_group, treatment_group,
                                        mock_control_performance, mock_treatment_performance):
        """Test comparison summary generation"""
        with patch.object(comparator, '_get_group_performance') as mock_get_perf:
            mock_get_perf.side_effect = [mock_control_performance, mock_treatment_performance]
            
            summary = await comparator.get_comparison_summary(control_group, treatment_group)
            
            assert 'relative_improvement' in summary
            assert 'percentage_improvement' in summary
            assert 'statistically_significant' in summary
            assert 'p_value' in summary
            assert 'recommendation' in summary
            
            # Treatment is better, so improvement should be positive
            assert summary['relative_improvement'] > 0
    
    def test_get_recommendation_advance(self, comparator):
        """Test recommendation for advancement"""
        # Good performance with significance
        comparison = Mock()
        comparison.statistical_analysis.statistically_significant = True
        comparison.relative_improvement = Decimal('0.05')  # 5% improvement
        comparison.risk_adjusted_improvement = Decimal('0.02')  # 2% risk-adjusted
        
        recommendation = comparator._get_recommendation(comparison)
        assert recommendation == "advance"
    
    def test_get_recommendation_rollback(self, comparator):
        """Test recommendation for rollback"""
        # Poor performance
        comparison = Mock()
        comparison.statistical_analysis.statistically_significant = True
        comparison.relative_improvement = Decimal('-0.08')  # 8% degradation
        comparison.risk_adjusted_improvement = Decimal('-0.08')
        
        recommendation = comparator._get_recommendation(comparison)
        assert recommendation == "rollback"
    
    def test_get_recommendation_hold(self, comparator):
        """Test recommendation to hold"""
        # Not statistically significant
        comparison = Mock()
        comparison.statistical_analysis.statistically_significant = False
        comparison.relative_improvement = Decimal('0.03')
        comparison.risk_adjusted_improvement = Decimal('0.01')
        
        recommendation = comparator._get_recommendation(comparison)
        assert recommendation == "hold"
    
    def test_get_recommendation_caution(self, comparator):
        """Test recommendation for caution"""
        # Good return but high risk
        comparison = Mock()
        comparison.statistical_analysis.statistically_significant = True
        comparison.relative_improvement = Decimal('0.05')  # Good improvement
        comparison.risk_adjusted_improvement = Decimal('0.005')  # But low risk-adjusted
        
        recommendation = comparator._get_recommendation(comparison)
        assert recommendation == "caution"
    
    @pytest.mark.asyncio
    async def test_validate_sample_adequacy(self, comparator, control_group, treatment_group):
        """Test sample size adequacy validation"""
        # Mock returns for adequate sample
        with patch.object(comparator, '_get_group_returns') as mock_returns:
            mock_returns.side_effect = [
                [float(np.random.normal(0, 1)) for _ in range(50)],  # Control
                [float(np.random.normal(0, 1)) for _ in range(50)]   # Treatment
            ]
            
            adequacy = await comparator.validate_sample_adequacy(control_group, treatment_group)
            
            assert 'adequate_sample' in adequacy
            assert 'actual_sample_size' in adequacy
            assert 'power_achieved' in adequacy
            assert adequacy['actual_sample_size'] == 50
    
    @pytest.mark.asyncio
    async def test_validate_sample_adequacy_insufficient(self, comparator, control_group, treatment_group):
        """Test sample adequacy with insufficient data"""
        # Mock returns for insufficient sample
        with patch.object(comparator, '_get_group_returns') as mock_returns:
            mock_returns.side_effect = [
                [1.0, 2.0, 3.0],  # Control - too few
                [2.0, 3.0, 4.0]   # Treatment - too few
            ]
            
            adequacy = await comparator.validate_sample_adequacy(control_group, treatment_group)
            
            assert adequacy['adequate_sample'] is False
            assert adequacy['actual_sample_size'] == 3


@pytest.mark.asyncio
async def test_performance_comparison_integration():
    """Integration test for complete performance comparison workflow"""
    comparator = PerformanceComparator()
    
    # Create test groups
    control_group = TestGroup(
        group_type="control",
        accounts=["CTL001", "CTL002", "CTL003"],
        allocation_percentage=Decimal('50')
    )
    
    treatment_group = TestGroup(
        group_type="treatment", 
        accounts=["TRT001", "TRT002", "TRT003"],
        allocation_percentage=Decimal('50')
    )
    
    # Mock performance data
    control_perf = PerformanceMetrics(
        total_trades=120,
        winning_trades=66,
        losing_trades=54,
        win_rate=Decimal('0.55'),
        expectancy=Decimal('0.008'),
        total_return=Decimal('0.04'),
        sharpe_ratio=Decimal('0.75'),
        max_drawdown=Decimal('0.09'),
        volatility=Decimal('0.018')
    )
    
    treatment_perf = PerformanceMetrics(
        total_trades=115,
        winning_trades=75,
        losing_trades=40,
        win_rate=Decimal('0.65'),
        expectancy=Decimal('0.012'),
        total_return=Decimal('0.065'),
        sharpe_ratio=Decimal('0.92'),
        max_drawdown=Decimal('0.065'),
        volatility=Decimal('0.015')
    )
    
    # Mock the data providers
    with patch.object(comparator, '_get_group_performance') as mock_get_perf:
        mock_get_perf.side_effect = [control_perf, treatment_perf]
        
        # Perform comparison
        comparison = await comparator.compare_groups(control_group, treatment_group)
        
        # Verify comprehensive comparison
        assert isinstance(comparison, PerformanceComparison)
        assert comparison.relative_improvement > 0  # Treatment better
        assert comparison.statistical_analysis.sample_size > 0
        
        # Get summary
        summary = await comparator.get_comparison_summary(control_group, treatment_group)
        assert summary['recommendation'] in ['advance', 'caution', 'hold', 'manual_review']
        
        # Check sample adequacy
        adequacy = await comparator.validate_sample_adequacy(control_group, treatment_group)
        assert 'adequate_sample' in adequacy


if __name__ == "__main__":
    pytest.main([__file__, "-v"])