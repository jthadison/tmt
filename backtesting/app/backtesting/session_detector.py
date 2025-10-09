"""
Trading Session Detection for Backtesting - Story 11.2

Detects trading sessions (Sydney, Tokyo, London, NY, Overlap) from timestamps
using GMT/UTC timezone logic for accurate session-targeted backtesting.
"""

from datetime import datetime, timezone, time
from typing import Optional
import logging

from .models import TradingSession

logger = logging.getLogger(__name__)


class TradingSessionDetector:
    """
    Detect trading sessions from timestamps

    Uses GMT/UTC timezone logic to accurately determine which trading
    session a given timestamp falls into. Critical for session-targeted
    backtesting with different parameter sets per session.
    """

    def __init__(self):
        """Initialize session detector with UTC session times"""

        # Session times in UTC (24-hour format)
        self.session_times = {
            TradingSession.SYDNEY: {
                'start': 21,  # 21:00 UTC (Sydney opens)
                'end': 6,     # 06:00 UTC (Sydney closes)
            },
            TradingSession.TOKYO: {
                'start': 23,  # 23:00 UTC (Tokyo opens)
                'end': 8,     # 08:00 UTC (Tokyo closes)
            },
            TradingSession.LONDON: {
                'start': 7,   # 07:00 UTC (London opens)
                'end': 16,    # 16:00 UTC (London closes)
            },
            TradingSession.NEW_YORK: {
                'start': 12,  # 12:00 UTC (New York opens)
                'end': 21,    # 21:00 UTC (New York closes)
            },
        }

        # Overlap periods (higher priority than single sessions)
        self.overlap_times = {
            'london_tokyo': {
                'start': 7,
                'end': 8,
                'session': TradingSession.OVERLAP
            },
            'london_ny': {
                'start': 12,
                'end': 16,
                'session': TradingSession.OVERLAP
            },
        }

    def detect_session(self, timestamp: datetime) -> TradingSession:
        """
        Detect trading session for a given timestamp

        Args:
            timestamp: Timestamp to analyze (will be converted to UTC)

        Returns:
            TradingSession enum value

        Example:
            >>> detector = TradingSessionDetector()
            >>> ts = datetime(2023, 6, 15, 14, 30, tzinfo=timezone.utc)
            >>> session = detector.detect_session(ts)
            >>> print(session)  # TradingSession.OVERLAP (London/NY)
        """

        # Ensure UTC timezone
        if timestamp.tzinfo is None:
            logger.warning(f"Naive timestamp provided, assuming UTC: {timestamp}")
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        else:
            timestamp = timestamp.astimezone(timezone.utc)

        utc_hour = timestamp.hour

        # Check weekends first (market closed)
        if self._is_weekend(timestamp):
            logger.debug(f"Weekend detected for timestamp: {timestamp}")
            # Default to Sydney for weekend bars (will be filtered out anyway)
            return TradingSession.SYDNEY

        # Check overlaps first (higher priority)
        overlap_session = self._check_overlaps(utc_hour)
        if overlap_session:
            return overlap_session

        # Check individual sessions
        session = self._check_individual_sessions(utc_hour)
        if session:
            return session

        # Default to Sydney if no match (off-hours)
        logger.debug(f"No session match for hour {utc_hour}, defaulting to Sydney")
        return TradingSession.SYDNEY

    def _check_overlaps(self, utc_hour: int) -> Optional[TradingSession]:
        """Check if hour falls within overlap periods"""

        for overlap_name, overlap_info in self.overlap_times.items():
            if self._is_time_in_range(utc_hour, overlap_info['start'], overlap_info['end']):
                logger.debug(f"Overlap detected: {overlap_name} at hour {utc_hour}")
                return overlap_info['session']

        return None

    def _check_individual_sessions(self, utc_hour: int) -> Optional[TradingSession]:
        """Check if hour falls within individual session times"""

        for session, session_info in self.session_times.items():
            if self._is_time_in_range(utc_hour, session_info['start'], session_info['end']):
                logger.debug(f"Session detected: {session.value} at hour {utc_hour}")
                return session

        return None

    def _is_time_in_range(self, hour: int, start: int, end: int) -> bool:
        """
        Check if hour is within session range

        Handles overnight sessions (e.g., Sydney 21:00-06:00)

        Args:
            hour: Current hour (0-23)
            start: Session start hour
            end: Session end hour

        Returns:
            True if within range
        """

        if start <= end:
            # Normal range (e.g., 7-16 for London)
            return start <= hour < end
        else:
            # Overnight range (e.g., 21-6 for Sydney)
            return hour >= start or hour < end

    def _is_weekend(self, timestamp: datetime) -> bool:
        """
        Check if timestamp falls on weekend (market closed)

        Forex market:
        - Closes: Friday 21:00 UTC
        - Opens: Sunday 21:00 UTC

        Args:
            timestamp: Timestamp to check

        Returns:
            True if market is closed (weekend)
        """

        weekday = timestamp.weekday()  # 0=Monday, 6=Sunday
        hour = timestamp.hour

        # Friday after 21:00 UTC
        if weekday == 4 and hour >= 21:
            return True

        # All day Saturday
        if weekday == 5:
            return True

        # Sunday before 21:00 UTC
        if weekday == 6 and hour < 21:
            return True

        return False

    def get_session_parameters(
        self,
        timestamp: datetime,
        universal_params: dict,
        session_params: Optional[dict] = None
    ) -> dict:
        """
        Get appropriate parameters for a given timestamp

        Merges universal parameters with session-specific overrides if available.

        Args:
            timestamp: Timestamp to get parameters for
            universal_params: Universal/default parameters
            session_params: Optional session-specific parameter overrides

        Returns:
            Merged parameter dict for the detected session

        Example:
            >>> detector = TradingSessionDetector()
            >>> ts = datetime(2023, 6, 15, 14, 30, tzinfo=timezone.utc)
            >>> universal = {'confidence_threshold': 55.0, 'min_risk_reward': 1.8}
            >>> session_overrides = {
            ...     TradingSession.LONDON: {'confidence_threshold': 66.0}
            ... }
            >>> params = detector.get_session_parameters(ts, universal, session_overrides)
            >>> # Returns: {'confidence_threshold': 66.0, 'min_risk_reward': 1.8}
        """

        # Detect session
        session = self.detect_session(timestamp)

        # Start with universal parameters
        params = universal_params.copy()

        # Apply session-specific overrides if available
        if session_params and session in session_params:
            session_override = session_params[session]
            params.update(session_override)
            logger.debug(f"Applied session override for {session.value}: {session_override}")

        return params
