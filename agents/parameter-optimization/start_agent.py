#!/usr/bin/env python3
"""
Parameter Optimization Agent Startup Script
Starts the parameter optimization agent on the expected port for orchestrator integration
"""

import os
import uvicorn
from app.main import app

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8003"))  # Default port expected by orchestrator
    
    print(f"Starting Parameter Optimization Agent on port {port}")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )