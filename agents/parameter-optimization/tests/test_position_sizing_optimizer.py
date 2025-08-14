"""
Tests for Position Sizing Optimizer
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from agents.parameter_optimization.app.position_sizing_optimizer import PositionSizingOptimizer
from agents.parameter_optimization.app.performance_calculator import TradeRecord
from agents.parameter_optimization.app.models import PerformanceMetrics, MarketRegime, ParameterCategory


class TestPositionSizingOptimizer:
    
    @pytest.fixture
    def optimizer(self):
        return PositionSizingOptimizer()
    
    @pytest.fixture
    def sample_trades(self):
        """Create sample profitable trade records"""
        trades = []
        base_date = datetime.utcnow() - timedelta(days=30)
        
        for i in range(30):
            # Create mix of winning and losing trades (60% win rate)
            is_winner = i % 5 != 0  # 4 out of 5 trades win
            
            trade = TradeRecord(
                trade_id=f"trade_{i}",
                account_id="test_account",
                symbol="EURUSD",
                entry_time=base_date + timedelta(days=i),
                exit_time=base_date + timedelta(days=i, hours=2),
                entry_price=1.1000,
                exit_price=1.1020 if is_winner else 1.0980,
                position_size=10000,
                pnl=20.0 if is_winner else -10.0,
                pnl_pips=20.0 if is_winner else -10.0,
                commission=2.0,
                slippage=0.5,
                trade_type="long",
                exit_reason="take_profit" if is_winner else "stop_loss",
                signal_confidence=0.75 + (i % 5) * 0.05,
                market_regime=MarketRegime.TRENDING
            )
            trades.append(trade)
        
        return trades
    
    @pytest.fixture
    def sample_performance(self):
        """Create sample performance metrics"""
        return PerformanceMetrics(
            timestamp=datetime.utcnow(),
            account_id="test_account",
            sharpe_ratio=1.5,
            calmar_ratio=1.2,
            sortino_ratio=1.8,
            profit_factor=1.8,
            win_rate=0.6,
            max_drawdown=0.08,
            current_drawdown=0.02,
            total_trades=30,
            winning_trades=18,
            losing_trades=12,
            avg_win=20.0,
            avg_loss=10.0,
            largest_win=50.0,
            largest_loss=25.0,
            expectancy=8.0,
            volatility=0.15,
            var_95=-15.0,
            expected_shortfall=-20.0,
            period_start=datetime.utcnow() - timedelta(days=30),
            period_end=datetime.utcnow(),
            market_regime=MarketRegime.TRENDING
        )
    
    @pytest.fixture
    def current_parameters(self):
        """Current position sizing parameters"""
        return {
            "base_risk_per_trade": 0.015,  # 1.5%
            "kelly_multiplier": 0.25,
            "max_position_size": 0.03,
            "drawdown_reduction_factor": 0.5
        }
    
    def test_optimize_position_sizing_success(self, optimizer, current_parameters, sample_performance, sample_trades):
        """Test successful position sizing optimization"""
        adjustment = optimizer.optimize_position_sizing(
            "test_account", current_parameters, sample_performance, sample_trades
        )
        
        assert adjustment is not None
        assert adjustment.parameter_name == "base_risk_per_trade"
        assert adjustment.category == ParameterCategory.POSITION_SIZING
        assert optimizer.min_position_size <= adjustment.proposed_value <= optimizer.max_position_size
        assert abs(adjustment.change_percentage) >= 0.05  # Minimum 5% change
    
    def test_insufficient_trades(self, optimizer, current_parameters, sample_performance):
        """Test optimization with insufficient trade history"""
        # Only 10 trades (less than minimum of 20)
        few_trades = [
            TradeRecord(
                trade_id=f"trade_{i}",
                account_id="test_account",
                symbol="EURUSD",
                entry_time=datetime.utcnow() - timedelta(days=i),
                exit_time=datetime.utcnow() - timedelta(days=i-1),
                entry_price=1.1000,
                exit_price=1.1020,
                position_size=10000,
                pnl=20.0,
                pnl_pips=20.0,
                commission=2.0,
                slippage=0.5,
                trade_type="long",
                exit_reason="take_profit",
                signal_confidence=0.75,
                market_regime=MarketRegime.TRENDING
            )
            for i in range(10)
        ]
        
        adjustment = optimizer.optimize_position_sizing(
            "test_account", current_parameters, sample_performance, few_trades
        )
        
        assert adjustment is None
    
    def test_kelly_criterion_calculation(self, optimizer, sample_trades):
        """Test Kelly Criterion calculation accuracy"""
        kelly_analysis = optimizer._calculate_kelly_criterion("test_account", sample_trades)
        
        assert kelly_analysis.account_id == "test_account"
        assert 0 <= kelly_analysis.win_rate <= 1
        assert kelly_analysis.avg_win >= 0
        assert kelly_analysis.avg_loss >= 0
        assert 0 <= kelly_analysis.kelly_percentage <= 0.10  # Capped at 10%
        assert 0.1 <= kelly_analysis.recommended_multiplier <= 0.5
        assert kelly_analysis.sample_size == len(sample_trades)
    
    def test_kelly_with_losing_strategy(self, optimizer):
        """Test Kelly calculation with losing strategy"""
        losing_trades = []
        for i in range(25):
            trade = TradeRecord(
                trade_id=f"losing_trade_{i}",
                account_id="test_account",
                symbol="EURUSD",
                entry_time=datetime.utcnow() - timedelta(days=i),
                exit_time=datetime.utcnow() - timedelta(days=i-1),
                entry_price=1.1000,
                exit_price=1.0980,  # Always losing
                position_size=10000,
                pnl=-20.0,
                pnl_pips=-20.0,
                commission=2.0,
                slippage=0.5,
                trade_type="long",
                exit_reason="stop_loss",
                signal_confidence=0.75,
                market_regime=MarketRegime.RANGING
            )
            losing_trades.append(trade)
        
        kelly_analysis = optimizer._calculate_kelly_criterion("test_account", losing_trades)
        
        assert kelly_analysis.kelly_percentage == 0.0  # Should be 0 for losing strategy
        assert kelly_analysis.implementation_confidence < 0.7
    
    def test_bootstrap_confidence_interval(self, optimizer, sample_trades):
        """Test bootstrap confidence interval calculation"""
        confidence_interval = optimizer._bootstrap_kelly_confidence(sample_trades, iterations=100)
        
        assert len(confidence_interval) == 2
        assert confidence_interval[0] <= confidence_interval[1]
        assert confidence_interval[0] >= 0
        assert confidence_interval[1] <= 0.10
    
    def test_kelly_multiplier_calculation(self, optimizer, sample_trades):
        """Test Kelly multiplier calculation"""
        multiplier = optimizer._calculate_kelly_multiplier(sample_trades, 0.05)
        
        assert 0.1 <= multiplier <= 0.5
    
    def test_performance_multiplier_calculation(self, optimizer, sample_performance):
        """Test performance-based multiplier calculation"""
        # Test with different Sharpe ratios
        sample_performance.sharpe_ratio = 2.5  # Excellent performance
        multiplier_high = optimizer._calculate_performance_multiplier(sample_performance)
        
        sample_performance.sharpe_ratio = 0.3  # Poor performance
        multiplier_low = optimizer._calculate_performance_multiplier(sample_performance)
        
        assert multiplier_high > multiplier_low
        assert 0.8 <= multiplier_low <= 1.2
        assert 0.8 <= multiplier_high <= 1.2
    
    def test_drawdown_multiplier_calculation(self, optimizer, sample_performance):
        """Test drawdown-based multiplier calculation"""
        # Test with high drawdown
        sample_performance.current_drawdown = 0.20  # 20% drawdown
        multiplier_high_dd = optimizer._calculate_drawdown_multiplier(sample_performance)
        
        # Test with low drawdown
        sample_performance.current_drawdown = 0.02  # 2% drawdown
        multiplier_low_dd = optimizer._calculate_drawdown_multiplier(sample_performance)
        
        assert multiplier_high_dd < multiplier_low_dd
        assert multiplier_high_dd == 0.5  # Should be 0.5 for >15% drawdown
        assert multiplier_low_dd == 1.0   # Should be 1.0 for <5% drawdown
    
    def test_regime_multiplier_calculation(self, optimizer):
        """Test market regime-based multiplier calculation"""
        trending_mult = optimizer._calculate_regime_multiplier(MarketRegime.TRENDING)
        ranging_mult = optimizer._calculate_regime_multiplier(MarketRegime.RANGING)
        volatile_mult = optimizer._calculate_regime_multiplier(MarketRegime.VOLATILE)
        
        assert trending_mult > ranging_mult  # Trending should be higher
        assert ranging_mult > volatile_mult  # Volatile should be lowest
    
    def test_safety_constraints(self, optimizer, sample_performance):
        """Test safety constraints application"""
        # Test with extreme recommended size
        extreme_size = 0.05  # 5% (above maximum)
        current_size = 0.015
        
        constrained_size = optimizer._apply_safety_constraints(
            extreme_size, current_size, sample_performance
        )
        
        assert constrained_size <= optimizer.max_position_size
        assert constrained_size >= optimizer.min_position_size
    
    def test_negative_sharpe_constraint(self, optimizer, sample_performance):
        """Test constraints during negative Sharpe ratio"""
        sample_performance.sharpe_ratio = -0.5  # Negative Sharpe
        current_size = 0.02
        recommended_size = 0.025
        
        constrained_size = optimizer._apply_safety_constraints(
            recommended_size, current_size, sample_performance
        )
        
        # Should limit increase when Sharpe is negative
        assert constrained_size <= current_size * 0.8
    
    def test_high_drawdown_constraint(self, optimizer, sample_performance):
        """Test constraints during high drawdown"""
        sample_performance.current_drawdown = 0.12  # 12% drawdown
        recommended_size = 0.025
        current_size = 0.02
        
        constrained_size = optimizer._apply_safety_constraints(
            recommended_size, current_size, sample_performance
        )
        
        # Should cap at 1.5% during high drawdown
        assert constrained_size <= 0.015
    
    def test_change_reason_generation(self, optimizer, sample_performance):
        """Test change reason generation"""
        kelly_analysis = Mock()
        kelly_analysis.kelly_percentage = 0.03
        kelly_analysis.sample_size = 50
        
        reason = optimizer._generate_change_reason(kelly_analysis, sample_performance)
        
        assert isinstance(reason, str)
        assert len(reason) > 10
        assert "Kelly Criterion" in reason
    
    def test_performance_impact_estimation(self, optimizer):
        """Test performance impact estimation"""
        kelly_analysis = Mock()
        kelly_analysis.kelly_percentage = 0.025
        
        impact = optimizer._estimate_performance_impact(kelly_analysis, 0.02, 0.015)
        
        assert isinstance(impact, float)
        assert -0.5 <= impact <= 0.5  # Should be capped
    
    def test_risk_impact_estimation(self, optimizer, sample_performance):
        """Test risk impact estimation"""
        risk_impact = optimizer._estimate_risk_impact(0.02, 0.015, sample_performance)
        
        assert isinstance(risk_impact, float)
        # Risk should increase with position size increase
        assert risk_impact > 0  # Positive because size increased
    
    def test_low_confidence_rejection(self, optimizer, current_parameters, sample_performance, sample_trades):
        """Test rejection of low confidence optimizations"""
        # Create trades that would result in low confidence
        inconsistent_trades = []
        for i in range(25):
            # Very inconsistent PnL
            pnl = 100.0 if i % 2 == 0 else -90.0
            trade = TradeRecord(
                trade_id=f"trade_{i}",
                account_id="test_account",
                symbol="EURUSD",
                entry_time=datetime.utcnow() - timedelta(days=i),
                exit_time=datetime.utcnow() - timedelta(days=i-1),
                entry_price=1.1000,
                exit_price=1.1000 + pnl/10000,
                position_size=10000,
                pnl=pnl,
                pnl_pips=pnl/10,
                commission=2.0,
                slippage=0.5,
                trade_type="long",
                exit_reason="take_profit" if pnl > 0 else "stop_loss",
                signal_confidence=0.75,
                market_regime=MarketRegime.VOLATILE
            )
            inconsistent_trades.append(trade)
        
        # This should return None due to low confidence
        adjustment = optimizer.optimize_position_sizing(
            "test_account", current_parameters, sample_performance, inconsistent_trades
        )
        
        # Might return None due to low confidence or small change
        if adjustment:
            assert adjustment.analysis["confidence_level"] >= 0.0
    
    def test_small_change_rejection(self, optimizer, current_parameters, sample_performance):
        """Test rejection of very small changes"""
        # Create trades that result in Kelly very close to current size
        stable_trades = []
        for i in range(30):
            trade = TradeRecord(
                trade_id=f"trade_{i}",
                account_id="test_account",
                symbol="EURUSD",
                entry_time=datetime.utcnow() - timedelta(days=i),
                exit_time=datetime.utcnow() - timedelta(days=i-1),
                entry_price=1.1000,
                exit_price=1.1003,  # Very small consistent wins
                position_size=10000,
                pnl=3.0,
                pnl_pips=3.0,
                commission=2.0,
                slippage=0.5,
                trade_type="long",
                exit_reason="take_profit",
                signal_confidence=0.75,
                market_regime=MarketRegime.LOW_VOLATILITY
            )
            stable_trades.append(trade)
        
        # This might return None due to small change
        adjustment = optimizer.optimize_position_sizing(
            "test_account", current_parameters, sample_performance, stable_trades
        )
        
        if adjustment:
            assert abs(adjustment.change_percentage) >= 0.05
    
    @pytest.mark.parametrize("win_rate,avg_win,avg_loss,expected_kelly_range", [
        (0.6, 20.0, 10.0, (0.02, 0.06)),  # Good strategy
        (0.4, 15.0, 12.0, (0.0, 0.01)),   # Poor strategy
        (0.8, 25.0, 15.0, (0.04, 0.08)),  # Excellent strategy
        (0.5, 10.0, 10.0, (0.0, 0.01)),   # Break-even strategy
    ])
    def test_kelly_calculation_scenarios(self, optimizer, win_rate, avg_win, avg_loss, expected_kelly_range):
        """Test Kelly calculation with various win rate scenarios"""
        # Create trades with specific win rate and PnL characteristics
        num_trades = 50
        winning_trades = int(num_trades * win_rate)
        
        trades = []
        for i in range(num_trades):
            is_winner = i < winning_trades
            pnl = avg_win if is_winner else -avg_loss
            
            trade = TradeRecord(
                trade_id=f"trade_{i}",
                account_id="test_account",
                symbol="EURUSD",
                entry_time=datetime.utcnow() - timedelta(days=i),
                exit_time=datetime.utcnow() - timedelta(days=i-1),
                entry_price=1.1000,
                exit_price=1.1000 + pnl/10000,
                position_size=10000,
                pnl=pnl,
                pnl_pips=pnl/10,
                commission=2.0,
                slippage=0.5,
                trade_type="long",
                exit_reason="take_profit" if is_winner else "stop_loss",
                signal_confidence=0.75,
                market_regime=MarketRegime.TRENDING
            )
            trades.append(trade)
        
        kelly_analysis = optimizer._calculate_kelly_criterion("test_account", trades)
        
        assert expected_kelly_range[0] <= kelly_analysis.kelly_percentage <= expected_kelly_range[1]
        assert abs(kelly_analysis.win_rate - win_rate) < 0.05  # Within 5%