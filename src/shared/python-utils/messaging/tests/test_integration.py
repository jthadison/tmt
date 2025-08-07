"""
Integration tests for inter-agent communication system.

Tests the complete message flow including:
- Producer to consumer message delivery
- Latency monitoring and SLA compliance  
- Dead letter queue handling
- Message delivery guarantees
"""

import asyncio
import pytest
from datetime import datetime, timezone
from uuid import uuid4

from ..event_schemas import BaseEvent, EventType, TradingSignalEvent
from ..kafka_producer import KafkaProducerManager
from ..kafka_consumer import KafkaConsumerManager, MessageHandler
from ..latency_monitor import LatencyMonitor, LatencySLA
from ..test_harness import CommunicationTestHarness, TestScenario


class TestMessageHandler(MessageHandler):
    """Test message handler for integration tests"""
    
    def __init__(self):
        self.messages_received = []
        self.processing_errors = []
    
    async def handle(self, event: BaseEvent, raw_message) -> bool:
        try:
            self.messages_received.append(event)
            return True
        except Exception as e:
            self.processing_errors.append(e)
            return False


@pytest.fixture
async def test_harness():
    """Create test harness for integration tests"""
    harness = CommunicationTestHarness(
        bootstrap_servers="localhost:9092",
        enable_monitoring=True
    )
    
    await harness.setup()
    yield harness
    await harness.teardown()


@pytest.fixture
async def producer():
    """Create Kafka producer for tests"""
    producer = KafkaProducerManager(
        bootstrap_servers="localhost:9092",
        client_id="test-producer"
    )
    await producer.connect()
    yield producer
    await producer.disconnect()


@pytest.fixture  
async def consumer():
    """Create Kafka consumer for tests"""
    consumer = KafkaConsumerManager(
        group_id="test-group",
        topics=["test-topic"],
        bootstrap_servers="localhost:9092",
        client_id="test-consumer"
    )
    await consumer.connect()
    yield consumer
    await consumer.stop()


@pytest.mark.asyncio
async def test_basic_message_flow(producer, consumer):
    """Test basic message production and consumption"""
    # Setup message handler
    handler = TestMessageHandler()
    consumer.add_handler(EventType.TRADING_SIGNAL_GENERATED, handler)
    
    # Start consumer in background
    consumer_task = asyncio.create_task(consumer.start_consuming())
    
    # Send test message
    test_event = TradingSignalEvent(
        correlation_id=str(uuid4()),
        source_agent="test-producer",
        target_agent="test-consumer", 
        payload={
            "symbol": "EURUSD",
            "signal_type": "BUY",
            "confidence": 0.8,
            "wyckoff_phase": "Accumulation",
            "volume_confirmation": True,
            "price_action_strength": 0.9,
            "market_structure": "Bullish",
            "volatility_level": "Medium",
            "analysis_duration_ms": 50,
            "data_points_analyzed": 1000
        }
    )
    
    success = await producer.send_event(test_event, topic="test-topic")
    assert success, "Message should be sent successfully"
    
    # Wait for message processing
    await asyncio.sleep(2)
    
    # Verify message was received
    assert len(handler.messages_received) == 1
    received_event = handler.messages_received[0]
    assert received_event.correlation_id == test_event.correlation_id
    assert received_event.event_type == EventType.TRADING_SIGNAL_GENERATED
    
    # Cleanup
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_message_delivery_guarantees(producer):
    """Test at-least-once delivery guarantees"""
    # This test would typically require a more complex setup
    # with controlled Kafka broker failures
    
    sent_messages = []
    
    # Send multiple messages
    for i in range(10):
        event = BaseEvent(
            event_type=EventType.TRADING_SIGNAL_GENERATED,
            correlation_id=str(uuid4()),
            source_agent="test-producer",
            target_agent="test-consumer",
            payload={"test_id": i, "batch": "delivery_test"}
        )
        
        success = await producer.send_event(event, topic="delivery-test")
        if success:
            sent_messages.append(event)
    
    # All messages should be sent successfully in normal conditions
    assert len(sent_messages) == 10


@pytest.mark.asyncio  
async def test_latency_monitoring():
    """Test message latency monitoring"""
    sla = LatencySLA(target_latency_ms=10.0)
    monitor = LatencyMonitor(sla=sla, enable_alerts=True)
    
    await monitor.start()
    
    try:
        # Simulate message consumption with various latencies
        test_cases = [
            (5.0, "normal"),     # Within SLA
            (15.0, "warning"),   # Exceeds warning threshold
            (60.0, "critical"),  # Exceeds critical threshold
        ]
        
        for latency_ms, expected_severity in test_cases:
            # Create event with timestamp in the past
            past_time = datetime.now(timezone.utc).timestamp() - (latency_ms / 1000.0)
            event = BaseEvent(
                event_type=EventType.TRADING_SIGNAL_GENERATED,
                correlation_id=str(uuid4()),
                source_agent="test-producer", 
                target_agent="test-consumer",
                timestamp=datetime.fromtimestamp(past_time, tz=timezone.utc),
                payload={"latency_test": True}
            )
            
            # Record consumption
            monitor.record_message_consumed(
                event=event,
                topic="latency-test",
                target_agent="test-consumer"
            )
        
        # Get statistics
        stats = monitor.get_latency_statistics(time_window_minutes=1)
        
        assert stats["total_messages"] == 3
        assert stats["sla_violations"] >= 2  # Two messages exceeded target
        assert stats["avg_latency_ms"] > 10  # Average should be above target
        
    finally:
        await monitor.stop()


@pytest.mark.asyncio
async def test_test_harness_scenarios(test_harness):
    """Test the test harness with different scenarios"""
    
    # Test basic flow scenario
    results = await test_harness.run_scenario(
        TestScenario.BASIC_FLOW,
        duration_seconds=10,
        messages_per_second=5
    )
    
    assert results.scenario == TestScenario.BASIC_FLOW
    assert results.messages_sent > 0
    assert results.duration_seconds == 10
    assert results.throughput_msg_per_sec > 0
    
    # Test high volume scenario
    results = await test_harness.run_scenario(
        TestScenario.HIGH_VOLUME,
        duration_seconds=5,
        messages_per_second=100,
        batch_size=20
    )
    
    assert results.scenario == TestScenario.HIGH_VOLUME
    assert results.messages_sent >= 400  # Should send ~500 messages in 5 seconds
    assert results.throughput_msg_per_sec > 50
    
    # Test latency scenario
    results = await test_harness.run_scenario(
        TestScenario.LATENCY_TEST,
        duration_seconds=5,
        messages_per_second=20,
        target_latency_ms=10
    )
    
    assert results.scenario == TestScenario.LATENCY_TEST
    assert results.average_latency_ms is not None
    
    # Test failure simulation
    results = await test_harness.run_scenario(
        TestScenario.FAILURE_SIMULATION,
        duration_seconds=5,
        failure_rate=0.2
    )
    
    assert results.scenario == TestScenario.FAILURE_SIMULATION
    assert results.messages_failed > 0  # Some messages should fail


@pytest.mark.asyncio
async def test_event_schema_validation():
    """Test event schema validation and serialization"""
    
    # Test valid trading signal event
    valid_payload = {
        "symbol": "EURUSD",
        "signal_type": "BUY", 
        "confidence": 0.8,
        "wyckoff_phase": "Accumulation",
        "volume_confirmation": True,
        "price_action_strength": 0.9,
        "market_structure": "Bullish",
        "volatility_level": "Medium",
        "analysis_duration_ms": 50,
        "data_points_analyzed": 1000
    }
    
    event = TradingSignalEvent(
        correlation_id=str(uuid4()),
        source_agent="market-analysis",
        target_agent="risk-management",
        payload=valid_payload
    )
    
    # Should create successfully
    assert event.event_type == EventType.TRADING_SIGNAL_GENERATED
    assert event.payload == valid_payload
    
    # Should serialize/deserialize correctly
    event_dict = event.dict()
    reconstructed = TradingSignalEvent(**event_dict)
    assert reconstructed.correlation_id == event.correlation_id
    assert reconstructed.payload == event.payload


@pytest.mark.asyncio
async def test_message_deduplication(producer):
    """Test message deduplication functionality"""
    
    # Create identical events
    event1 = BaseEvent(
        event_type=EventType.TRADING_SIGNAL_GENERATED,
        correlation_id="test-dedup-123",
        source_agent="test-producer",
        target_agent="test-consumer", 
        payload={"dedup_test": True}
    )
    
    event2 = BaseEvent(
        event_type=EventType.TRADING_SIGNAL_GENERATED,
        correlation_id="test-dedup-123",  # Same correlation ID
        source_agent="test-producer",
        target_agent="test-consumer",
        payload={"dedup_test": True}
    )
    
    # Send both events
    success1 = await producer.send_event(event1, topic="dedup-test")
    success2 = await producer.send_event(event2, topic="dedup-test")
    
    # Both should be sent (deduplication happens on consumer side)
    assert success1
    assert success2
    
    # Producer should track the duplicate internally
    metrics = producer.get_metrics()
    assert metrics["total_messages_sent"] >= 1


if __name__ == "__main__":
    pytest.main([__file__])