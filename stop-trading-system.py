#!/usr/bin/env python3
"""
TMT Trading System - Stop Script

Gracefully stops all TMT trading system services.

Usage:
    python stop-trading-system.py [--force]
    
Options:
    --force: Force kill processes if graceful shutdown fails
"""

import asyncio
import sys
import time
import logging
import argparse
import psutil
from typing import List, Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("trading_system_stop")

class TradingSystemStopper:
    """Stops all TMT trading system services"""
    
    def __init__(self, force_kill: bool = False):
        self.force_kill = force_kill
        
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
            "integration_test": {
                "ports": [],
                "process_names": ["python"],
                "keywords": ["test-trading-pipeline"]
            }
        }
    
    async def stop_all_services(self) -> bool:
        """Stop all trading system services"""
        logger.info("🛑 TMT Trading System Shutdown")
        logger.info("=" * 50)
        
        # Find all running trading processes
        found_processes = self.find_trading_processes()
        
        if not found_processes:
            logger.info("✅ No trading system processes found running")
            logger.info("System is already stopped")
            return True
        
        logger.info(f"Found {len(found_processes)} trading system processes")
        
        # Try graceful shutdown first
        logger.info("🤝 Attempting graceful shutdown...")
        graceful_success = await self.graceful_shutdown(found_processes)
        
        if graceful_success:
            logger.info("✅ All services stopped gracefully")
            await self.cleanup_ports()
            logger.info("=" * 50)
            logger.info("✅ TMT Trading System Shutdown Complete")
            return True
        
        # Force kill if needed and allowed
        if self.force_kill:
            logger.warning("⚡ Graceful shutdown failed, force killing remaining processes...")
            force_success = await self.force_kill_processes(found_processes)
            
            if force_success:
                await self.cleanup_ports()
                logger.info("=" * 50)
                logger.info("✅ TMT Trading System Force Shutdown Complete")
                return True
            else:
                logger.error("❌ Failed to stop all processes")
                return False
        else:
            logger.warning("⚠️ Some processes could not be stopped gracefully")
            logger.info("Use --force flag to force kill remaining processes")
            return False
    
    def find_trading_processes(self) -> List[psutil.Process]:
        """Find all running trading system processes"""
        found_processes = []
        services_found = set()
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'connections']):
            try:
                proc_info = proc.info
                name = proc_info['name']
                cmdline = ' '.join(proc_info['cmdline']) if proc_info['cmdline'] else ''
                
                # Check if this process matches any trading system service
                for service_name, config in self.trading_processes.items():
                    if self.is_trading_process(proc, name, cmdline, config):
                        if service_name not in services_found:
                            logger.info(f"  Found {service_name} service:")
                            services_found.add(service_name)
                        
                        logger.info(f"    PID {proc.pid}: {cmdline[:60]}...")
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
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            pass
        
        return False
    
    async def graceful_shutdown(self, processes: List[psutil.Process]) -> bool:
        """Attempt graceful shutdown of processes"""
        # Send SIGTERM to all processes
        terminated_count = 0
        for proc in processes:
            try:
                logger.info(f"  Sending SIGTERM to PID {proc.pid}")
                proc.terminate()
                terminated_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        if terminated_count == 0:
            logger.warning("  No processes could be terminated")
            return False
        
        # Wait up to 15 seconds for graceful shutdown
        wait_time = 15
        logger.info(f"⏳ Waiting up to {wait_time} seconds for graceful shutdown...")
        
        for i in range(wait_time):
            still_running = []
            for proc in processes:
                try:
                    if proc.is_running():
                        still_running.append(proc)
                except psutil.NoSuchProcess:
                    continue
            
            if not still_running:
                logger.info(f"✅ All processes stopped gracefully after {i+1} seconds")
                return True
            
            if i < wait_time - 1:  # Don't sleep on last iteration
                await asyncio.sleep(1)
        
        logger.warning(f"⚠️ {len(still_running)} processes still running after {wait_time} seconds")
        for proc in still_running:
            try:
                cmdline = ' '.join(proc.cmdline()) if proc.cmdline() else 'N/A'
                logger.warning(f"  Still running: PID {proc.pid} - {cmdline[:50]}...")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
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
        
        logger.warning(f"  Force killing {len(remaining_processes)} remaining processes...")
        
        killed_count = 0
        for proc in remaining_processes:
            try:
                cmdline = ' '.join(proc.cmdline()) if proc.cmdline() else 'N/A'
                logger.warning(f"    Force killing PID {proc.pid}: {cmdline[:40]}...")
                proc.kill()
                killed_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                logger.error(f"    Failed to kill PID {proc.pid}: {e}")
        
        # Wait a moment for kill to take effect
        await asyncio.sleep(3)
        
        # Verify all processes are gone
        still_alive = []
        for proc in remaining_processes:
            try:
                if proc.is_running():
                    still_alive.append(proc)
            except psutil.NoSuchProcess:
                continue
        
        if still_alive:
            logger.error(f"❌ {len(still_alive)} processes could not be killed:")
            for proc in still_alive:
                try:
                    cmdline = ' '.join(proc.cmdline()) if proc.cmdline() else 'N/A'
                    logger.error(f"    PID {proc.pid}: {cmdline[:50]}...")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return False
        
        logger.info(f"✅ Successfully force killed {killed_count} processes")
        return True
    
    async def cleanup_ports(self) -> None:
        """Check and report on port cleanup"""
        logger.info("🧹 Checking port cleanup...")
        
        trading_ports = [8000, 8002, 8004]
        ports_in_use = []
        
        for port in trading_ports:
            try:
                # Find processes using the port
                port_users = []
                for proc in psutil.process_iter(['pid', 'name', 'connections']):
                    try:
                        connections = proc.connections()
                        for conn in connections:
                            if hasattr(conn, 'laddr') and conn.laddr and conn.laddr.port == port:
                                port_users.append(f"PID {proc.pid} ({proc.name()})")
                    except (psutil.AccessDenied, psutil.NoSuchProcess):
                        continue
                
                if port_users:
                    ports_in_use.append(f"Port {port}: {', '.join(port_users)}")
                else:
                    logger.info(f"  ✅ Port {port} is free")
                    
            except Exception as e:
                logger.debug(f"Error checking port {port}: {e}")
        
        if ports_in_use:
            logger.warning("⚠️ Some trading system ports are still in use:")
            for port_info in ports_in_use:
                logger.warning(f"  {port_info}")
        else:
            logger.info("✅ All trading system ports are free")

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Stop TMT Trading System")
    parser.add_argument("--force", action="store_true", 
                       help="Force kill processes if graceful shutdown fails")
    
    args = parser.parse_args()
    
    stopper = TradingSystemStopper(force_kill=args.force)
    
    try:
        success = await stopper.stop_all_services()
        
        if success:
            logger.info("👋 All trading system services stopped successfully")
            return 0
        else:
            logger.error("💥 Failed to stop all trading system services")
            logger.info("Some processes may still be running. Use --force to force kill them.")
            return 1
            
    except KeyboardInterrupt:
        logger.info("Stop operation interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error during stop: {e}")
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