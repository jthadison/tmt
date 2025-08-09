"""
Trading Session Detection System - Comprehensive session analysis with overlap handling
"""

from datetime import datetime, timezone, time
from typing import Dict, List, Optional, Any
import pytz
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class TradingSession:
    """Trading session representation"""
    name: str
    type: str  # single, overlap, off_hours
    characteristics: Dict[str, Any]
    expected_volatility: str
    typical_volume: str
    peak_hours: Optional[List[int]] = None
    is_peak: bool = False


class TradingSessionDetector:
    """Comprehensive trading session detection with overlap analysis"""
    
    def __init__(self):
        # Session times in UTC
        self.sessions = {
            'asian': {
                'start': 21,  # 21:00 UTC
                'end': 6,     # 06:00 UTC
                'peak': [23, 2],
                'currencies': ['JPY', 'AUD', 'NZD'],
                'characteristics': {
                    'volatility': 'moderate',
                    'volume': 'moderate',
                    'typical_range': 'narrow'
                }
            },
            'london': {
                'start': 7,   # 07:00 UTC
                'end': 16,    # 16:00 UTC
                'peak': [8, 12],
                'currencies': ['GBP', 'EUR', 'CHF'],
                'characteristics': {
                    'volatility': 'high',
                    'volume': 'high',
                    'typical_range': 'wide'
                }
            },
            'new_york': {
                'start': 12,  # 12:00 UTC
                'end': 21,    # 21:00 UTC
                'peak': [13, 17],
                'currencies': ['USD', 'CAD'],
                'characteristics': {
                    'volatility': 'high',
                    'volume': 'very_high',
                    'typical_range': 'wide'
                }
            }
        }
        
        # Overlap periods with enhanced characteristics
        self.overlaps = {
            'london_tokyo': {
                'start': 7,
                'end': 9,
                'currencies': ['JPY', 'GBP', 'EUR'],
                'characteristics': {
                    'volatility': 'high',
                    'volume': 'high',
                    'typical_behavior': 'Increased JPY pair volatility',
                    'recommended_pairs': ['GBPJPY', 'EURJPY']
                }
            },
            'london_ny': {
                'start': 12,
                'end': 16,
                'currencies': ['USD', 'EUR', 'GBP'],
                'characteristics': {
                    'volatility': 'very_high',
                    'volume': 'very_high',
                    'typical_behavior': 'Maximum liquidity and volatility',
                    'recommended_pairs': ['EURUSD', 'GBPUSD']
                }
            },
            'asian_sydney': {
                'start': 21,
                'end': 23,
                'currencies': ['AUD', 'NZD', 'JPY'],
                'characteristics': {
                    'volatility': 'moderate',
                    'volume': 'moderate',
                    'typical_behavior': 'AUD/NZD active trading',
                    'recommended_pairs': ['AUDUSD', 'NZDUSD', 'AUDJPY']
                }
            }
        }
        
        # Holiday calendar (simplified - would integrate with external service in production)
        self.market_holidays = {
            'US': ['2024-01-01', '2024-07-04', '2024-12-25'],
            'UK': ['2024-01-01', '2024-12-25', '2024-12-26'],
            'JP': ['2024-01-01', '2024-01-02', '2024-01-03']
        }
    
    def detect_current_session(self, timestamp: datetime) -> TradingSession:
        """
        Detect current trading session with overlap analysis
        
        Args:
            timestamp: Current timestamp
            
        Returns:
            TradingSession object with details
        """
        utc_time = timestamp.astimezone(timezone.utc)
        utc_hour = utc_time.hour
        
        # Check if market is closed (weekend)
        if self._is_weekend(utc_time):
            return TradingSession(
                name='weekend',
                type='closed',
                characteristics={'status': 'Market closed'},
                expected_volatility='none',
                typical_volume='none'
            )
        
        # Check for holiday closures
        holiday_info = self._check_holidays(utc_time)
        if holiday_info['is_holiday']:
            return TradingSession(
                name='holiday',
                type='reduced',
                characteristics={
                    'status': 'Reduced liquidity',
                    'closed_markets': holiday_info['closed_markets']
                },
                expected_volatility='low',
                typical_volume='below_average'
            )
        
        # Check for overlaps first (higher priority)
        for overlap_name, overlap_time in self.overlaps.items():
            if self._is_time_in_range(utc_hour, overlap_time['start'], overlap_time['end']):
                return TradingSession(
                    name=overlap_name,
                    type='overlap',
                    characteristics=overlap_time['characteristics'],
                    expected_volatility=overlap_time['characteristics']['volatility'],
                    typical_volume=overlap_time['characteristics']['volume']
                )
        
        # Check individual sessions
        for session_name, session_time in self.sessions.items():
            if self._is_time_in_range(utc_hour, session_time['start'], session_time['end']):
                is_peak = utc_hour in range(session_time['peak'][0], session_time['peak'][1] + 1)
                return TradingSession(
                    name=session_name,
                    type='single',
                    characteristics=session_time['characteristics'],
                    expected_volatility=session_time['characteristics']['volatility'],
                    typical_volume=session_time['characteristics']['volume'],
                    peak_hours=session_time['peak'],
                    is_peak=is_peak
                )
        
        # Off-hours trading
        return TradingSession(
            name='off_hours',
            type='quiet',
            characteristics={
                'volatility': 'low',
                'volume': 'below_average',
                'typical_behavior': 'Thin liquidity, wider spreads'
            },
            expected_volatility='low',
            typical_volume='below_average'
        )
    
    def get_session_schedule(self, date: datetime) -> List[Dict[str, Any]]:
        """
        Get full session schedule for a given date
        
        Args:
            date: Date to get schedule for
            
        Returns:
            List of session periods with times
        """
        schedule = []
        
        # Add individual sessions
        for session_name, session_info in self.sessions.items():
            schedule.append({
                'session': session_name,
                'type': 'single',
                'start_utc': session_info['start'],
                'end_utc': session_info['end'],
                'peak_hours': session_info['peak'],
                'currencies': session_info['currencies']
            })
        
        # Add overlaps
        for overlap_name, overlap_info in self.overlaps.items():
            schedule.append({
                'session': overlap_name,
                'type': 'overlap',
                'start_utc': overlap_info['start'],
                'end_utc': overlap_info['end'],
                'currencies': overlap_info['currencies'],
                'characteristics': overlap_info['characteristics']
            })
        
        return sorted(schedule, key=lambda x: x['start_utc'])
    
    def get_best_trading_times(self, currency_pair: str) -> List[Dict[str, Any]]:
        """
        Get best trading times for a specific currency pair
        
        Args:
            currency_pair: Currency pair (e.g., 'EURUSD')
            
        Returns:
            List of optimal trading periods
        """
        base_currency = currency_pair[:3]
        quote_currency = currency_pair[3:6]
        
        best_times = []
        
        # Check sessions for currency involvement
        for session_name, session_info in self.sessions.items():
            if base_currency in session_info['currencies'] or quote_currency in session_info['currencies']:
                best_times.append({
                    'session': session_name,
                    'start_utc': session_info['start'],
                    'end_utc': session_info['end'],
                    'peak_hours': session_info['peak'],
                    'reason': f"{base_currency} or {quote_currency} home session"
                })
        
        # Check overlaps
        for overlap_name, overlap_info in self.overlaps.items():
            if base_currency in overlap_info['currencies'] or quote_currency in overlap_info['currencies']:
                if currency_pair in overlap_info['characteristics'].get('recommended_pairs', []):
                    best_times.append({
                        'session': overlap_name,
                        'start_utc': overlap_info['start'],
                        'end_utc': overlap_info['end'],
                        'reason': 'High liquidity overlap period',
                        'priority': 'high'
                    })
        
        return best_times
    
    def calculate_session_volatility_multiplier(self, session: TradingSession) -> float:
        """
        Calculate volatility multiplier based on session
        
        Args:
            session: Current trading session
            
        Returns:
            Volatility multiplier for position sizing
        """
        volatility_multipliers = {
            'none': 0.0,
            'low': 0.7,
            'moderate': 1.0,
            'high': 1.3,
            'very_high': 1.5
        }
        
        base_multiplier = volatility_multipliers.get(session.expected_volatility, 1.0)
        
        # Adjust for peak hours
        if session.is_peak:
            base_multiplier *= 1.1
        
        # Adjust for overlap periods
        if session.type == 'overlap':
            base_multiplier *= 1.2
        
        return base_multiplier
    
    def _is_time_in_range(self, hour: int, start: int, end: int) -> bool:
        """
        Check if hour is within session range
        Handles overnight sessions (e.g., Asian session 21:00-06:00)
        
        Args:
            hour: Current hour (0-23)
            start: Session start hour
            end: Session end hour
            
        Returns:
            True if within range
        """
        if start <= end:
            return start <= hour <= end
        else:  # Overnight session
            return hour >= start or hour <= end
    
    def _is_weekend(self, timestamp: datetime) -> bool:
        """
        Check if timestamp falls on weekend (market closed)
        
        Args:
            timestamp: Timestamp to check
            
        Returns:
            True if weekend
        """
        # Forex market closes Friday 21:00 UTC and opens Sunday 21:00 UTC
        weekday = timestamp.weekday()
        hour = timestamp.hour
        
        if weekday == 4 and hour >= 21:  # Friday after 21:00 UTC
            return True
        elif weekday == 5:  # Saturday
            return True
        elif weekday == 6 and hour < 21:  # Sunday before 21:00 UTC
            return True
        
        return False
    
    def _check_holidays(self, timestamp: datetime) -> Dict[str, Any]:
        """
        Check for market holidays
        
        Args:
            timestamp: Timestamp to check
            
        Returns:
            Holiday information
        """
        date_str = timestamp.strftime('%Y-%m-%d')
        closed_markets = []
        
        for market, holidays in self.market_holidays.items():
            if date_str in holidays:
                closed_markets.append(market)
        
        return {
            'is_holiday': len(closed_markets) > 0,
            'closed_markets': closed_markets
        }
    
    def get_session_characteristics(self, session_name: str) -> Dict[str, Any]:
        """
        Get detailed characteristics for a specific session
        
        Args:
            session_name: Name of the session
            
        Returns:
            Session characteristics
        """
        # Check individual sessions
        if session_name in self.sessions:
            return self.sessions[session_name]['characteristics']
        
        # Check overlaps
        if session_name in self.overlaps:
            return self.overlaps[session_name]['characteristics']
        
        # Default characteristics
        return {
            'volatility': 'unknown',
            'volume': 'unknown',
            'typical_behavior': 'Unknown session'
        }