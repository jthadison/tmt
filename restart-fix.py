#!/usr/bin/env python3
"""
Simple restart script fix for TMT Trading System
"""

import asyncio
import subprocess
import sys
import logging
import os
import argparse
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("restart")

async def stop_docker_services():
    """Stop Docker services"""
    logger.info("Stopping Docker services...")
    try:
        result = subprocess.run(
            ["docker-compose", "down", "--remove-orphans"],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            logger.info("Docker services stopped")
            return True
        else:
            logger.error(f"Docker stop failed: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Error: {e}")
        return False

async def start_docker_services():
    """Start Docker services"""
    logger.info("Starting Docker services...")
    try:
        result = subprocess.run(
            ["docker-compose", "up", "-d", "--build"],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            logger.info("Docker services started")
            return True
        else:
            logger.error(f"Docker start failed: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Error: {e}")
        return False

async def restart_docker():
    """Restart Docker services"""
    logger.info("Docker Restart Starting...")
    
    # Stop
    if not await stop_docker_services():
        logger.error("Failed to stop services")
        return False
    
    # Wait
    logger.info("Waiting for clean shutdown...")
    await asyncio.sleep(5)
    
    # Start
    if not await start_docker_services():
        logger.error("Failed to start services")
        return False
    
    # Wait for startup
    logger.info("Waiting for services to initialize...")
    await asyncio.sleep(30)
    
    logger.info("Docker restart completed!")
    logger.info("")
    logger.info("Service URLs:")
    logger.info("  Orchestrator:     http://localhost:8000/health")
    logger.info("  Market Analysis:  http://localhost:8002/health")
    logger.info("  Execution Engine: http://localhost:8004/health")
    logger.info("  Dashboard:        http://localhost:3000")
    logger.info("  Grafana:          http://localhost:3001")
    logger.info("  Prometheus:       http://localhost:9090")
    
    return True

async def main():
    parser = argparse.ArgumentParser(description="Simple TMT Restart")
    parser.add_argument("--mode", choices=["docker"], default="docker",
                       help="Only Docker mode supported in this version")
    
    args = parser.parse_args()
    
    if args.mode == "docker":
        success = await restart_docker()
    else:
        logger.error("Only Docker mode supported")
        return 1
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))