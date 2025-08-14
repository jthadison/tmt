"""
Tests for Performance Calculator
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import statistics

from agents.parameter_optimization.app.performance_calculator import (
    RollingPerformanceCalculator, TradeRecord, PerformancePeriod
)
from agents.parameter_optimization.app.models import MarketRegime


class TestRollingPerformanceCalculator:
    
    @pytest.fixture
    def calculator(self):
        return RollingPerformanceCalculator(rolling_window_days=30)
    
    @pytest.fixture
    def sample_trades(self):
        """Create sample trade records for testing"""
        trades = []
        base_date = datetime.utcnow() - timedelta(days=45)
        
        for i in range(20):
            trade = TradeRecord(
                trade_id=f"trade_{i}",
                account_id="test_account",
                symbol="EURUSD",
                entry_time=base_date + timedelta(days=i),
                exit_time=base_date + timedelta(days=i, hours=2),
                entry_price=1.1000 + i * 0.0001,
                exit_price=1.1000 + i * 0.0001 + (0.0010 if i % 2 == 0 else -0.0005),
                position_size=10000,
                pnl=10.0 if i % 2 == 0 else -5.0,
                pnl_pips=10.0 if i % 2 == 0 else -5.0,
                commission=2.0,
                slippage=0.5,
                trade_type="long",
                exit_reason="take_profit" if i % 2 == 0 else "stop_loss",
                signal_confidence=0.75 + (i % 5) * 0.05,
                market_regime=MarketRegime.TRENDING if i % 3 == 0 else MarketRegime.RANGING
            )
            trades.append(trade)
        
        return trades
    
    def test_calculate_current_performance(self, calculator, sample_trades):
        """Test current performance calculation"""
        performance = calculator.calculate_current_performance("test_account", sample_trades)
        
        assert performance.account_id == "test_account"
        assert performance.total_trades > 0
        assert 0 <= performance.win_rate <= 1
        assert performance.sharpe_ratio is not None
        assert performance.max_drawdown >= 0
    
    def test_calculate_rolling_performance(self, calculator, sample_trades):
        """Test rolling performance calculation"""
        periods = calculator.calculate_rolling_performance("test_account", sample_trades)
        
        assert len(periods) > 0
        assert all(isinstance(period, PerformancePeriod) for period in periods)
        assert all(len(period.trades) >= 5 for period in periods)  # Min trades requirement
    
    def test_empty_trades_handling(self, calculator):
        """Test handling of empty trade list"""
        performance = calculator.calculate_current_performance("test_account", [])
        
        assert performance.total_trades == 0
        assert performance.win_rate == 0
        assert performance.sharpe_ratio == 0
    
    def test_insufficient_trades(self, calculator):
        """Test handling of insufficient trades"""
        # Create only 3 trades (less than minimum of 5)
        trades = [
            TradeRecord(
                trade_id=f"trade_{i}",
                account_id="test_account",
                symbol="EURUSD",
                entry_time=datetime.utcnow() - timedelta(days=i),
                exit_time=datetime.utcnow() - timedelta(days=i-1),
                entry_price=1.1000,
                exit_price=1.1010,
                position_size=10000,
                pnl=10.0,
                pnl_pips=10.0,
                commission=2.0,
                slippage=0.5,
                trade_type="long",
                exit_reason="take_profit",
                signal_confidence=0.75,
                market_regime=MarketRegime.TRENDING
            )
            for i in range(3)
        ]
        
        periods = calculator.calculate_rolling_performance("test_account", trades)
        assert len(periods) == 0  # Should return empty due to insufficient trades
    
    def test_drawdown_calculation(self, calculator, sample_trades):
        """Test drawdown calculation accuracy"""
        performance = calculator.calculate_current_performance("test_account", sample_trades)
        
        # Calculate expected max drawdown manually
        cumulative_pnl = []
        running_total = 0.0
        
        for trade in sorted(sample_trades, key=lambda t: t.exit_time):
            running_total += trade.pnl
            cumulative_pnl.append(running_total)
        
        peak = cumulative_pnl[0]
        expected_max_dd = 0.0
        
        for pnl in cumulative_pnl:
            if pnl > peak:
                peak = pnl
            if peak != 0:
                drawdown = (peak - pnl) / abs(peak)
                expected_max_dd = max(expected_max_dd, drawdown)
        
        assert abs(performance.max_drawdown - expected_max_dd) < 0.01
    
    def test_sharpe_ratio_calculation(self, calculator, sample_trades):
        """Test Sharpe ratio calculation"""
        performance = calculator.calculate_current_performance("test_account", sample_trades)
        
        # Sharpe ratio should be reasonable for profitable strategy
        if performance.total_trades > 1:
            assert -3 <= performance.sharpe_ratio <= 5  # Reasonable bounds
    
    def test_performance_comparison(self, calculator, sample_trades):
        """Test performance comparison functionality"""
        periods = calculator.calculate_rolling_performance("test_account", sample_trades)
        
        if len(periods) >= 2:
            current_period = periods[0]
            historical_periods = periods[1:]
            
            comparison = calculator.get_performance_comparison(current_period, historical_periods)
            
            assert "sharpe_ratio_delta" in comparison
            assert "win_rate_delta" in comparison
            assert "sharpe_ratio_improvement" in comparison
    
    def test_market_regime_determination(self, calculator, sample_trades):
        """Test market regime determination"""
        performance = calculator.calculate_current_performance("test_account", sample_trades)
        
        assert performance.market_regime in [MarketRegime.TRENDING, MarketRegime.RANGING, MarketRegime.UNKNOWN]
    
    def test_cache_functionality(self, calculator):
        """Test cache clearing functionality"""
        calculator.cache["test"] = "value"
        calculator.clear_cache()
        assert len(calculator.cache) == 0
    
    def test_risk_metrics_calculation(self, calculator, sample_trades):
        """Test risk metrics calculation"""
        performance = calculator.calculate_current_performance("test_account", sample_trades)
        
        assert performance.var_95 is not None
        assert performance.expected_shortfall is not None
        assert performance.volatility >= 0
    
    @pytest.mark.parametrize("window_days", [7, 14, 30, 60])
    def test_different_window_sizes(self, window_days, sample_trades):
        """Test calculator with different window sizes"""
        calculator = RollingPerformanceCalculator(rolling_window_days=window_days)
        performance = calculator.calculate_current_performance("test_account", sample_trades)
        
        assert performance.account_id == "test_account"
        assert (performance.period_end - performance.period_start).days == window_days
    
    def test_edge_cases(self, calculator):
        """Test edge cases and error handling"""
        # Test with None trades
        with pytest.raises(Exception):
            calculator.calculate_current_performance("test_account", None)
        
        # Test with trades having zero position size
        zero_trades = [
            TradeRecord(
                trade_id="zero_trade",
                account_id="test_account",
                symbol="EURUSD",
                entry_time=datetime.utcnow(),
                exit_time=datetime.utcnow(),
                entry_price=1.1000,
                exit_price=1.1010,
                position_size=0,  # Zero position size
                pnl=0,
                pnl_pips=0,
                commission=0,
                slippage=0,
                trade_type="long",
                exit_reason="manual",
                signal_confidence=0.75,
                market_regime=MarketRegime.UNKNOWN
            )
        ]
        
        performance = calculator.calculate_current_performance("test_account", zero_trades)
        assert performance.total_trades == 1
        assert performance.avg_win == 0
        assert performance.avg_loss == 0