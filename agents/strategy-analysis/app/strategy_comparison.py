"""
Strategy comparison and ranking system.
"""
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
import asyncio
from dataclasses import asdict

from .models import (
    TradingStrategy, StrategyRanking, TrendDirection, PerformanceMetrics
)
from .statistical_tester import StatisticalSignificanceTester

logger = logging.getLogger(__name__)


class StrategyComparison:
    """
    System for comparing strategies and generating rankings based on various metrics.
    """
    
    def __init__(self):
        self.statistical_tester = StatisticalSignificanceTester()
        
        # Ranking weights for different metrics
        self.ranking_weights = {
            'performance': {
                'expectancy': Decimal('0.3'),
                'total_return': Decimal('0.25'),
                'win_rate': Decimal('0.2'),
                'profit_factor': Decimal('0.15'),
                'total_trades': Decimal('0.1')
            },
            'risk_adjusted': {
                'sharpe_ratio': Decimal('0.4'),
                'calmar_ratio': Decimal('0.3'),
                'max_drawdown': Decimal('0.2'),  # Inverted (lower is better)
                'expectancy': Decimal('0.1')
            },
            'consistency': {
                'win_rate': Decimal('0.3'),
                'sharpe_ratio': Decimal('0.25'),
                'max_drawdown': Decimal('0.2'),  # Inverted
                'profit_factor': Decimal('0.15'),
                'calmar_ratio': Decimal('0.1')
            },
            'diversification': {
                'correlation_score': Decimal('0.5'),  # Based on correlation analysis
                'regime_adaptability': Decimal('0.3'),
                'consistency_score': Decimal('0.2')
            }
        }
    
    async def rank_strategies_by_performance(self, strategies: List[TradingStrategy]) -> List[StrategyRanking]:
        """Rank strategies by overall performance metrics."""
        return await self._rank_strategies(strategies, 'performance', 'Overall Performance')
    
    async def rank_strategies_by_risk_adjusted_return(self, strategies: List[TradingStrategy]) -> List[StrategyRanking]:
        """Rank strategies by risk-adjusted return metrics."""
        return await self._rank_strategies(strategies, 'risk_adjusted', 'Risk-Adjusted Return')
    
    async def rank_strategies_by_consistency(self, strategies: List[TradingStrategy]) -> List[StrategyRanking]:
        """Rank strategies by performance consistency."""
        return await self._rank_strategies(strategies, 'consistency', 'Consistency')
    
    async def rank_strategies_by_diversification_benefit(self, strategies: List[TradingStrategy],
                                                       correlation_analysis: Optional[Dict] = None) -> List[StrategyRanking]:
        """Rank strategies by their diversification benefit to the portfolio."""
        
        # Calculate diversification scores
        diversification_scores = {}
        
        for strategy in strategies:
            score = await self._calculate_diversification_score(strategy, correlation_analysis)
            diversification_scores[strategy.strategy_id] = score
        
        # Create rankings
        rankings = []
        sorted_strategies = sorted(strategies, key=lambda s: diversification_scores[s.strategy_id], reverse=True)
        
        for rank, strategy in enumerate(sorted_strategies, 1):
            score = diversification_scores[strategy.strategy_id]
            percentile = ((len(strategies) - rank + 1) / len(strategies)) * 100
            
            ranking = StrategyRanking(
                rank=rank,
                strategy_id=strategy.strategy_id,
                strategy_name=strategy.strategy_name,
                score=score,
                metric="Diversification Benefit",
                percentile=Decimal(str(percentile)),
                trend=self._get_strategy_trend(strategy),
                comments=self._generate_diversification_comments(strategy, score)
            )
            rankings.append(ranking)
        
        return rankings
    
    async def _rank_strategies(self, strategies: List[TradingStrategy], 
                             ranking_type: str, metric_name: str) -> List[StrategyRanking]:
        """Generic strategy ranking method."""
        
        if not strategies:
            return []
        
        # Calculate composite scores for each strategy
        strategy_scores = {}
        
        for strategy in strategies:
            score = await self._calculate_composite_score(strategy, ranking_type)
            strategy_scores[strategy.strategy_id] = score
        
        # Sort strategies by score (descending)
        sorted_strategies = sorted(strategies, key=lambda s: strategy_scores[s.strategy_id], reverse=True)
        
        # Create rankings
        rankings = []
        for rank, strategy in enumerate(sorted_strategies, 1):
            score = strategy_scores[strategy.strategy_id]
            percentile = ((len(strategies) - rank + 1) / len(strategies)) * 100
            
            ranking = StrategyRanking(
                rank=rank,
                strategy_id=strategy.strategy_id,
                strategy_name=strategy.strategy_name,
                score=score,
                metric=metric_name,
                percentile=Decimal(str(percentile)),
                trend=self._get_strategy_trend(strategy),
                comments=self._generate_ranking_comments(strategy, ranking_type, rank, len(strategies))
            )
            rankings.append(ranking)
        
        return rankings
    
    async def _calculate_composite_score(self, strategy: TradingStrategy, ranking_type: str) -> Decimal:
        """Calculate composite score for a strategy based on ranking type."""
        
        if ranking_type not in self.ranking_weights:
            logger.warning(f"Unknown ranking type: {ranking_type}")
            return Decimal('0')
        
        weights = self.ranking_weights[ranking_type]
        performance = strategy.performance.overall
        
        # Normalize metrics to 0-1 scale and apply weights
        total_score = Decimal('0')
        total_weight = Decimal('0')
        
        for metric, weight in weights.items():
            normalized_value = await self._normalize_metric(strategy, metric, performance)
            
            if normalized_value is not None:
                total_score += normalized_value * weight
                total_weight += weight
        
        # Return weighted average score (0-100 scale)
        if total_weight > 0:
            return (total_score / total_weight) * Decimal('100')
        else:
            return Decimal('0')
    
    async def _normalize_metric(self, strategy: TradingStrategy, metric: str, 
                              performance: PerformanceMetrics) -> Optional[Decimal]:
        """Normalize a performance metric to 0-1 scale."""
        
        try:
            if metric == 'expectancy':
                # Normalize expectancy (positive is good, scale around typical range)
                value = performance.expectancy
                # Scale: -0.01 = 0, 0 = 0.5, 0.01 = 1.0
                normalized = (value + Decimal('0.01')) / Decimal('0.02')
                return max(Decimal('0'), min(Decimal('1'), normalized))
            
            elif metric == 'total_return':
                # Normalize total return (positive is good)
                value = performance.total_return
                # Scale based on reasonable return range
                normalized = (value + Decimal('0.1')) / Decimal('0.2')  # -10% to +10% range
                return max(Decimal('0'), min(Decimal('1'), normalized))
            
            elif metric == 'win_rate':
                # Win rate is already 0-1, just return it
                return performance.win_rate
            
            elif metric == 'profit_factor':
                # Normalize profit factor (1.0 = break-even, 2.0+ = excellent)
                value = performance.profit_factor
                # Scale: 0.5 = 0, 1.0 = 0.5, 2.0 = 1.0
                normalized = (value - Decimal('0.5')) / Decimal('1.5')
                return max(Decimal('0'), min(Decimal('1'), normalized))
            
            elif metric == 'sharpe_ratio':
                # Normalize Sharpe ratio (0 = break-even, 2.0+ = excellent)
                value = performance.sharpe_ratio
                # Scale: -1.0 = 0, 0 = 0.5, 2.0 = 1.0
                normalized = (value + Decimal('1.0')) / Decimal('3.0')
                return max(Decimal('0'), min(Decimal('1'), normalized))
            
            elif metric == 'calmar_ratio':
                # Normalize Calmar ratio (similar to Sharpe)
                value = performance.calmar_ratio
                normalized = (value + Decimal('1.0')) / Decimal('3.0')
                return max(Decimal('0'), min(Decimal('1'), normalized))
            
            elif metric == 'max_drawdown':
                # Invert max drawdown (lower is better)
                value = performance.max_drawdown
                # Scale: 0.5 = 0, 0.1 = 0.8, 0.0 = 1.0
                normalized = Decimal('1') - min(value / Decimal('0.5'), Decimal('1'))
                return max(Decimal('0'), normalized)
            
            elif metric == 'total_trades':
                # Normalize trade count (more trades = more statistical significance)
                value = Decimal(str(performance.total_trades))
                # Scale: 0 = 0, 100 = 0.5, 500+ = 1.0
                normalized = min(value / Decimal('500'), Decimal('1'))
                return normalized
            
            else:
                logger.warning(f"Unknown metric for normalization: {metric}")
                return None
        
        except Exception as e:
            logger.error(f"Error normalizing metric {metric}: {e}")
            return None
    
    async def _calculate_diversification_score(self, strategy: TradingStrategy,
                                             correlation_analysis: Optional[Dict] = None) -> Decimal:
        """Calculate diversification benefit score for a strategy."""
        
        score = Decimal('50')  # Base score
        
        # Factor 1: Low correlation with other strategies
        if correlation_analysis and 'correlation_matrix' in correlation_analysis:
            correlation_score = await self._calculate_correlation_score(
                strategy, correlation_analysis['correlation_matrix']
            )
            score += correlation_score * Decimal('30')  # Up to 30 points
        
        # Factor 2: Regime adaptability
        regime_score = await self._calculate_regime_adaptability_score(strategy)
        score += regime_score * Decimal('15')  # Up to 15 points
        
        # Factor 3: Consistency across different market conditions
        consistency_score = await self._calculate_consistency_score(strategy)
        score += consistency_score * Decimal('5')  # Up to 5 points
        
        return min(score, Decimal('100'))
    
    async def _calculate_correlation_score(self, strategy: TradingStrategy,
                                         correlation_matrix: Dict[str, Dict[str, Decimal]]) -> Decimal:
        """Calculate correlation score (lower correlation = higher score)."""
        
        strategy_id = strategy.strategy_id
        
        if strategy_id not in correlation_matrix:
            return Decimal('0.5')  # Neutral score if no correlation data
        
        # Calculate average correlation with other strategies
        correlations = []
        for other_id, correlation in correlation_matrix[strategy_id].items():
            if other_id != strategy_id:
                correlations.append(abs(correlation))  # Use absolute correlation
        
        if not correlations:
            return Decimal('1.0')  # Perfect score if no other strategies
        
        avg_correlation = sum(correlations) / len(correlations)
        
        # Invert correlation (lower correlation = higher diversification benefit)
        score = Decimal('1') - avg_correlation
        return max(Decimal('0'), min(Decimal('1'), score))
    
    async def _calculate_regime_adaptability_score(self, strategy: TradingStrategy) -> Decimal:
        """Calculate how well strategy adapts to different market regimes."""
        
        if not hasattr(strategy.performance, 'regime_performance'):
            return Decimal('0.5')  # Neutral score if no regime data
        
        regime_performance = strategy.performance.regime_performance
        
        if not regime_performance:
            return Decimal('0.5')
        
        # Count regimes where strategy has positive performance
        positive_regimes = 0
        total_regimes = len(regime_performance)
        
        for regime_data in regime_performance.values():
            if regime_data.performance.expectancy > Decimal('0'):
                positive_regimes += 1
        
        # Score based on percentage of regimes with positive performance
        adaptability_score = Decimal(positive_regimes) / Decimal(total_regimes)
        return adaptability_score
    
    async def _calculate_consistency_score(self, strategy: TradingStrategy) -> Decimal:
        """Calculate consistency score based on performance stability."""
        
        performance = strategy.performance.overall
        
        # Use Sharpe ratio as proxy for consistency (risk-adjusted return)
        sharpe = performance.sharpe_ratio
        
        # Normalize Sharpe ratio to 0-1 scale
        normalized_sharpe = (sharpe + Decimal('1')) / Decimal('3')  # -1 to 2 range
        consistency_score = max(Decimal('0'), min(Decimal('1'), normalized_sharpe))
        
        return consistency_score
    
    def _get_strategy_trend(self, strategy: TradingStrategy) -> TrendDirection:
        """Get the performance trend for a strategy."""
        if hasattr(strategy.performance, 'trend'):
            return strategy.performance.trend.direction
        return TrendDirection.STABLE
    
    def _generate_ranking_comments(self, strategy: TradingStrategy, ranking_type: str,
                                 rank: int, total_strategies: int) -> str:
        """Generate comments for strategy ranking."""
        
        performance = strategy.performance.overall
        
        if rank == 1:
            comment_prefix = "Top performer"
        elif rank <= total_strategies * 0.25:
            comment_prefix = "Excellent performance"
        elif rank <= total_strategies * 0.5:
            comment_prefix = "Above average"
        elif rank <= total_strategies * 0.75:
            comment_prefix = "Below average"
        else:
            comment_prefix = "Underperforming"
        
        # Add specific insights based on ranking type
        if ranking_type == 'performance':
            detail = f"Expectancy: {performance.expectancy:.4f}, Win Rate: {performance.win_rate:.1%}"
        elif ranking_type == 'risk_adjusted':
            detail = f"Sharpe: {performance.sharpe_ratio:.2f}, Max DD: {performance.max_drawdown:.1%}"
        elif ranking_type == 'consistency':
            detail = f"Win Rate: {performance.win_rate:.1%}, Profit Factor: {performance.profit_factor:.2f}"
        else:
            detail = f"Total Trades: {performance.total_trades}"
        
        return f"{comment_prefix}. {detail}"
    
    def _generate_diversification_comments(self, strategy: TradingStrategy, score: Decimal) -> str:
        """Generate comments for diversification ranking."""
        
        if score >= Decimal('80'):
            return "Excellent diversification benefit, low correlation with other strategies"
        elif score >= Decimal('60'):
            return "Good diversification benefit, moderate correlation"
        elif score >= Decimal('40'):
            return "Average diversification benefit"
        elif score >= Decimal('20'):
            return "Limited diversification benefit, high correlation with existing strategies"
        else:
            return "Poor diversification benefit, highly correlated with other strategies"
    
    async def compare_strategies_pairwise(self, strategy1: TradingStrategy,
                                        strategy2: TradingStrategy) -> Dict:
        """Perform detailed pairwise comparison of two strategies."""
        
        perf1 = strategy1.performance.overall
        perf2 = strategy2.performance.overall
        
        # Get historical returns for statistical comparison
        returns1 = await self._get_strategy_returns(strategy1.strategy_id)
        returns2 = await self._get_strategy_returns(strategy2.strategy_id)
        
        # Perform statistical significance test
        significance_test = self.statistical_tester.test_strategy_comparison(
            returns1, returns2, Decimal('0.95')
        )
        
        # Compare key metrics
        comparison = {
            'strategy1_id': strategy1.strategy_id,
            'strategy2_id': strategy2.strategy_id,
            'performance_comparison': {
                'expectancy': {
                    'strategy1': perf1.expectancy,
                    'strategy2': perf2.expectancy,
                    'difference': perf1.expectancy - perf2.expectancy,
                    'better': strategy1.strategy_id if perf1.expectancy > perf2.expectancy else strategy2.strategy_id
                },
                'sharpe_ratio': {
                    'strategy1': perf1.sharpe_ratio,
                    'strategy2': perf2.sharpe_ratio,
                    'difference': perf1.sharpe_ratio - perf2.sharpe_ratio,
                    'better': strategy1.strategy_id if perf1.sharpe_ratio > perf2.sharpe_ratio else strategy2.strategy_id
                },
                'max_drawdown': {
                    'strategy1': perf1.max_drawdown,
                    'strategy2': perf2.max_drawdown,
                    'difference': perf1.max_drawdown - perf2.max_drawdown,
                    'better': strategy1.strategy_id if perf1.max_drawdown < perf2.max_drawdown else strategy2.strategy_id
                },
                'win_rate': {
                    'strategy1': perf1.win_rate,
                    'strategy2': perf2.win_rate,
                    'difference': perf1.win_rate - perf2.win_rate,
                    'better': strategy1.strategy_id if perf1.win_rate > perf2.win_rate else strategy2.strategy_id
                }
            },
            'statistical_significance': significance_test,
            'recommendation': self._generate_comparison_recommendation(
                strategy1, strategy2, significance_test
            )
        }
        
        return comparison
    
    async def _get_strategy_returns(self, strategy_id: str) -> List[float]:
        """Get historical returns for a strategy (mock implementation)."""
        # In production, this would query actual strategy returns
        return [0.001, -0.002, 0.003, 0.0, -0.001]  # Mock returns
    
    def _generate_comparison_recommendation(self, strategy1: TradingStrategy,
                                          strategy2: TradingStrategy,
                                          significance_test: Dict) -> str:
        """Generate recommendation based on strategy comparison."""
        
        if significance_test['significantly_different']:
            better_strategy_id = strategy1.strategy_id if significance_test.get('better_strategy') == 1 else strategy2.strategy_id
            better_strategy_name = strategy1.strategy_name if better_strategy_id == strategy1.strategy_id else strategy2.strategy_name
            
            return f"Statistical analysis shows {better_strategy_name} ({better_strategy_id}) performs significantly better. Consider increasing allocation to this strategy."
        else:
            return "No statistically significant difference between strategies. Both can be maintained in portfolio for diversification."