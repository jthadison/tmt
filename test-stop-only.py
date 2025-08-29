#!/usr/bin/env python3
"""Test just the stop functionality"""

import asyncio
import sys
import os
import importlib.util

# Import the clean restart module
spec = importlib.util.spec_from_file_location("restart_clean", "restart-trading-system-clean.py")
restart_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(restart_module)

async def test_stop_only():
    """Test just the stop functionality"""
    print("Testing stop functionality...")
    
    restarter = restart_module.TradingSystemRestarter(
        force_kill=False,
        skip_health_check=True,
        deployment_mode="docker"
    )
    
    # Test just the stop part
    success = await restarter.stop_all_services()
    
    if success:
        print("Stop test completed successfully!")
        return 0
    else:
        print("Stop test failed!")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(test_stop_only()))