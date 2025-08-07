"""
Kafka Producer Manager for Inter-Agent Communication

Provides high-performance, reliable message production with:
- At-least-once delivery guarantees
- Connection pooling and resource management  
- Idempotency and message deduplication
- Performance monitoring and metrics
- Correlation ID propagation for distributed tracing
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from uuid import uuid4

from kafka import KafkaProducer
from kafka.errors import KafkaError, KafkaTimeoutError
import structlog
from prometheus_client import Counter, Histogram, Gauge

from .event_schemas import BaseEvent, EventType, get_topic_for_event, get_dlq_topic_for_event


logger = structlog.get_logger(__name__)

# Prometheus metrics
MESSAGES_SENT = Counter(
    'kafka_messages_sent_total',
    'Total number of messages sent to Kafka',
    ['topic', 'event_type', 'status']
)

MESSAGE_SEND_DURATION = Histogram(
    'kafka_message_send_duration_seconds',
    'Time spent sending messages to Kafka',
    ['topic', 'event_type']
)

PRODUCER_CONNECTIONS = Gauge(
    'kafka_producer_connections_active',
    'Number of active producer connections'
)

MESSAGE_SIZE_BYTES = Histogram(
    'kafka_message_size_bytes',
    'Size of messages sent to Kafka',
    ['topic', 'event_type']
)


class KafkaProducerManager:
    """
    High-performance Kafka producer with financial-grade reliability.
    
    Features:
    - At-least-once delivery with acks=all
    - Automatic retries with exponential backoff
    - Idempotency to prevent duplicate messages
    - Connection pooling for optimal performance
    - Dead letter queue routing for failed messages
    - Comprehensive monitoring and metrics
    """
    
    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        client_id: str = "trading-system-producer",
        max_retries: int = 3,
        retry_backoff_ms: int = 1000,
        request_timeout_ms: int = 30000,
        batch_size: int = 16384,
        linger_ms: int = 5,  # Small linger for low latency
        enable_monitoring: bool = True
    ):
        self.bootstrap_servers = bootstrap_servers
        self.client_id = client_id
        self.max_retries = max_retries
        self.retry_backoff_ms = retry_backoff_ms
        self.request_timeout_ms = request_timeout_ms
        self.batch_size = batch_size
        self.linger_ms = linger_ms
        self.enable_monitoring = enable_monitoring
        
        self._producer: Optional[KafkaProducer] = None
        self._is_connected = False
        self._connection_lock = asyncio.Lock()
        self._sent_messages: Dict[str, datetime] = {}  # For deduplication
        
        # Performance tracking
        self._start_time = time.time()
        self._total_messages_sent = 0
        self._total_bytes_sent = 0
        
        logger.info(
            "KafkaProducerManager initialized",
            bootstrap_servers=bootstrap_servers,
            client_id=client_id,
            max_retries=max_retries
        )
    
    async def connect(self) -> None:
        """
        Establish connection to Kafka cluster.
        
        Raises:
            KafkaError: If connection fails after retries
        """
        async with self._connection_lock:
            if self._is_connected and self._producer:
                return
            
            try:
                logger.info("Connecting to Kafka cluster", servers=self.bootstrap_servers)
                
                # Financial-grade producer configuration
                producer_config = {
                    'bootstrap_servers': self.bootstrap_servers,
                    'client_id': self.client_id,
                    'key_serializer': lambda k: str(k).encode('utf-8') if k else None,
                    'value_serializer': lambda v: json.dumps(v, default=str).encode('utf-8'),
                    
                    # Reliability settings for at-least-once delivery
                    'acks': 'all',  # Wait for all replicas
                    'retries': self.max_retries,
                    'retry_backoff_ms': self.retry_backoff_ms,
                    'request_timeout_ms': self.request_timeout_ms,
                    'delivery_timeout_ms': self.request_timeout_ms * 2,
                    
                    # Idempotency for exactly-once semantics
                    'enable_idempotence': True,
                    'max_in_flight_requests_per_connection': 5,
                    
                    # Performance optimization
                    'batch_size': self.batch_size,
                    'linger_ms': self.linger_ms,
                    'compression_type': 'snappy',
                    'buffer_memory': 33554432,  # 32MB buffer
                    
                    # Monitoring and debugging
                    'api_version': (0, 10, 1),
                    'security_protocol': 'PLAINTEXT'
                }
                
                self._producer = KafkaProducer(**producer_config)
                self._is_connected = True
                
                if self.enable_monitoring:
                    PRODUCER_CONNECTIONS.inc()
                
                logger.info(
                    "Successfully connected to Kafka",
                    bootstrap_servers=self.bootstrap_servers,
                    client_id=self.client_id
                )
                
            except Exception as e:
                logger.error(
                    "Failed to connect to Kafka",
                    error=str(e),
                    bootstrap_servers=self.bootstrap_servers
                )
                raise KafkaError(f"Failed to connect to Kafka: {str(e)}")
    
    async def disconnect(self) -> None:
        """Gracefully disconnect from Kafka cluster"""
        async with self._connection_lock:
            if self._producer:
                try:
                    # Flush any pending messages
                    self._producer.flush(timeout=10)
                    self._producer.close(timeout=10)
                    
                    if self.enable_monitoring:
                        PRODUCER_CONNECTIONS.dec()
                    
                    logger.info(
                        "Disconnected from Kafka",
                        total_messages=self._total_messages_sent,
                        total_bytes=self._total_bytes_sent,
                        uptime_seconds=int(time.time() - self._start_time)
                    )
                    
                except Exception as e:
                    logger.warning("Error during Kafka disconnect", error=str(e))
                
                finally:
                    self._producer = None
                    self._is_connected = False
    
    async def send_event(
        self,
        event: BaseEvent,
        topic: Optional[str] = None,
        key: Optional[str] = None,
        headers: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send an event to Kafka with delivery guarantees.
        
        Args:
            event: The event to send
            topic: Override default topic routing
            key: Message key for partitioning (defaults to correlation_id)
            headers: Additional message headers
            
        Returns:
            bool: True if message was sent successfully
            
        Raises:
            KafkaError: If message fails to send after retries
        """
        if not self._is_connected:
            await self.connect()
        
        start_time = time.time()
        
        # Determine topic
        if not topic:
            topic = get_topic_for_event(event.event_type)
        
        # Use correlation_id as default key for consistent partitioning
        if not key:
            key = event.correlation_id
        
        # Check for duplicate messages
        dedup_key = f"{event.event_id}-{topic}"
        if self._is_duplicate_message(dedup_key):
            logger.warning(
                "Duplicate message detected, skipping",
                event_id=event.event_id,
                correlation_id=event.correlation_id,
                topic=topic
            )
            return True
        
        # Prepare message
        message_data = event.dict()
        message_size = len(json.dumps(message_data, default=str).encode('utf-8'))
        
        # Prepare headers
        message_headers = {
            'correlation_id': event.correlation_id.encode('utf-8'),
            'event_type': event.event_type.value.encode('utf-8'),
            'source_agent': event.source_agent.encode('utf-8'),
            'timestamp': event.timestamp.isoformat().encode('utf-8'),
            'priority': event.priority.value.encode('utf-8')
        }
        if headers:
            for k, v in headers.items():
                message_headers[k] = str(v).encode('utf-8')
        
        try:
            logger.debug(
                "Sending message to Kafka",
                event_id=event.event_id,
                correlation_id=event.correlation_id,
                topic=topic,
                event_type=event.event_type.value,
                message_size=message_size
            )
            
            # Send message with future for async handling
            future = self._producer.send(
                topic=topic,
                value=message_data,
                key=key,
                headers=list(message_headers.items())
            )
            
            # Wait for acknowledgment (blocking call)
            record_metadata = future.get(timeout=self.request_timeout_ms / 1000)
            
            # Record successful send
            self._record_successful_send(dedup_key)
            
            send_duration = time.time() - start_time
            self._total_messages_sent += 1
            self._total_bytes_sent += message_size
            
            # Update metrics
            if self.enable_monitoring:
                MESSAGES_SENT.labels(
                    topic=topic,
                    event_type=event.event_type.value,
                    status='success'
                ).inc()
                
                MESSAGE_SEND_DURATION.labels(
                    topic=topic,
                    event_type=event.event_type.value
                ).observe(send_duration)
                
                MESSAGE_SIZE_BYTES.labels(
                    topic=topic,
                    event_type=event.event_type.value
                ).observe(message_size)
            
            logger.info(
                "Message sent successfully",
                event_id=event.event_id,
                correlation_id=event.correlation_id,
                topic=topic,
                partition=record_metadata.partition,
                offset=record_metadata.offset,
                send_duration_ms=int(send_duration * 1000),
                message_size=message_size
            )
            
            return True
            
        except KafkaTimeoutError as e:
            logger.error(
                "Kafka timeout sending message",
                event_id=event.event_id,
                correlation_id=event.correlation_id,
                topic=topic,
                error=str(e),
                timeout_ms=self.request_timeout_ms
            )
            
            # Send to dead letter queue
            await self._send_to_dlq(event, topic, f"Timeout: {str(e)}")
            
            if self.enable_monitoring:
                MESSAGES_SENT.labels(
                    topic=topic,
                    event_type=event.event_type.value,
                    status='timeout'
                ).inc()
            
            raise KafkaError(f"Timeout sending message: {str(e)}")
            
        except Exception as e:
            logger.error(
                "Error sending message to Kafka",
                event_id=event.event_id,
                correlation_id=event.correlation_id,
                topic=topic,
                error=str(e),
                error_type=type(e).__name__
            )
            
            # Send to dead letter queue
            await self._send_to_dlq(event, topic, str(e))
            
            if self.enable_monitoring:
                MESSAGES_SENT.labels(
                    topic=topic,
                    event_type=event.event_type.value,
                    status='error'
                ).inc()
            
            raise KafkaError(f"Failed to send message: {str(e)}")
    
    async def send_batch(
        self,
        events: List[BaseEvent],
        topic: Optional[str] = None
    ) -> Dict[str, bool]:
        """
        Send multiple events in batch for improved performance.
        
        Args:
            events: List of events to send
            topic: Override topic routing for all events
            
        Returns:
            Dict mapping event_id to success status
        """
        results = {}
        
        for event in events:
            try:
                success = await self.send_event(event, topic=topic)
                results[event.event_id] = success
            except Exception as e:
                logger.error(
                    "Batch send failed for event",
                    event_id=event.event_id,
                    error=str(e)
                )
                results[event.event_id] = False
        
        return results
    
    def _is_duplicate_message(self, dedup_key: str) -> bool:
        """Check if message is a duplicate based on deduplication key"""
        if dedup_key in self._sent_messages:
            sent_time = self._sent_messages[dedup_key]
            # Consider duplicates within 24 hours
            if (datetime.now(timezone.utc) - sent_time).total_seconds() < 86400:
                return True
            else:
                # Clean up old entries
                del self._sent_messages[dedup_key]
        return False
    
    def _record_successful_send(self, dedup_key: str) -> None:
        """Record successful message send for deduplication"""
        self._sent_messages[dedup_key] = datetime.now(timezone.utc)
        
        # Periodic cleanup of old entries (keep last 1000)
        if len(self._sent_messages) > 1000:
            # Remove oldest entries
            sorted_keys = sorted(
                self._sent_messages.items(),
                key=lambda x: x[1]
            )[:100]  # Remove oldest 100
            
            for key, _ in sorted_keys:
                del self._sent_messages[key]
    
    async def _send_to_dlq(
        self,
        event: BaseEvent,
        original_topic: str,
        error_reason: str
    ) -> None:
        """Send failed message to dead letter queue"""
        try:
            dlq_topic = get_dlq_topic_for_event(event.event_type)
            
            # Add failure metadata
            event.retry_count += 1
            failed_event_data = event.dict()
            failed_event_data['dlq_metadata'] = {
                'original_topic': original_topic,
                'failure_reason': error_reason,
                'failed_at': datetime.now(timezone.utc).isoformat(),
                'retry_count': event.retry_count
            }
            
            # Send to DLQ (without retry to avoid infinite loops)
            dlq_future = self._producer.send(
                topic=dlq_topic,
                value=failed_event_data,
                key=event.correlation_id
            )
            
            dlq_future.get(timeout=5)  # Short timeout for DLQ
            
            logger.warning(
                "Message sent to dead letter queue",
                event_id=event.event_id,
                correlation_id=event.correlation_id,
                original_topic=original_topic,
                dlq_topic=dlq_topic,
                error_reason=error_reason
            )
            
        except Exception as dlq_error:
            logger.critical(
                "Failed to send message to dead letter queue",
                event_id=event.event_id,
                correlation_id=event.correlation_id,
                original_topic=original_topic,
                dlq_error=str(dlq_error),
                original_error=error_reason
            )
    
    async def flush(self, timeout: float = 10.0) -> None:
        """Flush any pending messages"""
        if self._producer:
            try:
                self._producer.flush(timeout=timeout)
                logger.debug("Kafka producer flushed successfully")
            except Exception as e:
                logger.error("Error flushing Kafka producer", error=str(e))
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get producer performance metrics"""
        uptime = time.time() - self._start_time
        return {
            'is_connected': self._is_connected,
            'total_messages_sent': self._total_messages_sent,
            'total_bytes_sent': self._total_bytes_sent,
            'average_message_size': (
                self._total_bytes_sent / self._total_messages_sent
                if self._total_messages_sent > 0 else 0
            ),
            'messages_per_second': (
                self._total_messages_sent / uptime
                if uptime > 0 else 0
            ),
            'uptime_seconds': uptime,
            'pending_messages': len(self._sent_messages)
        }
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()