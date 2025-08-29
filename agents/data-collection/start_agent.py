#!/usr/bin/env python3
"""
Data Collection Agent Startup Script
Starts the data collection agent on the expected port for orchestrator integration
"""

import os
import uvicorn
from app.main import app

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8006"))  # Default port expected by orchestrator
    
    print(f"Starting Data Collection Agent on port {port}")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )