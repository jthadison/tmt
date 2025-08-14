"""
Tests for Strategy Performance Analyzer.
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from app.strategy_performance_analyzer import (
    StrategyPerformanceAnalyzer, Trade
)
from app.models import (
    TradingStrategy, StrategyType, StrategyStatus, StrategyConfiguration,
    StrategyClassification, StrategyLogic, StrategyLifecycle, StrategyComplexity
)


@pytest.fixture
def sample_trades():
    """Create sample trades for testing."""
    base_time = datetime.utcnow()
    trades = []
    
    # Mix of winning and losing trades
    for i in range(50):
        pnl = Decimal('100') if i % 3 == 0 else Decimal('-50')  # 33% win rate
        win = pnl > 0
        trade = Trade(
            strategy_id="test_strategy",
            timestamp=base_time + timedelta(hours=i),
            pnl=pnl,
            win=win,
            hold_time=timedelta(hours=2)
        )
        trades.append(trade)
    
    return trades


@pytest.fixture
def mock_strategy():
    """Create a mock trading strategy."""
    return TradingStrategy(
        strategy_id="test_strategy",
        strategy_name="Test Strategy",
        version="1.0",
        classification=StrategyClassification(
            type=StrategyType.TREND_FOLLOWING,
            subtype="momentum",
            timeframe=["H1", "H4"],
            symbols=["EURUSD", "GBPUSD"],
            market_regimes=[]
        ),
        logic=StrategyLogic(
            entry_conditions=["price > ma20"],
            exit_conditions=["price < ma20"],
            risk_management=["stop_loss", "position_sizing"],
            signal_generation="momentum_based",
            complexity=StrategyComplexity.MODERATE
        ),
        performance=None,  # Will be set by analyzer
        lifecycle=StrategyLifecycle(
            created_at=datetime.utcnow(),
            activated_at=datetime.utcnow(),
            last_modified=datetime.utcnow(),
            status=StrategyStatus.ACTIVE
        ),
        configuration=StrategyConfiguration(
            enabled=True,
            weight=Decimal('0.1'),
            max_allocation=Decimal('0.25'),
            min_trades_for_evaluation=30,
            evaluation_period=90
        )
    )


class TestStrategyPerformanceAnalyzer:
    """Test cases for StrategyPerformanceAnalyzer."""
    
    def setup_method(self):
        """Setup test environment."""
        self.analyzer = StrategyPerformanceAnalyzer()
    
    def test_calculate_performance_metrics(self, sample_trades):
        """Test performance metrics calculation."""
        metrics = self.analyzer._calculate_performance_metrics(sample_trades)
        
        assert metrics.total_trades == 50
        assert metrics.win_count == 17  # Approximately 33%
        assert metrics.loss_count == 33
        assert 0.30 <= float(metrics.win_rate) <= 0.40  # Around 33%
        assert metrics.total_return > 0  # Should be profitable overall
    
    def test_calculate_max_drawdown(self, sample_trades):
        """Test maximum drawdown calculation."""
        drawdown = self.analyzer._calculate_max_drawdown(sample_trades)
        
        assert drawdown >= 0
        assert isinstance(drawdown, Decimal)
    
    def test_calculate_sharpe_ratio(self, sample_trades):
        """Test Sharpe ratio calculation."""
        sharpe = self.analyzer._calculate_sharpe_ratio(sample_trades)
        
        assert isinstance(sharpe, Decimal)
        # Should be reasonable value for our sample data
        assert -5 <= float(sharpe) <= 5
    
    def test_empty_trades_handling(self):
        """Test handling of empty trade list."""
        metrics = self.analyzer._calculate_performance_metrics([])
        
        assert metrics.total_trades == 0
        assert metrics.win_rate == Decimal('0')
        assert metrics.total_return == Decimal('0')
    
    @pytest.mark.asyncio
    async def test_analyze_strategy_performance_insufficient_data(self, mock_strategy):
        """Test analysis with insufficient data."""
        # Mock insufficient trades
        with patch.object(self.analyzer, '_get_strategy_trades', return_value=[]):
            performance = await self.analyzer.analyze_strategy_performance(
                "test_strategy", timedelta(days=30)
            )
            
            assert performance.strategy_id == "test_strategy"
            assert not performance.significance.statistically_significant
            assert performance.overall.total_trades == 0
    
    @pytest.mark.asyncio
    async def test_analyze_strategy_performance_sufficient_data(self, mock_strategy, sample_trades):
        """Test analysis with sufficient data."""
        # Mock sufficient trades
        with patch.object(self.analyzer, '_get_strategy_trades', return_value=sample_trades):
            performance = await self.analyzer.analyze_strategy_performance(
                "test_strategy", timedelta(days=30)
            )
            
            assert performance.strategy_id == "test_strategy"
            assert performance.overall.total_trades == 50
            assert performance.time_based is not None
            assert performance.trend is not None
    
    def test_calculate_daily_performance(self, sample_trades):
        """Test daily performance calculation."""
        daily_performance = self.analyzer._calculate_daily_performance(sample_trades)
        
        assert len(daily_performance) > 0
        
        # Check first day performance
        first_day = list(daily_performance.values())[0]
        assert first_day.trades > 0
        assert isinstance(first_day.pnl, Decimal)
        assert 0 <= float(first_day.win_rate) <= 1
    
    @pytest.mark.asyncio
    async def test_detect_performance_trend_improving(self):
        """Test performance trend detection for improving strategy."""
        # Create trades with improving performance
        trades = []
        base_time = datetime.utcnow()
        
        # First half: poor performance
        for i in range(25):
            pnl = Decimal('-10')  # Losing trades
            trade = Trade("test", base_time + timedelta(hours=i), pnl, False, timedelta(hours=1))
            trades.append(trade)
        
        # Second half: good performance
        for i in range(25, 50):
            pnl = Decimal('20')  # Winning trades
            trade = Trade("test", base_time + timedelta(hours=i), pnl, True, timedelta(hours=1))
            trades.append(trade)
        
        trend = await self.analyzer._detect_performance_trend(trades)
        
        assert trend.direction.value in ['improving', 'stable']  # Should detect improvement
        assert trend.trend_strength > Decimal('0')
    
    def test_calmar_ratio_calculation(self):
        """Test Calmar ratio calculation."""
        total_return = Decimal('0.15')
        max_drawdown = Decimal('0.05')
        num_trades = 100
        
        calmar = self.analyzer._calculate_calmar_ratio(total_return, max_drawdown, num_trades)
        
        assert calmar > 0
        assert isinstance(calmar, Decimal)
    
    def test_calmar_ratio_zero_drawdown(self):
        """Test Calmar ratio with zero drawdown."""
        total_return = Decimal('0.15')
        max_drawdown = Decimal('0')
        num_trades = 100
        
        calmar = self.analyzer._calculate_calmar_ratio(total_return, max_drawdown, num_trades)
        
        assert calmar == Decimal('0')  # Should handle zero drawdown gracefully
    
    @pytest.mark.asyncio
    async def test_analyze_time_based_performance(self, sample_trades):
        """Test time-based performance analysis."""
        time_based = await self.analyzer._analyze_time_based_performance(sample_trades)
        
        assert time_based.daily is not None
        assert time_based.weekly is not None
        assert time_based.monthly is not None
        assert time_based.rolling_30_day is not None
        assert time_based.rolling_90_day is not None
        assert time_based.rolling_365_day is not None
    
    def test_performance_metrics_validation(self, sample_trades):
        """Test that performance metrics are within expected ranges."""
        metrics = self.analyzer._calculate_performance_metrics(sample_trades)
        
        # Validate ranges
        assert 0 <= float(metrics.win_rate) <= 1
        assert metrics.total_trades >= 0
        assert metrics.win_count >= 0
        assert metrics.loss_count >= 0
        assert metrics.win_count + metrics.loss_count == metrics.total_trades
        assert metrics.max_drawdown >= 0
    
    @pytest.mark.asyncio
    async def test_create_minimal_performance(self, sample_trades):
        """Test creation of minimal performance analysis."""
        # Use only a few trades (insufficient for full analysis)
        few_trades = sample_trades[:5]
        
        performance = await self.analyzer._create_minimal_performance("test_strategy", few_trades)
        
        assert performance.strategy_id == "test_strategy"
        assert not performance.significance.statistically_significant
        assert performance.significance.sample_size == 5
        assert performance.overall.total_trades == 5