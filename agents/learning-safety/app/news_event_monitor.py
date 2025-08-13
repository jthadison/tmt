"""
News Event Impact Monitor

Monitors economic news events and their impact on market conditions,
implementing lockout periods after high-impact announcements.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from enum import Enum
import logging

from market_condition_detector import MarketConditionAnomaly, MarketConditionType, Severity

logger = logging.getLogger(__name__)


class NewsImpact(Enum):
    """News event impact levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NewsCurrency(Enum):
    """Major currencies for news events"""
    USD = "USD"
    EUR = "EUR" 
    GBP = "GBP"
    JPY = "JPY"
    CHF = "CHF"
    CAD = "CAD"
    AUD = "AUD"
    NZD = "NZD"


@dataclass
class NewsEvent:
    """Economic news event"""
    event_id: str
    title: str
    currency: NewsCurrency
    impact: NewsImpact
    scheduled_time: datetime
    actual_time: Optional[datetime] = None
    
    # Event details
    previous_value: Optional[str] = None
    forecast_value: Optional[str] = None
    actual_value: Optional[str] = None
    
    # Impact assessment
    market_moving: bool = False
    surprise_factor: float = 0.0  # 0-1, how much actual differs from forecast
    
    @property
    def is_released(self) -> bool:
        """Check if event has been released"""
        return self.actual_time is not None


@dataclass
class NewsEventLockout:
    """Active lockout period due to news event"""
    event: NewsEvent
    start_time: datetime
    end_time: datetime
    affected_symbols: Set[str]
    lockout_reason: str


class NewsEventMonitor:
    """Monitors news events and manages learning lockouts"""
    
    def __init__(self, lockout_minutes: int = 60):
        self.lockout_minutes = lockout_minutes
        self.scheduled_events: Dict[str, NewsEvent] = {}
        self.active_lockouts: List[NewsEventLockout] = []
        self.processed_events: Set[str] = set()
        
        # High-impact event types that always trigger lockouts
        self.critical_events = {
            "Non-Farm Payrolls",
            "Federal Reserve Decision",
            "ECB Decision", 
            "Bank of England Decision",
            "Bank of Japan Decision",
            "Consumer Price Index",
            "Gross Domestic Product",
            "Employment Change"
        }
        
        # Currency pair mappings for news impact
        self.currency_pairs = {
            NewsCurrency.USD: ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD"],
            NewsCurrency.EUR: ["EURUSD", "EURGBP", "EURJPY", "EURCHF", "EURCAD", "EURAUD"],
            NewsCurrency.GBP: ["GBPUSD", "EURGBP", "GBPJPY", "GBPCHF", "GBPCAD", "GBPAUD"],
            NewsCurrency.JPY: ["USDJPY", "EURJPY", "GBPJPY", "CHFJPY", "CADJPY", "AUDJPY"],
            NewsCurrency.CHF: ["USDCHF", "EURCHF", "GBPCHF", "CHFJPY"],
            NewsCurrency.CAD: ["USDCAD", "EURCAD", "GBPCAD", "CADJPY"],
            NewsCurrency.AUD: ["AUDUSD", "EURAUD", "GBPAUD", "AUDJPY"],
            NewsCurrency.NZD: ["NZDUSD", "NZDJPY"]
        }
    
    def add_scheduled_event(self, event: NewsEvent) -> None:
        """Add a scheduled news event"""
        self.scheduled_events[event.event_id] = event
        logger.info(f"Added scheduled news event: {event.title} at {event.scheduled_time}")
    
    def process_event_release(self, event_id: str, actual_time: datetime, 
                            actual_value: Optional[str] = None) -> Optional[NewsEventLockout]:
        """Process the release of a news event"""
        if event_id not in self.scheduled_events:
            logger.warning(f"Unknown news event released: {event_id}")
            return None
            
        event = self.scheduled_events[event_id]
        event.actual_time = actual_time
        event.actual_value = actual_value
        
        # Calculate surprise factor if we have forecast and actual values
        if event.forecast_value and actual_value:
            event.surprise_factor = self._calculate_surprise_factor(
                event.forecast_value, actual_value
            )
        
        # Determine if this event should trigger a lockout
        should_lockout = self._should_trigger_lockout(event)
        
        if should_lockout:
            lockout = self._create_lockout(event, actual_time)
            self.active_lockouts.append(lockout)
            self.processed_events.add(event_id)
            
            logger.warning(f"News event lockout triggered: {event.title} "
                         f"until {lockout.end_time}")
            return lockout
            
        self.processed_events.add(event_id)
        return None
    
    def check_lockout_status(self, symbol: str, timestamp: datetime) -> Optional[MarketConditionAnomaly]:
        """Check if symbol is under news event lockout"""
        # Clean up expired lockouts
        self._cleanup_expired_lockouts(timestamp)
        
        # Check if symbol is affected by any active lockout
        for lockout in self.active_lockouts:
            if symbol in lockout.affected_symbols:
                if lockout.start_time <= timestamp <= lockout.end_time:
                    return MarketConditionAnomaly(
                        detection_id=f"news_lockout_{symbol}_{timestamp.isoformat()}",
                        timestamp=timestamp,
                        condition_type=MarketConditionType.NEWS_EVENT,
                        severity=self._get_severity_for_impact(lockout.event.impact),
                        confidence=1.0,
                        observed_value=1.0,  # Binary - lockout active
                        expected_value=0.0,  # Normal state
                        threshold=0.5,  # Threshold for lockout
                        deviation_magnitude=1.0,
                        symbol=symbol,
                        description=f"News event lockout: {lockout.event.title}",
                        potential_causes=[f"High-impact {lockout.event.currency.value} news event"],
                        learning_safe=False,
                        quarantine_recommended=lockout.event.impact in [NewsImpact.HIGH, NewsImpact.CRITICAL],
                        lockout_duration_minutes=int((lockout.end_time - timestamp).total_seconds() / 60)
                    )
        
        return None
    
    def get_upcoming_events(self, hours_ahead: int = 24) -> List[NewsEvent]:
        """Get upcoming news events within specified hours"""
        cutoff_time = datetime.utcnow() + timedelta(hours=hours_ahead)
        
        upcoming = []
        for event in self.scheduled_events.values():
            if not event.is_released and event.scheduled_time <= cutoff_time:
                upcoming.append(event)
                
        return sorted(upcoming, key=lambda e: e.scheduled_time)
    
    def _should_trigger_lockout(self, event: NewsEvent) -> bool:
        """Determine if event should trigger a learning lockout"""
        # Always lockout for critical impact events
        if event.impact == NewsImpact.CRITICAL:
            return True
            
        # Always lockout for known high-impact event types
        if any(critical_type in event.title for critical_type in self.critical_events):
            return True
            
        # Lockout for high impact events
        if event.impact == NewsImpact.HIGH:
            return True
            
        # Lockout for medium impact events with high surprise factor
        if event.impact == NewsImpact.MEDIUM and event.surprise_factor > 0.7:
            return True
            
        return False
    
    def _create_lockout(self, event: NewsEvent, start_time: datetime) -> NewsEventLockout:
        """Create a news event lockout"""
        # Determine lockout duration based on impact
        duration_minutes = self.lockout_minutes
        if event.impact == NewsImpact.CRITICAL:
            duration_minutes = self.lockout_minutes * 2  # Double for critical events
        elif event.impact == NewsImpact.HIGH:
            duration_minutes = self.lockout_minutes
        elif event.impact == NewsImpact.MEDIUM:
            duration_minutes = self.lockout_minutes // 2  # Half for medium events
            
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        # Determine affected symbols
        affected_symbols = set()
        if event.currency in self.currency_pairs:
            affected_symbols.update(self.currency_pairs[event.currency])
            
        return NewsEventLockout(
            event=event,
            start_time=start_time,
            end_time=end_time,
            affected_symbols=affected_symbols,
            lockout_reason=f"{event.impact.value.title()} impact {event.currency.value} news event"
        )
    
    def _calculate_surprise_factor(self, forecast: str, actual: str) -> float:
        """Calculate surprise factor based on forecast vs actual values"""
        try:
            # Simple numeric comparison (would need more sophisticated parsing for real data)
            forecast_num = float(forecast.replace('%', '').replace('K', '000').replace('M', '000000'))
            actual_num = float(actual.replace('%', '').replace('K', '000').replace('M', '000000'))
            
            if forecast_num == 0:
                return 1.0 if actual_num != 0 else 0.0
                
            deviation = abs(actual_num - forecast_num) / abs(forecast_num)
            return min(1.0, deviation)  # Cap at 1.0
            
        except (ValueError, AttributeError):
            # If we can't parse the values, assume medium surprise
            return 0.5
    
    def _get_severity_for_impact(self, impact: NewsImpact) -> Severity:
        """Map news impact to anomaly severity"""
        mapping = {
            NewsImpact.LOW: Severity.LOW,
            NewsImpact.MEDIUM: Severity.MEDIUM,
            NewsImpact.HIGH: Severity.HIGH,
            NewsImpact.CRITICAL: Severity.CRITICAL
        }
        return mapping[impact]
    
    def _cleanup_expired_lockouts(self, current_time: datetime) -> None:
        """Remove expired lockouts"""
        self.active_lockouts = [
            lockout for lockout in self.active_lockouts 
            if lockout.end_time > current_time
        ]
    
    def get_active_lockouts(self) -> List[NewsEventLockout]:
        """Get currently active lockouts"""
        current_time = datetime.utcnow()
        self._cleanup_expired_lockouts(current_time)
        return self.active_lockouts.copy()