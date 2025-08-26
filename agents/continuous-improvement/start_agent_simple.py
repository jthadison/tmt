#!/usr/bin/env python3
"""
Simple Continuous Improvement Agent Startup Script
Temporary version with basic functionality until import issues are resolved
"""

import os
import uvicorn
from fastapi import FastAPI
from datetime import datetime

# Create simple FastAPI app
app = FastAPI(
    title="TMT Continuous Improvement Agent",
    description="Continuous improvement and optimization agent",
    version="1.0.0"
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "agent": "continuous_improvement",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "capabilities": ["improvement_testing", "gradual_rollout", "performance_analysis"],
        "mode": "simplified"
    }

@app.get("/status")
async def status():
    """Status endpoint"""
    return {
        "agent": "continuous_improvement",
        "status": "running",
        "mode": "simplified",
        "active_tests": 0,
        "pending_improvements": 0,
        "completed_tests": 0,
        "last_update": datetime.now().isoformat()
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8007"))  # Default port expected by orchestrator
    
    print(f"Starting Continuous Improvement Agent (Simple) on port {port}")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )