"""
Tests for Event Bus
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from typing import Dict, Any

from app.event_bus import EventBus, Event, EventHandler
from app.exceptions import OrchestratorException


class TestEvent:
    """Test Event model"""
    
    def test_event_creation(self):
        """Test creating an Event"""
        now = datetime.utcnow()
        data = {"test": "value", "number": 123}
        
        event = Event(
            event_id="test_event_123",
            event_type="test.event",
            timestamp=now,
            source="test_source",
            data=data,
            correlation_id="corr_123"
        )
        
        assert event.event_id == "test_event_123"
        assert event.event_type == "test.event"
        assert event.timestamp == now
        assert event.source == "test_source"
        assert event.data == data
        assert event.correlation_id == "corr_123"
    
    def test_event_without_correlation_id(self):
        """Test creating Event without correlation ID"""
        event = Event(
            event_id="test_event_123",
            event_type="test.event",
            timestamp=datetime.utcnow(),
            source="test_source",
            data={"test": "value"}
        )
        
        assert event.correlation_id is None


class TestEventHandler:
    """Test EventHandler class"""
    
    def test_event_handler_creation(self):
        """Test creating an EventHandler"""
        def dummy_handler(event):
            pass
        
        def dummy_filter(event):
            return event.event_type == "test.event"
        
        handler = EventHandler("test.event", dummy_handler, dummy_filter)
        
        assert handler.event_type == "test.event"
        assert handler.handler == dummy_handler
        assert handler.filter_func == dummy_filter
    
    def test_event_handler_without_filter(self):
        """Test creating EventHandler without filter"""
        def dummy_handler(event):
            pass
        
        handler = EventHandler("test.event", dummy_handler)
        
        assert handler.event_type == "test.event"
        assert handler.handler == dummy_handler
        assert handler.filter_func is None


class TestEventBus:
    """Test EventBus functionality"""
    
    @pytest.fixture
    async def event_bus(self, test_settings, mock_redis):
        """Create EventBus instance for testing"""
        with patch('app.event_bus.get_settings', return_value=test_settings):
            with patch('app.event_bus.redis.from_url', return_value=mock_redis):
                bus = EventBus()
                yield bus
                await bus.stop()
    
    @pytest.mark.asyncio
    async def test_event_bus_start_success(self, event_bus, mock_redis):
        """Test successful EventBus startup"""
        mock_redis.ping.return_value = True
        
        await event_bus.start()
        
        assert event_bus.redis_client is not None
        mock_redis.ping.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_event_bus_start_failure(self, test_settings, mock_redis):
        """Test EventBus startup failure"""
        mock_redis.ping.side_effect = Exception("Redis connection failed")
        
        with patch('app.event_bus.get_settings', return_value=test_settings):
            with patch('app.event_bus.redis.from_url', return_value=mock_redis):
                bus = EventBus()
                
                with pytest.raises(OrchestratorException) as excinfo:
                    await bus.start()
                
                assert "Event Bus startup failed" in str(excinfo.value)
    
    @pytest.mark.asyncio
    async def test_publish_event_success(self, event_bus, mock_redis):
        """Test successful event publishing"""
        await event_bus.start()
        
        event = Event(
            event_id="test_123",
            event_type="test.event",
            timestamp=datetime.utcnow(),
            source="test_source",
            data={"message": "test data"}
        )
        
        await event_bus.publish(event)
        
        # Should publish to both specific and general channels
        assert mock_redis.publish.call_count == 2
        calls = mock_redis.publish.call_args_list
        
        # Check specific channel
        assert calls[0][0][0] == "events:test.event"
        assert calls[1][0][0] == "events:all"
        
        # Check event storage
        mock_redis.setex.assert_called()
        mock_redis.zadd.assert_called()
    
    @pytest.mark.asyncio
    async def test_publish_event_failure(self, event_bus, mock_redis):
        """Test event publishing failure"""
        await event_bus.start()
        mock_redis.publish.side_effect = Exception("Redis publish failed")
        
        event = Event(
            event_id="test_123",
            event_type="test.event",
            timestamp=datetime.utcnow(),
            source="test_source",
            data={"message": "test data"}
        )
        
        with pytest.raises(OrchestratorException) as excinfo:
            await event_bus.publish(event)
        
        assert "Event publishing failed" in str(excinfo.value)
    
    @pytest.mark.asyncio
    async def test_subscribe_to_events(self, event_bus, mock_redis):
        """Test subscribing to events"""
        await event_bus.start()
        
        # Mock pubsub
        mock_pubsub = AsyncMock()
        mock_redis.pubsub.return_value = mock_pubsub
        
        received_events = []
        
        def test_handler(event: Event):
            received_events.append(event)
        
        await event_bus.subscribe("test.event", test_handler)
        
        # Should have registered the handler
        assert "test.event" in event_bus.handlers
        assert len(event_bus.handlers["test.event"]) == 1
        assert event_bus.handlers["test.event"][0].handler == test_handler
        
        # Should have started subscriber task
        assert "test.event" in event_bus.subscribers
    
    @pytest.mark.asyncio
    async def test_subscribe_with_filter(self, event_bus, mock_redis):
        """Test subscribing to events with filter"""
        await event_bus.start()
        
        # Mock pubsub
        mock_pubsub = AsyncMock()
        mock_redis.pubsub.return_value = mock_pubsub
        
        received_events = []
        
        def test_handler(event: Event):
            received_events.append(event)
        
        def test_filter(event: Event):
            return event.source == "allowed_source"
        
        await event_bus.subscribe("test.event", test_handler, test_filter)
        
        handler = event_bus.handlers["test.event"][0]
        assert handler.filter_func == test_filter
    
    @pytest.mark.asyncio
    async def test_emit_signal_generated(self, event_bus, mock_redis):
        """Test emitting signal generated event"""
        await event_bus.start()
        
        await event_bus.emit_signal_generated(
            "signal_123", 
            "market-analysis", 
            {"instrument": "EUR_USD", "direction": "long"}
        )
        
        # Should have published event
        mock_redis.publish.assert_called()
        
        # Verify event data
        call_args = mock_redis.publish.call_args_list[0][0]
        channel = call_args[0]
        event_json = call_args[1]
        
        assert channel == "events:signal_generated"
        
        event_data = json.loads(event_json)
        assert event_data["event_type"] == "signal_generated"
        assert event_data["source"] == "market-analysis"
        assert event_data["data"]["signal_id"] == "signal_123"
    
    @pytest.mark.asyncio
    async def test_emit_trade_executed(self, event_bus, mock_redis):
        """Test emitting trade executed event"""
        await event_bus.start()
        
        await event_bus.emit_trade_executed(
            "trade_123",
            "account_456",
            {"instrument": "EUR_USD", "units": 1000, "price": 1.0500}
        )
        
        # Verify event was published
        mock_redis.publish.assert_called()
        
        call_args = mock_redis.publish.call_args_list[0][0]
        channel = call_args[0]
        event_json = call_args[1]
        
        assert channel == "events:trade_executed"
        
        event_data = json.loads(event_json)
        assert event_data["event_type"] == "trade_executed"
        assert event_data["source"] == "orchestrator"
        assert event_data["data"]["trade_id"] == "trade_123"
        assert event_data["data"]["account_id"] == "account_456"
    
    @pytest.mark.asyncio
    async def test_emit_circuit_breaker_triggered(self, event_bus, mock_redis):
        """Test emitting circuit breaker triggered event"""
        await event_bus.start()
        
        await event_bus.emit_circuit_breaker_triggered(
            "account_loss",
            "account_123",
            "Account loss exceeded 5% threshold"
        )
        
        # Verify event was published
        mock_redis.publish.assert_called()
        
        call_args = mock_redis.publish.call_args_list[0][0]
        event_data = json.loads(call_args[1])
        
        assert event_data["event_type"] == "circuit_breaker_triggered"
        assert event_data["source"] == "safety_monitor"
        assert event_data["data"]["breaker_type"] == "account_loss"
        assert event_data["data"]["reason"] == "Account loss exceeded 5% threshold"
    
    @pytest.mark.asyncio
    async def test_emit_agent_status_changed(self, event_bus, mock_redis):
        """Test emitting agent status changed event"""
        await event_bus.start()
        
        await event_bus.emit_agent_status_changed(
            "market-analysis",
            "active",
            "error"
        )
        
        # Verify event was published
        mock_redis.publish.assert_called()
        
        call_args = mock_redis.publish.call_args_list[0][0]
        event_data = json.loads(call_args[1])
        
        assert event_data["event_type"] == "agent_status_changed"
        assert event_data["source"] == "agent_manager"
        assert event_data["data"]["agent_id"] == "market-analysis"
        assert event_data["data"]["old_status"] == "active"
        assert event_data["data"]["new_status"] == "error"
    
    @pytest.mark.asyncio
    async def test_emit_performance_alert(self, event_bus, mock_redis):
        """Test emitting performance alert event"""
        await event_bus.start()
        
        await event_bus.emit_performance_alert(
            "drawdown",
            0.08,  # 8%
            0.05,  # 5% threshold
            "account_123"
        )
        
        # Verify event was published
        mock_redis.publish.assert_called()
        
        call_args = mock_redis.publish.call_args_list[0][0]
        event_data = json.loads(call_args[1])
        
        assert event_data["event_type"] == "performance_alert"
        assert event_data["source"] == "performance_monitor"
        assert event_data["data"]["metric"] == "drawdown"
        assert event_data["data"]["value"] == 0.08
        assert event_data["data"]["threshold"] == 0.05
    
    @pytest.mark.asyncio
    async def test_get_event_history(self, event_bus, mock_redis):
        """Test getting event history"""
        await event_bus.start()
        
        # Mock stored events
        mock_redis.zrevrange.return_value = ["event_1", "event_2", "event_3"]
        
        # Mock event retrieval
        def mock_get(key):
            if "event_1" in key:
                return json.dumps({
                    "event_id": "event_1",
                    "event_type": "test.event",
                    "timestamp": datetime.utcnow().isoformat(),
                    "source": "test",
                    "data": {"message": "test 1"}
                })
            elif "event_2" in key:
                return json.dumps({
                    "event_id": "event_2", 
                    "event_type": "test.event",
                    "timestamp": datetime.utcnow().isoformat(),
                    "source": "test",
                    "data": {"message": "test 2"}
                })
            return None
        
        mock_redis.get.side_effect = mock_get
        
        events = await event_bus.get_event_history("test.event", limit=10)
        
        assert len(events) == 2  # Only 2 events had valid data
        assert all(isinstance(event, Event) for event in events)
        assert events[0].event_id == "event_1"
        assert events[1].event_id == "event_2"
    
    @pytest.mark.asyncio
    async def test_get_system_events(self, event_bus, mock_redis):
        """Test getting system events"""
        await event_bus.start()
        
        # Mock empty history for each event type
        mock_redis.zrevrange.return_value = []
        
        events = await event_bus.get_system_events(limit=100)
        
        # Should return empty list when no events
        assert events == []
        
        # Should have called zrevrange for each system event type
        expected_calls = len([
            "signal_generated", "trade_executed", "agent_status_changed",
            "circuit_breaker_triggered", "system_status_changed"
        ])
        assert mock_redis.zrevrange.call_count == expected_calls
    
    @pytest.mark.asyncio
    async def test_event_storage(self, event_bus, mock_redis):
        """Test event storage mechanism"""
        await event_bus.start()
        
        event = Event(
            event_id="storage_test",
            event_type="test.storage",
            timestamp=datetime.utcnow(),
            source="test",
            data={"test": "storage"}
        )
        
        await event_bus.publish(event)
        
        # Should store event with expiration
        mock_redis.setex.assert_called()
        setex_call = mock_redis.setex.call_args
        key = setex_call[0][0]
        ttl = setex_call[0][1]
        event_json = setex_call[0][2]
        
        assert "event_history:test.storage:storage_test" in key
        assert ttl == 24 * 3600  # 24 hours in seconds
        
        # Should add to timeline
        mock_redis.zadd.assert_called()
        zadd_call = mock_redis.zadd.call_args
        timeline_key = zadd_call[0][0]
        score_dict = zadd_call[0][1]
        
        assert "timeline:test.storage" in timeline_key
        assert "storage_test" in score_dict
    
    @pytest.mark.asyncio
    async def test_event_processing_with_handlers(self, event_bus, mock_redis):
        """Test event processing with registered handlers"""
        await event_bus.start()
        
        received_events = []
        
        async def async_handler(event: Event):
            received_events.append(("async", event))
        
        def sync_handler(event: Event):
            received_events.append(("sync", event))
        
        # Register handlers
        event_bus.handlers["test.event"] = [
            EventHandler("test.event", async_handler),
            EventHandler("test.event", sync_handler)
        ]
        
        # Create test event
        event = Event(
            event_id="handler_test",
            event_type="test.event",
            timestamp=datetime.utcnow(),
            source="test",
            data={"message": "handler test"}
        )
        
        # Process event directly
        await event_bus._handle_event("test.event", event)
        
        # Both handlers should have received the event
        assert len(received_events) == 2
        assert received_events[0][0] == "async"
        assert received_events[1][0] == "sync"
        assert received_events[0][1].event_id == "handler_test"
        assert received_events[1][1].event_id == "handler_test"
    
    @pytest.mark.asyncio
    async def test_event_processing_with_filter(self, event_bus):
        """Test event processing with filters"""
        received_events = []
        
        def filtered_handler(event: Event):
            received_events.append(event)
        
        def filter_func(event: Event):
            return event.source == "allowed_source"
        
        # Register handler with filter
        event_bus.handlers["test.event"] = [
            EventHandler("test.event", filtered_handler, filter_func)
        ]
        
        # Create events with different sources
        allowed_event = Event(
            event_id="allowed",
            event_type="test.event",
            timestamp=datetime.utcnow(),
            source="allowed_source",
            data={}
        )
        
        blocked_event = Event(
            event_id="blocked",
            event_type="test.event", 
            timestamp=datetime.utcnow(),
            source="blocked_source",
            data={}
        )
        
        # Process both events
        await event_bus._handle_event("test.event", allowed_event)
        await event_bus._handle_event("test.event", blocked_event)
        
        # Only the allowed event should have been processed
        assert len(received_events) == 1
        assert received_events[0].event_id == "allowed"
    
    @pytest.mark.asyncio
    async def test_stop_event_bus(self, event_bus, mock_redis):
        """Test stopping the event bus"""
        await event_bus.start()
        
        # Add some subscriber tasks
        mock_task = Mock()
        mock_task.cancel = Mock()
        event_bus.subscribers["test"] = mock_task
        
        await event_bus.stop()
        
        # Should cancel tasks and close Redis connection
        mock_task.cancel.assert_called_once()
        mock_redis.close.assert_called_once()
        assert event_bus._shutdown is True