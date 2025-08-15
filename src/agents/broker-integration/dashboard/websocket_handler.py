"""
WebSocket Handler for Dashboard Updates
Story 8.2 - Task 5: Real-time WebSocket communication for dashboard
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
import json
import websockets
from websockets.server import WebSocketServerProtocol
from dataclasses import asdict

from .account_dashboard import AccountDashboard, DashboardWidget

logger = logging.getLogger(__name__)

class WebSocketMessage:
    """WebSocket message structure"""
    
    @staticmethod
    def success(message_type: str, data: Any, request_id: Optional[str] = None) -> str:
        """Create success message"""
        return json.dumps({
            'type': message_type,
            'status': 'success',
            'data': data,
            'timestamp': datetime.utcnow().isoformat(),
            'request_id': request_id
        }, default=str)
    
    @staticmethod
    def error(message_type: str, error: str, request_id: Optional[str] = None) -> str:
        """Create error message"""
        return json.dumps({
            'type': message_type,
            'status': 'error',
            'error': error,
            'timestamp': datetime.utcnow().isoformat(),
            'request_id': request_id
        }, default=str)
    
    @staticmethod
    def update(update_type: str, data: Any) -> str:
        """Create update message"""
        return json.dumps({
            'type': 'update',
            'update_type': update_type,
            'data': data,
            'timestamp': datetime.utcnow().isoformat()
        }, default=str)

class DashboardWebSocketHandler:
    """Handles WebSocket connections for dashboard updates"""
    
    def __init__(self, dashboard: AccountDashboard, port: int = 8765):
        self.dashboard = dashboard
        self.port = port
        self.clients: Set[WebSocketServerProtocol] = set()
        self.server = None
        self.is_running = False
        
        # Metrics
        self.metrics = {
            'connected_clients': 0,
            'messages_sent': 0,
            'messages_received': 0,
            'errors': 0,
            'start_time': None
        }
        
        # Subscribe to dashboard updates
        self.dashboard.add_update_callback(self._handle_dashboard_update)
    
    async def start_server(self):
        """Start the WebSocket server"""
        if self.is_running:
            return
        
        logger.info(f"Starting dashboard WebSocket server on port {self.port}")
        
        try:
            self.server = await websockets.serve(
                self._handle_client_connection,
                "localhost",
                self.port,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            )
            
            self.is_running = True
            self.metrics['start_time'] = datetime.utcnow()
            
            logger.info(f"Dashboard WebSocket server started on ws://localhost:{self.port}")
            
        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")
            raise
    
    async def stop_server(self):
        """Stop the WebSocket server"""
        if not self.is_running:
            return
        
        logger.info("Stopping dashboard WebSocket server")
        
        self.is_running = False
        
        # Close all client connections
        if self.clients:
            await asyncio.gather(
                *[client.close() for client in self.clients],
                return_exceptions=True
            )
        
        # Close server
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        logger.info("Dashboard WebSocket server stopped")
    
    async def _handle_client_connection(self, websocket: WebSocketServerProtocol, path: str):
        """Handle new client connection"""
        client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        logger.info(f"New WebSocket client connected: {client_id}")
        
        self.clients.add(websocket)
        self.metrics['connected_clients'] = len(self.clients)
        
        try:
            # Send initial dashboard data
            await self._send_initial_data(websocket)
            
            # Handle incoming messages
            async for message in websocket:
                await self._handle_client_message(websocket, message)
                
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"WebSocket client disconnected: {client_id}")
        except Exception as e:
            logger.error(f"Error handling WebSocket client {client_id}: {e}")
            self.metrics['errors'] += 1
        finally:
            self.clients.discard(websocket)
            self.metrics['connected_clients'] = len(self.clients)
    
    async def _send_initial_data(self, websocket: WebSocketServerProtocol):
        """Send initial dashboard data to new client"""
        try:
            # Get all current widgets
            widgets = await self.dashboard.get_all_widgets()
            
            # Send dashboard summary first
            summary = await self.dashboard.get_dashboard_summary()
            await websocket.send(WebSocketMessage.success(
                'dashboard_summary',
                summary
            ))
            
            # Send all widgets
            widgets_data = {widget_id: widget.to_dict() for widget_id, widget in widgets.items()}
            await websocket.send(WebSocketMessage.success(
                'initial_widgets',
                widgets_data
            ))
            
            self.metrics['messages_sent'] += 2
            
        except Exception as e:
            logger.error(f"Failed to send initial data: {e}")
            await websocket.send(WebSocketMessage.error(
                'initial_data',
                str(e)
            ))
    
    async def _handle_client_message(self, websocket: WebSocketServerProtocol, message: str):
        """Handle incoming message from client"""
        try:
            data = json.loads(message)
            self.metrics['messages_received'] += 1
            
            message_type = data.get('type')
            request_id = data.get('request_id')
            
            if message_type == 'get_widget':
                await self._handle_get_widget(websocket, data, request_id)
            elif message_type == 'get_all_widgets':
                await self._handle_get_all_widgets(websocket, request_id)
            elif message_type == 'refresh_dashboard':
                await self._handle_refresh_dashboard(websocket, request_id)
            elif message_type == 'get_summary':
                await self._handle_get_summary(websocket, request_id)
            elif message_type == 'ping':
                await websocket.send(WebSocketMessage.success('pong', {'timestamp': datetime.utcnow().isoformat()}, request_id))
            else:
                await websocket.send(WebSocketMessage.error(
                    'unknown_message',
                    f"Unknown message type: {message_type}",
                    request_id
                ))
                
        except json.JSONDecodeError:
            await websocket.send(WebSocketMessage.error('parse_error', 'Invalid JSON'))
        except Exception as e:
            logger.error(f"Error handling client message: {e}")
            await websocket.send(WebSocketMessage.error('internal_error', str(e)))
    
    async def _handle_get_widget(self, websocket: WebSocketServerProtocol, data: Dict, request_id: str):
        """Handle get_widget request"""
        widget_id = data.get('widget_id')
        if not widget_id:
            await websocket.send(WebSocketMessage.error(
                'get_widget',
                'widget_id is required',
                request_id
            ))
            return
        
        try:
            widget = await self.dashboard.get_widget(widget_id)
            if widget:
                await websocket.send(WebSocketMessage.success(
                    'widget_data',
                    widget.to_dict(),
                    request_id
                ))
            else:
                await websocket.send(WebSocketMessage.error(
                    'get_widget',
                    f'Widget {widget_id} not found',
                    request_id
                ))
        except Exception as e:
            await websocket.send(WebSocketMessage.error(
                'get_widget',
                str(e),
                request_id
            ))
    
    async def _handle_get_all_widgets(self, websocket: WebSocketServerProtocol, request_id: str):
        """Handle get_all_widgets request"""
        try:
            widgets = await self.dashboard.get_all_widgets()
            widgets_data = {widget_id: widget.to_dict() for widget_id, widget in widgets.items()}
            
            await websocket.send(WebSocketMessage.success(
                'all_widgets',
                widgets_data,
                request_id
            ))
        except Exception as e:
            await websocket.send(WebSocketMessage.error(
                'get_all_widgets',
                str(e),
                request_id
            ))
    
    async def _handle_refresh_dashboard(self, websocket: WebSocketServerProtocol, request_id: str):
        """Handle refresh_dashboard request"""
        try:
            widgets = await self.dashboard.refresh_all_widgets()
            widgets_data = {widget_id: widget.to_dict() for widget_id, widget in widgets.items()}
            
            await websocket.send(WebSocketMessage.success(
                'dashboard_refreshed',
                widgets_data,
                request_id
            ))
        except Exception as e:
            await websocket.send(WebSocketMessage.error(
                'refresh_dashboard',
                str(e),
                request_id
            ))
    
    async def _handle_get_summary(self, websocket: WebSocketServerProtocol, request_id: str):
        """Handle get_summary request"""
        try:
            summary = await self.dashboard.get_dashboard_summary()
            await websocket.send(WebSocketMessage.success(
                'dashboard_summary',
                summary,
                request_id
            ))
        except Exception as e:
            await websocket.send(WebSocketMessage.error(
                'get_summary',
                str(e),
                request_id
            ))
    
    async def _handle_dashboard_update(self, update_type: str, data: Any):
        """Handle updates from dashboard"""
        if not self.clients:
            return
        
        try:
            # Convert widgets to dict format
            if isinstance(data, dict):
                update_data = {}
                for key, value in data.items():
                    if hasattr(value, 'to_dict'):
                        update_data[key] = value.to_dict()
                    else:
                        update_data[key] = value
            else:
                update_data = data
            
            message = WebSocketMessage.update(update_type, update_data)
            
            # Send to all connected clients
            disconnected_clients = []
            for client in self.clients:
                try:
                    await client.send(message)
                    self.metrics['messages_sent'] += 1
                except websockets.exceptions.ConnectionClosed:
                    disconnected_clients.append(client)
                except Exception as e:
                    logger.error(f"Error sending update to client: {e}")
                    disconnected_clients.append(client)
            
            # Remove disconnected clients
            for client in disconnected_clients:
                self.clients.discard(client)
            
            self.metrics['connected_clients'] = len(self.clients)
            
        except Exception as e:
            logger.error(f"Error handling dashboard update: {e}")
            self.metrics['errors'] += 1
    
    async def broadcast_message(self, message_type: str, data: Any):
        """Broadcast message to all connected clients"""
        if not self.clients:
            return
        
        message = WebSocketMessage.success(message_type, data)
        
        disconnected_clients = []
        for client in self.clients:
            try:
                await client.send(message)
                self.metrics['messages_sent'] += 1
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.append(client)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected_clients.append(client)
        
        # Remove disconnected clients
        for client in disconnected_clients:
            self.clients.discard(client)
        
        self.metrics['connected_clients'] = len(self.clients)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get WebSocket handler metrics"""
        return {
            **self.metrics,
            'uptime_seconds': (datetime.utcnow() - self.metrics['start_time']).total_seconds() if self.metrics['start_time'] else 0
        }