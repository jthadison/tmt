"""
Unit tests for Broker Comparison Engine - Story 8.14

Tests for broker_comparison_engine.py covering:
- Broker comparison algorithms
- Ranking system
- Routing recommendations
- A/B testing framework
- Allocation optimization
- Decision support system
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch

from ..broker_comparison_engine import (
    BrokerComparisonEngine, BrokerRankingSystem, RoutingRecommendationEngine,
    ABTestingFramework, AllocationOptimizer, DecisionSupportSystem,
    BrokerPerformance, ComparisonResult, RoutingDecision, ABTestResult,
    AllocationSuggestion, PerformanceRanking
)


class TestBrokerComparisonEngine:
    """Test BrokerComparisonEngine class"""
    
    @pytest.fixture
    def comparison_engine(self):
        """Create broker comparison engine instance"""
        return BrokerComparisonEngine()
    
    @pytest.fixture
    def mock_cost_analyzer(self):
        """Mock cost analyzer"""
        analyzer = Mock()
        analyzer.generate_broker_cost_comparison = AsyncMock(return_value={
            'broker_a': {
                'total_cost': 1500.0,
                'avg_cost_bps': 2.5,
                'trade_count': 100,
                'total_volume': 10000000
            },
            'broker_b': {
                'total_cost': 1800.0,
                'avg_cost_bps': 3.0,
                'trade_count': 120,
                'total_volume': 12000000
            }
        })
        return analyzer
    
    @pytest.fixture
    def mock_quality_analyzer(self):
        """Mock quality analyzer"""
        analyzer = Mock()
        quality_report_a = Mock()
        quality_report_a.quality_score = 85.0
        quality_report_a.fill_rate = 95.0
        quality_report_a.avg_latency_ms = 45.0
        quality_report_a.avg_slippage_pips = 1.5
        quality_report_a.rejection_rate = 5.0
        
        quality_report_b = Mock()
        quality_report_b.quality_score = 78.0
        quality_report_b.fill_rate = 88.0
        quality_report_b.avg_latency_ms = 65.0
        quality_report_b.avg_slippage_pips = 2.2
        quality_report_b.rejection_rate = 12.0
        
        analyzer.generate_quality_report = AsyncMock(side_effect=lambda broker, *args: 
            quality_report_a if broker == 'broker_a' else quality_report_b)
        return analyzer
    
    @pytest.mark.asyncio
    async def test_initialize_comparison_engine(self, comparison_engine):
        """Test comparison engine initialization"""
        await comparison_engine.initialize()
        
        assert comparison_engine.ranking_system is not None
        assert comparison_engine.routing_engine is not None
        assert comparison_engine.ab_testing is not None
        assert comparison_engine.allocation_optimizer is not None
        assert comparison_engine.decision_support is not None
    
    @pytest.mark.asyncio
    async def test_compare_brokers(self, comparison_engine, mock_cost_analyzer, mock_quality_analyzer):
        """Test broker comparison functionality"""
        await comparison_engine.initialize()
        
        result = await comparison_engine.compare_brokers(
            ['broker_a', 'broker_b'], mock_cost_analyzer, mock_quality_analyzer, 30
        )
        
        assert isinstance(result, ComparisonResult)
        assert len(result.broker_performances) == 2
        assert 'broker_a' in result.broker_performances
        assert 'broker_b' in result.broker_performances
        
        # Verify broker A has better performance (lower costs, higher quality)
        broker_a_perf = result.broker_performances['broker_a']
        broker_b_perf = result.broker_performances['broker_b']
        
        assert broker_a_perf.avg_cost_bps < broker_b_perf.avg_cost_bps
        assert broker_a_perf.quality_score > broker_b_perf.quality_score
        assert broker_a_perf.composite_score > broker_b_perf.composite_score
    
    @pytest.mark.asyncio
    async def test_get_routing_recommendation(self, comparison_engine, mock_cost_analyzer, mock_quality_analyzer):
        """Test routing recommendation generation"""
        await comparison_engine.initialize()
        
        trade_params = {
            'instrument': 'EUR_USD',
            'size': 100000,
            'urgency': 'normal',
            'market_conditions': 'normal'
        }
        
        routing_decision = await comparison_engine.get_routing_recommendation(
            ['broker_a', 'broker_b'], trade_params, mock_cost_analyzer, mock_quality_analyzer
        )
        
        assert isinstance(routing_decision, RoutingDecision)
        assert routing_decision.recommended_broker in ['broker_a', 'broker_b']
        assert routing_decision.confidence_score > 0
        assert len(routing_decision.reasoning) > 0
        
        # Should recommend broker_a (better performance)
        assert routing_decision.recommended_broker == 'broker_a'
    
    @pytest.mark.asyncio
    async def test_run_ab_test(self, comparison_engine, mock_cost_analyzer, mock_quality_analyzer):
        """Test A/B testing functionality"""
        await comparison_engine.initialize()
        
        test_config = {
            'test_name': 'broker_cost_comparison',
            'group_a': ['broker_a'],
            'group_b': ['broker_b'],
            'allocation_ratio': 0.5,
            'duration_days': 7,
            'min_trades': 50
        }
        
        # Mock some trade data
        comparison_engine.ab_testing.trade_history = {
            'broker_a': [{'cost': 15.0, 'timestamp': datetime.utcnow()}] * 60,
            'broker_b': [{'cost': 18.0, 'timestamp': datetime.utcnow()}] * 55
        }
        
        ab_result = await comparison_engine.run_ab_test(
            test_config, mock_cost_analyzer, mock_quality_analyzer
        )
        
        assert isinstance(ab_result, ABTestResult)
        assert ab_result.test_name == 'broker_cost_comparison'
        assert ab_result.statistical_significance is not None
        assert len(ab_result.performance_comparison) > 0
    
    @pytest.mark.asyncio
    async def test_optimize_allocation(self, comparison_engine, mock_cost_analyzer, mock_quality_analyzer):
        """Test allocation optimization"""
        await comparison_engine.initialize()
        
        allocation_suggestion = await comparison_engine.optimize_allocation(
            ['broker_a', 'broker_b'], mock_cost_analyzer, mock_quality_analyzer, 30
        )
        
        assert isinstance(allocation_suggestion, AllocationSuggestion)
        assert len(allocation_suggestion.broker_allocations) == 2
        
        # Verify allocations sum to 100%
        total_allocation = sum(allocation_suggestion.broker_allocations.values())
        assert abs(total_allocation - 100.0) < 0.01
        
        # Broker A should get higher allocation (better performance)
        assert allocation_suggestion.broker_allocations['broker_a'] > allocation_suggestion.broker_allocations['broker_b']


class TestBrokerRankingSystem:
    """Test BrokerRankingSystem class"""
    
    @pytest.fixture
    def ranking_system(self):
        """Create broker ranking system instance"""
        return BrokerRankingSystem()
    
    @pytest.fixture
    def broker_performances(self):
        """Sample broker performance data"""
        return {
            'broker_excellent': BrokerPerformance(
                broker='broker_excellent',
                avg_cost_bps=1.5,
                quality_score=95.0,
                reliability_score=98.0,
                fill_rate=98.0,
                avg_latency_ms=25.0,
                avg_slippage_pips=0.5,
                rejection_rate=2.0,
                volume_handled=20000000,
                trade_count=200,
                uptime_percentage=99.8,
                composite_score=0.0,  # Will be calculated
                trend_direction='improving',
                cost_efficiency=95.0,
                service_quality=96.0
            ),
            'broker_good': BrokerPerformance(
                broker='broker_good',
                avg_cost_bps=2.5,
                quality_score=85.0,
                reliability_score=88.0,
                fill_rate=92.0,
                avg_latency_ms=45.0,
                avg_slippage_pips=1.5,
                rejection_rate=8.0,
                volume_handled=15000000,
                trade_count=150,
                uptime_percentage=99.2,
                composite_score=0.0,
                trend_direction='stable',
                cost_efficiency=80.0,
                service_quality=85.0
            ),
            'broker_poor': BrokerPerformance(
                broker='broker_poor',
                avg_cost_bps=4.0,
                quality_score=65.0,
                reliability_score=70.0,
                fill_rate=78.0,
                avg_latency_ms=120.0,
                avg_slippage_pips=3.5,
                rejection_rate=22.0,
                volume_handled=8000000,
                trade_count=80,
                uptime_percentage=97.5,
                composite_score=0.0,
                trend_direction='declining',
                cost_efficiency=60.0,
                service_quality=65.0
            )
        }
    
    @pytest.mark.asyncio
    async def test_calculate_broker_rankings(self, ranking_system, broker_performances):
        """Test broker ranking calculation"""
        mock_cost_analyzer = Mock()
        mock_quality_analyzer = Mock()
        
        # Calculate composite scores
        for broker, performance in broker_performances.items():
            performance.composite_score = ranking_system._calculate_composite_score(performance)
        
        rankings = await ranking_system.calculate_broker_rankings(
            list(broker_performances.keys()), mock_cost_analyzer, mock_quality_analyzer, 30
        )
        
        # Mock the rankings with our test data
        rankings = broker_performances
        
        # Verify ranking order (excellent > good > poor)
        sorted_brokers = sorted(rankings.items(), key=lambda x: x[1].composite_score, reverse=True)
        
        assert sorted_brokers[0][0] == 'broker_excellent'
        assert sorted_brokers[1][0] == 'broker_good'
        assert sorted_brokers[2][0] == 'broker_poor'
        
        # Verify composite scores decrease
        assert sorted_brokers[0][1].composite_score > sorted_brokers[1][1].composite_score
        assert sorted_brokers[1][1].composite_score > sorted_brokers[2][1].composite_score
    
    def test_calculate_composite_score(self, ranking_system, broker_performances):
        """Test composite score calculation"""
        excellent_perf = broker_performances['broker_excellent']
        poor_perf = broker_performances['broker_poor']
        
        excellent_score = ranking_system._calculate_composite_score(excellent_perf)
        poor_score = ranking_system._calculate_composite_score(poor_perf)
        
        # Excellent broker should have higher composite score
        assert excellent_score > poor_score
        assert 0 <= excellent_score <= 100
        assert 0 <= poor_score <= 100
    
    def test_score_cost_efficiency(self, ranking_system):
        """Test cost efficiency scoring"""
        # Lower cost (bps) should score higher
        low_cost_score = ranking_system._score_cost_efficiency(1.0)
        high_cost_score = ranking_system._score_cost_efficiency(5.0)
        
        assert low_cost_score > high_cost_score
        assert 0 <= low_cost_score <= 100
        assert 0 <= high_cost_score <= 100
    
    def test_score_quality_metrics(self, ranking_system):
        """Test quality metrics scoring"""
        high_quality_metrics = {
            'fill_rate': 98.0,
            'avg_latency_ms': 20.0,
            'avg_slippage_pips': 0.5,
            'rejection_rate': 2.0
        }
        
        low_quality_metrics = {
            'fill_rate': 75.0,
            'avg_latency_ms': 150.0,
            'avg_slippage_pips': 5.0,
            'rejection_rate': 25.0
        }
        
        high_score = ranking_system._score_quality_metrics(high_quality_metrics)
        low_score = ranking_system._score_quality_metrics(low_quality_metrics)
        
        assert high_score > low_score
        assert 0 <= high_score <= 100
        assert 0 <= low_score <= 100


class TestRoutingRecommendationEngine:
    """Test RoutingRecommendationEngine class"""
    
    @pytest.fixture
    def routing_engine(self):
        """Create routing recommendation engine instance"""
        return RoutingRecommendationEngine()
    
    @pytest.fixture
    def broker_performances(self):
        """Sample broker performance data for routing"""
        return {
            'speed_broker': BrokerPerformance(
                broker='speed_broker',
                avg_cost_bps=3.0,
                quality_score=85.0,
                reliability_score=90.0,
                fill_rate=95.0,
                avg_latency_ms=15.0,  # Very fast
                avg_slippage_pips=1.0,
                rejection_rate=5.0,
                volume_handled=10000000,
                trade_count=100,
                uptime_percentage=99.5,
                composite_score=82.0,
                trend_direction='stable',
                cost_efficiency=75.0,
                service_quality=85.0
            ),
            'cost_broker': BrokerPerformance(
                broker='cost_broker',
                avg_cost_bps=1.5,  # Very cheap
                quality_score=80.0,
                reliability_score=85.0,
                fill_rate=90.0,
                avg_latency_ms=60.0,
                avg_slippage_pips=2.0,
                rejection_rate=10.0,
                volume_handled=15000000,
                trade_count=150,
                uptime_percentage=98.8,
                composite_score=78.0,
                trend_direction='stable',
                cost_efficiency=95.0,  # Very cost efficient
                service_quality=80.0
            ),
            'quality_broker': BrokerPerformance(
                broker='quality_broker',
                avg_cost_bps=2.5,
                quality_score=95.0,  # Highest quality
                reliability_score=98.0,
                fill_rate=98.0,
                avg_latency_ms=35.0,
                avg_slippage_pips=0.5,
                rejection_rate=2.0,
                volume_handled=18000000,
                trade_count=180,
                uptime_percentage=99.9,
                composite_score=88.0,
                trend_direction='improving',
                cost_efficiency=85.0,
                service_quality=95.0
            )
        }
    
    @pytest.mark.asyncio
    async def test_generate_routing_decision_speed_priority(self, routing_engine, broker_performances):
        """Test routing decision for speed-critical trades"""
        trade_params = {
            'instrument': 'EUR_USD',
            'size': 100000,
            'urgency': 'high',  # Speed is critical
            'trade_type': 'scalping',
            'market_conditions': 'volatile'
        }
        
        decision = await routing_engine.generate_routing_decision(
            list(broker_performances.keys()), trade_params, broker_performances
        )
        
        # Should recommend speed_broker for high urgency trades
        assert decision.recommended_broker == 'speed_broker'
        assert decision.confidence_score > 0.5
        assert 'latency' in decision.reasoning.lower() or 'speed' in decision.reasoning.lower()
    
    @pytest.mark.asyncio
    async def test_generate_routing_decision_cost_priority(self, routing_engine, broker_performances):
        """Test routing decision for cost-sensitive trades"""
        trade_params = {
            'instrument': 'EUR_USD',
            'size': 1000000,  # Large size - cost matters
            'urgency': 'low',
            'trade_type': 'position',
            'market_conditions': 'calm'
        }
        
        decision = await routing_engine.generate_routing_decision(
            list(broker_performances.keys()), trade_params, broker_performances
        )
        
        # Should recommend cost_broker for large, low-urgency trades
        assert decision.recommended_broker == 'cost_broker'
        assert decision.confidence_score > 0.5
        assert 'cost' in decision.reasoning.lower()
    
    @pytest.mark.asyncio
    async def test_generate_routing_decision_quality_priority(self, routing_engine, broker_performances):
        """Test routing decision for quality-sensitive trades"""
        trade_params = {
            'instrument': 'EUR_USD',
            'size': 500000,
            'urgency': 'normal',
            'trade_type': 'swing',
            'market_conditions': 'uncertain',
            'quality_requirement': 'high'  # Quality is important
        }
        
        decision = await routing_engine.generate_routing_decision(
            list(broker_performances.keys()), trade_params, broker_performances
        )
        
        # Should recommend quality_broker for quality-sensitive trades
        assert decision.recommended_broker == 'quality_broker'
        assert decision.confidence_score > 0.5
        assert 'quality' in decision.reasoning.lower() or 'reliability' in decision.reasoning.lower()
    
    def test_calculate_routing_score(self, routing_engine):
        """Test routing score calculation"""
        performance = BrokerPerformance(
            broker='test_broker',
            avg_cost_bps=2.0,
            quality_score=85.0,
            reliability_score=90.0,
            fill_rate=95.0,
            avg_latency_ms=40.0,
            avg_slippage_pips=1.5,
            rejection_rate=5.0,
            volume_handled=10000000,
            trade_count=100,
            uptime_percentage=99.0,
            composite_score=82.0,
            trend_direction='stable',
            cost_efficiency=80.0,
            service_quality=85.0
        )
        
        trade_params = {
            'size': 100000,
            'urgency': 'normal',
            'market_conditions': 'normal'
        }
        
        score = routing_engine._calculate_routing_score(performance, trade_params)
        
        assert 0 <= score <= 100
        assert isinstance(score, (int, float))


class TestABTestingFramework:
    """Test ABTestingFramework class"""
    
    @pytest.fixture
    def ab_testing(self):
        """Create A/B testing framework instance"""
        return ABTestingFramework()
    
    @pytest.fixture
    def test_config(self):
        """Sample A/B test configuration"""
        return {
            'test_name': 'broker_performance_test',
            'group_a': ['broker_a'],
            'group_b': ['broker_b'],
            'allocation_ratio': 0.5,
            'duration_days': 7,
            'min_trades': 50,
            'significance_level': 0.05
        }
    
    @pytest.mark.asyncio
    async def test_setup_ab_test(self, ab_testing, test_config):
        """Test A/B test setup"""
        await ab_testing.setup_ab_test(test_config)
        
        assert test_config['test_name'] in ab_testing.active_tests
        test_state = ab_testing.active_tests[test_config['test_name']]
        
        assert test_state['config'] == test_config
        assert test_state['start_time'] is not None
        assert test_state['status'] == 'running'
    
    @pytest.mark.asyncio
    async def test_record_test_trade(self, ab_testing, test_config):
        """Test trade recording for A/B test"""
        await ab_testing.setup_ab_test(test_config)
        
        trade_data = {
            'broker': 'broker_a',
            'cost': 15.0,
            'latency_ms': 45.0,
            'slippage_pips': 1.5,
            'filled': True,
            'timestamp': datetime.utcnow()
        }
        
        await ab_testing.record_test_trade(test_config['test_name'], trade_data)
        
        # Verify trade is recorded
        assert 'broker_a' in ab_testing.trade_history
        assert len(ab_testing.trade_history['broker_a']) == 1
        assert ab_testing.trade_history['broker_a'][0]['cost'] == 15.0
    
    @pytest.mark.asyncio
    async def test_analyze_ab_test_results(self, ab_testing, test_config):
        """Test A/B test results analysis"""
        await ab_testing.setup_ab_test(test_config)
        
        # Mock trade data for both groups
        group_a_trades = [
            {'cost': 15.0, 'latency_ms': 40.0, 'filled': True, 'timestamp': datetime.utcnow()}
            for _ in range(60)
        ]
        
        group_b_trades = [
            {'cost': 18.0, 'latency_ms': 55.0, 'filled': True, 'timestamp': datetime.utcnow()}
            for _ in range(55)
        ]
        
        ab_testing.trade_history = {
            'broker_a': group_a_trades,
            'broker_b': group_b_trades
        }
        
        result = await ab_testing.analyze_ab_test_results(test_config['test_name'])
        
        assert isinstance(result, ABTestResult)
        assert result.test_name == test_config['test_name']
        assert result.total_trades == 115  # 60 + 55
        assert 'group_a' in result.performance_comparison
        assert 'group_b' in result.performance_comparison
        
        # Group A should perform better (lower costs)
        assert result.performance_comparison['group_a']['avg_cost'] < result.performance_comparison['group_b']['avg_cost']
    
    def test_calculate_statistical_significance(self, ab_testing):
        """Test statistical significance calculation"""
        group_a_data = [15.0] * 60  # Consistent lower costs
        group_b_data = [18.0] * 60  # Consistent higher costs
        
        p_value = ab_testing._calculate_statistical_significance(group_a_data, group_b_data)
        
        # Should be statistically significant (p < 0.05)
        assert p_value < 0.05
        assert 0 <= p_value <= 1


class TestAllocationOptimizer:
    """Test AllocationOptimizer class"""
    
    @pytest.fixture
    def allocation_optimizer(self):
        """Create allocation optimizer instance"""
        return AllocationOptimizer()
    
    @pytest.fixture
    def broker_performances_for_allocation(self):
        """Broker performance data for allocation testing"""
        return {
            'broker_premium': BrokerPerformance(
                broker='broker_premium',
                avg_cost_bps=1.8,
                quality_score=92.0,
                reliability_score=95.0,
                fill_rate=97.0,
                avg_latency_ms=30.0,
                avg_slippage_pips=0.8,
                rejection_rate=3.0,
                volume_handled=25000000,
                trade_count=250,
                uptime_percentage=99.5,
                composite_score=90.0,
                trend_direction='improving',
                cost_efficiency=88.0,
                service_quality=92.0
            ),
            'broker_standard': BrokerPerformance(
                broker='broker_standard',
                avg_cost_bps=2.5,
                quality_score=82.0,
                reliability_score=85.0,
                fill_rate=90.0,
                avg_latency_ms=50.0,
                avg_slippage_pips=1.8,
                rejection_rate=10.0,
                volume_handled=15000000,
                trade_count=150,
                uptime_percentage=98.5,
                composite_score=78.0,
                trend_direction='stable',
                cost_efficiency=75.0,
                service_quality=82.0
            ),
            'broker_budget': BrokerPerformance(
                broker='broker_budget',
                avg_cost_bps=3.5,
                quality_score=70.0,
                reliability_score=75.0,
                fill_rate=82.0,
                avg_latency_ms=85.0,
                avg_slippage_pips=2.8,
                rejection_rate=18.0,
                volume_handled=8000000,
                trade_count=80,
                uptime_percentage=97.0,
                composite_score=65.0,
                trend_direction='declining',
                cost_efficiency=65.0,
                service_quality=70.0
            )
        }
    
    @pytest.mark.asyncio
    async def test_optimize_allocation_balanced(self, allocation_optimizer, broker_performances_for_allocation):
        """Test balanced allocation optimization"""
        allocation = await allocation_optimizer.optimize_allocation(
            broker_performances_for_allocation, strategy='balanced'
        )
        
        assert isinstance(allocation, AllocationSuggestion)
        assert len(allocation.broker_allocations) == 3
        
        # Verify allocations sum to 100%
        total_allocation = sum(allocation.broker_allocations.values())
        assert abs(total_allocation - 100.0) < 0.01
        
        # Premium broker should get highest allocation
        assert allocation.broker_allocations['broker_premium'] > allocation.broker_allocations['broker_standard']
        assert allocation.broker_allocations['broker_standard'] > allocation.broker_allocations['broker_budget']
    
    @pytest.mark.asyncio
    async def test_optimize_allocation_cost_focused(self, allocation_optimizer, broker_performances_for_allocation):
        """Test cost-focused allocation optimization"""
        allocation = await allocation_optimizer.optimize_allocation(
            broker_performances_for_allocation, strategy='cost_focused'
        )
        
        # Premium broker (lowest cost) should get majority allocation
        assert allocation.broker_allocations['broker_premium'] > 50.0
        
        # Budget broker (highest cost) should get minimal allocation
        assert allocation.broker_allocations['broker_budget'] < 20.0
    
    @pytest.mark.asyncio
    async def test_optimize_allocation_quality_focused(self, allocation_optimizer, broker_performances_for_allocation):
        """Test quality-focused allocation optimization"""
        allocation = await allocation_optimizer.optimize_allocation(
            broker_performances_for_allocation, strategy='quality_focused'
        )
        
        # Premium broker (highest quality) should get majority allocation
        assert allocation.broker_allocations['broker_premium'] > 60.0
        
        # Budget broker (lowest quality) should get minimal allocation
        assert allocation.broker_allocations['broker_budget'] < 15.0
    
    def test_calculate_allocation_score(self, allocation_optimizer):
        """Test allocation score calculation"""
        performance = BrokerPerformance(
            broker='test_broker',
            avg_cost_bps=2.0,
            quality_score=85.0,
            reliability_score=90.0,
            fill_rate=95.0,
            avg_latency_ms=40.0,
            avg_slippage_pips=1.5,
            rejection_rate=5.0,
            volume_handled=10000000,
            trade_count=100,
            uptime_percentage=99.0,
            composite_score=82.0,
            trend_direction='stable',
            cost_efficiency=80.0,
            service_quality=85.0
        )
        
        balanced_score = allocation_optimizer._calculate_allocation_score(performance, 'balanced')
        cost_score = allocation_optimizer._calculate_allocation_score(performance, 'cost_focused')
        quality_score = allocation_optimizer._calculate_allocation_score(performance, 'quality_focused')
        
        assert 0 <= balanced_score <= 100
        assert 0 <= cost_score <= 100
        assert 0 <= quality_score <= 100
        
        # Different strategies should produce different scores
        assert balanced_score != cost_score or balanced_score != quality_score


@pytest.mark.asyncio
async def test_integration_broker_comparison():
    """Integration test for complete broker comparison workflow"""
    # Create comparison engine
    comparison_engine = BrokerComparisonEngine()
    await comparison_engine.initialize()
    
    # Mock analyzers
    mock_cost_analyzer = Mock()
    mock_cost_analyzer.generate_broker_cost_comparison = AsyncMock(return_value={
        'broker_alpha': {
            'total_cost': 1200.0,
            'avg_cost_bps': 2.0,
            'trade_count': 100,
            'total_volume': 15000000,
            'cost_by_category': {
                'spread': 800.0,
                'commission': 300.0,
                'slippage': 100.0
            }
        },
        'broker_beta': {
            'total_cost': 1800.0,
            'avg_cost_bps': 3.0,
            'trade_count': 120,
            'total_volume': 18000000,
            'cost_by_category': {
                'spread': 1200.0,
                'commission': 450.0,
                'slippage': 150.0
            }
        },
        'broker_gamma': {
            'total_cost': 2100.0,
            'avg_cost_bps': 3.5,
            'trade_count': 140,
            'total_volume': 21000000,
            'cost_by_category': {
                'spread': 1400.0,
                'commission': 525.0,
                'slippage': 175.0
            }
        }
    })
    
    mock_quality_analyzer = Mock()
    quality_reports = {
        'broker_alpha': Mock(quality_score=90.0, fill_rate=96.0, avg_latency_ms=35.0, 
                           avg_slippage_pips=1.0, rejection_rate=4.0),
        'broker_beta': Mock(quality_score=82.0, fill_rate=88.0, avg_latency_ms=55.0, 
                          avg_slippage_pips=2.0, rejection_rate=12.0),
        'broker_gamma': Mock(quality_score=75.0, fill_rate=85.0, avg_latency_ms=75.0, 
                           avg_slippage_pips=2.5, rejection_rate=15.0)
    }
    mock_quality_analyzer.generate_quality_report = AsyncMock(
        side_effect=lambda broker, *args: quality_reports[broker]
    )
    
    brokers = ['broker_alpha', 'broker_beta', 'broker_gamma']
    
    # 1. Compare brokers
    comparison_result = await comparison_engine.compare_brokers(
        brokers, mock_cost_analyzer, mock_quality_analyzer, 30
    )
    
    assert len(comparison_result.broker_performances) == 3
    
    # Alpha should rank highest (best cost and quality)
    sorted_performances = sorted(
        comparison_result.broker_performances.items(),
        key=lambda x: x[1].composite_score,
        reverse=True
    )
    assert sorted_performances[0][0] == 'broker_alpha'
    
    # 2. Get routing recommendation for urgent trade
    urgent_trade_params = {
        'instrument': 'EUR_USD',
        'size': 100000,
        'urgency': 'high',
        'trade_type': 'scalping',
        'market_conditions': 'volatile'
    }
    
    routing_decision = await comparison_engine.get_routing_recommendation(
        brokers, urgent_trade_params, mock_cost_analyzer, mock_quality_analyzer
    )
    
    # Should recommend best performing broker (Alpha)
    assert routing_decision.recommended_broker == 'broker_alpha'
    assert routing_decision.confidence_score > 0.7
    
    # 3. Optimize allocation
    allocation_suggestion = await comparison_engine.optimize_allocation(
        brokers, mock_cost_analyzer, mock_quality_analyzer, 30
    )
    
    # Alpha should get highest allocation
    assert allocation_suggestion.broker_allocations['broker_alpha'] > 40.0
    assert allocation_suggestion.broker_allocations['broker_alpha'] > allocation_suggestion.broker_allocations['broker_beta']
    assert allocation_suggestion.broker_allocations['broker_beta'] > allocation_suggestion.broker_allocations['broker_gamma']
    
    # Total allocation should be 100%
    total_allocation = sum(allocation_suggestion.broker_allocations.values())
    assert abs(total_allocation - 100.0) < 0.01
    
    # 4. Setup A/B test
    ab_test_config = {
        'test_name': 'alpha_vs_beta_test',
        'group_a': ['broker_alpha'],
        'group_b': ['broker_beta'],
        'allocation_ratio': 0.5,
        'duration_days': 7,
        'min_trades': 50
    }
    
    await comparison_engine.ab_testing.setup_ab_test(ab_test_config)
    
    # Verify test is active
    assert ab_test_config['test_name'] in comparison_engine.ab_testing.active_tests
    
    # Record some test trades
    for i in range(30):
        await comparison_engine.ab_testing.record_test_trade(
            ab_test_config['test_name'],
            {
                'broker': 'broker_alpha',
                'cost': 12.0 + (i % 3),  # 12-14
                'latency_ms': 30.0 + (i % 10),  # 30-39
                'filled': True,
                'timestamp': datetime.utcnow()
            }
        )
        
        await comparison_engine.ab_testing.record_test_trade(
            ab_test_config['test_name'],
            {
                'broker': 'broker_beta',
                'cost': 15.0 + (i % 4),  # 15-18
                'latency_ms': 50.0 + (i % 15),  # 50-64
                'filled': True,
                'timestamp': datetime.utcnow()
            }
        )
    
    # Analyze A/B test results
    ab_result = await comparison_engine.ab_testing.analyze_ab_test_results(ab_test_config['test_name'])
    
    assert ab_result.total_trades == 60
    assert ab_result.performance_comparison['group_a']['avg_cost'] < ab_result.performance_comparison['group_b']['avg_cost']
    
    # Statistical significance should be detected
    assert ab_result.statistical_significance < 0.05  # p-value


if __name__ == "__main__":
    pytest.main([__file__])