"""
Unit tests for Execution Quality Analyzer - Story 8.14

Tests for execution_quality_analyzer.py covering:
- Execution quality measurement
- Slippage analysis
- Fill rate tracking
- Latency monitoring
- Rejection rate analysis
- Quality scoring
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch

from ..execution_quality_analyzer import (
    ExecutionQualityAnalyzer, LatencyTracker, FillRateTracker, 
    QualityScorer, ExecutionData, QualityReport, QualityMetrics
)


class TestExecutionQualityAnalyzer:
    """Test ExecutionQualityAnalyzer class"""
    
    @pytest.fixture
    def quality_analyzer(self):
        """Create execution quality analyzer instance"""
        return ExecutionQualityAnalyzer()
    
    @pytest.fixture
    def sample_execution_data(self):
        """Sample execution data for testing"""
        return ExecutionData(
            trade_id='test_execution_123',
            broker='test_broker',
            instrument='EUR_USD',
            order_type='market',
            order_size=Decimal('100000'),
            request_time=datetime.utcnow() - timedelta(milliseconds=50),
            execution_time=datetime.utcnow(),
            expected_price=Decimal('1.0500'),
            executed_price=Decimal('1.0502'),
            slippage_pips=Decimal('2.0'),
            fill_status='filled',
            rejection_reason=None,
            market_conditions={
                'volatility': 'normal',
                'liquidity': 'high',
                'session': 'london'
            }
        )
    
    @pytest.mark.asyncio
    async def test_initialize_quality_analyzer(self, quality_analyzer):
        """Test quality analyzer initialization"""
        await quality_analyzer.initialize()
        
        assert quality_analyzer.latency_tracker is not None
        assert quality_analyzer.fill_rate_tracker is not None
        assert quality_analyzer.quality_scorer is not None
        assert len(quality_analyzer.execution_history) == 0
    
    @pytest.mark.asyncio
    async def test_record_execution(self, quality_analyzer, sample_execution_data):
        """Test execution recording"""
        await quality_analyzer.initialize()
        await quality_analyzer.record_execution(sample_execution_data)
        
        # Check execution is recorded
        assert len(quality_analyzer.execution_history) == 1
        assert quality_analyzer.execution_history[0].trade_id == 'test_execution_123'
        
        # Check individual trackers are updated
        latency_ms = (sample_execution_data.execution_time - sample_execution_data.request_time).total_seconds() * 1000
        broker_latencies = quality_analyzer.latency_tracker.latency_data.get('test_broker', [])
        assert len(broker_latencies) == 1
        assert broker_latencies[0]['latency_ms'] == latency_ms
    
    @pytest.mark.asyncio
    async def test_generate_quality_report(self, quality_analyzer, sample_execution_data):
        """Test quality report generation"""
        await quality_analyzer.initialize()
        
        # Record multiple executions
        executions = []
        for i in range(5):
            execution = ExecutionData(
                trade_id=f'test_execution_{i}',
                broker='test_broker',
                instrument='EUR_USD',
                order_type='market',
                order_size=Decimal('100000'),
                request_time=datetime.utcnow() - timedelta(milliseconds=50, seconds=i),
                execution_time=datetime.utcnow() - timedelta(seconds=i),
                expected_price=Decimal('1.0500'),
                executed_price=Decimal('1.0500') + Decimal(f'0.000{i}'),
                slippage_pips=Decimal(f'{i}'),
                fill_status='filled' if i < 4 else 'rejected',
                rejection_reason='insufficient_liquidity' if i == 4 else None,
                market_conditions={'volatility': 'normal', 'liquidity': 'high', 'session': 'london'}
            )
            executions.append(execution)
            await quality_analyzer.record_execution(execution)
        
        # Generate report
        report = await quality_analyzer.generate_quality_report('test_broker', 'EUR_USD', 30)
        
        assert isinstance(report, QualityReport)
        assert report.broker == 'test_broker'
        assert report.instrument == 'EUR_USD'
        assert report.period_days == 30
        assert report.total_orders == 5
        assert report.filled_orders == 4
        assert report.rejected_orders == 1
        assert report.fill_rate == 80.0  # 4/5 * 100
        assert report.rejection_rate == 20.0  # 1/5 * 100
        assert report.avg_slippage_pips > 0
        assert report.avg_latency_ms > 0
        assert 0 <= report.quality_score <= 100
    
    @pytest.mark.asyncio
    async def test_get_quality_metrics(self, quality_analyzer):
        """Test quality metrics calculation"""
        await quality_analyzer.initialize()
        
        # Record sample executions with varying quality
        good_execution = ExecutionData(
            trade_id='good_execution',
            broker='test_broker',
            instrument='EUR_USD',
            order_type='market',
            order_size=Decimal('100000'),
            request_time=datetime.utcnow() - timedelta(milliseconds=10),
            execution_time=datetime.utcnow(),
            expected_price=Decimal('1.0500'),
            executed_price=Decimal('1.0500'),
            slippage_pips=Decimal('0'),
            fill_status='filled',
            rejection_reason=None,
            market_conditions={'volatility': 'low', 'liquidity': 'high', 'session': 'london'}
        )
        
        poor_execution = ExecutionData(
            trade_id='poor_execution',
            broker='test_broker',
            instrument='EUR_USD',
            order_type='market',
            order_size=Decimal('100000'),
            request_time=datetime.utcnow() - timedelta(milliseconds=200),
            execution_time=datetime.utcnow(),
            expected_price=Decimal('1.0500'),
            executed_price=Decimal('1.0510'),
            slippage_pips=Decimal('10'),
            fill_status='filled',
            rejection_reason=None,
            market_conditions={'volatility': 'high', 'liquidity': 'low', 'session': 'ny'}
        )
        
        await quality_analyzer.record_execution(good_execution)
        await quality_analyzer.record_execution(poor_execution)
        
        metrics = await quality_analyzer.get_quality_metrics('test_broker', 'EUR_USD', 7)
        
        assert isinstance(metrics, QualityMetrics)
        assert metrics.avg_slippage_pips == 5.0  # (0 + 10) / 2
        assert metrics.total_executions == 2
        assert metrics.successful_executions == 2
        assert metrics.execution_efficiency == 100.0  # 2/2 * 100


class TestLatencyTracker:
    """Test LatencyTracker class"""
    
    @pytest.fixture
    def latency_tracker(self):
        """Create latency tracker instance"""
        return LatencyTracker()
    
    @pytest.mark.asyncio
    async def test_record_latency(self, latency_tracker):
        """Test latency recording"""
        await latency_tracker.record_latency(
            'test_broker', 'EUR_USD', 45.5, 'market', 'london'
        )
        
        assert 'test_broker' in latency_tracker.latency_data
        assert len(latency_tracker.latency_data['test_broker']) == 1
        
        record = latency_tracker.latency_data['test_broker'][0]
        assert record['instrument'] == 'EUR_USD'
        assert record['latency_ms'] == 45.5
        assert record['order_type'] == 'market'
        assert record['session'] == 'london'
    
    @pytest.mark.asyncio
    async def test_get_average_latency(self, latency_tracker):
        """Test average latency calculation"""
        # Record multiple latencies
        latencies = [25.0, 35.0, 45.0, 55.0]
        for latency in latencies:
            await latency_tracker.record_latency(
                'test_broker', 'EUR_USD', latency, 'market', 'london'
            )
        
        avg_latency = await latency_tracker.get_average_latency('test_broker', 7)
        expected_avg = sum(latencies) / len(latencies)
        
        assert avg_latency == expected_avg
    
    @pytest.mark.asyncio
    async def test_get_latency_percentiles(self, latency_tracker):
        """Test latency percentile calculation"""
        # Record latencies: 10, 20, 30, 40, 50, 60, 70, 80, 90, 100
        latencies = [float(i) for i in range(10, 101, 10)]
        
        for latency in latencies:
            await latency_tracker.record_latency(
                'test_broker', 'EUR_USD', latency, 'market', 'london'
            )
        
        percentiles = await latency_tracker.get_latency_percentiles('test_broker', 7)
        
        assert percentiles['p50'] == 55.0  # Median
        assert percentiles['p95'] == 95.0  # 95th percentile
        assert percentiles['p99'] == 99.0  # 99th percentile
    
    @pytest.mark.asyncio
    async def test_get_latency_by_session(self, latency_tracker):
        """Test latency breakdown by market session"""
        # Record latencies for different sessions
        session_latencies = {
            'london': [20.0, 25.0, 30.0],
            'ny': [35.0, 40.0, 45.0],
            'asian': [50.0, 55.0, 60.0]
        }
        
        for session, latencies in session_latencies.items():
            for latency in latencies:
                await latency_tracker.record_latency(
                    'test_broker', 'EUR_USD', latency, 'market', session
                )
        
        session_breakdown = await latency_tracker.get_latency_by_session('test_broker', 7)
        
        for session, expected_latencies in session_latencies.items():
            expected_avg = sum(expected_latencies) / len(expected_latencies)
            assert session_breakdown[session]['avg_latency'] == expected_avg
            assert session_breakdown[session]['count'] == len(expected_latencies)


class TestFillRateTracker:
    """Test FillRateTracker class"""
    
    @pytest.fixture
    def fill_rate_tracker(self):
        """Create fill rate tracker instance"""
        return FillRateTracker()
    
    @pytest.mark.asyncio
    async def test_record_order_outcome(self, fill_rate_tracker):
        """Test order outcome recording"""
        await fill_rate_tracker.record_order_outcome(
            'test_broker', 'EUR_USD', 'market', 'filled', None
        )
        
        await fill_rate_tracker.record_order_outcome(
            'test_broker', 'EUR_USD', 'limit', 'rejected', 'price_not_available'
        )
        
        assert 'test_broker' in fill_rate_tracker.order_outcomes
        assert len(fill_rate_tracker.order_outcomes['test_broker']) == 2
        
        outcomes = fill_rate_tracker.order_outcomes['test_broker']
        assert outcomes[0]['status'] == 'filled'
        assert outcomes[1]['status'] == 'rejected'
        assert outcomes[1]['rejection_reason'] == 'price_not_available'
    
    @pytest.mark.asyncio
    async def test_calculate_fill_rate(self, fill_rate_tracker):
        """Test fill rate calculation"""
        # Record 8 filled and 2 rejected orders
        for i in range(8):
            await fill_rate_tracker.record_order_outcome(
                'test_broker', 'EUR_USD', 'market', 'filled', None
            )
        
        for i in range(2):
            await fill_rate_tracker.record_order_outcome(
                'test_broker', 'EUR_USD', 'market', 'rejected', 'insufficient_liquidity'
            )
        
        fill_rate = await fill_rate_tracker.calculate_fill_rate('test_broker', 7)
        
        # 8 filled out of 10 total = 80%
        assert fill_rate == 80.0
    
    @pytest.mark.asyncio
    async def test_get_rejection_analysis(self, fill_rate_tracker):
        """Test rejection reason analysis"""
        # Record various rejection reasons
        rejection_reasons = [
            'insufficient_liquidity',
            'insufficient_liquidity',
            'price_not_available',
            'connection_error'
        ]
        
        for reason in rejection_reasons:
            await fill_rate_tracker.record_order_outcome(
                'test_broker', 'EUR_USD', 'market', 'rejected', reason
            )
        
        rejection_analysis = await fill_rate_tracker.get_rejection_analysis('test_broker', 7)
        
        assert rejection_analysis['total_rejections'] == 4
        assert rejection_analysis['rejection_reasons']['insufficient_liquidity'] == 2
        assert rejection_analysis['rejection_reasons']['price_not_available'] == 1
        assert rejection_analysis['rejection_reasons']['connection_error'] == 1
    
    @pytest.mark.asyncio
    async def test_get_fill_rate_by_order_type(self, fill_rate_tracker):
        """Test fill rate breakdown by order type"""
        # Market orders: 9/10 filled
        for i in range(9):
            await fill_rate_tracker.record_order_outcome(
                'test_broker', 'EUR_USD', 'market', 'filled', None
            )
        await fill_rate_tracker.record_order_outcome(
            'test_broker', 'EUR_USD', 'market', 'rejected', 'slippage_limit'
        )
        
        # Limit orders: 6/10 filled
        for i in range(6):
            await fill_rate_tracker.record_order_outcome(
                'test_broker', 'EUR_USD', 'limit', 'filled', None
            )
        for i in range(4):
            await fill_rate_tracker.record_order_outcome(
                'test_broker', 'EUR_USD', 'limit', 'rejected', 'price_not_reached'
            )
        
        fill_rates_by_type = await fill_rate_tracker.get_fill_rate_by_order_type('test_broker', 7)
        
        assert fill_rates_by_type['market']['fill_rate'] == 90.0  # 9/10
        assert fill_rates_by_type['limit']['fill_rate'] == 60.0   # 6/10


class TestQualityScorer:
    """Test QualityScorer class"""
    
    @pytest.fixture
    def quality_scorer(self):
        """Create quality scorer instance"""
        return QualityScorer()
    
    def test_calculate_quality_score_perfect(self, quality_scorer):
        """Test quality score for perfect execution"""
        metrics = QualityMetrics(
            avg_latency_ms=10.0,      # Excellent latency
            avg_slippage_pips=0.0,    # No slippage
            fill_rate=100.0,          # Perfect fill rate
            rejection_rate=0.0,       # No rejections
            execution_efficiency=100.0, # Perfect efficiency
            total_executions=100
        )
        
        score = quality_scorer.calculate_quality_score(metrics)
        
        # Should be close to perfect score (100)
        assert score >= 95.0
        assert score <= 100.0
    
    def test_calculate_quality_score_poor(self, quality_scorer):
        """Test quality score for poor execution"""
        metrics = QualityMetrics(
            avg_latency_ms=500.0,     # Very high latency
            avg_slippage_pips=20.0,   # High slippage
            fill_rate=50.0,           # Poor fill rate
            rejection_rate=50.0,      # High rejection rate
            execution_efficiency=50.0, # Poor efficiency
            total_executions=100
        )
        
        score = quality_scorer.calculate_quality_score(metrics)
        
        # Should be low score
        assert score >= 0.0
        assert score <= 30.0
    
    def test_calculate_quality_score_average(self, quality_scorer):
        """Test quality score for average execution"""
        metrics = QualityMetrics(
            avg_latency_ms=100.0,     # Moderate latency
            avg_slippage_pips=2.0,    # Moderate slippage
            fill_rate=85.0,           # Good fill rate
            rejection_rate=15.0,      # Moderate rejection rate
            execution_efficiency=85.0, # Good efficiency
            total_executions=100
        )
        
        score = quality_scorer.calculate_quality_score(metrics)
        
        # Should be moderate score
        assert score >= 60.0
        assert score <= 85.0
    
    def test_score_component_calculations(self, quality_scorer):
        """Test individual component score calculations"""
        # Test latency scoring
        assert quality_scorer._score_latency(10.0) > quality_scorer._score_latency(100.0)
        assert quality_scorer._score_latency(0.0) == 100.0  # Perfect latency
        
        # Test slippage scoring
        assert quality_scorer._score_slippage(0.0) == 100.0  # No slippage
        assert quality_scorer._score_slippage(1.0) > quality_scorer._score_slippage(10.0)
        
        # Test fill rate scoring
        assert quality_scorer._score_fill_rate(100.0) == 100.0
        assert quality_scorer._score_fill_rate(80.0) > quality_scorer._score_fill_rate(60.0)
        
        # Test rejection rate scoring
        assert quality_scorer._score_rejection_rate(0.0) == 100.0
        assert quality_scorer._score_rejection_rate(10.0) > quality_scorer._score_rejection_rate(30.0)


@pytest.mark.asyncio
async def test_integration_quality_analysis():
    """Integration test for complete execution quality analysis"""
    # Create analyzer
    quality_analyzer = ExecutionQualityAnalyzer()
    await quality_analyzer.initialize()
    
    # Simulate various execution scenarios
    executions = [
        # Good executions
        ExecutionData(
            trade_id='good_1',
            broker='test_broker',
            instrument='EUR_USD',
            order_type='market',
            order_size=Decimal('100000'),
            request_time=datetime.utcnow() - timedelta(milliseconds=20),
            execution_time=datetime.utcnow(),
            expected_price=Decimal('1.0500'),
            executed_price=Decimal('1.0500'),
            slippage_pips=Decimal('0'),
            fill_status='filled',
            rejection_reason=None,
            market_conditions={'volatility': 'low', 'liquidity': 'high', 'session': 'london'}
        ),
        ExecutionData(
            trade_id='good_2',
            broker='test_broker',
            instrument='EUR_USD',
            order_type='market',
            order_size=Decimal('50000'),
            request_time=datetime.utcnow() - timedelta(milliseconds=25),
            execution_time=datetime.utcnow(),
            expected_price=Decimal('1.0510'),
            executed_price=Decimal('1.0511'),
            slippage_pips=Decimal('1'),
            fill_status='filled',
            rejection_reason=None,
            market_conditions={'volatility': 'low', 'liquidity': 'high', 'session': 'london'}
        ),
        # Average execution
        ExecutionData(
            trade_id='average_1',
            broker='test_broker',
            instrument='EUR_USD',
            order_type='market',
            order_size=Decimal('200000'),
            request_time=datetime.utcnow() - timedelta(milliseconds=80),
            execution_time=datetime.utcnow(),
            expected_price=Decimal('1.0520'),
            executed_price=Decimal('1.0525'),
            slippage_pips=Decimal('5'),
            fill_status='filled',
            rejection_reason=None,
            market_conditions={'volatility': 'normal', 'liquidity': 'medium', 'session': 'ny'}
        ),
        # Poor execution
        ExecutionData(
            trade_id='poor_1',
            broker='test_broker',
            instrument='EUR_USD',
            order_type='market',
            order_size=Decimal('500000'),
            request_time=datetime.utcnow() - timedelta(milliseconds=200),
            execution_time=datetime.utcnow(),
            expected_price=Decimal('1.0530'),
            executed_price=Decimal('1.0540'),
            slippage_pips=Decimal('10'),
            fill_status='filled',
            rejection_reason=None,
            market_conditions={'volatility': 'high', 'liquidity': 'low', 'session': 'asian'}
        ),
        # Rejected execution
        ExecutionData(
            trade_id='rejected_1',
            broker='test_broker',
            instrument='EUR_USD',
            order_type='market',
            order_size=Decimal('1000000'),
            request_time=datetime.utcnow() - timedelta(milliseconds=150),
            execution_time=datetime.utcnow(),
            expected_price=Decimal('1.0540'),
            executed_price=None,
            slippage_pips=None,
            fill_status='rejected',
            rejection_reason='insufficient_liquidity',
            market_conditions={'volatility': 'high', 'liquidity': 'low', 'session': 'asian'}
        )
    ]
    
    # Record all executions
    for execution in executions:
        await quality_analyzer.record_execution(execution)
    
    # Generate comprehensive quality report
    report = await quality_analyzer.generate_quality_report('test_broker', 'EUR_USD', 30)
    
    # Verify report accuracy
    assert report.total_orders == 5
    assert report.filled_orders == 4
    assert report.rejected_orders == 1
    assert report.fill_rate == 80.0  # 4/5 * 100
    assert report.rejection_rate == 20.0  # 1/5 * 100
    
    # Verify slippage calculation (0 + 1 + 5 + 10) / 4 = 4.0
    assert report.avg_slippage_pips == 4.0
    
    # Verify latency calculation
    expected_latencies = [20, 25, 80, 200]  # Excluding rejected order
    expected_avg_latency = sum(expected_latencies) / len(expected_latencies)
    assert report.avg_latency_ms == expected_avg_latency
    
    # Verify quality score is reasonable
    assert 30 <= report.quality_score <= 90  # Should be moderate due to mixed quality
    
    # Test quality metrics
    metrics = await quality_analyzer.get_quality_metrics('test_broker', 'EUR_USD', 30)
    
    assert metrics.total_executions == 5
    assert metrics.successful_executions == 4
    assert metrics.execution_efficiency == 80.0
    assert metrics.avg_slippage_pips == 4.0
    assert metrics.avg_latency_ms == expected_avg_latency
    
    # Test latency analysis
    latency_percentiles = await quality_analyzer.latency_tracker.get_latency_percentiles('test_broker', 30)
    assert 'p50' in latency_percentiles
    assert 'p95' in latency_percentiles
    assert 'p99' in latency_percentiles
    
    # Test fill rate analysis
    fill_rate = await quality_analyzer.fill_rate_tracker.calculate_fill_rate('test_broker', 30)
    assert fill_rate == 80.0
    
    rejection_analysis = await quality_analyzer.fill_rate_tracker.get_rejection_analysis('test_broker', 30)
    assert rejection_analysis['total_rejections'] == 1
    assert rejection_analysis['rejection_reasons']['insufficient_liquidity'] == 1


if __name__ == "__main__":
    pytest.main([__file__])