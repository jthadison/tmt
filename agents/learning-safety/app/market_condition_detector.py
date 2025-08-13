"""
Market Condition Anomaly Detection

Detects abnormal market conditions that should trigger learning circuit breakers,
including flash crashes, gaps, volatility spikes, and news events.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
from statistics import stdev, mean

logger = logging.getLogger(__name__)


class MarketConditionType(Enum):
    """Types of market condition anomalies"""
    FLASH_CRASH = "flash_crash"
    PRICE_GAP = "price_gap"
    VOLATILITY_SPIKE = "volatility_spike"
    VOLUME_SPIKE = "volume_spike"
    SPREAD_WIDENING = "spread_widening"
    NEWS_EVENT = "news_event"
    MARKET_HOURS = "market_hours"


class Severity(Enum):
    """Anomaly severity levels"""
    LOW = "low"
    MEDIUM = "medium" 
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class MarketData:
    """Market data point"""
    timestamp: datetime
    symbol: str
    bid: Decimal
    ask: Decimal
    volume: int
    price: Decimal
    
    @property
    def spread(self) -> Decimal:
        """Calculate bid-ask spread"""
        return self.ask - self.bid


@dataclass
class MarketConditionThresholds:
    """Configuration thresholds for market condition detection"""
    # Volatility thresholds
    max_volatility_spike: float = 3.0  # 3x normal volatility
    max_gap_size: Decimal = Decimal("100")  # 100+ pips
    max_price_movement: float = 0.05  # 5% in 5 minutes
    
    # Volume thresholds
    min_volume_for_learning: int = 1000  # Minimum volume required
    max_volume_spike: float = 10.0  # 10x normal volume
    
    # Spread thresholds
    max_spread_widening: float = 5.0  # 5x normal spread
    
    # News event impact
    news_event_lockout_minutes: int = 60  # 60 minutes after high-impact news
    
    # Market hours
    exclude_market_open: bool = True  # First 30 minutes
    exclude_market_close: bool = True  # Last 30 minutes
    exclude_weekend_gaps: bool = True  # Sunday evening gaps


@dataclass
class MarketConditionAnomaly:
    """Detected market condition anomaly"""
    detection_id: str
    timestamp: datetime
    condition_type: MarketConditionType
    severity: Severity
    confidence: float  # 0-1
    
    # Metrics
    observed_value: float
    expected_value: float
    threshold: float
    deviation_magnitude: float
    
    # Context
    symbol: str
    description: str
    potential_causes: List[str]
    
    # Recommendation
    learning_safe: bool
    quarantine_recommended: bool
    lockout_duration_minutes: int


class FlashCrashDetector:
    """Detects flash crash events"""
    
    def __init__(self, thresholds: MarketConditionThresholds):
        self.thresholds = thresholds
        self.price_history: Dict[str, List[Tuple[datetime, Decimal]]] = {}
        
    def detect(self, data: MarketData) -> Optional[MarketConditionAnomaly]:
        """Detect flash crash conditions"""
        symbol = data.symbol
        
        # Maintain price history (last 10 minutes)
        if symbol not in self.price_history:
            self.price_history[symbol] = []
            
        cutoff_time = data.timestamp - timedelta(minutes=10)
        self.price_history[symbol] = [
            (ts, price) for ts, price in self.price_history[symbol] 
            if ts > cutoff_time
        ]
        self.price_history[symbol].append((data.timestamp, data.price))
        
        if len(self.price_history[symbol]) < 6:  # Need enough data points
            return None
            
        # Calculate price movement in last 5 minutes
        five_min_ago = data.timestamp - timedelta(minutes=5)
        recent_entries = [
            (ts, price) for ts, price in self.price_history[symbol] 
            if ts >= five_min_ago
        ]
        
        if len(recent_entries) < 2:
            return None
            
        # Get first and last prices in the window
        recent_entries.sort()  # Sort by timestamp
        start_price = recent_entries[0][1]
        end_price = recent_entries[-1][1]
            
        price_change = abs(float(end_price - start_price) / float(start_price))
        
        if price_change > self.thresholds.max_price_movement:
            # Calculate volatility for severity assessment
            recent_prices = [float(entry[1]) for entry in recent_entries]
            volatility = stdev(recent_prices) if len(recent_prices) > 1 else 0
            expected_volatility = volatility / 3  # Baseline assumption
            
            severity = self._calculate_severity(price_change, self.thresholds.max_price_movement, 1.8)  # Lower critical threshold
            
            return MarketConditionAnomaly(
                detection_id=f"flash_crash_{symbol}_{data.timestamp.isoformat()}",
                timestamp=data.timestamp,
                condition_type=MarketConditionType.FLASH_CRASH,
                severity=severity,
                confidence=min(1.0, price_change / self.thresholds.max_price_movement),
                observed_value=price_change,
                expected_value=expected_volatility,
                threshold=self.thresholds.max_price_movement,
                deviation_magnitude=price_change - self.thresholds.max_price_movement,
                symbol=symbol,
                description=f"Flash crash detected: {price_change:.2%} price movement in 5 minutes",
                potential_causes=["Market manipulation", "Algorithm error", "News event", "Liquidity crisis"],
                learning_safe=False,
                quarantine_recommended=True,
                lockout_duration_minutes=30 if severity in [Severity.HIGH, Severity.CRITICAL] else 15
            )
            
        return None
    
    def _calculate_severity(self, observed: float, threshold: float, critical_multiplier: float) -> Severity:
        """Calculate severity based on threshold deviation"""
        ratio = observed / threshold
        if ratio >= critical_multiplier:
            return Severity.CRITICAL
        elif ratio >= 1.3:  # Lowered from 1.5 for 6%+ movements
            return Severity.HIGH
        elif ratio >= 1.1:  # Lowered from 1.2
            return Severity.MEDIUM
        else:
            return Severity.LOW


class GapDetector:
    """Detects price gaps between sessions"""
    
    def __init__(self, thresholds: MarketConditionThresholds):
        self.thresholds = thresholds
        self.last_close_prices: Dict[str, Decimal] = {}
        
    def detect(self, data: MarketData) -> Optional[MarketConditionAnomaly]:
        """Detect price gaps"""
        symbol = data.symbol
        
        # Check if this is a new session (simplified - would need market hours logic)
        if self._is_session_open(data.timestamp):
            if symbol in self.last_close_prices:
                gap_size = abs(data.price - self.last_close_prices[symbol])
                
                if gap_size > self.thresholds.max_gap_size:
                    gap_percentage = float(gap_size / self.last_close_prices[symbol])
                    
                    # Weekend gaps are often normal and excluded if configured
                    is_weekend_gap = self._is_weekend_gap(data.timestamp)
                    if is_weekend_gap and self.thresholds.exclude_weekend_gaps:
                        return None
                    
                    severity = self._calculate_gap_severity(gap_percentage)
                    
                    return MarketConditionAnomaly(
                        detection_id=f"gap_{symbol}_{data.timestamp.isoformat()}",
                        timestamp=data.timestamp,
                        condition_type=MarketConditionType.PRICE_GAP,
                        severity=severity,
                        confidence=min(1.0, float(gap_size) / float(self.thresholds.max_gap_size)),
                        observed_value=float(gap_size),
                        expected_value=0.0,
                        threshold=float(self.thresholds.max_gap_size),
                        deviation_magnitude=float(gap_size) - float(self.thresholds.max_gap_size),
                        symbol=symbol,
                        description=f"Price gap detected: {gap_size} pips ({gap_percentage:.2%})",
                        potential_causes=["Weekend news", "Market open volatility", "Economic announcements"],
                        learning_safe=False if severity in [Severity.HIGH, Severity.CRITICAL] else True,
                        quarantine_recommended=severity in [Severity.HIGH, Severity.CRITICAL],
                        lockout_duration_minutes=60 if is_weekend_gap else 30
                    )
        
        # Update last close price (simplified)
        if self._is_session_close(data.timestamp):
            self.last_close_prices[symbol] = data.price
            
        return None
    
    def _is_session_open(self, timestamp: datetime) -> bool:
        """Check if this is near session open (simplified)"""
        # This is a simplified version - real implementation would need proper market hours
        hour = timestamp.hour
        return hour == 0 or hour == 9  # Forex midnight rollover or equity market open
    
    def _is_session_close(self, timestamp: datetime) -> bool:
        """Check if this is near session close (simplified)"""
        hour = timestamp.hour
        return hour == 16 or hour == 23  # Equity close or forex day end
    
    def _is_weekend_gap(self, timestamp: datetime) -> bool:
        """Check if this is a weekend gap"""
        return timestamp.weekday() == 6  # Sunday
    
    def _calculate_gap_severity(self, gap_percentage: float) -> Severity:
        """Calculate gap severity"""
        if gap_percentage >= 0.02:  # 2%+
            return Severity.CRITICAL
        elif gap_percentage >= 0.01:  # 1%+
            return Severity.HIGH
        elif gap_percentage >= 0.005:  # 0.5%+
            return Severity.MEDIUM
        else:
            return Severity.LOW


class VolatilityDetector:
    """Detects volatility spikes"""
    
    def __init__(self, thresholds: MarketConditionThresholds):
        self.thresholds = thresholds
        self.volatility_history: Dict[str, List[Tuple[datetime, float]]] = {}
        
    def detect(self, data: MarketData) -> Optional[MarketConditionAnomaly]:
        """Detect volatility spikes"""
        symbol = data.symbol
        
        # Calculate current volatility (simplified ATR-like calculation)
        current_volatility = self._calculate_current_volatility(data)
        
        if symbol not in self.volatility_history:
            self.volatility_history[symbol] = []
            
        # Maintain volatility history (last 24 hours)
        cutoff_time = data.timestamp - timedelta(hours=24)
        self.volatility_history[symbol] = [
            (ts, vol) for ts, vol in self.volatility_history[symbol] 
            if ts > cutoff_time
        ]
        self.volatility_history[symbol].append((data.timestamp, current_volatility))
        
        if len(self.volatility_history[symbol]) < 20:  # Need baseline
            return None
            
        # Calculate baseline volatility
        baseline_volatilities = [vol for _, vol in self.volatility_history[symbol][:-1]]
        baseline_volatility = mean(baseline_volatilities)
        
        volatility_spike = current_volatility / baseline_volatility if baseline_volatility > 0 else 0
        
        if volatility_spike > self.thresholds.max_volatility_spike:
            severity = self._calculate_volatility_severity(volatility_spike)
            
            return MarketConditionAnomaly(
                detection_id=f"volatility_{symbol}_{data.timestamp.isoformat()}",
                timestamp=data.timestamp,
                condition_type=MarketConditionType.VOLATILITY_SPIKE,
                severity=severity,
                confidence=min(1.0, volatility_spike / self.thresholds.max_volatility_spike),
                observed_value=current_volatility,
                expected_value=baseline_volatility,
                threshold=baseline_volatility * self.thresholds.max_volatility_spike,
                deviation_magnitude=current_volatility - (baseline_volatility * self.thresholds.max_volatility_spike),
                symbol=symbol,
                description=f"Volatility spike: {volatility_spike:.1f}x normal levels",
                potential_causes=["News release", "Market stress", "Low liquidity", "Algorithm activity"],
                learning_safe=False,
                quarantine_recommended=severity in [Severity.HIGH, Severity.CRITICAL],
                lockout_duration_minutes=15 if severity == Severity.MEDIUM else 30
            )
            
        return None
    
    def _calculate_current_volatility(self, data: MarketData) -> float:
        """Calculate current volatility metric (simplified)"""
        # This is a simplified calculation - real implementation would use proper ATR
        spread_percentage = float(data.spread / data.price) if data.price > 0 else 0
        return spread_percentage * 100  # Convert to basis points
    
    def _calculate_volatility_severity(self, spike_ratio: float) -> Severity:
        """Calculate volatility spike severity"""
        if spike_ratio >= 10:
            return Severity.CRITICAL
        elif spike_ratio >= 5:
            return Severity.HIGH
        elif spike_ratio >= 3:
            return Severity.MEDIUM
        else:
            return Severity.LOW


class MarketConditionDetector:
    """Main market condition anomaly detector"""
    
    def __init__(self, thresholds: Optional[MarketConditionThresholds] = None):
        self.thresholds = thresholds or MarketConditionThresholds()
        self.flash_crash_detector = FlashCrashDetector(self.thresholds)
        self.gap_detector = GapDetector(self.thresholds)
        self.volatility_detector = VolatilityDetector(self.thresholds)
        
    def detect_anomalies(self, data: MarketData) -> List[MarketConditionAnomaly]:
        """Detect all market condition anomalies"""
        anomalies = []
        
        # Run all detectors
        detectors = [
            self.flash_crash_detector,
            self.gap_detector,
            self.volatility_detector
        ]
        
        for detector in detectors:
            try:
                anomaly = detector.detect(data)
                if anomaly:
                    anomalies.append(anomaly)
                    logger.info(f"Market condition anomaly detected: {anomaly.condition_type.value} "
                              f"for {anomaly.symbol} at {anomaly.timestamp}")
            except Exception as e:
                logger.error(f"Error in detector {detector.__class__.__name__}: {e}")
                
        # Check market hours exclusions
        market_hours_anomaly = self._check_market_hours(data)
        if market_hours_anomaly:
            anomalies.append(market_hours_anomaly)
            
        return anomalies
    
    def _check_market_hours(self, data: MarketData) -> Optional[MarketConditionAnomaly]:
        """Check if current time should exclude learning due to market hours"""
        if not (self.thresholds.exclude_market_open or self.thresholds.exclude_market_close):
            return None
            
        hour = data.timestamp.hour
        minute = data.timestamp.minute
        
        # Check market open (simplified - assuming 9:30 AM market open)
        if self.thresholds.exclude_market_open:
            if hour == 9 and minute < 30:  # First 30 minutes
                return MarketConditionAnomaly(
                    detection_id=f"market_open_{data.symbol}_{data.timestamp.isoformat()}",
                    timestamp=data.timestamp,
                    condition_type=MarketConditionType.MARKET_HOURS,
                    severity=Severity.LOW,
                    confidence=1.0,
                    observed_value=hour + minute/60,
                    expected_value=10.0,  # After 10 AM
                    threshold=9.5,  # 9:30 AM
                    deviation_magnitude=0,
                    symbol=data.symbol,
                    description="Market opening period - high volatility expected",
                    potential_causes=["Market open volatility", "Overnight news impact"],
                    learning_safe=False,
                    quarantine_recommended=False,
                    lockout_duration_minutes=30
                )
        
        # Check market close (simplified - assuming 4:00 PM market close)
        if self.thresholds.exclude_market_close:
            if hour == 15 and minute >= 30:  # Last 30 minutes
                return MarketConditionAnomaly(
                    detection_id=f"market_close_{data.symbol}_{data.timestamp.isoformat()}",
                    timestamp=data.timestamp,
                    condition_type=MarketConditionType.MARKET_HOURS,
                    severity=Severity.LOW,
                    confidence=1.0,
                    observed_value=hour + minute/60,
                    expected_value=14.0,  # Before 2 PM
                    threshold=15.5,  # 3:30 PM
                    deviation_magnitude=0,
                    symbol=data.symbol,
                    description="Market closing period - end-of-day activity",
                    potential_causes=["End-of-day rebalancing", "Position squaring"],
                    learning_safe=False,
                    quarantine_recommended=False,
                    lockout_duration_minutes=30
                )
                
        return None