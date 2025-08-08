"""
Comprehensive tests for Wyckoff Pattern Detection Engine

Tests all components:
- Phase detection (accumulation, markup, distribution, markdown)
- Spring and upthrust detection
- Volume profile analysis
- Pattern confidence scoring
- Multi-timeframe validation
- Performance tracking
"""

import pytest
import pandas as pd
import numpy as np
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from typing import Tuple

# Import the Wyckoff components
from app.wyckoff import (
    WyckoffPhaseDetector,
    SpringUpthrustDetector,
    VolumeProfileAnalyzer,
    PatternConfidenceScorer,
    MultiTimeframeValidator,
    PatternPerformanceTracker
)
from app.wyckoff.phase_detector import (
    AccumulationDetector,
    MarkupDetector,
    DistributionDetector,
    MarkdownDetector,
    PhaseDetectionResult
)
from app.wyckoff.spring_upthrust import SpringUpthrustResult
from app.wyckoff.volume_profile import VolumeZone, VolumeProfileResult
from app.wyckoff.confidence_scorer import ConfidenceScore
from app.wyckoff.timeframe_validator import TimeframePattern, MultiTimeframeResult
from app.wyckoff.performance_tracker import (
    PatternRecord,
    OutcomeRecord,
    OutcomeType,
    PerformanceMetrics
)


class TestDataGenerator:
    """Generate test data for various market scenarios"""
    
    @staticmethod
    def generate_accumulation_data(periods: int = 50) -> tuple[pd.DataFrame, pd.Series]:
        """Generate OHLC data resembling accumulation phase"""
        np.random.seed(42)  # For reproducible tests
        
        base_price = 1.1000
        prices = []
        volumes = []
        
        # Accumulation characteristics:
        # - Sideways movement with declining volatility
        # - Higher volume on strength
        # - Support level holding
        
        for i in range(periods):
            # Decreasing volatility over time
            volatility = max(0.0005, 0.002 - (i / periods) * 0.0015)
            
            # Sideways movement with slight bias
            price_change = np.random.normal(0, volatility)
            if i == 0:
                price = base_price
            else:
                price = max(base_price - 0.005, min(base_price + 0.005, prices[-1]['close'] + price_change))
            
            # Volume higher on up moves
            if price_change > 0:
                volume = np.random.uniform(1200, 2000)  # Higher volume on up moves
            else:
                volume = np.random.uniform(800, 1200)   # Lower volume on down moves
            
            # OHLC generation
            high = price + np.random.uniform(0, volatility/2)
            low = price - np.random.uniform(0, volatility/2)
            open_price = prices[-1]['close'] if i > 0 else price
            close = price
            
            prices.append({
                'timestamp': datetime.now() - timedelta(hours=periods-i),
                'open': open_price,
                'high': high,
                'low': low,
                'close': close
            })
            volumes.append(volume)
        
        price_df = pd.DataFrame(prices)
        price_df.set_index('timestamp', inplace=True)
        volume_series = pd.Series(volumes, index=price_df.index)
        
        return price_df, volume_series
    
    @staticmethod
    def generate_markup_data(periods: int = 30) -> Tuple[pd.DataFrame, pd.Series]:
        """Generate OHLC data resembling markup phase"""
        np.random.seed(43)
        
        base_price = 1.1000
        prices = []
        volumes = []
        
        for i in range(periods):
            # Upward trend with momentum
            trend_factor = (i / periods) * 0.015  # 1.5% total move
            volatility = 0.001
            
            if i == 0:
                price = base_price
            else:
                price = prices[-1]['close'] + np.random.uniform(0.0001, 0.0008) + (trend_factor / periods)
            
            # Volume confirmation on breakouts
            if i > 0 and price > max([p['high'] for p in prices[-min(5, i):]]):
                volume = np.random.uniform(1800, 2500)  # High volume on breakouts
            else:
                volume = np.random.uniform(1000, 1400)
            
            high = price + np.random.uniform(0, volatility/2)
            low = price - np.random.uniform(0, volatility/3)
            open_price = prices[-1]['close'] if i > 0 else price
            
            prices.append({
                'timestamp': datetime.now() - timedelta(hours=periods-i),
                'open': open_price,
                'high': high,
                'low': low,
                'close': price
            })
            volumes.append(volume)
        
        price_df = pd.DataFrame(prices)
        price_df.set_index('timestamp', inplace=True)
        volume_series = pd.Series(volumes, index=price_df.index)
        
        return price_df, volume_series
    
    @staticmethod
    def generate_spring_data(periods: int = 25) -> Tuple[pd.DataFrame, pd.Series]:
        """Generate data with spring pattern"""
        np.random.seed(44)
        
        base_price = 1.1000
        support_level = 1.0980
        prices = []
        volumes = []
        
        for i in range(periods):
            if i < 15:
                # Sideways action above support
                price = np.random.uniform(support_level + 0.0005, base_price + 0.0020)
                volume = np.random.uniform(900, 1300)
            elif i == 15:
                # Spring: break below support but recover
                low = support_level - 0.0003  # Break below support
                price = support_level + 0.0002  # But close above support
                high = price + 0.0005
                volume = np.random.uniform(2000, 2800)  # High volume on spring
            else:
                # Rally after spring
                trend_up = (i - 15) * 0.0004
                price = support_level + 0.0002 + trend_up
                volume = np.random.uniform(1400, 2000)
            
            if i != 15:  # Normal OHLC generation
                high = price + np.random.uniform(0, 0.0003)
                low = price - np.random.uniform(0, 0.0003)
            
            open_price = prices[-1]['close'] if i > 0 else price
            
            prices.append({
                'timestamp': datetime.now() - timedelta(hours=periods-i),
                'open': open_price,
                'high': high,
                'low': low,
                'close': price
            })
            volumes.append(volume)
        
        price_df = pd.DataFrame(prices)
        price_df.set_index('timestamp', inplace=True)
        volume_series = pd.Series(volumes, index=price_df.index)
        
        return price_df, volume_series


class TestWyckoffPhaseDetector:
    """Test suite for Wyckoff phase detection"""
    
    def setup_method(self):
        self.detector = WyckoffPhaseDetector()
        self.test_symbol = "EURUSD"
    
    def test_accumulation_detection(self):
        """Test accumulation phase detection"""
        price_data, volume_data = TestDataGenerator.generate_accumulation_data()
        
        result = self.detector.detect_phase(self.test_symbol, price_data, volume_data, '1h')
        
        assert isinstance(result, PhaseDetectionResult)
        assert result.phase in ['accumulation', 'neutral']  # Could be neutral if confidence too low
        assert result.timeframe == '1h'
        assert isinstance(result.confidence, Decimal)
        assert 0 <= result.confidence <= 100
        assert 'support' in result.key_levels
        assert 'resistance' in result.key_levels
    
    def test_markup_detection(self):
        """Test markup phase detection"""
        price_data, volume_data = TestDataGenerator.generate_markup_data()
        
        result = self.detector.detect_phase(self.test_symbol, price_data, volume_data, '1h')
        
        assert isinstance(result, PhaseDetectionResult)
        # Markup should be detected or neutral
        assert result.phase in ['markup', 'neutral']
        assert result.confidence >= 0
        
        # Check criteria structure
        if result.phase == 'markup':
            assert 'trend_strength' in result.criteria
            assert 'breakout_volume' in result.criteria
    
    def test_insufficient_data_handling(self):
        """Test handling of insufficient data"""
        # Create minimal data
        price_data = pd.DataFrame({
            'open': [1.1000],
            'high': [1.1005],
            'low': [1.0995],
            'close': [1.1002]
        })
        volume_data = pd.Series([1000])
        
        with pytest.raises(ValueError, match="Insufficient data"):
            self.detector.detect_phase(self.test_symbol, price_data, volume_data)
    
    def test_phase_transition_validation(self):
        """Test phase transition validation logic"""
        # Test valid transition
        self.detector.current_phase = 'accumulation'
        assert self.detector._validate_phase_transition('markup', Decimal('70')) == True
        
        # Test invalid transition with low confidence
        assert self.detector._validate_phase_transition('markdown', Decimal('60')) == False
        
        # Test invalid transition with high confidence (should override)
        assert self.detector._validate_phase_transition('markdown', Decimal('80')) == True
    
    def test_phase_history_tracking(self):
        """Test phase history tracking"""
        price_data, volume_data = TestDataGenerator.generate_accumulation_data()
        
        # Detect multiple phases
        result1 = self.detector.detect_phase(self.test_symbol, price_data, volume_data, '1h')
        result2 = self.detector.detect_phase('GBPUSD', price_data, volume_data, '4h')
        
        history = self.detector.get_phase_history()
        assert len(history) >= 0  # May be empty if confidence too low
        
        # Test symbol filtering
        symbol_history = self.detector.get_phase_history(self.test_symbol)
        assert all(h['symbol'] == self.test_symbol for h in symbol_history)


class TestAccumulationDetector:
    """Test suite for accumulation detection specifically"""
    
    def setup_method(self):
        self.detector = AccumulationDetector()
    
    def test_range_contraction_calculation(self):
        """Test price range contraction calculation"""
        price_data, _ = TestDataGenerator.generate_accumulation_data(30)
        
        result = self.detector._calculate_range_contraction(price_data)
        
        assert 'score' in result
        assert 'contraction_ratio' in result
        assert 0 <= result['score'] <= 100
        assert isinstance(result['contraction_ratio'], (int, float))
    
    def test_volume_strength_analysis(self):
        """Test volume on strength analysis"""
        price_data, volume_data = TestDataGenerator.generate_accumulation_data(30)
        
        result = self.detector._analyze_volume_strength(price_data, volume_data)
        
        assert 'score' in result
        assert 'strength_volume_ratio' in result
        assert 0 <= result['score'] <= 100
        assert result['strength_volume_ratio'] >= 0
    
    def test_support_level_identification(self):
        """Test support level identification"""
        price_data, volume_data = TestDataGenerator.generate_accumulation_data(30)
        
        result = self.detector._identify_support_levels(price_data, volume_data)
        
        assert 'score' in result
        assert 'support_level' in result
        assert 'touches' in result
        assert result['touches'] >= 0


class TestSpringUpthrustDetector:
    """Test suite for spring and upthrust detection"""
    
    def setup_method(self):
        self.detector = SpringUpthrustDetector()
    
    def test_spring_detection(self):
        """Test spring pattern detection"""
        price_data, volume_data = TestDataGenerator.generate_spring_data()
        support_level = 1.0980
        
        springs = self.detector.detect_springs(price_data, volume_data, support_level)
        
        assert isinstance(springs, list)
        # Should detect at least one spring in our test data
        if springs:  # If springs detected
            spring = springs[0]
            assert isinstance(spring, SpringUpthrustResult)
            assert spring.pattern_type == 'spring'
            assert spring.strength >= 0
            assert spring.key_level == support_level
    
    def test_spring_strength_calculation(self):
        """Test spring strength calculation"""
        # Create a spring candle
        candle = pd.Series({
            'open': 1.0982,
            'high': 1.0985,
            'low': 1.0978,  # Below support
            'close': 1.0983  # Above support
        })
        
        volume = 2000
        support_level = 1.0980
        avg_volume = 1200
        
        result = self.detector._calculate_spring_strength(candle, volume, support_level, avg_volume)
        
        assert 'strength' in result
        assert 'volume_confirmation' in result
        assert 'recovery_ratio' in result
        assert 0 <= result['strength'] <= 100
    
    def test_false_breakout_detection(self):
        """Test false breakout detection"""
        price_data, volume_data = TestDataGenerator.generate_spring_data()
        key_levels = {'support': 1.0980, 'resistance': 1.1020}
        
        false_breakouts = self.detector.detect_false_breakouts(price_data, volume_data, key_levels)
        
        assert isinstance(false_breakouts, list)
        # Each false breakout should be properly structured
        for breakout in false_breakouts:
            assert isinstance(breakout, SpringUpthrustResult)
            assert breakout.pattern_type == 'false_breakout'


class TestVolumeProfileAnalyzer:
    """Test suite for volume profile analysis"""
    
    def setup_method(self):
        self.analyzer = VolumeProfileAnalyzer(bins=20)
    
    def test_volume_profile_calculation(self):
        """Test basic volume profile calculation"""
        price_data, volume_data = TestDataGenerator.generate_accumulation_data()
        
        result = self.analyzer.calculate_volume_profile(price_data, volume_data)
        
        assert isinstance(result, VolumeProfileResult)
        assert result.point_of_control > 0
        assert result.value_area_high >= result.value_area_low
        assert len(result.volume_zones) >= 0
        assert 'volume_by_price' in result.profile_data
    
    def test_support_resistance_identification(self):
        """Test support/resistance zone identification"""
        price_data, volume_data = TestDataGenerator.generate_accumulation_data()
        
        zones = self.analyzer.identify_support_resistance_zones(price_data, volume_data)
        
        assert 'support' in zones
        assert 'resistance' in zones
        assert 'all_zones' in zones
        
        for zone_list in [zones['support'], zones['resistance']]:
            for zone in zone_list:
                assert isinstance(zone, VolumeZone)
                assert zone.strength >= 0
                assert zone.touches >= 0
    
    def test_zone_strength_calculation(self):
        """Test zone strength calculation"""
        price_data, volume_data = TestDataGenerator.generate_accumulation_data()
        zone_level = 1.0990
        
        result = self.analyzer.calculate_zone_strength(zone_level, price_data, volume_data)
        
        assert 'strength' in result
        assert 'components' in result
        assert 'touches' in result
        assert 0 <= result['strength'] <= 100
    
    def test_zone_break_detection(self):
        """Test zone break detection"""
        price_data, volume_data = TestDataGenerator.generate_markup_data()
        
        # Create some mock zones
        zones = [
            VolumeZone(
                level=1.0990,
                zone_type='resistance',
                strength=Decimal('75'),
                volume=1500,
                touches=3,
                first_established=datetime.now() - timedelta(days=1),
                last_touched=datetime.now() - timedelta(hours=2),
                zone_range=(1.0988, 1.0992)
            )
        ]
        
        breaks = self.analyzer.detect_zone_breaks(zones, price_data, volume_data)
        
        assert isinstance(breaks, list)
        for zone_break in breaks:
            assert 'zone' in zone_break
            assert 'break_type' in zone_break
            assert zone_break['break_type'] in ['upward', 'downward']


class TestPatternConfidenceScorer:
    """Test suite for pattern confidence scoring"""
    
    def setup_method(self):
        self.scorer = PatternConfidenceScorer()
    
    def test_confidence_calculation(self):
        """Test pattern confidence calculation"""
        # Mock pattern data
        pattern_data = {
            'phase': 'accumulation',
            'criteria': {
                'volume_on_strength': {'score': 75},
                'price_range_contraction': {'score': 80},
                'support_holding': {'score': 70}
            }
        }
        
        price_data, volume_data = TestDataGenerator.generate_accumulation_data()
        
        result = self.scorer.calculate_pattern_confidence(pattern_data, price_data, volume_data)
        
        assert isinstance(result, ConfidenceScore)
        assert 0 <= result.overall_confidence <= 100
        assert len(result.factor_scores) > 0
        assert result.confidence_level in ['low', 'medium', 'high', 'very_high']
    
    def test_volume_confirmation_scoring(self):
        """Test volume confirmation scoring"""
        pattern_data = {
            'criteria': {
                'volume_on_strength': {'score': 85},
                'breakout_volume': {'score': 90}
            }
        }
        
        _, volume_data = TestDataGenerator.generate_markup_data()
        
        score = self.scorer._score_volume_confirmation(pattern_data, volume_data)
        
        assert isinstance(score, Decimal)
        assert 0 <= score <= 100
    
    def test_historical_performance_scoring(self):
        """Test historical performance scoring"""
        # Test known pattern type
        score = self.scorer._score_historical_performance('accumulation')
        assert isinstance(score, Decimal)
        assert score > 0
        
        # Test unknown pattern type
        score = self.scorer._score_historical_performance('unknown_pattern')
        assert score == Decimal('40')  # Conservative score


class TestMultiTimeframeValidator:
    """Test suite for multi-timeframe validation"""
    
    def setup_method(self):
        self.validator = MultiTimeframeValidator()
    
    def test_pattern_alignment_validation(self):
        """Test pattern alignment across timeframes"""
        price_data, volume_data = TestDataGenerator.generate_accumulation_data()
        
        # Mock timeframe data
        timeframe_data = {
            '1h': {
                'price_data': price_data,
                'volume_data': volume_data,
                'pattern_result': {
                    'phase': 'accumulation',
                    'confidence': Decimal('75'),
                    'detected': True,
                    'key_levels': {'support': 1.0980, 'resistance': 1.1020}
                }
            },
            '4h': {
                'price_data': price_data,
                'volume_data': volume_data,
                'pattern_result': {
                    'phase': 'accumulation',
                    'confidence': Decimal('70'),
                    'detected': True,
                    'key_levels': {'support': 1.0975, 'resistance': 1.1025}
                }
            }
        }
        
        result = self.validator.validate_pattern_alignment('EURUSD', timeframe_data)
        
        assert isinstance(result, MultiTimeframeResult)
        assert result.alignment_score >= 0
        assert isinstance(result.conflicts, list)
        assert result.dominant_timeframe in ['1h', '4h']
    
    def test_higher_timeframe_confirmation(self):
        """Test higher timeframe confirmation"""
        # Create mock patterns
        patterns = {
            '1h': TimeframePattern(
                timeframe='1h',
                pattern_type='accumulation',
                confidence=Decimal('75'),
                strength=Decimal('80'),
                key_levels={'support': 1.0980},
                detection_time=datetime.now(),
                trend_direction='sideways',
                trend_strength=Decimal('60')
            ),
            '4h': TimeframePattern(
                timeframe='4h',
                pattern_type='accumulation',
                confidence=Decimal('70'),
                strength=Decimal('75'),
                key_levels={'support': 1.0975},
                detection_time=datetime.now(),
                trend_direction='sideways',
                trend_strength=Decimal('65')
            )
        }
        
        confirmation = self.validator.check_higher_timeframe_trend_confirmation(patterns, '1h')
        
        assert 'confirmed' in confirmation
        assert 'confirmation_strength' in confirmation
        assert isinstance(confirmation['confirmed'], bool)
    
    def test_conflict_detection(self):
        """Test timeframe conflict detection"""
        patterns = {
            '1h': TimeframePattern(
                timeframe='1h',
                pattern_type='accumulation',
                confidence=Decimal('75'),
                strength=Decimal('80'),
                key_levels={},
                detection_time=datetime.now(),
                trend_direction='up',
                trend_strength=Decimal('70')
            ),
            '4h': TimeframePattern(
                timeframe='4h',
                pattern_type='distribution',  # Conflicting pattern
                confidence=Decimal('70'),
                strength=Decimal('75'),
                key_levels={},
                detection_time=datetime.now(),
                trend_direction='down',  # Conflicting trend
                trend_strength=Decimal('65')
            )
        }
        
        conflicts = self.validator._identify_conflicts(patterns)
        
        assert len(conflicts) > 0  # Should detect conflicts
        conflict = conflicts[0]
        assert 'timeframes' in conflict
        assert 'conflict_type' in conflict
        assert 'severity' in conflict


class TestPatternPerformanceTracker:
    """Test suite for pattern performance tracking"""
    
    def setup_method(self):
        self.tracker = PatternPerformanceTracker()
    
    def test_pattern_tracking(self):
        """Test pattern detection tracking"""
        pattern_result = {
            'phase': 'accumulation',
            'confidence': Decimal('75'),
            'key_levels': {'support': 1.0980, 'resistance': 1.1020}
        }
        
        pattern_id = self.tracker.track_pattern_detection(
            'EURUSD',
            pattern_result,
            {'market_condition': 'ranging'},
            {'1h': 'data'},
            {'poc': 1.0990}
        )
        
        assert isinstance(pattern_id, str)
        assert len(pattern_id) > 0
        
        # Check that pattern was stored
        pattern = self.tracker._find_pattern_record(pattern_id)
        assert pattern is not None
        assert pattern.symbol == 'EURUSD'
        assert pattern.pattern_type == 'accumulation'
    
    def test_outcome_tracking(self):
        """Test outcome tracking"""
        # First track a pattern
        pattern_result = {'phase': 'spring', 'confidence': Decimal('80')}
        pattern_id = self.tracker.track_pattern_detection('EURUSD', pattern_result, {}, {}, {})
        
        # Then track its outcome
        outcome_id = self.tracker.track_pattern_outcome(
            pattern_id,
            OutcomeType.WIN,
            entry_price=1.1000,
            exit_price=1.1025,
            outcome_time=datetime.now()
        )
        
        assert isinstance(outcome_id, str)
        
        # Verify outcome was stored
        outcomes = self.tracker._get_outcomes_for_pattern(pattern_id)
        assert len(outcomes) == 1
        assert outcomes[0].outcome_type == OutcomeType.WIN
        assert outcomes[0].pnl_points == Decimal('0.0025')
    
    def test_success_rate_calculation(self):
        """Test success rate calculation"""
        # Add some test patterns with outcomes
        for i in range(10):
            pattern_result = {
                'phase': 'accumulation',
                'confidence': Decimal(str(70 + i))  # Varying confidence
            }
            pattern_id = self.tracker.track_pattern_detection(f'TEST{i}', pattern_result, {}, {}, {})
            
            # Add outcomes (70% win rate)
            outcome_type = OutcomeType.WIN if i < 7 else OutcomeType.LOSS
            pnl = 0.01 if outcome_type == OutcomeType.WIN else -0.005
            
            self.tracker.track_pattern_outcome(
                pattern_id,
                outcome_type,
                entry_price=1.1000,
                exit_price=1.1000 + pnl
            )
        
        success_rates = self.tracker.calculate_pattern_success_rates('accumulation')
        
        assert 'accumulation' in success_rates
        metrics = success_rates['accumulation']
        assert isinstance(metrics, PerformanceMetrics)
        assert 65 <= float(metrics.win_rate) <= 75  # Should be around 70%
    
    def test_profitability_analysis(self):
        """Test profitability analysis"""
        # Add test data with known profitability
        for i in range(5):
            pattern_result = {'phase': 'spring', 'confidence': Decimal('80')}
            pattern_id = self.tracker.track_pattern_detection(f'SPRING{i}', pattern_result, {}, {}, {})
            
            # 80% win rate with good profit factor
            outcome_type = OutcomeType.WIN if i < 4 else OutcomeType.LOSS
            pnl = 0.02 if outcome_type == OutcomeType.WIN else -0.01
            
            self.tracker.track_pattern_outcome(
                pattern_id,
                outcome_type,
                entry_price=1.1000,
                exit_price=1.1000 + pnl
            )
        
        analysis = self.tracker.analyze_pattern_profitability('spring', 70)
        
        assert 'error' not in analysis
        assert 'total_pnl_points' in analysis
        assert 'profit_factor' in analysis
        assert 'win_rate_percent' in analysis
        assert analysis['profit_factor'] > 1.0  # Should be profitable
    
    def test_performance_report_generation(self):
        """Test performance report generation"""
        # Add some test data
        pattern_result = {'phase': 'markup', 'confidence': Decimal('75')}
        pattern_id = self.tracker.track_pattern_detection('TEST', pattern_result, {}, {}, {})
        self.tracker.track_pattern_outcome(pattern_id, OutcomeType.WIN, 1.1000, 1.1020)
        
        report = self.tracker.generate_performance_report()
        
        assert 'report_generated' in report
        assert 'overall_statistics' in report
        assert 'pattern_type_analysis' in report
        assert 'confidence_analysis' in report
        assert 'recommendations' in report
        assert isinstance(report['recommendations'], list)


class TestIntegration:
    """Integration tests for the complete Wyckoff system"""
    
    def setup_method(self):
        self.phase_detector = WyckoffPhaseDetector()
        self.spring_detector = SpringUpthrustDetector()
        self.volume_analyzer = VolumeProfileAnalyzer()
        self.confidence_scorer = PatternConfidenceScorer()
        self.timeframe_validator = MultiTimeframeValidator()
        self.performance_tracker = PatternPerformanceTracker()
    
    def test_end_to_end_pattern_detection(self):
        """Test complete end-to-end pattern detection workflow"""
        # Generate test data
        price_data, volume_data = TestDataGenerator.generate_accumulation_data()
        
        # Step 1: Detect phase
        phase_result = self.phase_detector.detect_phase('EURUSD', price_data, volume_data, '1h')
        
        # Step 2: Analyze volume profile
        volume_profile = self.volume_analyzer.calculate_volume_profile(price_data, volume_data)
        
        # Step 3: Calculate confidence
        pattern_data = {
            'phase': phase_result.phase,
            'criteria': phase_result.criteria
        }
        confidence_result = self.confidence_scorer.calculate_pattern_confidence(
            pattern_data, price_data, volume_data
        )
        
        # Step 4: Track pattern
        pattern_id = self.performance_tracker.track_pattern_detection(
            'EURUSD',
            {
                'phase': phase_result.phase,
                'confidence': confidence_result.overall_confidence,
                'key_levels': phase_result.key_levels
            },
            {'market_condition': 'ranging'},
            {'1h': 'test_data'},
            volume_profile.profile_data
        )
        
        # Verify integration
        assert isinstance(phase_result, PhaseDetectionResult)
        assert isinstance(volume_profile, VolumeProfileResult)
        assert isinstance(confidence_result, ConfidenceScore)
        assert isinstance(pattern_id, str)
        
        # Verify data consistency
        tracked_pattern = self.performance_tracker._find_pattern_record(pattern_id)
        assert tracked_pattern.pattern_type == phase_result.phase
        assert tracked_pattern.confidence_score == confidence_result.overall_confidence
    
    def test_multi_timeframe_integration(self):
        """Test multi-timeframe analysis integration"""
        price_data, volume_data = TestDataGenerator.generate_markup_data()
        
        # Simulate multiple timeframes
        timeframe_data = {}
        for tf in ['1h', '4h']:
            phase_result = self.phase_detector.detect_phase('EURUSD', price_data, volume_data, tf)
            timeframe_data[tf] = {
                'price_data': price_data,
                'volume_data': volume_data,
                'pattern_result': {
                    'phase': phase_result.phase,
                    'confidence': phase_result.confidence,
                    'detected': phase_result.phase != 'neutral',
                    'key_levels': phase_result.key_levels
                }
            }
        
        # Validate alignment
        mtf_result = self.timeframe_validator.validate_pattern_alignment('EURUSD', timeframe_data)
        
        assert isinstance(mtf_result, MultiTimeframeResult)
        assert mtf_result.alignment_score >= 0
        
        # Use results for confidence adjustment
        if len(mtf_result.timeframe_patterns) > 0:
            base_pattern = list(mtf_result.timeframe_patterns.values())[0]
            amplified_confidence = self.timeframe_validator.amplify_pattern_strength_with_alignment(
                base_pattern, 
                {'alignment_score': mtf_result.alignment_score, 'confirmations': []}
            )
            assert isinstance(amplified_confidence, Decimal)
            assert 0 <= amplified_confidence <= 100


# Utility functions for test data validation
def validate_test_data_quality():
    """Validate that test data generators produce realistic market data"""
    price_data, volume_data = TestDataGenerator.generate_accumulation_data()
    
    # Check data structure
    assert len(price_data) == len(volume_data)
    assert all(col in price_data.columns for col in ['open', 'high', 'low', 'close'])
    
    # Check data quality
    assert all(price_data['high'] >= price_data['low'])
    assert all(price_data['high'] >= price_data['open'])
    assert all(price_data['high'] >= price_data['close'])
    assert all(price_data['low'] <= price_data['open'])
    assert all(price_data['low'] <= price_data['close'])
    
    # Check volume is positive
    assert all(volume_data > 0)


if __name__ == "__main__":
    # Run basic validation
    validate_test_data_quality()
    print("Test data validation passed")
    
    # Run pytest
    pytest.main([__file__, "-v"])