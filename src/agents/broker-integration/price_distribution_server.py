"""
Real-Time Price Distribution Server
Story 8.5: Real-Time Price Streaming - Task 5: Build real-time data distribution
"""
import asyncio
import websockets
import json
import logging
import secrets
import hashlib
import hmac
import jwt
from typing import Dict, Set, Optional, List, Any, Callable
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import gzip
import time
from collections import defaultdict, deque
import re

from oanda_price_stream import PriceTick, OandaStreamManager
from market_session_handler import MarketSessionHandler, SessionEvent

logger = logging.getLogger(__name__)

class MessageType(Enum):
    """WebSocket message types"""
    PRICE_UPDATE = "price_update"
    BATCH_UPDATE = "batch_update"
    SUBSCRIPTION_ACK = "subscription_ack"
    MARKET_STATUS = "market_status"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"
    FREQUENCY_UPDATE = "frequency_update"
    LATENCY_STATS = "latency_stats"

class CompressionLevel(Enum):
    """Compression levels for data"""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

@dataclass
class ClientConnection:
    """Client connection information"""
    websocket: websockets.WebSocketServerProtocol
    client_id: str
    subscriptions: Set[str]
    last_activity: datetime
    compression_enabled: bool = False
    compression_level: CompressionLevel = CompressionLevel.NONE
    update_frequency: float = 1.0  # Updates per second
    last_ping: Optional[datetime] = None
    authenticated: bool = False
    auth_token: Optional[str] = None
    connection_time: datetime = None
    message_count: int = 0
    error_count: int = 0
    
    def __post_init__(self):
        if self.connection_time is None:
            self.connection_time = datetime.now(timezone.utc)
    
class ClientCircuitBreaker:
    """Circuit breaker for client connections"""
    
    def __init__(self, max_errors: int = 10, max_queue_size: int = 1000, max_message_rate: int = 100):
        self.max_errors = max_errors
        self.max_queue_size = max_queue_size
        self.max_message_rate = max_message_rate
        self.error_count = 0
        self.is_open = False
        self.last_reset = datetime.now(timezone.utc)
        self.message_timestamps = deque(maxlen=max_message_rate)
        
    def record_error(self) -> bool:
        """Record an error and check if circuit should open"""
        self.error_count += 1
        if self.error_count >= self.max_errors:
            self.is_open = True
            return True
        return False
        
    def record_message(self) -> bool:
        """Record a message and check rate limit"""
        now = datetime.now(timezone.utc)
        self.message_timestamps.append(now)
        
        # Check rate limit (messages per minute)
        one_minute_ago = now - timedelta(minutes=1)
        recent_messages = sum(1 for ts in self.message_timestamps if ts > one_minute_ago)
        return recent_messages <= self.max_message_rate
        
    def can_process(self) -> bool:
        """Check if circuit breaker allows processing"""
        if not self.is_open:
            return True
            
        # Auto-reset circuit breaker after 5 minutes
        if (datetime.now(timezone.utc) - self.last_reset).total_seconds() > 300:
            self.is_open = False
            self.error_count = 0
            self.last_reset = datetime.now(timezone.utc)
            return True
            
        return False

class SecurityManager:
    """Handles authentication and security"""
    
    def __init__(self, jwt_secret: str):
        self.jwt_secret = jwt_secret
        self.valid_api_keys = set()  # In production, load from secure storage
        self.blocked_ips = set()
        self.rate_limits: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
    def generate_secure_client_id(self) -> str:
        """Generate cryptographically secure client ID"""
        random_bytes = secrets.token_bytes(16)
        timestamp = str(int(time.time()))
        combined = random_bytes + timestamp.encode()
        return hashlib.sha256(combined).hexdigest()[:32]
        
    def validate_jwt_token(self, token: str) -> Optional[Dict]:
        """Validate JWT authentication token"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            # Check expiration
            if payload.get('exp', 0) < time.time():
                return None
            return payload
        except jwt.InvalidTokenError:
            return None
            
    def validate_api_key(self, api_key: str) -> bool:
        """Validate API key authentication"""
        return api_key in self.valid_api_keys
        
    def is_ip_blocked(self, ip: str) -> bool:
        """Check if IP is blocked"""
        return ip in self.blocked_ips
        
    def check_rate_limit(self, client_ip: str, limit_per_minute: int = 60) -> bool:
        """Check if client exceeds rate limit"""
        now = datetime.now(timezone.utc)
        client_requests = self.rate_limits[client_ip]
        
        # Remove old requests
        one_minute_ago = now - timedelta(minutes=1)
        while client_requests and client_requests[0] < one_minute_ago:
            client_requests.popleft()
            
        # Check limit
        if len(client_requests) >= limit_per_minute:
            return False
            
        client_requests.append(now)
        return True
        
    def validate_message_input(self, message: str) -> bool:
        """Validate input message for security"""
        # Check message size
        if len(message) > 10000:  # 10KB limit
            return False
            
        try:
            data = json.loads(message)
            
            # Validate required fields
            if not isinstance(data, dict):
                return False
                
            action = data.get('action')
            if not isinstance(action, str) or len(action) > 50:
                return False
                
            # Validate action types
            valid_actions = {'subscribe', 'unsubscribe', 'set_frequency', 'set_compression', 'set_filter', 'ping'}
            if action not in valid_actions:
                return False
                
            # Validate instruments list
            if 'instruments' in data:
                instruments = data['instruments']
                if not isinstance(instruments, list) or len(instruments) > 100:
                    return False
                for instrument in instruments:
                    if not isinstance(instrument, str) or not re.match(r'^[A-Z]{3}_[A-Z]{3}$', instrument):
                        return False
                        
            return True
            
        except (json.JSONDecodeError, ValueError):
            return False

class PriceMessage:
    """Price update message"""
    
    def __init__(self, message_type: MessageType, data: Dict, timestamp: Optional[datetime] = None):
        self.type = message_type
        self.data = data
        self.timestamp = timestamp or datetime.now(timezone.utc)
        
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'type': self.type.value,
            'data': self.data,
            'timestamp': self.timestamp.isoformat()
        }
        
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), default=str)
        
    def compress(self, level: CompressionLevel = CompressionLevel.MEDIUM) -> bytes:
        """Compress message data"""
        json_data = self.to_json()
        
        if level == CompressionLevel.NONE:
            return json_data.encode('utf-8')
        
        # Use gzip compression
        compress_level = {
            CompressionLevel.LOW: 1,
            CompressionLevel.MEDIUM: 6,
            CompressionLevel.HIGH: 9
        }.get(level, 6)
        
        return gzip.compress(json_data.encode('utf-8'), compresslevel=compress_level)

class UpdateFrequencyManager:
    """Manages update frequency per client"""
    
    def __init__(self):
        self.client_frequencies: Dict[str, float] = {}
        self.last_update_times: Dict[str, datetime] = {}
        self.update_counters: Dict[str, int] = defaultdict(int)
        self.frequency_violations: Dict[str, int] = defaultdict(int)
        
    def can_send_update(self, client_id: str, frequency: float) -> bool:
        """Check if client can receive update based on frequency"""
        now = datetime.now(timezone.utc)
        
        if client_id not in self.last_update_times:
            self.last_update_times[client_id] = now
            self.client_frequencies[client_id] = frequency
            return True
            
        # Calculate time since last update
        time_since_last = (now - self.last_update_times[client_id]).total_seconds()
        required_interval = 1.0 / frequency  # Seconds between updates
        
        if time_since_last >= required_interval:
            self.last_update_times[client_id] = now
            self.update_counters[client_id] += 1
            return True
            
        self.frequency_violations[client_id] += 1
        return False
        
    def get_actual_frequency(self, client_id: str, window_seconds: int = 60) -> float:
        """Get actual update frequency for client"""
        if client_id not in self.update_counters:
            return 0.0
            
        # This is a simplified calculation
        # In production, you'd track updates in a rolling window
        return self.update_counters[client_id] / window_seconds
        
    def get_metrics(self) -> Dict:
        """Get frequency management metrics"""
        return {
            'clients': len(self.client_frequencies),
            'total_updates': len(self.last_update_times),  # Number of clients that have sent updates
            'frequency_violations': sum(self.frequency_violations.values()),
            'avg_frequency': sum(self.client_frequencies.values()) / len(self.client_frequencies) if self.client_frequencies else 0
        }

class SelectiveUpdateFilter:
    """Filters updates based on significance and client preferences"""
    
    def __init__(self):
        self.price_thresholds: Dict[str, float] = {}  # Minimum price change in pips
        self.time_thresholds: Dict[str, float] = {}   # Minimum time between updates
        self.last_sent_prices: Dict[str, Dict[str, PriceTick]] = defaultdict(dict)
        
    def should_send_update(self, client_id: str, instrument: str, price_tick: PriceTick) -> bool:
        """Determine if update should be sent to client"""
        
        # Get thresholds (use defaults if not set)
        price_threshold = self.price_thresholds.get(f"{client_id}_{instrument}", 0.1)  # 0.1 pip default
        time_threshold = self.time_thresholds.get(f"{client_id}_{instrument}", 0.1)    # 0.1 second default
        
        # Check if we have previous price
        last_price = self.last_sent_prices[client_id].get(instrument)
        if not last_price:
            # First update, always send
            self.last_sent_prices[client_id][instrument] = price_tick
            return True
            
        # Check time threshold
        time_diff = (price_tick.timestamp - last_price.timestamp).total_seconds()
        if time_diff < time_threshold:
            return False
            
        # Check price change threshold
        bid_change = abs(price_tick.bid - last_price.bid)
        ask_change = abs(price_tick.ask - last_price.ask)
        
        # Convert to pips for comparison
        from decimal import Decimal
        pip_value = Decimal("0.01") if "JPY" in instrument else Decimal("0.0001")
        bid_change_pips = float(bid_change / pip_value)
        ask_change_pips = float(ask_change / pip_value)
        
        max_change_pips = max(bid_change_pips, ask_change_pips)
        
        if max_change_pips >= price_threshold:
            self.last_sent_prices[client_id][instrument] = price_tick
            return True
            
        return False
        
    def set_client_thresholds(self, client_id: str, instrument: str, 
                            price_threshold_pips: float, time_threshold_seconds: float):
        """Set filtering thresholds for client and instrument"""
        self.price_thresholds[f"{client_id}_{instrument}"] = price_threshold_pips
        self.time_thresholds[f"{client_id}_{instrument}"] = time_threshold_seconds

class PriceDistributionServer:
    """WebSocket server for distributing real-time price data"""
    
    def __init__(self, 
                 stream_manager: OandaStreamManager,
                 session_handler: Optional[MarketSessionHandler] = None,
                 host: str = "localhost",
                 port: int = 8765,
                 jwt_secret: str = None,
                 require_authentication: bool = True,
                 max_connections: int = 1000,
                 enable_health_check: bool = True):
        
        self.stream_manager = stream_manager
        self.session_handler = session_handler
        self.host = host
        self.port = port
        self.require_authentication = require_authentication
        self.max_connections = max_connections
        self.enable_health_check = enable_health_check
        
        # Security management
        self.security_manager = SecurityManager(
            jwt_secret or secrets.token_urlsafe(32)
        )
        
        # Client management
        self.clients: Dict[str, ClientConnection] = {}
        self.websocket_to_client_id: Dict[websockets.WebSocketServerProtocol, str] = {}
        self.client_circuit_breakers: Dict[str, ClientCircuitBreaker] = {}
        
        # Update management
        self.frequency_manager = UpdateFrequencyManager()
        self.update_filter = SelectiveUpdateFilter()
        
        # Server state
        self.server: Optional[websockets.WebSocketServer] = None
        self.is_running = False
        self.shutdown_event = asyncio.Event()
        
        # Message queues for batching
        self.message_queues: Dict[str, List[PriceMessage]] = defaultdict(list)
        self.batch_size = 10
        self.batch_timeout = 0.5  # seconds
        
        # Performance metrics
        self.metrics = {
            'connections': 0,
            'total_messages_sent': 0,
            'messages_compressed': 0,
            'bytes_sent': 0,
            'bytes_saved_compression': 0,
            'update_frequency_violations': 0,
            'filtered_updates': 0,
            'latency_measurements': deque(maxlen=1000),
            'authentication_failures': 0,
            'rate_limit_violations': 0,
            'circuit_breaker_trips': 0,
            'invalid_messages': 0
        }
        
        # Background tasks
        self.batch_processor_task: Optional[asyncio.Task] = None
        self.ping_task: Optional[asyncio.Task] = None
        self.metrics_task: Optional[asyncio.Task] = None
        self.health_check_task: Optional[asyncio.Task] = None
        self.cleanup_task: Optional[asyncio.Task] = None
        
        # Setup callbacks
        self._setup_callbacks()
        
        logger.info(f"Price distribution server initialized on {host}:{port}")
        
    def _setup_callbacks(self):
        """Setup callbacks for price updates and market events"""
        # Price update callback
        self.stream_manager.add_price_callback(self._on_price_update)
        
        # Market status callback
        if self.session_handler:
            self.session_handler.add_status_change_callback(self._on_market_status_change)
            
    async def start(self):
        """Start the WebSocket server"""
        if self.is_running:
            return
            
        logger.info(f"Starting price distribution server on {self.host}:{self.port}")
        
        # Start WebSocket server
        self.server = await websockets.serve(
            self._handle_client,
            self.host,
            self.port,
            ping_interval=20,
            ping_timeout=10,
            close_timeout=10
        )
        
        self.is_running = True
        
        # Start background tasks
        self.batch_processor_task = asyncio.create_task(self._batch_processor_loop())
        self.ping_task = asyncio.create_task(self._ping_loop())
        self.metrics_task = asyncio.create_task(self._metrics_loop())
        
        if self.enable_health_check:
            self.health_check_task = asyncio.create_task(self._health_check_loop())
        
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        logger.info("Price distribution server started successfully")
        
    async def stop(self):
        """Stop the WebSocket server"""
        if not self.is_running:
            return
            
        logger.info("Stopping price distribution server")
        self.is_running = False
        
        # Signal shutdown
        self.shutdown_event.set()
        
        # Cancel background tasks
        tasks_to_cancel = [
            self.batch_processor_task,
            self.ping_task, 
            self.metrics_task,
            self.health_check_task,
            self.cleanup_task
        ]
        
        for task in tasks_to_cancel:
            if task:
                task.cancel()
                
        # Wait for tasks to complete
        await asyncio.gather(*[task for task in tasks_to_cancel if task], return_exceptions=True)
            
        # Close all client connections
        if self.clients:
            await asyncio.gather(*[
                client.websocket.close() 
                for client in self.clients.values()
            ], return_exceptions=True)
            
        # Stop server
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            
        logger.info("Price distribution server stopped")
        
    async def _handle_client(self, websocket: websockets.WebSocketServerProtocol, path: str):
        """Handle new client connection"""
        client_id = f"client_{id(websocket)}_{int(time.time())}"
        
        try:
            # Create client connection
            client = ClientConnection(
                websocket=websocket,
                client_id=client_id,
                subscriptions=set(),
                last_activity=datetime.now(timezone.utc)
            )
            
            self.clients[client_id] = client
            self.websocket_to_client_id[websocket] = client_id
            self.metrics['connections'] += 1
            
            logger.info(f"Client {client_id} connected from {websocket.remote_address}")
            
            # Send welcome message
            welcome_msg = PriceMessage(
                MessageType.SUBSCRIPTION_ACK,
                {
                    'client_id': client_id,
                    'message': 'Connected to price distribution server',
                    'available_instruments': list(self.stream_manager.subscription_manager.active_subscriptions)
                }
            )
            await self._send_message_to_client(client_id, welcome_msg)
            
            # Handle client messages
            async for message in websocket:
                await self._handle_client_message(client_id, message)
                
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {client_id} disconnected")
        except Exception as e:
            logger.error(f"Error handling client {client_id}: {e}")
        finally:
            # Cleanup
            self.clients.pop(client_id, None)
            self.websocket_to_client_id.pop(websocket, None)
            self.message_queues.pop(client_id, None)
            
    async def _handle_client_message(self, client_id: str, message: str):
        """Handle message from client"""
        try:
            data = json.loads(message)
            action = data.get('action')
            
            if action == 'subscribe':
                await self._handle_subscribe(client_id, data)
            elif action == 'unsubscribe':
                await self._handle_unsubscribe(client_id, data)
            elif action == 'set_frequency':
                await self._handle_set_frequency(client_id, data)
            elif action == 'set_compression':
                await self._handle_set_compression(client_id, data)
            elif action == 'set_filter':
                await self._handle_set_filter(client_id, data)
            elif action == 'ping':
                await self._handle_ping(client_id, data)
            else:
                logger.warning(f"Unknown action from client {client_id}: {action}")
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from client {client_id}: {message}")
        except Exception as e:
            logger.error(f"Error handling message from client {client_id}: {e}")
            if client_id in self.clients:
                self.clients[client_id].error_count += 1
            if client_id in self.client_circuit_breakers:
                if self.client_circuit_breakers[client_id].record_error():
                    self.metrics['circuit_breaker_trips'] += 1
                    logger.warning(f"Circuit breaker opened for client {client_id}")
    
    async def _send_error_message(self, client_id: str, error_message: str):
        """Send error message to client"""
        error_msg = PriceMessage(
            MessageType.ERROR,
            {
                'error': error_message,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        )
        await self._send_message_to_client(client_id, error_msg)
            
    async def _handle_subscribe(self, client_id: str, data: Dict):
        """Handle subscription request"""
        instruments = data.get('instruments', [])
        
        if client_id in self.clients:
            client = self.clients[client_id]
            client.subscriptions.update(instruments)
            client.last_activity = datetime.now(timezone.utc)
            
            # Acknowledge subscription
            ack_msg = PriceMessage(
                MessageType.SUBSCRIPTION_ACK,
                {
                    'subscribed_instruments': list(client.subscriptions),
                    'message': f'Subscribed to {len(instruments)} instruments'
                }
            )
            await self._send_message_to_client(client_id, ack_msg)
            
            logger.info(f"Client {client_id} subscribed to: {instruments}")
            
    async def _handle_unsubscribe(self, client_id: str, data: Dict):
        """Handle unsubscription request"""
        instruments = data.get('instruments', [])
        
        if client_id in self.clients:
            client = self.clients[client_id]
            client.subscriptions -= set(instruments)
            client.last_activity = datetime.now(timezone.utc)
            
            # Acknowledge unsubscription
            ack_msg = PriceMessage(
                MessageType.SUBSCRIPTION_ACK,
                {
                    'subscribed_instruments': list(client.subscriptions),
                    'message': f'Unsubscribed from {len(instruments)} instruments'
                }
            )
            await self._send_message_to_client(client_id, ack_msg)
            
            logger.info(f"Client {client_id} unsubscribed from: {instruments}")
            
    async def _handle_set_frequency(self, client_id: str, data: Dict):
        """Handle frequency setting"""
        frequency = data.get('frequency', 1.0)
        
        if client_id in self.clients:
            client = self.clients[client_id]
            client.update_frequency = frequency
            client.last_activity = datetime.now(timezone.utc)
            
            # Send frequency update confirmation
            freq_msg = PriceMessage(
                MessageType.FREQUENCY_UPDATE,
                {
                    'frequency': frequency,
                    'message': f'Update frequency set to {frequency} updates/second'
                }
            )
            await self._send_message_to_client(client_id, freq_msg)
            
    async def _handle_set_compression(self, client_id: str, data: Dict):
        """Handle compression setting"""
        enabled = data.get('enabled', False)
        level = data.get('level', 'medium')
        
        if client_id in self.clients:
            client = self.clients[client_id]
            client.compression_enabled = enabled
            client.compression_level = CompressionLevel(level)
            client.last_activity = datetime.now(timezone.utc)
            
    async def _handle_set_filter(self, client_id: str, data: Dict):
        """Handle filter setting"""
        instrument = data.get('instrument')
        price_threshold = data.get('price_threshold_pips', 0.1)
        time_threshold = data.get('time_threshold_seconds', 0.1)
        
        if instrument:
            self.update_filter.set_client_thresholds(
                client_id, instrument, price_threshold, time_threshold
            )
            
    async def _handle_ping(self, client_id: str, data: Dict):
        """Handle ping from client"""
        if client_id in self.clients:
            client = self.clients[client_id]
            client.last_ping = datetime.now(timezone.utc)
            
            # Send pong response
            pong_msg = PriceMessage(
                MessageType.PONG,
                {'timestamp': client.last_ping.isoformat()}
            )
            await self._send_message_to_client(client_id, pong_msg)
            
    async def _on_price_update(self, price_tick: PriceTick):
        """Handle price update from stream manager"""
        # Distribute to subscribed clients
        for client_id, client in self.clients.items():
            if price_tick.instrument in client.subscriptions:
                # Check frequency limits
                if not self.frequency_manager.can_send_update(client_id, client.update_frequency):
                    self.metrics['update_frequency_violations'] += 1
                    continue
                    
                # Check filters
                if not self.update_filter.should_send_update(client_id, price_tick.instrument, price_tick):
                    self.metrics['filtered_updates'] += 1
                    continue
                    
                # Create price message
                price_msg = PriceMessage(
                    MessageType.PRICE_UPDATE,
                    {
                        'instrument': price_tick.instrument,
                        'bid': str(price_tick.bid),
                        'ask': str(price_tick.ask),
                        'spread_pips': str(price_tick.spread_pips),
                        'timestamp': price_tick.timestamp.isoformat(),
                        'tradeable': price_tick.tradeable,
                        'latency_ms': price_tick.latency_ms
                    }
                )
                
                # Add to message queue for batching
                self.message_queues[client_id].append(price_msg)
                
    async def _on_market_status_change(self, event: SessionEvent):
        """Handle market status change"""
        # Send market status update to all clients
        status_msg = PriceMessage(
            MessageType.MARKET_STATUS,
            {
                'instrument': event.instrument,
                'status': event.status.value,
                'message': event.message,
                'next_change': event.next_change.isoformat() if event.next_change else None
            }
        )
        
        # Send to all clients subscribed to this instrument
        for client_id, client in self.clients.items():
            if event.instrument in client.subscriptions:
                await self._send_message_to_client(client_id, status_msg)
                
    async def _send_message_to_client(self, client_id: str, message: PriceMessage):
        """Send message to specific client"""
        if client_id not in self.clients:
            return
            
        client = self.clients[client_id]
        
        try:
            # Prepare message
            if client.compression_enabled:
                data = message.compress(client.compression_level)
                self.metrics['messages_compressed'] += 1
                uncompressed_size = len(message.to_json().encode('utf-8'))
                compressed_size = len(data)
                self.metrics['bytes_saved_compression'] += uncompressed_size - compressed_size
            else:
                data = message.to_json()
                
            # Send message
            await client.websocket.send(data)
            
            # Update metrics
            self.metrics['total_messages_sent'] += 1
            self.metrics['bytes_sent'] += len(data) if isinstance(data, bytes) else len(data.encode('utf-8'))
            
        except websockets.exceptions.ConnectionClosed:
            logger.debug(f"Client {client_id} connection closed")
        except Exception as e:
            logger.error(f"Error sending message to client {client_id}: {e}")
            
    async def _batch_processor_loop(self):
        """Process message queues for batching"""
        while self.is_running:
            try:
                for client_id, messages in self.message_queues.items():
                    if len(messages) >= self.batch_size:
                        # Send batch
                        await self._send_batch_to_client(client_id, messages)
                        messages.clear()
                        
                await asyncio.sleep(self.batch_timeout)
                
                # Send remaining messages after timeout
                for client_id, messages in self.message_queues.items():
                    if messages:
                        await self._send_batch_to_client(client_id, messages)
                        messages.clear()
                        
            except Exception as e:
                logger.error(f"Error in batch processor: {e}")
                await asyncio.sleep(1)
                
    async def _send_batch_to_client(self, client_id: str, messages: List[PriceMessage]):
        """Send batch of messages to client"""
        if not messages:
            return
            
        batch_msg = PriceMessage(
            MessageType.BATCH_UPDATE,
            {
                'count': len(messages),
                'updates': [msg.data for msg in messages]
            }
        )
        
        await self._send_message_to_client(client_id, batch_msg)
        
    async def _ping_loop(self):
        """Send periodic pings to clients"""
        while self.is_running:
            try:
                for client_id, client in self.clients.items():
                    ping_msg = PriceMessage(MessageType.PING, {'timestamp': datetime.now(timezone.utc).isoformat()})
                    await self._send_message_to_client(client_id, ping_msg)
                    
                await asyncio.sleep(30)  # Ping every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in ping loop: {e}")
                await asyncio.sleep(5)
                
    async def _metrics_loop(self):
        """Update and log metrics periodically"""
        while self.is_running:
            try:
                # Update latency stats
                await self._update_latency_stats()
                
                # Log metrics every minute
                if int(time.time()) % 60 == 0:
                    logger.info(f"Price distribution metrics: {self.get_metrics()}")
                    
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in metrics loop: {e}")
                await asyncio.sleep(5)
                
    async def _update_latency_stats(self):
        """Update latency statistics"""
        for client_id, client in self.clients.items():
            if client.last_ping:
                # Calculate ping latency (simplified)
                latency = (datetime.now(timezone.utc) - client.last_ping).total_seconds() * 1000
                self.metrics['latency_measurements'].append(latency)
    
    async def _health_check_loop(self):
        """Health check and monitoring loop"""
        while self.is_running and not self.shutdown_event.is_set():
            try:
                # Check server health
                health_status = await self._check_server_health()
                
                if health_status['status'] != 'healthy':
                    logger.warning(f"Server health check failed: {health_status}")
                
                await asyncio.sleep(30)  # Health check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(5)
    
    async def _cleanup_loop(self):
        """Background cleanup tasks"""
        while self.is_running and not self.shutdown_event.is_set():
            try:
                # Clean up inactive clients
                await self._cleanup_inactive_clients()
                
                # Clean up circuit breakers
                await self._cleanup_circuit_breakers()
                
                # Clean up message queues
                await self._cleanup_message_queues()
                
                await asyncio.sleep(60)  # Cleanup every minute
                
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(10)
    
    async def _check_server_health(self) -> Dict:
        """Check server health status"""
        try:
            active_connections = len(self.clients)
            total_messages = self.metrics['total_messages_sent']
            error_rate = (self.metrics['authentication_failures'] + 
                         self.metrics['invalid_messages']) / max(total_messages, 1)
            
            # Determine health status
            if active_connections > self.max_connections * 0.9:
                status = 'degraded'
                reason = 'High connection load'
            elif error_rate > 0.1:  # 10% error rate
                status = 'degraded'
                reason = 'High error rate'
            else:
                status = 'healthy'
                reason = 'All systems normal'
            
            return {
                'status': status,
                'reason': reason,
                'active_connections': active_connections,
                'error_rate': error_rate,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'reason': f'Health check error: {e}',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    async def _cleanup_inactive_clients(self):
        """Remove inactive clients"""
        current_time = datetime.now(timezone.utc)
        inactive_threshold = timedelta(minutes=30)
        
        inactive_clients = []
        for client_id, client in self.clients.items():
            if current_time - client.last_activity > inactive_threshold:
                inactive_clients.append(client_id)
        
        for client_id in inactive_clients:
            logger.info(f"Removing inactive client {client_id}")
            client = self.clients.get(client_id)
            if client:
                try:
                    await client.websocket.close(code=4000, reason="Inactive")
                except:
                    pass
                self.clients.pop(client_id, None)
                self.client_circuit_breakers.pop(client_id, None)
                self.message_queues.pop(client_id, None)
    
    async def _cleanup_circuit_breakers(self):
        """Clean up unused circuit breakers"""
        active_client_ids = set(self.clients.keys())
        breaker_client_ids = set(self.client_circuit_breakers.keys())
        
        for client_id in breaker_client_ids - active_client_ids:
            self.client_circuit_breakers.pop(client_id, None)
    
    async def _cleanup_message_queues(self):
        """Clean up empty message queues"""
        empty_queues = [
            client_id for client_id, queue in self.message_queues.items()
            if not queue and client_id not in self.clients
        ]
        
        for client_id in empty_queues:
            self.message_queues.pop(client_id, None)
                
    def get_metrics(self) -> Dict:
        """Get server metrics"""
        latencies = list(self.metrics['latency_measurements'])
        
        return {
            'server': {
                'is_running': self.is_running,
                'connected_clients': len(self.clients),
                'total_connections': self.metrics['connections']
            },
            'messages': {
                'total_sent': self.metrics['total_messages_sent'],
                'compressed': self.metrics['messages_compressed'],
                'frequency_violations': self.metrics['update_frequency_violations'],
                'filtered_updates': self.metrics['filtered_updates']
            },
            'bandwidth': {
                'bytes_sent': self.metrics['bytes_sent'],
                'bytes_saved_compression': self.metrics['bytes_saved_compression'],
                'compression_ratio': (self.metrics['bytes_saved_compression'] / 
                                    max(self.metrics['bytes_sent'], 1)) * 100
            },
            'latency': {
                'count': len(latencies),
                'avg_ms': sum(latencies) / len(latencies) if latencies else 0,
                'min_ms': min(latencies) if latencies else 0,
                'max_ms': max(latencies) if latencies else 0
            },
            'frequency': self.frequency_manager.get_metrics(),
            'clients': {
                client_id: {
                    'subscriptions': len(client.subscriptions),
                    'compression_enabled': client.compression_enabled,
                    'update_frequency': client.update_frequency,
                    'last_activity': client.last_activity.isoformat()
                }
                for client_id, client in self.clients.items()
            }
        }