#!/usr/bin/env python3
"""
Market Analysis Agent - FastAPI Service
Provides real-time market analysis and signal generation
"""

import os
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .market_state_agent import MarketStateAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("market_analysis_service")

# Initialize FastAPI app
app = FastAPI(
    title="TMT Market Analysis Service",
    description="Real-time market analysis and signal generation for trading system",
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

# Global market analysis agent
market_agent = None

@app.on_event("startup")
async def startup_event():
    """Initialize market analysis agent on startup"""
    global market_agent
    
    logger.info("🚀 Starting Market Analysis Service")
    
    # Initialize market state agent
    market_agent = MarketStateAgent()
    
    # Start market monitoring in background
    asyncio.create_task(market_agent.start_monitoring())
    
    logger.info("✅ Market Analysis Service ready")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        if market_agent is None:
            return {
                "status": "starting",
                "timestamp": datetime.now().isoformat(),
                "market_data_connected": False,
                "subscribed_instruments": [],
                "last_price_update": None,
                "total_signals": 0
            }
        
        # Get real status from market agent
        connected = getattr(market_agent, 'connected', False)
        signal_count = getattr(market_agent, 'signal_count', 0)
        
        market_data = getattr(market_agent, 'market_data', {})
        instruments = list(market_data.get('prices', {}).keys()) if market_data else []
        last_update = market_data.get('timestamp') if market_data else None
        
        status = "healthy" if connected else "degraded"
        
        return {
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": int((datetime.now() - datetime.now()).total_seconds()) if connected else 0,
            "market_data_connected": connected,
            "subscribed_instruments": instruments,
            "last_price_update": last_update.isoformat() if last_update else None,
            "total_signals": signal_count,
            "oanda_configured": bool(os.getenv("OANDA_API_KEY")),
            "market_state": getattr(market_agent, 'current_state', 'unknown')
        }
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "market_data_connected": False,
            "subscribed_instruments": [],
            "last_price_update": None,
            "total_signals": 0
        }

@app.get("/market-data")
async def get_market_data():
    """Get current market data"""
    try:
        if market_agent is None or not hasattr(market_agent, 'market_data'):
            raise HTTPException(status_code=503, detail="Market data not available")
        
        return market_agent.market_data
        
    except Exception as e:
        logger.error(f"Market data error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/market-state")
async def get_market_state():
    """Get current market state analysis"""
    try:
        if market_agent is None:
            raise HTTPException(status_code=503, detail="Market agent not available")
        
        return {
            "current_state": getattr(market_agent, 'current_state', 'unknown'),
            "timestamp": datetime.now().isoformat(),
            "confidence": 0.8,  # Basic confidence for real-time analysis
            "analysis": getattr(market_agent, 'market_data', {}).get('volatility_analysis', {})
        }
        
    except Exception as e:
        logger.error(f"Market state error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze/{instrument}")
async def analyze_instrument(instrument: str):
    """Analyze specific instrument"""
    try:
        if market_agent is None:
            raise HTTPException(status_code=503, detail="Market agent not available")
        
        # Get instrument data
        market_data = getattr(market_agent, 'market_data', {})
        prices = market_data.get('prices', {})
        
        if instrument not in prices:
            raise HTTPException(status_code=404, detail=f"Instrument {instrument} not found")
        
        price_data = prices[instrument]
        spread = market_data.get('spreads', {}).get(instrument, 0)
        
        return {
            "instrument": instrument,
            "analysis": {
                "current_price": price_data['mid'],
                "bid": price_data['bid'],
                "ask": price_data['ask'],
                "spread": spread,
                "spread_pips": (spread / price_data['mid']) * 10000,
                "market_state": market_data.get('market_state', 'unknown'),
                "execution_quality": "good" if spread < price_data['mid'] * 0.0002 else "fair",
                "timestamp": price_data['time']
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis error for {instrument}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/instruments")
async def get_supported_instruments():
    """Get list of supported instruments"""
    return {
        "instruments": ["EUR_USD", "GBP_USD", "USD_JPY", "USD_CHF", "AUD_USD", "NZD_USD", "USD_CAD"],
        "total": 7,
        "actively_monitored": len(getattr(market_agent, 'market_data', {}).get('prices', {}))
    }

@app.post("/emergency-stop")
async def emergency_stop():
    """Emergency stop market analysis"""
    try:
        logger.critical("🚨 Emergency stop requested for market analysis")
        
        if market_agent:
            market_agent.connected = False
            
        return {
            "status": "stopped",
            "timestamp": datetime.now().isoformat(),
            "message": "Market analysis emergency stopped"
        }
        
    except Exception as e:
        logger.error(f"Emergency stop error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8002,
        reload=True,
        log_level="info"
    )