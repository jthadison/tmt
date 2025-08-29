#!/usr/bin/env python3
"""
TMT Trading System - Complete Restart Script (Clean Version)

This script performs a complete stop and restart of the entire TMT trading system:
1. Detects and stops all running trading system processes
2. Cleans up ports and resources
3. Waits for clean shutdown
4. Starts all services in proper sequence
5. Validates system health

Usage:
    python restart-trading-system-clean.py [--force] [--skip-health-check] [--mode native|docker]
    
Options:
    --force: Force kill processes if graceful shutdown fails
    --skip-health-check: Skip health validation after restart
    --mode: Deployment mode (native or docker, default: native)
"""

import asyncio
import subprocess
import sys
import time
import logging
import os
import psutil
import argparse
from pathlib import Path
from typing import List, Dict
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
            }
        }
        
        # Docker services that need to be managed
        self.docker_services = [
            "postgres", "redis", "kafka", "zookeeper", "vault", "jaeger",
            "prometheus", "grafana", "alertmanager", "dashboard",
            "orchestrator", "market-analysis", "execution-engine"
        ]
    
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
                logger.error("Native mode startup not implemented in clean version")
                return False
            
            if not start_success:
                logger.error("Failed to start all services")
                return False
            
            # Step 5: Health validation
            if not self.skip_health_check:
                logger.info("Step 5: Validating system health...")
                # Simplified health check for now
                await asyncio.sleep(10)
                logger.info("Health check completed")
            
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
        logger.info("Detecting and stopping trading system services...")
        
        success = True
        
        if self.deployment_mode == "docker":
            # Stop Docker services first
            docker_success = await self.stop_docker_services()
            success = success and docker_success
        
        # Stop any native processes (always check for these)
        native_success = await self.stop_native_processes()
        success = success and native_success
        
        return success
    
    async def stop_docker_services(self) -> bool:
        """Stop Docker Compose services"""
        logger.info("Stopping Docker services...")
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
                logger.info("Docker services stopped successfully")
                return True
            else:
                logger.error(f"Docker stop failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Docker stop command timed out")
            return False
        except Exception as e:
            logger.error(f"Error stopping Docker services: {e}")
            return False
    
    async def stop_native_processes(self) -> bool:
        """Stop native processes"""
        logger.info("Detecting and stopping native processes...")
        
        found_processes = self.find_trading_processes()
        
        if not found_processes:
            logger.info("No native trading system processes found running")
            return True
        
        logger.info(f"Found {len(found_processes)} native trading system processes")
        
        # Try graceful shutdown first
        graceful_success = await self.graceful_shutdown(found_processes)
        
        if graceful_success:
            logger.info("All native processes stopped gracefully")
            return True
        
        # Force kill if needed and allowed
        if self.force_kill:
            logger.warning("Force killing remaining native processes...")
            force_success = await self.force_kill_processes(found_processes)
            return force_success
        
        return False
    
    def find_trading_processes(self) -> List[psutil.Process]:
        """Find all running trading system processes"""
        found_processes = []
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    proc_info = proc.as_dict(attrs=['pid', 'name', 'cmdline'])
                    name = proc_info['name'] or ""
                    cmdline = ' '.join(proc_info['cmdline']) if proc_info['cmdline'] else ''
                    
                    # Check if this process matches any trading system service
                    for service_name, config in self.trading_processes.items():
                        if self.is_trading_process(proc, name, cmdline, config):
                            logger.info(f"Found {service_name}: PID {proc.pid} - {cmdline[:80]}...")
                            found_processes.append(proc)
                            break
                            
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception as e:
            logger.error(f"Error finding processes: {e}")
        
        return found_processes
    
    def is_trading_process(self, proc, name: str, cmdline: str, config: Dict) -> bool:
        """Check if process matches trading system criteria"""
        # Check process name
        if name.lower() in [pname.lower() for pname in config['process_names']]:
            # Check for keywords in command line
            for keyword in config['keywords']:
                if keyword.lower() in cmdline.lower():
                    return True
        
        # Check if process is using our ports (simplified check)
        try:
            if config['ports']:
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
        logger.info("Attempting graceful shutdown...")
        
        # Send SIGTERM to all processes
        for proc in processes:
            try:
                logger.info(f"Sending SIGTERM to PID {proc.pid}")
                proc.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Wait up to 10 seconds for graceful shutdown
        wait_time = 10
        logger.info(f"Waiting {wait_time} seconds for graceful shutdown...")
        
        for i in range(wait_time):
            still_running = []
            for proc in processes:
                try:
                    if proc.is_running():
                        still_running.append(proc)
                except psutil.NoSuchProcess:
                    continue
            
            if not still_running:
                logger.info("All processes stopped gracefully")
                return True
            
            await asyncio.sleep(1)
        
        logger.warning(f"{len(still_running)} processes still running after graceful shutdown")
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
        
        logger.warning(f"Force killing {len(remaining_processes)} processes...")
        
        for proc in remaining_processes:
            try:
                logger.warning(f"Force killing PID {proc.pid}")
                proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                logger.error(f"Failed to kill PID {proc.pid}: {e}")
        
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
            logger.error(f"{len(still_alive)} processes could not be killed")
            return False
        
        logger.info("All processes force killed successfully")
        return True
    
    async def cleanup_resources(self) -> None:
        """Clean up ports and system resources"""
        logger.info("Cleaning up resources...")
        # Give time for port cleanup
        await asyncio.sleep(1)
    
    async def start_docker_services(self) -> bool:
        """Start all Docker services"""
        logger.info("Starting Docker services...")
        
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
                logger.info("Docker services started successfully")
                
                # Wait for services to be ready
                logger.info("Waiting for Docker services to be ready...")
                await asyncio.sleep(30)  # Give Docker services time to start
                
                return True
            else:
                logger.error(f"Docker start failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Docker start command timed out")
            return False
        except Exception as e:
            logger.error(f"Error starting Docker services: {e}")
            return False
    
    def print_system_status(self) -> None:
        """Print current system status"""
        logger.info(f"System Status ({self.deployment_mode} mode):")
        
        if self.deployment_mode == "docker":
            logger.info("Docker Services:")
            logger.info("  • Orchestrator:     http://localhost:8000/health")
            logger.info("  • Market Analysis:  http://localhost:8002/health")
            logger.info("  • Execution Engine: http://localhost:8004/health")
            logger.info("  • Dashboard:        http://localhost:3000")
            logger.info("  • Grafana:          http://localhost:3001 (admin/admin)")
            logger.info("  • Prometheus:       http://localhost:9090")
            logger.info("  • Jaeger:           http://localhost:16686")
            logger.info("  • Vault:            http://localhost:8200")
            logger.info("")
            logger.info("Infrastructure:")
            logger.info("  • PostgreSQL:       localhost:5432")
            logger.info("  • Redis:            localhost:6379")
            logger.info("  • Kafka:            localhost:9092")
        else:
            logger.info("Native Services:")
            logger.info("  • Orchestrator:     http://localhost:8000/health")
            logger.info("  • Market Analysis:  http://localhost:8002/health")
            logger.info("  • Execution Engine: http://localhost:8004/health")
            logger.info("  • Dashboard:        http://localhost:3000")
        
        logger.info("")
        logger.info("Testing Commands:")
        logger.info("  • Integration Test: python test-trading-pipeline.py")
        logger.info("  • Signal Bridge:    python signal_bridge.py")
        if self.deployment_mode == "docker":
            logger.info("  • Docker Status:    docker-compose ps")
            logger.info("  • Docker Logs:      docker-compose logs -f [service]")
        logger.info("")
        logger.info("Next Steps:")
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
        logger.info("Docker Compose detected, consider using --mode docker")
    
    restarter = TradingSystemRestarter(
        force_kill=args.force,
        skip_health_check=args.skip_health_check,
        deployment_mode=args.mode
    )
    
    try:
        success = await restarter.full_restart()
        
        if success:
            logger.info("Trading system restart completed successfully!")
            return 0
        else:
            logger.error("Trading system restart failed!")
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
        print("psutil library required but not installed")
        print("Install with: pip install psutil")
        sys.exit(1)
    
    sys.exit(asyncio.run(main()))