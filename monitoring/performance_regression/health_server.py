"""
Simple health check HTTP server for regression detection service
"""

import asyncio
import json
from datetime import datetime
from aiohttp import web
import logging

logger = logging.getLogger(__name__)


class HealthServer:
    def __init__(self, port: int = 8080):
        self.port = port
        self.app = web.Application()
        self.setup_routes()
        self.last_check_time = None
        self.status = "starting"
    
    def setup_routes(self):
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_get('/status', self.detailed_status)
        self.app.router.add_get('/metrics', self.metrics)
    
    async def health_check(self, request):
        """Simple health check endpoint"""
        if self.status == "healthy":
            return web.json_response({"status": "healthy", "timestamp": datetime.utcnow().isoformat()})
        else:
            return web.json_response(
                {"status": self.status, "timestamp": datetime.utcnow().isoformat()},
                status=503
            )
    
    async def detailed_status(self, request):
        """Detailed status information"""
        return web.json_response({
            "status": self.status,
            "last_check": self.last_check_time.isoformat() if self.last_check_time else None,
            "uptime": self.get_uptime(),
            "service": "performance-regression-detector",
            "version": "1.0.0"
        })
    
    async def metrics(self, request):
        """Prometheus-compatible metrics endpoint"""
        metrics = [
            f'regression_detector_status{{status="{self.status}"}} 1',
            f'regression_detector_last_check_timestamp {self.last_check_time.timestamp() if self.last_check_time else 0}',
            f'regression_detector_uptime_seconds {self.get_uptime()}'
        ]
        
        return web.Response(text='\n'.join(metrics), content_type='text/plain')
    
    def get_uptime(self):
        """Calculate uptime in seconds"""
        if hasattr(self, 'start_time'):
            return (datetime.utcnow() - self.start_time).total_seconds()
        return 0
    
    def update_status(self, status: str, last_check_time: datetime = None):
        """Update service status"""
        self.status = status
        if last_check_time:
            self.last_check_time = last_check_time
    
    async def start_server(self):
        """Start the health server"""
        self.start_time = datetime.utcnow()
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()
        logger.info(f"Health server started on port {self.port}")


# Global health server instance
health_server = HealthServer()


async def start_health_server():
    """Start health server in background"""
    await health_server.start_server()


def update_health_status(status: str, last_check_time: datetime = None):
    """Update health status"""
    health_server.update_status(status, last_check_time)


if __name__ == "__main__":
    # Run standalone health server
    asyncio.run(start_health_server())
    
    # Keep running
    try:
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        logger.info("Health server stopped")