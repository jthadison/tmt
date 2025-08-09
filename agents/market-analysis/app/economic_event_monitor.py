"""
Economic Event Monitor - Real-time economic calendar integration and event impact analysis
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from decimal import Decimal
import asyncio
import aiohttp
from dataclasses import dataclass, field
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class EventImportance(Enum):
    """Economic event importance levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class EconomicEvent:
    """Economic event representation"""
    event_id: str
    event_name: str
    country: str
    currency: str
    event_time: datetime
    importance: EventImportance
    previous_value: Optional[Decimal] = None
    forecast_value: Optional[Decimal] = None
    actual_value: Optional[Decimal] = None
    restriction_window: Dict[str, datetime] = field(default_factory=dict)
    affected_pairs: List[str] = field(default_factory=list)


class EconomicEventMonitor:
    """Monitor and analyze economic events for trading impact"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.event_buffer_minutes = 30
        self.cache_duration_minutes = 60
        self.cached_events: List[EconomicEvent] = []
        self.cache_timestamp: Optional[datetime] = None
        
        # High-impact indicators that always trigger restrictions
        self.high_impact_indicators = [
            'Non Farm Payrolls',
            'FOMC Rate Decision', 
            'ECB Rate Decision',
            'BOE Rate Decision',
            'GDP',
            'Inflation Rate',
            'CPI',
            'Unemployment Rate',
            'Retail Sales',
            'ISM Manufacturing PMI',
            'Interest Rate Decision'
        ]
        
        # Currency to country mapping
        self.currency_country_map = {
            'USD': 'United States',
            'EUR': 'Euro Area',
            'GBP': 'United Kingdom',
            'JPY': 'Japan',
            'CHF': 'Switzerland',
            'CAD': 'Canada',
            'AUD': 'Australia',
            'NZD': 'New Zealand'
        }
        
        # Country to currency mapping
        self.country_currency_map = {v: k for k, v in self.currency_country_map.items()}
    
    async def get_upcoming_events(
        self, 
        hours_ahead: int = 24,
        currencies: Optional[List[str]] = None
    ) -> List[EconomicEvent]:
        """
        Get upcoming high-impact economic events
        
        Args:
            hours_ahead: Number of hours to look ahead
            currencies: List of currencies to filter for
            
        Returns:
            List of upcoming economic events
        """
        # Check cache first
        if self._is_cache_valid():
            return self._filter_cached_events(hours_ahead, currencies)
        
        # Fetch new events
        try:
            events = await self._fetch_economic_calendar(hours_ahead)
            self.cached_events = self._process_events(events, currencies)
            self.cache_timestamp = datetime.now(timezone.utc)
            return self.cached_events
        except Exception as e:
            logger.error(f"Failed to fetch economic events: {e}")
            return []
    
    async def _fetch_economic_calendar(self, hours_ahead: int) -> List[Dict[str, Any]]:
        """
        Fetch economic calendar from API
        Note: In production, this would connect to a real economic calendar API
        """
        # Simulated API response for development
        # In production, replace with actual API call
        current_time = datetime.now(timezone.utc)
        
        # Simulated events for testing
        simulated_events = [
            {
                'event': 'Non Farm Payrolls',
                'country': 'United States',
                'date': current_time + timedelta(hours=2),
                'importance': 'high',
                'previous': '150K',
                'forecast': '180K'
            },
            {
                'event': 'ECB Rate Decision',
                'country': 'Euro Area',
                'date': current_time + timedelta(hours=6),
                'importance': 'high',
                'previous': '4.50%',
                'forecast': '4.50%'
            },
            {
                'event': 'GDP',
                'country': 'United Kingdom',
                'date': current_time + timedelta(hours=12),
                'importance': 'high',
                'previous': '0.3%',
                'forecast': '0.4%'
            }
        ]
        
        return simulated_events
    
    def _process_events(
        self, 
        raw_events: List[Dict[str, Any]], 
        currencies: Optional[List[str]] = None
    ) -> List[EconomicEvent]:
        """
        Process raw events into EconomicEvent objects
        
        Args:
            raw_events: Raw event data from API
            currencies: Optional currency filter
            
        Returns:
            Processed economic events
        """
        processed_events = []
        
        for event_data in raw_events:
            # Determine currency from country
            currency = self.country_currency_map.get(
                event_data['country'], 
                'USD'  # Default to USD if country not mapped
            )
            
            # Filter by currencies if specified
            if currencies and currency not in currencies:
                continue
            
            # Determine importance
            importance = self._determine_importance(event_data)
            
            # Skip low importance events
            if importance == EventImportance.LOW:
                continue
            
            # Calculate restriction window
            event_time = event_data['date']
            if isinstance(event_time, str):
                event_time = datetime.fromisoformat(event_time)
            
            restriction_window = {
                'start': event_time - timedelta(minutes=self.event_buffer_minutes),
                'end': event_time + timedelta(minutes=self.event_buffer_minutes)
            }
            
            # Determine affected pairs
            affected_pairs = self._get_affected_pairs(currency)
            
            # Create event object
            event = EconomicEvent(
                event_id=f"{event_data['country']}_{event_data['event']}_{event_time.isoformat()}",
                event_name=event_data['event'],
                country=event_data['country'],
                currency=currency,
                event_time=event_time,
                importance=importance,
                previous_value=self._parse_value(event_data.get('previous')),
                forecast_value=self._parse_value(event_data.get('forecast')),
                actual_value=self._parse_value(event_data.get('actual')),
                restriction_window=restriction_window,
                affected_pairs=affected_pairs
            )
            
            processed_events.append(event)
        
        return sorted(processed_events, key=lambda x: x.event_time)
    
    def _determine_importance(self, event_data: Dict[str, Any]) -> EventImportance:
        """
        Determine event importance level
        
        Args:
            event_data: Raw event data
            
        Returns:
            Event importance level
        """
        # Check if explicitly marked as high impact
        if event_data.get('importance') == 'high':
            return EventImportance.HIGH
        
        # Check against high-impact indicators list
        if event_data['event'] in self.high_impact_indicators:
            return EventImportance.HIGH
        
        # Check if explicitly marked
        if event_data.get('importance') == 'medium':
            return EventImportance.MEDIUM
        elif event_data.get('importance') == 'low':
            return EventImportance.LOW
        
        # Default to medium if not specified
        return EventImportance.MEDIUM
    
    def _get_affected_pairs(self, currency: str) -> List[str]:
        """
        Get forex pairs affected by events for a currency
        
        Args:
            currency: Currency code
            
        Returns:
            List of affected forex pairs
        """
        major_pairs = [
            'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 
            'AUDUSD', 'USDCAD', 'NZDUSD'
        ]
        
        minor_pairs = [
            'EURJPY', 'GBPJPY', 'AUDJPY', 'NZDJPY',
            'EURGBP', 'EURAUD', 'EURNZD', 'EURCAD',
            'GBPAUD', 'GBPNZD', 'GBPCAD', 'AUDNZD',
            'AUDCAD', 'NZDCAD'
        ]
        
        affected = []
        all_pairs = major_pairs + minor_pairs
        
        for pair in all_pairs:
            if currency in pair:
                affected.append(pair)
        
        return affected
    
    def is_trading_restricted(
        self, 
        symbol: str, 
        current_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Check if trading is restricted due to upcoming economic events
        
        Args:
            symbol: Trading symbol to check
            current_time: Time to check (defaults to now)
            
        Returns:
            Restriction information
        """
        if current_time is None:
            current_time = datetime.now(timezone.utc)
        
        # Ensure we have fresh events
        if not self._is_cache_valid():
            # In async context, this would need to be awaited
            # For sync usage, return no restriction if cache invalid
            logger.warning("Event cache invalid, unable to check restrictions")
            return {'restricted': False, 'reason': 'Cache invalid'}
        
        for event in self.cached_events:
            if symbol in event.affected_pairs:
                if (event.restriction_window['start'] <= current_time <= 
                    event.restriction_window['end']):
                    return {
                        'restricted': True,
                        'reason': f"{event.event_name} - {event.country}",
                        'restriction_ends': event.restriction_window['end'],
                        'event_impact': event.importance.value,
                        'event_time': event.event_time
                    }
        
        return {'restricted': False}
    
    def get_event_impact_analysis(self, event: EconomicEvent) -> Dict[str, Any]:
        """
        Analyze potential impact of an economic event
        
        Args:
            event: Economic event to analyze
            
        Returns:
            Impact analysis
        """
        impact_analysis = {
            'event_name': event.event_name,
            'currency': event.currency,
            'importance': event.importance.value,
            'affected_pairs': event.affected_pairs,
            'expected_volatility': self._estimate_volatility_impact(event),
            'trading_recommendations': self._get_trading_recommendations(event)
        }
        
        # Add deviation analysis if actual value available
        if event.actual_value and event.forecast_value:
            deviation = float(event.actual_value - event.forecast_value)
            deviation_percent = (deviation / float(event.forecast_value)) * 100 if event.forecast_value else 0
            
            impact_analysis['deviation'] = {
                'absolute': deviation,
                'percentage': deviation_percent,
                'direction': 'above' if deviation > 0 else 'below',
                'significance': self._assess_deviation_significance(deviation_percent, event)
            }
        
        return impact_analysis
    
    def _estimate_volatility_impact(self, event: EconomicEvent) -> str:
        """
        Estimate volatility impact of an event
        
        Args:
            event: Economic event
            
        Returns:
            Estimated volatility impact level
        """
        if event.importance == EventImportance.HIGH:
            if event.event_name in ['Non Farm Payrolls', 'FOMC Rate Decision', 'ECB Rate Decision']:
                return 'extreme'
            return 'high'
        elif event.importance == EventImportance.MEDIUM:
            return 'moderate'
        else:
            return 'low'
    
    def _get_trading_recommendations(self, event: EconomicEvent) -> List[str]:
        """
        Get trading recommendations for an event
        
        Args:
            event: Economic event
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        if event.importance == EventImportance.HIGH:
            recommendations.extend([
                f"Avoid new positions in {event.currency} pairs 30 minutes before event",
                "Consider closing or reducing existing positions",
                "Widen stops on existing positions if holding through event",
                "Wait for initial volatility to settle after release"
            ])
        elif event.importance == EventImportance.MEDIUM:
            recommendations.extend([
                f"Exercise caution with {event.currency} pairs",
                "Consider reducing position size",
                "Monitor for unexpected results"
            ])
        
        return recommendations
    
    def _assess_deviation_significance(
        self, 
        deviation_percent: float, 
        event: EconomicEvent
    ) -> str:
        """
        Assess significance of deviation from forecast
        
        Args:
            deviation_percent: Percentage deviation
            event: Economic event
            
        Returns:
            Significance level
        """
        abs_deviation = abs(deviation_percent)
        
        if event.importance == EventImportance.HIGH:
            if abs_deviation > 20:
                return 'extreme'
            elif abs_deviation > 10:
                return 'high'
            elif abs_deviation > 5:
                return 'moderate'
            else:
                return 'low'
        else:
            if abs_deviation > 30:
                return 'high'
            elif abs_deviation > 15:
                return 'moderate'
            else:
                return 'low'
    
    def _parse_value(self, value_str: Optional[str]) -> Optional[Decimal]:
        """
        Parse string value to Decimal
        
        Args:
            value_str: String value to parse
            
        Returns:
            Decimal value or None
        """
        if not value_str:
            return None
        
        try:
            # Remove common suffixes
            cleaned = value_str.replace('K', '000').replace('M', '000000').replace('%', '')
            return Decimal(cleaned)
        except:
            return None
    
    def _is_cache_valid(self) -> bool:
        """
        Check if event cache is still valid
        
        Returns:
            True if cache is valid
        """
        if not self.cache_timestamp or not self.cached_events:
            return False
        
        cache_age = datetime.now(timezone.utc) - self.cache_timestamp
        return cache_age.total_seconds() < self.cache_duration_minutes * 60
    
    def _filter_cached_events(
        self, 
        hours_ahead: int, 
        currencies: Optional[List[str]] = None
    ) -> List[EconomicEvent]:
        """
        Filter cached events by time and currency
        
        Args:
            hours_ahead: Hours to look ahead
            currencies: Optional currency filter
            
        Returns:
            Filtered events
        """
        current_time = datetime.now(timezone.utc)
        cutoff_time = current_time + timedelta(hours=hours_ahead)
        
        filtered = []
        for event in self.cached_events:
            # Filter by time
            if event.event_time > cutoff_time:
                continue
            
            # Filter by currency
            if currencies and event.currency not in currencies:
                continue
            
            filtered.append(event)
        
        return filtered