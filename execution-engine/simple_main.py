"""
Simplified Execution Engine Starter
Handles missing dependencies gracefully and provides basic functionality.
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional

# Try to load .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    DOTENV_AVAILABLE = True
except ImportError:
    # Fallback: manually read .env file
    DOTENV_AVAILABLE = False
    try:
        if os.path.exists('.env'):
            with open('.env', 'r') as f:
                for line in f:
                    if '=' in line and not line.strip().startswith('#'):
                        key, value = line.strip().split('=', 1)
                        os.environ[key] = value
    except Exception:
        pass

# Try to import dependencies, fallback gracefully if missing
try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    FASTAPI_AVAILABLE = True
except ImportError:
    print("FastAPI not available - running in minimal mode")
    FASTAPI_AVAILABLE = False

try:
    import uvicorn
    UVICORN_AVAILABLE = True
except ImportError:
    print("Uvicorn not available")
    UVICORN_AVAILABLE = False

try:
    import structlog
    STRUCTLOG_AVAILABLE = True
except ImportError:
    print("Structlog not available - using basic logging")
    STRUCTLOG_AVAILABLE = False

# Basic logging setup
if STRUCTLOG_AVAILABLE:
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    logger = structlog.get_logger(__name__)
else:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

class ExecutionEngineState:
    """Simplified execution engine state"""
    
    def __init__(self):
        self.initialized = False
        self.start_time = datetime.now()
        self.oanda_configured = bool(os.getenv("OANDA_API_KEY"))
        self.environment = os.getenv("OANDA_ENVIRONMENT", "practice")
        self.paper_trading_mode = os.getenv("PAPER_TRADING_MODE", "false").lower() == "true"
        self.paper_trading_balance = float(os.getenv("PAPER_TRADING_BALANCE", "100000"))
        
    def get_status(self) -> Dict[str, Any]:
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "service": "execution-engine",
            "status": "running",
            "mode": "simplified" if not FASTAPI_AVAILABLE else "full",
            "uptime_seconds": int(uptime),
            "oanda_configured": self.oanda_configured,
            "environment": self.environment,
            "paper_trading_mode": self.paper_trading_mode,
            "paper_trading_balance": self.paper_trading_balance,
            "dependencies": {
                "fastapi": FASTAPI_AVAILABLE,
                "uvicorn": UVICORN_AVAILABLE,
                "structlog": STRUCTLOG_AVAILABLE,
                "dotenv": DOTENV_AVAILABLE
            },
            "timestamp": datetime.now().isoformat()
        }

# Global state
app_state = ExecutionEngineState()

if FASTAPI_AVAILABLE:
    # Full FastAPI application
    app = FastAPI(
        title="TMT Execution Engine",
        description="High-performance execution engine for automated trading",
        version="1.0.0"
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return JSONResponse(content=app_state.get_status())
    
    @app.get("/status")
    async def status():
        """Detailed status endpoint"""
        return JSONResponse(content=app_state.get_status())
    
    @app.get("/")
    async def root():
        """Root endpoint"""
        return {"message": "TMT Execution Engine - Simplified Mode", "status": "running"}
    
    @app.post("/orders/market")
    async def create_market_order(order_data: dict):
        """Paper trading market order endpoint"""
        logger.info("Paper trading order received", order_data=order_data)
        
        if app_state.paper_trading_mode:
            # Paper trading mode - simulate order
            order_id = f"paper_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
            
            return {
                "success": True,
                "mode": "paper_trading",
                "order_id": order_id,
                "status": "filled",
                "fill_price": order_data.get("price", 1.0000),
                "message": "Paper trading order simulated",
                "order_data": order_data,
                "paper_trading_balance": app_state.paper_trading_balance
            }
        else:
            # Live trading mode - would connect to OANDA
            return {
                "success": False,
                "mode": "live",
                "message": "Live trading not implemented - use paper trading mode",
                "order_data": order_data
            }
    
    @app.get("/positions")
    async def get_positions():
        """Mock positions endpoint"""
        return {
            "positions": [],
            "mode": "mock",
            "message": "No positions - execution engine in simplified mode"
        }

def run_http_server():
    """Run a simple HTTP server if FastAPI is not available"""
    import http.server
    import socketserver
    from urllib.parse import urlparse, parse_qs
    
    class SimpleHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            parsed_path = urlparse(self.path)
            
            if parsed_path.path in ['/health', '/status']:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = json.dumps(app_state.get_status())
                self.wfile.write(response.encode())
            
            elif parsed_path.path == '/':
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = json.dumps({
                    "message": "TMT Execution Engine - Minimal Mode",
                    "status": "running",
                    "note": "FastAPI not available - using basic HTTP server"
                })
                self.wfile.write(response.encode())
            
            else:
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = json.dumps({"error": "Not found"})
                self.wfile.write(response.encode())
        
        def log_message(self, format, *args):
            # Suppress default logging
            pass
    
    PORT = 8082
    print(f"Starting minimal HTTP server on port {PORT}")
    print("Available endpoints:")
    print(f"  http://localhost:{PORT}/")
    print(f"  http://localhost:{PORT}/health")
    print(f"  http://localhost:{PORT}/status")
    
    with socketserver.TCPServer(("", PORT), SimpleHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped")

def main():
    """Main entry point"""
    logger.info("Starting TMT Execution Engine")
    
    app_state.initialized = True
    
    if FASTAPI_AVAILABLE and UVICORN_AVAILABLE:
        logger.info("Starting with FastAPI and Uvicorn")
        uvicorn.run(
            "simple_main:app",
            host="0.0.0.0",
            port=8082,
            reload=False,
            log_level="info"
        )
    else:
        logger.info("Starting with minimal HTTP server")
        run_http_server()

if __name__ == "__main__":
    main()