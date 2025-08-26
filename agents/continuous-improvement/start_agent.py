#!/usr/bin/env python3
"""
Continuous Improvement Agent Startup Script
Starts the continuous improvement agent on the expected port for orchestrator integration
"""

import os
import uvicorn
from app.main import app

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8007"))  # Default port expected by orchestrator
    
    print(f"Starting Continuous Improvement Agent on port {port}")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )