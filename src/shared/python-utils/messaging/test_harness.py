"""
Test Harness for Inter-Agent Communication

Provides comprehensive testing utilities for:
- Simulating multi-agent message flows
- Performance testing and latency validation
- Message delivery guarantee testing
- Dead letter queue behavior testing
- Chaos engineering and failure simulation
"""

import asyncio
import random
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Callable, Awaitable
from uuid import uuid4
from dataclasses import dataclass
from enum import Enum

import structlog

from .event_schemas import (
    BaseEvent, EventType, TradingSignalEvent, RiskParameterEvent,
    CircuitBreakerEvent, PersonalityVarianceEvent, ExecutionEvent, Priority
)
from .kafka_producer import KafkaProducerManager
from .kafka_consumer import KafkaConsumerManager, MessageHandler
from .latency_monitor import LatencyMonitor
from .dlq_handler import DLQHandler


logger = structlog.get_logger(__name__)


class TestScenario(Enum):
    """Pre-defined test scenarios"""
    BASIC_FLOW = "basic_flow"
    HIGH_VOLUME = "high_volume"
    LATENCY_TEST = "latency_test"
    FAILURE_SIMULATION = "failure_simulation"
    DLQ_TESTING = "dlq_testing"
    CHAOS_ENGINEERING = "chaos_engineering"


@dataclass
class TestAgent:
    """Simulated agent for testing"""
    name: str
    message_types: List[EventType]
    processing_delay_ms: int = 0
    failure_rate: float = 0.0
    
    def __post_init__(self):
        self.messages_sent = 0
        self.messages_received = 0
        self.processing_errors = 0


@dataclass
class TestResults:
    """Test execution results"""
    scenario: TestScenario
    duration_seconds: float
    messages_sent: int
    messages_received: int
    messages_failed: int
    average_latency_ms: float
    max_latency_ms: float
    throughput_msg_per_sec: float
    sla_violations: int
    dlq_messages: int
    errors: List[str]


class TestMessageHandler(MessageHandler):
    """Test message handler that simulates agent processing"""
    
    def __init__(
        self,
        agent: TestAgent,
        latency_monitor: LatencyMonitor,
        on_message_callback: Optional[Callable] = None
    ):
        self.agent = agent
        self.latency_monitor = latency_monitor
        self.on_message_callback = on_message_callback
    
    async def handle(self, event: BaseEvent, raw_message: Dict[str, Any]) -> bool:
        """Handle received message with simulated processing"""
        start_time = time.time()
        
        try:
            # Record message reception for latency monitoring
            self.latency_monitor.record_message_consumed(
                event=event,
                topic=raw_message.get('topic', 'unknown'),
                target_agent=self.agent.name
            )
            
            # Simulate processing delay
            if self.agent.processing_delay_ms > 0:
                await asyncio.sleep(self.agent.processing_delay_ms / 1000.0)
            
            # Simulate processing failures
            if random.random() < self.agent.failure_rate:
                self.agent.processing_errors += 1
                raise Exception(f"Simulated processing failure in {self.agent.name}")
            
            # Update counters
            self.agent.messages_received += 1
            
            # Call custom callback if provided
            if self.on_message_callback:
                await self.on_message_callback(event, self.agent)
            
            processing_time = (time.time() - start_time) * 1000
            
            logger.debug(
                "Test message processed successfully",
                agent=self.agent.name,
                correlation_id=event.correlation_id,
                event_type=event.event_type.value,
                processing_time_ms=round(processing_time, 2)
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Test message processing failed",
                agent=self.agent.name,
                correlation_id=event.correlation_id,
                error=str(e)
            )
            return False


class CommunicationTestHarness:
    """
    Comprehensive test harness for inter-agent communication.
    
    Provides tools for:
    - Multi-agent simulation with configurable behaviors
    - Performance testing and benchmarking
    - Latency validation and SLA testing
    - Failure scenario simulation
    - Message delivery guarantee verification
    """
    
    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        enable_monitoring: bool = True
    ):
        self.bootstrap_servers = bootstrap_servers
        self.enable_monitoring = enable_monitoring
        
        # Test components
        self.producer: Optional[KafkaProducerManager] = None
        self.consumers: Dict[str, KafkaConsumerManager] = {}
        self.latency_monitor: Optional[LatencyMonitor] = None
        self.dlq_handler: Optional[DLQHandler] = None
        
        # Test state
        self.test_agents: Dict[str, TestAgent] = {}
        self.test_running = False
        self.test_start_time: Optional[float] = None
        self.test_errors: List[str] = []
        
        logger.info("CommunicationTestHarness initialized", servers=bootstrap_servers)
    
    async def setup(self) -> None:
        """Initialize test harness components"""
        logger.info("Setting up test harness")
        
        # Initialize producer
        self.producer = KafkaProducerManager(
            bootstrap_servers=self.bootstrap_servers,
            client_id="test-harness-producer",
            enable_monitoring=self.enable_monitoring
        )
        await self.producer.connect()
        
        # Initialize latency monitor
        if self.enable_monitoring:
            self.latency_monitor = LatencyMonitor(enable_alerts=True)
            await self.latency_monitor.start()
        
        # Initialize DLQ handler
        self.dlq_handler = DLQHandler(self.producer)
        
        logger.info("Test harness setup completed")
    
    async def teardown(self) -> None:
        """Clean up test harness components"""
        logger.info("Tearing down test harness")
        
        # Stop consumers
        for consumer in self.consumers.values():
            await consumer.stop()
        self.consumers.clear()
        
        # Stop monitoring
        if self.latency_monitor:
            await self.latency_monitor.stop()
        
        # Disconnect producer
        if self.producer:
            await self.producer.disconnect()
        
        logger.info("Test harness teardown completed")
    
    def add_test_agent(
        self,
        name: str,
        message_types: List[EventType],
        processing_delay_ms: int = 0,
        failure_rate: float = 0.0
    ) -> TestAgent:
        """Add a test agent to the harness"""
        agent = TestAgent(
            name=name,
            message_types=message_types,
            processing_delay_ms=processing_delay_ms,
            failure_rate=failure_rate
        )
        
        self.test_agents[name] = agent
        
        logger.info(
            "Test agent added",
            name=name,
            message_types=[t.value for t in message_types],
            processing_delay_ms=processing_delay_ms,
            failure_rate=failure_rate
        )
        
        return agent
    
    async def start_agent_consumers(self) -> None:
        """Start consumers for all test agents"""
        for agent_name, agent in self.test_agents.items():
            # Create consumer
            consumer = KafkaConsumerManager(
                group_id=f"test-{agent_name}-group",
                topics=[f"test-{agent_name}"],
                bootstrap_servers=self.bootstrap_servers,
                client_id=f"test-{agent_name}-consumer",
                enable_monitoring=self.enable_monitoring
            )
            
            # Add handler
            handler = TestMessageHandler(
                agent=agent,
                latency_monitor=self.latency_monitor,
                on_message_callback=self._on_test_message_received
            )
            
            # Register handler for all agent message types
            for event_type in agent.message_types:
                consumer.add_handler(event_type, handler)
            
            # Connect and store
            await consumer.connect()
            self.consumers[agent_name] = consumer
            
            # Start consuming in background
            asyncio.create_task(consumer.start_consuming())
        
        logger.info(f"Started consumers for {len(self.test_agents)} test agents")
    
    async def run_scenario(
        self,
        scenario: TestScenario,
        duration_seconds: int = 60,
        **scenario_params
    ) -> TestResults:
        """Run a predefined test scenario"""
        logger.info(f"Running test scenario: {scenario.value}", duration=duration_seconds)
        
        self.test_running = True
        self.test_start_time = time.time()
        self.test_errors.clear()
        
        try:
            if scenario == TestScenario.BASIC_FLOW:
                await self._run_basic_flow_test(duration_seconds, **scenario_params)
            elif scenario == TestScenario.HIGH_VOLUME:
                await self._run_high_volume_test(duration_seconds, **scenario_params)
            elif scenario == TestScenario.LATENCY_TEST:
                await self._run_latency_test(duration_seconds, **scenario_params)
            elif scenario == TestScenario.FAILURE_SIMULATION:
                await self._run_failure_simulation_test(duration_seconds, **scenario_params)
            elif scenario == TestScenario.DLQ_TESTING:
                await self._run_dlq_test(duration_seconds, **scenario_params)
            elif scenario == TestScenario.CHAOS_ENGINEERING:
                await self._run_chaos_engineering_test(duration_seconds, **scenario_params)
            else:
                raise ValueError(f"Unknown test scenario: {scenario}")
            
            # Collect results
            return await self._collect_test_results(scenario, duration_seconds)
            
        except Exception as e:
            logger.error(f"Test scenario failed: {e}")
            self.test_errors.append(str(e))
            raise
        finally:
            self.test_running = False
    
    async def _run_basic_flow_test(self, duration_seconds: int, **params) -> None:
        """Test basic message flow between agents"""
        messages_per_second = params.get('messages_per_second', 10)
        
        # Create simple agent flow: market-analysis -> risk-management -> execution
        if not self.test_agents:
            self.add_test_agent("market-analysis", [EventType.TRADING_SIGNAL_GENERATED])
            self.add_test_agent("risk-management", [EventType.RISK_PARAMETERS_UPDATED])
            self.add_test_agent("execution", [EventType.ORDER_PLACED])
        
        await self.start_agent_consumers()
        
        # Send messages for duration
        end_time = time.time() + duration_seconds
        message_interval = 1.0 / messages_per_second
        
        while time.time() < end_time and self.test_running:
            # Create trading signal
            signal_event = TradingSignalEvent(
                correlation_id=str(uuid4()),
                source_agent="market-analysis",
                target_agent="risk-management",
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
            
            await self.producer.send_event(signal_event, topic="test-risk-management")
            self.test_agents["market-analysis"].messages_sent += 1
            
            await asyncio.sleep(message_interval)
    
    async def _run_high_volume_test(self, duration_seconds: int, **params) -> None:
        """Test high-volume message processing"""
        messages_per_second = params.get('messages_per_second', 1000)
        batch_size = params.get('batch_size', 100)
        
        # Create agents if not exist
        if not self.test_agents:
            self.add_test_agent("high-volume-producer", [])
            self.add_test_agent("high-volume-consumer", [EventType.TRADING_SIGNAL_GENERATED])
        
        await self.start_agent_consumers()
        
        end_time = time.time() + duration_seconds
        batch_interval = batch_size / messages_per_second
        
        while time.time() < end_time and self.test_running:
            # Send batch of messages
            batch_events = []
            for i in range(batch_size):
                event = BaseEvent(
                    event_type=EventType.TRADING_SIGNAL_GENERATED,
                    correlation_id=str(uuid4()),
                    source_agent="high-volume-producer",
                    target_agent="high-volume-consumer",
                    priority=Priority.HIGH,
                    payload={"batch_id": i, "timestamp": time.time()}
                )
                batch_events.append(event)
            
            # Send batch
            results = await self.producer.send_batch(batch_events, topic="test-high-volume-consumer")
            successful_sends = sum(1 for success in results.values() if success)
            self.test_agents["high-volume-producer"].messages_sent += successful_sends
            
            await asyncio.sleep(batch_interval)
    
    async def _run_latency_test(self, duration_seconds: int, **params) -> None:
        """Test message latency performance"""
        target_latency_ms = params.get('target_latency_ms', 10)
        messages_per_second = params.get('messages_per_second', 100)
        
        # Create latency-sensitive agents
        if not self.test_agents:
            self.add_test_agent("latency-producer", [])
            self.add_test_agent("latency-consumer", [EventType.TRADING_SIGNAL_GENERATED], processing_delay_ms=1)
        
        await self.start_agent_consumers()
        
        end_time = time.time() + duration_seconds
        message_interval = 1.0 / messages_per_second
        
        while time.time() < end_time and self.test_running:
            # Send precisely timestamped message
            event = BaseEvent(
                event_type=EventType.TRADING_SIGNAL_GENERATED,
                correlation_id=str(uuid4()),
                source_agent="latency-producer",
                target_agent="latency-consumer",
                priority=Priority.CRITICAL,
                payload={
                    "send_timestamp": time.time(),
                    "target_latency_ms": target_latency_ms
                }
            )
            
            await self.producer.send_event(event, topic="test-latency-consumer")
            self.test_agents["latency-producer"].messages_sent += 1
            
            await asyncio.sleep(message_interval)
    
    async def _run_failure_simulation_test(self, duration_seconds: int, **params) -> None:
        """Simulate various failure scenarios"""
        failure_rate = params.get('failure_rate', 0.1)
        recovery_delay_seconds = params.get('recovery_delay_seconds', 30)
        
        # Create agents with failure simulation
        if not self.test_agents:
            self.add_test_agent("failure-producer", [])
            self.add_test_agent("failure-consumer", [EventType.TRADING_SIGNAL_GENERATED], failure_rate=failure_rate)
        
        await self.start_agent_consumers()
        
        # Simulate intermittent failures
        end_time = time.time() + duration_seconds
        next_failure_time = time.time() + recovery_delay_seconds
        
        while time.time() < end_time and self.test_running:
            # Adjust failure rate periodically
            if time.time() > next_failure_time:
                # Toggle between high and low failure rates
                current_rate = self.test_agents["failure-consumer"].failure_rate
                new_rate = 0.5 if current_rate < 0.3 else 0.1
                self.test_agents["failure-consumer"].failure_rate = new_rate
                next_failure_time = time.time() + recovery_delay_seconds
                
                logger.info(f"Adjusted failure rate to {new_rate}")
            
            # Send test messages
            event = BaseEvent(
                event_type=EventType.TRADING_SIGNAL_GENERATED,
                correlation_id=str(uuid4()),
                source_agent="failure-producer",
                target_agent="failure-consumer",
                payload={"test_id": random.randint(1, 1000)}
            )
            
            await self.producer.send_event(event, topic="test-failure-consumer")
            self.test_agents["failure-producer"].messages_sent += 1
            
            await asyncio.sleep(0.1)  # 10 messages per second
    
    async def _run_dlq_test(self, duration_seconds: int, **params) -> None:
        """Test dead letter queue behavior"""
        poison_message_rate = params.get('poison_message_rate', 0.05)
        
        # Create DLQ test agents
        if not self.test_agents:
            self.add_test_agent("dlq-producer", [])
            self.add_test_agent("dlq-consumer", [EventType.TRADING_SIGNAL_GENERATED], failure_rate=0.2)
        
        await self.start_agent_consumers()
        
        end_time = time.time() + duration_seconds
        
        while time.time() < end_time and self.test_running:
            # Send mix of good and poison messages
            if random.random() < poison_message_rate:
                # Send poison message (malformed payload)
                event = BaseEvent(
                    event_type=EventType.TRADING_SIGNAL_GENERATED,
                    correlation_id=str(uuid4()),
                    source_agent="dlq-producer",
                    target_agent="dlq-consumer",
                    payload={"poison": True, "invalid_data": "This will cause processing failures"}
                )
            else:
                # Send normal message
                event = BaseEvent(
                    event_type=EventType.TRADING_SIGNAL_GENERATED,
                    correlation_id=str(uuid4()),
                    source_agent="dlq-producer",
                    target_agent="dlq-consumer",
                    payload={"normal_message": True, "data": "valid"}
                )
            
            await self.producer.send_event(event, topic="test-dlq-consumer")
            self.test_agents["dlq-producer"].messages_sent += 1
            
            await asyncio.sleep(0.05)  # 20 messages per second
    
    async def _run_chaos_engineering_test(self, duration_seconds: int, **params) -> None:
        """Chaos engineering test with random disruptions"""
        # This would simulate network partitions, broker failures, etc.
        # For now, we simulate with variable delays and failures
        
        if not self.test_agents:
            self.add_test_agent("chaos-producer", [])
            self.add_test_agent("chaos-consumer", [EventType.TRADING_SIGNAL_GENERATED])
        
        await self.start_agent_consumers()
        
        end_time = time.time() + duration_seconds
        
        while time.time() < end_time and self.test_running:
            # Introduce random chaos
            chaos_event = random.choice([
                "normal", "delay", "failure", "burst"
            ])
            
            if chaos_event == "delay":
                # Introduce processing delays
                self.test_agents["chaos-consumer"].processing_delay_ms = random.randint(10, 100)
            elif chaos_event == "failure":
                # Introduce failures
                self.test_agents["chaos-consumer"].failure_rate = random.uniform(0.1, 0.3)
            elif chaos_event == "burst":
                # Send burst of messages
                for i in range(50):
                    event = BaseEvent(
                        event_type=EventType.TRADING_SIGNAL_GENERATED,
                        correlation_id=str(uuid4()),
                        source_agent="chaos-producer",
                        target_agent="chaos-consumer",
                        payload={"burst_id": i}
                    )
                    await self.producer.send_event(event, topic="test-chaos-consumer")
                    self.test_agents["chaos-producer"].messages_sent += 1
            else:
                # Reset to normal
                self.test_agents["chaos-consumer"].processing_delay_ms = 0
                self.test_agents["chaos-consumer"].failure_rate = 0.0
            
            await asyncio.sleep(random.uniform(1, 5))
    
    async def _on_test_message_received(self, event: BaseEvent, agent: TestAgent) -> None:
        """Callback for when test messages are received"""
        # This can be used for additional test logic
        pass
    
    async def _collect_test_results(self, scenario: TestScenario, duration_seconds: int) -> TestResults:
        """Collect and return test results"""
        # Wait a moment for final message processing
        await asyncio.sleep(2)
        
        # Calculate totals
        total_sent = sum(agent.messages_sent for agent in self.test_agents.values())
        total_received = sum(agent.messages_received for agent in self.test_agents.values())
        total_errors = sum(agent.processing_errors for agent in self.test_agents.values())
        
        # Get latency statistics
        latency_stats = {}
        if self.latency_monitor:
            latency_stats = self.latency_monitor.get_latency_statistics(time_window_minutes=duration_seconds)
        
        avg_latency = latency_stats.get('avg_latency_ms', 0)
        max_latency = latency_stats.get('max_latency_ms', 0)
        sla_violations = latency_stats.get('sla_violations', 0)
        
        # Get DLQ statistics
        dlq_stats = self.dlq_handler.get_dlq_statistics() if self.dlq_handler else {}
        dlq_messages = dlq_stats.get('active_dlq_messages', 0)
        
        # Calculate throughput
        throughput = total_received / duration_seconds if duration_seconds > 0 else 0
        
        results = TestResults(
            scenario=scenario,
            duration_seconds=duration_seconds,
            messages_sent=total_sent,
            messages_received=total_received,
            messages_failed=total_errors,
            average_latency_ms=avg_latency,
            max_latency_ms=max_latency,
            throughput_msg_per_sec=throughput,
            sla_violations=sla_violations,
            dlq_messages=dlq_messages,
            errors=self.test_errors.copy()
        )
        
        logger.info(
            "Test scenario completed",
            scenario=scenario.value,
            duration=duration_seconds,
            messages_sent=total_sent,
            messages_received=total_received,
            throughput=round(throughput, 2),
            avg_latency_ms=round(avg_latency, 2)
        )
        
        return results
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.setup()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.teardown()