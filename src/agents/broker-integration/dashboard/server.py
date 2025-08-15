"""
Dashboard Server - Story 8.2 Task 5
Comprehensive dashboard server for account monitoring
"""
import asyncio
import logging
import os
from pathlib import Path
from typing import Optional
from datetime import datetime
import signal
import sys

from aiohttp import web, WSMsgType
from aiohttp.web_static import static

from ..account_manager import OandaAccountManager
from ..instrument_service import OandaInstrumentService
from ..realtime_updates import AccountUpdateService
from ..historical_data import HistoricalDataService
from .account_dashboard import AccountDashboard
from .websocket_handler import DashboardWebSocketHandler

logger = logging.getLogger(__name__)

class DashboardServer:
    """Main dashboard server coordinating all components"""
    
    def __init__(self, 
                 api_key: str,
                 account_id: str,
                 base_url: str = "https://api-fxtrade.oanda.com",
                 http_port: int = 8080,
                 ws_port: int = 8765):
        
        self.api_key = api_key
        self.account_id = account_id
        self.base_url = base_url
        self.http_port = http_port
        self.ws_port = ws_port
        
        # Core components
        self.account_manager: Optional[OandaAccountManager] = None
        self.instrument_service: Optional[OandaInstrumentService] = None
        self.update_service: Optional[AccountUpdateService] = None
        self.historical_service: Optional[HistoricalDataService] = None
        self.dashboard: Optional[AccountDashboard] = None
        self.websocket_handler: Optional[DashboardWebSocketHandler] = None
        
        # Web server
        self.app: Optional[web.Application] = None
        self.http_server = None
        
        # Runtime state
        self.is_running = False
        self.startup_time: Optional[datetime] = None
        
        # Signal handling
        self.shutdown_event = asyncio.Event()
    
    async def initialize(self):
        """Initialize all dashboard components"""
        logger.info("Initializing dashboard server components...")
        
        try:
            # Initialize core services
            self.account_manager = OandaAccountManager(
                api_key=self.api_key,
                account_id=self.account_id,
                base_url=self.base_url
            )
            await self.account_manager.initialize()
            
            self.instrument_service = OandaInstrumentService(
                api_key=self.api_key,
                account_id=self.account_id,
                base_url=self.base_url
            )
            await self.instrument_service.initialize()
            
            self.historical_service = HistoricalDataService(
                account_id=self.account_id
            )
            
            self.update_service = AccountUpdateService(
                account_manager=self.account_manager,
                instrument_service=self.instrument_service,
                update_interval=5  # 5-second updates
            )
            
            # Initialize dashboard
            self.dashboard = AccountDashboard(
                account_manager=self.account_manager,
                instrument_service=self.instrument_service,
                update_service=self.update_service,
                historical_service=self.historical_service
            )
            await self.dashboard.initialize()
            
            # Initialize WebSocket handler
            self.websocket_handler = DashboardWebSocketHandler(
                dashboard=self.dashboard,
                port=self.ws_port
            )
            
            # Initialize web server
            await self._setup_web_server()
            
            logger.info("Dashboard server components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize dashboard server: {e}")
            raise
    
    async def _setup_web_server(self):
        """Setup HTTP web server for serving dashboard"""
        self.app = web.Application()
        
        # Get template directory
        template_dir = Path(__file__).parent / "templates"
        
        # Routes
        self.app.router.add_get('/', self._serve_dashboard)
        self.app.router.add_get('/dashboard', self._serve_dashboard)
        self.app.router.add_get('/health', self._health_check)
        self.app.router.add_get('/metrics', self._get_metrics)
        self.app.router.add_get('/api/summary', self._api_get_summary)
        self.app.router.add_get('/api/widgets', self._api_get_widgets)
        self.app.router.add_get('/api/widget/{widget_id}', self._api_get_widget)
        self.app.router.add_post('/api/refresh', self._api_refresh_dashboard)
        
        # Static files (if needed)
        if template_dir.exists():
            self.app.router.add_static('/static/', template_dir, name='static')
    
    async def _serve_dashboard(self, request):
        """Serve the main dashboard HTML"""
        template_path = Path(__file__).parent / "templates" / "dashboard.html"
        
        if not template_path.exists():
            return web.Response(
                text="Dashboard template not found",
                status=404,
                content_type='text/html'
            )
        
        with open(template_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        return web.Response(
            text=html_content,
            content_type='text/html'
        )
    
    async def _health_check(self, request):
        """Health check endpoint"""
        health_status = {
            'status': 'healthy' if self.is_running else 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'uptime_seconds': (datetime.utcnow() - self.startup_time).total_seconds() if self.startup_time else 0,
            'components': {
                'account_manager': 'initialized' if self.account_manager else 'not_initialized',
                'instrument_service': 'initialized' if self.instrument_service else 'not_initialized',
                'update_service': 'running' if self.update_service and self.update_service.is_running else 'stopped',
                'dashboard': 'initialized' if self.dashboard else 'not_initialized',
                'websocket_handler': 'running' if self.websocket_handler and self.websocket_handler.is_running else 'stopped'
            }
        }
        
        return web.json_response(health_status)
    
    async def _get_metrics(self, request):
        """Get server metrics"""
        metrics = {
            'server': {
                'uptime_seconds': (datetime.utcnow() - self.startup_time).total_seconds() if self.startup_time else 0,
                'is_running': self.is_running
            }
        }
        
        if self.account_manager:
            metrics['account_manager'] = self.account_manager.get_metrics()
        
        if self.instrument_service:
            metrics['instrument_service'] = self.instrument_service.get_metrics()
        
        if self.update_service:
            metrics['update_service'] = self.update_service.get_metrics()
        
        if self.dashboard:
            metrics['dashboard'] = self.dashboard.get_metrics()
        
        if self.websocket_handler:
            metrics['websocket_handler'] = self.websocket_handler.get_metrics()
        
        return web.json_response(metrics)
    
    async def _api_get_summary(self, request):
        """API endpoint for dashboard summary"""
        try:
            if not self.dashboard:
                return web.json_response({'error': 'Dashboard not initialized'}, status=500)
            
            summary = await self.dashboard.get_dashboard_summary()
            return web.json_response(summary)
        
        except Exception as e:
            logger.error(f"Error getting dashboard summary: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def _api_get_widgets(self, request):
        """API endpoint for all widgets"""
        try:
            if not self.dashboard:
                return web.json_response({'error': 'Dashboard not initialized'}, status=500)
            
            widgets = await self.dashboard.get_all_widgets()
            widgets_data = {widget_id: widget.to_dict() for widget_id, widget in widgets.items()}
            
            return web.json_response(widgets_data)
        
        except Exception as e:
            logger.error(f"Error getting widgets: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def _api_get_widget(self, request):
        """API endpoint for specific widget"""
        try:
            widget_id = request.match_info['widget_id']
            
            if not self.dashboard:
                return web.json_response({'error': 'Dashboard not initialized'}, status=500)
            
            widget = await self.dashboard.get_widget(widget_id)
            if not widget:
                return web.json_response({'error': 'Widget not found'}, status=404)
            
            return web.json_response(widget.to_dict())
        
        except Exception as e:
            logger.error(f"Error getting widget: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def _api_refresh_dashboard(self, request):
        """API endpoint to refresh dashboard"""
        try:
            if not self.dashboard:
                return web.json_response({'error': 'Dashboard not initialized'}, status=500)
            
            widgets = await self.dashboard.refresh_all_widgets()
            widgets_data = {widget_id: widget.to_dict() for widget_id, widget in widgets.items()}
            
            return web.json_response({
                'status': 'refreshed',
                'timestamp': datetime.utcnow().isoformat(),
                'widgets': widgets_data
            })
        
        except Exception as e:
            logger.error(f"Error refreshing dashboard: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def start(self):
        """Start the dashboard server"""
        if self.is_running:
            return
        
        logger.info("Starting dashboard server...")
        
        try:
            # Initialize components
            await self.initialize()
            
            # Start WebSocket server
            await self.websocket_handler.start_server()
            
            # Start real-time updates
            await self.update_service.start()
            
            # Start historical data collection
            self.historical_service.start_data_collection()
            
            # Start HTTP server
            runner = web.AppRunner(self.app)
            await runner.setup()
            
            site = web.TCPSite(runner, 'localhost', self.http_port)
            await site.start()
            
            self.http_server = runner
            self.is_running = True
            self.startup_time = datetime.utcnow()
            
            logger.info(f"Dashboard server started successfully!")
            logger.info(f"HTTP Server: http://localhost:{self.http_port}")
            logger.info(f"WebSocket Server: ws://localhost:{self.ws_port}")
            logger.info("Dashboard available at: http://localhost:8080/dashboard")
            
        except Exception as e:
            logger.error(f"Failed to start dashboard server: {e}")
            await self.stop()
            raise
    
    async def stop(self):
        """Stop the dashboard server"""
        if not self.is_running:
            return
        
        logger.info("Stopping dashboard server...")
        
        self.is_running = False
        
        try:
            # Stop historical data collection
            if self.historical_service:
                self.historical_service.stop_data_collection()
            
            # Stop real-time updates
            if self.update_service:
                await self.update_service.stop()
            
            # Stop WebSocket server
            if self.websocket_handler:
                await self.websocket_handler.stop_server()
            
            # Stop HTTP server
            if self.http_server:
                await self.http_server.cleanup()
            
            # Close core services
            if self.instrument_service:
                await self.instrument_service.close()
            
            if self.account_manager:
                await self.account_manager.close()
            
            logger.info("Dashboard server stopped")
            
        except Exception as e:
            logger.error(f"Error stopping dashboard server: {e}")
    
    async def run_forever(self):
        """Run the server until shutdown signal"""
        await self.start()
        
        # Setup signal handlers
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            self.shutdown_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            # Wait for shutdown signal
            await self.shutdown_event.wait()
        finally:
            await self.stop()

async def create_dashboard_server(api_key: str, account_id: str, base_url: str = "https://api-fxtrade.oanda.com") -> DashboardServer:
    """Factory function to create and initialize dashboard server"""
    server = DashboardServer(
        api_key=api_key,
        account_id=account_id,
        base_url=base_url
    )
    
    return server

def main():
    """Main entry point for running dashboard server"""
    import argparse
    
    parser = argparse.ArgumentParser(description='TMT Account Dashboard Server')
    parser.add_argument('--api-key', required=True, help='OANDA API key')
    parser.add_argument('--account-id', required=True, help='OANDA account ID')
    parser.add_argument('--base-url', default='https://api-fxtrade.oanda.com', help='OANDA API base URL')
    parser.add_argument('--http-port', type=int, default=8080, help='HTTP server port')
    parser.add_argument('--ws-port', type=int, default=8765, help='WebSocket server port')
    parser.add_argument('--log-level', default='INFO', help='Logging level')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and run server
    async def run_server():
        server = DashboardServer(
            api_key=args.api_key,
            account_id=args.account_id,
            base_url=args.base_url,
            http_port=args.http_port,
            ws_port=args.ws_port
        )
        
        await server.run_forever()
    
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        logger.info("Dashboard server shutdown by user")
    except Exception as e:
        logger.error(f"Dashboard server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()