#!/usr/bin/env python3
"""
TMT Trading System - Infrastructure Restart Script

This script restarts just the infrastructure services (databases, monitoring, etc.)
and then launches the trading services natively.

Usage:
    python restart-infrastructure.py [--force]
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
logger = logging.getLogger("infrastructure_restart")

class InfrastructureManager:
    """Manages infrastructure services and native trading services"""
    
    def __init__(self, force_kill: bool = False):
        self.force_kill = force_kill
        self.compose_file = "docker-compose-simple.yml"
    
    async def restart_infrastructure(self) -> bool:
        """Restart infrastructure services"""
        logger.info("Starting Infrastructure Restart...")
        
        # Stop infrastructure
        if not await self.stop_infrastructure():
            logger.error("Failed to stop infrastructure")
            return False
        
        # Wait for clean shutdown
        logger.info("Waiting for clean shutdown...")
        await asyncio.sleep(5)
        
        # Start infrastructure
        if not await self.start_infrastructure():
            logger.error("Failed to start infrastructure")
            return False
        
        # Wait for services to be ready
        logger.info("Waiting for infrastructure to initialize...")
        await asyncio.sleep(15)
        
        logger.info("Infrastructure restart completed!")
        return True
    
    async def stop_infrastructure(self) -> bool:
        """Stop infrastructure services"""
        logger.info("Stopping infrastructure services...")
        
        try:
            result = subprocess.run(
                ["docker-compose", "-f", self.compose_file, "down", "--remove-orphans"],
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                logger.info("Infrastructure services stopped")
                return True
            else:
                logger.error(f"Infrastructure stop failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error stopping infrastructure: {e}")
            return False
    
    async def start_infrastructure(self) -> bool:
        """Start infrastructure services"""
        logger.info("Starting infrastructure services...")
        
        try:
            result = subprocess.run(
                ["docker-compose", "-f", self.compose_file, "up", "-d"],
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
                timeout=180
            )
            
            if result.returncode == 0:
                logger.info("Infrastructure services started")
                return True
            else:
                logger.error(f"Infrastructure start failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error starting infrastructure: {e}")
            return False
    
    async def start_trading_services(self) -> bool:
        """Start native trading services"""
        logger.info("Starting native trading services...")
        
        # Create environment
        env = os.environ.copy()
        env.update({
            "OANDA_API_KEY": os.getenv("OANDA_API_KEY", ""),
            "OANDA_ACCOUNT_IDS": os.getenv("OANDA_ACCOUNT_IDS", "101-001-21040028-001"),
            "OANDA_ENVIRONMENT": os.getenv("OANDA_ENVIRONMENT", "practice"),
            "DATABASE_URL": os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/trading_system"),
            "REDIS_URL": os.getenv("REDIS_URL", "redis://localhost:6379"),
            "KAFKA_BROKERS": os.getenv("KAFKA_BROKERS", "localhost:9092"),
            # Dashboard environment variables
            "NODE_ENV": "development",
            "NEXT_PUBLIC_API_URL": "http://localhost:8000",
            "NEXT_PUBLIC_OANDA_API_KEY": os.getenv("OANDA_API_KEY", ""),
            "NEXT_PUBLIC_OANDA_ACCOUNT_IDS": os.getenv("OANDA_ACCOUNT_IDS", "101-001-21040028-001"),
            "NEXT_PUBLIC_OANDA_API_URL": "https://api-fxpractice.oanda.com",
            "NEXT_PUBLIC_OANDA_STREAM_URL": "https://stream-fxpractice.oanda.com",
            "NEXT_PUBLIC_OANDA_ENVIRONMENT": os.getenv("OANDA_ENVIRONMENT", "practice")
        })
        
        services = [
            {
                "name": "orchestrator",
                "command": ["python", "-m", "uvicorn", "orchestrator.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
                "cwd": Path.cwd(),
                "delay": 5
            },
            {
                "name": "market_analysis", 
                "command": ["python", "start-market-analysis.py"],
                "cwd": Path.cwd(),
                "delay": 3
            },
            {
                "name": "execution_engine",
                "command": ["python", "start-execution-engine.py"], 
                "cwd": Path.cwd(),
                "delay": 3
            },
            {
                "name": "dashboard",
                "command": ["cmd", "/c", "npm", "run", "dev"],
                "cwd": str(Path.cwd() / "dashboard"),
                "delay": 8
            }
        ]
        
        started_processes = []
        
        try:
            for service in services:
                logger.info(f"Starting {service['name']}...")
                
                try:
                    # Special handling for dashboard on Windows
                    if service["name"] == "dashboard" and sys.platform == "win32":
                        # Verify dashboard directory exists
                        dashboard_path = Path(service["cwd"])
                        if not dashboard_path.exists():
                            logger.error(f"  Dashboard directory not found: {dashboard_path}")
                            continue
                        
                        # Check if package.json exists
                        package_json = dashboard_path / "package.json"
                        if not package_json.exists():
                            logger.error(f"  package.json not found in dashboard directory")
                            continue
                    
                    # Start the process in background
                    process = subprocess.Popen(
                        service["command"],
                        cwd=service["cwd"],
                        env=env,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        shell=(service["name"] == "dashboard" and sys.platform == "win32")
                    )
                    
                    started_processes.append({
                        "name": service["name"],
                        "process": process
                    })
                    
                    logger.info(f"  {service['name']} started (PID: {process.pid})")
                    
                except Exception as e:
                    logger.warning(f"  Failed to start {service['name']}: {e}")
                    if service["name"] == "dashboard":
                        logger.info("  Dashboard can be started manually: cd dashboard && npm run dev")
                    # Continue with other services, don't fail completely
                    continue
                
                # Wait before starting next service
                await asyncio.sleep(service["delay"])
            
            if started_processes:
                logger.info(f"Started {len(started_processes)} native trading services")
                return True
            else:
                logger.error("No services could be started")
                return False
            
        except Exception as e:
            logger.error(f"Failed to start trading services: {e}")
            
            # Clean up any started processes
            for service_info in started_processes:
                try:
                    service_info["process"].terminate()
                    logger.info(f"Cleaned up {service_info['name']}")
                except:
                    pass
            
            return False
    
    async def full_restart(self) -> bool:
        """Full system restart - infrastructure + trading services"""
        logger.info("=" * 60)
        logger.info("TMT Trading System Full Restart")
        logger.info("=" * 60)
        
        # Restart infrastructure
        if not await self.restart_infrastructure():
            return False
        
        # Start native trading services
        if not await self.start_trading_services():
            return False
        
        # Wait a bit more for everything to settle
        logger.info("Final initialization wait...")
        await asyncio.sleep(10)
        
        # Show status
        self.print_system_status()
        
        logger.info("=" * 60)
        logger.info("Full restart completed successfully!")
        return True
    
    def print_system_status(self) -> None:
        """Print current system status"""
        logger.info("")
        logger.info("System Status:")
        logger.info("Infrastructure Services (Docker):")
        logger.info("  • PostgreSQL:       localhost:5432")
        logger.info("  • Redis:            localhost:6379")
        logger.info("  • Kafka:            localhost:9092")
        logger.info("  • Prometheus:       http://localhost:9090")
        logger.info("  • Grafana:          http://localhost:3001 (admin/admin)")
        logger.info("")
        logger.info("Trading Services (Native):")
        logger.info("  • Orchestrator:     http://localhost:8000/health")
        logger.info("  • Market Analysis:  http://localhost:8002/health")
        logger.info("  • Execution Engine: http://localhost:8004/health")
        logger.info("  • Dashboard:        http://localhost:3000")
        logger.info("")
        logger.info("Testing Commands:")
        logger.info("  • Integration Test: python test-trading-pipeline.py")
        logger.info("  • Signal Bridge:    python signal_bridge.py")
        logger.info("  • Infrastructure:   docker-compose -f docker-compose-simple.yml ps")

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="TMT Infrastructure Restart")
    parser.add_argument("--force", action="store_true", 
                       help="Force kill processes if needed")
    parser.add_argument("--infrastructure-only", action="store_true",
                       help="Only restart infrastructure, not trading services")
    
    args = parser.parse_args()
    
    manager = InfrastructureManager(force_kill=args.force)
    
    try:
        if args.infrastructure_only:
            success = await manager.restart_infrastructure()
            if success:
                logger.info("Infrastructure services:")
                logger.info("  • PostgreSQL: localhost:5432")
                logger.info("  • Redis: localhost:6379")
                logger.info("  • Kafka: localhost:9092")
                logger.info("  • Prometheus: http://localhost:9090")
                logger.info("  • Grafana: http://localhost:3001")
        else:
            success = await manager.full_restart()
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        logger.info("Restart interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Restart failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))