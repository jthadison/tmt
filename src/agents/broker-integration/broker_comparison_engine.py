"""
Broker Comparison Engine & Routing Optimizer - Story 8.14 Task 3

This module provides intelligent broker comparison, ranking, and routing optimization
capabilities for maximizing trading profitability and execution quality.

Features:
- Cost comparison algorithms with multi-factor analysis
- Dynamic broker ranking based on performance metrics
- Intelligent routing recommendations
- A/B testing framework for broker evaluation
- Optimal allocation suggestions
- Decision support system with confidence scoring
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Union
from decimal import Decimal
from datetime import datetime, timedelta, date
from enum import Enum
import asyncio
import logging
import statistics
import random
from collections import defaultdict, namedtuple

import structlog

logger = structlog.get_logger(__name__)


class RoutingStrategy(str, Enum):
    """Routing strategy types"""
    COST_OPTIMIZED = "cost_optimized"
    QUALITY_OPTIMIZED = "quality_optimized"
    BALANCED = "balanced"
    SPEED_OPTIMIZED = "speed_optimized"
    RELIABILITY_OPTIMIZED = "reliability_optimized"


class AllocationStrategy(str, Enum):
    """Portfolio allocation strategies"""
    EQUAL_WEIGHT = "equal_weight"
    PERFORMANCE_WEIGHT = "performance_weight"
    INVERSE_COST_WEIGHT = "inverse_cost_weight"
    KELLY_CRITERION = "kelly_criterion"
    SHARPE_OPTIMIZED = "sharpe_optimized"


@dataclass
class BrokerPerformance:
    """Comprehensive broker performance metrics"""
    broker: str
    period_start: datetime
    period_end: datetime
    total_trades: int
    total_volume: Decimal
    total_cost: Decimal
    avg_cost_per_trade: Decimal
    avg_cost_bps: Decimal
    cost_variance: Decimal
    quality_score: float
    execution_score: float
    reliability_score: float
    composite_score: float
    cost_breakdown: Dict[str, Decimal]
    quality_metrics: Dict[str, float]
    trend_direction: str  # 'improving', 'declining', 'stable'
    confidence_score: float
    last_updated: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ComparisonResult:
    """Broker comparison result"""
    instrument: str
    trade_size: Decimal
    comparison_timestamp: datetime
    brokers_analyzed: List[str]
    cost_rankings: List[Tuple[str, Decimal]]  # (broker, estimated_cost)
    quality_rankings: List[Tuple[str, float]]  # (broker, quality_score)
    composite_rankings: List[Tuple[str, float]]  # (broker, composite_score)
    recommended_broker: str
    cost_savings: Decimal
    confidence: float
    reasoning: str
    market_conditions: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ABTestResult:
    """A/B testing result for broker evaluation"""
    test_id: str
    broker_a: str
    broker_b: str
    start_time: datetime
    end_time: datetime
    trades_a: int
    trades_b: int
    avg_cost_a: Decimal
    avg_cost_b: Decimal
    quality_score_a: float
    quality_score_b: float
    statistical_significance: float
    winner: Optional[str]
    cost_difference: Decimal
    quality_difference: float
    confidence_interval: Tuple[float, float]
    recommendation: str


@dataclass
class OptimalAllocation:
    """Optimal broker allocation recommendation"""
    strategy: AllocationStrategy
    allocations: Dict[str, float]  # broker -> allocation percentage
    expected_cost_savings: Decimal
    expected_quality_improvement: float
    risk_metrics: Dict[str, float]
    rebalance_frequency: str
    confidence: float
    effective_date: datetime
    next_review_date: datetime


class CostComparisonAlgorithm:
    """Advanced cost comparison and analysis"""
    
    def __init__(self):
        self.cost_factors = {
            'spread_cost': 0.30,
            'commission': 0.25,
            'slippage_cost': 0.20,
            'swap_cost': 0.15,
            'financing_cost': 0.10
        }
        self.historical_costs: Dict[str, List[Tuple[datetime, Decimal]]] = defaultdict(list)
        
    async def compare_brokers(self, brokers: List[str], instrument: str, 
                            trade_size: Decimal, trade_type: str,
                            cost_analyzer, quality_analyzer) -> ComparisonResult:
        """Comprehensive broker comparison"""
        comparison_timestamp = datetime.utcnow()
        
        # Get cost and quality data for each broker
        broker_analysis = {}
        
        for broker in brokers:
            # Get recent cost data
            cost_comparison = await cost_analyzer.generate_broker_cost_comparison(7)
            broker_costs = cost_comparison.get(broker, {})
            
            # Get quality metrics
            quality_report = await quality_analyzer.generate_quality_report(broker, instrument, 7)
            
            # Estimate trade cost
            estimated_cost = await self._estimate_trade_cost(
                broker, instrument, trade_size, trade_type, cost_analyzer
            )
            
            broker_analysis[broker] = {
                'estimated_cost': estimated_cost,
                'quality_score': quality_report.quality_score,
                'avg_cost_bps': broker_costs.get('avg_cost_bps', Decimal('10')),
                'reliability': quality_report.fill_rate,
                'speed': 100 - quality_report.avg_latency_ms / 10  # Convert to score
            }
        
        # Calculate rankings
        cost_rankings = sorted(
            [(broker, data['estimated_cost']) for broker, data in broker_analysis.items()],
            key=lambda x: x[1]
        )
        
        quality_rankings = sorted(
            [(broker, data['quality_score']) for broker, data in broker_analysis.items()],
            key=lambda x: x[1], reverse=True
        )
        
        # Calculate composite scores with weightings
        composite_scores = []
        for broker, data in broker_analysis.items():
            # Normalize scores (0-100)
            cost_score = self._normalize_cost_score(data['estimated_cost'], [d['estimated_cost'] for d in broker_analysis.values()])
            quality_score = data['quality_score']
            
            # Weighted composite based on trade type
            if trade_type == 'scalping':
                composite = (cost_score * 0.4) + (quality_score * 0.6)
            elif trade_type == 'swing':
                composite = (cost_score * 0.6) + (quality_score * 0.4)
            else:  # default balanced
                composite = (cost_score * 0.5) + (quality_score * 0.5)
            
            composite_scores.append((broker, composite))
        
        composite_rankings = sorted(composite_scores, key=lambda x: x[1], reverse=True)
        
        # Determine recommendation
        recommended_broker = composite_rankings[0][0]
        
        # Calculate cost savings vs worst broker
        best_cost = cost_rankings[0][1]
        worst_cost = cost_rankings[-1][1]
        cost_savings = worst_cost - best_cost
        
        # Calculate confidence based on margin between top brokers
        confidence = self._calculate_confidence(composite_rankings)
        
        # Generate reasoning
        reasoning = self._generate_reasoning(
            recommended_broker, broker_analysis[recommended_broker], cost_rankings, quality_rankings
        )
        
        return ComparisonResult(
            instrument=instrument,
            trade_size=trade_size,
            comparison_timestamp=comparison_timestamp,
            brokers_analyzed=brokers,
            cost_rankings=cost_rankings,
            quality_rankings=quality_rankings,
            composite_rankings=composite_rankings,
            recommended_broker=recommended_broker,
            cost_savings=cost_savings,
            confidence=confidence,
            reasoning=reasoning,
            market_conditions=await self._get_market_conditions()
        )
    
    async def _estimate_trade_cost(self, broker: str, instrument: str, 
                                 trade_size: Decimal, trade_type: str,
                                 cost_analyzer) -> Decimal:
        """Estimate total cost for a hypothetical trade"""
        # Get recent average costs by category
        recent_costs = await cost_analyzer.generate_broker_cost_comparison(7)
        broker_data = recent_costs.get(broker, {})
        
        # Estimate each cost component
        avg_spread_cost = broker_data.get('cost_by_category', {}).get('spread', Decimal('0'))
        avg_commission = broker_data.get('cost_by_category', {}).get('commission', Decimal('0'))
        avg_slippage = broker_data.get('cost_by_category', {}).get('slippage', Decimal('0'))
        
        # Scale by trade size ratio
        avg_volume = broker_data.get('total_volume', Decimal('100000'))
        size_ratio = trade_size / avg_volume if avg_volume > 0 else Decimal('1')
        
        estimated_cost = (avg_spread_cost + avg_commission + avg_slippage) * size_ratio
        
        # Adjust for trade type
        if trade_type == 'market':
            estimated_cost *= Decimal('1.1')  # Market orders typically cost more
        elif trade_type == 'limit':
            estimated_cost *= Decimal('0.9')   # Limit orders typically cost less
        
        return estimated_cost
    
    def _normalize_cost_score(self, cost: Decimal, all_costs: List[Decimal]) -> float:
        """Normalize cost to 0-100 score (lower cost = higher score)"""
        if not all_costs:
            return 50.0
            
        min_cost = min(all_costs)
        max_cost = max(all_costs)
        
        if max_cost == min_cost:
            return 100.0
        
        # Invert so lower cost = higher score
        normalized = 100 - ((float(cost - min_cost) / float(max_cost - min_cost)) * 100)
        return max(0, min(100, normalized))
    
    def _calculate_confidence(self, rankings: List[Tuple[str, float]]) -> float:
        """Calculate confidence in recommendation based on score margins"""
        if len(rankings) < 2:
            return 1.0
        
        top_score = rankings[0][1]
        second_score = rankings[1][1]
        
        # Confidence based on margin (0-100 scale)
        margin = top_score - second_score
        confidence = min(1.0, margin / 20)  # 20 point margin = 100% confidence
        
        return max(0.1, confidence)
    
    def _generate_reasoning(self, broker: str, broker_data: Dict[str, Any],
                          cost_rankings: List[Tuple[str, Decimal]],
                          quality_rankings: List[Tuple[str, float]]) -> str:
        """Generate human-readable reasoning for recommendation"""
        cost_rank = next(i for i, (b, _) in enumerate(cost_rankings, 1) if b == broker)
        quality_rank = next(i for i, (b, _) in enumerate(quality_rankings, 1) if b == broker)
        
        reasoning_parts = [f"{broker} recommended"]
        
        if cost_rank == 1:
            reasoning_parts.append("lowest cost")
        elif cost_rank <= 3:
            reasoning_parts.append("competitive cost")
        
        if quality_rank == 1:
            reasoning_parts.append("highest quality")
        elif quality_rank <= 3:
            reasoning_parts.append("good execution quality")
        
        quality_score = broker_data['quality_score']
        if quality_score >= 80:
            reasoning_parts.append("excellent reliability")
        elif quality_score >= 60:
            reasoning_parts.append("good reliability")
        
        return ", ".join(reasoning_parts)
    
    async def _get_market_conditions(self) -> Dict[str, Any]:
        """Get current market conditions for context"""
        # In production, this would connect to market data sources
        return {
            'market_session': self._get_current_session(),
            'volatility_level': 'normal',  # Would be calculated from real data
            'liquidity_level': 'normal',
            'timestamp': datetime.utcnow()
        }
    
    def _get_current_session(self) -> str:
        """Determine current market session"""
        utc_hour = datetime.utcnow().hour
        if 22 <= utc_hour or utc_hour < 8:
            return "asian"
        elif 8 <= utc_hour < 13:
            return "london"
        elif 13 <= utc_hour < 22:
            return "ny"
        else:
            return "overlap"


class BrokerRankingSystem:
    """Dynamic broker ranking based on performance"""
    
    def __init__(self):
        self.ranking_criteria = {
            'cost_efficiency': 0.30,
            'execution_quality': 0.25,
            'reliability': 0.20,
            'speed': 0.15,
            'innovation': 0.10
        }
        self.broker_scores: Dict[str, BrokerPerformance] = {}
        self.ranking_history: List[Tuple[datetime, Dict[str, int]]] = []
        
    async def calculate_broker_rankings(self, brokers: List[str],
                                      cost_analyzer, quality_analyzer,
                                      period_days: int = 30) -> Dict[str, BrokerPerformance]:
        """Calculate comprehensive broker rankings"""
        broker_performances = {}
        
        for broker in brokers:
            performance = await self._calculate_broker_performance(
                broker, cost_analyzer, quality_analyzer, period_days
            )
            broker_performances[broker] = performance
        
        # Store in history
        current_rankings = {
            broker: rank for rank, (broker, _) in enumerate(
                sorted(broker_performances.items(), 
                      key=lambda x: x[1].composite_score, reverse=True), 1
            )
        }
        
        self.ranking_history.append((datetime.utcnow(), current_rankings))
        self.broker_scores.update(broker_performances)
        
        return broker_performances
    
    async def _calculate_broker_performance(self, broker: str, cost_analyzer, 
                                          quality_analyzer, period_days: int) -> BrokerPerformance:
        """Calculate comprehensive performance metrics for a broker"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=period_days)
        
        # Get cost data
        cost_data = await cost_analyzer.generate_broker_cost_comparison(period_days)
        broker_costs = cost_data.get(broker, {})
        
        # Get quality data
        quality_report = await quality_analyzer.generate_quality_report(broker, None, period_days)
        
        # Calculate cost efficiency score
        cost_efficiency = self._calculate_cost_efficiency(broker_costs)
        
        # Calculate reliability score
        reliability_score = self._calculate_reliability_score(quality_report)
        
        # Calculate execution score
        execution_score = quality_report.execution_efficiency
        
        # Calculate composite score
        composite_score = (
            cost_efficiency * self.ranking_criteria['cost_efficiency'] +
            quality_report.quality_score * self.ranking_criteria['execution_quality'] +
            reliability_score * self.ranking_criteria['reliability'] +
            execution_score * self.ranking_criteria['speed']
        )
        
        # Determine trend
        trend_direction = await self._calculate_trend(broker, composite_score)
        
        # Calculate confidence
        confidence_score = self._calculate_confidence_score(
            broker_costs.get('trade_count', 0), period_days
        )
        
        return BrokerPerformance(
            broker=broker,
            period_start=start_date,
            period_end=end_date,
            total_trades=broker_costs.get('trade_count', 0),
            total_volume=broker_costs.get('total_volume', Decimal('0')),
            total_cost=broker_costs.get('total_cost', Decimal('0')),
            avg_cost_per_trade=broker_costs.get('avg_cost_per_trade', Decimal('0')),
            avg_cost_bps=broker_costs.get('avg_cost_bps', Decimal('0')),
            cost_variance=Decimal('0'),  # Would calculate from historical data
            quality_score=quality_report.quality_score,
            execution_score=execution_score,
            reliability_score=reliability_score,
            composite_score=composite_score,
            cost_breakdown=broker_costs.get('cost_by_category', {}),
            quality_metrics={
                'fill_rate': quality_report.fill_rate,
                'avg_latency_ms': quality_report.avg_latency_ms,
                'rejection_rate': quality_report.rejection_rate
            },
            trend_direction=trend_direction,
            confidence_score=confidence_score
        )
    
    def _calculate_cost_efficiency(self, cost_data: Dict[str, Any]) -> float:
        """Calculate cost efficiency score (0-100)"""
        avg_cost_bps = float(cost_data.get('avg_cost_bps', 10))
        
        # Assume 5 bps is reasonable, 10 bps is poor
        if avg_cost_bps <= 3:
            return 100.0
        elif avg_cost_bps <= 5:
            return 80.0
        elif avg_cost_bps <= 7:
            return 60.0
        elif avg_cost_bps <= 10:
            return 40.0
        else:
            return max(0, 40 - (avg_cost_bps - 10) * 5)
    
    def _calculate_reliability_score(self, quality_report) -> float:
        """Calculate reliability score based on consistency metrics"""
        fill_rate = quality_report.fill_rate
        rejection_rate = quality_report.rejection_rate
        
        # Weight fill rate heavily, penalize rejections
        reliability = (fill_rate * 100) - (rejection_rate * 200)
        return max(0, min(100, reliability))
    
    async def _calculate_trend(self, broker: str, current_score: float) -> str:
        """Calculate performance trend direction"""
        # Look at historical scores
        if len(self.ranking_history) < 2:
            return "stable"
        
        # Get scores from last few periods
        recent_scores = []
        for timestamp, rankings in self.ranking_history[-5:]:
            if broker in rankings:
                # Convert ranking to score (lower rank = higher score)
                rank_score = 100 - (rankings[broker] - 1) * 10
                recent_scores.append(rank_score)
        
        if len(recent_scores) < 2:
            return "stable"
        
        # Calculate trend
        trend = recent_scores[-1] - recent_scores[0]
        if trend > 5:
            return "improving"
        elif trend < -5:
            return "declining"
        else:
            return "stable"
    
    def _calculate_confidence_score(self, trade_count: int, period_days: int) -> float:
        """Calculate confidence in metrics based on sample size"""
        min_trades_per_day = 1
        expected_trades = period_days * min_trades_per_day
        
        if trade_count >= expected_trades * 2:
            return 1.0
        elif trade_count >= expected_trades:
            return 0.8
        elif trade_count >= expected_trades * 0.5:
            return 0.6
        else:
            return 0.3


class RoutingRecommendationEngine:
    """Intelligent broker routing recommendations"""
    
    def __init__(self):
        self.routing_rules: Dict[str, Dict[str, Any]] = {}
        self.routing_history: List[Tuple[datetime, str, str, str]] = []  # timestamp, instrument, broker, reason
        
    async def recommend_broker(self, instrument: str, trade_size: Decimal,
                             trade_type: str, strategy: RoutingStrategy,
                             comparison_result: ComparisonResult) -> str:
        """Recommend optimal broker based on strategy"""
        brokers_data = {
            broker: score for broker, score in comparison_result.composite_rankings
        }
        
        if strategy == RoutingStrategy.COST_OPTIMIZED:
            recommended = comparison_result.cost_rankings[0][0]
            reason = "lowest cost"
            
        elif strategy == RoutingStrategy.QUALITY_OPTIMIZED:
            recommended = comparison_result.quality_rankings[0][0]
            reason = "highest quality"
            
        elif strategy == RoutingStrategy.SPEED_OPTIMIZED:
            # Choose based on latency (would need additional data)
            recommended = comparison_result.quality_rankings[0][0]
            reason = "fastest execution"
            
        elif strategy == RoutingStrategy.RELIABILITY_OPTIMIZED:
            # Choose most reliable broker
            recommended = comparison_result.quality_rankings[0][0]
            reason = "highest reliability"
            
        else:  # BALANCED
            recommended = comparison_result.recommended_broker
            reason = comparison_result.reasoning
        
        # Apply routing rules if any
        final_recommendation = await self._apply_routing_rules(
            instrument, trade_size, trade_type, recommended
        )
        
        # Record decision
        self.routing_history.append((
            datetime.utcnow(), instrument, final_recommendation, reason
        ))
        
        logger.info("Broker routing recommendation",
                   instrument=instrument,
                   trade_size=float(trade_size),
                   strategy=strategy.value,
                   recommended_broker=final_recommendation,
                   reason=reason)
        
        return final_recommendation
    
    async def _apply_routing_rules(self, instrument: str, trade_size: Decimal,
                                 trade_type: str, default_broker: str) -> str:
        """Apply custom routing rules"""
        # Example rules (would be configurable)
        
        # Large size rule
        if trade_size > Decimal('100000'):
            return self.routing_rules.get('large_size_broker', default_broker)
        
        # Instrument-specific rules
        instrument_rules = self.routing_rules.get(f'instrument_{instrument}', {})
        if instrument_rules and trade_type in instrument_rules:
            return instrument_rules[trade_type]
        
        # Time-based rules
        current_hour = datetime.utcnow().hour
        if 22 <= current_hour or current_hour < 8:  # Asian session
            return self.routing_rules.get('asian_session_broker', default_broker)
        
        return default_broker
    
    async def add_routing_rule(self, rule_name: str, conditions: Dict[str, Any],
                             target_broker: str) -> None:
        """Add custom routing rule"""
        self.routing_rules[rule_name] = {
            'conditions': conditions,
            'target_broker': target_broker,
            'created': datetime.utcnow()
        }
        
        logger.info("Routing rule added",
                   rule_name=rule_name,
                   target_broker=target_broker)


class ABTestingFramework:
    """A/B testing framework for broker evaluation"""
    
    def __init__(self):
        self.active_tests: Dict[str, Dict[str, Any]] = {}
        self.completed_tests: List[ABTestResult] = []
        
    async def create_ab_test(self, test_id: str, broker_a: str, broker_b: str,
                           allocation_ratio: float = 0.5, duration_days: int = 7,
                           instruments: List[str] = None) -> None:
        """Create new A/B test"""
        test_config = {
            'test_id': test_id,
            'broker_a': broker_a,
            'broker_b': broker_b,
            'allocation_ratio': allocation_ratio,  # % of trades to broker_a
            'start_time': datetime.utcnow(),
            'end_time': datetime.utcnow() + timedelta(days=duration_days),
            'instruments': instruments or [],
            'trades_a': [],
            'trades_b': [],
            'status': 'active'
        }
        
        self.active_tests[test_id] = test_config
        
        logger.info("A/B test created",
                   test_id=test_id,
                   broker_a=broker_a,
                   broker_b=broker_b,
                   duration_days=duration_days)
    
    async def route_trade_for_test(self, test_id: str, trade_data: Dict[str, Any]) -> str:
        """Route trade according to A/B test configuration"""
        if test_id not in self.active_tests:
            raise ValueError(f"Test {test_id} not found")
        
        test_config = self.active_tests[test_id]
        
        # Check if test is still active
        if datetime.utcnow() > test_config['end_time']:
            await self._complete_test(test_id)
            return None
        
        # Check instrument filter
        if test_config['instruments'] and trade_data['instrument'] not in test_config['instruments']:
            return None
        
        # Route based on allocation ratio
        if random.random() < test_config['allocation_ratio']:
            selected_broker = test_config['broker_a']
            test_config['trades_a'].append(trade_data)
        else:
            selected_broker = test_config['broker_b']
            test_config['trades_b'].append(trade_data)
        
        return selected_broker
    
    async def _complete_test(self, test_id: str) -> ABTestResult:
        """Complete A/B test and calculate results"""
        test_config = self.active_tests[test_id]
        test_config['status'] = 'completed'
        
        trades_a = test_config['trades_a']
        trades_b = test_config['trades_b']
        
        # Calculate statistics
        if trades_a and trades_b:
            avg_cost_a = sum(Decimal(str(t.get('cost', 0))) for t in trades_a) / len(trades_a)
            avg_cost_b = sum(Decimal(str(t.get('cost', 0))) for t in trades_b) / len(trades_b)
            
            quality_a = sum(t.get('quality_score', 50) for t in trades_a) / len(trades_a)
            quality_b = sum(t.get('quality_score', 50) for t in trades_b) / len(trades_b)
            
            # Simple statistical significance test
            cost_difference = avg_cost_a - avg_cost_b
            quality_difference = quality_a - quality_b
            
            # Determine winner (simplified)
            if abs(float(cost_difference)) > 0.5:  # 0.5 bps threshold
                winner = test_config['broker_a'] if cost_difference < 0 else test_config['broker_b']
            else:
                winner = None
            
            statistical_significance = 0.8 if len(trades_a) > 20 and len(trades_b) > 20 else 0.5
        else:
            avg_cost_a = avg_cost_b = Decimal('0')
            quality_a = quality_b = 0
            cost_difference = Decimal('0')
            quality_difference = 0
            winner = None
            statistical_significance = 0
        
        result = ABTestResult(
            test_id=test_id,
            broker_a=test_config['broker_a'],
            broker_b=test_config['broker_b'],
            start_time=test_config['start_time'],
            end_time=test_config['end_time'],
            trades_a=len(trades_a),
            trades_b=len(trades_b),
            avg_cost_a=avg_cost_a,
            avg_cost_b=avg_cost_b,
            quality_score_a=quality_a,
            quality_score_b=quality_b,
            statistical_significance=statistical_significance,
            winner=winner,
            cost_difference=cost_difference,
            quality_difference=quality_difference,
            confidence_interval=(0.95, 1.05),  # Simplified
            recommendation=f"Winner: {winner}" if winner else "No significant difference"
        )
        
        self.completed_tests.append(result)
        del self.active_tests[test_id]
        
        logger.info("A/B test completed",
                   test_id=test_id,
                   winner=winner,
                   cost_difference=float(cost_difference),
                   significance=statistical_significance)
        
        return result


class OptimalAllocationEngine:
    """Optimal broker allocation suggestions"""
    
    def __init__(self):
        self.allocation_models: Dict[AllocationStrategy, callable] = {
            AllocationStrategy.EQUAL_WEIGHT: self._equal_weight_allocation,
            AllocationStrategy.PERFORMANCE_WEIGHT: self._performance_weight_allocation,
            AllocationStrategy.INVERSE_COST_WEIGHT: self._inverse_cost_weight_allocation,
            AllocationStrategy.KELLY_CRITERION: self._kelly_criterion_allocation,
            AllocationStrategy.SHARPE_OPTIMIZED: self._sharpe_optimized_allocation
        }
    
    async def calculate_optimal_allocation(self, brokers: List[str],
                                         strategy: AllocationStrategy,
                                         broker_performances: Dict[str, BrokerPerformance],
                                         target_volume: Decimal) -> OptimalAllocation:
        """Calculate optimal allocation across brokers"""
        
        # Calculate allocations based on strategy
        allocation_func = self.allocation_models[strategy]
        allocations = await allocation_func(brokers, broker_performances)
        
        # Normalize allocations to sum to 1.0
        total_allocation = sum(allocations.values())
        if total_allocation > 0:
            allocations = {broker: allocation / total_allocation 
                         for broker, allocation in allocations.items()}
        
        # Calculate expected benefits
        expected_cost_savings = await self._calculate_expected_savings(
            allocations, broker_performances, target_volume
        )
        
        expected_quality_improvement = await self._calculate_expected_quality_improvement(
            allocations, broker_performances
        )
        
        # Calculate risk metrics
        risk_metrics = await self._calculate_risk_metrics(allocations, broker_performances)
        
        # Determine rebalance frequency
        rebalance_frequency = self._determine_rebalance_frequency(strategy, risk_metrics)
        
        # Calculate confidence
        confidence = self._calculate_allocation_confidence(broker_performances, allocations)
        
        return OptimalAllocation(
            strategy=strategy,
            allocations=allocations,
            expected_cost_savings=expected_cost_savings,
            expected_quality_improvement=expected_quality_improvement,
            risk_metrics=risk_metrics,
            rebalance_frequency=rebalance_frequency,
            confidence=confidence,
            effective_date=datetime.utcnow(),
            next_review_date=datetime.utcnow() + timedelta(days=30)
        )
    
    async def _equal_weight_allocation(self, brokers: List[str], 
                                     performances: Dict[str, BrokerPerformance]) -> Dict[str, float]:
        """Equal weight allocation"""
        weight = 1.0 / len(brokers)
        return {broker: weight for broker in brokers}
    
    async def _performance_weight_allocation(self, brokers: List[str],
                                           performances: Dict[str, BrokerPerformance]) -> Dict[str, float]:
        """Allocation based on composite performance scores"""
        total_score = sum(perf.composite_score for perf in performances.values())
        
        if total_score == 0:
            return await self._equal_weight_allocation(brokers, performances)
        
        return {
            broker: perf.composite_score / total_score
            for broker, perf in performances.items()
            if broker in brokers
        }
    
    async def _inverse_cost_weight_allocation(self, brokers: List[str],
                                            performances: Dict[str, BrokerPerformance]) -> Dict[str, float]:
        """Allocation inversely proportional to costs"""
        # Use inverse of cost (higher cost = lower allocation)
        inverse_costs = {}
        for broker in brokers:
            if broker in performances:
                cost_bps = float(performances[broker].avg_cost_bps)
                # Add small epsilon to avoid division by zero
                inverse_costs[broker] = 1.0 / (cost_bps + 0.1)
            else:
                inverse_costs[broker] = 1.0
        
        total_inverse = sum(inverse_costs.values())
        return {broker: weight / total_inverse for broker, weight in inverse_costs.items()}
    
    async def _kelly_criterion_allocation(self, brokers: List[str],
                                        performances: Dict[str, BrokerPerformance]) -> Dict[str, float]:
        """Kelly criterion based allocation (simplified)"""
        # Simplified Kelly criterion based on cost savings probability
        allocations = {}
        
        for broker in brokers:
            if broker in performances:
                perf = performances[broker]
                # Estimate win rate and average win/loss
                win_rate = perf.quality_score / 100  # Proxy for success rate
                avg_cost_bps = float(perf.avg_cost_bps)
                
                # Kelly fraction: (bp - q) / b where b is odds, p is win prob, q is loss prob
                if avg_cost_bps < 5:  # Assume 5 bps is break-even
                    kelly_fraction = max(0, win_rate - (1 - win_rate) / 2)
                else:
                    kelly_fraction = 0.1  # Conservative allocation for high cost brokers
                
                allocations[broker] = kelly_fraction
            else:
                allocations[broker] = 0.1
        
        return allocations
    
    async def _sharpe_optimized_allocation(self, brokers: List[str],
                                         performances: Dict[str, BrokerPerformance]) -> Dict[str, float]:
        """Sharpe ratio optimized allocation (simplified)"""
        # Simplified Sharpe optimization based on return/risk ratio
        allocations = {}
        
        for broker in brokers:
            if broker in performances:
                perf = performances[broker]
                # Use composite score as return and cost variance as risk
                return_proxy = perf.composite_score
                risk_proxy = max(0.1, float(perf.cost_variance))  # Avoid division by zero
                
                sharpe_proxy = return_proxy / risk_proxy
                allocations[broker] = sharpe_proxy
            else:
                allocations[broker] = 1.0
        
        return allocations
    
    async def _calculate_expected_savings(self, allocations: Dict[str, float],
                                        performances: Dict[str, BrokerPerformance],
                                        target_volume: Decimal) -> Decimal:
        """Calculate expected cost savings from allocation"""
        # Compare weighted average cost vs equal allocation
        weighted_cost = sum(
            allocations[broker] * float(performances[broker].avg_cost_bps)
            for broker in allocations
            if broker in performances
        )
        
        equal_weight_cost = sum(
            float(performances[broker].avg_cost_bps)
            for broker in allocations
            if broker in performances
        ) / len(allocations)
        
        cost_savings_bps = equal_weight_cost - weighted_cost
        cost_savings = Decimal(str(cost_savings_bps)) * target_volume / 10000
        
        return max(Decimal('0'), cost_savings)
    
    async def _calculate_expected_quality_improvement(self, allocations: Dict[str, float],
                                                    performances: Dict[str, BrokerPerformance]) -> float:
        """Calculate expected quality improvement"""
        weighted_quality = sum(
            allocations[broker] * performances[broker].quality_score
            for broker in allocations
            if broker in performances
        )
        
        equal_weight_quality = sum(
            performances[broker].quality_score
            for broker in allocations
            if broker in performances
        ) / len(allocations)
        
        return max(0, weighted_quality - equal_weight_quality)
    
    async def _calculate_risk_metrics(self, allocations: Dict[str, float],
                                    performances: Dict[str, BrokerPerformance]) -> Dict[str, float]:
        """Calculate risk metrics for allocation"""
        # Concentration risk
        concentration_risk = max(allocations.values()) if allocations else 0
        
        # Diversification ratio
        diversification = 1 - sum(w**2 for w in allocations.values())
        
        # Performance variance
        performance_variance = statistics.variance([
            performances[broker].composite_score
            for broker in allocations
            if broker in performances
        ]) if len(allocations) > 1 else 0
        
        return {
            'concentration_risk': concentration_risk,
            'diversification_ratio': diversification,
            'performance_variance': performance_variance,
            'max_allocation': max(allocations.values()) if allocations else 0
        }
    
    def _determine_rebalance_frequency(self, strategy: AllocationStrategy,
                                     risk_metrics: Dict[str, float]) -> str:
        """Determine optimal rebalancing frequency"""
        if strategy == AllocationStrategy.EQUAL_WEIGHT:
            return "quarterly"
        elif risk_metrics['performance_variance'] > 100:
            return "weekly"
        elif risk_metrics['concentration_risk'] > 0.5:
            return "bi-weekly"
        else:
            return "monthly"
    
    def _calculate_allocation_confidence(self, performances: Dict[str, BrokerPerformance],
                                       allocations: Dict[str, float]) -> float:
        """Calculate confidence in allocation recommendation"""
        # Base confidence on data quality and performance stability
        avg_confidence = sum(
            perf.confidence_score for perf in performances.values()
        ) / len(performances) if performances else 0.5
        
        # Adjust for concentration
        concentration_penalty = max(allocations.values()) if allocations else 0
        
        confidence = avg_confidence * (1 - concentration_penalty * 0.2)
        return max(0.1, min(1.0, confidence))


class BrokerComparisonEngine:
    """Main broker comparison and optimization engine"""
    
    def __init__(self):
        self.cost_comparison = CostComparisonAlgorithm()
        self.ranking_system = BrokerRankingSystem()
        self.routing_engine = RoutingRecommendationEngine()
        self.ab_testing = ABTestingFramework()
        self.allocation_engine = OptimalAllocationEngine()
        
    async def initialize(self, brokers: List[str]) -> None:
        """Initialize comparison engine with available brokers"""
        logger.info("Broker comparison engine initialized", brokers=brokers)
    
    async def get_broker_recommendation(self, instrument: str, trade_size: Decimal,
                                      trade_type: str, strategy: RoutingStrategy,
                                      cost_analyzer, quality_analyzer) -> Dict[str, Any]:
        """Get comprehensive broker recommendation"""
        # Get available brokers (would be from configuration)
        available_brokers = ['broker1', 'broker2', 'broker3']  # Example
        
        # Perform comparison
        comparison = await self.cost_comparison.compare_brokers(
            available_brokers, instrument, trade_size, trade_type,
            cost_analyzer, quality_analyzer
        )
        
        # Get routing recommendation
        recommended_broker = await self.routing_engine.recommend_broker(
            instrument, trade_size, trade_type, strategy, comparison
        )
        
        return {
            'recommended_broker': recommended_broker,
            'comparison_result': comparison,
            'confidence': comparison.confidence,
            'reasoning': comparison.reasoning,
            'cost_savings': float(comparison.cost_savings),
            'alternative_options': [
                {'broker': broker, 'score': score}
                for broker, score in comparison.composite_rankings[1:3]
            ]
        }
    
    async def get_portfolio_allocation_recommendation(self, brokers: List[str],
                                                    strategy: AllocationStrategy,
                                                    target_volume: Decimal,
                                                    cost_analyzer, quality_analyzer) -> OptimalAllocation:
        """Get optimal portfolio allocation across brokers"""
        # Calculate broker rankings
        broker_performances = await self.ranking_system.calculate_broker_rankings(
            brokers, cost_analyzer, quality_analyzer
        )
        
        # Calculate optimal allocation
        optimal_allocation = await self.allocation_engine.calculate_optimal_allocation(
            brokers, strategy, broker_performances, target_volume
        )
        
        return optimal_allocation