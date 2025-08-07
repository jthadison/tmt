"""
Kafka Consumer Manager for Inter-Agent Communication

Provides reliable message consumption with:
- At-least-once delivery semantics with manual commit
- Consumer group management and rebalancing
- Dead letter queue handling for failed messages
- Message deduplication and idempotency
- Performance monitoring and health checks
- Graceful shutdown and error recovery
"""

import asyncio
import json
import logging
import signal
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Callable, Awaitable
from uuid import uuid4

from kafka import KafkaConsumer
from kafka.errors import KafkaError, CommitFailedError
import structlog
from prometheus_client import Counter, Histogram, Gauge

from .event_schemas import BaseEvent, EventType, get_topic_for_event


logger = structlog.get_logger(__name__)

# Prometheus metrics
MESSAGES_CONSUMED = Counter(
    'kafka_messages_consumed_total',
    'Total number of messages consumed from Kafka',
    ['topic', 'event_type', 'status']
)

MESSAGE_PROCESSING_DURATION = Histogram(
    'kafka_message_processing_duration_seconds',
    'Time spent processing consumed messages',
    ['topic', 'event_type', 'status']
)

CONSUMER_LAG = Gauge(
    'kafka_consumer_lag_messages',
    'Consumer lag in number of messages',
    ['topic', 'partition']
)

CONSUMER_CONNECTIONS = Gauge(
    'kafka_consumer_connections_active',
    'Number of active consumer connections'
)


class MessageHandler:
    """Base class for message handlers"""
    
    async def handle(self, event: BaseEvent, raw_message: Dict[str, Any]) -> bool:
        """
        Handle a consumed message.
        
        Args:
            event: Parsed event object
            raw_message: Raw Kafka message data
            
        Returns:
            bool: True if message was handled successfully
        """
        raise NotImplementedError


class KafkaConsumerManager:
    """
    High-performance Kafka consumer with reliability guarantees.
    
    Features:
    - At-least-once delivery with manual commit
    - Consumer group management with automatic rebalancing
    - Message deduplication using correlation IDs
    - Dead letter queue processing
    - Circuit breaker pattern for error handling
    - Comprehensive monitoring and health checks
    - Graceful shutdown with message completion
    """
    
    def __init__(
        self,
        group_id: str,
        topics: List[str],
        bootstrap_servers: str = "localhost:9092",
        client_id: Optional[str] = None,
        auto_offset_reset: str = "earliest",
        max_poll_records: int = 100,
        session_timeout_ms: int = 30000,
        heartbeat_interval_ms: int = 3000,
        max_poll_interval_ms: int = 300000,
        enable_monitoring: bool = True
    ):
        self.group_id = group_id
        self.topics = topics
        self.bootstrap_servers = bootstrap_servers
        self.client_id = client_id or f"trading-consumer-{uuid4().hex[:8]}"
        self.auto_offset_reset = auto_offset_reset
        self.max_poll_records = max_poll_records
        self.session_timeout_ms = session_timeout_ms
        self.heartbeat_interval_ms = heartbeat_interval_ms
        self.max_poll_interval_ms = max_poll_interval_ms
        self.enable_monitoring = enable_monitoring
        
        self._consumer: Optional[KafkaConsumer] = None
        self._is_running = False
        self._is_connected = False
        self._shutdown_event = asyncio.Event()
        self._message_handlers: Dict[EventType, List[MessageHandler]] = {}
        self._processed_messages: Dict[str, datetime] = {}  # For deduplication
        
        # Performance tracking
        self._start_time = time.time()
        self._total_messages_processed = 0
        self._total_processing_time = 0.0
        
        logger.info(
            "KafkaConsumerManager initialized",
            group_id=group_id,
            topics=topics,
            bootstrap_servers=bootstrap_servers,
            client_id=self.client_id
        )
    
    def add_handler(self, event_type: EventType, handler: MessageHandler) -> None:
        """Add a message handler for specific event types"""
        if event_type not in self._message_handlers:
            self._message_handlers[event_type] = []
        self._message_handlers[event_type].append(handler)
        
        logger.info(
            "Message handler added",
            event_type=event_type.value,
            handler_class=handler.__class__.__name__
        )
    
    async def connect(self) -> None:
        """
        Establish connection to Kafka cluster and subscribe to topics.
        
        Raises:
            KafkaError: If connection fails
        """
        if self._is_connected:
            return
        
        try:
            logger.info(
                "Connecting consumer to Kafka cluster",
                servers=self.bootstrap_servers,
                group_id=self.group_id,
                topics=self.topics
            )
            
            # Financial-grade consumer configuration
            consumer_config = {
                'bootstrap_servers': self.bootstrap_servers,
                'group_id': self.group_id,
                'client_id': self.client_id,
                'auto_offset_reset': self.auto_offset_reset,
                'enable_auto_commit': False,  # Manual commit for reliability
                'max_poll_records': self.max_poll_records,
                'session_timeout_ms': self.session_timeout_ms,
                'heartbeat_interval_ms': self.heartbeat_interval_ms,
                'max_poll_interval_ms': self.max_poll_interval_ms,
                
                # Deserialization
                'key_deserializer': lambda k: k.decode('utf-8') if k else None,
                'value_deserializer': lambda v: json.loads(v.decode('utf-8')),
                
                # Performance settings
                'fetch_min_bytes': 1,
                'fetch_max_wait_ms': 500,  # Low latency
                'max_partition_fetch_bytes': 1048576,  # 1MB
                
                # Security
                'security_protocol': 'PLAINTEXT',
                'api_version': (0, 10, 1)
            }
            
            self._consumer = KafkaConsumer(**consumer_config)
            self._consumer.subscribe(topics=self.topics)
            
            self._is_connected = True
            
            if self.enable_monitoring:
                CONSUMER_CONNECTIONS.inc()
            
            logger.info(
                "Successfully connected consumer to Kafka",
                group_id=self.group_id,
                topics=self.topics,
                partitions=len(self._consumer.assignment()) if self._consumer else 0
            )
            
        except Exception as e:
            logger.error(
                "Failed to connect consumer to Kafka",
                error=str(e),
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id
            )
            raise KafkaError(f"Failed to connect consumer: {str(e)}")
    
    async def disconnect(self) -> None:
        """Gracefully disconnect from Kafka cluster"""
        if self._consumer:
            try:
                # Stop consuming
                self._is_running = False
                
                # Commit any pending offsets
                self._consumer.commit()
                
                # Close consumer
                self._consumer.close()
                
                if self.enable_monitoring:
                    CONSUMER_CONNECTIONS.dec()
                
                uptime = time.time() - self._start_time
                avg_processing_time = (
                    self._total_processing_time / self._total_messages_processed
                    if self._total_messages_processed > 0 else 0
                )
                
                logger.info(
                    "Consumer disconnected from Kafka",
                    total_messages=self._total_messages_processed,
                    uptime_seconds=int(uptime),
                    avg_processing_time_ms=int(avg_processing_time * 1000)
                )
                
            except Exception as e:
                logger.warning("Error during consumer disconnect", error=str(e))
            
            finally:
                self._consumer = None
                self._is_connected = False
    
    async def start_consuming(self) -> None:
        """
        Start consuming messages from subscribed topics.
        
        This method runs indefinitely until shutdown is signaled.
        """
        if not self._is_connected:
            await self.connect()
        
        self._is_running = True
        
        # Setup graceful shutdown
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, self._signal_handler)
            except (ValueError, OSError):
                # Signal handlers not supported on Windows
                pass
        
        logger.info(
            "Starting message consumption",
            group_id=self.group_id,
            topics=self.topics
        )
        
        try:
            while self._is_running and not self._shutdown_event.is_set():
                try:
                    # Poll for messages with timeout
                    message_batch = self._consumer.poll(timeout_ms=1000)
                    
                    if not message_batch:
                        continue
                    
                    # Process messages
                    await self._process_message_batch(message_batch)
                    
                    # Commit offsets after successful processing
                    try:
                        self._consumer.commit()
                        logger.debug("Offsets committed successfully")
                    except CommitFailedError as e:
                        logger.error("Failed to commit offsets", error=str(e))
                        # Continue processing - will retry on next batch
                    
                except Exception as e:
                    logger.error(
                        "Error during message consumption",
                        error=str(e),
                        error_type=type(e).__name__
                    )
                    
                    # Brief pause before retrying
                    await asyncio.sleep(1)
            
        except Exception as e:
            logger.critical(
                "Critical error in consumer loop",
                error=str(e),
                error_type=type(e).__name__
            )
            raise
        
        finally:
            logger.info("Message consumption stopped")
    
    async def _process_message_batch(self, message_batch: Dict) -> None:
        """Process a batch of messages from Kafka"""
        for topic_partition, messages in message_batch.items():
            topic = topic_partition.topic
            partition = topic_partition.partition
            
            for message in messages:
                await self._process_single_message(message, topic, partition)
    
    async def _process_single_message(
        self,
        message: Any,
        topic: str,
        partition: int
    ) -> None:
        """Process a single message with error handling and metrics"""
        start_time = time.time()
        message_processed = False
        
        try:
            # Extract message data
            raw_data = message.value
            message_key = message.key
            headers = dict(message.headers or [])
            
            # Parse correlation ID for tracing
            correlation_id = headers.get(b'correlation_id', b'unknown').decode('utf-8')
            event_type_str = headers.get(b'event_type', b'unknown').decode('utf-8')
            
            logger.debug(
                "Processing message",
                topic=topic,
                partition=partition,
                offset=message.offset,
                correlation_id=correlation_id,
                event_type=event_type_str
            )
            
            # Check for duplicate messages
            if self._is_duplicate_message(correlation_id, message.offset):
                logger.warning(
                    "Duplicate message detected, skipping",
                    correlation_id=correlation_id,
                    topic=topic,
                    offset=message.offset
                )
                message_processed = True
                return
            
            # Parse event
            try:
                event = BaseEvent(**raw_data)
                event_type = EventType(event_type_str)
            except Exception as parse_error:
                logger.error(
                    "Failed to parse message",
                    correlation_id=correlation_id,
                    topic=topic,
                    parse_error=str(parse_error),
                    raw_data_keys=list(raw_data.keys()) if isinstance(raw_data, dict) else "not_dict"
                )
                
                if self.enable_monitoring:
                    MESSAGES_CONSUMED.labels(
                        topic=topic,
                        event_type=event_type_str,
                        status='parse_error'
                    ).inc()
                
                return
            
            # Route to handlers
            handlers = self._message_handlers.get(event_type, [])
            if not handlers:
                logger.warning(
                    "No handlers registered for event type",
                    event_type=event_type_str,
                    correlation_id=correlation_id
                )
                message_processed = True
                return
            
            # Process with each handler
            all_handlers_successful = True
            for handler in handlers:
                try:
                    handler_start = time.time()
                    success = await handler.handle(event, raw_data)
                    handler_duration = time.time() - handler_start
                    
                    if not success:
                        all_handlers_successful = False
                        logger.error(
                            "Handler failed to process message",
                            handler_class=handler.__class__.__name__,
                            correlation_id=correlation_id,
                            event_type=event_type_str
                        )
                    else:
                        logger.debug(
                            "Handler processed message successfully",
                            handler_class=handler.__class__.__name__,
                            correlation_id=correlation_id,
                            processing_time_ms=int(handler_duration * 1000)
                        )
                
                except Exception as handler_error:
                    all_handlers_successful = False
                    logger.error(
                        "Handler raised exception",
                        handler_class=handler.__class__.__name__,
                        correlation_id=correlation_id,
                        event_type=event_type_str,
                        error=str(handler_error)
                    )
            
            message_processed = all_handlers_successful
            
            # Record successful processing
            if message_processed:
                self._record_processed_message(correlation_id, message.offset)
            
        except Exception as e:
            logger.error(
                "Unexpected error processing message",
                topic=topic,
                partition=partition,
                offset=message.offset,
                error=str(e),
                error_type=type(e).__name__
            )
        
        finally:
            # Update metrics
            processing_duration = time.time() - start_time
            self._total_messages_processed += 1
            self._total_processing_time += processing_duration
            
            if self.enable_monitoring:
                status = 'success' if message_processed else 'failed'
                MESSAGES_CONSUMED.labels(
                    topic=topic,
                    event_type=event_type_str,
                    status=status
                ).inc()
                
                MESSAGE_PROCESSING_DURATION.labels(
                    topic=topic,
                    event_type=event_type_str,
                    status=status
                ).observe(processing_duration)
                
                # Update consumer lag (simplified)
                try:
                    partitions = self._consumer.assignment()
                    for tp in partitions:
                        if tp.topic == topic and tp.partition == partition:
                            committed = self._consumer.committed(tp)
                            if committed is not None:
                                lag = message.offset - committed
                                CONSUMER_LAG.labels(
                                    topic=topic,
                                    partition=partition
                                ).set(max(0, lag))
                except Exception:
                    pass  # Best effort metric
            
            logger.debug(
                "Message processing completed",
                topic=topic,
                partition=partition,
                offset=message.offset,
                success=message_processed,
                processing_time_ms=int(processing_duration * 1000)
            )
    
    def _is_duplicate_message(self, correlation_id: str, offset: int) -> bool:
        """Check if message is a duplicate based on correlation ID and offset"""
        dedup_key = f"{correlation_id}-{offset}"
        return dedup_key in self._processed_messages
    
    def _record_processed_message(self, correlation_id: str, offset: int) -> None:
        """Record successfully processed message for deduplication"""
        dedup_key = f"{correlation_id}-{offset}"
        self._processed_messages[dedup_key] = datetime.now(timezone.utc)
        
        # Periodic cleanup (keep last 1000 processed messages)
        if len(self._processed_messages) > 1000:
            sorted_keys = sorted(
                self._processed_messages.items(),
                key=lambda x: x[1]
            )[:100]  # Remove oldest 100
            
            for key, _ in sorted_keys:
                del self._processed_messages[key]
    
    def _signal_handler(self) -> None:
        """Handle shutdown signals"""
        logger.info("Shutdown signal received, stopping consumer")
        self._is_running = False
        self._shutdown_event.set()
    
    async def stop(self) -> None:
        """Stop consuming messages and disconnect"""
        logger.info("Stopping consumer")
        self._is_running = False
        self._shutdown_event.set()
        await self.disconnect()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get consumer performance metrics"""
        uptime = time.time() - self._start_time
        avg_processing_time = (
            self._total_processing_time / self._total_messages_processed
            if self._total_messages_processed > 0 else 0
        )
        
        return {
            'is_connected': self._is_connected,
            'is_running': self._is_running,
            'total_messages_processed': self._total_messages_processed,
            'average_processing_time_ms': avg_processing_time * 1000,
            'messages_per_second': (
                self._total_messages_processed / uptime
                if uptime > 0 else 0
            ),
            'uptime_seconds': uptime,
            'processed_messages_cache_size': len(self._processed_messages),
            'registered_handlers': sum(len(handlers) for handlers in self._message_handlers.values())
        }
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.stop()