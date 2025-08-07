"""
Messaging utilities for inter-agent communication via Kafka.

Provides standardized producer and consumer clients with:
- Connection pooling and resource management
- Message delivery guarantees (at-least-once)
- Idempotency handling and deduplication
- Correlation ID propagation for distributed tracing
- Dead letter queue integration
- Performance monitoring and metrics
"""

from .kafka_producer import KafkaProducerManager
from .kafka_consumer import KafkaConsumerManager
from .event_schemas import (
    BaseEvent,
    TradingSignalEvent,
    RiskParameterEvent,
    CircuitBreakerEvent,
    PersonalityVarianceEvent,
    ExecutionEvent
)

__version__ = "0.1.0"

__all__ = [
    "KafkaProducerManager",
    "KafkaConsumerManager",
    "BaseEvent",
    "TradingSignalEvent",
    "RiskParameterEvent", 
    "CircuitBreakerEvent",
    "PersonalityVarianceEvent",
    "ExecutionEvent"
]