"""
Integration tests for OpenTelemetry distributed tracing across agent communications.

These tests verify that:
1. Correlation IDs are properly propagated across service boundaries
2. Trace context is maintained through Kafka messages
3. Custom spans are created for trading operations
4. Sampling works correctly across different environments
"""

import asyncio
import json
import time
import uuid
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock, patch

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from ..tracing import (
    configure_tracing,
    get_tracer,
    create_span,
    add_correlation_context,
    get_correlation_id,
    trace_trading_operation
)
from ..middleware import (
    KafkaTracingMiddleware,
    trace_circuit_breaker_operation,
    trace_trading_operation as middleware_trace_trading_operation
)
from ..config import ObservabilityConfig, ServiceConfigs

# Test fixtures
@pytest.fixture
def in_memory_exporter():
    """Create an in-memory span exporter for testing."""
    exporter = InMemorySpanExporter()
    return exporter

@pytest.fixture
def test_tracer(in_memory_exporter):
    """Configure a test tracer with in-memory export."""
    configure_tracing(
        service_name="test-agent",
        service_version="1.0.0-test",
        environment="development",
        sampling_rate=1.0,
        export_console=False
    )
    
    # Add in-memory processor for testing
    tracer_provider = trace.get_tracer_provider()
    processor = SimpleSpanProcessor(in_memory_exporter)
    tracer_provider.add_span_processor(processor)
    
    return get_tracer("test-tracer")

@pytest.fixture
def mock_kafka_message():
    """Create a mock Kafka message for testing."""
    message = Mock()
    message.topic = "trading.signals.generated"
    message.partition = 0
    message.offset = 12345
    message.headers = [
        (b"correlation_id", b"test-correlation-123"),
        (b"traceparent", b"00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01")
    ]
    message.value = json.dumps({
        "event_id": "event-123",
        "event_type": "TRADING_SIGNAL_GENERATED",
        "correlation_id": "test-correlation-123",
        "timestamp": "2025-08-07T10:30:00Z",
        "data": {"signal": "BUY", "confidence": 0.85}
    }).encode("utf-8")
    return message

class TestCorrelationIDPropagation:
    """Test correlation ID propagation across service boundaries."""
    
    def test_correlation_id_context(self):
        """Test that correlation IDs are properly managed in context."""
        # Initially no correlation ID
        assert get_correlation_id() is None
        
        # Set correlation ID
        test_correlation_id = "test-123-456"
        add_correlation_context(test_correlation_id)
        
        # Verify it's retrieved correctly
        assert get_correlation_id() == test_correlation_id
    
    @pytest.mark.asyncio
    async def test_span_correlation_injection(self, test_tracer, in_memory_exporter):
        """Test that correlation IDs are injected into spans."""
        correlation_id = "test-span-correlation-789"
        add_correlation_context(correlation_id)
        
        with create_span("test_operation") as span:
            # Verify span has correlation ID attribute
            pass
        
        # Check exported spans
        spans = in_memory_exporter.get_finished_spans()
        assert len(spans) == 1
        
        span = spans[0]
        assert span.attributes.get("correlation_id") == correlation_id

class TestTradingOperationTracing:
    """Test custom spans for critical trading operations."""
    
    @pytest.mark.asyncio
    async def test_trading_operation_decorator(self, test_tracer, in_memory_exporter):
        """Test the trading operation tracing decorator."""
        
        @trace_trading_operation("signal_generation", "analysis")
        async def generate_trading_signal(symbol: str, confidence: float):
            await asyncio.sleep(0.01)  # Simulate processing time
            return {"signal": "BUY", "confidence": confidence, "symbol": symbol}
        
        correlation_id = "trading-op-test-123"
        add_correlation_context(correlation_id)
        
        # Execute the traced operation
        result = await generate_trading_signal("EURUSD", 0.85)
        
        # Verify result
        assert result["signal"] == "BUY"
        assert result["confidence"] == 0.85
        
        # Check exported spans
        spans = in_memory_exporter.get_finished_spans()
        assert len(spans) == 1
        
        span = spans[0]
        assert span.name == "analysis.signal_generation"
        assert span.attributes.get("correlation_id") == correlation_id
        assert span.attributes.get("operation.type") == "analysis"
        assert span.attributes.get("operation.name") == "signal_generation"
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_tracing(self, test_tracer, in_memory_exporter):
        """Test circuit breaker operation tracing."""
        
        @trace_circuit_breaker_operation("account", "high_loss_rate")
        async def activate_circuit_breaker():
            return {"status": "activated", "tier": "account"}
        
        correlation_id = "circuit-breaker-test-456"
        add_correlation_context(correlation_id)
        
        # Execute the traced circuit breaker operation
        result = await activate_circuit_breaker()
        
        # Verify result
        assert result["status"] == "activated"
        
        # Check exported spans
        spans = in_memory_exporter.get_finished_spans()
        assert len(spans) == 1
        
        span = spans[0]
        assert "circuit_breaker" in span.name
        assert span.attributes.get("circuit_breaker.tier") == "account"
        assert span.attributes.get("circuit_breaker.reason") == "high_loss_rate"

class TestKafkaTracing:
    """Test Kafka message tracing and context propagation."""
    
    @pytest.mark.asyncio
    async def test_kafka_producer_tracing(self, test_tracer, in_memory_exporter):
        """Test tracing of Kafka message production."""
        
        # Mock event object
        mock_event = Mock()
        mock_event.event_id = "kafka-test-event-123"
        mock_event.correlation_id = "kafka-correlation-456"
        mock_event.event_type.value = "TRADING_SIGNAL_GENERATED"
        
        # Mock producer method
        async def mock_send_event(event, topic=None, key=None, headers=None):
            # Verify headers contain trace information
            assert headers is not None
            assert "correlation_id" in headers
            return True
        
        # Apply tracing wrapper
        traced_send = KafkaTracingMiddleware.wrap_producer_send(mock_send_event)
        
        # Set correlation context
        add_correlation_context(mock_event.correlation_id)
        
        # Execute traced send
        result = await traced_send(None, mock_event, topic="test.topic")
        
        assert result is True
        
        # Check exported spans
        spans = in_memory_exporter.get_finished_spans()
        assert len(spans) == 1
        
        span = spans[0]
        assert span.name == "kafka.producer.send"
        assert span.attributes.get("messaging.system") == "kafka"
        assert span.attributes.get("messaging.destination") == "test.topic"
        assert span.attributes.get("correlation_id") == mock_event.correlation_id
    
    @pytest.mark.asyncio  
    async def test_kafka_consumer_tracing(self, test_tracer, in_memory_exporter, mock_kafka_message):
        """Test tracing of Kafka message consumption."""
        
        async def mock_process_message(message):
            # Simulate message processing
            await asyncio.sleep(0.01)
            return {"processed": True, "topic": message.topic}
        
        # Apply tracing wrapper
        traced_process = KafkaTracingMiddleware.wrap_consumer_process(mock_process_message)
        
        # Execute traced processing
        result = await traced_process(None, mock_kafka_message)
        
        assert result["processed"] is True
        assert result["topic"] == "trading.signals.generated"
        
        # Check exported spans
        spans = in_memory_exporter.get_finished_spans()
        assert len(spans) == 1
        
        span = spans[0]
        assert span.name == "kafka.consumer.process"
        assert span.attributes.get("messaging.system") == "kafka"
        assert span.attributes.get("messaging.source") == "trading.signals.generated"

class TestSamplingConfiguration:
    """Test sampling rate configuration for different environments."""
    
    def test_development_sampling(self):
        """Test that development environment uses 100% sampling."""
        config = ServiceConfigs.circuit_breaker_agent()
        assert config.tracing.sampling_rate == 1.0
    
    def test_production_sampling_optimization(self):
        """Test that production sampling rates are optimized for performance."""
        # Mock production environment
        with patch.dict("os.environ", {"TRADING_ENVIRONMENT": "production"}):
            config = ObservabilityConfig.for_service("market-analysis-agent")
            # Should use reduced sampling in production
            assert config.tracing.sampling_rate <= 0.5
    
    def test_critical_service_sampling(self):
        """Test that critical services maintain high sampling rates."""
        config = ServiceConfigs.circuit_breaker_agent()
        # Circuit breaker should always use 100% sampling for safety
        assert config.tracing.sampling_rate == 1.0
        
        config = ServiceConfigs.execution_engine()
        # Execution engine should maintain high sampling
        assert config.tracing.sampling_rate >= 0.3

class TestEndToEndTracing:
    """Test complete end-to-end distributed tracing scenarios."""
    
    @pytest.mark.asyncio
    async def test_multi_service_trace_propagation(self, test_tracer, in_memory_exporter):
        """Test trace propagation across multiple services."""
        
        # Simulate market analysis agent generating a signal
        @middleware_trace_trading_operation("signal")
        async def analyze_market():
            return {"signal": "BUY", "confidence": 0.85}
        
        # Simulate risk management agent processing the signal
        @middleware_trace_trading_operation("risk")
        async def calculate_risk(signal_data):
            position_size = signal_data["confidence"] * 1000
            return {"position_size": position_size, "risk_score": 0.2}
        
        # Simulate execution engine executing the trade
        @middleware_trace_trading_operation("execution") 
        async def execute_trade(risk_data):
            return {"trade_id": "TRADE-123", "status": "executed", "size": risk_data["position_size"]}
        
        correlation_id = "e2e-test-correlation-789"
        add_correlation_context(correlation_id)
        
        # Execute the complete workflow
        signal = await analyze_market()
        risk_assessment = await calculate_risk(signal)
        trade_result = await execute_trade(risk_assessment)
        
        # Verify final result
        assert trade_result["status"] == "executed"
        assert trade_result["trade_id"] == "TRADE-123"
        
        # Check that all spans were created with proper correlation
        spans = in_memory_exporter.get_finished_spans()
        assert len(spans) == 3
        
        # Verify all spans have the same correlation ID
        for span in spans:
            assert span.attributes.get("correlation_id") == correlation_id
        
        # Verify span names indicate different trading operations
        span_names = [span.name for span in spans]
        assert any("signal" in name for name in span_names)
        assert any("risk" in name for name in span_names) 
        assert any("execution" in name for name in span_names)

class TestPerformanceOptimization:
    """Test performance optimizations in tracing configuration."""
    
    def test_batch_size_configuration(self):
        """Test that batch sizes are properly configured for different services."""
        execution_config = ServiceConfigs.execution_engine()
        dashboard_config = ServiceConfigs.dashboard()
        
        # Execution engine should have smaller batches for lower latency
        assert execution_config.tracing.span_processor_batch_size <= 256
        
        # Dashboard can have larger batches
        assert dashboard_config.tracing.span_processor_batch_size >= 256
    
    def test_timeout_configuration(self):
        """Test export timeout configuration."""
        config = ServiceConfigs.execution_engine()
        
        # Execution engine should have shorter timeouts
        assert config.tracing.span_processor_export_timeout_ms <= 15000

# Integration test that requires actual infrastructure
@pytest.mark.integration
class TestRealInfrastructureTracing:
    """Integration tests that require real Kafka and Jaeger infrastructure."""
    
    @pytest.mark.asyncio
    async def test_jaeger_export_integration(self):
        """Test actual export to Jaeger (requires Jaeger running)."""
        configure_tracing(
            service_name="integration-test-agent",
            jaeger_endpoint="localhost:14268",
            sampling_rate=1.0
        )
        
        correlation_id = str(uuid.uuid4())
        add_correlation_context(correlation_id)
        
        with create_span("integration_test_span") as span:
            span.set_attribute("test.type", "integration")
            span.set_attribute("test.timestamp", time.time())
            
            # Simulate some work
            await asyncio.sleep(0.1)
        
        # Allow time for export
        await asyncio.sleep(1)
        
        # This test would verify the span appears in Jaeger UI
        # In a real scenario, you'd query Jaeger API to verify the span was received