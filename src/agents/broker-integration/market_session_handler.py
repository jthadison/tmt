"""
Market Session Handler
Story 8.5: Real-Time Price Streaming - Task 4: Handle market sessions and closures
"""
import logging
from typing import Dict, Set, Optional, Callable, List
from datetime import datetime, timezone, timedelta, time
from enum import Enum
from dataclasses import dataclass
import asyncio
from collections import defaultdict

logger = logging.getLogger(__name__)

class MarketStatus(Enum):
    """Market status enumeration"""
    OPEN = "open"
    CLOSED = "closed"
    CLOSING_SOON = "closing_soon"
    OPENING_SOON = "opening_soon"
    HOLIDAY = "holiday"
    WEEKEND = "weekend"
    UNKNOWN = "unknown"

class SessionState(Enum):
    """Session state enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    TRANSITIONING = "transitioning"

@dataclass
class MarketSession:
    """Market session definition"""
    instrument: str
    open_time: time  # UTC time
    close_time: time  # UTC time
    open_days: Set[int]  # 0=Monday, 6=Sunday
    timezone_name: str = "UTC"

@dataclass
class SessionEvent:
    """Market session event"""
    instrument: str
    status: MarketStatus
    timestamp: datetime
    next_change: Optional[datetime] = None
    message: str = ""

class MarketScheduleManager:
    """Manages market schedules for different instruments"""
    
    def __init__(self):
        # Standard Forex market schedules (UTC times)
        self.market_schedules: Dict[str, MarketSession] = {
            # Major currency pairs - 24/5 market
            'EUR_USD': MarketSession(
                instrument='EUR_USD',
                open_time=time(22, 0),    # Sunday 22:00 UTC (Sydney open)
                close_time=time(22, 0),   # Friday 22:00 UTC (NY close)
                open_days={0, 1, 2, 3, 4}  # Monday-Friday trading
            ),
            'GBP_USD': MarketSession(
                instrument='GBP_USD',
                open_time=time(22, 0),
                close_time=time(22, 0),
                open_days={0, 1, 2, 3, 4}
            ),
            'USD_JPY': MarketSession(
                instrument='USD_JPY',
                open_time=time(22, 0),
                close_time=time(22, 0),
                open_days={0, 1, 2, 3, 4}
            ),
            'GBP_JPY': MarketSession(
                instrument='GBP_JPY',
                open_time=time(22, 0),
                close_time=time(22, 0),
                open_days={0, 1, 2, 3, 4}
            ),
            'AUD_USD': MarketSession(
                instrument='AUD_USD',
                open_time=time(22, 0),
                close_time=time(22, 0),
                open_days={0, 1, 2, 3, 4}
            ),
            'USD_CAD': MarketSession(
                instrument='USD_CAD',
                open_time=time(22, 0),
                close_time=time(22, 0),
                open_days={0, 1, 2, 3, 4}
            ),
            'EUR_JPY': MarketSession(
                instrument='EUR_JPY',
                open_time=time(22, 0),
                close_time=time(22, 0),
                open_days={0, 1, 2, 3, 4}
            ),
            'EUR_GBP': MarketSession(
                instrument='EUR_GBP',
                open_time=time(22, 0),
                close_time=time(22, 0),
                open_days={0, 1, 2, 3, 4}
            )
        }
        
        # Known market holidays (simplified - in production would use full holiday calendar)
        self.known_holidays: Set[str] = {
            "2024-01-01",  # New Year's Day
            "2024-12-25",  # Christmas Day
            # Add more holidays as needed
        }
        
        # Warning periods (minutes before market events)
        self.closing_warning_minutes = 30
        self.opening_warning_minutes = 30
        
    def add_market_schedule(self, schedule: MarketSession):
        """Add or update market schedule for instrument"""
        self.market_schedules[schedule.instrument] = schedule
        logger.info(f"Added market schedule for {schedule.instrument}")
        
    def is_holiday(self, date: datetime) -> bool:
        """Check if given date is a market holiday"""
        date_str = date.strftime("%Y-%m-%d")
        return date_str in self.known_holidays
        
    def get_market_status(self, instrument: str, current_time: Optional[datetime] = None) -> MarketStatus:
        """Get current market status for instrument"""
        if current_time is None:
            current_time = datetime.now(timezone.utc)
            
        # Check if instrument has schedule
        if instrument not in self.market_schedules:
            logger.warning(f"No market schedule found for {instrument}")
            return MarketStatus.UNKNOWN
            
        schedule = self.market_schedules[instrument]
        
        # Check for holidays
        if self.is_holiday(current_time):
            return MarketStatus.HOLIDAY
            
        # Get current day of week (0=Monday, 6=Sunday)
        current_weekday = current_time.weekday()
        current_time_only = current_time.time()
        
        # Check if opening soon (before trading hours) - check this first for Sunday
        if self._is_opening_soon(current_time, schedule):
            return MarketStatus.OPENING_SOON
            
        # Check for weekend
        if current_weekday not in schedule.open_days:
            # Check if it's Sunday after market open time (market opens Sunday night)
            if current_weekday == 6 and current_time_only >= schedule.open_time:
                return MarketStatus.OPEN
            # Saturday is always weekend
            elif current_weekday == 5:
                return MarketStatus.WEEKEND
            else:
                return MarketStatus.WEEKEND
            
        # Check if within trading hours
        if self._is_within_trading_hours(current_time, schedule):
            # Check if closing soon
            if self._is_closing_soon(current_time, schedule):
                return MarketStatus.CLOSING_SOON
            return MarketStatus.OPEN
        else:
            return MarketStatus.CLOSED
            
    def _is_within_trading_hours(self, current_time: datetime, schedule: MarketSession) -> bool:
        """Check if current time is within trading hours"""
        current_weekday = current_time.weekday()
        current_time_only = current_time.time()
        
        # For 24/5 forex markets, trading runs from Sunday 22:00 to Friday 22:00 UTC
        if current_weekday == 6:  # Sunday
            return current_time_only >= schedule.open_time
        elif current_weekday in {0, 1, 2, 3}:  # Monday-Thursday
            return True  # 24 hour trading
        elif current_weekday == 4:  # Friday
            return current_time_only < schedule.close_time
        else:  # Saturday
            return False
            
    def _is_closing_soon(self, current_time: datetime, schedule: MarketSession) -> bool:
        """Check if market is closing soon"""
        if current_time.weekday() == 4:  # Friday
            close_datetime = current_time.replace(
                hour=schedule.close_time.hour,
                minute=schedule.close_time.minute,
                second=0,
                microsecond=0
            )
            time_until_close = (close_datetime - current_time).total_seconds() / 60
            return 0 < time_until_close <= self.closing_warning_minutes
        return False
        
    def _is_opening_soon(self, current_time: datetime, schedule: MarketSession) -> bool:
        """Check if market is opening soon"""
        if current_time.weekday() == 6:  # Sunday
            open_datetime = current_time.replace(
                hour=schedule.open_time.hour,
                minute=schedule.open_time.minute,
                second=0,
                microsecond=0
            )
            time_until_open = (open_datetime - current_time).total_seconds() / 60
            # Market is opening soon if we're within warning period and before open time
            return 0 < time_until_open <= self.opening_warning_minutes
        return False
        
    def get_next_market_event(self, instrument: str, current_time: Optional[datetime] = None) -> Optional[datetime]:
        """Get the next market open/close event"""
        if current_time is None:
            current_time = datetime.now(timezone.utc)
            
        if instrument not in self.market_schedules:
            return None
            
        schedule = self.market_schedules[instrument]
        current_status = self.get_market_status(instrument, current_time)
        
        if current_status in {MarketStatus.OPEN, MarketStatus.CLOSING_SOON}:
            # Market is open, find next close time
            if current_time.weekday() == 4:  # Friday
                return current_time.replace(
                    hour=schedule.close_time.hour,
                    minute=schedule.close_time.minute,
                    second=0,
                    microsecond=0
                )
            else:
                # Find next Friday close
                days_until_friday = (4 - current_time.weekday()) % 7
                if days_until_friday == 0:
                    days_until_friday = 7
                next_close = current_time + timedelta(days=days_until_friday)
                return next_close.replace(
                    hour=schedule.close_time.hour,
                    minute=schedule.close_time.minute,
                    second=0,
                    microsecond=0
                )
        else:
            # Market is closed, find next open time
            if current_time.weekday() == 6:  # Sunday
                return current_time.replace(
                    hour=schedule.open_time.hour,
                    minute=schedule.open_time.minute,
                    second=0,
                    microsecond=0
                )
            else:
                # Find next Sunday open
                days_until_sunday = (6 - current_time.weekday()) % 7
                if days_until_sunday == 0:
                    days_until_sunday = 7
                next_open = current_time + timedelta(days=days_until_sunday)
                return next_open.replace(
                    hour=schedule.open_time.hour,
                    minute=schedule.open_time.minute,
                    second=0,
                    microsecond=0
                )

class MarketSessionHandler:
    """Handles market session monitoring and notifications"""
    
    def __init__(self, schedule_manager: Optional[MarketScheduleManager] = None):
        self.schedule_manager = schedule_manager or MarketScheduleManager()
        
        # Tracked instruments
        self.monitored_instruments: Set[str] = set()
        
        # Session state tracking
        self.instrument_states: Dict[str, SessionState] = {}
        self.last_status: Dict[str, MarketStatus] = {}
        
        # Event callbacks
        self.status_change_callbacks: List[Callable[[SessionEvent], None]] = []
        self.stale_price_callbacks: List[Callable[[str, datetime], None]] = []
        
        # Stale price detection
        self.last_price_times: Dict[str, datetime] = {}
        self.stale_price_threshold_minutes = 15
        
        # Background monitoring
        self.monitoring_task: Optional[asyncio.Task] = None
        self.is_monitoring = False
        self.check_interval = 60  # Check every minute
        
        # Session metrics
        self.session_metrics = {
            'status_changes': 0,
            'stale_price_alerts': 0,
            'last_check': None
        }
        
    def add_instrument(self, instrument: str):
        """Add instrument to monitoring"""
        self.monitored_instruments.add(instrument)
        self.instrument_states[instrument] = SessionState.INACTIVE
        
        # Initialize status
        status = self.schedule_manager.get_market_status(instrument)
        self.last_status[instrument] = status
        
        if status == MarketStatus.OPEN:
            self.instrument_states[instrument] = SessionState.ACTIVE
            
        logger.info(f"Added {instrument} to market session monitoring (status: {status.value})")
        
    def remove_instrument(self, instrument: str):
        """Remove instrument from monitoring"""
        self.monitored_instruments.discard(instrument)
        self.instrument_states.pop(instrument, None)
        self.last_status.pop(instrument, None)
        self.last_price_times.pop(instrument, None)
        
        logger.info(f"Removed {instrument} from market session monitoring")
        
    def update_price_time(self, instrument: str, timestamp: datetime):
        """Update last price time for stale detection"""
        self.last_price_times[instrument] = timestamp
        
    def add_status_change_callback(self, callback: Callable[[SessionEvent], None]):
        """Add callback for market status changes"""
        self.status_change_callbacks.append(callback)
        
    def add_stale_price_callback(self, callback: Callable[[str, datetime], None]):
        """Add callback for stale price detection"""
        self.stale_price_callbacks.append(callback)
        
    async def start_monitoring(self):
        """Start background market session monitoring"""
        if self.is_monitoring:
            return
            
        self.is_monitoring = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Started market session monitoring")
        
    async def stop_monitoring(self):
        """Stop background monitoring"""
        if not self.is_monitoring:
            return
            
        self.is_monitoring = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            
        logger.info("Stopped market session monitoring")
        
    async def _monitoring_loop(self):
        """Background monitoring loop"""
        while self.is_monitoring:
            try:
                await self._check_all_instruments()
                await self._check_stale_prices()
                self.session_metrics['last_check'] = datetime.now(timezone.utc)
                
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error in market session monitoring: {e}")
                await asyncio.sleep(5)  # Short delay before retry
                
    async def _check_all_instruments(self):
        """Check market status for all monitored instruments"""
        for instrument in self.monitored_instruments:
            await self._check_instrument_status(instrument)
            
    async def _check_instrument_status(self, instrument: str):
        """Check and handle status changes for instrument"""
        current_status = self.schedule_manager.get_market_status(instrument)
        previous_status = self.last_status.get(instrument)
        
        if current_status != previous_status:
            # Status changed
            self.last_status[instrument] = current_status
            self.session_metrics['status_changes'] += 1
            
            # Update session state
            if current_status == MarketStatus.OPEN:
                self.instrument_states[instrument] = SessionState.ACTIVE
            elif current_status in {MarketStatus.CLOSED, MarketStatus.WEEKEND, MarketStatus.HOLIDAY}:
                self.instrument_states[instrument] = SessionState.INACTIVE
            else:
                self.instrument_states[instrument] = SessionState.TRANSITIONING
                
            # Create and send event
            next_change = self.schedule_manager.get_next_market_event(instrument)
            event = SessionEvent(
                instrument=instrument,
                status=current_status,
                timestamp=datetime.now(timezone.utc),
                next_change=next_change,
                message=f"Market status changed to {current_status.value}"
            )
            
            await self._notify_status_change(event)
            
    async def _check_stale_prices(self):
        """Check for stale prices during market hours"""
        current_time = datetime.now(timezone.utc)
        
        for instrument in self.monitored_instruments:
            # Only check for stale prices when market should be open
            status = self.schedule_manager.get_market_status(instrument)
            if status != MarketStatus.OPEN:
                continue
                
            last_price_time = self.last_price_times.get(instrument)
            if not last_price_time:
                continue
                
            # Check if price is stale
            minutes_since_price = (current_time - last_price_time).total_seconds() / 60
            if minutes_since_price > self.stale_price_threshold_minutes:
                self.session_metrics['stale_price_alerts'] += 1
                await self._notify_stale_price(instrument, last_price_time)
                
    async def _notify_status_change(self, event: SessionEvent):
        """Notify callbacks of status change"""
        logger.info(f"Market status change: {event.instrument} -> {event.status.value}")
        
        for callback in self.status_change_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Error in status change callback: {e}")
                
    async def _notify_stale_price(self, instrument: str, last_price_time: datetime):
        """Notify callbacks of stale price"""
        logger.warning(f"Stale price detected for {instrument}, last update: {last_price_time}")
        
        for callback in self.stale_price_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(instrument, last_price_time)
                else:
                    callback(instrument, last_price_time)
            except Exception as e:
                logger.error(f"Error in stale price callback: {e}")
                
    def get_instrument_status(self, instrument: str) -> Optional[MarketStatus]:
        """Get current market status for instrument"""
        if instrument not in self.monitored_instruments:
            return None
        return self.schedule_manager.get_market_status(instrument)
        
    def get_session_state(self, instrument: str) -> Optional[SessionState]:
        """Get current session state for instrument"""
        return self.instrument_states.get(instrument)
        
    def is_tradeable(self, instrument: str) -> bool:
        """Check if instrument is currently tradeable"""
        status = self.get_instrument_status(instrument)
        return status == MarketStatus.OPEN
        
    def get_metrics(self) -> Dict:
        """Get session monitoring metrics"""
        return {
            'monitored_instruments': len(self.monitored_instruments),
            'active_sessions': sum(1 for state in self.instrument_states.values() 
                                 if state == SessionState.ACTIVE),
            'inactive_sessions': sum(1 for state in self.instrument_states.values() 
                                   if state == SessionState.INACTIVE),
            'metrics': self.session_metrics.copy(),
            'instrument_states': {
                instrument: {
                    'status': self.last_status.get(instrument, MarketStatus.UNKNOWN).value,
                    'state': state.value,
                    'last_price_time': self.last_price_times.get(instrument).isoformat() 
                                     if self.last_price_times.get(instrument) else None
                }
                for instrument, state in self.instrument_states.items()
            }
        }
        
    def get_trading_schedule(self, instrument: str) -> Optional[Dict]:
        """Get trading schedule information for instrument"""
        if instrument not in self.schedule_manager.market_schedules:
            return None
            
        schedule = self.schedule_manager.market_schedules[instrument]
        current_status = self.schedule_manager.get_market_status(instrument)
        next_event = self.schedule_manager.get_next_market_event(instrument)
        
        return {
            'instrument': instrument,
            'current_status': current_status.value,
            'next_event': next_event.isoformat() if next_event else None,
            'open_time': schedule.open_time.strftime('%H:%M'),
            'close_time': schedule.close_time.strftime('%H:%M'),
            'trading_days': list(schedule.open_days),
            'timezone': schedule.timezone_name
        }