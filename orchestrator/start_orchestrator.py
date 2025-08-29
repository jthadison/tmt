#!/usr/bin/env python3
"""
Trading System Orchestrator Startup Script

This script starts the TMT Trading System Orchestrator which coordinates
all trading agents and manages automated trading on OANDA accounts.
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add the current directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

try:
    import uvicorn
    from app.config import get_settings
    from app.main import app
except ImportError as e:
    print(f"Error importing dependencies: {e}")
    print("Please install requirements: pip install -r requirements.txt")
    sys.exit(1)


def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('orchestrator.log')
        ]
    )


def validate_environment():
    """Validate required environment variables"""
    settings = get_settings()
    
    required_vars = [
        'OANDA_API_KEY',
        'OANDA_ACCOUNT_IDS'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not getattr(settings, var.lower(), None):
            missing_vars.append(var)
    
    if missing_vars:
        print("Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these variables in your .env file or environment.")
        return False
    
    print("Environment validation passed")
    return True


def print_startup_info():
    """Print startup information"""
    settings = get_settings()
    
    print("\n" + "="*60)
    print("TMT Trading System Orchestrator")
    print("="*60)
    print(f"Version: {settings.app_version}")
    print(f"Environment: {settings.oanda_environment}")
    print(f"OANDA Accounts: {len(settings.account_ids_list)}")
    print(f"Server: http://{settings.host}:{settings.port}")
    print(f"Debug Mode: {settings.debug}")
    print(f"Log Level: {settings.log_level}")
    print("="*60)
    
    print("\nOANDA Account Configuration:")
    for i, account_id in enumerate(settings.account_ids_list, 1):
        print(f"   {i}. {account_id}")
    
    print(f"\nOANDA API: {settings.oanda_api_url}")
    print(f"Stream API: {settings.oanda_streaming_url}")
    
    print("\nExpected Agent Endpoints:")
    for agent_type, endpoint in settings.agent_endpoints.items():
        print(f"   - {agent_type}: {endpoint}")
    
    print("\nIMPORTANT SAFETY NOTES:")
    print(f"   - Max risk per trade: {settings.risk_per_trade*100:.1f}%")
    print(f"   - Max daily loss: {settings.max_daily_loss*100:.1f}%")
    print(f"   - Circuit breaker at: {settings.circuit_breaker_threshold*100:.1f}%")
    print(f"   - Max concurrent trades: {settings.max_concurrent_trades}")
    print(f"   - Emergency close positions: {settings.emergency_close_positions}")
    
    if settings.is_live_trading:
        print("\nLIVE TRADING MODE - REAL MONEY AT RISK!")
    else:
        print("\nPRACTICE MODE - Using demo account")
    
    print("="*60)


async def health_check():
    """Perform basic health checks before startup"""
    print("\nPerforming startup health checks...")
    
    # Check Redis connection
    try:
        import redis
        settings = get_settings()
        r = redis.from_url(settings.message_broker_url)
        r.ping()
        print("   + Redis connection successful")
    except Exception as e:
        print(f"   - Redis connection failed: {e}")
        return False
    
    # TODO: Add more health checks
    # - Database connection
    # - Agent availability
    # - OANDA API connectivity
    
    print("   + Basic health checks passed")
    return True


def main():
    """Main entry point"""
    setup_logging()
    
    print_startup_info()
    
    if not validate_environment():
        sys.exit(1)
    
    # Perform health checks
    if not asyncio.run(health_check()):
        print("\nHealth checks failed. Please check your configuration.")
        sys.exit(1)
    
    print("\nStarting Trading System Orchestrator...")
    print("   Press Ctrl+C to stop\n")
    
    # Get settings
    settings = get_settings()
    
    try:
        # Start the server
        uvicorn.run(
            "app.main:app",
            host=settings.host,
            port=settings.port,
            reload=settings.debug,
            log_level=settings.log_level.lower(),
            access_log=True
        )
    except KeyboardInterrupt:
        print("\nShutting down Trading System Orchestrator...")
        print("   Goodbye!")
    except Exception as e:
        print(f"\nStartup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()