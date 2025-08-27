#!/usr/bin/env python3
"""
Simple Market Analysis Agent - Minimal Health Service
Provides health endpoint for dashboard integration
"""

import os
import logging
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("market_analysis_simple")

# Initialize FastAPI app
app = FastAPI(
    title="Market Analysis Agent",
    description="Market Analysis and Signal Generation Service",
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

@app.on_event("startup")
async def startup_event():
    logger.info("Starting Market Analysis Agent (Simple Mode)")
    logger.info("Market analysis capabilities initialized")

@app.get("/health")
async def health_check():
    """Health check endpoint for service monitoring"""
    return {
        "status": "healthy",
        "agent": "market_analysis",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "capabilities": [
            "market_scanning",
            "signal_generation", 
            "trend_analysis",
            "volume_analysis"
        ],
        "mode": "simplified"
    }

@app.get("/status")
async def get_status():
    """Get detailed agent status"""
    return {
        "agent_id": "market_analysis_001",
        "status": "active",
        "last_scan": datetime.now().isoformat(),
        "markets_monitored": ["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD"],
        "signals_generated_today": 0,
        "mode": "simplified"
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Market Analysis Agent",
        "status": "running",
        "endpoints": ["/health", "/status"]
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    logger.info(f"Starting Market Analysis Agent on port {port}")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )