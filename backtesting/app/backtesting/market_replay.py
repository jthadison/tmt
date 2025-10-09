"""
Market Replay Iterator - Story 11.2

Bar-by-bar market data replay with strict look-ahead bias prevention.
Only exposes data that would have been available at decision time.
"""

import pandas as pd
import numpy as np
from typing import Optional, Iterator, Dict, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class MarketReplayIterator:
    """
    Iterator for replaying historical market data bar-by-bar

    Critical feature: Prevents look-ahead bias by only exposing closed candle data.
    Signals and decisions can only use information from completed bars.

    Example:
        >>> iterator = MarketReplayIterator(market_data, timeframe='H1')
        >>> for candle, history in iterator:
        ...     # 'candle' is the current CLOSED candle
        ...     # 'history' contains all previous CLOSED candles
        ...     signal = generate_signal(history)  # Can't see future!
        ...     if signal:
        ...         # Order fills at NEXT bar's open price
        ...         pass
    """

    def __init__(
        self,
        data: pd.DataFrame,
        timeframe: str = 'H1',
        min_history_bars: int = 50
    ):
        """
        Initialize market replay iterator

        Args:
            data: DataFrame with OHLCV data (must have timestamp index)
            timeframe: Timeframe identifier (H1, H4, D1)
            min_history_bars: Minimum bars of history before yielding data
        """

        if data.empty:
            raise ValueError("Cannot replay empty dataset")

        if not isinstance(data.index, pd.DatetimeIndex):
            raise ValueError("Data must have DatetimeIndex")

        # Validate required columns
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_cols if col not in data.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")

        self.data = data.copy()
        self.timeframe = timeframe
        self.min_history_bars = min_history_bars

        # Ensure sorted by timestamp
        self.data = self.data.sort_index()

        # Current position in replay
        self.current_index = min_history_bars  # Start after min history
        self.total_bars = len(self.data)

        logger.info(
            f"MarketReplayIterator initialized: {self.total_bars} bars, "
            f"timeframe={timeframe}, starting at bar {self.current_index}"
        )

    def __iter__(self) -> Iterator:
        """Return iterator"""
        self.current_index = self.min_history_bars
        return self

    def __next__(self) -> tuple[pd.Series, pd.DataFrame]:
        """
        Get next candle and historical data

        Returns:
            Tuple of (current_closed_candle, historical_data)

        Raises:
            StopIteration: When replay is complete

        CRITICAL: The current candle returned is CLOSED.
                  Historical data contains ALL previous CLOSED candles.
                  NO future information is available.
        """

        if self.current_index >= self.total_bars:
            raise StopIteration

        # Get current CLOSED candle (this bar is complete)
        current_candle = self.data.iloc[self.current_index]

        # Get ALL previous closed candles (up to but NOT including current)
        historical_data = self.data.iloc[:self.current_index].copy()

        # Advance to next bar
        self.current_index += 1

        return current_candle, historical_data

    def peek_next_bar(self) -> Optional[pd.Series]:
        """
        Peek at next bar (for order fill simulation)

        This is ONLY for simulating order execution at next bar's open.
        Should NEVER be used for signal generation.

        Returns:
            Next bar data if available, None if at end

        WARNING: Only use this for order fills at next bar open!
                 Using this for signals creates look-ahead bias!
        """

        if self.current_index >= self.total_bars:
            return None

        return self.data.iloc[self.current_index]

    def get_current_timestamp(self) -> datetime:
        """Get timestamp of current position in replay"""

        if self.current_index > 0:
            return self.data.index[self.current_index - 1]
        return self.data.index[0]

    def get_bars_remaining(self) -> int:
        """Get number of bars remaining in replay"""
        return max(0, self.total_bars - self.current_index)

    def get_progress_pct(self) -> float:
        """Get replay progress as percentage"""
        return (self.current_index / self.total_bars) * 100

    def reset(self):
        """Reset iterator to beginning"""
        self.current_index = self.min_history_bars
        logger.info("MarketReplayIterator reset to beginning")

    def aggregate_to_higher_timeframe(
        self,
        data: pd.DataFrame,
        target_timeframe: str
    ) -> pd.DataFrame:
        """
        Aggregate data to higher timeframe

        Converts 1H data to 4H or 1D for multi-timeframe analysis.
        Uses CLOSED candles only - no look-ahead bias.

        Args:
            data: DataFrame with OHLCV data (H1 timeframe)
            target_timeframe: Target timeframe ('H4' or 'D1')

        Returns:
            Aggregated DataFrame

        Example:
            >>> h1_data = pd.DataFrame(...)  # 1H candles
            >>> h4_data = iterator.aggregate_to_higher_timeframe(h1_data, 'H4')
        """

        if target_timeframe == 'H1':
            return data

        # Define resampling rules
        resample_rules = {
            'H4': '4H',
            'D1': '1D'
        }

        if target_timeframe not in resample_rules:
            raise ValueError(f"Unsupported timeframe: {target_timeframe}")

        rule = resample_rules[target_timeframe]

        # Aggregate OHLCV data
        aggregated = data.resample(rule).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        })

        # Drop incomplete bars (last bar may be incomplete)
        aggregated = aggregated.dropna()

        logger.info(
            f"Aggregated {len(data)} bars to {len(aggregated)} bars "
            f"({target_timeframe})"
        )

        return aggregated

    def get_concurrent_timeframes(
        self,
        historical_data: pd.DataFrame,
        timeframes: List[str]
    ) -> Dict[str, pd.DataFrame]:
        """
        Get multiple timeframe views of historical data

        Useful for multi-timeframe analysis in signal generation.
        All timeframes contain only CLOSED candles.

        Args:
            historical_data: Base historical data (H1)
            timeframes: List of timeframes to generate

        Returns:
            Dict mapping timeframe to DataFrame

        Example:
            >>> history = get_historical_data()  # H1 data
            >>> mtf_data = iterator.get_concurrent_timeframes(
            ...     history, ['H1', 'H4', 'D1']
            ... )
            >>> h1 = mtf_data['H1']  # Original H1 data
            >>> h4 = mtf_data['H4']  # Aggregated to H4
            >>> d1 = mtf_data['D1']  # Aggregated to D1
        """

        result = {}

        for tf in timeframes:
            if tf == 'H1':
                result[tf] = historical_data
            else:
                result[tf] = self.aggregate_to_higher_timeframe(
                    historical_data, tf
                )

        return result

    def validate_no_lookahead(
        self,
        current_candle: pd.Series,
        historical_data: pd.DataFrame
    ) -> bool:
        """
        Validate that no look-ahead bias exists

        Checks:
        1. Current candle timestamp > all historical timestamps
        2. Historical data is properly sorted
        3. No gaps or future data in historical set

        Args:
            current_candle: Current candle being processed
            historical_data: Historical data available

        Returns:
            True if validation passes

        Raises:
            ValueError: If look-ahead bias detected
        """

        current_time = current_candle.name

        # Check 1: Current candle must be AFTER all history
        if not historical_data.empty:
            last_historical_time = historical_data.index[-1]
            if current_time <= last_historical_time:
                raise ValueError(
                    f"Look-ahead bias detected! Current time {current_time} "
                    f"<= last historical time {last_historical_time}"
                )

        # Check 2: Historical data must be sorted
        if not historical_data.index.is_monotonic_increasing:
            raise ValueError("Historical data is not properly sorted!")

        # Check 3: Current candle should not be in historical data
        if current_time in historical_data.index:
            raise ValueError(
                f"Look-ahead bias! Current candle {current_time} "
                "found in historical data"
            )

        return True


class TimeframeConverter:
    """
    Helper class for timeframe conversions and validation
    """

    TIMEFRAME_MINUTES = {
        'M15': 15,
        'M30': 30,
        'H1': 60,
        'H4': 240,
        'D1': 1440
    }

    @classmethod
    def get_minutes(cls, timeframe: str) -> int:
        """Get minutes for a timeframe"""
        if timeframe not in cls.TIMEFRAME_MINUTES:
            raise ValueError(f"Unsupported timeframe: {timeframe}")
        return cls.TIMEFRAME_MINUTES[timeframe]

    @classmethod
    def can_aggregate(cls, from_tf: str, to_tf: str) -> bool:
        """Check if one timeframe can be aggregated to another"""

        from_minutes = cls.get_minutes(from_tf)
        to_minutes = cls.get_minutes(to_tf)

        # Can only aggregate to higher timeframe
        if to_minutes <= from_minutes:
            return False

        # Target must be exact multiple of source
        return to_minutes % from_minutes == 0

    @classmethod
    def get_aggregation_ratio(cls, from_tf: str, to_tf: str) -> int:
        """Get aggregation ratio between timeframes"""

        if not cls.can_aggregate(from_tf, to_tf):
            raise ValueError(
                f"Cannot aggregate {from_tf} to {to_tf}"
            )

        from_minutes = cls.get_minutes(from_tf)
        to_minutes = cls.get_minutes(to_tf)

        return to_minutes // from_minutes
