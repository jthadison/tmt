#!/usr/bin/env python3
"""
Market Analysis Agent Startup Script
Starts the market analysis service on port 8002
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Add market analysis to Python path
market_analysis_path = Path(__file__).parent / "agents" / "market-analysis"
sys.path.insert(0, str(market_analysis_path))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("market_analysis_startup")

async def main():
    """Start the market analysis agent"""
    port = int(os.getenv("PORT", "8001"))
    logger.info(f"🚀 Starting Market Analysis Agent on port {port}")
    
    try:
        # Check if main.py exists in market analysis
        main_py_path = market_analysis_path / "app" / "main.py"
        if not main_py_path.exists():
            logger.warning("⚠️ Market Analysis main.py not found, creating simple FastAPI server")
            await create_simple_market_analysis_server(port)
        else:
            # Import and start existing market analysis
            from app.main import app
            import uvicorn
            
            config = uvicorn.Config(
                app,
                host="0.0.0.0", 
                port=port,
                log_level="info",
                reload=False,
                access_log=True
            )
            
            server = uvicorn.Server(config)
            logger.info(f"✅ Market Analysis Agent starting on http://localhost:{port}")
            await server.serve()
        
    except ImportError as e:
        logger.warning(f"⚠️ Failed to import market analysis app: {e}")
        logger.info("Creating simple market analysis server for testing...")
        await create_simple_market_analysis_server(port)
    except Exception as e:
        logger.error(f"❌ Failed to start market analysis: {e}")
        sys.exit(1)

async def create_simple_market_analysis_server(port=8001):
    """Create a simple FastAPI server for market analysis testing"""
    try:
        from fastapi import FastAPI
        from fastapi.responses import JSONResponse
        import uvicorn
        from datetime import datetime
        import random
        
        app = FastAPI(title="Market Analysis Agent", version="1.0.0")
        
        @app.get("/health")
        async def health():
            return {"status": "healthy", "service": "market_analysis", "port": port}
        
        @app.get("/api/market-overview")
        async def market_overview():
            """Provide sample market data for testing"""
            return {
                "status": "success",
                "data": {
                    "major_pairs": [
                        {
                            "symbol": "EUR_USD",
                            "price": round(1.0500 + random.uniform(-0.01, 0.01), 5),
                            "change_24h": round(random.uniform(-0.02, 0.02), 4),
                            "volatility": round(random.uniform(0.005, 0.03), 4),
                            "trend": random.choice(["bullish", "bearish", "neutral"]),
                            "last_updated": datetime.now().isoformat()
                        },
                        {
                            "symbol": "GBP_USD", 
                            "price": round(1.2500 + random.uniform(-0.01, 0.01), 5),
                            "change_24h": round(random.uniform(-0.02, 0.02), 4),
                            "volatility": round(random.uniform(0.005, 0.03), 4),
                            "trend": random.choice(["bullish", "bearish", "neutral"]),
                            "last_updated": datetime.now().isoformat()
                        },
                        {
                            "symbol": "USD_JPY",
                            "price": round(150.00 + random.uniform(-2, 2), 3),
                            "change_24h": round(random.uniform(-0.02, 0.02), 4),
                            "volatility": round(random.uniform(0.005, 0.03), 4),
                            "trend": random.choice(["bullish", "bearish", "neutral"]),
                            "last_updated": datetime.now().isoformat()
                        }
                    ],
                    "market_state": "active",
                    "timestamp": datetime.now().isoformat()
                }
            }
        
        @app.get("/api/signals/{instrument}")
        async def generate_signal(instrument: str):
            """Generate a sample trading signal"""
            confidence = round(random.uniform(0.6, 0.95), 2)
            
            if confidence > 0.75:  # Only generate signals above 75% confidence
                direction = random.choice(["long", "short"])
                base_price = 1.0500 if instrument == "EUR_USD" else (1.2500 if instrument == "GBP_USD" else 150.0)
                current_price = base_price + random.uniform(-0.01, 0.01)
                
                if direction == "long":
                    entry_price = current_price
                    stop_loss = current_price * 0.995
                    take_profit = current_price * 1.015
                else:
                    entry_price = current_price
                    stop_loss = current_price * 1.005
                    take_profit = current_price * 0.985
                
                return {
                    "signal": {
                        "id": f"ma_signal_{instrument}_{int(datetime.now().timestamp())}",
                        "instrument": instrument,
                        "direction": direction,
                        "confidence": confidence,
                        "entry_price": round(entry_price, 5),
                        "stop_loss": round(stop_loss, 5),
                        "take_profit": round(take_profit, 5),
                        "timestamp": datetime.now().isoformat(),
                        "analysis_source": "market_analysis_agent"
                    }
                }
            else:
                return {"signal": None, "reason": "Low confidence"}
        
        # Start the server
        config = uvicorn.Config(
            app,
            host="0.0.0.0",
            port=port,
            log_level="info",
            reload=False,
            access_log=True
        )
        
        server = uvicorn.Server(config)
        logger.info(f"✅ Simple Market Analysis Server starting on http://localhost:{port}")
        await server.serve()
        
    except Exception as e:
        logger.error(f"❌ Failed to create simple market analysis server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Market Analysis Agent shutdown complete")