#!/usr/bin/env python3
"""
TMT Trading System - Docker Restart Script

Specialized script for managing the Docker-based trading system deployment.
Provides Docker-specific operations and better integration with docker-compose.

Usage:
    python docker-restart.py [command]
    
Commands:
    restart     Full restart (stop + start) 
    start       Start all services
    stop        Stop all services
    status      Show service status
    logs        Show recent logs
    clean       Clean restart (remove volumes)
"""

import asyncio
import subprocess
import sys
import argparse
import json
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("docker_restart")

class DockerTradingSystemManager:
    """Manages Docker-based trading system deployment"""
    
    def __init__(self):
        self.compose_file = Path("docker-compose.yml")
        if not self.compose_file.exists():
            raise FileNotFoundError("docker-compose.yml not found. Make sure you're in the project root.")
    
    async def restart(self, clean: bool = False) -> bool:
        """Full restart of Docker services"""
        logger.info("🔄 Docker Trading System Restart")
        logger.info("=" * 50)
        
        try:
            # Stop services
            if not await self.stop():
                logger.error("❌ Failed to stop services")
                return False
            
            # Clean volumes if requested
            if clean:
                if not await self.clean_volumes():
                    logger.warning("⚠️ Volume cleanup had issues")
            
            # Start services
            if not await self.start():
                logger.error("❌ Failed to start services")
                return False
            
            # Show status
            await self.status()
            
            logger.info("=" * 50)
            logger.info("✅ Docker restart complete!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Docker restart failed: {e}")
            return False
    
    async def start(self) -> bool:
        """Start all Docker services"""
        logger.info("🚀 Starting Docker services...")
        
        try:
            # Pull latest images
            logger.info("📦 Pulling latest images...")
            result = await self.run_compose(["pull"])
            if result.returncode != 0:
                logger.warning("⚠️ Image pull had issues, continuing...")
            
            # Build and start
            logger.info("🏗️ Building and starting services...")
            result = await self.run_compose(["up", "-d", "--build"])
            
            if result.returncode == 0:
                logger.info("✅ Docker services started successfully")
                await asyncio.sleep(10)  # Give services time to initialize
                return True
            else:
                logger.error(f"❌ Failed to start services: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error starting Docker services: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop all Docker services"""
        logger.info("🛑 Stopping Docker services...")
        
        try:
            result = await self.run_compose(["down", "--remove-orphans"])
            
            if result.returncode == 0:
                logger.info("✅ Docker services stopped successfully")
                return True
            else:
                logger.error(f"❌ Failed to stop services: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error stopping Docker services: {e}")
            return False
    
    async def clean_volumes(self) -> bool:
        """Clean Docker volumes and networks"""
        logger.info("🧹 Cleaning Docker volumes and networks...")
        
        try:
            # Stop everything first
            await self.run_compose(["down", "-v", "--remove-orphans"])
            
            # Prune unused networks
            result = subprocess.run(
                ["docker", "network", "prune", "-f"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info("✅ Volumes and networks cleaned")
                return True
            else:
                logger.warning(f"⚠️ Volume cleanup issues: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error cleaning volumes: {e}")
            return False
    
    async def status(self) -> bool:
        """Show service status"""
        logger.info("📊 Docker Service Status:")
        
        try:
            # Get service status
            result = await self.run_compose(["ps", "--format", "json"])
            
            if result.returncode == 0:
                services = []
                for line in result.stdout.strip().split('\n'):
                    if line:
                        try:
                            service = json.loads(line)
                            services.append(service)
                        except json.JSONDecodeError:
                            continue
                
                if not services:
                    logger.info("  No services running")
                    return True
                
                # Display service status
                for service in services:
                    name = service.get('Name', 'Unknown')
                    state = service.get('State', 'Unknown')
                    status = service.get('Status', 'Unknown')
                    
                    if state == 'running':
                        logger.info(f"  ✅ {name}: {status}")
                    else:
                        logger.info(f"  ❌ {name}: {state} - {status}")
                
                return True
            else:
                logger.error(f"❌ Failed to get service status: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error getting service status: {e}")
            return False
    
    async def logs(self, service: str = None, tail: int = 50) -> bool:
        """Show service logs"""
        if service:
            logger.info(f"📋 Recent logs for {service} (last {tail} lines):")
            cmd = ["logs", "--tail", str(tail), service]
        else:
            logger.info(f"📋 Recent logs for all services (last {tail} lines each):")
            cmd = ["logs", "--tail", str(tail)]
        
        try:
            result = await self.run_compose(cmd)
            
            if result.returncode == 0:
                print(result.stdout)
                return True
            else:
                logger.error(f"❌ Failed to get logs: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error getting logs: {e}")
            return False
    
    async def run_compose(self, cmd: list, timeout: int = 120) -> subprocess.CompletedProcess:
        """Run docker-compose command"""
        full_cmd = ["docker-compose"] + cmd
        
        return subprocess.run(
            full_cmd,
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
            timeout=timeout
        )

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="TMT Trading System Docker Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  restart     Full restart (stop + start)
  start       Start all services  
  stop        Stop all services
  status      Show service status
  logs        Show recent logs
  clean       Clean restart (removes volumes)

Examples:
  python docker-restart.py restart           # Full restart
  python docker-restart.py start             # Start services
  python docker-restart.py logs orchestrator # Show orchestrator logs
        """
    )
    
    parser.add_argument("command", nargs="?", 
                       choices=["restart", "start", "stop", "status", "logs", "clean"],
                       default="restart", help="Command to run (default: restart)")
    parser.add_argument("--service", help="Specific service for logs command")
    parser.add_argument("--tail", type=int, default=50, help="Number of log lines to show")
    parser.add_argument("--clean-volumes", action="store_true", 
                       help="Clean volumes during restart")
    
    args = parser.parse_args()
    
    try:
        manager = DockerTradingSystemManager()
        
        if args.command == "restart":
            success = await manager.restart(clean=args.clean_volumes)
        elif args.command == "start":
            success = await manager.start()
        elif args.command == "stop":
            success = await manager.stop()
        elif args.command == "status":
            success = await manager.status()
        elif args.command == "logs":
            success = await manager.logs(args.service, args.tail)
        elif args.command == "clean":
            success = await manager.restart(clean=True)
        else:
            logger.error(f"Unknown command: {args.command}")
            return 1
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        logger.info("Operation interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))