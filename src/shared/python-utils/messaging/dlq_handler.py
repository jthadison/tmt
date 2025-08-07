"""
Dead Letter Queue Handler for Failed Message Processing

Provides comprehensive dead letter queue management with:
- Failed message collection and analysis
- Retry mechanisms with exponential backoff
- Poison message detection and isolation
- Manual recovery tools for operations teams
- Alerting and monitoring for DLQ accumulation
"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Callable
from uuid import uuid4
from enum import Enum

import structlog
from prometheus_client import Counter, Gauge, Histogram

from .event_schemas import BaseEvent, EventType, get_dlq_topic_for_event
from .kafka_producer import KafkaProducerManager
from .kafka_consumer import KafkaConsumerManager, MessageHandler


logger = structlog.get_logger(__name__)

# Prometheus metrics for DLQ monitoring
DLQ_MESSAGES_RECEIVED = Counter(
    'dlq_messages_received_total',
    'Total number of messages received in dead letter queue',
    ['original_topic', 'failure_reason']
)

DLQ_MESSAGES_PROCESSED = Counter(
    'dlq_messages_processed_total',
    'Total number of DLQ messages processed',
    ['original_topic', 'action']
)

DLQ_QUEUE_SIZE = Gauge(
    'dlq_queue_size_messages',
    'Number of messages currently in dead letter queues',
    ['dlq_topic']
)

DLQ_RETRY_DURATION = Histogram(
    'dlq_retry_duration_seconds',
    'Time spent retrying DLQ messages',
    ['original_topic', 'retry_attempt']
)


class DLQAction(str, Enum):
    """Actions that can be taken for DLQ messages"""
    RETRY = "retry"
    DISCARD = "discard"
    MANUAL_REVIEW = "manual_review"
    REPROCESS = "reprocess"


class FailureClassification(str, Enum):
    """Classification of message failures"""
    TRANSIENT = "transient"          # Network issues, temporary unavailability
    PERMANENT = "permanent"          # Schema validation, corrupt data
    POISON = "poison"               # Messages that consistently fail processing
    CONFIGURATION = "configuration" # Missing handlers, misconfiguration
    TIMEOUT = "timeout"             # Processing timeouts


class DLQMessage:
    """Represents a message in the dead letter queue"""
    
    def __init__(
        self,
        original_event: BaseEvent,
        original_topic: str,
        failure_reason: str,
        failure_classification: FailureClassification = FailureClassification.TRANSIENT,
        retry_count: int = 0,
        first_failed_at: Optional[datetime] = None,
        last_failed_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.dlq_id = str(uuid4())
        self.original_event = original_event
        self.original_topic = original_topic
        self.failure_reason = failure_reason
        self.failure_classification = failure_classification
        self.retry_count = retry_count
        self.first_failed_at = first_failed_at or datetime.now(timezone.utc)
        self.last_failed_at = last_failed_at or datetime.now(timezone.utc)
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'dlq_id': self.dlq_id,
            'original_event': self.original_event.dict(),
            'original_topic': self.original_topic,
            'failure_reason': self.failure_reason,
            'failure_classification': self.failure_classification.value,
            'retry_count': self.retry_count,
            'first_failed_at': self.first_failed_at.isoformat(),
            'last_failed_at': self.last_failed_at.isoformat(),
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DLQMessage':
        """Create from dictionary"""
        original_event = BaseEvent(**data['original_event'])
        first_failed_at = datetime.fromisoformat(data['first_failed_at'])
        last_failed_at = datetime.fromisoformat(data['last_failed_at'])
        
        return cls(
            original_event=original_event,
            original_topic=data['original_topic'],
            failure_reason=data['failure_reason'],
            failure_classification=FailureClassification(data['failure_classification']),
            retry_count=data['retry_count'],
            first_failed_at=first_failed_at,
            last_failed_at=last_failed_at,
            metadata=data.get('metadata', {})
        )


class DLQRetryPolicy:
    """Retry policy configuration for DLQ message processing"""
    
    def __init__(
        self,
        max_retries: int = 5,
        initial_delay_seconds: int = 60,
        max_delay_seconds: int = 3600,
        backoff_multiplier: float = 2.0,
        jitter: bool = True
    ):
        self.max_retries = max_retries
        self.initial_delay_seconds = initial_delay_seconds
        self.max_delay_seconds = max_delay_seconds
        self.backoff_multiplier = backoff_multiplier
        self.jitter = jitter
    
    def calculate_delay(self, retry_count: int) -> int:
        """Calculate delay for retry attempt with exponential backoff"""
        delay = min(
            self.initial_delay_seconds * (self.backoff_multiplier ** retry_count),
            self.max_delay_seconds
        )
        
        if self.jitter:
            import random
            delay = delay * (0.5 + random.random())
        
        return int(delay)
    
    def should_retry(self, dlq_message: DLQMessage) -> bool:
        """Determine if message should be retried"""
        if dlq_message.retry_count >= self.max_retries:
            return False
        
        # Don't retry poison messages
        if dlq_message.failure_classification == FailureClassification.POISON:
            return False
        
        # Don't retry permanent failures
        if dlq_message.failure_classification == FailureClassification.PERMANENT:
            return False
        
        # Check if enough time has passed since last failure
        retry_delay = self.calculate_delay(dlq_message.retry_count)
        time_since_failure = (datetime.now(timezone.utc) - dlq_message.last_failed_at).total_seconds()
        
        return time_since_failure >= retry_delay


class DLQHandler:
    """
    Comprehensive dead letter queue handler with retry mechanisms.
    
    Manages failed messages with intelligent retry policies, poison message
    detection, and operational tools for message recovery.
    """
    
    def __init__(
        self,
        producer: KafkaProducerManager,
        retry_policy: Optional[DLQRetryPolicy] = None,
        enable_monitoring: bool = True
    ):
        self.producer = producer
        self.retry_policy = retry_policy or DLQRetryPolicy()
        self.enable_monitoring = enable_monitoring
        
        self._dlq_messages: Dict[str, DLQMessage] = {}
        self._poison_messages: Dict[str, DLQMessage] = {}
        self._manual_review_queue: List[DLQMessage] = []
        
        # Failure pattern tracking
        self._failure_patterns: Dict[str, int] = {}
        self._poison_threshold = 3  # Messages that fail this many times are poison
        
        logger.info("DLQHandler initialized", retry_policy_max_retries=retry_policy.max_retries if retry_policy else 5)
    
    async def handle_failed_message(
        self,
        event: BaseEvent,
        original_topic: str,
        failure_reason: str,
        failure_classification: Optional[FailureClassification] = None
    ) -> None:
        """
        Handle a message that failed processing.
        
        Args:
            event: The failed event
            original_topic: Topic where message originally failed
            failure_reason: Description of why it failed
            failure_classification: Classification of failure type
        """
        # Classify failure if not provided
        if not failure_classification:
            failure_classification = self._classify_failure(failure_reason)
        
        # Check for existing DLQ message
        dlq_message = self._dlq_messages.get(event.event_id)
        if dlq_message:
            # Update existing message
            dlq_message.retry_count += 1
            dlq_message.last_failed_at = datetime.now(timezone.utc)
            dlq_message.failure_reason = failure_reason
            dlq_message.failure_classification = failure_classification
        else:
            # Create new DLQ message
            dlq_message = DLQMessage(
                original_event=event,
                original_topic=original_topic,
                failure_reason=failure_reason,
                failure_classification=failure_classification
            )
            self._dlq_messages[event.event_id] = dlq_message
        
        # Track failure patterns
        failure_pattern = f"{original_topic}:{type(failure_reason).__name__}"
        self._failure_patterns[failure_pattern] = self._failure_patterns.get(failure_pattern, 0) + 1
        
        # Check for poison message
        if dlq_message.retry_count >= self._poison_threshold:
            await self._handle_poison_message(dlq_message)
            return
        
        # Update metrics
        if self.enable_monitoring:
            DLQ_MESSAGES_RECEIVED.labels(
                original_topic=original_topic,
                failure_reason=failure_classification.value
            ).inc()
        
        # Send to DLQ topic
        await self._send_to_dlq_topic(dlq_message)
        
        logger.warning(
            "Message added to dead letter queue",
            event_id=event.event_id,
            correlation_id=event.correlation_id,
            original_topic=original_topic,
            failure_reason=failure_reason,
            retry_count=dlq_message.retry_count,
            classification=failure_classification.value
        )
    
    async def process_dlq_messages(self) -> None:
        """Process messages in the dead letter queue for retry"""
        logger.info("Starting DLQ message processing")
        
        retry_candidates = []
        for dlq_message in self._dlq_messages.values():
            if self.retry_policy.should_retry(dlq_message):
                retry_candidates.append(dlq_message)
        
        if not retry_candidates:
            logger.debug("No DLQ messages ready for retry")
            return
        
        logger.info(f"Processing {len(retry_candidates)} DLQ messages for retry")
        
        for dlq_message in retry_candidates:
            await self._retry_message(dlq_message)
    
    async def _retry_message(self, dlq_message: DLQMessage) -> None:
        """Retry processing a DLQ message"""
        start_time = datetime.now(timezone.utc)
        
        try:
            logger.info(
                "Retrying DLQ message",
                dlq_id=dlq_message.dlq_id,
                event_id=dlq_message.original_event.event_id,
                retry_count=dlq_message.retry_count + 1,
                original_topic=dlq_message.original_topic
            )
            
            # Update retry count
            dlq_message.retry_count += 1
            dlq_message.last_failed_at = datetime.now(timezone.utc)
            
            # Attempt to reprocess by sending back to original topic
            success = await self.producer.send_event(
                event=dlq_message.original_event,
                topic=dlq_message.original_topic
            )
            
            if success:
                # Remove from DLQ on successful retry
                del self._dlq_messages[dlq_message.original_event.event_id]
                
                if self.enable_monitoring:
                    DLQ_MESSAGES_PROCESSED.labels(
                        original_topic=dlq_message.original_topic,
                        action=DLQAction.RETRY.value
                    ).inc()
                
                logger.info(
                    "DLQ message retry successful",
                    dlq_id=dlq_message.dlq_id,
                    event_id=dlq_message.original_event.event_id,
                    retry_count=dlq_message.retry_count
                )
            else:
                logger.error(
                    "DLQ message retry failed",
                    dlq_id=dlq_message.dlq_id,
                    event_id=dlq_message.original_event.event_id,
                    retry_count=dlq_message.retry_count
                )
        
        except Exception as e:
            logger.error(
                "Error retrying DLQ message",
                dlq_id=dlq_message.dlq_id,
                error=str(e)
            )
        
        finally:
            # Update metrics
            if self.enable_monitoring:
                retry_duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                DLQ_RETRY_DURATION.labels(
                    original_topic=dlq_message.original_topic,
                    retry_attempt=dlq_message.retry_count
                ).observe(retry_duration)
    
    async def _handle_poison_message(self, dlq_message: DLQMessage) -> None:
        """Handle a poison message that repeatedly fails"""
        dlq_message.failure_classification = FailureClassification.POISON
        
        # Move to poison messages collection
        self._poison_messages[dlq_message.dlq_id] = dlq_message
        
        # Remove from active DLQ
        if dlq_message.original_event.event_id in self._dlq_messages:
            del self._dlq_messages[dlq_message.original_event.event_id]
        
        # Add to manual review queue
        self._manual_review_queue.append(dlq_message)
        
        logger.critical(
            "Poison message detected",
            dlq_id=dlq_message.dlq_id,
            event_id=dlq_message.original_event.event_id,
            retry_count=dlq_message.retry_count,
            original_topic=dlq_message.original_topic,
            failure_reason=dlq_message.failure_reason
        )
        
        if self.enable_monitoring:
            DLQ_MESSAGES_PROCESSED.labels(
                original_topic=dlq_message.original_topic,
                action="poison_detected"
            ).inc()
    
    async def _send_to_dlq_topic(self, dlq_message: DLQMessage) -> None:
        """Send message to the appropriate DLQ Kafka topic"""
        try:
            dlq_topic = get_dlq_topic_for_event(dlq_message.original_event.event_type)
            
            # Create DLQ event with metadata
            dlq_event_data = dlq_message.to_dict()
            
            # Send to DLQ topic (using producer's send method directly)
            await self.producer.send_event(
                event=BaseEvent(
                    event_type=dlq_message.original_event.event_type,
                    correlation_id=dlq_message.original_event.correlation_id,
                    source_agent="dlq-handler",
                    payload=dlq_event_data
                ),
                topic=dlq_topic
            )
            
            if self.enable_monitoring:
                DLQ_QUEUE_SIZE.labels(dlq_topic=dlq_topic).inc()
            
        except Exception as e:
            logger.error(
                "Failed to send message to DLQ topic",
                dlq_id=dlq_message.dlq_id,
                error=str(e)
            )
    
    def _classify_failure(self, failure_reason: str) -> FailureClassification:
        """Automatically classify failure based on error message"""
        failure_lower = failure_reason.lower()
        
        # Transient failures
        if any(keyword in failure_lower for keyword in [
            'timeout', 'connection', 'network', 'unavailable', 'temporary'
        ]):
            return FailureClassification.TRANSIENT
        
        # Configuration issues
        if any(keyword in failure_lower for keyword in [
            'handler', 'configuration', 'missing', 'not found'
        ]):
            return FailureClassification.CONFIGURATION
        
        # Schema/data issues
        if any(keyword in failure_lower for keyword in [
            'validation', 'schema', 'parse', 'deserialize', 'corrupt'
        ]):
            return FailureClassification.PERMANENT
        
        # Default to transient for retry
        return FailureClassification.TRANSIENT
    
    def get_dlq_statistics(self) -> Dict[str, Any]:
        """Get DLQ statistics for monitoring"""
        total_failures_by_classification = {}
        for msg in self._dlq_messages.values():
            classification = msg.failure_classification.value
            total_failures_by_classification[classification] = \
                total_failures_by_classification.get(classification, 0) + 1
        
        return {
            'active_dlq_messages': len(self._dlq_messages),
            'poison_messages': len(self._poison_messages),
            'manual_review_queue': len(self._manual_review_queue),
            'failure_patterns': dict(self._failure_patterns),
            'failures_by_classification': total_failures_by_classification,
            'oldest_message_age_hours': (
                (datetime.now(timezone.utc) - min(
                    msg.first_failed_at for msg in self._dlq_messages.values()
                )).total_seconds() / 3600
                if self._dlq_messages else 0
            )
        }
    
    async def manual_discard_message(self, event_id: str, reason: str) -> bool:
        """Manually discard a DLQ message"""
        if event_id in self._dlq_messages:
            dlq_message = self._dlq_messages[event_id]
            del self._dlq_messages[event_id]
            
            logger.info(
                "DLQ message manually discarded",
                event_id=event_id,
                reason=reason,
                original_topic=dlq_message.original_topic
            )
            
            if self.enable_monitoring:
                DLQ_MESSAGES_PROCESSED.labels(
                    original_topic=dlq_message.original_topic,
                    action=DLQAction.DISCARD.value
                ).inc()
            
            return True
        return False
    
    async def manual_reprocess_message(self, event_id: str) -> bool:
        """Manually reprocess a DLQ message"""
        if event_id in self._dlq_messages:
            dlq_message = self._dlq_messages[event_id]
            await self._retry_message(dlq_message)
            return True
        return False
    
    def get_manual_review_queue(self) -> List[Dict[str, Any]]:
        """Get messages requiring manual review"""
        return [msg.to_dict() for msg in self._manual_review_queue]