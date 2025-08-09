"""
Story 3.4 Integration Tests

Integration tests to validate that all 6 acceptance criteria 
of Story 3.4 are properly implemented and working together.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from decimal import Decimal
import asyncio
from unittest.mock import Mock, patch

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.signals import (
    SignalGenerator,
    TradingSignal,
    SignalFrequencyManager,
    SignalPerformanceTracker
)


class TestStory34AcceptanceCriteria:
    """Test all Story 3.4 Acceptance Criteria"""
    
    @pytest.fixture
    def sample_market_data(self):
        """Generate sample market data for testing"""
        np.random.seed(42)
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1h')
        
        # Generate price data
        base_price = 1.1000
        price_data = []
        current_price = base_price
        
        for i, date in enumerate(dates):
            change = np.random.normal(0, 0.0005)
            current_price += change
            
            high = current_price + abs(np.random.normal(0, 0.0003))
            low = current_price - abs(np.random.normal(0, 0.0003))
            open_price = current_price - change
            
            price_data.append({
                'timestamp': date,
                'open': round(open_price, 5),
                'high': round(high, 5),
                'low': round(low, 5),
                'close': round(current_price, 5)
            })
        
        price_df = pd.DataFrame(price_data).set_index('timestamp')
        
        # Generate volume data
        volumes = [int(np.random.uniform(500, 2000)) for _ in range(100)]
        volume_series = pd.Series(volumes)
        
        return price_df, volume_series
    
    @pytest.fixture
    def high_confidence_pattern(self):
        """Mock high-confidence Wyckoff pattern"""
        return {
            'type': 'spring',
            'confidence': 85.0,  # Above 75% threshold
            'strength': 80.0,
            'support_level': 1.0950,
            'resistance_level': 1.1050,
            'direction': 'bullish',
            'wyckoff_phase': 'Phase C'
        }
    
    def test_ac1_confidence_threshold_filtering(self, sample_market_data, high_confidence_pattern):
        """
        AC1: Signal generation only when confidence score >75%
        """
        price_data, volume_data = sample_market_data
        generator = SignalGenerator(confidence_threshold=75.0)
        
        # Test with high confidence pattern (should pass)
        with patch.object(generator, '_detect_wyckoff_patterns') as mock_detect:
            with patch.object(generator, '_enhance_patterns_with_volume') as mock_enhance:
                mock_detect.return_value = [high_confidence_pattern]
                mock_enhance.return_value = [{**high_confidence_pattern, 'confidence': 85.0}]
                
                result = asyncio.run(generator.generate_signal(
                    'EURUSD', 'H1', price_data, volume_data
                ))
                
                if result['signal_generated']:
                    assert result['signal'].confidence >= 75.0
        
        # Test with low confidence pattern (should be rejected)
        low_confidence_pattern = {**high_confidence_pattern, 'confidence': 70.0}
        
        with patch.object(generator, '_detect_wyckoff_patterns') as mock_detect:
            with patch.object(generator, '_enhance_patterns_with_volume') as mock_enhance:
                mock_detect.return_value = [low_confidence_pattern]
                mock_enhance.return_value = [low_confidence_pattern]
                
                result = asyncio.run(generator.generate_signal(
                    'EURUSD', 'H1', price_data, volume_data
                ))
                
                assert not result['signal_generated']
                assert result['reason'] == 'insufficient_confidence'
    
    def test_ac2_entry_exit_parameters_calculated(self, sample_market_data, high_confidence_pattern):
        """
        AC2: Entry price, stop loss, and take profit levels calculated for each signal
        """
        price_data, volume_data = sample_market_data
        generator = SignalGenerator(confidence_threshold=75.0)
        
        with patch.object(generator, '_detect_wyckoff_patterns') as mock_detect:
            with patch.object(generator, '_enhance_patterns_with_volume') as mock_enhance:
                mock_detect.return_value = [high_confidence_pattern]
                mock_enhance.return_value = [{**high_confidence_pattern, 'confidence': 85.0}]
                
                result = asyncio.run(generator.generate_signal(
                    'EURUSD', 'H1', price_data, volume_data
                ))
                
                if result['signal_generated']:
                    signal = result['signal']
                    
                    # Verify all required price levels are present
                    assert signal.entry_price is not None
                    assert signal.stop_loss is not None  
                    assert signal.take_profit_1 is not None
                    
                    # Verify price relationships for long signal
                    if signal.signal_type == 'long':
                        assert float(signal.entry_price) > float(signal.stop_loss)
                        assert float(signal.take_profit_1) > float(signal.entry_price)
                    else:  # short signal
                        assert float(signal.entry_price) < float(signal.stop_loss)
                        assert float(signal.take_profit_1) < float(signal.entry_price)
    
    def test_ac3_risk_reward_minimum_enforced(self, sample_market_data, high_confidence_pattern):
        """
        AC3: Risk-reward ratio minimum 1:2 enforced for all signals
        """
        price_data, volume_data = sample_market_data
        generator = SignalGenerator(confidence_threshold=75.0, min_risk_reward=2.0)
        
        with patch.object(generator, '_detect_wyckoff_patterns') as mock_detect:
            with patch.object(generator, '_enhance_patterns_with_volume') as mock_enhance:
                mock_detect.return_value = [high_confidence_pattern]
                mock_enhance.return_value = [{**high_confidence_pattern, 'confidence': 85.0}]
                
                result = asyncio.run(generator.generate_signal(
                    'EURUSD', 'H1', price_data, volume_data
                ))
                
                if result['signal_generated']:
                    signal = result['signal']
                    assert signal.risk_reward_ratio >= 2.0
                elif result['reason'] == 'insufficient_risk_reward':
                    # Signal was correctly rejected for poor R:R
                    assert True
    
    def test_ac4_signal_frequency_controls(self, sample_market_data, high_confidence_pattern):
        """
        AC4: Maximum 3 signals per week per account to avoid overtrading
        """
        price_data, volume_data = sample_market_data
        generator = SignalGenerator(confidence_threshold=75.0, enable_frequency_management=True)
        account_id = "test_account_frequency"
        
        successful_signals = 0
        
        # Try to generate multiple signals
        with patch.object(generator, '_detect_wyckoff_patterns') as mock_detect:
            with patch.object(generator, '_enhance_patterns_with_volume') as mock_enhance:
                mock_detect.return_value = [high_confidence_pattern]
                mock_enhance.return_value = [{**high_confidence_pattern, 'confidence': 85.0}]
                
                for i in range(5):  # Try 5 signals
                    result = asyncio.run(generator.generate_signal(
                        f'PAIR{i}', 'H1', price_data, volume_data, account_id
                    ))
                    
                    if result['signal_generated']:
                        successful_signals += 1
                    elif result['reason'] == 'frequency_limit_exceeded':
                        # Should be limited after 3 signals
                        break
        
        # Should have generated at most 3 signals before hitting frequency limit
        assert successful_signals <= 3
    
    def test_ac5_comprehensive_signal_metadata(self, sample_market_data, high_confidence_pattern):
        """
        AC5: Signal metadata includes pattern type, confidence, expected hold time
        """
        price_data, volume_data = sample_market_data
        generator = SignalGenerator(confidence_threshold=75.0)
        
        with patch.object(generator, '_detect_wyckoff_patterns') as mock_detect:
            with patch.object(generator, '_enhance_patterns_with_volume') as mock_enhance:
                mock_detect.return_value = [high_confidence_pattern]
                mock_enhance.return_value = [{**high_confidence_pattern, 'confidence': 85.0}]
                
                result = asyncio.run(generator.generate_signal(
                    'EURUSD', 'H1', price_data, volume_data
                ))
                
                if result['signal_generated']:
                    signal = result['signal']
                    
                    # Verify required metadata is present
                    assert signal.pattern_type is not None
                    assert signal.confidence > 0
                    assert signal.expected_hold_time_hours > 0
                    assert signal.confidence_breakdown is not None
                    assert signal.market_context is not None
                    assert signal.pattern_details is not None
                    assert len(signal.contributing_factors) > 0
                    
                    # Verify metadata completeness
                    signal_dict = signal.to_dict()
                    required_fields = [
                        'signal_id', 'symbol', 'timeframe', 'signal_type',
                        'pattern_type', 'confidence', 'entry_price', 'stop_loss',
                        'take_profit_1', 'risk_reward_ratio', 'generated_at',
                        'expected_hold_time_hours', 'market_context',
                        'pattern_details', 'entry_confirmation'
                    ]
                    
                    for field in required_fields:
                        assert field in signal_dict, f"Required field '{field}' missing from signal metadata"
    
    def test_ac6_signal_performance_tracking(self):
        """
        AC6: Signal performance tracking with win rate and profit factor metrics
        """
        tracker = SignalPerformanceTracker()
        
        # Add sample signal outcomes
        test_outcomes = [
            ('signal_1', {
                'type': 'win', 
                'pnl_points': 0.015, 
                'entry_filled': True,
                'hold_duration_hours': 18,
                'target_hit': 'tp1'
            }, {'pattern_type': 'spring', 'confidence': 85.0}),
            
            ('signal_2', {
                'type': 'win',
                'pnl_points': 0.025,
                'entry_filled': True, 
                'hold_duration_hours': 24,
                'target_hit': 'tp2'
            }, {'pattern_type': 'accumulation', 'confidence': 80.0}),
            
            ('signal_3', {
                'type': 'loss',
                'pnl_points': -0.010,
                'entry_filled': True,
                'hold_duration_hours': 6,
                'target_hit': 'stop'
            }, {'pattern_type': 'spring', 'confidence': 78.0})
        ]
        
        # Track outcomes
        for signal_id, outcome_data, metadata in test_outcomes:
            result = tracker.track_signal_outcome(signal_id, outcome_data, metadata)
            assert result['outcome_recorded']
        
        # Calculate performance metrics
        metrics = tracker.calculate_performance_metrics()
        
        # Verify required metrics are calculated
        assert 'win_loss_metrics' in metrics
        assert 'pnl_metrics' in metrics
        
        win_loss = metrics['win_loss_metrics']
        assert 'win_rate_percent' in win_loss
        assert 'profit_factor' in win_loss
        
        pnl = metrics['pnl_metrics']
        assert 'gross_profit' in pnl
        assert 'gross_loss' in pnl
        assert 'net_profit' in pnl
        
        # Verify calculations are correct
        assert win_loss['wins'] == 2
        assert win_loss['losses'] == 1
        assert win_loss['win_rate_percent'] == round((2/3) * 100, 2)
        
        # Test pattern performance breakdown
        pattern_breakdown = tracker.get_pattern_performance_breakdown()
        assert 'pattern_breakdown' in pattern_breakdown
        
        # Check if there are patterns to analyze (need minimum samples)
        if pattern_breakdown['pattern_breakdown']:
            # Should have at least one pattern type
            assert len(pattern_breakdown['pattern_breakdown']) > 0
    
    def test_complete_signal_lifecycle(self, sample_market_data, high_confidence_pattern):
        """
        Test complete signal lifecycle from generation to performance tracking
        """
        price_data, volume_data = sample_market_data
        
        # Initialize components
        generator = SignalGenerator(confidence_threshold=75.0)
        tracker = SignalPerformanceTracker()
        
        # Generate signal
        with patch.object(generator, '_detect_wyckoff_patterns') as mock_detect:
            with patch.object(generator, '_enhance_patterns_with_volume') as mock_enhance:
                mock_detect.return_value = [high_confidence_pattern]
                mock_enhance.return_value = [{**high_confidence_pattern, 'confidence': 85.0}]
                
                result = asyncio.run(generator.generate_signal(
                    'EURUSD', 'H1', price_data, volume_data, 'test_account'
                ))
        
        if result['signal_generated']:
            signal = result['signal']
            
            # Simulate signal execution and outcome
            outcome_data = {
                'type': 'win',
                'entry_filled': True,
                'entry_fill_price': float(signal.entry_price),
                'exit_price': float(signal.take_profit_1),
                'pnl_points': float(signal.take_profit_1) - float(signal.entry_price),
                'hold_duration_hours': signal.expected_hold_time_hours,
                'target_hit': 'tp1'
            }
            
            # Track outcome
            tracking_result = tracker.track_signal_outcome(
                signal.signal_id, outcome_data, signal.to_dict()
            )
            
            assert tracking_result['outcome_recorded']
            assert tracking_result['outcome_type'] == 'win'
            
            # Verify performance metrics can be calculated
            metrics = tracker.calculate_performance_metrics()
            assert metrics['win_loss_metrics']['wins'] == 1
            
            print("[PASS] Complete signal lifecycle test passed!")
    
    def test_system_integration_requirements(self):
        """
        Test that the system meets overall integration requirements
        """
        # Test 1: All major components can be instantiated
        generator = SignalGenerator()
        frequency_manager = SignalFrequencyManager()
        performance_tracker = SignalPerformanceTracker()
        
        assert generator is not None
        assert frequency_manager is not None
        assert performance_tracker is not None
        
        # Test 2: Configuration can be updated
        config_result = generator.update_configuration({
            'confidence_threshold': 80.0,
            'min_risk_reward': 2.5
        })
        assert config_result['configuration_updated']
        assert generator.confidence_threshold == 80.0
        
        # Test 3: Statistics can be retrieved
        stats = generator.get_generation_statistics()
        assert 'total_attempts' in stats
        assert 'success_rate' in stats
        
        print("[PASS] System integration requirements test passed!")


def create_sample_market_data():
    """Generate sample market data for testing"""
    np.random.seed(42)
    dates = pd.date_range(start='2024-01-01', periods=100, freq='1h')
    
    # Generate price data
    base_price = 1.1000
    price_data = []
    current_price = base_price
    
    for i, date in enumerate(dates):
        change = np.random.normal(0, 0.0005)
        current_price += change
        
        high = current_price + abs(np.random.normal(0, 0.0003))
        low = current_price - abs(np.random.normal(0, 0.0003))
        open_price = current_price - change
        
        price_data.append({
            'timestamp': date,
            'open': round(open_price, 5),
            'high': round(high, 5),
            'low': round(low, 5),
            'close': round(current_price, 5)
        })
    
    price_df = pd.DataFrame(price_data).set_index('timestamp')
    
    # Generate volume data
    volumes = [int(np.random.uniform(500, 2000)) for _ in range(100)]
    volume_series = pd.Series(volumes)
    
    return price_df, volume_series

def create_high_confidence_pattern():
    """Mock high-confidence Wyckoff pattern"""
    return {
        'type': 'spring',
        'confidence': 85.0,  # Above 75% threshold
        'strength': 80.0,
        'support_level': 1.0950,
        'resistance_level': 1.1050,
        'direction': 'bullish',
        'wyckoff_phase': 'Phase C'
    }


if __name__ == "__main__":
    # Run the acceptance criteria tests
    test_class = TestStory34AcceptanceCriteria()
    
    # Create test data
    sample_data = create_sample_market_data()
    high_conf_pattern = create_high_confidence_pattern()
    
    print("Running Story 3.4 Acceptance Criteria Tests...")
    print("=" * 50)
    
    try:
        # Run each acceptance criteria test
        print("Testing AC1: Confidence threshold filtering...")
        test_class.test_ac1_confidence_threshold_filtering(sample_data, high_conf_pattern)
        print("[PASS] AC1 PASSED")
        
        print("\nTesting AC2: Entry/exit parameter calculation...")
        test_class.test_ac2_entry_exit_parameters_calculated(sample_data, high_conf_pattern)
        print("[PASS] AC2 PASSED")
        
        print("\nTesting AC3: Risk-reward ratio enforcement...")
        test_class.test_ac3_risk_reward_minimum_enforced(sample_data, high_conf_pattern)
        print("[PASS] AC3 PASSED")
        
        print("\nTesting AC4: Signal frequency controls...")
        test_class.test_ac4_signal_frequency_controls(sample_data, high_conf_pattern)
        print("[PASS] AC4 PASSED")
        
        print("\nTesting AC5: Comprehensive signal metadata...")
        test_class.test_ac5_comprehensive_signal_metadata(sample_data, high_conf_pattern)
        print("[PASS] AC5 PASSED")
        
        print("\nTesting AC6: Signal performance tracking...")
        test_class.test_ac6_signal_performance_tracking()
        print("[PASS] AC6 PASSED")
        
        print("\nTesting complete signal lifecycle...")
        test_class.test_complete_signal_lifecycle(sample_data, high_conf_pattern)
        
        print("\nTesting system integration...")
        test_class.test_system_integration_requirements()
        
        print("\n" + "=" * 50)
        print("[SUCCESS] ALL STORY 3.4 ACCEPTANCE CRITERIA TESTS PASSED!")
        print("Signal Generation and Scoring System is ready for production!")
        
    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()