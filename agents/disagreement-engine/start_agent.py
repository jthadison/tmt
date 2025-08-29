#!/usr/bin/env python3
"""
Disagreement Engine Agent Startup Script
Starts the disagreement engine on the expected port for orchestrator integration
"""

import os
import uvicorn
from app.main import app

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8005"))  # Default port expected by orchestrator
    
    print(f"Starting Disagreement Engine Agent on port {port}")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )