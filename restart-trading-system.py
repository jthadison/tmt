#!/usr/bin/env python3
"""
TMT Trading System - Complete Restart Script

This script performs a complete stop and restart of the entire TMT trading system:
1. Detects and stops all running trading system processes
2. Cleans up ports and resources
3. Waits for clean shutdown
4. Starts all services in proper sequence
5. Validates system health

Usage:
    python restart-trading-system.py [--force] [--skip-health-check]
    
Options:
    --force: Force kill processes if graceful shutdown fails
    --skip-health-check: Skip health validation after restart
"""

import asyncio
import subprocess
import sys
import time
import logging
import signal
import os
import psutil
import argparse
from pathlib import Path
from typing import List, Dict, Set
import aiohttp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("trading_system_restart")

class TradingSystemRestarter:
    """Complete restart manager for TMT trading system"""
    
    def __init__(self, force_kill: bool = False, skip_health_check: bool = False, deployment_mode: str = "native"):
        self.force_kill = force_kill
        self.skip_health_check = skip_health_check
        self.deployment_mode = deployment_mode
        
        # Known trading system processes and ports
        self.trading_processes = {
            "orchestrator": {
                "ports": [8000],
                "process_names": ["uvicorn", "python"],
                "keywords": ["orchestrator", "app.main", "8000"]
            },
            "market_analysis": {
                "ports": [8002],
                "process_names": ["python"],
                "keywords": ["market-analysis", "start-market-analysis", "8002"]
            },
            "execution_engine": {
                "ports": [8004],
                "process_names": ["python", "uvicorn"],
                "keywords": ["execution-engine", "start-execution-engine", "8004"]
            },
            "signal_bridge": {
                "ports": [],
                "process_names": ["python"],
                "keywords": ["signal_bridge", "signal-bridge"]
            },
            "dashboard": {
                "ports": [3000],
                "process_names": ["node", "npm", "next"],
                "keywords": ["dashboard", "next", "3000"]
            },
            "risk_analytics": {
                "ports": [],
                "process_names": ["python"],
                "keywords": ["risk-analytics-engine", "risk_analytics"]
            }
        }
        
        # Docker services that need to be managed
        self.docker_services = [
            "postgres", "redis", "kafka", "zookeeper", "vault", "jaeger",
            "prometheus", "grafana", "alertmanager", "dashboard",
            "orchestrator", "market-analysis", "execution-engine"
        ]
        
        # Service startup configurations for native mode
        self.native_startup_configs = {
            "orchestrator": {
                "command": ["python", "-m", "uvicorn", "orchestrator.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
                "cwd": Path.cwd(),
                "port": 8000,
                "health_endpoint": "/health",
                "startup_delay": 5
            },
            "market_analysis": {
                "command": ["python", "start-market-analysis.py"],
                "cwd": Path.cwd(),
                "port": 8002,
                "health_endpoint": "/health",
                "startup_delay": 3
            },
            "execution_engine": {
                "command": ["python", "start-execution-engine.py"],
                "cwd": Path.cwd(),
                "port": 8004,
                "health_endpoint": "/health",
                "startup_delay": 3
            },
            "dashboard": {
                "command": ["npm", "run", "dev"],
                "cwd": Path.cwd() / "dashboard",
                "port": 3000,
                "health_endpoint": "/api/health",
                "startup_delay": 8
            }
        }
        
        # Docker service health check endpoints
        self.docker_health_configs = {
            "orchestrator": {"port": 8000, "endpoint": "/health"},
            "market-analysis": {"port": 8002, "endpoint": "/health"},
            "execution-engine": {"port": 8004, "endpoint": "/health"},
            "dashboard": {"port": 3000, "endpoint": "/api/health"},
            "postgres": {"port": 5432, "endpoint": None},
            "redis": {"port": 6379, "endpoint": None},
            "kafka": {"port": 9092, "endpoint": None},
            "prometheus": {"port": 9090, "endpoint": "/-/healthy"},
            "grafana": {"port": 3001, "endpoint": "/api/health"}
        }
        
        # Deployment mode (native or docker)
        self.deployment_mode = "native"  # Can be overridden
    
    async def full_restart(self) -> bool:
        """Perform complete system restart"""
        logger.info(f"Starting TMT Trading System Complete Restart ({self.deployment_mode} mode)")
        logger.info("=" * 60)
        
        try:
            # Step 1: Stop all services
            logger.info("Step 1: Stopping all trading system services...")
            stop_success = await self.stop_all_services()
            
            if not stop_success:
                logger.error("Failed to stop all services cleanly")
                if not self.force_kill:
                    logger.info("Use --force flag to force kill remaining processes")
                    return False
            
            # Step 2: Clean up ports and resources
            logger.info("Step 2: Cleaning up ports and resources...")
            await self.cleanup_resources()
            
            # Step 3: Wait for clean state
            logger.info("Step 3: Waiting for clean shutdown...")
            await asyncio.sleep(3)
            
            # Step 4: Start all services based on deployment mode
            logger.info(f"Step 4: Starting all services in {self.deployment_mode} mode...")
            if self.deployment_mode == "docker":
                start_success = await self.start_docker_services()
            else:
                start_success = await self.start_native_services()
            
            if not start_success:
                logger.error("Failed to start all services")
                return False
            
            # Step 5: Health validation
            if not self.skip_health_check:
                logger.info("Step 5: Validating system health...")
                health_success = await self.validate_system_health()
                
                if not health_success:
                    logger.warning("Some services may not be fully healthy")
                    return False
            
            logger.info("=" * 60)
            logger.info("TMT Trading System Restart Complete!")
            logger.info("")
            self.print_system_status()
            
            return True
            
        except Exception as e:
            logger.error(f"Restart failed: {e}")
            return False
    
    async def stop_all_services(self) -> bool:
        """Stop all trading system services based on deployment mode"""
        logger.info("🛑 Detecting and stopping trading system services...")
        
        success = True
        
        if self.deployment_mode == "docker":
            # Stop Docker services first
            docker_success = await self.stop_docker_services()
            success = success and docker_success
        
        # Stop any native processes
        native_success = await self.stop_native_processes()
        success = success and native_success
        
        return success
        
    async def stop_docker_services(self) -> bool:
        """Stop Docker Compose services"""
        logger.info("🐳 Stopping Docker services...")
        try:
            # Stop docker-compose services
            result = subprocess.run(
                ["docker-compose", "down", "--remove-orphans"],
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                logger.info("✅ Docker services stopped successfully")
                return True
            else:
                logger.error(f"❌ Docker stop failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("❌ Docker stop command timed out")
            return False
        except Exception as e:
            logger.error(f"❌ Error stopping Docker services: {e}")
            return False
    
    async def stop_native_processes(self) -> bool:
        """Stop native processes"""
        logger.info("🔍 Detecting and stopping native processes...")
        
        found_processes = self.find_trading_processes()
        
        if not found_processes:
            logger.info("✅ No native trading system processes found running")
            return True
        
        logger.info(f"Found {len(found_processes)} native trading system processes")
        
        # Try graceful shutdown first
        graceful_success = await self.graceful_shutdown(found_processes)
        
        if graceful_success:
            logger.info("✅ All native processes stopped gracefully")
            return True
        
        # Force kill if needed and allowed
        if self.force_kill:
            logger.warning("⚡ Force killing remaining native processes...")
            force_success = await self.force_kill_processes(found_processes)
            return force_success
        
        return False
    
    def find_trading_processes(self) -> List[psutil.Process]:
        """Find all running trading system processes"""
        found_processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                proc_info = proc.as_dict(attrs=['pid', 'name', 'cmdline'])
                name = proc_info['name']
                cmdline = ' '.join(proc_info['cmdline']) if proc_info['cmdline'] else ''
                
                # Check if this process matches any trading system service
                for service_name, config in self.trading_processes.items():
                    if self.is_trading_process(proc, name, cmdline, config):
                        logger.info(f"  Found {service_name}: PID {proc.pid} - {cmdline[:80]}...")
                        found_processes.append(proc)
                        break
                        
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        return found_processes
    
    def is_trading_process(self, proc, name: str, cmdline: str, config: Dict) -> bool:
        """Check if process matches trading system criteria"""
        # Check process name
        if name.lower() in [pname.lower() for pname in config['process_names']]:
            # Check for keywords in command line
            for keyword in config['keywords']:
                if keyword.lower() in cmdline.lower():
                    return True
        
        # Check if process is using our ports
        try:
            connections = proc.connections()
            for conn in connections:
                if hasattr(conn, 'laddr') and conn.laddr and conn.laddr.port in config['ports']:
                    return True
        except (psutil.AccessDenied, psutil.NoSuchProcess, AttributeError):
            # AttributeError can occur if connections() is not available
            pass
        
        return False
    
    async def graceful_shutdown(self, processes: List[psutil.Process]) -> bool:
        """Attempt graceful shutdown of processes"""
        logger.info("🤝 Attempting graceful shutdown...")
        
        # Send SIGTERM to all processes
        for proc in processes:
            try:
                logger.info(f"  Sending SIGTERM to PID {proc.pid}")
                proc.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Wait up to 10 seconds for graceful shutdown
        wait_time = 10
        logger.info(f"⏳ Waiting {wait_time} seconds for graceful shutdown...")
        
        for i in range(wait_time):
            still_running = []
            for proc in processes:
                try:
                    if proc.is_running():
                        still_running.append(proc)
                except psutil.NoSuchProcess:
                    continue
            
            if not still_running:
                logger.info("✅ All processes stopped gracefully")
                return True
            
            await asyncio.sleep(1)
        
        logger.warning(f"⚠️ {len(still_running)} processes still running after graceful shutdown")
        return False
    
    async def force_kill_processes(self, processes: List[psutil.Process]) -> bool:
        """Force kill remaining processes"""
        remaining_processes = []
        
        for proc in processes:
            try:
                if proc.is_running():
                    remaining_processes.append(proc)
            except psutil.NoSuchProcess:
                continue
        
        if not remaining_processes:
            return True
        
        logger.warning(f"⚡ Force killing {len(remaining_processes)} processes...")
        
        for proc in remaining_processes:
            try:
                logger.warning(f"  Force killing PID {proc.pid}")
                proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                logger.error(f"  Failed to kill PID {proc.pid}: {e}")
        
        # Wait a moment for kill to take effect
        await asyncio.sleep(2)
        
        # Verify all processes are gone
        still_alive = []
        for proc in remaining_processes:
            try:
                if proc.is_running():
                    still_alive.append(proc)
            except psutil.NoSuchProcess:
                continue
        
        if still_alive:
            logger.error(f"❌ {len(still_alive)} processes could not be killed")
            return False
        
        logger.info("✅ All processes force killed successfully")
        return True
    
    async def cleanup_resources(self) -> None:
        """Clean up ports and system resources"""
        # Check for processes still using our ports
        all_ports = []
        for service_config in self.trading_processes.values():
            all_ports.extend(service_config['ports'])
        
        for port in all_ports:
            if port == 0:  # Skip empty ports
                continue
                
            try:
                # Find processes using the port
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        connections = proc.connections()
                        for conn in connections:
                            if hasattr(conn, 'laddr') and conn.laddr and conn.laddr.port == port:
                                logger.warning(f"  Port {port} still in use by PID {proc.pid} ({proc.name()})")
                                if self.force_kill:
                                    proc.kill()
                                    logger.info(f"  Killed process using port {port}")
                    except (psutil.AccessDenied, psutil.NoSuchProcess, AttributeError):
                        continue
            except Exception as e:
                logger.debug(f"Error checking port {port}: {e}")
        
        # Give time for port cleanup
        await asyncio.sleep(1)
    
    async def start_docker_services(self) -> bool:
        """Start all Docker services"""
        logger.info("🐳 Starting Docker services...")
        
        try:
            # Start docker-compose services
            result = subprocess.run(
                ["docker-compose", "up", "-d", "--build"],
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes for build and start
            )
            
            if result.returncode == 0:
                logger.info("✅ Docker services started successfully")
                
                # Wait for services to be ready
                logger.info("⏳ Waiting for Docker services to be ready...")
                await asyncio.sleep(30)  # Give Docker services time to start
                
                return True
            else:
                logger.error(f"❌ Docker start failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("❌ Docker start command timed out")
            return False
        except Exception as e:
            logger.error(f"❌ Error starting Docker services: {e}")
            return False
    
    async def start_native_services(self) -> bool:
        """Start all native services in proper sequence"""
        logger.info("🚀 Starting native services in sequence...")
        
        started_processes = {}
        
        try:
            for service_name, config in self.native_startup_configs.items():
                logger.info(f"  Starting {service_name} on port {config['port']}...")
                
                # Create environment
                env = os.environ.copy()
                env.update({
                    "OANDA_API_KEY": os.getenv("OANDA_API_KEY", ""),
                    "OANDA_ACCOUNT_IDS": os.getenv("OANDA_ACCOUNT_IDS", "101-001-21040028-001"),
                    "OANDA_ENVIRONMENT": os.getenv("OANDA_ENVIRONMENT", "practice"),
                    "DATABASE_URL": os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/trading_system"),
                    "REDIS_URL": os.getenv("REDIS_URL", "redis://localhost:6379"),
                    "KAFKA_BROKERS": os.getenv("KAFKA_BROKERS", "localhost:9092")
                })
                
                # Start the process
                process = subprocess.Popen(
                    config["command"],
                    cwd=config["cwd"],
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1
                )
                
                started_processes[service_name] = {
                    "process": process,
                    "config": config
                }
                
                logger.info(f"    ✅ {service_name} started (PID: {process.pid})")
                
                # Wait before starting next service
                await asyncio.sleep(config["startup_delay"])
                
                # Quick health check
                if not await self.quick_health_check(service_name, config):
                    logger.warning(f"    ⚠️ {service_name} may not be fully ready yet")
            
            logger.info("✅ All native services started successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start native services: {e}")
            
            # Clean up any started processes
            for service_name, service_info in started_processes.items():
                try:
                    process = service_info["process"]
                    process.terminate()
                    logger.info(f"Cleaned up {service_name}")
                except:
                    pass
            
            return False
    
    async def quick_health_check(self, service_name: str, config: Dict) -> bool:
        """Quick health check for a service"""
        try:
            url = f"http://localhost:{config['port']}{config['health_endpoint']}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=3)) as response:
                    if response.status == 200:
                        return True
        except:
            pass
        
        return False
    
    async def validate_system_health(self) -> bool:
        """Comprehensive system health validation"""
        logger.info("🏥 Running comprehensive health checks...")
        
        all_healthy = True
        
        if self.deployment_mode == "docker":
            # Check Docker service health
            docker_healthy = await self.check_docker_health()
            all_healthy = all_healthy and docker_healthy
        else:
            # Check native service health
            native_healthy = await self.check_native_health()
            all_healthy = all_healthy and native_healthy
        
        return all_healthy
    
    async def check_docker_health(self) -> bool:
        """Check Docker service health"""
        logger.info("🐳 Checking Docker service health...")
        all_healthy = True
        
        for service_name, config in self.docker_health_configs.items():
            if config["endpoint"]:
                logger.info(f"  Checking {service_name}...")
                url = f"http://localhost:{config['port']}{config['endpoint']}"
                
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                            if response.status == 200:
                                try:
                                    health_data = await response.json()
                                    logger.info(f"    ✅ {service_name}: {health_data}")
                                except:
                                    logger.info(f"    ✅ {service_name}: Healthy")
                            else:
                                logger.error(f"    ❌ {service_name}: HTTP {response.status}")
                                all_healthy = False
                except Exception as e:
                    logger.error(f"    ❌ {service_name}: {e}")
                    all_healthy = False
            else:
                # For services without HTTP endpoints, check if port is open
                if await self.check_port_open(config["port"]):
                    logger.info(f"    ✅ {service_name}: Port {config['port']} is open")
                else:
                    logger.error(f"    ❌ {service_name}: Port {config['port']} is not accessible")
                    all_healthy = False
        
        return all_healthy
    
    async def check_native_health(self) -> bool:
        """Check native service health"""
        logger.info("🔧 Checking native service health...")
        all_healthy = True
        
        for service_name, config in self.native_startup_configs.items():
            logger.info(f"  Checking {service_name}...")
            
            url = f"http://localhost:{config['port']}{config['health_endpoint']}"
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        if response.status == 200:
                            try:
                                health_data = await response.json()
                                logger.info(f"    ✅ {service_name}: {health_data}")
                            except:
                                logger.info(f"    ✅ {service_name}: Healthy")
                        else:
                            logger.error(f"    ❌ {service_name}: HTTP {response.status}")
                            all_healthy = False
            except Exception as e:
                logger.error(f"    ❌ {service_name}: {e}")
                all_healthy = False
        
        return all_healthy
    
    async def check_port_open(self, port: int) -> bool:
        """Check if a port is open"""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection('localhost', port),
                timeout=3
            )
            writer.close()
            await writer.wait_closed()
            return True
        except:
            return False
    
    def print_system_status(self) -> None:
        """Print current system status"""
        logger.info(f"📊 System Status ({self.deployment_mode} mode):")
        
        if self.deployment_mode == "docker":
            logger.info("🐳 Docker Services:")
            logger.info("  • Orchestrator:     http://localhost:8000/health")
            logger.info("  • Market Analysis:  http://localhost:8002/health")
            logger.info("  • Execution Engine: http://localhost:8004/health")
            logger.info("  • Dashboard:        http://localhost:3000")
            logger.info("  • Grafana:          http://localhost:3001 (admin/admin)")
            logger.info("  • Prometheus:       http://localhost:9090")
            logger.info("  • Jaeger:           http://localhost:16686")
            logger.info("  • Vault:            http://localhost:8200")
            logger.info("")
            logger.info("🖺 Infrastructure:")
            logger.info("  • PostgreSQL:       localhost:5432")
            logger.info("  • Redis:            localhost:6379")
            logger.info("  • Kafka:            localhost:9092")
        else:
            logger.info("🔧 Native Services:")
            logger.info("  • Orchestrator:     http://localhost:8000/health")
            logger.info("  • Market Analysis:  http://localhost:8002/health")
            logger.info("  • Execution Engine: http://localhost:8004/health")
            logger.info("  • Dashboard:        http://localhost:3000")
        
        logger.info("")
        logger.info("🧪 Testing Commands:")
        logger.info("  • Integration Test: python test-trading-pipeline.py")
        logger.info("  • Signal Bridge:    python signal_bridge.py")
        if self.deployment_mode == "docker":
            logger.info("  • Docker Status:    docker-compose ps")
            logger.info("  • Docker Logs:      docker-compose logs -f [service]")
        logger.info("")
        logger.info("📈 Next Steps:")
        logger.info("  • Run integration tests to verify functionality")
        logger.info("  • Monitor logs for any issues")
        logger.info("  • Start signal processing if desired")
        if self.deployment_mode == "docker":
            logger.info("  • Access monitoring dashboards for system insights")

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="TMT Trading System Complete Restart")
    parser.add_argument("--force", action="store_true", 
                       help="Force kill processes if graceful shutdown fails")
    parser.add_argument("--skip-health-check", action="store_true",
                       help="Skip health validation after restart")
    parser.add_argument("--mode", choices=["native", "docker"], default="native",
                       help="Deployment mode: native or docker (default: native)")
    
    args = parser.parse_args()
    
    # Auto-detect deployment mode if docker-compose.yml exists
    if args.mode == "native" and Path("docker-compose.yml").exists():
        logger.info("🔍 Docker Compose detected, consider using --mode docker")
    
    restarter = TradingSystemRestarter(
        force_kill=args.force,
        skip_health_check=args.skip_health_check,
        deployment_mode=args.mode
    )
    
    try:
        success = await restarter.full_restart()
        
        if success:
            logger.info("🎉 Trading system restart completed successfully!")
            return 0
        else:
            logger.error("💥 Trading system restart failed!")
            return 1
            
    except KeyboardInterrupt:
        logger.info("Restart interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error during restart: {e}")
        return 1

if __name__ == "__main__":
    # Check if psutil is available
    try:
        import psutil
    except ImportError:
        print("❌ psutil library required but not installed")
        print("Install with: pip install psutil")
        sys.exit(1)
    
    sys.exit(asyncio.run(main()))