"""
Kafka Event Integration

Handles Kafka event publishing and consumption for circuit breaker
agent coordination and system-wide communication.
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Callable, List
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError
import structlog

from .models import KafkaEvent, BreakerLevel, BreakerState, TriggerReason
from .config import config

logger = structlog.get_logger(__name__)


class KafkaEventManager:
    """
    Manages Kafka event publishing and consumption for circuit breaker
    coordination and system-wide event distribution.
    """
    
    def __init__(self):
        self.producer: Optional[KafkaProducer] = None
        self.consumers: Dict[str, KafkaConsumer] = {}
        self.is_connected = False
        self._consumer_tasks: Dict[str, asyncio.Task] = {}
        self._event_handlers: Dict[str, List[Callable]] = {}
        
        # Event topics
        self.topics = {
            'breaker_agent_triggered': 'breaker.agent.triggered',
            'breaker_system_emergency': 'breaker.system.emergency',
            'breaker_status_update': 'breaker.status.update',
            'agent_health': 'agent.health.update',
            'position_closure': 'execution.position.closure',
            'system_alert': 'system.alert'
        }
        
        logger.info("Kafka event manager initialized")
    
    async def connect(self) -> bool:
        """
        Connect to Kafka cluster and initialize producer/consumers.
        
        Returns:
            True if connection successful
        """
        try:
            # Initialize producer
            self.producer = KafkaProducer(
                bootstrap_servers=config.kafka_bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                retries=3,
                retry_backoff_ms=100,
                request_timeout_ms=30000,
                compression_type='gzip',
                batch_size=16384,
                linger_ms=5
            )
            
            # Test producer connectivity
            future = self.producer.send('test.connectivity', {'test': 'connection'})
            future.get(timeout=5)
            
            self.is_connected = True
            
            logger.info(
                "Kafka connection established",
                bootstrap_servers=config.kafka_bootstrap_servers
            )
            return True
            
        except Exception as e:
            logger.exception("Failed to connect to Kafka", error=str(e))
            self.is_connected = False
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from Kafka and cleanup resources"""
        try:
            # Stop all consumers
            for task_name, task in self._consumer_tasks.items():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            # Close consumers
            for consumer in self.consumers.values():
                consumer.close()
            
            # Close producer
            if self.producer:
                self.producer.close()
            
            self.is_connected = False
            self._consumer_tasks.clear()
            self.consumers.clear()
            
            logger.info("Kafka connection closed")
            
        except Exception as e:
            logger.exception("Error disconnecting from Kafka", error=str(e))
    
    def add_event_handler(self, event_type: str, handler: Callable) -> None:
        """
        Add event handler for specific event type.
        
        Args:
            event_type: Type of event to handle
            handler: Async function to handle the event
        """
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)
        
        logger.debug("Event handler added", event_type=event_type)
    
    async def publish_breaker_triggered(
        self, 
        level: BreakerLevel,
        identifier: str,
        reason: TriggerReason,
        details: Dict[str, Any],
        correlation_id: str
    ) -> bool:
        """
        Publish circuit breaker triggered event.
        
        Args:
            level: Breaker level that was triggered
            identifier: Breaker identifier (agent ID, account ID, etc.)
            reason: Trigger reason
            details: Additional details
            correlation_id: Request correlation ID
            
        Returns:
            True if published successfully
        """
        if not self.is_connected:
            logger.warning("Cannot publish event - Kafka not connected")
            return False
        
        try:
            topic = (self.topics['breaker_system_emergency'] if level == BreakerLevel.SYSTEM 
                    else self.topics['breaker_agent_triggered'])
            
            event = KafkaEvent(
                event_type='circuit_breaker_triggered',
                event_data={
                    'level': level.value,
                    'identifier': identifier,
                    'reason': reason.value,
                    'details': details,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                },
                correlation_id=correlation_id
            )
            
            future = self.producer.send(
                topic,
                key=f"{level.value}-{identifier}",
                value=event.dict()
            )
            
            # Don't block on delivery for performance
            future.add_callback(
                lambda metadata: logger.info(
                    "Breaker triggered event published",
                    topic=metadata.topic,
                    partition=metadata.partition,
                    offset=metadata.offset,
                    level=level.value,
                    identifier=identifier
                )
            ).add_errback(
                lambda exc: logger.error(
                    "Failed to publish breaker triggered event",
                    error=str(exc),
                    level=level.value,
                    identifier=identifier
                )
            )
            
            return True
            
        except Exception as e:
            logger.exception("Error publishing breaker triggered event", error=str(e))
            return False
    
    async def publish_status_update(
        self,
        breaker_status: Dict[str, Any],
        correlation_id: str
    ) -> bool:
        """
        Publish circuit breaker status update.
        
        Args:
            breaker_status: Current breaker status
            correlation_id: Request correlation ID
            
        Returns:
            True if published successfully
        """
        if not self.is_connected:
            logger.warning("Cannot publish status update - Kafka not connected")
            return False
        
        try:
            event = KafkaEvent(
                event_type='breaker_status_update',
                event_data={
                    'status': breaker_status,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                },
                correlation_id=correlation_id
            )
            
            future = self.producer.send(
                self.topics['breaker_status_update'],
                key='circuit-breaker-status',
                value=event.dict()
            )
            
            future.add_callback(
                lambda metadata: logger.debug(
                    "Status update published",
                    topic=metadata.topic,
                    offset=metadata.offset
                )
            )
            
            return True
            
        except Exception as e:
            logger.exception("Error publishing status update", error=str(e))
            return False
    
    async def publish_system_alert(
        self,
        alert_type: str,
        message: str,
        severity: str,
        details: Dict[str, Any],
        correlation_id: str
    ) -> bool:
        """
        Publish system alert event.
        
        Args:
            alert_type: Type of alert
            message: Alert message
            severity: Alert severity (info, warning, critical)
            details: Additional alert details
            correlation_id: Request correlation ID
            
        Returns:
            True if published successfully
        """
        if not self.is_connected:
            logger.warning("Cannot publish system alert - Kafka not connected")
            return False
        
        try:
            event = KafkaEvent(
                event_type='system_alert',
                event_data={
                    'alert_type': alert_type,
                    'message': message,
                    'severity': severity,
                    'details': details,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                },
                correlation_id=correlation_id
            )
            
            future = self.producer.send(
                self.topics['system_alert'],
                key=alert_type,
                value=event.dict()
            )
            
            future.add_callback(
                lambda metadata: logger.info(
                    "System alert published",
                    alert_type=alert_type,
                    severity=severity,
                    topic=metadata.topic
                )
            )
            
            return True
            
        except Exception as e:
            logger.exception("Error publishing system alert", error=str(e))
            return False
    
    async def start_consuming(self, topics: List[str]) -> bool:
        """
        Start consuming from specified topics.
        
        Args:
            topics: List of topic names to consume from
            
        Returns:
            True if consumers started successfully
        """
        if not self.is_connected:
            logger.error("Cannot start consuming - Kafka not connected")
            return False
        
        try:
            for topic in topics:
                if topic in self._consumer_tasks:
                    logger.warning("Consumer already running for topic", topic=topic)
                    continue
                
                consumer = KafkaConsumer(
                    topic,
                    **config.kafka_config,
                    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                    key_deserializer=lambda k: k.decode('utf-8') if k else None
                )
                
                self.consumers[topic] = consumer
                
                # Start consumer task
                self._consumer_tasks[topic] = asyncio.create_task(
                    self._consume_messages(topic, consumer)
                )
                
                logger.info("Started consuming from topic", topic=topic)
            
            return True
            
        except Exception as e:
            logger.exception("Error starting consumers", error=str(e))
            return False
    
    async def _consume_messages(self, topic: str, consumer: KafkaConsumer) -> None:
        """
        Consume messages from a Kafka topic.
        
        Args:
            topic: Topic name
            consumer: Kafka consumer instance
        """
        try:
            logger.info("Message consumption started", topic=topic)
            
            while True:
                try:
                    # Poll for messages with timeout
                    message_batch = consumer.poll(timeout_ms=1000)
                    
                    for topic_partition, messages in message_batch.items():
                        for message in messages:
                            await self._process_message(topic, message)
                    
                    # Commit offsets
                    consumer.commit_async()
                    
                except Exception as e:
                    logger.exception(
                        "Error processing message batch",
                        topic=topic,
                        error=str(e)
                    )
                    await asyncio.sleep(1)
                    
        except asyncio.CancelledError:
            logger.info("Message consumption cancelled", topic=topic)
        except Exception as e:
            logger.exception("Consumer task failed", topic=topic, error=str(e))
    
    async def _process_message(self, topic: str, message) -> None:
        """
        Process a single Kafka message.
        
        Args:
            topic: Topic the message came from
            message: Kafka message object
        """
        try:
            start_time = time.time()
            
            # Parse message
            event_data = message.value
            event_type = event_data.get('event_type', 'unknown')
            correlation_id = event_data.get('correlation_id', 'unknown')
            
            logger.debug(
                "Processing Kafka message",
                topic=topic,
                event_type=event_type,
                correlation_id=correlation_id,
                offset=message.offset
            )
            
            # Call registered handlers
            handlers = self._event_handlers.get(event_type, [])
            
            if handlers:
                # Execute handlers concurrently
                handler_tasks = [
                    asyncio.create_task(handler(event_data))
                    for handler in handlers
                ]
                
                results = await asyncio.gather(*handler_tasks, return_exceptions=True)
                
                # Log any handler failures
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.exception(
                            "Event handler failed",
                            event_type=event_type,
                            handler_index=i,
                            error=str(result)
                        )
            else:
                logger.debug(
                    "No handlers registered for event type",
                    event_type=event_type,
                    topic=topic
                )
            
            processing_time = int((time.time() - start_time) * 1000)
            
            if processing_time > 100:  # Log slow processing
                logger.warning(
                    "Slow message processing",
                    processing_time_ms=processing_time,
                    event_type=event_type,
                    topic=topic
                )
                
        except Exception as e:
            logger.exception(
                "Error processing Kafka message",
                topic=topic,
                error=str(e),
                offset=message.offset if hasattr(message, 'offset') else None
            )
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get Kafka connection status information"""
        return {
            'connected': self.is_connected,
            'producer_active': self.producer is not None,
            'active_consumers': list(self.consumers.keys()),
            'consumer_tasks': list(self._consumer_tasks.keys()),
            'event_handler_types': list(self._event_handlers.keys()),
            'bootstrap_servers': config.kafka_bootstrap_servers
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform Kafka health check"""
        try:
            if not self.is_connected or not self.producer:
                return {'status': 'unhealthy', 'error': 'Not connected'}
            
            # Test producer with a health check message
            start_time = time.time()
            future = self.producer.send('health.check', {'timestamp': time.time()})
            future.get(timeout=5)
            response_time = int((time.time() - start_time) * 1000)
            
            return {
                'status': 'healthy',
                'response_time_ms': response_time,
                'active_consumers': len(self.consumers),
                'event_handlers': len(self._event_handlers)
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy', 
                'error': str(e),
                'response_time_ms': 5000
            }