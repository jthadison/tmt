"""Data normalization engine for converting market data to standard OHLCV format."""

import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MarketTick:
    """
    Standard OHLCV format for all market data sources.
    
    Provides consistent data structure across OANDA, Polygon.io,
    and any future data providers with proper validation.
    """
    symbol: str
    timestamp: datetime
    timeframe: str  # '1m', '5m', '1h', '4h', '1d'
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    source: str  # 'oanda', 'polygon'
    
    def __post_init__(self):
        """Validate data integrity after initialization."""
        self._validate_prices()
        self._validate_timestamp()
        self._validate_volume()
        
    def _validate_prices(self):
        """Ensure OHLC prices are logically consistent."""
        if not all(isinstance(price, Decimal) for price in [self.open, self.high, self.low, self.close]):
            raise ValueError("All prices must be Decimal type")
            
        if self.high < max(self.open, self.close):
            logger.warning(f"High price {self.high} less than max(open, close) for {self.symbol}")
            
        if self.low > min(self.open, self.close):
            logger.warning(f"Low price {self.low} greater than min(open, close) for {self.symbol}")
            
        if any(price <= 0 for price in [self.open, self.high, self.low, self.close]):
            raise ValueError("All prices must be positive")
            
    def _validate_timestamp(self):
        """Validate timestamp format and range."""
        if not isinstance(self.timestamp, datetime):
            raise ValueError("Timestamp must be datetime object")
            
        # Check if timestamp is reasonable (not too far in past/future)
        # Handle timezone-aware vs timezone-naive comparison
        if self.timestamp.tzinfo is not None:
            now = datetime.now(self.timestamp.tzinfo)
        else:
            now = datetime.now()
            
        if self.timestamp.year < 2000 or self.timestamp > now:
            logger.warning(f"Unusual timestamp {self.timestamp} for {self.symbol}")
            
    def _validate_volume(self):
        """Validate volume data."""
        if not isinstance(self.volume, int) or self.volume < 0:
            raise ValueError("Volume must be non-negative integer")
            
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert MarketTick to dictionary format.
        
        @returns: Dictionary representation with proper JSON serialization
        """
        return {
            'symbol': self.symbol,
            'timestamp': self.timestamp.isoformat(),
            'timeframe': self.timeframe,
            'open': float(self.open),
            'high': float(self.high),
            'low': float(self.low),
            'close': float(self.close),
            'volume': self.volume,
            'source': self.source
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MarketTick':
        """
        Create MarketTick from dictionary data.
        
        @param data: Dictionary containing market data
        @returns: MarketTick instance
        """
        return cls(
            symbol=data['symbol'],
            timestamp=datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00')),
            timeframe=data['timeframe'],
            open=Decimal(str(data['open'])),
            high=Decimal(str(data['high'])),
            low=Decimal(str(data['low'])),
            close=Decimal(str(data['close'])),
            volume=int(data['volume']),
            source=data['source']
        )


class DataNormalizer:
    """
    Data normalization engine for converting raw market data to standard format.
    
    Handles data transformation from multiple sources with validation,
    deduplication, and performance optimization for <50ms processing time.
    """
    
    def __init__(self):
        """Initialize data normalizer with validation settings."""
        self.processed_count = 0
        self.error_count = 0
        self.duplicate_count = 0
        
        # Deduplication cache (timestamp + symbol -> processed tick)
        self.processed_cache = {}
        self.cache_max_size = 10000
        
    def normalize_oanda_candle(self, raw_data: Dict[str, Any], symbol: str) -> MarketTick:
        """
        Normalize OANDA candlestick data to standard format.
        
        @param raw_data: Raw OANDA candle data
        @param symbol: Instrument symbol
        @returns: Normalized MarketTick
        @throws: ValueError on invalid data
        """
        try:
            # Extract OANDA-specific fields
            time_str = raw_data.get('time', '')
            mid_data = raw_data.get('mid', {})
            
            # Parse timestamp
            timestamp = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            
            # Extract OHLC from mid prices
            open_price = Decimal(str(mid_data.get('o', '0')))
            high_price = Decimal(str(mid_data.get('h', '0')))
            low_price = Decimal(str(mid_data.get('l', '0')))
            close_price = Decimal(str(mid_data.get('c', '0')))
            
            # OANDA doesn't provide volume for forex, use 0
            volume = int(raw_data.get('volume', 0))
            
            tick = MarketTick(
                symbol=symbol,
                timestamp=timestamp,
                timeframe='1m',  # Default timeframe
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=volume,
                source='oanda'
            )
            
            self.processed_count += 1
            return tick
            
        except (KeyError, ValueError, TypeError) as e:
            self.error_count += 1
            logger.error(f"Failed to normalize OANDA data: {e}, data: {raw_data}")
            raise ValueError(f"Invalid OANDA data format: {e}")
            
    def normalize_oanda_tick(self, raw_data: Dict[str, Any]) -> MarketTick:
        """
        Normalize OANDA price tick to standard format.
        
        @param raw_data: Raw OANDA price tick data
        @returns: Normalized MarketTick
        """
        try:
            symbol = raw_data.get('symbol', '')
            timestamp_str = raw_data.get('timestamp', '')
            
            # Parse timestamp
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            
            # For ticks, use mid price for all OHLC values
            mid_price = Decimal(str(raw_data.get('mid', '0')))
            
            tick = MarketTick(
                symbol=symbol,
                timestamp=timestamp,
                timeframe='tick',
                open=mid_price,
                high=mid_price,
                low=mid_price,
                close=mid_price,
                volume=0,  # No volume for forex ticks
                source='oanda'
            )
            
            self.processed_count += 1
            return tick
            
        except (KeyError, ValueError, TypeError) as e:
            self.error_count += 1
            logger.error(f"Failed to normalize OANDA tick: {e}, data: {raw_data}")
            raise ValueError(f"Invalid OANDA tick format: {e}")
            
    def normalize_polygon_aggregate(self, raw_data: Dict[str, Any], symbol: str) -> MarketTick:
        """
        Normalize Polygon.io aggregate data to standard format.
        
        @param raw_data: Raw Polygon aggregate data
        @param symbol: Ticker symbol
        @returns: Normalized MarketTick
        """
        try:
            # Extract Polygon-specific fields
            timestamp_ms = raw_data.get('t', 0)
            timestamp = datetime.fromtimestamp(timestamp_ms / 1000)
            
            open_price = Decimal(str(raw_data.get('o', '0')))
            high_price = Decimal(str(raw_data.get('h', '0')))
            low_price = Decimal(str(raw_data.get('l', '0')))
            close_price = Decimal(str(raw_data.get('c', '0')))
            volume = int(raw_data.get('v', 0))
            
            tick = MarketTick(
                symbol=symbol,
                timestamp=timestamp,
                timeframe='1m',  # Default timeframe
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=volume,
                source='polygon'
            )
            
            self.processed_count += 1
            return tick
            
        except (KeyError, ValueError, TypeError) as e:
            self.error_count += 1
            logger.error(f"Failed to normalize Polygon data: {e}, data: {raw_data}")
            raise ValueError(f"Invalid Polygon data format: {e}")
            
    def normalize_polygon_trade(self, raw_data: Dict[str, Any]) -> MarketTick:
        """
        Normalize Polygon.io trade data to standard format.
        
        @param raw_data: Raw Polygon trade data
        @returns: Normalized MarketTick
        """
        try:
            symbol = raw_data.get('symbol', '')
            timestamp_str = raw_data.get('timestamp', '')
            
            # Parse timestamp
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            
            # For trades, use price for all OHLC values
            price = Decimal(str(raw_data.get('price', '0')))
            volume = int(raw_data.get('volume', 0))
            
            tick = MarketTick(
                symbol=symbol,
                timestamp=timestamp,
                timeframe='tick',
                open=price,
                high=price,
                low=price,
                close=price,
                volume=volume,
                source='polygon'
            )
            
            self.processed_count += 1
            return tick
            
        except (KeyError, ValueError, TypeError) as e:
            self.error_count += 1
            logger.error(f"Failed to normalize Polygon trade: {e}, data: {raw_data}")
            raise ValueError(f"Invalid Polygon trade format: {e}")
            
    def deduplicate_tick(self, tick: MarketTick) -> bool:
        """
        Check if tick is a duplicate and add to cache if new.
        
        @param tick: MarketTick to check for duplication
        @returns: True if new tick, False if duplicate
        """
        cache_key = f"{tick.symbol}_{tick.timestamp.isoformat()}"
        
        if cache_key in self.processed_cache:
            self.duplicate_count += 1
            return False
            
        # Add to cache
        self.processed_cache[cache_key] = tick
        
        # Maintain cache size limit
        if len(self.processed_cache) > self.cache_max_size:
            # Remove oldest entries (FIFO)
            oldest_keys = list(self.processed_cache.keys())[:1000]
            for key in oldest_keys:
                del self.processed_cache[key]
                
        return True
        
    def validate_data_quality(self, tick: MarketTick) -> bool:
        """
        Perform data quality validation on normalized tick.
        
        @param tick: MarketTick to validate
        @returns: True if data passes quality checks
        """
        try:
            # Price validation
            if any(price <= 0 for price in [tick.open, tick.high, tick.low, tick.close]):
                logger.warning(f"Invalid prices detected for {tick.symbol}")
                return False
                
            # Price relationship validation
            if tick.high < max(tick.open, tick.close):
                logger.warning(f"High < max(open, close) for {tick.symbol}")
                return False
                
            if tick.low > min(tick.open, tick.close):
                logger.warning(f"Low > min(open, close) for {tick.symbol}")
                return False
                
            # Volume validation (allow 0 for forex)
            if tick.volume < 0:
                logger.warning(f"Negative volume for {tick.symbol}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Data quality validation error: {e}")
            return False
            
    def get_statistics(self) -> Dict[str, int]:
        """
        Get processing statistics.
        
        @returns: Dictionary with processing metrics
        """
        return {
            'processed_count': self.processed_count,
            'error_count': self.error_count,
            'duplicate_count': self.duplicate_count,
            'cache_size': len(self.processed_cache)
        }
        
    def reset_statistics(self):
        """Reset all processing statistics."""
        self.processed_count = 0
        self.error_count = 0
        self.duplicate_count = 0
        self.processed_cache.clear()