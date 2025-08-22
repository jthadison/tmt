#!/usr/bin/env python3
"""
Execution Engine Startup Script
Starts the execution engine service on port 8004
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Add execution engine to Python path
execution_engine_path = Path(__file__).parent / "execution-engine"
sys.path.insert(0, str(execution_engine_path))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("execution_engine_startup")

async def main():
    """Start the execution engine"""
    logger.info("🚀 Starting Execution Engine on port 8004")
    
    try:
        # Import execution engine main module
        from app.main import app
        import uvicorn
        
        # Configure for development
        config = uvicorn.Config(
            app,
            host="0.0.0.0",
            port=8004,
            log_level="info",
            reload=False,  # Set to True for development
            access_log=True
        )
        
        server = uvicorn.Server(config)
        logger.info("✅ Execution Engine starting on http://localhost:8004")
        await server.serve()
        
    except ImportError as e:
        logger.error(f"❌ Failed to import execution engine: {e}")
        logger.error("Make sure you're in the correct directory and dependencies are installed")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Failed to start execution engine: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Execution Engine shutdown complete")