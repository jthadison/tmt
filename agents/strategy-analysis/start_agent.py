#!/usr/bin/env python3
"""
Strategy Analysis Agent Startup Script
Starts the strategy analysis agent on the expected port for orchestrator integration
"""

import os
import sys
from pathlib import Path

# Add the root directory and src directory to Python path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(root_dir / "src"))

import uvicorn
from app.main import app

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8002"))  # Default port expected by orchestrator
    
    print(f"Starting Strategy Analysis Agent on port {port}")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )