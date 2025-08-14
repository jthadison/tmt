"""
Performance Comparison Engine

Provides comprehensive statistical analysis and performance comparison between
control and treatment groups in A/B testing. This engine is critical for
making data-driven decisions about improvement advancement and rollback.

Key Features:
- Statistical significance testing (t-tests, Mann-Whitney U)
- Effect size calculation (Cohen's d, eta squared)
- Confidence interval estimation
- Power analysis and sample size calculations
- Risk-adjusted performance metrics
- Time-series performance analysis
- Variance and correlation impact assessment
"""

import logging
import numpy as np
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import asdict
import scipy.stats as stats
from sklearn.metrics import mean_squared_error

from .models import (
    PerformanceMetrics, PerformanceComparison, StatisticalAnalysis,
    TestGroup, ImprovementTest
)

# Import data interfaces
from ...src.shared.python_utils.data_interfaces import (
    PerformanceDataInterface, MockPerformanceDataProvider,
    TradeDataInterface, MockTradeDataProvider
)

logger = logging.getLogger(__name__)


class PerformanceComparator:
    """
    Advanced performance comparison engine for A/B testing validation.
    
    This engine provides comprehensive statistical analysis to determine
    whether improvements should advance, rollback, or require manual review.
    It implements rigorous statistical methods to ensure reliable decision-making.
    """
    
    def __init__(self,
                 performance_data_provider: Optional[PerformanceDataInterface] = None,
                 trade_data_provider: Optional[TradeDataInterface] = None):
        
        # Data providers
        self.performance_data_provider = performance_data_provider or MockPerformanceDataProvider()
        self.trade_data_provider = trade_data_provider or MockTradeDataProvider()
        
        # Statistical configuration
        self.config = {
            'significance_level': 0.05,  # 95% confidence
            'power_level': 0.8,  # 80% power
            'min_effect_size': 0.2,  # Minimum meaningful effect size (Cohen's d)
            'min_sample_size': 30,  # Minimum sample for statistical tests
            'outlier_threshold': 3.0,  # Standard deviations for outlier detection
            'bootstrap_iterations': 1000,  # Bootstrap resampling iterations
            'confidence_level': 0.95,  # Confidence interval level
            'bonferroni_correction': True  # Multiple comparison correction
        }
        
        # Performance comparison cache
        self._comparison_cache: Dict[str, PerformanceComparison] = {}
        
        logger.info("Performance Comparator initialized")
    
    async def compare_groups(self, control_group: TestGroup, 
                           treatment_group: TestGroup) -> PerformanceComparison:
        """
        Perform comprehensive performance comparison between control and treatment groups.
        
        Args:
            control_group: Control group data
            treatment_group: Treatment group data
            
        Returns:
            PerformanceComparison with detailed statistical analysis
        """
        try:
            logger.info(f"Comparing performance: Control({len(control_group.accounts)}) vs Treatment({len(treatment_group.accounts)})")
            
            # Get performance metrics for both groups
            control_metrics = await self._get_group_performance(control_group)
            treatment_metrics = await self._get_group_performance(treatment_group)
            
            # Calculate relative performance
            relative_improvement = await self._calculate_relative_improvement(
                control_metrics, treatment_metrics
            )
            
            # Perform statistical analysis
            statistical_analysis = await self._perform_statistical_analysis(
                control_group, treatment_group, control_metrics, treatment_metrics
            )
            
            # Calculate risk-adjusted metrics
            risk_adjusted_improvement = await self._calculate_risk_adjusted_improvement(
                control_metrics, treatment_metrics
            )
            
            # Build comprehensive comparison
            comparison = PerformanceComparison(
                control_performance=control_metrics,
                treatment_performance=treatment_metrics,
                relative_improvement=relative_improvement,
                absolute_difference=treatment_metrics.expectancy - control_metrics.expectancy,
                percentage_improvement=relative_improvement * 100,
                statistical_analysis=statistical_analysis,
                risk_adjusted_improvement=risk_adjusted_improvement,
                correlation_impact=await self._calculate_correlation_impact(control_group, treatment_group),
                volatility_impact=treatment_metrics.volatility - control_metrics.volatility
            )
            
            # Cache results
            cache_key = f"{control_group.group_id}_{treatment_group.group_id}"
            self._comparison_cache[cache_key] = comparison
            
            logger.info(f"Performance comparison completed: {relative_improvement:.2%} improvement")
            return comparison
            
        except Exception as e:
            logger.error(f"Failed to compare group performance: {e}")
            raise
    
    async def _get_group_performance(self, group: TestGroup) -> PerformanceMetrics:
        """Get aggregated performance metrics for a test group"""
        
        if group.current_performance:
            return group.current_performance
        
        # Aggregate performance across all accounts in the group
        aggregated_metrics = PerformanceMetrics()
        total_trades = 0
        total_return = Decimal('0')
        daily_returns = []
        all_trade_durations = []
        win_count = 0
        loss_count = 0
        total_wins = Decimal('0')
        total_losses = Decimal('0')
        
        for account_id in group.accounts:
            try:
                # Get account performance data
                account_perf = await self.performance_data_provider.get_account_performance(
                    account_id, 'daily'
                )
                
                if account_perf:
                    total_trades += account_perf.total_trades
                    total_return += account_perf.total_return
                    win_count += account_perf.winning_trades
                    loss_count += account_perf.losing_trades
                    total_wins += account_perf.average_win * account_perf.winning_trades
                    total_losses += account_perf.average_loss * account_perf.losing_trades
                    
                    # Get daily returns for volatility calculation
                    account_returns = await self._get_account_daily_returns(account_id)
                    daily_returns.extend(account_returns)
                
            except Exception as e:
                logger.warning(f"Failed to get performance for account {account_id}: {e}")
        
        # Calculate aggregated metrics
        if total_trades > 0:
            aggregated_metrics.total_trades = total_trades
            aggregated_metrics.winning_trades = win_count
            aggregated_metrics.losing_trades = loss_count
            aggregated_metrics.win_rate = Decimal(str(win_count / total_trades))
            aggregated_metrics.total_return = total_return
            
            if win_count > 0:
                aggregated_metrics.average_win = total_wins / win_count
            if loss_count > 0:
                aggregated_metrics.average_loss = total_losses / loss_count
            
            # Calculate profit factor
            if total_losses > 0:
                aggregated_metrics.profit_factor = total_wins / total_losses
            else:
                aggregated_metrics.profit_factor = Decimal('1000')  # Very high if no losses
            
            # Calculate expectancy
            win_rate = aggregated_metrics.win_rate
            avg_win = aggregated_metrics.average_win
            avg_loss = aggregated_metrics.average_loss
            aggregated_metrics.expectancy = (win_rate * avg_win) - ((Decimal('1') - win_rate) * avg_loss)
            
            # Calculate volatility and Sharpe ratio
            if len(daily_returns) > 1:
                returns_array = np.array([float(r) for r in daily_returns])
                aggregated_metrics.volatility = Decimal(str(np.std(returns_array)))
                
                mean_return = np.mean(returns_array)
                std_return = np.std(returns_array)
                if std_return > 0:
                    aggregated_metrics.sharpe_ratio = Decimal(str(mean_return / std_return))
            
            # Calculate max drawdown
            aggregated_metrics.max_drawdown = await self._calculate_max_drawdown(group.accounts)
        
        return aggregated_metrics
    
    async def _get_account_daily_returns(self, account_id: str) -> List[Decimal]:
        """Get daily returns for an account"""
        try:
            # Get trade data for the account
            trades = await self.trade_data_provider.get_account_trades(account_id, limit=1000)
            
            # Group trades by date and calculate daily returns
            daily_pnl = {}
            for trade in trades:
                trade_date = trade.timestamp.date()
                if trade_date not in daily_pnl:
                    daily_pnl[trade_date] = Decimal('0')
                daily_pnl[trade_date] += trade.pnl
            
            return list(daily_pnl.values())
            
        except Exception as e:
            logger.warning(f"Failed to get daily returns for account {account_id}: {e}")
            return []
    
    async def _calculate_max_drawdown(self, accounts: List[str]) -> Decimal:
        """Calculate maximum drawdown across accounts"""
        max_drawdown = Decimal('0')
        
        for account_id in accounts:
            try:
                account_perf = await self.performance_data_provider.get_account_performance(
                    account_id, 'daily'
                )
                if account_perf and account_perf.max_drawdown > max_drawdown:
                    max_drawdown = account_perf.max_drawdown
            except Exception as e:
                logger.warning(f"Failed to get drawdown for account {account_id}: {e}")
        
        return max_drawdown
    
    async def _calculate_relative_improvement(self, control: PerformanceMetrics, 
                                           treatment: PerformanceMetrics) -> Decimal:
        """Calculate relative improvement of treatment vs control"""
        
        if control.expectancy == 0:
            # If control has zero expectancy, use absolute difference
            return treatment.expectancy
        
        # Calculate relative improvement based on expectancy
        relative_improvement = (treatment.expectancy - control.expectancy) / abs(control.expectancy)
        return relative_improvement
    
    async def _perform_statistical_analysis(self, control_group: TestGroup, 
                                          treatment_group: TestGroup,
                                          control_metrics: PerformanceMetrics,
                                          treatment_metrics: PerformanceMetrics) -> StatisticalAnalysis:
        """Perform comprehensive statistical analysis"""
        
        try:
            # Get raw return data for both groups
            control_returns = await self._get_group_returns(control_group)
            treatment_returns = await self._get_group_returns(treatment_group)
            
            # Check minimum sample size
            sample_size = min(len(control_returns), len(treatment_returns))
            if sample_size < self.config['min_sample_size']:
                logger.warning(f"Insufficient sample size: {sample_size} < {self.config['min_sample_size']}")
            
            # Perform statistical tests
            test_results = await self._perform_statistical_tests(control_returns, treatment_returns)
            
            # Calculate effect size
            effect_size = await self._calculate_effect_size(control_returns, treatment_returns)
            
            # Calculate confidence intervals
            confidence_interval = await self._calculate_confidence_interval(
                control_returns, treatment_returns
            )
            
            # Perform power analysis
            power_analysis = await self._calculate_power_analysis(
                control_returns, treatment_returns, effect_size
            )
            
            # Determine statistical significance
            significance_level = self.config['significance_level']
            if self.config['bonferroni_correction']:
                # Adjust for multiple comparisons
                significance_level = significance_level / 3  # Assuming 3 main tests
            
            statistically_significant = (
                test_results['p_value'] < significance_level and 
                abs(effect_size) >= self.config['min_effect_size'] and
                sample_size >= self.config['min_sample_size']
            )
            
            return StatisticalAnalysis(
                sample_size=sample_size,
                power_analysis=power_analysis,
                p_value=test_results['p_value'],
                confidence_interval=confidence_interval,
                effect_size=effect_size,
                statistically_significant=statistically_significant,
                significance_level=significance_level,
                t_statistic=test_results.get('t_statistic'),
                degrees_of_freedom=test_results.get('degrees_of_freedom'),
                confidence_level=self.config['confidence_level']
            )
            
        except Exception as e:
            logger.error(f"Statistical analysis failed: {e}")
            # Return default analysis
            return StatisticalAnalysis(
                sample_size=0,
                power_analysis=0.0,
                p_value=1.0,
                confidence_interval=(0.0, 0.0),
                effect_size=0.0,
                statistically_significant=False
            )
    
    async def _get_group_returns(self, group: TestGroup) -> List[float]:
        """Get individual trade returns for a group"""
        all_returns = []
        
        for account_id in group.accounts:
            try:
                trades = await self.trade_data_provider.get_account_trades(account_id, limit=500)
                account_returns = [float(trade.pnl) for trade in trades if trade.pnl is not None]
                all_returns.extend(account_returns)
            except Exception as e:
                logger.warning(f"Failed to get returns for account {account_id}: {e}")
        
        # Remove outliers
        if len(all_returns) > 10:
            all_returns = self._remove_outliers(all_returns)
        
        return all_returns
    
    def _remove_outliers(self, data: List[float]) -> List[float]:
        """Remove statistical outliers using Z-score method"""
        if len(data) < 10:
            return data
        
        data_array = np.array(data)
        mean = np.mean(data_array)
        std = np.std(data_array)
        
        if std == 0:
            return data
        
        z_scores = np.abs((data_array - mean) / std)
        threshold = self.config['outlier_threshold']
        
        filtered_data = data_array[z_scores < threshold]
        
        removed_count = len(data) - len(filtered_data)
        if removed_count > 0:
            logger.debug(f"Removed {removed_count} outliers from dataset")
        
        return filtered_data.tolist()
    
    async def _perform_statistical_tests(self, control_data: List[float], 
                                       treatment_data: List[float]) -> Dict[str, float]:
        """Perform multiple statistical tests"""
        
        if len(control_data) < 3 or len(treatment_data) < 3:
            return {'p_value': 1.0, 't_statistic': 0.0, 'degrees_of_freedom': 0}
        
        # Convert to numpy arrays
        control_array = np.array(control_data)
        treatment_array = np.array(treatment_data)
        
        try:
            # Welch's t-test (unequal variances)
            t_stat, p_value = stats.ttest_ind(treatment_array, control_array, equal_var=False)
            
            # Mann-Whitney U test (non-parametric alternative)
            u_stat, u_p_value = stats.mannwhitneyu(treatment_array, control_array, alternative='two-sided')
            
            # Kolmogorov-Smirnov test (distribution comparison)
            ks_stat, ks_p_value = stats.ks_2samp(treatment_array, control_array)
            
            # Use the most conservative p-value
            final_p_value = max(p_value, u_p_value, ks_p_value)
            
            degrees_of_freedom = len(control_data) + len(treatment_data) - 2
            
            return {
                'p_value': final_p_value,
                't_statistic': float(t_stat) if not np.isnan(t_stat) else 0.0,
                'u_statistic': float(u_stat) if not np.isnan(u_stat) else 0.0,
                'ks_statistic': float(ks_stat) if not np.isnan(ks_stat) else 0.0,
                'degrees_of_freedom': degrees_of_freedom
            }
            
        except Exception as e:
            logger.error(f"Statistical tests failed: {e}")
            return {'p_value': 1.0, 't_statistic': 0.0, 'degrees_of_freedom': 0}
    
    async def _calculate_effect_size(self, control_data: List[float], 
                                   treatment_data: List[float]) -> float:
        """Calculate Cohen's d effect size"""
        
        if len(control_data) < 2 or len(treatment_data) < 2:
            return 0.0
        
        try:
            control_array = np.array(control_data)
            treatment_array = np.array(treatment_data)
            
            # Calculate means
            control_mean = np.mean(control_array)
            treatment_mean = np.mean(treatment_array)
            
            # Calculate pooled standard deviation
            control_std = np.std(control_array, ddof=1)
            treatment_std = np.std(treatment_array, ddof=1)
            
            n1, n2 = len(control_data), len(treatment_data)
            pooled_std = np.sqrt(((n1 - 1) * control_std**2 + (n2 - 1) * treatment_std**2) / (n1 + n2 - 2))
            
            if pooled_std == 0:
                return 0.0
            
            # Cohen's d
            cohens_d = (treatment_mean - control_mean) / pooled_std
            
            return float(cohens_d)
            
        except Exception as e:
            logger.error(f"Effect size calculation failed: {e}")
            return 0.0
    
    async def _calculate_confidence_interval(self, control_data: List[float], 
                                           treatment_data: List[float]) -> Tuple[float, float]:
        """Calculate confidence interval for the difference in means"""
        
        if len(control_data) < 3 or len(treatment_data) < 3:
            return (0.0, 0.0)
        
        try:
            control_array = np.array(control_data)
            treatment_array = np.array(treatment_data)
            
            # Calculate difference in means
            diff_mean = np.mean(treatment_array) - np.mean(control_array)
            
            # Calculate standard error of the difference
            se_control = stats.sem(control_array)
            se_treatment = stats.sem(treatment_array)
            se_diff = np.sqrt(se_control**2 + se_treatment**2)
            
            # Calculate confidence interval
            confidence_level = self.config['confidence_level']
            alpha = 1 - confidence_level
            df = len(control_data) + len(treatment_data) - 2
            t_critical = stats.t.ppf(1 - alpha/2, df)
            
            margin_error = t_critical * se_diff
            ci_lower = diff_mean - margin_error
            ci_upper = diff_mean + margin_error
            
            return (float(ci_lower), float(ci_upper))
            
        except Exception as e:
            logger.error(f"Confidence interval calculation failed: {e}")
            return (0.0, 0.0)
    
    async def _calculate_power_analysis(self, control_data: List[float], 
                                      treatment_data: List[float], 
                                      effect_size: float) -> float:
        """Calculate statistical power of the test"""
        
        try:
            from statsmodels.stats.power import ttest_power
            
            sample_size = min(len(control_data), len(treatment_data))
            alpha = self.config['significance_level']
            
            # Calculate power
            power = ttest_power(effect_size, sample_size, alpha, alternative='two-sided')
            
            return float(power)
            
        except ImportError:
            logger.warning("statsmodels not available for power analysis")
            # Simplified power calculation
            sample_size = min(len(control_data), len(treatment_data))
            if sample_size < 30:
                return max(0.1, sample_size / 30 * 0.8)
            else:
                return min(0.95, 0.8 + (sample_size - 30) * 0.001)
        except Exception as e:
            logger.error(f"Power analysis failed: {e}")
            return 0.5
    
    async def _calculate_risk_adjusted_improvement(self, control: PerformanceMetrics,
                                                 treatment: PerformanceMetrics) -> Decimal:
        """Calculate risk-adjusted improvement (Sharpe ratio improvement)"""
        
        try:
            # If we have valid Sharpe ratios, use them
            if control.sharpe_ratio != 0 and treatment.sharpe_ratio != 0:
                return treatment.sharpe_ratio - control.sharpe_ratio
            
            # Otherwise, adjust return improvement by volatility increase
            return_improvement = treatment.expectancy - control.expectancy
            volatility_penalty = treatment.volatility - control.volatility
            
            # Penalize improvements that come with significantly higher volatility
            risk_adjusted = return_improvement - (volatility_penalty * Decimal('0.5'))
            
            return risk_adjusted
            
        except Exception as e:
            logger.error(f"Risk adjustment calculation failed: {e}")
            return treatment.expectancy - control.expectancy
    
    async def _calculate_correlation_impact(self, control_group: TestGroup, 
                                          treatment_group: TestGroup) -> Decimal:
        """Calculate correlation impact between groups"""
        
        try:
            control_returns = await self._get_group_returns(control_group)
            treatment_returns = await self._get_group_returns(treatment_group)
            
            if len(control_returns) < 10 or len(treatment_returns) < 10:
                return Decimal('0')
            
            # Align the data by taking the minimum length
            min_length = min(len(control_returns), len(treatment_returns))
            control_aligned = control_returns[:min_length]
            treatment_aligned = treatment_returns[:min_length]
            
            # Calculate correlation
            correlation = np.corrcoef(control_aligned, treatment_aligned)[0, 1]
            
            if np.isnan(correlation):
                return Decimal('0')
            
            # Return correlation as impact measure
            return Decimal(str(correlation))
            
        except Exception as e:
            logger.error(f"Correlation calculation failed: {e}")
            return Decimal('0')
    
    # Public API methods
    
    async def get_comparison_summary(self, control_group: TestGroup, 
                                   treatment_group: TestGroup) -> Dict[str, Any]:
        """Get a summary of performance comparison"""
        
        comparison = await self.compare_groups(control_group, treatment_group)
        
        return {
            'relative_improvement': float(comparison.relative_improvement),
            'percentage_improvement': float(comparison.percentage_improvement),
            'statistically_significant': comparison.statistical_analysis.statistically_significant,
            'p_value': comparison.statistical_analysis.p_value,
            'effect_size': comparison.statistical_analysis.effect_size,
            'confidence_interval': comparison.statistical_analysis.confidence_interval,
            'sample_size': comparison.statistical_analysis.sample_size,
            'risk_adjusted_improvement': float(comparison.risk_adjusted_improvement),
            'recommendation': self._get_recommendation(comparison)
        }
    
    def _get_recommendation(self, comparison: PerformanceComparison) -> str:
        """Get recommendation based on comparison results"""
        
        if not comparison.statistical_analysis.statistically_significant:
            return "hold"  # Need more data
        
        if comparison.relative_improvement >= Decimal('0.02'):  # 2%+ improvement
            if comparison.risk_adjusted_improvement >= Decimal('0.01'):  # 1%+ risk-adjusted
                return "advance"
            else:
                return "caution"  # Good return but high risk
        elif comparison.relative_improvement <= Decimal('-0.05'):  # 5%+ degradation
            return "rollback"
        else:
            return "manual_review"  # Marginal results
    
    async def validate_sample_adequacy(self, control_group: TestGroup, 
                                     treatment_group: TestGroup) -> Dict[str, Any]:
        """Validate if sample size is adequate for reliable conclusions"""
        
        control_returns = await self._get_group_returns(control_group)
        treatment_returns = await self._get_group_returns(treatment_group)
        
        min_sample = self.config['min_sample_size']
        actual_sample = min(len(control_returns), len(treatment_returns))
        
        # Calculate required sample size for desired power
        effect_size = await self._calculate_effect_size(control_returns, treatment_returns)
        required_sample = await self._calculate_required_sample_size(effect_size)
        
        return {
            'adequate_sample': actual_sample >= min_sample,
            'minimum_required': min_sample,
            'actual_sample_size': actual_sample,
            'recommended_sample_size': required_sample,
            'power_achieved': await self._calculate_power_analysis(control_returns, treatment_returns, effect_size),
            'days_to_adequate_sample': max(0, (min_sample - actual_sample) // 10)  # Assuming 10 trades/day
        }
    
    async def _calculate_required_sample_size(self, effect_size: float) -> int:
        """Calculate required sample size for desired power"""
        try:
            from statsmodels.stats.power import ttest_power
            
            alpha = self.config['significance_level']
            power = self.config['power_level']
            
            # Binary search for required sample size
            for n in range(10, 1000, 10):
                achieved_power = ttest_power(effect_size, n, alpha)
                if achieved_power >= power:
                    return n
            
            return 500  # Default maximum
            
        except ImportError:
            # Simple heuristic if statsmodels not available
            if abs(effect_size) >= 0.8:  # Large effect
                return 30
            elif abs(effect_size) >= 0.5:  # Medium effect
                return 50
            else:  # Small effect
                return 100