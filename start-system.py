#!/usr/bin/env python3
"""
Trading System Startup Script
Automatically starts all required services for full paper trading on OANDA
"""

import os
import sys
import time
import signal
import asyncio
import subprocess
from pathlib import Path
import logging
from typing import List, Dict
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_system.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TradingSystemManager:
    """Manages the startup and lifecycle of all trading system services"""
    
    def __init__(self):
        self.processes: Dict[str, subprocess.Popen] = {}
        self.running = False
        self.project_root = Path(__file__).parent
        
        # Service configuration
        self.services = [
            {
                "name": "orchestrator",
                "description": "Main orchestrator service",
                "path": self.project_root / "orchestrator",
                "command": [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
                "port": 8000,
                "health_endpoint": "http://localhost:8000/health",
                "critical": True
            },
            {
                "name": "market-analysis",
                "description": "Market analysis and signal generation agent",
                "path": self.project_root / "agents" / "market-analysis",
                "command": [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"],
                "port": 8001,
                "health_endpoint": "http://localhost:8001/health",
                "critical": True
            }
        ]
    
    def check_prerequisites(self) -> bool:
        """Check if all prerequisites are met"""
        logger.info("Checking system prerequisites...")
        
        # Check environment file
        env_file = self.project_root / ".env"
        if not env_file.exists():
            logger.error("No .env file found! Please configure your OANDA credentials.")
            return False
        
        # Load and validate environment variables
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
            
            required_vars = [
                "OANDA_API_KEY",
                "OANDA_ACCOUNT_ID",
                "OANDA_ENVIRONMENT"
            ]
            
            missing_vars = []
            for var in required_vars:
                if not os.getenv(var):
                    missing_vars.append(var)
            
            if missing_vars:
                logger.error(f"Missing required environment variables: {missing_vars}")
                return False
            
            logger.info("Environment configuration validated")
            
        except ImportError:
            logger.error("python-dotenv package not installed. Run: pip install python-dotenv")
            return False
        except Exception as e:
            logger.error(f"Error loading environment: {e}")
            return False
        
        logger.info("All prerequisites satisfied")
        return True
    
    async def test_oanda_connection(self) -> bool:
        """Test OANDA connection before starting services"""
        logger.info("Testing OANDA connection...")
        
        try:
            import aiohttp
            from dotenv import load_dotenv
            
            load_dotenv()
            
            api_key = os.getenv("OANDA_API_KEY")
            account_id = os.getenv("OANDA_ACCOUNT_ID")
            environment = os.getenv("OANDA_ENVIRONMENT", "practice")
            
            base_url = "https://api-fxpractice.oanda.com" if environment == "practice" else "https://api-fxtrade.oanda.com"
            headers = {"Authorization": f"Bearer {api_key}"}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{base_url}/v3/accounts/{account_id}", headers=headers, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        account = data.get("account", {})
                        balance = account.get("balance", "0")
                        currency = account.get("currency", "USD")
                        
                        logger.info(f"OANDA connection successful!")
                        logger.info(f"Account: {account_id} ({environment})")
                        logger.info(f"Balance: {balance} {currency}")
                        return True
                    else:
                        logger.error(f"OANDA connection failed: HTTP {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"OANDA connection test failed: {e}")
            return False
    
    def start_service(self, service: Dict) -> bool:
        """Start a single service"""
        logger.info(f"Starting {service['name']} ({service['description']})...")
        
        try:
            # Change to service directory
            original_cwd = os.getcwd()
            os.chdir(service['path'])
            
            # Start the process
            process = subprocess.Popen(
                service['command'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=dict(os.environ, PYTHONPATH=str(self.project_root))
            )
            
            # Store the process
            self.processes[service['name']] = process
            
            # Return to original directory
            os.chdir(original_cwd)
            
            # Give the service time to start
            time.sleep(5)
            
            # Check if process is still running
            if process.poll() is None:
                logger.info(f"SUCCESS: {service['name']} started (PID: {process.pid})")
                return True
            else:
                stdout, stderr = process.communicate()
                logger.error(f"FAILED: {service['name']} failed to start")
                logger.error(f"STDOUT: {stdout.decode()}")
                logger.error(f"STDERR: {stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"FAILED: {service['name']} error: {e}")
            return False
    
    async def wait_for_health_check(self, service: Dict, timeout: int = 30) -> bool:
        """Wait for service health check to pass"""
        if not service.get('health_endpoint'):
            return True
        
        logger.info(f"Waiting for {service['name']} health check...")
        
        import aiohttp
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(service['health_endpoint'], timeout=5) as response:
                        if response.status == 200:
                            logger.info(f"SUCCESS: {service['name']} health check passed")
                            return True
            except Exception:
                pass
            
            await asyncio.sleep(2)
        
        logger.warning(f"WARNING: {service['name']} health check timeout")
        return False
    
    async def start_all_services(self):
        """Start all services in order"""
        logger.info("=== TMT Trading System Startup ===")
        
        if not self.check_prerequisites():
            logger.error("FAILED: Prerequisites not met")
            return False
        
        if not await self.test_oanda_connection():
            logger.error("FAILED: OANDA connection failed")
            return False
        
        # Start services
        for service in self.services:
            if not self.start_service(service):
                logger.error(f"FAILED: Critical service {service['name']} failed")
                await self.stop_all_services()
                return False
            
            await self.wait_for_health_check(service)
        
        self.running = True
        logger.info("=== TRADING SYSTEM READY ===")
        logger.info("Dashboard: http://localhost:8000")
        logger.info("Market Analysis: http://localhost:8001") 
        logger.info("Status: READY FOR PAPER TRADING")
        return True
    
    async def stop_all_services(self):
        """Stop all running services"""
        logger.info("Stopping services...")
        
        for name, process in self.processes.items():
            try:
                logger.info(f"Stopping {name}...")
                process.terminate()
                process.wait(timeout=10)
                logger.info(f"SUCCESS: {name} stopped")
            except subprocess.TimeoutExpired:
                logger.warning(f"Force killing {name}...")
                process.kill()
                process.wait()
            except Exception as e:
                logger.error(f"Error stopping {name}: {e}")
        
        self.processes.clear()
        self.running = False
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Shutdown signal received")
            asyncio.create_task(self.stop_all_services())
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def run(self):
        """Main run loop"""
        self.setup_signal_handlers()
        
        if await self.start_all_services():
            logger.info("System running. Press Ctrl+C to stop.")
            
            # Keep running and monitor
            while self.running:
                await asyncio.sleep(5)
                
                # Check if processes are still alive
                for name, process in list(self.processes.items()):
                    if process.poll() is not None:
                        logger.warning(f"Service {name} died unexpectedly")
                        
        else:
            logger.error("SYSTEM STARTUP FAILED")
            sys.exit(1)

async def main():
    """Main entry point"""
    manager = TradingSystemManager()
    await manager.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutdown by user")
    except Exception as e:
        logger.error(f"System error: {e}")
        sys.exit(1)