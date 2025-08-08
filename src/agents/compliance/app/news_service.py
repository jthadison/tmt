"""
News Service for Economic Calendar Integration

Fetches economic news events for trading restrictions validation.
"""

import aiohttp
import logging
from datetime import datetime, timedelta
from typing import List, Optional
import json

from .models import NewsEvent
from .config import get_settings


logger = logging.getLogger(__name__)


class NewsService:
    """Service for fetching economic news events"""
    
    def __init__(self):
        self.settings = get_settings()
        self.session = None
    
    async def start(self):
        """Initialize HTTP session"""
        self.session = aiohttp.ClientSession()
        logger.info("News service started")
    
    async def stop(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
        logger.info("News service stopped")
    
    async def get_upcoming_events(
        self,
        hours_ahead: int = 2,
        impact_filter: Optional[str] = None
    ) -> List[NewsEvent]:
        """
        Get upcoming economic events
        
        Args:
            hours_ahead: How many hours ahead to look for events
            impact_filter: Filter by impact level ('high', 'medium', 'low')
            
        Returns:
            List of NewsEvent objects
        """
        try:
            if not self.settings.economic_calendar_api_key:
                logger.warning("No economic calendar API key configured, returning mock events")
                return await self._get_mock_events(hours_ahead)
            
            # Use Trading Economics API (example implementation)
            url = f"{self.settings.economic_calendar_url}/calendar"
            params = {
                "key": self.settings.economic_calendar_api_key,
                "limit": 50,
                "dateFrom": datetime.utcnow().strftime("%Y-%m-%d"),
                "dateTo": (datetime.utcnow() + timedelta(hours=hours_ahead)).strftime("%Y-%m-%d")
            }
            
            if impact_filter:
                params["importance"] = impact_filter
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return await self._parse_trading_economics_data(data)
                else:
                    logger.error(f"Economic calendar API returned status {response.status}")
                    return await self._get_mock_events(hours_ahead)
                    
        except Exception as e:
            logger.error(f"Error fetching economic events: {e}")
            return await self._get_mock_events(hours_ahead)
    
    async def _parse_trading_economics_data(self, data: List[dict]) -> List[NewsEvent]:
        """Parse Trading Economics API response"""
        events = []
        
        for item in data:
            try:
                # Parse timestamp
                timestamp_str = item.get("Date", "")
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                
                # Determine impact level
                importance = item.get("Importance", 1)
                if importance >= 3:
                    impact = "high"
                elif importance >= 2:
                    impact = "medium"
                else:
                    impact = "low"
                
                event = NewsEvent(
                    event_id=str(item.get("CalendarId", "")),
                    title=item.get("Event", ""),
                    currency=item.get("Currency", ""),
                    impact=impact,
                    actual=item.get("Actual"),
                    forecast=item.get("Forecast"),
                    previous=item.get("Previous"),
                    timestamp=timestamp
                )
                
                events.append(event)
                
            except Exception as e:
                logger.warning(f"Error parsing news event: {e}")
                continue
        
        return events
    
    async def _get_mock_events(self, hours_ahead: int) -> List[NewsEvent]:
        """Generate mock events for testing when API is unavailable"""
        mock_events = []
        
        # Create some mock high-impact events
        base_time = datetime.utcnow()
        
        # Mock NFP release (high impact)
        if base_time.weekday() == 4:  # Friday
            nfp_time = base_time.replace(hour=13, minute=30, second=0, microsecond=0)
            if base_time < nfp_time < base_time + timedelta(hours=hours_ahead):
                mock_events.append(NewsEvent(
                    event_id="mock_nfp",
                    title="Non-Farm Payrolls",
                    currency="USD",
                    impact="high",
                    forecast="200K",
                    previous="190K",
                    timestamp=nfp_time
                ))
        
        # Mock FOMC meeting (high impact)
        fomc_time = base_time.replace(hour=19, minute=0, second=0, microsecond=0)
        if base_time < fomc_time < base_time + timedelta(hours=hours_ahead):
            mock_events.append(NewsEvent(
                event_id="mock_fomc",
                title="FOMC Meeting Decision",
                currency="USD",
                impact="high",
                forecast="5.25%",
                previous="5.00%",
                timestamp=fomc_time
            ))
        
        # Mock GDP release (medium impact)
        gdp_time = base_time.replace(hour=13, minute=30, second=0, microsecond=0) + timedelta(hours=1)
        if base_time < gdp_time < base_time + timedelta(hours=hours_ahead):
            mock_events.append(NewsEvent(
                event_id="mock_gdp",
                title="GDP Quarter on Quarter",
                currency="USD",
                impact="medium",
                forecast="2.1%",
                previous="2.0%",
                timestamp=gdp_time
            ))
        
        logger.info(f"Generated {len(mock_events)} mock news events")
        return mock_events
    
    async def get_high_impact_events(self, hours_ahead: int = 2) -> List[NewsEvent]:
        """Get only high-impact events"""
        all_events = await self.get_upcoming_events(hours_ahead)
        return [event for event in all_events if event.is_high_impact()]
    
    async def is_news_blackout_period(
        self,
        buffer_minutes: int = 5,
        currencies: Optional[List[str]] = None
    ) -> tuple[bool, Optional[NewsEvent]]:
        """
        Check if currently in news blackout period
        
        Args:
            buffer_minutes: Minutes before/after news to block trading
            currencies: List of currencies to check (None for all)
            
        Returns:
            Tuple of (is_blackout, news_event_causing_blackout)
        """
        if buffer_minutes == 0:
            return False, None
        
        now = datetime.utcnow()
        buffer_time = timedelta(minutes=buffer_minutes)
        
        # Get events in the next buffer period
        upcoming_events = await self.get_high_impact_events(hours_ahead=buffer_minutes/60)
        
        for event in upcoming_events:
            # Check if we're within the blackout window
            time_to_event = event.timestamp - now
            
            # Within blackout window (before event)
            if timedelta(0) <= time_to_event <= buffer_time:
                if currencies is None or event.currency in currencies:
                    return True, event
            
            # Within blackout window (after event - for past events)
            time_since_event = now - event.timestamp
            if timedelta(0) <= time_since_event <= buffer_time:
                if currencies is None or event.currency in currencies:
                    return True, event
        
        return False, None
    
    async def get_next_high_impact_event(
        self,
        currencies: Optional[List[str]] = None
    ) -> Optional[NewsEvent]:
        """Get the next high-impact event for specified currencies"""
        events = await self.get_high_impact_events(hours_ahead=24)  # Look 24 hours ahead
        
        if currencies:
            events = [event for event in events if event.currency in currencies]
        
        if not events:
            return None
        
        # Sort by timestamp and return the next event
        events.sort(key=lambda e: e.timestamp)
        return events[0]


# Global news service instance
news_service = None


async def get_news_service() -> NewsService:
    """Get or create the global news service instance"""
    global news_service
    if news_service is None:
        news_service = NewsService()
        await news_service.start()
    return news_service


async def cleanup_news_service():
    """Cleanup the global news service instance"""
    global news_service
    if news_service:
        await news_service.stop()
        news_service = None