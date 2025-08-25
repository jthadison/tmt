#!/usr/bin/env python3
"""
Quick Trading System Readiness Test
Tests core functionality without complex imports
"""

import asyncio
import aiohttp
import logging
from dotenv import load_dotenv
import os
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_system_readiness():
    """Test core system components for readiness"""
    logger.info("=== TRADING SYSTEM READINESS CHECK ===")
    
    load_dotenv()
    results = {}
    
    # Test 1: OANDA Connection
    logger.info("\n1. OANDA Connection Test...")
    try:
        api_key = os.getenv("OANDA_API_KEY")
        account_id = os.getenv("OANDA_ACCOUNT_ID")
        
        if not api_key or not account_id:
            logger.error("   FAIL: Missing OANDA credentials")
            results["oanda"] = False
        else:
            base_url = "https://api-fxpractice.oanda.com"
            headers = {"Authorization": f"Bearer {api_key}"}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{base_url}/v3/accounts/{account_id}", headers=headers, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        balance = data.get("account", {}).get("balance", "0")
                        logger.info(f"   SUCCESS: Balance = {balance} USD")
                        results["oanda"] = True
                    else:
                        logger.error(f"   FAIL: HTTP {response.status}")
                        results["oanda"] = False
                        
    except Exception as e:
        logger.error(f"   FAIL: {e}")
        results["oanda"] = False
    
    # Test 2: Market Data Feed
    logger.info("\n2. Market Data Feed Test...")
    try:
        api_key = os.getenv("OANDA_API_KEY")
        account_id = os.getenv("OANDA_ACCOUNT_ID")
        base_url = "https://api-fxpractice.oanda.com"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{base_url}/v3/accounts/{account_id}/pricing",
                headers=headers,
                params={"instruments": "EUR_USD,GBP_USD"},
                timeout=10
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    prices = data.get("prices", [])
                    logger.info(f"   SUCCESS: {len(prices)} instruments streaming")
                    for price in prices:
                        logger.info(f"   - {price['instrument']}: {price['closeoutBid']}/{price['closeoutAsk']}")
                    results["market_data"] = True
                else:
                    logger.error(f"   FAIL: HTTP {response.status}")
                    results["market_data"] = False
                    
    except Exception as e:
        logger.error(f"   FAIL: {e}")
        results["market_data"] = False
    
    # Test 3: Core Dependencies
    logger.info("\n3. Dependencies Test...")
    try:
        required_packages = ["fastapi", "uvicorn", "aiohttp", "pandas", "pydantic", "python-dotenv"]
        missing = []
        
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                missing.append(package)
        
        if missing:
            logger.error(f"   FAIL: Missing packages: {missing}")
            results["dependencies"] = False
        else:
            logger.info("   SUCCESS: All dependencies available")
            results["dependencies"] = True
            
    except Exception as e:
        logger.error(f"   FAIL: {e}")
        results["dependencies"] = False
    
    # Test 4: File Structure
    logger.info("\n4. File Structure Test...")
    try:
        from pathlib import Path
        
        required_files = [
            "orchestrator/app/main.py",
            "orchestrator/app/orchestrator.py", 
            "orchestrator/app/trade_executor.py",
            "agents/market-analysis/app/main.py",
            "agents/market-analysis/app/signals/signal_generator.py",
            "start-system.py",
            ".env"
        ]
        
        missing_files = []
        for file_path in required_files:
            if not Path(file_path).exists():
                missing_files.append(file_path)
        
        if missing_files:
            logger.error(f"   FAIL: Missing files: {missing_files}")
            results["files"] = False
        else:
            logger.info("   SUCCESS: All required files present")
            results["files"] = True
            
    except Exception as e:
        logger.error(f"   FAIL: {e}")
        results["files"] = False
    
    # Test 5: Service Startup Test
    logger.info("\n5. Service Startup Test...")
    try:
        # Test if we can import the orchestrator main module
        import sys
        from pathlib import Path
        
        # Add orchestrator to path
        orchestrator_path = Path("orchestrator")
        if str(orchestrator_path) not in sys.path:
            sys.path.insert(0, str(orchestrator_path))
        
        # Try to import the main module
        from app.main import app
        logger.info("   SUCCESS: Orchestrator module imports successfully")
        results["startup"] = True
        
    except Exception as e:
        logger.error(f"   FAIL: {e}")
        results["startup"] = False
    
    # Generate Report
    logger.info("\n" + "="*50)
    logger.info("READINESS REPORT")
    logger.info("="*50)
    
    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result)
    
    for test_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        logger.info(f"  {test_name.replace('_', ' ').title():<20}: {status}")
    
    readiness_percent = (passed_tests / total_tests) * 100
    logger.info(f"\nSystem Readiness: {readiness_percent:.1f}%")
    
    if readiness_percent == 100:
        logger.info("STATUS: ✅ READY FOR PAPER TRADING")
        logger.info("\nTo start the system:")
        logger.info("  python start-system.py")
        logger.info("\nTo access dashboard:")
        logger.info("  http://localhost:8000")
        return True
    elif readiness_percent >= 80:
        logger.info("STATUS: ⚠️ MOSTLY READY")
        logger.info("Minor issues detected but system can start")
        return True
    else:
        logger.info("STATUS: ❌ NOT READY")
        logger.info("Critical issues must be resolved")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(test_system_readiness())
        exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Test failed: {e}")
        exit(1)