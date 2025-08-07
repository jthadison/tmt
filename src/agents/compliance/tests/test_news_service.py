"""
Test cases for News Service
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from ..app.news_service import NewsService
from ..app.models import NewsEvent


class TestNewsService:
    """Test the news service functionality"""
    
    @pytest.fixture
    async def news_service(self):
        """Create news service for testing"""
        service = NewsService()
        await service.start()
        yield service
        await service.stop()
    
    @pytest.mark.asyncio
    async def test_get_mock_events(self, news_service):
        """Test mock events generation"""
        events = await news_service._get_mock_events(hours_ahead=24)
        
        assert isinstance(events, list)
        # Should have some mock events on certain days
        for event in events:
            assert isinstance(event, NewsEvent)
            assert event.currency in ["USD", "EUR", "GBP"]
            assert event.impact in ["high", "medium", "low"]
    
    @pytest.mark.asyncio
    async def test_get_high_impact_events(self, news_service):
        """Test filtering for high-impact events only"""
        with patch.object(news_service, 'get_upcoming_events') as mock_get_events:
            # Mock mixed impact events
            mock_events = [
                NewsEvent(
                    event_id="1",
                    title="High Impact Event",
                    currency="USD",
                    impact="high",
                    timestamp=datetime.utcnow()
                ),
                NewsEvent(
                    event_id="2",
                    title="Medium Impact Event",
                    currency="USD",
                    impact="medium",
                    timestamp=datetime.utcnow()
                ),
                NewsEvent(
                    event_id="3",
                    title="Another High Impact",
                    currency="EUR",
                    impact="high",
                    timestamp=datetime.utcnow()
                )
            ]
            mock_get_events.return_value = mock_events
            
            high_impact = await news_service.get_high_impact_events()
            
            assert len(high_impact) == 2
            for event in high_impact:
                assert event.impact == "high"
    
    @pytest.mark.asyncio
    async def test_is_news_blackout_period_true(self, news_service):
        """Test news blackout period detection - in blackout"""
        with patch.object(news_service, 'get_high_impact_events') as mock_get_events:
            # Mock event in 2 minutes (within 5-minute buffer)
            upcoming_event = NewsEvent(
                event_id="nfp",
                title="Non-Farm Payrolls",
                currency="USD",
                impact="high",
                timestamp=datetime.utcnow() + timedelta(minutes=2)
            )
            mock_get_events.return_value = [upcoming_event]
            
            is_blackout, event = await news_service.is_news_blackout_period(
                buffer_minutes=5
            )
            
            assert is_blackout
            assert event == upcoming_event
    
    @pytest.mark.asyncio
    async def test_is_news_blackout_period_false(self, news_service):
        """Test news blackout period detection - not in blackout"""
        with patch.object(news_service, 'get_high_impact_events') as mock_get_events:
            # Mock event in 10 minutes (outside 5-minute buffer)
            upcoming_event = NewsEvent(
                event_id="gdp",
                title="GDP Release",
                currency="USD",
                impact="high",
                timestamp=datetime.utcnow() + timedelta(minutes=10)
            )
            mock_get_events.return_value = [upcoming_event]
            
            is_blackout, event = await news_service.is_news_blackout_period(
                buffer_minutes=5
            )
            
            assert not is_blackout
            assert event is None
    
    @pytest.mark.asyncio
    async def test_is_news_blackout_currency_filter(self, news_service):
        """Test news blackout with currency filtering"""
        with patch.object(news_service, 'get_high_impact_events') as mock_get_events:
            # Mock EUR event in 2 minutes
            eur_event = NewsEvent(
                event_id="ecb",
                title="ECB Rate Decision",
                currency="EUR",
                impact="high",
                timestamp=datetime.utcnow() + timedelta(minutes=2)
            )
            mock_get_events.return_value = [eur_event]
            
            # Test with USD filter - should not be in blackout
            is_blackout_usd, _ = await news_service.is_news_blackout_period(
                buffer_minutes=5,
                currencies=["USD"]
            )
            assert not is_blackout_usd
            
            # Test with EUR filter - should be in blackout
            is_blackout_eur, event = await news_service.is_news_blackout_period(
                buffer_minutes=5,
                currencies=["EUR"]
            )
            assert is_blackout_eur
            assert event == eur_event
    
    @pytest.mark.asyncio
    async def test_get_next_high_impact_event(self, news_service):
        """Test getting next high-impact event"""
        with patch.object(news_service, 'get_high_impact_events') as mock_get_events:
            now = datetime.utcnow()
            events = [
                NewsEvent(
                    event_id="3",
                    title="Later Event",
                    currency="USD",
                    impact="high",
                    timestamp=now + timedelta(hours=5)
                ),
                NewsEvent(
                    event_id="1",
                    title="Sooner Event",
                    currency="USD",
                    impact="high",
                    timestamp=now + timedelta(hours=2)
                ),
                NewsEvent(
                    event_id="2",
                    title="Middle Event",
                    currency="EUR",
                    impact="high",
                    timestamp=now + timedelta(hours=3)
                )
            ]
            mock_get_events.return_value = events
            
            next_event = await news_service.get_next_high_impact_event()
            
            assert next_event is not None
            assert next_event.event_id == "1"  # Should be the soonest
            assert next_event.title == "Sooner Event"
    
    @pytest.mark.asyncio
    async def test_get_next_event_with_currency_filter(self, news_service):
        """Test getting next event with currency filter"""
        with patch.object(news_service, 'get_high_impact_events') as mock_get_events:
            now = datetime.utcnow()
            events = [
                NewsEvent(
                    event_id="1",
                    title="USD Event",
                    currency="USD",
                    impact="high",
                    timestamp=now + timedelta(hours=1)
                ),
                NewsEvent(
                    event_id="2",
                    title="EUR Event",
                    currency="EUR",
                    impact="high",
                    timestamp=now + timedelta(hours=2)
                )
            ]
            mock_get_events.return_value = events
            
            next_eur_event = await news_service.get_next_high_impact_event(
                currencies=["EUR"]
            )
            
            assert next_eur_event is not None
            assert next_eur_event.currency == "EUR"
            assert next_eur_event.event_id == "2"
    
    @pytest.mark.asyncio
    async def test_no_blackout_when_disabled(self, news_service):
        """Test that blackout returns False when buffer_minutes is 0"""
        is_blackout, event = await news_service.is_news_blackout_period(
            buffer_minutes=0
        )
        
        assert not is_blackout
        assert event is None
    
    @pytest.mark.asyncio
    async def test_parse_trading_economics_data(self, news_service):
        """Test parsing Trading Economics API response"""
        mock_data = [
            {
                "CalendarId": "12345",
                "Event": "Non-Farm Payrolls",
                "Date": "2024-01-07T13:30:00Z",
                "Currency": "USD",
                "Importance": 3,
                "Actual": "200K",
                "Forecast": "195K",
                "Previous": "190K"
            },
            {
                "CalendarId": "12346",
                "Event": "Unemployment Rate",
                "Date": "2024-01-07T13:30:00Z",
                "Currency": "USD",
                "Importance": 2,
                "Actual": None,
                "Forecast": "3.7%",
                "Previous": "3.8%"
            }
        ]
        
        events = await news_service._parse_trading_economics_data(mock_data)
        
        assert len(events) == 2
        
        nfp_event = events[0]
        assert nfp_event.event_id == "12345"
        assert nfp_event.title == "Non-Farm Payrolls"
        assert nfp_event.currency == "USD"
        assert nfp_event.impact == "high"  # Importance 3 -> high
        assert nfp_event.actual == "200K"
        
        unemployment_event = events[1]
        assert unemployment_event.impact == "medium"  # Importance 2 -> medium
        assert unemployment_event.actual is None