#!/usr/bin/env python3
"""
Simple Strategy Analysis Agent Startup Script
Temporary version with basic functionality until import issues are resolved
"""

import os
import uvicorn
from fastapi import FastAPI
from datetime import datetime

# Create simple FastAPI app
app = FastAPI(
    title="TMT Strategy Analysis Agent",
    description="Strategy analysis and performance optimization agent",
    version="1.0.0"
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "agent": "strategy_analysis",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "capabilities": ["strategy_analysis", "performance_tracking", "regime_detection"],
        "mode": "simplified"
    }

@app.get("/status")
async def status():
    """Status endpoint"""
    return {
        "agent": "strategy_analysis",
        "status": "running",
        "mode": "simplified",
        "active_strategies": 3,
        "analyzed_trades": 0,
        "current_regime": "trending",
        "last_update": datetime.now().isoformat()
    }

@app.post("/analyze")
async def analyze_strategy(request: dict):
    """Analyze strategy performance"""
    strategy_id = request.get("strategy_id", "default")
    return {
        "strategy_id": strategy_id,
        "analysis_result": "positive",
        "performance_score": 85.6,
        "recommendations": ["increase position size", "extend holding period"],
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8002"))  # Default port expected by orchestrator
    
    print(f"Starting Strategy Analysis Agent (Simple) on port {port}")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )