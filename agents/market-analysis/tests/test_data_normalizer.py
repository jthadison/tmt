"""Tests for data normalization engine."""

from datetime import datetime
from decimal import Decimal

import pytest

from app.market_data.data_normalizer import (
    DataNormalizer,
    MarketTick
)


@pytest.fixture
def normalizer():
    """Create DataNormalizer instance for testing."""
    return DataNormalizer()


@pytest.fixture
def sample_market_tick():
    """Create sample MarketTick for testing."""
    return MarketTick(
        symbol="EUR_USD",
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        timeframe="1m",
        open=Decimal("1.1000"),
        high=Decimal("1.1010"),
        low=Decimal("1.0990"),
        close=Decimal("1.1005"),
        volume=1000,
        source="oanda"
    )


def test_market_tick_validation(sample_market_tick):
    """Test MarketTick validation logic."""
    # Valid tick should not raise exception
    assert sample_market_tick.symbol == "EUR_USD"
    
    # Test invalid prices (negative)
    with pytest.raises(ValueError, match="All prices must be positive"):
        MarketTick(
            symbol="EUR_USD",
            timestamp=datetime.now(),
            timeframe="1m",
            open=Decimal("-1.1000"),
            high=Decimal("1.1010"),
            low=Decimal("1.0990"),
            close=Decimal("1.1005"),
            volume=1000,
            source="oanda"
        )
    
    # Test invalid volume (negative)
    with pytest.raises(ValueError, match="Volume must be non-negative integer"):
        MarketTick(
            symbol="EUR_USD",
            timestamp=datetime.now(),
            timeframe="1m",
            open=Decimal("1.1000"),
            high=Decimal("1.1010"),
            low=Decimal("1.0990"),
            close=Decimal("1.1005"),
            volume=-100,
            source="oanda"
        )


def test_market_tick_to_dict(sample_market_tick):
    """Test MarketTick to dictionary conversion."""
    tick_dict = sample_market_tick.to_dict()
    
    assert tick_dict['symbol'] == "EUR_USD"
    assert tick_dict['timestamp'] == "2024-01-01T12:00:00"
    assert tick_dict['timeframe'] == "1m"
    assert tick_dict['open'] == 1.1000
    assert tick_dict['high'] == 1.1010
    assert tick_dict['low'] == 1.0990
    assert tick_dict['close'] == 1.1005
    assert tick_dict['volume'] == 1000
    assert tick_dict['source'] == "oanda"


def test_market_tick_from_dict():
    """Test MarketTick creation from dictionary."""
    data = {
        'symbol': "EUR_USD",
        'timestamp': "2024-01-01T12:00:00Z",
        'timeframe': "1m",
        'open': 1.1000,
        'high': 1.1010,
        'low': 1.0990,
        'close': 1.1005,
        'volume': 1000,
        'source': "oanda"
    }
    
    tick = MarketTick.from_dict(data)
    
    assert tick.symbol == "EUR_USD"
    assert tick.open == Decimal("1.1000")
    assert tick.volume == 1000


def test_normalize_oanda_candle(normalizer):
    """Test OANDA candle data normalization."""
    raw_data = {
        'time': '2024-01-01T12:00:00Z',
        'mid': {
            'o': '1.1000',
            'h': '1.1010',
            'l': '1.0990',
            'c': '1.1005'
        },
        'volume': 0
    }
    
    tick = normalizer.normalize_oanda_candle(raw_data, "EUR_USD")
    
    assert tick.symbol == "EUR_USD"
    assert tick.open == Decimal("1.1000")
    assert tick.high == Decimal("1.1010")
    assert tick.low == Decimal("1.0990")
    assert tick.close == Decimal("1.1005")
    assert tick.volume == 0
    assert tick.source == "oanda"


def test_normalize_oanda_tick(normalizer):
    """Test OANDA tick data normalization."""
    raw_data = {
        'symbol': 'EUR_USD',
        'timestamp': '2024-01-01T12:00:00Z',
        'mid': 1.1005
    }
    
    tick = normalizer.normalize_oanda_tick(raw_data)
    
    assert tick.symbol == "EUR_USD"
    assert tick.open == Decimal("1.1005")
    assert tick.high == Decimal("1.1005")
    assert tick.low == Decimal("1.1005")
    assert tick.close == Decimal("1.1005")
    assert tick.timeframe == "tick"
    assert tick.source == "oanda"


def test_normalize_polygon_aggregate(normalizer):
    """Test Polygon aggregate data normalization."""
    raw_data = {
        't': 1704110400000,  # 2024-01-01T12:00:00Z in milliseconds
        'o': 100.0,
        'h': 101.0,
        'l': 99.0,
        'c': 100.5,
        'v': 1000000
    }
    
    tick = normalizer.normalize_polygon_aggregate(raw_data, "AAPL")
    
    assert tick.symbol == "AAPL"
    assert tick.open == Decimal("100.0")
    assert tick.high == Decimal("101.0")
    assert tick.low == Decimal("99.0")
    assert tick.close == Decimal("100.5")
    assert tick.volume == 1000000
    assert tick.source == "polygon"


def test_normalize_polygon_trade(normalizer):
    """Test Polygon trade data normalization."""
    raw_data = {
        'symbol': 'AAPL',
        'timestamp': '2024-01-01T12:00:00Z',
        'price': 100.5,
        'volume': 100
    }
    
    tick = normalizer.normalize_polygon_trade(raw_data)
    
    assert tick.symbol == "AAPL"
    assert tick.open == Decimal("100.5")
    assert tick.high == Decimal("100.5")
    assert tick.low == Decimal("100.5")
    assert tick.close == Decimal("100.5")
    assert tick.volume == 100
    assert tick.timeframe == "tick"
    assert tick.source == "polygon"


def test_deduplication(normalizer, sample_market_tick):
    """Test tick deduplication functionality."""
    # First tick should be new
    assert normalizer.deduplicate_tick(sample_market_tick) is True
    
    # Same tick should be detected as duplicate
    assert normalizer.deduplicate_tick(sample_market_tick) is False
    
    # Different timestamp should be new
    different_tick = MarketTick(
        symbol="EUR_USD",
        timestamp=datetime(2024, 1, 1, 12, 1, 0),  # Different timestamp
        timeframe="1m",
        open=Decimal("1.1000"),
        high=Decimal("1.1010"),
        low=Decimal("1.0990"),
        close=Decimal("1.1005"),
        volume=1000,
        source="oanda"
    )
    assert normalizer.deduplicate_tick(different_tick) is True


def test_data_quality_validation(normalizer, sample_market_tick):
    """Test data quality validation."""
    # Valid tick should pass
    assert normalizer.validate_data_quality(sample_market_tick) is True
    
    # Invalid tick (high < close) should fail
    invalid_tick = MarketTick(
        symbol="EUR_USD",
        timestamp=datetime.now(),
        timeframe="1m",
        open=Decimal("1.1000"),
        high=Decimal("1.0990"),  # High less than close
        low=Decimal("1.0985"),
        close=Decimal("1.1005"),
        volume=1000,
        source="oanda"
    )
    assert normalizer.validate_data_quality(invalid_tick) is False


def test_statistics(normalizer):
    """Test processing statistics tracking."""
    initial_stats = normalizer.get_statistics()
    assert initial_stats['processed_count'] == 0
    assert initial_stats['error_count'] == 0
    assert initial_stats['duplicate_count'] == 0
    
    # Process valid data
    raw_data = {
        'time': '2024-01-01T12:00:00Z',
        'mid': {'o': '1.1000', 'h': '1.1010', 'l': '1.0990', 'c': '1.1005'}
    }
    normalizer.normalize_oanda_candle(raw_data, "EUR_USD")
    
    stats = normalizer.get_statistics()
    assert stats['processed_count'] == 1
    
    # Reset statistics
    normalizer.reset_statistics()
    stats = normalizer.get_statistics()
    assert stats['processed_count'] == 0


def test_error_handling(normalizer):
    """Test error handling for invalid data."""
    # Invalid OANDA data
    with pytest.raises(ValueError, match="Invalid OANDA data format"):
        normalizer.normalize_oanda_candle({}, "EUR_USD")
    
    # Invalid Polygon data
    with pytest.raises(ValueError, match="Invalid Polygon data format"):
        normalizer.normalize_polygon_aggregate({}, "AAPL")
    
    stats = normalizer.get_statistics()
    assert stats['error_count'] == 2