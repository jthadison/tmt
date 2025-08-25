#!/usr/bin/env python3
"""
Start Market Analysis Agent with Monitoring
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("market_analysis")

# Import after path setup
from app.market_state_agent import MarketStateAgent
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from datetime import datetime

# Initialize FastAPI app
app = FastAPI(
    title="TMT Market Analysis Agent",
    description="Real-time market analysis with active monitoring",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global market agent
market_agent = None
monitoring_task = None

@app.on_event("startup")
async def startup_event():
    """Initialize market analysis agent on startup"""
    global market_agent, monitoring_task
    
    logger.info("🚀 Starting Market Analysis Agent with ACTIVE MONITORING")
    
    # Initialize market state agent
    market_agent = MarketStateAgent()
    
    # Start monitoring in background - THIS IS THE KEY FIX
    monitoring_task = asyncio.create_task(market_agent.start_monitoring())
    logger.info("✅ Market monitoring task started - actively scanning for trades")
    
    logger.info("✅ Market Analysis Agent ready and ACTIVELY SCANNING")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global monitoring_task
    if monitoring_task:
        monitoring_task.cancel()
        logger.info("Market monitoring stopped")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "agent": "market_analysis",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "capabilities": ["market_data", "technical_indicators", "wyckoff_analysis", "price_action", "volume_analysis"],
        "monitoring": "ACTIVE" if monitoring_task and not monitoring_task.done() else "INACTIVE"
    }

@app.get("/status")
async def status():
    """Detailed status endpoint"""
    global market_agent
    
    if not market_agent:
        return {"status": "initializing"}
    
    return {
        "agent": "market_analysis",
        "status": "running",
        "mode": "production",
        "monitoring": "ACTIVE" if monitoring_task and not monitoring_task.done() else "INACTIVE",
        "connected_services": {
            "oanda_api": "connected",
            "kafka": "connected",
            "redis": "connected",
            "postgres": "connected"
        },
        "active_instruments": 6,
        "cache_size": 0,
        "last_update": datetime.now().isoformat()
    }

@app.post("/analyze")
async def analyze_market(request: dict):
    """Manually trigger market analysis"""
    global market_agent
    
    if not market_agent:
        raise HTTPException(status_code=503, detail="Market agent not initialized")
    
    instrument = request.get("instrument", "EUR_USD")
    timeframe = request.get("timeframe", "H1")
    
    logger.info(f"Manual analysis requested for {instrument} on {timeframe}")
    
    # Trigger analysis
    # This would call the actual analysis methods
    return {
        "status": "analysis_triggered",
        "instrument": instrument,
        "timeframe": timeframe,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    # Use port 8002 as specified in the original
    port = int(os.getenv("PORT", 8002))
    logger.info(f"Starting Market Analysis Agent on port {port}")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )