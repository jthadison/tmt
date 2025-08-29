#!/usr/bin/env python3
"""Test the restart script fixes"""

import sys
import os
import importlib.util
sys.path.append(os.path.dirname(__file__))

# Import the module with hyphen in name
spec = importlib.util.spec_from_file_location("restart_trading_system", "restart-trading-system.py")
restart_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(restart_module)

TradingSystemRestarter = restart_module.TradingSystemRestarter

def test_init():
    """Test that the restarter initializes correctly"""
    print("Testing TradingSystemRestarter initialization...")
    
    # Test native mode
    restarter_native = TradingSystemRestarter(deployment_mode="native")
    print(f"✅ Native mode: {restarter_native.deployment_mode}")
    
    # Test docker mode
    restarter_docker = TradingSystemRestarter(deployment_mode="docker")
    print(f"✅ Docker mode: {restarter_docker.deployment_mode}")
    
    # Test process finding (shouldn't crash)
    try:
        processes = restarter_native.find_trading_processes()
        print(f"✅ Process discovery works: found {len(processes)} processes")
    except Exception as e:
        print(f"❌ Process discovery failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = test_init()
    print("✅ All tests passed!" if success else "❌ Tests failed!")
    sys.exit(0 if success else 1)