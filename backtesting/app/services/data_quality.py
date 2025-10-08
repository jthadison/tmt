"""
Data Quality Validation Service

Validates historical data for completeness, gaps, and outliers.
"""

from datetime import datetime, timedelta
from typing import List, Tuple
import numpy as np
import pandas as pd
import structlog

from ..config import get_settings
from ..models.market_data import MarketCandleSchema, DataQualityReport

logger = structlog.get_logger()


class DataQualityValidator:
    """Validates data quality for historical market data"""

    def __init__(self):
        self.settings = get_settings()
        self.max_gap_hours = self.settings.max_gap_hours
        self.outlier_threshold = self.settings.outlier_std_threshold

    def validate_candles(
        self,
        candles: List[MarketCandleSchema],
        instrument: str,
        start_date: datetime,
        end_date: datetime,
        timeframe: str = "H1",
    ) -> DataQualityReport:
        """
        Validate candle data quality

        Args:
            candles: List of market candles to validate
            instrument: Instrument name
            start_date: Expected start date
            end_date: Expected end date
            timeframe: Candle timeframe

        Returns:
            DataQualityReport with validation results
        """
        logger.info(
            "Validating candle data quality",
            instrument=instrument,
            candles_count=len(candles),
            timeframe=timeframe,
        )

        issues = []

        # Calculate expected number of candles
        expected_candles = self._calculate_expected_candles(
            start_date, end_date, timeframe
        )

        # Detect gaps in data
        gaps = self._detect_gaps(candles, timeframe)

        # Detect outliers
        outliers = self._detect_outliers(candles)

        # Calculate completeness score
        completeness_score = (
            len(candles) / expected_candles if expected_candles > 0 else 0.0
        )

        # Calculate quality score (weighted combination)
        gap_penalty = min(len(gaps) * 0.01, 0.3)  # Max 30% penalty for gaps
        outlier_penalty = min(len(outliers) * 0.005, 0.2)  # Max 20% penalty
        quality_score = max(0.0, 1.0 - gap_penalty - outlier_penalty)

        # Compile issues
        if len(candles) < expected_candles * 0.95:
            issues.append(
                f"Missing {expected_candles - len(candles)} candles "
                f"({(1 - completeness_score) * 100:.1f}% incomplete)"
            )

        if gaps:
            issues.append(f"Detected {len(gaps)} gaps > {self.max_gap_hours} hours")
            for gap_start, gap_end, gap_hours in gaps[:5]:  # Report first 5 gaps
                issues.append(
                    f"  Gap from {gap_start.isoformat()} to {gap_end.isoformat()} "
                    f"({gap_hours:.1f} hours)"
                )

        if outliers:
            issues.append(f"Detected {len(outliers)} price outliers")
            for idx, candle in outliers[:5]:  # Report first 5 outliers
                issues.append(
                    f"  Outlier at {candle.timestamp.isoformat()}: "
                    f"Close={candle.close}"
                )

        logger.info(
            "Data quality validation complete",
            instrument=instrument,
            completeness=f"{completeness_score * 100:.1f}%",
            quality_score=f"{quality_score * 100:.1f}%",
            gaps=len(gaps),
            outliers=len(outliers),
        )

        return DataQualityReport(
            instrument=instrument,
            start_date=start_date,
            end_date=end_date,
            total_candles=len(candles),
            expected_candles=expected_candles,
            missing_candles=max(0, expected_candles - len(candles)),
            gaps_detected=len(gaps),
            outliers_detected=len(outliers),
            completeness_score=completeness_score,
            quality_score=quality_score,
            issues=issues,
        )

    def _calculate_expected_candles(
        self, start_date: datetime, end_date: datetime, timeframe: str
    ) -> int:
        """Calculate expected number of candles for date range"""
        total_hours = (end_date - start_date).total_seconds() / 3600

        # Mapping of timeframes to hours
        timeframe_hours = {
            "M1": 1 / 60,
            "M5": 5 / 60,
            "M15": 15 / 60,
            "M30": 30 / 60,
            "H1": 1,
            "H4": 4,
            "D": 24,
            "W": 168,
        }

        candle_hours = timeframe_hours.get(timeframe, 1)

        # Account for weekends (forex markets closed)
        # Rough estimate: 5/7 of total time
        expected = int((total_hours / candle_hours) * (5 / 7))

        return expected

    def _detect_gaps(
        self, candles: List[MarketCandleSchema], timeframe: str
    ) -> List[Tuple[datetime, datetime, float]]:
        """
        Detect gaps in candle data

        Returns:
            List of (gap_start, gap_end, gap_hours) tuples
        """
        if len(candles) < 2:
            return []

        gaps = []

        # Expected time between candles
        timeframe_hours = {"M1": 1 / 60, "M5": 5 / 60, "M15": 15 / 60, "M30": 30 / 60, "H1": 1, "H4": 4, "D": 24}
        expected_delta = timedelta(hours=timeframe_hours.get(timeframe, 1))

        # Sort candles by timestamp
        sorted_candles = sorted(candles, key=lambda c: c.timestamp)

        for i in range(len(sorted_candles) - 1):
            current = sorted_candles[i]
            next_candle = sorted_candles[i + 1]

            time_diff = next_candle.timestamp - current.timestamp
            gap_hours = time_diff.total_seconds() / 3600

            # Allow for some tolerance (weekends, holidays)
            # Gap is significant if > max_gap_hours
            if gap_hours > self.max_gap_hours:
                gaps.append((current.timestamp, next_candle.timestamp, gap_hours))

        return gaps

    def _detect_outliers(
        self, candles: List[MarketCandleSchema]
    ) -> List[Tuple[int, MarketCandleSchema]]:
        """
        Detect price outliers using statistical methods

        Returns:
            List of (index, candle) tuples for outliers
        """
        if len(candles) < 50:
            # Not enough data for statistical outlier detection
            return []

        outliers = []

        # Convert to pandas for easier statistical analysis
        prices = [c.close for c in candles]
        df = pd.DataFrame({"close": prices})

        # Calculate rolling mean and std dev (50-candle window for better detection)
        window_size = min(50, len(candles) // 3)
        df["rolling_mean"] = df["close"].rolling(window=window_size, min_periods=10).mean()
        df["rolling_std"] = df["close"].rolling(window=window_size, min_periods=10).std()

        # Detect outliers (> N standard deviations from mean)
        for idx, row in df.iterrows():
            if pd.notna(row["rolling_mean"]) and pd.notna(row["rolling_std"]):
                deviation = abs(row["close"] - row["rolling_mean"]) / (
                    row["rolling_std"] + 1e-10
                )
                if deviation > self.outlier_threshold:
                    outliers.append((idx, candles[idx]))

        return outliers

    def validate_continuity(
        self, candles: List[MarketCandleSchema]
    ) -> Tuple[bool, List[str]]:
        """
        Validate OHLC continuity (high >= low, close within range, etc.)

        Returns:
            (is_valid, issues) tuple
        """
        issues = []

        for i, candle in enumerate(candles):
            # Check OHLC relationships
            if candle.high < candle.low:
                issues.append(
                    f"Candle {i} at {candle.timestamp.isoformat()}: "
                    f"High ({candle.high}) < Low ({candle.low})"
                )

            if candle.close > candle.high or candle.close < candle.low:
                issues.append(
                    f"Candle {i} at {candle.timestamp.isoformat()}: "
                    f"Close ({candle.close}) outside High-Low range"
                )

            if candle.open > candle.high or candle.open < candle.low:
                issues.append(
                    f"Candle {i} at {candle.timestamp.isoformat()}: "
                    f"Open ({candle.open}) outside High-Low range"
                )

            # Check for zero or negative prices
            if any(
                p <= 0 for p in [candle.open, candle.high, candle.low, candle.close]
            ):
                issues.append(
                    f"Candle {i} at {candle.timestamp.isoformat()}: "
                    f"Contains zero or negative price"
                )

        is_valid = len(issues) == 0

        if is_valid:
            logger.info("OHLC continuity validation passed", candles_count=len(candles))
        else:
            logger.warning(
                "OHLC continuity validation failed",
                issues_count=len(issues),
                candles_count=len(candles),
            )

        return is_valid, issues
