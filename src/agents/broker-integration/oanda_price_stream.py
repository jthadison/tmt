"""
OANDA Price Streaming Manager
Story 8.5: Real-Time Price Streaming - Task 1: Implement OANDA streaming connection
"""
import asyncio
import websockets
import json
import logging
from typing import Dict, Set, Callable, AsyncIterator, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta, UTC
from decimal import Decimal
from enum import Enum
from collections import defaultdict, deque
import traceback

from credential_manager import OandaCredentialManager

logger = logging.getLogger(__name__)

class StreamState(Enum):
    """Stream connection states"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    STREAMING = "streaming"
    RECONNECTING = "reconnecting"
    FAILED = "failed"

@dataclass
class PriceTick:
    """Represents a price tick from OANDA"""
    instrument: str
    bid: Decimal
    ask: Decimal
    spread_pips: Decimal
    timestamp: datetime
    tradeable: bool
    latency_ms: float
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'instrument': self.instrument,
            'bid': str(self.bid),
            'ask': str(self.ask),
            'spread_pips': str(self.spread_pips),
            'timestamp': self.timestamp.isoformat(),
            'tradeable': self.tradeable,
            'latency_ms': self.latency_ms
        }

@dataclass
class StreamMetrics:
    """Streaming connection metrics"""
    messages_received: int = 0
    heartbeats_received: int = 0
    errors: int = 0
    reconnection_attempts: int = 0
    last_message_time: Optional[datetime] = None
    connection_start_time: Optional[datetime] = None
    total_uptime: float = 0.0
    average_latency: float = 0.0
    
    def update_latency(self, latency: float):
        """Update running average latency"""
        if self.average_latency == 0.0:
            self.average_latency = latency
        else:
            # Simple exponential moving average
            self.average_latency = 0.1 * latency + 0.9 * self.average_latency

class HeartbeatMonitor:
    """Monitors heartbeat messages for connection health"""
    
    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self.last_heartbeat: Optional[datetime] = None
        self.is_healthy = True
        
    def update_heartbeat(self):
        """Update last heartbeat time"""
        self.last_heartbeat = datetime.now(UTC)
        self.is_healthy = True
        
    def check_health(self) -> bool:
        """Check if connection is healthy based on heartbeats"""
        if not self.last_heartbeat:
            return True  # No heartbeat received yet
            
        time_since_heartbeat = (datetime.now(UTC) - self.last_heartbeat).total_seconds()
        self.is_healthy = time_since_heartbeat < self.timeout
        return self.is_healthy

class SubscriptionManager:
    """Manages instrument subscriptions for price streaming"""
    
    def __init__(self):
        self.active_subscriptions: Set[str] = set()
        self.pending_subscriptions: Set[str] = set()
        self.subscription_callbacks: Dict[str, List[Callable]] = defaultdict(list)
        self.subscription_stats: Dict[str, Dict] = {}
        self._lock = asyncio.Lock()
        
    async def add_subscriptions(self, instruments: List[str]) -> Set[str]:
        """Add instruments to subscription list"""
        async with self._lock:
            new_instruments = set(instruments) - self.active_subscriptions
            self.pending_subscriptions.update(new_instruments)
            return new_instruments
            
    async def confirm_subscriptions(self, instruments: List[str]):
        """Move instruments from pending to active"""
        async with self._lock:
            confirmed = set(instruments) & self.pending_subscriptions
            self.active_subscriptions.update(confirmed)
            self.pending_subscriptions -= confirmed
            
            # Initialize stats for new subscriptions
            for instrument in confirmed:
                self.subscription_stats[instrument] = {
                    'price_updates': 0,
                    'last_update': None,
                    'subscribers': 0
                }
                
    async def remove_subscriptions(self, instruments: List[str]) -> Set[str]:
        """Remove instruments from subscription list"""
        async with self._lock:
            removed = set(instruments) & self.active_subscriptions
            self.active_subscriptions -= removed
            
            # Clean up stats
            for instrument in removed:
                self.subscription_stats.pop(instrument, None)
                self.subscription_callbacks.pop(instrument, None)
                
            return removed
            
    def add_price_callback(self, instrument: str, callback: Callable):
        """Add callback for specific instrument price updates"""
        self.subscription_callbacks[instrument].append(callback)
        if instrument in self.subscription_stats:
            self.subscription_stats[instrument]['subscribers'] += 1
            
    def remove_price_callback(self, instrument: str, callback: Callable):
        """Remove callback for instrument"""
        if callback in self.subscription_callbacks[instrument]:
            self.subscription_callbacks[instrument].remove(callback)
            if instrument in self.subscription_stats:
                self.subscription_stats[instrument]['subscribers'] -= 1
                
    def update_price_stats(self, instrument: str):
        """Update statistics for instrument price update"""
        if instrument in self.subscription_stats:
            self.subscription_stats[instrument]['price_updates'] += 1
            self.subscription_stats[instrument]['last_update'] = datetime.now(UTC)

class OandaStreamManager:
    """OANDA price streaming manager with WebSocket connection"""
    
    def __init__(self, 
                 credential_manager: OandaCredentialManager,
                 account_id: str,
                 environment: str = 'practice'):
        
        self.credential_manager = credential_manager
        self.account_id = account_id
        self.environment = environment
        
        # Connection management
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.state = StreamState.DISCONNECTED
        self.connection_url = self._build_stream_url()
        
        # Subscription management
        self.subscription_manager = SubscriptionManager()
        
        # Health monitoring
        self.heartbeat_monitor = HeartbeatMonitor()
        self.metrics = StreamMetrics()
        
        # Reconnection management
        self.max_reconnect_attempts = 10
        self.reconnect_delay = 1.0  # Start with 1 second
        self.max_reconnect_delay = 60.0  # Max 60 seconds
        self.current_reconnect_attempt = 0
        
        # Price data callbacks
        self.price_callbacks: List[Callable[[PriceTick], None]] = []
        self.market_status_callbacks: List[Callable[[str, str], None]] = []
        
        # Background tasks
        self.stream_task: Optional[asyncio.Task] = None
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.is_running = False
        
        # Rate limiting
        self.rate_limiter = RateLimiter(requests_per_second=5)
        
        # Price history buffer
        self.price_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        logger.info(f"Initialized OANDA stream manager for account {account_id} in {environment}")
        
    def _build_stream_url(self) -> str:
        """Build OANDA streaming URL"""
        if self.environment == 'live':
            base_url = "wss://stream-fxtrade.oanda.com"  # Correct live URL
        else:
            base_url = "wss://stream-fxpractice.oanda.com"  # Practice URL
            
        return f"{base_url}/v3/accounts/{self.account_id}/pricing/stream"
        
    async def start_streaming(self, instruments: Optional[List[str]] = None):
        """Start price streaming"""
        if self.is_running:
            logger.warning("Stream already running")
            return
            
        self.is_running = True
        logger.info("Starting OANDA price streaming")
        
        # Add initial subscriptions
        if instruments:
            await self.subscribe(instruments)
            
        # Start streaming task
        self.stream_task = asyncio.create_task(self._stream_loop())
        self.heartbeat_task = asyncio.create_task(self._heartbeat_monitor_loop())
        
    async def stop_streaming(self):
        """Stop price streaming"""
        if not self.is_running:
            return
            
        logger.info("Stopping OANDA price streaming")
        self.is_running = False
        
        # Cancel tasks
        if self.stream_task:
            self.stream_task.cancel()
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            
        # Close WebSocket
        if self.websocket:
            await self.websocket.close()
            
        self.state = StreamState.DISCONNECTED
        
    async def subscribe(self, instruments: List[str]) -> bool:
        """Subscribe to price updates for instruments"""
        try:
            # Add to subscription manager
            new_instruments = await self.subscription_manager.add_subscriptions(instruments)
            
            if not new_instruments:
                logger.debug(f"Already subscribed to all requested instruments")
                return True
                
            # If connected, update subscription
            if self.state == StreamState.STREAMING:
                success = await self._update_subscription()
                if success:
                    await self.subscription_manager.confirm_subscriptions(list(new_instruments))
                return success
            else:
                logger.info(f"Queued subscription for {len(new_instruments)} instruments")
                return True
                
        except Exception as e:
            logger.error(f"Error subscribing to instruments: {e}")
            return False
            
    async def unsubscribe(self, instruments: List[str]) -> bool:
        """Unsubscribe from price updates"""
        try:
            removed = await self.subscription_manager.remove_subscriptions(instruments)
            
            if not removed:
                logger.debug("No instruments to unsubscribe")
                return True
                
            # If connected, update subscription
            if self.state == StreamState.STREAMING:
                return await self._update_subscription()
            else:
                logger.info(f"Queued unsubscription for {len(removed)} instruments")
                return True
                
        except Exception as e:
            logger.error(f"Error unsubscribing from instruments: {e}")
            return False
            
    def add_price_callback(self, callback: Callable[[PriceTick], None]):
        """Add callback for price updates"""
        self.price_callbacks.append(callback)
        
    def remove_price_callback(self, callback: Callable[[PriceTick], None]):
        """Remove price callback"""
        if callback in self.price_callbacks:
            self.price_callbacks.remove(callback)
            
    def add_market_status_callback(self, callback: Callable[[str, str], None]):
        """Add callback for market status updates"""
        self.market_status_callbacks.append(callback)
        
    async def _stream_loop(self):
        """Main streaming loop with reconnection logic"""
        while self.is_running:
            try:
                await self._establish_connection()
                await self._stream_prices()
                
            except Exception as e:
                logger.error(f"Streaming error: {e}")
                self.metrics.errors += 1
                await self._handle_disconnection()
                
    async def _establish_connection(self):
        """Establish WebSocket connection to OANDA"""
        if not await self.rate_limiter.can_proceed():
            logger.warning("Rate limit exceeded, waiting...")
            await asyncio.sleep(1)
            
        self.state = StreamState.CONNECTING
        logger.info("Establishing OANDA streaming connection...")
        
        # Get credentials
        credentials = await self.credential_manager.retrieve_credentials(f"oanda_{self.account_id}")
        if not credentials:
            raise Exception(f"No credentials found for account {self.account_id}")
            
        # Build connection parameters
        headers = {
            "Authorization": f"Bearer {credentials['api_key']}",
            "Accept-Datetime-Format": "RFC3339",
            "User-Agent": "Adaptive-Trading-System/1.0"
        }
        
        # Add instruments to URL if subscribed
        instruments_param = ""
        if self.subscription_manager.active_subscriptions:
            instruments_param = f"?instruments={','.join(self.subscription_manager.active_subscriptions)}"
        
        full_url = f"{self.connection_url}{instruments_param}"
        
        # Establish connection
        self.websocket = await websockets.connect(
            full_url,
            extra_headers=headers,
            ping_interval=20,
            ping_timeout=10,
            close_timeout=10
        )
        
        self.state = StreamState.CONNECTED
        self.metrics.connection_start_time = datetime.now(UTC)
        self.current_reconnect_attempt = 0
        self.reconnect_delay = 1.0  # Reset reconnect delay
        
        logger.info(f"OANDA streaming connection established: {full_url}")
        
    async def _stream_prices(self):
        """Process incoming price messages"""
        self.state = StreamState.STREAMING
        
        async for message in self.websocket:
            try:
                data = json.loads(message)
                await self._process_message(data)
                
                self.metrics.messages_received += 1
                self.metrics.last_message_time = datetime.now(UTC)
                
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in stream message: {e}")
                continue
            except Exception as e:
                logger.error(f"Error processing stream message: {e}")
                continue
                
    async def _process_message(self, data: Dict):
        """Process individual stream message"""
        message_type = data.get("type")
        
        if message_type == "PRICE":
            await self._process_price_update(data)
        elif message_type == "HEARTBEAT":
            await self._process_heartbeat(data)
        else:
            logger.debug(f"Unknown message type: {message_type}")
            
    async def _process_price_update(self, price_data: Dict):
        """Process price update message"""
        try:
            instrument = price_data["instrument"]
            
            # Parse price data
            closeout_bid = Decimal(price_data["closeoutBid"])
            closeout_ask = Decimal(price_data["closeoutAsk"])
            
            # Calculate spread in pips
            spread_pips = self._calculate_spread_pips(instrument, closeout_bid, closeout_ask)
            
            # Calculate latency
            oanda_time = datetime.fromisoformat(price_data["time"].replace('Z', '+00:00'))
            latency_ms = self._calculate_latency(oanda_time)
            
            # Create price tick
            price_tick = PriceTick(
                instrument=instrument,
                bid=closeout_bid,
                ask=closeout_ask,
                spread_pips=spread_pips,
                timestamp=oanda_time,
                tradeable=price_data.get("tradeable", True),
                latency_ms=latency_ms
            )
            
            # Update metrics
            self.metrics.update_latency(latency_ms)
            self.subscription_manager.update_price_stats(instrument)
            
            # Add to price history
            self.price_history[instrument].append(price_tick)
            
            # Call callbacks
            await self._distribute_price_update(price_tick)
            
        except Exception as e:
            logger.error(f"Error processing price update: {e}")
            logger.debug(f"Price data: {price_data}")
            
    async def _process_heartbeat(self, heartbeat_data: Dict):
        """Process heartbeat message"""
        self.heartbeat_monitor.update_heartbeat()
        self.metrics.heartbeats_received += 1
        logger.debug("Received heartbeat")
        
    async def _distribute_price_update(self, price_tick: PriceTick):
        """Distribute price update to callbacks"""
        # Call general price callbacks
        for callback in self.price_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(price_tick)
                else:
                    callback(price_tick)
            except Exception as e:
                logger.error(f"Error in price callback: {e}")
                
        # Call instrument-specific callbacks
        instrument_callbacks = self.subscription_manager.subscription_callbacks.get(price_tick.instrument, [])
        for callback in instrument_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(price_tick)
                else:
                    callback(price_tick)
            except Exception as e:
                logger.error(f"Error in instrument callback: {e}")
                
    def _calculate_spread_pips(self, instrument: str, bid: Decimal, ask: Decimal) -> Decimal:
        """Calculate spread in pips for instrument"""
        spread = ask - bid
        
        # Determine pip value based on currency pair
        if "JPY" in instrument:
            pip_value = Decimal("0.01")  # 2 decimal places for JPY pairs
        else:
            pip_value = Decimal("0.0001")  # 4 decimal places for most pairs
            
        return spread / pip_value
        
    def _calculate_latency(self, oanda_timestamp: datetime) -> float:
        """Calculate latency from OANDA timestamp to now"""
        now = datetime.now(UTC)
        if oanda_timestamp.tzinfo is None:
            oanda_timestamp = oanda_timestamp.replace(tzinfo=timezone.utc)
            
        latency = (now - oanda_timestamp).total_seconds() * 1000  # Convert to ms
        return max(0, latency)  # Ensure non-negative
        
    async def _update_subscription(self) -> bool:
        """Update subscription by reconnecting with new instruments"""
        if self.state != StreamState.STREAMING:
            return False
            
        try:
            # Close current connection
            if self.websocket:
                await self.websocket.close()
                
            # Re-establish with updated subscriptions
            await self._establish_connection()
            return True
            
        except Exception as e:
            logger.error(f"Error updating subscription: {e}")
            return False
            
    async def _handle_disconnection(self):
        """Handle connection disconnection with exponential backoff"""
        if not self.is_running:
            return
            
        self.state = StreamState.RECONNECTING
        self.current_reconnect_attempt += 1
        self.metrics.reconnection_attempts += 1
        
        if self.current_reconnect_attempt > self.max_reconnect_attempts:
            logger.error(f"Max reconnection attempts ({self.max_reconnect_attempts}) exceeded")
            self.state = StreamState.FAILED
            return
            
        # Exponential backoff
        delay = min(self.reconnect_delay * (2 ** (self.current_reconnect_attempt - 1)), 
                   self.max_reconnect_delay)
        
        logger.info(f"Reconnection attempt {self.current_reconnect_attempt}/{self.max_reconnect_attempts} "
                   f"in {delay:.1f} seconds")
        
        await asyncio.sleep(delay)
        
    async def _heartbeat_monitor_loop(self):
        """Monitor heartbeat health"""
        while self.is_running:
            try:
                if not self.heartbeat_monitor.check_health():
                    logger.warning("Heartbeat timeout detected, triggering reconnection")
                    if self.websocket:
                        await self.websocket.close()
                        
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in heartbeat monitor: {e}")
                await asyncio.sleep(5)
                
    def get_metrics(self) -> Dict:
        """Get streaming metrics"""
        uptime = 0
        if self.metrics.connection_start_time:
            uptime = (datetime.now(UTC) - self.metrics.connection_start_time).total_seconds()
            
        return {
            'state': self.state.value,
            'subscriptions': {
                'active': len(self.subscription_manager.active_subscriptions),
                'pending': len(self.subscription_manager.pending_subscriptions),
                'instruments': list(self.subscription_manager.active_subscriptions)
            },
            'metrics': {
                'messages_received': self.metrics.messages_received,
                'heartbeats_received': self.metrics.heartbeats_received,
                'errors': self.metrics.errors,
                'reconnection_attempts': self.metrics.reconnection_attempts,
                'uptime_seconds': uptime,
                'average_latency_ms': self.metrics.average_latency,
                'last_message': self.metrics.last_message_time.isoformat() if self.metrics.last_message_time else None
            },
            'subscription_stats': self.subscription_manager.subscription_stats
        }
        
    def get_price_history(self, instrument: str, limit: int = 10) -> List[Dict]:
        """Get recent price history for instrument"""
        history = list(self.price_history.get(instrument, []))
        return [tick.to_dict() for tick in history[-limit:]]

class RateLimiter:
    """Simple rate limiter for API calls"""
    
    def __init__(self, requests_per_second: int = 5):
        self.requests_per_second = requests_per_second
        self.request_times = deque()
        
    async def can_proceed(self) -> bool:
        """Check if we can make another request"""
        now = datetime.now(UTC)
        
        # Remove old requests outside the time window
        cutoff_time = now - timedelta(seconds=1)
        while self.request_times and self.request_times[0] < cutoff_time:
            self.request_times.popleft()
            
        # Check if we can make another request
        if len(self.request_times) < self.requests_per_second:
            self.request_times.append(now)
            return True
            
        return False