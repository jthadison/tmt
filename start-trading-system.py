#!/usr/bin/env python3
"""
Complete Trading System Startup Script

Starts all required services for the TMT trading system:
1. Orchestrator (port 8000)
2. Market Analysis (port 8002) 
3. Execution Engine (port 8004)

This script can be used as an alternative to Docker Compose for development.
"""

import asyncio
import subprocess
import sys
import time
import logging
import signal
import os
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("trading_system")

class TradingSystemLauncher:
    """Launches and manages all trading system services"""
    
    def __init__(self):
        self.processes = {}
        self.running = False
        
        # Service configurations
        self.services = {
            "orchestrator": {
                "script": "orchestrator/app/main.py",
                "port": 8000,
                "module": "uvicorn orchestrator.app.main:app --host 0.0.0.0 --port 8000 --reload",
                "cwd": Path.cwd(),
                "env": {
                    "OANDA_API_KEY": os.getenv("OANDA_API_KEY", ""),
                    "OANDA_ACCOUNT_IDS": os.getenv("OANDA_ACCOUNT_IDS", "101-001-21040028-001"),
                    "OANDA_ENVIRONMENT": os.getenv("OANDA_ENVIRONMENT", "practice")
                }
            },
            "market_analysis": {
                "script": "start-market-analysis.py", 
                "port": 8002,
                "module": "python start-market-analysis.py",
                "cwd": Path.cwd(),
                "env": {
                    "OANDA_API_KEY": os.getenv("OANDA_API_KEY", ""),
                    "POLYGON_API_KEY": os.getenv("POLYGON_API_KEY", "")
                }
            },
            "execution_engine": {
                "script": "start-execution-engine.py",
                "port": 8004, 
                "module": "python start-execution-engine.py",
                "cwd": Path.cwd(),
                "env": {
                    "OANDA_API_KEY": os.getenv("OANDA_API_KEY", ""),
                    "OANDA_ACCOUNT_ID": os.getenv("OANDA_ACCOUNT_IDS", "101-001-21040028-001"),
                    "OANDA_ENVIRONMENT": os.getenv("OANDA_ENVIRONMENT", "practice")
                }
            }
        }
    
    async def start_all_services(self):
        """Start all trading system services"""
        logger.info("🚀 Starting TMT Trading System")
        logger.info("=" * 50)
        
        self.running = True
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Start services sequentially with delays
        for service_name, config in self.services.items():
            if not self.running:
                break
                
            logger.info(f"Starting {service_name} on port {config['port']}")
            
            try:
                # Create environment
                env = os.environ.copy()
                env.update(config["env"])
                
                # Start the process
                process = subprocess.Popen(
                    config["module"].split(),
                    cwd=config["cwd"],
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1
                )
                
                self.processes[service_name] = {
                    "process": process,
                    "config": config
                }
                
                logger.info(f"✅ {service_name} started (PID: {process.pid})")
                
                # Wait a bit before starting next service
                await asyncio.sleep(3)
                
            except Exception as e:
                logger.error(f"❌ Failed to start {service_name}: {e}")
                continue
        
        logger.info("=" * 50)
        logger.info("🎯 All services started! System ready for trading.")
        logger.info("")
        logger.info("Service URLs:")
        logger.info("  • Orchestrator:     http://localhost:8000/health")
        logger.info("  • Market Analysis:  http://localhost:8002/health") 
        logger.info("  • Execution Engine: http://localhost:8004/health")
        logger.info("")
        logger.info("Testing URLs:")
        logger.info("  • Integration Test: python test-trading-pipeline.py")
        logger.info("  • Signal Bridge:    python signal_bridge.py")
        logger.info("")
        logger.info("Press Ctrl+C to stop all services")
        
        # Monitor services
        await self.monitor_services()
    
    async def monitor_services(self):
        """Monitor running services and restart if needed"""
        while self.running:
            try:
                # Check if any processes have died
                dead_services = []
                
                for service_name, service_info in self.processes.items():
                    process = service_info["process"]
                    
                    if process.poll() is not None:
                        # Process has died
                        dead_services.append(service_name)
                        logger.warning(f"⚠️ Service {service_name} has stopped (exit code: {process.returncode})")
                        
                        # Read any error output
                        try:
                            stderr_output = process.stderr.read()
                            if stderr_output:
                                logger.error(f"Error output from {service_name}: {stderr_output[:500]}")
                        except:
                            pass
                
                # Remove dead services
                for service_name in dead_services:
                    del self.processes[service_name]
                
                # Wait before next check
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Error in service monitoring: {e}")
                await asyncio.sleep(5)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        
        # Stop all processes
        for service_name, service_info in self.processes.items():
            try:
                process = service_info["process"]
                logger.info(f"Stopping {service_name}...")
                
                # Try graceful shutdown first
                process.terminate()
                
                # Wait a bit for graceful shutdown
                try:
                    process.wait(timeout=5)
                    logger.info(f"✅ {service_name} stopped gracefully")
                except subprocess.TimeoutExpired:
                    # Force kill if needed
                    logger.warning(f"Force killing {service_name}...")
                    process.kill()
                    process.wait()
                    logger.info(f"✅ {service_name} force stopped")
                    
            except Exception as e:
                logger.error(f"Error stopping {service_name}: {e}")
        
        logger.info("👋 Trading system shutdown complete")
        sys.exit(0)
    
    def check_prerequisites(self) -> bool:
        """Check if all prerequisites are available"""
        logger.info("🔍 Checking prerequisites...")
        
        issues = []
        
        # Check Python
        try:
            import uvicorn
            import fastapi
            import aiohttp
            logger.info("  ✅ Python dependencies available")
        except ImportError as e:
            issues.append(f"Missing Python dependency: {e}")
        
        # Check scripts exist
        for service_name, config in self.services.items():
            script_path = Path(config["cwd"]) / config["script"]
            if not script_path.exists() and service_name != "orchestrator":
                issues.append(f"Missing script: {script_path}")
            elif service_name != "orchestrator":
                logger.info(f"  ✅ Found {service_name} script")
        
        # Check orchestrator module
        orchestrator_path = Path("orchestrator/app/main.py")
        if orchestrator_path.exists():
            logger.info("  ✅ Found orchestrator module")
        else:
            issues.append("Missing orchestrator module")
        
        # Check environment variables
        if not os.getenv("OANDA_API_KEY"):
            logger.warning("  ⚠️ OANDA_API_KEY not set (using demo mode)")
        else:
            logger.info("  ✅ OANDA_API_KEY configured")
        
        if issues:
            logger.error("❌ Prerequisites check failed:")
            for issue in issues:
                logger.error(f"  • {issue}")
            return False
        
        logger.info("✅ All prerequisites satisfied")
        return True

async def main():
    """Main entry point"""
    launcher = TradingSystemLauncher()
    
    # Check prerequisites
    if not launcher.check_prerequisites():
        logger.error("Cannot start system due to missing prerequisites")
        return 1
    
    try:
        await launcher.start_all_services()
    except KeyboardInterrupt:
        logger.info("Startup interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"System startup failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))