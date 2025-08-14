"""
Weekly strategy effectiveness report generator.
"""
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
import asyncio
from dataclasses import asdict

from .models import (
    StrategyEffectivenessReport, ExecutiveSummary, StrategyRankings,
    RegimeAnalysis, StrategyRecommendations, ActionItems, ActionItem,
    PortfolioOptimization, TradingStrategy, PerformanceMetrics
)
from .strategy_comparison import StrategyComparison
from .correlation_analyzer import CorrelationAnalyzer
from .regime_analyzer import MarketRegimeAnalyzer

logger = logging.getLogger(__name__)


class ReportGenerator:
    """
    Generates comprehensive weekly strategy effectiveness reports.
    """
    
    def __init__(self):
        self.strategy_comparison = StrategyComparison()
        self.correlation_analyzer = CorrelationAnalyzer()
        self.regime_analyzer = MarketRegimeAnalyzer()
        
        # Report configuration
        self.report_config = {
            'lookback_period_days': 90,  # 3 months for analysis
            'min_strategies_for_report': 2,
            'top_performers_count': 5,
            'underperformers_count': 3
        }
    
    async def generate_weekly_report(self, strategies: List[TradingStrategy],
                                   report_date: Optional[datetime] = None) -> StrategyEffectivenessReport:
        """
        Generate comprehensive weekly strategy effectiveness report.
        
        Args:
            strategies: List of strategies to analyze
            report_date: Date for the report (defaults to current date)
            
        Returns:
            Complete strategy effectiveness report
        """
        if report_date is None:
            report_date = datetime.utcnow()
        
        logger.info(f"Generating weekly strategy effectiveness report for {len(strategies)} strategies")
        
        # Define report period (last 7 days)
        report_period_end = report_date
        report_period_start = report_date - timedelta(days=7)
        
        # Generate executive summary
        executive_summary = await self._generate_executive_summary(strategies, report_period_start, report_period_end)
        
        # Generate strategy rankings
        rankings = await self._generate_strategy_rankings(strategies)
        
        # Generate regime analysis
        regime_analysis = await self._generate_regime_analysis(strategies)
        
        # Generate recommendations
        recommendations = await self._generate_recommendations(strategies, executive_summary, rankings)
        
        # Generate action items
        action_items = await self._generate_action_items(strategies, executive_summary, recommendations)
        
        report = StrategyEffectivenessReport(
            report_id=f"weekly_report_{report_date.strftime('%Y%m%d')}",
            report_date=report_date,
            report_period_start=report_period_start,
            report_period_end=report_period_end,
            executive_summary=executive_summary,
            rankings=rankings,
            regime_analysis=regime_analysis,
            recommendations=recommendations,
            action_items=action_items
        )
        
        logger.info(f"Weekly report generated successfully: {report.report_id}")
        return report
    
    async def _generate_executive_summary(self, strategies: List[TradingStrategy],
                                        period_start: datetime,
                                        period_end: datetime) -> ExecutiveSummary:
        """Generate executive summary of strategy performance."""
        
        total_strategies = len(strategies)
        active_strategies = len([s for s in strategies if s.lifecycle.status.value == 'active'])
        suspended_strategies = len([s for s in strategies if s.lifecycle.status.value == 'suspended'])
        
        # Calculate portfolio performance
        portfolio_performance = await self._calculate_portfolio_performance(strategies)
        
        # Identify top performers and underperformers
        strategy_scores = {}
        for strategy in strategies:
            score = await self._calculate_strategy_score(strategy)
            strategy_scores[strategy.strategy_id] = score
        
        # Sort by performance
        sorted_strategies = sorted(strategies, key=lambda s: strategy_scores[s.strategy_id], reverse=True)
        
        top_performers = [s.strategy_id for s in sorted_strategies[:self.report_config['top_performers_count']]]
        underperformers = [s.strategy_id for s in sorted_strategies[-self.report_config['underperformers_count']:]]
        
        # Calculate diversification score
        diversification_score = await self._calculate_portfolio_diversification_score(strategies)
        
        # Calculate overall health score
        overall_health_score = await self._calculate_overall_health_score(strategies, portfolio_performance)
        
        return ExecutiveSummary(
            total_strategies=total_strategies,
            active_strategies=active_strategies,
            suspended_strategies=suspended_strategies,
            top_performers=top_performers,
            underperformers=underperformers,
            portfolio_performance=portfolio_performance,
            diversification_score=diversification_score,
            overall_health_score=overall_health_score
        )
    
    async def _generate_strategy_rankings(self, strategies: List[TradingStrategy]) -> StrategyRankings:
        """Generate comprehensive strategy rankings."""
        
        # Generate different types of rankings
        by_performance = await self.strategy_comparison.rank_strategies_by_performance(strategies)
        by_risk_adjusted_return = await self.strategy_comparison.rank_strategies_by_risk_adjusted_return(strategies)
        by_consistency = await self.strategy_comparison.rank_strategies_by_consistency(strategies)
        
        # Get correlation analysis for diversification ranking
        correlation_analysis = await self.correlation_analyzer.analyze_strategy_correlations(
            strategies, timedelta(days=self.report_config['lookback_period_days'])
        )
        
        by_diversification_benefit = await self.strategy_comparison.rank_strategies_by_diversification_benefit(
            strategies, asdict(correlation_analysis)
        )
        
        return StrategyRankings(
            by_performance=by_performance,
            by_risk_adjusted_return=by_risk_adjusted_return,
            by_consistency=by_consistency,
            by_diversification_benefit=by_diversification_benefit
        )
    
    async def _generate_regime_analysis(self, strategies: List[TradingStrategy]) -> RegimeAnalysis:
        """Generate market regime analysis."""
        
        # Get current market regime (simplified)
        current_regime = await self._determine_current_regime()
        
        # Map strategies to preferred regimes
        regime_strategies = await self._map_strategies_to_regimes(strategies)
        
        # Get recent regime transitions (mock data)
        regime_transitions = await self._get_recent_regime_transitions()
        
        # Generate regime forecasts (mock data)
        upcoming_regime_changes = await self._forecast_regime_changes()
        
        return RegimeAnalysis(
            current_regime=current_regime,
            regime_strategies=regime_strategies,
            regime_transitions=regime_transitions,
            upcoming_regime_changes=upcoming_regime_changes
        )
    
    async def _generate_recommendations(self, strategies: List[TradingStrategy],
                                      executive_summary: ExecutiveSummary,
                                      rankings: StrategyRankings) -> StrategyRecommendations:
        """Generate strategy management recommendations."""
        
        # Strategies to activate (from testing status)
        strategies_to_activate = await self._identify_strategies_to_activate(strategies)
        
        # Strategies to suspend (poor performers)
        strategies_to_suspend = await self._identify_strategies_to_suspend(strategies, executive_summary)
        
        # Allocation changes
        allocation_changes = await self._recommend_allocation_changes(strategies, rankings)
        
        # New strategy needs
        new_strategy_needs = await self._identify_new_strategy_needs(strategies, executive_summary)
        
        # Portfolio optimization
        portfolio_optimization = await self._generate_portfolio_optimization(strategies, allocation_changes)
        
        return StrategyRecommendations(
            strategies_to_activate=strategies_to_activate,
            strategies_to_suspend=strategies_to_suspend,
            allocation_changes=allocation_changes,
            new_strategy_needs=new_strategy_needs,
            portfolio_optimization=portfolio_optimization
        )
    
    async def _generate_action_items(self, strategies: List[TradingStrategy],
                                   executive_summary: ExecutiveSummary,
                                   recommendations: StrategyRecommendations) -> ActionItems:
        """Generate action items categorized by timeline."""
        
        immediate_actions = []
        short_term_actions = []
        long_term_actions = []
        
        # Immediate actions (this week)
        if recommendations.strategies_to_suspend:
            for strategy_id in recommendations.strategies_to_suspend:
                action = ActionItem(
                    item_id=f"suspend_{strategy_id}",
                    category="strategy_management",
                    priority="high",
                    description=f"Suspend underperforming strategy {strategy_id}",
                    expected_impact="Reduce portfolio risk and prevent further losses",
                    estimated_effort="2 hours",
                    deadline=datetime.utcnow() + timedelta(days=2),
                    assigned_to="portfolio_manager",
                    dependencies=[],
                    success_criteria=["Strategy successfully suspended", "Allocation redistributed"],
                    risk_mitigation=["Gradual position closure", "Impact assessment"]
                )
                immediate_actions.append(action)
        
        # High-priority allocation changes
        high_priority_changes = {k: v for k, v in recommendations.allocation_changes.items() 
                               if abs(v) > Decimal('0.05')}  # Changes > 5%
        
        if high_priority_changes:
            action = ActionItem(
                item_id="allocation_rebalancing",
                category="allocation",
                priority="medium",
                description=f"Rebalance allocation for {len(high_priority_changes)} strategies",
                expected_impact="Improve portfolio performance and risk profile",
                estimated_effort="4 hours",
                deadline=datetime.utcnow() + timedelta(days=5),
                assigned_to="portfolio_manager",
                dependencies=["suspension_actions_completed"],
                success_criteria=["Allocations updated", "Risk metrics improved"],
                risk_mitigation=["Gradual implementation", "Performance monitoring"]
            )
            immediate_actions.append(action)
        
        # Short-term actions (next month)
        if recommendations.strategies_to_activate:
            for strategy_id in recommendations.strategies_to_activate:
                action = ActionItem(
                    item_id=f"activate_{strategy_id}",
                    category="strategy_management",
                    priority="medium",
                    description=f"Activate and deploy strategy {strategy_id}",
                    expected_impact="Increase portfolio diversification and performance",
                    estimated_effort="8 hours",
                    deadline=datetime.utcnow() + timedelta(days=14),
                    assigned_to="strategy_developer",
                    dependencies=["testing_completion", "risk_approval"],
                    success_criteria=["Strategy deployed", "Initial performance positive"],
                    risk_mitigation=["Limited initial allocation", "Monitoring plan"]
                )
                short_term_actions.append(action)
        
        # Portfolio optimization implementation
        action = ActionItem(
            item_id="portfolio_optimization_implementation",
            category="allocation",
            priority="medium",
            description="Implement portfolio optimization recommendations",
            expected_impact=f"Expected return: {recommendations.portfolio_optimization.expected_return:.2%}, Risk reduction: 5%",
            estimated_effort="16 hours",
            deadline=datetime.utcnow() + timedelta(days=21),
            assigned_to="portfolio_manager",
            dependencies=["strategy_suspensions", "allocation_changes"],
            success_criteria=["Optimization implemented", "Performance improved"],
            risk_mitigation=["Phased implementation", "Continuous monitoring"]
        )
        short_term_actions.append(action)
        
        # Long-term actions (next quarter)
        if recommendations.new_strategy_needs:
            action = ActionItem(
                item_id="new_strategy_development",
                category="development",
                priority="low",
                description=f"Develop new strategies: {', '.join(recommendations.new_strategy_needs)}",
                expected_impact="Fill strategy gaps and improve diversification",
                estimated_effort="200 hours",
                deadline=datetime.utcnow() + timedelta(days=60),
                assigned_to="strategy_development_team",
                dependencies=["requirements_analysis", "market_research"],
                success_criteria=["Strategies developed", "Backtesting completed"],
                risk_mitigation=["Thorough testing", "Gradual deployment"]
            )
            long_term_actions.append(action)
        
        # Strategic review
        action = ActionItem(
            item_id="quarterly_strategy_review",
            category="strategy_management",
            priority="low",
            description="Conduct comprehensive quarterly strategy portfolio review",
            expected_impact="Ensure portfolio alignment with market conditions",
            estimated_effort="40 hours",
            deadline=datetime.utcnow() + timedelta(days=90),
            assigned_to="strategy_committee",
            dependencies=["quarterly_data_collection"],
            success_criteria=["Review completed", "Strategic plan updated"],
            risk_mitigation=["Data validation", "Multi-stakeholder input"]
        )
        long_term_actions.append(action)
        
        return ActionItems(
            immediate=immediate_actions,
            short_term=short_term_actions,
            long_term=long_term_actions
        )
    
    async def _calculate_portfolio_performance(self, strategies: List[TradingStrategy]) -> PerformanceMetrics:
        """Calculate aggregated portfolio performance."""
        
        if not strategies:
            return self._empty_performance_metrics()
        
        # Aggregate performance across all strategies
        total_trades = sum(s.performance.overall.total_trades for s in strategies)
        total_wins = sum(s.performance.overall.win_count for s in strategies)
        total_losses = sum(s.performance.overall.loss_count for s in strategies)
        
        win_rate = Decimal(total_wins) / Decimal(total_trades) if total_trades > 0 else Decimal('0')
        
        # Weighted average of returns (simplified - equal weights)
        total_return = sum(s.performance.overall.total_return for s in strategies) / len(strategies)
        
        # Portfolio-level risk metrics (simplified)
        max_drawdown = max((s.performance.overall.max_drawdown for s in strategies), default=Decimal('0'))
        avg_sharpe = sum(s.performance.overall.sharpe_ratio for s in strategies) / len(strategies)
        
        # Other metrics (simplified calculations)
        expectancy = sum(s.performance.overall.expectancy for s in strategies) / len(strategies)
        profit_factor = sum(s.performance.overall.profit_factor for s in strategies) / len(strategies)
        
        return PerformanceMetrics(
            total_trades=total_trades,
            win_count=total_wins,
            loss_count=total_losses,
            win_rate=win_rate,
            profit_factor=profit_factor,
            expectancy=expectancy,
            sharpe_ratio=avg_sharpe,
            calmar_ratio=Decimal('0'),  # Would calculate properly
            max_drawdown=max_drawdown,
            average_win=Decimal('0'),  # Would calculate properly
            average_loss=Decimal('0'),  # Would calculate properly
            average_hold_time=timedelta(hours=24),  # Default
            total_return=total_return,
            annualized_return=total_return * Decimal('4')  # Simplified annualization
        )
    
    async def _calculate_strategy_score(self, strategy: TradingStrategy) -> Decimal:
        """Calculate overall score for strategy ranking."""
        return await self.strategy_comparison._calculate_composite_score(strategy, 'performance')
    
    async def _calculate_portfolio_diversification_score(self, strategies: List[TradingStrategy]) -> Decimal:
        """Calculate portfolio diversification score."""
        
        if len(strategies) < 2:
            return Decimal('0')
        
        # Get correlation analysis
        correlation_analysis = await self.correlation_analyzer.analyze_strategy_correlations(
            strategies, timedelta(days=90)
        )
        
        # Convert correlation to diversification score
        avg_correlation = correlation_analysis.portfolio_analysis.overall_correlation
        diversification_score = (Decimal('1') - avg_correlation) * Decimal('100')
        
        return max(Decimal('0'), min(Decimal('100'), diversification_score))
    
    async def _calculate_overall_health_score(self, strategies: List[TradingStrategy],
                                            portfolio_performance: PerformanceMetrics) -> Decimal:
        """Calculate overall portfolio health score."""
        
        health_components = []
        
        # Performance component (40%)
        if portfolio_performance.expectancy > Decimal('0'):
            performance_score = min(Decimal('40'), portfolio_performance.expectancy * Decimal('4000'))
        else:
            performance_score = Decimal('0')
        health_components.append(performance_score)
        
        # Risk component (30%)
        risk_score = max(Decimal('0'), Decimal('30') * (Decimal('1') - portfolio_performance.max_drawdown / Decimal('0.3')))
        health_components.append(risk_score)
        
        # Diversification component (20%)
        diversification_score = await self._calculate_portfolio_diversification_score(strategies)
        health_components.append(diversification_score * Decimal('0.2'))
        
        # Strategy health component (10%)
        active_strategies = len([s for s in strategies if s.lifecycle.status.value == 'active'])
        total_strategies = len(strategies)
        strategy_health = Decimal(active_strategies) / Decimal(total_strategies) * Decimal('10') if total_strategies > 0 else Decimal('0')
        health_components.append(strategy_health)
        
        return sum(health_components)
    
    # Helper methods for regime analysis (simplified implementations)
    
    async def _determine_current_regime(self):
        """Determine current market regime."""
        from .models import MarketRegime
        return MarketRegime.SIDEWAYS  # Simplified
    
    async def _map_strategies_to_regimes(self, strategies: List[TradingStrategy]):
        """Map strategies to their preferred regimes."""
        from .models import MarketRegime
        
        regime_mapping = {regime: [] for regime in MarketRegime}
        
        for strategy in strategies:
            # Simplified mapping based on strategy type
            if hasattr(strategy.performance, 'regime_performance'):
                best_regime = None
                best_performance = Decimal('-1')
                
                for regime, perf_data in strategy.performance.regime_performance.items():
                    if perf_data.performance.expectancy > best_performance:
                        best_performance = perf_data.performance.expectancy
                        best_regime = regime
                
                if best_regime:
                    regime_mapping[best_regime].append(strategy.strategy_id)
            else:
                # Default mapping
                regime_mapping[MarketRegime.SIDEWAYS].append(strategy.strategy_id)
        
        return regime_mapping
    
    async def _get_recent_regime_transitions(self):
        """Get recent regime transitions."""
        return []  # Simplified
    
    async def _forecast_regime_changes(self):
        """Forecast upcoming regime changes."""
        return []  # Simplified
    
    # Helper methods for recommendations
    
    async def _identify_strategies_to_activate(self, strategies: List[TradingStrategy]) -> List[str]:
        """Identify strategies ready for activation."""
        candidates = []
        
        for strategy in strategies:
            if (strategy.lifecycle.status.value == 'testing' and
                strategy.performance.overall.total_trades >= 50 and
                strategy.performance.overall.sharpe_ratio > Decimal('0.8')):
                candidates.append(strategy.strategy_id)
        
        return candidates
    
    async def _identify_strategies_to_suspend(self, strategies: List[TradingStrategy],
                                            executive_summary: ExecutiveSummary) -> List[str]:
        """Identify strategies that should be suspended."""
        return executive_summary.underperformers[:2]  # Suspend worst 2 performers
    
    async def _recommend_allocation_changes(self, strategies: List[TradingStrategy],
                                          rankings: StrategyRankings) -> Dict[str, Decimal]:
        """Recommend allocation changes based on performance."""
        
        changes = {}
        
        # Increase allocation for top performers
        for ranking in rankings.by_performance[:3]:  # Top 3
            if ranking.rank <= 3:
                changes[ranking.strategy_id] = Decimal('0.02')  # +2%
        
        # Decrease allocation for poor performers
        for ranking in rankings.by_performance[-2:]:  # Bottom 2
            changes[ranking.strategy_id] = Decimal('-0.03')  # -3%
        
        return changes
    
    async def _identify_new_strategy_needs(self, strategies: List[TradingStrategy],
                                         executive_summary: ExecutiveSummary) -> List[str]:
        """Identify types of new strategies needed."""
        
        needs = []
        
        # Check strategy type coverage
        existing_types = set(s.classification.type.value for s in strategies)
        
        all_types = {'trend_following', 'mean_reversion', 'breakout', 'pattern_recognition', 'arbitrage'}
        missing_types = all_types - existing_types
        
        if missing_types:
            needs.extend(list(missing_types))
        
        # Check if diversification is low
        if executive_summary.diversification_score < Decimal('40'):
            needs.append('low_correlation_strategy')
        
        return needs
    
    async def _generate_portfolio_optimization(self, strategies: List[TradingStrategy],
                                             allocation_changes: Dict[str, Decimal]) -> PortfolioOptimization:
        """Generate portfolio optimization recommendations."""
        
        # Calculate target allocations
        target_allocation = {}
        total_weight = Decimal('0')
        
        for strategy in strategies:
            current_weight = strategy.configuration.weight
            change = allocation_changes.get(strategy.strategy_id, Decimal('0'))
            new_weight = max(Decimal('0'), current_weight + change)
            target_allocation[strategy.strategy_id] = new_weight
            total_weight += new_weight
        
        # Normalize to 100%
        if total_weight > 0:
            for strategy_id in target_allocation:
                target_allocation[strategy_id] = target_allocation[strategy_id] / total_weight
        
        # Estimate expected return and risk
        expected_return = Decimal('0.08')  # 8% - simplified
        expected_risk = Decimal('0.12')    # 12% - simplified
        diversification_score = await self._calculate_portfolio_diversification_score(strategies)
        
        return PortfolioOptimization(
            target_allocation=target_allocation,
            expected_return=expected_return,
            expected_risk=expected_risk,
            diversification_score=diversification_score,
            implementation_timeline=["Week 1: Suspend underperformers", "Week 2: Rebalance allocations", "Week 3: Monitor performance"]
        )
    
    def _empty_performance_metrics(self) -> PerformanceMetrics:
        """Create empty performance metrics."""
        return PerformanceMetrics(
            total_trades=0,
            win_count=0,
            loss_count=0,
            win_rate=Decimal('0'),
            profit_factor=Decimal('0'),
            expectancy=Decimal('0'),
            sharpe_ratio=Decimal('0'),
            calmar_ratio=Decimal('0'),
            max_drawdown=Decimal('0'),
            average_win=Decimal('0'),
            average_loss=Decimal('0'),
            average_hold_time=timedelta(0),
            total_return=Decimal('0'),
            annualized_return=Decimal('0')
        )