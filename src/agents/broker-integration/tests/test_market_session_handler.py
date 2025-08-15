"""
Tests for Market Session Handler
Story 8.5: Real-Time Price Streaming - Task 4 Tests
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone, time, timedelta

from market_session_handler import (
    MarketSessionHandler,
    MarketScheduleManager, 
    MarketSession,
    MarketStatus,
    SessionState,
    SessionEvent
)

class TestMarketScheduleManager:
    """Test market schedule management"""
    
    @pytest.fixture
    def schedule_manager(self):
        return MarketScheduleManager()
        
    def test_schedule_manager_creation(self, schedule_manager):
        """Test creating schedule manager"""
        assert len(schedule_manager.market_schedules) > 0
        assert 'EUR_USD' in schedule_manager.market_schedules
        assert 'GBP_USD' in schedule_manager.market_schedules
        
    def test_add_market_schedule(self, schedule_manager):
        """Test adding custom market schedule"""
        custom_schedule = MarketSession(
            instrument='TEST_PAIR',
            open_time=time(8, 0),
            close_time=time(16, 0),
            open_days={0, 1, 2, 3, 4}  # Monday-Friday
        )
        
        schedule_manager.add_market_schedule(custom_schedule)
        assert 'TEST_PAIR' in schedule_manager.market_schedules
        assert schedule_manager.market_schedules['TEST_PAIR'].open_time == time(8, 0)
        
    def test_is_holiday(self, schedule_manager):
        """Test holiday detection"""
        # Test known holiday
        new_years = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        assert schedule_manager.is_holiday(new_years) is True
        
        # Test regular day
        regular_day = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        assert schedule_manager.is_holiday(regular_day) is False
        
    @pytest.mark.parametrize("test_day,test_time,expected_status", [
        # Monday 12:00 UTC - should be open
        (0, time(12, 0), MarketStatus.OPEN),
        # Saturday 12:00 UTC - should be weekend
        (5, time(12, 0), MarketStatus.WEEKEND),
        # Sunday 21:30 UTC - should be opening soon (30 min before 22:00 open)
        (6, time(21, 30), MarketStatus.OPENING_SOON),
        # Sunday 23:00 UTC - should be open (after 22:00 open)
        (6, time(23, 0), MarketStatus.OPEN),
        # Friday 21:30 UTC - should be closing soon (30 min before 22:00 close)
        (4, time(21, 30), MarketStatus.CLOSING_SOON),
        # Friday 23:00 UTC - should be closed (after 22:00 close)
        (4, time(23, 0), MarketStatus.CLOSED),
    ])
    def test_get_market_status(self, schedule_manager, test_day, test_time, expected_status):
        """Test market status detection for different times"""
        # Create test datetime
        base_date = datetime(2024, 6, 3, tzinfo=timezone.utc)  # Monday June 3, 2024
        days_to_add = test_day
        test_datetime = base_date + timedelta(days=days_to_add)
        test_datetime = test_datetime.replace(
            hour=test_time.hour,
            minute=test_time.minute,
            second=0,
            microsecond=0
        )
        
        status = schedule_manager.get_market_status('EUR_USD', test_datetime)
        assert status == expected_status
        
    def test_get_market_status_holiday(self, schedule_manager):
        """Test market status on holiday"""
        # New Year's Day 2024 (Monday)
        holiday = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        status = schedule_manager.get_market_status('EUR_USD', holiday)
        assert status == MarketStatus.HOLIDAY
        
    def test_get_market_status_unknown_instrument(self, schedule_manager):
        """Test market status for unknown instrument"""
        status = schedule_manager.get_market_status('UNKNOWN_PAIR')
        assert status == MarketStatus.UNKNOWN
        
    def test_get_next_market_event_when_open(self, schedule_manager):
        """Test getting next market event when market is open"""
        # Wednesday 12:00 UTC (market open)
        wednesday = datetime(2024, 6, 5, 12, 0, 0, tzinfo=timezone.utc)
        next_event = schedule_manager.get_next_market_event('EUR_USD', wednesday)
        
        # Should be next Friday 22:00 UTC
        assert next_event is not None
        assert next_event.weekday() == 4  # Friday
        assert next_event.hour == 22
        assert next_event.minute == 0
        
    def test_get_next_market_event_when_closed(self, schedule_manager):
        """Test getting next market event when market is closed"""
        # Saturday 12:00 UTC (market closed)
        saturday = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        next_event = schedule_manager.get_next_market_event('EUR_USD', saturday)
        
        # Should be next Sunday 22:00 UTC
        assert next_event is not None
        assert next_event.weekday() == 6  # Sunday
        assert next_event.hour == 22
        assert next_event.minute == 0

class TestMarketSessionHandler:
    """Test market session handler"""
    
    @pytest.fixture
    def schedule_manager(self):
        return MarketScheduleManager()
        
    @pytest.fixture
    def session_handler(self, schedule_manager):
        return MarketSessionHandler(schedule_manager)
        
    def test_session_handler_creation(self, session_handler):
        """Test creating session handler"""
        assert len(session_handler.monitored_instruments) == 0
        assert session_handler.is_monitoring is False
        
    def test_add_instrument(self, session_handler):
        """Test adding instrument to monitoring"""
        session_handler.add_instrument('EUR_USD')
        
        assert 'EUR_USD' in session_handler.monitored_instruments
        assert 'EUR_USD' in session_handler.instrument_states
        assert 'EUR_USD' in session_handler.last_status
        
    def test_remove_instrument(self, session_handler):
        """Test removing instrument from monitoring"""
        # Add first
        session_handler.add_instrument('EUR_USD')
        assert 'EUR_USD' in session_handler.monitored_instruments
        
        # Remove
        session_handler.remove_instrument('EUR_USD')
        assert 'EUR_USD' not in session_handler.monitored_instruments
        assert 'EUR_USD' not in session_handler.instrument_states
        assert 'EUR_USD' not in session_handler.last_status
        
    def test_update_price_time(self, session_handler):
        """Test updating price timestamp"""
        instrument = 'EUR_USD'
        timestamp = datetime.now(timezone.utc)
        
        session_handler.update_price_time(instrument, timestamp)
        assert session_handler.last_price_times[instrument] == timestamp
        
    def test_callback_management(self, session_handler):
        """Test adding callbacks"""
        status_callback = Mock()
        stale_callback = Mock()
        
        session_handler.add_status_change_callback(status_callback)
        session_handler.add_stale_price_callback(stale_callback)
        
        assert status_callback in session_handler.status_change_callbacks
        assert stale_callback in session_handler.stale_price_callbacks
        
    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self, session_handler):
        """Test starting and stopping monitoring"""
        # Start monitoring
        await session_handler.start_monitoring()
        assert session_handler.is_monitoring is True
        assert session_handler.monitoring_task is not None
        
        # Stop monitoring
        await session_handler.stop_monitoring()
        assert session_handler.is_monitoring is False
        
    def test_get_instrument_status(self, session_handler):
        """Test getting instrument status"""
        # Unknown instrument
        status = session_handler.get_instrument_status('UNKNOWN')
        assert status is None
        
        # Add instrument and check status
        session_handler.add_instrument('EUR_USD')
        status = session_handler.get_instrument_status('EUR_USD')
        assert status is not None
        assert isinstance(status, MarketStatus)
        
    def test_get_session_state(self, session_handler):
        """Test getting session state"""
        # Unknown instrument
        state = session_handler.get_session_state('UNKNOWN')
        assert state is None
        
        # Add instrument and check state
        session_handler.add_instrument('EUR_USD')
        state = session_handler.get_session_state('EUR_USD')
        assert state is not None
        assert isinstance(state, SessionState)
        
    def test_is_tradeable(self, session_handler):
        """Test tradeable status check"""
        # Mock the schedule manager to return OPEN status
        session_handler.schedule_manager.get_market_status = Mock(return_value=MarketStatus.OPEN)
        session_handler.add_instrument('EUR_USD')
        
        assert session_handler.is_tradeable('EUR_USD') is True
        
        # Mock closed status
        session_handler.schedule_manager.get_market_status = Mock(return_value=MarketStatus.CLOSED)
        assert session_handler.is_tradeable('EUR_USD') is False
        
    def test_get_metrics(self, session_handler):
        """Test getting session metrics"""
        # Add some instruments
        session_handler.add_instrument('EUR_USD')
        session_handler.add_instrument('GBP_USD')
        
        metrics = session_handler.get_metrics()
        
        assert metrics['monitored_instruments'] == 2
        assert 'active_sessions' in metrics
        assert 'inactive_sessions' in metrics
        assert 'metrics' in metrics
        assert 'instrument_states' in metrics
        
    def test_get_trading_schedule(self, session_handler):
        """Test getting trading schedule"""
        # Unknown instrument
        schedule = session_handler.get_trading_schedule('UNKNOWN')
        assert schedule is None
        
        # Known instrument
        schedule = session_handler.get_trading_schedule('EUR_USD')
        assert schedule is not None
        assert schedule['instrument'] == 'EUR_USD'
        assert 'current_status' in schedule
        assert 'next_event' in schedule
        assert 'open_time' in schedule
        assert 'close_time' in schedule
        
    @pytest.mark.asyncio
    async def test_check_instrument_status_change(self, session_handler):
        """Test status change detection"""
        # Add callback
        status_callback = AsyncMock()
        session_handler.add_status_change_callback(status_callback)
        
        # Add instrument
        session_handler.add_instrument('EUR_USD')
        initial_status = session_handler.last_status['EUR_USD']
        
        # Mock status change
        new_status = MarketStatus.CLOSED if initial_status == MarketStatus.OPEN else MarketStatus.OPEN
        session_handler.schedule_manager.get_market_status = Mock(return_value=new_status)
        
        # Check status (should trigger callback)
        await session_handler._check_instrument_status('EUR_USD')
        
        # Verify callback was called
        status_callback.assert_called_once()
        
        # Verify status was updated
        assert session_handler.last_status['EUR_USD'] == new_status
        
    @pytest.mark.asyncio
    async def test_stale_price_detection(self, session_handler):
        """Test stale price detection"""
        # Add callback
        stale_callback = AsyncMock()
        session_handler.add_stale_price_callback(stale_callback)
        
        # Add instrument with open market
        session_handler.add_instrument('EUR_USD')
        session_handler.schedule_manager.get_market_status = Mock(return_value=MarketStatus.OPEN)
        
        # Set old price time (stale)
        old_time = datetime.now(timezone.utc) - timedelta(minutes=20)
        session_handler.update_price_time('EUR_USD', old_time)
        
        # Check for stale prices
        await session_handler._check_stale_prices()
        
        # Verify callback was called
        stale_callback.assert_called_once_with('EUR_USD', old_time)
        
    @pytest.mark.asyncio
    async def test_stale_price_no_alert_when_market_closed(self, session_handler):
        """Test no stale price alert when market is closed"""
        # Add callback
        stale_callback = AsyncMock()
        session_handler.add_stale_price_callback(stale_callback)
        
        # Add instrument with closed market
        session_handler.add_instrument('EUR_USD')
        session_handler.schedule_manager.get_market_status = Mock(return_value=MarketStatus.CLOSED)
        
        # Set old price time
        old_time = datetime.now(timezone.utc) - timedelta(minutes=20)
        session_handler.update_price_time('EUR_USD', old_time)
        
        # Check for stale prices
        await session_handler._check_stale_prices()
        
        # Verify callback was NOT called (market is closed)
        stale_callback.assert_not_called()

@pytest.mark.asyncio
async def test_integration_session_monitoring():
    """Test complete session monitoring integration"""
    # Create handler
    session_handler = MarketSessionHandler()
    
    # Add instruments
    session_handler.add_instrument('EUR_USD')
    session_handler.add_instrument('GBP_USD')
    
    # Add callbacks
    status_changes = []
    stale_alerts = []
    
    def status_callback(event):
        status_changes.append(event)
        
    def stale_callback(instrument, timestamp):
        stale_alerts.append((instrument, timestamp))
        
    session_handler.add_status_change_callback(status_callback)
    session_handler.add_stale_price_callback(stale_callback)
    
    # Start monitoring briefly
    await session_handler.start_monitoring()
    
    # Let it run for a short time
    await asyncio.sleep(0.1)
    
    # Stop monitoring
    await session_handler.stop_monitoring()
    
    # Verify metrics were updated
    metrics = session_handler.get_metrics()
    assert metrics['monitored_instruments'] == 2
    assert 'last_check' in metrics['metrics']

if __name__ == "__main__":
    pytest.main([__file__])