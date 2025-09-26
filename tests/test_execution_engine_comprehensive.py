#!/usr/bin/env python3
"""
Comprehensive Execution Engine Test Suite

Tests all critical functionality of the execution engine to prevent
bugs like the 'units_int' variable issue from reaching production.
"""

import asyncio
import aiohttp
import json
import logging
import pytest
from datetime import datetime, timezone
from typing import Dict, Any, List
from decimal import Decimal

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("execution_tests")

BASE_URL = "http://localhost:8082"


class TestExecutionEngine:
    """Comprehensive test suite for execution engine"""

    @pytest.fixture
    async def session(self):
        """Create aiohttp session for tests"""
        async with aiohttp.ClientSession() as session:
            yield session

    async def test_health_endpoint(self, session):
        """Test that health endpoint returns correct status"""
        async with session.get(f"{BASE_URL}/health") as response:
            assert response.status == 200
            data = await response.json()
            assert data["status"] == "running"
            assert "oanda_configured" in data
            logger.info("✅ Health check passed")

    async def test_market_order_valid(self, session):
        """Test placing a valid market order"""
        order = {
            "signal_id": "TEST_VALID_001",
            "instrument": "EUR_USD",
            "side": "buy",
            "units": 1000,
            "confidence": 80.0,
            "stop_loss_price": 1.0800,
            "take_profit_price": 1.0900,
            "account_id": "test_account"
        }

        async with session.post(f"{BASE_URL}/orders/market", json=order) as response:
            assert response.status == 200
            data = await response.json()

            # Check for the specific bug we found
            if not data.get("success"):
                error_msg = data.get("message", "")
                assert "units_int" not in error_msg, f"CRITICAL BUG: units_int variable error detected!"

            logger.info(f"✅ Market order test result: {data.get('success')}")

    async def test_market_order_missing_fields(self, session):
        """Test market order with missing required fields"""
        # Missing stop_loss_price
        order = {
            "signal_id": "TEST_MISSING_001",
            "instrument": "EUR_USD",
            "side": "buy",
            "units": 1000,
            "take_profit_price": 1.0900
        }

        async with session.post(f"{BASE_URL}/orders/market", json=order) as response:
            # Should return 400 or 422 for validation error
            assert response.status in [400, 422]
            logger.info("✅ Missing field validation works")

    async def test_market_order_invalid_side(self, session):
        """Test market order with invalid side"""
        order = {
            "signal_id": "TEST_INVALID_001",
            "instrument": "EUR_USD",
            "side": "invalid_side",  # Should be 'buy' or 'sell'
            "units": 1000,
            "stop_loss_price": 1.0800,
            "take_profit_price": 1.0900
        }

        async with session.post(f"{BASE_URL}/orders/market", json=order) as response:
            assert response.status in [400, 422]
            logger.info("✅ Invalid side validation works")

    async def test_positions_endpoint(self, session):
        """Test positions retrieval endpoint"""
        async with session.get(f"{BASE_URL}/positions") as response:
            assert response.status == 200
            data = await response.json()
            assert isinstance(data, (list, dict))
            logger.info("✅ Positions endpoint works")

    async def test_emergency_close_all(self, session):
        """Test emergency close all positions endpoint"""
        # This should work even with no positions
        async with session.post(f"{BASE_URL}/emergency/close_all") as response:
            assert response.status == 200
            data = await response.json()
            assert "message" in data or "status" in data
            logger.info("✅ Emergency close endpoint works")

    async def test_fifo_violation_check(self, session):
        """Test that FIFO violation checking doesn't crash"""
        # This specifically tests the bug we found
        order = {
            "signal_id": "TEST_FIFO_001",
            "instrument": "USD_JPY",  # Different instrument
            "side": "sell",
            "units": 500,
            "confidence": 70.0,
            "stop_loss_price": 110.50,
            "take_profit_price": 109.50,
            "account_id": "test_account"
        }

        async with session.post(f"{BASE_URL}/orders/market", json=order) as response:
            assert response.status == 200
            data = await response.json()

            # The key test: ensure no units_int error
            if not data.get("success"):
                error_msg = data.get("message", "")
                assert "units_int" not in error_msg, f"CRITICAL BUG: units_int error in FIFO check!"

            logger.info("✅ FIFO violation check doesn't crash")

    async def test_large_position_size(self, session):
        """Test handling of large position sizes"""
        order = {
            "signal_id": "TEST_LARGE_001",
            "instrument": "EUR_USD",
            "side": "buy",
            "units": 100000,  # Large position
            "confidence": 90.0,
            "stop_loss_price": 1.0800,
            "take_profit_price": 1.0900,
            "account_id": "test_account"
        }

        async with session.post(f"{BASE_URL}/orders/market", json=order) as response:
            assert response.status in [200, 400]  # May reject due to size
            data = await response.json()

            # Check no crash due to integer handling
            if not data.get("success"):
                error_msg = data.get("message", "")
                assert "units_int" not in error_msg

            logger.info("✅ Large position handling works")


async def run_all_tests():
    """Run all execution engine tests"""
    logger.info("🚀 Starting Comprehensive Execution Engine Tests")
    logger.info("=" * 60)

    test_suite = TestExecutionEngine()
    session = aiohttp.ClientSession()

    try:
        # Run all tests
        await test_suite.test_health_endpoint(session)
        await test_suite.test_market_order_valid(session)
        await test_suite.test_market_order_missing_fields(session)
        await test_suite.test_market_order_invalid_side(session)
        await test_suite.test_positions_endpoint(session)
        await test_suite.test_emergency_close_all(session)
        await test_suite.test_fifo_violation_check(session)
        await test_suite.test_large_position_size(session)

        logger.info("\n" + "=" * 60)
        logger.info("✅ ALL TESTS PASSED")
        logger.info("Execution engine is functioning correctly")
        return True

    except AssertionError as e:
        logger.error(f"\n❌ TEST FAILED: {e}")
        return False

    except Exception as e:
        logger.error(f"\n❌ UNEXPECTED ERROR: {e}")
        return False

    finally:
        await session.close()


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)