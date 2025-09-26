#!/usr/bin/env python3
"""
Execution Engine Order Placement Test

This test specifically validates the order placement functionality
to catch bugs like the 'units_int' undefined variable error.
"""

import asyncio
import aiohttp
import json
import logging
from datetime import datetime
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("execution_test")

async def test_order_placement():
    """Test the execution engine's order placement functionality"""

    logger.info("🚀 Testing Execution Engine Order Placement")
    logger.info("=" * 60)

    # Test order payload - matching what the orchestrator would send
    test_order = {
        "signal_id": "TEST_001",
        "instrument": "EUR_USD",
        "side": "buy",
        "units": 1000,
        "confidence": 75.0,
        "stop_loss_price": 1.0800,  # Example price
        "take_profit_price": 1.0900,  # Example price
        "account_id": "test_account",
        "metadata": {
            "source": "integration_test",
            "timestamp": datetime.utcnow().isoformat()
        }
    }

    try:
        async with aiohttp.ClientSession() as session:
            # Test 1: Health check
            logger.info("📋 Step 1: Checking execution engine health...")
            async with session.get("http://localhost:8082/health") as response:
                if response.status == 200:
                    health = await response.json()
                    logger.info(f"  ✅ Health check passed: {health['status']}")
                else:
                    logger.error(f"  ❌ Health check failed: HTTP {response.status}")
                    return False

            # Test 2: Place market order
            logger.info("\n📋 Step 2: Testing market order placement...")
            logger.info(f"  Order details: {test_order['instrument']} {test_order['side']} {test_order['units']} units")

            async with session.post(
                "http://localhost:8082/orders/market",
                json=test_order,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                response_text = await response.text()

                if response.status == 200:
                    result = json.loads(response_text)
                    logger.info(f"  ✅ Order placement successful!")
                    logger.info(f"  Response: {json.dumps(result, indent=2)}")

                    # Check for expected fields in response
                    if "success" in result:
                        if result["success"]:
                            logger.info(f"  ✅ Order executed successfully")
                        else:
                            logger.error(f"  ❌ Order failed: {result.get('message', 'Unknown error')}")
                            # This would catch our 'units_int' error!
                            if "units_int" in result.get("message", ""):
                                logger.error("  🐛 BUG DETECTED: Variable naming error in order placement!")
                            return False

                    return True

                elif response.status == 422:
                    logger.error(f"  ❌ Validation error: {response_text}")
                    return False

                elif response.status == 500:
                    logger.error(f"  ❌ Internal server error: {response_text}")
                    # Check for the specific bug
                    if "units_int" in response_text:
                        logger.error("  🐛 BUG DETECTED: 'units_int' is not defined error!")
                        logger.error("  This is the exact bug that prevented trade execution!")
                    return False

                else:
                    logger.error(f"  ❌ Unexpected response: HTTP {response.status}")
                    logger.error(f"  Response: {response_text}")
                    return False

    except asyncio.TimeoutError:
        logger.error("  ❌ Request timed out - execution engine may be hanging")
        return False

    except Exception as e:
        logger.error(f"  ❌ Test failed with exception: {e}")
        return False

async def main():
    """Run the test suite"""
    success = await test_order_placement()

    logger.info("\n" + "=" * 60)
    if success:
        logger.info("✅ EXECUTION ENGINE TEST PASSED")
        logger.info("The order placement functionality is working correctly")
    else:
        logger.info("❌ EXECUTION ENGINE TEST FAILED")
        logger.info("Order placement has issues that need to be fixed")
        logger.info("\n⚠️  This test would have caught the 'units_int' bug!")

    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)