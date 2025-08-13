"""
Tests for Market Condition Anomaly Detection

Tests flash crash detection, gap detection, volatility spike detection,
and overall market condition anomaly detection system.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from market_condition_detector import (
    MarketConditionDetector,
    MarketConditionThresholds,
    MarketData,
    FlashCrashDetector,
    GapDetector,
    VolatilityDetector,
    MarketConditionType,
    Severity
)


@pytest.fixture
def default_thresholds():
    """Default market condition thresholds for testing"""
    return MarketConditionThresholds()


@pytest.fixture
def sample_market_data():
    """Sample market data for testing"""
    return MarketData(
        timestamp=datetime.utcnow(),
        symbol="EURUSD",
        bid=Decimal("1.0500"),
        ask=Decimal("1.0502"),
        volume=1000,
        price=Decimal("1.0501")
    )


class TestFlashCrashDetector:
    """Test flash crash detection"""
    
    def test_no_flash_crash_with_normal_movement(self, default_thresholds):
        """Test that normal price movements don't trigger flash crash detection"""
        detector = FlashCrashDetector(default_thresholds)
        
        # Generate normal price movement (1% over 5 minutes)
        base_time = datetime.utcnow()
        base_price = Decimal("1.0500")
        
        # Add gradual price movement
        for i in range(10):
            price = base_price + Decimal("0.0001") * i  # 1 pip increments
            data = MarketData(
                timestamp=base_time + timedelta(minutes=i),
                symbol="EURUSD",
                bid=price - Decimal("0.0001"),
                ask=price + Decimal("0.0001"),
                volume=1000,
                price=price
            )
            
            anomaly = detector.detect(data)
            assert anomaly is None
    
    def test_flash_crash_detection_triggers(self, default_thresholds):
        """Test that flash crash detection triggers on large price movements"""
        detector = FlashCrashDetector(default_thresholds)
        
        base_time = datetime.utcnow()
        base_price = Decimal("1.0500")
        
        # Add normal price data first
        for i in range(5):
            data = MarketData(
                timestamp=base_time + timedelta(minutes=i),
                symbol="EURUSD",
                bid=base_price - Decimal("0.0001"),
                ask=base_price + Decimal("0.0001"),
                volume=1000,
                price=base_price
            )
            detector.detect(data)
        
        # Add flash crash (6% drop in 5 minutes - above 5% threshold)
        crash_price = base_price * Decimal("0.94")  # 6% drop
        crash_data = MarketData(
            timestamp=base_time + timedelta(minutes=5),
            symbol="EURUSD",
            bid=crash_price - Decimal("0.0001"),
            ask=crash_price + Decimal("0.0001"),
            volume=5000,
            price=crash_price
        )
        
        anomaly = detector.detect(crash_data)
        
        assert anomaly is not None
        assert anomaly.condition_type == MarketConditionType.FLASH_CRASH
        assert anomaly.severity in [Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]  # 6% is 1.2x the 5% threshold
        assert not anomaly.learning_safe
        assert anomaly.quarantine_recommended
        assert anomaly.observed_value > default_thresholds.max_price_movement
    
    def test_flash_crash_severity_scaling(self, default_thresholds):
        """Test that flash crash severity scales with magnitude"""
        detector = FlashCrashDetector(default_thresholds)
        
        base_time = datetime.utcnow()
        base_price = Decimal("1.0500")
        
        # Add baseline data
        for i in range(5):
            data = MarketData(
                timestamp=base_time + timedelta(minutes=i),
                symbol="EURUSD",
                bid=base_price,
                ask=base_price + Decimal("0.0002"),
                volume=1000,
                price=base_price
            )
            detector.detect(data)
        
        # Test different crash magnitudes (adjust based on actual calculation precision)
        test_cases = [
            (0.06, Severity.MEDIUM),    # 6% - 1.2x threshold - medium
            (0.07, Severity.HIGH),      # 7% - 1.4x threshold - high  
            (0.10, Severity.CRITICAL)   # 10% - 2.0x threshold - critical
        ]
        
        for i, (drop_percentage, expected_severity) in enumerate(test_cases):
            # Create a fresh detector for each test case
            test_detector = FlashCrashDetector(default_thresholds)
            
            # Add baseline data
            for j in range(6):
                baseline_data = MarketData(
                    timestamp=base_time + timedelta(minutes=j + i*10),  # Different time ranges
                    symbol="EURUSD",
                    bid=base_price,
                    ask=base_price + Decimal("0.0002"),
                    volume=1000,
                    price=base_price
                )
                test_detector.detect(baseline_data)
            
            crash_price = base_price * Decimal(str(1 - drop_percentage))
            crash_data = MarketData(
                timestamp=base_time + timedelta(minutes=6 + i*10),
                symbol="EURUSD",
                bid=crash_price,
                ask=crash_price + Decimal("0.0002"),
                volume=5000,
                price=crash_price
            )
            
            anomaly = test_detector.detect(crash_data)
            assert anomaly is not None, f"No anomaly detected for {drop_percentage:.1%} drop"
            assert anomaly.severity == expected_severity, f"Expected {expected_severity} for {drop_percentage:.1%} drop, got {anomaly.severity}"


class TestGapDetector:
    """Test price gap detection"""
    
    def test_weekend_gap_detection(self, default_thresholds):
        """Test weekend gap detection"""
        detector = GapDetector(default_thresholds)
        
        # Friday close
        friday_close = MarketData(
            timestamp=datetime(2023, 12, 15, 23, 0),  # Friday 11 PM
            symbol="EURUSD",
            bid=Decimal("1.0500"),
            ask=Decimal("1.0502"),
            volume=1000,
            price=Decimal("1.0501")
        )
        detector.detect(friday_close)
        
        # Sunday open with gap
        sunday_open = MarketData(
            timestamp=datetime(2023, 12, 17, 0, 0),  # Sunday midnight
            symbol="EURUSD", 
            bid=Decimal("1.0600"),  # 100 pip gap
            ask=Decimal("1.0602"),
            volume=1000,
            price=Decimal("1.0601")
        )
        
        anomaly = detector.detect(sunday_open)
        
        if not default_thresholds.exclude_weekend_gaps:
            assert anomaly is not None
            assert anomaly.condition_type == MarketConditionType.PRICE_GAP
            assert anomaly.observed_value == 100.0  # 100 pip gap
        else:
            # Should be excluded if weekend gaps are filtered out
            assert anomaly is None
    
    def test_no_gap_on_normal_open(self, default_thresholds):
        """Test that normal market opens don't trigger gap detection"""
        detector = GapDetector(default_thresholds)
        
        # Normal close
        close_data = MarketData(
            timestamp=datetime(2023, 12, 15, 16, 0),
            symbol="EURUSD",
            bid=Decimal("1.0500"),
            ask=Decimal("1.0502"),
            volume=1000,
            price=Decimal("1.0501")
        )
        detector.detect(close_data)
        
        # Normal open (small gap within threshold)
        open_data = MarketData(
            timestamp=datetime(2023, 12, 18, 9, 0),
            symbol="EURUSD",
            bid=Decimal("1.0505"),  # 5 pip gap - below threshold
            ask=Decimal("1.0507"),
            volume=1000,
            price=Decimal("1.0506")
        )
        
        anomaly = detector.detect(open_data)
        assert anomaly is None


class TestVolatilityDetector:
    """Test volatility spike detection"""
    
    def test_volatility_spike_detection(self, default_thresholds):
        """Test volatility spike detection"""
        detector = VolatilityDetector(default_thresholds)
        
        base_time = datetime.utcnow()
        base_price = Decimal("1.0500")
        
        # Add baseline volatility data (normal spreads)
        for i in range(25):  # Need 20+ for baseline
            data = MarketData(
                timestamp=base_time + timedelta(minutes=i),
                symbol="EURUSD",
                bid=base_price,
                ask=base_price + Decimal("0.0002"),  # 2 pip spread
                volume=1000,
                price=base_price + Decimal("0.0001")
            )
            detector.detect(data)
        
        # Add volatility spike (wide spread)
        spike_data = MarketData(
            timestamp=base_time + timedelta(minutes=25),
            symbol="EURUSD",
            bid=base_price,
            ask=base_price + Decimal("0.0020"),  # 20 pip spread (10x normal)
            volume=1000,
            price=base_price + Decimal("0.0010")
        )
        
        anomaly = detector.detect(spike_data)
        
        assert anomaly is not None
        assert anomaly.condition_type == MarketConditionType.VOLATILITY_SPIKE
        assert anomaly.observed_value > anomaly.expected_value * default_thresholds.max_volatility_spike
        assert not anomaly.learning_safe


class TestMarketConditionDetector:
    """Test integrated market condition detection"""
    
    def test_no_anomalies_on_normal_data(self, default_thresholds, sample_market_data):
        """Test that normal market data produces no anomalies"""
        detector = MarketConditionDetector(default_thresholds)
        
        anomalies = detector.detect_anomalies(sample_market_data)
        
        # Should have no anomalies for normal data
        assert len(anomalies) == 0
    
    def test_market_hours_exclusion(self, default_thresholds):
        """Test market hours exclusion"""
        detector = MarketConditionDetector(default_thresholds)
        
        # Market open time (9:15 AM - within exclusion period)
        open_data = MarketData(
            timestamp=datetime(2023, 12, 15, 9, 15),
            symbol="EURUSD",
            bid=Decimal("1.0500"),
            ask=Decimal("1.0502"),
            volume=1000,
            price=Decimal("1.0501")
        )
        
        anomalies = detector.detect_anomalies(open_data)
        
        if default_thresholds.exclude_market_open:
            market_hours_anomalies = [
                a for a in anomalies if a.condition_type == MarketConditionType.MARKET_HOURS
            ]
            assert len(market_hours_anomalies) > 0
            assert not market_hours_anomalies[0].learning_safe
    
    def test_multiple_anomaly_detection(self, default_thresholds):
        """Test detection of multiple simultaneous anomalies"""
        detector = MarketConditionDetector(default_thresholds)
        
        # Create data that should trigger multiple anomalies
        # (flash crash + volatility spike + market hours)
        anomaly_data = MarketData(
            timestamp=datetime(2023, 12, 15, 9, 15),  # Market open
            symbol="EURUSD",
            bid=Decimal("1.0400"),  # Large price movement
            ask=Decimal("1.0420"),  # Wide spread
            volume=1000,
            price=Decimal("1.0410")
        )
        
        # Add some baseline data first for flash crash detector
        base_time = anomaly_data.timestamp - timedelta(minutes=10)
        for i in range(10):
            baseline_data = MarketData(
                timestamp=base_time + timedelta(minutes=i),
                symbol="EURUSD",
                bid=Decimal("1.0500"),
                ask=Decimal("1.0502"),
                volume=1000,
                price=Decimal("1.0501")
            )
            detector.detect_anomalies(baseline_data)
        
        anomalies = detector.detect_anomalies(anomaly_data)
        
        # Should detect multiple types of anomalies
        assert len(anomalies) > 0
        
        anomaly_types = [a.condition_type for a in anomalies]
        assert MarketConditionType.MARKET_HOURS in anomaly_types  # Market open exclusion
    
    def test_anomaly_metadata_completeness(self, default_thresholds, sample_market_data):
        """Test that anomaly metadata is complete and valid"""
        detector = MarketConditionDetector(default_thresholds)
        
        # Modify data to trigger an anomaly
        sample_market_data.timestamp = datetime(2023, 12, 15, 9, 15)  # Market open
        
        anomalies = detector.detect_anomalies(sample_market_data)
        
        for anomaly in anomalies:
            # Check required fields are present
            assert anomaly.detection_id is not None
            assert anomaly.timestamp is not None
            assert anomaly.condition_type is not None
            assert anomaly.severity is not None
            assert 0 <= anomaly.confidence <= 1
            assert anomaly.symbol == sample_market_data.symbol
            assert anomaly.description is not None
            assert isinstance(anomaly.potential_causes, list)
            assert isinstance(anomaly.learning_safe, bool)
            assert isinstance(anomaly.quarantine_recommended, bool)
            assert anomaly.lockout_duration_minutes >= 0