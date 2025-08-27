#!/usr/bin/env python3
"""
Manual Circuit Breaker Reset Script
Directly resets circuit breakers and re-enables trading
"""

import asyncio
import sys
import os

# Add the orchestrator app to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

async def reset_circuit_breakers():
    """Reset circuit breakers manually"""
    try:
        from orchestrator import TradingOrchestrator
        from circuit_breaker import CircuitBreakerManager, BreakerType
        from config import get_settings
        
        print("Initializing orchestrator components...")
        
        # Create a minimal orchestrator setup
        settings = get_settings()
        
        # Create circuit breaker manager
        circuit_breaker = CircuitBreakerManager()
        
        print("Current circuit breaker status:")
        status = await circuit_breaker.get_status()
        print(f"   Overall status: {status.get('overall_status', 'unknown')}")
        
        print("\nResetting all circuit breakers...")
        
        # Reset all breakers
        await circuit_breaker.reset_all_breakers()
        
        print("SUCCESS: Circuit breakers reset successfully!")
        
        # Get updated status
        new_status = await circuit_breaker.get_status()
        print(f"\nNew circuit breaker status:")
        print(f"   Overall status: {new_status.get('overall_status', 'unknown')}")
        print(f"   Can trade: {new_status.get('can_trade', False)}")
        
        print("\nCircuit breaker reset completed!")
        print("You can now restart trading through the dashboard or API.")
        
    except ImportError as e:
        print(f"Import error: {e}")
        print("The orchestrator modules may not be available in this context.")
        
    except Exception as e:
        print(f"Error resetting circuit breakers: {e}")
        print(f"Error type: {type(e).__name__}")

if __name__ == "__main__":
    print("Manual Circuit Breaker Reset Tool")
    print("=" * 50)
    
    asyncio.run(reset_circuit_breakers())