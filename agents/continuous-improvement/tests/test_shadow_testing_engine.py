"""
Tests for Shadow Testing Engine
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from shadow_testing_engine import ShadowTestingEngine
from models import (
    ImprovementTest, ShadowTestResults, PerformanceMetrics,
    TestGroup, Change, ImprovementType, ImplementationComplexity
)


class TestShadowTestingEngine:
    """Test suite for ShadowTestingEngine"""
    
    @pytest.fixture
    def shadow_engine(self):
        """Create shadow testing engine for testing"""
        return ShadowTestingEngine()
    
    @pytest.fixture
    def mock_test(self):
        """Create mock improvement test"""
        test = ImprovementTest(
            name="Shadow Test",
            description="Test for shadow testing",
            improvement_type=ImprovementType.PARAMETER_OPTIMIZATION
        )
        
        # Create treatment group with changes
        treatment_group = TestGroup(
            group_type="treatment",
            accounts=["ACC001", "ACC002"],
            allocation_percentage=Decimal('50')
        )
        
        change = Change(
            component="test_component",
            description="Test change",
            change_type="parameter",
            old_value="old",
            new_value="new"
        )
        treatment_group.changes = [change]
        test.treatment_group = treatment_group
        
        return test
    
    @pytest.mark.asyncio
    async def test_start_shadow_test_valid(self, shadow_engine, mock_test):
        """Test starting a valid shadow test"""
        result = await shadow_engine.start_shadow_test(mock_test)
        assert result is True
        assert mock_test.test_id in shadow_engine._active_shadow_tests
    
    @pytest.mark.asyncio
    async def test_start_shadow_test_invalid(self, shadow_engine):
        """Test starting an invalid shadow test"""
        invalid_test = ImprovementTest(
            name="Invalid Test",
            description="Test without treatment group"
        )
        
        result = await shadow_engine.start_shadow_test(invalid_test)
        assert result is False
        assert invalid_test.test_id not in shadow_engine._active_shadow_tests
    
    @pytest.mark.asyncio
    async def test_update_shadow_test(self, shadow_engine, mock_test):
        """Test updating a shadow test"""
        # Start the test first
        await shadow_engine.start_shadow_test(mock_test)
        
        # Update the test
        update_result = await shadow_engine.update_shadow_test(mock_test.test_id)
        
        assert update_result is not None
        assert 'test_id' in update_result
        assert 'signals_generated' in update_result
        assert 'trades_simulated' in update_result
    
    @pytest.mark.asyncio
    async def test_update_nonexistent_shadow_test(self, shadow_engine):
        """Test updating a non-existent shadow test"""
        result = await shadow_engine.update_shadow_test("nonexistent_id")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_evaluate_shadow_test(self, shadow_engine, mock_test):
        """Test evaluating a completed shadow test"""
        # Start and simulate some activity
        await shadow_engine.start_shadow_test(mock_test)
        
        # Simulate some test data
        shadow_data = shadow_engine._active_shadow_tests[mock_test.test_id]
        shadow_data['signals_generated'] = 100
        shadow_data['trades_simulated'] = 50
        shadow_data['start_time'] = datetime.utcnow() - timedelta(days=8)  # Make it old enough
        
        # Add some mock trades to the performance tracking
        shadow_data['environment']['performance_tracking']['trades'] = [
            {'pnl': 50, 'entry_time': datetime.utcnow()} for _ in range(50)
        ]
        
        results = await shadow_engine.evaluate_shadow_test(mock_test)
        
        assert isinstance(results, ShadowTestResults)
        assert results.test_id == mock_test.test_id
        assert results.trades_executed == 50
        assert results.total_signals == 100
    
    @pytest.mark.asyncio
    async def test_validate_shadow_test_config_valid(self, shadow_engine, mock_test):
        """Test shadow test configuration validation with valid config"""
        result = await shadow_engine._validate_shadow_test_config(mock_test)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_validate_shadow_test_config_no_treatment_group(self, shadow_engine):
        """Test shadow test config validation without treatment group"""
        test_without_treatment = ImprovementTest(
            name="No Treatment Test",
            description="Test without treatment group"
        )
        
        result = await shadow_engine._validate_shadow_test_config(test_without_treatment)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_validate_shadow_test_config_no_accounts(self, shadow_engine):
        """Test shadow test config validation without accounts"""
        test_no_accounts = ImprovementTest(
            name="No Accounts Test",
            description="Test without accounts"
        )
        test_no_accounts.treatment_group = TestGroup(
            group_type="treatment",
            accounts=[],  # Empty accounts
            changes=[Change()]
        )
        
        result = await shadow_engine._validate_shadow_test_config(test_no_accounts)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_can_shadow_test_change_valid(self, shadow_engine):
        """Test change validation for shadow testing"""
        valid_change = Change(
            change_type="parameter",
            component="test_component"
        )
        
        result = await shadow_engine._can_shadow_test_change(valid_change)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_can_shadow_test_change_invalid_type(self, shadow_engine):
        """Test change validation with invalid type"""
        invalid_change = Change(
            change_type="infrastructure",  # Not shadowable
            component="test_component"
        )
        
        result = await shadow_engine._can_shadow_test_change(invalid_change)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_can_shadow_test_change_external_api(self, shadow_engine):
        """Test change validation with external API dependency"""
        external_change = Change(
            change_type="parameter",
            component="test_component",
            system_impact="external_api integration required"
        )
        
        result = await shadow_engine._can_shadow_test_change(external_change)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_create_shadow_environment(self, shadow_engine, mock_test):
        """Test shadow environment creation"""
        environment = await shadow_engine._create_shadow_environment(mock_test)
        
        assert 'test_id' in environment
        assert 'accounts' in environment
        assert 'changes_applied' in environment
        assert 'performance_tracking' in environment
        assert environment['test_id'] == mock_test.test_id
    
    @pytest.mark.asyncio
    async def test_apply_parameter_change(self, shadow_engine):
        """Test applying parameter changes to shadow environment"""
        change = Change(
            change_type="parameter",
            component="test_component",
            configuration_changes={"param1": "value1", "param2": "value2"}
        )
        
        environment = {
            'strategy_config': {}
        }
        
        await shadow_engine._apply_parameter_change(change, environment)
        
        assert 'test_component' in environment['strategy_config']
        assert environment['strategy_config']['test_component']['param1'] == "value1"
        assert environment['strategy_config']['test_component']['param2'] == "value2"
    
    @pytest.mark.asyncio
    async def test_generate_shadow_signals(self, shadow_engine, mock_test):
        """Test shadow signal generation"""
        # Start the test first
        await shadow_engine.start_shadow_test(mock_test)
        
        # Mock market data
        market_data = {
            'EURUSD': {
                'price': 1.1234,
                'volume': 1000,
                'volatility': 0.015,
                'trend_strength': 0.8,
                'regime_type': 'trending',
                'regime_confidence': 0.9,
                'timestamp': datetime.utcnow()
            }
        }
        
        signals = await shadow_engine._generate_shadow_signals(mock_test, market_data)
        
        assert isinstance(signals, list)
        # Signals may or may not be generated depending on probability
        if signals:
            signal = signals[0]
            assert 'signal_id' in signal
            assert 'test_id' in signal
            assert 'symbol' in signal
            assert signal['test_id'] == mock_test.test_id
    
    @pytest.mark.asyncio
    async def test_simulate_trades(self, shadow_engine):
        """Test trade simulation"""
        signals = [
            {
                'signal_id': 'SIG_001',
                'test_id': 'TEST_001',
                'symbol': 'EURUSD',
                'direction': 'buy',
                'price': 1.1234,
                'market_conditions': {'volatility': 0.015}
            }
        ]
        
        market_data = {
            'EURUSD': {
                'price': 1.1234,
                'volatility': 0.015
            }
        }
        
        trades = await shadow_engine._simulate_trades(signals, market_data)
        
        assert isinstance(trades, list)
        if trades:  # Trade simulation might not always produce trades
            trade = trades[0]
            assert 'trade_id' in trade
            assert 'symbol' in trade
            assert 'pnl' in trade
    
    @pytest.mark.asyncio
    async def test_calculate_signal_probability(self, shadow_engine, mock_test):
        """Test signal probability calculation"""
        # Start test to get environment
        await shadow_engine.start_shadow_test(mock_test)
        environment = shadow_engine._active_shadow_tests[mock_test.test_id]['environment']
        
        market_data = {
            'volatility': 0.02,
            'trend_strength': 0.8,
            'regime_type': 'trending'
        }
        
        probability = await shadow_engine._calculate_signal_probability(
            mock_test, 'EURUSD', market_data, environment
        )
        
        assert 0.0 <= probability <= 1.0
    
    def test_determine_signal_type(self, shadow_engine):
        """Test signal type determination"""
        # Test trend following
        market_data = {'volatility': 0.01, 'trend_strength': 0.02, 'regime_type': 'trending'}
        signal_type = shadow_engine._determine_signal_type(market_data, {})
        assert signal_type == 'trend_following'
        
        # Test volatility breakout
        market_data = {'volatility': 0.03, 'trend_strength': 0.01, 'regime_type': 'trending'}
        signal_type = shadow_engine._determine_signal_type(market_data, {})
        assert signal_type == 'volatility_breakout'
        
        # Test mean reversion
        market_data = {'volatility': 0.01, 'trend_strength': 0.01, 'regime_type': 'ranging'}
        signal_type = shadow_engine._determine_signal_type(market_data, {})
        assert signal_type == 'mean_reversion'
    
    @pytest.mark.asyncio
    async def test_check_shadow_completion_insufficient_duration(self, shadow_engine, mock_test):
        """Test shadow completion check with insufficient duration"""
        await shadow_engine.start_shadow_test(mock_test)
        
        # Set recent start time
        shadow_engine._active_shadow_tests[mock_test.test_id]['start_time'] = datetime.utcnow()
        
        completion_status = await shadow_engine._check_shadow_completion(mock_test.test_id)
        assert completion_status == 'insufficient_duration'
    
    @pytest.mark.asyncio
    async def test_check_shadow_completion_insufficient_signals(self, shadow_engine, mock_test):
        """Test shadow completion check with insufficient signals"""
        await shadow_engine.start_shadow_test(mock_test)
        
        # Set old start time but insufficient signals
        shadow_engine._active_shadow_tests[mock_test.test_id]['start_time'] = datetime.utcnow() - timedelta(days=8)
        shadow_engine._active_shadow_tests[mock_test.test_id]['signals_generated'] = 10  # Below minimum
        
        completion_status = await shadow_engine._check_shadow_completion(mock_test.test_id)
        assert completion_status == 'insufficient_signals'
    
    @pytest.mark.asyncio
    async def test_check_shadow_completion_complete(self, shadow_engine, mock_test):
        """Test shadow completion check with sufficient criteria"""
        await shadow_engine.start_shadow_test(mock_test)
        
        # Set sufficient criteria
        shadow_test = shadow_engine._active_shadow_tests[mock_test.test_id]
        shadow_test['start_time'] = datetime.utcnow() - timedelta(days=8)
        shadow_test['signals_generated'] = 100  # Above minimum
        shadow_test['trades_simulated'] = 50   # Above minimum
        
        completion_status = await shadow_engine._check_shadow_completion(mock_test.test_id)
        assert completion_status == 'complete'
    
    @pytest.mark.asyncio
    async def test_get_active_shadow_tests(self, shadow_engine, mock_test):
        """Test getting active shadow tests"""
        await shadow_engine.start_shadow_test(mock_test)
        
        active_tests = await shadow_engine.get_active_shadow_tests()
        
        assert len(active_tests) == 1
        assert active_tests[0]['test_id'] == mock_test.test_id
    
    @pytest.mark.asyncio
    async def test_get_shadow_test_status(self, shadow_engine, mock_test):
        """Test getting shadow test status"""
        await shadow_engine.start_shadow_test(mock_test)
        
        status = await shadow_engine.get_shadow_test_status(mock_test.test_id)
        
        assert status is not None
        assert status['test_id'] == mock_test.test_id
        assert 'start_time' in status
        assert 'duration' in status
        assert 'completion_status' in status
    
    @pytest.mark.asyncio
    async def test_stop_shadow_test(self, shadow_engine, mock_test):
        """Test stopping a shadow test"""
        await shadow_engine.start_shadow_test(mock_test)
        
        result = await shadow_engine.stop_shadow_test(mock_test.test_id, "Manual stop for testing")
        
        assert result is True
        shadow_data = shadow_engine._active_shadow_tests[mock_test.test_id]
        assert "stopped: Manual stop for testing" in shadow_data['validation_status']


@pytest.mark.asyncio
async def test_shadow_testing_integration():
    """Integration test for complete shadow testing workflow"""
    engine = ShadowTestingEngine()
    
    # Create test with proper structure
    test = ImprovementTest(
        name="Integration Test",
        description="Full shadow testing integration test",
        improvement_type=ImprovementType.PARAMETER_OPTIMIZATION
    )
    
    # Add treatment group with changes
    treatment_group = TestGroup(
        group_type="treatment",
        accounts=["ACC001", "ACC002", "ACC003"],
        allocation_percentage=Decimal('50')
    )
    
    change = Change(
        component="entry_criteria",
        description="Optimize entry timing",
        change_type="parameter",
        configuration_changes={"threshold": 0.85, "lookback": 20}
    )
    treatment_group.changes = [change]
    test.treatment_group = treatment_group
    
    # Start shadow test
    result = await engine.start_shadow_test(test)
    assert result is True
    
    # Simulate some updates
    for i in range(3):
        update_result = await engine.update_shadow_test(test.test_id)
        assert update_result is not None
    
    # Check status
    status = await engine.get_shadow_test_status(test.test_id)
    assert status is not None
    assert status['signals_generated'] >= 0
    assert status['trades_simulated'] >= 0
    
    # Stop the test
    stop_result = await engine.stop_shadow_test(test.test_id, "Integration test complete")
    assert stop_result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])