#!/usr/bin/env python3
"""
TMT Trading System - Core Services Restart (without dashboard)

Starts infrastructure + core trading services only.
Dashboard must be started separately if needed.
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
logger = logging.getLogger("core_services")

async def restart_core_services():
    """Restart core services without dashboard"""
    logger.info("=" * 60)
    logger.info("TMT Core Services Restart (No Dashboard)")
    logger.info("=" * 60)
    
    # 1. Stop infrastructure
    logger.info("Stopping infrastructure...")
    try:
        result = subprocess.run(
            ["docker-compose", "-f", "docker-compose-simple.yml", "down", "--remove-orphans"],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            logger.info("Infrastructure stopped")
        else:
            logger.error(f"Infrastructure stop failed: {result.stderr}")
    except Exception as e:
        logger.error(f"Error stopping infrastructure: {e}")
    
    await asyncio.sleep(3)
    
    # 2. Start infrastructure
    logger.info("Starting infrastructure...")
    try:
        result = subprocess.run(
            ["docker-compose", "-f", "docker-compose-simple.yml", "up", "-d"],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
            timeout=180
        )
        if result.returncode == 0:
            logger.info("Infrastructure started")
        else:
            logger.error(f"Infrastructure start failed: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Error starting infrastructure: {e}")
        return False
    
    await asyncio.sleep(15)
    
    # 3. Start trading services
    logger.info("Starting core trading services...")
    
    env = os.environ.copy()
    env.update({
        "OANDA_API_KEY": os.getenv("OANDA_API_KEY", ""),
        "OANDA_ACCOUNT_IDS": os.getenv("OANDA_ACCOUNT_IDS", "101-001-21040028-001"),
        "OANDA_ENVIRONMENT": os.getenv("OANDA_ENVIRONMENT", "practice"),
        "DATABASE_URL": "postgresql://postgres:password@localhost:5432/trading_system",
        "REDIS_URL": "redis://localhost:6379",
        "KAFKA_BROKERS": "localhost:9092"
    })
    
    services = [
        {
            "name": "orchestrator",
            "command": ["python", "-m", "uvicorn", "orchestrator.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
        },
        {
            "name": "market_analysis", 
            "command": ["python", "start-market-analysis.py"],
        },
        {
            "name": "execution_engine",
            "command": ["python", "start-execution-engine.py"], 
        }
    ]
    
    started_services = []
    
    for i, service in enumerate(services):
        logger.info(f"Starting {service['name']}...")
        
        try:
            process = subprocess.Popen(
                service["command"],
                cwd=Path.cwd(),
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            started_services.append(service['name'])
            logger.info(f"  {service['name']} started (PID: {process.pid})")
            
            # Wait between services
            if i < len(services) - 1:
                await asyncio.sleep(5)
                
        except Exception as e:
            logger.warning(f"  Failed to start {service['name']}: {e}")
    
    logger.info("=" * 60)
    logger.info("Core Services Status:")
    logger.info("")
    logger.info("Infrastructure (Docker):")
    logger.info("  • PostgreSQL:       localhost:5432")
    logger.info("  • Redis:            localhost:6379")
    logger.info("  • Kafka:            localhost:9092")
    logger.info("  • Prometheus:       http://localhost:9090")
    logger.info("  • Grafana:          http://localhost:3001 (admin/admin)")
    logger.info("")
    logger.info("Trading Services (Native):")
    for service in started_services:
        if service == "orchestrator":
            logger.info("  • Orchestrator:     http://localhost:8000/health")
        elif service == "market_analysis":
            logger.info("  • Market Analysis:  http://localhost:8002/health")
        elif service == "execution_engine":
            logger.info("  • Execution Engine: http://localhost:8004/health")
    logger.info("")
    logger.info("Dashboard:")
    logger.info("  • To start dashboard: cd dashboard && npm run dev")
    logger.info("  • Dashboard URL:      http://localhost:3000")
    logger.info("=" * 60)
    
    return True

async def main():
    success = await restart_core_services()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))