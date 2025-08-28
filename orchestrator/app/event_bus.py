"""
Event Bus for Trading System Orchestrator

Handles event-driven communication between components using Redis as message broker.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
from pydantic import BaseModel
import redis.asyncio as redis

from .config import get_settings
from .exceptions import OrchestratorException

logger = logging.getLogger(__name__)


class Event(BaseModel):
    """Base event structure"""
    event_id: str
    event_type: str
    timestamp: datetime
    source: str
    data: Dict[str, Any]
    correlation_id: Optional[str] = None


class EventHandler:
    """Event handler registration"""
    def __init__(self, event_type: str, handler: Callable, filter_func: Optional[Callable] = None):
        self.event_type = event_type
        self.handler = handler
        self.filter_func = filter_func


class EventBus:
    """Redis-based event bus for inter-component communication with in-memory fallback"""
    
    def __init__(self):
        self.settings = get_settings()
        self.redis_client: Optional[redis.Redis] = None
        self.handlers: Dict[str, List[EventHandler]] = {}
        self.subscribers: Dict[str, asyncio.Task] = {}
        self._shutdown = False
        self.mock_mode = False
        self.event_store: List[Event] = []
        
    async def start(self):
        """Start the event bus"""
        logger.info("Starting Event Bus")
        
        try:
            # Try to connect to Redis
            self.redis_client = redis.from_url(
                self.settings.message_broker_url,
                decode_responses=True
            )
            
            # Test connection
            await self.redis_client.ping()
            logger.info("Connected to Redis message broker")
            
            # Start event processing
            await self._start_event_processing()
            
        except Exception as e:
            logger.warning(f"Redis connection failed, using in-memory mock mode: {e}")
            self.mock_mode = True
            self.redis_client = None
            logger.info("Event Bus started in mock mode (no Redis)")
    
    async def stop(self):
        """Stop the event bus"""
        logger.info("Stopping Event Bus")
        self._shutdown = True
        
        # Cancel all subscriber tasks
        for task in self.subscribers.values():
            task.cancel()
        
        # Wait for tasks to complete
        if self.subscribers:
            await asyncio.gather(*self.subscribers.values(), return_exceptions=True)
        
        # Close Redis connection
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("Event Bus stopped")
    
    async def publish(self, event: Event):
        """Publish an event to the bus"""
        if self.mock_mode:
            # In-memory mock mode
            try:
                # Store event in memory
                self.event_store.append(event)
                
                # Process handlers for this event type
                if event.event_type in self.handlers:
                    for handler in self.handlers[event.event_type]:
                        try:
                            if handler.filter_func is None or handler.filter_func(event):
                                await handler.handler(event)
                        except Exception as handler_error:
                            logger.error(f"Error in event handler for {event.event_type}: {handler_error}")
                
                logger.debug(f"Published event {event.event_id} of type {event.event_type} (mock mode)")
                return
                
            except Exception as e:
                logger.error(f"Failed to publish event {event.event_id} in mock mode: {e}")
                return  # Don't raise exception in mock mode
        
        if not self.redis_client:
            logger.warning(f"Event Bus not initialized, dropping event {event.event_id}")
            return
        
        try:
            event_data = event.json()
            
            # Publish to specific event type channel
            channel = f"events:{event.event_type}"
            await self.redis_client.publish(channel, event_data)
            
            # Also publish to general events channel
            await self.redis_client.publish("events:all", event_data)
            
            # Store event for retention
            await self._store_event(event)
            
            logger.debug(f"Published event {event.event_id} of type {event.event_type}")
            
        except Exception as e:
            logger.error(f"Failed to publish event {event.event_id}: {e}")
            raise OrchestratorException(f"Event publishing failed: {e}")
    
    async def subscribe(self, event_type: str, handler: Callable, filter_func: Optional[Callable] = None):
        """Subscribe to events of a specific type"""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        
        event_handler = EventHandler(event_type, handler, filter_func)
        self.handlers[event_type].append(event_handler)
        
        # Start subscriber task if not already running and not in mock mode
        if not self.mock_mode and event_type not in self.subscribers:
            task = asyncio.create_task(self._subscribe_to_channel(event_type))
            self.subscribers[event_type] = task
        
        mode_info = " (mock mode)" if self.mock_mode else ""
        logger.info(f"Subscribed to events of type: {event_type}{mode_info}")
    
    async def emit_signal_generated(self, signal_id: str, agent_id: str, signal_data: Dict[str, Any]):
        """Emit a signal generated event"""
        event = Event(
            event_id=f"signal_{signal_id}",
            event_type="signal_generated",
            timestamp=datetime.utcnow(),
            source=agent_id,
            data={
                "signal_id": signal_id,
                "agent_id": agent_id,
                "signal_data": signal_data
            }
        )
        await self.publish(event)
    
    async def emit_trade_executed(self, trade_id: str, account_id: str, trade_data: Dict[str, Any]):
        """Emit a trade executed event"""
        event = Event(
            event_id=f"trade_{trade_id}",
            event_type="trade_executed",
            timestamp=datetime.utcnow(),
            source="orchestrator",
            data={
                "trade_id": trade_id,
                "account_id": account_id,
                "trade_data": trade_data
            }
        )
        await self.publish(event)
    
    async def emit_agent_status_changed(self, agent_id: str, old_status: str, new_status: str):
        """Emit an agent status change event"""
        event = Event(
            event_id=f"agent_status_{agent_id}_{datetime.utcnow().timestamp()}",
            event_type="agent_status_changed",
            timestamp=datetime.utcnow(),
            source="agent_manager",
            data={
                "agent_id": agent_id,
                "old_status": old_status,
                "new_status": new_status
            }
        )
        await self.publish(event)
    
    async def emit_circuit_breaker_triggered(self, breaker_type: str, account_id: str, reason: str):
        """Emit a circuit breaker triggered event"""
        event = Event(
            event_id=f"circuit_breaker_{breaker_type}_{datetime.utcnow().timestamp()}",
            event_type="circuit_breaker_triggered",
            timestamp=datetime.utcnow(),
            source="safety_monitor",
            data={
                "breaker_type": breaker_type,
                "account_id": account_id,
                "reason": reason
            }
        )
        await self.publish(event)
    
    async def emit_system_status_changed(self, old_status: str, new_status: str, reason: str):
        """Emit a system status change event"""
        event = Event(
            event_id=f"system_status_{datetime.utcnow().timestamp()}",
            event_type="system_status_changed",
            timestamp=datetime.utcnow(),
            source="orchestrator",
            data={
                "old_status": old_status,
                "new_status": new_status,
                "reason": reason
            }
        )
        await self.publish(event)
    
    async def emit_performance_alert(self, metric: str, value: float, threshold: float, account_id: str):
        """Emit a performance alert event"""
        event = Event(
            event_id=f"perf_alert_{metric}_{datetime.utcnow().timestamp()}",
            event_type="performance_alert",
            timestamp=datetime.utcnow(),
            source="performance_monitor",
            data={
                "metric": metric,
                "value": value,
                "threshold": threshold,
                "account_id": account_id
            }
        )
        await self.publish(event)
    
    async def _start_event_processing(self):
        """Start processing events for existing subscriptions"""
        # Subscribe to general events channel for monitoring
        task = asyncio.create_task(self._subscribe_to_channel("all"))
        self.subscribers["all"] = task
    
    async def _subscribe_to_channel(self, event_type: str):
        """Subscribe to a Redis channel for event type"""
        if not self.redis_client:
            return
        
        channel = f"events:{event_type}"
        
        try:
            pubsub = self.redis_client.pubsub()
            await pubsub.subscribe(channel)
            
            logger.info(f"Subscribed to channel: {channel}")
            
            while not self._shutdown:
                try:
                    message = await pubsub.get_message(timeout=1.0)
                    if message and message['type'] == 'message':
                        await self._process_event_message(event_type, message['data'])
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.error(f"Error processing message from {channel}: {e}")
                    await asyncio.sleep(1)
            
            await pubsub.unsubscribe(channel)
            await pubsub.close()
            
        except asyncio.CancelledError:
            logger.info(f"Channel subscription cancelled: {channel}")
        except Exception as e:
            logger.error(f"Channel subscription error for {channel}: {e}")
    
    async def _process_event_message(self, event_type: str, message_data: str):
        """Process an event message from Redis"""
        try:
            event_dict = json.loads(message_data)
            event = Event(**event_dict)
            
            # Handle the event with registered handlers
            await self._handle_event(event_type, event)
            
        except Exception as e:
            logger.error(f"Failed to process event message: {e}")
    
    async def _handle_event(self, event_type: str, event: Event):
        """Handle an event with registered handlers"""
        handlers = self.handlers.get(event_type, [])
        
        for handler in handlers:
            try:
                # Apply filter if provided
                if handler.filter_func and not handler.filter_func(event):
                    continue
                
                # Call the handler
                if asyncio.iscoroutinefunction(handler.handler):
                    await handler.handler(event)
                else:
                    handler.handler(event)
                    
            except Exception as e:
                logger.error(f"Error in event handler for {event_type}: {e}")
    
    async def _store_event(self, event: Event):
        """Store event for retention and audit purposes"""
        if not self.redis_client:
            return
        
        try:
            # Store in Redis with expiration
            key = f"event_history:{event.event_type}:{event.event_id}"
            await self.redis_client.setex(
                key,
                self.settings.event_retention_hours * 3600,
                event.json()
            )
            
            # Add to timeline (sorted set by timestamp)
            timeline_key = f"timeline:{event.event_type}"
            await self.redis_client.zadd(
                timeline_key,
                {event.event_id: event.timestamp.timestamp()}
            )
            
            # Expire timeline entries
            await self.redis_client.expire(
                timeline_key,
                self.settings.event_retention_hours * 3600
            )
            
        except Exception as e:
            logger.error(f"Failed to store event {event.event_id}: {e}")
    
    async def get_event_history(self, event_type: str, limit: int = 100) -> List[Event]:
        """Get recent events of a specific type"""
        if not self.redis_client:
            return []
        
        try:
            timeline_key = f"timeline:{event_type}"
            
            # Get recent event IDs from timeline
            event_ids = await self.redis_client.zrevrange(timeline_key, 0, limit - 1)
            
            events = []
            for event_id in event_ids:
                key = f"event_history:{event_type}:{event_id}"
                event_data = await self.redis_client.get(key)
                if event_data:
                    event_dict = json.loads(event_data)
                    events.append(Event(**event_dict))
            
            return events
            
        except Exception as e:
            logger.error(f"Failed to get event history for {event_type}: {e}")
            return []
    
    async def get_system_events(self, limit: int = 100) -> List[Event]:
        """Get recent system events"""
        system_event_types = [
            "signal_generated",
            "trade_executed", 
            "agent_status_changed",
            "circuit_breaker_triggered",
            "system_status_changed"
        ]
        
        all_events = []
        for event_type in system_event_types:
            events = await self.get_event_history(event_type, limit // len(system_event_types))
            all_events.extend(events)
        
        # Sort by timestamp
        all_events.sort(key=lambda e: e.timestamp, reverse=True)
        
        return all_events[:limit]
    
    async def process_pending_events(self):
        """Process any pending events (placeholder for orchestrator health check)"""
        # This method is called by the orchestrator event processing loop
        # For now, it's just a placeholder since events are processed in real-time
        # via Redis pub/sub subscriptions
        pass