"""
Example usage of the inter-agent communication system.

This example demonstrates:
- Creating and sending trading signal events
- Setting up consumers with message handlers
- Monitoring message latency and performance
- Handling dead letter queue scenarios
"""

import asyncio
import logging
from datetime import datetime, timezone
from uuid import uuid4

from event_schemas import TradingSignalEvent, EventType
from kafka_producer import KafkaProducerManager
from kafka_consumer import KafkaConsumerManager, MessageHandler
from latency_monitor import LatencyMonitor
from dlq_handler import DLQHandler

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TradingSignalHandler(MessageHandler):
    """Example handler for trading signals"""
    
    async def handle(self, event, raw_message):
        """Process trading signal event"""
        logger.info(
            f"Received trading signal: {event.payload['symbol']} "
            f"- {event.payload['signal_type']} "
            f"(confidence: {event.payload['confidence']})"
        )
        
        # Simulate signal processing
        await asyncio.sleep(0.01)  # 10ms processing time
        
        return True  # Signal processed successfully


async def example_producer():
    """Example of producing trading signals"""
    producer = KafkaProducerManager(
        bootstrap_servers="localhost:9092",
        client_id="trading-signal-producer"
    )
    
    async with producer:
        # Send trading signals
        for i in range(10):
            signal = TradingSignalEvent(
                correlation_id=str(uuid4()),
                source_agent="market-analysis",
                target_agent="risk-management",
                payload={
                    "symbol": "EURUSD",
                    "signal_type": "BUY" if i % 2 == 0 else "SELL", 
                    "confidence": 0.8 + (i * 0.02),
                    "wyckoff_phase": "Accumulation",
                    "volume_confirmation": True,
                    "price_action_strength": 0.9,
                    "market_structure": "Bullish",
                    "volatility_level": "Medium",
                    "analysis_duration_ms": 45,
                    "data_points_analyzed": 1500
                }
            )
            
            success = await producer.send_event(signal, topic="trading-signals")
            logger.info(f"Signal {i+1} sent: {'✓' if success else '✗'}")
            
            # Small delay between messages
            await asyncio.sleep(0.1)


async def example_consumer():
    """Example of consuming trading signals"""
    
    # Setup latency monitoring
    monitor = LatencyMonitor(enable_alerts=True)
    await monitor.start()
    
    # Setup consumer
    consumer = KafkaConsumerManager(
        group_id="risk-management-group",
        topics=["trading-signals"],
        bootstrap_servers="localhost:9092",
        client_id="risk-management-consumer"
    )
    
    # Add handler for trading signals
    handler = TradingSignalHandler()
    consumer.add_handler(EventType.TRADING_SIGNAL_GENERATED, handler)
    
    # Setup custom message received callback for latency monitoring
    original_handle = handler.handle
    
    async def monitored_handle(event, raw_message):
        # Record message consumption for latency monitoring
        monitor.record_message_consumed(
            event=event,
            topic="trading-signals",
            target_agent="risk-management"
        )
        return await original_handle(event, raw_message)
    
    handler.handle = monitored_handle
    
    try:
        async with consumer:
            # Consume messages for 30 seconds
            logger.info("Starting message consumption...")
            
            # Start consuming in background
            consume_task = asyncio.create_task(consumer.start_consuming())
            
            # Wait for messages
            await asyncio.sleep(30)
            
            # Stop consuming
            await consumer.stop()
            
            # Get latency statistics
            stats = monitor.get_latency_statistics(time_window_minutes=1)
            logger.info(f"Latency statistics: {stats}")
            
    finally:
        await monitor.stop()


async def example_dlq_scenario():
    """Example of dead letter queue handling"""
    
    producer = KafkaProducerManager(bootstrap_servers="localhost:9092")
    dlq_handler = DLQHandler(producer)
    
    async with producer:
        # Simulate a failing message
        failing_event = TradingSignalEvent(
            correlation_id=str(uuid4()),
            source_agent="market-analysis", 
            target_agent="risk-management",
            payload={
                "symbol": "INVALID_SYMBOL",  # This might cause processing to fail
                "signal_type": "INVALID",
                "confidence": -1.0,  # Invalid confidence
                "wyckoff_phase": "Unknown",
                "volume_confirmation": False,
                "price_action_strength": 0.0,
                "market_structure": "Unknown",
                "volatility_level": "Unknown", 
                "analysis_duration_ms": 0,
                "data_points_analyzed": 0
            }
        )
        
        # Send to DLQ as if it failed processing
        await dlq_handler.handle_failed_message(
            event=failing_event,
            original_topic="trading-signals",
            failure_reason="Invalid signal data - validation failed"
        )
        
        logger.info("Failed message sent to DLQ")
        
        # Process DLQ messages (retry logic)
        await dlq_handler.process_dlq_messages()
        
        # Get DLQ statistics
        stats = dlq_handler.get_dlq_statistics()
        logger.info(f"DLQ statistics: {stats}")


async def main():
    """Run examples"""
    logger.info("Starting inter-agent communication examples")
    
    # Example 1: Basic producer/consumer
    logger.info("\n--- Example 1: Producer/Consumer ---")
    
    # Start producer and consumer concurrently
    producer_task = asyncio.create_task(example_producer())
    consumer_task = asyncio.create_task(example_consumer())
    
    # Wait for both to complete
    await asyncio.gather(producer_task, consumer_task)
    
    # Example 2: DLQ handling
    logger.info("\n--- Example 2: Dead Letter Queue ---")
    await example_dlq_scenario()
    
    logger.info("\nExamples completed!")


if __name__ == "__main__":
    asyncio.run(main())