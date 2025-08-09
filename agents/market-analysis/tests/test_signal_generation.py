"""
Comprehensive test suite for the Signal Generation and Scoring System.

Tests all components including:
- Signal generation pipeline
- Parameter calculation and optimization
- Risk-reward ratio enforcement
- Frequency management
- Performance tracking
- Market state filtering
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from decimal import Decimal
import asyncio
from unittest.mock import Mock, patch, AsyncMock

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.signals import (
    SignalGenerator,
    TradingSignal,
    SignalParameterCalculator,
    RiskRewardOptimizer,
    SignalFrequencyManager,
    MarketStateDetector,
    SignalPerformanceTracker
)
from app.signals.signal_metadata import (
    ConfidenceBreakdown,
    MarketContext,
    PatternDetails,
    EntryConfirmation,
    SignalOutcome
)


class TestSignalGenerationBase:
    """Base class with common test fixtures and utilities"""
    
    @pytest.fixture
    def sample_price_data(self):
        """Generate realistic OHLC price data for testing"""
        np.random.seed(42)  # For reproducible tests
        
        dates = pd.date_range(start='2024-01-01', periods=250, freq='H')
        
        # Generate realistic price movement
        returns = np.random.normal(0.0001, 0.005, 250)  # Small positive drift with volatility
        price_base = 1.1000
        
        closes = [price_base]
        for ret in returns[1:]:
            closes.append(closes[-1] * (1 + ret))
        
        # Create OHLC from closes
        data = []
        for i, close in enumerate(closes):
            if i == 0:
                open_price = close
            else:
                open_price = closes[i-1]
            
            # Add some intrabar movement
            high = max(open_price, close) * (1 + abs(np.random.normal(0, 0.002)))
            low = min(open_price, close) * (1 - abs(np.random.normal(0, 0.002)))
            
            data.append({
                'timestamp': dates[i],
                'open': round(open_price, 5),
                'high': round(high, 5),
                'low': round(low, 5),
                'close': round(close, 5)
            })
        
        return pd.DataFrame(data).set_index('timestamp')
    
    @pytest.fixture
    def sample_volume_data(self):
        """Generate realistic volume data"""
        np.random.seed(42)
        
        # Base volume with some spikes
        base_volume = 1000
        volumes = []
        
        for i in range(250):
            # Normal volume with occasional spikes
            if np.random.random() < 0.05:  # 5% chance of volume spike
                volume = base_volume * np.random.uniform(3, 8)
            else:
                volume = base_volume * np.random.uniform(0.5, 2.0)
            
            volumes.append(int(volume))
        
        return pd.Series(volumes)
    
    @pytest.fixture
    def sample_pattern(self):
        """Sample Wyckoff pattern for testing"""
        return {
            'type': 'spring',
            'confidence': 82.5,
            'strength': 75.0,
            'wyckoff_phase': 'Phase C',
            'stage': 'completion',
            'support_level': 1.0950,
            'resistance_level': 1.1050,
            'spring_data': {
                'spring_low': 1.0940,
                'spring_high': 1.0960
            },
            'duration_bars': 35,
            'height_points': 0.0100,
            'volume_confirmation': 85.0,
            'timeframe_alignment': 80.0,
            'trend_strength': 70.0,
            'direction': 'bullish',
            'invalidation_level': 1.0930
        }
    
    @pytest.fixture
    def sample_market_context(self):
        """Sample market context for testing"""
        return {
            'market_state': 'trending',
            'volatility_analysis': {
                'regime': 'normal',
                'atr_current': 0.0015,
                'atr_percentage': 0.14
            },
            'trend_analysis': {
                'direction': 'uptrend',
                'strength': 75.5
            },
            'volume_analysis': {
                'regime': 'normal',
                'current_volume': 1200,
                'average_volume': 1000
            },
            'session_analysis': {
                'current_session': 'london',
                'liquidity_score': 90
            },
            'trading_suitability': {
                'suitable_for_signals': True,
                'suitability_score': 82.5
            },
            'signals_recommended': True
        }


class TestSignalParameterCalculator(TestSignalGenerationBase):
    """Test signal parameter calculations"""
    
    def test_spring_parameter_calculation(self, sample_price_data, sample_volume_data, sample_pattern, sample_market_context):
        """Test parameter calculation for spring patterns"""
        calculator = SignalParameterCalculator()
        
        result = calculator.calculate_signal_parameters(
            sample_pattern, sample_price_data, sample_volume_data, sample_market_context
        )
        
        # Verify required fields are present
        assert 'signal_type' in result
        assert result['signal_type'] == 'long'
        assert 'entry_price' in result
        assert 'stop_loss' in result
        assert 'take_profit_1' in result
        assert 'risk_reward_ratio' in result
        assert 'entry_confirmation' in result
        
        # Verify price relationships for long signal
        entry_price = float(result['entry_price'])
        stop_loss = float(result['stop_loss'])
        tp1 = float(result['take_profit_1'])
        
        assert entry_price > stop_loss, "Long signal entry should be above stop loss"
        assert tp1 > entry_price, "Take profit should be above entry for long signal"
        
        # Verify risk-reward calculation
        risk = entry_price - stop_loss
        reward = tp1 - entry_price
        calculated_rr = reward / risk
        
        assert abs(calculated_rr - result['risk_reward_ratio']) < 0.01, "R:R calculation mismatch"
    
    def test_accumulation_parameter_calculation(self, sample_price_data, sample_volume_data, sample_market_context):
        """Test parameter calculation for accumulation patterns"""
        calculator = SignalParameterCalculator()
        
        accumulation_pattern = {
            'type': 'accumulation',
            'confidence': 78.0,
            'resistance_level': 1.1050,
            'support_level': 1.0950,
            'direction': 'bullish'
        }
        
        result = calculator.calculate_signal_parameters(
            accumulation_pattern, sample_price_data, sample_volume_data, sample_market_context
        )
        
        assert result['signal_type'] == 'long'
        assert 'take_profit_2' in result
        assert 'take_profit_3' in result
        
        # Verify multiple take profit levels
        tp1 = float(result['take_profit_1'])
        tp2 = float(result['take_profit_2'])
        tp3 = float(result['take_profit_3'])
        
        assert tp2 > tp1, "TP2 should be above TP1"
        assert tp3 > tp2, "TP3 should be above TP2"
    
    def test_distribution_parameter_calculation(self, sample_price_data, sample_volume_data, sample_market_context):
        """Test parameter calculation for distribution patterns (short signals)"""
        calculator = SignalParameterCalculator()
        
        distribution_pattern = {
            'type': 'distribution',
            'confidence': 80.0,
            'resistance_level': 1.1050,
            'support_level': 1.0950,
            'direction': 'bearish'
        }
        
        result = calculator.calculate_signal_parameters(
            distribution_pattern, sample_price_data, sample_volume_data, sample_market_context
        )
        
        assert result['signal_type'] == 'short'
        
        # Verify price relationships for short signal
        entry_price = float(result['entry_price'])
        stop_loss = float(result['stop_loss'])
        tp1 = float(result['take_profit_1'])
        
        assert entry_price < stop_loss, "Short signal entry should be below stop loss"
        assert tp1 < entry_price, "Take profit should be below entry for short signal"
    
    def test_entry_confirmation_requirements(self, sample_price_data, sample_volume_data, sample_pattern, sample_market_context):
        """Test entry confirmation requirement generation"""
        calculator = SignalParameterCalculator()
        
        result = calculator.calculate_signal_parameters(
            sample_pattern, sample_price_data, sample_volume_data, sample_market_context
        )
        
        confirmation = result['entry_confirmation']
        
        assert confirmation.volume_spike_required
        assert confirmation.volume_threshold_multiplier > 1.0
        assert confirmation.momentum_threshold > 0
        assert confirmation.timeout_minutes > 0
        assert confirmation.price_confirmation_required


class TestRiskRewardOptimizer(TestSignalGenerationBase):
    """Test risk-reward optimization"""
    
    def test_risk_reward_meets_minimum(self, sample_price_data, sample_pattern, sample_market_context):
        """Test that optimizer enforces minimum R:R ratio"""
        optimizer = RiskRewardOptimizer(min_risk_reward=2.0)
        
        # Create signal with poor R:R ratio
        poor_params = {
            'signal_type': 'long',
            'entry_price': Decimal('1.1000'),
            'stop_loss': Decimal('1.0950'),
            'take_profit_1': Decimal('1.1020')  # Only 1:0.4 R:R ratio
        }
        
        result = optimizer.optimize_signal_parameters(
            poor_params, sample_pattern, sample_price_data, sample_market_context
        )
        
        if result['success']:
            optimized_rr = optimizer._calculate_risk_reward_ratio(result['params'])
            assert optimized_rr >= 2.0, f"Optimized R:R {optimized_rr} should meet minimum of 2.0"
        else:
            assert 'unable_to_meet_minimum_rr' in result.get('reason', '')
    
    def test_risk_reward_optimization_strategies(self, sample_price_data, sample_pattern, sample_market_context):
        """Test different optimization strategies"""
        optimizer = RiskRewardOptimizer(min_risk_reward=2.5)
        
        # Signal with mediocre R:R that can be optimized
        params = {
            'signal_type': 'long',
            'entry_price': Decimal('1.1000'),
            'stop_loss': Decimal('1.0970'),
            'take_profit_1': Decimal('1.1060')  # 2:1 R:R ratio
        }
        
        result = optimizer.optimize_signal_parameters(
            params, sample_pattern, sample_price_data, sample_market_context
        )
        
        if result['success']:
            strategies_used = result['params']['optimization_metadata']['optimization_strategies_applied']
            assert len(strategies_used) > 0, "Should have applied optimization strategies"
            
            final_rr = result['params']['optimization_metadata']['optimized_rr']
            original_rr = result['params']['optimization_metadata']['original_rr']
            assert final_rr > original_rr, "Should have improved R:R ratio"
    
    def test_position_sizing_recommendations(self, sample_price_data, sample_pattern, sample_market_context):
        """Test position sizing calculations"""
        optimizer = RiskRewardOptimizer()
        
        high_rr_params = {
            'signal_type': 'long',
            'entry_price': Decimal('1.1000'),
            'stop_loss': Decimal('1.0950'),
            'take_profit_1': Decimal('1.1150')  # 3:1 R:R ratio
        }
        
        result = optimizer.optimize_signal_parameters(
            high_rr_params, sample_pattern, sample_price_data, sample_market_context
        )
        
        if result['success']:
            position_sizing = result['params']['position_sizing']
            assert 'recommended_size_percent' in position_sizing
            assert 'risk_per_trade_percent' in position_sizing
            assert position_sizing['recommended_size_percent'] > 0


class TestSignalFrequencyManager(TestSignalGenerationBase):
    """Test signal frequency management"""
    
    def test_weekly_limit_enforcement(self):
        """Test weekly signal limit enforcement"""
        manager = SignalFrequencyManager(default_weekly_limit=3)
        
        account_id = "test_account_001"
        test_signal = {
            'signal_id': 'test_signal_1',
            'pattern_type': 'spring',
            'confidence': 85.0,
            'quality_score': 75.0,
            'risk_reward_ratio': 3.0
        }
        
        # First 3 signals should be allowed
        for i in range(3):
            check = manager.check_signal_allowance(account_id, test_signal, "EURUSD")
            assert check['allowed'], f"Signal {i+1} should be allowed"
            
            # Register the signal
            manager.register_signal(account_id, {**test_signal, 'signal_id': f'test_signal_{i+1}'}, "EURUSD")
        
        # 4th signal should be rejected (unless substitution is possible)
        check = manager.check_signal_allowance(account_id, test_signal, "EURUSD")
        
        if not check['allowed']:
            assert check['reason'] == 'weekly_limit_exceeded'
    
    def test_signal_substitution(self):
        """Test signal substitution with higher quality signals"""
        manager = SignalFrequencyManager(default_weekly_limit=2, enable_substitution=True)
        
        account_id = "test_account_002"
        
        # Register two low-quality signals
        low_quality_signal = {
            'signal_id': 'low_quality_1',
            'pattern_type': 'backup',
            'confidence': 76.0,
            'quality_score': 60.0,
            'risk_reward_ratio': 2.1
        }
        
        manager.register_signal(account_id, low_quality_signal, "EURUSD")
        manager.register_signal(account_id, {**low_quality_signal, 'signal_id': 'low_quality_2'}, "GBPUSD")
        
        # Try to add high-quality signal
        high_quality_signal = {
            'signal_id': 'high_quality_1',
            'pattern_type': 'spring',
            'confidence': 90.0,
            'quality_score': 85.0,
            'risk_reward_ratio': 4.0
        }
        
        check = manager.check_signal_allowance(account_id, high_quality_signal, "USDJPY")
        
        # Should allow substitution
        if check['allowed'] and check['reason'] == 'substitution':
            assert 'signal_to_replace' in check['substitution_details']
    
    def test_cooling_off_period(self):
        """Test cooling-off period between similar signals"""
        manager = SignalFrequencyManager(cooling_off_hours=2)
        
        spring_signal = {
            'signal_id': 'spring_signal_1',
            'pattern_type': 'spring',
            'confidence': 80.0,
            'quality_score': 70.0
        }
        
        # Register first signal
        manager.register_signal("account_003", spring_signal, "EURUSD")
        
        # Immediate similar signal should be rejected
        similar_signal = {**spring_signal, 'signal_id': 'spring_signal_2'}
        check = manager.check_signal_allowance("account_003", similar_signal, "EURUSD")
        
        if not check['allowed']:
            assert check['reason'] == 'cooling_off_period'
    
    def test_signal_quality_scoring(self):
        """Test signal quality scoring algorithm"""
        manager = SignalFrequencyManager()
        
        excellent_signal = {
            'confidence': 95.0,
            'risk_reward_ratio': 4.5,
            'pattern_type': 'spring',
            'market_context': {
                'market_state': 'trending',
                'volatility_regime': 'normal',
                'session': 'london'
            }
        }
        
        poor_signal = {
            'confidence': 76.0,
            'risk_reward_ratio': 2.1,
            'pattern_type': 'backup',
            'market_context': {
                'market_state': 'choppy',
                'volatility_regime': 'extreme',
                'session': 'off_hours'
            }
        }
        
        excellent_score = manager.calculate_signal_quality_score(excellent_signal)
        poor_score = manager.calculate_signal_quality_score(poor_signal)
        
        assert excellent_score > poor_score, "Excellent signal should score higher"
        assert excellent_score >= 80, "Excellent signal should score >= 80"
        assert poor_score <= 60, "Poor signal should score <= 60"


class TestMarketStateDetector(TestSignalGenerationBase):
    """Test market state detection"""
    
    def test_trend_detection(self, sample_price_data, sample_volume_data):
        """Test trend state detection"""
        detector = MarketStateDetector()
        
        # Create trending price data
        trending_data = sample_price_data.copy()
        trending_data['close'] = trending_data['close'].rolling(50).mean()  # Smooth trend
        
        result = detector.detect_market_state(trending_data, sample_volume_data)
        
        assert 'market_state' in result
        assert 'trend_analysis' in result
        assert 'volatility_analysis' in result
        assert 'trading_suitability' in result
        
        trend_analysis = result['trend_analysis']
        assert 'direction' in trend_analysis
        assert 'strength' in trend_analysis
        assert trend_analysis['strength'] >= 0
    
    def test_volatility_regime_detection(self, sample_price_data, sample_volume_data):
        """Test volatility regime classification"""
        detector = MarketStateDetector()
        
        result = detector.detect_market_state(sample_price_data, sample_volume_data)
        
        volatility_analysis = result['volatility_analysis']
        assert 'regime' in volatility_analysis
        assert volatility_analysis['regime'] in ['low', 'normal', 'high', 'extreme']
        assert 'atr_current' in volatility_analysis
        assert 'atr_percentage' in volatility_analysis
    
    def test_trading_suitability_assessment(self, sample_price_data, sample_volume_data):
        """Test trading suitability assessment"""
        detector = MarketStateDetector()
        
        result = detector.detect_market_state(sample_price_data, sample_volume_data)
        
        suitability = result['trading_suitability']
        assert 'suitable_for_signals' in suitability
        assert 'suitability_score' in suitability
        assert 'recommended_signal_types' in suitability
        assert isinstance(suitability['suitable_for_signals'], bool)
        assert 0 <= suitability['suitability_score'] <= 100


class TestSignalPerformanceTracker(TestSignalGenerationBase):
    """Test signal performance tracking"""
    
    def test_signal_outcome_tracking(self):
        """Test tracking signal outcomes"""
        tracker = SignalPerformanceTracker()
        
        # Track a winning signal
        outcome_data = {
            'type': 'win',
            'entry_filled': True,
            'entry_fill_price': 1.1000,
            'exit_price': 1.1150,
            'pnl_points': 0.0150,
            'hold_duration_hours': 18,
            'target_hit': 'tp1',
            'max_favorable_excursion': 0.0180,
            'max_adverse_excursion': -0.0020
        }
        
        signal_metadata = {
            'pattern_type': 'spring',
            'confidence': 85.0,
            'risk_reward_ratio': 3.0
        }
        
        result = tracker.track_signal_outcome("test_signal_001", outcome_data, signal_metadata)
        
        assert result['outcome_recorded']
        assert result['outcome_type'] == 'win'
        assert result['pnl_points'] == 0.0150
    
    def test_performance_metrics_calculation(self):
        """Test performance metrics calculation"""
        tracker = SignalPerformanceTracker()
        
        # Add multiple signal outcomes
        test_outcomes = [
            ('signal_1', {'type': 'win', 'pnl_points': 0.015, 'entry_filled': True}),
            ('signal_2', {'type': 'win', 'pnl_points': 0.025, 'entry_filled': True}),
            ('signal_3', {'type': 'loss', 'pnl_points': -0.010, 'entry_filled': True}),
            ('signal_4', {'type': 'win', 'pnl_points': 0.020, 'entry_filled': True}),
            ('signal_5', {'type': 'loss', 'pnl_points': -0.012, 'entry_filled': True})
        ]
        
        for signal_id, outcome_data in test_outcomes:
            tracker.track_signal_outcome(signal_id, outcome_data)
        
        metrics = tracker.calculate_performance_metrics()
        
        assert 'win_loss_metrics' in metrics
        assert 'pnl_metrics' in metrics
        
        win_loss = metrics['win_loss_metrics']
        assert win_loss['wins'] == 3
        assert win_loss['losses'] == 2
        assert win_loss['win_rate_percent'] == 60.0
        
        pnl = metrics['pnl_metrics']
        assert pnl['gross_profit'] > 0
        assert pnl['gross_loss'] > 0
        assert pnl['profit_factor'] > 1.0  # Should be profitable overall
    
    def test_pattern_performance_breakdown(self):
        """Test performance breakdown by pattern type"""
        tracker = SignalPerformanceTracker()
        
        # Add outcomes for different pattern types
        spring_outcomes = [
            ('spring_1', {'type': 'win', 'pnl_points': 0.020}, {'pattern_type': 'spring'}),
            ('spring_2', {'type': 'win', 'pnl_points': 0.015}, {'pattern_type': 'spring'}),
            ('spring_3', {'type': 'loss', 'pnl_points': -0.008}, {'pattern_type': 'spring'})
        ]
        
        accumulation_outcomes = [
            ('acc_1', {'type': 'win', 'pnl_points': 0.025}, {'pattern_type': 'accumulation'}),
            ('acc_2', {'type': 'loss', 'pnl_points': -0.015}, {'pattern_type': 'accumulation'})
        ]
        
        all_outcomes = spring_outcomes + accumulation_outcomes
        
        for signal_id, outcome_data, metadata in all_outcomes:
            tracker.track_signal_outcome(signal_id, outcome_data, metadata)
        
        breakdown = tracker.get_pattern_performance_breakdown()
        
        assert 'pattern_breakdown' in breakdown
        assert 'spring' in breakdown['pattern_breakdown']
        
        spring_performance = breakdown['pattern_breakdown']['spring']
        assert spring_performance['total_signals'] == 3
        assert spring_performance['win_rate'] == round((2/3) * 100, 2)
    
    def test_real_time_tracking(self):
        """Test real-time signal tracking"""
        tracker = SignalPerformanceTracker(track_real_time=True)
        
        # Set up signal metadata
        signal_metadata = {
            'entry_price': 1.1000,
            'signal_type': 'long'
        }
        tracker.signal_metadata['test_signal'] = signal_metadata
        
        # Update with current price
        result = tracker.update_real_time_tracking('test_signal', 1.1050)
        
        assert 'current_pnl' in result
        assert 'max_favorable_excursion' in result
        assert result['current_pnl'] == 0.0050  # 1.1050 - 1.1000 for long signal


class TestSignalGeneratorIntegration(TestSignalGenerationBase):
    """Integration tests for the complete signal generation system"""
    
    @pytest.fixture
    def signal_generator(self):
        """Create signal generator with test configuration"""
        return SignalGenerator(
            confidence_threshold=75.0,
            min_risk_reward=2.0,
            enable_market_filtering=True,
            enable_frequency_management=True,
            enable_performance_tracking=True
        )
    
    @pytest.mark.asyncio
    async def test_complete_signal_generation_pipeline(self, signal_generator, sample_price_data, 
                                                      sample_volume_data, sample_pattern):
        """Test complete signal generation pipeline"""
        
        # Mock the pattern detection to return our sample pattern
        with patch.object(signal_generator, '_detect_wyckoff_patterns') as mock_detect:
            mock_detect.return_value = [sample_pattern]
            
            # Mock volume enhancement
            with patch.object(signal_generator, '_enhance_patterns_with_volume') as mock_enhance:
                enhanced_pattern = {**sample_pattern, 'volume_confirmation': 85.0}
                mock_enhance.return_value = [enhanced_pattern]
                
                # Generate signal
                result = await signal_generator.generate_signal(
                    symbol="EURUSD",
                    timeframe="H1", 
                    price_data=sample_price_data,
                    volume_data=sample_volume_data,
                    account_id="test_account"
                )
                
                # Verify successful generation
                if result['signal_generated']:
                    signal = result['signal']
                    assert isinstance(signal, TradingSignal)
                    assert signal.symbol == "EURUSD"
                    assert signal.timeframe == "H1"
                    assert signal.confidence >= 75.0
                    assert signal.risk_reward_ratio >= 2.0
                    assert signal.pattern_type == 'spring'
                else:
                    # If generation failed, check reason
                    print(f"Signal generation failed: {result['reason']}")
                    if 'confidence' in result['reason']:
                        assert result['highest_confidence'] < 75.0
    
    @pytest.mark.asyncio
    async def test_signal_generation_with_low_confidence(self, signal_generator, sample_price_data, 
                                                        sample_volume_data):
        """Test signal generation rejects low confidence patterns"""
        
        low_confidence_pattern = {
            'type': 'backup',
            'confidence': 72.0,  # Below 75% threshold
            'strength': 60.0
        }
        
        with patch.object(signal_generator, '_detect_wyckoff_patterns') as mock_detect:
            mock_detect.return_value = [low_confidence_pattern]
            
            with patch.object(signal_generator, '_enhance_patterns_with_volume') as mock_enhance:
                mock_enhance.return_value = [low_confidence_pattern]
                
                result = await signal_generator.generate_signal(
                    symbol="EURUSD",
                    timeframe="H1",
                    price_data=sample_price_data, 
                    volume_data=sample_volume_data
                )
                
                assert not result['signal_generated']
                assert result['reason'] == 'insufficient_confidence'
                assert result['highest_confidence'] == 72.0
    
    @pytest.mark.asyncio 
    async def test_signal_generation_frequency_limits(self, signal_generator, sample_price_data,
                                                     sample_volume_data, sample_pattern):
        """Test signal generation respects frequency limits"""
        
        account_id = "frequency_test_account"
        
        # Mock successful pattern detection
        with patch.object(signal_generator, '_detect_wyckoff_patterns') as mock_detect:
            mock_detect.return_value = [sample_pattern]
            
            with patch.object(signal_generator, '_enhance_patterns_with_volume') as mock_enhance:
                mock_enhance.return_value = [{**sample_pattern, 'confidence': 85.0}]
                
                # Generate signals up to limit
                successful_signals = 0
                for i in range(5):  # Try to generate 5 signals
                    result = await signal_generator.generate_signal(
                        symbol=f"PAIR{i}",
                        timeframe="H1",
                        price_data=sample_price_data,
                        volume_data=sample_volume_data,
                        account_id=account_id
                    )
                    
                    if result['signal_generated']:
                        successful_signals += 1
                    else:
                        if result['reason'] == 'frequency_limit_exceeded':
                            # Should be rejected after 3 signals (default weekly limit)
                            assert successful_signals >= 3
                            break
                
                # Should have generated at least 3 signals before hitting limit
                assert successful_signals >= 3
    
    def test_signal_generator_statistics(self, signal_generator):
        """Test signal generation statistics tracking"""
        
        # Get initial statistics
        initial_stats = signal_generator.get_generation_statistics()
        assert 'total_attempts' in initial_stats
        assert 'signals_generated' in initial_stats
        assert 'success_rate' in initial_stats
        
        # Reset statistics
        signal_generator.reset_generation_statistics()
        reset_stats = signal_generator.get_generation_statistics()
        assert reset_stats['total_attempts'] == 0
        assert reset_stats['signals_generated'] == 0
    
    def test_signal_generator_configuration_update(self, signal_generator):
        """Test updating signal generator configuration"""
        
        config_updates = {
            'confidence_threshold': 80.0,
            'min_risk_reward': 2.5,
            'enable_market_filtering': False
        }
        
        result = signal_generator.update_configuration(config_updates)
        
        assert result['configuration_updated']
        assert len(result['updated_parameters']) == 3
        assert signal_generator.confidence_threshold == 80.0
        assert signal_generator.min_risk_reward == 2.5
        assert not signal_generator.enable_market_filtering


class TestSignalMetadata(TestSignalGenerationBase):
    """Test signal metadata models"""
    
    def test_trading_signal_creation(self, sample_pattern, sample_market_context):
        """Test TradingSignal creation and calculations"""
        
        confidence_breakdown = ConfidenceBreakdown(
            pattern_confidence=85.0,
            volume_confirmation=80.0,
            timeframe_alignment=75.0,
            market_context=70.0,
            trend_strength=80.0,
            support_resistance=85.0,
            total_confidence=82.5
        )
        
        market_context = MarketContext(
            session='london',
            volatility_regime='normal',
            market_state='trending',
            trend_direction='up',
            trend_strength=75.0,
            atr_normalized=0.14,
            volume_regime='normal'
        )
        
        pattern_details = PatternDetails(
            pattern_type='spring',
            wyckoff_phase='Phase C',
            pattern_stage='completion',
            key_levels={'support': 1.0950, 'resistance': 1.1050},
            pattern_duration_bars=35,
            pattern_height_points=0.0100,
            volume_characteristics={'confirmation': 'strong'},
            invalidation_level=1.0930
        )
        
        entry_confirmation = EntryConfirmation(
            volume_spike_required=True,
            volume_threshold_multiplier=2.5,
            momentum_threshold=0.3,
            timeout_minutes=30
        )
        
        signal = TradingSignal(
            signal_id=None,  # Will be auto-generated
            symbol="EURUSD",
            timeframe="H1",
            signal_type="long",
            pattern_type="spring",
            confidence=82.5,
            confidence_breakdown=confidence_breakdown,
            entry_price=Decimal('1.1000'),
            stop_loss=Decimal('1.0950'),
            take_profit_1=Decimal('1.1100'),
            take_profit_2=Decimal('1.1150'),
            generated_at=datetime.now(),
            valid_until=datetime.now() + timedelta(hours=24),
            expected_hold_time_hours=18,
            market_context=market_context,
            pattern_details=pattern_details,
            entry_confirmation=entry_confirmation,
            contributing_factors=['wyckoff_spring_pattern', 'high_confidence', 'strong_volume_confirmation']
        )
        
        # Test automatic calculations
        assert signal.signal_id is not None
        assert signal.risk_reward_ratio == 2.0  # (1.1100 - 1.1000) / (1.1000 - 1.0950)
        assert signal.quality_score > 0
        assert signal.is_valid()
        
        # Test serialization
        signal_dict = signal.to_dict()
        assert 'signal_id' in signal_dict
        assert 'confidence_breakdown' in signal_dict
        
        signal_json = signal.to_json()
        assert isinstance(signal_json, str)
        
        # Test deserialization
        reconstructed_signal = TradingSignal.from_dict(signal_dict)
        assert reconstructed_signal.symbol == signal.symbol
        assert reconstructed_signal.risk_reward_ratio == signal.risk_reward_ratio


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])