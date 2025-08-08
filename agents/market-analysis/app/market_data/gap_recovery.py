"""Gap recovery and connection resilience system for market data feeds."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """Connection state enumeration."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


@dataclass
class DataGap:
    """Represents a detected gap in market data."""
    symbol: str
    source: str
    start_time: datetime
    end_time: datetime
    expected_intervals: int
    recovery_status: str = "pending"  # pending, in_progress, completed, failed
    

class CircuitBreaker:
    """
    Circuit breaker for connection failures.
    
    Implements three states: CLOSED (normal), OPEN (failed), HALF_OPEN (testing).
    Prevents continuous failed connection attempts while allowing periodic retries.
    """
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 30):
        """
        Initialize circuit breaker.
        
        @param failure_threshold: Number of failures before opening circuit
        @param timeout: Seconds to wait before attempting reset
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        
    def call(self, func):
        """
        Execute function with circuit breaker protection.
        
        @param func: Function to execute
        @returns: Function result or raises exception
        """
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
            else:
                raise ConnectionError("Circuit breaker is OPEN")
                
        try:
            result = func()
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
            
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        return (datetime.now() - self.last_failure_time).total_seconds() > self.timeout
        
    def _on_success(self):
        """Handle successful execution."""
        self.failure_count = 0
        self.state = "CLOSED"
        
    def _on_failure(self):
        """Handle failed execution."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
        elif self.state == "HALF_OPEN":
            self.state = "OPEN"


class GapRecoveryManager:
    """
    Manager for detecting and recovering data gaps.
    
    Monitors data feed continuity, detects gaps, and initiates recovery
    procedures using REST API backfill when WebSocket connections fail.
    """
    
    def __init__(self, oanda_client=None, polygon_client=None):
        """
        Initialize gap recovery manager.
        
        @param oanda_client: OANDA API client instance
        @param polygon_client: Polygon.io API client instance
        """
        self.oanda_client = oanda_client
        self.polygon_client = polygon_client
        
        # Gap detection
        self.last_seen_timestamps: Dict[str, Dict[str, datetime]] = {}  # {symbol: {source: timestamp}}
        self.detected_gaps: List[DataGap] = []
        self.gap_detection_interval = timedelta(seconds=10)  # Check every 10 seconds
        
        # Connection state tracking
        self.connection_states: Dict[str, ConnectionState] = {
            "oanda": ConnectionState.DISCONNECTED,
            "polygon": ConnectionState.DISCONNECTED
        }
        
        # Circuit breakers for each data source
        self.circuit_breakers = {
            "oanda": CircuitBreaker(failure_threshold=5, timeout=30),
            "polygon": CircuitBreaker(failure_threshold=5, timeout=30)
        }
        
        # Recovery task management
        self.recovery_tasks: Set[asyncio.Task] = set()
        self.max_concurrent_recoveries = 3
        
    async def monitor_connection_health(self):
        """
        Monitor connection health and detect data gaps.
        
        Runs continuously to check for missing data and trigger recovery.
        """
        while True:
            try:
                await self._check_for_gaps()
                await self._process_pending_recoveries()
                await asyncio.sleep(self.gap_detection_interval.total_seconds())
                
            except Exception as e:
                logger.error(f"Error in connection health monitoring: {e}")
                await asyncio.sleep(5)  # Brief pause before retrying
                
    async def _check_for_gaps(self):
        """Detect data gaps by monitoring timestamp sequences."""
        current_time = datetime.now()
        
        for symbol, sources in self.last_seen_timestamps.items():
            for source, last_timestamp in sources.items():
                # Check if too much time has passed since last update
                time_since_update = current_time - last_timestamp
                
                # For real-time data, expect updates at least every 60 seconds
                if time_since_update > timedelta(seconds=60):
                    await self._detect_gap(symbol, source, last_timestamp, current_time)
                    
    async def _detect_gap(self, symbol: str, source: str, start_time: datetime, end_time: datetime):
        """
        Detect and record a data gap.
        
        @param symbol: Symbol with detected gap
        @param source: Data source (oanda/polygon)
        @param start_time: Gap start time
        @param end_time: Gap end time
        """
        # Calculate expected number of data points (assuming 1-minute intervals)
        duration_minutes = (end_time - start_time).total_seconds() / 60
        expected_intervals = max(1, int(duration_minutes))
        
        gap = DataGap(
            symbol=symbol,
            source=source,
            start_time=start_time,
            end_time=end_time,
            expected_intervals=expected_intervals
        )
        
        # Check if gap already exists
        existing_gap = next(
            (g for g in self.detected_gaps 
             if g.symbol == symbol and g.source == source and 
             abs((g.start_time - start_time).total_seconds()) < 60),
            None
        )
        
        if not existing_gap:
            self.detected_gaps.append(gap)
            logger.warning(f"Data gap detected: {symbol} ({source}) from {start_time} to {end_time}")
            
            # Trigger recovery if not too many concurrent recoveries
            if len(self.recovery_tasks) < self.max_concurrent_recoveries:
                task = asyncio.create_task(self._recover_gap(gap))
                self.recovery_tasks.add(task)
                task.add_done_callback(self.recovery_tasks.discard)
                
    async def _recover_gap(self, gap: DataGap):
        """
        Recover data gap using REST API backfill.
        
        @param gap: DataGap to recover
        """
        try:
            gap.recovery_status = "in_progress"
            logger.info(f"Starting gap recovery for {gap.symbol} ({gap.source})")
            
            if gap.source == "oanda" and self.oanda_client:
                await self._recover_oanda_gap(gap)
            elif gap.source == "polygon" and self.polygon_client:
                await self._recover_polygon_gap(gap)
            else:
                logger.error(f"No client available for gap recovery: {gap.source}")
                gap.recovery_status = "failed"
                return
                
            gap.recovery_status = "completed"
            logger.info(f"Gap recovery completed for {gap.symbol} ({gap.source})")
            
        except Exception as e:
            logger.error(f"Gap recovery failed for {gap.symbol} ({gap.source}): {e}")
            gap.recovery_status = "failed"
            
    async def _recover_oanda_gap(self, gap: DataGap):
        """Recover OANDA data gap using historical candles."""
        def fetch_data():
            # Use circuit breaker protection
            return self.circuit_breakers["oanda"].call(
                lambda: asyncio.create_task(
                    self.oanda_client.get_candles(
                        instrument=gap.symbol,
                        granularity="M1",
                        from_time=gap.start_time,
                        to_time=gap.end_time
                    )
                )
            )
        
        try:
            task = fetch_data()
            candles = await task
            
            logger.info(f"Recovered {len(candles)} OANDA candles for {gap.symbol}")
            # Note: In production, these candles would be processed and stored
            
        except Exception as e:
            logger.error(f"OANDA gap recovery failed: {e}")
            raise
            
    async def _recover_polygon_gap(self, gap: DataGap):
        """Recover Polygon data gap using aggregate data."""
        def fetch_data():
            return self.circuit_breakers["polygon"].call(
                lambda: asyncio.create_task(
                    self.polygon_client.get_aggregates(
                        ticker=gap.symbol,
                        multiplier=1,
                        timespan="minute",
                        from_date=gap.start_time.strftime("%Y-%m-%d"),
                        to_date=gap.end_time.strftime("%Y-%m-%d")
                    )
                )
            )
        
        try:
            task = fetch_data()
            aggregates = await task
            
            logger.info(f"Recovered {len(aggregates)} Polygon aggregates for {gap.symbol}")
            # Note: In production, these aggregates would be processed and stored
            
        except Exception as e:
            logger.error(f"Polygon gap recovery failed: {e}")
            raise
            
    async def _process_pending_recoveries(self):
        """Process and clean up completed recovery tasks."""
        # Remove completed gaps
        completed_gaps = [g for g in self.detected_gaps if g.recovery_status == "completed"]
        for gap in completed_gaps:
            self.detected_gaps.remove(gap)
            
        # Log failed recoveries (keep for manual investigation)
        failed_gaps = [g for g in self.detected_gaps if g.recovery_status == "failed"]
        if failed_gaps:
            logger.warning(f"Failed gap recoveries: {len(failed_gaps)}")
            
    def update_last_seen(self, symbol: str, source: str, timestamp: datetime):
        """
        Update last seen timestamp for gap detection.
        
        @param symbol: Symbol that was updated
        @param source: Data source
        @param timestamp: Timestamp of last data
        """
        if symbol not in self.last_seen_timestamps:
            self.last_seen_timestamps[symbol] = {}
        self.last_seen_timestamps[symbol][source] = timestamp
        
    def set_connection_state(self, source: str, state: ConnectionState):
        """
        Update connection state for a data source.
        
        @param source: Data source name
        @param state: New connection state
        """
        if source in self.connection_states:
            old_state = self.connection_states[source]
            self.connection_states[source] = state
            
            if old_state != state:
                logger.info(f"Connection state changed for {source}: {old_state.value} -> {state.value}")
                
    def get_connection_health(self) -> Dict[str, Any]:
        """
        Get current connection health status.
        
        @returns: Dictionary with health information
        """
        return {
            "connection_states": {k: v.value for k, v in self.connection_states.items()},
            "circuit_breakers": {
                source: {
                    "state": breaker.state,
                    "failure_count": breaker.failure_count,
                    "last_failure": breaker.last_failure_time.isoformat() if breaker.last_failure_time else None
                }
                for source, breaker in self.circuit_breakers.items()
            },
            "active_gaps": len([g for g in self.detected_gaps if g.recovery_status != "completed"]),
            "active_recoveries": len(self.recovery_tasks),
            "total_gaps_detected": len(self.detected_gaps)
        }
        
    async def force_recovery(self, symbol: str, source: str, start_time: datetime, end_time: datetime):
        """
        Force manual gap recovery for specific time range.
        
        @param symbol: Symbol to recover
        @param source: Data source
        @param start_time: Recovery start time
        @param end_time: Recovery end time
        """
        gap = DataGap(
            symbol=symbol,
            source=source,
            start_time=start_time,
            end_time=end_time,
            expected_intervals=int((end_time - start_time).total_seconds() / 60)
        )
        
        logger.info(f"Manual gap recovery initiated for {symbol} ({source})")
        await self._recover_gap(gap)