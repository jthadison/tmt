"""
Strategy correlation analyzer for portfolio diversification analysis.
"""
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Set
import asyncio
import numpy as np
from scipy.stats import pearsonr
from sklearn.cluster import AgglomerativeClustering
import pandas as pd

from .models import (
    StrategyCorrelationAnalysis, PortfolioAnalysis, DiversificationAnalysis,
    RiskConcentration, CorrelationCluster, TradingStrategy
)

logger = logging.getLogger(__name__)


class CorrelationAnalyzer:
    """
    Analyzes correlations between trading strategies for portfolio optimization
    and diversification assessment.
    """
    
    def __init__(self):
        self.correlation_threshold_high = Decimal('0.7')   # High correlation threshold
        self.correlation_threshold_medium = Decimal('0.3')  # Medium correlation threshold
        self.min_overlap_period = 30  # Minimum days of overlap for correlation calculation
        
    async def analyze_strategy_correlations(self, strategies: List[TradingStrategy],
                                          analysis_period: timedelta) -> StrategyCorrelationAnalysis:
        """
        Perform comprehensive correlation analysis of strategies.
        
        Args:
            strategies: List of trading strategies to analyze
            analysis_period: Time period for correlation analysis
            
        Returns:
            Complete correlation analysis results
        """
        logger.info(f"Analyzing correlations for {len(strategies)} strategies")
        
        if len(strategies) < 2:
            logger.warning("Need at least 2 strategies for correlation analysis")
            return self._create_empty_analysis()
        
        # Build correlation matrix
        correlation_matrix = await self._build_correlation_matrix(strategies, analysis_period)
        
        # Perform portfolio analysis
        portfolio_analysis = await self._analyze_portfolio(strategies, correlation_matrix)
        
        # Analyze diversification benefits
        diversification_analysis = await self._analyze_diversification(
            strategies, correlation_matrix, portfolio_analysis
        )
        
        # Assess risk concentration
        risk_concentration = await self._assess_risk_concentration(
            strategies, correlation_matrix, portfolio_analysis
        )
        
        return StrategyCorrelationAnalysis(
            analysis_id=f"corr_analysis_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            timestamp=datetime.utcnow(),
            correlation_matrix=correlation_matrix,
            portfolio_analysis=portfolio_analysis,
            diversification_analysis=diversification_analysis,
            risk_concentration=risk_concentration
        )
    
    async def _build_correlation_matrix(self, strategies: List[TradingStrategy],
                                      analysis_period: timedelta) -> Dict[str, Dict[str, Decimal]]:
        """Build correlation matrix between all strategy pairs."""
        
        correlation_matrix = {}
        
        # Get aligned returns for all strategies
        strategy_returns = await self._get_aligned_strategy_returns(strategies, analysis_period)
        
        for i, strategy1 in enumerate(strategies):
            strategy1_id = strategy1.strategy_id
            correlation_matrix[strategy1_id] = {}
            
            for j, strategy2 in enumerate(strategies):
                strategy2_id = strategy2.strategy_id
                
                if strategy1_id == strategy2_id:
                    # Perfect correlation with self
                    correlation_matrix[strategy1_id][strategy2_id] = Decimal('1.0')
                elif strategy2_id in correlation_matrix:
                    # Use already calculated correlation (symmetric)
                    correlation_matrix[strategy1_id][strategy2_id] = \
                        correlation_matrix[strategy2_id][strategy1_id]
                else:
                    # Calculate new correlation
                    correlation = await self._calculate_correlation(
                        strategy_returns.get(strategy1_id, []),
                        strategy_returns.get(strategy2_id, [])
                    )
                    correlation_matrix[strategy1_id][strategy2_id] = correlation
        
        return correlation_matrix
    
    async def _get_aligned_strategy_returns(self, strategies: List[TradingStrategy],
                                          analysis_period: timedelta) -> Dict[str, List[Decimal]]:
        """Get time-aligned returns for all strategies."""
        
        strategy_returns = {}
        end_date = datetime.utcnow()
        start_date = end_date - analysis_period
        
        for strategy in strategies:
            returns = await self._get_strategy_daily_returns(
                strategy.strategy_id, start_date, end_date
            )
            strategy_returns[strategy.strategy_id] = returns
        
        # Align returns to same dates (fill missing days with 0)
        aligned_returns = self._align_return_series(strategy_returns, start_date, end_date)
        
        return aligned_returns
    
    async def _get_strategy_daily_returns(self, strategy_id: str,
                                        start_date: datetime,
                                        end_date: datetime) -> List[Decimal]:
        """
        Get daily returns for a strategy over specified period.
        In production, this would query the actual trade database.
        """
        # Mock implementation - would query actual trade data
        logger.debug(f"Getting daily returns for strategy {strategy_id}")
        
        # Generate mock daily returns for demonstration
        num_days = (end_date - start_date).days
        returns = []
        
        for day in range(num_days):
            # Mock return (in production, would aggregate actual trade PnL by day)
            mock_return = Decimal('0.001') * (day % 10 - 5)  # Simple pattern
            returns.append(mock_return)
        
        return returns
    
    def _align_return_series(self, strategy_returns: Dict[str, List[Decimal]],
                           start_date: datetime, end_date: datetime) -> Dict[str, List[Decimal]]:
        """Align return series to same date range, filling missing values."""
        
        num_days = (end_date - start_date).days
        aligned_returns = {}
        
        for strategy_id, returns in strategy_returns.items():
            # Ensure all series have same length
            if len(returns) < num_days:
                # Pad with zeros for missing days
                padded_returns = returns + [Decimal('0')] * (num_days - len(returns))
            elif len(returns) > num_days:
                # Truncate if too long
                padded_returns = returns[:num_days]
            else:
                padded_returns = returns
            
            aligned_returns[strategy_id] = padded_returns
        
        return aligned_returns
    
    async def _calculate_correlation(self, returns1: List[Decimal],
                                   returns2: List[Decimal]) -> Decimal:
        """Calculate Pearson correlation between two return series."""
        
        if len(returns1) != len(returns2) or len(returns1) < self.min_overlap_period:
            return Decimal('0')  # Insufficient data
        
        try:
            # Convert to float for scipy
            series1 = [float(r) for r in returns1]
            series2 = [float(r) for r in returns2]
            
            # Remove any NaN or infinite values
            clean_pairs = [(r1, r2) for r1, r2 in zip(series1, series2) 
                          if not (np.isnan(r1) or np.isnan(r2) or 
                                np.isinf(r1) or np.isinf(r2))]
            
            if len(clean_pairs) < self.min_overlap_period:
                return Decimal('0')
            
            clean_series1, clean_series2 = zip(*clean_pairs)
            
            # Calculate Pearson correlation
            correlation, p_value = pearsonr(clean_series1, clean_series2)
            
            # Handle NaN result
            if np.isnan(correlation):
                return Decimal('0')
            
            return Decimal(str(round(correlation, 4)))
        
        except Exception as e:
            logger.warning(f"Error calculating correlation: {e}")
            return Decimal('0')
    
    async def _analyze_portfolio(self, strategies: List[TradingStrategy],
                               correlation_matrix: Dict[str, Dict[str, Decimal]]) -> PortfolioAnalysis:
        """Analyze portfolio-level correlation metrics."""
        
        if len(strategies) < 2:
            return self._create_empty_portfolio_analysis()
        
        # Calculate overall portfolio correlation
        overall_correlation = self._calculate_overall_correlation(correlation_matrix)
        
        # Calculate diversification ratio
        diversification_ratio = self._calculate_diversification_ratio(strategies, correlation_matrix)
        
        # Calculate portfolio volatility
        portfolio_volatility = await self._calculate_portfolio_volatility(strategies, correlation_matrix)
        
        # Calculate individual volatilities
        individual_volatilities = await self._calculate_individual_volatilities(strategies)
        
        # Identify correlation clusters
        correlation_clusters = await self._identify_correlation_clusters(strategies, correlation_matrix)
        
        return PortfolioAnalysis(
            overall_correlation=overall_correlation,
            diversification_ratio=diversification_ratio,
            portfolio_volatility=portfolio_volatility,
            individual_volatilities=individual_volatilities,
            correlation_clusters=correlation_clusters
        )
    
    def _calculate_overall_correlation(self, correlation_matrix: Dict[str, Dict[str, Decimal]]) -> Decimal:
        """Calculate average correlation across all strategy pairs."""
        
        correlations = []
        strategies = list(correlation_matrix.keys())
        
        for i, strategy1 in enumerate(strategies):
            for j, strategy2 in enumerate(strategies):
                if i < j:  # Avoid double counting and self-correlation
                    correlation = correlation_matrix[strategy1][strategy2]
                    correlations.append(correlation)
        
        if not correlations:
            return Decimal('0')
        
        return sum(correlations) / len(correlations)
    
    def _calculate_diversification_ratio(self, strategies: List[TradingStrategy],
                                       correlation_matrix: Dict[str, Dict[str, Decimal]]) -> Decimal:
        """
        Calculate diversification ratio: 
        (Weighted avg of individual volatilities) / (Portfolio volatility)
        """
        # Simplified calculation - in production would use actual volatilities and weights
        num_strategies = len(strategies)
        
        if num_strategies <= 1:
            return Decimal('1')
        
        # Approximate diversification benefit based on average correlation
        avg_correlation = self._calculate_overall_correlation(correlation_matrix)
        
        # Simplified diversification ratio calculation
        perfect_diversification = Decimal('1') / Decimal(str(num_strategies))
        actual_diversification_factor = Decimal('1') - avg_correlation
        
        diversification_ratio = perfect_diversification / actual_diversification_factor
        
        return min(diversification_ratio, Decimal('10'))  # Cap at 10x
    
    async def _calculate_portfolio_volatility(self, strategies: List[TradingStrategy],
                                            correlation_matrix: Dict[str, Dict[str, Decimal]]) -> Decimal:
        """Calculate portfolio volatility considering correlations."""
        
        # Simplified calculation - in production would use actual weights and volatilities
        individual_vols = await self._calculate_individual_volatilities(strategies)
        
        if len(strategies) <= 1:
            return list(individual_vols.values())[0] if individual_vols else Decimal('0')
        
        # Simplified portfolio volatility (equal weights assumed)
        weight = Decimal('1') / Decimal(len(strategies))
        
        variance = Decimal('0')
        for i, strategy1 in enumerate(strategies):
            for j, strategy2 in enumerate(strategies):
                vol1 = individual_vols.get(strategy1.strategy_id, Decimal('0'))
                vol2 = individual_vols.get(strategy2.strategy_id, Decimal('0'))
                correlation = correlation_matrix[strategy1.strategy_id][strategy2.strategy_id]
                
                variance += weight * weight * vol1 * vol2 * correlation
        
        portfolio_volatility = variance ** Decimal('0.5')
        return portfolio_volatility
    
    async def _calculate_individual_volatilities(self, strategies: List[TradingStrategy]) -> Dict[str, Decimal]:
        """Calculate volatility for each individual strategy."""
        
        volatilities = {}
        
        for strategy in strategies:
            # Get strategy performance metrics
            performance = strategy.performance
            
            # Use max drawdown as proxy for volatility if available
            if performance and hasattr(performance, 'overall'):
                volatility = performance.overall.max_drawdown
            else:
                # Fallback calculation or default
                volatility = Decimal('0.02')  # 2% default volatility
            
            volatilities[strategy.strategy_id] = volatility
        
        return volatilities
    
    async def _identify_correlation_clusters(self, strategies: List[TradingStrategy],
                                           correlation_matrix: Dict[str, Dict[str, Decimal]]) -> List[CorrelationCluster]:
        """Identify clusters of highly correlated strategies."""
        
        if len(strategies) < 3:
            return []  # Need at least 3 strategies for meaningful clustering
        
        try:
            # Convert correlation matrix to distance matrix for clustering
            strategy_ids = [s.strategy_id for s in strategies]
            n = len(strategy_ids)
            
            # Build distance matrix (1 - correlation)
            distance_matrix = np.zeros((n, n))
            for i, id1 in enumerate(strategy_ids):
                for j, id2 in enumerate(strategy_ids):
                    correlation = correlation_matrix[id1][id2]
                    distance = 1 - float(correlation)
                    distance_matrix[i][j] = distance
            
            # Perform hierarchical clustering
            clustering = AgglomerativeClustering(
                n_clusters=min(3, n//2),  # Adaptive number of clusters
                metric='precomputed',
                linkage='average'
            )
            
            cluster_labels = clustering.fit_predict(distance_matrix)
            
            # Build correlation clusters
            clusters = {}
            for i, strategy_id in enumerate(strategy_ids):
                cluster_id = cluster_labels[i]
                if cluster_id not in clusters:
                    clusters[cluster_id] = []
                clusters[cluster_id].append(strategy_id)
            
            # Convert to CorrelationCluster objects
            correlation_clusters = []
            for cluster_id, cluster_strategies in clusters.items():
                if len(cluster_strategies) >= 2:  # Only include clusters with 2+ strategies
                    cluster = await self._create_correlation_cluster(
                        cluster_id, cluster_strategies, strategies, correlation_matrix
                    )
                    correlation_clusters.append(cluster)
            
            return correlation_clusters
        
        except Exception as e:
            logger.warning(f"Error in correlation clustering: {e}")
            return []
    
    async def _create_correlation_cluster(self, cluster_id: int, cluster_strategy_ids: List[str],
                                        all_strategies: List[TradingStrategy],
                                        correlation_matrix: Dict[str, Dict[str, Decimal]]) -> CorrelationCluster:
        """Create a correlation cluster object."""
        
        # Calculate average correlation within cluster
        correlations = []
        for i, id1 in enumerate(cluster_strategy_ids):
            for j, id2 in enumerate(cluster_strategy_ids):
                if i < j:
                    correlation = correlation_matrix[id1][id2]
                    correlations.append(correlation)
        
        avg_correlation = sum(correlations) / len(correlations) if correlations else Decimal('0')
        
        # Calculate cluster weight (assuming equal weights)
        cluster_weight = Decimal(len(cluster_strategy_ids)) / Decimal(len(all_strategies))
        
        # Find dominant strategy (best performing in cluster)
        dominant_strategy = cluster_strategy_ids[0]  # Simplified - would use actual performance ranking
        
        # Identify redundant strategies (highly correlated with dominant)
        redundant_strategies = []
        for strategy_id in cluster_strategy_ids:
            if strategy_id != dominant_strategy:
                correlation_with_dominant = correlation_matrix[strategy_id][dominant_strategy]
                if correlation_with_dominant > self.correlation_threshold_high:
                    redundant_strategies.append(strategy_id)
        
        return CorrelationCluster(
            cluster_id=f"cluster_{cluster_id}",
            strategies=cluster_strategy_ids,
            average_correlation=avg_correlation,
            cluster_weight=cluster_weight,
            dominant_strategy=dominant_strategy,
            redundant_strategies=redundant_strategies
        )
    
    async def _analyze_diversification(self, strategies: List[TradingStrategy],
                                     correlation_matrix: Dict[str, Dict[str, Decimal]],
                                     portfolio_analysis: PortfolioAnalysis) -> DiversificationAnalysis:
        """Analyze current diversification and potential improvements."""
        
        # Calculate current diversification benefit
        current_benefit = self._calculate_current_diversification_benefit(portfolio_analysis)
        
        # Calculate potential improvement
        potential_improvement = await self._calculate_potential_improvement(
            strategies, correlation_matrix
        )
        
        # Recommend weight changes
        weight_changes = await self._recommend_weight_changes(strategies, correlation_matrix)
        
        # Calculate risk reduction potential
        risk_reduction = self._calculate_risk_reduction_potential(portfolio_analysis)
        
        # Estimate return impact
        return_impact = self._estimate_return_impact(weight_changes)
        
        return DiversificationAnalysis(
            current_diversification_benefit=current_benefit,
            potential_improvement=potential_improvement,
            recommended_weight_changes=weight_changes,
            risk_reduction=risk_reduction,
            return_impact=return_impact
        )
    
    def _calculate_current_diversification_benefit(self, portfolio_analysis: PortfolioAnalysis) -> Decimal:
        """Calculate current diversification benefit."""
        # Simplified calculation based on diversification ratio
        benefit = max(Decimal('0'), portfolio_analysis.diversification_ratio - Decimal('1'))
        return min(benefit, Decimal('1'))  # Cap at 100%
    
    async def _calculate_potential_improvement(self, strategies: List[TradingStrategy],
                                             correlation_matrix: Dict[str, Dict[str, Decimal]]) -> Decimal:
        """Calculate potential diversification improvement."""
        current_correlation = self._calculate_overall_correlation(correlation_matrix)
        
        # Estimate potential improvement by reducing high correlations
        high_correlations = []
        strategy_ids = [s.strategy_id for s in strategies]
        
        for i, id1 in enumerate(strategy_ids):
            for j, id2 in enumerate(strategy_ids):
                if i < j:
                    correlation = correlation_matrix[id1][id2]
                    if correlation > self.correlation_threshold_high:
                        high_correlations.append(correlation)
        
        if not high_correlations:
            return Decimal('0')
        
        # Potential improvement if high correlations were reduced
        avg_high_correlation = sum(high_correlations) / len(high_correlations)
        potential_improvement = avg_high_correlation - self.correlation_threshold_medium
        
        return max(Decimal('0'), potential_improvement)
    
    async def _recommend_weight_changes(self, strategies: List[TradingStrategy],
                                      correlation_matrix: Dict[str, Dict[str, Decimal]]) -> Dict[str, Decimal]:
        """Recommend weight changes to improve diversification."""
        
        weight_changes = {}
        
        # Simple heuristic: reduce weight of highly correlated strategies
        strategy_ids = [s.strategy_id for s in strategies]
        
        for strategy_id in strategy_ids:
            avg_correlation = Decimal('0')
            count = 0
            
            for other_id in strategy_ids:
                if other_id != strategy_id:
                    correlation = correlation_matrix[strategy_id][other_id]
                    avg_correlation += correlation
                    count += 1
            
            if count > 0:
                avg_correlation = avg_correlation / count
                
                # Recommend weight reduction for highly correlated strategies
                if avg_correlation > self.correlation_threshold_high:
                    weight_changes[strategy_id] = Decimal('-0.1')  # Reduce by 10%
                elif avg_correlation < self.correlation_threshold_medium:
                    weight_changes[strategy_id] = Decimal('0.05')   # Increase by 5%
                else:
                    weight_changes[strategy_id] = Decimal('0')      # No change
        
        return weight_changes
    
    def _calculate_risk_reduction_potential(self, portfolio_analysis: PortfolioAnalysis) -> Decimal:
        """Calculate potential risk reduction from diversification improvements."""
        # Simplified calculation based on current correlation level
        current_correlation = portfolio_analysis.overall_correlation
        
        if current_correlation > self.correlation_threshold_high:
            # High correlation - significant risk reduction potential
            return Decimal('0.3')  # 30% risk reduction potential
        elif current_correlation > self.correlation_threshold_medium:
            # Medium correlation - moderate risk reduction potential  
            return Decimal('0.15')  # 15% risk reduction potential
        else:
            # Low correlation - limited risk reduction potential
            return Decimal('0.05')  # 5% risk reduction potential
    
    def _estimate_return_impact(self, weight_changes: Dict[str, Decimal]) -> Decimal:
        """Estimate impact on returns from weight changes."""
        # Simplified estimation - assume minimal return impact from diversification
        total_weight_change = sum(abs(change) for change in weight_changes.values())
        
        # Estimate small negative impact on returns (diversification vs performance trade-off)
        return -total_weight_change * Decimal('0.1')
    
    async def _assess_risk_concentration(self, strategies: List[TradingStrategy],
                                       correlation_matrix: Dict[str, Dict[str, Decimal]],
                                       portfolio_analysis: PortfolioAnalysis) -> RiskConcentration:
        """Assess risk concentration in the strategy portfolio."""
        
        # Calculate concentration risk
        concentration_risk = self._calculate_concentration_risk(portfolio_analysis)
        
        # Find largest cluster weight
        largest_cluster_weight = Decimal('0')
        if portfolio_analysis.correlation_clusters:
            largest_cluster_weight = max(
                cluster.cluster_weight for cluster in portfolio_analysis.correlation_clusters
            )
        
        # Count independent strategies
        independent_strategies = self._count_independent_strategies(strategies, correlation_matrix)
        
        # Identify redundant strategies
        redundant_strategies = self._identify_redundant_strategies(
            strategies, correlation_matrix, portfolio_analysis
        )
        
        return RiskConcentration(
            concentration_risk=concentration_risk,
            largest_cluster_weight=largest_cluster_weight,
            independent_strategies=independent_strategies,
            redundant_strategies=redundant_strategies
        )
    
    def _calculate_concentration_risk(self, portfolio_analysis: PortfolioAnalysis) -> Decimal:
        """Calculate overall concentration risk (0-1, higher = more concentrated)."""
        overall_correlation = portfolio_analysis.overall_correlation
        
        # Convert correlation to concentration risk
        # High correlation = high concentration risk
        concentration_risk = max(Decimal('0'), overall_correlation)
        
        return min(concentration_risk, Decimal('1'))
    
    def _count_independent_strategies(self, strategies: List[TradingStrategy],
                                    correlation_matrix: Dict[str, Dict[str, Decimal]]) -> int:
        """Count strategies that are relatively independent (low correlation with others)."""
        
        independent_count = 0
        strategy_ids = [s.strategy_id for s in strategies]
        
        for strategy_id in strategy_ids:
            max_correlation = Decimal('0')
            
            for other_id in strategy_ids:
                if other_id != strategy_id:
                    correlation = abs(correlation_matrix[strategy_id][other_id])
                    max_correlation = max(max_correlation, correlation)
            
            # Consider independent if max correlation below threshold
            if max_correlation < self.correlation_threshold_medium:
                independent_count += 1
        
        return independent_count
    
    def _identify_redundant_strategies(self, strategies: List[TradingStrategy],
                                     correlation_matrix: Dict[str, Dict[str, Decimal]],
                                     portfolio_analysis: PortfolioAnalysis) -> List[str]:
        """Identify strategies that are highly correlated and potentially redundant."""
        
        redundant_strategies = set()
        
        # Add redundant strategies from correlation clusters
        for cluster in portfolio_analysis.correlation_clusters:
            redundant_strategies.update(cluster.redundant_strategies)
        
        # Additional check for pairwise high correlations
        strategy_ids = [s.strategy_id for s in strategies]
        for i, id1 in enumerate(strategy_ids):
            for j, id2 in enumerate(strategy_ids):
                if i < j:
                    correlation = correlation_matrix[id1][id2]
                    if correlation > self.correlation_threshold_high:
                        # Mark the second strategy as potentially redundant
                        redundant_strategies.add(id2)
        
        return list(redundant_strategies)
    
    def _create_empty_analysis(self) -> StrategyCorrelationAnalysis:
        """Create empty correlation analysis for insufficient data."""
        return StrategyCorrelationAnalysis(
            analysis_id="empty_analysis",
            timestamp=datetime.utcnow(),
            correlation_matrix={},
            portfolio_analysis=self._create_empty_portfolio_analysis(),
            diversification_analysis=DiversificationAnalysis(
                current_diversification_benefit=Decimal('0'),
                potential_improvement=Decimal('0'),
                recommended_weight_changes={},
                risk_reduction=Decimal('0'),
                return_impact=Decimal('0')
            ),
            risk_concentration=RiskConcentration(
                concentration_risk=Decimal('0'),
                largest_cluster_weight=Decimal('0'),
                independent_strategies=0,
                redundant_strategies=[]
            )
        )
    
    def _create_empty_portfolio_analysis(self) -> PortfolioAnalysis:
        """Create empty portfolio analysis."""
        return PortfolioAnalysis(
            overall_correlation=Decimal('0'),
            diversification_ratio=Decimal('1'),
            portfolio_volatility=Decimal('0'),
            individual_volatilities={},
            correlation_clusters=[]
        )