"""
Comprehensive Tests for Volume Analysis Components

Tests all volume analysis components implemented in Story 3.3:
- Volume spike detection
- Volume divergence detection  
- Accumulation/Distribution line
- VWAP analysis
- Volume classification
- Volume profile construction
- Wyckoff integration
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

# Import all volume analysis components
from app.volume_analysis import (
    VolumeSpikeDetector,
    VolumeDivergenceDetector,
    AccumulationDistributionLine,
    VWAPAnalyzer,
    VolumeClassifier,
    VolumeProfileBuilder,
    WyckoffVolumeIntegrator
)


class TestVolumeAnalysisBase:
    """Base class with common test data and utilities."""
    
    @pytest.fixture
    def sample_price_data(self):
        """Create sample OHLC price data for testing."""
        dates = pd.date_range('2024-01-01', periods=250, freq='H')
        
        # Create realistic price movement
        base_price = 100.0
        price_changes = np.random.normal(0, 0.5, 250).cumsum()
        
        data = []
        for i, date in enumerate(dates):
            open_price = base_price + price_changes[i]
            high_price = open_price + abs(np.random.normal(0, 0.3))
            low_price = open_price - abs(np.random.normal(0, 0.3))
            close_price = open_price + np.random.normal(0, 0.2)
            
            # Ensure OHLC relationships are correct
            high_price = max(high_price, open_price, close_price)
            low_price = min(low_price, open_price, close_price)
            
            data.append({
                'timestamp': date,
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close_price
            })
        
        return pd.DataFrame(data).set_index('timestamp')
    
    @pytest.fixture
    def sample_volume_data(self):
        """Create sample volume data for testing."""
        # Create volume data with some patterns
        base_volume = 1000
        volumes = []
        
        for i in range(250):
            # Add some volume spikes
            if i in [20, 45, 70, 85, 120, 150, 200, 220]:
                volume = base_volume * np.random.uniform(3, 5)  # 3-5x spike
            elif i in [15, 30, 60, 80, 110, 140, 180, 210]:
                volume = base_volume * np.random.uniform(0.3, 0.7)  # Low volume
            else:
                volume = base_volume * np.random.uniform(0.8, 1.2)  # Normal variation
            
            volumes.append(volume)
        
        dates = pd.date_range('2024-01-01', periods=250, freq='H')
        return pd.Series(volumes, index=dates)
    
    @pytest.fixture
    def minimal_data(self):
        """Create minimal data for edge case testing."""
        dates = pd.date_range('2024-01-01', periods=5, freq='H')
        
        price_data = pd.DataFrame({
            'open': [100, 101, 102, 101, 100],
            'high': [101, 103, 104, 102, 101],
            'low': [99, 100, 101, 100, 99],
            'close': [100.5, 102, 101.5, 100.8, 100.2]
        }, index=dates)
        
        volume_data = pd.Series([1000, 1200, 800, 1500, 900], index=dates)
        
        return price_data, volume_data


class TestVolumeSpikeDetector(TestVolumeAnalysisBase):
    """Test volume spike detection functionality."""
    
    def test_spike_detector_initialization(self):
        """Test spike detector initialization."""
        detector = VolumeSpikeDetector()
        
        assert detector.lookback_periods == [20, 50, 200]
        assert detector.spike_thresholds['moderate'] == 2.0
        assert detector.spike_thresholds['strong'] == 3.0
        assert detector.spike_thresholds['extreme'] == 5.0
    
    def test_spike_detector_custom_params(self):
        """Test spike detector with custom parameters."""
        custom_periods = [10, 30, 100]
        custom_thresholds = {'low': 1.5, 'high': 4.0}
        
        detector = VolumeSpikeDetector(
            lookback_periods=custom_periods,
            spike_thresholds=custom_thresholds
        )
        
        assert detector.lookback_periods == custom_periods
        assert detector.spike_thresholds == custom_thresholds
    
    def test_detect_volume_spikes_basic(self, sample_price_data, sample_volume_data):
        """Test basic volume spike detection."""
        detector = VolumeSpikeDetector()
        result = detector.detect_volume_spikes(sample_price_data, sample_volume_data)
        
        assert 'total_spikes' in result
        assert 'all_spikes' in result
        assert 'spikes_by_severity' in result
        assert isinstance(result['total_spikes'], int)
        assert result['total_spikes'] >= 0
    
    def test_detect_spikes_with_patterns(self, sample_price_data, sample_volume_data):
        """Test spike detection identifies expected patterns."""
        detector = VolumeSpikeDetector()
        result = detector.detect_volume_spikes(sample_price_data, sample_volume_data)
        
        # Should detect the programmed volume spikes
        extreme_spikes = result['spikes_by_severity'].get('extreme', [])
        strong_spikes = result['spikes_by_severity'].get('strong', [])
        
        # Should have detected some spikes given our test data
        assert len(extreme_spikes) + len(strong_spikes) > 0
        
        # Check spike structure
        if result['all_spikes']:
            spike = result['all_spikes'][0]
            required_keys = ['timestamp', 'volume', 'spike_ratio', 'severity', 
                           'classification', 'alert_score']
            for key in required_keys:
                assert key in spike
    
    def test_spike_detection_insufficient_data(self):
        """Test spike detection with insufficient data."""
        detector = VolumeSpikeDetector()
        
        # Create minimal data
        dates = pd.date_range('2024-01-01', periods=3, freq='H')
        price_data = pd.DataFrame({
            'open': [100, 101, 102],
            'high': [101, 102, 103],
            'low': [99, 100, 101], 
            'close': [100.5, 101.5, 102.5]
        }, index=dates)
        volume_data = pd.Series([1000, 2000, 1500], index=dates)
        
        result = detector.detect_volume_spikes(price_data, volume_data)
        assert 'error' in result
    
    def test_spike_detection_data_mismatch(self, sample_price_data):
        """Test spike detection with mismatched data lengths."""
        detector = VolumeSpikeDetector()
        
        # Create volume data with different length
        short_volume = pd.Series([1000, 2000, 1500])
        
        result = detector.detect_volume_spikes(sample_price_data, short_volume)
        assert 'error' in result


class TestVolumeDivergenceDetector(TestVolumeAnalysisBase):
    """Test volume divergence detection functionality."""
    
    def test_divergence_detector_initialization(self):
        """Test divergence detector initialization."""
        detector = VolumeDivergenceDetector()
        
        assert detector.lookback_window == 50
        assert detector.min_peak_distance == 5
        assert detector.peak_prominence == 0.1
    
    def test_detect_divergences_basic(self, sample_price_data, sample_volume_data):
        """Test basic divergence detection."""
        detector = VolumeDivergenceDetector()
        result = detector.detect_divergences(sample_price_data, sample_volume_data)
        
        assert 'total_divergences' in result
        assert 'regular_bullish' in result
        assert 'regular_bearish' in result
        assert 'hidden_bullish' in result
        assert 'hidden_bearish' in result
        assert isinstance(result['total_divergences'], int)
    
    def test_find_price_extremes(self, sample_price_data, sample_volume_data):
        """Test price extremes detection."""
        detector = VolumeDivergenceDetector()
        recent_data = sample_price_data.iloc[-30:]
        
        peaks, troughs = detector.find_price_extremes(recent_data)
        
        assert isinstance(peaks, list)
        assert isinstance(troughs, list)
        
        # Check structure of extremes
        if peaks:
            peak = peaks[0]
            assert 'index' in peak
            assert 'price' in peak
            assert 'timestamp' in peak
            assert 'type' in peak
            assert peak['type'] == 'peak'
    
    def test_find_volume_extremes(self, sample_volume_data):
        """Test volume extremes detection."""
        detector = VolumeDivergenceDetector()
        recent_data = sample_volume_data.iloc[-30:]
        
        peaks, troughs = detector.find_volume_extremes(recent_data)
        
        assert isinstance(peaks, list)
        assert isinstance(troughs, list)
        
        # Check structure
        if peaks:
            peak = peaks[0]
            assert 'volume' in peak
            assert 'timestamp' in peak
    
    def test_divergence_strength_calculation(self):
        """Test divergence strength calculation."""
        detector = VolumeDivergenceDetector()
        
        # Test bullish divergence strength
        strength = detector.calculate_divergence_strength(-2.0, 3.0, 'regular_bullish')
        
        assert 'score' in strength
        assert 'classification' in strength
        assert 0 <= strength['score'] <= 100
        assert strength['classification'] in ['weak', 'moderate', 'strong', 'very_strong']


class TestAccumulationDistributionLine(TestVolumeAnalysisBase):
    """Test A/D Line calculation and analysis."""
    
    def test_ad_line_initialization(self):
        """Test A/D line analyzer initialization."""
        ad_analyzer = AccumulationDistributionLine()
        
        assert ad_analyzer.divergence_lookback == 20
        assert ad_analyzer.oscillator_period == 14
        assert ad_analyzer.trend_periods == [10, 20, 50]
    
    def test_calculate_ad_line_basic(self, sample_price_data, sample_volume_data):
        """Test basic A/D line calculation."""
        ad_analyzer = AccumulationDistributionLine()
        result = ad_analyzer.calculate_ad_line(sample_price_data, sample_volume_data)
        
        assert 'ad_values' in result
        assert 'cumulative_ad' in result
        assert 'current_ad_value' in result
        assert 'ad_trend' in result
        
        # Check A/D values structure
        if result['ad_values']:
            ad_value = result['ad_values'][0]
            required_keys = ['timestamp', 'money_flow_multiplier', 'money_flow_volume']
            for key in required_keys:
                assert key in ad_value
    
    def test_ad_line_money_flow_calculation(self):
        """Test money flow multiplier calculation."""
        ad_analyzer = AccumulationDistributionLine()
        
        # Create test candle data
        dates = pd.date_range('2024-01-01', periods=5, freq='H')
        price_data = pd.DataFrame({
            'open': [100, 101, 102, 101, 100],
            'high': [105, 106, 107, 106, 105],
            'low': [95, 96, 97, 96, 95],
            'close': [102, 103, 104, 103, 102]  # Closes near high (bullish)
        }, index=dates)
        volume_data = pd.Series([1000, 1200, 800, 1500, 900], index=dates)
        
        result = ad_analyzer.calculate_ad_line(price_data, volume_data)
        
        # Money flow multiplier should be positive for closes near high
        ad_values = result['ad_values']
        assert len(ad_values) == 5
        
        # Most multipliers should be positive given our test data
        positive_multipliers = sum(1 for av in ad_values if av['money_flow_multiplier'] > 0)
        assert positive_multipliers >= 3
    
    def test_ad_divergence_detection(self, sample_price_data, sample_volume_data):
        """Test A/D line divergence detection."""
        ad_analyzer = AccumulationDistributionLine()
        result = ad_analyzer.calculate_ad_line(sample_price_data, sample_volume_data)
        
        divergence_analysis = result['divergence_analysis']
        assert 'divergences_detected' in divergence_analysis
        assert 'correlation' in divergence_analysis
        assert 'trends_aligned' in divergence_analysis
        
        # Correlation should be between -1 and 1
        correlation = divergence_analysis['correlation']
        assert -1 <= correlation <= 1
    
    def test_ad_oscillator(self, sample_price_data, sample_volume_data):
        """Test A/D oscillator calculation."""
        ad_analyzer = AccumulationDistributionLine()
        result = ad_analyzer.calculate_ad_line(sample_price_data, sample_volume_data)
        
        oscillator = result['ad_oscillator']
        assert 'current_value' in oscillator
        assert 'momentum_state' in oscillator
        assert 'zero_line_crosses' in oscillator
        
        momentum_state = oscillator['momentum_state']
        expected_states = ['strong_bullish', 'bullish', 'neutral', 'bearish', 'strong_bearish']
        assert momentum_state in expected_states


class TestVWAPAnalyzer(TestVolumeAnalysisBase):
    """Test VWAP analysis functionality."""
    
    def test_vwap_initialization(self):
        """Test VWAP analyzer initialization."""
        vwap_analyzer = VWAPAnalyzer()
        
        assert vwap_analyzer.band_multipliers == [1.0, 2.0, 3.0]
        assert vwap_analyzer.session_start.hour == 9
        assert vwap_analyzer.session_end.hour == 16
    
    def test_calculate_vwap_basic(self, sample_price_data, sample_volume_data):
        """Test basic VWAP calculation."""
        vwap_analyzer = VWAPAnalyzer()
        result = vwap_analyzer.calculate_vwap_with_bands(sample_price_data, sample_volume_data)
        
        assert 'vwap_data' in result
        assert 'bands_data' in result
        assert 'signals' in result
        assert 'trend_analysis' in result
        
        # Check VWAP data structure
        vwap_data = result['vwap_data']
        if vwap_data:
            vwap_entry = vwap_data[0]
            assert 'timestamp' in vwap_entry
            assert 'vwap' in vwap_entry
            assert 'typical_price' in vwap_entry
            assert 'volume' in vwap_entry
    
    def test_vwap_bands_calculation(self, sample_price_data, sample_volume_data):
        """Test VWAP standard deviation bands."""
        vwap_analyzer = VWAPAnalyzer()
        result = vwap_analyzer.calculate_vwap_with_bands(sample_price_data, sample_volume_data)
        
        bands_data = result['bands_data']
        if bands_data:
            bands_entry = bands_data[0]
            assert 'vwap' in bands_entry
            assert 'bands' in bands_entry
            
            bands = bands_entry['bands']
            # Should have upper and lower bands for each multiplier
            assert 'upper_1.0' in bands
            assert 'lower_1.0' in bands
            assert 'upper_2.0' in bands
            assert 'lower_2.0' in bands
            
            # Upper bands should be above VWAP, lower bands below
            vwap_value = bands_entry['vwap']
            assert bands['upper_1.0'] >= vwap_value
            assert bands['lower_1.0'] <= vwap_value
    
    def test_vwap_signal_generation(self, sample_price_data, sample_volume_data):
        """Test VWAP signal generation."""
        vwap_analyzer = VWAPAnalyzer()
        result = vwap_analyzer.calculate_vwap_with_bands(sample_price_data, sample_volume_data)
        
        signals = result['signals']
        assert 'signals' in signals
        assert 'total_signals' in signals
        assert 'signal_quality' in signals
        
        signal_types = signals['signals']
        expected_types = ['mean_reversion', 'trend_following', 'breakout', 'pullback', 'support_resistance']
        for signal_type in expected_types:
            assert signal_type in signal_types
    
    def test_anchored_vwap(self, sample_price_data, sample_volume_data):
        """Test anchored VWAP calculation."""
        vwap_analyzer = VWAPAnalyzer()
        
        # Use some anchor points
        anchor_points = [10, 30, 50]
        
        result = vwap_analyzer.calculate_anchored_vwap(
            sample_price_data, sample_volume_data, anchor_points
        )
        
        assert 'anchored_vwaps' in result
        assert 'total_anchors' in result
        assert 'consensus_analysis' in result
        
        anchored_vwaps = result['anchored_vwaps']
        assert len(anchored_vwaps) <= len(anchor_points)
        
        if anchored_vwaps:
            anchor_key = list(anchored_vwaps.keys())[0]
            anchor_data = anchored_vwaps[anchor_key]
            assert 'vwap_values' in anchor_data
            assert 'current_vwap' in anchor_data
            assert 'periods_since_anchor' in anchor_data


class TestVolumeClassifier(TestVolumeAnalysisBase):
    """Test volume classification functionality."""
    
    def test_volume_classifier_initialization(self):
        """Test volume classifier initialization."""
        classifier = VolumeClassifier()
        
        assert classifier.large_volume_threshold_pct == 90.0
        assert classifier.frequency_analysis_window == 20
        assert len(classifier.institutional_hours) == 2
        assert 'size_factor_weight' in classifier.smart_money_indicators
    
    def test_classify_volume_basic(self, sample_price_data, sample_volume_data):
        """Test basic volume classification."""
        classifier = VolumeClassifier()
        result = classifier.classify_volume_type(sample_price_data, sample_volume_data)
        
        assert 'classifications' in result
        assert 'total_periods' in result
        assert 'smart_money_periods' in result
        assert 'retail_periods' in result
        assert 'aggregate_analysis' in result
        
        # Check classification structure
        if result['classifications']:
            classification = result['classifications'][0]
            required_keys = ['timestamp', 'classification', 'confidence', 
                           'smart_money_score', 'factors']
            for key in required_keys:
                assert key in classification
            
            # Classification should be one of expected types
            assert classification['classification'] in ['smart_money', 'retail', 'mixed']
            
            # Confidence and score should be in valid range
            assert 0 <= classification['confidence'] <= 1
            assert 0 <= classification['smart_money_score'] <= 1
    
    def test_volume_size_analysis(self):
        """Test volume size factor analysis."""
        classifier = VolumeClassifier()
        
        # Create test volume data with clear large volume
        volume_data = pd.Series([1000] * 50 + [5000])  # Last volume is 5x larger
        
        size_analysis = classifier.analyze_volume_size(5000, 50, volume_data)
        
        assert 'score' in size_analysis
        assert 'percentile' in size_analysis
        assert 'size_category' in size_analysis
        
        # Large volume should get high percentile and score
        assert size_analysis['percentile'] > 95
        assert size_analysis['score'] > 0.8
        assert size_analysis['size_category'] in ['large', 'very_large']
    
    def test_accumulation_distribution_detection(self, sample_price_data, sample_volume_data):
        """Test accumulation/distribution pattern detection."""
        classifier = VolumeClassifier()
        
        # Test accumulation detection
        accumulation = classifier.detect_accumulation_pattern(sample_price_data, sample_volume_data, 50)
        
        assert 'detected' in accumulation
        assert 'pattern_type' in accumulation
        assert 'strength' in accumulation
        
        # Test distribution detection  
        distribution = classifier.detect_distribution_pattern(sample_price_data, sample_volume_data, 50)
        
        assert 'detected' in distribution
        assert 'pattern_type' in distribution
        assert 'strength' in distribution
    
    def test_institutional_flow_detection(self, sample_price_data, sample_volume_data):
        """Test institutional flow pattern detection."""
        classifier = VolumeClassifier()
        result = classifier.classify_volume_type(sample_price_data, sample_volume_data)
        
        institutional_flow = result['institutional_flow']
        assert 'flow_direction' in institutional_flow
        assert 'flow_strength' in institutional_flow
        assert 'institutional_periods' in institutional_flow
        
        flow_directions = ['net_accumulation', 'net_distribution', 'balanced_flow']
        assert institutional_flow['flow_direction'] in flow_directions


class TestVolumeProfileBuilder(TestVolumeAnalysisBase):
    """Test volume profile construction."""
    
    def test_volume_profile_initialization(self):
        """Test volume profile builder initialization."""
        profiler = VolumeProfileBuilder()
        
        assert profiler.default_bins == 100
        assert profiler.value_area_percentage == 0.68
        assert profiler.min_volume_threshold == 0.01
    
    def test_build_volume_profile_basic(self, sample_price_data, sample_volume_data):
        """Test basic volume profile construction."""
        profiler = VolumeProfileBuilder()
        result = profiler.build_volume_profile(sample_price_data, sample_volume_data)
        
        assert 'poc' in result
        assert 'value_area' in result
        assert 'shape_analysis' in result
        assert 'volume_by_price' in result
        assert 'profile_statistics' in result
        
        # Check POC structure
        poc = result['poc']
        assert 'price' in poc
        assert 'volume' in poc
        assert 'volume_percentage' in poc
        assert 'poc_strength' in poc
        
        # Check Value Area structure
        value_area = result['value_area']
        assert 'vah' in value_area
        assert 'val' in value_area
        assert 'volume_percentage' in value_area
        
        # VAH should be >= VAL
        assert value_area['vah'] >= value_area['val']
    
    def test_volume_profile_shape_analysis(self, sample_price_data, sample_volume_data):
        """Test volume profile shape analysis."""
        profiler = VolumeProfileBuilder()
        result = profiler.build_volume_profile(sample_price_data, sample_volume_data)
        
        shape_analysis = result['shape_analysis']
        assert 'shape' in shape_analysis
        assert 'balance_score' in shape_analysis
        assert 'skewness' in shape_analysis
        assert 'kurtosis' in shape_analysis
        
        expected_shapes = ['balanced', 'trending', 'double_distribution', 'irregular', 'semi_balanced']
        assert shape_analysis['shape'] in expected_shapes
        assert 0 <= shape_analysis['balance_score'] <= 100
    
    def test_volume_profile_signals(self, sample_price_data, sample_volume_data):
        """Test volume profile signal generation."""
        profiler = VolumeProfileBuilder()
        result = profiler.build_volume_profile(sample_price_data, sample_volume_data)
        
        signals = result['signals']
        expected_signal_types = ['breakout_signals', 'rejection_signals', 
                               'rotation_signals', 'profile_edge_signals']
        
        for signal_type in expected_signal_types:
            assert signal_type in signals
        
        assert 'total_signals' in signals
        assert 'signal_quality' in signals
    
    def test_high_volume_nodes(self, sample_price_data, sample_volume_data):
        """Test high-volume node identification."""
        profiler = VolumeProfileBuilder()
        result = profiler.build_volume_profile(sample_price_data, sample_volume_data)
        
        hv_nodes = result['high_volume_nodes']
        assert isinstance(hv_nodes, list)
        
        if hv_nodes:
            node = hv_nodes[0]
            assert 'price' in node
            assert 'volume' in node
            assert 'volume_percentage' in node
            assert 'strength' in node
    
    def test_session_profiles(self, sample_price_data, sample_volume_data):
        """Test session-based volume profile construction."""
        profiler = VolumeProfileBuilder()
        
        # Test daily profiles
        result = profiler.build_session_profiles(
            sample_price_data, sample_volume_data, 'daily'
        )
        
        assert 'session_profiles' in result
        assert 'total_sessions' in result
        assert 'session_definition' in result
        assert 'profile_evolution' in result


class TestWyckoffVolumeIntegrator(TestVolumeAnalysisBase):
    """Test Wyckoff-Volume integration."""
    
    def test_integrator_initialization(self):
        """Test Wyckoff-Volume integrator initialization."""
        integrator = WyckoffVolumeIntegrator()
        
        # Check all components are initialized
        assert integrator.spike_detector is not None
        assert integrator.divergence_detector is not None
        assert integrator.ad_line_analyzer is not None
        assert integrator.vwap_analyzer is not None
        assert integrator.volume_classifier is not None
        assert integrator.volume_profiler is not None
        
        # Check pattern weights are configured
        assert 'accumulation' in integrator.wyckoff_volume_weights
        assert 'distribution' in integrator.wyckoff_volume_weights
        assert 'spring' in integrator.wyckoff_volume_weights
        assert 'upthrust' in integrator.wyckoff_volume_weights
    
    def test_enhance_wyckoff_pattern_basic(self, sample_price_data, sample_volume_data):
        """Test basic Wyckoff pattern enhancement."""
        integrator = WyckoffVolumeIntegrator()
        
        # Create mock Wyckoff pattern
        wyckoff_pattern = {
            'type': 'accumulation',
            'confidence': 70,
            'start_time': sample_price_data.index[10],
            'end_time': sample_price_data.index[20],
            'key_levels': [100, 105, 110]
        }
        
        result = integrator.enhance_wyckoff_pattern(
            wyckoff_pattern, sample_price_data, sample_volume_data
        )
        
        # Should have enhanced fields
        assert 'volume_analysis' in result
        assert 'volume_confirmation' in result
        assert 'enhanced_confidence' in result
        assert 'volume_signals' in result
        assert 'risk_assessment' in result
        assert 'volume_enhancement_applied' in result
        
        # Original pattern fields should be preserved
        assert result['type'] == 'accumulation'
        assert result['confidence'] == 70
    
    def test_volume_confirmation_scoring(self, sample_price_data, sample_volume_data):
        """Test volume confirmation scoring for different patterns."""
        integrator = WyckoffVolumeIntegrator()
        
        # Test accumulation pattern
        accumulation_pattern = {'type': 'accumulation', 'confidence': 60}
        result_acc = integrator.enhance_wyckoff_pattern(
            accumulation_pattern, sample_price_data, sample_volume_data
        )
        
        volume_confirmation = result_acc['volume_confirmation']
        assert 'confirmation_score' in volume_confirmation
        assert 'factors' in volume_confirmation
        assert 'pattern_type' in volume_confirmation
        assert 0 <= volume_confirmation['confirmation_score'] <= 100
        
        # Test spring pattern
        spring_pattern = {'type': 'spring', 'confidence': 65}
        result_spring = integrator.enhance_wyckoff_pattern(
            spring_pattern, sample_price_data, sample_volume_data
        )
        
        spring_confirmation = result_spring['volume_confirmation']
        assert spring_confirmation['pattern_type'] == 'spring'
    
    def test_enhanced_confidence_calculation(self, sample_price_data, sample_volume_data):
        """Test enhanced confidence calculation."""
        integrator = WyckoffVolumeIntegrator()
        
        wyckoff_pattern = {
            'type': 'distribution',
            'confidence': 50
        }
        
        result = integrator.enhance_wyckoff_pattern(
            wyckoff_pattern, sample_price_data, sample_volume_data
        )
        
        enhanced_confidence = result['enhanced_confidence']
        assert 'score' in enhanced_confidence
        assert 'level' in enhanced_confidence
        assert 'original_confidence' in enhanced_confidence
        assert 'enhancement_factor' in enhanced_confidence
        
        # Enhanced confidence should be reasonable
        assert 0 <= enhanced_confidence['score'] <= 100
        assert enhanced_confidence['level'] in ['low', 'medium', 'high']
        assert enhanced_confidence['original_confidence'] == 50
    
    def test_volume_enhanced_signals(self, sample_price_data, sample_volume_data):
        """Test volume-enhanced signal generation."""
        integrator = WyckoffVolumeIntegrator()
        
        wyckoff_pattern = {
            'type': 'spring',
            'confidence': 75
        }
        
        result = integrator.enhance_wyckoff_pattern(
            wyckoff_pattern, sample_price_data, sample_volume_data
        )
        
        volume_signals = result['volume_signals']
        expected_signal_types = ['entry_signals', 'exit_signals', 'risk_signals', 'confirmation_signals']
        
        for signal_type in expected_signal_types:
            assert signal_type in volume_signals
            assert isinstance(volume_signals[signal_type], list)
    
    def test_risk_assessment(self, sample_price_data, sample_volume_data):
        """Test volume-based risk assessment."""
        integrator = WyckoffVolumeIntegrator()
        
        wyckoff_pattern = {
            'type': 'upthrust',
            'confidence': 80
        }
        
        result = integrator.enhance_wyckoff_pattern(
            wyckoff_pattern, sample_price_data, sample_volume_data
        )
        
        risk_assessment = result['risk_assessment']
        assert 'risk_level' in risk_assessment
        assert 'risk_score' in risk_assessment
        assert 'risk_factors' in risk_assessment
        
        risk_levels = ['very_low', 'low', 'medium', 'high']
        assert risk_assessment['risk_level'] in risk_levels
        assert 0 <= risk_assessment['risk_score'] <= 100
        assert isinstance(risk_assessment['risk_factors'], list)
    
    def test_integration_error_handling(self):
        """Test error handling in integration."""
        integrator = WyckoffVolumeIntegrator()
        
        # Test with invalid data
        result = integrator.enhance_wyckoff_pattern(None, None, None)
        assert 'error' in result
        
        # Test with mismatched data
        dates = pd.date_range('2024-01-01', periods=10, freq='H')
        price_data = pd.DataFrame({
            'open': range(10), 'high': range(1, 11), 
            'low': range(10), 'close': range(10)
        }, index=dates)
        volume_data = pd.Series(range(5))  # Different length
        
        wyckoff_pattern = {'type': 'test', 'confidence': 50}
        result = integrator.enhance_wyckoff_pattern(wyckoff_pattern, price_data, volume_data)
        assert 'error' in result


class TestVolumeAnalysisIntegration(TestVolumeAnalysisBase):
    """Test integration between different volume analysis components."""
    
    def test_component_compatibility(self, sample_price_data, sample_volume_data):
        """Test that all components can work with the same data."""
        # Initialize all components
        spike_detector = VolumeSpikeDetector()
        divergence_detector = VolumeDivergenceDetector()
        ad_analyzer = AccumulationDistributionLine()
        vwap_analyzer = VWAPAnalyzer()
        classifier = VolumeClassifier()
        profiler = VolumeProfileBuilder()
        
        # Test each component with same data
        spike_result = spike_detector.detect_volume_spikes(sample_price_data, sample_volume_data)
        div_result = divergence_detector.detect_divergences(sample_price_data, sample_volume_data)
        ad_result = ad_analyzer.calculate_ad_line(sample_price_data, sample_volume_data)
        vwap_result = vwap_analyzer.calculate_vwap_with_bands(sample_price_data, sample_volume_data)
        class_result = classifier.classify_volume_type(sample_price_data, sample_volume_data)
        profile_result = profiler.build_volume_profile(sample_price_data, sample_volume_data)
        
        # All should complete without errors
        assert 'error' not in spike_result
        assert 'error' not in div_result
        assert 'error' not in ad_result
        assert 'error' not in vwap_result
        assert 'error' not in class_result
        assert 'error' not in profile_result
    
    def test_comprehensive_analysis_workflow(self, sample_price_data, sample_volume_data):
        """Test complete volume analysis workflow."""
        integrator = WyckoffVolumeIntegrator()
        
        # Simulate comprehensive analysis
        wyckoff_pattern = {
            'type': 'accumulation',
            'confidence': 65,
            'phase': 'C',
            'start_time': sample_price_data.index[0],
            'end_time': sample_price_data.index[-1]
        }
        
        enhanced_pattern = integrator.enhance_wyckoff_pattern(
            wyckoff_pattern, sample_price_data, sample_volume_data
        )
        
        # Verify comprehensive analysis was performed
        assert 'volume_analysis' in enhanced_pattern
        volume_analysis = enhanced_pattern['volume_analysis']
        
        # All major components should be present
        expected_components = ['spikes', 'divergences', 'accumulation_distribution', 
                              'vwap', 'classification', 'profile']
        for component in expected_components:
            assert component in volume_analysis
        
        # Summary should be generated
        assert 'summary' in volume_analysis
        summary = volume_analysis['summary']
        assert 'components_analyzed' in summary
        assert 'analysis_completeness' in summary


# Pytest configuration and fixtures
@pytest.fixture
def sample_data_factory():
    """Factory for creating test data with different characteristics."""
    def create_data(periods=100, volatility=0.5, volume_base=1000, add_spikes=True):
        dates = pd.date_range('2024-01-01', periods=periods, freq='H')
        
        # Create price data
        base_price = 100.0
        price_changes = np.random.normal(0, volatility, periods).cumsum()
        
        price_data = []
        for i, date in enumerate(dates):
            open_price = base_price + price_changes[i]
            high_price = open_price + abs(np.random.normal(0, volatility * 0.5))
            low_price = open_price - abs(np.random.normal(0, volatility * 0.5))
            close_price = open_price + np.random.normal(0, volatility * 0.3)
            
            high_price = max(high_price, open_price, close_price)
            low_price = min(low_price, open_price, close_price)
            
            price_data.append({
                'open': open_price, 'high': high_price,
                'low': low_price, 'close': close_price
            })
        
        price_df = pd.DataFrame(price_data, index=dates)
        
        # Create volume data
        volumes = []
        for i in range(periods):
            if add_spikes and i in [periods//4, periods//2, 3*periods//4]:
                volume = volume_base * np.random.uniform(3, 5)
            else:
                volume = volume_base * np.random.uniform(0.8, 1.2)
            volumes.append(volume)
        
        volume_series = pd.Series(volumes, index=dates)
        
        return price_df, volume_series
    
    return create_data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])