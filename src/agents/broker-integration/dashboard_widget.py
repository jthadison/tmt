"""
Dashboard Connection Status Widget Backend
Story 8.1 - Task 5: Create dashboard connection status widget
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
from dataclasses import dataclass, asdict
from enum import Enum

from .reconnection_manager import OandaReconnectionManager, ConnectionState
from .connection_pool import OandaConnectionPool
from .oanda_auth_handler import OandaAuthHandler

logger = logging.getLogger(__name__)

class ConnectionQuality(Enum):
    EXCELLENT = "excellent"  # < 100ms, no errors
    GOOD = "good"           # < 300ms, minimal errors
    FAIR = "fair"           # < 500ms, some errors
    POOR = "poor"           # > 500ms or high error rate

@dataclass
class ConnectionStatusData:
    """Real-time connection status information for dashboard"""
    connection_id: str
    account_id: str
    environment: str
    state: ConnectionState
    quality: ConnectionQuality
    last_seen: datetime
    response_time_ms: Optional[float]
    error_rate: float
    uptime_percentage: float
    is_reconnecting: bool
    reconnection_attempts: int
    last_error: Optional[str]
    connection_history: List[Dict[str, Any]]

@dataclass
class SystemStatusSummary:
    """Overall system status for dashboard"""
    total_connections: int
    healthy_connections: int
    reconnecting_connections: int
    failed_connections: int
    overall_health_percentage: float
    average_response_time: float
    total_uptime_percentage: float
    active_reconnections: int
    circuit_breakers_open: int

class ConnectionStatusWidget:
    """Backend service for dashboard connection status widget"""
    
    def __init__(self, 
                 auth_handler: OandaAuthHandler,
                 connection_pool: OandaConnectionPool,
                 reconnection_manager: OandaReconnectionManager):
        
        self.auth_handler = auth_handler
        self.connection_pool = connection_pool
        self.reconnection_manager = reconnection_manager
        
        # WebSocket connections for real-time updates
        self.websocket_clients = set()
        
        # Status tracking
        self.connection_statuses: Dict[str, ConnectionStatusData] = {}
        self.status_history: Dict[str, List[Dict[str, Any]]] = {}
        self.last_update = datetime.utcnow()
        
        # Update intervals
        self.update_interval = 5  # seconds
        self.history_retention_hours = 24
        
        # Background task
        self.update_task: Optional[asyncio.Task] = None
        self.running = False
    
    async def start(self):
        """Start the dashboard widget service"""
        if self.running:
            return
            
        logger.info("Starting connection status widget service")
        self.running = True
        
        # Subscribe to reconnection events
        self.reconnection_manager.subscribe_to_events('connection_lost', self._handle_connection_lost)
        self.reconnection_manager.subscribe_to_events('reconnection_started', self._handle_reconnection_started)
        self.reconnection_manager.subscribe_to_events('reconnection_success', self._handle_reconnection_success)
        self.reconnection_manager.subscribe_to_events('reconnection_failed', self._handle_reconnection_failed)
        
        # Start background update task
        self.update_task = asyncio.create_task(self._update_loop())
        
        logger.info("Connection status widget service started")
    
    async def stop(self):
        """Stop the dashboard widget service"""
        if not self.running:
            return
            
        logger.info("Stopping connection status widget service")
        self.running = False
        
        # Cancel update task
        if self.update_task:
            self.update_task.cancel()
            try:
                await self.update_task
            except asyncio.CancelledError:
                pass
        
        # Close all WebSocket connections
        for websocket in self.websocket_clients.copy():
            try:
                await websocket.close()
            except:
                pass
        
        self.websocket_clients.clear()
        logger.info("Connection status widget service stopped")
    
    async def get_connection_status(self, connection_id: str) -> Optional[ConnectionStatusData]:
        """Get status for specific connection"""
        return self.connection_statuses.get(connection_id)
    
    async def get_all_connection_statuses(self) -> List[ConnectionStatusData]:
        """Get status for all connections"""
        await self._update_connection_statuses()
        return list(self.connection_statuses.values())
    
    async def get_system_summary(self) -> SystemStatusSummary:
        """Get overall system status summary"""
        await self._update_connection_statuses()
        
        statuses = list(self.connection_statuses.values())
        total = len(statuses)
        
        if total == 0:
            return SystemStatusSummary(
                total_connections=0,
                healthy_connections=0,
                reconnecting_connections=0,
                failed_connections=0,
                overall_health_percentage=0.0,
                average_response_time=0.0,
                total_uptime_percentage=0.0,
                active_reconnections=0,
                circuit_breakers_open=0
            )
        
        healthy = sum(1 for s in statuses if s.state == ConnectionState.CONNECTED and s.quality in [ConnectionQuality.EXCELLENT, ConnectionQuality.GOOD])
        reconnecting = sum(1 for s in statuses if s.is_reconnecting)
        failed = sum(1 for s in statuses if s.state == ConnectionState.FAILED)
        
        # Calculate averages
        avg_response_time = sum(s.response_time_ms or 0 for s in statuses) / total
        avg_uptime = sum(s.uptime_percentage for s in statuses) / total
        health_percentage = (healthy / total) * 100
        
        # Get reconnection manager stats
        health_info = self.reconnection_manager.get_system_health()
        active_reconnections = health_info['active_reconnection_tasks']
        circuit_breakers_open = health_info['circuit_breakers']['open']
        
        return SystemStatusSummary(
            total_connections=total,
            healthy_connections=healthy,
            reconnecting_connections=reconnecting,
            failed_connections=failed,
            overall_health_percentage=health_percentage,
            average_response_time=avg_response_time,
            total_uptime_percentage=avg_uptime,
            active_reconnections=active_reconnections,
            circuit_breakers_open=circuit_breakers_open
        )
    
    async def get_connection_history(self, connection_id: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get connection status history"""
        history = self.status_history.get(connection_id, [])
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        return [
            event for event in history
            if datetime.fromisoformat(event['timestamp']) >= cutoff
        ]
    
    async def add_websocket_client(self, websocket):
        """Add WebSocket client for real-time updates"""
        self.websocket_clients.add(websocket)
        logger.debug(f"WebSocket client added. Total clients: {len(self.websocket_clients)}")
        
        # Send initial status
        try:
            initial_data = await self.get_dashboard_data()
            await websocket.send(json.dumps({
                'type': 'initial_status',
                'data': initial_data
            }))
        except Exception as e:
            logger.error(f"Error sending initial status: {e}")
    
    async def remove_websocket_client(self, websocket):
        """Remove WebSocket client"""
        self.websocket_clients.discard(websocket)
        logger.debug(f"WebSocket client removed. Total clients: {len(self.websocket_clients)}")
    
    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get complete dashboard data"""
        summary = await self.get_system_summary()
        connections = await self.get_all_connection_statuses()
        
        return {
            'summary': asdict(summary),
            'connections': [asdict(conn) for conn in connections],
            'last_updated': datetime.utcnow().isoformat()
        }
    
    async def _update_loop(self):
        """Background loop to update connection statuses"""
        while self.running:
            try:
                await asyncio.sleep(self.update_interval)
                
                if not self.running:
                    break
                
                await self._update_connection_statuses()
                await self._broadcast_updates()
                await self._cleanup_old_history()
                
            except Exception as e:
                logger.error(f"Error in status update loop: {e}")
    
    async def _update_connection_statuses(self):
        """Update all connection statuses"""
        # Get session info from auth handler
        session_stats = self.auth_handler.get_session_stats()
        
        # Get pool stats
        pool_stats = self.connection_pool.get_pool_stats()
        
        # Get reconnection states
        connection_states = self.reconnection_manager.get_all_connection_states()
        
        # Update each connection status
        current_time = datetime.utcnow()
        
        for session_key, context in self.auth_handler.active_sessions.items():
            connection_id = f"oanda_{context.account_id}"
            
            # Get connection quality
            quality = await self._calculate_connection_quality(context)
            
            # Get reconnection info
            state = connection_states.get(connection_id, ConnectionState.CONNECTED)
            reconnection_stats = self.reconnection_manager.get_reconnection_stats(connection_id)
            
            # Calculate uptime
            uptime_percentage = self._calculate_uptime(connection_id)
            
            status = ConnectionStatusData(
                connection_id=connection_id,
                account_id=context.account_id,
                environment=context.environment.value,
                state=state,
                quality=quality,
                last_seen=context.last_refresh,
                response_time_ms=None,  # Would be updated from actual API calls
                error_rate=0.0,  # Would be calculated from actual API calls
                uptime_percentage=uptime_percentage,
                is_reconnecting=state == ConnectionState.RECONNECTING,
                reconnection_attempts=reconnection_stats.total_attempts if reconnection_stats else 0,
                last_error=None,
                connection_history=[]
            )
            
            # Update status
            old_status = self.connection_statuses.get(connection_id)
            self.connection_statuses[connection_id] = status
            
            # Record status change in history
            if not old_status or old_status.state != status.state:
                await self._record_status_change(connection_id, status)
    
    async def _calculate_connection_quality(self, context) -> ConnectionQuality:
        """Calculate connection quality based on metrics"""
        # This would integrate with actual connection metrics
        # For now, use simple heuristics
        
        time_since_refresh = datetime.utcnow() - context.last_refresh
        
        if time_since_refresh < timedelta(seconds=30):
            return ConnectionQuality.EXCELLENT
        elif time_since_refresh < timedelta(minutes=2):
            return ConnectionQuality.GOOD
        elif time_since_refresh < timedelta(minutes=5):
            return ConnectionQuality.FAIR
        else:
            return ConnectionQuality.POOR
    
    def _calculate_uptime(self, connection_id: str) -> float:
        """Calculate uptime percentage for last 24 hours"""
        history = self.status_history.get(connection_id, [])
        
        if not history:
            return 100.0  # Assume good if no history
        
        # Simple calculation - would be more sophisticated in production
        recent_events = [
            event for event in history
            if datetime.fromisoformat(event['timestamp']) >= datetime.utcnow() - timedelta(hours=24)
        ]
        
        if not recent_events:
            return 100.0
        
        connected_events = [event for event in recent_events if event['state'] == 'connected']
        return (len(connected_events) / len(recent_events)) * 100
    
    async def _record_status_change(self, connection_id: str, status: ConnectionStatusData):
        """Record status change in history"""
        if connection_id not in self.status_history:
            self.status_history[connection_id] = []
        
        history_event = {
            'timestamp': datetime.utcnow().isoformat(),
            'state': status.state.value,
            'quality': status.quality.value,
            'response_time_ms': status.response_time_ms,
            'error_rate': status.error_rate
        }
        
        self.status_history[connection_id].append(history_event)
        
        # Limit history size
        if len(self.status_history[connection_id]) > 1000:
            self.status_history[connection_id] = self.status_history[connection_id][-500:]
    
    async def _broadcast_updates(self):
        """Broadcast updates to all WebSocket clients"""
        if not self.websocket_clients:
            return
        
        try:
            update_data = await self.get_dashboard_data()
            message = json.dumps({
                'type': 'status_update',
                'data': update_data
            })
            
            # Send to all connected clients
            disconnected_clients = set()
            for websocket in self.websocket_clients:
                try:
                    await websocket.send(message)
                except Exception:
                    disconnected_clients.add(websocket)
            
            # Remove disconnected clients
            for websocket in disconnected_clients:
                self.websocket_clients.discard(websocket)
                
        except Exception as e:
            logger.error(f"Error broadcasting updates: {e}")
    
    async def _cleanup_old_history(self):
        """Clean up old history records"""
        cutoff = datetime.utcnow() - timedelta(hours=self.history_retention_hours)
        
        for connection_id in list(self.status_history.keys()):
            history = self.status_history[connection_id]
            cleaned_history = [
                event for event in history
                if datetime.fromisoformat(event['timestamp']) >= cutoff
            ]
            
            if len(cleaned_history) != len(history):
                self.status_history[connection_id] = cleaned_history
                logger.debug(f"Cleaned {len(history) - len(cleaned_history)} old history records for {connection_id}")
    
    # Event handlers for reconnection events
    async def _handle_connection_lost(self, event_data: Dict[str, Any]):
        """Handle connection lost event"""
        await self._broadcast_event_update('connection_lost', event_data)
    
    async def _handle_reconnection_started(self, event_data: Dict[str, Any]):
        """Handle reconnection started event"""
        await self._broadcast_event_update('reconnection_started', event_data)
    
    async def _handle_reconnection_success(self, event_data: Dict[str, Any]):
        """Handle reconnection success event"""
        await self._broadcast_event_update('reconnection_success', event_data)
    
    async def _handle_reconnection_failed(self, event_data: Dict[str, Any]):
        """Handle reconnection failed event"""
        await self._broadcast_event_update('reconnection_failed', event_data)
    
    async def _broadcast_event_update(self, event_type: str, event_data: Dict[str, Any]):
        """Broadcast specific event to WebSocket clients"""
        if not self.websocket_clients:
            return
        
        message = json.dumps({
            'type': 'event',
            'event_type': event_type,
            'data': event_data
        })
        
        disconnected_clients = set()
        for websocket in self.websocket_clients:
            try:
                await websocket.send(message)
            except Exception:
                disconnected_clients.add(websocket)
        
        # Remove disconnected clients
        for websocket in disconnected_clients:
            self.websocket_clients.discard(websocket)