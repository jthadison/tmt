#!/usr/bin/env python3
"""
TMT Trading System - Quick Restart Script

A simplified wrapper around the full restart script for common use cases.

Usage:
    python quick-restart.py [native|docker] [--force]
    
Examples:
    python quick-restart.py                    # Restart in native mode
    python quick-restart.py docker             # Restart in Docker mode
    python quick-restart.py native --force     # Force restart native mode
"""

import asyncio
import sys
import argparse
from pathlib import Path

# Import the main restart functionality
from restart_trading_system import TradingSystemRestarter, logger

async def quick_restart(mode: str, force: bool = False) -> bool:
    """Quick restart with sensible defaults"""
    logger.info(f"🚀 Quick Restart - {mode.upper()} mode")
    
    restarter = TradingSystemRestarter(
        force_kill=force,
        skip_health_check=False,  # Always do health checks for safety
        deployment_mode=mode
    )
    
    return await restarter.full_restart()

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="TMT Trading System Quick Restart",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python quick-restart.py                    # Native mode restart
  python quick-restart.py docker             # Docker mode restart  
  python quick-restart.py native --force     # Force native restart
        """
    )
    
    parser.add_argument("mode", nargs="?", choices=["native", "docker"], 
                       default="native", help="Deployment mode (default: native)")
    parser.add_argument("--force", action="store_true", 
                       help="Force kill processes if graceful shutdown fails")
    
    args = parser.parse_args()
    
    # Auto-detect mode if docker-compose is present
    if args.mode == "native" and Path("docker-compose.yml").exists():
        logger.info("💡 Tip: Docker Compose detected. Use 'docker' mode for full stack restart.")
    
    try:
        success = await quick_restart(args.mode, args.force)
        return 0 if success else 1
    except KeyboardInterrupt:
        logger.info("Quick restart interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Quick restart failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))