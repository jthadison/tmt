"""
Statistical significance testing for strategy performance.
"""
import logging
import math
from decimal import Decimal
from typing import List, Tuple
from scipy import stats
import numpy as np

from .models import StatisticalSignificance

logger = logging.getLogger(__name__)


class StatisticalSignificanceTester:
    """
    Statistical significance testing for trading strategy performance.
    Implements various statistical tests to determine if strategy performance
    is statistically significant or could be due to random chance.
    """
    
    def __init__(self):
        self.default_confidence_level = Decimal('0.95')  # 95% confidence
        self.min_sample_size = 30  # Minimum trades for meaningful testing
    
    async def test_significance(self, trades: List, confidence_level: Decimal = None) -> StatisticalSignificance:
        """
        Test statistical significance of strategy performance.
        
        Args:
            trades: List of Trade objects
            confidence_level: Confidence level for testing (default 0.95)
            
        Returns:
            Statistical significance results
        """
        if confidence_level is None:
            confidence_level = self.default_confidence_level
        
        sample_size = len(trades)
        
        if sample_size == 0:
            return self._create_empty_significance(confidence_level)
        
        # Extract returns/PnL from trades
        returns = [float(trade.pnl) for trade in trades]
        
        # Perform t-test against zero (testing if mean return significantly different from 0)
        t_statistic, p_value = self._perform_t_test(returns)
        
        # Calculate confidence interval
        confidence_interval = self._calculate_confidence_interval(returns, confidence_level)
        
        # Determine if statistically significant
        alpha = 1 - float(confidence_level)
        is_significant = p_value < alpha and sample_size >= self.min_sample_size
        
        # Calculate required sample size for significance
        required_size = self._calculate_required_sample_size(returns, confidence_level)
        
        # Calculate current significance level
        current_sig_level = self._calculate_current_significance_level(returns, sample_size)
        
        return StatisticalSignificance(
            sample_size=sample_size,
            confidence_level=confidence_level,
            p_value=Decimal(str(p_value)),
            confidence_interval=(
                Decimal(str(confidence_interval[0])),
                Decimal(str(confidence_interval[1]))
            ),
            statistically_significant=is_significant,
            required_sample_size=required_size,
            current_significance_level=Decimal(str(current_sig_level))
        )
    
    def _perform_t_test(self, returns: List[float]) -> Tuple[float, float]:
        """
        Perform one-sample t-test against zero.
        
        Args:
            returns: List of return values
            
        Returns:
            Tuple of (t_statistic, p_value)
        """
        if len(returns) < 2:
            return 0.0, 1.0
        
        try:
            # One-sample t-test against zero (null hypothesis: mean return = 0)
            t_statistic, p_value = stats.ttest_1samp(returns, 0.0)
            
            # Handle NaN values
            if math.isnan(t_statistic) or math.isnan(p_value):
                return 0.0, 1.0
            
            return float(t_statistic), float(p_value)
        
        except Exception as e:
            logger.warning(f"Error in t-test calculation: {e}")
            return 0.0, 1.0
    
    def _calculate_confidence_interval(self, returns: List[float], confidence_level: Decimal) -> Tuple[float, float]:
        """
        Calculate confidence interval for mean return.
        
        Args:
            returns: List of return values
            confidence_level: Confidence level (e.g., 0.95 for 95%)
            
        Returns:
            Tuple of (lower_bound, upper_bound)
        """
        if len(returns) < 2:
            return (0.0, 0.0)
        
        try:
            alpha = 1 - float(confidence_level)
            mean_return = np.mean(returns)
            std_error = stats.sem(returns)  # Standard error of the mean
            
            # Calculate degrees of freedom
            df = len(returns) - 1
            
            # Get critical t-value
            t_critical = stats.t.ppf(1 - alpha/2, df)
            
            # Calculate margin of error
            margin_of_error = t_critical * std_error
            
            lower_bound = mean_return - margin_of_error
            upper_bound = mean_return + margin_of_error
            
            return (float(lower_bound), float(upper_bound))
        
        except Exception as e:
            logger.warning(f"Error calculating confidence interval: {e}")
            return (0.0, 0.0)
    
    def _calculate_required_sample_size(self, returns: List[float], confidence_level: Decimal) -> int:
        """
        Calculate required sample size for statistical significance.
        
        Uses power analysis to determine sample size needed to detect
        the observed effect size with desired confidence level.
        
        Args:
            returns: List of return values
            confidence_level: Desired confidence level
            
        Returns:
            Required sample size
        """
        if len(returns) < 2:
            return self.min_sample_size
        
        try:
            # Calculate effect size (Cohen's d)
            mean_return = np.mean(returns)
            std_return = np.std(returns, ddof=1)
            
            if std_return == 0:
                return self.min_sample_size
            
            effect_size = abs(mean_return / std_return)
            
            # Use simplified power analysis formula
            # For 80% power and given confidence level
            alpha = 1 - float(confidence_level)
            z_alpha = stats.norm.ppf(1 - alpha/2)  # Critical z-value
            z_beta = stats.norm.ppf(0.8)  # 80% power
            
            # Sample size formula for one-sample t-test
            required_n = ((z_alpha + z_beta) / effect_size) ** 2
            
            # Add some buffer and ensure minimum
            required_n = max(int(required_n * 1.2), self.min_sample_size)
            
            return required_n
        
        except Exception as e:
            logger.warning(f"Error calculating required sample size: {e}")
            return self.min_sample_size
    
    def _calculate_current_significance_level(self, returns: List[float], sample_size: int) -> float:
        """
        Calculate current significance level based on observed data.
        
        Args:
            returns: List of return values
            sample_size: Current sample size
            
        Returns:
            Current significance level (0-1)
        """
        if sample_size < 2:
            return 0.0
        
        try:
            # Calculate normalized significance based on sample size and effect
            mean_return = np.mean(returns)
            std_return = np.std(returns, ddof=1)
            
            if std_return == 0:
                return 1.0 if mean_return > 0 else 0.0
            
            # Calculate t-statistic
            t_stat = mean_return / (std_return / math.sqrt(sample_size))
            
            # Calculate corresponding significance level
            df = sample_size - 1
            p_value = 2 * (1 - stats.t.cdf(abs(t_stat), df))  # Two-tailed test
            
            # Convert p-value to significance level (1 - p_value)
            significance_level = max(0.0, 1.0 - p_value)
            
            return significance_level
        
        except Exception as e:
            logger.warning(f"Error calculating current significance level: {e}")
            return 0.0
    
    def test_strategy_comparison(self, strategy1_returns: List[float], 
                               strategy2_returns: List[float],
                               confidence_level: Decimal = None) -> dict:
        """
        Test if two strategies have significantly different performance.
        
        Args:
            strategy1_returns: Returns for first strategy
            strategy2_returns: Returns for second strategy
            confidence_level: Confidence level for testing
            
        Returns:
            Dictionary with comparison results
        """
        if confidence_level is None:
            confidence_level = self.default_confidence_level
        
        if len(strategy1_returns) < 2 or len(strategy2_returns) < 2:
            return {
                'significantly_different': False,
                'p_value': 1.0,
                'better_strategy': None,
                'confidence_level': float(confidence_level)
            }
        
        try:
            # Perform two-sample t-test
            t_statistic, p_value = stats.ttest_ind(strategy1_returns, strategy2_returns)
            
            alpha = 1 - float(confidence_level)
            is_significant = p_value < alpha
            
            # Determine which strategy is better
            mean1 = np.mean(strategy1_returns)
            mean2 = np.mean(strategy2_returns)
            
            better_strategy = None
            if is_significant:
                better_strategy = 1 if mean1 > mean2 else 2
            
            return {
                'significantly_different': is_significant,
                'p_value': float(p_value),
                'better_strategy': better_strategy,
                'confidence_level': float(confidence_level),
                't_statistic': float(t_statistic),
                'mean_difference': float(mean1 - mean2)
            }
        
        except Exception as e:
            logger.error(f"Error in strategy comparison: {e}")
            return {
                'significantly_different': False,
                'p_value': 1.0,
                'better_strategy': None,
                'confidence_level': float(confidence_level),
                'error': str(e)
            }
    
    def calculate_sharpe_significance(self, returns: List[float], 
                                    confidence_level: Decimal = None) -> dict:
        """
        Test statistical significance of Sharpe ratio.
        
        Args:
            returns: List of return values
            confidence_level: Confidence level for testing
            
        Returns:
            Dictionary with Sharpe ratio significance results
        """
        if confidence_level is None:
            confidence_level = self.default_confidence_level
        
        if len(returns) < 3:
            return {
                'sharpe_ratio': 0.0,
                'sharpe_significant': False,
                'confidence_interval': (0.0, 0.0)
            }
        
        try:
            returns_array = np.array(returns)
            mean_return = np.mean(returns_array)
            std_return = np.std(returns_array, ddof=1)
            
            if std_return == 0:
                sharpe_ratio = 0.0
            else:
                sharpe_ratio = mean_return / std_return
            
            # Calculate confidence interval for Sharpe ratio
            # Using Jobson-Korkie methodology (simplified)
            n = len(returns)
            alpha = 1 - float(confidence_level)
            z_critical = stats.norm.ppf(1 - alpha/2)
            
            if std_return > 0:
                # Approximate standard error for Sharpe ratio
                sharpe_se = math.sqrt((1 + 0.5 * sharpe_ratio**2) / n)
                margin_of_error = z_critical * sharpe_se
                
                lower_bound = sharpe_ratio - margin_of_error
                upper_bound = sharpe_ratio + margin_of_error
            else:
                lower_bound = upper_bound = 0.0
            
            # Test if Sharpe ratio is significantly different from 0
            if std_return > 0:
                t_stat = sharpe_ratio * math.sqrt(n)
                p_value = 2 * (1 - stats.t.cdf(abs(t_stat), n-1))
                is_significant = p_value < alpha
            else:
                is_significant = False
            
            return {
                'sharpe_ratio': float(sharpe_ratio),
                'sharpe_significant': is_significant,
                'confidence_interval': (float(lower_bound), float(upper_bound)),
                'standard_error': float(sharpe_se) if std_return > 0 else 0.0
            }
        
        except Exception as e:
            logger.error(f"Error calculating Sharpe significance: {e}")
            return {
                'sharpe_ratio': 0.0,
                'sharpe_significant': False,
                'confidence_interval': (0.0, 0.0),
                'error': str(e)
            }
    
    def _create_empty_significance(self, confidence_level: Decimal) -> StatisticalSignificance:
        """Create empty significance result for no data."""
        return StatisticalSignificance(
            sample_size=0,
            confidence_level=confidence_level,
            p_value=Decimal('1.0'),
            confidence_interval=(Decimal('0'), Decimal('0')),
            statistically_significant=False,
            required_sample_size=self.min_sample_size,
            current_significance_level=Decimal('0')
        )