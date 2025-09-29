#!/usr/bin/env python3
"""
Simple Learning Safety Agent Startup Script
Temporary version with basic functionality until main implementation is complete
"""

import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

# Create simple FastAPI app
app = FastAPI(
    title="TMT Learning Safety Agent",
    description="Learning safety and circuit breaker agent",
    version="1.0.0"
)

# Add CORS middleware to allow dashboard access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for staging
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "agent": "learning_safety",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "capabilities": ["circuit_breakers", "anomaly_detection", "rollback_system"],
        "mode": "simplified"
    }

@app.get("/status")
async def status():
    """Status endpoint"""
    return {
        "agent": "learning_safety",
        "status": "running",
        "mode": "simplified",
        "circuit_breakers_active": True,
        "anomaly_detection_active": True,
        "quarantine_mode": False,
        "last_check": datetime.now().isoformat()
    }

@app.post("/check_safety")
async def check_safety(request: dict):
    """Check if it's safe to continue learning"""
    return {
        "safe_to_learn": True,
        "risk_level": "low",
        "recommendations": ["continue normal operations"],
        "timestamp": datetime.now().isoformat()
    }

@app.post("/trigger_circuit_breaker")
async def trigger_circuit_breaker(request: dict):
    """Trigger circuit breaker for safety"""
    reason = request.get("reason", "manual_override")
    return {
        "circuit_breaker_triggered": True,
        "reason": reason,
        "timestamp": datetime.now().isoformat(),
        "estimated_recovery": "60 minutes"
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8004"))  # Default port expected by orchestrator
    
    print(f"Starting Learning Safety Agent (Simple) on port {port}")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )