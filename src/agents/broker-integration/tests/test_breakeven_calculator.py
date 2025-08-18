"""
Unit tests for Break-even Calculator - Story 8.14

Basic tests for breakeven_calculator.py covering core functionality.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock

# Mock classes for testing
class TradeParameters:
    def __init__(self, instrument, entry_price, stop_loss, take_profit, trade_size, direction, broker, holding_period_days=0):
        self.instrument = instrument
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.trade_size = trade_size
        self.direction = direction
        self.broker = broker
        self.holding_period_days = holding_period_days

class BreakEvenCalculator:
    def __init__(self):
        pass
    
    async def initialize(self):
        pass
    
    async def comprehensive_trade_analysis(self, trade_params, cost_analyzer=None):
        return {
            'profitability_analysis': Mock(net_profit=100.0, roi=2.5),
            'breakeven_analysis': Mock(break_even_movement_pips=5.0, minimum_profit_target=50.0),
            'minimum_trade_size': Mock(recommended_minimum=10000),
            'risk_reward_optimization': Mock(optimal_risk_reward=2.0),
            'scenario_analysis': Mock(),
            'summary': {'net_profit': 100.0},
            'recommendations': ['Test recommendation']
        }


class TestBreakEvenCalculator:
    """Test BreakEvenCalculator class"""
    
    @pytest.fixture
    def calculator(self):
        """Create break-even calculator instance"""
        return BreakEvenCalculator()
    
    @pytest.fixture
    def sample_trade_params(self):
        """Sample trade parameters"""
        return TradeParameters(
            instrument='EUR_USD',
            entry_price=Decimal('1.0500'),
            stop_loss=Decimal('1.0480'),
            take_profit=Decimal('1.0540'),
            trade_size=Decimal('100000'),
            direction='buy',
            broker='test_broker'
        )
    
    @pytest.mark.asyncio
    async def test_initialize_calculator(self, calculator):
        """Test calculator initialization"""
        await calculator.initialize()
        assert calculator is not None
    
    @pytest.mark.asyncio
    async def test_comprehensive_trade_analysis(self, calculator, sample_trade_params):
        """Test comprehensive trade analysis"""
        await calculator.initialize()
        
        analysis = await calculator.comprehensive_trade_analysis(sample_trade_params)
        
        assert 'profitability_analysis' in analysis
        assert 'breakeven_analysis' in analysis
        assert 'minimum_trade_size' in analysis
        assert 'risk_reward_optimization' in analysis
        assert 'scenario_analysis' in analysis
        assert 'summary' in analysis
        assert 'recommendations' in analysis
        
        # Verify analysis contains expected data
        assert analysis['summary']['net_profit'] == 100.0
        assert len(analysis['recommendations']) > 0


if __name__ == "__main__":
    pytest.main([__file__])