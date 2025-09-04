#!/usr/bin/env python3
"""
Execution Engine Startup Script
Launches the execution engine service on port 8004
"""

import os
import sys
import subprocess
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("execution_engine")

def main():
    """Start the execution engine"""
    logger.info("Starting Execution Engine on port 8082")
    
    # Set environment variables
    env = os.environ.copy()
    env["PORT"] = "8082"
    
    # Ensure OANDA environment variables are set
    if not env.get("OANDA_API_KEY"):
        env["OANDA_API_KEY"] = os.getenv("OANDA_API_KEY", "")
    if not env.get("OANDA_ACCOUNT_ID"):
        env["OANDA_ACCOUNT_ID"] = os.getenv("OANDA_ACCOUNT_IDS", "101-001-21040028-001")
    if not env.get("OANDA_ENVIRONMENT"):
        env["OANDA_ENVIRONMENT"] = os.getenv("OANDA_ENVIRONMENT", "practice")
    
    # Check if simple_main.py exists in execution-engine directory
    execution_engine_path = "execution-engine/simple_main.py"
    if not os.path.exists(execution_engine_path):
        logger.error(f"Execution engine script not found: {execution_engine_path}")
        return 1
    
    try:
        # Start the execution engine
        # Change to execution-engine directory and run simple_main.py
        process = subprocess.Popen(
            [sys.executable, "simple_main.py"],
            cwd="execution-engine",
            env=env
        )
        
        logger.info(f"Execution Engine started (PID: {process.pid})")
        logger.info("Service URL: http://localhost:8082/health")
        
        # Wait for the process
        process.wait()
        
    except KeyboardInterrupt:
        logger.info("Execution Engine stopped by user")
        return 0
    except Exception as e:
        logger.error(f"Failed to start Execution Engine: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())